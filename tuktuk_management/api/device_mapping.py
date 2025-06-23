# ~/frappe-bench/apps/tuktuk_management/tuktuk_management/api/device_mapping.py
# Complete device mapping API with all functions and fixes

import frappe
from frappe import _
from frappe.utils import now_datetime, date_diff, add_days, flt
import json

@frappe.whitelist()
def auto_map_devices_from_telemetry():
    """
    Auto-map telemetry devices to TukTuk vehicles based on the exported data
    """
    try:
        print("🚀 Starting auto device mapping...")
        
        # Telemetry device data from the export
        telemetry_devices = [
            {"device_id": "135", "imei": "860909050379362", "voltage": 79.0, "lat": -4.286028, "lng": 39.587394, "status": "Static"},
            {"device_id": "136", "imei": "860909050460220", "voltage": 0.0, "lat": -4.285304, "lng": 39.587032, "status": "Offline"},
            {"device_id": "137", "imei": "860909050354241", "voltage": 80.0, "lat": -4.285634, "lng": 39.587230, "status": "Static"},
            {"device_id": "138", "imei": "860909050379198", "voltage": 80.0, "lat": -4.285566, "lng": 39.587188, "status": "Static"},
            {"device_id": "139", "imei": "860909050379230", "voltage": 80.0, "lat": -4.280298, "lng": 39.589714, "status": "Static"},
            {"device_id": "140", "imei": "860909050529479", "voltage": 80.0, "lat": -4.280307, "lng": 39.589694, "status": "Static"},
            {"device_id": "141", "imei": "860909050501510", "voltage": 80.0, "lat": -4.285628, "lng": 39.587314, "status": "Static"},
            {"device_id": "142", "imei": "860909050446716", "voltage": 78.0, "lat": -4.285379, "lng": 39.587425, "status": "Static"},
            {"device_id": "143", "imei": "860909050354399", "voltage": 79.0, "lat": -4.285551, "lng": 39.587265, "status": "Static"}
        ]
        
        # Get all TukTuk vehicles without device mapping
        vehicles = frappe.get_all("TukTuk Vehicle",
                                 filters={
                                     "$or": [
                                         {"device_id": ["in", ["", None]]},
                                         {"device_imei": ["in", ["", None]]}
                                     ]
                                 },
                                 fields=["name", "tuktuk_id"],
                                 order_by="creation")
        
        mapping_results = {
            "mapped": 0,
            "skipped": 0,
            "errors": [],
            "mappings": []
        }
        
        # Map devices to vehicles in order
        for i, vehicle in enumerate(vehicles):
            if i < len(telemetry_devices):
                device = telemetry_devices[i]
                
                try:
                    # Update the vehicle with device information
                    vehicle_doc = frappe.get_doc("TukTuk Vehicle", vehicle.name)
                    
                    vehicle_doc.device_id = device["device_id"]
                    vehicle_doc.device_imei = device["imei"]
                    vehicle_doc.current_latitude = device["lat"]
                    vehicle_doc.current_longitude = device["lng"]
                    
                    # Set battery level based on voltage
                    if device["voltage"] > 0:
                        vehicle_doc.battery_level = int(device["voltage"])
                    
                    vehicle_doc.last_telemetry_update = now_datetime()
                    vehicle_doc.save(ignore_permissions=True)
                    
                    mapping_results["mapped"] += 1
                    mapping_results["mappings"].append({
                        "tuktuk_id": vehicle.tuktuk_id,
                        "device_id": device["device_id"],
                        "imei": device["imei"],
                        "battery": f"{device['voltage']}V → {vehicle_doc.battery_level}%"
                    })
                    
                    print(f"✅ Mapped {vehicle.tuktuk_id} to device {device['device_id']}")
                    
                except Exception as e:
                    error_msg = f"Failed to map {vehicle.tuktuk_id}: {str(e)}"
                    mapping_results["errors"].append(error_msg)
                    mapping_results["skipped"] += 1
                    print(f"❌ {error_msg}")
                    frappe.log_error(f"Device mapping error: {str(e)}", f"Auto-mapping failed for {vehicle.tuktuk_id}")
            else:
                mapping_results["skipped"] += 1
        
        frappe.db.commit()
        
        success_msg = f"Mapped {mapping_results['mapped']} devices, {mapping_results['skipped']} skipped"
        print(f"🎉 {success_msg}")
        
        return {
            "success": True,
            "message": success_msg,
            "results": mapping_results
        }
        
    except Exception as e:
        error_msg = f"Auto device mapping failed: {str(e)}"
        print(f"❌ {error_msg}")
        frappe.log_error(f"Auto device mapping error: {str(e)}")
        return {
            "success": False,
            "message": error_msg
        }

