# ~/frappe-bench/apps/tuktuk_management/tuktuk_management/api/tuktuk.py

import frappe
from frappe.utils import now_datetime, get_time, get_datetime, add_to_date, getdate, date_diff, flt
from datetime import datetime, time
import re
import requests
import base64
import json

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
                    recipients=["manager@sunnytuktuk.com"],  # Update with actual email
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
    """Register callback URLs for C2B transactions - PRODUCTION VERSION"""
    settings = frappe.get_single("TukTuk Settings")
    access_token = get_access_token()
    
    if not access_token:
        frappe.throw("Failed to get production access token")
    
    # Use PRODUCTION URL
    api_url = f"{PRODUCTION_BASE_URL}/mpesa/c2b/v1/registerurl"
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    # Use YOUR production shortcode (paybill)
    shortcode = settings.mpesa_paybill or "4165253"
    
    # Your production ERPNext site URL
    base_url = frappe.utils.get_url()
    
    payload = {
        "ShortCode": shortcode,
        "ResponseType": "Completed",  # Only confirmed payments
        "ConfirmationURL": f"{base_url}/api/method/tuktuk_management.api.tuktuk.payment_confirmation",
        "ValidationURL": f"{base_url}/api/method/tuktuk_management.api.tuktuk.payment_validation"
    }
    
    try:
        response = requests.post(api_url, json=payload, headers=headers, timeout=30)
        result = response.json()
        
        if response.status_code == 200 and result.get("ResponseCode") == "0":
            frappe.msgprint(f"✅ Production C2B URL registration successful: {result.get('ResponseDescription')}")
            return True
        else:
            frappe.log_error("Production C2B Registration Failed", f"Response: {result}")
            frappe.throw(f"❌ Production C2B URL registration failed: {result}")
            return False
            
    except Exception as e:
        frappe.log_error("Production C2B Registration Error", str(e))
        frappe.throw(f"Production C2B registration error: {str(e)}")
        return False

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
        
        # Check if tuktuk exists
        tuktuk_exists = frappe.db.exists("TukTuk Vehicle", {"mpesa_account": account_number})
        if not tuktuk_exists:
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
    """M-Pesa confirmation endpoint - FIXED VERSION"""
    try:
        # Extract transaction details
        transaction_id = kwargs.get('TransID')
        amount = float(kwargs.get('TransAmount', 0))
        account_number = kwargs.get('BillRefNumber', '').strip()
        customer_phone = kwargs.get('MSISDN')
        trans_time = kwargs.get('TransTime')
        first_name = kwargs.get('FirstName', '')
        last_name = kwargs.get('LastName', '')
        
        # Find the tuktuk
        tuktuk = frappe.db.get_value("TukTuk Vehicle", {"mpesa_account": account_number}, "name")
        if not tuktuk:
            frappe.log_error(f"M-Pesa Confirmation: TukTuk not found for account: {account_number}")
            return {"ResultCode": "0", "ResultDesc": "Success"}
        
        # Find assigned driver
        driver_name = frappe.db.get_value("TukTuk Driver", {"assigned_tuktuk": tuktuk}, "name")
        if not driver_name:
            frappe.log_error(f"M-Pesa Confirmation: No driver assigned to tuktuk: {tuktuk}")
            return {"ResultCode": "0", "ResultDesc": "Success"}
        
        # Check if transaction already exists
        if frappe.db.exists("TukTuk Transaction", {"transaction_id": transaction_id}):
            frappe.log_error(f"M-Pesa Confirmation: Transaction already processed: {transaction_id}")
            return {"ResultCode": "0", "ResultDesc": "Success"}
        
        # CRITICAL FIX: Get driver and settings for calculations
        driver = frappe.get_doc("TukTuk Driver", driver_name)
        settings = frappe.get_single("TukTuk Settings")
        
        # Calculate shares BEFORE creating transaction
        percentage = driver.fare_percentage or settings.global_fare_percentage
        target = driver.daily_target or settings.global_daily_target
        
        if driver.current_balance >= target:
            driver_share = amount  # 100% to driver
            target_contribution = 0
        else:
            driver_share = amount * (percentage / 100)
            target_contribution = amount - driver_share
        
        # Create transaction with calculated fields
        transaction = frappe.get_doc({
            "doctype": "TukTuk Transaction",
            "transaction_id": transaction_id,
            "tuktuk": tuktuk,
            "driver": driver_name,
            "amount": amount,
            "driver_share": driver_share,  # CRITICAL: Set before insert
            "target_contribution": target_contribution,  # CRITICAL: Set before insert
            "customer_phone": customer_phone,
            "timestamp": now_datetime(),
            "payment_status": "Completed"
        })
        
        transaction.insert(ignore_permissions=True)
        
        # Update driver balance
        driver.current_balance += target_contribution
        driver.save()
        
        # Send payment to driver
        try:
            if send_mpesa_payment(driver.mpesa_number, driver_share, "FARE"):
                frappe.log_error("M-Pesa Payment Success", f"Sent {driver_share} KSH to driver {driver.driver_name}")
            else:
                frappe.log_error("M-Pesa Payment Failed", f"Failed to send {driver_share} KSH to driver {driver.driver_name}")
        except Exception as payment_error:
            frappe.log_error("M-Pesa B2C Error", f"B2C payment failed: {str(payment_error)}")
        
        frappe.db.commit()
        frappe.log_error("M-Pesa Transaction Success", f"Transaction {transaction_id} processed successfully")
        
        return {"ResultCode": "0", "ResultDesc": "Success"}
        
    except Exception as e:
        frappe.log_error(f"M-Pesa Confirmation Error: {str(e)}")
        return {"ResultCode": "0", "ResultDesc": "Success"}

