# ~/frappe-bench/apps/tuktuk_management/tuktuk_management/api/csv_telemetry.py

import frappe
import csv
import io
from frappe import _
from frappe.utils import now_datetime, flt, cstr
from datetime import datetime
import json

@frappe.whitelist()
def upload_telemetry_csv_data(csv_content, mapping_type="auto"):
    """
    Upload and process telemetry data from CSV
    
    Args:
        csv_content: CSV file content as string
        mapping_type: "auto", "device_id", "imei", "tuktuk_id"
    
    Returns:
        Dictionary with processing results
    """
    try:
        results = {
            "total_rows": 0,
            "processed": 0,
            "updated": 0,
            "failed": 0,
            "skipped": 0,
            "errors": [],
            "warnings": [],
            "success_details": []
        }
        
        # Parse CSV content
        csv_reader = csv.reader(io.StringIO(csv_content))
        
        # Get header row
        headers = []
        try:
            headers = next(csv_reader)
            headers = [h.strip().lower() for h in headers]
        except StopIteration:
            frappe.throw(_("CSV file is empty or invalid"))
        
        # Detect CSV format
        csv_format = detect_csv_format(headers)
        if not csv_format:
            frappe.throw(_("Unrecognized CSV format. Please check the column headers."))
        
        results["csv_format"] = csv_format
        results["headers"] = headers
        
        # Process data rows
        for row_num, row in enumerate(csv_reader, start=2):  # Start from row 2
            results["total_rows"] += 1
            
            if not row or len(row) < 3:  # Skip empty or too short rows
                results["skipped"] += 1
                continue
            
            try:
                # Parse row based on detected format
                parsed_data = parse_csv_row(row, headers, csv_format)
                
                if not parsed_data:
                    results["failed"] += 1
                    results["errors"].append(f"Row {row_num}: Could not parse data")
                    continue
                
                # Find and update vehicle
                update_result = update_vehicle_from_csv_data(parsed_data, mapping_type)
                
                if update_result["success"]:
                    results["updated"] += 1
                    results["success_details"].append({
                        "row": row_num,
                        "tuktuk_id": update_result.get("tuktuk_id"),
                        "device_id": update_result.get("device_id"),
                        "updates": update_result.get("updates", [])
                    })
                else:
                    results["failed"] += 1
                    results["errors"].append(f"Row {row_num}: {update_result.get('error', 'Update failed')}")
                
                results["processed"] += 1
                
            except Exception as e:
                results["failed"] += 1
                results["errors"].append(f"Row {row_num}: {str(e)}")
        
        # Commit changes
        frappe.db.commit()
        
        return results
        
    except Exception as e:
        frappe.log_error(f"CSV telemetry upload failed: {str(e)}")
        frappe.throw(_("CSV upload failed: {0}").format(str(e)))

def detect_csv_format(headers):
    """
    Detect the CSV format based on headers
    Returns format type and column mappings
    """
    # Format 1: Telemetry export format
    telemetry_indicators = [
        'device imei', 'device id', 'latitude', 'longitude', 'voltage', 
        'speed', 'course', 'satellite', 'device status'
    ]
    
    # Format 2: Simple battery update format
    battery_indicators = ['tuktuk_id', 'battery', 'voltage']
    
    # Format 3: Location update format
    location_indicators = ['tuktuk_id', 'latitude', 'longitude', 'location']
    
    # Format 4: Complete vehicle data format
    vehicle_indicators = ['tuktuk_id', 'device_id', 'imei', 'battery', 'lat', 'lng']
    
    # Check for telemetry export format
    telemetry_matches = sum(1 for indicator in telemetry_indicators 
                           if any(indicator in header for header in headers))
    
    if telemetry_matches >= 5:
        return {
            "type": "telemetry_export",
            "mappings": map_telemetry_export_columns(headers)
        }
    
    # Check for battery update format
    battery_matches = sum(1 for indicator in battery_indicators 
                         if any(indicator in header for header in headers))
    
    if battery_matches >= 2:
        return {
            "type": "battery_update",
            "mappings": map_battery_columns(headers)
        }
    
    # Check for location update format
    location_matches = sum(1 for indicator in location_indicators 
                          if any(indicator in header for header in headers))
    
    if location_matches >= 3:
        return {
            "type": "location_update",
            "mappings": map_location_columns(headers)
        }
    
    # Check for vehicle data format
    vehicle_matches = sum(1 for indicator in vehicle_indicators 
                         if any(indicator in header for header in headers))
    
    if vehicle_matches >= 4:
        return {
            "type": "vehicle_data",
            "mappings": map_vehicle_columns(headers)
        }
    
    return None

