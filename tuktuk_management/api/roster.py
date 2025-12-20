# ~/frappe-bench/apps/tuktuk_management/tuktuk_management/api/roster.py

import frappe
from frappe import _
from frappe.utils import getdate, get_datetime, now_datetime, today, add_to_date
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
		deadline = add_to_date(operation_start, hours=-5)  # 1 AM same day
		
		if now_datetime() > deadline:
			return {
				"success": False,
				"message": f"Switch request must be made at least 5 hours before operation start time (6 AM). Current deadline: {deadline.strftime('%I:%M %p')}."
			}
		
		# Get active roster period
		roster_period = frappe.get_all(
			"TukTuk Roster Period",
			filters={
				"status": "Active",
				"start_date": ["<=", requested_date],
				"end_date": [">=", requested_date]
			},
			fields=["name", "start_date", "end_date"],
			limit=1
		)
		
		if not roster_period:
			return {
				"success": False,
				"message": "No active roster period found for the requested date."
			}
		
		roster_name = roster_period[0].name
		
		# Verify both dates are in the same roster period
		if not (roster_period[0].start_date <= my_scheduled_off <= roster_period[0].end_date):
			return {
				"success": False,
				"message": "Your scheduled off day is not in the same roster period as the requested date."
			}
		
		# Get the roster period document
		roster_doc = frappe.get_doc("TukTuk Roster Period", roster_name)
		
		# Verify my_scheduled_off is actually my scheduled off day
		my_schedule = None
		for schedule in roster_doc.day_off_schedules:
			if schedule.driver == my_driver_id and getdate(schedule.off_date) == my_scheduled_off:
				my_schedule = schedule
				break
		
		if not my_schedule:
			return {
				"success": False,
				"message": f"You are not scheduled off on {my_scheduled_off.strftime('%Y-%m-%d')}."
			}
		
		# Verify requested_date is the other driver's scheduled work day (not off)
		other_driver_off = False
		for schedule in roster_doc.day_off_schedules:
			if schedule.driver == switch_with_driver and getdate(schedule.off_date) == requested_date:
				other_driver_off = True
				break
		
		if other_driver_off:
			return {
				"success": False,
				"message": f"{switch_with_driver} is already scheduled off on {requested_date.strftime('%Y-%m-%d')}."
			}
		
		# Check for existing pending request with same dates
		existing = frappe.db.exists(
			"TukTuk Switch Request",
			{
				"requesting_driver": my_driver_id,
				"switch_with_driver": switch_with_driver,
				"my_scheduled_off": my_scheduled_off,
				"requested_date": requested_date,
				"status": "Pending"
			}
		)
		
		if existing:
			return {
				"success": False,
				"message": "You already have a pending switch request for these dates."
			}
		
		# Create switch request
		switch_request = frappe.get_doc({
			"doctype": "TukTuk Switch Request",
			"roster_period": roster_name,
			"requesting_driver": my_driver_id,
			"my_scheduled_off": my_scheduled_off,
			"switch_with_driver": switch_with_driver,
			"requested_date": requested_date,
			"reason": reason or "",
			"status": "Pending",
			"request_date": now_datetime()
		})
		
		switch_request.insert()
		frappe.db.commit()
		
		# Send SMS notification to the other driver
		try:
			other_driver_doc = frappe.get_doc("TukTuk Driver", switch_with_driver)
			my_driver_doc = frappe.get_doc("TukTuk Driver", my_driver_id)
			
			message = f"Day-Off Switch Request: {my_driver_doc.driver_name} wants to switch their {my_scheduled_off.strftime('%b %d')} off-day for your work day on {requested_date.strftime('%b %d')}. Login to approve/reject."
			
			from tuktuk_management.api.sms import send_sms
			send_sms(other_driver_doc.mpesa_phone_number, message)
		except Exception as e:
			frappe.log_error(f"Failed to send switch request SMS: {str(e)}")
		
		return {
			"success": True,
			"message": f"Switch request sent to {switch_with_driver}. They will receive an SMS notification.",
			"request_id": switch_request.name
		}
		
	except Exception as e:
		frappe.log_error(f"Switch request error: {str(e)}")
		return {
			"success": False,
			"message": f"Error creating switch request: {str(e)}"
		}