# Alternative endpoints without "mpesa" in URL (for Daraja compatibility)
@frappe.whitelist(allow_guest=True)
def payment_validation(**kwargs):
    """Alternative validation endpoint without 'mpesa' in URL"""
    return mpesa_validation(**kwargs)

@frappe.whitelist(allow_guest=True) 
def payment_confirmation(**kwargs):
    """Alternative confirmation endpoint without 'mpesa' in URL"""
    return mpesa_confirmation(**kwargs)

# ===== B2C PAYMENT FUNCTION =====

def send_mpesa_payment(mpesa_number, amount, payment_type="FARE"):
    """Send payment to driver via MPesa B2C using PRODUCTION Daraja API"""
    settings = frappe.get_single("TukTuk Settings")
    access_token = get_access_token()
    
    try:
        validate_mpesa_number_string(mpesa_number)
        
        if amount <= 0:
            frappe.throw("Invalid payment amount")
        
        if not access_token:
            frappe.log_error("❌ Cannot send production B2C: No access token")
            return False
        
        # Use PRODUCTION B2C API
        api_url = f"{PRODUCTION_BASE_URL}/mpesa/b2c/v1/paymentrequest"
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        # PRODUCTION B2C Configuration - UPDATE THESE
        initiator_name = "APITest"  # Replace with your actual initiator name from Safaricom
        security_credential = "YOUR_SECURITY_CREDENTIAL"  # Get this from Safaricom
        
        payload = {
            "InitiatorName": initiator_name,
            "SecurityCredential": security_credential,
            "CommandID": "BusinessPayment",
            "Amount": amount,
            "PartyA": settings.mpesa_paybill,
            "PartyB": mpesa_number,
            "Remarks": f"Sunny TukTuk {payment_type} payment",
            "QueueTimeOutURL": f"{frappe.utils.get_url()}/api/method/tuktuk_management.api.tuktuk.b2c_timeout",
            "ResultURL": f"{frappe.utils.get_url()}/api/method/tuktuk_management.api.tuktuk.b2c_result",
            "Occasion": "TukTuk Service Payment"
        }
        
        response = requests.post(api_url, json=payload, headers=headers, timeout=30)
        result = response.json()
        
        if response.status_code == 200 and result.get("ResponseCode") == "0":
            frappe.log_error("Production B2C Success", f"B2C payment initiated: {result}")
            return True
        else:
            frappe.log_error("Production B2C Failed", f"B2C payment failed: {result}")
            return False
            
    except Exception as e:
        frappe.log_error("Production B2C Error", f"B2C payment error: {str(e)}")
        return False

@frappe.whitelist(allow_guest=True)
def b2c_result(**kwargs):
    """Handle B2C payment results"""
    try:
        frappe.log_error("Production B2C Result", f"B2C result received: {json.dumps(kwargs)}")
        return {"ResultCode": "0", "ResultDesc": "Success"}
    except Exception as e:
        frappe.log_error("B2C Result Error", str(e))
        return {"ResultCode": "0", "ResultDesc": "Success"}

@frappe.whitelist(allow_guest=True)
def b2c_timeout(**kwargs):
    """Handle B2C payment timeouts"""
    try:
        frappe.log_error("Production B2C Timeout", f"B2C timeout: {json.dumps(kwargs)}")
        return {"ResultCode": "0", "ResultDesc": "Success"}
    except Exception as e:
        frappe.log_error("B2C Timeout Error", str(e))
        return {"ResultCode": "0", "ResultDesc": "Success"}

