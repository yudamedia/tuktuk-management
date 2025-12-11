# TextSMS.co.ke Integration Guide

## Overview

The TukTuk Management system now supports **two SMS providers**:
1. **TextBee** (existing)
2. **TextSMS.co.ke** (new)

You can switch between providers via the TukTuk Settings interface.

## Configuration Steps

### 1. Navigate to TukTuk Settings

Go to **TukTuk Settings** in your Frappe/ERPNext instance and open the **Notifications** tab.

### 2. Enable SMS Notifications

Check the **Enable SMS Notifications** checkbox.

### 3. Select SMS Provider

From the **SMS Provider** dropdown, select either:
- **TextBee** (default)
- **TextSMS**

### 4. Configure Provider Credentials

#### For TextBee:
- Enter your **TextBee API Key**

#### For TextSMS:
- Enter your **TextSMS API Key**
- Enter your **TextSMS Partner ID**
- Enter your **TextSMS Sender ID** (the shortcode/sender name for outgoing messages)

### 5. Save Settings

Click **Save** to apply the configuration.

## TextSMS API Details

### Endpoint
```
https://sms.textsms.co.ke/api/services/sendsms/
```

### Request Format
```json
{
  "apikey": "your-api-key",
  "partnerID": "your-partner-id",
  "message": "SMS message text",
  "shortcode": "your-sender-id",
  "mobile": "254712345678"
}
```

### Response Codes
- **200**: Success
- **1001**: Invalid sender ID
- **1002**: Network not allowed
- **1003**: Invalid mobile number
- **1004**: Low bulk credits
- **1005**: Failed. System error
- **1006**: Invalid credentials
- **1007**: Failed. System error
- **1008**: No Delivery Report
- **1009**: Unsupported data type
- **1010**: Unsupported request type
- **4090**: Internal Error. Try again after 5 minutes
- **4091**: No Partner ID is Set
- **4092**: No API KEY Provided
- **4093**: Details Not Found

## Features

All SMS notification features work with both providers:

1. **Scheduled Target Reminders** - Automatic SMS reminders to drivers about their daily targets
2. **Manual Test SMS** - Send test SMS to specific drivers
3. **Broadcast SMS** - Send SMS to multiple selected drivers
4. **Status Checking** - Check SMS configuration and eligible drivers

## Testing the Integration

### Method 1: Check SMS Status

From Frappe console:
```python
frappe.call('tuktuk_management.api.sms_notifications.get_sms_status')
```

This will return:
- Current SMS provider
- Configuration status
- Eligible drivers count

### Method 2: Test SMS to Specific Driver

From Frappe console:
```python
result = frappe.call(
    'tuktuk_management.api.sms_notifications.test_sms_to_driver',
    driver_name='DRV-112001'  # Replace with actual driver ID
)
print(result)
```

### Method 3: Check Error Logs

Navigate to **Error Log** in Frappe to see detailed SMS sending logs:
- Success logs are tagged with "SMS Success"
- Failure logs are tagged with "SMS Send Error"
- Provider-specific error codes are logged

## Switching Between Providers

To switch from TextBee to TextSMS (or vice versa):

1. Go to **TukTuk Settings** → **Notifications** tab
2. Change the **SMS Provider** dropdown selection
3. Fill in the credentials for the new provider
4. Click **Save**

The system will immediately start using the new provider for all SMS operations.

## Validation

The system validates that:
- When **TextBee** is selected and SMS is enabled, the TextBee API Key must be configured
- When **TextSMS** is selected and SMS is enabled, all three fields (API Key, Partner ID, Sender ID) must be configured

If validation fails, you'll see an error message indicating which field is missing.

## Migration Notes

- The existing TextBee integration remains fully functional
- All SMS functions now use a generic routing layer that automatically selects the correct provider
- No changes are required to existing code that calls SMS functions
- The default provider is TextBee for backward compatibility

## API Reference

### Generic SMS Function

All SMS sending now goes through a generic router:

```python
from tuktuk_management.api.sms_notifications import send_sms

# Automatically routes to the configured provider
success = send_sms(phone_number="254712345678", message="Hello Driver!")
```

### Provider-Specific Functions

You can also call provider-specific functions directly if needed:

```python
from tuktuk_management.api.sms_notifications import send_textbee_sms, send_textsms_sms

# Send via TextBee
send_textbee_sms(phone_number="254712345678", message="Hello!")

# Send via TextSMS
send_textsms_sms(phone_number="254712345678", message="Hello!")
```

## Troubleshooting

### Issue: "TextSMS credentials not fully configured"

**Solution:** Ensure all three fields are filled:
1. TextSMS API Key
2. TextSMS Partner ID
3. TextSMS Sender ID

### Issue: Error Code 1006 (Invalid credentials)

**Solution:** 
1. Verify your API Key and Partner ID are correct
2. Check that you copied them correctly from TextSMS.co.ke
3. Ensure there are no extra spaces

### Issue: Error Code 1004 (Low bulk credits)

**Solution:** Top up your TextSMS account balance

### Issue: Error Code 1001 (Invalid sender ID)

**Solution:** 
1. Ensure your Sender ID is registered with TextSMS
2. Use a valid shortcode provided by TextSMS
3. Contact TextSMS support to register your Sender ID

### Issue: SMS not being sent

**Solution:**
1. Check that SMS notifications are enabled in TukTuk Settings
2. Verify the correct provider is selected
3. Check Error Log for detailed error messages
4. Run `get_sms_status()` to verify configuration

## Support

For TextSMS API issues:
- Website: https://textsms.co.ke
- Email: info@textsms.co.ke
- Phone: +254 721 351 269 | +254 707 559 080

For TukTuk Management system issues:
- Check Error Log in Frappe
- Review this guide
- Contact your system administrator

