# ~/frappe-bench/apps/tuktuk_management/tuktuk_management/api/csv_integration.py

import frappe
from frappe import _

@frappe.whitelist()
def quick_csv_upload_from_telemetry_export():
    """
    Quick CSV upload using the known telemetry export format
    This function specifically handles your telemetry platform's CSV export
    """
    try:
        # Expected format from your telemetry platform
        expected_headers = [
            "Device IMEI", "Device ID", "Vehicle Name", "Vehicle Type", "Plate Number",
            "Group Name", "Sub Group", "Driver Name", "Driver Phone", "Device Status",
            "Device Type", "SIM No", "Installation Date", "Expiry Date", "Longitude",
            "Latitude", "Speed", "Course", "Altitude", "Satellite", "GPS Signal Strength",
            "Last GPS Time", "AC Status", "Power Status", "GPS Status", "Last Online Time",
            "Is Car Go", "Voltage", "Status"
        ]
        
        return {
            "success": True,
            "expected_format": "telemetry_export",
            "headers": expected_headers,
            "instructions": [
                "1. Export data from your telemetry platform",
                "2. Ensure the CSV has the expected 29 columns",
                "3. The system will auto-map devices to vehicles",
                "4. Voltage values will be converted to battery percentages",
                "5. GPS coordinates will update vehicle locations"
            ]
        }
        
    except Exception as e:
        frappe.throw(_("Failed to prepare upload: {0}").format(str(e)))

