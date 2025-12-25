# ~/frappe-bench/apps/tuktuk_management/tuktuk_management/api/driver_auth.py

import frappe
from frappe import _
from frappe.utils import now_datetime, today, get_datetime, add_to_date, format_date, format_datetime, getdate
import re
import random
import string

# ===== TUKTUK DRIVER USER ACCOUNT MANAGEMENT =====

@frappe.whitelist()
def create_tuktuk_driver_user_account(tuktuk_driver_name):
    """Create user account for tuktuk driver login"""
    try:
        tuktuk_driver = frappe.get_doc("TukTuk Driver", tuktuk_driver_name)
        
        # Extract number from driver name by stripping "DRV-" prefix
        if not tuktuk_driver_name.startswith("DRV-"):
            frappe.throw(f"Invalid driver name format. Expected format: DRV-112###, got: {tuktuk_driver_name}")
        
        driver_number = tuktuk_driver_name.replace("DRV-", "", 1)
        
        # Validate that we got a number
        if not driver_number.isdigit():
            frappe.throw(f"Invalid driver name format. Expected numbers after 'DRV-', got: {driver_number}")
        
        # Create user email from the extracted number
        user_email = f"{driver_number}@sunnytuktuk.com"
        
        # Check if user already exists
        if frappe.db.exists("User", user_email):
            frappe.msgprint(f"User account already exists for {user_email}")
            return user_email
        
        # Generate a simple password
        password = generate_tuktuk_driver_password()
        
        # Create user account
        user = frappe.get_doc({
            "doctype": "User",
            "email": user_email,
            "username": driver_number,
            "first_name": tuktuk_driver.driver_first_name,
            "last_name": tuktuk_driver.driver_last_name,
            "full_name": tuktuk_driver.driver_name,
            "mobile_no": tuktuk_driver.driver_primary_phone,
            "phone": tuktuk_driver.driver_primary_phone,
            "user_type": "System User",
            "send_welcome_email": 0,  # We'll send custom instructions
            "new_password": password,
            "roles": [
                {"role": "TukTuk Driver"}
            ]
        })
        
        user.insert(ignore_permissions=True)
        
        # Link driver to user account
        tuktuk_driver.user_account = user_email
        tuktuk_driver.save()
        
        # Send login credentials via SMS
        send_tuktuk_driver_login_sms(tuktuk_driver.driver_primary_phone, user_email, password, tuktuk_driver.driver_name)
        
        frappe.msgprint(f"✅ TukTuk driver account created: {user_email}")
        return user_email
        
    except Exception as e:
        frappe.log_error(f"Failed to create tuktuk driver account: {str(e)}")
        frappe.throw(f"Failed to create tuktuk driver account: {str(e)}")

def generate_tuktuk_driver_password():
    """Generate a simple 8-character password"""
    # Use combination of letters and numbers for simplicity
    chars = string.ascii_uppercase + string.digits
    password = ''.join(random.choice(chars) for _ in range(8))
    return password

def send_tuktuk_driver_login_sms(phone, email, password, tuktuk_driver_name):
    """Send login credentials via SMS"""
    message = f"""Welcome to Sunny TukTuk, {tuktuk_driver_name}!

Your login details:
Website: https://console.sunnytuktuk.com
Email: {email}
Password: {password}

Please change your password after first login.
Support: Call management for help."""
    
    # TODO: Implement actual SMS gateway integration
    # For now, log the message and create a notification
    frappe.log_error(f"SMS to {phone}: {message}", "TukTuk Driver Login SMS")
    
    # Create a notification log for management to manually send
    try:
        notification = frappe.get_doc({
            "doctype": "Notification Log",
            "subject": f"TukTuk Driver Login Credentials - {tuktuk_driver_name}",
            "email_content": f"""
            <h3>TukTuk Driver Login Credentials Created</h3>
            <p><strong>Driver:</strong> {tuktuk_driver_name}</p>
            <p><strong>Phone:</strong> {phone}</p>
            <p><strong>Email:</strong> {email}</p>
            <p><strong>Password:</strong> {password}</p>
            <hr>
            <p><strong>SMS Message to Send:</strong></p>
            <pre>{message}</pre>
            """,
            "document_type": "TukTuk Driver",
            "for_user": "Administrator"
        })
        notification.insert(ignore_permissions=True)
    except Exception as e:
        frappe.log_error(f"Failed to create notification: {str(e)}")

