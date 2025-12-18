# ~/frappe-bench/apps/tuktuk_management/tuktuk_management/api/roster.py

import frappe
from frappe import _
from frappe.utils import getdate, get_datetime, now_datetime, add_hours, today
from datetime import datetime, timedelta


@frappe.whitelist()
def request_switch(my_driver_id, my_scheduled_off, switch_with_driver, requested_date, reason=None):
	"""
	Request to switch day off with another driver
	
	Args:
		my_driver_id: Current driver requesting switch
		my_scheduled_off: The day off I'm willing to give up
		switch_with_driver: The driver I want to switch with
		requested_date: The date I want off (their currently scheduled work day)
		reason: Optional reason for switch
	
	Returns:
		dict: Success status and message
	"""
	try:
		my_scheduled_off = getdate(my_scheduled_off)
		requested_date = getdate(requested_date)
		
		# Validate: requested date must be at least 5 hours before operation start (6 AM)
		operation_start = get_datetime(f"{requested_date} 06:00:00")
		deadline = add_hours(operation_start, -5)  # 1 AM same day
		
		if now_datetime() > deadline:
			return {
				"success": False,
				"message": f"Switch request must be made at least 5 hours before operation start time (6 AM). Deadline was {deadline}"
			}
		
		# Get active roster
		active_roster = frappe.get_all(
			"TukTuk Roster Period",
			filters={"status": "Active"},
			limit=1
		)
		
		if not active_roster:
			return {"success": False, "message": "No active roster found"}
		
		roster = frappe.get_doc("TukTuk Roster Period", active_roster[0]["name"])
		
		# Find my scheduled day off
		my_off_schedule = None
		for schedule in roster.day_off_schedules:
			if schedule.driver == my_driver_id and getdate(schedule.date) == my_scheduled_off:
				my_off_schedule = schedule
				break
		
		if not my_off_schedule:
			return {
				"success": False,
				"message": f"You don't have a scheduled day off on {my_scheduled_off}"
			}
		
		# Verify the other driver is working on requested date (not scheduled off)
		other_driver_off = False
		for schedule in roster.day_off_schedules:
			if schedule.driver == switch_with_driver and getdate(schedule.date) == requested_date:
				other_driver_off = True
				break
		
		if other_driver_off:
			return {
				"success": False,
				"message": f"The driver you want to switch with is already scheduled off on {requested_date}"
			}
		
		# Create switch request by modifying my off schedule
		my_off_schedule.day_off_type = "Switched"
		my_off_schedule.original_driver = my_driver_id
		my_off_schedule.switched_with_driver = switch_with_driver
		my_off_schedule.switch_requested_by = frappe.session.user
		my_off_schedule.switch_requested_date = now_datetime()
		my_off_schedule.switch_status = "Pending"
		my_off_schedule.notes = reason or ""
		
		# Create a new pending day off for requested date
		roster.append("day_off_schedules", {
			"date": requested_date,
			"driver": my_driver_id,
			"driver_type": "Regular Driver",
			"day_off_type": "Switched",
			"original_driver": switch_with_driver,
			"switched_with_driver": my_driver_id,
			"switch_requested_by": frappe.session.user,
			"switch_requested_date": now_datetime(),
			"switch_status": "Pending",
			"notes": reason or ""
		})
		
		roster.save()
		frappe.db.commit()
		
		# Send SMS notification to other driver
		_notify_switch_request(my_driver_id, switch_with_driver, my_scheduled_off, requested_date)
		
		return {
			"success": True,
			"message": f"Switch request sent to {switch_with_driver}. Waiting for approval."
		}
		
	except Exception as e:
		frappe.log_error(f"Error in request_switch: {str(e)}", "Roster Switch Error")
		return {"success": False, "message": str(e)}


