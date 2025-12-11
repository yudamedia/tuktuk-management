# Uncaptured Payments - Quick Start Guide

## What is this feature?

When a customer accidentally sends a fare payment to the wrong M-Pesa account number, this feature allows office staff to manually record the payment and either:
1. Send the driver their share via M-Pesa B2C, OR
2. Add the full amount to the driver's target balance

## How to use it

### Step 1: Access the Feature
1. Open a TukTuk Driver form
2. Ensure the driver has an assigned TukTuk
3. Look for the **"Uncaptured Payments"** button in the **Admin** section
4. (Only visible to System Managers and TukTuk Managers)

### Step 2: Enter Payment Details
Click the button and enter:
- **M-Pesa Transaction Number**: The transaction code from the SMS (e.g., SH12ABC3XY)
- **Customer Phone Number**: The customer's phone number (e.g., 254712345678)
- **Amount Paid**: The amount the customer paid (e.g., 1000)

### Step 3: Choose Action

#### Option A: Send Driver Share
- Calculates driver share based on fare percentage (e.g., 70%)
- Sends M-Pesa B2C payment to driver
- Adds target contribution to driver's balance (e.g., 30%)
- Creates a "Payment" type transaction

**Use when:** Driver wants immediate M-Pesa payment

#### Option B: Deposit Driver Share
- Adds the FULL amount to driver's target balance
- Does NOT send M-Pesa payment
- Creates an "Adjustment" type transaction
- Bypasses "deposit required" check

**Use when:** Driver prefers to accumulate balance for later withdrawal

### Step 4: Confirm
- Review the payment details
- Click your chosen action button
- Confirm the action
- Wait for success message
- Form will refresh automatically

## Key Differences Between Options

| Feature | Send Driver Share | Deposit Driver Share |
|---------|------------------|---------------------|
| Transaction Type | Payment | Adjustment |
| M-Pesa B2C Sent | Yes | No |
| Driver Share | Calculated (e.g., 70%) | 0 |
| Target Contribution | Calculated (e.g., 30%) | Full Amount (100%) |
| Balance Update | Target contribution only | Full amount |
| Included in Earnings Reports | Yes | No (tracked separately) |

## Important Notes

✅ **DO:**
- Verify the M-Pesa transaction number is correct
- Ensure the transaction ID is unique
- Confirm the amount with the driver
- Check that the driver has an assigned TukTuk

❌ **DON'T:**
- Use the same transaction ID twice
- Process payments for drivers without assigned TukTuks
- Enter zero or negative amounts

## Troubleshooting

### "Transaction ID already exists"
- This transaction has already been recorded
- Check the TukTuk Transaction list for the existing entry

### "Driver must have an assigned TukTuk"
- Assign a TukTuk to the driver first
- Use the "Assign TukTuk" button in the Actions section

### "B2C payment failed"
- The transaction is still recorded
- Check Error Log for details
- Verify driver's M-Pesa number is correct
- Payment can be retried manually

## Where to Find Records

- **Transaction List**: TukTuk Transaction doctype
- **Driver Balance**: Driver form, current_balance field
- **Payment Logs**: Error Log (for B2C payment status)
- **Reports**: Driver Performance Report, TukTuk Driver Statement

## Need Help?

Refer to the detailed documentation:
- `UNCAPTURED_PAYMENTS_IMPLEMENTATION.md` - Technical details
- `UNCAPTURED_PAYMENTS_TESTING.md` - Testing guide and troubleshooting

