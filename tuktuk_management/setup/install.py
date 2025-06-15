import frappe

def after_install():
    create_roles()
    create_custom_fields()

def create_roles():
    if not frappe.db.exists('Role', 'Driver'):
        role = frappe.new_doc('Role')
        role.role_name = "Driver"
        role.desk_access = 1
        role.notifications = 1
        role.description = "TukTuk driver role for accessing personal dashboard and transactions"
        role.save(ignore_permissions=True)

def create_custom_fields():
    pass