@frappe.whitelist()
def approve_switch(roster_name, requesting_driver, my_driver_id, their_off_date, my_off_date):
	"""
	Approve a switch request
	
	Args:
		roster_name: Roster period name
		requesting_driver: Driver who requested the switch
		my_driver_id: Driver approving the switch
		their_off_date: Date the requesting driver wants off
		my_off_date: Date I (approver) am currently scheduled off
	
	Returns:
		dict: Success status
	"""
	try:
		their_off_date = getdate(their_off_date)
		my_off_date = getdate(my_off_date)
		
		roster = frappe.get_doc("TukTuk Roster Period", roster_name)
		
		# Find and update both switch schedules
		for schedule in roster.day_off_schedules:
			if (schedule.driver == requesting_driver and 
				getdate(schedule.date) == their_off_date and 
				schedule.switch_status == "Pending"):
				
				schedule.switch_status = "Approved"
				schedule.switch_approved_by = frappe.session.user
				schedule.switch_approved_date = now_datetime()
			
			elif (schedule.driver == requesting_driver and 
				  getdate(schedule.date) == my_off_date and 
				  schedule.switch_status == "Pending"):
				
				# Remove this schedule (they're giving up this day)
				schedule.switch_status = "Approved"
				schedule.day_off_type = "Scheduled"  # Revert to normal
				schedule.driver = my_driver_id  # Transfer to approver
		
		# Update substitute assignments if needed
		my_vehicle = frappe.db.get_value("TukTuk Driver", my_driver_id, "assigned_tuktuk")
		their_vehicle = frappe.db.get_value("TukTuk Driver", requesting_driver, "assigned_tuktuk")
		
		for assignment in roster.substitute_assignments:
			# Update assignment for my off day (now requesting driver works)
			if (getdate(assignment.date) == my_off_date and 
				assignment.regular_driver_off == my_driver_id):
				assignment.regular_driver_off = requesting_driver
				assignment.vehicle = their_vehicle
			
			# Update assignment for their new off day
			elif (getdate(assignment.date) == their_off_date and 
				  assignment.vehicle == their_vehicle):
				assignment.regular_driver_off = requesting_driver
		
		roster.save()
		frappe.db.commit()
		
		# Send SMS notification
		_notify_switch_approved(requesting_driver, my_driver_id, their_off_date, my_off_date)
		
		return {
			"success": True,
			"message": "Switch request approved successfully"
		}
		
	except Exception as e:
		frappe.log_error(f"Error in approve_switch: {str(e)}", "Roster Switch Error")
		return {"success": False, "message": str(e)}


@frappe.whitelist()
def reject_switch(roster_name, requesting_driver, requested_date):
	"""Reject a switch request"""
	try:
		requested_date = getdate(requested_date)
		roster = frappe.get_doc("TukTuk Roster Period", roster_name)
		
		# Find and update the pending switch
		schedules_to_remove = []
		for i, schedule in enumerate(roster.day_off_schedules):
			if (schedule.driver == requesting_driver and 
				getdate(schedule.date) == requested_date and 
				schedule.switch_status == "Pending"):
				
				schedules_to_remove.append(i)
		
		# Remove rejected switches (iterate backwards to avoid index issues)
		for i in sorted(schedules_to_remove, reverse=True):
			roster.day_off_schedules.pop(i)
		
		roster.save()
		frappe.db.commit()
		
		# Send SMS notification
		_notify_switch_rejected(requesting_driver, requested_date)
		
		return {"success": True, "message": "Switch request rejected"}
		
	except Exception as e:
		frappe.log_error(f"Error in reject_switch: {str(e)}", "Roster Switch Error")
		return {"success": False, "message": str(e)}


@frappe.whitelist()
def get_pending_switch_requests(driver_id):
	"""Get all pending switch requests for a driver"""
	try:
		active_roster = frappe.get_all(
			"TukTuk Roster Period",
			filters={"status": "Active"},
			limit=1
		)
		
		if not active_roster:
			return {"success": False, "message": "No active roster"}
		
		roster = frappe.get_doc("TukTuk Roster Period", active_roster[0]["name"])
		
		pending_requests = []
		for schedule in roster.day_off_schedules:
			if (schedule.switched_with_driver == driver_id and 
				schedule.switch_status == "Pending"):
				
				pending_requests.append({
					"requesting_driver": schedule.driver,
					"requesting_driver_name": schedule.driver_name,
					"requested_date": schedule.date,
					"my_off_date": schedule.original_driver,  # The date they're offering
					"reason": schedule.notes,
					"requested_on": schedule.switch_requested_date,
					"roster_name": roster.name
				})
		
		return {
			"success": True,
			"pending_requests": pending_requests
		}
		
	except Exception as e:
		frappe.log_error(f"Error in get_pending_switch_requests: {str(e)}", "Roster Switch Error")
		return {"success": False, "message": str(e)}


