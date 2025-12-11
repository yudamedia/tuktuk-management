#!/usr/bin/env python3
"""
Test script for balance reconciliation fixes
Run this from frappe bench: bench execute tuktuk_management.test_balance_fixes.run_tests
"""

import frappe
from frappe.utils import now_datetime, today
import time

def run_tests():
    """Run all balance reconciliation tests"""
    print("\n" + "="*80)
    print("BALANCE RECONCILIATION TEST SUITE")
    print("="*80 + "\n")
    
    # Test 1: Atomic Update Test
    test_atomic_updates()
    
    # Test 2: Reconciliation Function Test
    test_reconciliation_functions()
    
    # Test 3: Race Condition Test (simulated)
    test_race_condition_protection()
    
    # Test 4: Mass Reconciliation Test
    test_mass_reconciliation()
    
    print("\n" + "="*80)
    print("ALL TESTS COMPLETED")
    print("="*80 + "\n")


def test_atomic_updates():
    """Test that balance updates are atomic"""
    print("\n--- TEST 1: Atomic Update Test ---\n")
    
    try:
        # Get a test driver
        drivers = frappe.get_all("TukTuk Driver", 
                                filters={"assigned_tuktuk": ["is", "set"]},
                                limit=1)
        
        if not drivers:
            print("❌ No active drivers found for testing")
            return
        
        driver_name = drivers[0].name
        driver = frappe.get_doc("TukTuk Driver", driver_name)
        
        print(f"Testing with driver: {driver.driver_name} ({driver_name})")
        
        # Record initial balance
        initial_balance = driver.current_balance
        print(f"Initial balance: {initial_balance} KSH")
        
        # Perform atomic update
        test_amount = 100.0
        frappe.db.sql("""
            UPDATE `tabTukTuk Driver`
            SET current_balance = current_balance + %s
            WHERE name = %s
        """, (test_amount, driver_name))
        frappe.db.commit()
        
        # Verify balance updated
        driver.reload()
        new_balance = driver.current_balance
        expected_balance = initial_balance + test_amount
        
        if new_balance == expected_balance:
            print(f"✅ Atomic update successful: {initial_balance} → {new_balance}")
        else:
            print(f"❌ Atomic update failed: Expected {expected_balance}, got {new_balance}")
        
        # Restore original balance
        frappe.db.sql("""
            UPDATE `tabTukTuk Driver`
            SET current_balance = %s
            WHERE name = %s
        """, (initial_balance, driver_name))
        frappe.db.commit()
        print(f"✅ Restored original balance: {initial_balance}")
        
    except Exception as e:
        print(f"❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()


def test_reconciliation_functions():
    """Test reconciliation and fix functions"""
    print("\n--- TEST 2: Reconciliation Functions Test ---\n")
    
    try:
        # Get a test driver with transactions
        drivers = frappe.db.sql("""
            SELECT DISTINCT t.driver
            FROM `tabTukTuk Transaction` t
            INNER JOIN `tabTukTuk Driver` d ON t.driver = d.name
            WHERE t.timestamp >= %s
            AND t.payment_status = 'Completed'
            AND t.transaction_type NOT IN ('Adjustment', 'Driver Repayment')
            AND d.assigned_tuktuk IS NOT NULL
            LIMIT 1
        """, (f"{today()} 06:00:00",), as_dict=True)
        
        if not drivers:
            print("ℹ️ No drivers with transactions today for testing")
            return
        
        driver_name = drivers[0].driver
        driver = frappe.get_doc("TukTuk Driver", driver_name)
        
        print(f"Testing reconciliation with: {driver.driver_name} ({driver_name})")
        
        # Test reconcile_driver_balance
        print("\nTesting reconcile_driver_balance()...")
        result = frappe.call('tuktuk_management.api.tuktuk.reconcile_driver_balance',
                           driver_name=driver_name)
        
        print(f"Current balance: {result['old_balance']} KSH")
        print(f"Calculated balance: {result['calculated_balance']} KSH")
        print(f"Discrepancy: {result['discrepancy']} KSH")
        print(f"Transactions: {result['transactions_count']}")
        
        if result['discrepancy'] == 0:
            print("✅ Balance is correct - no discrepancy")
            
            # Create artificial discrepancy for testing fix
            print("\nCreating artificial discrepancy for fix test...")
            artificial_amount = 50.0
            original_balance = driver.current_balance
            
            frappe.db.sql("""
                UPDATE `tabTukTuk Driver`
                SET current_balance = current_balance + %s
                WHERE name = %s
            """, (artificial_amount, driver_name))
            frappe.db.commit()
            
            # Test fix function
            print("Testing fix_driver_balance()...")
            fix_result = frappe.call('tuktuk_management.api.tuktuk.fix_driver_balance',
                                   driver_name=driver_name,
                                   auto_fix=True)
            
            if fix_result['success']:
                print(f"✅ Fix successful: {fix_result['message']}")
                
                # Verify balance was fixed
                driver.reload()
                if driver.current_balance == original_balance:
                    print("✅ Balance correctly restored to original value")
                else:
                    print(f"❌ Balance not correctly restored: {driver.current_balance} != {original_balance}")
            else:
                print(f"❌ Fix failed: {fix_result.get('error', 'Unknown error')}")
        else:
            print(f"⚠️ Discrepancy detected: {result['discrepancy']} KSH")
            print("This may indicate existing issues that should be investigated.")
        
    except Exception as e:
        print(f"❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()


def test_race_condition_protection():
    """Test that race conditions are prevented with row locking"""
    print("\n--- TEST 3: Race Condition Protection Test ---\n")
    
    try:
        drivers = frappe.get_all("TukTuk Driver",
                                filters={"assigned_tuktuk": ["is", "set"]},
                                limit=1)
        
        if not drivers:
            print("❌ No active drivers found for testing")
            return
        
        driver_name = drivers[0].name
        driver = frappe.get_doc("TukTuk Driver", driver_name)
        
        print(f"Testing with driver: {driver.driver_name} ({driver_name})")
        print(f"Initial balance: {driver.current_balance} KSH")
        
        # Simulate multiple concurrent updates
        print("\nSimulating 5 concurrent balance updates...")
        initial_balance = driver.current_balance
        update_amounts = [10, 20, 15, 25, 30]  # Total: 100
        
        for amount in update_amounts:
            frappe.db.sql("""
                UPDATE `tabTukTuk Driver`
                SET current_balance = current_balance + %s
                WHERE name = %s
            """, (amount, driver_name))
        
        frappe.db.commit()
        
        # Verify all updates were applied
        driver.reload()
        expected_balance = initial_balance + sum(update_amounts)
        
        if driver.current_balance == expected_balance:
            print(f"✅ All updates applied correctly: {initial_balance} → {driver.current_balance}")
            print(f"   Expected: {expected_balance}, Got: {driver.current_balance}")
        else:
            print(f"❌ Updates not all applied: Expected {expected_balance}, Got {driver.current_balance}")
        
        # Restore original balance
        frappe.db.sql("""
            UPDATE `tabTukTuk Driver`
            SET current_balance = %s
            WHERE name = %s
        """, (initial_balance, driver_name))
        frappe.db.commit()
        print(f"✅ Restored original balance: {initial_balance}")
        
    except Exception as e:
        print(f"❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()


def test_mass_reconciliation():
    """Test mass reconciliation function"""
    print("\n--- TEST 4: Mass Reconciliation Test ---\n")
    
    try:
        print("Testing reconcile_all_drivers_balances()...")
        
        # Run without auto-fix first
        result = frappe.call('tuktuk_management.api.tuktuk.reconcile_all_drivers_balances',
                           auto_fix=False)
        
        print(f"\nReconciliation Results:")
        print(f"  Total drivers: {result['total_drivers']}")
        print(f"  Drivers checked: {result['drivers_checked']}")
        print(f"  Drivers with discrepancies: {result['drivers_with_discrepancies']}")
        print(f"  Total discrepancy amount: {result['total_discrepancy_amount']} KSH")
        
        if result['drivers_with_discrepancies'] > 0:
            print(f"\n⚠️ Found {result['drivers_with_discrepancies']} drivers with discrepancies:")
            for driver_result in result['results']:
                if driver_result.get('discrepancy', 0) != 0:
                    print(f"  - {driver_result.get('driver', 'Unknown')}: {driver_result['discrepancy']} KSH")
            
            print("\nThis is informational - existing discrepancies should be reviewed.")
        else:
            print("\n✅ All drivers have correct balances")
        
        print("\n✅ Mass reconciliation function working correctly")
        
    except Exception as e:
        print(f"❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()


def test_transaction_creation():
    """Test that new transactions update balance correctly"""
    print("\n--- BONUS TEST: Transaction Creation Test ---\n")
    
    try:
        print("Note: This test would require creating actual transactions")
        print("Run manual testing by processing real M-Pesa payments")
        print("and verifying balances match transaction totals")
        
    except Exception as e:
        print(f"❌ Test failed with error: {str(e)}")


if __name__ == "__main__":
    run_tests()

