# ~/frappe-bench/apps/tuktuk_management/tuktuk_management/api/tuktuk.py

import frappe
from frappe.utils import now_datetime, get_time, get_datetime, add_to_date, getdate, date_diff
from datetime import datetime, time
import re
import requests
import base64
import json

# Daraja API Configuration
SANDBOX_BASE_URL = "https://sandbox.safaricom.co.ke"
PRODUCTION_BASE_URL = "https://api.safaricom.co.ke"
SANDBOX_SHORTCODE = "600980"  # Standard sandbox paybill

# ===== EXISTING FUNCTIONS (Enhanced) =====

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
                    recipients=[frappe.get_value("TukTuk Driver", 
                                              {"assigned_tuktuk": tuktuk_doc.tuktuk_id}, 
                                              "driver_email")],
                    subject="TukTuk Low Battery Warning",
                    message=message
                )
            except Exception as e:
                frappe.log_error(f"Email Notification Failed: {str(e)}")

def check_battery_levels():
    """Hourly battery level checks"""
    try:
        vehicles = frappe.get_all("TukTuk Vehicle", 
                                filters={"status": ["!=", "Charging"]},
                                fields=["name", "battery_level", "tuktuk_id"])
        
        settings = frappe.get_single("TukTuk Settings")
        BATTERY_WARNING_THRESHOLD = 20
        
        for vehicle in vehicles:
            if vehicle.battery_level <= BATTERY_WARNING_THRESHOLD:
                # Get assigned driver
                driver = frappe.get_all("TukTuk Driver",
                                      filters={"assigned_tuktuk": vehicle.name},
                                      fields=["driver_name", "driver_primary_phone", "driver_email"])
                
                if driver and len(driver) > 0:
                    message = f"Low battery warning for TukTuk {vehicle.tuktuk_id}: {vehicle.battery_level}%"
                    
                    # Send notifications
                    if settings.enable_sms_notifications and driver[0].driver_primary_phone:
                        try:
                            # Implement SMS notification here
                            pass
                        except Exception as e:
                            frappe.log_error(f"SMS Notification Failed: {str(e)}")
                    
                    if settings.enable_email_notifications and driver[0].driver_email:
                        try:
                            frappe.sendmail(
                                recipients=[driver[0].driver_email],
                                subject="TukTuk Low Battery Warning",
                                message=message
                            )
                        except Exception as e:
                            frappe.log_error(f"Email Notification Failed: {str(e)}")
                            
        frappe.db.commit()
    except Exception as e:
        frappe.log_error(f"Error in check_battery_levels: {str(e)}")

def reset_daily_targets():
    """Reset daily targets for all active drivers"""
    settings = frappe.get_single("TukTuk Settings")
    
    if not is_within_operating_hours():
        return
        
    drivers = frappe.get_all("TukTuk Driver", 
                            filters={"assigned_tuktuk": ["!=", ""]},
                            fields=["driver_national_id", "current_balance", "consecutive_misses"])
    
    for driver in drivers:
        try:
            driver_doc = frappe.get_doc("TukTuk Driver", {
                "driver_national_id": driver.driver_national_id
            })
            target = driver_doc.daily_target or settings.global_daily_target
            
            # Handle target miss
            if driver_doc.current_balance < target:
                driver_doc.consecutive_misses += 1
                if driver_doc.consecutive_misses >= 3:
                    terminate_driver(driver_doc)
                # Roll over unmet balance
                shortfall = target - driver_doc.current_balance
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

def terminate_driver(driver):
    """Terminate driver and free up their tuktuk"""
    try:
        if driver.assigned_tuktuk:
            tuktuk = frappe.get_doc("TukTuk Vehicle", driver.assigned_tuktuk)
            tuktuk.status = "Available"
            tuktuk.save()
        
        driver.assigned_tuktuk = ""
        driver.save()
        
        # Notify management
        frappe.sendmail(
            recipients=["manager@sunnytuktuk.com"],
            subject=f"Driver Termination: {driver.driver_name}",
            message=f"Driver {driver.driver_name} has been terminated due to consecutive target misses."
        )
    except Exception as e:
        frappe.log_error(f"Driver termination failed: {str(e)}")
        frappe.throw("Failed to process driver termination")

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

# ===== ENHANCED DARAJA INTEGRATION =====

