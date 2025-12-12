# -*- coding: utf-8 -*-
"""
Enhanced M-Pesa Confirmation Webhook Handler for Sunny ID Payments

This module adds support for driver repayment via sunny_id as Bill Reference Number.
When a payment comes in with sunny_id, it:
1. Reduces driver's current_balance by the amount (up to current_balance)
2. Any excess goes to deposit balance as "Top Up"
3. Creates TukTuk Transaction as "Target Reduction/Deposit" type
4. No B2C payment is sent
"""

import frappe
from frappe.utils import now_datetime, flt, getdate
import hashlib

def handle_sunny_id_payment(transaction_id, amount, sunny_id, customer_phone, trans_time):
    """
    Handle payment made to driver's sunny_id for target reduction and deposit top-up
    
    Args:
        transaction_id: M-Pesa transaction ID
        amount: Payment amount
        sunny_id: Driver's sunny_id (Bill Reference Number)
        customer_phone: Customer's phone number
        trans_time: Transaction timestamp
        
    Returns:
        dict: Success/failure status
    """
    try:
        frappe.flags.ignore_permissions = True
        
        # Find driver by sunny_id
        driver_data = frappe.db.get_value(
            "TukTuk Driver",
            {"sunny_id": sunny_id},
            ["name", "driver_name", "current_balance", "current_deposit_balance", 
             "assigned_tuktuk", "user"],
            as_dict=True
        )
        
        if not driver_data:
            frappe.log_error(
                "Sunny ID Payment - Driver Not Found",
                f"No driver found with sunny_id: {sunny_id}\n"
                f"Transaction ID: {transaction_id}\n"
                f"Amount: {amount}"
            )
            return {"ResultCode": "0", "ResultDesc": "Success"}
        
        # Check for duplicate transaction
        if frappe.db.exists("TukTuk Transaction", {"transaction_id": transaction_id}):
            frappe.log_error(
                "Sunny ID Payment - Duplicate Transaction",
                f"Transaction {transaction_id} already exists"
            )
            return {"ResultCode": "0", "ResultDesc": "Success"}
        
        # Get driver's tuktuk (required for transaction record)
        tuktuk = driver_data.assigned_tuktuk
        if not tuktuk:
            frappe.log_error(
                "Sunny ID Payment - No Assigned TukTuk",
                f"Driver {driver_data.driver_name} has no assigned tuktuk\n"
                f"Transaction ID: {transaction_id}"
            )
            return {"ResultCode": "0", "ResultDesc": "Success"}
        
        # Calculate target reduction and deposit amount
        current_balance = flt(driver_data.current_balance or 0)
        payment_amount = flt(amount)
        
        # Target reduction is min of current_balance and payment amount
        target_reduction = min(current_balance, payment_amount)
        
        # Deposited amount is any excess after target reduction
        deposited_amount = payment_amount - target_reduction
        
        # Use database savepoint for transaction integrity
        savepoint = 'sunny_id_payment_savepoint'
        try:
            frappe.db.savepoint(savepoint)
            
            # Double-check for duplicate within transaction
            if frappe.db.exists("TukTuk Transaction", {"transaction_id": transaction_id}):
                frappe.db.rollback(save_point=savepoint)
                frappe.log_error(
                    "Sunny ID Payment - Duplicate in Transaction",
                    f"Transaction {transaction_id} already exists"
                )
                return {"ResultCode": "0", "ResultDesc": "Success"}
            
            # Hash customer phone for privacy
            hashed_phone = hashlib.sha256(customer_phone.encode()).hexdigest()
            
            # Parse M-Pesa transaction time
            transaction_time = parse_mpesa_trans_time(trans_time)
            
            # Create TukTuk Transaction record
            transaction = frappe.get_doc({
                "doctype": "TukTuk Transaction",
                "transaction_id": transaction_id,
                "transaction_type": "Target Reduction/Deposit",
                "tuktuk": tuktuk,
                "driver": driver_data.name,
                "amount": payment_amount,
                "driver_share": 0,  # No B2C payment
                "target_contribution": target_reduction,
                "deposited_amount": deposited_amount,
                "customer_phone": hashed_phone,
                "timestamp": transaction_time,
                "payment_status": "Completed",
                "b2c_payment_sent": 0  # No B2C payment for this type
            })
            
            transaction.insert(ignore_permissions=True)
            
            # Update driver's current_balance (reduce by target_reduction)
            # Use atomic SQL UPDATE to prevent race conditions
            if target_reduction > 0:
                frappe.db.sql("""
                    UPDATE `tabTukTuk Driver`
                    SET current_balance = GREATEST(0, current_balance - %s)
                    WHERE name = %s
                """, (target_reduction, driver_data.name))
                
                # Also update left_to_target
                settings = frappe.get_single("TukTuk Settings")
                global_target = settings.global_daily_target or 0
                
                frappe.db.sql("""
                    UPDATE `tabTukTuk Driver`
                    SET left_to_target = GREATEST(0, 
                        COALESCE(NULLIF(daily_target, 0), %s) - current_balance
                    )
                    WHERE name = %s
                """, (global_target, driver_data.name))
            
            # Add deposit transaction if there's deposited amount
            if deposited_amount > 0:
                # Get or create driver document
                driver_doc = frappe.get_doc("TukTuk Driver", driver_data.name)
                
                # Update deposit balance
                new_deposit_balance = flt(driver_doc.current_deposit_balance or 0) + deposited_amount
                driver_doc.current_deposit_balance = new_deposit_balance
                
                # Add deposit transaction to child table
                # This bypasses deposit_required validation as requested
                driver_doc.append("deposit_transactions", {
                    "transaction_date": getdate(),
                    "transaction_type": "Top Up",
                    "amount": deposited_amount,
                    "balance_after_transaction": new_deposit_balance,
                    "transaction_reference": transaction_id,
                    "description": f"Automatic top-up from sunny_id payment. Target reduction: {target_reduction} KSH, Excess deposited: {deposited_amount} KSH",
                    "approved_by": driver_doc.user or frappe.session.user
                })
                
                # Save driver document
                driver_doc.flags.ignore_validate_update_after_submit = True
                driver_doc.flags.ignore_permissions = True
                driver_doc.save(ignore_permissions=True)
            
            # Commit all changes
            frappe.db.commit()
            
            # Log success
            frappe.log_error(
                "✅ Sunny ID Payment Processed Successfully",
                f"""
                Driver: {driver_data.driver_name} ({sunny_id})
                Transaction ID: {transaction_id}
                Total Amount: {payment_amount} KSH
                Target Reduction: {target_reduction} KSH
                Deposited Amount: {deposited_amount} KSH
                New Current Balance: {current_balance - target_reduction} KSH
                New Deposit Balance: {flt(driver_data.current_deposit_balance or 0) + deposited_amount} KSH
                """
            )
            
            return {"ResultCode": "0", "ResultDesc": "Success"}
            
        except Exception as inner_error:
            # Rollback on error
            frappe.db.rollback(save_point=savepoint)
            frappe.log_error(
                "Sunny ID Payment - Transaction Error",
                f"Error: {str(inner_error)}\n"
                f"Transaction ID: {transaction_id}"
            )
            raise
            
    except Exception as e:
        frappe.log_error(
            "Sunny ID Payment - System Error",
            f"Error: {str(e)}\n"
            f"Transaction ID: {transaction_id}"
        )
        return {"ResultCode": "0", "ResultDesc": "Success"}


