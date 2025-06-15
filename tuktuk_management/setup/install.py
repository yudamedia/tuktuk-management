# ~/frappe-bench/apps/tuktuk_management/tuktuk_management/setup/install.py

import frappe

def after_install():
    """Setup function called after app installation"""
    create_roles()
    create_default_settings()
    create_custom_fields()
    setup_permissions()
    print("✅ TukTuk Management app installed successfully!")

def create_roles():
    """Create all necessary roles for TukTuk management"""
    
    roles_to_create = [
        {
            'role_name': 'Tuktuk Manager',
            'description': 'Full management access to TukTuk operations, drivers, vehicles, and settings',
            'desk_access': 1,
            'notifications': 1,
            'is_custom': 1
        },
        {
            'role_name': 'Driver',
            'description': 'TukTuk driver role for accessing personal dashboard, transactions, and rentals',
            'desk_access': 1,
            'notifications': 1,
            'is_custom': 1
        },
        {
            'role_name': 'Fleet Supervisor',
            'description': 'Supervises fleet operations, vehicle maintenance, and driver assignments',
            'desk_access': 1,
            'notifications': 1,
            'is_custom': 1
        },
        {
            'role_name': 'Finance Officer',
            'description': 'Manages financial transactions, daily targets, and payment processing',
            'desk_access': 1,
            'notifications': 1,
            'is_custom': 1
        },
        {
            'role_name': 'Operations Viewer',
            'description': 'Read-only access to view operations data and reports',
            'desk_access': 1,
            'notifications': 0,
            'is_custom': 1
        }
    ]
    
    for role_data in roles_to_create:
        create_role_if_not_exists(role_data)

def create_role_if_not_exists(role_data):
    """Create a role if it doesn't already exist"""
    role_name = role_data['role_name']
    
    if not frappe.db.exists('Role', role_name):
        try:
            role = frappe.new_doc('Role')
            role.role_name = role_name
            role.desk_access = role_data.get('desk_access', 1)
            role.notifications = role_data.get('notifications', 1)
            role.description = role_data.get('description', '')
            role.is_custom = role_data.get('is_custom', 1)
            role.save(ignore_permissions=True)
            print(f"✅ Created role: {role_name}")
        except Exception as e:
            print(f"❌ Error creating role {role_name}: {str(e)}")
            frappe.log_error(f"Role Creation Error: {str(e)}", f"Failed to create role: {role_name}")
    else:
        print(f"⚠️  Role already exists: {role_name}")

def create_default_settings():
    """Create default TukTuk Settings if they don't exist"""
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
            print("✅ Created default TukTuk Settings")
        except Exception as e:
            print(f"❌ Error creating default settings: {str(e)}")
            frappe.log_error(f"Settings Creation Error: {str(e)}")

