// ~/frappe-bench/apps/tuktuk_management/tuktuk_management/public/js/tuktuk_transaction_list.js
frappe.listview_settings['TukTuk Transaction'] = {
    onload: function(listview) {
        // Add breadcrumb
        frappe.breadcrumbs.add({
            type: 'Custom',
            label: 'Tuktuk Management',
            route: '/app/tuktuk-management'
        });
    }
};

// Custom list view configuration for TukTuk Transaction

frappe.listview_settings['TukTuk Transaction'] = {
    // Define which fields to show in list view
    add_fields: ["transaction_id", "amount", "driver", "timestamp", "payment_status"],
    
    // Customize the display format
    get_indicator: function(doc) {
        if (doc.payment_status === "Completed") {
            return [__("Completed"), "green", "payment_status,=,Completed"];
        } else if (doc.payment_status === "Pending") {
            return [__("Pending"), "orange", "payment_status,=,Pending"];
        } else if (doc.payment_status === "Failed") {
            return [__("Failed"), "red", "payment_status,=,Failed"];
        }
    },
    
    // Format how each row is displayed
    formatters: {
        amount: function(value) {
            return `<strong>KSH ${frappe.format(value, {fieldtype: 'Currency'})}</strong>`;
        },
        transaction_id: function(value) {
            return `<code style="background: #f8f9fa; padding: 2px 4px; border-radius: 3px; font-size: 11px;">${value}</code>`;
        },
        timestamp: function(value) {
            return frappe.datetime.str_to_user(value);
        }
    },
    
    // Custom columns for list view
    onload: function(listview) {
        // Customize the primary display columns
        listview.page.set_primary_action(__("New Transaction"), function() {
            frappe.new_doc("TukTuk Transaction");
        });
        
        // Add refresh button
        listview.page.add_menu_item(__("Refresh"), function() {
            listview.refresh();
        });
    }
};