def map_telemetry_export_columns(headers):
    """Map telemetry export CSV columns to data fields"""
    mappings = {}
    
    for i, header in enumerate(headers):
        header_lower = header.lower()
        
        if 'imei' in header_lower:
            mappings['imei'] = i
        elif 'device id' in header_lower or 'device_id' in header_lower:
            mappings['device_id'] = i
        elif 'latitude' in header_lower or 'lat' in header_lower:
            mappings['latitude'] = i
        elif 'longitude' in header_lower or 'lng' in header_lower or 'lon' in header_lower:
            mappings['longitude'] = i
        elif 'voltage' in header_lower or 'battery' in header_lower:
            mappings['voltage'] = i
        elif 'speed' in header_lower:
            mappings['speed'] = i
        elif 'course' in header_lower or 'direction' in header_lower:
            mappings['course'] = i
        elif 'satellite' in header_lower:
            mappings['satellite'] = i
        elif 'status' in header_lower:
            mappings['status'] = i
        elif 'time' in header_lower or 'timestamp' in header_lower:
            mappings['timestamp'] = i
    
    return mappings

def map_battery_columns(headers):
    """Map battery update CSV columns"""
    mappings = {}
    
    for i, header in enumerate(headers):
        header_lower = header.lower()
        
        if 'tuktuk' in header_lower or 'vehicle' in header_lower:
            mappings['tuktuk_id'] = i
        elif 'battery' in header_lower or 'voltage' in header_lower:
            mappings['battery'] = i
        elif 'percentage' in header_lower or '%' in header_lower:
            mappings['percentage'] = i
        elif 'is_voltage' in header_lower or 'type' in header_lower:
            mappings['is_voltage'] = i
    
    return mappings

def map_location_columns(headers):
    """Map location update CSV columns"""
    mappings = {}
    
    for i, header in enumerate(headers):
        header_lower = header.lower()
        
        if 'tuktuk' in header_lower or 'vehicle' in header_lower:
            mappings['tuktuk_id'] = i
        elif 'latitude' in header_lower or 'lat' in header_lower:
            mappings['latitude'] = i
        elif 'longitude' in header_lower or 'lng' in header_lower:
            mappings['longitude'] = i
        elif 'address' in header_lower or 'location' in header_lower:
            mappings['address'] = i
        elif 'time' in header_lower or 'timestamp' in header_lower:
            mappings['timestamp'] = i
    
    return mappings

def map_vehicle_columns(headers):
    """Map complete vehicle data CSV columns"""
    mappings = {}
    
    for i, header in enumerate(headers):
        header_lower = header.lower()
        
        if 'tuktuk' in header_lower:
            mappings['tuktuk_id'] = i
        elif 'device_id' in header_lower:
            mappings['device_id'] = i
        elif 'imei' in header_lower:
            mappings['imei'] = i
        elif 'battery' in header_lower or 'voltage' in header_lower:
            mappings['battery'] = i
        elif 'latitude' in header_lower or 'lat' in header_lower:
            mappings['latitude'] = i
        elif 'longitude' in header_lower or 'lng' in header_lower:
            mappings['longitude'] = i
        elif 'speed' in header_lower:
            mappings['speed'] = i
        elif 'status' in header_lower:
            mappings['status'] = i
    
    return mappings

