import frappe
from frappe import _

def get_context(context):
    """Driver Transactions page context"""
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
        
        # Get transactions (latest 5)
        from tuktuk_management.api.driver_auth import get_driver_transactions
        transactions_data = get_driver_transactions(limit=5)
        
        from frappe.utils import format_date, today
        context.update({
            "show_sidebar": False,
            "no_breadcrumbs": True,
            "current_page": "transactions",
            "driver_name": driver.driver_name,
            "today_date": format_date(today(), "dd MMM yyyy"),
            "transactions": transactions_data.get("transactions", []),
            "transaction_count": transactions_data.get("count", 0)
        })
        
    except frappe.Redirect:
        raise
    except Exception as e:
        frappe.log_error(f"Driver transactions page error: {str(e)}")
        context.update({
            "error": str(e),
            "show_sidebar": False,
            "no_breadcrumbs": True,
            "current_page": "transactions",
            "transactions": [],
            "transaction_count": 0
        })
