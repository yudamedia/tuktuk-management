# ~/frappe-bench/apps/tuktuk_management/tuktuk_management/tuktuk_management/doctype/tuktuk_petty_cash/tuktuk_petty_cash.py

import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime, flt
import re

class TukTukPettyCash(Document):
    def validate(self):
        """Validate petty cash payment before saving"""
        self.validate_phone_number()
        self.validate_amount()
        self.auto_fill_driver_details()
        
    def validate_phone_number(self):
        """Validate and format phone number"""
        if not self.recipient_phone:
            frappe.throw("Recipient phone number is required")
            
        # Clean the phone number
        cleaned_number = str(self.recipient_phone).replace(' ', '').replace('-', '')
        
        # Check format: +254XXXXXXXXX or 254XXXXXXXXX or 0XXXXXXXXX
        pattern = r'^(?:\+254|254|0)\d{9}$'
        if not re.match(pattern, cleaned_number):
            frappe.throw("Invalid phone number format. Use format: +254XXXXXXXXX or 0XXXXXXXXX")
            
        # Standardize format to 254XXXXXXXXX
        if cleaned_number.startswith('+'):
            cleaned_number = cleaned_number[1:]
        elif cleaned_number.startswith('0'):
            cleaned_number = '254' + cleaned_number[1:]
                
        self.recipient_phone = cleaned_number
    
    def validate_amount(self):
        """Validate payment amount"""
        if flt(self.amount) <= 0:
            frappe.throw("Payment amount must be greater than zero")
        
        # Optional: Set maximum limit for petty cash
        settings = frappe.get_single("TukTuk Settings")
        max_petty_cash = getattr(settings, 'max_petty_cash_amount', 10000)
        
        if flt(self.amount) > flt(max_petty_cash):
            frappe.throw(f"Payment amount exceeds maximum petty cash limit of KSH {max_petty_cash}")
    
    def auto_fill_driver_details(self):
        """Auto-fill recipient details if driver is selected"""
        if self.recipient_type == "Driver" and self.driver:
            driver = frappe.get_doc("TukTuk Driver", self.driver)
            self.recipient_name = driver.driver_name
            self.recipient_phone = driver.mpesa_number
    
    def before_submit(self):
        """Prevent submission if not approved"""
        if self.payment_status not in ["Approved", "Completed"]:
            frappe.throw("Only approved payments can be submitted")


@frappe.whitelist()
def approve_payment(docname):
    """Approve a petty cash payment"""
    doc = frappe.get_doc("TukTuk Petty Cash", docname)
    
    if doc.payment_status != "Pending":
        frappe.throw("Only pending payments can be approved")
    
    doc.payment_status = "Approved"
    doc.approved_by = frappe.session.user
    doc.approved_date = now_datetime()
    doc.save()
    
    frappe.msgprint(f"Payment {docname} approved successfully")
    return doc


@frappe.whitelist()
def reject_payment(docname, reason):
    """Reject a petty cash payment"""
    doc = frappe.get_doc("TukTuk Petty Cash", docname)
    
    if doc.payment_status != "Pending":
        frappe.throw("Only pending payments can be rejected")
    
    if not reason:
        frappe.throw("Rejection reason is required")
    
    doc.payment_status = "Rejected"
    doc.rejected_by = frappe.session.user
    doc.rejected_date = now_datetime()
    doc.rejection_reason = reason
    doc.save()
    
    frappe.msgprint(f"Payment {docname} rejected")
    return doc


