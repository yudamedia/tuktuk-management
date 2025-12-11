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
def validate_csv_before_upload(csv_content):
    """
    Validate CSV content before processing
    
    Args:
        csv_content: CSV file content as string
    
    Returns:
        Dictionary with validation results
    """
    try:
        # Parse CSV content
        csv_reader = csv.reader(io.StringIO(csv_content))
        
        # Get header row
        headers = []
        try:
            headers = next(csv_reader)
            headers = [h.strip() for h in headers]
        except StopIteration:
            return {"valid": False, "error": "CSV file is empty or invalid"}
        
        if not headers:
            return {"valid": False, "error": "No headers found in CSV"}
        
        # Count rows
        row_count = 0
        for row in csv_reader:
            if row:  # Skip empty rows
                row_count += 1
        
        if row_count == 0:
            return {"valid": False, "error": "No data rows found in CSV"}
        
        # Detect format
        headers_lower = [h.strip().lower() for h in headers]
        csv_format = detect_csv_format(headers_lower)
        
        return {
            "valid": True,
            "headers": headers,
            "row_count": row_count,
            "detected_format": csv_format.get('type', 'Unknown') if csv_format else 'Unknown',
            "message": f"CSV is valid with {row_count} data rows and {len(headers)} columns"
        }
        
    except Exception as e:
        return {"valid": False, "error": f"CSV validation failed: {str(e)}"}

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
        
        # Process data rows
        row_number = 1  # Start from 1 (after header)
        
        for row in csv_reader:
            row_number += 1
            results["total_rows"] += 1
            
            if not row or all(not cell.strip() for cell in row):
                results["skipped"] += 1
                continue
            
            try:
                # Process row based on detected format
                if csv_format["type"] == "telemetry_export":
                    success = process_telemetry_export_row(row, headers, csv_format["mappings"], results)
                elif csv_format["type"] == "battery_update":
                    success = process_battery_update_row(row, headers, csv_format["mappings"], results)
                elif csv_format["type"] == "location_update":
                    success = process_location_update_row(row, headers, csv_format["mappings"], results)
                elif csv_format["type"] == "vehicle_data":
                    success = process_vehicle_data_row(row, headers, csv_format["mappings"], results)
                else:
                    # Try generic processing
                    success = process_generic_row(row, headers, results)
                
                if success:
                    results["processed"] += 1
                    results["updated"] += 1
                else:
                    results["failed"] += 1
                    
            except Exception as e:
                results["failed"] += 1
                results["errors"].append(f"Row {row_number}: {str(e)}")
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
            "required_fields": ["device id", "imei", "device name"],
            "optional_fields": ["voltage", "latitude", "longitude", "battery level", "mileage"],
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
                    mappings[req_field] = i
                    required_found += 1
                    break
            
            # Check for optional fields
            for opt_field in format_def["optional_fields"]:
                if opt_field in header or header in opt_field:
                    mappings[opt_field] = i
                    break
        
        # If all required fields found, this is likely the format
        if required_found >= len(format_def["required_fields"]):
            return {
                "type": format_type,
                "mappings": mappings,
                "confidence": required_found / len(format_def["required_fields"])
            }
    
    # If no exact match, try generic matching
    return detect_generic_format(headers)

def detect_generic_format(headers):
    """
    Detect generic format when specific patterns don't match
    """
    mappings = {}
    
    # Common field mappings
    field_mappings = {
        "device_imei": ["imei", "device imei", "device_imei"],
        "device_id": ["device id", "deviceid", "device_id"],
        "device_name": ["device name", "name", "vehicle"],
        "latitude": ["latitude", "lat"],
        "longitude": ["longitude", "lng", "lon"],
        "voltage": ["voltage", "battery voltage"],
        "speed": ["speed"],
        "course": ["course", "direction", "heading"],
        "satellite": ["satellite", "satellites", "sat"],
        "last_gps_time": ["last gps time", "gps time", "timestamp"],
        "mileage": ["mileage", "total mileage", "odometer"]
    }
    
    for i, header in enumerate(headers):
        for field, patterns in field_mappings.items():
            if any(pattern in header for pattern in patterns):
                mappings[field] = i
                break
    
    if mappings:
        return {
            "type": "generic_telemetry",
            "mappings": mappings,
            "confidence": 0.5
        }
    
    return None

