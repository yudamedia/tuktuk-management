# ~/frappe-bench/apps/tuktuk_management/tuktuk_management/overrides/tuktuk_settings.py
import frappe
from frappe.model.document import Document

class TukTukSettingsOverride(Document):
    """
    Override class for TukTuk Settings to ensure proper permissions and access
    """
    
    def has_permission(self, ptype, user=None):
        """
        Override permission check to allow proper access
        """
        if not user:
            user = frappe.session.user
        
        # Allow access for System Manager and Tuktuk Manager
        user_roles = frappe.get_roles(user)
        
        if "System Manager" in user_roles or "Tuktuk Manager" in user_roles:
            return True
        
        # For read access, allow if user has any of the driver roles
        if ptype == "read" and "Driver" in user_roles:
            return True
            
        return False
    
    def validate(self):
        """
        Validate TukTuk Settings
        """
        super().validate()
        
        # Ensure operating hours are valid
        if self.operating_hours_start and self.operating_hours_end:
            # Additional validation can be added here
            pass
            
        # Always ensure global targets are positive (target tracking continues regardless of sharing setting)
        if self.global_daily_target and self.global_daily_target <= 0:
            frappe.throw("Global daily target must be greater than 0")

        if self.global_fare_percentage and (self.global_fare_percentage <= 0 or self.global_fare_percentage > 100):
            frappe.throw("Global fare percentage must be between 1 and 100")
    
    def on_update(self):
        """
        Actions to perform when settings are updated
        """
        super().on_update()
        
        # Clear cache to ensure new settings are loaded
        frappe.cache().delete_value("tuktuk_settings")
        
        # Log the update
        frappe.log_error(
            f"TukTuk Settings updated by {frappe.session.user}",
            "TukTuk Settings Update"
        )