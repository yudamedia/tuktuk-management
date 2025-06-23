# ~/frappe-bench/apps/tuktuk_management/tuktuk_management/api/battery_utils.py

import frappe
from frappe.utils import flt, now_datetime
import json

class BatteryConverter:
    """
    Utility class to handle battery voltage to percentage conversion
    """
    
    # Battery system configurations
    BATTERY_CONFIGS = {
        "48V": {"min_voltage": 39.0, "max_voltage": 51.0},
        "72V": {"min_voltage": 58.0, "max_voltage": 76.0}, 
        "96V": {"min_voltage": 77.0, "max_voltage": 101.0}
    }
    
    @staticmethod
    def voltage_to_percentage(voltage, system_type="auto"):
        """
        Convert battery voltage to percentage
        
        Args:
            voltage (float): Battery voltage reading
            system_type (str): Battery system type ("48V", "72V", "96V", "auto")
            
        Returns:
            int: Battery percentage (0-100)
        """
        voltage = flt(voltage)
        
        if voltage <= 0:
            return 0
        
        # Based on telemetry analysis, values 0-100 are likely already percentages
        if 0 <= voltage <= 100:
            return int(round(voltage))
        
        # Auto-detect system type based on voltage range
        if system_type == "auto":
            if voltage <= 55:
                system_type = "48V"
            elif voltage <= 85:
                system_type = "72V"
            else:
                system_type = "96V"
        
        config = BatteryConverter.BATTERY_CONFIGS.get(system_type)
        if not config:
            # Fallback: treat as percentage if unknown system
            return int(min(100, max(0, voltage)))
        
        # Calculate percentage based on voltage range
        min_v = config["min_voltage"]
        max_v = config["max_voltage"]
        
        percentage = ((voltage - min_v) / (max_v - min_v)) * 100
        return int(max(0, min(100, round(percentage))))
    
    @staticmethod
    def get_battery_status(percentage):
        """
        Get battery status based on percentage
        
        Args:
            percentage (int): Battery percentage
            
        Returns:
            dict: Status information
        """
        if percentage <= 10:
            return {
                "status": "Critical",
                "color": "red",
                "action": "Immediate charging required",
                "priority": "high"
            }
        elif percentage <= 20:
            return {
                "status": "Low", 
                "color": "orange",
                "action": "Charging recommended",
                "priority": "medium"
            }
        elif percentage <= 50:
            return {
                "status": "Medium",
                "color": "yellow", 
                "action": "Monitor level",
                "priority": "low"
            }
        else:
            return {
                "status": "Good",
                "color": "green",
                "action": "Normal operation",
                "priority": "none"
            }
    
    @staticmethod
    def estimate_range_km(percentage, base_range_km=50):
        """
        Estimate remaining range based on battery percentage
        
        Args:
            percentage (int): Current battery percentage
            base_range_km (int): Full battery range in kilometers
            
        Returns:
            float: Estimated remaining range in km
        """
        if percentage <= 0:
            return 0.0
        
        # Account for battery degradation at low levels
        if percentage <= 20:
            efficiency_factor = 0.7  # Reduced efficiency at low battery
        else:
            efficiency_factor = 1.0
        
        return round((percentage / 100) * base_range_km * efficiency_factor, 1)

def update_battery_from_telemetry(vehicle_name, telemetry_data):
    """
    Update vehicle battery information from telemetry data
    
    Args:
        vehicle_name (str): TukTuk Vehicle document name
        telemetry_data (dict): Telemetry data containing voltage and other info
    """
    try:
        vehicle = frappe.get_doc("TukTuk Vehicle", vehicle_name)
        
        # Extract voltage from telemetry
        raw_voltage = telemetry_data.get("voltage", 0)
        
        if raw_voltage:
            # Store raw voltage
            vehicle.battery_voltage = flt(raw_voltage)
            
            # Convert to percentage
            new_percentage = BatteryConverter.voltage_to_percentage(raw_voltage)
            
            # Store previous reading
            if vehicle.battery_level:
                vehicle.last_battery_reading = vehicle.battery_level
            
            # Update current level
            vehicle.battery_level = new_percentage
            
            # Update timestamp
            vehicle.last_reported = now_datetime()
            
            # Check for battery alerts
            battery_status = BatteryConverter.get_battery_status(new_percentage)
            
            if battery_status["priority"] in ["high", "medium"]:
                send_battery_alert(vehicle, battery_status)
            
            vehicle.save(ignore_permissions=True)
            
            return {
                "success": True,
                "voltage": raw_voltage,
                "percentage": new_percentage,
                "status": battery_status["status"]
            }
        
        return {"success": False, "message": "No voltage data provided"}
        
    except Exception as e:
        frappe.log_error(f"Battery update error for {vehicle_name}: {str(e)}")
        return {"success": False, "message": str(e)}

