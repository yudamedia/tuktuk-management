// ~/frappe-bench/apps/tuktuk_management/tuktuk_management/public/js/tuktuk_driver_list.js
frappe.listview_settings['TukTuk Driver'] = {
    onload: function(listview) {
        // Add breadcrumb
        frappe.breadcrumbs.add({
            type: 'Custom',
            label: 'Tuktuk Management',
            route: '/app/tuktuk-management'
        });
    }
};