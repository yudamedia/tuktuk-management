import frappe
from frappe import _

@frappe.whitelist()
def withdraw_driver_balance(driver_name: str):
    """
    Withdraw the driver's current target balance via MPesa B2C.
    Sends the full positive balance to the driver's Mpesa number and zeroes the balance.
    """
    try:
        driver = frappe.get_doc("TukTuk Driver", driver_name)

        amount = float(driver.current_balance or 0)
        if amount <= 0:
            return {"success": False, "error": "No balance available for withdrawal"}

        # Ensure mpesa number exists
        if not driver.mpesa_number:
            return {"success": False, "error": "Driver has no Mpesa number configured"}

        # Send B2C payment
        from tuktuk_management.api.sendpay import send_mpesa_payment
        success = send_mpesa_payment(driver.mpesa_number, amount, payment_type="FARE")

        if not success:
            return {"success": False, "error": "Failed to initiate MPesa payout"}

        # Zero out the balance after initiating payout
        driver.current_balance = 0
        driver.save(ignore_permissions=True)
        frappe.db.commit()

        # Add comment for audit trail
        driver.add_comment('Comment', f'Balance withdrawal initiated: {amount} KSH sent to {driver.mpesa_number}')

        return {"success": True, "amount": amount}

    except Exception as e:
        frappe.log_error(f"Withdraw Driver Balance Error: {str(e)}")
        return {"success": False, "error": str(e)}