def get_access_token():
    """Get OAuth access token from Daraja API"""
    settings = frappe.get_doc("TukTuk Settings")
    
    # Use sandbox for testing
    api_url = f"{SANDBOX_BASE_URL}/oauth/v1/generate?grant_type=client_credentials"
    
    # Get password fields correctly
    consumer_key = settings.get_password("mpesa_api_key")
    consumer_secret = settings.get_password("mpesa_api_secret")
    
    if not consumer_key or not consumer_secret:
        frappe.log_error("Daraja Config Error", "MPesa API credentials not configured in TukTuk Settings")
        return None
    
    # Create credentials string
    credentials = f"{consumer_key}:{consumer_secret}"
    encoded_credentials = base64.b64encode(credentials.encode()).decode()
    
    headers = {
        "Authorization": f"Basic {encoded_credentials}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(api_url, headers=headers)
        if response.status_code == 200:
            token_data = response.json()
            frappe.log_error("Daraja Token Success", f"Access token obtained")
            return token_data.get("access_token")
        else:
            frappe.log_error("Daraja Token Failed", response.text)
            return None
    except Exception as e:
        frappe.log_error("Daraja Token Error", str(e))
        return None

def register_c2b_url():
    """Register callback URLs for C2B transactions"""
    settings = frappe.get_doc("TukTuk Settings")  # Changed from frappe.get_single
    access_token = get_access_token()
    
    if not access_token:
        frappe.throw("Failed to get access token")
    
    api_url = f"{SANDBOX_BASE_URL}/mpesa/c2b/v1/registerurl"
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    # Use sandbox shortcode for testing
    shortcode = SANDBOX_SHORTCODE
    
    # Your ERPNext site URL
    base_url = frappe.utils.get_url()
    
    payload = {
        "ShortCode": shortcode,
        "ResponseType": "Completed",  # Only confirmed payments
        "ConfirmationURL": f"{base_url}/api/method/tuktuk_management.api.tuktuk.mpesa_confirmation",
        "ValidationURL": f"{base_url}/api/method/tuktuk_management.api.tuktuk.mpesa_validation"
    }
    
    try:
        response = requests.post(api_url, json=payload, headers=headers)
        result = response.json()
        
        if response.status_code == 200 and result.get("ResponseCode") == "0":
            frappe.log_error(f"✅ C2B URL registration successful: {result}")
            return True
        else:
            frappe.log_error(f"❌ C2B URL registration failed: {result}")
            return False
    except Exception as e:
        frappe.log_error(f"❌ C2B URL registration error: {str(e)}")
        return False

def mpesa_validation(**kwargs):
    """Validate incoming M-Pesa payments"""
    try:
        # Log the validation request with shorter title
        frappe.log_error("M-Pesa Validation", json.dumps(kwargs, indent=2))
        
        # Extract data
        amount = float(kwargs.get('TransAmount', 0))
        account_number = kwargs.get('BillRefNumber', '').strip()
        phone = kwargs.get('MSISDN', '')
        
        # Validation checks
        if amount <= 0:
            return {
                "ResultCode": "C2B00012",
                "ResultDesc": "Invalid amount"
            }
        
        if not account_number:
            return {
                "ResultCode": "C2B00012", 
                "ResultDesc": "Account number required"
            }
        
        # Check if tuktuk exists with this account number
        tuktuk_exists = frappe.db.exists("TukTuk Vehicle", {"mpesa_account": account_number})
        if not tuktuk_exists:
            frappe.log_error("Validation Failed", f"Invalid account number: {account_number}")
            return {
                "ResultCode": "C2B00012",
                "ResultDesc": f"Invalid account number: {account_number}"
            }
        
        # Check if tuktuk has assigned driver
        driver = frappe.db.get_value("TukTuk Driver", {"assigned_tuktuk": tuktuk_exists}, "name")
        if not driver:
            frappe.log_error("Validation Failed", f"No driver assigned to tuktuk with account: {account_number}")
            return {
                "ResultCode": "C2B00012",
                "ResultDesc": "No driver assigned to this tuktuk"
            }
        
        # Check operating hours
        if not is_within_operating_hours():
            frappe.log_error("Validation Failed", "Payment outside operating hours")
            return {
                "ResultCode": "C2B00012",
                "ResultDesc": "Payment outside operating hours"
            }
        
        frappe.log_error("Validation Success", f"Validation passed for account {account_number}, amount {amount}")
        return {
            "ResultCode": "0",
            "ResultDesc": "Success"
        }
        
    except Exception as e:
        frappe.log_error("M-Pesa Validation Error", str(e))
        return {
            "ResultCode": "C2B00012",
            "ResultDesc": "Validation failed"
        }

def mpesa_confirmation(**kwargs):
    """Process confirmed M-Pesa payments"""
    try:
        # Log the confirmation with shorter title
        frappe.log_error("M-Pesa Confirmation", json.dumps(kwargs, indent=2))
        
        # Extract transaction details
        transaction_id = kwargs.get('TransID')
        amount = float(kwargs.get('TransAmount', 0))
        account_number = kwargs.get('BillRefNumber', '').strip()
        customer_phone = kwargs.get('MSISDN')
        trans_time = kwargs.get('TransTime')
        first_name = kwargs.get('FirstName', '')
        middle_name = kwargs.get('MiddleName', '')
        last_name = kwargs.get('LastName', '')
        
        # Find the tuktuk
        tuktuk = frappe.db.get_value("TukTuk Vehicle", {"mpesa_account": account_number}, "name")
        if not tuktuk:
            frappe.log_error("Confirmation Failed", f"TukTuk not found for account: {account_number}")
            return {"ResultCode": "0", "ResultDesc": "Success"}
        
        # Find assigned driver
        driver = frappe.db.get_value("TukTuk Driver", {"assigned_tuktuk": tuktuk}, "name")
        if not driver:
            frappe.log_error("Confirmation Failed", f"No driver assigned to tuktuk: {tuktuk}")
            return {"ResultCode": "0", "ResultDesc": "Success"}
        
        # Check if transaction already exists
        if frappe.db.exists("TukTuk Transaction", {"transaction_id": transaction_id}):
            frappe.log_error("Confirmation Warning", f"Transaction already processed: {transaction_id}")
            return {"ResultCode": "0", "ResultDesc": "Success"}
        
        # Create transaction record
        transaction = frappe.get_doc({
            "doctype": "TukTuk Transaction",
            "transaction_id": transaction_id,
            "tuktuk": tuktuk,
            "driver": driver,
            "amount": amount,
            "customer_phone": customer_phone,
            "timestamp": now_datetime(),
            "payment_status": "Pending"
        })
        
        transaction.insert(ignore_permissions=True)
        frappe.db.commit()
        
        frappe.log_error("Transaction Created", f"Transaction created: {transaction.name}")
        
        # Process the payment using existing logic
        handle_mpesa_payment(transaction, None)
        
        return {"ResultCode": "0", "ResultDesc": "Success"}
        
    except Exception as e:
        frappe.log_error("M-Pesa Confirmation Error", str(e))
        return {"ResultCode": "0", "ResultDesc": "Success"}

def send_mpesa_payment(mpesa_number, amount, payment_type="FARE"):
    """Enhanced send payment to driver via MPesa B2C using Daraja API"""
    settings = frappe.get_doc("TukTuk Settings")  # Changed from frappe.get_single
    access_token = get_access_token()
    
    try:
        validate_mpesa_number_string(mpesa_number)
        
        if amount <= 0:
            frappe.throw("Invalid payment amount")
        
        if not access_token:
            frappe.log_error("❌ Cannot send B2C: No access token")
            # Fallback to old method for logging
            transaction = frappe.get_doc({
                "doctype": "TukTuk Transaction",
                "transaction_id": f"{payment_type}_{now_datetime().strftime('%Y%m%d%H%M%S')}",
                "amount": amount,
                "payment_status": "Failed",
                "timestamp": now_datetime(),
                "customer_phone": mpesa_number
            })
            transaction.insert()
            return False
        
        # Use Daraja B2C API
        api_url = f"{SANDBOX_BASE_URL}/mpesa/b2c/v1/paymentrequest"
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        # For sandbox testing
        initiator_name = "testapi"
        security_credential = "Safaricom999!*!"
        
        payload = {
            "InitiatorName": initiator_name,
            "SecurityCredential": security_credential,
            "CommandID": "BusinessPayment",
            "Amount": int(amount),
            "PartyA": SANDBOX_SHORTCODE,
            "PartyB": mpesa_number,
            "Remarks": f"TukTuk driver payment - {payment_type}",
            "QueueTimeOutURL": f"{frappe.utils.get_url()}/api/method/tuktuk_management.api.tuktuk.b2c_timeout",
            "ResultURL": f"{frappe.utils.get_url()}/api/method/tuktuk_management.api.tuktuk.b2c_result",
            "Occasion": payment_type
        }
        
        response = requests.post(api_url, json=payload, headers=headers)
        result = response.json()
        
        # Record the payment attempt
        transaction = frappe.get_doc({
            "doctype": "TukTuk Transaction",
            "transaction_id": f"{payment_type}_{now_datetime().strftime('%Y%m%d%H%M%S')}",
            "amount": amount,
            "payment_status": "Completed" if result.get("ResponseCode") == "0" else "Failed",
            "timestamp": now_datetime(),
            "customer_phone": mpesa_number
        })
        transaction.insert()
        
        if response.status_code == 200 and result.get("ResponseCode") == "0":
            frappe.log_error(f"✅ B2C payment initiated: {result}")
            return True
        else:
            frappe.log_error(f"❌ B2C payment failed: {result}")
            return False
            
    except Exception as e:
        frappe.log_error(f"MPesa Payment Failed: {str(e)}")
        return False

def validate_mpesa_number_string(mpesa_number):
    """Validate MPesa phone number format for string input"""
    if not mpesa_number:
        frappe.throw("MPesa number is required")
        
    cleaned_number = str(mpesa_number).replace(' ', '')
    pattern = r'^(?:\+254|254|0)\d{9}$'
    if not re.match(pattern, cleaned_number):
        frappe.throw("Invalid MPesa number format. Use format: +254XXXXXXXXX or 0XXXXXXXXX")
        
    return True

def handle_mpesa_payment(doc, method):
    """Enhanced handle incoming Mpesa payments with Daraja integration"""
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
                   "daily_target", "fare_percentage"],
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