@frappe.whitelist()
def create_all_tuktuk_driver_accounts():
    """Create user accounts for all tuktuk drivers who don't have one"""
    try:
        tuktuk_drivers = frappe.get_all("TukTuk Driver",
                                filters={"user_account": ["in", ["", None]]},
                                fields=["name", "driver_name"])
        
        if not tuktuk_drivers:
            frappe.msgprint("All TukTuk drivers already have user accounts!")
            return []
        
        created_accounts = []
        failed_accounts = []
        
        for tuktuk_driver in tuktuk_drivers:
            try:
                email = create_tuktuk_driver_user_account(tuktuk_driver.name)
                created_accounts.append({
                    "tuktuk_driver": tuktuk_driver.driver_name,
                    "email": email
                })
            except Exception as e:
                failed_accounts.append({
                    "tuktuk_driver": tuktuk_driver.driver_name,
                    "error": str(e)
                })
                frappe.log_error(f"Failed to create account for {tuktuk_driver.driver_name}: {str(e)}")
        
        frappe.msgprint(f"✅ Created {len(created_accounts)} tuktuk driver accounts. {len(failed_accounts)} failed.")
        
        if failed_accounts:
            frappe.msgprint(f"❌ Failed accounts: {', '.join([f['tuktuk_driver'] for f in failed_accounts])}")
        
        return {
            "created": created_accounts,
            "failed": failed_accounts
        }
        
    except Exception as e:
        frappe.throw(f"Bulk account creation failed: {str(e)}")

@frappe.whitelist()
def reset_tuktuk_driver_password(tuktuk_driver_name):
    """Reset password for a tuktuk driver"""
    try:
        tuktuk_driver = frappe.get_doc("TukTuk Driver", tuktuk_driver_name)
        
        if not tuktuk_driver.user_account:
            frappe.throw("TukTuk driver does not have a user account")
        
        user = frappe.get_doc("User", tuktuk_driver.user_account)
        new_password = generate_tuktuk_driver_password()
        
        user.new_password = new_password
        user.save()
        
        # Send new password via SMS
        send_tuktuk_driver_login_sms(
            tuktuk_driver.driver_primary_phone, 
            tuktuk_driver.user_account, 
            new_password,
            tuktuk_driver.driver_name
        )
        
        frappe.msgprint(f"✅ Password reset for {tuktuk_driver.driver_name}")
        return new_password
        
    except Exception as e:
        frappe.throw(f"Password reset failed: {str(e)}")

# ===== TUKTUK DRIVER PORTAL DATA FUNCTIONS =====

