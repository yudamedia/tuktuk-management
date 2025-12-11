// ~/frappe-bench/apps/tuktuk_management/tuktuk_management/public/js/tuktuk_daily_report_list.js
frappe.listview_settings['TukTuk Daily Report'] = {
    onload: function(listview) {
        // Add breadcrumb
        frappe.breadcrumbs.add({
            type: 'Custom',
            label: 'Tuktuk Management',
            route: '/app/tuktuk-management'
        });
        
        // Add "Generate Daily Report" button
        listview.page.add_menu_item(__("Generate Daily Report"), function() {
            generate_daily_report_dialog(listview);
        });
    }
};

function generate_daily_report_dialog(listview) {
    let d = new frappe.ui.Dialog({
        title: __('Generate Daily Report'),
        fields: [
            {
                label: __('Report Date'),
                fieldname: 'report_date',
                fieldtype: 'Date',
                default: frappe.datetime.get_today(),
                reqd: 1
            },
            {
                label: __('Save to Database'),
                fieldname: 'save_to_db',
                fieldtype: 'Check',
                default: 1,
                description: __('Save the report data to the database for historical tracking')
            }
        ],
        primary_action_label: __('Generate Report'),
        primary_action(values) {
            generate_daily_report(values, listview, d);
        }
    });
    
    d.show();
}

function generate_daily_report(values, listview, dialog) {
    frappe.call({
        method: 'tuktuk_management.api.tuktuk.send_daily_report_email',
        args: {
            report_date: values.report_date,
            save_to_db: values.save_to_db ? 1 : 0
        },
        freeze: true,
        freeze_message: __('Generating daily report...'),
        callback: function(r) {
            if (r.message && r.message.success) {
                frappe.show_alert({
                    message: __('Daily report generated and sent successfully!'),
                    indicator: 'green'
                }, 5);
                
                // Refresh the listview to show the new report
                if (values.save_to_db) {
                    setTimeout(function() {
                        listview.refresh();
                    }, 1000);
                }
                
                dialog.hide();
            } else {
                frappe.show_alert({
                    message: __('Failed to generate report. Please check error logs.'),
                    indicator: 'red'
                }, 5);
            }
        },
        error: function(r) {
            frappe.show_alert({
                message: __('Error generating report: ') + (r.message || 'Unknown error'),
                indicator: 'red'
            }, 5);
        }
    });
}