import frappe
from frappe import _

def get_context(context):
    """Driver Deposit page context"""
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
        
        # Get deposit data
        from tuktuk_management.api.driver_auth import get_driver_deposit_data
        deposit_data = get_driver_deposit_data()
        
        from frappe.utils import format_date, today, format_datetime
        # Format deposit transaction dates
        for transaction in deposit_data.get("deposit_transactions", []):
            if transaction.get("transaction_date"):
                transaction["date_formatted"] = format_date(transaction["transaction_date"], "dd MMM yyyy")
        
        context.update({
            "show_sidebar": False,
            "no_breadcrumbs": True,
            "current_page": "deposit",
            "driver_name": driver.driver_name,
            "today_date": format_date(today(), "dd MMM yyyy"),
            "current_deposit_balance": deposit_data.get("current_deposit_balance", 0),
            "initial_deposit_amount": deposit_data.get("initial_deposit_amount", 0),
            "deposit_required": deposit_data.get("deposit_required", 0),
            "deposit_transactions": deposit_data.get("deposit_transactions", []),
            "transaction_count": deposit_data.get("transaction_count", 0),
            "refund_status": deposit_data.get("refund_status", "N/A"),
            "refund_amount": deposit_data.get("refund_amount", 0)
        })
        
    except frappe.Redirect:
        raise
    except Exception as e:
        frappe.log_error(f"Driver deposit page error: {str(e)}")
        context.update({
            "error": str(e),
            "show_sidebar": False,
            "no_breadcrumbs": True,
            "current_page": "deposit",
            "current_deposit_balance": 0,
            "deposit_transactions": []
        })
