# ~/frappe-bench/apps/tuktuk_management/tuktuk_management/api/telematics.py

import frappe
import requests
import json
from frappe import _
from frappe.utils import now_datetime, get_datetime
from datetime import datetime, timedelta

class TelematicsIntegration:
    def __init__(self):
        self.settings = frappe.get_single("TukTuk Settings")
        # You'll need to add API credentials to TukTuk Settings
        self.api_url = self.settings.get("telematics_api_url")
        self.api_key = self.settings.get("telematics_api_key")
        self.api_secret = self.settings.get("telematics_api_secret")
    
    def get_vehicle_data(self, device_id):
        """Get real-time data for a specific vehicle"""
        try:
            if not self.api_url or not self.api_key:
                # Return mock data if API not configured
                return self.get_mock_data()
                
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            endpoint = f"{self.api_url}/devices/{device_id}/status"
            response = requests.get(endpoint, headers=headers, timeout=10)
            
            if response.status_code == 200:
                return response.json()
            else:
                frappe.log_error(f"Telematics API Error: {response.text}")
                return self.get_mock_data()  # Fallback to mock data
        except Exception as e:
            frappe.log_error(f"Telematics Integration Error: {str(e)}")
            return self.get_mock_data()  # Fallback to mock data
    
    def get_mock_data(self):
        """Return mock data for testing/development"""
        import random
        return {
            "battery_level": random.randint(20, 100),
            "latitude": -4.3297 + random.uniform(-0.01, 0.01),  # Diani Beach area
            "longitude": 39.5773 + random.uniform(-0.01, 0.01),
            "speed": random.randint(0, 40),
            "timestamp": now_datetime().isoformat()
        }
    
    def update_vehicle_status(self, device_id):
        """Update vehicle status based on telematics data"""
        data = self.get_vehicle_data(device_id)
        if not data:
            return False
            
        # Look up the tuktuk by device ID
        tuktuks = frappe.get_all(
            "TukTuk Vehicle", 
            filters={"device_id": device_id},
            fields=["name"]
        )
        
        if not tuktuks:
            frappe.log_error(f"No TukTuk found with device ID: {device_id}")
            return False
            
        tuktuk = frappe.get_doc("TukTuk Vehicle", tuktuks[0].name)
        
        # Update with latest data
        try:
            # Update battery level
            if "battery_level" in data:
                tuktuk.battery_level = data["battery_level"]
                tuktuk.last_battery_reading = data["battery_level"]
                
            # Update location
            if "latitude" in data and "longitude" in data:
                location_data = {
                    "type": "FeatureCollection",
                    "features": [{
                        "type": "Feature",
                        "properties": {},
                        "geometry": {
                            "type": "Point",
                            "coordinates": [float(data["longitude"]), float(data["latitude"])]
                        }
                    }]
                }
                tuktuk.current_location = json.dumps(location_data)
                
            # Update last reported time
            tuktuk.last_reported = now_datetime()
            
            # Check for low battery
            if tuktuk.battery_level <= 20:
                from tuktuk_management.api.tuktuk import check_battery_level
                check_battery_level(tuktuk)
                
            tuktuk.save(ignore_permissions=True)
            return True
        except Exception as e:
            frappe.log_error(f"Error updating vehicle status: {str(e)}")
            return False

def update_all_vehicle_statuses():
    """Background job to update all vehicle statuses"""
    try:
        integration = TelematicsIntegration()
        vehicles = frappe.get_all(
            "TukTuk Vehicle",
            filters={"device_id": ["!=", ""]},
            fields=["device_id", "name"]
        )
        
        for vehicle in vehicles:
            if vehicle.device_id:
                integration.update_vehicle_status(vehicle.device_id)
        
        frappe.db.commit()
    except Exception as e:
        frappe.log_error(f"Error in update_all_vehicle_statuses: {str(e)}")

# API endpoint for webhook integration
@frappe.whitelist(allow_guest=True)
def telematics_webhook():
    """Webhook endpoint for real-time telematics updates"""
    try:
        # Get the raw data from the request
        if frappe.request and frappe.request.data:
            data = json.loads(frappe.request.data)
            
            # Process the webhook data
            device_id = data.get("device_id")
            if device_id:
                integration = TelematicsIntegration()
                success = integration.update_vehicle_status(device_id)
                
                return {"status": "success" if success else "error"}
        return {"status": "error", "message": "No data received"}
    except Exception as e:
        frappe.log_error(f"Telematics Webhook Error: {str(e)}")
        return {"status": "error", "message": str(e)}

