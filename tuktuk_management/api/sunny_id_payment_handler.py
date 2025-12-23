# -*- coding: utf-8 -*-
"""
Enhanced M-Pesa Confirmation Webhook Handler for Sunny ID Payments

CRITICAL FIX (2025-12-22):
- Now CALCULATES left_to_target FRESH from current_balance and target
- Previous version used stale left_to_target from database which could be incorrect
- left_to_target = max(0, daily_target - current_balance)
- This ensures payments are always applied correctly regardless of DB state

How it works:
- left_to_target = exact amount needed to clear daily target (calculated fresh)
- current_balance = running total of payments toward target
- daily_target = driver's individual target OR global_daily_target

This module adds support for driver repayment via sunny_id as Bill Reference Number.
When a payment comes in with sunny_id, it:
1. Calculates left_to_target fresh from current balance and target
2. Reduces driver's left_to_target (outstanding debt) by payment amount
3. Adds payment to current_balance (running total toward target)
4. Any excess after clearing left_to_target goes to deposit
5. No B2C payment is sent
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
            ["name", "driver_name", "current_balance", "daily_target",
             "current_deposit_balance", "assigned_tuktuk", "user"],
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

        # CRITICAL FIX: Calculate left_to_target FRESH instead of using stale DB value
        # This prevents issues where left_to_target in DB might be incorrect
        settings = frappe.get_single("TukTuk Settings")
        driver_target = flt(driver_data.daily_target or settings.global_daily_target or 0)
        current_balance = flt(driver_data.current_balance or 0)
        left_to_target = max(0, driver_target - current_balance)

        payment_amount = flt(amount)

        # Target reduction is min of left_to_target (debt) and payment amount
        target_reduction = min(left_to_target, payment_amount)

        # Deposited amount is any excess after clearing debt
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
            
            # FIXED: Use single atomic SQL UPDATE to prevent race conditions
            # Updates current_balance, left_to_target, and deposit_balance in one statement
            # This prevents the before_save hook from overwriting correct values

            # Get global target for calculation
            settings = frappe.get_single("TukTuk Settings")
            global_target = settings.global_daily_target or 0

            # Get current deposit balance for the new balance calculation
            current_deposit = flt(driver_data.get('current_deposit_balance', 0))
            new_deposit_balance = current_deposit + deposited_amount

            # Single atomic SQL update for ALL fields (prevents race condition)
            frappe.db.sql("""
                UPDATE `tabTukTuk Driver`
                SET
                    current_balance = current_balance + %s,
                    left_to_target = GREATEST(0,
                        COALESCE(NULLIF(daily_target, 0), %s) - (current_balance + %s)
                    ),
                    current_deposit_balance = current_deposit_balance + %s
                WHERE name = %s
            """, (target_reduction, global_target, target_reduction, deposited_amount, driver_data.name))

            # Add deposit transaction to child table using direct SQL INSERT
            # This avoids loading/saving the driver document which would trigger before_save hook
            if deposited_amount > 0:
                # Generate unique name for child table row
                from frappe.model.naming import make_autoname
                child_name = make_autoname('hash', 'Driver Deposit Transaction')

                frappe.db.sql("""
                    INSERT INTO `tabDriver Deposit Transaction`
                    (name, parent, parenttype, parentfield, idx, creation, modified,
                     transaction_date, transaction_type, amount, balance_after_transaction,
                     transaction_reference, description, approved_by)
                    VALUES (%s, %s, 'TukTuk Driver', 'deposit_transactions',
                            (SELECT COALESCE(MAX(idx), 0) + 1 FROM `tabDriver Deposit Transaction` WHERE parent = %s),
                            NOW(), NOW(), %s, %s, %s, %s, %s, %s, %s)
                """, (
                    child_name,
                    driver_data.name,
                    driver_data.name,
                    getdate(),
                    'Top Up',
                    deposited_amount,
                    new_deposit_balance,
                    transaction_id,
                    f"Automatic top-up from sunny_id payment. Target reduction: {target_reduction} KSH, Excess deposited: {deposited_amount} KSH",
                    driver_data.get('user') or frappe.session.user
                ))
            
            # Commit all changes
            frappe.db.commit()
            
            # Log success
            frappe.log_error(
                "✅ Sunny ID Payment Processed Successfully",
                f"""
                Driver: {driver_data.driver_name} ({sunny_id})
                Transaction ID: {transaction_id}
                Total Amount: {payment_amount} KSH

                BEFORE:
                - Target: {driver_target} KSH
                - left_to_target (calculated fresh): {left_to_target} KSH
                - current_balance: {driver_data.current_balance} KSH

                APPLIED:
                - Target Reduction: {target_reduction} KSH
                - Deposited Amount: {deposited_amount} KSH

                AFTER:
                - left_to_target: {max(0, left_to_target - target_reduction)} KSH
                - current_balance: {driver_data.current_balance + target_reduction} KSH
                - deposit_balance: {flt(driver_data.current_deposit_balance or 0) + deposited_amount} KSH
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