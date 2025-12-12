# SMS Driver Communication Guide

## Overview

The TukTuk Management system now provides powerful SMS communication tools that allow managers to send personalized SMS messages to individual drivers or groups of drivers directly from the driver interface.

## Features

### 1. Individual Driver SMS (Form View)
Send personalized SMS messages to a specific driver from their profile page.

### 2. Bulk Driver SMS (List View)
Send SMS messages to multiple drivers at once with flexible recipient selection options.

### 3. Field Interpolation
Use dynamic placeholders in your messages that automatically get replaced with each driver's actual data.

## Accessing SMS Features

### Send SMS to Individual Driver

1. Navigate to **TukTuk Driver** list
2. Open any driver's profile
3. Click on **Communications** dropdown in the toolbar
4. Select **SMS Driver**
5. Compose your message and click **Send SMS**

**Requirements:**
- User must have role: **System Manager** or **Tuktuk Manager**
- Driver must have an M-Pesa number configured

### Send SMS to Multiple Drivers

1. Navigate to **TukTuk Driver** list view
2. Click on **Actions** dropdown (or the three-dot menu)
3. Select **SMS Drivers**
4. Select recipients and compose your message
5. Click **Send SMS**

**Requirements:**
- User must have role: **System Manager** or **Tuktuk Manager**
- Drivers must have M-Pesa numbers configured

## Field Interpolation

### Available Fields

You can use these placeholders in your messages. They will be automatically replaced with each driver's actual values:

| Placeholder | Description | Example Output |
|------------|-------------|----------------|
| `{driver_name}` | Full name of the driver | "John Doe" |
| `{sunny_id}` | Driver's Sunny ID | "D112001" |
| `{left_to_target}` | Amount remaining to reach daily target | "1,250" |
| `{current_balance}` | Current target balance | "1,750" |
| `{daily_target}` | Driver's daily target amount | "3,000" |
| `{assigned_tuktuk}` | Assigned TukTuk ID | "TUK-001" or "None" |
| `{mpesa_number}` | Driver's M-Pesa phone number | "254712345678" |
| `{mpesa_paybill}` | M-Pesa Paybill number from settings | "123456" |
| `{mpesa_account}` | M-Pesa account number from assigned vehicle | "001" or "" |
| `{current_deposit_balance}` | Current deposit balance | "5,000" |

### Field Interpolation Examples

#### Example 1: Target Reminder
```
Hello {driver_name}! You have KES {left_to_target} left to complete today's target. Keep going!
```

**Result for John Doe:**
```
Hello John Doe! You have KES 1,250 left to complete today's target. Keep going!
```

#### Example 2: Performance Update
```
Hi {driver_name}, your current balance is KES {current_balance}. Daily target: KES {daily_target}. Great work!
```

**Result for Jane Smith:**
```
Hi Jane Smith, your current balance is KES 2,500. Daily target: KES 3,000. Great work!
```

#### Example 3: Assignment Notification
```
{driver_name}, you are assigned to {assigned_tuktuk}. Today's target: KES {daily_target}. Good luck!
```

**Result for Mike Johnson:**
```
Mike Johnson, you are assigned to TUK-005. Today's target: KES 3,000. Good luck!
```

#### Example 4: Custom Message
```
Reminder for {driver_name}: Please ensure {assigned_tuktuk} is charged. Contact us at +254712345678 if you need assistance.
```

## Bulk SMS Recipient Options

When sending bulk SMS, you can select recipients using these filters:

### 1. All Drivers
Sends SMS to **every driver** in the system.

### 2. All Assigned Drivers
Sends SMS only to drivers who have a **TukTuk assigned**.

### 3. All Unassigned Drivers
Sends SMS only to drivers who **do not have a TukTuk assigned**.

### 4. Drivers with Remaining Target
Sends SMS only to drivers who have **not yet reached their daily target** (`left_to_target > 0`).

### 5. Select Specific Drivers
Allows you to **manually select** which drivers receive the SMS.

## SMS Preview

Both individual and bulk SMS interfaces provide a **live preview** feature:

- As you type your message, the preview shows how it will look
- Field placeholders are replaced with actual values
- Helps you verify the message before sending

## SMS Delivery Status

After sending SMS:

### Success Indicators
- Green notification: "SMS sent successfully"
- Shows count of successfully sent messages
- Logged in Error Log with "SMS Success" title

### Failure Indicators
- Red notification: "SMS Failed"
- Shows count of failed messages
- Detailed error information in Error Log with "SMS Send Error" title

### Bulk SMS Summary
For bulk SMS, you'll see:
- **Total Recipients:** Number of drivers selected
- **Successfully Sent:** Count of successful deliveries
- **Failed:** Count of failed deliveries
- Individual status for each driver in the results

## Use Cases

### 1. Daily Target Reminders
```
Good morning {driver_name}! Today's target is KES {daily_target}. You can do this!
```

### 2. Mid-Day Performance Update
```
Hi {driver_name}, you've earned KES {current_balance} so far. Only KES {left_to_target} to go!
```

