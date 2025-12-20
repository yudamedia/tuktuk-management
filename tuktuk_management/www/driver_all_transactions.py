import frappe
from frappe import _
from frappe.utils import format_datetime, get_datetime

def get_context(context):
    """Driver All Transactions page context"""
    try:
        # Check if user is logged in and is a driver
        if frappe.session.user == "Guest":
            frappe.local.flags.redirect_location = "/login"
            raise frappe.Redirect
        
        user_roles = frappe.get_roles(frappe.session.user)
        if "TukTuk Driver" not in user_roles:
            frappe.throw(_("Access denied - TukTuk Driver role required"), frappe.PermissionError)
        
        # Get driver details
        driver = frappe.get_all("TukTuk Driver", 
                               filters={"user_account": frappe.session.user},
                               fields=["name", "driver_name"],
                               limit=1)
        
        if not driver:
            frappe.throw(_("TukTuk driver record not found"))
        
        driver_record = driver[0]
        
        # Get pagination parameters
        page = int(frappe.form_dict.get("page", 1))
        per_page = 50
        start = (page - 1) * per_page
        
        # Get all transactions for this driver
        transactions = frappe.get_all(
            "TukTuk Transaction",
            filters={"driver": driver_record.name},
            fields=[
                "name",
                "timestamp",
                "transaction_id",
                "amount",
                "driver_share",
                "target_contribution",
                "payment_status",
                "customer_phone",
                "transaction_type"
            ],
            order_by="timestamp desc",
            limit_start=start,
            limit_page_length=per_page
        )
        
        # Get total count for pagination
        total_count = frappe.db.count(
            "TukTuk Transaction",
            filters={"driver": driver_record.name}
        )
        
        # Format transaction data
        for transaction in transactions:
            transaction.timestamp_formatted = format_datetime(
                transaction.timestamp, 
                "dd MMM yyyy HH:mm"
            )
            
            # Add date grouping
            transaction.date_only = get_datetime(transaction.timestamp).date()
        
        # Group by date
        transactions_by_date = {}
        for transaction in transactions:
            date_str = transaction.date_only.strftime("%A, %d %B %Y")
            if date_str not in transactions_by_date:
                transactions_by_date[date_str] = {
                    "date": date_str,
                    "date_obj": transaction.date_only,
                    "transactions": [],
                    "total_amount": 0,
                    "total_driver_share": 0,
                    "total_target": 0
                }
            
            transactions_by_date[date_str]["transactions"].append(transaction)
            transactions_by_date[date_str]["total_amount"] += transaction.amount or 0
            transactions_by_date[date_str]["total_driver_share"] += transaction.driver_share or 0
            transactions_by_date[date_str]["total_target"] += transaction.target_contribution or 0
        
        # Convert to list and sort
        grouped_transactions = list(transactions_by_date.values())
        grouped_transactions.sort(key=lambda x: x["date_obj"], reverse=True)
        
        # Calculate totals
        total_amount = sum(t.amount for t in transactions if t.amount)
        total_driver_share = sum(t.driver_share for t in transactions if t.driver_share)
        total_target = sum(t.target_contribution for t in transactions if t.target_contribution)
        
        # Calculate pagination
        total_pages = (total_count + per_page - 1) // per_page
        has_previous = page > 1
        has_next = page < total_pages
        
        context.update({
            "show_sidebar": False,
            "no_breadcrumbs": True,
            "current_page": "transactions",
            "driver_name": driver_record.driver_name,
            "driver_id": driver_record.name,
            "grouped_transactions": grouped_transactions,
            "transaction_count": total_count,
            "total_amount": total_amount,
            "total_driver_share": total_driver_share,
            "total_target": total_target,
            "page": page,
            "total_pages": total_pages,
            "has_previous": has_previous,
            "has_next": has_next,
            "per_page": per_page
        })
        
    except frappe.Redirect:
        raise
    except Exception as e:
        frappe.log_error(f"Driver all transactions page error: {str(e)}")
        context.update({
            "error": str(e),
            "show_sidebar": False,
            "no_breadcrumbs": True,
            "current_page": "transactions",
            "grouped_transactions": [],
            "transaction_count": 0
        })