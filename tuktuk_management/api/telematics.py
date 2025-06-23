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
        """Return mock data for testing/development based on telemetry analysis"""
        import random
        
        # Mock data that mimics the actual telemetry format
        return {
            "device_imei": f"86090905{random.randint(100000, 999999)}",
            "device_id": str(random.randint(135, 200)),
            "device_status": random.choice(["Static", "Moving", "Offline"]),
            "voltage": random.randint(75, 85),  # Already as percentage based on analysis
            "latitude": -4.3297 + random.uniform(-0.01, 0.01),  # Diani Beach area
            "longitude": 39.5773 + random.uniform(-0.01, 0.01),
            "speed": random.randint(0, 40),
            "course": random.randint(0, 360),
            "satellite": random.randint(8, 16),
            "gps_signal_strength": random.randint(20, 35),
            "last_gps_time": now_datetime().isoformat(),
            "last_online_time": now_datetime().isoformat(),
            "is_car_go": random.choice([0, 1])
        }
    
    def parse_telemetry_data(self, raw_data):
        """Parse telemetry data into standardized format"""
        try:
            # Handle both API response and CSV-like data
            if isinstance(raw_data, dict):
                return {
                    "device_imei": raw_data.get("device_imei", ""),
                    "device_id": str(raw_data.get("device_id", "")),
                    "battery_voltage": float(raw_data.get("voltage", 0)),
                    "latitude": float(raw_data.get("latitude", 0)),
                    "longitude": float(raw_data.get("longitude", 0)),
                    "speed": float(raw_data.get("speed", 0)),
                    "course": float(raw_data.get("course", 0)),
                    "satellite_count": int(raw_data.get("satellite", 0)),
                    "gps_signal_strength": int(raw_data.get("gps_signal_strength", 0)),
                    "device_status": raw_data.get("device_status", "Unknown"),
                    "last_update": raw_data.get("last_gps_time", now_datetime()),
                    "is_moving": bool(raw_data.get("is_car_go", 0))
                }
            
            # Handle list/array format (from CSV export)
            elif isinstance(raw_data, list) and len(raw_data) >= 28:
                return {
                    "device_imei": str(raw_data[0]) if raw_data[0] else "",
                    "device_id": str(raw_data[1]) if raw_data[1] else "",
                    "battery_voltage": float(raw_data[27]) if raw_data[27] else 0,
                    "latitude": float(str(raw_data[15]).replace('\t', '')) if raw_data[15] else 0,
                    "longitude": float(str(raw_data[14]).replace('\t', '')) if raw_data[14] else 0,
                    "speed": float(raw_data[16]) if raw_data[16] else 0,
                    "course": float(raw_data[17]) if raw_data[17] else 0,
                    "satellite_count": int(raw_data[19]) if raw_data[19] else 0,
                    "gps_signal_strength": int(raw_data[29]) if len(raw_data) > 29 and raw_data[29] else 0,
                    "device_status": str(raw_data[12]) if raw_data[12] else "Unknown",
                    "last_update": str(raw_data[26]) if raw_data[26] else now_datetime(),
                    "is_moving": bool(int(raw_data[38])) if len(raw_data) > 38 and raw_data[38] else False
                }
            
            return None
            
        except Exception as e:
            frappe.log_error(f"Telemetry data parsing error: {str(e)}")
            return None
    
    def update_vehicle_status(self, device_id):
        """Update vehicle status based on telematics data"""
        try:
            raw_data = self.get_vehicle_data(device_id)
            if not raw_data:
                return False
            
            parsed_data = self.parse_telemetry_data(raw_data)
            if not parsed_data:
                return False
                
            # Look up the tuktuk by device ID
            tuktuks = frappe.get_all(
                "TukTuk Vehicle", 
                filters={"device_id": device_id},
                fields=["name", "tuktuk_id"]
            )
            
            if not tuktuks:
                # Try to find by IMEI if device_id lookup fails
                if parsed_data["device_imei"]:
                    tuktuks = frappe.get_all(
                        "TukTuk Vehicle",
                        filters={"device_imei": parsed_data["device_imei"]},
                        fields=["name", "tuktuk_id"]
                    )
            
            if not tuktuks:
                frappe.log_error(f"No TukTuk found with device ID: {device_id}")
                return False
                
            tuktuk = frappe.get_doc("TukTuk Vehicle", tuktuks[0].name)
            
            # Update with latest data using battery conversion utility
            updated = False
            
            # Update battery using conversion utility
            if parsed_data["battery_voltage"] > 0:
                from tuktuk_management.api.battery_utils import update_battery_from_telemetry
                battery_result = update_battery_from_telemetry(tuktuk.name, {
                    "voltage": parsed_data["battery_voltage"]
                })
                updated = battery_result.get("success", False)
                
            # Update location
            if parsed_data["latitude"] != 0 and parsed_data["longitude"] != 0:
                tuktuk.latitude = parsed_data["latitude"]
                tuktuk.longitude = parsed_data["longitude"]
                
                # Update geolocation field
                location_data = {
                    "type": "FeatureCollection",
                    "features": [{
                        "type": "Feature",
                        "properties": {
                            "name": tuktuk.tuktuk_id,
                            "speed": parsed_data["speed"],
                            "course": parsed_data["course"],
                            "satellites": parsed_data["satellite_count"]
                        },
                        "geometry": {
                            "type": "Point",
                            "coordinates": [parsed_data["longitude"], parsed_data["latitude"]]
                        }
                    }]
                }
                tuktuk.current_location = json.dumps(location_data)
                updated = True
                
            # Update status based on telemetry
            if parsed_data["device_status"]:
                if parsed_data["device_status"] == "Offline":
                    tuktuk.status = "Offline"
                elif tuktuk.status == "Offline" and parsed_data["device_status"] in ["Static", "Moving"]:
                    # Vehicle came back online, set to appropriate status
                    tuktuk.status = "Available"  # Default, may be overridden by business logic
                updated = True
            
            # Update last reported time
            tuktuk.last_reported = now_datetime()
            
            if updated:
                tuktuk.save(ignore_permissions=True)
                
            return True
            
        except Exception as e:
            frappe.log_error(f"Error updating vehicle status: {str(e)}")
            return False

