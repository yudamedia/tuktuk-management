# ~/frappe-bench/apps/tuktuk_management/tuktuk_management/tuktuk_management/doctype/tuktuk_vehicle/tuktuk_vehicle.py

import frappe
from frappe.model.document import Document
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
    
    def validate_coordinates(self):
        """Validate latitude and longitude if provided"""
        if self.latitude is not None:
            if self.latitude < -90 or self.latitude > 90:
                frappe.throw("Latitude must be between -90 and 90 degrees")
        
        if self.longitude is not None:
            if self.longitude < -180 or self.longitude > 180:
                frappe.throw("Longitude must be between -180 and 180 degrees")
    
    def sync_geolocation_with_coordinates(self):
        """Sync geolocation field with latitude/longitude coordinates"""
        # If both latitude and longitude are provided, update the geolocation field
        if self.latitude is not None and self.longitude is not None:
            geojson = {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "properties": {
                            "name": self.tuktuk_id or "TukTuk Location",
                            "description": f"TukTuk {self.tuktuk_id} - {self.status}",
                            "tuktuk_id": self.tuktuk_id,
                            "status": self.status,
                            "battery_level": self.battery_level
                        },
                        "geometry": {
                            "type": "Point",
                            "coordinates": [float(self.longitude), float(self.latitude)]  # [lng, lat] for GeoJSON
                        }
                    }
                ]
            }
            self.current_location = json.dumps(geojson)
            
        # If geolocation is provided, extract coordinates
        elif self.current_location and not (self.latitude and self.longitude):
            try:
                location_data = json.loads(self.current_location)
                if (location_data.get("features") and 
                    len(location_data["features"]) > 0 and 
                    location_data["features"][0].get("geometry") and
                    location_data["features"][0]["geometry"].get("coordinates")):
                    
                    coordinates = location_data["features"][0]["geometry"]["coordinates"]
                    if len(coordinates) >= 2:
                        self.longitude = coordinates[0]  # First coordinate is longitude
                        self.latitude = coordinates[1]   # Second coordinate is latitude
            except (json.JSONDecodeError, KeyError, IndexError):
                # If parsing fails, don't update coordinates
                pass
    
    def before_save(self):
        """Actions before saving"""
        # Auto-generate mpesa account if not provided
        if not self.mpesa_account:
            self.auto_generate_mpesa_account()
        
        # Update last_reported time if location changed
        if self.has_value_changed('current_location') or self.has_value_changed('latitude') or self.has_value_changed('longitude'):
            self.last_reported = now_datetime()
    
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
        
        # Log location changes for tracking
        if self.has_value_changed('current_location') or self.has_value_changed('latitude') or self.has_value_changed('longitude'):
            self.log_location_change()
    
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
    
    def log_location_change(self):
        """Log location changes for audit trail"""
        try:
            location_info = ""
            if self.latitude and self.longitude:
                location_info = f"Coordinates: {self.latitude:.6f}, {self.longitude:.6f}"
            
            if self.location_notes:
                location_info += f" - Notes: {self.location_notes}"
            
            if location_info:
                frappe.get_doc({
                    "doctype": "Comment",
                    "comment_type": "Info", 
                    "reference_doctype": "TukTuk Vehicle",
                    "reference_name": self.name,
                    "content": f"Location updated: {location_info}"
                }).insert(ignore_permissions=True)
        except Exception as e:
            frappe.log_error(f"Error logging location change: {str(e)}")
    
    def update_location_from_coordinates(self, latitude, longitude, notes=""):
        """Update location from external coordinates (API method)"""
        self.latitude = latitude
        self.longitude = longitude
        if notes:
            self.location_notes = notes
        
        # This will trigger sync_geolocation_with_coordinates in validate()
        self.save()
        
        return {
            "success": True,
            "message": f"Location updated to {latitude:.6f}, {longitude:.6f}",
            "coordinates": [longitude, latitude]
        }
    
    def get_current_coordinates(self):
        """Get current coordinates as a tuple (latitude, longitude)"""
        if self.latitude is not None and self.longitude is not None:
            return (float(self.latitude), float(self.longitude))
        
        # Try to extract from geolocation field
        if self.current_location:
            try:
                location_data = json.loads(self.current_location)
                if (location_data.get("features") and 
                    len(location_data["features"]) > 0 and 
                    location_data["features"][0].get("geometry") and
                    location_data["features"][0]["geometry"].get("coordinates")):
                    
                    coordinates = location_data["features"][0]["geometry"]["coordinates"]
                    if len(coordinates) >= 2:
                        return (float(coordinates[1]), float(coordinates[0]))  # Return as (lat, lng)
            except (json.JSONDecodeError, KeyError, IndexError, ValueError):
                pass
        
        return None
    
    def get_distance_to(self, other_latitude, other_longitude):
        """Calculate distance to another point in kilometers using Haversine formula"""
        current_coords = self.get_current_coordinates()
        if not current_coords:
            return None
        
        import math
        
        lat1, lon1 = current_coords
        lat2, lon2 = float(other_latitude), float(other_longitude)
        
        # Convert latitude and longitude from degrees to radians
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        
        # Haversine formula
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        # Radius of earth in kilometers
        r = 6371
        
        return c * r