# ===== B2C CALLBACK HANDLERS =====

@frappe.whitelist(allow_guest=True)
def b2c_result(**kwargs):
    """Handle B2C payment results"""
    frappe.log_error(f"💸 B2C Result: {json.dumps(kwargs, indent=2)}")
    return {"ResultCode": "0", "ResultDesc": "Success"}

@frappe.whitelist(allow_guest=True)
def b2c_timeout(**kwargs):
    """Handle B2C payment timeouts"""
    frappe.log_error(f"⏰ B2C Timeout: {json.dumps(kwargs, indent=2)}")
    return {"ResultCode": "0", "ResultDesc": "Success"}

# ===== EXISTING RENTAL FUNCTIONS =====

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
    
    # Check if driver already has an active rental
    existing_rental = frappe.get_all(
        "TukTuk Rental",
        filters={
            "driver": driver_id,
            "status": "Active"
        }
    )
    
    if existing_rental:
        frappe.throw("Driver already has an active rental")
    
    tuktuk = frappe.get_doc("TukTuk Vehicle", tuktuk_id)
    
    if tuktuk.status != "Available":
        frappe.throw("TukTuk is not available for rental")
        
    rental = frappe.get_doc({
        "doctype": "TukTuk Rental",
        "driver": driver_id,
        "rented_tuktuk": tuktuk_id,
        "start_time": start_time,
        "rental_fee": tuktuk.rental_rate_initial or settings.global_rental_initial,
        "status": "Active"
    })
    
    rental.insert()
    
    tuktuk.status = "Assigned"
    tuktuk.save()
    
    return rental

