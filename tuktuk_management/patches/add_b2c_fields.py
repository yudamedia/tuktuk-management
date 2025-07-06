# ~/frappe-bench/apps/tuktuk_management/tuktuk_management/patches/add_b2c_fields.py

import frappe

def execute():
    """Add B2C payment fields to TukTuk Settings DocType"""
    try:
        doctype_name = "TukTuk Settings"
        
        if not frappe.db.exists("DocType", doctype_name):
            print(f"❌ DocType {doctype_name} does not exist")
            return
        
        # Check if B2C fields already exist
        existing_fields = frappe.get_all("DocField", 
                                       filters={"parent": doctype_name},
                                       fields=["fieldname"])
        existing_fieldnames = [f.fieldname for f in existing_fields]
        
        # B2C fields to add
        b2c_fields = [
            {
                "fieldname": "b2c_section",
                "fieldtype": "Section Break",
                "label": "MPesa B2C (Business to Customer) Settings",
                "description": "Settings for automatic payments to drivers",
                "insert_after": "mpesa_api_secret"
            },
            {
                "fieldname": "mpesa_initiator_name",
                "fieldtype": "Password",
                "label": "MPesa Initiator Name",
                "description": "Your Initiator Name from Safaricom for B2C transactions"
            },
            {
                "fieldname": "mpesa_security_credential",
                "fieldtype": "Password", 
                "label": "MPesa Security Credential",
                "description": "Your Security Credential from Safaricom for B2C transactions"
            },
            {
                "fieldname": "column_break_b2c",
                "fieldtype": "Column Break"
            },
            {
                "fieldname": "mpesa_initiator_password",
                "fieldtype": "Password",
                "label": "MPesa Initiator Password",
                "description": "Your Initiator Password (used to generate Security Credential)"
            },
            {
                "fieldname": "b2c_enabled",
                "fieldtype": "Check",
                "label": "Enable B2C Payments",
                "description": "Enable automatic payments to drivers via B2C",
                "default": "0"
            }
        ]
        
        # Add fields that don't exist
        fields_added = 0
        for field_config in b2c_fields:
            if field_config["fieldname"] not in existing_fieldnames:
                add_field_to_doctype(doctype_name, field_config)
                fields_added += 1
                print(f"✅ Added B2C field: {field_config['fieldname']}")
            else:
                print(f"⚠️  B2C field already exists: {field_config['fieldname']}")
        
        if fields_added > 0:
            # Reload the DocType
            frappe.reload_doctype(doctype_name)
            print(f"✅ Added {fields_added} B2C fields to {doctype_name}")
            print("✅ DocType reloaded successfully")
            
            # Update field order to ensure proper positioning
            update_field_order(doctype_name)
            
        else:
            print(f"ℹ️  All B2C fields already exist in {doctype_name}")
        
        frappe.db.commit()
        print("✅ B2C fields patch completed successfully")
        
    except Exception as e:
        print(f"❌ Error adding B2C fields: {str(e)}")
        frappe.log_error(f"B2C fields patch error: {str(e)}")

def add_field_to_doctype(doctype_name, field_config):
    """Add a field to a doctype"""
    try:
        # Get the doctype document
        doc = frappe.get_doc("DocType", doctype_name)
        
        # Find insertion point
        insert_after = field_config.pop("insert_after", None)
        insert_idx = len(doc.fields)
        
        if insert_after:
            for idx, field in enumerate(doc.fields):
                if field.fieldname == insert_after:
                    insert_idx = idx + 1
                    break
        
        # Create new field
        new_field = frappe.new_doc("DocField")
        new_field.update(field_config)
        new_field.parent = doctype_name
        new_field.parenttype = "DocType"
        new_field.parentfield = "fields"
        new_field.idx = insert_idx + 1
        
        # Insert the field
        doc.fields.insert(insert_idx, new_field)
        
        # Update idx for all fields after insertion point
        for i in range(insert_idx + 1, len(doc.fields)):
            doc.fields[i].idx = i + 1
        
        # Save the doctype
        doc.save(ignore_permissions=True)
        
    except Exception as e:
        print(f"❌ Error adding B2C field {field_config.get('fieldname')}: {str(e)}")
        raise

def update_field_order(doctype_name):
    """Update field order to include B2C fields in the proper sequence"""
    try:
        doc = frappe.get_doc("DocType", doctype_name)
        
        # Get current field order
        current_order = [field.fieldname for field in doc.fields]
        
        # Define the desired order for B2C fields after mpesa section
        b2c_field_order = [
            "b2c_section",
            "mpesa_initiator_name", 
            "mpesa_security_credential",
            "column_break_b2c",
            "mpesa_initiator_password",
            "b2c_enabled"
        ]
        
        # Find where to insert B2C fields (after mpesa_api_secret)
        insert_point = None
        for idx, fieldname in enumerate(current_order):
            if fieldname == "mpesa_api_secret":
                insert_point = idx + 1
                break
        
        if insert_point is not None:
            # Remove B2C fields from current positions
            remaining_fields = [f for f in current_order if f not in b2c_field_order]
            
            # Insert B2C fields at the correct position
            new_order = remaining_fields[:insert_point] + b2c_field_order + remaining_fields[insert_point:]
            
            # Update the field_order property
            doc.field_order = new_order
            doc.save(ignore_permissions=True)
            
            print("✅ Updated field order for B2C fields")
        
    except Exception as e:
        print(f"⚠️  Could not update field order: {str(e)}")
        # This is not critical, fields will still work