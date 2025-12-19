#!/usr/bin/env python3
"""
Check a specific substitute driver
"""

import frappe

def check_driver(driver_name):
    """Check and analyze a specific substitute driver"""
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

        print(f"\n🔍 Analysis for {driver_name}:")
        print(f"   Name: {driver.first_name} {driver.last_name}")
        print(f"   Current total_days_worked: {driver.total_days_worked or 0}")
        print(f"   Calculated from transactions: {actual_days}")
        print(f"   Date joined: {driver.date_joined}")
        print(f"   Last worked: {driver.last_worked_date}")
        print(f"   Needs fix: {'YES' if (driver.total_days_worked or 0) != actual_days else 'NO'}")

        if transactions:
            print(f"   Transaction history ({len(transactions)} days):")
            for tx in transactions:
                print(f"     {tx.work_date}: {tx.transactions} transactions, KSH {tx.daily_revenue}")
        else:
            print("   No transactions found")

        # Ask if we should fix it
        if (driver.total_days_worked or 0) != actual_days:
            print(f"\n🔧 Should fix {driver_name} from {driver.total_days_worked or 0} to {actual_days}? (y/n)")
            response = input().lower().strip()
            if response == 'y':
                frappe.db.sql("""
                    UPDATE `tabTukTuk Substitute Driver`
                    SET total_days_worked = %s
                    WHERE name = %s
                """, (actual_days, driver_name))
                frappe.db.commit()
                print(f"✅ Fixed {driver_name}")
                frappe.log_error(
                    f"Fixed total_days_worked for substitute driver {driver_name}: "
                    f"{driver.total_days_worked or 0} → {actual_days}",
                    "Substitute Driver Days Worked Fix"
                )

        return True

    except Exception as e:
        print(f"❌ Error analyzing driver {driver_name}: {str(e)}")
        return False

if __name__ == "__main__":
    check_driver("SUB-212169")