def _notify_switch_request(requesting_driver, target_driver, their_off_date, requested_date):
	"""Send SMS notification for switch request"""
	try:
		from tuktuk_management.api.sms_notifications import send_sms
		
		requesting_driver_doc = frappe.get_doc("TukTuk Driver", requesting_driver)
		target_driver_doc = frappe.get_doc("TukTuk Driver", target_driver)
		
		if not target_driver_doc.mpesa_number:
			return
		
		message = (f"Sunny TukTuk: {requesting_driver_doc.driver_name} wants to switch days off. "
				  f"They offer {their_off_date.strftime('%b %d')} for your {requested_date.strftime('%b %d')}. "
				  f"Login to approve/reject.")
		
		send_sms(target_driver_doc.mpesa_number, message)
		
	except Exception as e:
		frappe.log_error(f"Error sending switch request SMS: {str(e)}", "SMS Error")


def _notify_switch_approved(requesting_driver, approving_driver, their_new_off, their_old_off):
	"""Send SMS notification for approved switch"""
	try:
		from tuktuk_management.api.sms_notifications import send_sms
		
		requesting_driver_doc = frappe.get_doc("TukTuk Driver", requesting_driver)
		
		if not requesting_driver_doc.mpesa_number:
			return
		
		message = (f"Sunny TukTuk: Your day off switch request was APPROVED! "
				  f"Your new day off is {their_new_off.strftime('%b %d')}.")
		
		send_sms(requesting_driver_doc.mpesa_number, message)
		
	except Exception as e:
		frappe.log_error(f"Error sending switch approved SMS: {str(e)}", "SMS Error")


def _notify_switch_rejected(requesting_driver, requested_date):
	"""Send SMS notification for rejected switch"""
	try:
		from tuktuk_management.api.sms_notifications import send_sms
		
		requesting_driver_doc = frappe.get_doc("TukTuk Driver", requesting_driver)
		
		if not requesting_driver_doc.mpesa_number:
			return
		
		message = (f"Sunny TukTuk: Your day off switch request for {requested_date.strftime('%b %d')} "
				  f"was declined. Your original schedule remains.")
		
		send_sms(requesting_driver_doc.mpesa_number, message)
		
	except Exception as e:
		frappe.log_error(f"Error sending switch rejected SMS: {str(e)}", "SMS Error")


@frappe.whitelist()
def mark_sick_day(driver_id, date, notes=None):
	"""Mark a driver as sick on a specific date"""
	try:
		date = getdate(date)
		
		active_roster = frappe.get_all(
			"TukTuk Roster Period",
			filters={"status": "Active"},
			limit=1
		)
		
		if not active_roster:
			return {"success": False, "message": "No active roster"}
		
		roster = frappe.get_doc("TukTuk Roster Period", active_roster[0]["name"])
		
		# Check if already marked off
		already_off = False
		for schedule in roster.day_off_schedules:
			if schedule.driver == driver_id and getdate(schedule.date) == date:
				# Update to sick day
				schedule.day_off_type = "Sick"
				schedule.notes = notes or "Sick day"
				already_off = True
				break
		
		# If not already off, create new sick day entry
		if not already_off:
			roster.append("day_off_schedules", {
				"date": date,
				"driver": driver_id,
				"driver_type": "Regular Driver",
				"day_off_type": "Sick",
				"notes": notes or "Sick day"
			})
		
		roster.save()
		frappe.db.commit()
		
		return {
			"success": True,
			"message": f"Sick day marked for {driver_id} on {date}"
		}
		
	except Exception as e:
		frappe.log_error(f"Error in mark_sick_day: {str(e)}", "Roster Error")
		return {"success": False, "message": str(e)}


@frappe.whitelist()
def is_driver_scheduled_off(driver_id, date=None):
	"""
	Check if a driver is scheduled off on a specific date
	Used by transaction processing to exclude scheduled offs from performance tracking
	"""
	if not date:
		date = today()
	else:
		date = getdate(date)
	
	active_roster = frappe.get_all(
		"TukTuk Roster Period",
		filters={"status": "Active"},
		limit=1
	)
	
	if not active_roster:
		return {"scheduled_off": False}
	
	roster = frappe.get_doc("TukTuk Roster Period", active_roster[0]["name"])
	
	for schedule in roster.day_off_schedules:
		if schedule.driver == driver_id and getdate(schedule.date) == date:
			return {
				"scheduled_off": True,
				"day_off_type": schedule.day_off_type
			}
	
	return {"scheduled_off": False}
