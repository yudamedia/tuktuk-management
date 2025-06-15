// ~/frappe-bench/apps/tuktuk_management/tuktuk_management/public/js/tuktuk_driver.js

frappe.ui.form.on('TukTuk Driver', {
    refresh: function(frm) {
        // Set driver name if not set
        if (!frm.doc.driver_name) {
            set_driver_name(frm);
        }
        
        // Add custom buttons and indicators for existing records
        if (!frm.doc.__islocal) {
            setup_custom_buttons(frm);
            setup_indicators(frm);
        }
    },
    
    driver_first_name: function(frm) {
        set_driver_name(frm);
    },
    
    driver_middle_name: function(frm) {
        set_driver_name(frm);
    },
    
    driver_last_name: function(frm) {
        set_driver_name(frm);
    },
    
    before_save: function(frm) {
        // Ensure driver name is set before saving
        set_driver_name(frm);
    },
    
    assigned_tuktuk: function(frm) {
        // When tuktuk assignment changes, show tuktuk details
        if (frm.doc.assigned_tuktuk) {
            frappe.call({
                method: 'frappe.client.get',
                args: {
                    doctype: 'TukTuk Vehicle',
                    name: frm.doc.assigned_tuktuk
                },
                callback: function(r) {
                    if (r.message) {
                        const tuktuk = r.message;
                        frm.dashboard.add_indicator(__('TukTuk: {0} (Battery: {1}%)', 
                            [tuktuk.tuktuk_id, tuktuk.battery_level]), 
                            tuktuk.battery_level > 50 ? 'green' : 'orange');
                    }
                }
            });
        }
    },
    
    daily_target: function(frm) {
        // Refresh indicators when target changes
        if (!frm.doc.__islocal) {
            setup_indicators(frm);
        }
    },
    
    current_balance: function(frm) {
        // Refresh indicators when balance changes
        if (!frm.doc.__islocal) {
            setup_indicators(frm);
        }
    }
});

function set_driver_name(frm) {
    const firstName = frm.doc.driver_first_name || '';
    const middleName = frm.doc.driver_middle_name || '';
    const lastName = frm.doc.driver_last_name || '';
    
    const fullName = [firstName, middleName, lastName].filter(Boolean).join(' ');
    
    // Set the name if it's different and form is either new or saved
    if (fullName && fullName !== frm.doc.driver_name) {
        frm.set_value('driver_name', fullName);
    }
}

function setup_custom_buttons(frm) {
    // Clear existing custom buttons
    frm.clear_custom_buttons();
    
    // Add button to view driver transactions
    frm.add_custom_button(__('View Transactions'), function() {
        frappe.route_options = {
            'driver': frm.doc.name
        };
        frappe.set_route('List', 'TukTuk Transaction');
    }, __('Reports'));
    
    // Add button to view performance report
    frm.add_custom_button(__('Performance Report'), function() {
        frappe.route_options = {
            'driver': frm.doc.name,
            'from_date': frappe.datetime.add_days(frappe.datetime.get_today(), -30),
            'to_date': frappe.datetime.get_today()
        };
        frappe.set_route('query-report', 'Driver Performance Report');
    }, __('Reports'));
    
    // Add button to view rentals
    frm.add_custom_button(__('View Rentals'), function() {
        frappe.route_options = {
            'driver': frm.doc.name
        };
        frappe.set_route('List', 'TukTuk Rental');
    }, __('Reports'));
    
    // Add action buttons based on driver status
    if (!frm.doc.assigned_tuktuk) {
        frm.add_custom_button(__('Assign TukTuk'), function() {
            assign_tuktuk(frm);
        }, __('Actions'));
    } else {
        frm.add_custom_button(__('Unassign TukTuk'), function() {
            unassign_tuktuk(frm);
        }, __('Actions'));
        
        frm.add_custom_button(__('Check TukTuk Status'), function() {
            check_tuktuk_status(frm);
        }, __('Actions'));
    }
    
    // Reset target balance button (for managers)
    if (frappe.user.has_role(['System Manager', 'Tuktuk Manager'])) {
        frm.add_custom_button(__('Reset Target Balance'), function() {
            reset_target_balance(frm);
        }, __('Admin'));
        
        frm.add_custom_button(__('Reset Consecutive Misses'), function() {
            reset_consecutive_misses(frm);
        }, __('Admin'));
    }
}

