# ~/frappe-bench/apps/tuktuk_management/tuktuk_management/api/sms_notifications.py

import frappe
import requests
import json
from frappe.utils import flt

# TextBee API Configuration
TEXTBEE_DEVICE_ID = "692e1467d3fdd9bd6cf9b331"
TEXTBEE_API_URL = f"https://api.textbee.dev/api/v1/gateway/devices/{TEXTBEE_DEVICE_ID}/send-sms"


def send_textbee_sms(phone_number, message):
    """
    Send SMS via TextBee API
    
    Args:
        phone_number (str): Phone number in format 254XXXXXXXXX
        message (str): SMS message text
        
    Returns:
        bool: True if SMS sent successfully, False otherwise
    """
    try:
        # Get API key from TukTuk Settings
        settings = frappe.get_single("TukTuk Settings")
        api_key = settings.get_password("textbee_api_key")
        
        if not api_key:
            frappe.log_error("TextBee API key not configured in TukTuk Settings", "SMS Send Error")
            return False
        
        # Prepare request payload
        payload = {
            "recipients": [phone_number],
            "message": message
        }
        
        # Prepare headers
        headers = {
            "Content-Type": "application/json",
            "x-api-key": api_key
        }
        
        # Send request to TextBee API
        response = requests.post(
            TEXTBEE_API_URL,
            json=payload,
            headers=headers,
            timeout=10
        )
        
        # Check response (200 OK or 201 Created are both success)
        if response.status_code in [200, 201]:
            frappe.log_error(
                f"SMS sent successfully to {phone_number}\nMessage: {message}\nStatus Code: {response.status_code}\nResponse: {response.text}",
                "SMS Success"
            )
            return True
        else:
            frappe.log_error(
                f"Failed to send SMS to {phone_number}\nStatus Code: {response.status_code}\nResponse: {response.text}\nMessage: {message}",
                "SMS Send Error"
            )
            return False
            
    except requests.exceptions.Timeout:
        frappe.log_error(
            f"Timeout while sending SMS to {phone_number}\nMessage: {message}",
            "SMS Timeout Error"
        )
        return False
    except requests.exceptions.RequestException as e:
        frappe.log_error(
            f"Network error while sending SMS to {phone_number}\nError: {str(e)}\nMessage: {message}",
            "SMS Network Error"
        )
        return False
    except Exception as e:
        frappe.log_error(
            f"Unexpected error while sending SMS to {phone_number}\nError: {str(e)}\nMessage: {message}",
            "SMS Unexpected Error"
        )
        return False