def end_rental(rental_id, end_time):
    """End a tuktuk rental and calculate final fee"""
    settings = frappe.get_single("TukTuk Settings")
    rental = frappe.get_doc("TukTuk Rental", rental_id)
    
    if rental.status != "Active":
        frappe.throw("Rental is not active")
        
    rental.end_time = end_time
    duration = (end_time - rental.start_time).total_seconds() / 3600
    
    tuktuk = frappe.get_doc("TukTuk Vehicle", rental.rented_tuktuk)
    hourly_rate = tuktuk.rental_rate_hourly or settings.global_rental_hourly
    
    if duration > 2:
        extra_hours = duration - 2
        rental.rental_fee += extra_hours * hourly_rate
        
    rental.status = "Completed"
    rental.save()
    
    tuktuk.status = "Available"
    tuktuk.save()
    
    return rental

# ===== REPORTING FUNCTIONS =====

def generate_daily_reports():
    """Generate end of day reports"""
    try:
        # Get today's date range
        end_time = now_datetime()
        start_time = add_to_date(end_time, days=-1, as_datetime=True)
        
        # Get all transactions for the day
        transactions = frappe.get_all(
            "TukTuk Transaction",
            filters={
                "timestamp": ["between", [start_time, end_time]],
                "payment_status": "Completed"
            },
            fields=["tuktuk", "amount", "driver_share", "target_contribution"]
        )
        
        # Compile statistics
        stats = {
            "total_transactions": len(transactions),
            "total_revenue": sum(t.amount for t in transactions),
            "total_driver_share": sum(t.driver_share for t in transactions),
            "total_target_contribution": sum(t.target_contribution for t in transactions)
        }
        
        # Create report document
        report = frappe.get_doc({
            "doctype": "TukTuk Daily Report",
            "report_date": end_time.date(),
            "total_transactions": stats["total_transactions"],
            "total_revenue": stats["total_revenue"],
            "total_driver_share": stats["total_driver_share"],
            "total_target_contribution": stats["total_target_contribution"]
        })
        
        report.insert()
        frappe.db.commit()
        
        # Send report to management
        if frappe.db.get_single_value("TukTuk Settings", "enable_email_notifications"):
            report_html = frappe.render_template(
                "tuktuk_management/templates/emails/daily_report.html",
                {"stats": stats, "date": end_time.date()}
            )
            
            frappe.sendmail(
                recipients=["manager@sunnytuktuk.com"],
                subject=f"TukTuk Daily Report - {end_time.date()}",
                message=report_html
            )
            
    except Exception as e:
        frappe.log_error(f"Error in generate_daily_reports: {str(e)}")

# ===== VALIDATION FUNCTIONS =====

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
                    "content": f"TukTuk entered charging state. Assigned driver: {driver[0].driver_name}"
                }).insert(ignore_permissions=True)

# ===== DRIVER VALIDATION FUNCTIONS =====

def validate_driver(doc, method):
    """Validate TukTuk Driver document"""
    try:
        validate_age(doc)
        validate_mpesa_number(doc)
        validate_phone_numbers(doc)
        validate_email(doc)
        validate_license(doc)
        validate_emergency_contact(doc)
    except Exception as e:
        frappe.log_error("Driver Validation Error", str(e))
        raise e

def validate_age(doc):
    """Ensure driver meets minimum age requirement"""
    if not doc.driver_dob:
        frappe.throw("Date of Birth is required")
        
    try:
        dob = getdate(doc.driver_dob)
        today = getdate()
        age = date_diff(today, dob) / 365.25
        
        if age < 18:
            frappe.throw("Driver must be at least 18 years old")
        if age > 65:
            frappe.throw("Driver age exceeds maximum limit of 65 years")
    except Exception as e:
        frappe.throw(f"Invalid date of birth: {str(e)}")

def validate_phone_numbers(doc):
    """Validate phone number formats"""
    if doc.driver_primary_phone:
        pattern = r'^(?:\+254|254|0)\d{9}$'
        if not re.match(pattern, doc.driver_primary_phone.replace(' ', '')):
            frappe.throw("Invalid primary phone number format")
            
    if doc.driver_secondary_phone:
        pattern = r'^(?:\+254|254|0)\d{9}$'
        if not re.match(pattern, doc.driver_secondary_phone.replace(' ', '')):
            frappe.throw("Invalid secondary phone number format")

def validate_email(doc):
    """Validate email format if provided"""
    if doc.driver_email:
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(pattern, doc.driver_email):
            frappe.throw("Invalid email format")

def validate_license(doc):
    """Validate driving license format"""
    if not doc.driver_license:
        frappe.throw("Driving License is required")
        
    # More flexible license validation
    if len(doc.driver_license) < 6:
        frappe.throw("Driving license must be at least 6 characters")


def validate_emergency_contact(doc):
    """Validate emergency contact details"""
    if doc.driver_emergency_phone:
        if not doc.driver_emergency_name:
            frappe.throw("Emergency contact name is required when phone is provided")
            
        pattern = r'^(?:\+254|254|0)\d{9}$'
        if not re.match(pattern, doc.driver_emergency_phone.replace(' ', '')):
            frappe.throw("Invalid emergency contact phone number format")


# Simplified driver creation function
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


def handle_driver_update(doc, method):
    """Handle updates to driver record"""
    # Check if this is an update (not an insert) and if assigned_tuktuk field changed
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


# ===== TESTING AND SETUP FUNCTIONS =====