def send_battery_alert(vehicle, battery_status):
    """
    Send battery alert notifications
    
    Args:
        vehicle: TukTuk Vehicle document
        battery_status (dict): Battery status information
    """
    try:
        # Get assigned driver
        driver = frappe.get_all("TukTuk Driver",
                               filters={"assigned_tuktuk": vehicle.name},
                               fields=["driver_name", "driver_primary_phone", "driver_email"],
                               limit=1)
        
        if not driver:
            return
        
        driver = driver[0]
        
        # Create alert message
        message = f"""
🔋 {battery_status['status']} Battery Alert
TukTuk: {vehicle.tuktuk_id}
Battery: {vehicle.battery_level}%
Action: {battery_status['action']}
Time: {frappe.utils.now_datetime().strftime('%H:%M')}
"""
        
        # Send SMS if enabled
        settings = frappe.get_single("TukTuk Settings")
        if settings.enable_sms_notifications and driver.driver_primary_phone:
            # TODO: Implement SMS gateway
            pass
        
        # Send email if enabled
        if settings.enable_email_notifications and driver.driver_email:
            frappe.sendmail(
                recipients=[driver.driver_email],
                subject=f"Battery Alert - TukTuk {vehicle.tuktuk_id}",
                message=message
            )
        
        # Create notification log
        frappe.get_doc({
            "doctype": "Notification Log",
            "subject": f"Battery Alert - {vehicle.tuktuk_id}",
            "email_content": message,
            "document_type": "TukTuk Vehicle",
            "document_name": vehicle.name,
            "for_user": "Administrator"
        }).insert(ignore_permissions=True)
        
    except Exception as e:
        frappe.log_error(f"Battery alert error: {str(e)}")

@frappe.whitelist()
def manual_battery_update(vehicle_name, voltage_or_percentage, is_voltage=True):
    """
    Manually update battery level
    
    Args:
        vehicle_name (str): Vehicle document name
        voltage_or_percentage (float): Either voltage or direct percentage
        is_voltage (bool): Whether the input is voltage (True) or percentage (False)
    """
    try:
        vehicle = frappe.get_doc("TukTuk Vehicle", vehicle_name)
        
        if is_voltage:
            # Convert voltage to percentage
            voltage = flt(voltage_or_percentage)
            percentage = BatteryConverter.voltage_to_percentage(voltage)
            vehicle.battery_voltage = voltage
        else:
            # Direct percentage input
            percentage = int(max(0, min(100, flt(voltage_or_percentage))))
            vehicle.battery_voltage = None  # Clear voltage if setting percentage directly
        
        # Store previous reading
        if vehicle.battery_level:
            vehicle.last_battery_reading = vehicle.battery_level
        
        vehicle.battery_level = percentage
        vehicle.last_reported = now_datetime()
        
        vehicle.save()
        
        # Get status info
        battery_status = BatteryConverter.get_battery_status(percentage)
        estimated_range = BatteryConverter.estimate_range_km(percentage)
        
        return {
            "success": True,
            "battery_level": percentage,
            "status": battery_status["status"],
            "estimated_range_km": estimated_range,
            "message": f"Battery updated to {percentage}% ({battery_status['status']})"
        }
        
    except Exception as e:
        frappe.throw(f"Failed to update battery: {str(e)}")

@frappe.whitelist()
def get_battery_analytics():
    """
    Get battery analytics for all vehicles
    """
    try:
        vehicles = frappe.get_all("TukTuk Vehicle",
                                 fields=["name", "tuktuk_id", "battery_level", "status", "last_reported"],
                                 order_by="battery_level asc")
        
        analytics = {
            "total_vehicles": len(vehicles),
            "average_battery": 0,
            "critical_count": 0,
            "low_count": 0, 
            "charging_count": 0,
            "vehicles_by_status": {},
            "battery_distribution": {
                "0-20%": 0,
                "21-50%": 0,
                "51-80%": 0,
                "81-100%": 0
            }
        }
        
        total_battery = 0
        
        for vehicle in vehicles:
            battery = vehicle.battery_level or 0
            total_battery += battery
            
            # Count by status
            status_key = vehicle.status or "Unknown"
            analytics["vehicles_by_status"][status_key] = analytics["vehicles_by_status"].get(status_key, 0) + 1
            
            # Count battery levels
            if battery <= 10:
                analytics["critical_count"] += 1
            elif battery <= 20:
                analytics["low_count"] += 1
            
            if vehicle.status == "Charging":
                analytics["charging_count"] += 1
            
            # Battery distribution
            if battery <= 20:
                analytics["battery_distribution"]["0-20%"] += 1
            elif battery <= 50:
                analytics["battery_distribution"]["21-50%"] += 1
            elif battery <= 80:
                analytics["battery_distribution"]["51-80%"] += 1
            else:
                analytics["battery_distribution"]["81-100%"] += 1
        
        if vehicles:
            analytics["average_battery"] = round(total_battery / len(vehicles), 1)
        
        return analytics
        
    except Exception as e:
        frappe.throw(f"Failed to get battery analytics: {str(e)}")

