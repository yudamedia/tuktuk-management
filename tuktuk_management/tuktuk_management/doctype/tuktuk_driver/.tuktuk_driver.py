# ~/frappe-bench/apps/tuktuk_management/tuktuk_management/tuktuk_management/doctype/tuktuk_driver/tuktuk_driver.py
import frappe
from frappe.model.document import Document

class TukTukDriver(Document):
    def before_save(self):
        self.set_full_name()
        
    def set_full_name(self):
        parts = [self.driver_first_name, self.driver_middle_name, self.driver_last_name]
        self.driver_name = ' '.join(filter(None, parts))