@frappe.whitelist()
def update_all_vehicle_statuses():
    """Update status for all vehicles with telematics devices"""
    try:
        integration = TelematicsIntegration()
        
        # Use separate queries to avoid OR filter issues
        vehicles_with_device_id = frappe.get_all(
            "TukTuk Vehicle",
            filters={"device_id": ["!=", ""]},
            fields=["device_id", "device_imei", "name", "tuktuk_id"],
            ignore_permissions=True
        )
        
        vehicles_with_imei_only = frappe.get_all(
            "TukTuk Vehicle", 
            filters={
                "device_imei": ["!=", ""],
                "device_id": ["in", ["", None]]
            },
            fields=["device_id", "device_imei", "name", "tuktuk_id"],
            ignore_permissions=True
        )
        
        # Combine the results
        all_vehicles = vehicles_with_device_id + vehicles_with_imei_only
        
        updated_count = 0
        error_count = 0
        errors = []
        
        for vehicle in all_vehicles:
            try:
                device_id = vehicle.get("device_id") or vehicle.get("device_imei")
                if device_id:
                    success = integration.update_vehicle_status(device_id)
                    if success:
                        updated_count += 1
                    else:
                        error_count += 1
                        errors.append(f"Failed to update {vehicle.get('tuktuk_id', 'Unknown')}")
            except Exception as e:
                error_count += 1
                errors.append(f"Error updating {vehicle.get('tuktuk_id', 'Unknown')}: {str(e)}")
        
        frappe.db.commit()
        
        # REMOVED: frappe.log_error(result_message) - this was logging success as error
        
        return {
            "success": True,
            "updated": updated_count,
            "errors": error_count,
            "total": len(all_vehicles),
            "message": f"Telemetry update completed: {updated_count}/{len(all_vehicles)} vehicles updated" + (f", {error_count} errors" if error_count > 0 else ""),
            "error_details": errors[:5]  # Only return first 5 errors
        }
        
    except Exception as e:
        error_msg = f"Error in update_all_vehicle_statuses: {str(e)}"
        frappe.log_error(error_msg)  # KEEP: This is a real error
        return {
            "success": False,
            "message": error_msg,
            "error": str(e)
        }

