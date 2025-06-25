# ~/frappe-bench/apps/tuktuk_management/tuktuk_management/boot.py
import frappe

# Apply welcome email override on boot
try:
    from tuktuk_management.api.user_management import apply_welcome_email_override
    apply_welcome_email_override()
except Exception as e:
    frappe.log_error(f"Failed to apply welcome email override on boot: {str(e)}")

def boot_session(bootinfo):
    """
    Boot session setup with automatic redirect for TukTuk roles
    """
    if frappe.session.user == "Guest":
        return
    
    # Basic boot info
    bootinfo.tuktuk_management = {
        "version": "1.0.0",
        "initialized": True
    }
    
    # Check user roles and set appropriate redirects
    user_roles = frappe.get_roles(frappe.session.user)
    
    # Priority-based redirect system
    if "TukTuk Driver" in user_roles:
        # TukTuk Drivers go to their dashboard
        if not frappe.local.request or not frappe.local.request.path.startswith('/tuktuk-driver-dashboard'):
            bootinfo.tuktuk_redirect = "/tuktuk-driver-dashboard"
            bootinfo.tuktuk_redirect_role = "TukTuk Driver"
    
    elif "Tuktuk Manager" in user_roles:
        # TukTuk Managers go to management workspace
        if not frappe.local.request or not frappe.local.request.path.startswith('/app/tuktuk-management'):
            bootinfo.tuktuk_redirect = "/app/tuktuk-management"
            bootinfo.tuktuk_redirect_role = "Tuktuk Manager"
    
    elif "System Manager" in user_roles:
        # System Managers can choose, but default to TukTuk management if they have that role too
        # First check if they also have TukTuk Manager role, if not, assign it
        try:
            user = frappe.get_doc("User", frappe.session.user)
            user_roles_list = [role.role for role in user.roles]
            
            if "Tuktuk Manager" not in user_roles_list:
                user.append("roles", {"role": "Tuktuk Manager"})
                user.save(ignore_permissions=True)
                # After adding role, redirect to TukTuk management
                bootinfo.tuktuk_redirect = "/app/tuktuk-management"
                bootinfo.tuktuk_redirect_role = "System Manager (Auto-assigned Tuktuk Manager)"
        except Exception as e:
            frappe.log_error(f"Boot role assignment error: {str(e)}")
    
    # Basic settings for all TukTuk users
    if any(role in user_roles for role in ["TukTuk Driver", "Tuktuk Manager", "System Manager"]):
        try:
            settings = frappe.get_single("TukTuk Settings")
            bootinfo.tuktuk_settings = {
                "operating_hours_start": settings.operating_hours_start,
                "operating_hours_end": settings.operating_hours_end,
                "global_daily_target": settings.global_daily_target,
                "global_fare_percentage": settings.global_fare_percentage
            }
        except Exception:
            # Provide defaults if settings don't exist
            bootinfo.tuktuk_settings = {
                "operating_hours_start": "06:00:00",
                "operating_hours_end": "00:00:00",
                "global_daily_target": 3000,
                "global_fare_percentage": 50
            }