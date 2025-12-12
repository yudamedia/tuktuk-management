# ~/frappe-bench/apps/tuktuk_management/tuktuk_management/tuktuk_management/doctype/tuktuk_driver/tuktuk_driver.py

import frappe
from frappe.model.document import Document
from frappe.utils import getdate, date_diff, now_datetime, flt
import re

class TukTukDriver(Document):
    def validate(self):
        validate_age(self)
        validate_mpesa_number(self)
        validate_phone_numbers(self)
        validate_email(self)
        validate_license(self)
        validate_emergency_contact(self)
        self.validate_deposit_settings()
        
    def before_save(self):
        self.set_full_name()
        self.generate_sunny_id()
        self.handle_deposit_changes()
        self.update_left_to_target()
        
    def set_full_name(self):
        parts = [self.driver_first_name, self.driver_middle_name, self.driver_last_name]
        self.driver_name = ' '.join(filter(None, parts))

    def generate_sunny_id(self):
        """
        Generate Sunny ID from document name
        Transforms DRV-112### to D112###
        """
        if self.name and self.name.startswith("DRV-"):
            # Strip "DRV-" and add "D" prefix
            self.sunny_id = "D" + self.name.replace("DRV-", "")    
        
    def update_left_to_target(self):
        """Calculate and update the countdown to daily target"""
        # Skip automatic update if manually set during reset
        if self.flags.get('skip_left_to_target_update'):
            return
        
        # If driver is unassigned, don't calculate target (they are on pause)
        if not self.assigned_tuktuk:
            self.left_to_target = 0
            return
            
        settings = frappe.get_single("TukTuk Settings")
        target = flt(self.daily_target or settings.global_daily_target)
        current = flt(self.current_balance or 0)
        
        # Countdown stops at zero (doesn't go negative)
        self.left_to_target = max(0, target - current)
        
    def on_update(self):
        self.handle_tuktuk_assignment()
        
    def validate_deposit_settings(self):
        """Validate deposit-related fields"""
        if self.deposit_required:
            if not self.initial_deposit_amount or self.initial_deposit_amount <= 0:
                frappe.throw("Initial deposit amount is required when deposit is mandatory")
        
        # Ensure current balance is not negative
        if self.current_deposit_balance and self.current_deposit_balance < 0:
            frappe.throw("Deposit balance cannot be negative")
            
    def handle_deposit_changes(self):
        """Handle changes to deposit amounts and create transaction records"""
        if self.is_new():
            # New driver - create initial deposit transaction if required
            if self.deposit_required and self.initial_deposit_amount:
                self.current_deposit_balance = self.initial_deposit_amount
                self.add_deposit_transaction(
                    transaction_type="Initial Deposit",
                    amount=self.initial_deposit_amount,
                    description="Initial deposit upon driver registration"
                )
        else:
            # Check if initial deposit amount changed (for adjustments)
            old_initial = frappe.db.get_value("TukTuk Driver", self.name, "initial_deposit_amount") or 0
            if self.initial_deposit_amount != old_initial and not self.is_new():
                difference = flt(self.initial_deposit_amount) - flt(old_initial)
                if difference != 0:
                    self.current_deposit_balance = flt(self.current_deposit_balance) + difference
                    self.add_deposit_transaction(
                        transaction_type="Adjustment",
                        amount=difference,
                        description=f"Deposit adjustment: {old_initial} → {self.initial_deposit_amount}"
                    )
        
    def add_deposit_transaction(self, transaction_type, amount, description="", reference=""):
        """Add a deposit transaction record"""
        self.append("deposit_transactions", {
            "transaction_date": getdate(),
            "transaction_type": transaction_type,
            "amount": amount,
            "balance_after_transaction": flt(self.current_deposit_balance),
            "description": description,
            "transaction_reference": reference,
            "approved_by": frappe.session.user
        })
        
    def handle_tuktuk_assignment(self):
        """Update TukTuk status and assigned driver when assigned to driver"""
        if self.has_value_changed('assigned_tuktuk'):
            # Get old value before clearing to detect reassignment
            old_value = frappe.db.get_value("TukTuk Driver", self.name, "assigned_tuktuk")
            is_reassignment = bool(old_value and self.assigned_tuktuk)
            
            # Clear old assignment
            if old_value:
                old_tuktuk = frappe.get_doc("TukTuk Vehicle", old_value)
                old_tuktuk.status = "Available"
                old_tuktuk.update_assigned_driver_name()
                old_tuktuk.save()
                
            # Set new assignment
            if self.assigned_tuktuk:
                new_tuktuk = frappe.get_doc("TukTuk Vehicle", self.assigned_tuktuk)
                if new_tuktuk.status != "Available":
                    frappe.throw(f"TukTuk {self.assigned_tuktuk} is not available for assignment")
                
                # CRITICAL FIX: Check if tuktuk is already assigned to another driver
                existing_driver = frappe.db.get_value(
                    "TukTuk Driver",
                    {"assigned_tuktuk": self.assigned_tuktuk, "name": ["!=", self.name]},
                    "name"
                )
                if existing_driver:
                    existing_driver_name = frappe.db.get_value("TukTuk Driver", existing_driver, "driver_name")
                    frappe.throw(f"TukTuk {self.assigned_tuktuk} is already assigned to driver {existing_driver_name}")
                
                new_tuktuk.status = "Assigned"
                new_tuktuk.update_assigned_driver_name()
                new_tuktuk.save()
                
                # If this is a reassignment during operating hours, preserve balance and target
                if is_reassignment:
                    from tuktuk_management.api.tuktuk import is_within_operating_hours
                    if is_within_operating_hours():
                        # Preserve balance and target tracking during reassignment
                        frappe.msgprint(f"Driver {self.driver_name} reassigned to new TukTuk. Balance and target tracking preserved.")
                        return  # Exit early to preserve balance/target
            else:
                # Driver became unassigned - reset target tracking (they are on pause)
                self.current_balance = 0
                self.left_to_target = 0
                frappe.msgprint(f"Driver {self.driver_name} is now unassigned and paused from daily targets")
    
    def process_target_miss_deduction(self, missed_amount):
        """Process deduction from deposit for missed targets (only if driver allows it)"""
        if not self.allow_target_deduction_from_deposit:
            frappe.msgprint("Driver has not allowed target deductions from deposit")
            return False
            
        if not self.current_deposit_balance or self.current_deposit_balance < missed_amount:
            frappe.msgprint(f"Insufficient deposit balance. Available: {self.current_deposit_balance}, Required: {missed_amount}")
            return False
            
        # Deduct from deposit
        self.current_deposit_balance = flt(self.current_deposit_balance) - flt(missed_amount)
        
        # Add transaction record
        self.add_deposit_transaction(
            transaction_type="Target Deduction",
            amount=-missed_amount,  # Negative because it's a deduction
            description=f"Deduction for missed daily target: {missed_amount} KSH"
        )
        
        self.save()
        return True
    
    def process_damage_deduction(self, damage_amount, description, reference=""):
        """Process deduction from deposit for vehicle damage"""
        if not self.current_deposit_balance or self.current_deposit_balance < damage_amount:
            frappe.throw(f"Insufficient deposit balance for damage deduction. Available: {self.current_deposit_balance}, Required: {damage_amount}")
            
        # Deduct from deposit
        self.current_deposit_balance = flt(self.current_deposit_balance) - flt(damage_amount)
        
        # Add transaction record
        self.add_deposit_transaction(
            transaction_type="Damage Deduction",
            amount=-damage_amount,  # Negative because it's a deduction
            description=f"Vehicle damage deduction: {description}",
            reference=reference
        )
        
        self.save()
        frappe.msgprint(f"Damage deduction of {damage_amount} KSH processed successfully")
    
    def process_deposit_top_up(self, top_up_amount, reference="", description=""):
        """Process deposit top-up by driver"""
        if not top_up_amount or top_up_amount <= 0:
            frappe.throw("Top-up amount must be greater than 0")
            
        # Add to deposit balance
        self.current_deposit_balance = flt(self.current_deposit_balance) + flt(top_up_amount)
        
        # Add transaction record
        self.add_deposit_transaction(
            transaction_type="Top Up",
            amount=top_up_amount,
            description=description or "Driver deposit top-up",
            reference=reference
        )
        
        self.save()
        frappe.msgprint(f"Deposit top-up of {top_up_amount} KSH processed successfully")
    
    def process_exit_refund(self, exit_date=None):
        """Process driver exit and calculate refund amount"""
        if not exit_date:
            exit_date = getdate()
            
        self.exit_date = exit_date
        self.refund_amount = self.current_deposit_balance
        self.refund_status = "Pending"
        
        # Clear tuktuk assignment
        if self.assigned_tuktuk:
            tuktuk = frappe.get_doc("TukTuk Vehicle", self.assigned_tuktuk)
            tuktuk.status = "Available"
            tuktuk.save()
            self.assigned_tuktuk = ""
        
        # Add final transaction record
        if self.refund_amount > 0:
            self.add_deposit_transaction(
                transaction_type="Refund",
                amount=-self.refund_amount,  # Negative because it's leaving the deposit
                description=f"Exit refund processed on {exit_date}"
            )
            
            # Zero out the deposit balance
            self.current_deposit_balance = 0
        
        self.save()
        frappe.msgprint(f"Driver exit processed. Refund amount: {self.refund_amount} KSH")
    
    def restore_terminated_driver(self):
        """Restore a terminated driver by reversing the termination process"""
        # Check if driver has been terminated or has refund data
        if not self.exit_date and not self.refund_amount:
            frappe.throw(f"Driver {self.driver_name} has not been terminated or has no refund data to restore")
        
        # Store the refund amount (this was their original deposit balance)
        original_deposit = flt(self.refund_amount) if self.refund_amount else 0
        
        # Log the restoration action
        frappe.log_error(
            f"Restoring terminated driver: {self.driver_name} (ID: {self.name})\n"
            f"Exit Date: {self.exit_date}\n"
            f"Original Deposit to Restore: {original_deposit} KSH\n"
            f"Consecutive Misses Before: {self.consecutive_misses}\n"
            f"Current Balance Before: {self.current_balance}\n"
            f"Restored By: {frappe.session.user}",
            "Driver Restoration"
        )
        
        # Remove "Refund" type transactions from deposit_transactions child table
        transactions_to_remove = []
        for transaction in self.deposit_transactions:
            if transaction.transaction_type == "Refund":
                transactions_to_remove.append(transaction)
        
        for transaction in transactions_to_remove:
            self.remove(transaction)
        
        # Restore the deposit balance
        self.current_deposit_balance = original_deposit
        
        # Add a restoration transaction record for audit trail (using "Adjustment" type which is allowed)
        if original_deposit > 0:
            self.add_deposit_transaction(
                transaction_type="Adjustment",
                amount=original_deposit,
                description=f"Driver restoration - reversed termination from {self.exit_date or 'manual deletion'}. Restored by {frappe.session.user}"
            )
        
        # Clear termination-related fields
        self.exit_date = None
        self.refund_amount = 0
        self.refund_status = None
        
        # Reset performance tracking
        self.consecutive_misses = 0
        self.current_balance = 0
        
        # Save the document
        self.save()
        
        frappe.msgprint(f"✅ Driver {self.driver_name} has been successfully restored with deposit balance of {original_deposit} KSH")
        
        return {
            "success": True,
            "driver_name": self.driver_name,
            "restored_deposit": original_deposit,
            "message": "Driver successfully restored"
        }

