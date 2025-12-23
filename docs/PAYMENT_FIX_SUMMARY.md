# Sunny ID Payment Fix Summary

**Date:** 2025-12-22
**Issue:** DRV-112006 payment of 305 KSH went entirely to deposit instead of applying to target

## Root Cause

The payment handler was using a **stale `left_to_target` value** from the database instead of calculating it fresh.

### What Happened:

1. **22:00:35** - Payment of 600 KSH processed successfully
   - Before: left_to_target = 825 KSH, current_balance = 95 KSH
   - After: left_to_target = 225 KSH, current_balance = 695 KSH ✓

2. **22:43:52** - Payment of 305 KSH **FAILED**
   - Before: left_to_target = **0 KSH** (incorrect DB value), current_balance = 695 KSH
   - After: Entire 305 KSH went to deposit ✗

### Why It Happened:

The payment handler (`sunny_id_payment_handler.py`) was:
1. Fetching `left_to_target` from the database (line 44)
2. Using that potentially stale value to determine payment allocation (line 77)

If the database value was incorrect (set to 0 due to a previous error or race condition), the payment would go entirely to deposit.

## The Fix

**File:** `apps/tuktuk_management/tuktuk_management/api/sunny_id_payment_handler.py`

### Changes Made:

1. **Removed `left_to_target` from database fetch** (line 44)
   - Now fetches `daily_target` instead

2. **Calculate `left_to_target` fresh** (lines 82-87)
   ```python
   # CRITICAL FIX: Calculate left_to_target FRESH instead of using stale DB value
   settings = frappe.get_single("TukTuk Settings")
   driver_target = flt(driver_data.daily_target or settings.global_daily_target or 0)
   current_balance = flt(driver_data.current_balance or 0)
   left_to_target = max(0, driver_target - current_balance)
   ```

3. **Updated logging** to show the calculated value

### Benefits:

- **Eliminates race conditions**: No longer depends on potentially stale DB values
- **Always accurate**: Calculates from current balance and target each time
- **Self-healing**: Even if DB `left_to_target` is wrong, payments still work correctly
- **Better logging**: Shows the target and calculated left_to_target for debugging

## Verification

To verify the fix is working, check future payment logs for:
- "left_to_target (calculated fresh): X KSH" in the success log
- Payments should now correctly apply to target when left_to_target > 0

## Testing Recommendation

Test with DRV-112006 (D112006):
- Current state: current_balance = 695, target = 1000, left_to_target should be 305
- Make a test payment of 100 KSH using sunny_id D112006
- Expected: 100 KSH to target, 0 KSH to deposit
- After: current_balance = 795, left_to_target = 205

## Prevention

This fix prevents the issue from occurring again by:
1. Not trusting the `left_to_target` field in the database
2. Always calculating it fresh from source data
3. Using the same calculation logic as the daily reset function

## Related Files

- `apps/tuktuk_management/tuktuk_management/api/sunny_id_payment_handler.py` (FIXED)
- `apps/tuktuk_management/tuktuk_management/tuktuk_management/doctype/tuktuk_driver/tuktuk_driver.py` (update_left_to_target hook - no changes needed)

## Impact

- **All future sunny_id payments** will now calculate correctly
- **No database migration needed** - fix is in application logic only
- **No risk to existing data** - only changes payment processing logic
