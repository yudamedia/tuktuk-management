# Copyright (c) 2024, Yuda and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import getdate, add_days, now_datetime, get_datetime, today
from datetime import datetime, timedelta
import random


class TukTukRosterPeriod(Document):
	def validate(self):
		"""Validate roster period"""
		# Ensure end date is after start date
		if getdate(self.end_date) <= getdate(self.start_date):
			frappe.throw("End date must be after start date")
		
		# Calculate period length
		period_days = (getdate(self.end_date) - getdate(self.start_date)).days + 1
		
		# Ensure it's exactly 14 days
		if period_days != 14:
			frappe.throw("Roster period must be exactly 14 days")
		
		# Update statistics
		self.total_scheduled_offs = len(self.day_off_schedules) if self.day_off_schedules else 0
		self.total_substitute_days = len(self.substitute_assignments) if self.substitute_assignments else 0
	
	def before_save(self):
		"""Set generation info if creating new roster"""
		if not self.generated_by:
			self.generated_by = frappe.session.user
		if not self.generation_date:
			self.generation_date = now_datetime()


@frappe.whitelist()
def generate_roster(start_date, end_date=None):
	"""
	Generate a 14-day roster
	
	Args:
		start_date: Start date of roster period (YYYY-MM-DD)
		end_date: Optional end date (defaults to start_date + 13 days)
	
	Returns:
		dict: Generated roster document
	"""
	start_date = getdate(start_date)
	
	if not end_date:
		end_date = add_days(start_date, 13)
	else:
		end_date = getdate(end_date)
	
	# Validate 14-day period
	period_days = (end_date - start_date).days + 1
	if period_days != 14:
		frappe.throw("Roster period must be exactly 14 days")
	
	# Check if roster already exists for this period
	existing = frappe.db.exists("TukTuk Roster Period", {
		"start_date": start_date,
		"end_date": end_date
	})
	
	if existing:
		frappe.throw(f"A roster already exists for this period: {existing}")
	
	# Get all active drivers
	regular_drivers = frappe.get_all(
		"TukTuk Driver",
		filters={"assigned_tuktuk": ["is", "set"]},
		fields=["name", "driver_name", "assigned_tuktuk", "preferred_day_off"]
	)
	
	substitute_drivers = frappe.get_all(
		"TukTuk Substitute Driver",
		filters={"status": ["in", ["Active", "On Assignment"]]},
		fields=["name", "first_name", "last_name", "preferred_day_off"]
	)
	
	if len(substitute_drivers) < 3:
		frappe.throw(f"Need at least 3 substitute drivers. Currently have {len(substitute_drivers)}")
	
	# Generate the roster
	roster_data = _generate_roster_logic(start_date, end_date, regular_drivers, substitute_drivers)
	
	# Create roster document
	roster = frappe.get_doc({
		"doctype": "TukTuk Roster Period",
		"start_date": start_date,
		"end_date": end_date,
		"status": "Draft",
		"day_off_schedules": roster_data["day_offs"],
		"substitute_assignments": roster_data["substitute_assignments"]
	})
	
	roster.insert()
	frappe.db.commit()
	
	return {
		"success": True,
		"roster_name": roster.name,
		"message": f"Roster generated successfully for {start_date} to {end_date}",
		"total_offs": len(roster_data["day_offs"]),
		"total_substitute_days": len(roster_data["substitute_assignments"])
	}