@frappe.whitelist()
def bulk_battery_update_from_csv(csv_data):
    """
    Bulk update battery levels from CSV data
    Expected format: tuktuk_id,voltage_or_percentage,is_voltage
    """
    try:
        import csv
        import io
        
        results = {
            "updated": 0,
            "failed": 0,
            "errors": []
        }
        
        csv_reader = csv.reader(io.StringIO(csv_data))
        
        for row_num, row in enumerate(csv_reader, 1):
            if len(row) < 2:
                continue
                
            try:
                tuktuk_id = row[0].strip()
                value = flt(row[1])
                is_voltage = row[2].lower() in ['true', '1', 'yes'] if len(row) > 2 else True
                
                # Find vehicle by tuktuk_id
                vehicle_name = frappe.get_value("TukTuk Vehicle", {"tuktuk_id": tuktuk_id}, "name")
                
                if not vehicle_name:
                    results["errors"].append(f"Row {row_num}: TukTuk {tuktuk_id} not found")
                    results["failed"] += 1
                    continue
                
                # Update battery
                result = manual_battery_update(vehicle_name, value, is_voltage)
                
                if result["success"]:
                    results["updated"] += 1
                else:
                    results["failed"] += 1
                    results["errors"].append(f"Row {row_num}: Update failed for {tuktuk_id}")
                    
            except Exception as e:
                results["failed"] += 1
                results["errors"].append(f"Row {row_num}: {str(e)}")
        
        return results
        
    except Exception as e:
        frappe.throw(f"Bulk update failed: {str(e)}")

# Scheduled task functions
def update_all_batteries_from_telemetry():
    """
    Scheduled task to update all vehicle batteries from telemetry
    """
    try:
        from tuktuk_management.api.telematics import TelematicsIntegration
        
        integration = TelematicsIntegration()
        
        # Get all vehicles with device IDs
        vehicles = frappe.get_all("TukTuk Vehicle",
                                 filters={"device_id": ["!=", ""]},
                                 fields=["name", "device_id", "tuktuk_id"])
        
        updated_count = 0
        
        for vehicle in vehicles:
            try:
                # Get telemetry data
                telemetry_data = integration.get_vehicle_data(vehicle.device_id)
                
                if telemetry_data:
                    result = update_battery_from_telemetry(vehicle.name, telemetry_data)
                    if result["success"]:
                        updated_count += 1
                        
            except Exception as e:
                frappe.log_error(f"Telemetry update failed for {vehicle.tuktuk_id}: {str(e)}")
        
        frappe.db.commit()
        frappe.log_error(f"Battery telemetry update completed: {updated_count} vehicles updated")
        
    except Exception as e:
        frappe.log_error(f"Scheduled battery update failed: {str(e)}")

def check_low_battery_alerts():
    """
    Scheduled task to check for low battery vehicles and send alerts
    """
    try:
        # Get vehicles with low battery that haven't been alerted recently
        low_battery_vehicles = frappe.db.sql("""
            SELECT name, tuktuk_id, battery_level, last_reported
            FROM `tabTukTuk Vehicle`
            WHERE battery_level <= 20 
            AND status NOT IN ('Charging', 'Maintenance')
            AND (last_reported IS NULL OR last_reported < DATE_SUB(NOW(), INTERVAL 1 HOUR))
        """, as_dict=True)
        
        for vehicle_data in low_battery_vehicles:
            try:
                vehicle = frappe.get_doc("TukTuk Vehicle", vehicle_data.name)
                battery_status = BatteryConverter.get_battery_status(vehicle.battery_level)
                send_battery_alert(vehicle, battery_status)
                
            except Exception as e:
                frappe.log_error(f"Low battery alert failed for {vehicle_data.tuktuk_id}: {str(e)}")
        
        if low_battery_vehicles:
            frappe.log_error(f"Low battery alerts sent for {len(low_battery_vehicles)} vehicles")
            
    except Exception as e:
        frappe.log_error(f"Low battery check failed: {str(e)}")