function setup_indicators(frm) {
    // Clear existing indicators
    frm.dashboard.clear_indicators();
    
    // Add target status indicator
    const target = frm.doc.daily_target || 3000; // Default target
    const balance = frm.doc.current_balance || 0;
    const progress = Math.min((balance / target) * 100, 100);
    
    let color = 'red';
    let status = 'Behind Target';
    
    if (progress >= 100) {
        color = 'green';
        status = 'Target Met';
    } else if (progress >= 80) {
        color = 'orange';
        status = 'Near Target';
    }
    
    frm.dashboard.add_indicator(__('Target Progress: {0}% - {1}', [Math.round(progress), status]), color);
    
    // Add balance indicator
    const balanceColor = balance >= 0 ? 'green' : 'red';
    const balanceLabel = balance >= 0 ? 'Credit' : 'Debt';
    frm.dashboard.add_indicator(__('Balance: {0} KSH ({1})', [Math.abs(balance), balanceLabel]), balanceColor);
    
    // Add consecutive misses warning
    if (frm.doc.consecutive_misses > 0) {
        const missColor = frm.doc.consecutive_misses >= 2 ? 'red' : 'orange';
        const warningText = frm.doc.consecutive_misses >= 2 ? 'CRITICAL' : 'WARNING';
        frm.dashboard.add_indicator(__('Consecutive Misses: {0}/3 - {1}', [frm.doc.consecutive_misses, warningText]), missColor);
    }
    
    // Add assignment status
    if (frm.doc.assigned_tuktuk) {
        frm.dashboard.add_indicator(__('Assigned to TukTuk'), 'blue');
    } else {
        frm.dashboard.add_indicator(__('No TukTuk Assigned'), 'grey');
    }
}

function assign_tuktuk(frm) {
    frappe.prompt([
        {
            label: 'Available TukTuk',
            fieldname: 'tuktuk',
            fieldtype: 'Link',
            options: 'TukTuk Vehicle',
            reqd: 1,
            get_query: function() {
                return {
                    filters: {
                        'status': 'Available'
                    }
                };
            }
        }
    ], function(values) {
        frappe.call({
            method: 'frappe.client.set_value',
            args: {
                doctype: 'TukTuk Vehicle',
                name: values.tuktuk,
                fieldname: 'status',
                value: 'Assigned'
            },
            callback: function(r) {
                if (!r.exc) {
                    frm.set_value('assigned_tuktuk', values.tuktuk);
                    frm.save();
                    frappe.msgprint(__('TukTuk assigned successfully'));
                }
            }
        });
    }, __('Assign TukTuk'), __('Assign'));
}

function unassign_tuktuk(frm) {
    frappe.confirm(
        __('Are you sure you want to unassign this driver from their TukTuk?'),
        function() {
            const current_tuktuk = frm.doc.assigned_tuktuk;
            
            // Set tuktuk status back to available
            frappe.call({
                method: 'frappe.client.set_value',
                args: {
                    doctype: 'TukTuk Vehicle',
                    name: current_tuktuk,
                    fieldname: 'status',
                    value: 'Available'
                },
                callback: function(r) {
                    if (!r.exc) {
                        frm.set_value('assigned_tuktuk', '');
                        frm.save();
                        frappe.msgprint(__('TukTuk unassigned successfully'));
                    }
                }
            });
        }
    );
}

function check_tuktuk_status(frm) {
    if (frm.doc.assigned_tuktuk) {
        frappe.call({
            method: 'frappe.client.get',
            args: {
                doctype: 'TukTuk Vehicle',
                name: frm.doc.assigned_tuktuk
            },
            callback: function(r) {
                if (r.message) {
                    const tuktuk = r.message;
                    const message = `
                        <h4>TukTuk Status: ${tuktuk.tuktuk_id}</h4>
                        <p><strong>Status:</strong> ${tuktuk.status}</p>
                        <p><strong>Battery Level:</strong> ${tuktuk.battery_level}%</p>
                        <p><strong>Mpesa Account:</strong> ${tuktuk.mpesa_account}</p>
                        ${tuktuk.last_reported ? `<p><strong>Last Updated:</strong> ${tuktuk.last_reported}</p>` : ''}
                    `;
                    
                    frappe.msgprint({
                        title: __('TukTuk Status'),
                        message: message,
                        indicator: tuktuk.battery_level > 50 ? 'green' : 'orange'
                    });
                }
            }
        });
    }
}

function reset_target_balance(frm) {
    frappe.prompt([
        {
            label: 'New Balance',
            fieldname: 'balance',
            fieldtype: 'Currency',
            default: 0,
            reqd: 1
        },
        {
            label: 'Reason',
            fieldname: 'reason',
            fieldtype: 'Small Text',
            reqd: 1
        }
    ], function(values) {
        frm.set_value('current_balance', values.balance);
        frm.save();
        
        // Add comment for audit trail
        frappe.call({
            method: 'frappe.desk.form.utils.add_comment',
            args: {
                reference_doctype: frm.doctype,
                reference_name: frm.docname,
                content: `Target balance reset to ${values.balance} KSH. Reason: ${values.reason}`,
                comment_email: frappe.session.user,
                comment_by: frappe.session.user_fullname
            }
        });
        
        frappe.msgprint(__('Target balance reset successfully'));
    }, __('Reset Target Balance'), __('Reset'));
}

function reset_consecutive_misses(frm) {
    frappe.confirm(
        __('Are you sure you want to reset consecutive misses to 0?'),
        function() {
            frm.set_value('consecutive_misses', 0);
            frm.save();
            
            // Add comment for audit trail
            frappe.call({
                method: 'frappe.desk.form.utils.add_comment',
                args: {
                    reference_doctype: frm.doctype,
                    reference_name: frm.docname,
                    content: `Consecutive misses reset by ${frappe.session.user_fullname}`,
                    comment_email: frappe.session.user,
                    comment_by: frappe.session.user_fullname
                }
            });
            
            frappe.msgprint(__('Consecutive misses reset successfully'));
        }
    );
}