def process_telemetry_export_row(row, headers, mappings, results):
    """Process a row from telemetry export CSV"""
    try:
        # Extract key identifiers
        device_id = str(row[mappings.get("device id", 0)]).strip() if mappings.get("device id") is not None else ""
        device_imei = str(row[mappings.get("imei", 1)]).strip() if mappings.get("imei") is not None else ""
        device_name = str(row[mappings.get("device name", 4)]).strip() if mappings.get("device name") is not None else ""
        
        # Find matching TukTuk Vehicle
        tuktuk_doc = None
        
        # Try to find by device_id first
        if device_id:
            tuktuk_doc = frappe.db.get_value("TukTuk Vehicle", 
                                           {"device_id": device_id}, 
                                           ["name", "tuktuk_id", "device_id", "device_imei"])
        
        # Try to find by IMEI if device_id didn't work
        if not tuktuk_doc and device_imei:
            tuktuk_doc = frappe.db.get_value("TukTuk Vehicle", 
                                           {"device_imei": device_imei}, 
                                           ["name", "tuktuk_id", "device_id", "device_imei"])
        
        # Try to find by device name
        if not tuktuk_doc and device_name:
            tuktuk_doc = frappe.db.get_value("TukTuk Vehicle", 
                                           {"tuktuk_id": device_name}, 
                                           ["name", "tuktuk_id", "device_id", "device_imei"])
        
        if not tuktuk_doc:
            results["warnings"].append(f"No matching TukTuk found for Device ID: {device_id}, IMEI: {device_imei}, Name: {device_name}")
            return False
        
        # Get the document for updating
        doc = frappe.get_doc("TukTuk Vehicle", tuktuk_doc[0])
        updated = False
        
        # Update fields based on available data
        if mappings.get("voltage") is not None and len(row) > mappings["voltage"]:
            voltage = flt(row[mappings["voltage"]])
            if voltage > 0:
                doc.battery_voltage = voltage
                # Estimate battery level from voltage (12V system assumed)
                battery_percentage = min(100, max(0, ((voltage - 11.8) / (12.6 - 11.8)) * 100))
                doc.battery_level = battery_percentage
                updated = True
        
        if mappings.get("latitude") is not None and len(row) > mappings["latitude"]:
            lat = flt(row[mappings["latitude"]])
            if lat != 0:
                doc.latitude = lat
                updated = True
        
        if mappings.get("longitude") is not None and len(row) > mappings["longitude"]:
            lng = flt(row[mappings["longitude"]])
            if lng != 0:
                doc.longitude = lng
                updated = True
        
        if mappings.get("mileage") is not None and len(row) > mappings["mileage"]:
            mileage = flt(row[mappings["mileage"]])
            if mileage > 0:
                # Convert from meters to kilometers (divide by 1000)
                doc.mileage = mileage / 1000
                updated = True
        
        if updated:
            doc.last_reported = now_datetime()  # Use correct field name
            doc.save(ignore_permissions=True)
            
            results["success_details"].append({
                "tuktuk_id": doc.tuktuk_id,
                "device_id": device_id,
                "imei": device_imei,
                "battery_level": doc.battery_level,
                "timestamp": doc.last_reported
            })
            
            return True
        else:
            results["skipped"] += 1
            return False
            
    except Exception as e:
        frappe.log_error(f"Error processing telemetry export row: {str(e)}")
        return False

def process_battery_update_row(row, headers, mappings, results):
    """Process a row from battery update CSV"""
    try:
        tuktuk_id = str(row[mappings.get("tuktuk id", 0)]).strip() if mappings.get("tuktuk id") is not None else ""
        battery_level = flt(row[mappings.get("battery level", 1)]) if mappings.get("battery level") is not None else 0
        
        if not tuktuk_id or battery_level <= 0:
            return False
        
        # Find TukTuk Vehicle
        doc = frappe.get_doc("TukTuk Vehicle", {"tuktuk_id": tuktuk_id})
        if not doc:
            results["warnings"].append(f"TukTuk {tuktuk_id} not found")
            return False
        
        doc.battery_level = battery_level
        doc.last_reported = now_datetime()
        doc.save(ignore_permissions=True)
        
        results["success_details"].append({
            "tuktuk_id": tuktuk_id,
            "battery_level": battery_level,
            "timestamp": doc.last_reported
        })
        
        return True
        
    except Exception as e:
        frappe.log_error(f"Error processing battery update row: {str(e)}")
        return False

def process_location_update_row(row, headers, mappings, results):
    """Process a row from location update CSV"""
    try:
        tuktuk_id = str(row[mappings.get("tuktuk id", 0)]).strip() if mappings.get("tuktuk id") is not None else ""
        latitude = flt(row[mappings.get("latitude", 1)]) if mappings.get("latitude") is not None else 0
        longitude = flt(row[mappings.get("longitude", 2)]) if mappings.get("longitude") is not None else 0
        
        if not tuktuk_id or latitude == 0 or longitude == 0:
            return False
        
        # Find TukTuk Vehicle
        doc = frappe.get_doc("TukTuk Vehicle", {"tuktuk_id": tuktuk_id})
        if not doc:
            results["warnings"].append(f"TukTuk {tuktuk_id} not found")
            return False
        
        doc.latitude = latitude
        doc.longitude = longitude
        doc.last_reported = now_datetime()
        doc.save(ignore_permissions=True)
        
        results["success_details"].append({
            "tuktuk_id": tuktuk_id,
            "latitude": latitude,
            "longitude": longitude,
            "timestamp": doc.last_reported
        })
        
        return True
        
    except Exception as e:
        frappe.log_error(f"Error processing location update row: {str(e)}")
        return False

