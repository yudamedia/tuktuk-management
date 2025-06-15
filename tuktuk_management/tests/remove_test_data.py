# ~/frappe-bench/apps/tuktuk_management/tuktuk_management/tests/remove_test_data.py

import frappe

def remove_test_data():
    """Safely remove all test data from Sunny TukTuk system"""
    try:
        print("Removing test data...")
        
        # Clear cache
        frappe.clear_cache()
        
        # Remove from Singles table
        if frappe.db.exists("Singles", {"doctype": "TukTuk Settings"}):
            frappe.db.delete("Singles", {"doctype": "TukTuk Settings"})
            print("Cleaned TukTuk Settings")
        
        # Get list of our doctypes
        doctypes = [
            "TukTuk Rental",
            "TukTuk Transaction",
            "TukTuk Driver",
            "TukTuk Vehicle",
            "TukTuk Daily Report"
        ]
        
        # Safely delete from each doctype
        for doctype in doctypes:
            try:
                if frappe.db.exists("DocType", doctype):
                    docs = frappe.get_all(doctype)
                    for doc in docs:
                        frappe.delete_doc(doctype, doc.name, force=1)
                    print(f"Deleted {len(docs)} {doctype} records")
            except Exception as e:
                print(f"Skipping {doctype}: {str(e)}")
                
        # Commit changes
        frappe.db.commit()
        print("Test data removal completed")
        
    except Exception as e:
        print(f"Error removing test data: {str(e)}")
        frappe.log_error(f"Test Data Removal Error: {str(e)}")

if __name__ == "__main__":
    remove_test_data()