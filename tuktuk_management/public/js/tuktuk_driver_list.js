// tuktuk_management/public/js/tuktuk_driver_list.js

// Helper function to show driver accounts dialog
function show_driver_accounts_dialog(accounts) {
    let html = `
        <div style="max-height: 400px; overflow-y: auto;">
            <table class="table table-bordered table-striped">
                <thead>
                    <tr>
                        <th>Driver Name</th>
                        <th>Email/Account</th>
                        <th>Phone</th>
                        <th>TukTuk</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
    `;
    
    accounts.forEach(driver => {
        const hasAccount = driver.user_account ? '✓' : '—';
        const statusColor = driver.user_account ? 'success' : 'muted';
        html += `
            <tr>
                <td>${driver.driver_name}</td>
                <td>${driver.user_account || '<span class="text-muted">Not created</span>'}</td>
                <td>${driver.mpesa_number || ''}</td>
                <td>${driver.assigned_tuktuk || '<span class="text-muted">Unassigned</span>'}</td>
                <td><span class="text-${statusColor}">${hasAccount}</span></td>
            </tr>
        `;
    });
    
    html += `
                </tbody>
            </table>
        </div>
    `;
    
    let d = new frappe.ui.Dialog({
        title: __('Driver Accounts Overview'),
        fields: [
            {
                fieldtype: 'HTML',
                options: html
            }
        ],
        primary_action_label: __('Close')
    });
    
    d.show();
}

