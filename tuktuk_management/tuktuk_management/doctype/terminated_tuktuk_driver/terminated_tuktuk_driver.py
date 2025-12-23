# Copyright (c) 2025, Sunny TukTuk and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class TerminatedTukTukDriver(Document):
	"""
	Archived driver record for terminated TukTuk Drivers.
	This doctype stores historical data for drivers who have exited the system.
	All fields are read-only except refund_status and archival_reason.
	"""

	def validate(self):
		"""Validate that archived data is not modified"""
		# Allow updates to refund_status and archival_reason
		if not self.is_new():
			# Get the current document from database
			old_doc = self.get_doc_before_save()

			# List of fields that can be modified
			editable_fields = ['refund_status', 'archival_reason', 'modified', 'modified_by']

			# Check if any non-editable fields were changed
			for field in self.meta.get_fieldnames():
				if field not in editable_fields:
					old_value = old_doc.get(field) if old_doc else None
					new_value = self.get(field)

					# Skip comparison for child tables (handled separately)
					if self.meta.get_field(field).fieldtype == 'Table':
						continue

					if old_value != new_value:
						frappe.throw(
							f"Cannot modify archived driver data. Field '{field}' is read-only.",
							title="Modification Not Allowed"
						)

	def before_save(self):
		"""Set archival metadata on creation"""
		if self.is_new():
			if not self.archived_on:
				self.archived_on = frappe.utils.now_datetime()
			if not self.archived_by:
				self.archived_by = frappe.session.user
