import frappe
from frappe import _

def get_context(context):
    """SMS Broadcast page context"""
    try:
        # Check if user is logged in
        if frappe.session.user == "Guest":
            frappe.local.flags.redirect_location = "/login"
            raise frappe.Redirect
        
        # Check permissions - only System Manager and Tuktuk Manager can access
        user_roles = frappe.get_roles(frappe.session.user)
        allowed_roles = ["System Manager", "Tuktuk Manager"]
        
        if not any(role in allowed_roles for role in user_roles):
            frappe.throw(_("Access denied - Insufficient permissions"), frappe.PermissionError)
        
        # Get SMS configuration status
        try:
            from tuktuk_management.api.sms_notifications import get_sms_status
            sms_status = get_sms_status()
        except Exception as e:
            frappe.log_error(f"Error getting SMS status: {str(e)}")
            sms_status = {"success": False, "message": "Error loading SMS status"}
        
        context.update({
            "show_sidebar": True,
            "no_breadcrumbs": False,
            "sms_status": sms_status
        })
        
    except frappe.Redirect:
        raise
    except Exception as e:
        frappe.log_error(f"SMS Broadcast page error: {str(e)}")
        context.update({
            "error": str(e),
            "show_sidebar": True,
            "no_breadcrumbs": False
        })