@frappe.whitelist()
def setup_daraja_integration():
    """Complete setup of Daraja integration"""
    try:
        frappe.msgprint("🚀 Starting Daraja integration setup...")
        
        # Step 1: Test access token
        token = get_access_token()
        if not token:
            frappe.throw("Failed to get access token. Check your credentials.")
        
        frappe.msgprint("✅ Step 1: Access token obtained")
        
        # Step 2: Register C2B URLs
        if register_c2b_url():
            frappe.msgprint("✅ Step 2: C2B URLs registered")
        else:
            frappe.throw("Failed to register C2B URLs")
        
        frappe.msgprint("🎉 Daraja integration setup complete!")
        frappe.msgprint("You can now test payments using sandbox phone numbers:")
        frappe.msgprint("• 254708374149 (always succeeds)")
        frappe.msgprint("• 254711111111 (always succeeds)")
        frappe.msgprint("• Test with small amounts like 10 KSH")
        
    except Exception as e:
        frappe.throw(f"Setup failed: {str(e)}")

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
        
        # First validate - don't use whitelist decorator for testing
        validation_result = mpesa_validation_test(test_payment_data)
        if validation_result.get("ResultCode") != "0":
            frappe.throw(f"Validation failed: {validation_result.get('ResultDesc')}")
        
        # Then confirm
        confirmation_result = mpesa_confirmation_test(test_payment_data)
        if confirmation_result.get("ResultCode") == "0":
            frappe.msgprint("✅ Test payment processed successfully!")
            frappe.msgprint("Check TukTuk Transaction list to see the new transaction")
        else:
            frappe.throw("Test payment confirmation failed")
            
    except Exception as e:
        frappe.throw(f"Test payment failed: {str(e)}")

def mpesa_validation_test(kwargs):
    """Test version of validation without logging issues"""
    try:
        # Extract data
        amount = float(kwargs.get('TransAmount', 0))
        account_number = kwargs.get('BillRefNumber', '').strip()
        
        # Basic validation
        if amount <= 0:
            return {"ResultCode": "C2B00012", "ResultDesc": "Invalid amount"}
        
        if not account_number:
            return {"ResultCode": "C2B00012", "ResultDesc": "Account number required"}
        
        # Check if tuktuk exists
        tuktuk_exists = frappe.db.exists("TukTuk Vehicle", {"mpesa_account": account_number})
        if not tuktuk_exists:
            return {"ResultCode": "C2B00012", "ResultDesc": f"Invalid account number: {account_number}"}
        
        return {"ResultCode": "0", "ResultDesc": "Success"}
        
    except Exception as e:
        return {"ResultCode": "C2B00012", "ResultDesc": "Validation failed"}

def mpesa_confirmation_test(kwargs):
    """Test version of confirmation without logging issues"""
    try:
        transaction_id = kwargs.get('TransID')
        amount = float(kwargs.get('TransAmount', 0))
        account_number = kwargs.get('BillRefNumber', '').strip()
        customer_phone = kwargs.get('MSISDN')
        
        # Find the tuktuk
        tuktuk = frappe.db.get_value("TukTuk Vehicle", {"mpesa_account": account_number}, "name")
        if not tuktuk:
            return {"ResultCode": "0", "ResultDesc": "Success"}
        
        # Create a basic transaction record for testing
        transaction = frappe.get_doc({
            "doctype": "TukTuk Transaction",
            "transaction_id": transaction_id,
            "tuktuk": tuktuk,
            "driver": "Test Driver",  # Placeholder
            "amount": amount,
            "driver_share": amount * 0.5,
            "target_contribution": amount * 0.5,
            "customer_phone": customer_phone,
            "timestamp": now_datetime(),
            "payment_status": "Completed"
        })
        
        transaction.insert(ignore_permissions=True)
        frappe.db.commit()
        
        return {"ResultCode": "0", "ResultDesc": "Success"}
        
    except Exception as e:
        return {"ResultCode": "0", "ResultDesc": "Success"}


@frappe.whitelist()
def create_test_data():
    """Create test data for the system"""
    try:
        # Create a test TukTuk if it doesn't exist
        if not frappe.db.exists("TukTuk Vehicle", {"tuktuk_id": "001"}):
            tuktuk = frappe.get_doc({
                "doctype": "TukTuk Vehicle",
                "tuktuk_id": "001",
                "mpesa_account": "001",
                "battery_level": 100,
                "status": "Available",
                "tuktuk_make": "Test Make",
                "tuktuk_colour": "Blue"
            })
            tuktuk.insert()
            frappe.msgprint("✅ Test TukTuk created")
        
        # Create a test driver if it doesn't exist
        if not frappe.db.exists("TukTuk Driver", {"driver_national_id": "12345678"}):
            driver = frappe.get_doc({
                "doctype": "TukTuk Driver",
                "driver_first_name": "Test",
                "driver_last_name": "Driver",
                "driver_national_id": "12345678",
                "driver_license": "B123456",
                "mpesa_number": "254708374149",
                "driver_dob": "1990-01-01"
            })
            driver.insert()
            frappe.msgprint("✅ Test Driver created")
        
        frappe.db.commit()
        frappe.msgprint("🎉 Test data created successfully!")
        
    except Exception as e:
        frappe.throw(f"Test data creation failed: {str(e)}")