@frappe.whitelist()
def approve_switch_request(request_id):
	"""
	Approve a switch request and update roster
	
	Args:
		request_id: Name of the TukTuk Switch Request document
	
	Returns:
		dict: Success status and message
	"""
	try:
		# Get the switch request
		switch_request = frappe.get_doc("TukTuk Switch Request", request_id)
		
		if switch_request.status != "Pending":
			return {
				"success": False,
				"message": f"This request has already been {switch_request.status.lower()}."
			}
		
		# Verify the current user is the switch_with_driver
		driver = frappe.get_all(
			"TukTuk Driver",
			filters={"user_account": frappe.session.user},
			fields=["name"],
			limit=1
		)
		
		if not driver or driver[0].name != switch_request.switch_with_driver:
			return {
				"success": False,
				"message": "You are not authorized to approve this request."
			}
		
		# Get the roster period
		roster_doc = frappe.get_doc("TukTuk Roster Period", switch_request.roster_period)
		
		# Find and update the schedules
		requesting_driver_schedule = None
		for schedule in roster_doc.day_off_schedules:
			if (schedule.driver == switch_request.requesting_driver and 
				getdate(schedule.off_date) == getdate(switch_request.my_scheduled_off)):
				requesting_driver_schedule = schedule
				break
		
		if not requesting_driver_schedule:
			return {
				"success": False,
				"message": "Original schedule not found in roster."
			}
		
		# Create new schedule for the switch_with_driver on the requesting driver's original off day
		roster_doc.append("day_off_schedules", {
			"driver": switch_request.switch_with_driver,
			"driver_name": frappe.db.get_value("TukTuk Driver", switch_request.switch_with_driver, "driver_name"),
			"off_date": switch_request.my_scheduled_off,
			"day_of_week": switch_request.my_scheduled_off.strftime("%A").upper(),
			"reason": "Switch - Approved",
			"is_sick_day": 0
		})
		
		# Update the requesting driver's schedule to the new requested date
		requesting_driver_schedule.off_date = switch_request.requested_date
		requesting_driver_schedule.day_of_week = switch_request.requested_date.strftime("%A").upper()
		requesting_driver_schedule.reason = "Switch - Approved"
		
		# Update substitute assignments if needed
		# (This is complex - may need to reassign substitutes based on the new schedule)
		
		# Save roster
		roster_doc.save()
		
		# Update switch request status
		switch_request.status = "Approved"
		switch_request.approved_date = now_datetime()
		switch_request.approved_by = frappe.session.user
		switch_request.save()
		
		frappe.db.commit()
		
		# Send SMS notifications
		try:
			requesting_driver_doc = frappe.get_doc("TukTuk Driver", switch_request.requesting_driver)
			switch_with_driver_doc = frappe.get_doc("TukTuk Driver", switch_request.switch_with_driver)
			
			req_message = f"Day-Off Switch APPROVED! You're now scheduled off on {switch_request.requested_date.strftime('%b %d')} instead of {switch_request.my_scheduled_off.strftime('%b %d')}."
			sw_message = f"Day-Off Switch APPROVED! You're now scheduled off on {switch_request.my_scheduled_off.strftime('%b %d')} (working {switch_request.requested_date.strftime('%b %d')})."
			
			from tuktuk_management.api.sms import send_sms
			send_sms(requesting_driver_doc.mpesa_phone_number, req_message)
			send_sms(switch_with_driver_doc.mpesa_phone_number, sw_message)
		except Exception as e:
			frappe.log_error(f"Failed to send approval SMS: {str(e)}")
		
		return {
			"success": True,
			"message": "Switch request approved and roster updated."
		}
		
	except Exception as e:
		frappe.log_error(f"Approve switch error: {str(e)}")
		frappe.db.rollback()
		return {
			"success": False,
			"message": f"Error approving switch request: {str(e)}"
		}


@frappe.whitelist()
def reject_switch_request(request_id, rejection_reason=None):
	"""
	Reject a switch request
	
	Args:
		request_id: Name of the TukTuk Switch Request document
		rejection_reason: Optional reason for rejection
	
	Returns:
		dict: Success status and message
	"""
	try:
		# Get the switch request
		switch_request = frappe.get_doc("TukTuk Switch Request", request_id)
		
		if switch_request.status != "Pending":
			return {
				"success": False,
				"message": f"This request has already been {switch_request.status.lower()}."
			}
		
		# Verify the current user is the switch_with_driver
		driver = frappe.get_all(
			"TukTuk Driver",
			filters={"user_account": frappe.session.user},
			fields=["name"],
			limit=1
		)
		
		if not driver or driver[0].name != switch_request.switch_with_driver:
			return {
				"success": False,
				"message": "You are not authorized to reject this request."
			}
		
		# Update switch request status
		switch_request.status = "Rejected"
		switch_request.rejection_reason = rejection_reason or ""
		switch_request.rejected_date = now_datetime()
		switch_request.rejected_by = frappe.session.user
		switch_request.save()
		
		frappe.db.commit()
		
		# Send SMS notification to requesting driver
		try:
			requesting_driver_doc = frappe.get_doc("TukTuk Driver", switch_request.requesting_driver)
			
			message = f"Day-Off Switch REJECTED by {switch_request.switch_with_driver}. Your original schedule remains: off on {switch_request.my_scheduled_off.strftime('%b %d')}."
			if rejection_reason:
				message += f" Reason: {rejection_reason}"
			
			from tuktuk_management.api.sms import send_sms
			send_sms(requesting_driver_doc.mpesa_phone_number, message)
		except Exception as e:
			frappe.log_error(f"Failed to send rejection SMS: {str(e)}")
		
		return {
			"success": True,
			"message": "Switch request rejected."
		}
		
	except Exception as e:
		frappe.log_error(f"Reject switch error: {str(e)}")
		frappe.db.rollback()
		return {
			"success": False,
			"message": f"Error rejecting switch request: {str(e)}"
		}


