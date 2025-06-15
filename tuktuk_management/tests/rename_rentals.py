# ~/frappe-bench/apps/tuktuk_management/tuktuk_management/tests/rename_rentals.py

import frappe
from frappe.utils import getdate

def rename_tuktuk_rentals():
    """Rename TukTuk Rental documents to format RENT-DDMMYY-#####"""
    try:
        rentals = frappe.get_all("TukTuk Rental", 
                                fields=["name", "start_time"],
                                order_by="start_time")
        
        counters = {}  # Track counters per date
        
        for rental in rentals:
            date = getdate(rental.start_time)
            date_str = date.strftime("%d%m%y")
            
            # Initialize counter for new date
            if date_str not in counters:
                counters[date_str] = 1
                
            new_name = f"RENT-{date_str}-{counters[date_str]:05d}"
            print(f"Renaming {rental.name} to {new_name}")
            
            try:
                frappe.rename_doc("TukTuk Rental", rental.name, new_name, force=True)
                counters[date_str] += 1
            except Exception as e:
                print(f"Error renaming {rental.name}: {str(e)}")
                
        frappe.db.commit()
        print("Renaming completed successfully")
        
    except Exception as e:
        print(f"Error during renaming: {str(e)}")
        frappe.log_error(f"Rental Renaming Error: {str(e)}")

if __name__ == "__main__":
    rename_tuktuk_rentals()