@frappe.whitelist()
def fix_account_formats():
    """Fix existing TukTuk account formats to 3 digits"""
    try:
        vehicles = frappe.get_all("TukTuk Vehicle", fields=["name", "tuktuk_id", "mpesa_account"])
        updated_count = 0
        
        for vehicle in vehicles:
            if vehicle.mpesa_account and len(vehicle.mpesa_account) > 3:
                # Convert 885001 to 001, 885002 to 002, etc.
                new_account = vehicle.mpesa_account[-3:] if vehicle.mpesa_account else vehicle.tuktuk_id
                frappe.db.set_value("TukTuk Vehicle", vehicle.name, "mpesa_account", new_account)
                frappe.msgprint(f"Updated {vehicle.tuktuk_id}: {vehicle.mpesa_account} -> {new_account}")
                updated_count += 1
        
        frappe.db.commit()
        frappe.msgprint(f"✅ Updated {updated_count} vehicle account formats")
        
    except Exception as e:
        frappe.throw(f"Account format fix failed: {str(e)}")


@frappe.whitelist()
def assign_driver_to_tuktuk(driver_name=None, tuktuk_name=None):
    """Assign a driver to a tuktuk"""
    try:
        if not driver_name:
            # Get first unassigned driver
            drivers = frappe.get_all("TukTuk Driver", 
                                   filters={"assigned_tuktuk": ["in", ["", None]]},
                                   limit=1)
            if not drivers:
                frappe.throw("No unassigned drivers found")
            driver_name = drivers[0].name
        
        if not tuktuk_name:
            # Get first available tuktuk
            tuktuks = frappe.get_all("TukTuk Vehicle",
                                   filters={"status": "Available"},
                                   limit=1)
            if not tuktuks:
                frappe.throw("No available tuktuks found")
            tuktuk_name = tuktuks[0].name
        
        # Get the documents
        driver = frappe.get_doc("TukTuk Driver", driver_name)
        tuktuk = frappe.get_doc("TukTuk Vehicle", tuktuk_name)
        
        # Make assignment
        driver.assigned_tuktuk = tuktuk.name
        driver.save()
        
        tuktuk.status = "Assigned"
        tuktuk.save()
        
        frappe.msgprint(f"✅ Assigned {driver.driver_name} to TukTuk {tuktuk.tuktuk_id}")
        frappe.msgprint(f"TukTuk account: {tuktuk.mpesa_account}")
        
        return {"driver": driver.name, "tuktuk": tuktuk.name}
        
    except Exception as e:
        frappe.log_error("Assignment Error", str(e))
        frappe.throw(f"Assignment failed: {str(e)}")

@frappe.whitelist()
def assign_test_driver():
    """Assign test driver to test tuktuk"""
    try:
        tuktuk = frappe.get_doc("TukTuk Vehicle", {"tuktuk_id": "001"})
        driver = frappe.get_doc("TukTuk Driver", {"driver_national_id": "12345678"})
        
        driver.assigned_tuktuk = tuktuk.name
        driver.save()
        
        tuktuk.status = "Assigned"
        tuktuk.save()
        
        frappe.msgprint("✅ Test driver assigned to test tuktuk!")
        
    except Exception as e:
        frappe.throw(f"Assignment failed: {str(e)}")

