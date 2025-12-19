#!/usr/bin/env python3
"""
Script to fix total_days_worked for TukTuk Substitute Drivers
This recalculates the correct number of days worked based on actual transaction history

Run with: bench execute tuktuk_management.scripts.fix_substitute_driver_days_worked
"""

import frappe
from frappe.utils import today


def fix_substitute_driver_days_worked():
    """
    Recalculate and fix total_days_worked for all substitute drivers
    based on their actual transaction history
    """
    print("🔧 Starting total_days_worked reconciliation for substitute drivers...")

    # Get all substitute drivers
    substitute_drivers = frappe.get_all(
        "TukTuk Substitute Driver",
        fields=["name", "first_name", "last_name", "date_joined", "total_days_worked", "last_worked_date"]
    )

    print(f"📊 Found {len(substitute_drivers)} substitute drivers to check")

    fixed_count = 0
    error_count = 0

    for driver in substitute_drivers:
        try:
            # Calculate actual days worked from transaction history
            actual_days_worked = frappe.db.sql("""
                SELECT COUNT(DISTINCT DATE(timestamp)) as days_worked
                FROM `tabTukTuk Transaction`
                WHERE substitute_driver = %s
                AND payment_status = 'Completed'
                AND transaction_type = 'Payment'
            """, (driver.name,), as_dict=True)[0].days_worked or 0

            current_value = driver.total_days_worked or 0

            if actual_days_worked != current_value:
                print(f"🔄 Fixing {driver.name} ({driver.first_name} {driver.last_name}): "
                      f"{current_value} → {actual_days_worked}")

                # Update the driver record
                frappe.db.sql("""
                    UPDATE `tabTukTuk Substitute Driver`
                    SET total_days_worked = %s
                    WHERE name = %s
                """, (actual_days_worked, driver.name))

                fixed_count += 1

                # Log the correction
                frappe.log_error(
                    f"Fixed total_days_worked for substitute driver {driver.name}: "
                    f"{current_value} → {actual_days_worked}",
                    "Substitute Driver Days Worked Fix"
                )
            else:
                print(f"✅ {driver.name} is correct: {actual_days_worked} days")

        except Exception as e:
            print(f"❌ Error fixing {driver.name}: {str(e)}")
            frappe.log_error(f"Error fixing substitute driver {driver.name}: {str(e)}")
            error_count += 1

    frappe.db.commit()

    print("\n🎉 Reconciliation complete!")
    print(f"📈 Drivers fixed: {fixed_count}")
    print(f"❌ Errors: {error_count}")

    return {
        "total_drivers": len(substitute_drivers),
        "fixed_count": fixed_count,
        "error_count": error_count
    }


def check_specific_driver(driver_name):
    """
    Check and fix a specific substitute driver
    """
    try:
        driver = frappe.get_doc("TukTuk Substitute Driver", driver_name)

        # Get actual transaction days
        actual_days = frappe.db.sql("""
            SELECT COUNT(DISTINCT DATE(timestamp)) as days_worked
            FROM `tabTukTuk Transaction`
            WHERE substitute_driver = %s
            AND payment_status = 'Completed'
            AND transaction_type = 'Payment'
        """, (driver_name,), as_dict=True)[0].days_worked or 0

        # Get transaction details for verification
        transactions = frappe.db.sql("""
            SELECT DATE(timestamp) as work_date, COUNT(*) as transactions, SUM(amount) as daily_revenue
            FROM `tabTukTuk Transaction`
            WHERE substitute_driver = %s
            AND payment_status = 'Completed'
            AND transaction_type = 'Payment'
            GROUP BY DATE(timestamp)
            ORDER BY work_date
        """, (driver_name,), as_dict=True)

        result = {
            "driver_name": driver_name,
            "current_total_days_worked": driver.total_days_worked or 0,
            "calculated_days_worked": actual_days,
            "date_joined": driver.date_joined,
            "last_worked_date": driver.last_worked_date,
            "needs_fix": (driver.total_days_worked or 0) != actual_days,
            "transaction_summary": transactions
        }

        print(f"\n🔍 Analysis for {driver_name}:")
        print(f"   Current total_days_worked: {result['current_total_days_worked']}")
        print(f"   Calculated from transactions: {result['calculated_days_worked']}")
        print(f"   Date joined: {result['date_joined']}")
        print(f"   Last worked: {result['last_worked_date']}")
        print(f"   Needs fix: {'YES' if result['needs_fix'] else 'NO'}")

        if transactions:
            print(f"   Transaction history ({len(transactions)} days):")
            for tx in transactions:
                print(f"     {tx.work_date}: {tx.transactions} transactions, KSH {tx.daily_revenue}")

        return result

    except Exception as e:
        print(f"❌ Error analyzing driver {driver_name}: {str(e)}")
        return None


if __name__ == "__main__":
    # For testing specific drivers
    import sys
    if len(sys.argv) > 1:
        driver_name = sys.argv[1]
        check_specific_driver(driver_name)
    else:
        fix_substitute_driver_days_worked()