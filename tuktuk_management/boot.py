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
    
    # Get user roles
    user_roles = frappe.get_roles(frappe.session.user)
    
    # CRITICAL: Priority-based redirect system
    # Check roles in strict priority order with early returns to prevent conflicts
    
    # HIGHEST PRIORITY: TukTuk Driver
    # If user is a driver WITH an actual TukTuk Driver record, redirect to dashboard
    # This prevents Administrator from being redirected (they get all roles by default)
    if "TukTuk Driver" in user_roles:
        # Check if user actually has a TukTuk Driver record
        driver_record = frappe.db.exists("TukTuk Driver", {"user_account": frappe.session.user})
        if driver_record:
            bootinfo.tuktuk_redirect = "/driver/home"
            bootinfo.tuktuk_redirect_role = "TukTuk Driver"
            frappe.logger().info(f"TukTuk Driver redirect set for user: {frappe.session.user}")
            _load_tuktuk_settings(bootinfo, user_roles)
            return  # EXIT EARLY
    
    # SECOND PRIORITY: Tuktuk Executive (if you have this role)
    if "Tuktuk Executive" in user_roles:
        bootinfo.tuktuk_redirect = "/app/tuktuk-management"
        bootinfo.tuktuk_redirect_role = "Tuktuk Executive"
        frappe.logger().info(f"Tuktuk Executive redirect set for user: {frappe.session.user}")
        _load_tuktuk_settings(bootinfo, user_roles)
        return  # EXIT EARLY
    
    # THIRD PRIORITY: Tuktuk Manager
    if "Tuktuk Manager" in user_roles:
        bootinfo.tuktuk_redirect = "/app/tuktuk-management"
        bootinfo.tuktuk_redirect_role = "Tuktuk Manager"
        frappe.logger().info(f"Tuktuk Manager redirect set for user: {frappe.session.user}")
        _load_tuktuk_settings(bootinfo, user_roles)
        return  # EXIT EARLY
    
    # FOURTH PRIORITY: System Manager
    # System Managers go to tuktuk-management ONLY if they don't have driver/manager roles
    if "System Manager" in user_roles:
        # Auto-assign Tuktuk Manager role to System Managers for convenience
        # This allows them to manage the TukTuk system
        try:
            user = frappe.get_doc("User", frappe.session.user)
            user_roles_list = [role.role for role in user.roles]
            
            # Only add Tuktuk Manager if they don't already have it
            if "Tuktuk Manager" not in user_roles_list:
                user.append("roles", {"role": "Tuktuk Manager"})
                user.save(ignore_permissions=True)
                frappe.db.commit()
                frappe.logger().info(f"Auto-assigned Tuktuk Manager role to System Manager: {frappe.session.user}")
                # Redirect to TukTuk management after adding role
                bootinfo.tuktuk_redirect = "/app/tuktuk-management"
                bootinfo.tuktuk_redirect_role = "System Manager (Auto-assigned Tuktuk Manager)"
        except Exception as e:
            frappe.log_error(f"Boot role assignment error: {str(e)}")
        
        # Redirect System Managers to tuktuk-management
        bootinfo.tuktuk_redirect = "/app/tuktuk-management"
        bootinfo.tuktuk_redirect_role = "System Manager"
        frappe.logger().info(f"System Manager redirect set for user: {frappe.session.user}")
        _load_tuktuk_settings(bootinfo, user_roles)
        return  # EXIT EARLY
    
    # No TukTuk-specific redirect needed for other roles
    frappe.logger().info(f"No TukTuk redirect for user: {frappe.session.user}")


def _load_tuktuk_settings(bootinfo, user_roles):
    """
    Helper function to load TukTuk settings for all TukTuk users
    Separated to avoid code duplication
    """
    # Basic settings for all TukTuk users
    if any(role in user_roles for role in ["TukTuk Driver", "Tuktuk Manager", "Tuktuk Executive", "System Manager"]):
        try:
            settings = frappe.get_single("TukTuk Settings")
            bootinfo.tuktuk_settings = {
                "operating_hours_start": settings.operating_hours_start,
                "operating_hours_end": settings.operating_hours_end,
                "global_daily_target": settings.global_daily_target,
                "global_fare_percentage": settings.global_fare_percentage
            }
        except Exception as e:
            # Provide defaults if settings don't exist
            frappe.logger().warning(f"Failed to load TukTuk Settings, using defaults: {str(e)}")
            bootinfo.tuktuk_settings = {
                "operating_hours_start": "06:00:00",
                "operating_hours_end": "00:00:00",
                "global_daily_target": 1400,
                "global_fare_percentage": 50
            }