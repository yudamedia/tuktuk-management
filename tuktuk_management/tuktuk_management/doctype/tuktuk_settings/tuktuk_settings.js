// Copyright (c) 2024, Yuda Media and contributors
// For license information, please see license.txt

// In tuktuk_settings.js
frappe.ui.form.on("TukTuk Settings", {
    refresh: function(frm) {
        // Only show Setup Daraja Integration button to System Managers
        if (frappe.user.has_role('System Manager')) {
            frm.add_custom_button(__('Setup Daraja Integration'), function() {
                setup_daraja_integration();
            });
        }
        
        // Set field permissions for Tuktuk Executive role (has more permissions than Manager)
        if (frappe.user.has_role('Tuktuk Executive') && !frappe.user.has_role('System Manager')) {
            set_tuktuk_executive_permissions(frm);
        }
        // Set field permissions for Tuktuk Manager role (but NOT if also Tuktuk Executive)
        else if (frappe.user.has_role('Tuktuk Manager') && 
                 !frappe.user.has_role('System Manager') && 
                 !frappe.user.has_role('Tuktuk Executive')) {
            set_tuktuk_manager_permissions(frm);
        }
    }
});

function set_tuktuk_manager_permissions(frm) {
    // Fields that Tuktuk Manager can edit (Operating Hours, Global Targets, Bonuses)
    const editable_fields = [
        'operating_hours_start',
        'operating_hours_end',
        'global_daily_target', 
        'global_fare_percentage',
        'bonus_enabled',
        'bonus_amount'
    ];
    
    // Fields that should be read-only for Tuktuk Manager (Rental Rates, Mpesa, Notifications, Telematics)
    const readonly_fields = [
        'global_rental_initial',
        'global_rental_hourly',
        'mpesa_paybill',
        'mpesa_api_key',
        'mpesa_api_secret',
        'enable_sms_notifications',
        'enable_email_notifications',
        'telematics_api_url',
        'telematics_api_key',
        'telematics_api_secret',
        'update_interval'
    ];
    
    // Make specified fields read-only
    readonly_fields.forEach(function(fieldname) {
        frm.set_df_property(fieldname, 'read_only', 1);
    });
    
    // Ensure editable fields are not read-only (in case they were set elsewhere)
    editable_fields.forEach(function(fieldname) {
        frm.set_df_property(fieldname, 'read_only', 0);
    });
}

function set_tuktuk_executive_permissions(frm) {
    // Fields that Tuktuk Executive can edit (includes rental rates)
    const editable_fields = [
        'operating_hours_start',
        'operating_hours_end',
        'global_daily_target', 
        'global_fare_percentage',
        'bonus_enabled',
        'bonus_amount',
        'global_rental_initial',
        'global_rental_hourly',
        'enable_target_sharing',
        'instant_payouts_enabled'
    ];
    
    // Fields that should be read-only for Tuktuk Executive (Mpesa, Notifications, Telematics)
    const readonly_fields = [
        'mpesa_paybill',
        'mpesa_api_key',
        'mpesa_api_secret',
        'b2c_enabled',
        'mpesa_initiator_name',
        'mpesa_security_credential',
        'mpesa_initiator_password',
        'enable_sms_notifications',
        'enable_email_notifications',
        'telematics_api_url',
        'telematics_api_key',
        'telematics_api_secret',
        'update_interval'
    ];
    
    // Ensure editable fields are not read-only
    editable_fields.forEach(function(fieldname) {
        frm.set_df_property(fieldname, 'read_only', 0);
    });
    
    // Make specified fields read-only
    readonly_fields.forEach(function(fieldname) {
        frm.set_df_property(fieldname, 'read_only', 1);
    });
}

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