@frappe.whitelist()
def get_tuktuk_driver_dashboard_data():
    """Get dashboard data for logged-in tuktuk driver"""
    try:
        # Check if user is logged in and is a driver
        if frappe.session.user == "Guest":
            frappe.throw(_("Please login to access tuktuk driver dashboard"), frappe.PermissionError)
        
        user_roles = frappe.get_roles(frappe.session.user)
        if "TukTuk Driver" not in user_roles:
            frappe.throw(_("Access denied - TukTuk Driver role required"), frappe.PermissionError)
        
        # Get driver details
        tuktuk_driver = frappe.get_all("TukTuk Driver", 
                               filters={"user_account": frappe.session.user},
                               fields=["*"],
                               limit=1)
        
        if not tuktuk_driver:
            frappe.throw(_("TukTuk driver record not found"))
        
        tuktuk_driver = tuktuk_driver[0]
        
        # Get assigned tuktuk
        tuktuk = None
        if tuktuk_driver.assigned_tuktuk:
            tuktuk_data = frappe.get_doc("TukTuk Vehicle", tuktuk_driver.assigned_tuktuk)
            tuktuk = {
                "tuktuk_id": tuktuk_data.tuktuk_id,
                "battery_level": tuktuk_data.battery_level,
                "status": tuktuk_data.status,
                "mpesa_account": tuktuk_data.mpesa_account
            }
        
        # Get recent transactions (last 10)
        transactions = frappe.get_all("TukTuk Transaction",
                                     filters={"driver": tuktuk_driver.name},
                                     fields=["timestamp", "amount", "driver_share", "target_contribution", "payment_status"],
                                     order_by="timestamp desc",
                                     limit=10)
        
        # Format transaction timestamps for template
        for transaction in transactions:
            transaction.timestamp_formatted = format_datetime(transaction.timestamp, "dd MMM yyyy, hh:mm a")
        
        # Get current rentals
        rentals = frappe.get_all("TukTuk Rental",
                                filters={"driver": tuktuk_driver.name, "status": "Active"},
                                fields=["rented_tuktuk", "start_time", "rental_fee"])
        
        # Format rental start times for template
        for rental in rentals:
            rental.start_time_formatted = format_datetime(rental.start_time, "dd MMM yyyy, hh:mm a")
        
        # Calculate today's earnings
        today_transactions = frappe.get_all("TukTuk Transaction",
                                           filters={
                                               "driver": tuktuk_driver.name,
                                               "timestamp": [">=", today()],
                                               "payment_status": "Completed",
                                               "transaction_type": ["not in", ["Adjustment", "Driver Repayment"]]  # Exclude adjustments and repayments from earnings
                                           },
                                           fields=["driver_share", "target_contribution"])
        
        today_earnings = sum([t.driver_share for t in today_transactions])
        today_target_contribution = sum([t.target_contribution for t in today_transactions])
        
        # Get settings for target calculation
        settings = frappe.get_single("TukTuk Settings")
        daily_target = tuktuk_driver.daily_target or settings.global_daily_target

        # Calculate target progress always (for dashboard display) regardless of sharing setting
        if daily_target > 0:
            target_progress = min((tuktuk_driver.current_balance / daily_target) * 100, 100)
        else:
            target_progress = 0
        
        return {
            "tuktuk_driver": {
                "name": tuktuk_driver.driver_name,
                "current_balance": tuktuk_driver.current_balance,
                "consecutive_misses": tuktuk_driver.consecutive_misses,
                "mpesa_number": tuktuk_driver.mpesa_number
            },
            "tuktuk": tuktuk,
            "transactions": transactions,
            "rentals": rentals,
            "today_earnings": today_earnings,
            "today_target_contribution": today_target_contribution,
            "daily_target": daily_target,
            "target_progress": target_progress,
            "today_date": format_date(today(), "dd MMM yyyy"),
            "operating_hours": {
                "start": settings.operating_hours_start,
                "end": settings.operating_hours_end
            }
        }
        
    except Exception as e:
        frappe.log_error(f"TukTuk driver dashboard data error: {str(e)}")
        frappe.throw(f"Failed to load tuktuk driver dashboard data: {str(e)}")

@frappe.whitelist()
def get_driver_target_data():
    """Get target progress data with left_to_target for logged-in driver"""
    try:
        tuktuk_driver = get_current_tuktuk_driver()
        settings = frappe.get_single("TukTuk Settings")
        
        daily_target = tuktuk_driver.daily_target or settings.global_daily_target
        current_balance = tuktuk_driver.current_balance or 0
        left_to_target = tuktuk_driver.left_to_target or 0
        
        # Calculate progress percentage
        if daily_target > 0:
            target_progress = min((current_balance / daily_target) * 100, 100)
        else:
            target_progress = 0
        
        return {
            "daily_target": daily_target,
            "current_balance": current_balance,
            "left_to_target": left_to_target,
            "target_progress": target_progress,
            "assigned_tuktuk": tuktuk_driver.assigned_tuktuk or None
        }
    except Exception as e:
        frappe.log_error(f"Driver target data error: {str(e)}")
        frappe.throw(f"Failed to load target data: {str(e)}")