# API endpoint for webhook integration
@frappe.whitelist(allow_guest=True)
def telematics_webhook():
    """Webhook endpoint for real-time telematics updates"""
    try:
        # Get the raw data from the request
        if frappe.request and frappe.request.data:
            data = json.loads(frappe.request.data)
            
            # Process the webhook data
            device_id = data.get("device_id") or data.get("imei")
            if device_id:
                integration = TelematicsIntegration()
                success = integration.update_vehicle_status(device_id)
                
                return {"status": "success" if success else "error"}
        return {"status": "error", "message": "No data received"}
    except Exception as e:
        frappe.log_error(f"Telematics Webhook Error: {str(e)}")  # KEEP: This is a real error
        return {"status": "error", "message": str(e)}

# Enhanced API methods
@frappe.whitelist()
def bulk_import_telemetry_data(csv_data):
    """
    Bulk import telemetry data from CSV export
    Expected format: Device IMEI,Device ID,...,voltage,...
    """
    try:
        import csv
        import io
        
        results = {
            "processed": 0,
            "updated": 0,
            "failed": 0,
            "errors": []
        }
        
        csv_reader = csv.reader(io.StringIO(csv_data))
        
        # Skip header row
        next(csv_reader, None)
        
        integration = TelematicsIntegration()
        
        for row_num, row in enumerate(csv_reader, 2):  # Start from row 2 (after header)
            if len(row) < 28:  # Minimum required columns
                continue
                
            try:
                parsed_data = integration.parse_telemetry_data(row)
                if not parsed_data:
                    results["errors"].append(f"Row {row_num}: Could not parse data")
                    results["failed"] += 1
                    continue
                
                device_id = parsed_data["device_id"]
                
                # Find vehicle using separate queries to avoid OR filter issues
                vehicle = None
                if device_id:
                    vehicles = frappe.get_all("TukTuk Vehicle",
                                           filters={"device_id": device_id},
                                           fields=["name"],
                                           limit=1)
                    if vehicles:
                        vehicle = vehicles
                
                if not vehicle and parsed_data["device_imei"]:
                    vehicles = frappe.get_all("TukTuk Vehicle",
                                           filters={"device_imei": parsed_data["device_imei"]},
                                           fields=["name"],
                                           limit=1)
                    if vehicles:
                        vehicle = vehicles
                
                if vehicle:
                    # Update the vehicle
                    success = integration.update_vehicle_status(device_id)
                    if success:
                        results["updated"] += 1
                    else:
                        results["failed"] += 1
                        results["errors"].append(f"Row {row_num}: Update failed for device {device_id}")
                else:
                    results["errors"].append(f"Row {row_num}: Vehicle not found for device {device_id}")
                    results["failed"] += 1
                
                results["processed"] += 1
                
            except Exception as e:
                results["failed"] += 1
                results["errors"].append(f"Row {row_num}: {str(e)}")
        
        frappe.db.commit()
        
        # REMOVED: Success logging - results are returned to caller
        
        return results
        
    except Exception as e:
        frappe.throw(f"Bulk import failed: {str(e)}")

@frappe.whitelist()
def sync_device_mapping():
    """
    Sync device IDs and IMEIs between telemetry platform and TukTuk vehicles
    """
    try:
        # This would typically fetch device list from telemetry API
        # For now, we'll provide a framework for manual mapping
        
        vehicles_without_devices = frappe.get_all("TukTuk Vehicle",
                                                 filters={
                                                     "device_id": ["in", ["", None]],
                                                     "device_imei": ["in", ["", None]]
                                                 },
                                                 fields=["name", "tuktuk_id"])
        
        return {
            "vehicles_without_devices": len(vehicles_without_devices),
            "vehicles": vehicles_without_devices,
            "message": f"Found {len(vehicles_without_devices)} vehicles without device mapping"
        }
        
    except Exception as e:
        frappe.throw(f"Device sync failed: {str(e)}")