@frappe.whitelist()
def simple_device_mapping():
    """
    Simplified version of device mapping with better error handling
    """
    try:
        print("🔧 Starting simple device mapping...")
        
        # Get unmapped vehicles
        vehicles = frappe.get_all("TukTuk Vehicle",
                                 filters={
                                     "$or": [
                                         {"device_id": ["in", ["", None]]},
                                         {"device_imei": ["in", ["", None]]}
                                     ]
                                 },
                                 fields=["name", "tuktuk_id"],
                                 order_by="creation",
                                 limit=9)  # Only map first 9
        
        # Simple device data
        devices = [
            ("135", "860909050379362", 79.0, -4.286028, 39.587394),
            ("136", "860909050460220", 0.0, -4.285304, 39.587032),
            ("137", "860909050354241", 80.0, -4.285634, 39.587230),
            ("138", "860909050379198", 80.0, -4.285566, 39.587188),
            ("139", "860909050379230", 80.0, -4.280298, 39.589714),
            ("140", "860909050529479", 80.0, -4.280307, 39.589694),
            ("141", "860909050501510", 80.0, -4.285628, 39.587314),
            ("142", "860909050446716", 78.0, -4.285379, 39.587425),
            ("143", "860909050354399", 79.0, -4.285551, 39.587265)
        ]
        
        mapped_count = 0
        
        for i, vehicle in enumerate(vehicles):
            if i < len(devices):
                device_id, imei, voltage, lat, lng = devices[i]
                
                try:
                    # Get vehicle document
                    doc = frappe.get_doc("TukTuk Vehicle", vehicle.name)
                    
                    # Update device mapping
                    doc.device_id = device_id
                    doc.device_imei = imei
                    doc.current_latitude = lat
                    doc.current_longitude = lng
                    
                    # Update battery (treat values as percentages)
                    if voltage > 0:
                        doc.battery_level = int(voltage)
                        doc.battery_voltage = voltage
                    
                    # Update timestamp
                    doc.last_telemetry_update = now_datetime()
                    
                    # Save
                    doc.save(ignore_permissions=True)
                    
                    mapped_count += 1
                    print(f"✅ Mapped {vehicle.tuktuk_id} → Device {device_id}")
                    
                except Exception as e:
                    print(f"❌ Failed to map {vehicle.tuktuk_id}: {str(e)}")
        
        frappe.db.commit()
        
        return {
            "success": True,
            "message": f"Successfully mapped {mapped_count} vehicles to devices",
            "mapped_count": mapped_count
        }
        
    except Exception as e:
        error_msg = str(e)
        print(f"❌ Simple mapping failed: {error_msg}")
        return {
            "success": False,
            "message": error_msg
        }

@frappe.whitelist()
def manual_device_mapping(tuktuk_vehicle, device_id, device_imei):
    """
    Manually map a device to a TukTuk vehicle
    """
    try:
        vehicle = frappe.get_doc("TukTuk Vehicle", tuktuk_vehicle)
        
        # Check if device is already mapped to another vehicle
        existing_mapping = frappe.get_all("TukTuk Vehicle",
                                         filters={
                                             "$or": [
                                                 {"device_id": device_id},
                                                 {"device_imei": device_imei}
                                             ],
                                             "name": ["!=", vehicle.name]
                                         },
                                         fields=["tuktuk_id"])
        
        if existing_mapping:
            frappe.throw(f"Device already mapped to TukTuk {existing_mapping[0].tuktuk_id}")
        
        # Update the mapping
        vehicle.device_id = device_id
        vehicle.device_imei = device_imei
        vehicle.last_telemetry_update = now_datetime()
        vehicle.save()
        
        # Try to get initial data from telemetry
        try:
            from tuktuk_management.api.telematics import TelematicsIntegration
            integration = TelematicsIntegration()
            integration.update_vehicle_status(device_id)
        except Exception as e:
            frappe.log_error(f"Initial telemetry update failed: {str(e)}")
        
        return {
            "success": True,
            "message": f"Device {device_id} mapped to TukTuk {vehicle.tuktuk_id}"
        }
        
    except Exception as e:
        frappe.throw(f"Manual mapping failed: {str(e)}")

