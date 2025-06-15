# ~/frappe-bench/apps/tuktuk_management/tuktuk_management/hooks.py
app_name = "tuktuk_management"
app_title = "Tuktuk Management"
app_publisher = "Yuda Media"
app_description = "Sunny Tuktuk Management System"
app_email = "yuda@graphicshop.co.ke"
app_license = "MIT"

app_include_css = [
    "/assets/tuktuk_management/css/tuktuk_management.css",
    # "https://unpkg.com/leaflet@1.7.1/dist/leaflet.css",
    # "https://cdn.jsdelivr.net/npm/leaflet.locatecontrol@0.74.4/dist/L.Control.Locate.min.css"
]

app_include_js = [
    # "https://unpkg.com/leaflet@1.7.1/dist/leaflet.js",
    # "https://cdn.jsdelivr.net/npm/leaflet.locatecontrol@0.74.4/dist/L.Control.Locate.min.js",
    "/assets/tuktuk_management/js/tuktuk_management.js",
    "/assets/tuktuk_management/js/tuktuk_tracker.js"
]

app_icon = "octicon octicon-file-directory"
app_color = "blue"

# Whitelisted Methods - Critical for form operations
whitelisted_methods = [
    "tuktuk_management.api.tuktuk.get_tuktuk_for_rental",
    "tuktuk_management.api.tuktuk.start_rental",
    "tuktuk_management.api.tuktuk.send_mpesa_payment",
    "tuktuk_management.api.telematics.update_vehicle_status",
    "tuktuk_management.api.telematics.update_from_device",
    "tuktuk_management.api.telematics.update_location",
    "tuktuk_management.api.telematics.update_battery",
    "tuktuk_management.api.telematics.get_status"
]

# Override whitelisted methods to ensure core Frappe functions work
# override_whitelisted_methods = {
#     "frappe.desk.form.save.savedocs": "frappe.desk.form.save.savedocs",
#     "frappe.desk.form.load.getdoctype": "frappe.desk.form.load.getdoctype",
#     "frappe.desk.form.load.getdoc": "frappe.desk.form.load.getdoc",
#     "frappe.desk.form.utils.validate_link": "frappe.desk.form.utils.validate_link",
#     "frappe.desk.search.search_link": "frappe.desk.search.search_link",
#     "frappe.desk.reportview.get": "frappe.desk.reportview.get",
#     "frappe.client.get": "frappe.client.get",
#     "frappe.client.get_list": "frappe.client.get_list",
#     "frappe.client.save": "frappe.client.save",
#     "frappe.client.submit": "frappe.client.submit",
#     "frappe.client.cancel": "frappe.client.cancel",
#     "frappe.client.delete": "frappe.client.delete"
# }

# Document Events
doc_events = {
    "TukTuk Transaction": {
        "after_insert": "tuktuk_management.api.tuktuk.handle_mpesa_payment"
    },
    "TukTuk Driver": {
        "validate": "tuktuk_management.api.tuktuk.validate_driver",
        "on_update": "tuktuk_management.api.tuktuk.handle_driver_update"
    },
    "TukTuk Vehicle": {
        "validate": "tuktuk_management.api.tuktuk.validate_vehicle",
        "on_update": "tuktuk_management.api.tuktuk.handle_vehicle_status_change"
    }
}

# Scheduled Tasks
scheduler_events = {
    "cron": {
        # Reset daily targets at midnight
        "0 0 * * *": [
            "tuktuk_management.api.tuktuk.reset_daily_targets",
            "tuktuk_management.api.tuktuk.end_operating_hours"
        ],
        # Check for operating hours at 6 AM
        "0 6 * * *": [
            "tuktuk_management.api.tuktuk.start_operating_hours"
        ],
        # Update vehicle statuses every 5 minutes
        "*/5 * * * *": [
            "tuktuk_management.api.telematics.update_all_vehicle_statuses"
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
    "TukTuk Driver": "public/js/tuktuk_driver.js"
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
        "name": "Driver Performance Report",
        "report_name": "Driver Performance Report",
        "report_type": "Script Report",
        "ref_doctype": "TukTuk Driver"
    }
]

# Standard includes for web forms and pages
standard_portal_menu_items = [
    {"title": "Driver Dashboard", "route": "/driver-dashboard", "reference_doctype": "TukTuk Driver"}
]

# Website context for portal pages
website_context = {
    "favicon": "/assets/tuktuk_management/images/favicon.ico",
    "splash_image": "/assets/tuktuk_management/images/tuktuk-logo.png"
}