# ===== ENHANCED PAYMENT HANDLING WITH DEPOSITS =====

def handle_mpesa_payment_with_deposit(doc, method):
    """Enhanced handle incoming Mpesa payments with deposit integration"""
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
        
        # Calculate shares based on target status
        if driver_doc.current_balance >= target:
            doc.driver_share = amount
            doc.target_contribution = 0
        else:
            doc.driver_share = amount * (percentage / 100)
            doc.target_contribution = amount - doc.driver_share
            
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
    if doc.rental_rate_initial and doc.rental_rate_initial <= 0:
        frappe.throw("Initial rental rate must be greater than 0")
    if doc.rental_rate_hourly and doc.rental_rate_hourly <= 0:
        frappe.throw("Hourly rental rate must be greater than 0")

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
    settings = frappe.get_single("TukTuk Settings")
    
    if not is_within_operating_hours():
        return
        
    drivers = frappe.get_all("TukTuk Driver", 
                            filters={"assigned_tuktuk": ["!=", ""]},
                            fields=["driver_national_id", "current_balance", "consecutive_misses",
                                   "allow_target_deduction_from_deposit", "current_deposit_balance"])
    
    for driver in drivers:
        try:
            driver_doc = frappe.get_doc("TukTuk Driver", {
                "driver_national_id": driver.driver_national_id
            })
            target = driver_doc.daily_target or settings.global_daily_target
            
            # Handle target miss
            if driver_doc.current_balance < target:
                shortfall = target - driver_doc.current_balance
                driver_doc.consecutive_misses += 1
                
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
                    terminate_driver_with_deposit_refund(driver_doc)
                else:
                    # Roll over unmet balance
                    driver_doc.current_balance = -shortfall  # Negative balance indicates debt
            else:
                driver_doc.consecutive_misses = 0
                # Pay bonus if enabled and criteria met
                if settings.bonus_enabled and settings.bonus_amount:
                    if send_mpesa_payment(driver_doc.mpesa_number, settings.bonus_amount, "BONUS"):
                        frappe.msgprint(f"Bonus payment sent to driver {driver_doc.driver_name}")
                driver_doc.current_balance = 0
                
            driver_doc.save()
        except Exception as e:
            frappe.log_error(f"Failed to reset targets for driver {driver.driver_national_id}: {str(e)}")

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
            recipients=["manager@sunnytuktuk.com"],
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
                                filters={"status": ["in", ["Charging", "Assigned"]]})
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
        today = frappe.utils.today()
        
        # Get today's transactions
        transactions = frappe.get_all("TukTuk Transaction",
                                    filters={"timestamp": [">=", today]},
                                    fields=["amount", "driver_share", "target_contribution", "payment_status"])
        
        # Calculate totals
        total_revenue = sum(t.amount for t in transactions if t.payment_status == "Completed")
        total_driver_payments = sum(t.driver_share for t in transactions if t.payment_status == "Completed")
        total_target_contributions = sum(t.target_contribution for t in transactions if t.payment_status == "Completed")
        
        # Get driver performance
        drivers_at_target = frappe.get_all("TukTuk Driver",
                                          filters={"current_balance": [">=", 3000]})
        
        # Generate report
        report = f"""
📊 SUNNY TUKTUK DAILY REPORT - {today}

💰 FINANCIAL SUMMARY:
- Total Revenue: {total_revenue:,.0f} KSH
- Driver Payments: {total_driver_payments:,.0f} KSH
- Target Contributions: {total_target_contributions:,.0f} KSH
- Transaction Count: {len(transactions)}

👥 DRIVER PERFORMANCE:
- Drivers at Target: {len(drivers_at_target)}
- Target Achievement Rate: {len(drivers_at_target)/21*100:.1f}%

🚗 FLEET STATUS:
- Active TukTuks: {frappe.db.count('TukTuk Vehicle', {'status': 'Assigned'})}
- Available TukTuks: {frappe.db.count('TukTuk Vehicle', {'status': 'Available'})}
- Charging TukTuks: {frappe.db.count('TukTuk Vehicle', {'status': 'Charging'})}
        """
        
        # Email report to management
        frappe.sendmail(
            recipients=["manager@sunnytuktuk.com"],
            subject=f"Daily Operations Report - {today}",
            message=report
        )
        
        frappe.log_error("Daily Report Generated", report)
        
    except Exception as e:
        frappe.log_error(f"Failed to generate daily report: {str(e)}")

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
            
            if driver.current_balance < target:
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
        
        # Drivers at target
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

# ===== END OF FILE =====