@frappe.whitelist()
def process_payment(docname):
    """Process approved petty cash payment via B2C"""
    from tuktuk_management.api.sendpay import send_mpesa_payment
    
    doc = frappe.get_doc("TukTuk Petty Cash", docname)
    
    # Validate payment can be processed
    if doc.payment_status != "Approved":
        frappe.throw("Only approved payments can be processed")
    
    # Update status to processing
    doc.payment_status = "Processing"
    doc.save()
    frappe.db.commit()
    
    try:
        # Send B2C payment
        success = send_mpesa_payment(
            mpesa_number=doc.recipient_phone,
            amount=doc.amount,
            payment_type="PETTY_CASH",
            petty_cash_doc=doc.name
        )
        
        if success:
            frappe.msgprint(f"✅ B2C payment of KSH {doc.amount} initiated to {doc.recipient_name}")
            frappe.msgprint("Payment is being processed by MPesa. Check transaction details shortly.")
            return {"success": True, "message": "Payment initiated successfully"}
        else:
            # Update status back to approved if failed
            doc.payment_status = "Approved"
            doc.save()
            frappe.throw("Failed to initiate B2C payment. Check Error Log for details.")
            
    except Exception as e:
        # Revert status on error
        doc.payment_status = "Approved"
        doc.save()
        frappe.log_error(f"Petty Cash Payment Failed: {str(e)}", "B2C Payment Error")
        frappe.throw(f"Error processing payment: {str(e)}")


@frappe.whitelist()
def update_mpesa_response(docname, conversation_id, originator_conversation_id, response_code, response_description):
    """Update petty cash record with MPesa response"""
    doc = frappe.get_doc("TukTuk Petty Cash", docname)
    
    doc.mpesa_conversation_id = conversation_id
    doc.mpesa_originator_conversation_id = originator_conversation_id
    doc.mpesa_response_code = response_code
    doc.mpesa_response_description = response_description
    
    # Update status based on response
    if response_code == "0":
        doc.payment_status = "Processing"
    else:
        doc.payment_status = "Failed"
    
    doc.save()
    frappe.db.commit()


@frappe.whitelist()
def update_mpesa_result(conversation_id, result_code, transaction_id):
    """Update petty cash record with final MPesa result"""
    # Find the petty cash record by conversation ID
    petty_cash = frappe.get_all(
        "TukTuk Petty Cash",
        filters={"mpesa_conversation_id": conversation_id},
        fields=["name"]
    )
    
    if not petty_cash:
        frappe.log_error(f"No petty cash record found for conversation ID: {conversation_id}")
        return
    
    doc = frappe.get_doc("TukTuk Petty Cash", petty_cash[0].name)
    
    doc.mpesa_result_code = str(result_code)
    doc.mpesa_transaction_id = transaction_id
    
    # Update status based on result
    if str(result_code) == "0":
        doc.payment_status = "Completed"
    else:
        doc.payment_status = "Failed"
    
    doc.save()
    frappe.db.commit()
    
    frappe.log_error(
        f"Petty Cash Payment Result: {doc.payment_status}",
        f"Transaction ID: {transaction_id}"
    )


@frappe.whitelist()
def get_pending_payments():
    """Get all pending petty cash payments"""
    return frappe.get_all(
        "TukTuk Petty Cash",
        filters={"payment_status": "Pending"},
        fields=["name", "recipient_name", "amount", "purpose", "payment_date", "category"],
        order_by="payment_date desc"
    )


@frappe.whitelist()
def get_payment_summary(from_date=None, to_date=None):
    """Get summary of petty cash payments"""
    filters = {}
    
    if from_date:
        filters["payment_date"] = [">=", from_date]
    if to_date:
        if "payment_date" in filters:
            filters["payment_date"] = ["between", [from_date, to_date]]
        else:
            filters["payment_date"] = ["<=", to_date]
    
    payments = frappe.get_all(
        "TukTuk Petty Cash",
        filters=filters,
        fields=["payment_status", "amount", "category"]
    )
    
    summary = {
        "total_approved": 0,
        "total_completed": 0,
        "total_pending": 0,
        "total_failed": 0,
        "by_category": {}
    }
    
    for payment in payments:
        amount = flt(payment.amount)
        
        if payment.payment_status == "Approved":
            summary["total_approved"] += amount
        elif payment.payment_status == "Completed":
            summary["total_completed"] += amount
        elif payment.payment_status == "Pending":
            summary["total_pending"] += amount
        elif payment.payment_status == "Failed":
            summary["total_failed"] += amount
        
        # Category summary
        category = payment.category or "Other"
        if category not in summary["by_category"]:
            summary["by_category"][category] = 0
        summary["by_category"][category] += amount
    
    return summary