@frappe.whitelist()
def get_pending_switch_requests(driver_id):
	"""
	Get all pending switch requests for a driver
	
	SIMPLIFIED VERSION: Just returns empty list until switch request feature is fully implemented
	"""
	try:
		# Get active roster to verify it exists
		active_roster = frappe.get_all(
			"TukTuk Roster Period",
			filters={"status": "Active"},
			limit=1
		)
		
		if not active_roster:
			return {
				"success": False,
				"message": "No active roster",
				"pending_requests": []
			}
		
		# For now, just return empty - no pending requests
		# This prevents errors when the switch request fields aren't set up yet
		return {
			"success": True,
			"pending_requests": []
		}
		
	except Exception as e:
		frappe.log_error(f"Error in get_pending_switch_requests: {str(e)}", "Roster Switch Error")
		# IMPORTANT: Return dict, not list!
		return {
			"success": False,
			"message": str(e),
			"pending_requests": []
		}




@frappe.whitelist()
def mark_sick_day(driver_id, sick_date):
	"""
	Mark a driver as sick for a specific date
	
	Args:
		driver_id: Driver ID
		sick_date: Date driver is sick (YYYY-MM-DD)
	
	Returns:
		dict: Success status and message
	"""
	try:
		sick_date = getdate(sick_date)
		
		# Get active roster period
		roster_period = frappe.get_all(
			"TukTuk Roster Period",
			filters={
				"status": "Active",
				"start_date": ["<=", sick_date],
				"end_date": [">=", sick_date]
			},
			fields=["name"],
			limit=1
		)
		
		if not roster_period:
			return {
				"success": False,
				"message": "No active roster period found for this date."
			}
		
		roster_name = roster_period[0].name
		roster_doc = frappe.get_doc("TukTuk Roster Period", roster_name)
		
		# Check if driver already has a schedule for this date
		existing_schedule = None
		for schedule in roster_doc.day_off_schedules:
			if schedule.driver == driver_id and getdate(schedule.off_date) == sick_date:
				existing_schedule = schedule
				break
		
		if existing_schedule:
			# Update existing schedule
			existing_schedule.is_sick_day = 1
			existing_schedule.reason = "Sick Day"
		else:
			# Create new sick day schedule
			driver_name = frappe.db.get_value("TukTuk Driver", driver_id, "driver_name")
			roster_doc.append("day_off_schedules", {
				"driver": driver_id,
				"driver_name": driver_name,
				"off_date": sick_date,
				"day_of_week": sick_date.strftime("%A").upper(),
				"reason": "Sick Day",
				"is_sick_day": 1
			})
		
		# Assign substitute if needed
		# TODO: Implement substitute assignment logic
		
		roster_doc.save()
		frappe.db.commit()
		
		return {
			"success": True,
			"message": f"Sick day marked for {sick_date.strftime('%Y-%m-%d')}."
		}
		
	except Exception as e:
		frappe.log_error(f"Mark sick day error: {str(e)}")
		frappe.db.rollback()
		return {
			"success": False,
			"message": f"Error marking sick day: {str(e)}"
		}


@frappe.whitelist()
def get_driver_schedule(driver_id, start_date=None, end_date=None):
	"""
	Get a driver's schedule for a date range
	
	Args:
		driver_id: Driver ID
		start_date: Optional start date (defaults to today)
		end_date: Optional end date (defaults to 14 days from start)
	
	Returns:
		list: Schedule entries
	"""
	try:
		if not start_date:
			start_date = today()
		else:
			start_date = getdate(start_date)
		
		if not end_date:
			end_date = add_to_date(start_date, days=14)
		else:
			end_date = getdate(end_date)
		
		# Get roster periods that overlap with the date range
		roster_periods = frappe.get_all(
			"TukTuk Roster Period",
			filters={
				"status": "Active",
				"start_date": ["<=", end_date],
				"end_date": [">=", start_date]
			},
			fields=["name", "start_date", "end_date"]
		)
		
		schedule = []
		
		for period in roster_periods:
			roster_doc = frappe.get_doc("TukTuk Roster Period", period.name)
			
			for day_off in roster_doc.day_off_schedules:
				if day_off.driver == driver_id:
					off_date = getdate(day_off.off_date)
					if start_date <= off_date <= end_date:
						schedule.append({
							"date": off_date,
							"day_of_week": day_off.day_of_week,
							"reason": day_off.reason,
							"is_sick_day": day_off.is_sick_day,
							"status": "Off"
						})
		
		# Sort by date
		schedule.sort(key=lambda x: x["date"])
		
		return schedule
		
	except Exception as e:
		frappe.log_error(f"Get driver schedule error: {str(e)}")
		return []