// Helper function to show bulk SMS dialog with field interpolation
// MOVED TO TOP - BEFORE frappe.listview_settings
function show_bulk_sms_dialog(listview) {
    // Get selected drivers - use get_checked_items() which returns array of names
    const selected_drivers = listview.get_checked_items() || [];
    
    frappe.call({
        method: 'frappe.client.get_list',
        args: {
            doctype: 'TukTuk Driver',
            fields: ['name', 'driver_name', 'sunny_id', 'mpesa_number', 'assigned_tuktuk', 'left_to_target', 'current_balance', 'current_deposit_balance', 'daily_target'],
            order_by: 'driver_name asc',
            limit_page_length: 500
        },
        callback: function(r) {
            if (r.message) {
                const drivers = r.message;
                
                // Get TukTuk Settings for mpesa paybill
                frappe.call({
                    method: 'frappe.client.get',
                    args: {
                        doctype: 'TukTuk Settings',
                        name: 'TukTuk Settings'
                    },
                    callback: function(settings_r) {
                        const settings = settings_r.message || {};
                        const mpesa_paybill = settings.mpesa_paybill_number || '';
                        
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
                                    onchange: function() {
                                        const type = d.get_value('recipient_type');
                                        d.fields_dict.selected_drivers.df.hidden = (type !== 'Select Specific Drivers');
                                        d.fields_dict.selected_drivers.refresh();
                                        update_recipient_count(d, drivers, selected_drivers);
                                    }
                                },
                                {
                                    label: 'Select Drivers',
                                    fieldname: 'selected_drivers',
                                    fieldtype: 'MultiSelectList',
                                    get_data: function(txt) {
                                        return drivers.map(d => ({
                                            value: d.name,
                                            description: `${d.driver_name} - ${d.assigned_tuktuk || 'Unassigned'} - Target Left: KSH ${flt(d.left_to_target, 0).toLocaleString()}`
                                        }));
                                    },
                                    hidden: 1,
                                    onchange: function() {
                                        update_recipient_count(d, drivers, selected_drivers);
                                    }
                                },
                                {
                                    fieldtype: 'HTML',
                                    fieldname: 'available_fields',
                                    options: `
                                        <div style="padding: 10px; background-color: #f8f9fa; border: 1px solid #dee2e6; border-radius: 5px; margin-bottom: 10px;">
                                            <h5 style="margin: 0 0 10px 0; color: #495057;">📋 Available Fields for Personalization:</h5>
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
                        
                        d.show();
                        update_recipient_count(d, drivers, selected_drivers);
                    }
                });
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

// Main list view settings
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
        
        // Permission check for admin functions
        if (frappe.user.has_role(['System Manager', 'Tuktuk Manager'])) {
            
            // Add bulk actions for deposit management
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
            
            // Add "Reconciliation Check" button
            listview.page.add_menu_item(__('Reconciliation Check'), function() {
                frappe.call({
                    method: 'tuktuk_management.api.tuktuk.reconcile_all_drivers_balances',
                    args: { auto_fix: false },
                    freeze: true,
                    freeze_message: __('Checking balances...'),
                    callback: function(r) {
                        if (r.message) {
                            const result = r.message;
                            const has_issues = result.drivers_with_discrepancies > 0;
                            
                            let html = `
                                <div style="padding: 10px;">
                                    <p><strong>Total Drivers Checked:</strong> ${result.total_drivers}</p>
                                    <p><strong>Drivers with Discrepancies:</strong> 
                                        <span style="color: ${has_issues ? 'red' : 'green'}; font-weight: bold;">
                                            ${result.drivers_with_discrepancies}
                                        </span>
                                    </p>
                                    <p><strong>Total Discrepancy:</strong> KSH ${flt(result.total_discrepancy, 2).toLocaleString()}</p>
                            `;
                            
                            if (has_issues && result.details && result.details.length > 0) {
                                html += `
                                    <hr style="margin: 15px 0;">
                                    <h5>Affected Drivers:</h5>
                                    <table class="table table-bordered table-sm" style="font-size: 0.9em;">
                                        <thead>
                                            <tr>
                                                <th>Driver</th>
                                                <th>Current Balance</th>
                                                <th>Should Be</th>
                                                <th>Discrepancy</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                `;
                                
                                result.details.forEach(d => {
                                    const discrepancy_color = Math.abs(d.discrepancy) > 0.01 ? 'red' : 'green';
                                    html += `
                                        <tr>
                                            <td>${d.driver_name}</td>
                                            <td>KSH ${flt(d.current_balance, 2).toLocaleString()}</td>
                                            <td>KSH ${flt(d.calculated_balance, 2).toLocaleString()}</td>
                                            <td style="color: ${discrepancy_color}; font-weight: bold;">
                                                KSH ${flt(d.discrepancy, 2).toLocaleString()}
                                            </td>
                                        </tr>
                                    `;
                                });
                                
                                html += `
                                        </tbody>
                                    </table>
                                `;
                            }
                            
                            html += `</div>`;
                            
                            let d = new frappe.ui.Dialog({
                                title: __('Balance Reconciliation Report'),
                                fields: [
                                    {
                                        fieldtype: 'HTML',
                                        options: html
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

            // Add "Reconcile Target Left" button (checks left_to_target calculation)
            listview.page.add_menu_item(__('Reconcile Target Left'), function() {
                frappe.call({
                    method: 'tuktuk_management.api.balance_reconciliation.check_balance_discrepancies',
                    args: { auto_fix: false },
                    freeze: true,
                    freeze_message: __('Checking target calculations...'),
                    callback: function(r) {
                        if (r.message) {
                            const result = r.message;
                            const has_issues = result.discrepancies_found > 0;

                            let html = `
                                <div style="padding: 10px;">
                                    <p><strong>Total Drivers Checked:</strong> ${result.total_drivers_checked}</p>
                                    <p><strong>Discrepancies Found:</strong>
                                        <span style="color: ${has_issues ? 'red' : 'green'}; font-weight: bold;">
                                            ${result.discrepancies_found}
                                        </span>
                                    </p>
                                    <p><strong>Total Error Amount:</strong> KSH ${flt(result.total_error_amount, 2).toLocaleString()}</p>
                                    <p style="font-size: 0.9em; color: #666; margin-top: 10px;">
                                        <em>This check validates that left_to_target = max(0, target - current_balance)</em>
                                    </p>
                            `;

                            if (has_issues && result.details && result.details.length > 0) {
                                html += `
                                    <hr style="margin: 15px 0;">
                                    <h5>Affected Drivers:</h5>
                                    <table class="table table-bordered table-sm" style="font-size: 0.9em;">
                                        <thead>
                                            <tr>
                                                <th>Driver</th>
                                                <th>Balance</th>
                                                <th>Expected Left</th>
                                                <th>Actual Left</th>
                                                <th>Error</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                `;

                                result.details.forEach(d => {
                                    const error_color = Math.abs(d.error) > 0.01 ? 'red' : 'green';
                                    html += `
                                        <tr>
                                            <td>${d.driver_name}</td>
                                            <td>KSH ${flt(d.current_balance, 2).toLocaleString()}</td>
                                            <td>KSH ${flt(d.expected_left_to_target, 2).toLocaleString()}</td>
                                            <td>KSH ${flt(d.actual_left_to_target, 2).toLocaleString()}</td>
                                            <td style="color: ${error_color}; font-weight: bold;">
                                                KSH ${flt(d.error, 2).toLocaleString()}
                                            </td>
                                        </tr>
                                    `;
                                });

                                html += `
                                        </tbody>
                                    </table>
                                `;
                            }

                            html += `</div>`;

                            let d = new frappe.ui.Dialog({
                                title: __('Target Left Reconciliation Report'),
                                fields: [
                                    {
                                        fieldtype: 'HTML',
                                        options: html
                                    }
                                ],
                                primary_action_label: has_issues ? __('Auto-Fix All Errors') : __('Close'),
                                primary_action: function() {
                                    if (has_issues) {
                                        frappe.confirm(
                                            __('Fix left_to_target for all {0} driver(s) automatically?', [result.discrepancies_found]),
                                            function() {
                                                frappe.call({
                                                    method: 'tuktuk_management.api.balance_reconciliation.fix_all_discrepancies',
                                                    freeze: true,
                                                    freeze_message: __('Fixing discrepancies...'),
                                                    callback: function(fix_r) {
                                                        if (fix_r.message) {
                                                            frappe.msgprint({
                                                                title: __('Target Left Reconciliation Complete'),
                                                                message: __('Fixed {0} driver(s)', [fix_r.message.discrepancies_fixed]),
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

            // Add bulk account creation menu items
            listview.page.add_menu_item(__('Create All Driver Accounts'), function() {
                frappe.confirm(
                    __('Create user accounts for all drivers who don\'t have one? This will generate login credentials for each driver.'),
                    function() {
                        frappe.call({
                            method: 'tuktuk_management.api.driver_auth.create_all_driver_accounts',
                            callback: function(r) {
                                if (r.message) {
                                    const result = r.message;
                                    let message = `✅ Created ${result.created.length} accounts`;
                                    if (result.failed.length > 0) {
                                        message += `\n❌ ${result.failed.length} failed`;
                                    }
                                    
                                    frappe.msgprint({
                                        title: __('Bulk Account Creation Complete'),
                                        message: message,
                                        indicator: result.failed.length > 0 ? 'orange' : 'green'
                                    });
                                    
                                    listview.refresh();
                                }
                            }
                        });
                    }
                );
            });
            
            listview.page.add_menu_item(__('View All Driver Accounts'), function() {
                frappe.call({
                    method: 'tuktuk_management.api.driver_auth.get_all_driver_accounts',
                    callback: function(r) {
                        if (r.message) {
                            show_driver_accounts_dialog(r.message);
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
    add_fields: ["assigned_tuktuk", "current_balance", "consecutive_misses", "deposit_required", "current_deposit_balance", "hailing_status"],
    
    get_indicator: function(doc) {
        // Simple indicator based on tuktuk assignment status
        if (doc.assigned_tuktuk) {
            return [__("Assigned"), "green", "assigned_tuktuk,!=,''"];
        } else {
            return [__("Unassigned"), "gray", "assigned_tuktuk,=,''"];
        }
    },
    
    formatters: {
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
        },
        
        hailing_status: function(value, df, options, doc) {
            const status = value || 'Offline';
            let badgeClass = 'badge-secondary';
            
            if (status === 'Available') {
                badgeClass = 'badge-success';
            } else if (status === 'En Route') {
                badgeClass = 'badge-warning';
            } else if (status === 'Busy') {
                badgeClass = 'badge-danger';
            }
            
            return `<span class="badge ${badgeClass}">${status}</span>`;
        }
    }
};