import frappe
from frappe import _

def get_context(context):
    """Driver Roster page context"""
    try:
        # Check if user is logged in and is a driver
        if frappe.session.user == "Guest":
            frappe.local.flags.redirect_location = "/login"
            raise frappe.Redirect
        
        user_roles = frappe.get_roles(frappe.session.user)
        if "TukTuk Driver" not in user_roles:
            frappe.throw(_("Access denied - TukTuk Driver role required"), frappe.PermissionError)
        
        # Get driver details
        tuktuk_driver = frappe.get_all("TukTuk Driver", 
                               filters={"user_account": frappe.session.user},
                               fields=["name", "driver_name"],
                               limit=1)
        
        if not tuktuk_driver:
            frappe.throw(_("TukTuk driver record not found"))
        
        driver = tuktuk_driver[0]
        
        # Get roster data
        from tuktuk_management.api.driver_auth import get_driver_roster_data
        roster_data = get_driver_roster_data()
        
        from frappe.utils import format_date, today
        context.update({
            "show_sidebar": False,
            "no_breadcrumbs": True,
            "current_page": "roster",
            "driver_name": driver.driver_name,
            "driver_id": driver.name,
            "today_date": format_date(today(), "dd MMM yyyy"),
            "has_active_roster": roster_data.get("has_active_roster", False),
            "roster_period": roster_data.get("roster_period"),
            "schedule": roster_data.get("schedule", []),
            "pending_requests": roster_data.get("pending_requests", [])
        })
        
    except frappe.Redirect:
        raise
    except Exception as e:
        frappe.log_error(f"Driver roster page error: {str(e)}")
        context.update({
            "error": str(e),
            "show_sidebar": False,
            "no_breadcrumbs": True,
            "current_page": "roster",
            "has_active_roster": False,
            "schedule": [],
            "pending_requests": []
        })
