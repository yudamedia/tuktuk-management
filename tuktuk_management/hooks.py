app_name = "tuktuk_management"
app_title = "Tuktuk Management"
app_publisher = "Yuda Media"
app_description = "Sunny Tuktuk Management System"
app_email = "yuda@graphicshop.co.ke"
app_license = "MIT"

app_include_css = [
    "/assets/tuktuk_management/css/tuktuk_management.css"
]

app_include_js = [
    "/assets/tuktuk_management/js/tuktuk_management.js",
    "/assets/tuktuk_management/js/tuktuk_tracker.js",
    "/assets/tuktuk_management/js/csv_telemetry_upload.js",
    "/assets/tuktuk_management/js/tuktuk_transaction_list.js",
    "/assets/tuktuk_management/js/tuktuk_driver_redirect.js"
]

app_icon = "octicon octicon-file-directory"
app_color = "blue"

# Whitelisted Methods - Critical for form operations
whitelisted_methods = [
    # From tuktuk.py
    "tuktuk_management.api.tuktuk.get_tuktuk_for_rental",
    "tuktuk_management.api.tuktuk.start_rental",
    "tuktuk_management.api.tuktuk.end_rental",
    "tuktuk_management.api.tuktuk.payment_validation", 
    "tuktuk_management.api.tuktuk.payment_confirmation",
    "tuktuk_management.api.tuktuk.transaction_validation",
    "tuktuk_management.api.tuktuk.transaction_confirmation",    
    "tuktuk_management.api.tuktuk.setup_daraja_integration",
    "tuktuk_management.api.tuktuk.test_payment_simulation",
    # "tuktuk_management.api.tuktuk.create_test_data",
    "tuktuk_management.api.tuktuk.fix_account_formats",
    "tuktuk_management.api.tuktuk.assign_driver_to_tuktuk",
    "tuktuk_management.api.tuktuk.assign_test_driver",
    "tuktuk_management.api.tuktuk.get_system_status",
    "tuktuk_management.api.tuktuk.check_daraja_connection",

    # B2C endpoints from sendpay.py
    "tuktuk_management.api.sendpay.b2c_result",
    "tuktuk_management.api.sendpay.b2c_timeout",
    "tuktuk_management.api.sendpay.setup_b2c_credentials",
    "tuktuk_management.api.sendpay.test_b2c_payment",
    "tuktuk_management.api.sendpay.get_b2c_requirements",

    # "tuktuk_management.api.tuktuk.create_simple_test_driver",
    # From telematics.py
    "tuktuk_management.api.telematics.telematics_webhook",
    "tuktuk_management.api.telematics.update_from_device",
    "tuktuk_management.api.telematics.update_location",
    "tuktuk_management.api.telematics.update_battery",
    "tuktuk_management.api.telematics.get_status",

    # Device mapping methods...
    "tuktuk_management.api.device_mapping.auto_map_devices_from_telemetry",
    "tuktuk_management.api.device_mapping.manual_device_mapping",
    "tuktuk_management.api.device_mapping.get_unmapped_devices",
    "tuktuk_management.api.device_mapping.validate_device_mappings",
    "tuktuk_management.api.device_mapping.reset_device_mapping",
    "tuktuk_management.api.device_mapping.apply_mapping_suggestions",    

    # CSV UPLOAD METHODS:
    "tuktuk_management.api.csv_telemetry.upload_telemetry_csv_data",
    "tuktuk_management.api.csv_telemetry.validate_csv_before_upload",
    "tuktuk_management.api.csv_telemetry.get_csv_upload_template",
    "tuktuk_management.api.csv_integration.batch_update_from_device_export",
    "tuktuk_management.api.csv_integration.process_uploaded_file",
    "tuktuk_management.api.csv_integration.get_upload_statistics",
    "tuktuk_management.api.csv_integration.create_sample_csv_data",

    # TukTuk Driver Authentication and Portal API endpoints (updated names)
    "tuktuk_management.api.driver_auth.create_tuktuk_driver_user_account",
    "tuktuk_management.api.driver_auth.create_all_tuktuk_driver_accounts", 
    "tuktuk_management.api.driver_auth.reset_tuktuk_driver_password",
    "tuktuk_management.api.driver_auth.get_tuktuk_driver_dashboard_data",
    "tuktuk_management.api.driver_auth.get_tuktuk_driver_transaction_history",
    "tuktuk_management.api.driver_auth.get_tuktuk_driver_rental_history",
    "tuktuk_management.api.driver_auth.request_tuktuk_rental",
    "tuktuk_management.api.driver_auth.start_tuktuk_rental",
    "tuktuk_management.api.driver_auth.update_tuktuk_driver_phone",
    "tuktuk_management.api.driver_auth.get_all_tuktuk_driver_accounts",
    "tuktuk_management.api.driver_auth.disable_tuktuk_driver_account",
    "tuktuk_management.api.driver_auth.enable_tuktuk_driver_account",

    # deposit management methods
    "tuktuk_management.tuktuk_management.doctype.tuktuk_driver.tuktuk_driver.process_deposit_top_up",
    "tuktuk_management.tuktuk_management.doctype.tuktuk_driver.tuktuk_driver.process_damage_deduction", 
    "tuktuk_management.tuktuk_management.doctype.tuktuk_driver.tuktuk_driver.process_target_miss_deduction",
    "tuktuk_management.tuktuk_management.doctype.tuktuk_driver.tuktuk_driver.process_driver_exit",
    "tuktuk_management.tuktuk_management.doctype.tuktuk_driver.tuktuk_driver.get_deposit_summary",
    "tuktuk_management.api.tuktuk.get_drivers_with_deposit_info",
    "tuktuk_management.api.tuktuk.bulk_process_target_deductions",
    "tuktuk_management.api.tuktuk.generate_deposit_report",
    "tuktuk_management.api.tuktuk.process_bulk_refunds",

    # Balance reconciliation methods
    "tuktuk_management.api.tuktuk.reconcile_driver_balance",
    "tuktuk_management.api.tuktuk.fix_driver_balance",
    "tuktuk_management.api.tuktuk.reconcile_all_drivers_balances",

    # User management methods
    "tuktuk_management.api.user_management.create_tuktuk_manager_user",
    "tuktuk_management.api.user_management.resend_welcome_email",
    "tuktuk_management.api.user_management.check_and_send_tuktuk_manager_welcome",
    "tuktuk_management.api.user_management.check_role_change_and_send_welcome",

    # SMS notification methods
    "tuktuk_management.api.sms_notifications.test_sms_to_driver",
    "tuktuk_management.api.sms_notifications.get_sms_status",
    "tuktuk_management.api.sms_notifications.get_all_drivers_for_broadcast",
    "tuktuk_management.api.sms_notifications.send_broadcast_sms",

    # From weekly_report.py
    "tuktuk_management.api.weekly_report.generate_weekly_report"
]

