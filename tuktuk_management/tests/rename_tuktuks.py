# ~/frappe-bench/apps/tuktuk_management/tuktuk_management/tests/rename_tuktuks.py

import frappe

def rename_tuktuk_vehicles():
    """Rename existing TukTuk Vehicle documents to follow new naming pattern"""
    try:
        # Get all TukTuk Vehicles
        vehicles = frappe.get_all("TukTuk Vehicle", 
                                fields=["name", "tuktuk_id"],
                                order_by="creation")
        
        # Start counter from 1
        counter = 1
        
        for vehicle in vehicles:
            new_name = f"TUK-002{counter:03d}"  # This will create TUK-002001, TUK-002002, etc.
            print(f"Renaming {vehicle.name} to {new_name}")
            
            try:
                frappe.rename_doc("TukTuk Vehicle", vehicle.name, new_name, force=True)
                counter += 1
            except Exception as e:
                print(f"Error renaming {vehicle.name}: {str(e)}")
                
        frappe.db.commit()
        print("Renaming completed successfully")
        
    except Exception as e:
        print(f"Error during renaming: {str(e)}")
        frappe.log_error(f"TukTuk Renaming Error: {str(e)}")

if __name__ == "__main__":
    rename_tuktuk_vehicles()