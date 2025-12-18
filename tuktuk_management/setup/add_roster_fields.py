#!/usr/bin/env python3
"""
Script to add preferred_day_off field to TukTuk Driver and TukTuk Substitute Driver DocTypes
Run this script using: bench execute tuktuk_management.setup.add_roster_fields
"""

import frappe


def add_roster_fields():
	"""Add roster-related fields to driver DocTypes"""
	
	# Add field to TukTuk Driver
	try:
		driver_meta = frappe.get_meta("TukTuk Driver")
		
		# Check if field already exists
		if not driver_meta.has_field("preferred_day_off"):
			# Get the DocType
			doc = frappe.get_doc("DocType", "TukTuk Driver")
			
			# Find position after 'driver_license' field
			insert_after_idx = None
			for i, field in enumerate(doc.fields):
				if field.fieldname == "driver_license":
					insert_after_idx = i + 1
					break
			
			if insert_after_idx is None:
				insert_after_idx = len(doc.fields)
			
			# Insert preferred_day_off field
			doc.fields.insert(insert_after_idx, {
				"fieldname": "preferred_day_off",
				"fieldtype": "Select",
				"label": "Preferred Day Off",
				"options": "MONDAY\nTUESDAY\nWEDNESDAY\nTHURSDAY\nFRIDAY\nSATURDAY\nSUNDAY\nNo Preference",
				"description": "Preferred weekly day off for roster scheduling"
			})
			
			# Insert accumulated_off_days field
			doc.fields.insert(insert_after_idx + 1, {
				"fieldname": "accumulated_off_days",
				"fieldtype": "Int",
				"label": "Accumulated Off Days (This Month)",
				"default": "0",
				"read_only": 1,
				"description": "Unused off days that roll over within the month"
			})
			
			doc.save()
			frappe.db.commit()
			
			print("✓ Added roster fields to TukTuk Driver")
		else:
			print("✓ Roster fields already exist in TukTuk Driver")
			
	except Exception as e:
		print(f"✗ Error updating TukTuk Driver: {str(e)}")
		frappe.log_error(f"Error in add_roster_fields for TukTuk Driver: {str(e)}")
	
	# Add field to TukTuk Substitute Driver
	try:
		sub_meta = frappe.get_meta("TukTuk Substitute Driver")
		
		if not sub_meta.has_field("preferred_day_off"):
			doc = frappe.get_doc("DocType", "TukTuk Substitute Driver")
			
			# Find position after 'driver_type' field
			insert_after_idx = None
			for i, field in enumerate(doc.fields):
				if field.fieldname == "driver_type":
					insert_after_idx = i + 1
					break
			
			if insert_after_idx is None:
				insert_after_idx = len(doc.fields)
			
			# Insert preferred_day_off field
			doc.fields.insert(insert_after_idx, {
				"fieldname": "preferred_day_off",
				"fieldtype": "Select",
				"label": "Preferred Day Off",
				"options": "MONDAY\nTUESDAY\nWEDNESDAY\nTHURSDAY\nFRIDAY\nSATURDAY\nSUNDAY\nNo Preference",
				"description": "Preferred weekly day off for roster scheduling"
			})
			
			doc.save()
			frappe.db.commit()
			
			print("✓ Added preferred_day_off field to TukTuk Substitute Driver")
		else:
			print("✓ preferred_day_off field already exists in TukTuk Substitute Driver")
			
	except Exception as e:
		print(f"✗ Error updating TukTuk Substitute Driver: {str(e)}")
		frappe.log_error(f"Error in add_roster_fields for TukTuk Substitute Driver: {str(e)}")


def import_driver_preferences_from_csv():
	"""Import driver preferences from the CSV file"""
	import csv
	
	csv_data = """ID,Prefered Weekly Off Day
DRV-112110,SUNDAY
DRV-112102,SUNDAY
DRV-112101,
DRV-112087,WEDNESDAY
DRV-112059,SUNDAY
DRV-112042,
DRV-112040,SUNDAY
DRV-112039,FRIDAY
DRV-112022,
DRV-112018,SUNDAY
DRV-112017,4 days at the end of the month
DRV-112016,
DRV-112011,FRIDAY
DRV-112010,WEDNESDAY
DRV-112006,MONDAY
SUB-212170,
SUB-212169,
SUB-212166,"""
	
	reader = csv.DictReader(csv_data.strip().split('\n'))
	
	updated_count = 0
	error_count = 0
	
	for row in reader:
		driver_id = row['ID'].strip()
		pref_day = row['Prefered Weekly Off Day'].strip().upper()
		
		try:
			if driver_id.startswith('DRV'):
				# Regular driver
				if frappe.db.exists("TukTuk Driver", driver_id):
					driver = frappe.get_doc("TukTuk Driver", driver_id)
					
					# Handle special case
					if "4 days" in pref_day.lower() or "end of" in pref_day.lower():
						driver.preferred_day_off = "No Preference"
						# Note: Special case for DRV-112017 handled in roster generation logic
					elif pref_day and pref_day in ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY", "SUNDAY"]:
						driver.preferred_day_off = pref_day
					else:
						driver.preferred_day_off = "No Preference"
					
					driver.save()
					updated_count += 1
					print(f"✓ Updated {driver_id}: {driver.preferred_day_off}")
				else:
					print(f"✗ Driver not found: {driver_id}")
					error_count += 1
					
			elif driver_id.startswith('SUB'):
				# Substitute driver
				if frappe.db.exists("TukTuk Substitute Driver", driver_id):
					sub = frappe.get_doc("TukTuk Substitute Driver", driver_id)
					
					if pref_day and pref_day in ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY", "SUNDAY"]:
						sub.preferred_day_off = pref_day
					else:
						sub.preferred_day_off = "No Preference"
					
					sub.save()
					updated_count += 1
					print(f"✓ Updated {driver_id}: {sub.preferred_day_off}")
				else:
					print(f"✗ Substitute not found: {driver_id}")
					error_count += 1
					
		except Exception as e:
			print(f"✗ Error updating {driver_id}: {str(e)}")
			error_count += 1
			frappe.log_error(f"Error importing preference for {driver_id}: {str(e)}")
	
	frappe.db.commit()
	
	print(f"\n=== Import Complete ===")
	print(f"Updated: {updated_count}")
	print(f"Errors: {error_count}")


if __name__ == "__main__":
	add_roster_fields()
	import_driver_preferences_from_csv()