def parse_csv_row(row, headers, csv_format):
    """Parse a CSV row based on the detected format"""
    try:
        mappings = csv_format["mappings"]
        format_type = csv_format["type"]
        
        parsed = {
            "format_type": format_type,
            "raw_row": row
        }
        
        # Parse based on format type
        if format_type == "telemetry_export":
            if 'imei' in mappings and mappings['imei'] < len(row):
                parsed['imei'] = cstr(row[mappings['imei']]).strip()
            if 'device_id' in mappings and mappings['device_id'] < len(row):
                parsed['device_id'] = cstr(row[mappings['device_id']]).strip()
            if 'latitude' in mappings and mappings['latitude'] < len(row):
                parsed['latitude'] = flt(row[mappings['latitude']])
            if 'longitude' in mappings and mappings['longitude'] < len(row):
                parsed['longitude'] = flt(row[mappings['longitude']])
            if 'voltage' in mappings and mappings['voltage'] < len(row):
                parsed['voltage'] = flt(row[mappings['voltage']])
            if 'speed' in mappings and mappings['speed'] < len(row):
                parsed['speed'] = flt(row[mappings['speed']])
            if 'course' in mappings and mappings['course'] < len(row):
                parsed['course'] = flt(row[mappings['course']])
            if 'satellite' in mappings and mappings['satellite'] < len(row):
                parsed['satellite'] = flt(row[mappings['satellite']])
            if 'status' in mappings and mappings['status'] < len(row):
                parsed['status'] = cstr(row[mappings['status']]).strip()
                
        elif format_type == "battery_update":
            if 'tuktuk_id' in mappings and mappings['tuktuk_id'] < len(row):
                parsed['tuktuk_id'] = cstr(row[mappings['tuktuk_id']]).strip()
            if 'battery' in mappings and mappings['battery'] < len(row):
                parsed['battery'] = flt(row[mappings['battery']])
            if 'percentage' in mappings and mappings['percentage'] < len(row):
                parsed['percentage'] = flt(row[mappings['percentage']])
            if 'is_voltage' in mappings and mappings['is_voltage'] < len(row):
                parsed['is_voltage'] = cstr(row[mappings['is_voltage']]).lower() in ['true', '1', 'yes', 'voltage']
                
        elif format_type == "location_update":
            if 'tuktuk_id' in mappings and mappings['tuktuk_id'] < len(row):
                parsed['tuktuk_id'] = cstr(row[mappings['tuktuk_id']]).strip()
            if 'latitude' in mappings and mappings['latitude'] < len(row):
                parsed['latitude'] = flt(row[mappings['latitude']])
            if 'longitude' in mappings and mappings['longitude'] < len(row):
                parsed['longitude'] = flt(row[mappings['longitude']])
            if 'address' in mappings and mappings['address'] < len(row):
                parsed['address'] = cstr(row[mappings['address']]).strip()
                
        elif format_type == "vehicle_data":
            if 'tuktuk_id' in mappings and mappings['tuktuk_id'] < len(row):
                parsed['tuktuk_id'] = cstr(row[mappings['tuktuk_id']]).strip()
            if 'device_id' in mappings and mappings['device_id'] < len(row):
                parsed['device_id'] = cstr(row[mappings['device_id']]).strip()
            if 'imei' in mappings and mappings['imei'] < len(row):
                parsed['imei'] = cstr(row[mappings['imei']]).strip()
            if 'battery' in mappings and mappings['battery'] < len(row):
                parsed['battery'] = flt(row[mappings['battery']])
            if 'latitude' in mappings and mappings['latitude'] < len(row):
                parsed['latitude'] = flt(row[mappings['latitude']])
            if 'longitude' in mappings and mappings['longitude'] < len(row):
                parsed['longitude'] = flt(row[mappings['longitude']])
            if 'speed' in mappings and mappings['speed'] < len(row):
                parsed['speed'] = flt(row[mappings['speed']])
            if 'status' in mappings and mappings['status'] < len(row):
                parsed['status'] = cstr(row[mappings['status']]).strip()
        
        return parsed
        
    except Exception as e:
        frappe.log_error(f"Error parsing CSV row: {str(e)}")
        return None

