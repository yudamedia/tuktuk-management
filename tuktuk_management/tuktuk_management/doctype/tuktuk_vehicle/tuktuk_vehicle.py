# ~/frappe-bench/apps/tuktuk_management/tuktuk_management/tuktuk_management/doctype/tuktuk_vehicle/tuktuk_vehicle.py

import frappe
from frappe.model.document import Document
from frappe.utils import flt, cint
import re
import json
from frappe.utils import now_datetime

class TukTukVehicle(Document):
    def validate(self):
        """Validate TukTuk Vehicle data"""
        self.validate_tuktuk_id()
        self.validate_mpesa_account()
        self.validate_battery_level()
        self.validate_rental_rates()
        self.validate_coordinates()
        self.sync_geolocation_with_coordinates()
    
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
        """Validate battery level - FIXED VERSION"""
        if self.battery_level is not None:
            try:
                # Convert to float/int to handle both string and numeric inputs
                battery_level = flt(self.battery_level)
                
                if battery_level < 0 or battery_level > 100:
                    frappe.throw("Battery level must be between 0 and 100")
                
                # Ensure it's stored as integer
                self.battery_level = cint(battery_level)
                
            except (ValueError, TypeError):
                frappe.throw("Battery level must be a valid number between 0 and 100")
    
    def validate_rental_rates(self):
        """Validate rental rate values"""
        if self.rental_rate_initial is not None:
            if flt(self.rental_rate_initial) < 0:
                frappe.throw("Initial rental rate must not be negative")
        
        if self.rental_rate_hourly is not None:
            if flt(self.rental_rate_hourly) < 0:
                frappe.throw("Hourly rental rate must not be negative")
    
    def validate_coordinates(self):
        """Validate latitude and longitude - FIXED FIELD NAMES"""
        # Use correct field names from DocType: 'latitude' and 'longitude'
        if hasattr(self, 'latitude') and self.latitude is not None:
            lat = flt(self.latitude)
            if not (-90 <= lat <= 90):
                frappe.throw("Latitude must be between -90 and 90 degrees")
        
        if hasattr(self, 'longitude') and self.longitude is not None:
            lng = flt(self.longitude)
            if not (-180 <= lng <= 180):
                frappe.throw("Longitude must be between -180 and 180 degrees")
    
    def sync_geolocation_with_coordinates(self):
        """Sync geolocation field with individual coordinates - FIXED FIELD NAMES"""
        # Use correct field names from DocType: 'latitude' and 'longitude'
        if (hasattr(self, 'latitude') and hasattr(self, 'longitude') and 
            self.latitude and self.longitude):
            # Create geolocation data for maps
            self.current_location = json.dumps({
                "type": "FeatureCollection",
                "features": [{
                    "type": "Feature",
                    "properties": {},
                    "geometry": {
                        "type": "Point",
                        "coordinates": [flt(self.longitude), flt(self.latitude)]
                    }
                }]
            })
    
    def after_insert(self):
        """Actions after vehicle is created"""
        # Log creation
        frappe.logger().info(f"TukTuk Vehicle {self.tuktuk_id} created successfully")
    
    def on_update(self):
        """Actions when vehicle is updated"""
        # Update any related records if needed
        pass
    
    def get_battery_status(self):
        """Get battery status information"""
        try:
            from tuktuk_management.api.battery_utils import BatteryConverter
            
            if self.battery_level is not None:
                return BatteryConverter.get_battery_status(self.battery_level)
        except ImportError:
            pass
        
        return {"status": "Unknown", "color": "gray", "action": "No data", "priority": "none"}
    
    def get_estimated_range(self):
        """Get estimated range based on current battery level"""
        try:
            from tuktuk_management.api.battery_utils import BatteryConverter
            
            if self.battery_level is not None:
                return BatteryConverter.estimate_range_km(self.battery_level)
        except ImportError:
            pass
        
        return 0.0
    
    def update_battery_from_voltage(self, voltage):
        """Update battery level from voltage reading"""
        try:
            from tuktuk_management.api.battery_utils import BatteryConverter
            
            # Store raw voltage
            self.battery_voltage = flt(voltage)
            
            # Convert to percentage
            self.battery_level = BatteryConverter.voltage_to_percentage(voltage)
            
            # Update timestamp
            self.last_reported = now_datetime()
            
            return True
            
        except Exception as e:
            frappe.logger().error(f"Battery voltage update failed: {str(e)}")
            return False