# Validation functions (existing ones remain the same)
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
    """Validate driving license - ensure it's provided"""
    if not doc.driver_license:
        frappe.throw("Driving License is required")
    
    # Remove pattern validation as Kenyan driving licenses have no uniform format
    # Just ensure the license number is not empty and trim whitespace
    doc.driver_license = doc.driver_license.strip()

def validate_emergency_contact(doc):
    """Validate emergency contact details"""
    if doc.driver_emergency_phone:
        if not doc.driver_emergency_name:
            frappe.throw("Emergency contact name is required when phone is provided")
            
        pattern = r'^(?:\+254|254|0)\d{9}$'
        if not re.match(pattern, doc.driver_emergency_phone.replace(' ', '')):
            frappe.throw("Invalid emergency contact phone number format")

# API Methods for deposit management
@frappe.whitelist()
def process_deposit_top_up(driver_name, amount, reference="", description=""):
    """API method to process deposit top-up"""
    driver = frappe.get_doc("TukTuk Driver", driver_name)
    driver.process_deposit_top_up(float(amount), reference, description)
    return {"success": True, "new_balance": driver.current_deposit_balance}

@frappe.whitelist()
def process_damage_deduction(driver_name, amount, description, reference=""):
    """API method to process damage deduction"""
    driver = frappe.get_doc("TukTuk Driver", driver_name)
    driver.process_damage_deduction(float(amount), description, reference)
    return {"success": True, "new_balance": driver.current_deposit_balance}

