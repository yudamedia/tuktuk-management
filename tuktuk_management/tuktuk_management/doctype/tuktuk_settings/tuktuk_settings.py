# ~/frappe-bench/apps/tuktuk_management/tuktuk_management/tuktuk_management/doctype/tuktuk_settings/tuktuk_settings.py
import frappe
from frappe.model.document import Document

class TukTukSettings(Document):
    def validate(self):
        """
        Validate TukTuk Settings without calling super().validate()
        """
        # Ensure operating hours are valid
        if self.operating_hours_start and self.operating_hours_end:
            # Additional validation can be added here
            pass
            
        # Ensure global targets are positive
        if self.global_daily_target and self.global_daily_target <= 0:
            frappe.throw("Global daily target must be greater than 0")
            
        if self.global_fare_percentage and (self.global_fare_percentage <= 0 or self.global_fare_percentage > 100):
            frappe.throw("Global fare percentage must be between 1 and 100")
            
        # Validate rental rates
        if self.global_rental_initial and self.global_rental_initial <= 0:
            frappe.throw("Global rental initial rate must be greater than 0")
            
        if self.global_rental_hourly and self.global_rental_hourly <= 0:
            frappe.throw("Global rental hourly rate must be greater than 0")
            
        # Validate bonus settings
        if self.bonus_enabled and self.bonus_amount and self.bonus_amount <= 0:
            frappe.throw("Bonus amount must be greater than 0 when bonus is enabled")
    
    def on_update(self):
        """
        Actions to perform when settings are updated
        """
        # Clear cache to ensure new settings are loaded
        frappe.cache().delete_value("tuktuk_settings")
        
        # Log the update for audit trail
        frappe.logger().info(f"TukTuk Settings updated by {frappe.session.user}")
        
    def after_insert(self):
        """
        Actions to perform after first creation
        """
        frappe.logger().info("TukTuk Settings created successfully")
        
    def on_trash(self):
        """
        Prevent deletion of settings
        """
        frappe.throw("TukTuk Settings cannot be deleted. You can only modify the existing settings.")