def send_textsms_sms(phone_number, message):
    """
    Send SMS via TextSMS API
    
    Args:
        phone_number (str): Phone number in format 254XXXXXXXXX
        message (str): SMS message text
        
    Returns:
        bool: True if SMS sent successfully, False otherwise
    """
    try:
        # Get API credentials from TukTuk Settings
        settings = frappe.get_single("TukTuk Settings")
        api_key = settings.get_password("textsms_api_key")
        partner_id = settings.textsms_partner_id
        sender_id = settings.textsms_sender_id
        
        if not api_key:
            frappe.log_error("TextSMS API key not configured in TukTuk Settings", "SMS Send Error")
            return False
        
        if not partner_id:
            frappe.log_error("TextSMS Partner ID not configured in TukTuk Settings", "SMS Send Error")
            return False
        
        if not sender_id:
            frappe.log_error("TextSMS Sender ID not configured in TukTuk Settings", "SMS Send Error")
            return False
        
        # Prepare request payload according to TextSMS API documentation
        payload = {
            "apikey": api_key,
            "partnerID": partner_id,
            "message": message,
            "shortcode": sender_id,
            "mobile": phone_number
        }
        
        # Prepare headers
        headers = {
            "Content-Type": "application/json"
        }
        
        # Send request to TextSMS API
        response = requests.post(
            "https://sms.textsms.co.ke/api/services/sendsms/",
            json=payload,
            headers=headers,
            timeout=10
        )
        
        # Check response
        if response.status_code == 200:
            try:
                response_data = response.json()
                # Check if responses array exists and has data
                if "responses" in response_data and len(response_data["responses"]) > 0:
                    first_response = response_data["responses"][0]
                    # Check for both "response-code" (correct) and "respose-code" (API doc typo)
                    # TextSMS documentation shows "respose-code" but actual API returns "response-code"
                    response_code = first_response.get("response-code") or first_response.get("respose-code")
                    
                    if response_code == 200:
                        frappe.log_error(
                            f"SMS sent successfully to {phone_number}\nMessage: {message}\nResponse: {response.text}",
                            "SMS Success"
                        )
                        return True
                    else:
                        # Handle specific error codes
                        error_messages = {
                            1001: "Invalid sender ID",
                            1002: "Network not allowed",
                            1003: "Invalid mobile number",
                            1004: "Low bulk credits",
                            1005: "Failed. System error",
                            1006: "Invalid credentials",
                            1007: "Failed. System error",
                            1008: "No Delivery Report",
                            1009: "Unsupported data type",
                            1010: "Unsupported request type",
                            4090: "Internal Error. Try again after 5 minutes",
                            4091: "No Partner ID is Set",
                            4092: "No API KEY Provided",
                            4093: "Details Not Found"
                        }
                        error_msg = error_messages.get(response_code, f"Unknown error code: {response_code}")
                        frappe.log_error(
                            f"Failed to send SMS to {phone_number}\nError Code: {response_code}\nError: {error_msg}\nMessage: {message}\nResponse: {response.text}",
                            "SMS Send Error"
                        )
                        return False
            except json.JSONDecodeError:
                frappe.log_error(
                    f"Invalid JSON response from TextSMS API\nStatus Code: {response.status_code}\nResponse: {response.text}",
                    "SMS Send Error"
                )
                return False
        else:
            frappe.log_error(
                f"Failed to send SMS to {phone_number}\nStatus Code: {response.status_code}\nResponse: {response.text}\nMessage: {message}",
                "SMS Send Error"
            )
            return False
            
    except requests.exceptions.Timeout:
        frappe.log_error(
            f"Timeout while sending SMS to {phone_number}\nMessage: {message}",
            "SMS Timeout Error"
        )
        return False
    except requests.exceptions.RequestException as e:
        frappe.log_error(
            f"Network error while sending SMS to {phone_number}\nError: {str(e)}\nMessage: {message}",
            "SMS Network Error"
        )
        return False
    except Exception as e:
        frappe.log_error(
            f"Unexpected error while sending SMS to {phone_number}\nError: {str(e)}\nMessage: {message}",
            "SMS Unexpected Error"
        )
        return False


def send_sms(phone_number, message):
    """
    Generic SMS sending function that routes to the appropriate provider
    based on TukTuk Settings configuration
    
    Args:
        phone_number (str): Phone number in format 254XXXXXXXXX
        message (str): SMS message text
        
    Returns:
        bool: True if SMS sent successfully, False otherwise
    """
    try:
        settings = frappe.get_single("TukTuk Settings")
        sms_provider = settings.sms_provider or "TextBee"  # Default to TextBee
        
        if sms_provider == "TextSMS":
            return send_textsms_sms(phone_number, message)
        else:
            return send_textbee_sms(phone_number, message)
            
    except Exception as e:
        frappe.log_error(
            f"Error in send_sms routing: {str(e)}",
            "SMS Router Error"
        )
        return False


def get_eligible_drivers_for_reminder():
    """
    Get list of drivers eligible for SMS reminders
    Uses efficient server-side filtering to avoid DB hammering
    
    Returns:
        list: List of driver dictionaries with name, driver_name, mpesa_number, left_to_target
    """
    try:
        # Use efficient DB-level filtering
        drivers = frappe.get_all(
            "TukTuk Driver",
            filters={
                "assigned_tuktuk": ["!=", ""],
                "left_to_target": [">", 0]
            },
            fields=["name", "driver_name", "mpesa_number", "left_to_target"]
        )
        
        return drivers
        
    except Exception as e:
        frappe.log_error(
            f"Error fetching eligible drivers for SMS reminder: {str(e)}",
            "SMS Driver Query Error"
        )
        return []


