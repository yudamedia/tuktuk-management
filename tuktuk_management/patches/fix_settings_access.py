# ~/frappe-bench/apps/tuktuk_management/tuktuk_management/patches/fix_settings_access.py
import frappe

def execute():
    """
    Comprehensive fix for TukTuk Settings access issues
    """
    
    # Step 1: Create roles if missing
    create_required_roles()
    
    # Step 2: Fix doctype permissions
    fix_doctype_permissions()
    
    # Step 3: Create default settings record
    create_default_settings()
    
    # Step 4: Assign roles to current user
    assign_roles_to_current_user()
    
    # Step 5: Reload doctypes
    reload_all_doctypes()
    
    # Step 6: Clear cache
    frappe.clear_cache()
    
    frappe.db.commit()
    print("TukTuk Settings access has been fixed!")

def create_required_roles():
    """Create required roles"""
    roles = [
        {
            'role_name': 'Tuktuk Manager',
            'description': 'Manager role for TukTuk operations with full access'
        },
        {
            'role_name': 'Driver',
            'description': 'TukTuk driver role for accessing personal dashboard and transactions'
        }
    ]
    
    for role_data in roles:
        if not frappe.db.exists('Role', role_data['role_name']):
            role = frappe.new_doc('Role')
            role.role_name = role_data['role_name']
            role.desk_access = 1
            role.notifications = 1
            role.description = role_data['description']
            role.save(ignore_permissions=True)
            print(f"Created role: {role_data['role_name']}")

def fix_doctype_permissions():
    """Fix permissions for all TukTuk doctypes"""
    doctypes = [
        'TukTuk Vehicle', 'TukTuk Driver', 'TukTuk Transaction', 
        'TukTuk Rental', 'TukTuk Settings', 'TukTuk Daily Report'
    ]
    
    for doctype in doctypes:
        if frappe.db.exists('DocType', doctype):
            # Clear existing permissions
            frappe.db.delete('DocPerm', {'parent': doctype})
            
            # Add System Manager permissions (full access)
            add_permission(doctype, 'System Manager', {
                'read': 1, 'write': 1, 'create': 1, 'delete': 1,
                'submit': 0, 'cancel': 0, 'amend': 0,
                'report': 1, 'export': 1, 'import': 1, 'print': 1, 'email': 1, 'share': 1
            })
            
            # Add Tuktuk Manager permissions
            if doctype == 'TukTuk Settings':
                # Settings - full access for managers
                add_permission(doctype, 'Tuktuk Manager', {
                    'read': 1, 'write': 1, 'create': 1, 'delete': 0,
                    'report': 1, 'export': 1, 'print': 1, 'email': 1, 'share': 1
                })
            else:
                # Other doctypes - full operational access
                add_permission(doctype, 'Tuktuk Manager', {
                    'read': 1, 'write': 1, 'create': 1, 'delete': 1,
                    'report': 1, 'export': 1, 'print': 1, 'email': 1, 'share': 1
                })
            
            # Add Driver permissions (limited access)
            if doctype in ['TukTuk Driver', 'TukTuk Transaction', 'TukTuk Vehicle']:
                add_permission(doctype, 'Driver', {'read': 1})
            elif doctype == 'TukTuk Rental':
                add_permission(doctype, 'Driver', {'read': 1, 'create': 1})
            elif doctype == 'TukTuk Settings':
                add_permission(doctype, 'Driver', {'read': 1})
            
            print(f"Fixed permissions for: {doctype}")

def add_permission(doctype, role, perms):
    """Add permission for a role to a doctype"""
    try:
        perm = frappe.new_doc('DocPerm')
        perm.parent = doctype
        perm.parenttype = 'DocType'
        perm.parentfield = 'permissions'
        perm.role = role
        
        for perm_type, value in perms.items():
            setattr(perm, perm_type, value)
        
        perm.insert(ignore_permissions=True)
    except Exception as e:
        print(f"Error adding permission for {doctype}, {role}: {str(e)}")

def create_default_settings():
    """Create default TukTuk Settings record if it doesn't exist"""
    if not frappe.db.exists('TukTuk Settings', 'TukTuk Settings'):
        try:
            settings = frappe.new_doc('TukTuk Settings')
            settings.operating_hours_start = '06:00:00'
            settings.operating_hours_end = '00:00:00'
            settings.global_daily_target = 3000
            settings.global_fare_percentage = 50
            settings.global_rental_initial = 500
            settings.global_rental_hourly = 200
            settings.bonus_enabled = 0
            settings.bonus_amount = 500
            settings.mpesa_paybill = '000000'  # Placeholder
            settings.mpesa_api_key = 'your_api_key_here'
            settings.mpesa_api_secret = 'your_api_secret_here'
            settings.enable_sms_notifications = 0
            settings.enable_email_notifications = 1
            settings.save(ignore_permissions=True)
            print("Created default TukTuk Settings")
        except Exception as e:
            print(f"Error creating default settings: {str(e)}")

def assign_roles_to_current_user():
    """Assign Tuktuk Manager role to current user"""
    try:
        current_user = frappe.session.user
        if current_user and current_user != "Guest":
            user_doc = frappe.get_doc("User", current_user)
            
            # Check if user already has Tuktuk Manager role
            existing_roles = [role.role for role in user_doc.roles]
            
            if "Tuktuk Manager" not in existing_roles:
                user_doc.append("roles", {"role": "Tuktuk Manager"})
                user_doc.save(ignore_permissions=True)
                print(f"Assigned Tuktuk Manager role to {current_user}")
                
    except Exception as e:
        print(f"Error assigning roles: {str(e)}")

def reload_all_doctypes():
    """Reload all doctypes to apply changes"""
    doctypes = [
        'TukTuk Vehicle', 'TukTuk Driver', 'TukTuk Transaction', 
        'TukTuk Rental', 'TukTuk Settings', 'TukTuk Daily Report'
    ]
    
    for doctype in doctypes:
        try:
            frappe.reload_doctype(doctype)
            print(f"Reloaded: {doctype}")
        except Exception as e:
            print(f"Error reloading {doctype}: {str(e)}")