@frappe.whitelist()
def process_target_miss_deduction(driver_name, missed_amount):
    """API method to process target miss deduction (only if driver allows it)"""
    driver = frappe.get_doc("TukTuk Driver", driver_name)
    success = driver.process_target_miss_deduction(float(missed_amount))
    return {"success": success, "new_balance": driver.current_deposit_balance if success else None}

@frappe.whitelist()
def process_driver_exit(driver_name, exit_date=None):
    """API method to process driver exit and refund"""
    driver = frappe.get_doc("TukTuk Driver", driver_name)
    driver.process_exit_refund(exit_date)
    return {"success": True, "refund_amount": driver.refund_amount}

@frappe.whitelist()
def get_deposit_summary(driver_name):
    """Get comprehensive deposit summary for a driver"""
    driver = frappe.get_doc("TukTuk Driver", driver_name)
    
    # Calculate totals from transactions
    total_deposits = sum([t.amount for t in driver.deposit_transactions if t.amount > 0])
    total_deductions = sum([t.amount for t in driver.deposit_transactions if t.amount < 0])
    
    return {
        "driver_name": driver.driver_name,
        "initial_deposit": driver.initial_deposit_amount,
        "current_balance": driver.current_deposit_balance,
        "total_deposits": total_deposits,
        "total_deductions": abs(total_deductions),
        "allows_target_deduction": driver.allow_target_deduction_from_deposit,
        "transaction_count": len(driver.deposit_transactions),
        "exit_date": driver.exit_date,
        "refund_status": driver.refund_status,
        "refund_amount": driver.refund_amount
    }