@frappe.whitelist()
def get_driver_transactions(limit=5):
    """Get latest transactions for logged-in driver"""
    try:
        tuktuk_driver = get_current_tuktuk_driver()
        
        transactions = frappe.get_all("TukTuk Transaction",
                                     filters={"driver": tuktuk_driver.name},
                                     fields=[
                                         "name", "timestamp", "transaction_id", "amount",
                                         "driver_share", "target_contribution",
                                         "payment_status", "transaction_type"
                                     ],
                                     order_by="timestamp desc",
                                     limit=int(limit))
        
        # Format timestamps
        for transaction in transactions:
            transaction.timestamp_formatted = format_datetime(transaction.timestamp, "dd MMM yyyy, hh:mm a")
        
        return {
            "transactions": transactions,
            "count": len(transactions)
        }
    except Exception as e:
        frappe.log_error(f"Driver transactions error: {str(e)}")
        frappe.throw(f"Failed to load transactions: {str(e)}")

@frappe.whitelist()
def get_driver_deposit_data():
    """Get deposit balance and transaction history for logged-in driver"""
    try:
        tuktuk_driver = get_current_tuktuk_driver()
        
        # Get deposit transactions
        deposit_transactions = []
        if tuktuk_driver.deposit_transactions:
            for dt in tuktuk_driver.deposit_transactions:
                deposit_transactions.append({
                    "transaction_date": dt.transaction_date,
                    "transaction_type": dt.transaction_type,
                    "amount": dt.amount,
                    "balance_after_transaction": dt.balance_after_transaction,
                    "description": dt.description or dt.transaction_type,
                    "transaction_reference": dt.transaction_reference or ""
                })
        
        # Sort by date descending
        deposit_transactions.sort(key=lambda x: x.get("transaction_date", ""), reverse=True)
        
        return {
            "current_deposit_balance": tuktuk_driver.current_deposit_balance or 0,
            "initial_deposit_amount": tuktuk_driver.initial_deposit_amount or 0,
            "deposit_required": tuktuk_driver.deposit_required or 0,
            "deposit_transactions": deposit_transactions[:20],  # Latest 20
            "transaction_count": len(deposit_transactions),
            "refund_status": tuktuk_driver.refund_status or "N/A",
            "refund_amount": tuktuk_driver.refund_amount or 0
        }
    except Exception as e:
        frappe.log_error(f"Driver deposit data error: {str(e)}")
        frappe.throw(f"Failed to load deposit data: {str(e)}")

@frappe.whitelist()
def get_driver_performance_data():
    """Get performance metrics including target misses for logged-in driver"""
    try:
        tuktuk_driver = get_current_tuktuk_driver()
        settings = frappe.get_single("TukTuk Settings")
        
        # Calculate today's performance
        today_transactions = frappe.get_all("TukTuk Transaction",
                                           filters={
                                               "driver": tuktuk_driver.name,
                                               "timestamp": [">=", today()],
                                               "payment_status": "Completed",
                                               "transaction_type": ["not in", ["Adjustment", "Driver Repayment"]]
                                           },
                                           fields=["driver_share", "target_contribution", "amount"])
        
        today_earnings = sum([t.driver_share for t in today_transactions])
        today_target_contribution = sum([t.target_contribution for t in today_transactions])
        today_total = sum([t.amount for t in today_transactions])
        
        daily_target = tuktuk_driver.daily_target or settings.global_daily_target
        current_balance = tuktuk_driver.current_balance or 0
        
        return {
            "consecutive_misses": tuktuk_driver.consecutive_misses or 0,
            "current_balance": current_balance,
            "daily_target": daily_target,
            "left_to_target": tuktuk_driver.left_to_target or 0,
            "today_earnings": today_earnings,
            "today_target_contribution": today_target_contribution,
            "today_total": today_total,
            "today_transaction_count": len(today_transactions),
            "operating_hours": {
                "start": settings.operating_hours_start,
                "end": settings.operating_hours_end
            },
            "mpesa_number": tuktuk_driver.mpesa_number or ""
        }
    except Exception as e:
        frappe.log_error(f"Driver performance data error: {str(e)}")
        frappe.throw(f"Failed to load performance data: {str(e)}")

