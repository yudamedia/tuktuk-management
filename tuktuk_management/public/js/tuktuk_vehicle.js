// ~/frappe-bench/apps/tuktuk_management/tuktuk_management/public/js/tuktuk_vehicle.js
// Enhanced TukTuk Vehicle client script with device mapping integration

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
        
        // Add real-time location and battery display
        if (frm.doc.latitude && frm.doc.longitude) {
            add_location_display(frm);
        }
        
        // Show device mapping status
        show_device_mapping_status(frm);
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
        // Refresh form actions when status changes
        setup_form_actions(frm);
        setup_indicators(frm);
    }
});

// Device Mapping Functions
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
            
            frm.add_custom_button(__('View Available Devices'), function() {
                view_available_devices(frm);
            }, __('Device Mapping'));
        } else {
            // Device already mapped - show management options
            frm.add_custom_button(__('Update from Device'), function() {
                update_from_telematics(frm);
            }, __('Device Mapping'));
            
            frm.add_custom_button(__('Reset Device Mapping'), function() {
                reset_device_mapping(frm);
            }, __('Device Mapping'));
            
            frm.add_custom_button(__('Validate Mapping'), function() {
                validate_device_mapping(frm);
            }, __('Device Mapping'));
            
            frm.add_custom_button(__('View Location History'), function() {
                view_location_history(frm);
            }, __('Device Mapping'));
        }
    }
}

function auto_map_device(frm) {
    frappe.call({
        method: 'tuktuk_management.api.device_mapping.get_unmapped_devices',
        callback: function(r) {
            if (r.message && r.message.mapping_suggestions.length > 0) {
                // Find suggestion for this tuktuk
                const suggestion = r.message.mapping_suggestions.find(s => s.tuktuk_name === frm.docname);
                
                if (suggestion) {
                    frappe.confirm(
                        __('Auto-map device {0} (IMEI: {1}) to this TukTuk?<br><br>Device Status: {2}<br>Confidence: {3}', 
                           [suggestion.suggested_device_id, suggestion.suggested_imei, 
                            suggestion.device_status, suggestion.confidence]),
                        function() {
                            apply_device_mapping(frm, suggestion.suggested_device_id, suggestion.suggested_imei);
                        }
                    );
                } else {
                    frappe.msgprint(__('No available devices found for auto-mapping'));
                }
            } else {
                frappe.msgprint(__('No unmapped devices available'));
            }
        }
    });
}

function manual_map_device_dialog(frm) {
    // Get available devices first
    frappe.call({
        method: 'tuktuk_management.api.device_mapping.get_unmapped_devices',
        callback: function(r) {
            if (r.message && r.message.available_devices.length > 0) {
                show_device_selection_dialog(frm, r.message.available_devices);
            } else {
                frappe.msgprint(__('No available devices to map'));
            }
        }
    });
}

function show_device_selection_dialog(frm, devices) {
    const device_options = devices.map(d => ({
        label: `Device ${d.device_id} (${d.imei}) - ${d.status}`,
        value: JSON.stringify({device_id: d.device_id, imei: d.imei})
    }));
    
    const dialog = new frappe.ui.Dialog({
        title: __('Select Device to Map'),
        fields: [
            {
                fieldtype: 'Select',
                fieldname: 'selected_device',
                label: __('Available Devices'),
                options: device_options,
                reqd: 1
            },
            {
                fieldtype: 'HTML',
                fieldname: 'device_info',
                options: '<div id="device-info-display"></div>'
            }
        ],
        primary_action: function(values) {
            const device_data = JSON.parse(values.selected_device);
            apply_device_mapping(frm, device_data.device_id, device_data.imei);
            dialog.hide();
        },
        primary_action_label: __('Map Device')
    });
    
    dialog.show();
    
    // Add device info display when selection changes
    dialog.fields_dict.selected_device.$input.on('change', function() {
        const selected = JSON.parse(this.value);
        const device = devices.find(d => d.device_id === selected.device_id);
        if (device) {
            $('#device-info-display').html(`
                <div class="alert alert-info">
                    <strong>Device Details:</strong><br>
                    Device ID: ${device.device_id}<br>
                    IMEI: ${device.imei}<br>
                    Status: ${device.status}<br>
                    Last Location: ${device.lat || 'N/A'}, ${device.lng || 'N/A'}
                </div>
            `);
        }
    });
}