def _generate_roster_logic(start_date, end_date, regular_drivers, substitute_drivers):
	"""
	Core roster generation algorithm
	
	Returns:
		dict: {
			"day_offs": [list of day off schedule rows],
			"substitute_assignments": [list of substitute assignment rows]
		}
	"""
	# Initialize structures
	day_offs = []
	substitute_assignments = []
	
	# Track driver off days per week
	week1_offs = {d["name"]: 0 for d in regular_drivers}
	week2_offs = {d["name"]: 0 for d in regular_drivers}
	sub_week1_offs = {s["name"]: 0 for s in substitute_drivers}
	sub_week2_offs = {s["name"]: 0 for s in substitute_drivers}
	
	# Get driver preferences
	driver_preferences = {}
	for driver in regular_drivers:
		driver_preferences[driver["name"]] = {
			"preferred_day": driver.get("preferred_day_off"),
			"driver_name": driver["driver_name"],
			"assigned_tuktuk": driver["assigned_tuktuk"]
		}
	
	sub_preferences = {}
	for sub in substitute_drivers:
		sub_preferences[sub["name"]] = {
			"preferred_day": sub.get("preferred_day_off"),
			"sub_name": f"{sub['first_name']} {sub['last_name']}"
		}
	
	# Handle special case: DRV-112017 (4 consecutive days end of December)
	special_driver = "DRV-112017"
	if start_date.month == 12 and special_driver in driver_preferences:
		# Assign Dec 28, 29, 30, 31 if they fall in this roster
		special_dates = [getdate(f"2024-12-{day}") for day in [28, 29, 30, 31]]
		for special_date in special_dates:
			if start_date <= special_date <= end_date:
				day_offs.append({
					"date": special_date,
					"driver": special_driver,
					"driver_type": "Regular Driver",
					"day_off_type": "Scheduled",
					"notes": "Special request: 4 consecutive days end of month"
				})
				# Track week offs
				week_num = 1 if (special_date - start_date).days < 7 else 2
				if week_num == 1:
					week1_offs[special_driver] += 1
				else:
					week2_offs[special_driver] += 1
	
	# Generate roster for each day
	current_date = start_date
	while current_date <= end_date:
		day_name = current_date.strftime("%A").upper()
		week_num = 1 if (current_date - start_date).days < 7 else 2
		week_offs = week1_offs if week_num == 1 else week2_offs
		sub_week_offs = sub_week1_offs if week_num == 1 else sub_week2_offs
		
		# Determine max offs for this day
		max_regular_offs = 15 if day_name == "SUNDAY" else 3
		min_working = 9 if day_name == "SUNDAY" else 12
		
		# Assign regular driver offs for this day
		drivers_off_today = []
		
		# First pass: drivers with matching preferred day who haven't had off this week
		for driver_id, pref in driver_preferences.items():
			if pref["preferred_day"] == day_name and week_offs[driver_id] == 0:
				# Check if already scheduled off (special case)
				already_off = any(d["driver"] == driver_id and d["date"] == current_date for d in day_offs)
				if not already_off and len(drivers_off_today) < max_regular_offs:
					drivers_off_today.append(driver_id)
					week_offs[driver_id] += 1
		
		# Second pass: drivers who need an off day this week
		if len(drivers_off_today) < max_regular_offs:
			eligible = [d for d in regular_drivers 
					   if d["name"] not in drivers_off_today 
					   and week_offs[d["name"]] == 0
					   and not any(do["driver"] == d["name"] and do["date"] == current_date for do in day_offs)]
			
			# Sort by preference match, then randomly
			random.shuffle(eligible)
			
			for driver in eligible:
				if len(drivers_off_today) >= max_regular_offs:
					break
				drivers_off_today.append(driver["name"])
				week_offs[driver["name"]] += 1
		
		# Add day offs to schedule
		for driver_id in drivers_off_today:
			# Check if not already added (special case)
			if not any(d["driver"] == driver_id and d["date"] == current_date for d in day_offs):
				day_offs.append({
					"date": current_date,
					"driver": driver_id,
					"driver_type": "Regular Driver",
					"day_off_type": "Scheduled"
				})
		
		# Assign substitute drivers for regular drivers who are off
		available_subs = [s for s in substitute_drivers if sub_week_offs[s["name"]] == 0]
		
		# Ensure we have enough subs
		if len(available_subs) < len(drivers_off_today):
			# Some subs need to work even if they've had their day off
			available_subs = substitute_drivers.copy()
		
		random.shuffle(available_subs)
		
		for i, driver_id in enumerate(drivers_off_today):
			if i < len(available_subs):
				sub_id = available_subs[i]["name"]
				vehicle = driver_preferences[driver_id]["assigned_tuktuk"]
				
				substitute_assignments.append({
					"date": current_date,
					"substitute_driver": sub_id,
					"vehicle": vehicle,
					"regular_driver_off": driver_id,
					"assignment_status": "Scheduled"
				})
		
		# Assign substitute driver offs (1 per week per substitute)
		subs_off_today = []
		for sub_id, pref in sub_preferences.items():
			if pref["preferred_day"] == day_name and sub_week_offs[sub_id] == 0:
				# Check they're not already assigned to work
				already_working = any(sa["substitute_driver"] == sub_id and sa["date"] == current_date 
									 for sa in substitute_assignments)
				if not already_working:
					subs_off_today.append(sub_id)
					sub_week_offs[sub_id] += 1
		
		# Add substitute offs to schedule
		for sub_id in subs_off_today:
			day_offs.append({
				"date": current_date,
				"driver": sub_id,
				"driver_type": "Substitute Driver",
				"day_off_type": "Scheduled"
			})
		
		current_date = add_days(current_date, 1)
	
	return {
		"day_offs": day_offs,
		"substitute_assignments": substitute_assignments
	}


@frappe.whitelist()
def activate_roster(roster_name):
	"""Activate a draft roster"""
	roster = frappe.get_doc("TukTuk Roster Period", roster_name)
	
	if roster.status != "Draft":
		frappe.throw(f"Can only activate Draft rosters. Current status: {roster.status}")
	
	# Deactivate any other active rosters
	frappe.db.sql("""
		UPDATE `tabTukTuk Roster Period`
		SET status = 'Completed'
		WHERE status = 'Active'
	""")
	
	# Activate this roster
	roster.status = "Active"
	roster.save()
	frappe.db.commit()
	
	return {"success": True, "message": f"Roster {roster_name} activated successfully"}


@frappe.whitelist()
def get_active_roster():
	"""Get the currently active roster"""
	active_roster = frappe.get_all(
		"TukTuk Roster Period",
		filters={"status": "Active"},
		fields=["name", "start_date", "end_date"],
		limit=1
	)
	
	if active_roster:
		roster = frappe.get_doc("TukTuk Roster Period", active_roster[0]["name"])
		return {
			"success": True,
			"roster": roster.as_dict()
		}
	
	return {"success": False, "message": "No active roster found"}


@frappe.whitelist()
def get_driver_schedule(driver_id, start_date=None, end_date=None):
	"""Get schedule for a specific driver"""
	if not start_date:
		start_date = today()
	if not end_date:
		end_date = add_days(start_date, 13)
	
	# Get all day offs for this driver in the period
	day_offs = frappe.get_all(
		"TukTuk Day Off Schedule",
		filters={
			"driver": driver_id,
			"date": ["between", [start_date, end_date]]
		},
		fields=["date", "day_off_type", "switch_status", "notes"],
		order_by="date asc"
	)
	
	return {
		"success": True,
		"driver": driver_id,
		"day_offs": day_offs
	}
