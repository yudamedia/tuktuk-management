// ~/frappe-bench/apps/tuktuk_management/tuktuk_management/public/js/tuktuk_driver_list.js

frappe.listview_settings['TukTuk Driver'] = {
    onload: function(listview) {
        // Hide the ID (name) column
        $(document).ready(function() {
            $('th:contains("ID"), td:contains("ID")').hide();  // Adjust this selector as needed
        });
        
        // Add breadcrumb
        frappe.breadcrumbs.add({
            type: 'Custom',
            label: 'Tuktuk Management',
            route: '/app/tuktuk-management'
        });
        
        // Add Reports menu to the list view
        listview.page.add_menu_item(__('Deposit Management Report'), function() {
            frappe.set_route('query-report', 'Deposit Management Report');
        });
        
        listview.page.add_menu_item(__('Driver Performance Report'), function() {
            frappe.set_route('query-report', 'Driver Performance Report');
        });
        
        // Add bulk actions for deposit management
        if (frappe.user.has_role(['System Manager', 'Tuktuk Manager'])) {
            listview.page.add_menu_item(__('Bulk Process Target Deductions'), function() {
                frappe.confirm(
                    __('Process target deductions from deposits for all eligible drivers?'),
                    function() {
                        frappe.call({
                            method: 'tuktuk_management.api.tuktuk.bulk_process_target_deductions',
                            callback: function(r) {
                                if (r.message && r.message.success) {
                                    frappe.msgprint({
                                        title: __('Bulk Processing Complete'),
                                        message: __('Processed {0} drivers with target deductions', [r.message.processed_count]),
                                        indicator: 'green'
                                    });
                                    listview.refresh();
                                }
                            }
                        });
                    }
                );
            });
            
            listview.page.add_menu_item(__('Process Bulk Refunds'), function() {
                frappe.confirm(
                    __('Process all pending deposit refunds?'),
                    function() {
                        frappe.call({
                            method: 'tuktuk_management.api.tuktuk.process_bulk_refunds',
                            callback: function(r) {
                                if (r.message && r.message.success) {
                                    frappe.msgprint({
                                        title: __('Bulk Refunds Complete'),
                                        message: __('Processed {0} refunds, {1} failed', [r.message.processed_count, r.message.failed_count]),
                                        indicator: r.message.failed_count > 0 ? 'orange' : 'green'
                                    });
                                    listview.refresh();
                                }
                            }
                        });
                    }
                );
            });
            
            // Add balance reconciliation check (Admin only)
            listview.page.add_menu_item(__('Reconciliation Check'), function() {
                frappe.call({
                    method: 'tuktuk_management.api.tuktuk.reconcile_all_drivers_balances',
                    callback: function(r) {
                        if (r.message) {
                            const result = r.message;
                            const has_issues = result.drivers_with_discrepancies > 0;
                            
                            // Show results dialog
                            let message = `
                                <div style="padding: 15px;">
                                    <h4>Reconciliation Results</h4>
                                    <table class="table table-bordered" style="margin-top: 10px;">
                                        <tr>
                                            <td><strong>Total Drivers:</strong></td>
                                            <td>${result.total_drivers}</td>
                                        </tr>
                                        <tr>
                                            <td><strong>Drivers Checked:</strong></td>
                                            <td>${result.drivers_checked}</td>
                                        </tr>
                                        <tr>
                                            <td><strong>Drivers with Discrepancies:</strong></td>
                                            <td style="color: ${has_issues ? 'red' : 'green'}">
                                                ${result.drivers_with_discrepancies}
                                            </td>
                                        </tr>
                                        <tr>
                                            <td><strong>Total Discrepancy Amount:</strong></td>
                                            <td>${result.total_discrepancy_amount} KSH</td>
                                        </tr>
                                    </table>
                            `;
                            
                            if (has_issues) {
                                message += `
                                    <div class="alert alert-warning" style="margin-top: 15px;">
                                        <strong>Drivers with issues:</strong>
                                        <ul style="margin-top: 10px;">
                                `;
                                result.results.forEach(driver => {
                                    if (driver.discrepancy !== 0) {
                                        message += `
                                            <li>
                                                ${driver.driver} (${driver.driver_name}): 
                                                <strong>${Math.abs(driver.discrepancy)} KSH</strong> 
                                                ${driver.discrepancy > 0 ? 'extra' : 'missing'}
                                            </li>
                                        `;
                                    }
                                });
                                message += `</ul></div>`;
                            }
                            
                            message += `</div>`;
                            
                            const d = new frappe.ui.Dialog({
                                title: __('Balance Reconciliation Check'),
                                fields: [
                                    {
                                        fieldtype: 'HTML',
                                        fieldname: 'results',
                                        options: message
                                    }
                                ],
                                primary_action_label: has_issues ? __('Auto-Fix All Discrepancies') : __('Close'),
                                primary_action: function() {
                                    if (has_issues) {
                                        frappe.confirm(
                                            __('Fix all {0} driver balances automatically?', [result.drivers_with_discrepancies]),
                                            function() {
                                                frappe.call({
                                                    method: 'tuktuk_management.api.tuktuk.reconcile_all_drivers_balances',
                                                    args: { auto_fix: true },
                                                    callback: function(fix_r) {
                                                        if (fix_r.message) {
                                                            frappe.msgprint({
                                                                title: __('Reconciliation Complete'),
                                                                message: __('Fixed {0} driver balances', [fix_r.message.drivers_with_discrepancies]),
                                                                indicator: 'green'
                                                            });
                                                            listview.refresh();
                                                            d.hide();
                                                        }
                                                    }
                                                });
                                            }
                                        );
                                    } else {
                                        d.hide();
                                    }
                                }
                            });
                            d.show();
                        }
                    }
                });
            });
            
            // Add bulk SMS with fields menu item
            listview.page.add_menu_item(__('Send Bulk SMS with Fields'), function() {
                show_bulk_sms_dialog(listview);
            });            
        }
    },
    
    // Enhanced list view settings
    add_fields: ["assigned_tuktuk", "current_balance", "consecutive_misses", "deposit_required", "current_deposit_balance"],
    
    get_indicator: function(doc) {
        // Priority indicators based on deposit and performance status
        if (doc.consecutive_misses >= 2) {
            return [__("Critical"), "red", "consecutive_misses,>=,2"];
        } else if (doc.deposit_required && doc.current_deposit_balance <= 0) {
            return [__("No Deposit"), "red", "current_deposit_balance,<=,0"];
        } else if (doc.deposit_required && doc.current_deposit_balance < 1000) {
            return [__("Low Deposit"), "orange", "current_deposit_balance,<,1000"];
        } else if (doc.assigned_tuktuk) {
            return [__("Assigned"), "green", "assigned_tuktuk,!=,"];
        } else {
            return [__("Unassigned"), "grey", "assigned_tuktuk,=,"];
        }
    },
    
    // Add custom columns to list view
    formatters: {
        current_deposit_balance: function(value, df, options, doc) {
            if (!doc.deposit_required) {
                return '<span class="text-muted">N/A</span>';
            }
            
            let color = 'green';
            if (value <= 0) {
                color = 'red';
            } else if (value < 1000) {
                color = 'orange';
            }
            
            return `<span style="color: ${color}">KSH ${frappe.format(value, {fieldtype: 'Currency'})}</span>`;
        },
        
        current_balance: function(value, df, options, doc) {
            let color = value >= 0 ? 'green' : 'red';
            let label = value >= 0 ? 'Credit' : 'Debt';
            
            return `<span style="color: ${color}" title="${label}">KSH ${frappe.format(Math.abs(value), {fieldtype: 'Currency'})}</span>`;
        },
        
        consecutive_misses: function(value, df, options, doc) {
            if (value === 0) {
                return '<span class="text-success">0</span>';
            } else if (value >= 2) {
                return `<span class="text-danger"><strong>${value}/3</strong></span>`;
            } else {
                return `<span class="text-warning">${value}/3</span>`;
            }
        }
    }
};