def setup_permissions():
    """Setup basic permissions for the roles"""
    try:
        # Define permission matrix
        permissions_matrix = {
            'TukTuk Vehicle': {
                'Tuktuk Manager': {'read': 1, 'write': 1, 'create': 1, 'delete': 1, 'report': 1, 'export': 1},
                'Fleet Supervisor': {'read': 1, 'write': 1, 'create': 1, 'delete': 0, 'report': 1, 'export': 1},
                'Driver': {'read': 1, 'write': 0, 'create': 0, 'delete': 0, 'report': 0, 'export': 0},
                'Finance Officer': {'read': 1, 'write': 0, 'create': 0, 'delete': 0, 'report': 1, 'export': 1},
                'Operations Viewer': {'read': 1, 'write': 0, 'create': 0, 'delete': 0, 'report': 1, 'export': 0}
            },
            'TukTuk Driver': {
                'Tuktuk Manager': {'read': 1, 'write': 1, 'create': 1, 'delete': 1, 'report': 1, 'export': 1},
                'Fleet Supervisor': {'read': 1, 'write': 1, 'create': 1, 'delete': 0, 'report': 1, 'export': 1},
                'Driver': {'read': 1, 'write': 0, 'create': 0, 'delete': 0, 'report': 0, 'export': 0},
                'Finance Officer': {'read': 1, 'write': 0, 'create': 0, 'delete': 0, 'report': 1, 'export': 1},
                'Operations Viewer': {'read': 1, 'write': 0, 'create': 0, 'delete': 0, 'report': 1, 'export': 0}
            },
            'TukTuk Transaction': {
                'Tuktuk Manager': {'read': 1, 'write': 1, 'create': 1, 'delete': 1, 'report': 1, 'export': 1},
                'Fleet Supervisor': {'read': 1, 'write': 0, 'create': 0, 'delete': 0, 'report': 1, 'export': 1},
                'Driver': {'read': 1, 'write': 0, 'create': 0, 'delete': 0, 'report': 0, 'export': 0},
                'Finance Officer': {'read': 1, 'write': 1, 'create': 1, 'delete': 0, 'report': 1, 'export': 1},
                'Operations Viewer': {'read': 1, 'write': 0, 'create': 0, 'delete': 0, 'report': 1, 'export': 0}
            },
            'TukTuk Rental': {
                'Tuktuk Manager': {'read': 1, 'write': 1, 'create': 1, 'delete': 1, 'report': 1, 'export': 1},
                'Fleet Supervisor': {'read': 1, 'write': 1, 'create': 1, 'delete': 0, 'report': 1, 'export': 1},
                'Driver': {'read': 1, 'write': 0, 'create': 1, 'delete': 0, 'report': 0, 'export': 0},
                'Finance Officer': {'read': 1, 'write': 0, 'create': 0, 'delete': 0, 'report': 1, 'export': 1},
                'Operations Viewer': {'read': 1, 'write': 0, 'create': 0, 'delete': 0, 'report': 1, 'export': 0}
            },
            'TukTuk Settings': {
                'Tuktuk Manager': {'read': 1, 'write': 1, 'create': 1, 'delete': 0, 'report': 0, 'export': 0},
                'Fleet Supervisor': {'read': 1, 'write': 0, 'create': 0, 'delete': 0, 'report': 0, 'export': 0},
                'Driver': {'read': 1, 'write': 0, 'create': 0, 'delete': 0, 'report': 0, 'export': 0},
                'Finance Officer': {'read': 1, 'write': 0, 'create': 0, 'delete': 0, 'report': 0, 'export': 0},
                'Operations Viewer': {'read': 1, 'write': 0, 'create': 0, 'delete': 0, 'report': 0, 'export': 0}
            },
            'TukTuk Daily Report': {
                'Tuktuk Manager': {'read': 1, 'write': 1, 'create': 1, 'delete': 1, 'report': 1, 'export': 1},
                'Fleet Supervisor': {'read': 1, 'write': 0, 'create': 0, 'delete': 0, 'report': 1, 'export': 1},
                'Driver': {'read': 0, 'write': 0, 'create': 0, 'delete': 0, 'report': 0, 'export': 0},
                'Finance Officer': {'read': 1, 'write': 0, 'create': 0, 'delete': 0, 'report': 1, 'export': 1},
                'Operations Viewer': {'read': 1, 'write': 0, 'create': 0, 'delete': 0, 'report': 1, 'export': 0}
            }
        }
        
        # Apply permissions (this will be handled by DocType JSON files)
        print("✅ Permission matrix defined (will be applied via DocType definitions)")
        
    except Exception as e:
        print(f"❌ Error setting up permissions: {str(e)}")
        frappe.log_error(f"Permission Setup Error: {str(e)}")

def create_custom_fields():
    """Create any custom fields if needed"""
    try:
        # Add any custom fields here if needed for integration
        # For now, we'll skip this as DocTypes should have all needed fields
        print("✅ Custom fields setup completed")
    except Exception as e:
        print(f"❌ Error creating custom fields: {str(e)}")
        frappe.log_error(f"Custom Fields Error: {str(e)}")

def assign_default_roles_to_administrator():
    """Assign TukTuk Manager role to Administrator"""
    try:
        admin_user = frappe.get_doc("User", "Administrator")
        
        # Check if TukTuk Manager role already exists for admin
        existing_roles = [role.role for role in admin_user.roles]
        
        if "Tuktuk Manager" not in existing_roles:
            admin_user.append("roles", {"role": "Tuktuk Manager"})
            admin_user.save(ignore_permissions=True)
            print("✅ Assigned TukTuk Manager role to Administrator")
        else:
            print("⚠️  Administrator already has TukTuk Manager role")
            
    except Exception as e:
        print(f"❌ Error assigning roles to Administrator: {str(e)}")
        frappe.log_error(f"Admin Role Assignment Error: {str(e)}")

# Additional helper function for post-install setup
def setup_demo_data():
    """Create demo data for testing (optional)"""
    # This can be called separately after installation if needed
    pass