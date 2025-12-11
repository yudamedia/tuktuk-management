# ~/frappe-bench/apps/tuktuk_management/tuktuk_management/api/sendpay.py

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

# ===== B2C PAYMENT FUNCTIONS =====

def validate_mpesa_number_string(mpesa_number):
    """Validate MPesa number format for string input"""
    if not mpesa_number:
        frappe.throw("MPesa number is required")
        
    cleaned_number = str(mpesa_number).replace(' ', '')
    pattern = r'^(?:\+254|254|0)\d{9}$'
    if not re.match(pattern, cleaned_number):
        frappe.throw("Invalid MPesa number format. Use format: +254XXXXXXXXX or 0XXXXXXXXX")
        
    # Standardize format to 254XXXXXXXXX
    if cleaned_number.startswith('+'):
        cleaned_number = cleaned_number[1:]
    elif cleaned_number.startswith('0'):
        cleaned_number = '254' + cleaned_number[1:]
        
    return cleaned_number

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

def send_mpesa_payment(mpesa_number, amount, payment_type="FARE", petty_cash_doc=None):
    """
    Send payment via MPesa B2C using PRODUCTION Daraja API
    
    Args:
        mpesa_number: Recipient phone number (254XXXXXXXXX format)
        amount: Amount to send in KSH
        payment_type: Type of payment (FARE, PETTY_CASH, RENTAL, BONUS)
        petty_cash_doc: TukTuk Petty Cash document name (optional, for petty cash payments)
    
    Returns:
        bool: True if payment initiated successfully, False otherwise
    """
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
        
        # Get production credentials from TukTuk Settings
        initiator_name = settings.get_password("mpesa_initiator_name")
        security_credential = settings.get_password("mpesa_security_credential")
        
        # Validate required B2C credentials
        if not initiator_name:
            frappe.log_error("B2C Config Error", "Initiator name not configured in TukTuk Settings")
            return False
            
        if not security_credential:
            frappe.log_error("B2C Config Error", "Security credential not configured in TukTuk Settings")
            return False
        
        # Determine remarks based on payment type
        remarks_map = {
            "FARE": "Sunny TukTuk Fare Payment",
            "PETTY_CASH": "Sunny TukTuk Petty Cash",
            "RENTAL": "Sunny TukTuk Rental Payment",
            "BONUS": "Sunny TukTuk Bonus Payment",
            "TEST": "Sunny TukTuk Test Payment"
        }
        remarks = remarks_map.get(payment_type, "Sunny TukTuk Payment")
        
        payload = {
            "InitiatorName": initiator_name,
            "SecurityCredential": security_credential,
            "CommandID": "BusinessPayment",
            "Amount": amount,
            "PartyA": settings.mpesa_paybill,
            "PartyB": mpesa_number,
            "Remarks": remarks,
            "QueueTimeOutURL": f"{frappe.utils.get_url()}/api/method/tuktuk_management.api.sendpay.b2c_timeout",
            "ResultURL": f"{frappe.utils.get_url()}/api/method/tuktuk_management.api.sendpay.b2c_result",
            "Occasion": f"TukTuk {payment_type} Payment"
        }
        
        response = requests.post(api_url, json=payload, headers=headers, timeout=30)
        result = response.json()
        
        # Log the complete response for debugging
        frappe.log_error("B2C API Response", f"Payment Type: {payment_type}\nResponse: {json.dumps(result, indent=2)}")
        
        if result.get("ResponseCode") == "0":
            frappe.log_error(
                "✅ B2C Payment Initiated",
                f"Type: {payment_type}\nAmount: {amount}\nPhone: {mpesa_number}\nConversation ID: {result.get('ConversationID')}"
            )
            
            # Update petty cash record if provided
            if petty_cash_doc and payment_type == "PETTY_CASH":
                try:
                    from tuktuk_management.tuktuk_management.doctype.tuktuk_petty_cash.tuktuk_petty_cash import update_mpesa_response
                    
                    update_mpesa_response(
                        docname=petty_cash_doc,
                        conversation_id=result.get("ConversationID"),
                        originator_conversation_id=result.get("OriginatorConversationID"),
                        response_code=result.get("ResponseCode"),
                        response_description=result.get("ResponseDescription")
                    )
                except Exception as e:
                    frappe.log_error(f"Failed to update petty cash record: {str(e)}")
            
            return True
        else:
            frappe.log_error(
                "❌ B2C Payment Failed",
                f"Type: {payment_type}\nResponse Code: {result.get('ResponseCode')}\nDescription: {result.get('ResponseDescription')}"
            )
            return False
            
    except Exception as e:
        frappe.log_error("B2C Payment Error", f"Type: {payment_type}\nError: {str(e)}")
        return False


