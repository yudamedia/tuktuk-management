// ~/frappe-bench/apps/tuktuk_management/tuktuk_management/public/js/tuktuk_vehicle_list.js
frappe.listview_settings['TukTuk Vehicle'] = {
    onload: function(listview) {
        // Add breadcrumb
        frappe.breadcrumbs.add({
            type: 'Custom',
            label: 'Tuktuk Management',
            route: '/app/tuktuk-management'
        });
    }
};