# ~/frappe-bench/apps/tuktuk_management/tuktuk_management/api/tuktuk.py

import frappe
from frappe.utils import now_datetime, get_time, get_datetime, add_to_date, getdate, date_diff, flt
from datetime import datetime, time
import re
import requests
import base64
import json

from tuktuk_management.api.sunny_id_payment_handler import (
    handle_sunny_id_payment,
    is_sunny_id_format,
    parse_mpesa_trans_time
)

# Import B2C payment function from sendpay module
from tuktuk_management.api.sendpay import send_mpesa_payment

# PRODUCTION Daraja API Configuration
PRODUCTION_BASE_URL = "https://api.safaricom.co.ke"
SANDBOX_BASE_URL = "https://sandbox.safaricom.co.ke"

# ===== CORE VALIDATION FUNCTIONS =====

def validate_mpesa_number(doc):
    """Validate MPesa phone number format"""
    if not doc.mpesa_number:
        frappe.throw("MPesa number is required")
        
    # Clean the phone number
    cleaned_number = str(doc.mpesa_number).replace(' ', '')
    
    # Check format: +254XXXXXXXXX or 254XXXXXXXXX or 0XXXXXXXXX
    pattern = r'^(?:\+254|254|0)\d{9}$'
    if not re.match(pattern, cleaned_number):
        frappe.throw("Invalid MPesa number format. Use format: +254XXXXXXXXX or 0XXXXXXXXX")
        
    # Standardize format to 254XXXXXXXXX
    if cleaned_number.startswith('+'):
        cleaned_number = cleaned_number[1:]
    elif cleaned_number.startswith('0'):
        cleaned_number = '254' + cleaned_number[1:]
            
    doc.mpesa_number = cleaned_number

def validate_mpesa_number_string(mpesa_number):
    """Validate MPesa number format for string input"""
    if not mpesa_number:
        frappe.throw("MPesa number is required")
        
    cleaned_number = str(mpesa_number).replace(' ', '')
    pattern = r'^(?:\+254|254|0)\d{9}$'
    if not re.match(pattern, cleaned_number):
        frappe.throw("Invalid MPesa number format. Use format: +254XXXXXXXXX or 0XXXXXXXXX")
        
    return True

# def parse_mpesa_trans_time(trans_time_str):
#     """Parse M-Pesa TransTime format (YYYYMMDDHHmmss) to datetime object"""
#     if not trans_time_str:
#         return now_datetime()
    
#     try:
#         # M-Pesa format: YYYYMMDDHHmmss (e.g., "20250101153053")
#         if len(trans_time_str) == 14:
#             dt = datetime.strptime(trans_time_str, '%Y%m%d%H%M%S')
#             return get_datetime(dt)
#         else:
#             # If format is unexpected, return current time
#             return now_datetime()
#     except (ValueError, TypeError):
#         # If parsing fails, return current time
#         return now_datetime()

def is_within_operating_hours():
    """Check if current time is within operating hours"""
    settings = frappe.get_single("TukTuk Settings")
    current_time = get_time(now_datetime())
    start_time = get_time(settings.operating_hours_start)
    end_time = get_time(settings.operating_hours_end)
    
    if end_time < start_time:  # Handles overnight period (e.g., 6:00 to 00:00)
        return current_time >= start_time or current_time <= end_time
    return start_time <= current_time <= end_time

def check_battery_level(tuktuk_doc):
    """Check battery level and send notifications if low"""
    BATTERY_WARNING_THRESHOLD = 20
    if tuktuk_doc.battery_level <= BATTERY_WARNING_THRESHOLD:
        settings = frappe.get_single("TukTuk Settings")
        message = f"Low battery warning for TukTuk {tuktuk_doc.tuktuk_id}: {tuktuk_doc.battery_level}%"
        
        if settings.enable_sms_notifications:
            # Implement SMS notification
            try:
                # Add SMS gateway integration here
                pass
            except Exception as e:
                frappe.log_error(f"SMS Notification Failed: {str(e)}")
                
        if settings.enable_email_notifications:
            try:
                frappe.sendmail(
                    recipients=["yuda@sunnytuktuk.com"],  # Update with actual email
                    subject="Low Battery Alert",
                    message=message
                )
            except Exception as e:
                frappe.log_error(f"Email Notification Failed: {str(e)}")

# ===== PRODUCTION DARAJA INTEGRATION =====