function apply_device_mapping(frm, device_id, device_imei) {
    frappe.call({
        method: 'tuktuk_management.api.device_mapping.manual_device_mapping',
        args: {
            tuktuk_vehicle: frm.docname,
            device_id: device_id,
            device_imei: device_imei
        },
        callback: function(r) {
            if (r.message && r.message.success) {
                frappe.show_alert({
                    message: r.message.message,
                    indicator: 'green'
                });
                
                // Refresh the form to show new mapping
                frm.reload_doc();
            } else {
                frappe.msgprint(__('Device mapping failed: {0}', [r.message.message || 'Unknown error']));
            }
        }
    });
}

function reset_device_mapping(frm) {
    frappe.confirm(
        __('Reset device mapping for this TukTuk? This will remove the device ID and IMEI.'),
        function() {
            frappe.call({
                method: 'tuktuk_management.api.device_mapping.reset_device_mapping',
                args: {
                    tuktuk_vehicle: frm.docname
                },
                callback: function(r) {
                    if (r.message && r.message.success) {
                        frappe.show_alert({
                            message: r.message.message,
                            indicator: 'orange'
                        });
                        frm.reload_doc();
                    }
                }
            });
        }
    );
}

function validate_device_mapping(frm) {
    frappe.call({
        method: 'tuktuk_management.api.device_mapping.validate_device_mappings',
        callback: function(r) {
            if (r.message) {
                const results = r.message;
                let message = `
                    <strong>Device Mapping Validation Results:</strong><br><br>
                    Total Vehicles: ${results.total_vehicles}<br>
                    Mapped: ${results.mapped_vehicles}<br>
                    Unmapped: ${results.unmapped_vehicles}<br>
                    Recent Updates: ${results.recent_updates}<br>
                `;
                
                if (results.duplicate_mappings.length > 0) {
                    message += '<br><strong>⚠️ Duplicate Mappings Found:</strong><br>';
                    results.duplicate_mappings.forEach(dup => {
                        message += `Device ${dup.device_id || dup.imei}: ${dup.vehicles.join(', ')}<br>`;
                    });
                }
                
                if (results.inactive_devices.length > 0) {
                    message += '<br><strong>🔴 Inactive Devices:</strong><br>';
                    results.inactive_devices.forEach(inactive => {
                        message += `${inactive.tuktuk_id}: Last seen ${inactive.hours_ago}h ago<br>`;
                    });
                }
                
                frappe.msgprint({
                    title: __('Validation Results'),
                    message: message,
                    indicator: results.duplicate_mappings.length > 0 ? 'red' : 'blue'
                });
            }
        }
    });
}

function view_available_devices(frm) {
    frappe.call({
        method: 'tuktuk_management.api.device_mapping.get_unmapped_devices',
        callback: function(r) {
            if (r.message) {
                const data = r.message;
                let message = '<strong>Device Mapping Overview:</strong><br><br>';
                
                message += `<strong>Unmapped Vehicles (${data.unmapped_vehicles.length}):</strong><br>`;
                data.unmapped_vehicles.forEach(v => {
                    message += `• ${v.tuktuk_id} (${v.status})<br>`;
                });
                
                message += `<br><strong>Available Devices (${data.available_devices.length}):</strong><br>`;
                data.available_devices.forEach(d => {
                    message += `• Device ${d.device_id} - ${d.imei} (${d.status})<br>`;
                });
                
                if (data.mapping_suggestions.length > 0) {
                    message += '<br><strong>Suggested Mappings:</strong><br>';
                    data.mapping_suggestions.forEach(s => {
                        message += `• ${s.tuktuk_id} → Device ${s.suggested_device_id}<br>`;
                    });
                }
                
                frappe.msgprint({
                    title: __('Available Devices'),
                    message: message
                });
            }
        }
    });
}