# Email templates
email_template_dirs = [
    "tuktuk_management/templates/emails"
]


# Document Events
doc_events = {
    # Removed after_insert hook for TukTuk Transaction to prevent double payments
    # All payment processing is handled by mpesa_confirmation webhook with proper idempotency checks
    "TukTuk Driver": {
        "validate": "tuktuk_management.api.tuktuk.validate_driver",
        "on_update": "tuktuk_management.api.tuktuk.handle_driver_update"
    },
    "TukTuk Vehicle": {
        "validate": "tuktuk_management.api.tuktuk.validate_vehicle",
        "on_update": "tuktuk_management.api.tuktuk.handle_vehicle_status_change"
    },
    "User": {
            "before_insert": "tuktuk_management.api.user_management.disable_default_welcome_for_tuktuk_managers",
            "after_insert": "tuktuk_management.api.user_management.check_and_send_tuktuk_manager_welcome",
            "on_update": "tuktuk_management.api.user_management.check_role_change_and_send_welcome",
            "before_save": "tuktuk_management.api.user_management.disable_default_welcome_for_tuktuk_managers"
    }
}
# Scheduled Tasks
scheduler_events = {
    "cron": {
        # Reset daily targets at midnight EAT 
        "0 0 * * *": [
            "tuktuk_management.api.tuktuk.reset_daily_targets_with_deposit",
            "tuktuk_management.api.tuktuk.end_operating_hours"
        ],
        # Check for operating hours at 6 AM EAT
        "0 3 * * *": [
            "tuktuk_management.api.tuktuk.start_operating_hours"
        ],
        # Update vehicle statuses every 5 minutes (now this method exists!)
        #"*/5 * * * *": [
        #    "tuktuk_management.api.telematics.update_all_vehicle_statuses"
        #],
        # SMS reminders at specific times (East Africa Time - UTC+3)
        "0 13 * * *": [  # 13 PM EAT (10 AM UTC)
            "tuktuk_management.api.sms_notifications.send_driver_target_reminder"
        ],
        "0 18 * * *": [  # 6 PM EAT (3 PM UTC)
            "tuktuk_management.api.sms_notifications.send_driver_target_reminder"
        ],
        "0 22 * * *": [  # 10 PM EAT (7 PM UTC)
            "tuktuk_management.api.sms_notifications.send_driver_target_reminder"
        ]
    },
    "hourly": [
        "tuktuk_management.api.tuktuk.check_battery_levels"
    ]
}

