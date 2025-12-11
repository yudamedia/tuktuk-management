#!/usr/bin/env python3

import frappe
from frappe.utils import now_datetime

def find_and_remove_pending_adjustments():
    """
    Find and remove pending adjustment transactions for DRV-112017 with amount 50
    """
    try:
        # Find pending adjustment transactions for DRV-112017 with amount 50
        pending_adjustments = frappe.get_all("TukTuk Transaction",
                                            filters={
                                                "driver": "DRV-112017",
                                                "transaction_type": "Adjustment",
                                                "amount": 50,
                                                "payment_status": "Completed"
                                            },
                                            fields=["name", "transaction_id", "amount", "timestamp"])

        if not pending_adjustments:
            print("No pending adjustment transactions found for DRV-112017 with amount 50")
            return False

        print(f"Found {len(pending_adjustments)} pending adjustment transactions:")
        for adjustment in pending_adjustments:
            print(f"  - Transaction: {adjustment.name}")
            print(f"    ID: {adjustment.transaction_id}")
            print(f"    Amount: {adjustment.amount}")
            print(f"    Timestamp: {adjustment.timestamp}")

        # Delete each pending adjustment transaction
        for adjustment in pending_adjustments:
            try:
                frappe.delete_doc("TukTuk Transaction", adjustment.name)
                frappe.db.commit()
                print(f"✅ Successfully deleted adjustment transaction: {adjustment.name}")
            except Exception as e:
                frappe.db.rollback()
                print(f"❌ Failed to delete transaction {adjustment.name}: {str(e)}")
                return False

        print(f"✅ Successfully removed {len(pending_adjustments)} pending adjustment transactions for DRV-112017")
        return True

    except Exception as e:
        print(f"❌ Error finding or removing pending adjustments: {str(e)}")
        return False

if __name__ == "__main__":
    # Initialize Frappe environment
    frappe.init(site='frappe-bench')
    frappe.connect()

    print("🔍 Searching for pending adjustment transactions for DRV-112017...")
    success = find_and_remove_pending_adjustments()

    if success:
        print("🎉 Operation completed successfully!")
        print("💡 Sh. 50 transactions for DRV-112017 should now be processed normally.")
    else:
        print("❌ Operation failed or no adjustments found.")