// Enhanced Status and Display Functions
function show_device_mapping_status(frm) {
    if (frm.doc.device_id && frm.doc.device_imei) {
        // Device is mapped - show status
        const status_html = `
            <div class="device-mapping-status" style="background: #e8f5e8; padding: 10px; border-radius: 4px; margin: 10px 0;">
                <strong>📱 Device Mapped:</strong><br>
                Device ID: ${frm.doc.device_id}<br>
                IMEI: ${frm.doc.device_imei}<br>
                ${frm.doc.last_reported ? `Last Update: ${frappe.datetime.str_to_user(frm.doc.last_reported)}` : 'No recent updates'}
            </div>
        `;
        
        frm.dashboard.add_comment(status_html);
    } else {
        // No device mapped - show warning
        const warning_html = `
            <div class="device-mapping-warning" style="background: #fff3cd; padding: 10px; border-radius: 4px; margin: 10px 0;">
                <strong>⚠️ No Device Mapped</strong><br>
                This TukTuk is not connected to a telematics device. 
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

// Existing Functions (Enhanced)
function setup_form_actions(frm) {
    // Clear existing custom buttons
    frm.clear_custom_buttons();
    
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
    
    // Add status indicator
    let status_color = get_status_color(frm.doc.status);
    frm.dashboard.add_indicator(__('Status: {0}', [frm.doc.status]), status_color);
    
    // Add device connectivity indicator
    if (frm.doc.device_id) {
        const connectivity_color = frm.doc.last_reported ? 
            (flt(frappe.datetime.get_diff(frappe.datetime.now_datetime(), frm.doc.last_reported)) < 1 ? 'green' : 'orange') : 
            'red';
        frm.dashboard.add_indicator(__('Device: Connected'), connectivity_color);
    } else {
        frm.dashboard.add_indicator(__('Device: Not Mapped'), 'red');
    }
    
    // Add last reported indicator if available
    if (frm.doc.last_reported) {
        let time_diff = flt(frappe.datetime.get_diff(frappe.datetime.now_datetime(), frm.doc.last_reported));
        let hours_ago = cint(Math.floor(time_diff / 3600));
        let indicator_color = hours_ago > 24 ? 'red' : (hours_ago > 6 ? 'orange' : 'green');
        frm.dashboard.add_indicator(__('Last Update: {0}h ago', [hours_ago]), indicator_color);
    }
}

function add_battery_indicator(frm) {
    const battery_level = flt(frm.doc.battery_level);
    let color = 'green';
    let icon = '🔋';
    
    if (battery_level <= 10) {
        color = 'red';
        icon = '🪫';
    } else if (battery_level <= 25) {
        color = 'orange';
        icon = '🔋';
    } else if (battery_level <= 50) {
        color = 'yellow';
        icon = '🔋';
    }
    
    frm.dashboard.add_indicator(__('Battery: {0}% {1}', [battery_level, icon]), color);
}

function add_location_display(frm) {
    if (frm.doc.latitude && frm.doc.longitude) {
        const location_html = `
            <div class="location-display" style="background: #f8f9fa; padding: 10px; border-radius: 4px; margin: 10px 0;">
                <strong>📍 Current Location:</strong><br>
                Latitude: ${frm.doc.latitude}<br>
                Longitude: ${frm.doc.longitude}<br>
                ${frm.doc.current_location ? `Address: ${frm.doc.current_location}` : ''}
                <br><br>
                <button class="btn btn-xs btn-primary" onclick="view_on_map_inline('${frm.doc.latitude}', '${frm.doc.longitude}')">
                    View on Map
                </button>
            </div>
        `;
        
        frm.dashboard.add_comment(location_html);
    }
}

// Utility Functions
function get_status_color(status) {
    const status_colors = {
        'Available': 'green',
        'Assigned': 'blue',
        'Charging': 'orange',
        'Maintenance': 'red',
        'Out of Service': 'red'
    };
    return status_colors[status] || 'gray';
}

function view_on_map(frm) {
    if (frm.doc.latitude && frm.doc.longitude) {
        const url = `https://www.google.com/maps?q=${frm.doc.latitude},${frm.doc.longitude}&z=15`;
        window.open(url, '_blank');
    } else {
        frappe.msgprint(__('No location data available'));
    }
}

// Global function for inline map viewing
window.view_on_map_inline = function(lat, lng) {
    const url = `https://www.google.com/maps?q=${lat},${lng}&z=15`;
    window.open(url, '_blank');
};

// Status change functions
function assign_to_driver(frm) {
    frappe.route_options = {
        "assigned_tuktuk": ""
    };
    frappe.new_doc("TukTuk Driver");
}

function set_charging(frm) {
    frm.set_value('status', 'Charging');
    frm.save();
}

function set_maintenance(frm) {
    frm.set_value('status', 'Maintenance');
    frm.save();
}

function complete_charging(frm) {
    frm.set_value('status', 'Assigned');
    frm.set_value('battery_level', 100);
    frm.save();
}

function update_from_telematics(frm) {
    if (frm.doc.device_id) {
        frappe.call({
            method: 'tuktuk_management.api.telematics.update_vehicle_status',
            args: {
                device_id: frm.doc.device_id
            },
            callback: function(r) {
                if (r.message && r.message.success) {
                    frappe.show_alert({
                        message: __('Telematics data updated'),
                        indicator: 'green'
                    });
                    frm.reload_doc();
                } else {
                    frappe.msgprint(__('Failed to update from telematics device'));
                }
            }
        });
    }
}

function view_location_history(frm) {
    frappe.route_options = {
        "tuktuk_vehicle": frm.docname
    };
    frappe.set_route("query-report", "TukTuk Location History");
}