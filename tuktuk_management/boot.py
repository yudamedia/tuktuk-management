# ~/frappe-bench/apps/tuktuk_management/tuktuk_management/boot.py
import frappe

def boot_session(bootinfo):
    """
    Simple boot session setup without complex whitelisting
    """
    if frappe.session.user == "Guest":
        return
    
    # Basic boot info
    bootinfo.tuktuk_management = {
        "version": "1.0.0",
        "initialized": True
    }
    
    # Simple role assignment for System Managers
    try:
        user = frappe.get_doc("User", frappe.session.user)
        user_roles = [role.role for role in user.roles]
        
        # Only add Tuktuk Manager role if user is System Manager
        if "System Manager" in user_roles and "Tuktuk Manager" not in user_roles:
            user.append("roles", {"role": "Tuktuk Manager"})
            user.save(ignore_permissions=True)
    except Exception as e:
        # Don't fail boot if role assignment fails
        frappe.log_error(f"Boot role assignment error: {str(e)}")
    
    # Basic settings
    try:
        settings = frappe.get_single("TukTuk Settings")
        bootinfo.tuktuk_settings = {
            "operating_hours_start": settings.operating_hours_start,
            "operating_hours_end": settings.operating_hours_end
        }
    except Exception:
        # Provide defaults if settings don't exist
        bootinfo.tuktuk_settings = {
            "operating_hours_start": "06:00:00",
            "operating_hours_end": "00:00:00"
        }