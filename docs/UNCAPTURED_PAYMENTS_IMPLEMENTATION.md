# Uncaptured Payments Feature - Implementation Summary

## Overview
Implemented a new "Uncaptured Payments" feature that allows System Managers and TukTuk Managers to manually record M-Pesa payments that were sent to wrong account numbers.

## Feature Description

When a customer accidentally sends a fare payment to the wrong M-Pesa account number, the driver can ask the customer to forward the SMS as proof of payment. The driver then comes to the office to claim payment. This feature provides two options:

1. **Send Driver Share:** Calculate driver share based on fare percentage and send via M-Pesa B2C
2. **Deposit Driver Share:** Credit the full amount to the driver's target balance without sending M-Pesa payment

## Files Modified

### 1. Frontend: `tuktuk_management/public/js/tuktuk_driver.js`

**Changes:**
- Added "Uncaptured Payments" button in the Admin section (line ~218)
- Implemented `process_uncaptured_payment(frm)` function
- Implemented `process_uncaptured_payment_action(frm, payment_data, action_type)` function

**Button Location:**
- Visible only to users with "System Manager" or "Tuktuk Manager" roles
- Located in the Admin button group alongside other admin functions

**User Flow:**
1. Click "Uncaptured Payments" button
2. Enter transaction details:
   - M-Pesa Transaction Number (required)
   - Customer Phone Number (required)
   - Amount Paid in KSH (required)
3. Review payment details in confirmation dialog
4. Choose action:
   - "Send Driver Share" - Primary action button
   - "Deposit Driver Share" - Secondary action button
5. Confirm the action
6. View success/error message
7. Form automatically refreshes to show updated data

### 2. Backend: `tuktuk_management/api/tuktuk.py`

**Changes:**
- Added `process_uncaptured_payment()` function after `create_adjustment_transaction()` (line ~546)

**Function Signature:**
```python
@frappe.whitelist()
def process_uncaptured_payment(driver, tuktuk, transaction_id, customer_phone, amount, action_type)
```

**Input Validation:**
- Verifies driver has assigned TukTuk
- Validates M-Pesa transaction number doesn't already exist
- Validates amount is positive and non-zero
- Validates action_type is either 'send_share' or 'deposit_share'

**Processing Logic:**

#### Send Driver Share (action_type='send_share')
1. Calculate driver share based on fare percentage and target sharing settings
2. Calculate target contribution (amount - driver_share)
3. Create TukTuk Transaction with type "Payment"
4. Update driver's `current_balance` with target contribution
5. Send B2C payment to driver for driver_share amount
6. Set payment_status based on B2C result
7. Add comment explaining this is an uncaptured payment
8. Log transaction details

**Transaction Fields:**
- `transaction_type`: "Payment"
- `transaction_id`: M-Pesa transaction code
- `amount`: Full payment amount
- `driver_share`: Calculated based on fare percentage
- `target_contribution`: amount - driver_share
- `customer_phone`: Customer's phone number
- `payment_status`: "Completed" if B2C succeeds, "Pending" if fails
- `b2c_payment_sent`: 1 (after B2C attempt)

#### Deposit Driver Share (action_type='deposit_share')
1. Create TukTuk Transaction with type "Adjustment"
2. Set driver_share = 0 (no payment sent)
3. Set target_contribution = full amount
4. Update driver's `current_balance` by full amount
5. Set payment_status = "Completed"
6. Set b2c_payment_sent = 1 (prevent accidental triggers)
7. Add comment explaining this is an uncaptured payment deposited to balance
8. Log transaction details

**Transaction Fields:**
- `transaction_type`: "Adjustment"
- `transaction_id`: M-Pesa transaction code
- `amount`: Full payment amount
- `driver_share`: 0
- `target_contribution`: Full amount
- `customer_phone`: Customer's phone number
- `payment_status`: "Completed"
- `b2c_payment_sent`: 1

## Key Technical Details

### Duplicate Prevention
- System checks if transaction_id already exists before creating new transaction
- Throws error if duplicate found

### Target Sharing Logic (Send Driver Share)
The system respects the existing target sharing logic:
- If target sharing is enabled AND driver has met daily target: driver_share = 100%, target_contribution = 0
- Otherwise: driver_share = amount × (fare_percentage / 100), target_contribution = amount - driver_share

### Balance Updates
- **Send Driver Share:** Updates `current_balance` with `target_contribution` only
- **Deposit Driver Share:** Updates `current_balance` with full `amount`

### B2C Payment Integration
- Uses existing `send_mpesa_payment()` function from `tuktuk_management.api.sendpay`
- Payment type: "FARE"
- Handles B2C failures gracefully (transaction recorded, payment failure logged)

### Report Exclusion
Adjustment transactions (Deposit Driver Share) are excluded from earnings calculations in reports:
- Not counted in total trips
- Not included in total revenue
- Not included in total driver earnings
- Tracked separately in adjustment counts/amounts

This is consistent with existing adjustment transaction handling in reports like:
- Driver Performance Report
- TukTuk Driver Statement

### Audit Trail
Both options create comprehensive audit trails:
- Transaction records with all details
- Comments explaining the uncaptured payment context
- Error log entries for B2C payment attempts
- Balance change tracking

## Security Considerations

1. **Role-Based Access Control:** Only System Managers and TukTuk Managers can access the feature
2. **Input Validation:** All inputs are validated before processing
3. **Duplicate Prevention:** Transaction IDs are checked for uniqueness
4. **Transaction Integrity:** Database commits are handled properly with error rollback
5. **Audit Logging:** All actions are logged in Error Log for tracking

## Testing

A comprehensive testing guide has been created: `UNCAPTURED_PAYMENTS_TESTING.md`

Key test scenarios:
1. Send Driver Share with B2C payment
2. Deposit Driver Share without B2C payment
3. Duplicate transaction ID validation
4. Missing TukTuk validation
5. Invalid input validation
6. Report exclusion verification
7. Target sharing logic verification

## Integration with Existing Features

This feature integrates seamlessly with:
- Existing transaction management system
- B2C payment infrastructure
- Driver balance tracking
- Target contribution calculations
- Report generation (with proper exclusions)
- Audit and logging systems

## Future Enhancements (Optional)

Potential improvements for future iterations:
1. Bulk uncaptured payment processing
2. SMS notification to driver when payment is processed
3. Dashboard widget showing pending uncaptured payments
4. Integration with customer verification system
5. Automatic reconciliation with M-Pesa statements
6. Photo upload for SMS proof of payment

## Support and Troubleshooting

Common issues and solutions are documented in `UNCAPTURED_PAYMENTS_TESTING.md` under the "Troubleshooting" section.

For additional support:
1. Check Error Log for detailed error messages
2. Verify TukTuk Settings configuration
3. Verify driver has correct M-Pesa number
4. Verify driver has assigned TukTuk
5. Check transaction list for duplicate IDs