// Helper function to show bulk SMS dialog with field interpolation
function show_bulk_sms_dialog(listview) {
    // Get selected drivers - use get_checked_items() which returns array of names
    const selected_drivers = listview.get_checked_items() || [];
    
    frappe.call({
        method: 'frappe.client.get_list',
        args: {
            doctype: 'TukTuk Driver',
            fields: ['name', 'driver_name', 'sunny_id', 'mpesa_number', 'assigned_tuktuk', 'left_to_target', 'current_balance', 'current_deposit_balance'],
            order_by: 'driver_name asc',
            limit_page_length: 500
        },
        callback: function(r) {
            if (r.message) {
                const drivers = r.message;
                
                // Create dialog
                let d = new frappe.ui.Dialog({
                    title: __('Send SMS to Drivers with Field Interpolation'),
                    size: 'large',
                    fields: [
                        {
                            label: 'Select Recipients',
                            fieldname: 'recipient_type',
                            fieldtype: 'Select',
                            options: 'Selected Drivers\nAll Drivers\nAll Assigned Drivers\nAll Unassigned Drivers\nDrivers with Remaining Target\nSelect Specific Drivers',
                            default: selected_drivers.length > 0 ? 'Selected Drivers' : 'All Drivers',
                            reqd: 1,
                            onchange: function() {
                                const type = d.get_value('recipient_type');
                                d.get_field('selected_drivers').df.hidden = (type !== 'Select Specific Drivers');
                                d.get_field('selected_drivers').refresh();
                                update_recipient_count(d, drivers, selected_drivers);
                            }
                        },
                        {
                            label: 'Select Drivers',
                            fieldname: 'selected_drivers',
                            fieldtype: 'MultiSelectList',
                            hidden: 1,
                            options: drivers.map(d => ({
                                value: d.name,
                                label: `${d.driver_name} (${d.mpesa_number || 'No Phone'})`
                            })),
                            get_data: function() {
                                return drivers.map(d => ({
                                    value: d.name,
                                    label: `${d.driver_name} - ${d.assigned_tuktuk || 'Unassigned'} - Target Left: ${flt(d.left_to_target, 0)} KSH`,
                                    description: d.mpesa_number || 'No phone number'
                                }));
                            },
                            onchange: function() {
                                update_recipient_count(d, drivers, selected_drivers);
                            }
                        },
                        {
                            fieldtype: 'HTML',
                            fieldname: 'available_fields',
                            options: `
                                <div style="padding: 10px; background-color: #f8f9fa; border-radius: 5px; margin: 15px 0;">
                                    <strong>Available Fields:</strong>
                                    <p style="margin: 5px 0; font-size: 0.9em;">
                                        <code>{driver_name}</code>, 
                                        <code>{sunny_id}</code>,
                                        <code>{left_to_target}</code>, 
                                        <code>{current_balance}</code>, 
                                        <code>{daily_target}</code>, 
                                        <code>{assigned_tuktuk}</code>, 
                                        <code>{mpesa_number}</code>, 
                                        <code>{mpesa_paybill}</code>, 
                                        <code>{mpesa_account}</code>, 
                                        <code>{current_deposit_balance}</code>
                                    </p>
                                    <p style="margin: 5px 0; font-size: 0.85em; color: #666;">
                                        These placeholders will be replaced with each driver's actual values.
                                    </p>
                                </div>
                            `
                        },
                        {
                            label: 'Message Template',
                            fieldname: 'message',
                            fieldtype: 'Small Text',
                            reqd: 1,
                            description: 'Compose your SMS message. Use field placeholders like {driver_name} or {left_to_target}'
                        },
                        {
                            fieldtype: 'HTML',
                            fieldname: 'recipient_count',
                            options: '<div id="recipient-count" style="padding: 10px; background-color: #e9ecef; border-radius: 5px; margin-top: 10px;"></div>'
                        }
                    ],
                    primary_action_label: __('Send SMS'),
                    primary_action: function(values) {
                        if (!values.message || !values.message.trim()) {
                            frappe.msgprint(__('Please enter a message'));
                            return;
                        }
                        
                        // Determine driver IDs based on selection
                        let driver_ids = [];
                        const type = values.recipient_type;
                        
                        if (type === 'Selected Drivers') {
                            // selected_drivers is already an array of driver names (strings)
                            driver_ids = selected_drivers;
                        } else if (type === 'All Drivers') {
                            driver_ids = drivers.map(d => d.name);
                        } else if (type === 'All Assigned Drivers') {
                            driver_ids = drivers.filter(d => d.assigned_tuktuk).map(d => d.name);
                        } else if (type === 'All Unassigned Drivers') {
                            driver_ids = drivers.filter(d => !d.assigned_tuktuk).map(d => d.name);
                        } else if (type === 'Drivers with Remaining Target') {
                            driver_ids = drivers.filter(d => flt(d.left_to_target) > 0).map(d => d.name);
                        } else if (type === 'Select Specific Drivers') {
                            driver_ids = values.selected_drivers || [];
                        }
                        
                        if (driver_ids.length === 0) {
                            frappe.msgprint(__('No drivers selected'));
                            return;
                        }
                        
                        frappe.confirm(
                            __('Send SMS to {0} driver(s)?', [driver_ids.length]),
                            function() {
                                frappe.call({
                                    method: 'tuktuk_management.api.sms_notifications.send_bulk_sms_with_fields',
                                    args: {
                                        driver_ids: driver_ids,
                                        message_template: values.message
                                    },
                                    freeze: true,
                                    freeze_message: __('Sending SMS...'),
                                    callback: function(r) {
                                        if (r.message && r.message.success) {
                                            frappe.msgprint({
                                                title: __('SMS Sent'),
                                                message: __('Successfully sent: {0}<br>Failed: {1}', 
                                                    [r.message.success_count, r.message.failure_count]),
                                                indicator: r.message.failure_count > 0 ? 'orange' : 'green'
                                            });
                                            d.hide();
                                            listview.refresh();
                                        } else {
                                            frappe.msgprint({
                                                title: __('SMS Failed'),
                                                message: r.message ? r.message.message : __('Failed to send SMS'),
                                                indicator: 'red'
                                            });
                                        }
                                    }
                                });
                            }
                        );
                    }
                });
                
                // Update recipient count when selection changes
                d.fields_dict.recipient_type.$input.on('change', function() {
                    update_recipient_count(d, drivers, selected_drivers);
                });
                
                // Also update when MultiSelectList changes
                d.on('selected_drivers', function() {
                    update_recipient_count(d, drivers, selected_drivers);
                });
                
                d.show();
                update_recipient_count(d, drivers, selected_drivers);
            }
        }
    });
}

function update_recipient_count(dialog, drivers, selected_drivers) {
    const type = dialog.get_value('recipient_type');
    let count = 0;
    
    if (type === 'Selected Drivers') {
        count = selected_drivers.length;
    } else if (type === 'All Drivers') {
        count = drivers.length;
    } else if (type === 'All Assigned Drivers') {
        count = drivers.filter(d => d.assigned_tuktuk).length;
    } else if (type === 'All Unassigned Drivers') {
        count = drivers.filter(d => !d.assigned_tuktuk).length;
    } else if (type === 'Drivers with Remaining Target') {
        count = drivers.filter(d => flt(d.left_to_target) > 0).length;
    } else if (type === 'Select Specific Drivers') {
        const selected = dialog.get_value('selected_drivers') || [];
        count = selected.length;
    }
    
    $('#recipient-count').html(`<strong>Recipients:</strong> ${count} driver(s) will receive this SMS`);
}