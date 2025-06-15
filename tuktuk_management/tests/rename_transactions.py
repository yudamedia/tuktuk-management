# ~/frappe-bench/apps/tuktuk_management/tuktuk_management/tests/rename_transactions.py

import frappe
from frappe.utils import getdate

def rename_tuktuk_transactions():
    """Rename TukTuk Transaction documents to format TRANS-DDMMYY-#####"""
    try:
        transactions = frappe.get_all("TukTuk Transaction", 
                                    fields=["name", "timestamp"],
                                    order_by="timestamp")
        
        counters = {}  # Track counters per date
        
        for transaction in transactions:
            date = getdate(transaction.timestamp)
            date_str = date.strftime("%d%m%y")
            
            if date_str not in counters:
                counters[date_str] = 1
                
            new_name = f"TRANS-{date_str}-{counters[date_str]:05d}"
            print(f"Renaming {transaction.name} to {new_name}")
            
            try:
                frappe.rename_doc("TukTuk Transaction", transaction.name, new_name, force=True)
                counters[date_str] += 1
            except Exception as e:
                print(f"Error renaming {transaction.name}: {str(e)}")
                
        frappe.db.commit()
        print("Renaming completed successfully")
        
    except Exception as e:
        print(f"Error during renaming: {str(e)}")
        frappe.log_error(f"Transaction Renaming Error: {str(e)}")

if __name__ == "__main__":
    rename_tuktuk_transactions()