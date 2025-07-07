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
        
        # FIXED: Get production credentials from TukTuk Settings
        initiator_name = settings.get_password("mpesa_initiator_name")
        security_credential = settings.get_password("mpesa_security_credential")
        
        # Validate required B2C credentials
        if not initiator_name:
            frappe.log_error("B2C Config Error", "Initiator name not configured in TukTuk Settings")
            return False
            
        if not security_credential:
            frappe.log_error("B2C Config Error", "Security credential not configured in TukTuk Settings")
            return False
        
        payload = {
            "InitiatorName": initiator_name,
            "SecurityCredential": security_credential,
            "CommandID": "BusinessPayment",
            "Amount": amount,
            "PartyA": settings.mpesa_paybill,
            "PartyB": mpesa_number,
            "Remarks": f"Sunny TukTuk {payment_type} payment",
            # FIXED: Updated URLs to point to sendpay.py endpoints
            "QueueTimeOutURL": f"{frappe.utils.get_url()}/api/method/tuktuk_management.api.sendpay.b2c_timeout",
            "ResultURL": f"{frappe.utils.get_url()}/api/method/tuktuk_management.api.sendpay.b2c_result",
            "Occasion": "TukTuk Service Payment"
        }
        
        response = requests.post(api_url, json=payload, headers=headers, timeout=30)
        result = response.json()
        
        # Log the complete response for debugging
        frappe.log_error("B2C API Response", f"Status: {response.status_code}, Response: {result}")
        
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
    """Handle B2C payment results with enhanced processing"""
    try:
        # Log the complete response
        frappe.log_error("Production B2C Result", f"B2C result received: {json.dumps(kwargs, indent=2)}")
        
        # Extract result data
        result_data = kwargs.get('Result', {})
        result_type = result_data.get('ResultType')
        result_code = result_data.get('ResultCode')
        result_desc = result_data.get('ResultDesc', '')
        transaction_id = result_data.get('TransactionID', '')
        conversation_id = result_data.get('ConversationID', '')
        
        # Check if payment was successful
        if result_code == 0:
            # Payment successful
            frappe.log_error("B2C Payment Success", f"Payment successful - TransactionID: {transaction_id}")
            
            # Extract payment details from ResultParameters
            result_parameters = result_data.get('ResultParameters', {}).get('ResultParameter', [])
            payment_details = {}
            
            for param in result_parameters:
                key = param.get('Key', '')
                value = param.get('Value', '')
                payment_details[key] = value
            
            # Log payment details
            frappe.log_error("B2C Payment Details", f"Payment details: {json.dumps(payment_details)}")
            
            # TODO: Update transaction status in your system
            # You can use the ConversationID to match with your original request
            
        else:
            # Payment failed
            frappe.log_error("B2C Payment Failed", f"Payment failed - Code: {result_code}, Desc: {result_desc}")
            
            # TODO: Update transaction status to failed
            # TODO: Notify driver about payment failure
            # TODO: Queue for retry or manual processing
        
        return {"ResultCode": "0", "ResultDesc": "Success"}
        
    except Exception as e:
        frappe.log_error("B2C Result Error", f"Error processing B2C result: {str(e)}")
        return {"ResultCode": "0", "ResultDesc": "Success"}

@frappe.whitelist(allow_guest=True)
def b2c_timeout(**kwargs):
    """Handle B2C payment timeouts with enhanced processing"""
    try:
        # Log the timeout
        frappe.log_error("Production B2C Timeout", f"B2C timeout received: {json.dumps(kwargs, indent=2)}")
        
        # Extract timeout data
        result_data = kwargs.get('Result', {})
        conversation_id = result_data.get('ConversationID', '')
        result_desc = result_data.get('ResultDesc', 'Payment request timed out')
        
        # Log timeout details
        frappe.log_error("B2C Timeout Details", f"ConversationID: {conversation_id}, Description: {result_desc}")
        
        # TODO: Handle timeout scenario
        # - Mark payment as timed out
        # - Queue for retry
        # - Notify relevant parties
        
        return {"ResultCode": "0", "ResultDesc": "Success"}
        
    except Exception as e:
        frappe.log_error("B2C Timeout Error", f"Error processing B2C timeout: {str(e)}")
        return {"ResultCode": "0", "ResultDesc": "Success"}


# Function to test webhook endpoints
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
        # Test success webhook
        frappe.msgprint("Testing B2C result webhook...")
        b2c_result(**success_data)
        
        # Test timeout webhook  
        frappe.msgprint("Testing B2C timeout webhook...")
        b2c_timeout(**timeout_data)
        
        frappe.msgprint("✅ Webhook tests completed. Check Error Log for results.")
        
    except Exception as e:
        frappe.throw(f"Webhook test failed: {str(e)}")

# Function to check webhook URL accessibility
@frappe.whitelist()
def verify_webhook_urls():
    """Verify that webhook URLs are accessible from external calls"""
    import requests
    
    base_url = frappe.utils.get_url()
    result_url = f"{base_url}/api/method/tuktuk_management.api.sendpay.b2c_result"
    timeout_url = f"{base_url}/api/method/tuktuk_management.api.sendpay.b2c_timeout"
    
    frappe.msgprint(f"🔗 Your B2C Webhook URLs:")
    frappe.msgprint(f"Result URL: {result_url}")
    frappe.msgprint(f"Timeout URL: {timeout_url}")
    
    # These URLs should be accessible from external systems (Safaricom)
    # Make sure your firewall allows incoming connections to these endpoints
    
    return {
        "result_url": result_url,
        "timeout_url": timeout_url,
        "accessible": "URLs configured - ensure firewall allows external access"
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
            filters={"status": "Active"},
            fields=["driver_name", "mpesa_number"],
            limit=1
        )
        
        if not test_driver:
            frappe.throw("No active drivers found for testing")
            
        driver = test_driver[0]
        test_amount = 1.0  # 1 KSH test amount
        
        frappe.msgprint(f"🧪 Testing B2C payment of {test_amount} KSH to {driver.driver_name}")
        
        # Attempt the payment
        success = send_mpesa_payment(driver.mpesa_number, test_amount, "TEST")
        
        if success:
            frappe.msgprint("✅ B2C test payment initiated successfully!")
            frappe.msgprint("Check the Error Log for the API response details")
        else:
            frappe.msgprint("❌ B2C test payment failed")
            frappe.msgprint("Check the Error Log for error details")
            
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