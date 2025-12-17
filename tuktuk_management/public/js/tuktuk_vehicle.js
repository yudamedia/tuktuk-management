// ~/frappe-bench/apps/tuktuk_management/tuktuk_management/public/js/tuktuk_vehicle.js
// Complete TukTuk Vehicle client script with device mapping integration AND substitute driver management

// Ensure Frappe utility functions are available for type safety
if (typeof flt === 'undefined') {
    window.flt = function(value, precision = 2) {
        if (value === null || value === undefined || value === '') return 0;
        const num = parseFloat(value);
        return isNaN(num) ? 0 : parseFloat(num.toFixed(precision));
    };
}

if (typeof cint === 'undefined') {
    window.cint = function(value) {
        if (value === null || value === undefined || value === '') return 0;
        const num = parseInt(value);
        return isNaN(num) ? 0 : num;
    };
}

frappe.ui.form.on('TukTuk Vehicle', {
    refresh: function(frm) {
        // Setup custom buttons and indicators
        setup_form_actions(frm);
        setup_indicators(frm);
        setup_device_mapping_buttons(frm);
        
        // Add substitute driver management buttons
        setup_substitute_driver_buttons(frm);
        
        // Add real-time location and battery display
        if (frm.doc.latitude && frm.doc.longitude) {
            add_location_display(frm);
        }
        
        // Show device mapping status
        show_device_mapping_status(frm);
        
        // Show substitute assignment info if applicable
        if (frm.doc.current_substitute_driver) {
            show_substitute_info(frm);
        }
    },
    
    device_id: function(frm) {
        // When device ID changes, validate and fetch initial data
        if (frm.doc.device_id && frm.doc.device_imei) {
            fetch_initial_device_data(frm);
        }
    },
    
    device_imei: function(frm) {
        // When IMEI changes, validate format
        if (frm.doc.device_imei) {
            validate_imei_format(frm);
        }
    },
    
    battery_level: function(frm) {
        // Update indicators when battery level changes
        setup_indicators(frm);
    },
    
    status: function(frm) {
        // Handle status changes
        if (frm.doc.status === 'Subbed' && !frm.doc.current_substitute_driver) {
            frappe.msgprint(__('Please assign a substitute driver'));
            frm.set_value('status', frm.doc.__oldstatus || 'Available');
        }
        
        // Refresh form actions when status changes
        setup_form_actions(frm);
        setup_indicators(frm);
    },
    
    current_substitute_driver: function(frm) {
        if (frm.doc.current_substitute_driver && frm.doc.status !== 'Subbed') {
            frm.set_value('status', 'Subbed');
        } else if (!frm.doc.current_substitute_driver && frm.doc.status === 'Subbed') {
            // Reset to appropriate status
            if (frm.doc.assigned_driver) {
                frm.set_value('status', 'Assigned');
            } else {
                frm.set_value('status', 'Available');
            }
        }
    }
});

// ===== SUBSTITUTE DRIVER MANAGEMENT FUNCTIONS =====

function setup_substitute_driver_buttons(frm) {
    if (!frm.is_new()) {
        // Add button to suggest substitute driver
        if (frm.doc.assigned_driver && !frm.doc.current_substitute_driver) {
            frm.add_custom_button(__('Assign Substitute Driver'), function() {
                suggest_and_assign_substitute(frm);
            }, __('Actions'));
        }
        
        // Add button to remove substitute
        if (frm.doc.current_substitute_driver) {
            frm.add_custom_button(__('Remove Substitute Driver'), function() {
                remove_substitute_driver(frm);
            }, __('Actions'));
        }
        
        // Add button to view transactions
        frm.add_custom_button(__('View Transactions'), function() {
            frappe.set_route('List', 'TukTuk Transaction', {
                'tuktuk': frm.doc.name
            });
        }, __('Reports'));
    }
}

function show_substitute_info(frm) {
    frappe.call({
        method: 'frappe.client.get',
        args: {
            doctype: 'TukTuk Substitute Driver',
            name: frm.doc.current_substitute_driver
        },
        callback: function(r) {
            if (r.message) {
                const sub_driver = r.message;
                const info_html = `
                    <div class="alert alert-info">
                        <strong>Substitute Driver Active:</strong> ${sub_driver.first_name} ${sub_driver.last_name}
                        <br><strong>Phone:</strong> ${sub_driver.phone_number}
                        <br><strong>Assigned Since:</strong> ${frappe.datetime.str_to_user(frm.doc.substitute_assignment_date)}
                    </div>
                `;
                frm.set_df_property('current_substitute_driver', 'description', info_html);
            }
        }
    });
}

