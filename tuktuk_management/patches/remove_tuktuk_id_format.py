# ~/frappe-bench/apps/tuktuk_management/tuktuk_management/patches/remove_tuktuk_id_format.py

import frappe

def execute():
    """Remove TukTuk ID format validation by updating the tuktuk.py file"""
    
    # Log the patch execution
    frappe.log_error("Executing patch to remove TukTuk ID format validation")
    
    # The actual update should be made to the file:
    # ~/frappe-bench/apps/tuktuk_management/tuktuk_management/api/tuktuk.py
    # by manually modifying the validate_vehicle function
    
    # This is just a placeholder to track that the change was manually applied
    frappe.db.commit()
    
    # Add a comment to existing vehicles that might have non-standard IDs
    vehicles = frappe.get_all("TukTuk Vehicle", fields=["name"])
    for vehicle in vehicles:
        frappe.get_doc({
            "doctype": "Comment",
            "comment_type": "Info",
            "reference_doctype": "TukTuk Vehicle", 
            "reference_name": vehicle.name,
            "content": "TukTuk ID format validation has been removed. IDs no longer need to follow the KAAxxxT pattern."
        }).insert(ignore_permissions=True)
    
    frappe.db.commit()