def send_driver_target_reminder():
    """
    Main scheduled task function to send target reminders to drivers
    Sends SMS to all assigned drivers who haven't reached their daily target
    """
    try:
        # Cache settings to avoid repeated DB queries
        settings = frappe.get_single("TukTuk Settings")
        
        # Check if SMS notifications are enabled
        if not settings.enable_sms_notifications:
            frappe.log_error(
                "SMS notifications are disabled in TukTuk Settings. Skipping driver target reminders.",
                "SMS Reminder Skipped"
            )
            return
        
        # Check if SMS provider is configured
        sms_provider = settings.sms_provider or "TextBee"
        if sms_provider == "TextBee":
            api_key = settings.get_password("textbee_api_key")
            if not api_key:
                frappe.log_error(
                    "TextBee API key not configured in TukTuk Settings. Cannot send SMS reminders.",
                    "SMS Reminder Error"
                )
                return
        elif sms_provider == "TextSMS":
            api_key = settings.get_password("textsms_api_key")
            partner_id = settings.textsms_partner_id
            sender_id = settings.textsms_sender_id
            if not api_key or not partner_id or not sender_id:
                frappe.log_error(
                    "TextSMS credentials not fully configured in TukTuk Settings. Cannot send SMS reminders.",
                    "SMS Reminder Error"
                )
                return
        
        # Get eligible drivers
        drivers = get_eligible_drivers_for_reminder()
        
        if not drivers:
            frappe.log_error(
                "No eligible drivers found for SMS reminders (all drivers have reached target or are unassigned).",
                "SMS Reminder Info"
            )
            return
        
        # Send SMS to each eligible driver
        success_count = 0
        failure_count = 0
        
        for driver in drivers:
            driver_name = driver.get("driver_name", "Driver")
            mpesa_number = driver.get("mpesa_number")
            left_to_target = flt(driver.get("left_to_target", 0))
            
            # Validate phone number exists
            if not mpesa_number:
                frappe.log_error(
                    f"Driver {driver_name} ({driver.get('name')}) has no M-Pesa number configured. Skipping SMS.",
                    "SMS Missing Phone"
                )
                failure_count += 1
                continue
            
            # Format the message
            message = f"Hello {driver_name}! You have KES {left_to_target:,.0f} to complete today's target amount."
            
            # Send SMS using generic router
            if send_sms(mpesa_number, message):
                success_count += 1
            else:
                failure_count += 1
        
        # Log summary
        frappe.log_error(
            f"Driver Target SMS Reminder Summary:\n"
            f"Total Eligible Drivers: {len(drivers)}\n"
            f"Successfully Sent: {success_count}\n"
            f"Failed: {failure_count}",
            "SMS Reminder Summary"
        )
        
    except Exception as e:
        frappe.log_error(
            f"Critical error in send_driver_target_reminder: {str(e)}",
            "SMS Reminder Critical Error"
        )


@frappe.whitelist()
def test_sms_to_driver(driver_name):
    """
    Manual test function to send SMS to a specific driver
    Can be called from Frappe console or via API
    
    Usage from console:
        frappe.call('tuktuk_management.api.sms_notifications.test_sms_to_driver', driver_name='DRV-112001')
    
    Args:
        driver_name (str): Driver ID (e.g., 'DRV-112001')
        
    Returns:
        dict: Result with success status and message
    """
    try:
        # Get driver details
        driver = frappe.get_doc("TukTuk Driver", driver_name)
        
        if not driver:
            return {
                "success": False,
                "message": f"Driver {driver_name} not found"
            }
        
        if not driver.mpesa_number:
            return {
                "success": False,
                "message": f"Driver {driver.driver_name} has no M-Pesa number configured"
            }
        
        # Check if driver is eligible
        if not driver.assigned_tuktuk:
            return {
                "success": False,
                "message": f"Driver {driver.driver_name} is not assigned to any TukTuk"
            }
        
        if flt(driver.left_to_target) <= 0:
            return {
                "success": False,
                "message": f"Driver {driver.driver_name} has already reached their target (left_to_target: {driver.left_to_target})"
            }
        
        # Format test message
        message = f"Hello {driver.driver_name}! You have KES {flt(driver.left_to_target):,.0f} to complete today's target amount."
        
        # Send SMS using generic router
        success = send_sms(driver.mpesa_number, message)
        
        if success:
            return {
                "success": True,
                "message": f"Test SMS sent successfully to {driver.driver_name} ({driver.mpesa_number})",
                "sms_content": message
            }
        else:
            return {
                "success": False,
                "message": f"Failed to send SMS to {driver.driver_name}. Check Error Log for details."
            }
            
    except Exception as e:
        frappe.log_error(
            f"Error in test_sms_to_driver for {driver_name}: {str(e)}",
            "SMS Test Error"
        )
        return {
            "success": False,
            "message": f"Error: {str(e)}"
        }


