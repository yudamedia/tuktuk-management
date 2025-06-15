# ~/frappe-bench/apps/tuktuk_management/tuktuk_management/api/tuktuk.py

import frappe
from frappe.utils import now_datetime, get_time, get_datetime
from datetime import datetime, time

def is_within_operating_hours():
    settings = frappe.get_single("TukTuk Settings")
    current_time = get_time(now_datetime())
    start_time = get_time(settings.operating_hours_start)
    end_time = get_time(settings.operating_hours_end)
    
    if end_time < start_time:  # Handles overnight period
        return current_time >= start_time or current_time <= end_time
    return start_time <= current_time <= end_time

def reset_daily_targets():
    """Reset daily targets for all active drivers"""
    settings = frappe.get_single("TukTuk Settings")
    
    if not is_within_operating_hours():
        return
        
    drivers = frappe.get_all("TukTuk Driver", 
                            filters={"assigned_tuktuk": ["!=", ""]},
                            fields=["driver_national_id"])
    
    for driver in drivers:
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
            driver_doc.current_balance = shortfall
        else:
            driver_doc.consecutive_misses = 0
            # Pay bonus if enabled
            if settings.bonus_enabled and settings.bonus_amount:
                send_mpesa_payment(driver_doc.mpesa_number, settings.bonus_amount)
            driver_doc.current_balance = 0
            
        driver_doc.save()

def terminate_driver(driver):
    """Terminate driver and free up their tuktuk"""
    if driver.assigned_tuktuk:
        tuktuk = frappe.get_doc("TukTuk Vehicle", driver.assigned_tuktuk)
        tuktuk.status = "Available"
        tuktuk.save()
    
    driver.assigned_tuktuk = ""
    driver.save()

def send_mpesa_payment(mpesa_number, amount):
    """Send payment to driver via MPesa B2C"""
    settings = frappe.get_single("TukTuk Settings")
    try:
        # Implement MPesa B2C API call using:
        # - settings.mpesa_api_key
        # - settings.mpesa_api_secret
        # - settings.mpesa_paybill
        # - mpesa_number (driver's mpesa number)
        # - amount
        
        # Record the payment attempt
        frappe.get_doc({
            "doctype": "TukTuk Transaction",
            "transaction_id": "B2C_" + now_datetime().strftime("%Y%m%d%H%M%S"),
            "amount": amount,
            "payment_status": "Completed",
            "timestamp": now_datetime(),
            "customer_phone": mpesa_number
        }).insert()
        
        return True
    except Exception as e:
        frappe.log_error(f"MPesa Payment Failed: {str(e)}")
        return False

def handle_mpesa_payment(doc, method):
    """Handle incoming Mpesa payments"""
    if not is_within_operating_hours():
        doc.payment_status = "Failed"
        doc.save()
        return
        
    settings = frappe.get_single("TukTuk Settings")
    
    driver = frappe.get_all(
        "TukTuk Driver",
        filters={"assigned_tuktuk": doc.tuktuk},
        fields=["driver_national_id", "mpesa_number"],
        limit=1
    )
    
    if not driver:
        doc.payment_status = "Failed"
        doc.save()
        return
        
    try:
        driver_doc = frappe.get_doc("TukTuk Driver", {
            "driver_national_id": driver[0].driver_national_id
        })
        
        amount = doc.amount
        percentage = driver_doc.fare_percentage or settings.global_fare_percentage
        target = driver_doc.daily_target or settings.global_daily_target
        
        if driver_doc.current_balance >= target:
            doc.driver_share = amount
            doc.target_contribution = 0
        else:
            doc.driver_share = amount * (percentage / 100)
            doc.target_contribution = amount - doc.driver_share
            
        if send_mpesa_payment(driver_doc.mpesa_number, doc.driver_share):
            if doc.target_contribution:
                driver_doc.current_balance += doc.target_contribution
            
            doc.payment_status = "Completed"
            doc.save()
            driver_doc.save()
        else:
            doc.payment_status = "Failed"
            doc.save()
            
    except Exception as e:
        frappe.log_error(f"Payment Processing Failed: {str(e)}")
        doc.payment_status = "Failed"
        doc.save()

def get_tuktuk_for_rental():
    """Get available tuktuk for rental"""
    return frappe.get_all(
        "TukTuk Vehicle",
        filters={
            "status": "Available"
        },
        fields=["tuktuk_id", "rental_rate_initial", "rental_rate_hourly"]
    )

def start_rental(driver_id, tuktuk_id, start_time):
    """Start a tuktuk rental"""
    settings = frappe.get_single("TukTuk Settings")
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