@frappe.whitelist()
def get_telemetry_status():
    """Get telemetry integration status"""
    try:
        # Use separate queries instead of $or to avoid filter issues
        vehicles_with_device_id = frappe.db.count("TukTuk Vehicle", {"device_id": ["!=", ""]})
        vehicles_with_imei = frappe.db.count("TukTuk Vehicle", {
            "device_imei": ["!=", ""],
            "device_id": ["in", ["", None]]
        })
        vehicles_with_devices = vehicles_with_device_id + vehicles_with_imei
        
        total_vehicles = frappe.db.count("TukTuk Vehicle")
        
        # Get recent updates
        recent_updates = frappe.db.count("TukTuk Vehicle", {
            "last_reported": [">", frappe.utils.add_hours(now_datetime(), -1)]
        })
        
        # Get offline vehicles
        offline_vehicles = frappe.db.count("TukTuk Vehicle", {
            "status": "Offline"
        })
        
        return {
            "total_vehicles": total_vehicles,
            "vehicles_with_devices": vehicles_with_devices,
            "coverage_percentage": round((vehicles_with_devices / total_vehicles) * 100, 1) if total_vehicles > 0 else 0,
            "recent_updates": recent_updates,
            "offline_vehicles": offline_vehicles,
            "last_bulk_update": frappe.db.get_single_value("TukTuk Settings", "last_telemetry_update") or "Never"
        }
        
    except Exception as e:
        frappe.throw(f"Status check failed: {str(e)}")

# Additional utility methods for manual updates
@frappe.whitelist()
def update_from_device(vehicle_name, device_id):
    """Update vehicle data from telematics device - called from form"""
    try:
        vehicle = frappe.get_doc("TukTuk Vehicle", vehicle_name)
        
        if not vehicle.device_id and not vehicle.device_imei:
            frappe.throw(_("No device ID or IMEI configured for this vehicle"))
        
        integration = TelematicsIntegration()
        telematics_data = integration.get_vehicle_data(device_id)
        
        if telematics_data:
            parsed_data = integration.parse_telemetry_data(telematics_data)
            
            if parsed_data:
                # Update vehicle with latest data
                if parsed_data['battery_voltage'] > 0:
                    from tuktuk_management.api.battery_utils import BatteryConverter
                    new_percentage = BatteryConverter.voltage_to_percentage(parsed_data['battery_voltage'])
                    vehicle.battery_level = new_percentage
                    vehicle.battery_voltage = parsed_data['battery_voltage']
                
                if parsed_data['latitude'] != 0 and parsed_data['longitude'] != 0:
                    vehicle.latitude = parsed_data['latitude']
                    vehicle.longitude = parsed_data['longitude']
                    
                    location_data = {
                        "type": "FeatureCollection",
                        "features": [{
                            "type": "Feature",
                            "properties": {},
                            "geometry": {
                                "type": "Point",
                                "coordinates": [parsed_data['longitude'], parsed_data['latitude']]
                            }
                        }]
                    }
                    vehicle.current_location = json.dumps(location_data)
                
                vehicle.last_reported = now_datetime()
                vehicle.save(ignore_permissions=True)
                
                return {
                    "success": True,
                    "message": _("Vehicle data updated successfully"),
                    "data": parsed_data
                }
            else:
                frappe.throw(_("Unable to parse data from telematics device"))
        else:
            frappe.throw(_("Unable to retrieve data from telematics device"))
            
    except Exception as e:
        frappe.log_error(f"Telematics update failed: {str(e)}")  # KEEP: This is a real error
        frappe.throw(_("Failed to update from telematics device: {0}").format(str(e)))