# Installation
after_install = "tuktuk_management.setup.install.after_install"

# Client Scripts
doctype_js = {
    "TukTuk Vehicle": "public/js/tuktuk_vehicle.js",
    "TukTuk Driver": "public/js/tuktuk_driver.js",
    "TukTuk Daily Report": "tuktuk_management/doctype/tuktuk_daily_report/tuktuk_daily_report.js"
}

doctype_list_js = {
    "TukTuk Vehicle": "public/js/tuktuk_vehicle_list.js",
    "TukTuk Driver": "public/js/tuktuk_driver_list.js",
    "TukTuk Transaction": "public/js/tuktuk_transaction_list.js",
    "TukTuk Rental": "public/js/tuktuk_rental_list.js",
    "TukTuk Daily Report": "public/js/tuktuk_daily_report_list.js"
}

# Boot session - ensures proper initialization
boot_session = "tuktuk_management.boot.boot_session"

translate_app = True

# Login hooks for automatic redirect
on_session_creation = "tuktuk_management.api.driver_auth.on_session_creation"

fixtures = [
    {
        "doctype": "Workspace",
        "filters": [
            [
                "name",
                "in",
                ["Tuktuk Management"]
            ]
        ]
    },
    {
        "doctype": "Dashboard Chart",
        "filters": [
            [
                "name",
                "in",
                ["Daily Revenue", "Target Achievement Rate"]
            ]
        ]
    }
]

reports = [
    {
        "doctype": "Report",
        "is_standard": "Yes", 
        "name": "Deposit Management Report",
        "report_name": "Deposit Management Report",
        "report_type": "Script Report",
        "ref_doctype": "TukTuk Driver"
    },
    {
        "doctype": "Report",
        "is_standard": "Yes",
        "name": "Driver Performance Report",
        "report_name": "Driver Performance Report",
        "report_type": "Script Report",
        "ref_doctype": "TukTuk Driver"
    }
]

# Website Routes - Add the new TukTuk driver dashboard route
website_route_rules = [
    {"from_route": "/tuktuk-driver-dashboard", "to_route": "tuktuk_driver_dashboard"},
    {"from_route": "/sms-broadcast", "to_route": "sms_broadcast"},
]

# Portal settings for TukTuk drivers
has_website_permission = {
    "TukTuk Driver": "tuktuk_management.api.driver_auth.has_website_permission"
}

# Website context for portal pages
website_context = {
    "favicon": "/assets/tuktuk_management/images/favicon.ico",
    "splash_image": "/assets/tuktuk_management/images/tuktuk-logo.png"
}