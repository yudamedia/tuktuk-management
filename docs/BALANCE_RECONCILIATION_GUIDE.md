# Balance Reconciliation Guide

## Overview

This guide explains the fixes implemented to prevent `current_balance` discrepancies and how to use the reconciliation tools.

## Problem Statement

The `current_balance` field was occasionally missing transactions due to:

1. **Race Conditions**: Concurrent transactions reading the same stale balance value
2. **Non-Atomic Updates**: Read-modify-save pattern vulnerable to lost updates
3. **Missing Commits**: Balance updates not committed before errors occurred

## Implemented Fixes

### 1. Database Row Locking

The driver document is now loaded with `for_update=True` inside a database transaction, preventing concurrent modifications:

```python
# BEFORE (vulnerable to race conditions)
driver = frappe.get_doc("TukTuk Driver", driver_name)
# ... calculate shares ...
driver.current_balance += target_contribution
driver.save()

# AFTER (protected by row lock)
frappe.db.savepoint('transaction_savepoint')
driver = frappe.get_doc("TukTuk Driver", driver_name, for_update=True)
# ... calculate shares ...
frappe.db.sql("""
    UPDATE `tabTukTuk Driver`
    SET current_balance = current_balance + %s
    WHERE name = %s
""", (target_contribution, driver_name))
frappe.db.commit()
```

### 2. Atomic SQL Updates

Balance updates now use atomic SQL `UPDATE` statements instead of read-modify-save:

```python
# BEFORE (not atomic)
driver.current_balance += amount
driver.save()

# AFTER (atomic)
frappe.db.sql("""
    UPDATE `tabTukTuk Driver`
    SET current_balance = current_balance + %s
    WHERE name = %s
""", (amount, driver_name))
```

### 3. Explicit Commits

All balance updates are now followed by explicit commits to ensure they persist immediately:

```python
# Update balance atomically
frappe.db.sql("UPDATE ... SET current_balance = current_balance + %s ...", (amount, driver))
frappe.db.commit()  # Explicit commit
```

### 4. Transaction Processing Order

The transaction processing now follows this order:
1. Lock driver row
2. Create transaction record
3. Update balance atomically
4. Commit immediately
5. Process B2C payment (outside transaction)

## Reconciliation Functions

### Function 1: `reconcile_driver_balance`

Check if a driver's balance matches the sum of their transactions.

**Usage:**
```python
# From Python console
result = frappe.call('tuktuk_management.api.tuktuk.reconcile_driver_balance', 
                     driver_name='DRV-112001')
print(result)

# From desk (via custom button or console)
frappe.call({
    method: 'tuktuk_management.api.tuktuk.reconcile_driver_balance',
    args: {
        driver_name: 'DRV-112001',
        date: '2025-12-07'  // Optional: defaults to today
    },
    callback: function(r) {
        console.log(r.message);
    }
});
```

**Returns:**
```json
{
    "driver_name": "DRV-112001",
    "driver": "John Doe",
    "old_balance": 2500,
    "calculated_balance": 2350,
    "discrepancy": 150,
    "transactions_count": 8,
    "from_datetime": "2025-12-07 06:00:00",
    "message": "⚠️ DISCREPANCY DETECTED: 150 KSH extra"
}
```

### Function 2: `fix_driver_balance`

Automatically fix a driver's balance to match calculated value.

**Usage:**
```python
# Fix a specific driver's balance
result = frappe.call('tuktuk_management.api.tuktuk.fix_driver_balance',
                     driver_name='DRV-112001',
                     auto_fix=True)
print(result)
```

**Returns:**
```json
{
    "success": true,
    "message": "✅ Balance fixed: 2500 → 2350 (adjusted 150 KSH)",
    "driver_name": "DRV-112001",
    "driver": "John Doe",
    "old_balance": 2500,
    "new_balance": 2350,
    "adjustment": 150,
    "transactions_count": 8
}
```

### Function 3: `reconcile_all_drivers_balances`

Check and optionally fix balances for all active drivers.

**Usage:**
```python
# Check all drivers (no auto-fix)
result = frappe.call('tuktuk_management.api.tuktuk.reconcile_all_drivers_balances')
print(f"Found {result['drivers_with_discrepancies']} drivers with issues")

# Check and auto-fix all drivers
result = frappe.call('tuktuk_management.api.tuktuk.reconcile_all_drivers_balances',
                     auto_fix=True)
print(result)
```

**Returns:**
```json
{
    "success": true,
    "total_drivers": 25,
    "drivers_checked": 25,
    "drivers_with_discrepancies": 3,
    "total_discrepancy_amount": 450,
    "auto_fixed": true,
    "results": [
        {
            "driver_name": "DRV-112001",
            "discrepancy": 150,
            "fixed": true
        },
        // ... more drivers
    ]
}
```

## Daily Operations Workflow

### Morning Reconciliation (Recommended)

Run this every morning before the daily reset:

