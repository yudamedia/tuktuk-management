// ~/frappe-bench/apps/tuktuk_management/tuktuk_management/public/js/tuktuk_vehicle.js

frappe.ui.form.on('TukTuk Vehicle', {
    refresh: function(frm) {
        // Initialize form with error handling
        try {
            setup_form_actions(frm);
            setup_indicators(frm);
            setup_auto_fields(frm);
        } catch (error) {
            console.error('Error in form refresh:', error);
        }
    },
    
    tuktuk_id: function(frm) {
        // Auto-generate mpesa account based on tuktuk_id
        if (frm.doc.tuktuk_id && !frm.doc.mpesa_account) {
            auto_generate_mpesa_account(frm);
        }
    },
    
    battery_level: function(frm) {
        try {
            add_battery_indicator(frm);
            
            // Warn if battery is low
            if (frm.doc.battery_level <= 20) {
                frappe.msgprint({
                    title: __('Low Battery Warning'),
                    message: __('Battery level is at {0}%. Consider charging this TukTuk.', [frm.doc.battery_level]),
                    indicator: 'orange'
                });
            }
        } catch (error) {
            console.error('Error in battery_level handler:', error);
        }
    },
    
    before_save: function(frm) {
        try {
            // Validate required fields
            if (!frm.doc.tuktuk_id) {
                frappe.msgprint(__('TukTuk ID is required'));
                frappe.validated = false;
                return;
            }
            
            // Auto-generate mpesa account if not provided
            if (!frm.doc.mpesa_account) {
                auto_generate_mpesa_account(frm);
            }
        } catch (error) {
            console.error('Error in before_save:', error);
        }
    },
    
    // Handle geolocation field with error handling
    current_location: function(frm) {
        if (frm.doc.current_location) {
            try {
                // Update last reported time when location changes
                frm.set_value('last_reported', frappe.datetime.now_datetime());
            } catch (error) {
                console.error('Error updating location timestamp:', error);
            }
        }
    }
});

function setup_form_actions(frm) {
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
    
    // Add telematics actions if device is configured
    if (frm.doc.device_id && frm.doc.device_imei) {
        frm.add_custom_button(__('Update from Device'), function() {
            update_from_telematics(frm);
        }, __('Telematics'));
        
        frm.add_custom_button(__('View Location History'), function() {
            view_location_history(frm);
        }, __('Telematics'));
    }
}

function setup_indicators(frm) {
    // Add battery level indicator
    if (frm.doc.battery_level !== undefined) {
        add_battery_indicator(frm);
    }
    
    // Add status indicator
    let status_color = get_status_color(frm.doc.status);
    frm.dashboard.add_indicator(__('Status: {0}', [frm.doc.status]), status_color);
    
    // Add last reported indicator if available
    if (frm.doc.last_reported) {
        let time_diff = frappe.datetime.get_diff(frappe.datetime.now_datetime(), frm.doc.last_reported);
        let hours_ago = Math.floor(time_diff / 3600);
        let indicator_color = hours_ago > 24 ? 'red' : (hours_ago > 6 ? 'orange' : 'green');
        frm.dashboard.add_indicator(__('Last Report: {0}h ago', [hours_ago]), indicator_color);
    }
}

function setup_auto_fields(frm) {
    // Auto-generate mpesa account if not set
    if (!frm.doc.mpesa_account && !frm.doc.__islocal && frm.doc.tuktuk_id) {
        auto_generate_mpesa_account(frm);
    }
}

function assign_to_driver(frm) {
    frappe.prompt([
        {
            label: 'Driver',
            fieldname: 'driver',
            fieldtype: 'Link',
            options: 'TukTuk Driver',
            reqd: 1,
            get_query: function() {
                return {
                    filters: {
                        'assigned_tuktuk': ['in', ['', null]]
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
                    frm.save();
                    frappe.msgprint(__('Driver assigned successfully'));
                }
            }
        });
    }, __('Assign Driver'), __('Assign'));
}

function set_charging(frm) {
    frappe.confirm(
        __('Set this TukTuk to charging status? This will free up the driver to rent another vehicle.'),
        function() {
            frm.set_value('status', 'Charging');
            frm.save();
        }
    );
}

function complete_charging(frm) {
    frappe.prompt([
        {
            label: 'Battery Level After Charging',
            fieldname: 'battery_level',
            fieldtype: 'Percent',
            default: 100,
            reqd: 1
        }
    ], function(values) {
        frm.set_value('battery_level', values.battery_level);
        frm.set_value('status', 'Assigned');
        frm.save();
        frappe.msgprint(__('Charging completed. Vehicle is ready for service.'));
    }, __('Complete Charging'), __('Complete'));
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
        frm.save();
        
        // Add comment with maintenance notes
        frappe.call({
            method: 'frappe.desk.form.utils.add_comment',
            args: {
                reference_doctype: frm.doctype,
                reference_name: frm.docname,
                content: 'Maintenance: ' + values.notes,
                comment_email: frappe.session.user,
                comment_by: frappe.session.user_fullname
            }
        });
    }, __('Maintenance Details'), __('Set to Maintenance'));
}

function add_battery_indicator(frm) {
    if (frm.doc.battery_level !== undefined) {
        let color = 'green';
        let status = 'Good';
        
        if (frm.doc.battery_level <= 20) {
            color = 'red';
            status = 'Low - Charge Required';
        } else if (frm.doc.battery_level <= 50) {
            color = 'orange';
            status = 'Medium';
        }
        
        frm.dashboard.add_indicator(__('Battery: {0}% - {1}', [frm.doc.battery_level, status]), color);
    }
}

function get_status_color(status) {
    switch (status) {
        case 'Available': return 'green';
        case 'Assigned': return 'blue';
        case 'Charging': return 'orange';
        case 'Maintenance': return 'red';
        default: return 'gray';
    }
}

function auto_generate_mpesa_account(frm) {
    if (frm.doc.tuktuk_id) {
        // Extract number from tuktuk_id or use a simple incrementing number
        let account_number = '';
        
        // If tuktuk_id contains numbers, extract them
        let numbers = frm.doc.tuktuk_id.match(/\d+/g);
        if (numbers && numbers.length > 0) {
            account_number = numbers[0].padStart(3, '0').slice(-3);
        } else {
            // Fallback: use last 3 characters if they're digits, or generate
            let lastThree = frm.doc.tuktuk_id.slice(-3);
            if (/^\d{3}$/.test(lastThree)) {
                account_number = lastThree;
            } else {
                // Generate based on creation order or random
                account_number = String(Math.floor(Math.random() * 900) + 100);
            }
        }
        
        frm.set_value('mpesa_account', account_number);
    }
}

function update_from_telematics(frm) {
    if (!frm.doc.device_id) {
        frappe.msgprint(__('Device ID is required for telematics update'));
        return;
    }
    
    frappe.call({
        method: 'tuktuk_management.api.telematics.update_from_device',
        args: {
            vehicle_name: frm.doc.name,
            device_id: frm.doc.device_id
        },
        callback: function(r) {
            if (r.message) {
                frm.refresh();
                frappe.msgprint(__('Vehicle data updated from telematics device'));
            }
        }
    });
}

function view_location_history(frm) {
    frappe.route_options = {
        'vehicle': frm.doc.name
    };
    frappe.set_route('query-report', 'Vehicle Location History');
}