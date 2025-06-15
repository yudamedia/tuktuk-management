# ~/frappe-bench/apps/tuktuk_management/tuktuk_management/tests/test_data.py

import frappe
from frappe.utils import now_datetime, add_to_date
import logging

def create_test_data():
    """Create test data for Sunny TukTuk system"""
    try:
        # First check if data already exists
        if frappe.db.exists("TukTuk Settings", "TukTuk Settings"):
            print("Test data already exists. Skipping creation.")
            return

        print("Creating test data...")
        
        # Create TukTuk Settings
        settings = frappe.get_doc({
            "doctype": "TukTuk Settings",
            "operating_hours_start": "06:00:00",
            "operating_hours_end": "00:00:00",
            "global_daily_target": 3000,
            "global_fare_percentage": 50,
            "bonus_enabled": 1,
            "bonus_amount": 200,
            "global_rental_initial": 500,
            "global_rental_hourly": 200,
            "mpesa_paybill": "123456",
            "mpesa_api_key": "test_api_key",
            "mpesa_api_secret": "test_api_secret",
            "enable_sms_notifications": 1,
            "enable_email_notifications": 1
        })
        settings.insert()
        print("Created TukTuk Settings")

        # Create Test TukTuks
        tuktuk_data = [
            {
                "tuktuk_id": "KAA001T",
                "tuktuk_logbook": "LOG001",
                "battery_level": 100,
                "tuktuk_make": "Bajaj",
                "tuktuk_colour": "Blue",
                "status": "Available",
                "mpesa_account": "001"
            },
            {
                "tuktuk_id": "KAA002T",
                "tuktuk_logbook": "LOG002",
                "battery_level": 25,
                "tuktuk_make": "Bajaj",
                "tuktuk_colour": "Green",
                "status": "Available",
                "mpesa_account": "002"
            },
            {
                "tuktuk_id": "KAA003T",
                "tuktuk_logbook": "LOG003",
                "battery_level": 80,
                "tuktuk_make": "Bajaj",
                "tuktuk_colour": "Red",
                "status": "Charging",
                "mpesa_account": "003"
            }
        ]

        created_tuktuks = []
        for tuktuk in tuktuk_data:
            doc = frappe.get_doc({
                "doctype": "TukTuk Vehicle",
                **tuktuk
            })
            doc.insert()
            created_tuktuks.append(doc.name)
        print(f"Created {len(created_tuktuks)} TukTuks")

        # Create Test Drivers
        driver_data = [
            {
                "driver_first_name": "John",
                "driver_middle_name": "Kamau",
                "driver_last_name": "Mwangi",
                "driver_dob": "1990-01-15",
                "driver_national_id": "12345678",
                "driver_license": "B123456",
                "driver_primary_phone": "254700123456",
                "driver_email": "john@example.com",
                "mpesa_number": "254700123456",
                "assigned_tuktuk": created_tuktuks[0],
                "daily_target": 3500,
                "fare_percentage": 60,
                "current_balance": 2000,
                "consecutive_misses": 0
            },
            {
                "driver_first_name": "David",
                "driver_middle_name": "Kiprop",
                "driver_last_name": "Korir",
                "driver_dob": "1985-06-20",
                "driver_national_id": "23456789",
                "driver_license": "B234567",
                "driver_primary_phone": "254700234567",
                "driver_email": "david@example.com",
                "mpesa_number": "254700234567",
                "assigned_tuktuk": created_tuktuks[1],
                "current_balance": 500,
                "consecutive_misses": 2
            }
        ]

        created_drivers = []
        for driver in driver_data:
            doc = frappe.get_doc({
                "doctype": "TukTuk Driver",
                **driver
            })
            doc.insert()
            created_drivers.append(doc.name)
        print(f"Created {len(created_drivers)} Drivers")

        # Create Test Transactions
        for i, driver in enumerate(created_drivers):
            tuktuk = created_tuktuks[i]
            transaction = frappe.get_doc({
                "doctype": "TukTuk Transaction",
                "transaction_id": f"MPESA12345{i}",
                "tuktuk": tuktuk,
                "driver": driver,
                "amount": 500,
                "driver_share": 250,
                "target_contribution": 250,
                "customer_phone": f"25470099999{i}",
                "timestamp": now_datetime(),
                "payment_status": "Completed"
            })
            transaction.insert()
        print("Created test transactions")

        # Create Test Rental
        rental = frappe.get_doc({
            "doctype": "TukTuk Rental",
            "driver": created_drivers[1],
            "rented_tuktuk": created_tuktuks[2],
            "start_time": add_to_date(now_datetime(), hours=-3),
            "rental_fee": 500,
            "status": "Active",
            "notes": "Temporary rental while primary tuktuk charges"
        })
        rental.insert()
        print("Created test rental")

        print("Test data creation completed successfully")
        
    except Exception as e:
        print(f"Error creating test data: {str(e)}")
        frappe.log_error(f"Test Data Creation Error: {str(e)}")
        raise

if __name__ == "__main__":
    create_test_data()