@frappe.whitelist()
def get_sms_status():
    """
    Get current SMS notification status and configuration
    
    Returns:
        dict: Status information about SMS configuration
    """
    try:
        settings = frappe.get_single("TukTuk Settings")
        
        # Check configuration
        sms_enabled = settings.enable_sms_notifications
        sms_provider = settings.sms_provider or "TextBee"
        
        # Check provider-specific configuration
        provider_configured = False
        provider_config_details = {}
        
        if sms_provider == "TextBee":
            api_key_configured = bool(settings.get_password("textbee_api_key"))
            provider_configured = api_key_configured
            provider_config_details = {
                "api_key_configured": api_key_configured
            }
        elif sms_provider == "TextSMS":
            api_key_configured = bool(settings.get_password("textsms_api_key"))
            partner_id_configured = bool(settings.textsms_partner_id)
            sender_id_configured = bool(settings.textsms_sender_id)
            provider_configured = api_key_configured and partner_id_configured and sender_id_configured
            provider_config_details = {
                "api_key_configured": api_key_configured,
                "partner_id_configured": partner_id_configured,
                "sender_id_configured": sender_id_configured
            }
        
        # Get eligible drivers count
        eligible_drivers = get_eligible_drivers_for_reminder()
        
        return {
            "success": True,
            "sms_enabled": sms_enabled,
            "sms_provider": sms_provider,
            "provider_configured": provider_configured,
            "provider_config_details": provider_config_details,
            "eligible_drivers_count": len(eligible_drivers),
            "eligible_drivers": [
                {
                    "name": d.get("name"),
                    "driver_name": d.get("driver_name"),
                    "mpesa_number": d.get("mpesa_number"),
                    "left_to_target": flt(d.get("left_to_target"))
                }
                for d in eligible_drivers
            ],
            "message": f"SMS notification system is ready (using {sms_provider})" if (sms_enabled and provider_configured) else f"SMS notifications not fully configured for {sms_provider}"
        }
        
    except Exception as e:
        frappe.log_error(
            f"Error in get_sms_status: {str(e)}",
            "SMS Status Error"
        )
        return {
            "success": False,
            "message": f"Error: {str(e)}"
        }


@frappe.whitelist()
def get_all_drivers_for_broadcast():
    """
    Get all drivers with their details for SMS broadcast interface
    
    Returns:
        dict: List of all drivers with name, driver_name, mpesa_number, assigned_tuktuk
    """
    try:
        drivers = frappe.get_all(
            "TukTuk Driver",
            fields=["name", "driver_name", "mpesa_number", "assigned_tuktuk"],
            order_by="driver_name"
        )
        
        return {
            "success": True,
            "drivers": drivers
        }
        
    except Exception as e:
        frappe.log_error(
            f"Error fetching drivers for broadcast: {str(e)}",
            "SMS Broadcast Error"
        )
        return {
            "success": False,
            "message": f"Error: {str(e)}"
        }


@frappe.whitelist()
def send_driver_sms_with_fields(driver_name, message_template):
    """
    Send SMS to a single driver with field interpolation
    
    Args:
        driver_name (str): Driver ID
        message_template (str): Message with field placeholders like {driver_name}, {left_to_target}
        
    Returns:
        dict: Result with success status and message
    """
    try:
        # Get driver details
        driver = frappe.get_doc("TukTuk Driver", driver_name)
        
        if not driver:
            return {
                "success": False,
                "message": f"Driver {driver_name} not found"
            }
        
        if not driver.mpesa_number:
            return {
                "success": False,
                "message": f"Driver {driver.driver_name} has no M-Pesa number configured"
            }
        
        # Get global target for fallback
        settings = frappe.get_single("TukTuk Settings")
        daily_target = flt(driver.daily_target or settings.global_daily_target)
        
        # Get mpesa_account from vehicle if assigned
        mpesa_account = ""
        if driver.assigned_tuktuk:
            try:
                vehicle = frappe.get_doc("TukTuk Vehicle", driver.assigned_tuktuk)
                mpesa_account = vehicle.mpesa_account or ""
            except Exception:
                mpesa_account = ""
        
        # Interpolate fields in the message
        message = message_template
        message = message.replace("{driver_name}", driver.driver_name or "")
        message = message.replace("{sunny_id}", driver.sunny_id or "")
        message = message.replace("{left_to_target}", f"{flt(driver.left_to_target, 0):,.0f}")
        message = message.replace("{current_balance}", f"{flt(driver.current_balance, 0):,.0f}")
        message = message.replace("{daily_target}", f"{daily_target:,.0f}")
        message = message.replace("{assigned_tuktuk}", driver.assigned_tuktuk or "None")
        message = message.replace("{mpesa_number}", driver.mpesa_number or "")
        message = message.replace("{mpesa_paybill}", settings.mpesa_paybill or "")
        message = message.replace("{mpesa_account}", mpesa_account)
        message = message.replace("{current_deposit_balance}", f"{flt(driver.current_deposit_balance, 0):,.0f}")
        
        # Send SMS using generic router
        success = send_sms(driver.mpesa_number, message)
        
        if success:
            return {
                "success": True,
                "message": f"SMS sent successfully to {driver.driver_name}",
                "interpolated_message": message
            }
        else:
            return {
                "success": False,
                "message": f"Failed to send SMS to {driver.driver_name}. Check Error Log for details."
            }
            
    except Exception as e:
        frappe.log_error(
            f"Error in send_driver_sms_with_fields for {driver_name}: {str(e)}",
            "SMS Field Interpolation Error"
        )
        return {
            "success": False,
            "message": f"Error: {str(e)}"
        }


