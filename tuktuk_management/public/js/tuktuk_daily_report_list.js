// ~/frappe-bench/apps/tuktuk_management/tuktuk_management/public/js/tuktuk_daily_report_list.js
frappe.listview_settings['TukTuk Daily Report'] = {
    onload: function(listview) {
        // Add breadcrumb
        frappe.breadcrumbs.add({
            type: 'Custom',
            label: 'Tuktuk Management',
            route: '/app/tuktuk-management'
        });
    }
};