# Fixed B2C Payment Function
# File: ~/frappe-bench/apps/tuktuk_management/tuktuk_management/api/tuktuk.py

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
            "QueueTimeOutURL": f"{frappe.utils.get_url()}/api/method/tuktuk_management.api.tuktuk.b2c_timeout",
            "ResultURL": f"{frappe.utils.get_url()}/api/method/tuktuk_management.api.tuktuk.b2c_result",
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

# ===== B2C PAYMENT FUNCTION =====


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