def parse_mpesa_trans_time(trans_time):
    """
    Parse M-Pesa transaction time format (YYYYMMDDHHmmss) to datetime
    
    Args:
        trans_time: M-Pesa timestamp string (e.g., "20250112143045")
        
    Returns:
        datetime: Parsed datetime object
    """
    try:
        from datetime import datetime
        
        if not trans_time or len(trans_time) < 14:
            return now_datetime()
        
        # Parse format: YYYYMMDDHHmmss
        year = int(trans_time[0:4])
        month = int(trans_time[4:6])
        day = int(trans_time[6:8])
        hour = int(trans_time[8:10])
        minute = int(trans_time[10:12])
        second = int(trans_time[12:14])
        
        return datetime(year, month, day, hour, minute, second)
        
    except Exception as e:
        frappe.log_error(f"Error parsing M-Pesa time: {str(e)}")
        return now_datetime()


def is_sunny_id_format(account_number):
    """
    Check if account number matches sunny_id format
    
    Sunny ID format: D followed by 6 digits (e.g., D112456)
    
    Args:
        account_number: Account number from M-Pesa payment
        
    Returns:
        bool: True if matches sunny_id format
    """
    import re
    
    if not account_number:
        return False
    
    # Pattern: D followed by 6 digits
    pattern = r'^D\d{6}$'
    return bool(re.match(pattern, account_number.strip().upper()))


# Integration function to add to existing mpesa_confirmation webhook
def integrate_sunny_id_check(transaction_id, amount, account_number, customer_phone, trans_time):
    """
    Integration point for existing mpesa_confirmation webhook
    
    This should be called BEFORE checking for tuktuk account numbers
    If account_number is a sunny_id, process it and return immediately
    
    Args:
        transaction_id: M-Pesa transaction ID
        amount: Payment amount
        account_number: Bill Reference Number (could be tuktuk or sunny_id)
        customer_phone: Customer phone
        trans_time: Transaction time
        
    Returns:
        dict or None: Response if handled, None if not a sunny_id payment
    """
    
    # Check if this is a sunny_id payment
    if is_sunny_id_format(account_number):
        return handle_sunny_id_payment(
            transaction_id=transaction_id,
            amount=amount,
            sunny_id=account_number.strip().upper(),
            customer_phone=customer_phone,
            trans_time=trans_time
        )
    
    # Not a sunny_id, let regular flow continue
    return None
