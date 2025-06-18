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

frappe.listview_settings['TukTuk Driver'] = {
    add_fields: ["assigned_tuktuk", "current_balance", "consecutive_misses"],
    get_indicator: function(doc) {
        if (doc.consecutive_misses >= 2) {
            return [__("Critical"), "red", "consecutive_misses,>=,2"];
        } else if (doc.assigned_tuktuk) {
            return [__("Assigned"), "green", "assigned_tuktuk,!=,"];
        } else {
            return [__("Unassigned"), "grey", "assigned_tuktuk,=,"];
        }
    }
};