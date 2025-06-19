// ~/frappe-bench/apps/tuktuk_management/tuktuk_management/tuktuk_management/report/deposit_management_report/deposit_management_report.js

frappe.query_reports["Deposit Management Report"] = {
    "filters": [
        {
            "fieldname": "driver",
            "label": __("Driver"),
            "fieldtype": "Link",
            "options": "TukTuk Driver"
        },
        {
            "fieldname": "deposit_status",
            "label": __("Deposit Status"),
            "fieldtype": "Select",
            "options": "\nRequired\nNot Required"
        },
        {
            "fieldname": "exit_status", 
            "label": __("Driver Status"),
            "fieldtype": "Select",
            "options": "\nActive\nExited"
        },
        {
            "fieldname": "refund_status",
            "label": __("Refund Status"),
            "fieldtype": "Select", 
            "options": "\nPending\nProcessed\nCompleted\nCancelled"
        },
        {
            "fieldname": "allows_target_deduction",
            "label": __("Allows Target Deduction"),
            "fieldtype": "Select",
            "options": "\nYes\nNo"
        }
    ],
    
    "onload": function(report) {
        // Add custom buttons
        report.page.add_inner_button(__("Bulk Process Target Deductions"), function() {
            frappe.call({
                method: "tuktuk_management.api.tuktuk.bulk_process_target_deductions",
                callback: function(r) {
                    if (r.message && r.message.success) {
                        frappe.msgprint({
                            title: __("Bulk Processing Complete"),
                            message: __("Processed {0} drivers with target deductions", [r.message.processed_count]),
                            indicator: "green"
                        });
                        report.refresh();
                    }
                }
            });
        });
        
        report.page.add_inner_button(__("Process Bulk Refunds"), function() {
            frappe.confirm(
                __("Are you sure you want to process all pending refunds?"),
                function() {
                    frappe.call({
                        method: "tuktuk_management.api.tuktuk.process_bulk_refunds",
                        callback: function(r) {
                            if (r.message && r.message.success) {
                                frappe.msgprint({
                                    title: __("Bulk Refunds Complete"),
                                    message: __("Processed {0} refunds, {1} failed", [r.message.processed_count, r.message.failed_count]),
                                    indicator: r.message.failed_count > 0 ? "orange" : "green"
                                });
                                report.refresh();
                            }
                        }
                    });
                }
            );
        });
    }
};