### 3. End of Day Congratulations
```
Congratulations {driver_name}! You've completed your target. Well done!
```

### 4. Vehicle Maintenance Reminders
```
{driver_name}, please ensure {assigned_tuktuk} battery is charged before tomorrow.
```

### 5. Emergency Notifications
```
URGENT: {driver_name}, please contact the office immediately regarding {assigned_tuktuk}.
```

### 6. General Announcements
```
Attention {driver_name}: Office will be closed on Monday. Contact emergency line for urgent issues.
```

## Best Practices

### Message Composition

1. **Keep it Short:** SMS messages work best under 160 characters
2. **Be Clear:** Use simple, direct language
3. **Be Specific:** Include relevant details like amounts and vehicle IDs
4. **Be Respectful:** Maintain professional tone
5. **Test First:** Send a test message to yourself before bulk sending

### Timing

1. **Consider Time Zones:** Send during appropriate business hours
2. **Avoid Late Hours:** Don't send between 10 PM - 7 AM unless urgent
3. **Schedule Reminders:** Send target reminders in the morning or mid-day
4. **Timely Updates:** Send performance updates when they're most relevant

### Personalization

1. **Use Names:** Always include `{driver_name}` for personal touch
2. **Relevant Data:** Include fields that matter to the message context
3. **Context Matters:** Match message tone to the situation

### Verification

1. **Preview Messages:** Always check the preview before sending
2. **Verify Recipients:** Double-check recipient selection for bulk SMS
3. **Check Phone Numbers:** Ensure drivers have valid M-Pesa numbers
4. **Review Logs:** Check Error Log for delivery status

## Troubleshooting

### Issue: "Driver does not have an M-Pesa number configured"

**Solution:**
1. Open the driver's profile
2. Navigate to **Payment** tab
3. Enter valid M-Pesa phone number in format: `254712345678`
4. Save the driver profile

### Issue: "SMS Failed" for individual driver

**Solution:**
1. Check **Error Log** for detailed error message
2. Verify driver's M-Pesa number is correct
3. Ensure SMS notifications are enabled in **TukTuk Settings**
4. Verify SMS provider credentials are configured
5. Check your SMS account balance (for TextSMS or TextBee)

### Issue: Some messages sent, others failed in bulk SMS

**Solution:**
1. Review the results summary
2. Check which drivers failed (usually those without phone numbers)
3. Update missing phone numbers
4. Resend to failed recipients only

### Issue: Field placeholders not being replaced

**Solution:**
1. Ensure you're using correct syntax: `{field_name}`
2. Check spelling of field names
3. Use only supported field placeholders (see table above)
4. Contact system administrator if issue persists

### Issue: Message preview not showing

**Solution:**
1. Refresh the page and try again
2. Clear browser cache
3. Ensure JavaScript is enabled
4. Try a different browser

## SMS Provider Configuration

Before using SMS features, ensure SMS is properly configured:

1. Go to **TukTuk Settings**
2. Navigate to **Notifications** tab
3. Enable **SMS Notifications**
4. Select **SMS Provider** (TextBee or TextSMS)
5. Configure provider credentials:
   - **TextBee:** Enter API Key
   - **TextSMS:** Enter API Key, Partner ID, and Sender ID
6. Save settings

For detailed SMS provider setup, see: [TEXTSMS_INTEGRATION_GUIDE.md](TEXTSMS_INTEGRATION_GUIDE.md)

## Security & Permissions

### Required Roles

SMS functionality is restricted to:
- **System Manager**
- **Tuktuk Manager**

Regular users and drivers cannot send SMS messages.

### Audit Trail

All SMS activities are logged:
- **Success:** Logged with "SMS Success" title
- **Failures:** Logged with "SMS Send Error" title
- **Bulk Operations:** Logged with "Bulk SMS with Fields Summary" title

To view logs:
1. Navigate to **Error Log**
2. Filter by title to find specific SMS events
3. Review detailed information including message content, recipients, and status

## API Reference

For developers integrating SMS functionality:

### Send SMS to Individual Driver

```python
frappe.call({
    method: 'tuktuk_management.api.sms_notifications.send_driver_sms_with_fields',
    args: {
        driver_name: 'DRV-112001',
        message_template: 'Hello {driver_name}! Target: KES {daily_target}'
    }
})
```

### Send Bulk SMS

```python
frappe.call({
    method: 'tuktuk_management.api.sms_notifications.send_bulk_sms_with_fields',
    args: {
        driver_ids: ['DRV-112001', 'DRV-112002', 'DRV-112003'],
        message_template: 'Hello {driver_name}! You have KES {left_to_target} to go!'
    }
})
```

## Related Documentation

- [SMS Testing Guide](SMS_TESTING_GUIDE.md)
- [SMS Broadcast Guide](SMS_BROADCAST_GUIDE.md)
- [TextSMS Integration Guide](TEXTSMS_INTEGRATION_GUIDE.md)

## Support

For assistance with SMS features:
1. Check Error Log for detailed error messages
2. Review this guide for common solutions
3. Contact your system administrator
4. For provider-specific issues, contact TextBee or TextSMS support