function suggest_and_assign_substitute(frm) {
    frappe.call({
        method: 'tuktuk_management.tuktuk_management.doctype.tuktuk_substitute_driver.tuktuk_substitute_driver.suggest_substitute_for_vehicle',
        args: {
            vehicle_name: frm.doc.name
        },
        callback: function(r) {
            if (r.message && r.message.success) {
                const suggested = r.message.suggested_driver;
                const all_available = r.message.all_available;
                
                // Create dialog to show suggestions
                let options_html = '<div class="row">';
                
                all_available.forEach(driver => {
                    const is_suggested = driver.name === suggested.name;
                    options_html += `
                        <div class="col-md-6">
                            <div class="card ${is_suggested ? 'border-primary' : ''}" style="margin-bottom: 10px;">
                                <div class="card-body">
                                    ${is_suggested ? '<span class="badge badge-primary">Suggested</span>' : ''}
                                    <h5>${driver.first_name} ${driver.last_name}</h5>
                                    <p class="mb-1"><strong>Phone:</strong> ${driver.phone_number}</p>
                                    <p class="mb-1"><strong>Days Worked:</strong> ${driver.total_days_worked || 0}</p>
                                    <p class="mb-1"><strong>Avg Earnings:</strong> ${driver.average_daily_earnings ? driver.average_daily_earnings.toFixed(2) : '0.00'} KSH</p>
                                    <button class="btn btn-sm btn-primary assign-sub-btn" data-driver="${driver.name}">
                                        Assign
                                    </button>
                                </div>
                            </div>
                        </div>
                    `;
                });
                
                options_html += '</div>';
                
                let d = new frappe.ui.Dialog({
                    title: 'Select Substitute Driver',
                    fields: [{
                        fieldtype: 'HTML',
                        fieldname: 'driver_options',
                        options: options_html
                    }],
                    primary_action_label: 'Close'
                });
                
                d.show();
                
                // Add click handlers
                d.$wrapper.find('.assign-sub-btn').on('click', function() {
                    const driver_name = $(this).data('driver');
                    assign_substitute_driver(frm, driver_name);
                    d.hide();
                });
                
            } else {
                frappe.msgprint({
                    title: __('No Substitutes Available'),
                    message: r.message ? r.message.message : 'No substitute drivers available at this time',
                    indicator: 'orange'
                });
            }
        }
    });
}

function assign_substitute_driver(frm, substitute_driver_name) {
    frappe.call({
        method: 'tuktuk_management.tuktuk_management.doctype.tuktuk_substitute_driver.tuktuk_substitute_driver.assign_substitute_to_vehicle',
        args: {
            substitute_driver: substitute_driver_name,
            vehicle_name: frm.doc.name
        },
        callback: function(r) {
            if (r.message && r.message.success) {
                frappe.msgprint({
                    title: __('Success'),
                    message: r.message.message,
                    indicator: 'green'
                });
                frm.reload_doc();
            } else {
                frappe.msgprint({
                    title: __('Error'),
                    message: r.message ? r.message.message : 'Failed to assign substitute driver',
                    indicator: 'red'
                });
            }
        }
    });
}

function remove_substitute_driver(frm) {
    frappe.confirm(
        __('Are you sure you want to remove the substitute driver from this vehicle?'),
        function() {
            frappe.call({
                method: 'tuktuk_management.tuktuk_management.doctype.tuktuk_substitute_driver.tuktuk_substitute_driver.unassign_substitute_from_vehicle',
                args: {
                    substitute_driver: frm.doc.current_substitute_driver
                },
                callback: function(r) {
                    if (r.message && r.message.success) {
                        frappe.msgprint({
                            title: __('Success'),
                            message: r.message.message,
                            indicator: 'green'
                        });
                        frm.reload_doc();
                    } else {
                        frappe.msgprint({
                            title: __('Error'),
                            message: r.message ? r.message.message : 'Failed to remove substitute driver',
                            indicator: 'red'
                        });
                    }
                }
            });
        }
    );
}

// ===== DEVICE MAPPING FUNCTIONS =====

function setup_device_mapping_buttons(frm) {
    if (!frm.doc.__islocal) {
        // Add Device Mapping section
        if (!frm.doc.device_id || !frm.doc.device_imei) {
            // No device mapped - show mapping options
            frm.add_custom_button(__('Auto-Map Device'), function() {
                auto_map_device(frm);
            }, __('Device Mapping'));
            
            frm.add_custom_button(__('Manual Map Device'), function() {
                manual_map_device_dialog(frm);
            }, __('Device Mapping'));
        } else {
            // Device already mapped - show update and unmap options
            frm.add_custom_button(__('Update Device Data'), function() {
                fetch_initial_device_data(frm);
            }, __('Device Mapping'));
            
            frm.add_custom_button(__('Unmap Device'), function() {
                unmap_device(frm);
            }, __('Device Mapping'));
        }
    }
}