def process_vehicle_data_row(row, headers, mappings, results):
    """Process a row from vehicle data CSV"""
    try:
        tuktuk_id = str(row[mappings.get("tuktuk id", 0)]).strip() if mappings.get("tuktuk id") is not None else ""
        
        if not tuktuk_id:
            return False
        
        # Find TukTuk Vehicle
        doc = frappe.get_doc("TukTuk Vehicle", {"tuktuk_id": tuktuk_id})
        if not doc:
            results["warnings"].append(f"TukTuk {tuktuk_id} not found")
            return False
        
        updated = False
        
        # Update available fields
        if mappings.get("battery level") is not None and len(row) > mappings["battery level"]:
            battery_level = flt(row[mappings["battery level"]])
            if battery_level > 0:
                doc.battery_level = battery_level
                updated = True
        
        if mappings.get("latitude") is not None and len(row) > mappings["latitude"]:
            lat = flt(row[mappings["latitude"]])
            if lat != 0:
                doc.latitude = lat
                updated = True
        
        if mappings.get("longitude") is not None and len(row) > mappings["longitude"]:
            lng = flt(row[mappings["longitude"]])
            if lng != 0:
                doc.longitude = lng
                updated = True
        
        if updated:
            doc.last_reported = now_datetime()
            doc.save(ignore_permissions=True)
            
            results["success_details"].append({
                "tuktuk_id": tuktuk_id,
                "timestamp": doc.last_reported
            })
            
            return True
        else:
            results["skipped"] += 1
            return False
            
    except Exception as e:
        frappe.log_error(f"Error processing vehicle data row: {str(e)}")
        return False

def process_generic_row(row, headers, results):
    """Process a generic row when format is unknown"""
    try:
        # Try to find any identifier that matches our TukTuk records
        identifiers = []
        
        # Look for potential identifiers in the row
        for i, cell in enumerate(row):
            if cell and str(cell).strip():
                cell_value = str(cell).strip()
                # Skip obviously non-identifier values (coordinates, timestamps, etc.)
                if not any(char in cell_value for char in ['.', ':', '-']) or len(cell_value) < 3:
                    continue
                identifiers.append((i, cell_value))
        
        # Try to find a matching TukTuk Vehicle
        doc = None
        identifier = None
        
        for idx, identifier_value in identifiers:
            # Try different fields
            for field in ["tuktuk_id", "device_id", "device_imei"]:
                doc = frappe.db.get_value("TukTuk Vehicle", {field: identifier_value}, "name")
                if doc:
                    doc = frappe.get_doc("TukTuk Vehicle", doc)
                    identifier = identifier_value
                    break
            if doc:
                break
        
        if not doc:
            return False
        
        updated = False
        
        # Look for numeric values that could be battery level or voltage
        for i, cell in enumerate(row):
            if cell and str(cell).replace('.', '').replace(',', '').isdigit():
                value = flt(cell)
                if 0 <= value <= 100:  # Likely battery level
                    doc.battery_level = value
                    updated = True
                    break
        
        if updated:
            doc.last_reported = now_datetime()
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
                "GPS Status", "Last Online Time", "Is Car Go", "Voltage", "Mileage", "Status"
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
        
        # Create CSV content
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(templates[format_type])
        
        # Add sample data row
        if format_type == "telemetry_export":
            writer.writerow([
                "12345", "123456789012345", "TT001", "D001", "DL123",
                "KCA 001A", "Fleet A", "Group 1", "John Doe", "254712345678",
                "Online", "GPS", "254712345678", "2024-01-01", "2025-12-31",
                "39.6629", "-4.0435", "0", "0", "1200", "8",
                "85", "2024-12-26 10:30:00", "ON", "ON",
                "ON", "2024-12-26 10:30:00", "0", "12.4", "1250.50", "Active"
            ])
        elif format_type == "battery_update":
            writer.writerow(["TT001", "85", "12.4", "2024-12-26 10:30:00"])
        elif format_type == "location_update":
            writer.writerow(["TT001", "-4.0435", "39.6629", "Diani Beach", "2024-12-26 10:30:00"])
        elif format_type == "vehicle_data":
            writer.writerow(["TT001", "12345", "123456789012345", "85", "-4.0435", "39.6629", "0", "Active"])
        
        content = output.getvalue()
        output.close()
        
        return {
            "content": content,
            "filename": f"tuktuk_{format_type}_template.csv",
            "format": format_type
        }
        
    except Exception as e:
        frappe.throw(_("Failed to generate CSV template: {0}").format(str(e)))

@frappe.whitelist()
def get_upload_status():
    """Get the status of ongoing CSV uploads"""
    return {
        "status": "ready",
        "message": "System ready for CSV upload"
    }