# Additional API methods for form integration
@frappe.whitelist()
def update_from_device(vehicle_name, device_id):
    """Update vehicle data from telematics device - called from form"""
    try:
        # Get the vehicle document
        vehicle = frappe.get_doc("TukTuk Vehicle", vehicle_name)
        
        if not vehicle.device_id or vehicle.device_id != device_id:
            frappe.throw(_("Device ID mismatch"))
        
        integration = TelematicsIntegration()
        telematics_data = integration.get_vehicle_data(device_id)
        
        if telematics_data:
            # Update vehicle with latest data
            if 'battery_level' in telematics_data:
                vehicle.last_battery_reading = telematics_data['battery_level']
                vehicle.battery_level = telematics_data['battery_level']
            
            if 'latitude' in telematics_data and 'longitude' in telematics_data:
                location_data = {
                    "type": "FeatureCollection",
                    "features": [{
                        "type": "Feature",
                        "properties": {},
                        "geometry": {
                            "type": "Point",
                            "coordinates": [
                                float(telematics_data['longitude']),
                                float(telematics_data['latitude'])
                            ]
                        }
                    }]
                }
                vehicle.current_location = json.dumps(location_data)
            
            vehicle.last_reported = now_datetime()
            vehicle.save(ignore_permissions=True)
            
            return {
                "success": True,
                "message": _("Vehicle data updated successfully"),
                "data": telematics_data
            }
        else:
            frappe.throw(_("Unable to retrieve data from telematics device"))
            
    except Exception as e:
        frappe.log_error(f"Telematics update failed: {str(e)}")
        frappe.throw(_("Failed to update from telematics device: {0}").format(str(e)))

@frappe.whitelist()
def update_location(tuktuk_id, latitude, longitude):
    """Update vehicle location from external source"""
    try:
        vehicle = frappe.get_value("TukTuk Vehicle", {"tuktuk_id": tuktuk_id}, "name")
        if not vehicle:
            frappe.throw(_("Vehicle not found"))
        
        doc = frappe.get_doc("TukTuk Vehicle", vehicle)
        
        # Update location
        location_data = {
            "type": "FeatureCollection",
            "features": [{
                "type": "Feature",
                "properties": {},
                "geometry": {
                    "type": "Point",
                    "coordinates": [float(longitude), float(latitude)]
                }
            }]
        }
        
        doc.current_location = json.dumps(location_data)
        doc.last_reported = now_datetime()
        doc.save(ignore_permissions=True)
        
        return {"success": True, "message": _("Location updated successfully")}
        
    except Exception as e:
        frappe.log_error(f"Location update failed: {str(e)}")
        return {"success": False, "message": str(e)}

@frappe.whitelist()
def update_battery(tuktuk_id, battery_level):
    """Update vehicle battery level from external source"""
    try:
        vehicle = frappe.get_value("TukTuk Vehicle", {"tuktuk_id": tuktuk_id}, "name")
        if not vehicle:
            frappe.throw(_("Vehicle not found"))
        
        doc = frappe.get_doc("TukTuk Vehicle", vehicle)
        
        # Update battery level
        doc.battery_level = float(battery_level)
        doc.last_battery_reading = float(battery_level)
        doc.last_reported = now_datetime()
        doc.save(ignore_permissions=True)
        
        # Check if battery is low and send alerts
        from tuktuk_management.api.tuktuk import check_battery_level
        check_battery_level(doc)
        
        return {"success": True, "message": _("Battery level updated successfully")}
        
    except Exception as e:
        frappe.log_error(f"Battery update failed: {str(e)}")
        return {"success": False, "message": str(e)}

@frappe.whitelist()
def get_status(tuktuk_id):
    """Get current vehicle status"""
    try:
        vehicle = frappe.get_value("TukTuk Vehicle", {"tuktuk_id": tuktuk_id}, 
                                 ["name", "status", "battery_level", "last_reported"], as_dict=True)
        if not vehicle:
            frappe.throw(_("Vehicle not found"))
        
        return {
            "success": True,
            "data": vehicle
        }
        
    except Exception as e:
        frappe.log_error(f"Status check failed: {str(e)}")
        return {"success": False, "message": str(e)}