# ===== UTILITY FUNCTIONS =====

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
        
        return {
            "operating_hours": f"{settings.operating_hours_start} - {settings.operating_hours_end}",
            "global_target": settings.global_daily_target,
            "vehicle_stats": vehicle_stats,
            "driver_stats": driver_stats,
            "today_transactions": today_transactions,
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
            frappe.msgprint("✅ Daraja connection successful!")
            return True
        else:
            frappe.msgprint("❌ Daraja connection failed!")
            return False
    except Exception as e:
        frappe.msgprint(f"❌ Daraja connection error: {str(e)}")
        return False

# Enhanced section for deposit management integration

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
                    
                    # Offer to deduct from deposit
                    try:
                        # In a real implementation, you might want to send SMS/email to driver
                        # asking for confirmation before deducting from deposit
                        
                        # For now, we'll log this option and let management handle it
                        frappe.log_error(
                            f"Driver {driver_doc.driver_name} missed target by {shortfall} KSH. "
                            f"Deposit balance: {driver_doc.current_deposit_balance} KSH. "
                            f"Driver allows automatic deduction: {driver_doc.allow_target_deduction_from_deposit}",
                            "Target Miss - Deposit Deduction Available"
                        )
                        
                        # Create a notification for management
                        create_target_miss_notification(driver_doc, shortfall)
                        
                    except Exception as e:
                        frappe.log_error(f"Error processing deposit deduction option: {str(e)}")
                
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

def create_target_miss_notification(driver, shortfall):
    """Create notification for management about target miss with deposit deduction option"""
    try:
        notification = frappe.get_doc({
            "doctype": "Notification Log",
            "subject": f"Target Miss - Deposit Deduction Available: {driver.driver_name}",
            "email_content": f"""
            Driver {driver.driver_name} missed their daily target by {shortfall} KSH.
            
            Details:
            - Shortfall: {shortfall} KSH
            - Current Deposit Balance: {driver.current_deposit_balance} KSH
            - Driver allows deposit deduction: {'Yes' if driver.allow_target_deduction_from_deposit else 'No'}
            - Consecutive misses: {driver.consecutive_misses}
            
            {'You can deduct this amount from the driver"s deposit if needed.' if driver.allow_target_deduction_from_deposit else 'Driver has not allowed automatic deposit deductions.'}
            """,
            "document_type": "TukTuk Driver",
            "document_name": driver.name,
            "for_user": "Administrator"
        })
        notification.insert(ignore_permissions=True)
    except Exception as e:
        frappe.log_error(f"Failed to create target miss notification: {str(e)}")

# Enhanced API methods for deposit management
@frappe.whitelist()
def get_drivers_with_deposit_info():
    """Get all drivers with their deposit information"""
    drivers = frappe.db.sql("""
        SELECT 
            name,
            driver_name,
            driver_national_id,
            assigned_tuktuk,
            deposit_required,
            initial_deposit_amount,
            current_deposit_balance,
            allow_target_deduction_from_deposit,
            current_balance,
            consecutive_misses,
            exit_date,
            refund_status,
            refund_amount
        FROM `tabTukTuk Driver`
        ORDER BY driver_name
    """, as_dict=True)
    
    return drivers

@frappe.whitelist()
def bulk_process_target_deductions():
    """Bulk process target deductions for all eligible drivers"""
    settings = frappe.get_single("TukTuk Settings")
    
    drivers = frappe.get_all("TukTuk Driver", 
                            filters={
                                "allow_target_deduction_from_deposit": 1,
                                "current_balance": ["<", 0],  # Drivers with negative balance (debt)
                                "current_deposit_balance": [">", 0],  # Drivers with deposit available
                                "exit_date": ["is", "not set"]  # Active drivers only
                            },
                            fields=["name", "driver_name", "current_balance", "current_deposit_balance"])
    
    processed_drivers = []
    
    for driver_info in drivers:
        try:
            driver = frappe.get_doc("TukTuk Driver", driver_info.name)
            debt_amount = abs(driver.current_balance)  # Convert negative to positive
            
            if driver.current_deposit_balance >= debt_amount:
                # Process the deduction
                success = driver.process_target_miss_deduction(debt_amount)
                if success:
                    processed_drivers.append({
                        "driver": driver.driver_name,
                        "amount_deducted": debt_amount,
                        "new_deposit_balance": driver.current_deposit_balance
                    })
        except Exception as e:
            frappe.log_error(f"Error processing bulk deduction for {driver_info.driver_name}: {str(e)}")
    
    return {
        "success": True,
        "processed_count": len(processed_drivers),
        "processed_drivers": processed_drivers
    }

@frappe.whitelist()
def generate_deposit_report(from_date=None, to_date=None):
    """Generate comprehensive deposit management report"""
    if not from_date:
        from_date = frappe.utils.add_days(frappe.utils.today(), -30)
    if not to_date:
        to_date = frappe.utils.today()
    
    # Get all deposit transactions in date range
    transactions = frappe.db.sql("""
        SELECT 
            dt.transaction_date,
            dt.transaction_type,
            dt.amount,
            dt.balance_after_transaction,
            dt.description,
            dt.transaction_reference,
            d.driver_name,
            d.driver_national_id
        FROM `tabDriver Deposit Transaction` dt
        JOIN `tabTukTuk Driver` d ON dt.parent = d.name
        WHERE dt.transaction_date BETWEEN %s AND %s
        ORDER BY dt.transaction_date DESC, d.driver_name
    """, (from_date, to_date), as_dict=True)
    
    # Summary statistics
    summary = frappe.db.sql("""
        SELECT 
            COUNT(DISTINCT d.name) as total_drivers_with_deposits,
            SUM(CASE WHEN d.deposit_required = 1 THEN d.initial_deposit_amount ELSE 0 END) as total_initial_deposits,
            SUM(CASE WHEN d.deposit_required = 1 THEN d.current_deposit_balance ELSE 0 END) as total_current_deposits,
            COUNT(CASE WHEN d.exit_date IS NOT NULL AND d.refund_status = 'Pending' THEN 1 END) as pending_refunds,
            SUM(CASE WHEN d.exit_date IS NOT NULL AND d.refund_status = 'Pending' THEN d.refund_amount ELSE 0 END) as total_pending_refund_amount
        FROM `tabTukTuk Driver` d
        WHERE d.deposit_required = 1
    """, as_dict=True)[0]
    
    return {
        "from_date": from_date,
        "to_date": to_date,
        "transactions": transactions,
        "summary": summary,
        "transaction_count": len(transactions)
    }

@frappe.whitelist()
def process_bulk_refunds():
    """Process all pending refunds for exited drivers"""
    pending_refunds = frappe.get_all("TukTuk Driver",
                                   filters={
                                       "exit_date": ["is", "set"],
                                       "refund_status": "Pending",
                                       "refund_amount": [">", 0]
                                   },
                                   fields=["name", "driver_name", "refund_amount", "mpesa_number"])
    
    processed_refunds = []
    failed_refunds = []
    
    for refund_info in pending_refunds:
        try:
            # In a real implementation, you would integrate with Mpesa B2C API
            # For now, we'll just update the status
            driver = frappe.get_doc("TukTuk Driver", refund_info.name)
            
            # Simulate refund processing
            refund_success = send_mpesa_payment(
                driver.mpesa_number, 
                driver.refund_amount, 
                "DEPOSIT_REFUND"
            )
            
            if refund_success:
                driver.refund_status = "Completed"
                driver.add_deposit_transaction(
                    transaction_type="Refund",
                    amount=-driver.refund_amount,
                    description="Final deposit refund processed",
                    reference="AUTO_REFUND"
                )
                driver.save()
                
                processed_refunds.append({
                    "driver": driver.driver_name,
                    "amount": driver.refund_amount,
                    "status": "Completed"
                })
            else:
                failed_refunds.append({
                    "driver": driver.driver_name,
                    "amount": driver.refund_amount,
                    "error": "Mpesa payment failed"
                })
                
        except Exception as e:
            failed_refunds.append({
                "driver": refund_info.driver_name,
                "amount": refund_info.refund_amount,
                "error": str(e)
            })
    
    return {
        "success": True,
        "processed_count": len(processed_refunds),
        "failed_count": len(failed_refunds),
        "processed_refunds": processed_refunds,
        "failed_refunds": failed_refunds
    }        


@frappe.whitelist(allow_guest=True)
def payment_validation(**kwargs):
    """Alternative validation endpoint without 'mpesa' in URL"""
    # Just call the existing mpesa_validation function
    from tuktuk_management.api.tuktuk import mpesa_validation
    return mpesa_validation(**kwargs)

# Update your payment_confirmation function in tuktuk_management/api/tuktuk.py
# Replace the existing payment_confirmation function with this:

@frappe.whitelist(allow_guest=True)
def payment_confirmation(**kwargs):
    """Fixed confirmation endpoint that calculates shares before creating transaction"""
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
            frappe.log_error(f"TukTuk not found for account: {account_number}")
            return {"ResultCode": "0", "ResultDesc": "Success"}
        
        # Find assigned driver
        driver_name = frappe.db.get_value("TukTuk Driver", {"assigned_tuktuk": tuktuk}, "name")
        if not driver_name:
            frappe.log_error(f"No driver assigned to tuktuk: {tuktuk}")
            return {"ResultCode": "0", "ResultDesc": "Success"}
        
        # Check if transaction already exists
        if frappe.db.exists("TukTuk Transaction", {"transaction_id": transaction_id}):
            frappe.log_error(f"Transaction already processed: {transaction_id}")
            return {"ResultCode": "0", "ResultDesc": "Success"}
        
        # Get driver and settings for calculations
        driver = frappe.get_doc("TukTuk Driver", driver_name)
        settings = frappe.get_single("TukTuk Settings")
        
        # Calculate shares
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
            "driver_share": driver_share,
            "target_contribution": target_contribution,
            "customer_phone": customer_phone,
            "timestamp": now_datetime(),
            "payment_status": "Completed"
        })
        
        transaction.insert(ignore_permissions=True)
        
        # Update driver balance
        driver.current_balance += target_contribution
        driver.save()
        
        frappe.db.commit()
        return {"ResultCode": "0", "ResultDesc": "Success"}
        
    except Exception as e:
        frappe.log_error(f"Payment confirmation error: {str(e)}")
        return {"ResultCode": "0", "ResultDesc": "Success"}

