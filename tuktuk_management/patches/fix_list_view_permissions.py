import frappe

def execute():
    """Fix list view permissions for Tuktuk Manager role"""
    
    print("🔧 Fixing list view permissions for Tuktuk Manager...")
    
    try:
        # Ensure Tuktuk Manager can read all required fields
        doctype = "TukTuk Vehicle"
        role = "Tuktuk Manager"
        
        # Check if permission exists
        existing_perm = frappe.db.get_value("DocPerm", 
                                          {"parent": doctype, "role": role}, 
                                          ["name", "read", "if_owner"])
        
        if existing_perm:
            # Update existing permission to ensure full read access
            frappe.db.set_value("DocPerm", existing_perm[0], {
                "read": 1,
                "if_owner": 0,  # Remove if_owner restriction
                "report": 1,
                "export": 1
            })
            print(f"✅ Updated permissions for {role} on {doctype}")
        else:
            # Create new permission
            perm = frappe.new_doc("DocPerm")
            perm.parent = doctype
            perm.parenttype = "DocType"
            perm.parentfield = "permissions"
            perm.role = role
            perm.read = 1
            perm.write = 1
            perm.create = 1
            perm.delete = 1
            perm.if_owner = 0
            perm.report = 1
            perm.export = 1
            perm.print = 1
            perm.email = 1
            perm.insert(ignore_permissions=True)
            print(f"✅ Created new permissions for {role} on {doctype}")
        
        # Clear cache to apply changes
        frappe.clear_cache()
        frappe.db.commit()
        
        print("✅ List view permissions fixed successfully!")
        
    except Exception as e:
        print(f"❌ Error fixing permissions: {str(e)}")
        frappe.log_error(f"List view permission fix error: {str(e)}")
