// Copyright (c) 2024, Yuda Media and contributors
// For license information, please see license.txt

// In tuktuk_settings.js
frappe.ui.form.on("TukTuk Settings", {
    refresh: function(frm) {
        frm.add_custom_button(__('Setup Daraja Integration'), function() {
            setup_daraja_integration();
        });
    }
});

function setup_daraja_integration() {
    frappe.call({
        method: 'tuktuk_management.api.tuktuk.setup_daraja_integration',
        callback: function(r) {
            if (r.message) {
                frappe.msgprint('Daraja integration setup completed');
            }
        }
    });
}