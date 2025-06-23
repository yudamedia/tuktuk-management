# Create this new file: ~/frappe-bench/apps/tuktuk_management/tuktuk_management/utils/logging.py
import frappe
from frappe.utils import now_datetime

def log_telemetry_success(message, vehicle_count=None, updated_count=None):
    """Log telemetry success operations to Activity Log instead of Error Log"""
    try:
        # Create a proper activity log entry
        activity_log = frappe.get_doc({
            "doctype": "Activity Log",
            "subject": "Telemetry Update Success",
            "content": message,
            "status": "Complete",
            "user": frappe.session.user,
            "ip_address": frappe.local.request_ip if frappe.local.request_ip else None,
            "creation": now_datetime()
        })
        activity_log.insert(ignore_permissions=True)
        
        # Also log to console in development
        print(f"✅ TELEMETRY SUCCESS: {message}")
        
        # Optionally update a settings field to track last successful operation
        if vehicle_count is not None:
            frappe.db.set_single_value("TukTuk Settings", "last_telemetry_update", now_datetime())
            frappe.db.set_single_value("TukTuk Settings", "last_telemetry_vehicle_count", vehicle_count)
            
    except Exception as e:
        # Fallback to console if activity log fails
        print(f"✅ TELEMETRY SUCCESS: {message} (Activity log failed: {str(e)})")

def log_telemetry_info(message, reference_doctype=None, reference_name=None):
    """Log informational telemetry messages"""
    try:
        # Create an info-level comment if we have a reference
        if reference_doctype and reference_name:
            frappe.get_doc({
                "doctype": "Comment",
                "comment_type": "Info",
                "reference_doctype": reference_doctype,
                "reference_name": reference_name,
                "content": f"Telemetry: {message}"
            }).insert(ignore_permissions=True)
        
        # Log to console
        print(f"ℹ️ TELEMETRY INFO: {message}")
        
    except Exception as e:
        print(f"ℹ️ TELEMETRY INFO: {message} (Comment log failed: {str(e)})")

def log_telemetry_warning(message, reference_doctype=None, reference_name=None):
    """Log telemetry warnings (not errors, but things to watch)"""
    try:
        # Log warnings to a custom doctype or comment system
        if reference_doctype and reference_name:
            frappe.get_doc({
                "doctype": "Comment",
                "comment_type": "Workflow",
                "reference_doctype": reference_doctype,
                "reference_name": reference_name,
                "content": f"⚠️ Telemetry Warning: {message}"
            }).insert(ignore_permissions=True)
        
        print(f"⚠️ TELEMETRY WARNING: {message}")
        
    except Exception as e:
        print(f"⚠️ TELEMETRY WARNING: {message}")

def log_telemetry_error(message, exception=None, reference_doctype=None, reference_name=None):
    """Properly log actual telemetry errors"""
    try:
        error_message = message
        if exception:
            error_message += f" | Exception: {str(exception)}"
        
        # Use frappe.log_error only for actual errors
        frappe.log_error(error_message, "Telemetry Error")
        
        # Also add to reference document if provided
        if reference_doctype and reference_name:
            frappe.get_doc({
                "doctype": "Comment",
                "comment_type": "Info",
                "reference_doctype": reference_doctype,
                "reference_name": reference_name,
                "content": f"❌ Telemetry Error: {message}"
            }).insert(ignore_permissions=True)
            
    except Exception as e:
        # Fallback to console
        print(f"❌ TELEMETRY ERROR: {message}")

def log_batch_operation(operation_type, total_count, success_count, error_count, details=None):
    """Log batch operations with proper statistics"""
    try:
        success_rate = (success_count / total_count * 100) if total_count > 0 else 0
        
        message = f"{operation_type}: {success_count}/{total_count} successful ({success_rate:.1f}%)"
        if error_count > 0:
            message += f", {error_count} errors"
        
        if details:
            message += f" | Details: {details}"
        
        # Log as success if most operations succeeded, warning if mixed results
        if error_count == 0:
            log_telemetry_success(message, total_count, success_count)
        elif success_count > error_count:
            log_telemetry_warning(message)
        else:
            log_telemetry_error(message)
            
        return {
            "message": message,
            "success_rate": success_rate,
            "total": total_count,
            "success": success_count,
            "errors": error_count
        }
        
    except Exception as e:
        print(f"Failed to log batch operation: {str(e)}")


# UPDATED FUNCTIONS FOR TELEMATICS.PY
# Replace the problematic functions in your telematics.py with these:

@frappe.whitelist()
def update_all_vehicle_statuses():
    """Update status for all vehicles with telematics devices - FIXED VERSION"""
    from tuktuk_management.utils.logging import log_telemetry_success, log_telemetry_error, log_batch_operation
    
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
        
        all_vehicles = vehicles_with_device_id + vehicles_with_imei_only
        
        updated_count = 0
        error_count = 0
        error_details = []
        
        for vehicle in all_vehicles:
            try:
                device_id = vehicle.get("device_id") or vehicle.get("device_imei")
                if device_id:
                    success = integration.update_vehicle_status(device_id)
                    if success:
                        updated_count += 1
                        # Log individual success to vehicle record
                        log_telemetry_info(
                            f"Status updated successfully", 
                            "TukTuk Vehicle", 
                            vehicle.get("name")
                        )
                    else:
                        error_count += 1
                        error_details.append(f"Update failed for {vehicle.get('tuktuk_id')}")
            except Exception as e:
                error_count += 1
                error_details.append(f"Exception for {vehicle.get('tuktuk_id')}: {str(e)}")
                log_telemetry_error(
                    f"Update failed: {str(e)}", 
                    e, 
                    "TukTuk Vehicle", 
                    vehicle.get("name")
                )
        
        frappe.db.commit()
        
        # Log the batch operation result properly
        result = log_batch_operation(
            "Telemetry Batch Update", 
            len(all_vehicles), 
            updated_count, 
            error_count,
            f"Devices processed: {len(all_vehicles)}"
        )
        
        return {
            "success": True,
            "updated": updated_count,
            "errors": error_count,
            "total": len(all_vehicles),
            "message": result["message"],
            "error_details": error_details[:5]  # Only return first 5 errors
        }
        
    except Exception as e:
        log_telemetry_error(f"Batch update failed completely: {str(e)}", e)
        return {
            "success": False,
            "message": f"Batch update failed: {str(e)}",
            "error": str(e)
        }


# UPDATED BATTERY UTILS FUNCTIONS
# Replace these functions in battery_utils.py:

def update_all_battery_levels():
    """Update battery levels for all vehicles - with proper logging"""
    from tuktuk_management.utils.logging import log_telemetry_success, log_telemetry_error
    
    try:
        from tuktuk_management.api.telematics import TelematicsIntegration
        integration = TelematicsIntegration()
        
        vehicles = frappe.get_all("TukTuk Vehicle",
                                 filters={"device_id": ["!=", ""]},
                                 fields=["name", "device_id", "tuktuk_id"])
        
        updated_count = 0
        
        for vehicle in vehicles:
            try:
                telemetry_data = integration.get_vehicle_data(vehicle.device_id)
                
                if telemetry_data:
                    result = update_battery_from_telemetry(vehicle.name, telemetry_data)
                    if result["success"]:
                        updated_count += 1
                        
            except Exception as e:
                log_telemetry_error(f"Battery update failed for {vehicle.tuktuk_id}: {str(e)}", e)
        
        frappe.db.commit()
        
        # Proper success logging
        log_telemetry_success(f"Battery levels updated for {updated_count}/{len(vehicles)} vehicles")
        
    except Exception as e:
        log_telemetry_error(f"Scheduled battery update failed: {str(e)}", e)

def check_low_battery_alerts():
    """Check for low battery vehicles - with proper logging"""
    from tuktuk_management.utils.logging import log_telemetry_info, log_telemetry_error
    
    try:
        low_battery_vehicles = frappe.db.sql("""
            SELECT name, tuktuk_id, battery_level, last_reported
            FROM `tabTukTuk Vehicle`
            WHERE battery_level <= 20 
            AND status NOT IN ('Charging', 'Maintenance')
            AND (last_reported IS NULL OR last_reported < DATE_SUB(NOW(), INTERVAL 1 HOUR))
        """, as_dict=True)
        
        alert_count = 0
        for vehicle_data in low_battery_vehicles:
            try:
                vehicle = frappe.get_doc("TukTuk Vehicle", vehicle_data.name)
                battery_status = BatteryConverter.get_battery_status(vehicle.battery_level)
                send_battery_alert(vehicle, battery_status)
                alert_count += 1
                
            except Exception as e:
                log_telemetry_error(f"Low battery alert failed for {vehicle_data.tuktuk_id}: {str(e)}", e)
        
        if low_battery_vehicles:
            log_telemetry_info(f"Low battery alerts sent for {alert_count}/{len(low_battery_vehicles)} vehicles")
            
    except Exception as e:
        log_telemetry_error(f"Low battery check failed: {str(e)}", e)


# ADD THESE FIELDS TO TukTuk Settings DocType:
# Add these fields to track telemetry operations:
"""
{
   "fieldname": "telemetry_logging_section",
   "fieldtype": "Section Break",
   "label": "Telemetry Logging"
},
{
   "fieldname": "last_telemetry_update",
   "fieldtype": "Datetime",
   "label": "Last Telemetry Update",
   "read_only": 1
},
{
   "fieldname": "last_telemetry_vehicle_count",
   "fieldtype": "Int",
   "label": "Last Update Vehicle Count",
   "read_only": 1
},
{
   "fieldname": "enable_telemetry_success_logging",
   "fieldtype": "Check",
   "label": "Log Telemetry Success Operations",
   "default": 1,
   "description": "Log successful telemetry operations to Activity Log instead of Error Log"
}
"""