import frappe
from frappe.model.document import Document

class TukTukRental(Document):
    def after_insert(self):
        """Update vehicle assignment after rental is created"""
        self.update_vehicle_assigned_driver()
    
    def on_update(self):
        """Update vehicle assignment when rental is updated"""
        self.update_vehicle_assigned_driver()
    
    def on_cancel(self):
        """Update vehicle assignment when rental is cancelled"""
        self.update_vehicle_assigned_driver()
    
    def update_vehicle_assigned_driver(self):
        """Update the assigned driver name in the related vehicle"""
        if self.rented_tuktuk:
            try:
                vehicle = frappe.get_doc("TukTuk Vehicle", self.rented_tuktuk)
                vehicle.update_assigned_driver_name()
                vehicle.save(ignore_permissions=True)
            except Exception as e:
                frappe.logger().error(f"Failed to update vehicle assigned driver: {str(e)}")