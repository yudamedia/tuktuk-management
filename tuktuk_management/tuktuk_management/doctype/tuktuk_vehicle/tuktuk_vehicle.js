// Copyright (c) 2024, Yuda and Contributors
// MIT License. See license.txt

frappe.ui.form.on('TukTuk Vehicle', {
    refresh: function(frm) {
        // Add custom buttons based on vehicle status
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
        
        // Set status indicator colors
        set_status_indicator(frm);
        
        // Show substitute assignment info if applicable
        if (frm.doc.current_substitute_driver) {
            show_substitute_info(frm);
        }
    },
    
    status: function(frm) {
        // Handle status changes
        if (frm.doc.status === 'Subbed' && !frm.doc.current_substitute_driver) {
            frappe.msgprint(__('Please assign a substitute driver'));
            frm.set_value('status', frm.doc.__oldstatus || 'Available');
        }
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

function set_status_indicator(frm) {
    const status_colors = {
        'Available': 'green',
        'Assigned': 'blue',
        'Subbed': 'orange',
        'Charging': 'yellow',
        'Maintenance': 'red',
        'Offline': 'gray'
    };
    
    frm.set_df_property('status', 'options', 
        Object.keys(status_colors).map(status => 
            `<span class="indicator ${status_colors[status]}">${status}</span>`
        ).join('\n')
    );
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