@frappe.whitelist(allow_guest=True)
def b2c_result():
    """
    Handle B2C payment result callback from Safaricom
    This webhook receives the final result of B2C transactions
    """
    try:
        # Get the JSON payload from Safaricom
        result_data = frappe.request.get_json()
        
        if not result_data:
            frappe.log_error("B2C Result: Empty payload received")
            return {"ResultCode": 1, "ResultDesc": "Empty payload"}
        
        # Log the complete result for debugging
        frappe.log_error("B2C Result Received", json.dumps(result_data, indent=2))
        
        # Extract result parameters
        result_body = result_data.get("Result", {})
        conversation_id = result_body.get("ConversationID")
        originator_conversation_id = result_body.get("OriginatorConversationID")
        result_code = result_body.get("ResultCode")
        result_desc = result_body.get("ResultDesc")
        
        # Extract transaction ID from result parameters
        transaction_id = None
        result_parameters = result_body.get("ResultParameters", {}).get("ResultParameter", [])
        
        for param in result_parameters:
            if param.get("Key") == "TransactionID":
                transaction_id = param.get("Value")
                break
        
        # Check if this is a petty cash payment
        petty_cash_records = frappe.get_all(
            "TukTuk Petty Cash",
            filters={"mpesa_conversation_id": conversation_id},
            fields=["name"]
        )
        
        if petty_cash_records:
            # Update petty cash record
            try:
                from tuktuk_management.tuktuk_management.doctype.tuktuk_petty_cash.tuktuk_petty_cash import update_mpesa_result
                
                update_mpesa_result(
                    conversation_id=conversation_id,
                    result_code=result_code,
                    transaction_id=transaction_id
                )
                frappe.log_error(
                    "✅ Petty Cash B2C Result Processed",
                    f"Doc: {petty_cash_records[0].name}\nResult: {result_desc}\nTxn ID: {transaction_id}"
                )
            except Exception as e:
                frappe.log_error(f"Failed to update petty cash result: {str(e)}")
        else:
            # Handle other payment types (FARE, RENTAL, BONUS)
            # Log for now - you can add additional logic here for other payment types
            frappe.log_error(
                "B2C Result (Non-Petty Cash)",
                f"Conversation ID: {conversation_id}\nResult Code: {result_code}\nTransaction ID: {transaction_id}"
            )
        
        # Return success acknowledgment to Safaricom
        return {
            "ResultCode": 0,
            "ResultDesc": "Accepted"
        }
        
    except Exception as e:
        frappe.log_error("B2C Result Error", str(e))
        return {
            "ResultCode": 1,
            "ResultDesc": f"Error: {str(e)}"
        }


@frappe.whitelist(allow_guest=True)
def b2c_timeout():
    """
    Handle B2C payment timeout callback from Safaricom
    This is called when the B2C request times out
    """
    try:
        timeout_data = frappe.request.get_json()
        
        if not timeout_data:
            frappe.log_error("B2C Timeout: Empty payload")
            return {"ResultCode": 1, "ResultDesc": "Empty payload"}
        
        frappe.log_error("B2C Timeout Received", json.dumps(timeout_data, indent=2))
        
        # Extract timeout parameters
        result_body = timeout_data.get("Result", {})
        conversation_id = result_body.get("ConversationID")
        result_desc = result_body.get("ResultDesc", "Payment request timed out")
        
        # Check if this is a petty cash payment
        petty_cash_records = frappe.get_all(
            "TukTuk Petty Cash",
            filters={"mpesa_conversation_id": conversation_id},
            fields=["name"]
        )
        
        if petty_cash_records:
            try:
                doc = frappe.get_doc("TukTuk Petty Cash", petty_cash_records[0].name)
                doc.payment_status = "Failed"
                doc.mpesa_result_code = "408"  # Timeout code
                doc.save()
                frappe.db.commit()
                
                frappe.log_error(
                    "⏱️ Petty Cash B2C Timeout",
                    f"Doc: {petty_cash_records[0].name}\nConversation ID: {conversation_id}"
                )
            except Exception as e:
                frappe.log_error(f"Failed to update petty cash timeout: {str(e)}")
        else:
            # Log timeout for other payment types
            frappe.log_error(
                "B2C Timeout (Non-Petty Cash)",
                f"Conversation ID: {conversation_id}\nDescription: {result_desc}"
            )
        
        return {
            "ResultCode": 0,
            "ResultDesc": "Timeout acknowledged"
        }
        
    except Exception as e:
        frappe.log_error("B2C Timeout Error", str(e))
        return {
            "ResultCode": 1,
            "ResultDesc": f"Error: {str(e)}"
        }