```python
# In Python console or scheduled task
import frappe

# Reconcile all drivers
result = frappe.call('tuktuk_management.api.tuktuk.reconcile_all_drivers_balances')

# If discrepancies found, review and fix
if result['drivers_with_discrepancies'] > 0:
    print(f"⚠️ Found {result['drivers_with_discrepancies']} drivers with discrepancies")
    print(f"Total discrepancy: {result['total_discrepancy_amount']} KSH")
    
    # Review the results
    for driver_result in result['results']:
        if driver_result['discrepancy'] != 0:
            print(f"  - {driver_result['driver']}: {driver_result['discrepancy']} KSH")
    
    # Auto-fix if needed
    fix_result = frappe.call('tuktuk_management.api.tuktuk.reconcile_all_drivers_balances',
                             auto_fix=True)
    print(f"✅ Fixed {fix_result['drivers_with_discrepancies']} drivers")
```

### When Driver Reports Discrepancy

1. **Check their balance:**
```python
result = frappe.call('tuktuk_management.api.tuktuk.reconcile_driver_balance',
                     driver_name='DRV-112001')
```

2. **If discrepancy exists, review transactions:**
```python
# Get driver statement
transactions = frappe.get_all("TukTuk Transaction",
    filters={
        "driver": "DRV-112001",
        "timestamp": [">=", "2025-12-07 06:00:00"],
        "payment_status": "Completed",
        "transaction_type": ["not in", ["Adjustment", "Driver Repayment"]]
    },
    fields=["transaction_id", "amount", "target_contribution", "timestamp"]
)

# Verify the discrepancy
total = sum([t.target_contribution for t in transactions])
print(f"Transaction total: {total}")
print(f"Current balance: {result['old_balance']}")
print(f"Discrepancy: {result['discrepancy']}")
```

3. **Fix the balance:**
```python
fix_result = frappe.call('tuktuk_management.api.tuktuk.fix_driver_balance',
                         driver_name='DRV-112001',
                         auto_fix=True)
print(fix_result['message'])
```

## Monitoring & Alerts

### Set Up Daily Reconciliation

Add this to your scheduled tasks or run manually:

```python
# In hooks.py or as custom script
def daily_balance_check():
    """Run daily balance reconciliation"""
    result = frappe.call('tuktuk_management.api.tuktuk.reconcile_all_drivers_balances')
    
    if result['drivers_with_discrepancies'] > 0:
        # Send alert email
        frappe.sendmail(
            recipients=['yuda@sunnytuktuk.com'],
            subject=f"⚠️ Balance Discrepancies Detected - {result['drivers_with_discrepancies']} Drivers",
            message=f"""
            Daily balance check found discrepancies:
            
            - Total drivers: {result['total_drivers']}
            - Drivers with issues: {result['drivers_with_discrepancies']}
            - Total discrepancy: {result['total_discrepancy_amount']} KSH
            
            Please review and fix using the reconciliation tools.
            """
        )
```

## Affected Functions

The following functions have been updated with atomic balance updates:

1. `mpesa_confirmation()` - Main payment webhook
2. `process_uncaptured_payment()` - Uncaptured payment processing
3. `add_missed_transaction_*()` - Manual transaction recovery functions

## Testing

To verify the fixes are working:

1. **Test concurrent transactions:**
   - Process multiple payments simultaneously for the same driver
   - Verify all target_contributions are added to current_balance
   - Run reconciliation to confirm no discrepancies

2. **Test reconciliation:**
   - Create intentional discrepancy (manual balance edit)
   - Run `reconcile_driver_balance()` to detect it
   - Run `fix_driver_balance()` to correct it
   - Verify balance matches transactions

3. **Monitor logs:**
   - Check Error Log for "Balance Discrepancy Detected"
   - Review "Balance Fixed" entries
   - Track reconciliation patterns

## Troubleshooting

### Issue: Balance still incorrect after fix

**Solution:**
```python
# Force recalculation with fresh data
driver = frappe.get_doc("TukTuk Driver", "DRV-112001")
driver.reload()

# Run reconciliation again
result = frappe.call('tuktuk_management.api.tuktuk.reconcile_driver_balance',
                     driver_name='DRV-112001')

# If still incorrect, check for:
# 1. Transactions created outside operating hours
# 2. Adjustment transactions not excluded
# 3. Incomplete transaction records
```

### Issue: High discrepancy amount

**Solution:**
```python
# Check for missing or duplicate transactions
transactions = frappe.db.sql("""
    SELECT transaction_id, COUNT(*) as count
    FROM `tabTukTuk Transaction`
    WHERE driver = 'DRV-112001'
    AND timestamp >= '2025-12-07 06:00:00'
    GROUP BY transaction_id
    HAVING count > 1
""", as_dict=True)

if transactions:
    print("⚠️ Duplicate transactions found:")
    for t in transactions:
        print(f"  - {t.transaction_id}: {t.count} occurrences")
```

## Best Practices

1. **Run reconciliation daily** before the midnight reset
2. **Monitor reconciliation logs** for patterns of discrepancies
3. **Always review** before auto-fixing large discrepancies
4. **Document fixes** in driver comments for audit trail
5. **Investigate root cause** if same driver has repeated discrepancies

## Support

For issues or questions:
- Check Error Log for detailed error messages
- Review transaction history in Driver Statement
- Contact system administrator with driver ID and date of discrepancy

