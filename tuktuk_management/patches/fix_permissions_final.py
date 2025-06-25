# Fix permissions and access issues
import frappe

def execute():
    """Final fix for all permission and access issues"""
    
    print("🔧 Starting comprehensive permission fix...")
    
    # 1. Ensure roles exist
    ensure_roles_exist()
    
    # 2. Fix all doctype permissions
    fix_all_permissions()
    
    # 3. Assign current user the manager role
    assign_manager_role_to_current_user()
    
    # 4. Clear all caches
    frappe.clear_cache()
    frappe.db.commit()
    
    print("✅ Permission fix completed!")

def ensure_roles_exist():
    """Ensure all required roles exist"""
    roles = ['Tuktuk Manager', 'Driver', 'Fleet Supervisor']
    
    for role_name in roles:
        if not frappe.db.exists('Role', role_name):
            role = frappe.new_doc('Role')
            role.role_name = role_name
            role.desk_access = 1
            role.save(ignore_permissions=True)
            print(f"Created role: {role_name}")

def fix_all_permissions():
    """Fix permissions for all TukTuk doctypes"""
    doctypes = ['TukTuk Vehicle', 'TukTuk Driver', 'TukTuk Transaction', 'TukTuk Rental', 'TukTuk Settings']
    
    for doctype in doctypes:
        if frappe.db.exists('DocType', doctype):
            # Clear existing custom permissions
            frappe.db.sql(f"DELETE FROM `tabDocPerm` WHERE parent = '{doctype}' AND role IN ('Tuktuk Manager', 'Driver')")
            
            # Add System Manager permissions
            add_perm(doctype, 'System Manager', all_perms=True)
            
            # Add Tuktuk Manager permissions
            add_perm(doctype, 'Tuktuk Manager', {
                'read': 1, 'write': 1, 'create': 1, 'delete': 1,
                'report': 1, 'export': 1, 'print': 1, 'email': 1
            })
            
            # Add Driver permissions (read-only mostly)
            if doctype in ['TukTuk Vehicle', 'TukTuk Driver', 'TukTuk Transaction']:
                add_perm(doctype, 'Driver', {'read': 1})
            elif doctype == 'TukTuk Rental':
                add_perm(doctype, 'Driver', {'read': 1, 'create': 1})
            
            print(f"Fixed permissions for: {doctype}")

def add_perm(doctype, role, perms=None, all_perms=False):
    """Add permission for a role"""
    try:
        perm = frappe.new_doc('DocPerm')
        perm.parent = doctype
        perm.parenttype = 'DocType'
        perm.parentfield = 'permissions'
        perm.role = role
        
        if all_perms:
            for p in ['read', 'write', 'create', 'delete', 'submit', 'cancel', 'amend', 'report', 'export', 'print', 'email', 'share']:
                setattr(perm, p, 1)
        else:
            for perm_type, value in (perms or {}).items():
                setattr(perm, perm_type, value)
        
        perm.insert(ignore_permissions=True)
    except Exception as e:
        print(f"Error adding permission: {e}")

def assign_manager_role_to_current_user():
    """Assign Tuktuk Manager role to current user"""
    try:
        user = frappe.session.user
        if user and user != "Guest":
            user_doc = frappe.get_doc("User", user)
            
            # Check if user already has the role
            existing_roles = [r.role for r in user_doc.roles]
            if "Tuktuk Manager" not in existing_roles:
                user_doc.append("roles", {"role": "Tuktuk Manager"})
                user_doc.save(ignore_permissions=True)
                print(f"Assigned Tuktuk Manager role to {user}")
                
    except Exception as e:
        print(f"Error assigning role: {e}")
