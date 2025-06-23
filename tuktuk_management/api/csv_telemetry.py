# ~/frappe-bench/apps/tuktuk_management/tuktuk_management/api/csv_telemetry.py

import frappe
import csv
import io
from frappe import _
from frappe.utils import now_datetime, flt, cstr
from datetime import datetime
import json
import os

@frappe.whitelist()
def read_file_content(file_url):
    """
    Read content from an uploaded file using the correct ERPNext method
    
    Args:
        file_url: URL of the uploaded file
    
    Returns:
        String content of the file
    """
    try:
        # Get the File document
        file_doc = frappe.get_doc("File", {"file_url": file_url})
        
        if not file_doc:
            frappe.throw(_("File not found"))
        
        # Check if it's a CSV file
        if not file_doc.file_name.lower().endswith('.csv'):
            frappe.throw(_("File must be a CSV file"))
        
        # Get the full path to the file
        file_path = file_doc.get_full_path()
        
        # Read the file content with different encoding options
        encoding_options = ['utf-8', 'utf-8-sig', 'windows-1252', 'iso-8859-1']
        
        for encoding in encoding_options:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    content = f.read()
                    # If we successfully read without errors, return the content
                    return content
            except UnicodeDecodeError:
                continue
        
        # If all encodings fail, try reading as binary and decode with error handling
        with open(file_path, 'rb') as f:
            content = f.read()
            return content.decode('utf-8', errors='replace')
            
    except Exception as e:
        frappe.throw(_("Failed to read file: {0}").format(str(e)))

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
        
        frappe.publish_realtime(
            "csv_upload_progress",
            {"status": "processing", "format": csv_format["type"]},
            user=frappe.session.user
        )
        
        # Process each row
        row_number = 1
        for row in csv_reader:
            row_number += 1
            results["total_rows"] += 1
            
            try:
                if not row or all(not cell.strip() for cell in row):
                    results["skipped"] += 1
                    continue
                
                # Process based on detected format
                if csv_format["type"] == "telemetry_export":
                    success = process_telemetry_export_row(row, csv_format["mappings"], results)
                elif csv_format["type"] == "battery_update":
                    success = process_battery_update_row(row, csv_format["mappings"], results)
                elif csv_format["type"] == "location_update":
                    success = process_location_update_row(row, csv_format["mappings"], results)
                elif csv_format["type"] == "vehicle_data":
                    success = process_vehicle_data_row(row, csv_format["mappings"], results)
                else:
                    success = process_generic_row(row, csv_format["mappings"], results)
                
                if success:
                    results["updated"] += 1
                else:
                    results["failed"] += 1
                
                results["processed"] += 1
                
                # Publish progress every 10 rows
                if results["processed"] % 10 == 0:
                    frappe.publish_realtime(
                        "csv_upload_progress",
                        {
                            "status": "processing",
                            "processed": results["processed"],
                            "total": results["total_rows"]
                        },
                        user=frappe.session.user
                    )
                
            except Exception as e:
                results["failed"] += 1
                results["errors"].append({
                    "row": row_number,
                    "message": str(e)
                })
                frappe.log_error(f"CSV row processing error: {str(e)}")
        
        # Update settings with last upload time
        settings = frappe.get_single("TukTuk Settings")
        settings.last_telemetry_update = now_datetime()
        settings.save(ignore_permissions=True)
        
        frappe.publish_realtime(
            "csv_upload_progress",
            {"status": "completed", "results": results},
            user=frappe.session.user
        )
        
        frappe.db.commit()
        
        return results
        
    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(f"CSV upload failed: {str(e)}")
        frappe.throw(_("CSV upload failed: {0}").format(str(e)))

def detect_csv_format(headers):
    """
    Detect the format of the CSV based on headers
    
    Args:
        headers: List of column headers (lowercase)
    
    Returns:
        Dictionary with format type and column mappings
    """
    
    # Define format patterns
    formats = {
        "telemetry_export": {
            "required_fields": ["device id", "imei", "vehicle number"],
            "optional_fields": ["voltage", "latitude", "longitude", "battery level"],
            "mappings": {}
        },
        "battery_update": {
            "required_fields": ["tuktuk id", "battery level"],
            "optional_fields": ["timestamp", "voltage"],
            "mappings": {}
        },
        "location_update": {
            "required_fields": ["tuktuk id", "latitude", "longitude"],
            "optional_fields": ["address", "timestamp"],
            "mappings": {}
        },
        "vehicle_data": {
            "required_fields": ["tuktuk id"],
            "optional_fields": ["device id", "imei", "battery level", "latitude", "longitude", "speed"],
            "mappings": {}
        }
    }
    
    # Try to match each format
    for format_type, format_def in formats.items():
        mappings = {}
        required_found = 0
        
        for i, header in enumerate(headers):
            # Check for required fields
            for req_field in format_def["required_fields"]:
                if req_field in header or header in req_field:
                    mappings[req_field.replace(" ", "_")] = i
                    required_found += 1
                    break
            
            # Check for optional fields
            for opt_field in format_def["optional_fields"]:
                if opt_field in header or header in opt_field:
                    mappings[opt_field.replace(" ", "_")] = i
                    break
        
        # If we found all required fields, this is our format
        if required_found >= len(format_def["required_fields"]):
            return {
                "type": format_type,
                "mappings": mappings,
                "confidence": required_found / len(format_def["required_fields"])
            }
    
    return None