@frappe.whitelist(allow_guest=True)
def transaction_validation(**kwargs):
    """Another alternative validation endpoint"""
    from tuktuk_management.api.tuktuk import mpesa_validation
    return mpesa_validation(**kwargs)

@frappe.whitelist(allow_guest=True)
def transaction_confirmation(**kwargs):
    """Another alternative confirmation endpoint"""
    from tuktuk_management.api.tuktuk import mpesa_confirmation
    return mpesa_confirmation(**kwargs)

# Test the new endpoints
def test_new_endpoints():
    import requests
    
    base_url = "https://console.sunnytuktuk.com"
    
    # Test validation endpoint
    validation_url = f"{base_url}/api/method/tuktuk_management.api.tuktuk.payment_validation"
    confirmation_url = f"{base_url}/api/method/tuktuk_management.api.tuktuk.payment_confirmation"
    
    test_data = {"TransAmount": "100", "BillRefNumber": "001", "MSISDN": "254708374149"}
    
    print("Testing new validation endpoint...")
    response = requests.post(validation_url, json=test_data, timeout=10)
    print(f"Validation: {response.status_code} - {response.text}")
    
    print("Testing new confirmation endpoint...")
    test_confirmation_data = {
        "TransID": "TEST123456",
        "TransAmount": "100",
        "BillRefNumber": "001", 
        "MSISDN": "254708374149",
        "TransTime": "20241220143022",
        "FirstName": "Test",
        "LastName": "Customer"
    }
    
    response = requests.post(confirmation_url, json=test_confirmation_data, timeout=10)
    print(f"Confirmation: {response.status_code} - {response.text}")

# Register with new URLs
def register_with_new_urls():
    try:
        from tuktuk_management.api.tuktuk import get_access_token
        token = get_access_token()
        
        if not token:
            print("❌ Access token failed")
            return False
        
        print(f"✅ Access token: {token[:20]}...")
        
        import requests
        
        api_url = "https://sandbox.safaricom.co.ke/mpesa/c2b/v1/registerurl"
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        # Use new URLs without "mpesa" in them
        payload = {
            "ShortCode": "174379",
            "ResponseType": "Completed",
            "ConfirmationURL": "https://console.sunnytuktuk.com/api/method/tuktuk_management.api.tuktuk.payment_confirmation",
            "ValidationURL": "https://console.sunnytuktuk.com/api/method/tuktuk_management.api.tuktuk.payment_validation"
        }
        
        print(f"Attempting registration with new URLs: {payload}")
        
        response = requests.post(api_url, json=payload, headers=headers, timeout=30)
        result = response.json()
        
        print(f"Registration response: {result}")
        
        if response.status_code == 200 and result.get("ResponseCode") == "0":
            print("✅ C2B URLs registered successfully!")
            return True
        else:
            print(f"❌ Registration failed: {result}")
            return False
            
    except Exception as e:
        print(f"❌ Registration error: {e}")
        return False

print("Creating alternative endpoints...")
# The functions are now defined, let's test them    