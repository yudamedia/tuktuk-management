import frappe
from frappe import _

def get_context(context):
    """TukTuk Driver dashboard context - Redirects to new multi-page dashboard"""
    try:
        # Check if user is logged in and is a driver
        if frappe.session.user == "Guest":
            frappe.local.flags.redirect_location = "/login"
            raise frappe.Redirect
        
        user_roles = frappe.get_roles(frappe.session.user)
        if "TukTuk Driver" not in user_roles:
            frappe.throw(_("Access denied - TukTuk Driver role required"), frappe.PermissionError)
        
        # Redirect to new multi-page dashboard home
        frappe.local.flags.redirect_location = "/driver/home"
        raise frappe.Redirect
        
    except frappe.Redirect:
        raise
    except Exception as e:
        frappe.log_error(f"TukTuk driver dashboard redirect error: {str(e)}")
        # Fallback: redirect anyway
        frappe.local.flags.redirect_location = "/driver/home"
        raise frappe.Redirect