@frappe.whitelist()
def send_bulk_sms_with_fields(driver_ids, message_template):
    """
    Send SMS to multiple drivers with field interpolation for each driver
    
    Args:
        driver_ids (str|list): Comma-separated string or list of driver IDs
        message_template (str): Message with field placeholders like {driver_name}, {left_to_target}
        
    Returns:
        dict: Result with success count, failure count, and details
    """
    try:
        # Parse driver_ids if it's a string
        if isinstance(driver_ids, str):
            driver_ids = json.loads(driver_ids) if driver_ids.startswith('[') else [d.strip() for d in driver_ids.split(",") if d.strip()]
        
        if not driver_ids:
            return {
                "success": False,
                "message": "No drivers selected"
            }
        
        if not message_template or not message_template.strip():
            return {
                "success": False,
                "message": "Message cannot be empty"
            }
        
        # Get driver details
        drivers = frappe.get_all(
            "TukTuk Driver",
            filters={"name": ["in", driver_ids]},
            fields=["name", "driver_name", "sunny_id", "mpesa_number", "left_to_target", "current_balance", "daily_target", "assigned_tuktuk", "current_deposit_balance"]
        )
        
        if not drivers:
            return {
                "success": False,
                "message": "No valid drivers found"
            }
        
        # Get global target for fallback
        settings = frappe.get_single("TukTuk Settings")
        global_target = flt(settings.global_daily_target)
        
        # Send SMS to each driver with personalized message
        results = []
        success_count = 0
        failure_count = 0
        
        for driver in drivers:
            driver_name_str = driver.get("driver_name", "Driver")
            mpesa_number = driver.get("mpesa_number")
            
            if not mpesa_number:
                results.append({
                    "driver_id": driver.get("name"),
                    "driver_name": driver_name_str,
                    "status": "failed",
                    "message": "No M-Pesa number configured"
                })
                failure_count += 1
                continue
            
            # Get mpesa_account from vehicle if assigned
            mpesa_account = ""
            if driver.get("assigned_tuktuk"):
                try:
                    mpesa_account = frappe.db.get_value("TukTuk Vehicle", driver.get("assigned_tuktuk"), "mpesa_account") or ""
                except Exception:
                    mpesa_account = ""
            
            # Interpolate fields for this specific driver
            daily_target = flt(driver.get("daily_target") or global_target)
            message = message_template
            message = message.replace("{driver_name}", driver_name_str)
            message = message.replace("{sunny_id}", driver.get("sunny_id") or "")
            message = message.replace("{left_to_target}", f"{flt(driver.get('left_to_target'), 0):,.0f}")
            message = message.replace("{current_balance}", f"{flt(driver.get('current_balance'), 0):,.0f}")
            message = message.replace("{daily_target}", f"{daily_target:,.0f}")
            message = message.replace("{assigned_tuktuk}", driver.get("assigned_tuktuk") or "None")
            message = message.replace("{mpesa_number}", mpesa_number)
            message = message.replace("{mpesa_paybill}", settings.mpesa_paybill or "")
            message = message.replace("{mpesa_account}", mpesa_account)
            message = message.replace("{current_deposit_balance}", f"{flt(driver.get('current_deposit_balance'), 0):,.0f}")
            
            # Send SMS using generic router
            success = send_sms(mpesa_number, message.strip())
            
            if success:
                results.append({
                    "driver_id": driver.get("name"),
                    "driver_name": driver_name_str,
                    "phone": mpesa_number,
                    "status": "success",
                    "message": "SMS sent successfully",
                    "interpolated_message": message
                })
                success_count += 1
            else:
                results.append({
                    "driver_id": driver.get("name"),
                    "driver_name": driver_name_str,
                    "phone": mpesa_number,
                    "status": "failed",
                    "message": "Failed to send SMS (check Error Log)"
                })
                failure_count += 1
        
        # Log summary
        frappe.log_error(
            f"Bulk SMS with Fields Summary:\n"
            f"Total Drivers: {len(drivers)}\n"
            f"Successfully Sent: {success_count}\n"
            f"Failed: {failure_count}\n"
            f"Message Template: {message_template[:100]}...",
            "Bulk SMS with Fields Summary"
        )
        
        return {
            "success": True,
            "total": len(drivers),
            "success_count": success_count,
            "failure_count": failure_count,
            "results": results
        }
        
    except Exception as e:
        frappe.log_error(
            f"Error in send_bulk_sms_with_fields: {str(e)}",
            "Bulk SMS Field Interpolation Error"
        )
        return {
            "success": False,
            "message": f"Error: {str(e)}"
        }