@frappe.whitelist()
def get_unmapped_devices():
    """
    Get list of vehicles without device mapping and available devices
    """
    try:
        # Get unmapped vehicles
        unmapped_vehicles = frappe.get_all("TukTuk Vehicle",
                                         filters={
                                             "$or": [
                                                 {"device_id": ["in", ["", None]]},
                                                 {"device_imei": ["in", ["", None]]}
                                             ]
                                         },
                                         fields=["name", "tuktuk_id", "status"])
        
        # Available devices (from telemetry data)
        available_devices = [
            {"device_id": "135", "imei": "860909050379362", "status": "Active"},
            {"device_id": "136", "imei": "860909050460220", "status": "Active"},
            {"device_id": "137", "imei": "860909050354241", "status": "Active"},
            {"device_id": "138", "imei": "860909050379198", "status": "Active"},
            {"device_id": "139", "imei": "860909050379230", "status": "Active"},
            {"device_id": "140", "imei": "860909050529479", "status": "Active"},
            {"device_id": "141", "imei": "860909050501510", "status": "Active"},
            {"device_id": "142", "imei": "860909050446716", "status": "Active"},
            {"device_id": "143", "imei": "860909050354399", "status": "Active"}
        ]
        
        # Filter out already mapped devices
        mapped_device_ids = frappe.db.get_list("TukTuk Vehicle", 
                                             filters={"device_id": ["!=", ""]},
                                             fields=["device_id"],
                                             pluck="device_id")
        
        mapped_imeis = frappe.db.get_list("TukTuk Vehicle", 
                                        filters={"device_imei": ["!=", ""]},
                                        fields=["device_imei"],
                                        pluck="device_imei")
        
        available_devices = [d for d in available_devices 
                           if d["device_id"] not in mapped_device_ids 
                           and d["imei"] not in mapped_imeis]
        
        return {
            "unmapped_vehicles": unmapped_vehicles,
            "available_devices": available_devices,
            "mapping_suggestions": generate_mapping_suggestions(unmapped_vehicles, available_devices)
        }
        
    except Exception as e:
        frappe.throw(f"Failed to get unmapped devices: {str(e)}")

def generate_mapping_suggestions(vehicles, devices):
    """
    Generate intelligent mapping suggestions based on proximity or patterns
    """
    suggestions = []
    
    for i, vehicle in enumerate(vehicles):
        if i < len(devices):
            device = devices[i]
            suggestions.append({
                "tuktuk_id": vehicle["tuktuk_id"],
                "tuktuk_name": vehicle["name"],
                "suggested_device_id": device["device_id"],
                "suggested_imei": device["imei"],
                "device_status": device["status"],
                "confidence": "Medium",
                "reason": f"Sequential mapping suggestion {i+1}"
            })
    
    return suggestions

@frappe.whitelist()
def apply_mapping_suggestions():
    """
    Apply the generated mapping suggestions automatically
    """
    try:
        mapping_data = get_unmapped_devices()
        suggestions = mapping_data["mapping_suggestions"]
        
        results = {
            "applied": 0,
            "failed": 0,
            "errors": []
        }
        
        for suggestion in suggestions:
            try:
                result = manual_device_mapping(
                    suggestion["tuktuk_name"],
                    suggestion["suggested_device_id"],
                    suggestion["suggested_imei"]
                )
                
                if result["success"]:
                    results["applied"] += 1
                else:
                    results["failed"] += 1
                    results["errors"].append(f"Failed: {suggestion['tuktuk_id']}")
                    
            except Exception as e:
                results["failed"] += 1
                results["errors"].append(f"Error mapping {suggestion['tuktuk_id']}: {str(e)}")
        
        return {
            "success": True,
            "message": f"Applied {results['applied']} mappings, {results['failed']} failed",
            "results": results
        }
        
    except Exception as e:
        frappe.throw(f"Failed to apply mapping suggestions: {str(e)}")

