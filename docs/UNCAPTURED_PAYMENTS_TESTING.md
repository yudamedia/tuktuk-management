# Uncaptured Payments Feature - Testing Guide

## Overview
This document provides testing instructions for the new "Uncaptured Payments" feature that allows System Managers and TukTuk Managers to record payments sent to wrong account numbers.

## Prerequisites
1. User must have "System Manager" or "TukTuk Manager" role
2. Driver must have an assigned TukTuk
3. Frappe bench must be running

## Test Scenarios

### Test 1: Send Driver Share Option

**Objective:** Verify that the "Send Driver Share" option correctly calculates driver share, creates a Payment transaction, updates driver balance, and sends B2C payment.

**Steps:**
1. Navigate to a TukTuk Driver doctype form
2. Ensure the driver has an assigned TukTuk
3. Click the "Uncaptured Payments" button in the Admin section
4. Enter test data:
   - M-Pesa Transaction Number: `TEST001` (use unique ID each test)
   - Customer Phone Number: `254712345678`
   - Amount Paid: `1000`
5. Click "Next"
6. Review the payment details dialog
7. Click "Send Driver Share"
8. Confirm the action

**Expected Results:**
- Transaction is created with type "Payment"
- Driver share is calculated based on fare percentage (e.g., 70% = 700 KSH)
- Target contribution is calculated (e.g., 30% = 300 KSH)
- Driver's `current_balance` is updated with target contribution
- B2C payment is sent to driver's M-Pesa number for driver share amount
- Transaction status is "Completed" if B2C succeeds, "Pending" if it fails
- Success message displays transaction details
- Driver form refreshes to show updated balance