@frappe.whitelist()
def send_broadcast_sms(driver_ids, message):
    """
    Send SMS to multiple selected drivers
    
    Args:
        driver_ids (str|list): Comma-separated string or list of driver IDs
        message (str): SMS message to send
        
    Returns:
        dict: Result with success count, failure count, and details
    """
    try:
        # Parse driver_ids if it's a string
        if isinstance(driver_ids, str):
            driver_ids = [d.strip() for d in driver_ids.split(",") if d.strip()]
        
        if not driver_ids:
            return {
                "success": False,
                "message": "No drivers selected"
            }
        
        if not message or not message.strip():
            return {
                "success": False,
                "message": "Message cannot be empty"
            }
        
        # Get driver details
        # Debug: Log the driver_ids being passed
        frappe.log_error(
            f"DEBUG: send_broadcast_sms received driver_ids: {driver_ids} (type: {type(driver_ids)})",
            "SMS Broadcast Debug"
        )

        drivers = frappe.get_all(
            "TukTuk Driver",
            filters={"name": ["in", driver_ids]},
            fields=["name", "driver_name", "mpesa_number"]
        )

        # Debug: Log what was found
        frappe.log_error(
            f"DEBUG: Found {len(drivers)} drivers matching the IDs: {[d.get('name') for d in drivers]}",
            "SMS Broadcast Debug"
        )

        if not drivers:
            return {
                "success": False,
                "message": "No valid drivers found"
            }
        
        # Send SMS to each driver
        results = []
        success_count = 0
        failure_count = 0
        
        for driver in drivers:
            driver_name = driver.get("driver_name", "Driver")
            mpesa_number = driver.get("mpesa_number")
            
            if not mpesa_number:
                results.append({
                    "driver_id": driver.get("name"),
                    "driver_name": driver_name,
                    "status": "failed",
                    "message": "No M-Pesa number configured"
                })
                failure_count += 1
                continue
            
            # Send SMS using generic router
            success = send_sms(mpesa_number, message.strip())
            
            if success:
                results.append({
                    "driver_id": driver.get("name"),
                    "driver_name": driver_name,
                    "phone": mpesa_number,
                    "status": "success",
                    "message": "SMS sent successfully"
                })
                success_count += 1
            else:
                results.append({
                    "driver_id": driver.get("name"),
                    "driver_name": driver_name,
                    "phone": mpesa_number,
                    "status": "failed",
                    "message": "Failed to send SMS (check Error Log)"
                })
                failure_count += 1
        
        # Log summary
        frappe.log_error(
            f"SMS Broadcast Summary:\n"
            f"Total Drivers: {len(drivers)}\n"
            f"Successfully Sent: {success_count}\n"
            f"Failed: {failure_count}\n"
            f"Message: {message[:100]}...",
            "SMS Broadcast Summary"
        )
        
        return {
            "success": True,
            "total": len(drivers),
            "success_count": success_count,
            "failure_count": failure_count,
            "results": results
        }
        
    except Exception as e:
        frappe.log_error(
            f"Error in send_broadcast_sms: {str(e)}",
            "SMS Broadcast Error"
        )
        return {
            "success": False,
            "message": f"Error: {str(e)}"
        }