@frappe.whitelist()
def change_driver_password(old_password, new_password):
    """Change password for logged-in driver"""
    try:
        # Check if user is logged in
        if frappe.session.user == "Guest":
            frappe.throw(_("Please login to change password"), frappe.PermissionError)
        
        # Verify user is a driver
        user_roles = frappe.get_roles(frappe.session.user)
        if "TukTuk Driver" not in user_roles:
            frappe.throw(_("Access denied - TukTuk Driver role required"), frappe.PermissionError)
        
        # Get current user
        user = frappe.get_doc("User", frappe.session.user)
        
        # Verify old password using Frappe's password utilities
        from frappe.utils.password import check_password
        
        # check_password expects: check_password(user, pwd, doctype='User', fieldname='password')
        # It will raise AuthenticationError if password is wrong
        try:
            check_password(frappe.session.user, old_password)
        except frappe.AuthenticationError:
            frappe.throw(_("Current password is incorrect"))
        
        # Validate new password
        if not new_password or len(new_password) < 6:
            frappe.throw(_("New password must be at least 6 characters long"))
        
        # Update password in the User doc
        from frappe.utils.password import update_password
        update_password(user=frappe.session.user, pwd=new_password)
        
        frappe.db.commit()
        
        return {
            "success": True,
            "message": _("Password changed successfully")
        }
        
    except frappe.ValidationError:
        raise
    except frappe.AuthenticationError:
        raise
    except Exception as e:
        frappe.log_error(f"Password change error: {str(e)}")
        frappe.throw(f"Failed to change password: {str(e)}")

        
@frappe.whitelist()
def get_driver_roster_data():
    """Get roster schedule and pending requests for logged-in driver"""
    try:
        tuktuk_driver = get_current_tuktuk_driver()
        
        # Get active roster
        active_roster = frappe.get_all(
            "TukTuk Roster Period",
            filters={"status": "Active"},
            limit=1
        )
        
        if not active_roster:
            return {
                "has_active_roster": False,
                "message": "No active roster found",
                "schedule": [],
                "pending_requests": [],
                "roster_period": None
            }
        
        roster = frappe.get_doc("TukTuk Roster Period", active_roster[0]["name"])
        
        # Get driver's schedule (next 14 days)
        from tuktuk_management.tuktuk_management.doctype.tuktuk_roster_period.tuktuk_roster_period import get_driver_schedule
        schedule_data = get_driver_schedule(tuktuk_driver.name, roster.start_date, roster.end_date)
        
        # Get pending switch requests
        from tuktuk_management.api.roster import get_pending_switch_requests
        pending_data = get_pending_switch_requests(tuktuk_driver.name)
        
        # Format schedule dates
        formatted_schedule = []
        for day_off in schedule_data.get("day_offs", []):
            formatted_schedule.append({
                "date": day_off.get("date"),
                "date_formatted": format_date(day_off.get("date"), "dd MMM yyyy (EEE)"),
                "day_off_type": day_off.get("day_off_type", "Scheduled"),
                "switch_status": day_off.get("switch_status"),
                "notes": day_off.get("notes", "")
            })
        
        # Format pending requests - need to find the original off date from roster
        formatted_pending = []
        for req in pending_data.get("pending_requests", []):
            # Find the original off date by looking at the roster
            # The requesting driver's original scheduled off date is stored in a schedule where
            # they are the driver and original_driver matches the current driver
            original_off_date = None
            requesting_driver_id = req.get("requesting_driver")
            
            for schedule in roster.day_off_schedules:
                # Find the schedule where requesting driver is giving up their original off day
                if (schedule.driver == requesting_driver_id and
                    schedule.original_driver == requesting_driver_id and
                    schedule.switched_with_driver == tuktuk_driver.name and
                    schedule.switch_status == "Pending"):
                    original_off_date = schedule.date
                    break
            
            formatted_pending.append({
                "requesting_driver": requesting_driver_id,
                "requesting_driver_name": req.get("requesting_driver_name"),
                "requested_date": req.get("requested_date"),
                "requested_date_formatted": format_date(req.get("requested_date"), "dd MMM yyyy") if req.get("requested_date") else "",
                "my_off_date": original_off_date,
                "my_off_date_formatted": format_date(original_off_date, "dd MMM yyyy") if original_off_date else "",
                "reason": req.get("reason", ""),
                "roster_name": req.get("roster_name")
            })
        
        return {
            "has_active_roster": True,
            "roster_period": {
                "name": roster.name,
                "start_date": roster.start_date,
                "end_date": roster.end_date,
                "start_date_formatted": format_date(roster.start_date, "dd MMM yyyy"),
                "end_date_formatted": format_date(roster.end_date, "dd MMM yyyy")
            },
            "schedule": formatted_schedule,
            "pending_requests": formatted_pending
        }
    except Exception as e:
        frappe.log_error(f"Driver roster data error: {str(e)}")
        return {
            "has_active_roster": False,
            "error": str(e),
            "schedule": [],
            "pending_requests": []
        }

