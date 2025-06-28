#!/usr/bin/env python3
"""
Script to update the TukTuk Transaction doctype to show transaction_id and amount in list views
Run this from: bench execute tuktuk_management.update_transaction_listview.update_listview_fields
"""

import frappe

def update_listview_fields():
    """Update TukTuk Transaction doctype to show transaction_id and amount in list views"""
    try:
        # Get the doctype
        doctype = frappe.get_doc("DocType", "TukTuk Transaction")
        
        # Update field properties for better list view display
        field_updates = {
            "transaction_id": {
                "in_list_view": 1,
                "in_standard_filter": 1,
                "columns": 3
            },
            "amount": {
                "in_list_view": 1,
                "in_standard_filter": 1, 
                "columns": 2
            },
            "timestamp": {
                "in_list_view": 1,
                "columns": 2
            },
            "driver": {
                "in_list_view": 1,
                "columns": 2
            },
            "payment_status": {
                "in_list_view": 1,
                "columns": 1
            }
        }
        
        # Update existing fields
        for field in doctype.fields:
            if field.fieldname in field_updates:
                updates = field_updates[field.fieldname]
                for key, value in updates.items():
                    setattr(field, key, value)
                print(f"✅ Updated field: {field.fieldname}")
        
        # Set title field to transaction_id for better display
        if not doctype.title_field:
            doctype.title_field = "transaction_id"
            print("✅ Set title_field to transaction_id")
        
        # Save the doctype
        doctype.save()
        
        print("✅ Successfully updated TukTuk Transaction list view configuration")
        
        # Commit the changes
        frappe.db.commit()
        
        # Clear cache to ensure changes take effect
        frappe.clear_cache(doctype="TukTuk Transaction")
        
        print("✅ Cache cleared. Changes should be visible immediately.")
        
    except Exception as e:
        print(f"❌ Error updating list view: {str(e)}")
        frappe.log_error(f"List view update error: {str(e)}")

if __name__ == "__main__":
    update_listview_fields()
