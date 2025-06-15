# ~/frappe-bench/apps/tuktuk_management/tuktuk_management/tuktuk_management/doctype/tuktuk_driver/tuktuk_driver.py

import frappe
from frappe.model.document import Document
from frappe.utils import getdate, date_diff
import re

class TukTukDriver(Document):
    def validate(self):
        validate_age(self)
        validate_mpesa_number(self)
        validate_phone_numbers(self)
        validate_email(self)
        validate_license(self)
        validate_emergency_contact(self)
        
    def before_save(self):
        self.set_full_name()
        
    def set_full_name(self):
        parts = [self.driver_first_name, self.driver_middle_name, self.driver_last_name]
        self.driver_name = ' '.join(filter(None, parts))
        
    def on_update(self):
        self.handle_tuktuk_assignment()
        
    def handle_tuktuk_assignment(self):
        """Update TukTuk status when assigned to driver"""
        if self.has_value_changed('assigned_tuktuk'):
            # Clear old assignment
            old_value = frappe.db.get_value("TukTuk Driver", self.name, "assigned_tuktuk")
            if old_value:
                old_tuktuk = frappe.get_doc("TukTuk Vehicle", old_value)
                old_tuktuk.status = "Available"
                old_tuktuk.save()
                
        # Set new assignment
            if self.assigned_tuktuk:
                new_tuktuk = frappe.get_doc("TukTuk Vehicle", self.assigned_tuktuk)
                if new_tuktuk.status != "Available":
                    frappe.throw(f"TukTuk {self.assigned_tuktuk} is not available for assignment")
                new_tuktuk.status = "Assigned"
                new_tuktuk.save()
        
def validate_age(doc):
    """Ensure driver meets minimum age requirement"""
    if not doc.driver_dob:
        frappe.throw("Date of Birth is required")
        
    dob = getdate(doc.driver_dob)
    today = getdate()
    age = date_diff(today, dob) / 365.25
    
    if age < 18:
        frappe.throw("Driver must be at least 18 years old")
    if age > 65:
        frappe.throw("Driver age exceeds maximum limit of 65 years")

def validate_mpesa_number(doc):
    """Validate MPesa phone number format"""
    if not doc.mpesa_number:
        frappe.throw("MPesa number is required")
        
    cleaned_number = str(doc.mpesa_number).replace(' ', '')
    pattern = r'^(?:\+254|254|0)\d{9}$'
    if not re.match(pattern, cleaned_number):
        frappe.throw("Invalid MPesa number format. Use format: +254XXXXXXXXX or 0XXXXXXXXX")
        
    if cleaned_number.startswith('+'):
        cleaned_number = cleaned_number[1:]
    elif cleaned_number.startswith('0'):
        cleaned_number = '254' + cleaned_number[1:]
            
    doc.mpesa_number = cleaned_number

def validate_phone_numbers(doc):
    """Validate phone number formats"""
    if doc.driver_primary_phone:
        pattern = r'^(?:\+254|254|0)\d{9}$'
        if not re.match(pattern, doc.driver_primary_phone.replace(' ', '')):
            frappe.throw("Invalid primary phone number format")
            
    if doc.driver_secondary_phone:
        pattern = r'^(?:\+254|254|0)\d{9}$'
        if not re.match(pattern, doc.driver_secondary_phone.replace(' ', '')):
            frappe.throw("Invalid secondary phone number format")

def validate_email(doc):
    """Validate email format if provided"""
    if doc.driver_email:
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(pattern, doc.driver_email):
            frappe.throw("Invalid email format")

def validate_license(doc):
    """Validate driving license format"""
    if not doc.driver_license:
        frappe.throw("Driving License is required")
        
    if not re.match(r'^[A-Z]\d{6}$', doc.driver_license.upper()):
        frappe.throw("Invalid driving license format. Must be letter followed by 6 digits (e.g., B123456)")

def validate_emergency_contact(doc):
    """Validate emergency contact details"""
    if doc.driver_emergency_phone:
        if not doc.driver_emergency_name:
            frappe.throw("Emergency contact name is required when phone is provided")
            
        pattern = r'^(?:\+254|254|0)\d{9}$'
        if not re.match(pattern, doc.driver_emergency_phone.replace(' ', '')):
            frappe.throw("Invalid emergency contact phone number format")