def get_access_token():
    """Get OAuth access token from Daraja API - PRODUCTION VERSION"""
    settings = frappe.get_single("TukTuk Settings")
    
    # Use PRODUCTION URLs
    api_url = f"{PRODUCTION_BASE_URL}/oauth/v1/generate?grant_type=client_credentials"
    
    # Get your production credentials
    consumer_key = settings.get_password("mpesa_api_key")
    consumer_secret = settings.get_password("mpesa_api_secret")
    
    if not consumer_key or not consumer_secret:
        frappe.log_error("Production Daraja Config Error", "Production MPesa API credentials not configured in TukTuk Settings")
        return None
    
    # Create credentials string
    credentials = f"{consumer_key}:{consumer_secret}"
    encoded_credentials = base64.b64encode(credentials.encode()).decode()
    
    headers = {
        "Authorization": f"Basic {encoded_credentials}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(api_url, headers=headers, timeout=30)
        if response.status_code == 200:
            token_data = response.json()
            frappe.log_error("Production Daraja Token Success", f"Production access token obtained")
            return token_data.get("access_token")
        else:
            frappe.log_error("Production Daraja Token Failed", f"Status: {response.status_code}, Response: {response.text}")
            return None
    except Exception as e:
        frappe.log_error("Production Daraja Token Error", str(e))
        return None

def register_c2b_url():
    """Register callback URLs for C2B transactions - FIXED VERSION"""
    settings = frappe.get_single("TukTuk Settings")
    access_token = get_access_token()
    
    if not access_token:
        frappe.throw("Failed to get production access token")
    
    # Use PRODUCTION URL
    api_url = f"{PRODUCTION_BASE_URL}/mpesa/c2b/v2/registerurl"
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    # Use YOUR production shortcode (paybill)
    shortcode = settings.mpesa_paybill or "4165253"
    
    # FIXED: Use hardcoded correct URL instead of frappe.utils.get_url()
    base_url = "https://console.sunnytuktuk.com"  # Hardcode without :8000
    
    payload = {
        "ShortCode": shortcode,
        "ResponseType": "Completed",  # Only confirmed payments
        "ConfirmationURL": f"{base_url}/api/method/tuktuk_management.api.tuktuk.payment_confirmation",
        "ValidationURL": f"{base_url}/api/method/tuktuk_management.api.tuktuk.payment_validation"
    }
    
    # Log what we're registering
    frappe.msgprint(f"🔗 Registering URLs:")
    frappe.msgprint(f"Validation: {payload['ValidationURL']}")
    frappe.msgprint(f"Confirmation: {payload['ConfirmationURL']}")
    
    try:
        response = requests.post(api_url, json=payload, headers=headers, timeout=30)
        result = response.json()
        
        # FIXED: Handle both "0" and "00000000" response codes
        success_codes = ["0", "00000000"]
        response_code = result.get("ResponseCode", "")
        
        if response.status_code == 200 and response_code in success_codes:
            frappe.msgprint(f"✅ Production C2B URL registration successful!")
            frappe.msgprint(f"Response: {result.get('ResponseDescription', 'Success')}")
            frappe.log_error("Production C2B Registration Success", f"URLs registered successfully: {result}")
            return True
        else:
            frappe.log_error("Production C2B Registration Failed", f"Response: {result}")
            frappe.throw(f"❌ Production C2B URL registration failed: {result}")
            return False
            
    except Exception as e:
        frappe.log_error("Production C2B Registration Error", str(e))
        frappe.throw(f"Production C2B registration error: {str(e)}")
        return False

# Also add this function to check current site URL configuration
@frappe.whitelist()
def check_site_url_config():
    """Check and display current site URL configuration"""
    try:
        current_url = frappe.utils.get_url()
        
        frappe.msgprint(f"Current site URL: {current_url}")
        
        if ":8000" in current_url:
            frappe.msgprint("⚠️ WARNING: Site URL contains :8000 port!")
            frappe.msgprint("This needs to be fixed in your site configuration.")
            
            # Show how to fix it
            frappe.msgprint("To fix: Update site_config.json with correct host_name")
            
        return {
            "url": current_url,
            "has_port": ":8000" in current_url
        }
        
    except Exception as e:
        frappe.throw(f"URL check failed: {str(e)}")        

# ===== WEBHOOK ENDPOINTS (FIXED VERSIONS) =====

@frappe.whitelist(allow_guest=True)
def mpesa_validation(**kwargs):
    """M-Pesa validation endpoint"""
    try:
        # Extract data
        amount = float(kwargs.get('TransAmount', 0))
        account_number = kwargs.get('BillRefNumber', '').strip()
        phone = kwargs.get('MSISDN', '')
        
        # Validation checks
        if amount <= 0:
            return {"ResultCode": "C2B00012", "ResultDesc": "Invalid amount"}
        
        if not account_number:
            return {"ResultCode": "C2B00012", "ResultDesc": "Account number required"}

        # === NEW: Validate sunny_id format ===
        if is_sunny_id_format(account_number):
            # Check if driver exists with this sunny_id
            driver_exists = frappe.db.exists("TukTuk Driver", {"sunny_id": account_number.strip().upper()})
            if not driver_exists:
                # Log failed transaction
                try:
                    frappe.flags.ignore_permissions = True
                    transaction_id = kwargs.get('TransID', f"VAL-{frappe.utils.now_datetime().strftime('%Y%m%d%H%M%S')}-{account_number}")
                    trans_time = kwargs.get('TransTime', '')
                    
                    failed_log = frappe.get_doc({
                        "doctype": "Failed Transaction Log",
                        "transaction_id": transaction_id,
                        "customer_phone": phone,
                        "amount": amount,
                        "transaction_time": parse_mpesa_trans_time(trans_time),
                        "account_number": account_number,
                        "failure_stage": "Validation",
                        "status": "Failed"
                    })
                    failed_log.insert(ignore_permissions=True)
                    frappe.db.commit()
                except Exception as log_error:
                    frappe.log_error(f"Failed to log failed transaction: {str(log_error)}")
                
                return {"ResultCode": "C2B00012", "ResultDesc": f"Invalid sunny ID: {account_number}"}
            
            # Check if driver has assigned tuktuk
            driver = frappe.db.get_value("TukTuk Driver", {"sunny_id": account_number.strip().upper()}, "assigned_tuktuk")
            if not driver:
                return {"ResultCode": "C2B00012", "ResultDesc": "Driver has no assigned tuktuk"}
            
            # Sunny ID is valid, return success
            return {"ResultCode": "0", "ResultDesc": "Success"}
        # === END NEW CODE ===            
        
        # Check if tuktuk exists
        tuktuk_exists = frappe.db.exists("TukTuk Vehicle", {"mpesa_account": account_number})
        if not tuktuk_exists:
            # Log failed transaction
            try:
                frappe.flags.ignore_permissions = True
                transaction_id = kwargs.get('TransID', f"VAL-{frappe.utils.now_datetime().strftime('%Y%m%d%H%M%S')}-{account_number}")
                trans_time = kwargs.get('TransTime', '')
                
                failed_log = frappe.get_doc({
                    "doctype": "Failed Transaction Log",
                    "transaction_id": transaction_id,
                    "customer_phone": phone,
                    "amount": amount,
                    "transaction_time": parse_mpesa_trans_time(trans_time),
                    "account_number": account_number,
                    "failure_stage": "Validation",
                    "status": "Failed"
                })
                failed_log.insert(ignore_permissions=True)
                frappe.db.commit()
            except Exception as log_error:
                # Don't let logging failure break the webhook response
                frappe.log_error(f"Failed to log failed transaction: {str(log_error)}")
            
            return {"ResultCode": "C2B00012", "ResultDesc": f"Invalid account number: {account_number}"}
        
        # Check if tuktuk has assigned driver
        driver = frappe.db.get_value("TukTuk Driver", {"assigned_tuktuk": tuktuk_exists}, "name")
        if not driver:
            return {"ResultCode": "C2B00012", "ResultDesc": "No driver assigned to this tuktuk"}
        
        # Check operating hours
        if not is_within_operating_hours():
            return {"ResultCode": "C2B00012", "ResultDesc": "Payment outside operating hours"}
        
        return {"ResultCode": "0", "ResultDesc": "Success"}
        
    except Exception as e:
        frappe.log_error(f"M-Pesa Validation Error: {str(e)}")
        return {"ResultCode": "C2B00012", "ResultDesc": "Validation failed"}

@frappe.whitelist(allow_guest=True)
def mpesa_confirmation(**kwargs):
    """M-Pesa confirmation endpoint - FIXED VERSION to prevent duplicates"""
    try:
        # Set ignore permissions for all database operations in this webhook
        frappe.flags.ignore_permissions = True
        
        # Extract transaction details
        transaction_id = kwargs.get('TransID')
        amount = float(kwargs.get('TransAmount', 0))
        account_number = kwargs.get('BillRefNumber', '').strip()
        customer_phone = kwargs.get('MSISDN')
        trans_time = kwargs.get('TransTime')
        first_name = kwargs.get('FirstName', '')
        last_name = kwargs.get('LastName', '')
        
        # CRITICAL FIX: Check if transaction already exists FIRST
        existing_transaction = frappe.db.exists("TukTuk Transaction", {"transaction_id": transaction_id})
        if existing_transaction:
            frappe.log_error("Duplicate Transaction Prevented", 
                            f"Transaction {transaction_id} already processed. Skipping duplicate.")
            return {"ResultCode": "0", "ResultDesc": "Success"}

        # === NEW: Check if this is a sunny_id payment ===
        if is_sunny_id_format(account_number):
            return handle_sunny_id_payment(
                transaction_id=transaction_id,
                amount=amount,
                sunny_id=account_number.strip().upper(),
                customer_phone=customer_phone,
                trans_time=trans_time
            )
        # === END NEW CODE ===            
        
        # Find the tuktuk
        tuktuk = frappe.db.get_value("TukTuk Vehicle", {"mpesa_account": account_number}, "name")
        if not tuktuk:
            frappe.log_error(f"M-Pesa Confirmation: TukTuk not found for account: {account_number}")
            
            # Log failed transaction
            try:
                failed_log = frappe.get_doc({
                    "doctype": "Failed Transaction Log",
                    "transaction_id": transaction_id,
                    "customer_phone": customer_phone,
                    "amount": amount,
                    "transaction_time": parse_mpesa_trans_time(trans_time),
                    "account_number": account_number,
                    "failure_stage": "Confirmation",
                    "status": "Failed"
                })
                failed_log.insert(ignore_permissions=True)
                frappe.db.commit()
            except Exception as log_error:
                # Don't let logging failure break the webhook response
                frappe.log_error(f"Failed to log failed transaction: {str(log_error)}")
            
            return {"ResultCode": "0", "ResultDesc": "Success"}
        
        # Find assigned driver
        driver_name = frappe.db.get_value("TukTuk Driver", {"assigned_tuktuk": tuktuk}, "name")
        if not driver_name:
            frappe.log_error(f"M-Pesa Confirmation: No driver assigned to tuktuk: {tuktuk}")
            return {"ResultCode": "0", "ResultDesc": "Success"}
        
        # Get settings for calculations (outside savepoint)
        settings = frappe.get_single("TukTuk Settings")
        transaction_type = kwargs.get('transaction_type', 'Payment')
        
        # RACE CONDITION FIX: Use savepoint and lock driver row FIRST
        savepoint = 'mpesa_confirmation_savepoint'
        try:
            frappe.db.savepoint(savepoint)

            # Double-check for duplicate within transaction
            if frappe.db.exists("TukTuk Transaction", {"transaction_id": transaction_id}):
                frappe.log_error("Duplicate Transaction in Transaction Block",
                                f"Transaction {transaction_id} already exists. Aborting.")
                return {"ResultCode": "0", "ResultDesc": "Success"}

            # CRITICAL FIX: Load driver with row lock to prevent concurrent updates
            driver = frappe.get_doc("TukTuk Driver", driver_name, for_update=True)
            
            # Calculate shares INSIDE the locked transaction
            percentage = driver.fare_percentage or settings.global_fare_percentage
            target = driver.daily_target or settings.global_daily_target

            # Check if target sharing is enabled (driver override takes precedence)
            driver_target_override = getattr(driver, 'target_sharing_override', 'Follow Global')
            if driver_target_override == 'Enable':
                target_sharing_enabled = True
            elif driver_target_override == 'Disable':
                target_sharing_enabled = False
            else:
                target_sharing_enabled = getattr(settings, 'enable_target_sharing', 1)

            # Detect driver repayment: Check if amount matches pending adjustment
            is_driver_repayment = False
            if transaction_type == 'Payment':
                # Look for pending adjustment transactions for this driver
                pending_adjustments = frappe.get_all("TukTuk Transaction",
                                                   filters={
                                                       "driver": driver_name,
                                                       "transaction_type": "Adjustment",
                                                       "amount": amount,
                                                       "payment_status": "Completed"
                                                   },
                                                   fields=["name", "amount"],
                                                   limit=1)

                if pending_adjustments:
                    is_driver_repayment = True
                    transaction_type = 'Driver Repayment'

            if transaction_type == 'Adjustment' or is_driver_repayment:
                driver_share = 0  # No payment to driver
                target_contribution = 0  # No target credit
            elif target_sharing_enabled and driver.current_balance >= target:
                driver_share = amount  # 100% to driver when target met AND target sharing enabled
                target_contribution = 0
            else:
                # Always use percentage sharing when target not met OR target sharing disabled
                driver_share = amount * (percentage / 100)
                target_contribution = amount - driver_share  # Target contribution always calculated

            # Create transaction with calculated fields
            transaction = frappe.get_doc({
                "doctype": "TukTuk Transaction",
                "transaction_id": transaction_id,
                "transaction_type": transaction_type,
                "tuktuk": tuktuk,
                "driver": driver_name,
                "amount": amount,
                "driver_share": driver_share,
                "target_contribution": target_contribution,
                "customer_phone": customer_phone,
                "timestamp": now_datetime(),
                "payment_status": "Pending"  # Start as pending
            })

            transaction.insert(ignore_permissions=True)

            # ATOMIC UPDATE FIX: Use SQL UPDATE to prevent race conditions
            # Skip balance updates for adjustment and driver repayment transactions
            if target_contribution > 0 and transaction_type not in ['Adjustment', 'Driver Repayment']:
                # Get global target for left_to_target calculation
                global_target = settings.global_daily_target or 0
                
                # Use atomic SQL update instead of read-modify-save
                frappe.db.sql("""
                    UPDATE `tabTukTuk Driver`
                    SET current_balance = current_balance + %s
                    WHERE name = %s
                """, (target_contribution, driver_name))
                
                # Also update left_to_target atomically
                frappe.db.sql("""
                    UPDATE `tabTukTuk Driver`
                    SET left_to_target = GREATEST(0, 
                        COALESCE(NULLIF(daily_target, 0), %s) - current_balance
                    )
                    WHERE name = %s
                """, (global_target, driver_name))
                
                # Reload driver to get updated balance
                driver.reload()

            # Mark transaction as completed after successful driver update
            transaction.payment_status = "Completed"
            transaction.save(ignore_permissions=True)
            
            # EXPLICIT COMMIT: Commit the transaction and balance update immediately
            frappe.db.commit()

        except Exception as inner_error:
            frappe.db.rollback(save_point=savepoint)
            raise inner_error

        # CRITICAL FIX: Send payment to driver ONLY ONCE after successful database operations
        # Skip B2C payment for adjustment and driver repayment transactions
        payment_success = False
        if transaction_type not in ['Adjustment', 'Driver Repayment']:
            # Determine if instant payout is enabled (driver override takes precedence over global)
            instant_global = frappe.get_single("TukTuk Settings").get("instant_payouts_enabled") or 0
            driver_pref = (driver.get("instant_payout_override")
                           if hasattr(driver, "get") else getattr(driver, "instant_payout_override", None))
            # Normalize preference
            # Values: None/"Follow Global", "Enable", "Disable"
            should_instant_payout = False
            if driver_pref == "Enable":
                should_instant_payout = True
            elif driver_pref == "Disable":
                should_instant_payout = False
            else:
                should_instant_payout = bool(instant_global)

            if not should_instant_payout:
                # No instant payout: record only; mark as not sent
                frappe.db.set_value("TukTuk Transaction", transaction.name,
                                    "b2c_payment_sent", 0, update_modified=False)
                frappe.log_error("Instant Payout Disabled",
                                 f"Skipping B2C for {transaction_id}; driver_pref={driver_pref}, global={instant_global}")
                frappe.db.commit()
                return {"ResultCode": "0", "ResultDesc": "Success"}

            # Check if B2C payment was already attempted for this transaction
            b2c_already_sent = frappe.db.get_value("TukTuk Transaction",
                                                    transaction.name,
                                                    "b2c_payment_sent")

            if not b2c_already_sent:
                try:
                    # Mark B2C as sent BEFORE making the API call to prevent race conditions
                    frappe.db.set_value("TukTuk Transaction", transaction.name,
                                       "b2c_payment_sent", 1, update_modified=False)
                    frappe.db.commit()

                    if send_mpesa_payment(driver.mpesa_number, driver_share, "FARE"):
                        payment_success = True
                        frappe.log_error("M-Pesa Payment Success",
                                       f"Sent {driver_share} KSH to driver {driver.driver_name}")
                    else:
                        frappe.log_error("M-Pesa Payment Failed",
                                       f"Failed to send {driver_share} KSH to driver {driver.driver_name}")
                except Exception as payment_error:
                    frappe.log_error("M-Pesa B2C Error", f"B2C payment failed: {str(payment_error)}")

                # Update transaction with payment result
                if not payment_success:
                    transaction.add_comment('Comment', 'Driver payment failed but transaction recorded')
                    transaction.save(ignore_permissions=True)
            else:
                frappe.log_error("Duplicate B2C Prevention",
                               f"B2C payment already sent for transaction {transaction_id}. Skipping duplicate.")
        else:
            # For adjustment and driver repayment transactions, mark as completed without B2C payment
            frappe.db.set_value("TukTuk Transaction", transaction.name,
                               "b2c_payment_sent", 1, update_modified=False)
            payment_success = True
            
            # Add special comment for driver repayments
            if is_driver_repayment:
                transaction.add_comment('Comment', f'Driver repayment received: {amount} KSH - No B2C payment sent')
                transaction.save(ignore_permissions=True)
        
        frappe.db.commit()
        frappe.log_error("M-Pesa Transaction Success", 
                        f"Transaction {transaction_id} processed successfully")
        
        return {"ResultCode": "0", "ResultDesc": "Success"}
        
    except Exception as e:
        frappe.log_error(f"M-Pesa Confirmation Error: {str(e)}")
        return {"ResultCode": "0", "ResultDesc": "Success"}
    finally:
        # Reset ignore permissions flag
        frappe.flags.ignore_permissions = False

# Alternative endpoints without "mpesa" in URL (for Daraja compatibility)
@frappe.whitelist(allow_guest=True)
def payment_validation(**kwargs):
    """Alternative validation endpoint without 'mpesa' in URL"""
    return mpesa_validation(**kwargs)

@frappe.whitelist(allow_guest=True) 
def payment_confirmation(**kwargs):
    """Alternative confirmation endpoint - prevents duplicates"""
    transaction_id = kwargs.get('TransID', 'unknown')
    
    # Check if already processed by either endpoint
    if frappe.db.exists("TukTuk Transaction", {"transaction_id": transaction_id}):
        frappe.log_error("Duplicate Endpoint Call Prevented", 
                        f"Transaction {transaction_id} already processed via mpesa_confirmation")
        return {"ResultCode": "0", "ResultDesc": "Success"}
    
    # If not processed, call the main function
    return mpesa_confirmation(**kwargs)

# ===== MANUAL ADJUSTMENT TRANSACTIONS =====

@frappe.whitelist()
def create_adjustment_transaction(driver, tuktuk, amount, description):
    """
    Create a manual adjustment transaction for overpayment corrections
    
    Args:
        driver: Driver name/ID
        tuktuk: TukTuk vehicle name/ID  
        amount: Adjustment amount (negative for overpayments)
        description: Reason for adjustment
    
    Returns:
        dict: Transaction details
    """
    try:
        # Validate inputs
        if not driver or not tuktuk or not amount:
            frappe.throw("Driver, TukTuk, and amount are required")
        
        # Convert amount to float for proper handling
        try:
            amount = float(amount)
        except (ValueError, TypeError):
            frappe.throw("Invalid amount format. Please enter a valid number.")
        
        if amount == 0:
            frappe.throw("Adjustment amount cannot be zero")
        
        # Get driver and tuktuk documents
        driver_doc = frappe.get_doc("TukTuk Driver", driver)
        tuktuk_doc = frappe.get_doc("TukTuk Vehicle", tuktuk)
        
        # Generate unique transaction ID
        timestamp = frappe.utils.now_datetime().strftime("%Y%m%d%H%M%S")
        transaction_id = f"ADJ-{timestamp}-{driver}"
        
        # Create adjustment transaction
        transaction = frappe.get_doc({
            "doctype": "TukTuk Transaction",
            "transaction_id": transaction_id,
            "transaction_type": "Adjustment",
            "tuktuk": tuktuk,
            "driver": driver,
            "amount": abs(amount),  # Store as positive amount
            "driver_share": 0,  # No payment to driver
            "target_contribution": 0,  # No target credit
            "customer_phone": "ADJUSTMENT",
            "timestamp": frappe.utils.now_datetime(),
            "payment_status": "Completed",
            "b2c_payment_sent": 1  # Prevent any accidental payment triggers
        })
        
        transaction.insert(ignore_permissions=True)
        
        # Add comment explaining the adjustment
        transaction.add_comment('Comment', f"Manual adjustment: {description}")
        
        frappe.db.commit()
        
        frappe.log_error("Adjustment Transaction Created",
                        f"Created adjustment transaction {transaction_id} for driver {driver_doc.driver_name}: {amount} KSH - {description}")
        
        return {
            "success": True,
            "transaction_id": transaction_id,
            "message": f"Adjustment transaction created successfully. Transaction ID: {transaction_id}"
        }
        
    except Exception as e:
        frappe.log_error(f"Adjustment Transaction Error: {str(e)}")
        frappe.throw(f"Failed to create adjustment transaction: {str(e)}")

@frappe.whitelist()
def process_uncaptured_payment(driver, tuktuk, transaction_id, customer_phone, amount, action_type):
    """
    Process uncaptured payments (payments sent to wrong account numbers)
    
    Args:
        driver: Driver name/ID
        tuktuk: TukTuk vehicle name/ID
        transaction_id: M-Pesa transaction code
        customer_phone: Customer phone number
        amount: Payment amount
        action_type: 'send_share' or 'deposit_share'
    
    Returns:
        dict: Processing result
    """
    try:
        # Validate inputs
        if not driver or not tuktuk or not transaction_id or not amount:
            frappe.throw("Driver, TukTuk, transaction ID, and amount are required")
        
        if action_type not in ['send_share', 'deposit_share']:
            frappe.throw("Invalid action type. Must be 'send_share' or 'deposit_share'")
        
        # Convert amount to float
        try:
            amount = float(amount)
        except (ValueError, TypeError):
            frappe.throw("Invalid amount format. Please enter a valid number.")
        
        if amount <= 0:
            frappe.throw("Amount must be greater than zero")
        
        # Check for duplicate transaction ID
        if frappe.db.exists("TukTuk Transaction", {"transaction_id": transaction_id}):
            frappe.throw(f"Transaction ID {transaction_id} already exists in the system")
        
        # Get driver and tuktuk documents
        driver_doc = frappe.get_doc("TukTuk Driver", driver)
        tuktuk_doc = frappe.get_doc("TukTuk Vehicle", tuktuk)
        
        # Get settings for fare percentage and target
        settings = frappe.get_single("TukTuk Settings")
        percentage = driver_doc.fare_percentage or settings.global_fare_percentage
        target = driver_doc.daily_target or settings.global_daily_target
        
        # Check if target sharing is enabled
        driver_target_override = getattr(driver_doc, 'target_sharing_override', 'Follow Global')
        if driver_target_override == 'Enable':
            target_sharing_enabled = True
        elif driver_target_override == 'Disable':
            target_sharing_enabled = False
        else:
            target_sharing_enabled = getattr(settings, 'enable_target_sharing', 1)
        
        if action_type == 'send_share':
            # Calculate driver share and target contribution
            if target_sharing_enabled and driver_doc.current_balance >= target:
                driver_share = amount  # 100% to driver when target met
                target_contribution = 0
            else:
                driver_share = amount * (percentage / 100)
                target_contribution = amount - driver_share
            
            # Create transaction with type "Payment"
            transaction = frappe.get_doc({
                "doctype": "TukTuk Transaction",
                "transaction_id": transaction_id,
                "transaction_type": "Payment",
                "tuktuk": tuktuk,
                "driver": driver,
                "amount": amount,
                "driver_share": driver_share,
                "target_contribution": target_contribution,
                "customer_phone": customer_phone,
                "timestamp": frappe.utils.now_datetime(),
                "payment_status": "Pending",
                "b2c_payment_sent": 0
            })
            
            transaction.insert(ignore_permissions=True)
            
            # Add comment explaining this is an uncaptured payment
            transaction.add_comment('Comment', 
                f"Uncaptured payment - sent to wrong account. Customer: {customer_phone}")
            
            # ATOMIC UPDATE FIX: Use SQL UPDATE to prevent race conditions
            if target_contribution > 0:
                global_target = settings.global_daily_target or 0
                frappe.db.sql("""
                    UPDATE `tabTukTuk Driver`
                    SET current_balance = current_balance + %s
                    WHERE name = %s
                """, (target_contribution, driver))
                
                # Also update left_to_target atomically
                frappe.db.sql("""
                    UPDATE `tabTukTuk Driver`
                    SET left_to_target = GREATEST(0, 
                        COALESCE(NULLIF(daily_target, 0), %s) - current_balance
                    )
                    WHERE name = %s
                """, (global_target, driver))
            
            # Commit before sending B2C payment
            frappe.db.commit()
            
            # Send B2C payment to driver
            payment_success = False
            try:
                frappe.db.set_value("TukTuk Transaction", transaction.name,
                                   "b2c_payment_sent", 1, update_modified=False)
                frappe.db.commit()
                
                if send_mpesa_payment(driver_doc.mpesa_number, driver_share, "FARE"):
                    payment_success = True
                    transaction.payment_status = "Completed"
                    transaction.save(ignore_permissions=True)
                    frappe.db.commit()
                    
                    frappe.log_error("Uncaptured Payment - B2C Success",
                                   f"Sent {driver_share} KSH to driver {driver_doc.driver_name} for transaction {transaction_id}")
                else:
                    transaction.add_comment('Comment', 'B2C payment failed on initial attempt')
                    transaction.save(ignore_permissions=True)
                    frappe.db.commit()
                    
                    frappe.log_error("Uncaptured Payment - B2C Failed",
                                   f"Failed to send {driver_share} KSH to driver {driver_doc.driver_name} for transaction {transaction_id}")
            except Exception as payment_error:
                frappe.log_error("Uncaptured Payment - B2C Error", 
                               f"B2C payment error: {str(payment_error)}")
            
            result_message = f"Transaction recorded successfully. Transaction ID: {transaction_id}\n"
            result_message += f"Driver Share: KSH {driver_share:.2f}\n"
            result_message += f"Target Contribution: KSH {target_contribution:.2f}\n"
            if payment_success:
                result_message += "B2C payment sent to driver."
            else:
                result_message += "WARNING: B2C payment failed. Transaction recorded but payment not sent."
            
            return {
                "success": True,
                "transaction_id": transaction_id,
                "message": result_message,
                "payment_sent": payment_success
            }
            
        else:  # action_type == 'deposit_share'
            # Create adjustment transaction with full amount as target contribution
            transaction = frappe.get_doc({
                "doctype": "TukTuk Transaction",
                "transaction_id": transaction_id,
                "transaction_type": "Adjustment",
                "tuktuk": tuktuk,
                "driver": driver,
                "amount": amount,
                "driver_share": 0,  # No payment to driver
                "target_contribution": amount,  # Full amount to balance
                "customer_phone": customer_phone,
                "timestamp": frappe.utils.now_datetime(),
                "payment_status": "Completed",
                "b2c_payment_sent": 1  # Prevent payment triggers
            })
            
            transaction.insert(ignore_permissions=True)
            
            # Add comment explaining this is an uncaptured payment deposited to balance
            transaction.add_comment('Comment', 
                f"Uncaptured payment deposited to balance - sent to wrong account. Customer: {customer_phone}")
            
            # ATOMIC UPDATE FIX: Use SQL UPDATE to prevent race conditions
            old_balance = driver_doc.current_balance
            global_target = settings.global_daily_target or 0
            frappe.db.sql("""
                UPDATE `tabTukTuk Driver`
                SET current_balance = current_balance + %s
                WHERE name = %s
            """, (amount, driver))
            
            # Also update left_to_target atomically
            frappe.db.sql("""
                UPDATE `tabTukTuk Driver`
                SET left_to_target = GREATEST(0, 
                    COALESCE(NULLIF(daily_target, 0), %s) - current_balance
                )
                WHERE name = %s
            """, (global_target, driver))
            
            frappe.db.commit()
            
            # Get new balance after update
            new_balance = frappe.db.get_value("TukTuk Driver", driver, "current_balance")
            
            frappe.log_error("Uncaptured Payment - Deposited",
                           f"Deposited {amount} KSH to driver {driver_doc.driver_name}'s balance for transaction {transaction_id}. Balance: {old_balance} → {new_balance}")
            
            return {
                "success": True,
                "transaction_id": transaction_id,
                "message": f"Transaction recorded successfully. Transaction ID: {transaction_id}\nFull amount (KSH {amount:.2f}) added to driver's target balance.\nNew Balance: KSH {new_balance:.2f}"
            }
        
    except Exception as e:
        frappe.log_error(f"Uncaptured Payment Error: {str(e)}")
        return {
            "success": False,
            "error": f"Failed to process uncaptured payment: {str(e)}"
        }

# ===== ENHANCED PAYMENT HANDLING WITH DEPOSITS =====

def handle_mpesa_payment_with_deposit(doc, method):
    """Enhanced handle incoming Mpesa payments with deposit integration"""
    
    # Skip processing for adjustment and driver repayment transactions
    if doc.transaction_type in ['Adjustment', 'Driver Repayment']:
        return
    
    if not doc.tuktuk:
        frappe.throw("No TukTuk specified for payment")
        
    if not doc.amount or doc.amount <= 0:
        frappe.throw("Invalid payment amount")
        
    if not is_within_operating_hours():
        doc.payment_status = "Failed"
        doc.add_comment('Comment', 'Payment rejected: Outside operating hours')
        doc.save()
        return
        
    settings = frappe.get_single("TukTuk Settings")
    
    try:
        driver = frappe.get_all(
            "TukTuk Driver",
            filters={"assigned_tuktuk": doc.tuktuk},
            fields=["driver_national_id", "mpesa_number", "current_balance",
                   "daily_target", "fare_percentage", "allow_target_deduction_from_deposit",
                   "current_deposit_balance"],
            limit=1
        )
        
        if not driver:
            doc.payment_status = "Failed"
            doc.add_comment('Comment', 'Payment failed: No driver assigned to TukTuk')
            doc.save()
            return
            
        driver_doc = frappe.get_doc("TukTuk Driver", {
            "driver_national_id": driver[0].driver_national_id
        })
        
        amount = doc.amount
        percentage = driver_doc.fare_percentage or settings.global_fare_percentage
        target = driver_doc.daily_target or settings.global_daily_target

        # Check if target sharing is enabled (driver override takes precedence)
        driver_target_override = getattr(driver_doc, 'target_sharing_override', 'Follow Global')
        if driver_target_override == 'Enable':
            target_sharing_enabled = True
        elif driver_target_override == 'Disable':
            target_sharing_enabled = False
        else:
            target_sharing_enabled = getattr(settings, 'enable_target_sharing', 1)

        # Calculate shares based on target status and target sharing setting
        if target_sharing_enabled and driver_doc.current_balance >= target:
            doc.driver_share = amount  # 100% to driver when target met AND target sharing enabled
            doc.target_contribution = 0
        else:
            # Always use percentage sharing when target not met OR target sharing disabled
            doc.driver_share = amount * (percentage / 100)
            doc.target_contribution = amount - doc.driver_share  # Target contribution always calculated
            
        # Process driver payment using enhanced Daraja integration
        if send_mpesa_payment(driver_doc.mpesa_number, doc.driver_share):
            if doc.target_contribution:
                driver_doc.current_balance += doc.target_contribution
            
            doc.payment_status = "Completed"
            doc.save()
            driver_doc.save()
            
            # Check battery level after successful transaction
            tuktuk = frappe.get_doc("TukTuk Vehicle", doc.tuktuk)
            check_battery_level(tuktuk)
        else:
            doc.payment_status = "Failed"
            doc.add_comment('Comment', 'Driver payment failed')
            doc.save()
            
    except Exception as e:
        frappe.log_error(f"Payment Processing Failed: {str(e)}")
        doc.payment_status = "Failed"
        doc.add_comment('Comment', f'Payment processing error: {str(e)}')
        doc.save()

def handle_mpesa_payment(doc, method):
    """Standard handle incoming Mpesa payments"""
    return handle_mpesa_payment_with_deposit(doc, method)

# ===== RENTAL FUNCTIONS =====

def get_tuktuk_for_rental():
    """Get available tuktuk for rental"""
    return frappe.get_all(
        "TukTuk Vehicle",
        filters={
            "status": "Available",
            "battery_level": [">", 20]  # Only return tuktuks with sufficient battery
        },
        fields=["tuktuk_id", "rental_rate_initial", "rental_rate_hourly", 
                "battery_level"]
    )

def start_rental(driver_id, tuktuk_id, start_time):
    """Start a tuktuk rental"""
    settings = frappe.get_single("TukTuk Settings")
    
    # Get the actual TukTuk document
    tuktuk = frappe.get_doc("TukTuk Vehicle", {"tuktuk_id": tuktuk_id})
    if tuktuk.status != "Available":
        frappe.throw(f"TukTuk {tuktuk_id} is not available for rental")
    
    # Get driver
    driver = frappe.get_doc("TukTuk Driver", driver_id)
    
    # Calculate rental fee
    initial_fee = tuktuk.rental_rate_initial or settings.global_rental_initial
    
    # Create rental record
    rental = frappe.get_doc({
        "doctype": "TukTuk Rental",
        "driver": driver.name,
        "rented_tuktuk": tuktuk.name,
        "start_time": start_time,
        "rental_fee": initial_fee,
        "status": "Active"
    })
    
    rental.insert()
    
    # Update TukTuk status
    tuktuk.status = "Rented"
    tuktuk.save()
    
    return rental

def end_rental(rental_id, end_time):
    """End a tuktuk rental"""
    rental = frappe.get_doc("TukTuk Rental", rental_id)
    settings = frappe.get_single("TukTuk Settings")
    
    # Calculate total rental time
    start_datetime = get_datetime(rental.start_time)
    end_datetime = get_datetime(end_time)
    
    total_hours = (end_datetime - start_datetime).total_seconds() / 3600
    
    # Calculate final fee
    tuktuk = frappe.get_doc("TukTuk Vehicle", rental.rented_tuktuk)
    initial_rate = tuktuk.rental_rate_initial or settings.global_rental_initial
    hourly_rate = tuktuk.rental_rate_hourly or settings.global_rental_hourly
    
    if total_hours <= 2:
        final_fee = initial_rate
    else:
        additional_hours = total_hours - 2
        final_fee = initial_rate + (additional_hours * hourly_rate)
    
    # Update rental
    rental.end_time = end_time
    rental.rental_fee = final_fee
    rental.status = "Completed"
    rental.save()
    
    # Update TukTuk status
    tuktuk.status = "Available"
    tuktuk.save()
    
    return rental

# ===== VALIDATION FUNCTIONS =====

def validate_driver(doc, method):
    """Validate driver data"""
    validate_mpesa_number(doc)
    
    # Validate national ID uniqueness
    if frappe.db.exists("TukTuk Driver", {"driver_national_id": doc.driver_national_id, "name": ["!=", doc.name]}):
        frappe.throw("Driver with this National ID already exists")
    
    # Validate emergency contact phone
    if doc.driver_emergency_phone:
        pattern = r'^(?:\+254|254|0)\d{9}$'
        if not re.match(pattern, doc.driver_emergency_phone.replace(' ', '')):
            frappe.throw("Invalid emergency contact phone number format")

def validate_vehicle(doc, method):
    """Validate TukTuk Vehicle document"""
    # More flexible validation - don't require strict format initially
    if not doc.tuktuk_id:
        frappe.throw("TukTuk ID is required")
    
    # Validate mpesa account number (should be 3 digits) - only if provided
    if doc.mpesa_account and not re.match(r'^\d{3}$', doc.mpesa_account):
        frappe.throw("Mpesa account must be 3 digits")
    
    # Convert battery_level to float before comparison
    if doc.battery_level:
        try:
            battery_level = float(doc.battery_level)
            if battery_level < 0 or battery_level > 100:
                frappe.throw("Battery level must be between 0 and 100")
        except ValueError:
            frappe.throw("Battery level must be a number between 0 and 100")
    
    # Validate rental rates if set
    if doc.rental_rate_initial and doc.rental_rate_initial < 0:
        frappe.throw("Initial rental rate must not be negative")
    if doc.rental_rate_hourly and doc.rental_rate_hourly < 0:
        frappe.throw("Hourly rental rate must not be negative")

def handle_driver_update(doc, method):
    """Handle updates to driver record"""
    if hasattr(doc, 'get_old_value') and doc.has_value_changed('assigned_tuktuk'):
        # Clear old assignment
        old_tuktuk = doc.get_old_value('assigned_tuktuk')
        if old_tuktuk:
            try:
                old_tuktuk_doc = frappe.get_doc("TukTuk Vehicle", old_tuktuk)
                old_tuktuk_doc.status = "Available"
                old_tuktuk_doc.save()
            except Exception as e:
                frappe.log_error("Driver Update Error", f"Error clearing old tuktuk assignment: {str(e)}")
            
        # Set new assignment
        if doc.assigned_tuktuk:
            try:
                new_tuktuk = frappe.get_doc("TukTuk Vehicle", doc.assigned_tuktuk)
                if new_tuktuk.status != "Available":
                    frappe.throw(f"TukTuk {doc.assigned_tuktuk} is not available for assignment")
                
                # CRITICAL FIX: Check if tuktuk is already assigned to another driver
                existing_driver = frappe.db.get_value(
                    "TukTuk Driver",
                    {"assigned_tuktuk": doc.assigned_tuktuk, "name": ["!=", doc.name]},
                    "name"
                )
                if existing_driver:
                    existing_driver_name = frappe.db.get_value("TukTuk Driver", existing_driver, "driver_name")
                    frappe.throw(f"TukTuk {doc.assigned_tuktuk} is already assigned to driver {existing_driver_name}")
                
                new_tuktuk.status = "Assigned"
                new_tuktuk.save()
            except Exception as e:
                frappe.log_error("Driver Update Error", f"Error setting new tuktuk assignment: {str(e)}")

def handle_vehicle_status_change(doc, method):
    """Handle TukTuk Vehicle status changes"""
    if doc.has_value_changed('status'):
        if doc.status == "Charging":
            # Check if driver is assigned
            driver = frappe.get_all(
                "TukTuk Driver",
                filters={"assigned_tuktuk": doc.name},
                fields=["name", "driver_name"]
            )
            if driver:
                # Log the charging event
                frappe.get_doc({
                    "doctype": "Comment",
                    "comment_type": "Info",
                    "reference_doctype": "TukTuk Vehicle",
                    "reference_name": doc.name,
                    "content": f"TukTuk entered charging state. Driver can rent another vehicle if needed."
                }).insert()

# ===== DAILY OPERATIONS =====

def reset_daily_targets_with_deposit():
    """Enhanced reset daily targets with deposit deduction option"""
    
    # SAFETY CHECK #1: Don't run during migrations or installations
    if frappe.flags.in_migrate or frappe.flags.in_install or frappe.flags.in_patch:
        frappe.log_error(
            "Skipping daily target reset - system is in migration/installation mode",
            "Target Reset - Skipped"
        )
        return
    
    # SAFETY CHECK #2: Prevent multiple resets on the same day
    today = frappe.utils.today()
    last_reset_date = frappe.db.get_single_value("TukTuk Settings", "last_daily_reset_date")
    
    if last_reset_date and str(last_reset_date) == today:
        frappe.log_error(
            f"Skipping daily target reset - already ran today ({today}). Last reset: {last_reset_date}",
            "Target Reset - Already Run"
        )
        return
    
    settings = frappe.get_single("TukTuk Settings")
    
    # Log the start of the reset process
    frappe.log_error(
        f"Starting daily target reset for date: {today}\n"
        f"Last reset was on: {last_reset_date or 'Never'}\n"
        f"Global daily target: {settings.global_daily_target or 0}\n"
        f"Target sharing enabled: {getattr(settings, 'enable_target_sharing', 1)}",
        "Target Reset - Started"
    )
    
    # Daily reset runs at midnight regardless of operating hours
    # Operating hours are checked for other operations, not for end-of-day processing
        
    drivers = frappe.get_all("TukTuk Driver", 
                            filters={"assigned_tuktuk": ["!=", ""]},
                            fields=["name", "driver_national_id", "driver_name", "current_balance", 
                                   "consecutive_misses", "allow_target_deduction_from_deposit", 
                                   "current_deposit_balance", "modified"])
    
    processed_count = 0
    terminated_count = 0
    
    for driver in drivers:
        try:
            driver_doc = frappe.get_doc("TukTuk Driver", {
                "driver_national_id": driver.driver_national_id
            })
            target = driver_doc.daily_target or settings.global_daily_target

            # Check if target sharing is enabled for this driver
            driver_target_override = getattr(driver_doc, 'target_sharing_override', 'Follow Global')
            if driver_target_override == 'Enable':
                target_sharing_enabled = True
            elif driver_target_override == 'Disable':
                target_sharing_enabled = False
            else:
                target_sharing_enabled = getattr(settings, 'enable_target_sharing', 1)

            # Store yesterday's balance before processing
            yesterday_balance = driver_doc.current_balance

            # Handle target miss - if driver is assigned and didn't meet target, it's a miss
            if yesterday_balance < target:
                shortfall = target - yesterday_balance
                
                # Driver was assigned a tuktuk and didn't meet target → increment consecutive_misses
                driver_doc.consecutive_misses += 1
                
                # Enhanced logging for target misses
                frappe.log_error(
                    f"Target Miss Recorded:\n"
                    f"Driver: {driver_doc.driver_name} ({driver_doc.name})\n"
                    f"Yesterday Balance: {yesterday_balance} KSH\n"
                    f"Target: {target} KSH\n"
                    f"Shortfall: {shortfall} KSH\n"
                    f"Consecutive Misses: {driver_doc.consecutive_misses}\n"
                    f"Target Sharing Enabled: {target_sharing_enabled}",
                    "Target Miss - Recorded"
                )

                # Only apply penalties when target sharing is enabled
                if target_sharing_enabled:
                    # Check if driver allows deposit deduction for missed targets
                    if (driver_doc.allow_target_deduction_from_deposit and
                        driver_doc.current_deposit_balance >= shortfall):

                        # Log this option for management review
                        frappe.log_error(
                            f"Driver {driver_doc.driver_name} missed target by {shortfall} KSH. "
                            f"Deposit balance: {driver_doc.current_deposit_balance} KSH. "
                            f"Driver allows automatic deduction: {driver_doc.allow_target_deduction_from_deposit}",
                            "Target Miss - Deposit Deduction Available"
                        )

                        # Create a notification for management
                        create_target_miss_notification(driver_doc, shortfall)

                    if driver_doc.consecutive_misses >= 3:
                        frappe.log_error(
                            f"TERMINATING DRIVER:\n"
                            f"Driver: {driver_doc.driver_name} ({driver_doc.name})\n"
                            f"Consecutive Misses: {driver_doc.consecutive_misses}\n"
                            f"Deposit Balance: {driver_doc.current_deposit_balance} KSH",
                            "Target Reset - Driver Termination"
                        )
                        terminate_driver_with_deposit_refund(driver_doc)
                        terminated_count += 1
                    else:
                        # Roll over unmet balance as debt when target sharing enabled
                        driver_doc.current_balance = -shortfall  # Negative balance indicates debt
                else:
                    # When target sharing disabled, just reset balance without penalties
                    driver_doc.current_balance = 0
            else:
                driver_doc.consecutive_misses = 0
                # Pay bonus if enabled and criteria met (only when target sharing is enabled)
                if target_sharing_enabled and settings.bonus_enabled and settings.bonus_amount:
                    if send_mpesa_payment(driver_doc.mpesa_number, settings.bonus_amount, "BONUS"):
                        frappe.msgprint(f"Bonus payment sent to driver {driver_doc.driver_name}")
                driver_doc.current_balance = 0
            
            # Reset the countdown field to full target for the new day
            # Set flag to prevent automatic recalculation in before_save hook
            driver_doc.left_to_target = target
            driver_doc.flags.skip_left_to_target_update = True
                
            driver_doc.save()
            processed_count += 1
            
        except Exception as e:
            frappe.log_error(
                f"Failed to reset targets for driver {driver.driver_national_id}: {str(e)}\n"
                f"Driver Name: {driver.get('driver_name', 'Unknown')}",
                "Target Reset - Driver Error"
            )
    
    # Update the last reset date in settings
    frappe.db.set_value("TukTuk Settings", "TukTuk Settings", "last_daily_reset_date", today)
    frappe.db.commit()
    
    # Log completion summary
    frappe.log_error(
        f"Daily target reset completed for {today}:\n"
        f"Total Drivers Processed: {processed_count}\n"
        f"Drivers Terminated: {terminated_count}\n"
        f"Total Drivers Found: {len(drivers)}",
        "Target Reset - Completed"
    )

def terminate_driver_with_deposit_refund(driver):
    """Enhanced terminate driver and process deposit refund"""
    try:
        if driver.assigned_tuktuk:
            tuktuk = frappe.get_doc("TukTuk Vehicle", driver.assigned_tuktuk)
            tuktuk.status = "Available"
            tuktuk.save()
        
        # Process exit and refund
        driver.process_exit_refund()
        
        # Notify management
        frappe.sendmail(
            recipients=["yuda@sunnytuktuk.com"],
            subject=f"Driver Termination: {driver.driver_name}",
            message=f"""
            Driver {driver.driver_name} has been terminated due to consecutive target misses.
            
            Deposit Refund Details:
            - Original Deposit: {driver.initial_deposit_amount} KSH
            - Final Balance: {driver.current_deposit_balance} KSH
            - Refund Amount: {driver.refund_amount} KSH
            - Refund Status: {driver.refund_status}
            
            Please process the refund payment to the driver's registered Mpesa number.
            """
        )
        
    except Exception as e:
        frappe.log_error(f"Driver termination failed: {str(e)}")
        frappe.throw("Failed to process driver termination")

def create_target_miss_notification(driver_doc, shortfall):
    """Create notification for target miss with deposit deduction option"""
    try:
        notification = frappe.get_doc({
            "doctype": "Notification Log",
            "subject": f"Target Miss - Deposit Deduction Available: {driver_doc.driver_name}",
            "email_content": f"""
            Driver {driver_doc.driver_name} has missed their daily target.
            
            Details:
            - Shortfall: {shortfall} KSH
            - Available Deposit: {driver_doc.current_deposit_balance} KSH
            - Driver Allows Auto-Deduction: {'Yes' if driver_doc.allow_target_deduction_from_deposit else 'No'}
            - Consecutive Misses: {driver_doc.consecutive_misses}
            
            Action Required: Review and approve deposit deduction if appropriate.
            """,
            "document_type": "TukTuk Driver",
            "document_name": driver_doc.name,
            "for_user": "Administrator"
        })
        notification.insert()
    except Exception as e:
        frappe.log_error(f"Failed to create target miss notification: {str(e)}")

def start_operating_hours():
    """Start of operating hours tasks"""
    try:
        frappe.db.set_value("TukTuk Settings", None, "system_active", 1)
        
        # Reset any stalled statuses from previous day
        vehicles = frappe.get_all("TukTuk Vehicle", 
                                # filters={"status": ["in", ["Charging", "Assigned"]]})
                                filters={"status": ["in", ["Charging"]]})
        for vehicle in vehicles:
            tuktuk = frappe.get_doc("TukTuk Vehicle", vehicle.name)
            if not frappe.db.exists("TukTuk Rental", {"rented_tuktuk": tuktuk.name, "status": "Active"}):
                tuktuk.status = "Available"
                tuktuk.save()
                
        frappe.db.commit()
    except Exception as e:
        frappe.log_error(f"Error in start_operating_hours: {str(e)}")

def end_operating_hours():
    """End of operating hours tasks"""
    try:
        frappe.db.set_value("TukTuk Settings", None, "system_active", 0)
        
        # Generate end of day report
        generate_daily_reports()
        frappe.db.commit()
    except Exception as e:
        frappe.log_error(f"Error in end_operating_hours: {str(e)}")

def generate_daily_reports():
    """Generate daily operational reports"""
    try:
        # Report date is today (the day that just ended at midnight EAT)
        report_date = frappe.utils.today()
        # Use SQL for date-based aggregation to avoid datetime filter issues
        # Query for today's data (the day that just completed)
        total_revenue = frappe.db.sql("""
            SELECT COALESCE(SUM(amount), 0) as revenue
            FROM `tabTukTuk Transaction`
            WHERE DATE(timestamp) = CURDATE()
            AND transaction_type NOT IN ('Adjustment', 'Driver Repayment')
            AND payment_status = 'Completed'
        """, as_dict=True)[0].revenue

        total_driver_payments = frappe.db.sql("""
            SELECT COALESCE(SUM(driver_share), 0) as driver_payments
            FROM `tabTukTuk Transaction`
            WHERE DATE(timestamp) = CURDATE()
            AND transaction_type NOT IN ('Adjustment', 'Driver Repayment')
            AND payment_status = 'Completed'
        """, as_dict=True)[0].driver_payments

        total_target_contributions = frappe.db.sql("""
            SELECT COALESCE(SUM(target_contribution), 0) as target_contrib
            FROM `tabTukTuk Transaction`
            WHERE DATE(timestamp) = CURDATE()
            AND transaction_type NOT IN ('Adjustment', 'Driver Repayment')
            AND payment_status = 'Completed'
        """, as_dict=True)[0].target_contrib

        # Get driver performance using configured global target (fallback to 3000)
        settings = frappe.get_single("TukTuk Settings")
        target_threshold = settings.global_daily_target or 3000

        # Calculate drivers at target based on actual transactions for today
        # (Note: This runs AFTER daily reset, so current_balance is already 0)
        # Sum up target_contribution per driver for today
        drivers_performance = frappe.db.sql("""
            SELECT 
                driver,
                SUM(target_contribution) as daily_total
            FROM `tabTukTuk Transaction`
            WHERE DATE(timestamp) = CURDATE()
            AND transaction_type NOT IN ('Adjustment', 'Driver Repayment')
            AND payment_status = 'Completed'
            GROUP BY driver
            HAVING daily_total >= %s
        """, (target_threshold,), as_dict=True)
        
        drivers_at_target = len(drivers_performance)
        
        # Total drivers for rate calculation (count drivers who had transactions today)
        total_drivers_query = frappe.db.sql("""
            SELECT COUNT(DISTINCT driver) as cnt
            FROM `tabTukTuk Transaction`
            WHERE DATE(timestamp) = CURDATE()
            AND transaction_type NOT IN ('Adjustment', 'Driver Repayment')
        """, as_dict=True)
        
        total_drivers = total_drivers_query[0].cnt if total_drivers_query[0].cnt > 0 else 1
        
        # Transaction count for report date (excluding adjustments/repayments)
        transaction_count = frappe.db.sql("""
            SELECT COUNT(*) as cnt
            FROM `tabTukTuk Transaction`
            WHERE DATE(timestamp) = CURDATE()
            AND transaction_type NOT IN ('Adjustment', 'Driver Repayment')
        """, as_dict=True)[0].cnt
        
        # Count inactive drivers (not assigned to any tuktuk)
        inactive_drivers = frappe.db.count("TukTuk Driver", {
            "assigned_tuktuk": ["in", ["", None]]
        })
        
        # Count drivers needing attention
        # Drivers who did not meet their daily target
        # Use each driver's individual target or fall back to global target
        # Include all assigned drivers, even those with 0 transactions
        drivers_below_target_data = frappe.db.sql("""
            SELECT 
                d.name as driver,
                COALESCE(SUM(t.target_contribution), 0) as daily_total,
                COALESCE(d.daily_target, %s) as driver_target
            FROM `tabTukTuk Driver` d
            LEFT JOIN `tabTukTuk Transaction` t 
                ON d.name = t.driver 
                AND DATE(t.timestamp) = CURDATE()
                AND t.transaction_type NOT IN ('Adjustment', 'Driver Repayment')
                AND t.payment_status = 'Completed'
            WHERE d.assigned_tuktuk IS NOT NULL 
            AND d.assigned_tuktuk != ''
            GROUP BY d.name, d.daily_target
            HAVING daily_total < driver_target
        """, (target_threshold,), as_dict=True)
        
        drivers_below_target = len(drivers_below_target_data)
        drivers_below_target_list = [d.driver for d in drivers_below_target_data]
        
        # Drivers with consecutive misses >= 2
        drivers_at_risk_data = frappe.get_all("TukTuk Driver", 
            filters={
                "consecutive_misses": [">=", 2],
                "assigned_tuktuk": ["!=", ""]
            },
            fields=["name"]
        )
        drivers_at_risk = len(drivers_at_risk_data)
        drivers_at_risk_list = [d.name for d in drivers_at_risk_data]

        report = f"""
📊 SUNNY TUKTUK DAILY REPORT - {report_date}

💰 FINANCIAL SUMMARY:
- Total Revenue: {total_revenue:,.0f} KSH
- Driver Payments: {total_driver_payments:,.0f} KSH
- Target Contributions: {total_target_contributions:,.0f} KSH
- Transaction Count: {transaction_count}

👥 DRIVER PERFORMANCE:
- Drivers at Target: {drivers_at_target}
- Target Achievement Rate: {drivers_at_target/total_drivers*100:.1f}%
- Inactive Drivers: {inactive_drivers}

⚠️ NEEDS ATTENTION:
- Drivers who did not meet target: {drivers_below_target}
- Drivers with consecutive misses (≥2): {drivers_at_risk}

🚗 FLEET STATUS:
- Active TukTuks: {frappe.db.count('TukTuk Vehicle', {'status': 'Assigned'})}
- Available TukTuks: {frappe.db.count('TukTuk Vehicle', {'status': 'Available'})}
- Charging TukTuks: {frappe.db.count('TukTuk Vehicle', {'status': 'Charging'})}
        """
        
        # Email report to management
        frappe.sendmail(
            recipients=["yuda@sunnytuktuk.com"],
            subject=f"Daily Operations Report - {report_date}",
            message=report
        )
        
        # Save report to database for historical tracking
        try:
            # Check if report already exists for this date
            existing_report = frappe.db.exists("TukTuk Daily Report", {"report_date": report_date})
            
            if existing_report:
                # Update existing report
                daily_report = frappe.get_doc("TukTuk Daily Report", existing_report)
            else:
                # Create new report
                daily_report = frappe.new_doc("TukTuk Daily Report")
                daily_report.report_date = report_date
            
            # Set all the fields
            daily_report.total_revenue = total_revenue
            daily_report.total_driver_share = total_driver_payments
            daily_report.total_target_contribution = total_target_contributions
            daily_report.total_transactions = transaction_count
            daily_report.drivers_at_target = drivers_at_target
            daily_report.total_drivers = total_drivers
            daily_report.target_achievement_rate = (drivers_at_target/total_drivers*100) if total_drivers > 0 else 0
            daily_report.inactive_drivers = inactive_drivers
            daily_report.drivers_below_target = drivers_below_target
            daily_report.drivers_at_risk = drivers_at_risk
            daily_report.active_tuktuks = frappe.db.count('TukTuk Vehicle', {'status': 'Assigned'})
            daily_report.available_tuktuks = frappe.db.count('TukTuk Vehicle', {'status': 'Available'})
            daily_report.charging_tuktuks = frappe.db.count('TukTuk Vehicle', {'status': 'Charging'})
            daily_report.report_text = report
            daily_report.email_sent = 1
            daily_report.email_sent_at = frappe.utils.now()
            
            # Set the driver lists (Long Text fields - comma-separated)
            daily_report.drivers_below_target_list = ", ".join(drivers_below_target_list) if drivers_below_target_list else ""
            daily_report.drivers_at_risk_list = ", ".join(drivers_at_risk_list) if drivers_at_risk_list else ""
            
            daily_report.save(ignore_permissions=True)
            frappe.db.commit()
            
            frappe.log_error("Daily Report Generated and Saved", f"Report saved to database for {report_date}")
            
        except Exception as save_error:
            frappe.log_error(f"Failed to save daily report to database: {str(save_error)}", "Daily Report Save Error")
        
    except Exception as e:
        frappe.log_error(f"Failed to generate daily report: {str(e)}")

@frappe.whitelist()
def test_daily_report(report_date=None):
    """Generate a test daily report for a specific date"""
    try:
        if not report_date:
            report_date = frappe.utils.today()
        
        # Use SQL for date-based aggregation with specific date
        total_revenue = frappe.db.sql("""
            SELECT COALESCE(SUM(amount), 0) as revenue
            FROM `tabTukTuk Transaction`
            WHERE DATE(timestamp) = %s
            AND transaction_type NOT IN ('Adjustment', 'Driver Repayment')
            AND payment_status = 'Completed'
        """, (report_date,), as_dict=True)[0].revenue

        total_driver_payments = frappe.db.sql("""
            SELECT COALESCE(SUM(driver_share), 0) as driver_payments
            FROM `tabTukTuk Transaction`
            WHERE DATE(timestamp) = %s
            AND transaction_type NOT IN ('Adjustment', 'Driver Repayment')
            AND payment_status = 'Completed'
        """, (report_date,), as_dict=True)[0].driver_payments

        total_target_contributions = frappe.db.sql("""
            SELECT COALESCE(SUM(target_contribution), 0) as target_contrib
            FROM `tabTukTuk Transaction`
            WHERE DATE(timestamp) = %s
            AND transaction_type NOT IN ('Adjustment', 'Driver Repayment')
            AND payment_status = 'Completed'
        """, (report_date,), as_dict=True)[0].target_contrib

        # Get driver performance using configured global target (fallback to 3000)
        settings = frappe.get_single("TukTuk Settings")
        target_threshold = settings.global_daily_target or 3000

        # Calculate drivers at target based on actual transactions for that specific date
        # Sum up target_contribution per driver for the report date
        drivers_performance = frappe.db.sql("""
            SELECT 
                driver,
                SUM(target_contribution) as daily_total
            FROM `tabTukTuk Transaction`
            WHERE DATE(timestamp) = %s
            AND transaction_type NOT IN ('Adjustment', 'Driver Repayment')
            AND payment_status = 'Completed'
            GROUP BY driver
            HAVING daily_total >= %s
        """, (report_date, target_threshold), as_dict=True)
        
        drivers_at_target = len(drivers_performance)
        
        # Total drivers for rate calculation (count drivers who had transactions that day)
        total_drivers_query = frappe.db.sql("""
            SELECT COUNT(DISTINCT driver) as cnt
            FROM `tabTukTuk Transaction`
            WHERE DATE(timestamp) = %s
            AND transaction_type NOT IN ('Adjustment', 'Driver Repayment')
        """, (report_date,), as_dict=True)
        
        total_drivers = total_drivers_query[0].cnt if total_drivers_query[0].cnt > 0 else 1
        
        # Transaction count for report date (excluding adjustments/repayments)
        transaction_count = frappe.db.sql("""
            SELECT COUNT(*) as cnt
            FROM `tabTukTuk Transaction`
            WHERE DATE(timestamp) = %s
            AND transaction_type NOT IN ('Adjustment', 'Driver Repayment')
        """, (report_date,), as_dict=True)[0].cnt
        
        # Count inactive drivers (not assigned to any tuktuk)
        inactive_drivers = frappe.db.count("TukTuk Driver", {
            "assigned_tuktuk": ["in", ["", None]]
        })
        
        # Count drivers needing attention
        # Drivers who did not meet their daily target for the specific date
        # Use each driver's individual target or fall back to global target
        # Include all assigned drivers, even those with 0 transactions
        drivers_below_target_data = frappe.db.sql("""
            SELECT 
                d.name as driver,
                COALESCE(SUM(t.target_contribution), 0) as daily_total,
                COALESCE(d.daily_target, %s) as driver_target
            FROM `tabTukTuk Driver` d
            LEFT JOIN `tabTukTuk Transaction` t 
                ON d.name = t.driver 
                AND DATE(t.timestamp) = %s
                AND t.transaction_type NOT IN ('Adjustment', 'Driver Repayment')
                AND t.payment_status = 'Completed'
            WHERE d.assigned_tuktuk IS NOT NULL 
            AND d.assigned_tuktuk != ''
            GROUP BY d.name, d.daily_target
            HAVING daily_total < driver_target
        """, (target_threshold, report_date), as_dict=True)
        
        drivers_below_target = len(drivers_below_target_data)
        drivers_below_target_list = [d.driver for d in drivers_below_target_data]
        
        # Drivers with consecutive misses >= 2 (current status)
        drivers_at_risk_data = frappe.get_all("TukTuk Driver", 
            filters={
                "consecutive_misses": [">=", 2],
                "assigned_tuktuk": ["!=", ""]
            },
            fields=["name"]
        )
        drivers_at_risk = len(drivers_at_risk_data)
        drivers_at_risk_list = [d.name for d in drivers_at_risk_data]

        report = f"""
📊 SUNNY TUKTUK DAILY REPORT - {report_date}

💰 FINANCIAL SUMMARY:
- Total Revenue: {total_revenue:,.0f} KSH
- Driver Payments: {total_driver_payments:,.0f} KSH
- Target Contributions: {total_target_contributions:,.0f} KSH
- Transaction Count: {transaction_count}

👥 DRIVER PERFORMANCE:
- Drivers at Target: {drivers_at_target}
- Target Achievement Rate: {drivers_at_target/total_drivers*100:.1f}%
- Inactive Drivers: {inactive_drivers}

⚠️ NEEDS ATTENTION:
- Drivers who did not meet target: {drivers_below_target}
- Drivers with consecutive misses (≥2): {drivers_at_risk}

🚗 FLEET STATUS:
- Active TukTuks: {frappe.db.count('TukTuk Vehicle', {'status': 'Assigned'})}
- Available TukTuks: {frappe.db.count('TukTuk Vehicle', {'status': 'Available'})}
- Charging TukTuks: {frappe.db.count('TukTuk Vehicle', {'status': 'Charging'})}
        """
        
        frappe.msgprint(f"<pre>{report}</pre>", title=f"Test Daily Report - {report_date}")
        
        return {
            "report_date": report_date,
            "total_revenue": total_revenue,
            "total_driver_payments": total_driver_payments,
            "total_target_contributions": total_target_contributions,
            "transaction_count": transaction_count,
            "drivers_at_target": drivers_at_target,
            "total_drivers": total_drivers,
            "inactive_drivers": inactive_drivers,
            "drivers_below_target": drivers_below_target,
            "drivers_below_target_list": drivers_below_target_list,
            "drivers_at_risk": drivers_at_risk,
            "drivers_at_risk_list": drivers_at_risk_list,
            "report_text": report
        }
        
    except Exception as e:
        frappe.throw(f"Failed to generate test daily report: {str(e)}")

@frappe.whitelist()
def send_daily_report_email(report_date=None, save_to_db=True):
    """Send the daily report email for a specific date"""
    try:
        # Use test_daily_report to get the report data
        report_data = test_daily_report(report_date)
        
        # Send the actual email
        frappe.sendmail(
            recipients=["yuda@sunnytuktuk.com"],
            subject=f"Daily Operations Report - {report_data['report_date']}",
            message=report_data['report_text']
        )
        
        # Save to database if requested
        if save_to_db:
            try:
                # Check if report already exists for this date
                existing_report = frappe.db.exists("TukTuk Daily Report", {"report_date": report_data['report_date']})
                
                if existing_report:
                    # Update existing report
                    daily_report = frappe.get_doc("TukTuk Daily Report", existing_report)
                else:
                    # Create new report
                    daily_report = frappe.new_doc("TukTuk Daily Report")
                    daily_report.report_date = report_data['report_date']
                
                # Set all the fields from report_data
                daily_report.total_revenue = report_data['total_revenue']
                daily_report.total_driver_share = report_data['total_driver_payments']
                daily_report.total_target_contribution = report_data['total_target_contributions']
                daily_report.total_transactions = report_data['transaction_count']
                daily_report.drivers_at_target = report_data['drivers_at_target']
                daily_report.total_drivers = report_data['total_drivers']
                daily_report.target_achievement_rate = (report_data['drivers_at_target']/report_data['total_drivers']*100) if report_data['total_drivers'] > 0 else 0
                daily_report.inactive_drivers = report_data['inactive_drivers']
                daily_report.drivers_below_target = report_data['drivers_below_target']
                daily_report.drivers_at_risk = report_data['drivers_at_risk']
                daily_report.active_tuktuks = frappe.db.count('TukTuk Vehicle', {'status': 'Assigned'})
                daily_report.available_tuktuks = frappe.db.count('TukTuk Vehicle', {'status': 'Available'})
                daily_report.charging_tuktuks = frappe.db.count('TukTuk Vehicle', {'status': 'Charging'})
                daily_report.report_text = report_data['report_text']
                daily_report.email_sent = 1
                daily_report.email_sent_at = frappe.utils.now()
                
                # Set the driver lists (Long Text fields - comma-separated)
                driver_below_list = report_data.get('drivers_below_target_list', [])
                daily_report.drivers_below_target_list = ", ".join(driver_below_list) if driver_below_list else ""
                
                driver_risk_list = report_data.get('drivers_at_risk_list', [])
                daily_report.drivers_at_risk_list = ", ".join(driver_risk_list) if driver_risk_list else ""
                
                daily_report.save(ignore_permissions=True)
                frappe.db.commit()
                
            except Exception as save_error:
                frappe.log_error(f"Failed to save daily report: {str(save_error)}", "Daily Report Save Error")
        
        return {
            "success": True,
            "message": f"Daily report email sent successfully for {report_data['report_date']}",
            "recipient": "yuda@sunnytuktuk.com",
            "saved_to_db": save_to_db
        }
        
    except Exception as e:
        frappe.throw(f"Failed to send daily report email: {str(e)}")

@frappe.whitelist()
def get_historical_daily_reports(from_date=None, to_date=None, limit=30):
    """Get historical daily reports from database"""
    try:
        filters = {}
        if from_date:
            filters["report_date"] = [">=", from_date]
        if to_date:
            if "report_date" in filters:
                filters["report_date"] = ["between", [from_date, to_date]]
            else:
                filters["report_date"] = ["<=", to_date]
        
        reports = frappe.get_all("TukTuk Daily Report",
            filters=filters,
            fields=["name", "report_date", "total_revenue", "total_driver_share", 
                   "total_target_contribution", "total_transactions", "drivers_at_target",
                   "target_achievement_rate", "inactive_drivers", "drivers_below_target",
                   "drivers_at_risk", "active_tuktuks", "email_sent", "email_sent_at"],
            order_by="report_date desc",
            limit=limit
        )
        
        return reports
        
    except Exception as e:
        frappe.throw(f"Failed to retrieve historical reports: {str(e)}")

@frappe.whitelist()
def send_daily_report_to_recipients(report_name, recipients, subject=None):
    """Send a saved daily report to multiple email recipients"""
    try:
        # Get the report document
        report_doc = frappe.get_doc("TukTuk Daily Report", report_name)
        
        if not report_doc.report_text:
            frappe.throw("Report text is empty. Cannot send email.")
        
        # Use provided subject or generate default
        if not subject:
            subject = f"Daily Operations Report - {report_doc.report_date}"
        
        # Ensure recipients is a list
        if isinstance(recipients, str):
            recipients = [email.strip() for email in recipients.split(',') if email.strip()]
        
        # Validate recipients
        if not recipients or len(recipients) == 0:
            frappe.throw("Please provide at least one email recipient.")
        
        # Send email to all recipients
        frappe.sendmail(
            recipients=recipients,
            subject=subject,
            message=report_doc.report_text
        )
        
        # Log the email send
        frappe.log_error(
            f"Daily report emailed to: {', '.join(recipients)}\n"
            f"Report Date: {report_doc.report_date}\n"
            f"Subject: {subject}",
            "Daily Report - Email Sent"
        )
        
        return {
            "success": True,
            "message": f"Report emailed successfully to {len(recipients)} recipient(s)",
            "recipients": recipients,
            "report_date": str(report_doc.report_date)
        }
        
    except Exception as e:
        frappe.log_error(f"Failed to send daily report email: {str(e)}", "Daily Report Email Error")
        frappe.throw(f"Failed to send email: {str(e)}")

# ===== DEPOSIT MANAGEMENT FUNCTIONS =====

@frappe.whitelist()
def get_drivers_with_deposit_info():
    """Get all drivers with their deposit information"""
    drivers = frappe.get_all("TukTuk Driver",
                           fields=["name", "driver_name", "current_deposit_balance", 
                                  "initial_deposit_amount", "allow_target_deduction_from_deposit",
                                  "consecutive_misses", "current_balance"])
    return drivers

@frappe.whitelist()
def bulk_process_target_deductions(driver_list):
    """Process target deductions for multiple drivers"""
    try:
        for driver_name in driver_list:
            driver = frappe.get_doc("TukTuk Driver", driver_name)
            settings = frappe.get_single("TukTuk Settings")
            target = driver.daily_target or settings.global_daily_target

            # Check if target sharing is enabled for this driver
            driver_target_override = getattr(driver, 'target_sharing_override', 'Follow Global')
            if driver_target_override == 'Enable':
                target_sharing_enabled = True
            elif driver_target_override == 'Disable':
                target_sharing_enabled = False
            else:
                target_sharing_enabled = getattr(settings, 'enable_target_sharing', 1)

            if target_sharing_enabled and driver.current_balance < target:
                shortfall = target - driver.current_balance
                if driver.allow_target_deduction_from_deposit and driver.current_deposit_balance >= shortfall:
                    driver.process_target_miss_deduction(shortfall)
                    frappe.msgprint(f"Target deduction processed for {driver.driver_name}")
                    
        frappe.db.commit()
        return True
    except Exception as e:
        frappe.log_error(f"Bulk target deduction failed: {str(e)}")
        return False

@frappe.whitelist()
def generate_deposit_report():
    """Generate comprehensive deposit management report"""
    try:
        drivers = frappe.get_all("TukTuk Driver",
                               fields=["name", "driver_name", "current_deposit_balance", 
                                      "initial_deposit_amount", "consecutive_misses"])
        
        total_deposits = sum(d.current_deposit_balance for d in drivers if d.current_deposit_balance)
        drivers_with_deposits = len([d for d in drivers if d.current_deposit_balance > 0])
        
        report_data = {
            "total_drivers": len(drivers),
            "drivers_with_deposits": drivers_with_deposits,
            "total_deposit_amount": total_deposits,
            "average_deposit": total_deposits / drivers_with_deposits if drivers_with_deposits > 0 else 0,
            "drivers": drivers
        }
        
        return report_data
    except Exception as e:
        frappe.log_error(f"Deposit report generation failed: {str(e)}")
        return {}

@frappe.whitelist()
def process_bulk_refunds(driver_list):
    """Process bulk refunds for multiple drivers"""
    try:
        for driver_name in driver_list:
            driver = frappe.get_doc("TukTuk Driver", driver_name)
            if driver.current_deposit_balance > 0:
                driver.process_driver_exit()
                frappe.msgprint(f"Refund processed for {driver.driver_name}")
                
        frappe.db.commit()
        return True
    except Exception as e:
        frappe.log_error(f"Bulk refund processing failed: {str(e)}")
        return False

@frappe.whitelist()
def restore_driver_termination(driver_name):
    """
    Restore a terminated driver by reversing the termination process.
    Only accessible by System Manager or Tuktuk Manager.
    
    Args:
        driver_name: Name/ID of the TukTuk Driver document
        
    Returns:
        dict: Success status and restoration details
    """
    try:
        # Check permissions - only System Manager or Tuktuk Manager can restore drivers
        user_roles = frappe.get_roles(frappe.session.user)
        if "System Manager" not in user_roles and "Tuktuk Manager" not in user_roles:
            frappe.throw("Access denied. Only System Manager or Tuktuk Manager can restore terminated drivers.")
        
        # Get the driver document
        driver = frappe.get_doc("TukTuk Driver", driver_name)
        
        # Call the restoration method
        result = driver.restore_terminated_driver()
        
        # Commit the changes
        frappe.db.commit()
        
        return result
        
    except Exception as e:
        frappe.log_error(f"Driver restoration failed for {driver_name}: {str(e)}", "Driver Restoration Error")
        frappe.throw(f"Failed to restore driver: {str(e)}")

# ===== SETUP AND MANAGEMENT FUNCTIONS =====

@frappe.whitelist()
def setup_production_daraja_integration():
    """Setup PRODUCTION Daraja integration"""
    try:
        frappe.msgprint("🚀 Starting PRODUCTION Daraja integration setup...")
        
        # Verify production credentials
        settings = frappe.get_single("TukTuk Settings")
        if not settings.get_password("mpesa_api_key") or not settings.get_password("mpesa_api_secret"):
            frappe.throw("Production MPesa API credentials not configured in TukTuk Settings")
        
        if not settings.mpesa_paybill:
            frappe.throw("Production Paybill number not configured in TukTuk Settings")
        
        # Step 1: Test production access token
        token = get_access_token()
        if not token:
            frappe.throw("Failed to get production access token. Check your production credentials.")
        
        frappe.msgprint("✅ Step 1: Production access token obtained")
        
        # Step 2: Register production C2B URLs
        if register_c2b_url():
            frappe.msgprint("✅ Step 2: Production C2B URLs registered")
        else:
            frappe.throw("Failed to register production C2B URLs")
        
        frappe.msgprint("🎉 PRODUCTION Daraja integration setup complete!")
        frappe.msgprint("Your system is now LIVE and ready to accept real payments!")
        frappe.msgprint("Monitor the Error Log for transaction processing updates.")
        
    except Exception as e:
        frappe.throw(f"Production setup failed: {str(e)}")

@frappe.whitelist()
def setup_daraja_integration():
    """Setup Daraja integration - redirects to production version"""
    return setup_production_daraja_integration()

@frappe.whitelist()
def get_system_status():
    """Get current system status"""
    try:
        settings = frappe.get_single("TukTuk Settings")
        
        # Count vehicles by status
        vehicle_stats = frappe.db.sql("""
            SELECT status, COUNT(*) as count 
            FROM `tabTukTuk Vehicle` 
            GROUP BY status
        """, as_dict=True)
        
        # Count drivers
        driver_stats = frappe.db.sql("""
            SELECT 
                COUNT(*) as total_drivers,
                COUNT(assigned_tuktuk) as assigned_drivers
            FROM `tabTukTuk Driver`
        """, as_dict=True)[0]
        
        # Count transactions today
        today_transactions = frappe.db.count("TukTuk Transaction", {
            "timestamp": [">=", frappe.utils.today()]
        })
        
        # Calculate today's revenue
        today_revenue = frappe.db.sql("""
            SELECT COALESCE(SUM(amount), 0) as revenue
            FROM `tabTukTuk Transaction`
            WHERE DATE(timestamp) = CURDATE()
            AND payment_status = 'Completed'
        """, as_dict=True)[0].revenue
        
        return {
            "environment": "PRODUCTION",
            "paybill": settings.mpesa_paybill,
            "operating_hours": f"{settings.operating_hours_start} - {settings.operating_hours_end}",
            "global_target": settings.global_daily_target,
            "target_sharing_enabled": getattr(settings, 'enable_target_sharing', 1),
            "vehicle_stats": vehicle_stats,
            "driver_stats": driver_stats,
            "today_transactions": today_transactions,
            "today_revenue": today_revenue,
            "within_operating_hours": is_within_operating_hours()
        }
        
    except Exception as e:
        frappe.throw(f"Status check failed: {str(e)}")

@frappe.whitelist()
def check_daraja_connection():
    """Test Daraja API connection"""
    try:
        token = get_access_token()
        if token:
            frappe.msgprint("✅ Production Daraja connection successful!")
            return True
        else:
            frappe.msgprint("❌ Production Daraja connection failed!")
            return False
    except Exception as e:
        frappe.msgprint(f"❌ Production Daraja connection error: {str(e)}")
        return False

@frappe.whitelist()
def daily_operations_report():
    """Generate daily operations report"""
    try:
        # Active TukTuks
        active_tuktuks = frappe.get_all("TukTuk Vehicle", 
                                       filters={"status": "Assigned"},
                                       fields=["tuktuk_id", "battery_level"])
        
        # Low battery alerts
        low_battery = [t for t in active_tuktuks if t.battery_level < 20]
        
        # Today's revenue
        today_revenue = frappe.db.sql("""
            SELECT COALESCE(SUM(amount), 0) as revenue
            FROM `tabTukTuk Transaction`
            WHERE DATE(timestamp) = CURDATE()
            AND payment_status = 'Completed'
        """, as_dict=True)[0].revenue
        
        # Drivers at target (target tracking always continues)
        drivers_at_target = frappe.get_all("TukTuk Driver",
                                          filters={"current_balance": [">=", 3000]})
        
        report = f"""
📊 SUNNY TUKTUK DAILY REPORT - {frappe.utils.today()}

🚗 FLEET STATUS:
- Active TukTuks: {len(active_tuktuks)}/21
- Low Battery Alerts: {len(low_battery)} TukTuks
{[t.tuktuk_id for t in low_battery] if low_battery else "None"}

💰 FINANCIAL:
- Today's Revenue: {today_revenue:,.0f} KSH
- Drivers at Target: {len(drivers_at_target)}

🔋 BATTERY STATUS:
- Average Battery: {sum(t.battery_level for t in active_tuktuks)/len(active_tuktuks) if active_tuktuks else 0:.1f}%
        """
        
        frappe.msgprint(report)
        return report
        
    except Exception as e:
        frappe.throw(f"Report generation failed: {str(e)}")

# ===== TESTING FUNCTIONS =====

@frappe.whitelist()
def test_payment_simulation():
    """Simulate a test payment for testing purposes"""
    try:
        # Find any tuktuk with a 3-digit account for testing
        tuktuk_with_3digit = frappe.get_all("TukTuk Vehicle", 
                                           filters={"mpesa_account": ["like", "___"]},
                                           fields=["name", "mpesa_account", "tuktuk_id"],
                                           limit=1)
        
        if not tuktuk_with_3digit:
            frappe.throw("No TukTuk with 3-digit account found. Update account formats first.")
        
        account = tuktuk_with_3digit[0].mpesa_account
        
        # Simulate payment data from Daraja
        test_payment_data = {
            "TransID": f"TEST{frappe.utils.now_datetime().strftime('%Y%m%d%H%M%S')}",
            "TransAmount": "100",
            "BillRefNumber": account,
            "MSISDN": "254708374149",
            "TransTime": frappe.utils.now_datetime().strftime('%Y%m%d%H%M%S'),
            "FirstName": "TEST",
            "MiddleName": "",
            "LastName": "USER"
        }
        
        # First validate
        validation_result = mpesa_validation(**test_payment_data)
        if validation_result.get("ResultCode") != "0":
            frappe.throw(f"Validation failed: {validation_result.get('ResultDesc')}")
        
        # Then confirm
        confirmation_result = mpesa_confirmation(**test_payment_data)
        if confirmation_result.get("ResultCode") == "0":
            frappe.msgprint("✅ Test payment processed successfully!")
            frappe.msgprint("Check TukTuk Transaction list to see the new transaction")
        else:
            frappe.throw("Test payment confirmation failed")
            
    except Exception as e:
        frappe.throw(f"Test payment failed: {str(e)}")

@frappe.whitelist()
def create_test_data():
    """Create comprehensive test data for the system"""
    try:
        frappe.msgprint("🏗️ Creating test data...")
        
        # Create test settings if they don't exist
        if not frappe.db.exists('TukTuk Settings', 'TukTuk Settings'):
            settings = frappe.get_doc({
                "doctype": "TukTuk Settings",
                "operating_hours_start": "06:00:00",
                "operating_hours_end": "00:00:00",
                "global_daily_target": 3000,
                "global_fare_percentage": 50,
                "global_rental_initial": 500,
                "global_rental_hourly": 200,
                "bonus_enabled": 0,
                "bonus_amount": 500,
                "mpesa_paybill": "4165253",
                "enable_sms_notifications": 0,
                "enable_email_notifications": 1
            })
            settings.insert()
            frappe.msgprint("✅ Created TukTuk Settings")
        
        # Create test vehicles
        for i in range(1, 6):  # Create 5 test vehicles
            tuktuk_id = f"TT{i:03d}"
            account = f"{i:03d}"
            
            if not frappe.db.exists("TukTuk Vehicle", {"tuktuk_id": tuktuk_id}):
                vehicle = frappe.get_doc({
                    "doctype": "TukTuk Vehicle",
                    "tuktuk_id": tuktuk_id,
                    "mpesa_account": account,
                    "battery_level": 85 + (i * 2),
                    "status": "Available",
                    "tuktuk_make": "Bajaj",
                    "tuktuk_colour": "Green"
                })
                vehicle.insert()
                frappe.msgprint(f"✅ Created TukTuk {tuktuk_id}")
        
        # Create test drivers
        test_drivers = [
            {"first": "John", "last": "Kamau", "id": "12345678", "phone": "254708374149"},
            {"first": "Mary", "last": "Wanjiku", "id": "87654321", "phone": "254711111111"},
            {"first": "Peter", "last": "Maina", "id": "11223344", "phone": "254722222222"},
        ]
        
        for i, driver_data in enumerate(test_drivers):
            if not frappe.db.exists("TukTuk Driver", {"driver_national_id": driver_data["id"]}):
                driver = frappe.get_doc({
                    "doctype": "TukTuk Driver",
                    "driver_first_name": driver_data["first"],
                    "driver_last_name": driver_data["last"],
                    "driver_national_id": driver_data["id"],
                    "driver_license": f"B{driver_data['id']}",
                    "mpesa_number": driver_data["phone"],
                    "driver_dob": "1990-01-01",
                    "driver_primary_phone": driver_data["phone"],
                    "assigned_tuktuk": frappe.db.get_value("TukTuk Vehicle", {"tuktuk_id": f"TT{i+1:03d}"}, "name")
                })
                driver.insert()
                frappe.msgprint(f"✅ Created driver {driver_data['first']} {driver_data['last']}")
                
                # Update TukTuk status to Assigned
                tuktuk = frappe.get_doc("TukTuk Vehicle", {"tuktuk_id": f"TT{i+1:03d}"})
                tuktuk.status = "Assigned"
                tuktuk.save()
        
        frappe.db.commit()
        frappe.msgprint("🎉 Test data creation complete!")
        
    except Exception as e:
        frappe.log_error(f"Test data creation failed: {str(e)}")
        frappe.throw(f"Test data creation failed: {str(e)}")

@frappe.whitelist()
def create_simple_test_driver():
    """Create a simple test driver without complex validations"""
    try:
        driver = frappe.get_doc({
            "doctype": "TukTuk Driver",
            "driver_first_name": "John",
            "driver_last_name": "Kamau",
            "driver_national_id": "12345678",
            "driver_license": "B123456",
            "mpesa_number": "254708374149",
            "driver_dob": "1990-01-01",
            "driver_primary_phone": "254708374149"
        })
        
        # Set the full name manually
        driver.driver_name = f"{driver.driver_first_name} {driver.driver_last_name}"
        
        driver.insert(ignore_permissions=True)
        frappe.db.commit()
        
        frappe.msgprint(f"✅ Test driver created: {driver.driver_name}")
        return driver.name
        
    except Exception as e:
        frappe.log_error("Driver Creation Error", str(e))
        frappe.throw(f"Failed to create driver: {str(e)}")

# ===== ASSIGNMENT FUNCTIONS =====

@frappe.whitelist()
def assign_driver_to_tuktuk(driver_id, tuktuk_id):
    """Assign a driver to a specific tuktuk"""
    try:
        # Get driver and tuktuk documents
        driver = frappe.get_doc("TukTuk Driver", driver_id)
        tuktuk = frappe.get_doc("TukTuk Vehicle", {"tuktuk_id": tuktuk_id})
        
        # Check if tuktuk is available
        if tuktuk.status != "Available":
            frappe.throw(f"TukTuk {tuktuk_id} is not available for assignment")
        
        # CRITICAL FIX: Check if tuktuk is already assigned to another driver
        existing_driver = frappe.db.get_value(
            "TukTuk Driver",
            {"assigned_tuktuk": tuktuk.name, "name": ["!=", driver_id]},
            "name"
        )
        if existing_driver:
            existing_driver_name = frappe.db.get_value("TukTuk Driver", existing_driver, "driver_name")
            frappe.throw(f"TukTuk {tuktuk_id} is already assigned to driver {existing_driver_name}")
        
        # Check if driver is already assigned
        if driver.assigned_tuktuk:
            old_tuktuk = frappe.get_doc("TukTuk Vehicle", driver.assigned_tuktuk)
            old_tuktuk.status = "Available"
            old_tuktuk.save()
        
        # Make assignment
        driver.assigned_tuktuk = tuktuk.name
        driver.save()
        
        tuktuk.status = "Assigned"
        tuktuk.save()
        
        frappe.msgprint(f"✅ Driver {driver.driver_name} assigned to TukTuk {tuktuk_id}")
        return True
        
    except Exception as e:
        frappe.throw(f"Assignment failed: {str(e)}")

# ===== LEGACY COMPATIBILITY =====

def reset_daily_targets():
    """Legacy function - redirects to new version"""
    return reset_daily_targets_with_deposit()

# ===== MODULE INITIALIZATION =====

def on_doctype_update():
    """Called when doctypes are updated"""
    pass

def update_vehicle_statuses():
    """Scheduled function to update vehicle statuses"""
    try:
        # This function can be called by the scheduler
        # to update vehicle statuses based on telemetry data
        pass
    except Exception as e:
        frappe.log_error(f"Vehicle status update failed: {str(e)}")

# ===== BATTERY MANAGEMENT FUNCTIONS =====

def check_battery_levels():
    """
    Scheduled task to check battery levels and send alerts
    Called hourly from hooks.py
    """
    try:
        from tuktuk_management.api.battery_utils import check_low_battery_alerts
        check_low_battery_alerts()
        frappe.logger().info("Battery level check completed successfully")
    except Exception as e:
        frappe.log_error(f"Battery level check failed: {str(e)}", "Battery Check Error")

def update_vehicle_battery_from_telemetry():
    """
    Update all vehicle batteries from telemetry data
    Can be called as a scheduled task
    """
    try:
        from tuktuk_management.api.battery_utils import update_all_battery_levels
        update_all_battery_levels()
        frappe.logger().info("Vehicle battery telemetry update completed")
    except Exception as e:
        frappe.log_error(f"Battery telemetry update failed: {str(e)}", "Battery Update Error")

@frappe.whitelist()
def get_low_battery_vehicles():
    """
    Get list of vehicles with low battery levels
    Returns vehicles with battery < 20%
    """
    try:
        vehicles = frappe.db.sql("""
            SELECT 
                name, tuktuk_id, battery_level, status, 
                last_reported, current_latitude, current_longitude
            FROM `tabTukTuk Vehicle`
            WHERE battery_level < 20 
            AND status NOT IN ('Maintenance', 'Out of Service')
            ORDER BY battery_level ASC
        """, as_dict=True)
        
        return vehicles
        
    except Exception as e:
        frappe.throw(f"Failed to get low battery vehicles: {str(e)}")

@frappe.whitelist()
def force_battery_alert(vehicle_name):
    """
    Manually trigger a battery alert for a specific vehicle
    """
    try:
        from tuktuk_management.api.battery_utils import BatteryConverter, send_battery_alert
        
        vehicle = frappe.get_doc("TukTuk Vehicle", vehicle_name)
        battery_status = BatteryConverter.get_battery_status(vehicle.battery_level)
        
        send_battery_alert(vehicle, battery_status)
        
        return {
            "success": True,
            "message": f"Battery alert sent for TukTuk {vehicle.tuktuk_id}"
        }
        
    except Exception as e:
        frappe.throw(f"Failed to send battery alert: {str(e)}")

# ===== TRANSACTION RECOVERY FUNCTIONS =====

@frappe.whitelist()
def add_missed_transaction_TL176BJ1M3():
    """
    Add missed transaction TL176BJ1M3 from 01/12/2025 at 15:30:53
    Transaction details:
    - Amount: 400 KES
    - Account: 025 (TukTuk 025)
    - Driver: DRV-112010
    - Customer Phone: 0723526737
    """
    import hashlib
    
    try:
        frappe.flags.ignore_permissions = True
        
        # Transaction details from Safaricom
        transaction_id = "TL176BJ1M3"
        amount = 400.0
        account_number = "025"
        customer_phone = "0723526737"
        transaction_time = "2025-12-01 15:30:53"
        
        # Check if transaction already exists
        existing = frappe.db.exists("TukTuk Transaction", {"transaction_id": transaction_id})
        if existing:
            frappe.msgprint(f"❌ Transaction {transaction_id} already exists!")
            frappe.log_error("Transaction Already Exists", 
                           f"Transaction {transaction_id} already exists in the system")
            return {"success": False, "message": "Transaction already exists"}
        
        # Get TukTuk
        tuktuk_name = frappe.db.get_value("TukTuk Vehicle", {"mpesa_account": account_number}, "name")
        if not tuktuk_name:
            frappe.msgprint(f"❌ TukTuk not found for account: {account_number}")
            return {"success": False, "message": f"TukTuk not found for account: {account_number}"}
        
        frappe.msgprint(f"✅ Found TukTuk: {tuktuk_name}")
        
        # Get assigned driver
        driver_name = frappe.db.get_value("TukTuk Driver", {"assigned_tuktuk": tuktuk_name}, "name")
        if not driver_name:
            frappe.msgprint(f"❌ No driver assigned to tuktuk: {tuktuk_name}")
            return {"success": False, "message": f"No driver assigned to tuktuk: {tuktuk_name}"}
        
        frappe.msgprint(f"✅ Found Driver: {driver_name}")
        
        # Get driver document for calculations
        driver = frappe.get_doc("TukTuk Driver", driver_name)
        settings = frappe.get_single("TukTuk Settings")
        
        # Calculate shares
        percentage = driver.fare_percentage or settings.global_fare_percentage
        target = driver.daily_target or settings.global_daily_target
        
        # Check if target sharing is enabled
        driver_target_override = getattr(driver, 'target_sharing_override', 'Follow Global')
        if driver_target_override == 'Enable':
            target_sharing_enabled = True
        elif driver_target_override == 'Disable':
            target_sharing_enabled = False
        else:
            target_sharing_enabled = getattr(settings, 'enable_target_sharing', 1)
        
        # Calculate driver share and target contribution
        if target_sharing_enabled and driver.current_balance >= target:
            driver_share = amount  # 100% to driver when target met
            target_contribution = 0
        else:
            driver_share = amount * (percentage / 100)
            target_contribution = amount - driver_share
        
        frappe.msgprint(f"💰 Amount: {amount} KES")
        frappe.msgprint(f"💵 Driver Share: {driver_share} KES")
        frappe.msgprint(f"🎯 Target Contribution: {target_contribution} KES")
        
        # Hash customer phone for privacy (same method used in transactions)
        hashed_phone = hashlib.sha256(customer_phone.encode()).hexdigest()
        
        # Create the transaction
        transaction = frappe.get_doc({
            "doctype": "TukTuk Transaction",
            "transaction_id": transaction_id,
            "transaction_type": "Payment",
            "tuktuk": tuktuk_name,
            "driver": driver_name,
            "amount": amount,
            "driver_share": driver_share,
            "target_contribution": target_contribution,
            "customer_phone": hashed_phone,
            "timestamp": transaction_time,
            "payment_status": "Completed",
            "b2c_payment_sent": 0  # Not sent yet, will trigger now
        })
        
        transaction.insert(ignore_permissions=True)
        frappe.msgprint(f"✅ Transaction created: {transaction.name}")
        
        # ATOMIC UPDATE FIX: Use SQL UPDATE to prevent race conditions
        if target_contribution > 0:
            old_balance = driver.current_balance
            global_target = settings.global_daily_target or 0
            frappe.db.sql("""
                UPDATE `tabTukTuk Driver`
                SET current_balance = current_balance + %s
                WHERE name = %s
            """, (target_contribution, driver_name))
            
            # Also update left_to_target atomically
            frappe.db.sql("""
                UPDATE `tabTukTuk Driver`
                SET left_to_target = GREATEST(0, 
                    COALESCE(NULLIF(daily_target, 0), %s) - current_balance
                )
                WHERE name = %s
            """, (global_target, driver_name))
            
            new_balance = frappe.db.get_value("TukTuk Driver", driver_name, "current_balance")
            frappe.msgprint(f"✅ Driver balance updated: {old_balance} → {new_balance}")
        
        # Commit the transaction creation
        frappe.db.commit()
        
        # Now trigger B2C payment to driver
        frappe.msgprint(f"🚀 Triggering B2C payment to driver...")
        frappe.msgprint(f"   Driver: {driver.driver_name}")
        frappe.msgprint(f"   Phone: {driver.mpesa_number}")
        frappe.msgprint(f"   Amount: {driver_share} KES")
        
        # Send payment to driver
        payment_success = send_mpesa_payment(driver.mpesa_number, driver_share, "FARE")
        
        if payment_success:
            # Update transaction to mark B2C as sent
            frappe.db.set_value("TukTuk Transaction", transaction.name, 
                              "b2c_payment_sent", 1, update_modified=False)
            frappe.db.commit()
            frappe.msgprint(f"✅ B2C payment sent successfully!")
            frappe.msgprint(f"   Check Error Log for Conversation ID")
        else:
            frappe.msgprint(f"⚠️ B2C payment failed - transaction recorded but payment not sent")
            frappe.msgprint(f"   Check Error Log for details")
            # Add comment to transaction
            transaction.add_comment('Comment', 
                                  f'Manual transaction recovery: B2C payment failed on initial attempt')
            transaction.save(ignore_permissions=True)
            frappe.db.commit()
        
        result_message = f"""
        ✅ TRANSACTION RECOVERY COMPLETE
        =====================================
        Transaction ID: {transaction_id}
        Amount: {amount} KES
        Driver Share: {driver_share} KES
        Target Contribution: {target_contribution} KES
        Driver: {driver.driver_name} ({driver_name})
        TukTuk: {tuktuk_name}
        B2C Payment: {'SUCCESS' if payment_success else 'FAILED - retry manually'}
        =====================================
        """
        
        frappe.msgprint(result_message)
        frappe.log_error("Transaction Recovery Success", result_message)
        
        return {
            "success": True,
            "message": "Transaction recovered successfully",
            "transaction_id": transaction_id,
            "transaction_name": transaction.name,
            "amount": amount,
            "driver_share": driver_share,
            "target_contribution": target_contribution,
            "b2c_payment_sent": payment_success
        }
        
    except Exception as e:
        frappe.db.rollback()
        error_msg = f"Transaction recovery failed: {str(e)}"
        frappe.msgprint(f"❌ {error_msg}")
        frappe.log_error("Transaction Recovery Error", error_msg)
        import traceback
        frappe.log_error("Transaction Recovery Traceback", traceback.format_exc())
        return {"success": False, "message": error_msg}
    finally:
        frappe.flags.ignore_permissions = False

# ===== BALANCE RECONCILIATION FUNCTIONS =====

@frappe.whitelist()
def reconcile_driver_balance(driver_name, date=None):
    """
    Reconcile driver's current_balance by recalculating from transactions.
    This fixes discrepancies caused by race conditions or missing updates.
    
    Args:
        driver_name: Driver document name (e.g., DRV-112001)
        date: Optional date to calculate balance from (defaults to today at operating hours start)
    
    Returns:
        dict: Reconciliation result with old balance, calculated balance, and discrepancy
    """
    try:
        frappe.flags.ignore_permissions = True
        
        # Get driver document
        driver = frappe.get_doc("TukTuk Driver", driver_name)
        old_balance = driver.current_balance
        
        # Get operating hours start time
        settings = frappe.get_single("TukTuk Settings")
        operating_hours_start = settings.operating_hours_start or "06:00:00"
        
        # Calculate date to reconcile from
        if date:
            from_datetime = f"{date} {operating_hours_start}"
        else:
            # Use today's operating hours start (6 AM)
            today = frappe.utils.today()
            from_datetime = f"{today} {operating_hours_start}"
        
        # Query all transactions for this driver since operating hours start
        transactions = frappe.get_all("TukTuk Transaction",
                                     filters={
                                         "driver": driver_name,
                                         "timestamp": [">=", from_datetime],
                                         "payment_status": "Completed",
                                         "transaction_type": ["not in", ["Adjustment", "Driver Repayment"]]
                                     },
                                     fields=["name", "transaction_id", "amount", "target_contribution", "timestamp"],
                                     order_by="timestamp asc")
        
        # Calculate expected balance from transactions
        calculated_balance = sum([t.target_contribution for t in transactions])
        
        # Calculate discrepancy
        discrepancy = old_balance - calculated_balance
        
        result = {
            "driver_name": driver_name,
            "driver": driver.driver_name,
            "old_balance": old_balance,
            "calculated_balance": calculated_balance,
            "discrepancy": discrepancy,
            "transactions_count": len(transactions),
            "from_datetime": from_datetime,
            "reconciled": False
        }
        
        if discrepancy != 0:
            result["message"] = f"⚠️ DISCREPANCY DETECTED: {abs(discrepancy)} KSH {'missing' if discrepancy < 0 else 'extra'}"
            frappe.log_error("Balance Discrepancy Detected",
                           f"Driver: {driver.driver_name} ({driver_name})\n"
                           f"Current Balance: {old_balance}\n"
                           f"Calculated Balance: {calculated_balance}\n"
                           f"Discrepancy: {discrepancy}\n"
                           f"Transactions: {len(transactions)}\n"
                           f"From: {from_datetime}")
        else:
            result["message"] = "✅ Balance is correct - no discrepancy"
        
        return result
        
    except Exception as e:
        frappe.log_error(f"Balance Reconciliation Error: {str(e)}")
        return {
            "success": False,
            "error": f"Failed to reconcile balance: {str(e)}"
        }
    finally:
        frappe.flags.ignore_permissions = False

@frappe.whitelist()
def fix_driver_balance(driver_name, date=None, auto_fix=False):
    """
    Fix driver's current_balance by updating it to the calculated value from transactions.
    Use this when reconcile_driver_balance detects a discrepancy.
    
    Args:
        driver_name: Driver document name (e.g., DRV-112001)
        date: Optional date to calculate balance from (defaults to today at operating hours start)
        auto_fix: If True, automatically update the balance without confirmation
    
    Returns:
        dict: Fix result with old balance, new balance, and adjustment made
    """
    try:
        frappe.flags.ignore_permissions = True
        
        # First reconcile to get the calculated balance
        reconcile_result = reconcile_driver_balance(driver_name, date)
        
        if "error" in reconcile_result:
            return reconcile_result
        
        discrepancy = reconcile_result["discrepancy"]
        
        if discrepancy == 0:
            return {
                "success": True,
                "message": "✅ No fix needed - balance is already correct",
                "driver_name": driver_name,
                "balance": reconcile_result["old_balance"]
            }
        
        # Update balance using atomic SQL
        calculated_balance = reconcile_result["calculated_balance"]
        old_balance = reconcile_result["old_balance"]
        
        # Get global target for left_to_target calculation
        settings = frappe.get_single("TukTuk Settings")
        global_target = settings.global_daily_target or 0
        
        frappe.db.sql("""
            UPDATE `tabTukTuk Driver`
            SET current_balance = %s
            WHERE name = %s
        """, (calculated_balance, driver_name))
        
        # Update left_to_target atomically
        frappe.db.sql("""
            UPDATE `tabTukTuk Driver`
            SET left_to_target = GREATEST(0, 
                COALESCE(NULLIF(daily_target, 0), %s) - current_balance
            )
            WHERE name = %s
        """, (global_target, driver_name))
        
        frappe.db.commit()
        
        # Log the fix
        driver = frappe.get_doc("TukTuk Driver", driver_name)
        driver.add_comment('Comment',
                          f'Balance reconciliation: Fixed discrepancy of {discrepancy} KSH. '
                          f'Old balance: {old_balance}, New balance: {calculated_balance}')
        
        frappe.log_error("Balance Fixed",
                       f"Driver: {driver.driver_name} ({driver_name})\n"
                       f"Old Balance: {old_balance}\n"
                       f"New Balance: {calculated_balance}\n"
                       f"Adjustment: {discrepancy}\n"
                       f"Transactions: {reconcile_result['transactions_count']}")
        
        return {
            "success": True,
            "message": f"✅ Balance fixed: {old_balance} → {calculated_balance} (adjusted {discrepancy} KSH)",
            "driver_name": driver_name,
            "driver": driver.driver_name,
            "old_balance": old_balance,
            "new_balance": calculated_balance,
            "adjustment": discrepancy,
            "transactions_count": reconcile_result['transactions_count']
        }
        
    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(f"Balance Fix Error: {str(e)}")
        return {
            "success": False,
            "error": f"Failed to fix balance: {str(e)}"
        }
    finally:
        frappe.flags.ignore_permissions = False

@frappe.whitelist()
def reconcile_all_drivers_balances(date=None, auto_fix=False):
    """
    Reconcile balances for all active drivers.
    Useful for daily reconciliation or fixing widespread discrepancies.
    
    Args:
        date: Optional date to calculate balances from (defaults to today)
        auto_fix: If True, automatically fix all discrepancies found
    
    Returns:
        dict: Summary of reconciliation for all drivers
    """
    try:
        frappe.flags.ignore_permissions = True
        
        # Get all drivers with assigned tuktuks (active drivers)
        drivers = frappe.get_all("TukTuk Driver",
                                filters={"assigned_tuktuk": ["is", "set"]},
                                fields=["name", "driver_name"])
        
        results = []
        total_discrepancy = 0
        drivers_with_issues = 0
        
        for driver in drivers:
            result = reconcile_driver_balance(driver.name, date)
            
            if "error" not in result:
                if result["discrepancy"] != 0:
                    drivers_with_issues += 1
                    total_discrepancy += abs(result["discrepancy"])
                    
                    # Auto-fix if requested
                    if auto_fix:
                        fix_result = fix_driver_balance(driver.name, date, auto_fix=True)
                        result["fixed"] = fix_result.get("success", False)
                
                results.append(result)
        
        summary = {
            "success": True,
            "total_drivers": len(drivers),
            "drivers_checked": len(results),
            "drivers_with_discrepancies": drivers_with_issues,
            "total_discrepancy_amount": total_discrepancy,
            "results": results,
            "auto_fixed": auto_fix
        }
        
        if drivers_with_issues > 0:
            frappe.log_error("Mass Balance Reconciliation",
                           f"Found discrepancies in {drivers_with_issues} out of {len(drivers)} drivers\n"
                           f"Total discrepancy amount: {total_discrepancy} KSH\n"
                           f"Auto-fixed: {auto_fix}")
        
        return summary
        
    except Exception as e:
        frappe.log_error(f"Mass Reconciliation Error: {str(e)}")
        return {
            "success": False,
            "error": f"Failed to reconcile all drivers: {str(e)}"
        }
    finally:
        frappe.flags.ignore_permissions = False

def remove_pending_adjustments_for_driver():
    """
    Remove pending adjustment transactions for DRV-112017 with amount 50
    This function can be called to fix the Sh. 50 transaction issue
    """
    try:
        # Find pending adjustment transactions for DRV-112017 with amount 50
        pending_adjustments = frappe.get_all("TukTuk Transaction",
                                            filters={
                                                "driver": "DRV-112017",
                                                "transaction_type": "Adjustment",
                                                "amount": 50,
                                                "payment_status": "Completed"
                                            },
                                            fields=["name", "transaction_id", "amount", "timestamp"])

        if not pending_adjustments:
            frappe.msgprint("No pending adjustment transactions found for DRV-112017 with amount 50")
            return False

        frappe.msgprint(f"Found {len(pending_adjustments)} pending adjustment transactions:")
        for adjustment in pending_adjustments:
            frappe.msgprint(f"  - Transaction: {adjustment.name}")
            frappe.msgprint(f"    ID: {adjustment.transaction_id}")
            frappe.msgprint(f"    Amount: {adjustment.amount}")
            frappe.msgprint(f"    Timestamp: {adjustment.timestamp}")

        # Delete each pending adjustment transaction
        for adjustment in pending_adjustments:
            try:
                frappe.delete_doc("TukTuk Transaction", adjustment.name)
                frappe.db.commit()
                frappe.msgprint(f"✅ Successfully deleted adjustment transaction: {adjustment.name}")
            except Exception as e:
                frappe.log_error(f"Error deleting adjustment transaction: {adjustment.name}", str(e))
                frappe.msgprint(f"❌ Failed to delete adjustment transaction: {adjustment.name}. Error: {str(e)}")
        
        frappe.msgprint(f"✅ Completed processing {len(pending_adjustments)} adjustment transactions")
        return True
    
    except Exception as e:
        frappe.log_error("Error in remove_pending_adjustments_for_driver", str(e))
        frappe.msgprint(f"❌ Error processing adjustment transactions: {str(e)}")
        return False