# API Methods for location management

@frappe.whitelist()
def update_vehicle_location(vehicle_name, latitude, longitude, notes=""):
    """API method to update vehicle location"""
    try:
        vehicle = frappe.get_doc("TukTuk Vehicle", vehicle_name)
        result = vehicle.update_location_from_coordinates(
            float(latitude), 
            float(longitude), 
            notes
        )
        return result
    except Exception as e:
        frappe.log_error(f"Error updating vehicle location: {str(e)}")
        frappe.throw(f"Failed to update location: {str(e)}")

@frappe.whitelist()
def get_vehicle_coordinates(vehicle_name):
    """API method to get vehicle coordinates"""
    try:
        vehicle = frappe.get_doc("TukTuk Vehicle", vehicle_name)
        coords = vehicle.get_current_coordinates()
        
        if coords:
            return {
                "success": True,
                "latitude": coords[0],
                "longitude": coords[1],
                "last_reported": vehicle.last_reported
            }
        else:
            return {
                "success": False,
                "message": "No location data available"
            }
    except Exception as e:
        frappe.log_error(f"Error getting vehicle coordinates: {str(e)}")
        return {
            "success": False,
            "message": str(e)
        }

@frappe.whitelist()
def get_vehicles_near_location(latitude, longitude, radius_km=5):
    """Get all vehicles within a certain radius of a location"""
    try:
        vehicles = frappe.get_all("TukTuk Vehicle", 
                                 filters={"latitude": ["!=", ""], "longitude": ["!=", ""]},
                                 fields=["name", "tuktuk_id", "latitude", "longitude", "status", "battery_level"])
        
        nearby_vehicles = []
        
        for vehicle in vehicles:
            if vehicle.latitude and vehicle.longitude:
                vehicle_doc = frappe.get_doc("TukTuk Vehicle", vehicle.name)
                distance = vehicle_doc.get_distance_to(latitude, longitude)
                
                if distance and distance <= radius_km:
                    nearby_vehicles.append({
                        "name": vehicle.name,
                        "tuktuk_id": vehicle.tuktuk_id,
                        "latitude": vehicle.latitude,
                        "longitude": vehicle.longitude,
                        "status": vehicle.status,
                        "battery_level": vehicle.battery_level,
                        "distance_km": round(distance, 2)
                    })
        
        # Sort by distance
        nearby_vehicles.sort(key=lambda x: x["distance_km"])
        
        return {
            "success": True,
            "vehicles": nearby_vehicles,
            "count": len(nearby_vehicles)
        }
        
    except Exception as e:
        frappe.log_error(f"Error finding nearby vehicles: {str(e)}")
        return {
            "success": False,
            "message": str(e)
        }

@frappe.whitelist()
def bulk_update_locations_from_telematics():
    """Update all vehicle locations from telematics devices"""
    try:
        from tuktuk_management.api.telematics import update_all_vehicle_statuses
        update_all_vehicle_statuses()
        
        return {
            "success": True,
            "message": "All vehicle locations updated from telematics"
        }
    except Exception as e:
        frappe.log_error(f"Error in bulk location update: {str(e)}")
        return {
            "success": False,
            "message": str(e)
        }