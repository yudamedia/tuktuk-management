# ~/frappe-bench/apps/tuktuk_management/tuktuk_management/patches/add_sunny_id_field.py

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def execute():
    """Add Sunny ID field to TukTuk Driver doctype"""
    
    # Check if field already exists
    if frappe.db.exists("Custom Field", {"dt": "TukTuk Driver", "fieldname": "sunny_id"}):
        print("Sunny ID field already exists, skipping...")
        return
    
    custom_fields = {
        "TukTuk Driver": [
            {
                "fieldname": "sunny_id",
                "label": "Sunny ID",
                "fieldtype": "Data",
                "insert_after": "driver_address",
                "read_only": 1,
                "in_list_view": 1,
                "in_standard_filter": 1,
                "description": "Unique Sunny TukTuk identifier (auto-generated from driver code)",
                "bold": 1
            }
        ]
    }
    
    create_custom_fields(custom_fields, update=True)
    
    # Update existing drivers with Sunny ID
    drivers = frappe.get_all("TukTuk Driver", fields=["name"])
    
    for driver in drivers:
        if driver.name.startswith("DRV-"):
            sunny_id = "D" + driver.name.replace("DRV-", "")
            frappe.db.set_value("TukTuk Driver", driver.name, "sunny_id", sunny_id, update_modified=False)
    
    frappe.db.commit()
    
    print(f"✅ Sunny ID field added successfully and populated for {len(drivers)} drivers")