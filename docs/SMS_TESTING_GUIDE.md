# SMS Driver Target Reminder - Testing Guide

## Overview
This guide explains how to test the SMS notification system that sends periodic target reminders to drivers.

## Prerequisites

1. **TextBee API Key**: Obtain your API key from TextBee
2. **Active Drivers**: Have at least one driver with:
   - An assigned TukTuk (`assigned_tuktuk` field populated)
   - A remaining target balance (`left_to_target > 0`)
   - A valid M-Pesa number (`mpesa_number` field)

## Setup Steps

### 1. Configure TextBee API Key

1. Navigate to **TukTuk Settings** in your Frappe/ERPNext instance
2. Go to the **Notifications** tab
3. Enable **SMS Notifications** (check the box)
4. Enter your **TextBee API Key** in the password field
5. Save the settings

### 2. Verify Configuration

Use the status check function via Frappe console:

```python
frappe.call('tuktuk_management.api.sms_notifications.get_sms_status')
```

This will return:
- Whether SMS is enabled
- Whether API key is configured
- Count of eligible drivers
- List of eligible drivers with their details

## Testing Methods

### Method 1: Test SMS to Specific Driver (Console)

From Frappe console or bench console:

```python
# Test SMS to a specific driver
result = frappe.call(
    'tuktuk_management.api.sms_notifications.test_sms_to_driver',
    driver_name='DRV-112001'  # Replace with actual driver ID
)
print(result)
```

### Method 2: Test SMS to Specific Driver (API)

Using curl or any HTTP client:

```bash
curl -X POST \
  'https://your-site.com/api/method/tuktuk_management.api.sms_notifications.test_sms_to_driver' \
  -H 'Authorization: token YOUR_API_KEY:YOUR_API_SECRET' \
  -H 'Content-Type: application/json' \
  -d '{
    "driver_name": "DRV-112001"
  }'
```

### Method 3: Test Scheduled Function (Console)

Manually trigger the scheduled reminder function:

```python
# This will send SMS to ALL eligible drivers
from tuktuk_management.api.sms_notifications import send_driver_target_reminder
send_driver_target_reminder()
```

### Method 4: Check SMS Status (API)

```bash
curl -X GET \
  'https://your-site.com/api/method/tuktuk_management.api.sms_notifications.get_sms_status' \
  -H 'Authorization: token YOUR_API_KEY:YOUR_API_SECRET'
```

## Verify SMS Delivery

### 1. Check Error Logs

Navigate to **Error Log** in Frappe and look for:
- **SMS Success**: Successful SMS delivery logs
- **SMS Send Error**: Failed delivery attempts
- **SMS Reminder Summary**: Batch processing summaries

### 2. Check Actual SMS

Verify the driver receives an SMS with the format:
```
Hello [Driver Name]! You have KES [Amount] to complete today's target amount.
```

Example:
```
Hello John Kamau! You have KES 2,500 to complete today's target amount.
```

## Scheduled Execution Times

The system automatically sends reminders at:
- **8:00 AM EAT** (5:00 AM UTC)
- **12:00 PM EAT** (9:00 AM UTC)
- **5:00 PM EAT** (2:00 PM UTC)
- **9:00 PM EAT** (6:00 PM UTC)

## Troubleshooting

### Issue: No SMS being sent

**Check:**
1. Is `enable_sms_notifications` enabled in TukTuk Settings?
2. Is `textbee_api_key` configured?
3. Are there eligible drivers (assigned + left_to_target > 0)?
4. Do drivers have valid `mpesa_number` values?

**Solution:**
```python
# Run status check
result = frappe.call('tuktuk_management.api.sms_notifications.get_sms_status')
print(result)
```

### Issue: API Key Error

**Error in logs:** "TextBee API key not configured"

**Solution:**
1. Go to TukTuk Settings
2. Enter your TextBee API key
3. Save the settings

### Issue: No Eligible Drivers

**Error in logs:** "No eligible drivers found"

**Explanation:** All drivers have either:
- No assigned TukTuk (`assigned_tuktuk` is empty)
- Already reached their target (`left_to_target = 0`)

**Solution:**
- Assign a TukTuk to at least one driver
- Ensure the driver has a positive `left_to_target` value

### Issue: Invalid Phone Number

**Error in logs:** "Driver has no M-Pesa number configured"

**Solution:**
1. Open the driver's record
2. Go to **Payment Details** tab
3. Add a valid M-Pesa number (format: 254XXXXXXXXX)
4. Save the driver

### Issue: TextBee API Returns Error

**Check Error Log** for response details

**Common causes:**
1. Invalid API key
2. Insufficient SMS credits
3. Invalid phone number format
4. Network connectivity issues

**Solution:**
- Verify API key is correct
- Check your TextBee account balance
- Ensure phone numbers are in format: 254XXXXXXXXX

## Daily Reset Behavior

The system automatically handles target completion:
- When a driver reaches their target (`left_to_target = 0`), they stop receiving reminders
- At midnight (00:00 EAT), daily targets reset for all drivers
- SMS reminders resume the next day if targets haven't been met

## Performance Notes

The system is optimized for efficiency:
- Settings are cached (not queried repeatedly)
- Driver filtering happens at database level (no Python-side filtering)
- Failed SMS for one driver won't stop processing for others

## Manual Testing Checklist

- [ ] Configure TextBee API key in TukTuk Settings
- [ ] Enable SMS notifications
- [ ] Verify at least one eligible driver exists
- [ ] Run `get_sms_status()` to confirm configuration
- [ ] Run `test_sms_to_driver()` for a specific driver
- [ ] Verify SMS received on driver's phone
- [ ] Check Error Log for success message
- [ ] Test with driver who has `left_to_target = 0` (should not receive SMS)
- [ ] Test with unassigned driver (should not receive SMS)
- [ ] Verify scheduled jobs are configured in hooks.py

## Support

For issues or questions:
1. Check Error Log for detailed error messages
2. Use `get_sms_status()` to diagnose configuration issues
3. Review this testing guide
4. Contact TextBee support for API-related issues

