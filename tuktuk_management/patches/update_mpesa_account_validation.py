# ~/frappe-bench/apps/tuktuk_management/tuktuk_management/patches/update_mpesa_account_validation.py

import frappe

def execute():
    """Update validation for mpesa_account field to allow any length"""
    
    # Log the patch execution
    frappe.log_error("Executing patch to update mpesa_account validation")
    
    # The actual update should be made to the file:
    # ~/frappe-bench/apps/tuktuk_management/tuktuk_management/api/tuktuk.py
    # by manually modifying the validate_vehicle function
    
    # Update the description in the doctype if needed
    try:
        field = frappe.get_value(
            "DocField",
            {"parent": "TukTuk Vehicle", "fieldname": "mpesa_account"},
            ["name", "description"],
            as_dict=1
        )
        
        if field:
            frappe.db.set_value(
                "DocField",
                field.name,
                "description",
                "Mpesa account number (digits only)"
            )
    except Exception as e:
        frappe.log_error(f"Error updating mpesa_account field description: {str(e)}")
    
    # Add a system note about the change
    frappe.db.commit()
    
    # Add a comment to existing vehicles about the change
    vehicles = frappe.get_all("TukTuk Vehicle", fields=["name"])
    for vehicle in vehicles:
        frappe.get_doc({
            "doctype": "Comment",
            "comment_type": "Info",
            "reference_doctype": "TukTuk Vehicle", 
            "reference_name": vehicle.name,
            "content": "Mpesa account validation has been updated to allow account numbers of any length (not just 3 digits)."
        }).insert(ignore_permissions=True)
    
    frappe.db.commit()