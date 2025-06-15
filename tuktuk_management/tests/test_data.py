# ~/frappe-bench/apps/tuktuk_management/tuktuk_management/tests/test_data.py
import frappe
from frappe.utils import now_datetime, add_to_date, getdate

# Base test data
base_tuktuks = [
    {
        "tuktuk_id": "KAA001T",
        "tuktuk_logbook": "LOG001",
        "battery_level": 100,
        "tuktuk_make": "Bajaj",
        "tuktuk_colour": "Blue",
        "status": "Available",
        "mpesa_account": "001",
        "rental_rate_initial": 600,
        "rental_rate_hourly": 250
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

extra_tuktuks = [
    {"tuktuk_id": "KAA004T", "tuktuk_logbook": "LOG004", "battery_level": 90, "tuktuk_make": "Bajaj", "tuktuk_colour": "Yellow", "status": "Available", "mpesa_account": "004"},
    {"tuktuk_id": "KAA005T", "tuktuk_logbook": "LOG005", "battery_level": 35, "tuktuk_make": "Piaggio", "tuktuk_colour": "White", "status": "Available", "mpesa_account": "005"},
    {"tuktuk_id": "KAA006T", "tuktuk_logbook": "LOG006", "battery_level": 75, "tuktuk_make": "Bajaj", "tuktuk_colour": "Black", "status": "Maintenance", "mpesa_account": "006"},
    {"tuktuk_id": "KAA007T", "tuktuk_logbook": "LOG007", "battery_level": 100, "tuktuk_make": "Piaggio", "tuktuk_colour": "Silver", "status": "Available", "mpesa_account": "007"},
    {"tuktuk_id": "KAA008T", "tuktuk_logbook": "LOG008", "battery_level": 15, "tuktuk_make": "Bajaj", "tuktuk_colour": "Orange", "status": "Charging", "mpesa_account": "008"},
    {"tuktuk_id": "KAA009T", "tuktuk_logbook": "LOG009", "battery_level": 95, "tuktuk_make": "Piaggio", "tuktuk_colour": "Purple", "status": "Available", "mpesa_account": "009"},
    {"tuktuk_id": "KAA010T", "tuktuk_logbook": "LOG010", "battery_level": 60, "tuktuk_make": "Bajaj", "tuktuk_colour": "Green", "status": "Available", "mpesa_account": "010"},
    {"tuktuk_id": "KAA011T", "tuktuk_logbook": "LOG011", "battery_level": 85, "tuktuk_make": "Piaggio", "tuktuk_colour": "Blue", "status": "Available", "mpesa_account": "011"},
    {"tuktuk_id": "KAA012T", "tuktuk_logbook": "LOG012", "battery_level": 45, "tuktuk_make": "Bajaj", "tuktuk_colour": "Red", "status": "Available", "mpesa_account": "012"},
    {"tuktuk_id": "KAA013T", "tuktuk_logbook": "LOG013", "battery_level": 70, "tuktuk_make": "Piaggio", "tuktuk_colour": "Yellow", "status": "Available", "mpesa_account": "013"}
]

base_drivers = [
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
        "current_balance": 500,
        "consecutive_misses": 2
    }
]

extra_drivers = [
    {
        "driver_first_name": "James", "driver_middle_name": "Ochieng", "driver_last_name": "Otieno",
        "driver_dob": "1988-03-25", "driver_national_id": "34567890", "driver_license": "B345678",
        "driver_primary_phone": "254700345678", "driver_email": "james@example.com",
        "mpesa_number": "254700345678", "daily_target": 4000, "fare_percentage": 55
    },
    {
        "driver_first_name": "Peter", "driver_middle_name": "Kimani", "driver_last_name": "Njoroge",
        "driver_dob": "1992-07-12", "driver_national_id": "45678901", "driver_license": "B456789",
        "driver_primary_phone": "254700456789", "driver_email": "peter@example.com",
        "mpesa_number": "254700456789", "consecutive_misses": 1
    },
    {
        "driver_first_name": "Samuel", "driver_middle_name": "Kiprotich", "driver_last_name": "Ruto",
        "driver_dob": "1995-11-30", "driver_national_id": "56789012", "driver_license": "B567890",
        "driver_primary_phone": "254700567890", "driver_email": "samuel@example.com",
        "mpesa_number": "254700567890"
    },
    {
        "driver_first_name": "Joseph", "driver_middle_name": "Maina", "driver_last_name": "Kariuki",
        "driver_dob": "1987-09-15", "driver_national_id": "67890123", "driver_license": "B678901",
        "driver_primary_phone": "254700678901", "driver_email": "joseph@example.com",
        "mpesa_number": "254700678901", "daily_target": 3200
    },
    {
        "driver_first_name": "Michael", "driver_middle_name": "Omondi", "driver_last_name": "Okoth",
        "driver_dob": "1993-04-20", "driver_national_id": "78901234", "driver_license": "B789012",
        "driver_primary_phone": "254700789012", "driver_email": "michael@example.com",
        "mpesa_number": "254700789012"
    },
    {
        "driver_first_name": "George", "driver_middle_name": "Mutua", "driver_last_name": "Musyoka",
        "driver_dob": "1991-12-05", "driver_national_id": "89012345", "driver_license": "B890123",
        "driver_primary_phone": "254700890123", "driver_email": "george@example.com",
        "mpesa_number": "254700890123", "fare_percentage": 58
    }
]

def create_additional_transactions(created_tuktuks, created_drivers):
    transaction_times = [-5, -4, -3, -2, -1, 0]  # Hours from now
    amounts = [300, 400, 500, 600, 700, 800, 900, 1000]
    driver_shares = [150, 200, 250, 300, 350, 400, 450, 500]
    customer_phones = ["254711111111", "254722222222", "254733333333", 
                      "254744444444", "254755555555", "254766666666"]
    
    transactions = []
    for hour in transaction_times:
        for i in range(3):  # 3 transactions per hour
            driver_idx = (i + abs(hour)) % len(created_drivers)
            tuktuk_idx = (i + abs(hour)) % len(created_tuktuks)
            amount_idx = (i + abs(hour)) % len(amounts)
            phone_idx = (i + abs(hour)) % len(customer_phones)
            
            transactions.append({
                "transaction_id": f"MPESA{abs(hour)}{i}",
                "tuktuk": created_tuktuks[tuktuk_idx],
                "driver": created_drivers[driver_idx],
                "amount": amounts[amount_idx],
                "driver_share": driver_shares[amount_idx],
                "target_contribution": amounts[amount_idx] - driver_shares[amount_idx],
                "customer_phone": customer_phones[phone_idx],
                "timestamp": add_to_date(now_datetime(), hours=hour),
                "payment_status": "Completed"
            })
    return transactions

# def create_additional_rentals(created_drivers, created_tuktuks):
#     rental_times = [-6, -5, -4, -3, -2, -1]  # Hours from now
#     rental_fees = [400, 500, 600, 700]
#     rental_statuses = ["Completed", "Active", "Completed", "Active"]
    
#     rentals = []
#     for hour in rental_times:
#         driver_idx = abs(hour) % len(created_drivers)
#         tuktuk_idx = (abs(hour) + 1) % len(created_tuktuks)
#         fee_idx = abs(hour) % len(rental_fees)
#         status_idx = abs(hour) % len(rental_statuses)
        
#         rentals.append({
#             "driver": created_drivers[driver_idx],
#             "rented_tuktuk": created_tuktuks[tuktuk_idx],
#             "start_time": add_to_date(now_datetime(), hours=hour),
#             "end_time": add_to_date(now_datetime(), hours=hour+2) if rental_statuses[status_idx] == "Completed" else None,
#             "rental_fee": rental_fees[fee_idx],
#             "status": rental_statuses[status_idx],
#             "notes": f"Test rental {abs(hour)}"
#         })
#     return rentals

def create_additional_rentals(created_drivers, created_tuktuks):
    rental_times = [-6, -5, -4, -3, -2, -1]  # Hours from now
    rental_fees = [400, 500, 600, 700]
    rental_statuses = ["Completed", "Active", "Completed", "Active"]
    
    rentals = []
    for hour_idx, hour in enumerate(rental_times):
        driver_idx = abs(hour) % len(created_drivers)
        tuktuk_idx = (abs(hour) + 1) % len(created_tuktuks)
        fee_idx = abs(hour) % len(rental_fees)
        status_idx = abs(hour) % len(rental_statuses)
        
        rentals.append({
            "driver": created_drivers[driver_idx],
            "rented_tuktuk": created_tuktuks[tuktuk_idx],
            "start_time": add_to_date(now_datetime(), hours=hour),
            "end_time": add_to_date(now_datetime(), hours=hour+2) if rental_statuses[status_idx] == "Completed" else None,
            "rental_fee": rental_fees[fee_idx],
            "status": rental_statuses[status_idx],
            "notes": f"Test rental {hour_idx + 1}"  # Use sequential numbering
        })
    return rentals

def verify_doctypes():
    """Verify all required doctypes exist"""
    required_doctypes = [
        "TukTuk Settings",
        "TukTuk Vehicle",
        "TukTuk Driver",
        "TukTuk Transaction",
        "TukTuk Rental",
        "TukTuk Daily Report"
    ]
    
    missing_doctypes = []
    for doctype in required_doctypes:
        if not frappe.db.exists("DocType", doctype):
            missing_doctypes.append(doctype)
    
    if missing_doctypes:
        raise Exception(f"Missing required doctypes: {', '.join(missing_doctypes)}. Please install the app first.")

def create_test_data():
    """Create test data for Sunny TukTuk system"""
    try:
        print("Verifying system setup...")
        verify_doctypes()
        created_tuktuks = []
        created_drivers = []
        
        print("Creating test data...")
        
        # Create TukTuk Settings
        if not frappe.db.exists("Singles", {"doctype": "TukTuk Settings"}):
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
            settings.insert(ignore_permissions=True)
            print("Created TukTuk Settings")

        # Create all TukTuks (base + extra)
        all_tuktuks = base_tuktuks + extra_tuktuks
        for tuktuk in all_tuktuks:
            doc = frappe.get_doc({
                "doctype": "TukTuk Vehicle",
                **tuktuk
            })
            doc.insert(ignore_permissions=True)
            created_tuktuks.append(doc.name)
        print(f"Created {len(created_tuktuks)} TukTuks")

        # Create all Drivers (base + extra)
        all_drivers = base_drivers + extra_drivers
        for idx, driver in enumerate(all_drivers):
            if idx < len(base_drivers):
                driver["assigned_tuktuk"] = created_tuktuks[idx]
            else:
                # For extra drivers, find available tuktuks
                available_tuktuks = [t for t in created_tuktuks 
                                   if not frappe.db.exists("TukTuk Driver", {"assigned_tuktuk": t})]
                if available_tuktuks:
                    driver["assigned_tuktuk"] = available_tuktuks[0]
            
            doc = frappe.get_doc({
                "doctype": "TukTuk Driver",
                **driver
            })
            doc.insert(ignore_permissions=True)
            created_drivers.append(doc.name)
        print(f"Created {len(created_drivers)} Drivers")

# Create base transactions
        base_transactions = [
            {
                "transaction_id": "MPESA123456",
                "tuktuk": created_tuktuks[0],
                "driver": created_drivers[0],
                "amount": 500,
                "driver_share": 300,
                "target_contribution": 200,
                "customer_phone": "254700999999",
                "timestamp": now_datetime(),
                "payment_status": "Completed"
            },
            {
                "transaction_id": "MPESA123457",
                "tuktuk": created_tuktuks[1],
                "driver": created_drivers[1],
                "amount": 1000,
                "driver_share": 500,
                "target_contribution": 500,
                "customer_phone": "254700888888",
                "timestamp": add_to_date(now_datetime(), hours=-1),
                "payment_status": "Completed"
            }
        ]

        # Create all transactions (base + additional)
        created_transactions = []
        all_transactions = base_transactions
        additional_transactions = create_additional_transactions(created_tuktuks, created_drivers)
        all_transactions.extend(additional_transactions)
        
        for transaction in all_transactions:
            doc = frappe.get_doc({
                "doctype": "TukTuk Transaction",
                **transaction
            })
            doc.insert(ignore_permissions=True)
            created_transactions.append(doc.name)
        print(f"Created {len(created_transactions)} Transactions")

        # Create base rental
        base_rental = {
            "driver": created_drivers[1],
            "rented_tuktuk": created_tuktuks[2],
            "start_time": add_to_date(now_datetime(), hours=-3),
            "rental_fee": 500,
            "status": "Active",
            "notes": "Temporary rental while assigned tuktuk charges"
        }
        
        # Create all rentals (base + additional)
        all_rentals = [base_rental]
        additional_rentals = create_additional_rentals(created_drivers, created_tuktuks)
        all_rentals.extend(additional_rentals)
        
        rental_count = 0
        for rental in all_rentals:
            try:
                doc = frappe.get_doc({
                    "doctype": "TukTuk Rental",
                    **rental
                })
                doc.insert(ignore_permissions=True)
                rental_count += 1
            except frappe.DuplicateEntryError:
                print(f"Skipping duplicate rental entry for driver {rental['driver']}")
                continue
        print(f"Created {rental_count} Rentals")

        # Create Daily Report
        report_data = {
            "report_date": now_datetime().date(),
            "total_transactions": len(created_transactions),
            "total_revenue": sum(t.get("amount") for t in all_transactions),
            "total_driver_share": sum(t.get("driver_share") for t in all_transactions),
            "total_target_contribution": sum(t.get("target_contribution") for t in all_transactions)
        }

        daily_report = frappe.get_doc({
            "doctype": "TukTuk Daily Report",
            **report_data
        })
        daily_report.insert(ignore_permissions=True)
        print("Created Daily Report")

        frappe.db.commit()
        print("Test data creation completed successfully")
        
    except Exception as e:
        print(f"Error creating test data: {str(e)}")
        frappe.log_error(f"Test Data Creation Error: {str(e)}")
        raise

if __name__ == "__main__":
    create_test_data()