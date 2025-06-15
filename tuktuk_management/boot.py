# ~/frappe-bench/apps/tuktuk_management/tuktuk_management/boot.py
import frappe

def boot_session(bootinfo):
    """
    Called during boot to set up session data and ensure proper whitelisting
    """
    if frappe.session.user == "Guest":
        return
    
    # Add Tuktuk Management specific boot data
    bootinfo.tuktuk_management = {
        "version": "1.0.0",
        "initialized": True
    }
    
    # Ensure user has proper permissions
    user = frappe.get_doc("User", frappe.session.user)
    
    # Add Tuktuk Manager role to System Managers automatically
    if "System Manager" in [role.role for role in user.roles]:
        if not any(role.role == "Tuktuk Manager" for role in user.roles):
            user.append("roles", {"role": "Tuktuk Manager"})
            user.save(ignore_permissions=True)
    
    # Set boot info for roles
    bootinfo.user_roles = [role.role for role in user.roles]
    
    # Ensure core Frappe methods are whitelisted for this session
    ensure_core_methods_whitelisted()
    
    # Add TukTuk settings to boot if accessible
    try:
        settings = frappe.get_single("TukTuk Settings")
        bootinfo.tuktuk_settings = {
            "operating_hours_start": settings.operating_hours_start,
            "operating_hours_end": settings.operating_hours_end,
            "system_active": getattr(settings, 'system_active', True)
        }
    except Exception:
        # If settings don't exist or can't be accessed, use defaults
        bootinfo.tuktuk_settings = {
            "operating_hours_start": "06:00:00",
            "operating_hours_end": "00:00:00",
            "system_active": True
        }

def ensure_core_methods_whitelisted():
    """Ensure core Frappe methods are available"""
    try:
        # Get the current whitelisted methods
        if not hasattr(frappe.local, 'whitelisted_methods'):
            frappe.local.whitelisted_methods = set()
        
        # Add essential methods
        essential_methods = [
            "frappe.desk.form.save.savedocs",
            "frappe.desk.form.load.getdoctype", 
            "frappe.desk.form.load.getdoc",
            "frappe.client.get",
            "frappe.client.save",
            "frappe.client.get_list"
        ]
        
        for method in essential_methods:
            frappe.local.whitelisted_methods.add(method)
            
    except Exception as e:
        frappe.log_error(f"Error ensuring core methods whitelisted: {str(e)}")