@frappe.whitelist()
def get_available_drivers_for_switch():
    """Get list of other drivers for switch requests"""
    try:
        tuktuk_driver = get_current_tuktuk_driver()
        
        # Get all other assigned drivers
        other_drivers = frappe.get_all(
            "TukTuk Driver",
            filters={
                "name": ["!=", tuktuk_driver.name],
                "assigned_tuktuk": ["is", "set"]
            },
            fields=["name", "driver_name", "sunny_id"],
            order_by="driver_name"
        )
        
        return {
            "success": True,
            "drivers": other_drivers
        }
    except Exception as e:
        frappe.log_error(f"Error getting available drivers: {str(e)}")
        return {
            "success": False,
            "message": str(e),
            "drivers": []
        }

@frappe.whitelist()
def get_tuktuk_driver_transaction_history(limit=50, offset=0):
    """Get transaction history for logged-in tuktuk driver"""
    try:
        # Verify driver access
        tuktuk_driver = get_current_tuktuk_driver()
        
        transactions = frappe.get_all("TukTuk Transaction",
                                     filters={"driver": tuktuk_driver.name},
                                     fields=[
                                         "timestamp", "transaction_id", "amount", 
                                         "driver_share", "target_contribution", 
                                         "payment_status", "customer_phone"
                                     ],
                                     order_by="timestamp desc",
                                     limit=limit,
                                     start=offset)
        
        return transactions
        
    except Exception as e:
        frappe.throw(f"Failed to load transaction history: {str(e)}")

@frappe.whitelist()
def get_tuktuk_driver_rental_history(limit=20, offset=0):
    """Get rental history for logged-in tuktuk driver"""
    try:
        # Verify driver access
        tuktuk_driver = get_current_tuktuk_driver()
        
        rentals = frappe.get_all("TukTuk Rental",
                                filters={"driver": tuktuk_driver.name},
                                fields=[
                                    "rented_tuktuk", "start_time", "end_time",
                                    "rental_fee", "status", "notes"
                                ],
                                order_by="start_time desc",
                                limit=limit,
                                start=offset)
        
        return rentals
        
    except Exception as e:
        frappe.throw(f"Failed to load rental history: {str(e)}")

@frappe.whitelist()
def request_tuktuk_rental():
    """Allow tuktuk driver to request a tuktuk rental"""
    try:
        # Verify driver access
        tuktuk_driver = get_current_tuktuk_driver()
        
        # Check if driver already has an active rental
        existing_rental = frappe.get_all("TukTuk Rental",
                                        filters={"driver": tuktuk_driver.name, "status": "Active"},
                                        limit=1)
        
        if existing_rental:
            frappe.throw("You already have an active rental")
        
        # Find available tuktuks
        available_tuktuks = frappe.get_all("TukTuk Vehicle",
                                          filters={
                                              "status": "Available",
                                              "battery_level": [">", 20]
                                          },
                                          fields=["name", "tuktuk_id", "battery_level", "rental_rate_initial"],
                                          limit=5)
        
        if not available_tuktuks:
            frappe.throw("No TukTuks available for rental at the moment")
        
        return {
            "available_tuktuks": available_tuktuks,
            "tuktuk_driver_name": tuktuk_driver.driver_name
        }
        
    except Exception as e:
        frappe.throw(f"Rental request failed: {str(e)}")

