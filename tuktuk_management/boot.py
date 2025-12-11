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
    
    # Priority-based redirect system - TukTuk Driver has highest priority
    # IMPORTANT: Check TukTuk Driver FIRST, before any other role checks
    if "TukTuk Driver" in user_roles:
        # TukTuk Drivers ALWAYS go to their dashboard, regardless of other roles
        bootinfo.tuktuk_redirect = "/tuktuk-driver-dashboard"
        bootinfo.tuktuk_redirect_role = "TukTuk Driver"
        # Log for debugging
        frappe.logger().info(f"TukTuk Driver redirect set for user: {frappe.session.user}")
    
    elif "Tuktuk Manager" in user_roles:
        # TukTuk Managers go to management workspace (only if not a driver)
        if not frappe.local.request or not frappe.local.request.path.startswith('/app/tuktuk-management'):
            bootinfo.tuktuk_redirect = "/app/tuktuk-management"
            bootinfo.tuktuk_redirect_role = "Tuktuk Manager"
    
    elif "System Manager" in user_roles:
        # System Managers can choose, but default to TukTuk management if they have that role too
        # First check if they also have TukTuk Manager role, if not, assign it
        # BUT: Only do this if they are NOT a TukTuk Driver
        try:
            user = frappe.get_doc("User", frappe.session.user)
            user_roles_list = [role.role for role in user.roles]
            
            # Double-check: ensure we don't redirect System Managers who are also Drivers
            if "TukTuk Driver" not in user_roles_list and "Tuktuk Manager" not in user_roles_list:
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