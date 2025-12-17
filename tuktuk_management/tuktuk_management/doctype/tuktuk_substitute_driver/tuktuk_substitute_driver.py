# Copyright (c) 2024, Yuda and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime, today, get_datetime, flt

class TukTukSubstituteDriver(Document):
    def validate(self):
        """Validate substitute driver data before saving"""
        # Ensure driver_type is always set to Substitute
        self.driver_type = "Substitute"
        
        # Validate phone number format
        if self.phone_number and not self.phone_number.startswith('+'):
            if self.phone_number.startswith('0'):
                self.phone_number = '+254' + self.phone_number[1:]
            elif self.phone_number.startswith('254'):
                self.phone_number = '+' + self.phone_number
        
        # Calculate average daily earnings if total_days_worked > 0
        if self.total_days_worked and self.total_days_worked > 0:
            self.average_daily_earnings = flt(self.total_earnings) / flt(self.total_days_worked)
        else:
            self.average_daily_earnings = 0
    
    def before_save(self):
        """Actions before saving the document"""
        # If assigned_tuktuk changed, update assignment_date
        if self.has_value_changed('assigned_tuktuk') and self.assigned_tuktuk:
            self.assignment_date = now_datetime()
            self.status = "On Assignment"
        elif not self.assigned_tuktuk:
            self.status = "Active"
            self.assignment_date = None
    
    def on_update(self):
        """Actions after document is updated"""
        # Update vehicle status if assignment changed
        if self.has_value_changed('assigned_tuktuk'):
            self.update_vehicle_assignment()
    
    def update_vehicle_assignment(self):
        """Update the assigned vehicle's status"""
        # Unassign from old vehicle if exists
        old_vehicle = self.get_doc_before_save()
        if old_vehicle and old_vehicle.assigned_tuktuk and old_vehicle.assigned_tuktuk != self.assigned_tuktuk:
            try:
                old_tuktuk = frappe.get_doc("TukTuk Vehicle", old_vehicle.assigned_tuktuk)
                old_tuktuk.current_substitute_driver = None
                old_tuktuk.substitute_assignment_date = None
                # Reset to Available or back to regular driver if exists
                if old_tuktuk.assigned_driver:
                    old_tuktuk.status = "Assigned"
                else:
                    old_tuktuk.status = "Available"
                old_tuktuk.save(ignore_permissions=True)
            except Exception as e:
                frappe.log_error(f"Error updating old vehicle: {str(e)}")
        
        # Assign to new vehicle if exists
        if self.assigned_tuktuk:
            try:
                new_tuktuk = frappe.get_doc("TukTuk Vehicle", self.assigned_tuktuk)
                new_tuktuk.current_substitute_driver = self.name
                new_tuktuk.substitute_assignment_date = now_datetime()
                new_tuktuk.status = "Subbed"
                new_tuktuk.save(ignore_permissions=True)
            except Exception as e:
                frappe.log_error(f"Error updating new vehicle: {str(e)}")
                frappe.throw(f"Could not assign vehicle: {str(e)}")
    
    def reset_daily_targets(self):
        """Reset daily targets - called by scheduler at start of operating hours"""
        # For substitute drivers, we simply reset to 0 - no rollover
        self.todays_earnings = 0
        self.todays_target_contribution = 0
        self.target_balance = self.get_daily_target()
        self.save(ignore_permissions=True)
    
    def get_daily_target(self):
        """Get the daily target for this driver"""
        if self.daily_target:
            return flt(self.daily_target)
        
        # Get global setting
        settings = frappe.get_single("TukTuk Settings")
        return flt(settings.global_daily_target) if settings.global_daily_target else 3000.0
    
    def get_fare_percentage(self):
        """Get the fare percentage for this driver"""
        if self.fare_percentage_to_driver:
            return flt(self.fare_percentage_to_driver)
        
        # Get global setting
        settings = frappe.get_single("TukTuk Settings")
        return flt(settings.global_fare_percentage_to_driver) if settings.global_fare_percentage_to_driver else 50.0
    
    def process_transaction(self, transaction_amount, transaction_doc):
        """
        Process a transaction for this substitute driver
        Substitute drivers ALWAYS get the split percentage, never 100%
        """
        amount = flt(transaction_amount)
        fare_percentage = self.get_fare_percentage()
        daily_target = self.get_daily_target()
        
        # Calculate driver share - substitute always gets the percentage split
        driver_share = amount * (fare_percentage / 100)
        
        # All goes to target contribution for substitute drivers
        target_contribution = amount - driver_share
        
        # Update today's totals
        self.todays_earnings = flt(self.todays_earnings) + driver_share
        self.todays_target_contribution = flt(self.todays_target_contribution) + target_contribution
        self.target_balance = daily_target - self.todays_target_contribution
        
        # Update lifetime totals
        self.total_earnings = flt(self.total_earnings) + driver_share
        self.total_rides = (self.total_rides or 0) + 1
        
        # Update last worked date
        if self.last_worked_date != today():
            self.last_worked_date = today()
            self.total_days_worked = (self.total_days_worked or 0) + 1
        
        # Save without triggering validation loops
        self.save(ignore_permissions=True)
        
        return {
            "driver_share": driver_share,
            "target_contribution": target_contribution,
            "target_met": self.todays_target_contribution >= daily_target,
            "bonus_applicable": False,  # Substitutes never get bonuses
            "driver_type": "Substitute"
        }