@frappe.whitelist()
def start_tuktuk_rental(tuktuk_name):
    """Start a tuktuk rental for the logged-in tuktuk driver"""
    try:
        # Verify driver access
        tuktuk_driver = get_current_tuktuk_driver()
        
        # Check tuktuk availability
        tuktuk = frappe.get_doc("TukTuk Vehicle", tuktuk_name)
        if tuktuk.status != "Available":
            frappe.throw("Selected TukTuk is no longer available")
        
        # Get settings for rental rates
        settings = frappe.get_single("TukTuk Settings")
        rental_fee = tuktuk.rental_rate_initial or settings.global_rental_initial
        
        # Create rental record
        rental = frappe.get_doc({
            "doctype": "TukTuk Rental",
            "driver": tuktuk_driver.name,
            "rented_tuktuk": tuktuk_name,
            "start_time": now_datetime(),
            "rental_fee": rental_fee,
            "status": "Active",
            "notes": "Self-service rental started via tuktuk driver portal"
        })
        
        rental.insert(ignore_permissions=True)
        
        # Update tuktuk status
        tuktuk.status = "Assigned"
        tuktuk.save()
        
        frappe.msgprint(f"✅ Rental started for TukTuk {tuktuk.tuktuk_id}")
        return {
            "rental_id": rental.name,
            "tuktuk_id": tuktuk.tuktuk_id,
            "rental_fee": rental_fee
        }
        
    except Exception as e:
        frappe.throw(f"Failed to start rental: {str(e)}")

# ===== UTILITY FUNCTIONS =====

@frappe.whitelist()
def get_current_tuktuk_driver():
    """Get current logged-in tuktuk driver document"""
    if frappe.session.user == "Guest":
        frappe.throw(_("Please login to access this feature"), frappe.PermissionError)
    
    user_roles = frappe.get_roles(frappe.session.user)
    if "TukTuk Driver" not in user_roles:
        frappe.throw(_("Access denied - TukTuk Driver role required"), frappe.PermissionError)
    
    # Get driver details
    tuktuk_driver = frappe.get_all("TukTuk Driver",
                           filters={"user_account": frappe.session.user},
                           fields=["name"],
                           limit=1)

    if not tuktuk_driver:
        frappe.throw(_("TukTuk driver record not found"))

    # Return full document
    return frappe.get_doc("TukTuk Driver", tuktuk_driver[0].name)

@frappe.whitelist()
def get_driver_hailing_status():
    """Get current hailing status for logged-in driver"""
    try:
        tuktuk_driver = get_current_tuktuk_driver()
        
        return {
            "success": True,
            "driver_id": tuktuk_driver.name,
            "hailing_status": tuktuk_driver.get("hailing_status", "Offline"),
            "assigned_tuktuk": tuktuk_driver.assigned_tuktuk or None
        }
    except Exception as e:
        frappe.log_error(f"Driver hailing status error: {str(e)}")
        return {
            "success": False,
            "message": str(e),
            "hailing_status": "Offline"
        }

@frappe.whitelist()
def update_tuktuk_driver_phone(new_phone):
    """Allow tuktuk driver to update their phone number"""
    try:
        tuktuk_driver = get_current_tuktuk_driver()
        
        # Validate phone format
        if not re.match(r'^(?:\+254|254|0)\d{9}$', new_phone.replace(' ', '')):
            frappe.throw("Invalid phone number format")
        
        # Standardize format
        if new_phone.startswith('+'):
            new_phone = new_phone[1:]
        elif new_phone.startswith('0'):
            new_phone = '254' + new_phone[1:]
        
        tuktuk_driver.driver_primary_phone = new_phone
        tuktuk_driver.mpesa_number = new_phone
        tuktuk_driver.save()
        
        frappe.msgprint("✅ Phone number updated successfully")
        return new_phone
        
    except Exception as e:
        frappe.throw(f"Failed to update phone number: {str(e)}")

# ===== MANAGEMENT FUNCTIONS =====

@frappe.whitelist()
def get_all_tuktuk_driver_accounts():
    """Get list of all tuktuk driver accounts (for management)"""
    try:
        # Check if user has management access
        user_roles = frappe.get_roles(frappe.session.user)
        if "System Manager" not in user_roles and "Tuktuk Manager" not in user_roles:
            frappe.throw("Access denied")
        
        tuktuk_drivers = frappe.get_all("TukTuk Driver",
                                fields=[
                                    "name", "driver_name", "driver_primary_phone",
                                    "driver_email", "user_account", "assigned_tuktuk"
                                ],
                                order_by="driver_name")
        
        return tuktuk_drivers
        
    except Exception as e:
        frappe.throw(f"Failed to get tuktuk driver accounts: {str(e)}")

