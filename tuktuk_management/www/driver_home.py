import frappe
from frappe import _

def get_context(context):
    """Driver Home page context"""
    try:
        # Check if user is logged in and is a driver
        if frappe.session.user == "Guest":
            frappe.local.flags.redirect_location = "/login"
            raise frappe.Redirect
        
        user_roles = frappe.get_roles(frappe.session.user)
        if "TukTuk Driver" not in user_roles:
            frappe.throw(_("Access denied - TukTuk Driver role required"), frappe.PermissionError)
        
        # Get driver dashboard data
        from tuktuk_management.api.driver_auth import get_tuktuk_driver_dashboard_data
        dashboard_data = get_tuktuk_driver_dashboard_data()
        
        # Get driver details
        tuktuk_driver = frappe.get_all("TukTuk Driver", 
                               filters={"user_account": frappe.session.user},
                               fields=["name", "driver_name", "current_deposit_balance", "left_to_target"],
                               limit=1)
        
        if tuktuk_driver:
            driver = tuktuk_driver[0]
            context.driver_name = driver.driver_name
            context.current_deposit_balance = driver.current_deposit_balance or 0
            context.left_to_target = driver.left_to_target or 0
        else:
            context.driver_name = "Driver"
            context.current_deposit_balance = 0
            context.left_to_target = 0
        
        context.update({
            "show_sidebar": False,
            "no_breadcrumbs": True,
            "current_page": "home",
            "today_date": dashboard_data.get("today_date", ""),
            "today_earnings": dashboard_data.get("today_earnings", 0),
            "daily_target": dashboard_data.get("daily_target", 0),
            "current_balance": dashboard_data.get("tuktuk_driver", {}).get("current_balance", 0),
            "left_to_target": context.left_to_target,
            "target_progress": dashboard_data.get("target_progress", 0),
            "tuktuk": dashboard_data.get("tuktuk"),
            "consecutive_misses": dashboard_data.get("tuktuk_driver", {}).get("consecutive_misses", 0)
        })
        
    except frappe.Redirect:
        raise
    except Exception as e:
        frappe.log_error(f"Driver home page error: {str(e)}")
        context.update({
            "error": str(e),
            "show_sidebar": False,
            "no_breadcrumbs": True,
            "current_page": "home"
        })