function auto_map_device(frm) {
    frappe.call({
        method: 'tuktuk_management.api.telematics.auto_map_device_to_vehicle',
        args: {
            tuktuk_id: frm.doc.tuktuk_id
        },
        freeze: true,
        freeze_message: __('Searching for device...'),
        callback: function(r) {
            if (r.message && r.message.success) {
                frappe.show_alert({
                    message: __('Device mapped successfully'),
                    indicator: 'green'
                });
                frm.reload_doc();
            } else {
                frappe.msgprint({
                    title: __('Auto-Mapping Failed'),
                    message: r.message ? r.message.message : 'No matching device found',
                    indicator: 'orange'
                });
            }
        }
    });
}

function manual_map_device_dialog(frm) {
    let d = new frappe.ui.Dialog({
        title: __('Manual Device Mapping'),
        fields: [
            {
                fieldtype: 'Data',
                fieldname: 'device_id',
                label: __('Device ID'),
                reqd: 1
            },
            {
                fieldtype: 'Data',
                fieldname: 'device_imei',
                label: __('Device IMEI'),
                reqd: 1,
                description: __('15-digit IMEI number')
            },
            {
                fieldtype: 'Data',
                fieldname: 'device_model',
                label: __('Device Model'),
                default: 'Teltonika'
            }
        ],
        primary_action: function(values) {
            // Validate IMEI format
            if (!/^\d{15}$/.test(values.device_imei)) {
                frappe.msgprint(__('IMEI must be exactly 15 digits'));
                return;
            }
            
            frm.set_value('device_id', values.device_id);
            frm.set_value('device_imei', values.device_imei);
            frm.set_value('telematics_device_model', values.device_model);
            
            frm.save().then(() => {
                frappe.show_alert({
                    message: __('Device mapped successfully'),
                    indicator: 'green'
                });
                d.hide();
                fetch_initial_device_data(frm);
            });
        },
        primary_action_label: __('Map Device')
    });
    
    d.show();
}

function unmap_device(frm) {
    frappe.confirm(
        __('Are you sure you want to unmap this device? Telemetry data will no longer be received.'),
        function() {
            frm.set_value('device_id', '');
            frm.set_value('device_imei', '');
            frm.save().then(() => {
                frappe.show_alert({
                    message: __('Device unmapped'),
                    indicator: 'orange'
                });
            });
        }
    );
}

function show_device_mapping_status(frm) {
    if (!frm.doc.device_id) {
        const warning_html = `
            <div class="alert alert-warning">
                <strong>No Telemetry Device Mapped</strong><br>
                This vehicle is not receiving real-time location and battery updates.<br>
                Use the Device Mapping buttons to connect a device for real-time tracking.
            </div>
        `;
        
        frm.dashboard.add_comment(warning_html);
    }
}

function fetch_initial_device_data(frm) {
    if (frm.doc.device_id) {
        frappe.call({
            method: 'tuktuk_management.api.telematics.update_vehicle_status',
            args: {
                device_id: frm.doc.device_id
            },
            callback: function(r) {
                if (r.message && r.message.success) {
                    frappe.show_alert({
                        message: __('Device data updated successfully'),
                        indicator: 'green'
                    });
                    
                    // Refresh form to show updated data
                    setTimeout(() => {
                        frm.reload_doc();
                    }, 1000);
                }
            }
        });
    }
}

function validate_imei_format(frm) {
    const imei = frm.doc.device_imei;
    if (imei && !/^\d{15}$/.test(imei)) {
        frappe.msgprint({
            title: __('Invalid IMEI Format'),
            message: __('IMEI should be exactly 15 digits'),
            indicator: 'red'
        });
    }
}

// ===== EXISTING FORM FUNCTIONS =====

function setup_form_actions(frm) {
    // Clear existing custom buttons (except those added by substitute driver and device mapping functions)
    // Note: We don't clear all custom buttons to preserve the ones added above
    
    // Add custom buttons based on status
    if (frm.doc.status === 'Available') {
        frm.add_custom_button(__('Assign to Driver'), function() {
            assign_to_driver(frm);
        }, __('Actions'));
    }
    
    if (frm.doc.status === 'Assigned') {
        frm.add_custom_button(__('Set to Charging'), function() {
            set_charging(frm);
        }, __('Actions'));
        
        frm.add_custom_button(__('Set to Maintenance'), function() {
            set_maintenance(frm);
        }, __('Actions'));
    }
    
    if (frm.doc.status === 'Charging') {
        frm.add_custom_button(__('Complete Charging'), function() {
            complete_charging(frm);
        }, __('Actions'));
    }
    
    // Location actions
    if (frm.doc.latitude && frm.doc.longitude) {
        frm.add_custom_button(__('View on Map'), function() {
            view_on_map(frm);
        }, __('Location'));
    }
}