# ===== B2C SETUP AND TESTING FUNCTIONS =====

@frappe.whitelist()
def setup_b2c_credentials():
    """Setup and test B2C credentials"""
    try:
        settings = frappe.get_single("TukTuk Settings")
        
        # Check if B2C credentials are configured
        initiator_name = settings.get_password("mpesa_initiator_name")
        security_credential = settings.get_password("mpesa_security_credential")
        
        if not initiator_name:
            frappe.msgprint("❌ Missing: MPesa Initiator Name")
            frappe.msgprint("Please contact Safaricom to get your Initiator Name for B2C transactions")
            return False
            
        if not security_credential:
            frappe.msgprint("❌ Missing: MPesa Security Credential")
            frappe.msgprint("Please contact Safaricom to get your Security Credential for B2C transactions")
            return False
        
        frappe.msgprint("✅ B2C credentials are configured")
        frappe.msgprint(f"Initiator Name: {initiator_name}")
        frappe.msgprint("Security Credential: [CONFIGURED]")
        
        return True
        
    except Exception as e:
        frappe.throw(f"B2C setup check failed: {str(e)}")

@frappe.whitelist()
def test_b2c_payment():
    """Test B2C payment with a small amount"""
    try:
        # Find a test driver
        test_driver = frappe.get_all(
            "TukTuk Driver",
            fields=["driver_name", "mpesa_number"],
            limit=1
        )
        
        if not test_driver:
            frappe.throw("No drivers found for testing. Please create a driver first.")
            
        driver = test_driver[0]
        test_amount = 1.0  # 1 KSH test amount
        
        frappe.msgprint(f"🧪 Testing B2C payment of {test_amount} KSH to {driver.driver_name}")
        frappe.msgprint(f"Phone: {driver.mpesa_number}")
        
        # Attempt the payment
        success = send_mpesa_payment(driver.mpesa_number, test_amount, "TEST")
        
        if success:
            frappe.msgprint("✅ B2C test payment initiated successfully!")
            frappe.msgprint("🔍 Check the Error Log for API response details")
            frappe.msgprint("📱 Check your phone for MPesa SMS confirmation")
        else:
            frappe.msgprint("❌ B2C test payment failed")
            frappe.msgprint("🔍 Check the Error Log for error details")
            
        return success
        
    except Exception as e:
        frappe.throw(f"B2C test failed: {str(e)}")

@frappe.whitelist()
def get_b2c_requirements():
    """Get information about B2C requirements from Safaricom"""
    requirements = """
    🔧 To enable B2C payments, you need the following from Safaricom:
    
    1. **Initiator Name**: A unique identifier for your organization
       - This is assigned by Safaricom when you apply for B2C
       - Usually your business name or a short identifier
    
    2. **Security Credential**: An encrypted password for authentication
       - Generated by encrypting your initiator password with Safaricom's public key
       - You need to contact Safaricom support to get this
    
    3. **Initiator Password**: Your plain text password (for reference)
       - This is used to generate the security credential
       - Store this securely
    
    📞 Contact Safaricom:
    - Email: apisupport@safaricom.co.ke
    - Phone: +254 722 000 000
    - Developer Portal: developer.safaricom.co.ke
    
    📋 What to request:
    "I need B2C (Business to Customer) payment API access for my application.
    I already have C2B access working. Please provide:
    - Initiator Name
    - Security Credential
    - Production B2C API access"
    
    ⚡ Current Status:
    - C2B (Customer to Business): ✅ Working
    - B2C (Business to Customer): ❌ Needs credentials
    """
    
    frappe.msgprint(requirements)
    return requirements