# API Methods
@frappe.whitelist()
def get_available_substitutes():
    """Get list of available substitute drivers (not currently assigned)"""
    return frappe.get_all(
        "TukTuk Substitute Driver",
        filters={"status": "Active", "assigned_tuktuk": ["is", "not set"]},
        fields=["name", "first_name", "last_name", "phone_number", "total_days_worked", "average_daily_earnings"]
    )


@frappe.whitelist()
def suggest_substitute_for_vehicle(vehicle_name):
    """Suggest best available substitute driver for an AVAILABLE vehicle"""
    available_subs = get_available_substitutes()
    
    if not available_subs:
        return {"success": False, "message": "No substitute drivers available"}
    
    # Verify vehicle is available (no regular driver)
    vehicle = frappe.get_doc("TukTuk Vehicle", vehicle_name)
    if vehicle.assigned_driver:
        return {
            "success": False, 
            "message": "This vehicle has a regular driver. Substitutes are only for available vehicles."
        }
    
    # Sort by total days worked (experience) and average earnings
    sorted_subs = sorted(
        available_subs,
        key=lambda x: (x.get('total_days_worked', 0), x.get('average_daily_earnings', 0)),
        reverse=True
    )
    
    return {
        "success": True,
        "suggested_driver": sorted_subs[0],
        "all_available": sorted_subs
    }





@frappe.whitelist()
def get_available_vehicles_for_substitute():
    """Get list of AVAILABLE vehicles (no regular driver) for substitute assignment"""
    return frappe.get_all(
        "TukTuk Vehicle",
        filters={
            "assigned_driver": ["is", "not set"],  # NO regular driver (key change)
            "current_substitute_driver": ["is", "not set"],  # No substitute assigned
            "status": ["not in", ["Maintenance", "Offline"]]  # Not in maintenance
        },
        fields=[
            "name",
            "tuktuk_id",
            "status",
            "battery_level"
        ]
    )

@frappe.whitelist()
def assign_substitute_to_vehicle(substitute_driver, vehicle_name):
    """Assign a substitute driver to an AVAILABLE vehicle (no regular driver)"""
    try:
        # Get the substitute driver
        sub_driver = frappe.get_doc("TukTuk Substitute Driver", substitute_driver)
        
        # Check if substitute is available
        if sub_driver.status != "Active":
            return {"success": False, "message": "Substitute driver is not active"}
        
        if sub_driver.assigned_tuktuk:
            return {"success": False, "message": "Substitute driver is already assigned to another vehicle"}
        
        # Get the vehicle
        vehicle = frappe.get_doc("TukTuk Vehicle", vehicle_name)
        
        # UPDATED LOGIC: Vehicle should NOT have a regular driver (for available vehicles)
        # This is the key change - substitutes are for vehicles without regular drivers
        if vehicle.assigned_driver:
            return {
                "success": False, 
                "message": "This vehicle already has a regular driver assigned. Substitutes are only for available vehicles."
            }
        
        # Check if vehicle already has a substitute
        if vehicle.current_substitute_driver:
            return {"success": False, "message": "Vehicle already has a substitute driver assigned"}
        
        # Assign the substitute
        sub_driver.assigned_tuktuk = vehicle_name
        sub_driver.save()
        
        return {
            "success": True,
            "message": f"Substitute {sub_driver.first_name} {sub_driver.last_name} assigned to {vehicle_name}"
        }
    
    except Exception as e:
        frappe.log_error(f"Error assigning substitute: {str(e)}")
        return {"success": False, "message": str(e)}

@frappe.whitelist()
def unassign_substitute_from_vehicle(substitute_driver):
    """Unassign a substitute driver from their current vehicle"""
    try:
        sub_driver = frappe.get_doc("TukTuk Substitute Driver", substitute_driver)
        
        if not sub_driver.assigned_tuktuk:
            return {"success": False, "message": "Substitute driver is not assigned to any vehicle"}
        
        vehicle_name = sub_driver.assigned_tuktuk
        sub_driver.assigned_tuktuk = None
        sub_driver.save()
        
        return {
            "success": True,
            "message": f"Substitute unassigned from {vehicle_name}"
        }
    
    except Exception as e:
        frappe.log_error(f"Error unassigning substitute: {str(e)}")
        return {"success": False, "message": str(e)}