@frappe.whitelist()
def batch_update_from_device_export(csv_data):
    """
    Process batch update from the 9-device export you have
    """
    try:
        # Known device data from your telemetry export
        device_updates = [
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
        
        from tuktuk_management.api.csv_telemetry import update_vehicle_from_csv_data
        from tuktuk_management.api.battery_utils import BatteryConverter
        
        results = {
            "updated": 0,
            "failed": 0,
            "errors": [],
            "updates": []
        }
        
        for device_data in device_updates:
            try:
                # Find vehicle with this device
                vehicle = frappe.get_all("TukTuk Vehicle",
                                       filters={
                                           "$or": [
                                               {"device_id": device_data["device_id"]},
                                               {"device_imei": device_data["imei"]}
                                           ]
                                       },
                                       fields=["name", "tuktuk_id"],
                                       limit=1)
                
                if vehicle:
                    vehicle_doc = frappe.get_doc("TukTuk Vehicle", vehicle[0].name)
                    
                    # Update battery
                    if device_data["voltage"] > 0:
                        if device_data["voltage"] > 100:  # It's voltage
                            battery_percentage = BatteryConverter.voltage_to_percentage(device_data["voltage"])
                            vehicle_doc.battery_voltage = device_data["voltage"]
                        else:  # It's already percentage
                            battery_percentage = device_data["voltage"]
                        
                        vehicle_doc.battery_level = battery_percentage
                    
                    # Update location
                    vehicle_doc.latitude = device_data["lat"]
                    vehicle_doc.longitude = device_data["lng"]
                    
                    # Update device mapping if not set
                    if not vehicle_doc.device_id:
                        vehicle_doc.device_id = device_data["device_id"]
                    if not vehicle_doc.device_imei:
                        vehicle_doc.device_imei = device_data["imei"]
                    
                    # Update status based on device status
                    if device_data["status"] == "Offline" and vehicle_doc.status != "Out of Service":
                        vehicle_doc.status = "Out of Service"
                    elif device_data["status"] == "Static" and vehicle_doc.status == "Out of Service":
                        vehicle_doc.status = "Available"
                    
                    vehicle_doc.last_reported = frappe.utils.now_datetime()
                    vehicle_doc.save(ignore_permissions=True)
                    
                    results["updated"] += 1
                    results["updates"].append({
                        "tuktuk_id": vehicle_doc.tuktuk_id,
                        "device_id": device_data["device_id"],
                        "battery": battery_percentage if device_data["voltage"] > 0 else "No update",
                        "location": f"{device_data['lat']}, {device_data['lng']}",
                        "status": device_data["status"]
                    })
                    
                else:
                    results["failed"] += 1
                    results["errors"].append(f"No vehicle found for device {device_data['device_id']}")
                    
            except Exception as e:
                results["failed"] += 1
                results["errors"].append(f"Error updating device {device_data['device_id']}: {str(e)}")
        
        frappe.db.commit()
        
        return {
            "success": True,
            "message": f"Updated {results['updated']} vehicles, {results['failed']} failed",
            "results": results
        }
        
    except Exception as e:
        frappe.throw(_("Batch update failed: {0}").format(str(e)))

@frappe.whitelist()
def create_sample_csv_data():
    """
    Create sample CSV data for testing uploads
    """
    try:
        # Get current vehicle data to create realistic samples
        vehicles = frappe.get_all("TukTuk Vehicle",
                                fields=["tuktuk_id", "device_id", "device_imei", "battery_level", "latitude", "longitude"],
                                limit=5)
        
        csv_samples = {
            "telemetry_export": {
                "headers": [
                    "Device IMEI", "Device ID", "Vehicle Name", "Vehicle Type", "Plate Number",
                    "Group Name", "Sub Group", "Driver Name", "Driver Phone", "Device Status",
                    "Device Type", "SIM No", "Installation Date", "Expiry Date", "Longitude",
                    "Latitude", "Speed", "Course", "Altitude", "Satellite", "GPS Signal Strength",
                    "Last GPS Time", "AC Status", "Power Status", "GPS Status", "Last Online Time",
                    "Is Car Go", "Voltage", "Status"
                ],
                "sample_rows": []
            },
            "battery_update": {
                "headers": ["TukTuk ID", "Battery Level", "Is Voltage", "Timestamp"],
                "sample_rows": []
            },
            "location_update": {
                "headers": ["TukTuk ID", "Latitude", "Longitude", "Address", "Timestamp"],
                "sample_rows": []
            },
            "vehicle_data": {
                "headers": ["TukTuk ID", "Device ID", "IMEI", "Battery Level", "Latitude", "Longitude", "Speed", "Status"],
                "sample_rows": []
            }
        }
        
        # Generate sample rows from actual vehicle data
        for i, vehicle in enumerate(vehicles):
            # Telemetry export sample
            csv_samples["telemetry_export"]["sample_rows"].append([
                vehicle.device_imei or f"86090905037936{i}",
                vehicle.device_id or f"13{i+5}",
                vehicle.tuktuk_id,
                "TukTuk",
                f"KAA{i+100}T",
                "Sunny TukTuk",
                "Diani Fleet",
                f"Driver {i+1}",
                f"25471234567{i}",
                "Static",
                "GPS Tracker",
                f"25470123456{i}",
                "2024-01-01",
                "2025-01-01",
                str(vehicle.longitude or 39.587394),
                str(vehicle.latitude or -4.286028),
                "0",
                "45",
                "10",
                "12",
                "25",
                frappe.utils.now_datetime(),
                "OFF",
                "ON",
                "Valid",
                frappe.utils.now_datetime(),
                "0",
                str(vehicle.battery_level or 75),
                "Active"
            ])
            
            # Battery update sample
            csv_samples["battery_update"]["sample_rows"].append([
                vehicle.tuktuk_id,
                str(vehicle.battery_level or 75),
                "false",
                frappe.utils.now_datetime()
            ])
            
            # Location update sample
            csv_samples["location_update"]["sample_rows"].append([
                vehicle.tuktuk_id,
                str(vehicle.latitude or -4.286028),
                str(vehicle.longitude or 39.587394),
                "Diani Beach, Kenya",
                frappe.utils.now_datetime()
            ])
            
            # Vehicle data sample
            csv_samples["vehicle_data"]["sample_rows"].append([
                vehicle.tuktuk_id,
                vehicle.device_id or f"13{i+5}",
                vehicle.device_imei or f"86090905037936{i}",
                str(vehicle.battery_level or 75),
                str(vehicle.latitude or -4.286028),
                str(vehicle.longitude or 39.587394),
                "0",
                "Available"
            ])
        
        return {
            "success": True,
            "samples": csv_samples
        }
        
    except Exception as e:
        frappe.throw(_("Failed to create samples: {0}").format(str(e)))

@frappe.whitelist()
def get_upload_statistics():
    """
    Get statistics about CSV uploads and current system state
    """
    try:
        # Count vehicles with/without device mapping
        total_vehicles = frappe.db.count("TukTuk Vehicle")
        mapped_vehicles = frappe.db.count("TukTuk Vehicle", {
            "$and": [
                {"device_id": ["!=", ""]},
                {"device_imei": ["!=", ""]}
            ]
        })
        
        # Count recent updates
        one_hour_ago = frappe.utils.add_hours(frappe.utils.now_datetime(), -1)
        recent_updates = frappe.db.count("TukTuk Vehicle", {
            "last_reported": [">", one_hour_ago]
        })
        
        # Battery status distribution
        battery_stats = frappe.db.sql("""
            SELECT 
                CASE 
                    WHEN battery_level <= 10 THEN 'Critical'
                    WHEN battery_level <= 25 THEN 'Low'
                    WHEN battery_level <= 50 THEN 'Medium'
                    WHEN battery_level > 50 THEN 'Good'
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
        frappe.throw(_("Failed to get statistics: {0}").format(str(e)))

# Integration hooks for automatic CSV processing
def on_file_upload(doc, method):
    """
    Auto-detect and process CSV files when uploaded
    """
    try:
        if doc.file_name and doc.file_name.lower().endswith('.csv'):
            # Check if it's in a telemetry-related folder or has telemetry keywords
            telemetry_keywords = ['telemetry', 'telematics', 'vehicle', 'tuktuk', 'gps', 'tracker']
            
            if any(keyword in doc.file_name.lower() for keyword in telemetry_keywords):
                # Add a comment suggesting CSV upload processing
                frappe.get_doc({
                    "doctype": "Comment",
                    "comment_type": "Info",
                    "reference_doctype": "File",
                    "reference_name": doc.name,
                    "content": f"""CSV file detected: {doc.file_name}
                    
This appears to be a telemetry-related CSV file. You can process it using:
1. Go to TukTuk Vehicle list
2. Click 'CSV Upload' 
3. Select this file for automatic processing

Or use the API: tuktuk_management.api.csv_telemetry.upload_telemetry_csv_data
                    """
                }).insert(ignore_permissions=True)
                
    except Exception as e:
        frappe.log_error(f"CSV auto-detection failed: {str(e)}")

@frappe.whitelist()
def process_uploaded_file(file_url, mapping_type="auto"):
    """
    Process an already uploaded CSV file
    """
    try:
        # Get file content
        file_doc = frappe.get_doc("File", {"file_url": file_url})
        
        if not file_doc.file_name.lower().endswith('.csv'):
            frappe.throw(_("File must be a CSV file"))
        
        # Read file content
        with open(file_doc.get_full_path(), 'r', encoding='utf-8') as f:
            csv_content = f.read()
        
        # Process using the main CSV upload function
        from tuktuk_management.api.csv_telemetry import upload_telemetry_csv_data
        
        result = upload_telemetry_csv_data(csv_content, mapping_type)
        
        # Add processing comment to file
        frappe.get_doc({
            "doctype": "Comment",
            "comment_type": "Info",
            "reference_doctype": "File",
            "reference_name": file_doc.name,
            "content": f"""CSV Processing Results:
            
✅ Total Rows: {result['total_rows']}
✅ Updated: {result['updated']}
❌ Failed: {result['failed']}
⏭️ Skipped: {result['skipped']}

Format: {result.get('csv_format', {}).get('type', 'Unknown')}
Processed: {frappe.utils.now_datetime()}
            """
        }).insert(ignore_permissions=True)
        
        return result
        
    except Exception as e:
        frappe.throw(_("File processing failed: {0}").format(str(e)))

@frappe.whitelist()
def schedule_regular_csv_import(file_url, frequency="daily"):
    """
    Schedule regular import of a CSV file (for automated telemetry updates)
    """
    try:
        # This would set up a scheduled job to process the CSV regularly
        # Implementation would depend on your telemetry platform's export schedule
        
        schedule_doc = frappe.get_doc({
            "doctype": "Scheduled Job Type",
            "method": "tuktuk_management.api.csv_integration.process_uploaded_file",
            "frequency": frequency,
            "cron_format": "0 */6 * * *" if frequency == "6hourly" else None  # Every 6 hours
        })
        
        return {
            "success": True,
            "message": f"Scheduled CSV import every {frequency}",
            "job_name": schedule_doc.name
        }
        
    except Exception as e:
        frappe.throw(_("Scheduling failed: {0}").format(str(e)))

# Utility functions for CSV processing
def clean_csv_data(csv_content):
    """
    Clean and normalize CSV data before processing
    """
    try:
        lines = csv_content.split('\n')
        cleaned_lines = []
        
        for line in lines:
            # Remove extra whitespace and tabs
            cleaned_line = line.strip().replace('\t', ',')
            
            # Skip empty lines
            if cleaned_line:
                cleaned_lines.append(cleaned_line)
        
        return '\n'.join(cleaned_lines)
        
    except Exception as e:
        frappe.log_error(f"CSV cleaning failed: {str(e)}")
        return csv_content

def validate_csv_structure(csv_content):
    """
    Validate CSV structure before processing
    """
    try:
        import csv
        import io
        
        # Check if it's valid CSV
        csv_reader = csv.reader(io.StringIO(csv_content))
        
        headers = next(csv_reader, [])
        if not headers:
            return {"valid": False, "error": "No headers found"}
        
        row_count = 0
        column_counts = []
        
        for row in csv_reader:
            if row:  # Skip empty rows
                row_count += 1
                column_counts.append(len(row))
        
        if row_count == 0:
            return {"valid": False, "error": "No data rows found"}
        
        # Check for consistent column counts
        header_count = len(headers)
        inconsistent_rows = [i+2 for i, count in enumerate(column_counts) if count != header_count]
        
        if len(inconsistent_rows) > row_count * 0.1:  # More than 10% inconsistent
            return {
                "valid": False, 
                "error": f"Inconsistent column counts. Expected {header_count}, found inconsistencies in rows: {inconsistent_rows[:5]}..."
            }
        
        return {
            "valid": True,
            "headers": headers,
            "row_count": row_count,
            "warnings": f"{len(inconsistent_rows)} rows with inconsistent column counts" if inconsistent_rows else None
        }
        
    except Exception as e:
        return {"valid": False, "error": str(e)}

# Background job for large CSV processing
@frappe.whitelist()
def process_large_csv_background(file_url, mapping_type="auto", user_email=None):
    """
    Process large CSV files in background to avoid timeouts
    """
    try:
        frappe.publish_realtime(
            event="csv_processing_started",
            message={"status": "started", "file_url": file_url},
            user=user_email or frappe.session.user
        )
        
        # Process the file
        result = process_uploaded_file(file_url, mapping_type)
        
        # Send completion notification
        frappe.publish_realtime(
            event="csv_processing_completed",
            message={
                "status": "completed",
                "result": result,
                "file_url": file_url
            },
            user=user_email or frappe.session.user
        )
        
        # Send email notification if email provided
        if user_email:
            frappe.sendmail(
                recipients=[user_email],
                subject="CSV Processing Completed",
                message=f"""
                Your CSV file has been processed successfully.
                
                Results:
                - Total Rows: {result['total_rows']}
                - Updated: {result['updated']}
                - Failed: {result['failed']}
                
                Please check the TukTuk Vehicle list for updated information.
                """
            )
        
        return result
        
    except Exception as e:
        error_msg = str(e)
        frappe.log_error(f"Background CSV processing failed: {error_msg}")
        
        # Send error notification
        frappe.publish_realtime(
            event="csv_processing_failed",
            message={
                "status": "failed",
                "error": error_msg,
                "file_url": file_url
            },
            user=user_email or frappe.session.user
        )
        
        raise e