def process_battery_update_row(row, mappings, results):
    """Process a row from battery update format"""
    try:
        tuktuk_id = row[mappings.get("tuktuk_id", 0)].strip() if mappings.get("tuktuk_id") is not None else ""
        battery_level = flt(row[mappings.get("battery_level", 1)]) if mappings.get("battery_level") is not None else 0
        
        if not tuktuk_id:
            results["warnings"].append("Missing TukTuk ID in battery update row")
            return False
        
        # Find TukTuk
        tuktuk = frappe.db.get_value("TukTuk Vehicle", {"tuktuk_id": tuktuk_id}, "name")
        if not tuktuk:
            results["warnings"].append(f"TukTuk not found: {tuktuk_id}")
            return False
        
        # Update battery level
        if 0 <= battery_level <= 100:
            doc = frappe.get_doc("TukTuk Vehicle", tuktuk)
            doc.battery_level = battery_level
            doc.last_telemetry_update = now_datetime()
            doc.save(ignore_permissions=True)
            
            results["success_details"].append({
                "tuktuk_id": tuktuk_id,
                "battery_level": battery_level,
                "timestamp": doc.last_telemetry_update
            })
            
            return True
        else:
            results["warnings"].append(f"Invalid battery level: {battery_level} for TukTuk: {tuktuk_id}")
            return False
            
    except Exception as e:
        frappe.log_error(f"Error processing battery update row: {str(e)}")
        return False

def process_location_update_row(row, mappings, results):
    """Process a row from location update format"""
    try:
        tuktuk_id = row[mappings.get("tuktuk_id", 0)].strip() if mappings.get("tuktuk_id") is not None else ""
        latitude = flt(row[mappings.get("latitude", 1)]) if mappings.get("latitude") is not None else 0
        longitude = flt(row[mappings.get("longitude", 2)]) if mappings.get("longitude") is not None else 0
        
        if not tuktuk_id:
            results["warnings"].append("Missing TukTuk ID in location update row")
            return False
        
        # Find TukTuk
        tuktuk = frappe.db.get_value("TukTuk Vehicle", {"tuktuk_id": tuktuk_id}, "name")
        if not tuktuk:
            results["warnings"].append(f"TukTuk not found: {tuktuk_id}")
            return False
        
        # Update location
        if latitude and longitude:
            doc = frappe.get_doc("TukTuk Vehicle", tuktuk)
            doc.current_latitude = latitude
            doc.current_longitude = longitude
            
            # Update address if provided
            if mappings.get("address") is not None and len(row) > mappings["address"]:
                doc.current_address = row[mappings["address"]].strip()
            
            doc.last_telemetry_update = now_datetime()
            doc.save(ignore_permissions=True)
            
            results["success_details"].append({
                "tuktuk_id": tuktuk_id,
                "location": f"{latitude}, {longitude}",
                "timestamp": doc.last_telemetry_update
            })
            
            return True
        else:
            results["warnings"].append(f"Invalid coordinates for TukTuk: {tuktuk_id}")
            return False
            
    except Exception as e:
        frappe.log_error(f"Error processing location update row: {str(e)}")
        return False

