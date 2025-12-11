# ~/frappe-bench/apps/tuktuk_management/tuktuk_management/patches/fix_tuktuk_driver_permissions.py
import frappe

def execute():
    """
    Fix TukTuk Driver role permissions to be read-only (except for TukTuk Rental where create is allowed).
    """
    
    print("🔧 Fixing TukTuk Driver role permissions...")
    
    # Define correct permissions for TukTuk Driver role
    doctype_permissions = {
        'TukTuk Vehicle': {'read': 1, 'write': 0, 'create': 0, 'delete': 0},
        'TukTuk Driver': {'read': 1, 'write': 0, 'create': 0, 'delete': 0},
        'TukTuk Transaction': {'read': 1, 'write': 0, 'create': 0, 'delete': 0},
        'TukTuk Rental': {'read': 1, 'write': 0, 'create': 1, 'delete': 0},
        'TukTuk Settings': {'read': 1, 'write': 0, 'create': 0, 'delete': 0},
    }
    
    for doctype, perms in doctype_permissions.items():
        if frappe.db.exists('DocType', doctype):
            try:
                # Delete existing TukTuk Driver permissions for this doctype
                frappe.db.sql("""
                    DELETE FROM `tabDocPerm` 
                    WHERE parent = %s AND role = 'TukTuk Driver'
                """, (doctype,))
                
                # Create new permission with correct settings
                perm = frappe.new_doc('DocPerm')
                perm.parent = doctype
                perm.parenttype = 'DocType'
                perm.parentfield = 'permissions'
                perm.role = 'TukTuk Driver'
                
                for perm_type, value in perms.items():
                    setattr(perm, perm_type, value)
                
                perm.insert(ignore_permissions=True)
                print(f"   ✅ Fixed permissions for: {doctype} (read={perms['read']}, create={perms.get('create', 0)})")
                
            except Exception as e:
                print(f"   ❌ Error fixing permissions for {doctype}: {str(e)}")
    
    # Clear cache
    frappe.clear_cache()
    frappe.db.commit()
    
    print("✅ TukTuk Driver permissions fixed successfully!")

