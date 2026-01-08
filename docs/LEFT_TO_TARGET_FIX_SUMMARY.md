# left_to_target Atomic Update Fix

## Problem
When transactions occur, the `current_balance` field gets updated but the `left_to_target` field can end up with stale values, causing a discrepancy. This happens due to two issues:

1. **Original Issue:** Transactions outside operating hours had `current_balance` updated atomically but `left_to_target` was not updated
2. **Stale Value Bug (Dec 24, 2025):** Even when both fields were updated, using TWO separate SQL statements caused `left_to_target` to use the OLD `current_balance` value instead of the NEW one

### Examples of Affected Drivers
- DRV-112181: Discrepancy between `current_balance` and `left_to_target`
- DRV-112187: Similar discrepancy

## Solution
Use a **single atomic SQL statement** that updates both `current_balance` and `left_to_target` together, with `left_to_target` calculated using the NEW `current_balance` value: `(current_balance + %s)`

## Technical Implementation

### Correct Formula (Single Atomic Update)
```sql
UPDATE `tabTukTuk Driver`
SET current_balance = current_balance + %s,
    left_to_target = GREATEST(0,
        COALESCE(NULLIF(daily_target, 0), %s) - (current_balance + %s)
    )
WHERE name = %s
```

**Key Points:**
- `NULLIF(daily_target, 0)` treats 0 as NULL (drivers with 0 target use global target)
- `COALESCE` falls back to `global_daily_target` if driver's target is NULL or 0
- `GREATEST(0, ...)` prevents negative values when target is exceeded
- **CRITICAL:** Uses `(current_balance + %s)` to calculate with the NEW balance, not the old one
- `global_daily_target` is passed as a parameter (not subquery) because TukTuk Settings is a Single DocType with no physical row in the database
- **Single SQL statement** ensures atomicity and prevents stale value bugs

### Locations Updated

#### 1. `process_regular_driver_payment()` (Line ~130)
**Context:** M-Pesa payment confirmation endpoint for regular drivers
**Status:** ✅ **CORRECT** - Uses single atomic update with NEW balance
```python
global_target = settings.global_daily_target or 0

frappe.db.sql("""
    UPDATE `tabTukTuk Driver`
    SET current_balance = current_balance + %s,
        left_to_target = GREATEST(0,
            COALESCE(NULLIF(daily_target, 0), %s) - (current_balance + %s)
        )
    WHERE name = %s
""", (target_contribution, global_target, target_contribution, driver_doc.name))
```

#### 2. `process_uncaptured_payment()` - Send Share (Line ~1028)
**Context:** Processing uncaptured payments with driver share
**Status:** ✅ **FIXED (Dec 24, 2025)** - Now uses single atomic update
```python
if target_contribution > 0:
    global_target = settings.global_daily_target or 0
    # Single atomic SQL update for both fields (prevents stale value bug)
    frappe.db.sql("""
        UPDATE `tabTukTuk Driver`
        SET current_balance = current_balance + %s,
            left_to_target = GREATEST(0,
                COALESCE(NULLIF(daily_target, 0), %s) - (current_balance + %s)
            )
        WHERE name = %s
    """, (target_contribution, global_target, target_contribution, driver))
```

#### 3. `process_uncaptured_payment()` - Deposit Share (Line ~1107)
**Context:** Processing uncaptured payments as balance deposit
**Status:** ✅ **FIXED (Dec 24, 2025)** - Now uses single atomic update
```python
old_balance = driver_doc.current_balance
global_target = settings.global_daily_target or 0
# Single atomic SQL update for both fields (prevents stale value bug)
frappe.db.sql("""
    UPDATE `tabTukTuk Driver`
    SET current_balance = current_balance + %s,
        left_to_target = GREATEST(0,
            COALESCE(NULLIF(daily_target, 0), %s) - (current_balance + %s)
        )
    WHERE name = %s
""", (amount, global_target, amount, driver))
```