def update_vehicle_from_csv_data(parsed_data, mapping_type="auto"):
    """Update vehicle record from parsed CSV data"""
    try:
        # Find vehicle based on mapping type and available data
        vehicle = find_vehicle_for_update(parsed_data, mapping_type)
        
        if not vehicle:
            return {
                "success": False,
                "error": "Vehicle not found"
            }
        
        # Get vehicle document
        vehicle_doc = frappe.get_doc("TukTuk Vehicle", vehicle.name)
        updates = []
        
        # Update battery data
        if 'voltage' in parsed_data and parsed_data['voltage'] > 0:
            # Convert voltage to percentage if needed
            from tuktuk_management.api.battery_utils import BatteryConverter
            
            if parsed_data['voltage'] > 100:  # Assume it's voltage
                battery_percentage = BatteryConverter.voltage_to_percentage(parsed_data['voltage'])
                vehicle_doc.battery_voltage = parsed_data['voltage']
            else:  # Assume it's already percentage
                battery_percentage = parsed_data['voltage']
            
            vehicle_doc.battery_level = battery_percentage
            updates.append(f"Battery: {battery_percentage}%")
        
        elif 'battery' in parsed_data and parsed_data['battery'] > 0:
            # Handle battery field from other formats
            if 'is_voltage' in parsed_data and parsed_data['is_voltage']:
                from tuktuk_management.api.battery_utils import BatteryConverter
                battery_percentage = BatteryConverter.voltage_to_percentage(parsed_data['battery'])
                vehicle_doc.battery_voltage = parsed_data['battery']
            else:
                battery_percentage = parsed_data['battery']
            
            vehicle_doc.battery_level = battery_percentage
            updates.append(f"Battery: {battery_percentage}%")
        
        elif 'percentage' in parsed_data and parsed_data['percentage'] > 0:
            vehicle_doc.battery_level = parsed_data['percentage']
            updates.append(f"Battery: {parsed_data['percentage']}%")
        
        # Update location data
        if 'latitude' in parsed_data and 'longitude' in parsed_data:
            if parsed_data['latitude'] != 0 and parsed_data['longitude'] != 0:
                vehicle_doc.latitude = parsed_data['latitude']
                vehicle_doc.longitude = parsed_data['longitude']
                updates.append(f"Location: {parsed_data['latitude']}, {parsed_data['longitude']}")
                
                # Create location GeoJSON
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
                vehicle_doc.current_location = json.dumps(location_data)
        
        # Update device mapping if provided
        if 'device_id' in parsed_data and parsed_data['device_id']:
            if not vehicle_doc.device_id:
                vehicle_doc.device_id = parsed_data['device_id']
                updates.append(f"Device ID: {parsed_data['device_id']}")
        
        if 'imei' in parsed_data and parsed_data['imei']:
            if not vehicle_doc.device_imei:
                vehicle_doc.device_imei = parsed_data['imei']
                updates.append(f"IMEI: {parsed_data['imei']}")
        
        # Update other telemetry data
        if 'speed' in parsed_data:
            # You could add a speed field to track current speed
            updates.append(f"Speed: {parsed_data['speed']} km/h")
        
        if 'status' in parsed_data and parsed_data['status']:
            # Map device status to vehicle status if needed
            device_status_mapping = {
                'Static': 'Available',
                'Moving': 'Assigned',
                'Offline': 'Out of Service'
            }
            
            if parsed_data['status'] in device_status_mapping:
                new_status = device_status_mapping[parsed_data['status']]
                if vehicle_doc.status != new_status:
                    vehicle_doc.status = new_status
                    updates.append(f"Status: {new_status}")
        
        # Update timestamp
        vehicle_doc.last_reported = now_datetime()
        updates.append("Last reported updated")
        
        # Save vehicle
        vehicle_doc.save(ignore_permissions=True)
        
        return {
            "success": True,
            "tuktuk_id": vehicle_doc.tuktuk_id,
            "device_id": vehicle_doc.device_id,
            "updates": updates
        }
        
    except Exception as e:
        frappe.log_error(f"Error updating vehicle from CSV: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

def find_vehicle_for_update(parsed_data, mapping_type="auto"):
    """Find vehicle record for update based on available identifiers"""
    try:
        # Priority order for finding vehicles
        search_methods = []
        
        if mapping_type == "auto":
            # Try multiple methods in order of preference
            if 'tuktuk_id' in parsed_data and parsed_data['tuktuk_id']:
                search_methods.append(('tuktuk_id', parsed_data['tuktuk_id']))
            if 'device_id' in parsed_data and parsed_data['device_id']:
                search_methods.append(('device_id', parsed_data['device_id']))
            if 'imei' in parsed_data and parsed_data['imei']:
                search_methods.append(('device_imei', parsed_data['imei']))
        
        elif mapping_type == "tuktuk_id" and 'tuktuk_id' in parsed_data:
            search_methods.append(('tuktuk_id', parsed_data['tuktuk_id']))
        
        elif mapping_type == "device_id" and 'device_id' in parsed_data:
            search_methods.append(('device_id', parsed_data['device_id']))
        
        elif mapping_type == "imei" and 'imei' in parsed_data:
            search_methods.append(('device_imei', parsed_data['imei']))
        
        # Try each search method
        for field, value in search_methods:
            vehicles = frappe.get_all("TukTuk Vehicle",
                                    filters={field: value},
                                    fields=["name", "tuktuk_id"],
                                    limit=1)
            
            if vehicles:
                return vehicles[0]
        
        return None
        
    except Exception as e:
        frappe.log_error(f"Error finding vehicle: {str(e)}")
        return None

@frappe.whitelist()
def get_csv_upload_template(format_type="telemetry_export"):
    """Generate CSV template for uploads"""
    try:
        templates = {
            "telemetry_export": [
                "Device IMEI", "Device ID", "Vehicle Name", "Vehicle Type", "Plate Number",
                "Group Name", "Sub Group", "Driver Name", "Driver Phone", "Device Status",
                "Device Type", "SIM No", "Installation Date", "Expiry Date", "Longitude",
                "Latitude", "Speed", "Course", "Altitude", "Satellite", "GPS Signal Strength",
                "Last GPS Time", "AC Status", "Power Status", "GPS Status", "Last Online Time",
                "Is Car Go", "Voltage", "Status"
            ],
            "battery_update": [
                "TukTuk ID", "Battery Level", "Is Voltage", "Timestamp"
            ],
            "location_update": [
                "TukTuk ID", "Latitude", "Longitude", "Address", "Timestamp"
            ],
            "vehicle_data": [
                "TukTuk ID", "Device ID", "IMEI", "Battery Level", "Latitude", "Longitude", "Speed", "Status"
            ]
        }
        
        if format_type not in templates:
            format_type = "telemetry_export"
        
        return {
            "success": True,
            "headers": templates[format_type],
            "format_type": format_type
        }
        
    except Exception as e:
        frappe.throw(_("Failed to generate template: {0}").format(str(e)))

@frappe.whitelist()
def validate_csv_before_upload(csv_content):
    """Validate CSV content before processing"""
    try:
        # Parse CSV to check format
        csv_reader = csv.reader(io.StringIO(csv_content))
        headers = next(csv_reader, [])
        
        if not headers:
            return {
                "valid": False,
                "error": "CSV file is empty or has no headers"
            }
        
        # Detect format
        csv_format = detect_csv_format([h.strip().lower() for h in headers])
        
        if not csv_format:
            return {
                "valid": False,
                "error": "Unrecognized CSV format",
                "headers": headers
            }
        
        # Count rows
        row_count = sum(1 for row in csv_reader if row)
        
        return {
            "valid": True,
            "format": csv_format,
            "headers": headers,
            "row_count": row_count,
            "estimated_processing_time": row_count * 0.5  # seconds
        }
        
    except Exception as e:
        return {
            "valid": False,
            "error": str(e)
        }