@frappe.whitelist()
def disable_tuktuk_driver_account(tuktuk_driver_name):
    """Disable a tuktuk driver's user account"""
    try:
        # Check management access
        user_roles = frappe.get_roles(frappe.session.user)
        if "System Manager" not in user_roles and "Tuktuk Manager" not in user_roles:
            frappe.throw("Access denied")
        
        tuktuk_driver = frappe.get_doc("TukTuk Driver", tuktuk_driver_name)
        
        if not tuktuk_driver.user_account:
            frappe.throw("TukTuk driver does not have a user account")
        
        user = frappe.get_doc("User", tuktuk_driver.user_account)
        user.enabled = 0
        user.save()
        
        frappe.msgprint(f"✅ Account disabled for {tuktuk_driver.driver_name}")
        
    except Exception as e:
        frappe.throw(f"Failed to disable account: {str(e)}")

@frappe.whitelist()
def enable_tuktuk_driver_account(tuktuk_driver_name):
    """Enable a tuktuk driver's user account"""
    try:
        # Check management access
        user_roles = frappe.get_roles(frappe.session.user)
        if "System Manager" not in user_roles and "Tuktuk Manager" not in user_roles:
            frappe.throw("Access denied")
        
        tuktuk_driver = frappe.get_doc("TukTuk Driver", tuktuk_driver_name)
        
        if not tuktuk_driver.user_account:
            frappe.throw("TukTuk driver does not have a user account")
        
        user = frappe.get_doc("User", tuktuk_driver.user_account)
        user.enabled = 1
        user.save()
        
        frappe.msgprint(f"✅ Account enabled for {tuktuk_driver.driver_name}")
        
    except Exception as e:
        frappe.throw(f"Failed to enable account: {str(e)}")

# ===== WEBSITE PERMISSION FUNCTION =====

def has_website_permission(doc, ptype, user, verbose=False):
    """Check if user has permission to access TukTuk Driver records on website"""
    if user == "Guest":
        return False
    
    user_roles = frappe.get_roles(user)
    
    # Allow System Manager and Tuktuk Manager full access
    if "System Manager" in user_roles or "Tuktuk Manager" in user_roles:
        return True
    
    # Allow TukTuk drivers to access only their own record
    if "TukTuk Driver" in user_roles:
        tuktuk_driver = frappe.get_all("TukTuk Driver", 
                                     filters={"user_account": user},
                                     fields=["name"],
                                     limit=1)
        if tuktuk_driver and tuktuk_driver[0].name == doc:
            return True
    
    return False

# Add this to your existing driver_auth.py file

@frappe.whitelist()
def handle_tuktuk_driver_login():
    """Handle post-login actions for TukTuk drivers"""
    try:
        user_roles = frappe.get_roles(frappe.session.user)
        
        if "TukTuk Driver" in user_roles:
            # Check if user has a TukTuk driver record
            tuktuk_driver = frappe.get_all("TukTuk Driver", 
                                         filters={"user_account": frappe.session.user},
                                         fields=["name", "driver_name"],
                                         limit=1)
            
            if tuktuk_driver:
                # Set redirect flag
                frappe.local.response["type"] = "redirect"
                frappe.local.response["location"] = "/tuktuk-driver-dashboard"
                return True
        
        return False
        
    except Exception as e:
        frappe.log_error(f"TukTuk driver login handler error: {str(e)}")
        return False

# Alternative: Session hook method
def on_session_creation(login_manager):
    """Called when a new session is created (user logs in)"""
    try:
        user = login_manager.user
        user_roles = frappe.get_roles(user)
        
        if "TukTuk Driver" in user_roles:
            # Check if user has a TukTuk driver record
            tuktuk_driver = frappe.get_all("TukTuk Driver", 
                                         filters={"user_account": user},
                                         fields=["name"],
                                         limit=1)
            
            if tuktuk_driver:
                # Store redirect preference in session
                frappe.session["tuktuk_driver_redirect"] = True
                
    except Exception as e:
        frappe.log_error(f"Session creation handler error: {str(e)}")    