def process_vehicle_data_row(row, mappings, results):
    """Process a row from vehicle data format"""
    try:
        tuktuk_id = row[mappings.get("tuktuk_id", 0)].strip() if mappings.get("tuktuk_id") is not None else ""
        
        if not tuktuk_id:
            results["warnings"].append("Missing TukTuk ID in vehicle data row")
            return False
        
        # Find TukTuk
        tuktuk = frappe.db.get_value("TukTuk Vehicle", {"tuktuk_id": tuktuk_id}, "name")
        if not tuktuk:
            results["warnings"].append(f"TukTuk not found: {tuktuk_id}")
            return False
        
        # Update TukTuk with available data
        doc = frappe.get_doc("TukTuk Vehicle", tuktuk)
        updated = False
        
        # Update device_id if provided
        if mappings.get("device_id") is not None and len(row) > mappings["device_id"]:
            device_id = row[mappings["device_id"]].strip()
            if device_id and device_id != doc.device_id:
                doc.device_id = device_id
                updated = True
        
        # Update IMEI if provided
        if mappings.get("imei") is not None and len(row) > mappings["imei"]:
            imei = row[mappings["imei"]].strip()
            if imei and imei != doc.imei:
                doc.imei = imei
                updated = True
        
        # Update battery level if provided
        if mappings.get("battery_level") is not None and len(row) > mappings["battery_level"]:
            battery_level = flt(row[mappings["battery_level"]])
            if 0 <= battery_level <= 100:
                doc.battery_level = battery_level
                updated = True
        
        # Update location if provided
        if mappings.get("latitude") is not None and len(row) > mappings["latitude"]:
            latitude = flt(row[mappings["latitude"]])
            if latitude:
                doc.current_latitude = latitude
                updated = True
        
        if mappings.get("longitude") is not None and len(row) > mappings["longitude"]:
            longitude = flt(row[mappings["longitude"]])
            if longitude:
                doc.current_longitude = longitude
                updated = True
        
        # Update speed if provided
        if mappings.get("speed") is not None and len(row) > mappings["speed"]:
            speed = flt(row[mappings["speed"]])
            if speed >= 0:
                doc.current_speed = speed
                updated = True
        
        if updated:
            doc.last_telemetry_update = now_datetime()
            doc.save(ignore_permissions=True)
            
            results["success_details"].append({
                "tuktuk_id": tuktuk_id,
                "battery_level": doc.battery_level,
                "location": f"{doc.current_latitude}, {doc.current_longitude}" if doc.current_latitude and doc.current_longitude else None,
                "timestamp": doc.last_telemetry_update
            })
            
            return True
        else:
            results["skipped"] += 1
            return False
            
    except Exception as e:
        frappe.log_error(f"Error processing vehicle data row: {str(e)}")
        return False

def process_generic_row(row, mappings, results):
    """Process a generic row when format is unknown"""
    try:
        # Try to find any identifier (TukTuk ID, Device ID, IMEI)
        tuktuk = None
        identifier = None
        
        for i, cell in enumerate(row):
            cell = cell.strip()
            if not cell:
                continue
            
            # Try as TukTuk ID
            tuktuk_doc = frappe.db.get_value("TukTuk Vehicle", {"tuktuk_id": cell}, "name")
            if tuktuk_doc:
                tuktuk = tuktuk_doc
                identifier = f"TukTuk ID: {cell}"
                break
            
            # Try as Device ID
            tuktuk_doc = frappe.db.get_value("TukTuk Vehicle", {"device_id": cell}, "name")
            if tuktuk_doc:
                tuktuk = tuktuk_doc
                identifier = f"Device ID: {cell}"
                break
            
            # Try as IMEI
            tuktuk_doc = frappe.db.get_value("TukTuk Vehicle", {"imei": cell}, "name")
            if tuktuk_doc:
                tuktuk = tuktuk_doc
                identifier = f"IMEI: {cell}"
                break
        
        if not tuktuk:
            results["warnings"].append("No matching TukTuk found in generic row")
            return False
        
        # Update with whatever data we can find
        doc = frappe.get_doc("TukTuk Vehicle", tuktuk)
        updated = False
        
        # Look for numeric values that could be battery level
        for cell in row:
            if cell.strip().replace('.', '').isdigit():
                value = flt(cell)
                if 0 <= value <= 100:  # Likely battery level
                    doc.battery_level = value
                    updated = True
                    break
        
        if updated:
            doc.last_telemetry_update = now_datetime()
            doc.save(ignore_permissions=True)
            
            results["success_details"].append({
                "tuktuk_id": doc.tuktuk_id,
                "battery_level": doc.battery_level,
                "identifier": identifier,
                "timestamp": doc.last_telemetry_update
            })
            
            return True
        else:
            results["skipped"] += 1
            return False
            
    except Exception as e:
        frappe.log_error(f"Error processing generic row: {str(e)}")
        return False

