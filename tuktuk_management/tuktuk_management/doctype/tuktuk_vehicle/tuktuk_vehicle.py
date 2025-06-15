# ~/frappe-bench/apps/tuktuk_management/tuktuk_management/tuktuk_management/doctype/tuktuk_vehicle/tuktuk_vehicle.py

import frappe
from frappe.model.document import Document
import re

class TukTukVehicle(Document):
    def validate(self):
        """Validate TukTuk Vehicle data"""
        self.validate_tuktuk_id()
        self.validate_mpesa_account()
        self.validate_battery_level()
        self.validate_rental_rates()
    
    def validate_tuktuk_id(self):
        """Validate TukTuk ID format"""
        if not self.tuktuk_id:
            frappe.throw("TukTuk ID is required")
        
        # Ensure unique tuktuk_id
        existing = frappe.db.exists("TukTuk Vehicle", {"tuktuk_id": self.tuktuk_id, "name": ["!=", self.name]})
        if existing:
            frappe.throw(f"TukTuk ID {self.tuktuk_id} already exists")
    
    def validate_mpesa_account(self):
        """Validate Mpesa account number"""
        if self.mpesa_account:
            # Should be 3 digits for paybill account reference
            if not re.match(r'^\d{3}$', str(self.mpesa_account)):
                frappe.throw("Mpesa account must be exactly 3 digits")
            
            # Ensure unique mpesa_account
            existing = frappe.db.exists("TukTuk Vehicle", {"mpesa_account": self.mpesa_account, "name": ["!=", self.name]})
            if existing:
                frappe.throw(f"Mpesa account {self.mpesa_account} already exists")
    
    def validate_battery_level(self):
        """Validate battery level"""
        if self.battery_level is not None:
            if self.battery_level < 0 or self.battery_level > 100:
                frappe.throw("Battery level must be between 0 and 100")
    
    def validate_rental_rates(self):
        """Validate rental rates if provided"""
        if self.rental_rate_initial and self.rental_rate_initial <= 0:
            frappe.throw("Initial rental rate must be greater than 0")
        if self.rental_rate_hourly and self.rental_rate_hourly <= 0:
            frappe.throw("Hourly rental rate must be greater than 0")
    
    def before_save(self):
        """Actions before saving"""
        # Auto-generate mpesa account if not provided
        if not self.mpesa_account:
            self.auto_generate_mpesa_account()
    
    def auto_generate_mpesa_account(self):
        """Auto-generate 3-digit mpesa account"""
        if self.tuktuk_id:
            # Extract numbers from tuktuk_id
            numbers = re.findall(r'\d+', self.tuktuk_id)
            if numbers:
                # Use last 3 digits of the first number found
                account = numbers[0][-3:].zfill(3)
                
                # Ensure it's unique
                counter = 1
                original_account = account
                while frappe.db.exists("TukTuk Vehicle", {"mpesa_account": account}):
                    account = str(int(original_account) + counter).zfill(3)
                    counter += 1
                    if counter > 100:  # Prevent infinite loop
                        break
                
                self.mpesa_account = account
    
    def on_update(self):
        """Actions after update"""
        # Update assigned driver if status changes
        if self.has_value_changed('status'):
            self.handle_status_change()
    
    def handle_status_change(self):
        """Handle vehicle status changes"""
        # Find assigned driver
        assigned_driver = frappe.get_all("TukTuk Driver", 
                                       filters={"assigned_tuktuk": self.name},
                                       fields=["name", "driver_name"])
        
        if assigned_driver and self.status == "Available":
            # If vehicle becomes available, clear driver assignment
            driver_doc = frappe.get_doc("TukTuk Driver", assigned_driver[0].name)
            driver_doc.assigned_tuktuk = ""
            driver_doc.save()
            
            # Log the change
            frappe.get_doc({
                "doctype": "Comment",
                "comment_type": "Info",
                "reference_doctype": "TukTuk Vehicle",
                "reference_name": self.name,
                "content": f"Vehicle status changed to {self.status}. Driver assignment cleared."
            }).insert(ignore_permissions=True)