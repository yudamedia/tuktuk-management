import frappe
from frappe import _

def get_context(context):
    """TukTuk Driver dashboard context"""
    try:
        # Check if user is logged in and is a driver
        if frappe.session.user == "Guest":
            frappe.local.flags.redirect_location = "/login"
            raise frappe.Redirect
        
        user_roles = frappe.get_roles(frappe.session.user)
        if "TukTuk Driver" not in user_roles:
            frappe.throw(_("Access denied - TukTuk Driver role required"), frappe.PermissionError)
        
        # Get driver dashboard data using our API
        try:
            from tuktuk_management.api.driver_auth import get_tuktuk_driver_dashboard_data
            dashboard_data = get_tuktuk_driver_dashboard_data()
        except ImportError:
            # Handle case where driver_auth.py doesn't exist yet
            context.update({
                "error": "TukTuk driver authentication module not found. Please ensure driver_auth.py is created.",
                "show_sidebar": False,
                "no_breadcrumbs": True
            })
            return
        
        context.update({
            "show_sidebar": False,
            "no_breadcrumbs": True,
            **dashboard_data
        })
        
    except frappe.Redirect:
        raise
    except Exception as e:
        frappe.log_error(f"TukTuk driver dashboard error: {str(e)}")
        context.update({
            "error": str(e),
            "show_sidebar": False,
            "no_breadcrumbs": True
        })