@frappe.whitelist()
def get_csv_template(format_type="telemetry_export"):
    """Generate CSV template for download"""
    try:
        templates = {
            "telemetry_export": [
                "Device ID", "IMEI", "Vehicle Number", "Driver Code", "Driver License",
                "Plate Number", "Group Name", "Sub Group", "Driver Name", "Driver Phone", 
                "Device Status", "Device Type", "SIM No", "Installation Date", "Expiry Date", 
                "Longitude", "Latitude", "Speed", "Course", "Altitude", "Satellite", 
                "GPS Signal Strength", "Last GPS Time", "AC Status", "Power Status", 
                "GPS Status", "Last Online Time", "Is Car Go", "Voltage", "Status"
            ],
            "battery_update": [
                "TukTuk ID", "Battery Level", "Voltage", "Timestamp"
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

@frappe.whitelist()
def get_upload_statistics():
    """Get statistics about TukTuk vehicles and CSV upload readiness"""
    try:
        # Get total vehicles
        total_vehicles = frappe.db.count("TukTuk Vehicle")
        
        # Get vehicles with device mapping
        mapped_vehicles = frappe.db.count("TukTuk Vehicle", {
            "device_id": ["!=", ""]
        }) + frappe.db.count("TukTuk Vehicle", {
            "imei": ["!=", ""]
        })
        
        # Get recently updated vehicles (last 7 days)
        from frappe.utils import add_days, nowdate
        week_ago = add_days(nowdate(), -7)
        recent_updates = frappe.db.count("TukTuk Vehicle", {
            "last_telemetry_update": [">=", week_ago]
        })
        
        # Get battery level distribution
        battery_stats = frappe.db.sql("""
            SELECT 
                CASE 
                    WHEN battery_level >= 80 THEN 'High (80%+)'
                    WHEN battery_level >= 50 THEN 'Medium (50-79%)'
                    WHEN battery_level >= 20 THEN 'Low (20-49%)'
                    WHEN battery_level > 0 THEN 'Critical (<20%)'
                    ELSE 'Unknown'
                END as battery_status,
                COUNT(*) as count
            FROM `tabTukTuk Vehicle`
            GROUP BY battery_status
        """, as_dict=True)
        
        # Get last bulk update info
        last_bulk_update = frappe.db.get_value("Singles", 
                                             {"doctype": "TukTuk Settings", "field": "last_telemetry_update"}, 
                                             "value") or "Never"
        
        return {
            "success": True,
            "statistics": {
                "total_vehicles": total_vehicles,
                "mapped_vehicles": mapped_vehicles,
                "unmapped_vehicles": total_vehicles - mapped_vehicles,
                "mapping_percentage": round((mapped_vehicles / total_vehicles) * 100, 1) if total_vehicles > 0 else 0,
                "recent_updates": recent_updates,
                "battery_distribution": {item["battery_status"]: item["count"] for item in battery_stats},
                "last_bulk_update": last_bulk_update,
                "ready_for_csv_upload": mapped_vehicles > 0
            }
        }
        
    except Exception as e:
        frappe.throw(_("Failed to get statistics: {0}").format(str(e)))_telemetry_export_row(row, mappings, results):
    """Process a row from telemetry export format"""
    try:
        device_id = row[mappings.get("device_id", 0)].strip() if mappings.get("device_id") is not None else ""
        imei = row[mappings.get("imei", 1)].strip() if mappings.get("imei") is not None else ""
        vehicle_number = row[mappings.get("vehicle_number", 2)].strip() if mappings.get("vehicle_number") is not None else ""
        
        # Find TukTuk by device_id, imei, or vehicle_number
        tuktuk = None
        if device_id:
            tuktuk = frappe.db.get_value("TukTuk Vehicle", {"device_id": device_id}, "name")
        if not tuktuk and imei:
            tuktuk = frappe.db.get_value("TukTuk Vehicle", {"imei": imei}, "name")
        if not tuktuk and vehicle_number:
            tuktuk = frappe.db.get_value("TukTuk Vehicle", {"tuktuk_id": vehicle_number}, "name")
        
        if not tuktuk:
            results["warnings"].append(f"TukTuk not found for Device ID: {device_id}, IMEI: {imei}, Vehicle: {vehicle_number}")
            return False
        
        # Update TukTuk with available data
        doc = frappe.get_doc("TukTuk Vehicle", tuktuk)
        
        if mappings.get("battery_level") is not None and len(row) > mappings["battery_level"]:
            battery_level = flt(row[mappings["battery_level"]])
            if 0 <= battery_level <= 100:
                doc.battery_level = battery_level
        
        if mappings.get("latitude") is not None and len(row) > mappings["latitude"]:
            doc.current_latitude = flt(row[mappings["latitude"]])
        
        if mappings.get("longitude") is not None and len(row) > mappings["longitude"]:
            doc.current_longitude = flt(row[mappings["longitude"]])
        
        doc.last_telemetry_update = now_datetime()
        doc.save(ignore_permissions=True)
        
        results["success_details"].append({
            "tuktuk_id": doc.tuktuk_id,
            "battery_level": doc.battery_level,
            "location": f"{doc.current_latitude}, {doc.current_longitude}" if doc.current_latitude and doc.current_longitude else None,
            "timestamp": doc.last_telemetry_update
        })
        
        return True
        
    except Exception as e:
        frappe.log_error(f"Error processing telemetry export row: {str(e)}")
        return False

def process