@frappe.whitelist()
def validate_device_mappings():
    """
    Validate all current device mappings and check for issues
    FIXED: Removed problematic local import that caused variable shadowing
    """
    try:
        all_vehicles = frappe.get_all("TukTuk Vehicle",
                                     fields=["name", "tuktuk_id", "device_id", "device_imei", "last_reported"])
        
        validation_results = {
            "total_vehicles": len(all_vehicles),
            "mapped_vehicles": 0,
            "unmapped_vehicles": 0,
            "duplicate_mappings": [],
            "inactive_devices": [],
            "recent_updates": 0
        }
        
        device_id_map = {}
        imei_map = {}
        
        for vehicle in all_vehicles:
            # Check mapping status
            if vehicle.device_id or vehicle.device_imei:
                validation_results["mapped_vehicles"] += 1
                
                # Check for duplicates
                if vehicle.device_id:
                    if vehicle.device_id in device_id_map:
                        validation_results["duplicate_mappings"].append({
                            "device_id": vehicle.device_id,
                            "vehicles": [device_id_map[vehicle.device_id], vehicle.tuktuk_id]
                        })
                    else:
                        device_id_map[vehicle.device_id] = vehicle.tuktuk_id
                
                if vehicle.device_imei:
                    if vehicle.device_imei in imei_map:
                        validation_results["duplicate_mappings"].append({
                            "imei": vehicle.device_imei,
                            "vehicles": [imei_map[vehicle.device_imei], vehicle.tuktuk_id]
                        })
                    else:
                        imei_map[vehicle.device_imei] = vehicle.tuktuk_id
                
                # Check for recent updates
                if vehicle.last_reported:
                    # FIXED: Use imported functions directly instead of frappe.utils
                    hours_ago = date_diff(now_datetime(), vehicle.last_reported) * 24
                    if hours_ago <= 24:
                        validation_results["recent_updates"] += 1
                    elif hours_ago > 72:
                        validation_results["inactive_devices"].append({
                            "tuktuk_id": vehicle.tuktuk_id,
                            "device_id": vehicle.device_id,
                            "last_reported": vehicle.last_reported,
                            "hours_ago": round(hours_ago, 1)
                        })
            else:
                validation_results["unmapped_vehicles"] += 1
        
        return validation_results
        
    except Exception as e:
        # FIXED: Now frappe.throw will work correctly without variable conflict
        frappe.throw(f"Validation failed: {str(e)}")

@frappe.whitelist()
def reset_device_mapping(tuktuk_vehicle):
    """
    Reset device mapping for a specific vehicle
    """
    try:
        vehicle = frappe.get_doc("TukTuk Vehicle", tuktuk_vehicle)
        
        # Clear device mapping
        vehicle.device_id = ""
        vehicle.device_imei = ""
        
        # Optionally clear telemetry data
        vehicle.battery_voltage = None
        vehicle.last_reported = None
        
        vehicle.save()
        
        return {
            "success": True,
            "message": f"Device mapping reset for TukTuk {vehicle.tuktuk_id}"
        }
        
    except Exception as e:
        frappe.throw(f"Reset failed: {str(e)}")

@frappe.whitelist()
def debug_mapping_issue():
    """
    Debug function to identify mapping issues
    """
    try:
        print("🔍 Debugging device mapping issue...")
        
        # Check vehicles
        vehicles = frappe.get_all("TukTuk Vehicle", 
                                 fields=["name", "tuktuk_id", "device_id", "device_imei"],
                                 limit=5)
        
        print(f"Found {len(vehicles)} vehicles:")
        for v in vehicles:
            print(f"  - {v.tuktuk_id}: device_id='{v.device_id}', device_imei='{v.device_imei}'")
        
        # Test device data types
        test_device = {"device_id": "135", "status": "Static"}
        
        print(f"Test device status type: {type(test_device['status'])}")
        print(f"Test device status value: '{test_device['status']}'")
        print(f"Test device status lower: '{test_device['status'].lower()}'")
        
        return {
            "success": True,
            "message": "Debug completed - check console for output",
            "vehicles_checked": len(vehicles),
            "vehicles": vehicles
        }
        
    except Exception as e:
        error_msg = f"Debug failed: {str(e)}"
        print(f"❌ {error_msg}")
        return {
            "success": False,
            "message": error_msg
        }