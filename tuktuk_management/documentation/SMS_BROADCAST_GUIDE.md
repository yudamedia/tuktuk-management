# SMS Broadcast Interface Guide

## Overview
The SMS Broadcast interface allows you to send custom SMS messages to selected drivers or broadcast to all drivers at once.

## Accessing the Interface

### Method 1: Direct URL
Navigate to: `https://your-site.com/sms-broadcast`

### Method 2: From Workspace
1. Go to **Tuktuk Management** workspace
2. Look for **SMS Broadcast** in the menu (if added to workspace)
3. Or use the direct URL above

## Features

### 1. Driver Selection
- **Search**: Use the search box to filter drivers by name or phone number
- **Select All**: Click "Select All" to select all drivers at once
- **Deselect All**: Click "Deselect All" to clear all selections
- **Individual Selection**: Click on any driver to select/deselect them
- **Visual Indicators**:
  - Green badge = Assigned driver
  - Gray badge = Unassigned driver
  - Red text = No phone number configured

### 2. Message Composition
- **Text Area**: Enter your custom message
- **Character Counter**: Shows message length (SMS limit ~160 characters)
- **Warning Colors**:
  - Normal: Black
  - Warning (>140 chars): Orange
  - Danger (>160 chars): Red

### 3. Sending SMS
- **Send Button**: Only enabled when:
  - At least one driver is selected
  - Message is not empty
- **Preview**: Click "Preview" to see how the message will look
- **Confirmation**: System asks for confirmation before sending

### 4. Results
After sending, you'll see:
- **Summary**: Total sent, successful, and failed counts
- **Detailed Results**: Per-driver status with success/failure messages
- **Color Coding**:
  - Green = Success
  - Red = Failed

## Usage Examples

### Example 1: Send to All Drivers
1. Click "Select All"
2. Enter message: "Reminder: Please submit your daily report by 6 PM"
3. Click "Send SMS"
4. Confirm the action

### Example 2: Send to Specific Drivers
1. Use search to find specific drivers
2. Select individual drivers by clicking on them
3. Enter your message
4. Click "Send SMS"

### Example 3: Send to Assigned Drivers Only
1. Search for drivers
2. Select only drivers with green "Assigned" badges
3. Enter message
4. Send

## Permissions

Only users with these roles can access:
- **System Manager**
- **Tuktuk Manager**

## Troubleshooting

### Issue: Page shows "Access denied"
**Solution**: Ensure your user has System Manager or Tuktuk Manager role

### Issue: "SMS notifications are not properly configured"
**Solution**: 
1. Go to **TukTuk Settings** → **Notifications** tab
2. Enable "SMS Notifications"
3. Enter your TextBee API key
4. Save settings

### Issue: Some drivers show "No phone number"
**Solution**: 
1. Open the driver's record
2. Go to **Payment Details** tab
3. Add M-Pesa number
4. Save

### Issue: SMS sending fails
**Solution**:
1. Check Error Log for detailed error messages
2. Verify TextBee API key is correct
3. Check your TextBee account balance
4. Ensure phone numbers are in correct format (254XXXXXXXXX)

## Best Practices

1. **Test First**: Send a test SMS to yourself before broadcasting
2. **Keep Messages Short**: Stay under 160 characters for single SMS
3. **Check Phone Numbers**: Verify drivers have valid phone numbers before sending
4. **Review Results**: Always check the results panel after sending
5. **Use Search**: Use the search function to find specific drivers quickly

## Technical Details

### API Endpoints Used
- `get_all_drivers_for_broadcast` - Fetches all drivers
- `send_broadcast_sms` - Sends SMS to selected drivers

### Message Format
Messages are sent exactly as typed. No automatic formatting is applied unless you use the "Include target reminder info" option (if implemented).

### Rate Limiting
The system sends SMS sequentially to avoid overwhelming the API. Large broadcasts may take a few minutes to complete.

## Support

For issues:
1. Check Error Log in Frappe
2. Verify TextBee API configuration
3. Check individual driver phone numbers
4. Review SMS Broadcast Summary in Error Log

