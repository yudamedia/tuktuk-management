import frappe
from frappe import _

def get_context(context):
    """Driver Target Progress page context"""
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
        
        # Get target data
        from tuktuk_management.api.driver_auth import get_driver_target_data
        target_data = get_driver_target_data()
        
        from frappe.utils import format_date, today
        context.update({
            "show_sidebar": False,
            "no_breadcrumbs": True,
            "current_page": "target",
            "driver_name": driver.driver_name,
            "today_date": format_date(today(), "dd MMM yyyy"),
            "daily_target": target_data.get("daily_target", 0),
            "current_balance": target_data.get("current_balance", 0),
            "left_to_target": target_data.get("left_to_target", 0),
            "target_progress": target_data.get("target_progress", 0),
            "assigned_tuktuk": target_data.get("assigned_tuktuk")
        })
        
    except frappe.Redirect:
        raise
    except Exception as e:
        frappe.log_error(f"Driver target page error: {str(e)}")
        context.update({
            "error": str(e),
            "show_sidebar": False,
            "no_breadcrumbs": True,
            "current_page": "target"
        })