@frappe.whitelist()
def direct_b2c_test(phone_number=None, amount=1.0):
    """Direct B2C test with specific phone number"""
    try:
        if not phone_number:
            # Use a default test number or get from settings
            settings = frappe.get_single("TukTuk Settings")
            
            # Try to get a driver's phone number
            drivers = frappe.get_all(
                "TukTuk Driver", 
                fields=["mpesa_number"],
                limit=1
            )
            
            if drivers:
                phone_number = drivers[0].mpesa_number
            else:
                frappe.throw("Please provide a phone number or create a driver first")
        
        frappe.msgprint(f"🧪 Testing B2C payment: {amount} KSH to {phone_number}")
        
        # Test the payment
        success = send_mpesa_payment(phone_number, amount, "DIRECT_TEST")
        
        if success:
            frappe.msgprint("✅ B2C payment request successful!")
            frappe.msgprint("📱 Check phone for MPesa SMS")
            frappe.msgprint("🔍 Check Error Log for 'Production B2C Success'")
        else:
            frappe.msgprint("❌ B2C payment request failed")
            frappe.msgprint("🔍 Check Error Log for error details")
            
        return success
        
    except Exception as e:
        frappe.throw(f"Direct B2C test failed: {str(e)}")

@frappe.whitelist() 
def simple_b2c_test():
    """Simple B2C test without querying drivers"""
    try:
        # Use a test phone number directly
        test_phone = "254708374149"  # Replace with your phone number
        test_amount = 1.0
        
        frappe.msgprint(f"🧪 Testing B2C with {test_amount} KSH to {test_phone}")
        frappe.msgprint("🔍 Note: Replace test_phone in the function with your actual number")
        
        # Test the B2C payment
        success = send_mpesa_payment(test_phone, test_amount, "SIMPLE_TEST")
        
        if success:
            frappe.msgprint("✅ B2C API call successful!")
            frappe.msgprint("🎉 This means Safaricom has enabled B2C for your app!")
            frappe.msgprint("📱 Check your phone for 1 KSH MPesa credit")
        else:
            frappe.msgprint("❌ B2C API call failed")
            frappe.msgprint("📋 Check Error Log for specific error details")
            
        return success
        
    except Exception as e:
        frappe.log_error("Simple B2C Test Error", str(e))
        frappe.msgprint(f"❌ Test error: {str(e)}")
        return False    

@frappe.whitelist()
def test_b2c_webhooks():
    """Test B2C webhook endpoints with sample data"""
    
    # Test result webhook with success scenario
    success_data = {
        "Result": {
            "ResultType": 0,
            "ResultCode": 0,
            "ResultDesc": "The service request is processed successfully.",
            "OriginatorConversationID": "29115-34620561-1",
            "ConversationID": "AG_20191219_00005797af5d7d75f652",
            "TransactionID": "NLJ7RT61SV",
            "ResultParameters": {
                "ResultParameter": [
                    {"Key": "TransactionAmount", "Value": 100},
                    {"Key": "TransactionReceipt", "Value": "NLJ7RT61SV"},
                    {"Key": "ReceiverPartyPublicName", "Value": "254708374149 - John Doe"}
                ]
            }
        }
    }
    
    # Test timeout webhook
    timeout_data = {
        "Result": {
            "ResultType": 1,
            "ResultCode": 1,
            "ResultDesc": "The service request has timed out.",
            "OriginatorConversationID": "29115-34620561-1",
            "ConversationID": "AG_20191219_00005797af5d7d75f652"
        }
    }
    
    try:
        frappe.msgprint("Testing B2C result webhook...")
        b2c_result(**success_data)
        frappe.msgprint("Testing B2C timeout webhook...")
        b2c_timeout(**timeout_data)
        frappe.msgprint("✅ Webhook tests completed. Check Error Log for results.")
        return True
    except Exception as e:
        frappe.throw(f"Webhook test failed: {str(e)}")

@frappe.whitelist()
def verify_webhook_urls():
    """Verify that webhook URLs are accessible from external calls"""
    base_url = frappe.utils.get_url()
    result_url = f"{base_url}/api/method/tuktuk_management.api.sendpay.b2c_result"
    timeout_url = f"{base_url}/api/method/tuktuk_management.api.sendpay.b2c_timeout"
    
    frappe.msgprint(f"🔗 Your B2C Webhook URLs:")
    frappe.msgprint(f"Result URL: {result_url}")
    frappe.msgprint(f"Timeout URL: {timeout_url}")
    
    return {
        "result_url": result_url,
        "timeout_url": timeout_url,
        "status": "URLs configured"
    }