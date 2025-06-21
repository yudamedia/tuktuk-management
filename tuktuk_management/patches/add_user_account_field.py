# Create: tuktuk_management/patches/add_user_account_field.py

import frappe

def execute():
    """Add user_account field to TukTuk Driver DocType"""
    try:
        # Check if field already exists
        if frappe.db.exists("DocField", {"parent": "TukTuk Driver", "fieldname": "user_account"}):
            print("✅ user_account field already exists")
            return
        
        # Get the TukTuk Driver DocType
        doc = frappe.get_doc("DocType", "TukTuk Driver")
        
        # Find a good position to insert the field (after driver_email)
        insert_index = 0
        for i, field in enumerate(doc.fields):
            if field.fieldname == "driver_email":
                insert_index = i + 1
                break
        
        # Create the new field
        new_field = frappe.get_doc({
            "doctype": "DocField",
            "parent": "TukTuk Driver",
            "parenttype": "DocType",
            "parentfield": "fields",
            "fieldname": "user_account",
            "fieldtype": "Link",
            "label": "User Account",
            "options": "User",
            "read_only": 1,
            "description": "ERPNext user account for driver login",
            "idx": insert_index + 1
        })
        
        # Insert the field
        doc.insert_field(insert_index, new_field)
        
        # Save the DocType
        doc.save()
        
        # Reload the DocType
        frappe.reload_doctype("TukTuk Driver")
        
        print("✅ Added user_account field to TukTuk Driver")
        
    except Exception as e:
        print(f"❌ Error adding user_account field: {str(e)}")
        frappe.log_error(f"Error adding user_account field: {str(e)}")

# Alternative method - Direct SQL approach
def execute_sql_method():
    """Add user_account field using direct SQL"""
    try:
        # Check if column exists
        columns = frappe.db.sql("""
            SELECT COLUMN_NAME 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_NAME = 'tabTukTuk Driver' 
            AND COLUMN_NAME = 'user_account'
        """)
        
        if columns:
            print("✅ user_account column already exists")
            return
        
        # Add the column
        frappe.db.sql("""
            ALTER TABLE `tabTukTuk Driver` 
            ADD COLUMN `user_account` VARCHAR(140) DEFAULT NULL
        """)
        
        # Add the DocField record
        frappe.db.sql("""
            INSERT INTO `tabDocField` 
            (name, creation, modified, modified_by, owner, docstatus, parent, parenttype, parentfield, 
             fieldname, fieldtype, label, options, read_only, description, idx)
            VALUES 
            (UUID(), NOW(), NOW(), 'Administrator', 'Administrator', 0, 'TukTuk Driver', 'DocType', 'fields',
             'user_account', 'Link', 'User Account', 'User', 1, 'ERPNext user account for driver login', 50)
        """)
        
        frappe.db.commit()
        print("✅ Added user_account field using SQL method")
        
    except Exception as e:
        print(f"❌ Error with SQL method: {str(e)}")

if __name__ == "__main__":
    execute()