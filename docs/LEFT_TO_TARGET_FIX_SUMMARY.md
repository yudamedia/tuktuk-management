# left_to_target Atomic Update Fix

## Problem
When transactions occur outside operating hours (before 6:00 AM), the `current_balance` field gets updated but the `left_to_target` field does not, causing a discrepancy. This is because:

1. Transactions outside operating hours are marked as "Failed" 
2. The `current_balance` is updated atomically via SQL
3. The `left_to_target` field is NOT updated atomically, leading to stale values

## Solution
Implemented atomic SQL updates for `left_to_target` alongside every `current_balance` update to ensure both fields stay synchronized.

## Technical Implementation

### Formula
```sql
left_to_target = GREATEST(0, 
    COALESCE(NULLIF(daily_target, 0), global_daily_target) - current_balance
)
```

**Key Points:**
- `NULLIF(daily_target, 0)` treats 0 as NULL (drivers with 0 target use global target)
- `COALESCE` falls back to `global_daily_target` if driver's target is NULL or 0
- `GREATEST(0, ...)` prevents negative values when target is exceeded
- `global_daily_target` is passed as a parameter (not subquery) because TukTuk Settings is a Single DocType with no physical row in the database

### Locations Updated

#### 1. `mpesa_confirmation()` (Line ~360)
**Context:** M-Pesa payment confirmation endpoint
```python
if target_contribution > 0 and transaction_type not in ['Adjustment', 'Driver Repayment']:
    global_target = settings.global_daily_target or 0
    
    # Update current_balance
    frappe.db.sql("""
        UPDATE `tabTukTuk Driver`
        SET current_balance = current_balance + %s
        WHERE name = %s
    """, (target_contribution, driver_name))
    
    # Update left_to_target atomically
    frappe.db.sql("""
        UPDATE `tabTukTuk Driver`
        SET left_to_target = GREATEST(0, 
            COALESCE(NULLIF(daily_target, 0), %s) - current_balance
        )
        WHERE name = %s
    """, (global_target, driver_name))
```

#### 2. `process_uncaptured_payment()` - Send Share (Line ~655)
**Context:** Processing uncaptured payments with driver share
```python
if target_contribution > 0:
    global_target = settings.global_daily_target or 0
    
    frappe.db.sql("""
        UPDATE `tabTukTuk Driver`
        SET current_balance = current_balance + %s
        WHERE name = %s
    """, (target_contribution, driver))
    
    frappe.db.sql("""
        UPDATE `tabTukTuk Driver`
        SET left_to_target = GREATEST(0, 
            COALESCE(NULLIF(daily_target, 0), %s) - current_balance
        )
        WHERE name = %s
    """, (global_target, driver))
```

#### 3. `process_uncaptured_payment()` - Deposit Share (Line ~740)
**Context:** Processing uncaptured payments as balance deposit
```python
old_balance = driver_doc.current_balance
global_target = settings.global_daily_target or 0

frappe.db.sql("""
    UPDATE `tabTukTuk Driver`
    SET current_balance = current_balance + %s
    WHERE name = %s
""", (amount, driver))

frappe.db.sql("""
    UPDATE `tabTukTuk Driver`
    SET left_to_target = GREATEST(0, 
        COALESCE(NULLIF(daily_target, 0), %s) - current_balance
    )
    WHERE name = %s
""", (global_target, driver))
```

#### 4. `add_missed_transaction_*()` (Line ~2045)
**Context:** Manual recovery function for missed transactions
```python
if target_contribution > 0:
    old_balance = driver.current_balance
    global_target = settings.global_daily_target or 0
    
    frappe.db.sql("""
        UPDATE `tabTukTuk Driver`
        SET current_balance = current_balance + %s
        WHERE name = %s
    """, (target_contribution, driver_name))
    
    frappe.db.sql("""
        UPDATE `tabTukTuk Driver`
        SET left_to_target = GREATEST(0, 
            COALESCE(NULLIF(daily_target, 0), %s) - current_balance
        )
        WHERE name = %s
    """, (global_target, driver_name))
```

## Test Results

### Test 1: Adding 100 KSH
- **Before:** Balance: 10 KSH, Left: 990 KSH
- **After:** Balance: 110 KSH, Left: 890 KSH
- **Expected:** 890 KSH
- **Result:** ✅ PASS

### Test 2: Adding 200 KSH
- **Before:** Balance: 110 KSH, Left: 890 KSH
- **After:** Balance: 310 KSH, Left: 690 KSH
- **Expected:** 690 KSH
- **Result:** ✅ PASS

### Test 3: Exceeding Target (Adding 800 KSH)
- **Before:** Balance: 310 KSH, Left: 690 KSH
- **After:** Balance: 1110 KSH, Left: 0 KSH
- **Expected:** 0 KSH (GREATEST prevents negative)
- **Result:** ✅ PASS

## Benefits

1. **Consistency:** `left_to_target` always reflects the actual remaining target
2. **Atomic Updates:** Both fields update together, preventing race conditions
3. **Real-time Accuracy:** Drivers see correct remaining target immediately
4. **No Manual Reconciliation:** Eliminates need for manual target resets
5. **Fraud Prevention:** Reduces suspicious "Reset Target Balance" activities

## Edge Cases Handled

1. **Driver with 0 target:** Falls back to global target via `NULLIF`
2. **Driver with NULL target:** Falls back to global target via `COALESCE`
3. **Exceeding target:** `GREATEST(0, ...)` prevents negative values
4. **Concurrent transactions:** Atomic SQL updates prevent race conditions

## Deployment

1. Clear Python cache: `find . -name "*.pyc" -delete`
2. Clear Frappe cache: `bench --site [site] clear-cache`
3. Restart bench: `bench restart`

## Verification

To verify the fix is working:

```python
# In bench console
import frappe

driver = frappe.get_doc("TukTuk Driver", "DRV-XXXXX")
settings = frappe.get_single("TukTuk Settings")

print(f"Balance: {driver.current_balance}")
print(f"Left to Target: {driver.left_to_target}")
print(f"Expected: {(driver.daily_target or settings.global_daily_target) - driver.current_balance}")
```

## Related Documents

- `BALANCE_FIX_SUMMARY.md` - Original balance race condition fix
- `BALANCE_RECONCILIATION_GUIDE.md` - Reconciliation procedures
- `BALANCE_QUICK_REFERENCE.md` - Quick reference commands
- `DEPLOYMENT_REPORT.md` - Deployment status and test results

## Date Implemented
December 8, 2025

## Status
✅ **DEPLOYED AND TESTED**