function setup_indicators(frm) {
    // Clear existing indicators
    frm.dashboard.clear_headline();
    
    // Add battery level indicator
    if (frm.doc.battery_level !== undefined && frm.doc.battery_level !== null) {
        add_battery_indicator(frm);
    }
    
    // Add status indicator with color coding
    let status_color = get_status_color(frm.doc.status);
    frm.dashboard.add_indicator(__('Status: {0}', [frm.doc.status]), status_color);
    
    // Add device connectivity indicator
    if (frm.doc.device_id) {
        const connectivity_color = frm.doc.last_reported ? 
            (flt(frappe.datetime.get_diff(frappe.datetime.now_datetime(), frm.doc.last_reported)) < 1 ? 'green' : 'orange') : 'red';
        frm.dashboard.add_indicator(__('Device Connected'), connectivity_color);
    }
    
    // Add substitute driver indicator if applicable
    if (frm.doc.current_substitute_driver) {
        frm.dashboard.add_indicator(__('Substitute Driver Active'), 'orange');
    }
}

function add_battery_indicator(frm) {
    const battery = flt(frm.doc.battery_level);
    let color = 'green';
    let icon = '🔋';
    
    if (battery < 20) {
        color = 'red';
        icon = '🪫';
    } else if (battery < 50) {
        color = 'orange';
        icon = '🔋';
    }
    
    frm.dashboard.add_indicator(__(`${icon} Battery: {0}%`, [battery]), color);
}

function get_status_color(status) {
    const status_colors = {
        'Available': 'green',
        'Assigned': 'blue',
        'Subbed': 'orange',
        'Charging': 'yellow',
        'Maintenance': 'red',
        'Offline': 'gray'
    };
    return status_colors[status] || 'gray';
}

function add_location_display(frm) {
    if (frm.doc.latitude && frm.doc.longitude) {
        const map_link = `https://www.google.com/maps?q=${frm.doc.latitude},${frm.doc.longitude}`;
        const location_html = `
            <div class="alert alert-info">
                <strong>Last Known Location:</strong><br>
                Lat: ${frm.doc.latitude.toFixed(6)}, Long: ${frm.doc.longitude.toFixed(6)}<br>
                <a href="${map_link}" target="_blank" class="btn btn-xs btn-primary">
                    View on Google Maps
                </a>
            </div>
        `;
        frm.set_df_property('current_location', 'description', location_html);
    }
}

// ===== VEHICLE STATUS ACTIONS =====

function assign_to_driver(frm) {
    frappe.prompt([
        {
            label: 'Select Driver',
            fieldname: 'driver',
            fieldtype: 'Link',
            options: 'TukTuk Driver',
            reqd: 1,
            get_query: function() {
                return {
                    filters: {
                        'assigned_tuktuk': ['is', 'not set']
                    }
                };
            }
        }
    ], function(values) {
        frappe.call({
            method: 'frappe.client.set_value',
            args: {
                doctype: 'TukTuk Driver',
                name: values.driver,
                fieldname: 'assigned_tuktuk',
                value: frm.doc.name
            },
            callback: function(r) {
                if (!r.exc) {
                    frm.set_value('status', 'Assigned');
                    frm.set_value('assigned_driver', values.driver);
                    frm.save();
                    frappe.msgprint(__('Driver assigned successfully'));
                }
            }
        });
    }, __('Assign Driver'), __('Assign'));
}

function set_charging(frm) {
    frappe.confirm(
        __('Set this vehicle to charging status?'),
        function() {
            frm.set_value('status', 'Charging');
            frm.save();
        }
    );
}

function set_maintenance(frm) {
    frappe.prompt([
        {
            label: 'Maintenance Notes',
            fieldname: 'notes',
            fieldtype: 'Small Text',
            reqd: 1
        }
    ], function(values) {
        frm.set_value('status', 'Maintenance');
        frm.save().then(() => {
            // Add comment with maintenance notes
            frm.add_comment('Comment', `Maintenance: ${values.notes}`);
            frappe.msgprint(__('Vehicle set to maintenance'));
        });
    }, __('Maintenance Details'), __('Confirm'));
}

function complete_charging(frm) {
    frappe.confirm(
        __('Mark charging as complete?'),
        function() {
            // Reset to appropriate status
            if (frm.doc.assigned_driver) {
                frm.set_value('status', 'Assigned');
            } else {
                frm.set_value('status', 'Available');
            }
            frm.save();
        }
    );
}

function view_on_map(frm) {
    if (frm.doc.latitude && frm.doc.longitude) {
        const map_url = `https://www.google.com/maps?q=${frm.doc.latitude},${frm.doc.longitude}`;
        window.open(map_url, '_blank');
    } else {
        frappe.msgprint(__('No location data available'));
    }
}