**Validation Checks:**
- Check TukTuk Transaction list for new transaction with ID `TEST001`
- Verify transaction fields:
  - `transaction_type`: "Payment"
  - `amount`: 1000
  - `driver_share`: 700 (or based on driver's fare percentage)
  - `target_contribution`: 300 (or based on driver's fare percentage)
  - `customer_phone`: "254712345678"
  - `b2c_payment_sent`: 1
  - Comment: "Uncaptured payment - sent to wrong account..."
- Verify driver's `current_balance` increased by target contribution
- Check Error Log for B2C payment success/failure message

### Test 2: Deposit Driver Share Option

**Objective:** Verify that the "Deposit Driver Share" option creates an Adjustment transaction, adds full amount to driver balance, and does NOT send B2C payment.

**Steps:**
1. Navigate to a TukTuk Driver doctype form
2. Note the driver's current `current_balance` value
3. Click the "Uncaptured Payments" button
4. Enter test data:
   - M-Pesa Transaction Number: `TEST002` (use unique ID each test)
   - Customer Phone Number: `254723456789`
   - Amount Paid: `1500`
5. Click "Next"
6. Review the payment details dialog
7. Click "Deposit Driver Share"
8. Confirm the action

**Expected Results:**
- Transaction is created with type "Adjustment"
- `driver_share` is 0 (no payment sent)
- `target_contribution` is full amount (1500)
- Driver's `current_balance` is updated with full amount
- NO B2C payment is sent
- Transaction status is "Completed"
- Success message shows new balance
- Driver form refreshes to show updated balance

**Validation Checks:**
- Check TukTuk Transaction list for new transaction with ID `TEST002`
- Verify transaction fields:
  - `transaction_type`: "Adjustment"
  - `amount`: 1500
  - `driver_share`: 0
  - `target_contribution`: 1500
  - `customer_phone`: "254723456789"
  - `payment_status`: "Completed"
  - `b2c_payment_sent`: 1 (flag to prevent accidental triggers)
  - Comment: "Uncaptured payment deposited to balance..."
- Verify driver's `current_balance` increased by 1500
- Verify NO B2C payment was sent (check Error Log - should NOT have B2C entry for this transaction)

### Test 3: Duplicate Transaction ID Validation

**Objective:** Verify that the system prevents duplicate transaction IDs.

**Steps:**
1. Complete Test 1 or Test 2 with transaction ID `TEST003`
2. Attempt to create another uncaptured payment with the same transaction ID `TEST003`

**Expected Results:**
- Error message: "Transaction ID TEST003 already exists in the system"
- No new transaction is created
- Driver balance is not modified

### Test 4: Missing TukTuk Validation

**Objective:** Verify that drivers without assigned TukTuks cannot record uncaptured payments.

**Steps:**
1. Navigate to a TukTuk Driver without an assigned TukTuk
2. Click the "Uncaptured Payments" button

**Expected Results:**
- Error message: "Driver must have an assigned TukTuk to record uncaptured payments"
- Dialog does not open

### Test 5: Invalid Input Validation

**Objective:** Verify input validation for transaction details.

**Steps:**
1. Click "Uncaptured Payments" button
2. Test each invalid input:
   - Empty transaction ID
   - Empty customer phone
   - Zero amount
   - Negative amount
   - Non-numeric amount

**Expected Results:**
- Appropriate validation error messages
- Transaction is not created

### Test 6: Report Exclusion (Deposit Driver Share)

**Objective:** Verify that "Deposit Driver Share" adjustment transactions are excluded from earnings calculations in reports.

**Steps:**
1. Create a "Deposit Driver Share" transaction (Test 2)
2. Navigate to "Driver Performance Report"
3. Filter for the test driver
4. Check the earnings calculations

**Expected Results:**
- The adjustment transaction should NOT be included in:
  - Total trips count
  - Total revenue
  - Total driver earnings
- The adjustment should be tracked separately in adjustment counts/amounts
- Driver's target balance should reflect the deposited amount

### Test 7: Target Sharing Logic (Send Driver Share)

**Objective:** Verify that target sharing logic is applied correctly when sending driver share.

**Test 7a: Target Not Met**
- Driver's `current_balance` < `daily_target`
- Expected: Driver share calculated using fare percentage

**Test 7b: Target Met with Target Sharing Enabled**
- Driver's `current_balance` >= `daily_target`
- Target sharing enabled (global or driver override)
- Expected: Driver share = 100% of amount, target contribution = 0

**Test 7c: Target Met with Target Sharing Disabled**
- Driver's `current_balance` >= `daily_target`
- Target sharing disabled (driver override)
- Expected: Driver share calculated using fare percentage

## Regression Testing

After implementing this feature, verify that existing functionality still works:

1. **Normal M-Pesa Payments:** Verify regular customer payments still process correctly
2. **Manual Withdrawals:** Verify manual withdrawal button still works
3. **Deposit Management:** Verify deposit top-ups and deductions still work
4. **Driver Exit Processing:** Verify driver exit process handles all transaction types
5. **Reports:** Verify all reports still calculate correctly with new transaction types

## Security Testing

1. **Role-Based Access:** Verify that users without "System Manager" or "Tuktuk Manager" roles cannot see or use the "Uncaptured Payments" button
2. **SQL Injection:** Test with special characters in transaction ID and customer phone
3. **XSS Prevention:** Test with HTML/JavaScript in input fields

## Performance Testing

1. Test with large transaction amounts
2. Test with multiple concurrent uncaptured payment submissions
3. Verify database transactions are properly committed/rolled back on errors

## Known Limitations

1. The feature requires the driver to have an assigned TukTuk
2. Transaction IDs must be unique across the entire system
3. B2C payment failures are logged but the transaction is still recorded
4. Customer phone numbers are stored as provided (not hashed like regular transactions)

## Troubleshooting

### B2C Payment Fails
- Check Error Log for detailed error message
- Verify driver's M-Pesa number is correct
- Verify TukTuk Settings has correct B2C credentials
- Transaction is still recorded, payment can be retried manually

### Transaction Not Created
- Check Error Log for validation errors
- Verify all required fields are provided
- Verify transaction ID is unique
- Verify driver has assigned TukTuk

### Balance Not Updated
- Check if transaction was created successfully
- Verify transaction type (Adjustment for deposit, Payment for send)
- Check target_contribution field value
- Refresh driver form to see latest balance

