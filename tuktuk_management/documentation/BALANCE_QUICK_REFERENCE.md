# Balance Reconciliation - Quick Reference Card

## 🚨 When Driver Reports Balance Discrepancy

### Step 1: Check Their Balance
```bash
bench --site console.sunnytuktuk.com console
```

```python
import frappe

# Replace with actual driver ID
driver_id = 'DRV-112001'

result = frappe.call('tuktuk_management.api.tuktuk.reconcile_driver_balance',
                     driver_name=driver_id)

print(f"Current Balance: {result['old_balance']} KSH")
print(f"Should Be: {result['calculated_balance']} KSH")
print(f"Discrepancy: {result['discrepancy']} KSH")
print(f"Transactions Today: {result['transactions_count']}")
```

### Step 2: If Discrepancy Found, Fix It
```python
fix_result = frappe.call('tuktuk_management.api.tuktuk.fix_driver_balance',
                         driver_name=driver_id,
                         auto_fix=True)

print(fix_result['message'])
```

### Step 3: Verify Fix
```python
# Check again to confirm
verify = frappe.call('tuktuk_management.api.tuktuk.reconcile_driver_balance',
                     driver_name=driver_id)
                     
print(f"✅ New balance: {verify['old_balance']} KSH")
print(f"Discrepancy: {verify['discrepancy']} KSH")
```

---

## 📊 Daily Reconciliation Check

Run this every morning:

```python
import frappe

result = frappe.call('tuktuk_management.api.tuktuk.reconcile_all_drivers_balances')

print(f"Total Drivers: {result['total_drivers']}")
print(f"With Issues: {result['drivers_with_discrepancies']}")
print(f"Total Discrepancy: {result['total_discrepancy_amount']} KSH")

# Auto-fix all if needed
if result['drivers_with_discrepancies'] > 0:
    fix_all = frappe.call('tuktuk_management.api.tuktuk.reconcile_all_drivers_balances',
                          auto_fix=True)
    print(f"✅ Fixed {fix_all['drivers_with_discrepancies']} drivers")
```

---

## 🔍 Manual Verification

### Check Driver's Transactions
```python
from frappe.utils import today

driver_id = 'DRV-112001'

# Get today's transactions
txns = frappe.get_all("TukTuk Transaction",
    filters={
        "driver": driver_id,
        "timestamp": [">=", f"{today()} 06:00:00"],
        "payment_status": "Completed",
        "transaction_type": ["not in", ["Adjustment", "Driver Repayment"]]
    },
    fields=["transaction_id", "amount", "target_contribution", "timestamp"],
    order_by="timestamp asc"
)

# Calculate total
total = sum([t.target_contribution for t in txns])

print(f"Transactions: {len(txns)}")
print(f"Total Contribution: {total} KSH")

# Show each transaction
for t in txns:
    print(f"  {t.timestamp}: {t.transaction_id} - {t.target_contribution} KSH")
```

### Compare with Current Balance
```python
driver = frappe.get_doc("TukTuk Driver", driver_id)
print(f"\nCurrent Balance: {driver.current_balance} KSH")
print(f"Calculated Total: {total} KSH")
print(f"Difference: {driver.current_balance - total} KSH")
```

---

## 📞 Common Issues & Solutions

### Issue: Driver says balance is wrong

**Solution:**
1. Run reconciliation check (Step 1 above)
2. If discrepancy found, run fix (Step 2)
3. Show driver the fixed balance
4. Explain: "System automatically recalculated from your transactions"

### Issue: Multiple drivers reporting issues

**Solution:**
```python
# Check all drivers at once
result = frappe.call('tuktuk_management.api.tuktuk.reconcile_all_drivers_balances',
                     auto_fix=True)

print(f"Fixed {result['drivers_with_discrepancies']} drivers")
```

### Issue: Balance negative but shouldn't be

**Solution:**
1. Check if target sharing is enabled
2. Check if driver missed target yesterday
3. Negative balance = debt from missed target
4. Run reconciliation to verify accuracy

---

## ⚙️ Command Cheat Sheet

### Quick Commands

```bash
# Access console
bench --site console.sunnytuktuk.com console

# Run tests
bench --site console.sunnytuktuk.com execute tuktuk_management.api.test_balance_fixes.run_tests

# Clear cache & restart
bench --site console.sunnytuktuk.com clear-cache && bench restart
```

### Python Quick Commands

```python
import frappe

# Check one driver
frappe.call('tuktuk_management.api.tuktuk.reconcile_driver_balance', 
            driver_name='DRV-112001')

# Fix one driver
frappe.call('tuktuk_management.api.tuktuk.fix_driver_balance',
            driver_name='DRV-112001', auto_fix=True)

# Check all drivers
frappe.call('tuktuk_management.api.tuktuk.reconcile_all_drivers_balances')

# Fix all drivers
frappe.call('tuktuk_management.api.tuktuk.reconcile_all_drivers_balances',
            auto_fix=True)
```

---

## 📝 What Changed (For Reference)

### Before the Fix
- Race conditions could lose transactions
- Manual balance resets required
- Multiple reset entries looked suspicious

### After the Fix
- Database row locking prevents race conditions
- Atomic SQL updates ensure accuracy
- Automatic reconciliation tools available
- Clear audit trail for all fixes

### What This Means
- ✅ Fewer balance complaints from drivers
- ✅ Less manual work for you
- ✅ Better trust and data integrity
- ✅ Automatic detection of any issues

---

## 🆘 When to Escalate

Contact system administrator if:
- Same driver has repeated discrepancies after fixes
- Large discrepancies (>1000 KSH)
- Many drivers affected simultaneously
- Reconciliation tool fails to fix
- Error logs show "Balance Discrepancy" warnings

---

## 💡 Pro Tips

1. **Run daily checks** - Catch issues early
2. **Fix immediately** - Don't let discrepancies accumulate
3. **Document patterns** - Note if same drivers have issues
4. **Verify with driver** - Show them the transaction list
5. **Check Error Log** - Review "Balance Discrepancy" entries

---

**Last Updated:** December 8, 2025  
**Version:** 1.0  
**Status:** Active

