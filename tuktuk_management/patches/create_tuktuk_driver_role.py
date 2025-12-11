# ~/frappe-bench/apps/tuktuk_management/tuktuk_management/patches/create_tuktuk_driver_role.py
import frappe

def execute():
    """
    Create the 'TukTuk Driver' role to fix role naming inconsistency.
    The codebase expects 'TukTuk Driver' but only 'Driver' was created.
    """
    
    print("🔧 Creating TukTuk Driver role...")
    
    # Create TukTuk Driver role
    create_tuktuk_driver_role()
    
    # Migrate existing Driver role users to TukTuk Driver
    migrate_driver_users()
    
    # Update permissions
    update_doctype_permissions()
    
    # Clear cache
    frappe.clear_cache()
    frappe.db.commit()
    
    print("✅ TukTuk Driver role created successfully!")

def create_tuktuk_driver_role():
    """Create the TukTuk Driver role if it doesn't exist"""
    
    role_name = 'TukTuk Driver'
    
    if not frappe.db.exists('Role', role_name):
        try:
            role = frappe.new_doc('Role')
            role.role_name = role_name
            role.desk_access = 1
            role.notifications = 1
            role.description = 'TukTuk driver role for accessing personal dashboard, transactions, and rentals'
            role.is_custom = 1
            role.save(ignore_permissions=True)
            print(f"✅ Created role: {role_name}")
        except Exception as e:
            print(f"❌ Error creating role {role_name}: {str(e)}")
            frappe.log_error(f"Role Creation Error: {str(e)}", f"Failed to create role: {role_name}")
    else:
        print(f"⚠️  Role already exists: {role_name}")

def migrate_driver_users():
    """
    Find all users with 'Driver' role and add 'TukTuk Driver' role to them.
    Keep the existing 'Driver' role for backwards compatibility.
    """
    
    try:
        # Find all users with 'Driver' role
        users_with_driver_role = frappe.db.sql("""
            SELECT DISTINCT parent as user
            FROM `tabHas Role`
            WHERE role = 'Driver'
            AND parenttype = 'User'
        """, as_dict=True)
        
        migrated_count = 0
        for user_data in users_with_driver_role:
            user_name = user_data.get('user')
            
            # Skip system users
            if user_name in ['Administrator', 'Guest']:
                continue
            
            try:
                # Check if user already has TukTuk Driver role
                has_tuktuk_driver_role = frappe.db.exists('Has Role', {
                    'parent': user_name,
                    'role': 'TukTuk Driver',
                    'parenttype': 'User'
                })
                
                if not has_tuktuk_driver_role:
                    user_doc = frappe.get_doc("User", user_name)
                    user_doc.append("roles", {"role": "TukTuk Driver"})
                    user_doc.save(ignore_permissions=True)
                    migrated_count += 1
                    print(f"   ✅ Added TukTuk Driver role to: {user_name}")
                    
            except Exception as e:
                print(f"   ⚠️  Could not migrate user {user_name}: {str(e)}")
        
        if migrated_count > 0:
            print(f"✅ Migrated {migrated_count} user(s) to TukTuk Driver role")
        else:
            print("ℹ️  No users needed migration")
            
    except Exception as e:
        print(f"❌ Error during user migration: {str(e)}")
        frappe.log_error(f"Driver User Migration Error: {str(e)}")

def update_doctype_permissions():
    """Add TukTuk Driver role permissions to relevant doctypes"""
    
    # Define permissions for TukTuk Driver role
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
                # Check if permission already exists
                existing_perm = frappe.db.exists('DocPerm', {
                    'parent': doctype,
                    'role': 'TukTuk Driver'
                })
                
                if not existing_perm:
                    perm = frappe.new_doc('DocPerm')
                    perm.parent = doctype
                    perm.parenttype = 'DocType'
                    perm.parentfield = 'permissions'
                    perm.role = 'TukTuk Driver'
                    
                    for perm_type, value in perms.items():
                        setattr(perm, perm_type, value)
                    
                    perm.insert(ignore_permissions=True)
                    print(f"   ✅ Added TukTuk Driver permissions to: {doctype}")
                else:
                    print(f"   ⚠️  Permissions already exist for: {doctype}")
                    
            except Exception as e:
                print(f"   ❌ Error adding permissions to {doctype}: {str(e)}")