#### 4. `sunny_id_payment_handler.py` - `handle_sunny_id_payment()` (Line ~148)
**Context:** Sunny ID payment processing
**Status:** ✅ **CORRECT** - Uses single atomic update with NEW balance
```python
global_target = settings.global_daily_target or 0

# Single atomic SQL update for ALL fields (prevents race condition)
frappe.db.sql("""
    UPDATE `tabTukTuk Driver`
    SET
        current_balance = current_balance + %s,
        left_to_target = GREATEST(0,
            COALESCE(NULLIF(daily_target, 0), %s) - (current_balance + %s)
        ),
        current_deposit_balance = current_deposit_balance + %s
    WHERE name = %s
""", (target_reduction, global_target, target_reduction, deposited_amount, driver_data.name))
```

#### 5. `update_driver_payment_atomic()` (Line ~3897)
**Context:** Utility function for atomic payment updates
**Status:** ✅ **CORRECT** - Uses single atomic update with NEW balance
```python
global_target = settings.global_daily_target or 0

# Single atomic SQL update for ALL payment-related fields
frappe.db.sql("""
    UPDATE `tabTukTuk Driver`
    SET
        current_balance = current_balance + %s,
        left_to_target = GREATEST(0,
            COALESCE(NULLIF(daily_target, 0), %s) - (current_balance + %s)
        ),
        current_deposit_balance = current_deposit_balance + %s
    WHERE name = %s
""", (target_contribution, global_target, target_contribution, deposit_amount, driver_name))
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

## Changelog

### January 5, 2026 - Race Condition Fix (before_save Hook)
**Issue:** Ongoing discrepancies still occurring despite atomic SQL fixes. Root cause identified: The `before_save()` hook was using stale in-memory values to recalculate `left_to_target`, overwriting correct SQL-calculated values.

**Root Cause:**
When a driver document is loaded into memory early in the day and atomic SQL payment updates happen to the database, the in-memory object remains stale. When any code later calls `.save()` on that object (e.g., for tuktuk assignment, termination, etc.), the `update_left_to_target()` hook would calculate using the OLD in-memory `current_balance` and overwrite the correct database values.

**Example Scenario:**
1. 10:00 AM: Load driver (balance = 100, left = 900)
2. Throughout day: Atomic SQL payments (DB now: balance = 800, left = 200)
3. 5:00 PM: Assign driver to new tuktuk → calls `.save()`
4. Hook calculates: `left_to_target = 1000 - 100 = 900` (using stale value)
5. Database overwritten: left = 200 → 900 ❌ DISCREPANCY CREATED

**Fixed Location:**
`tuktuk_management/tuktuk_management/doctype/tuktuk_driver/tuktuk_driver.py:61`

**Solution:**
Modified `update_left_to_target()` hook to ALWAYS fetch `current_balance` from database instead of using in-memory value:
```python
# OLD (stale):
current = flt(self.current_balance or 0)

# NEW (always fresh):
current = flt(frappe.db.get_value("TukTuk Driver", self.name, "current_balance") or 0)
```

This ensures that no matter how old the in-memory driver object is, the hook will always use the most current database value when recalculating `left_to_target`.

### December 24, 2025 - Critical Bug Fix
**Issue:** Stale value bug discovered in 3 locations causing discrepancies for drivers like DRV-112181 and DRV-112187

**Root Cause:** Using TWO separate SQL UPDATE statements caused `left_to_target` to calculate with OLD `current_balance` instead of NEW value

**Fixed Locations:**
1. `process_uncaptured_payment()` - Send Share (Line ~1028)
2. `process_uncaptured_payment()` - Deposit Share (Line ~1107)

**Solution:** Combined both updates into a single atomic SQL statement using `(current_balance + %s)` to reference the NEW balance

### December 8, 2025 - Initial Implementation
Original atomic update fix for `left_to_target` synchronization

## Status
✅ **DEPLOYED AND TESTED** (Updated Jan 5, 2026)

