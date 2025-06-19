// ~/frappe-bench/apps/tuktuk_management/tuktuk_management/public/js/tuktuk_driver_list.js

frappe.listview_settings['TukTuk Driver'] = {
    onload: function(listview) {
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