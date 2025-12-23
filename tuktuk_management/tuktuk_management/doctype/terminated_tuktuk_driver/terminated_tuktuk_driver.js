// Copyright (c) 2025, Sunny TukTuk and contributors
// For license information, please see license.txt

frappe.ui.form.on("Terminated TukTuk Driver", {
	refresh(frm) {
		// Make form read-only with visual distinction
		frm.disable_save();
		frm.page.set_indicator(__('Archived'), 'red');

		// Add restore button
		frm.add_custom_button(__('Restore to Active'), function() {
			frappe.confirm(
				`Restore driver ${frm.doc.driver_name} to active status?<br><br>
				<b>This will:</b><br>
				- Move driver back to active records<br>
				- Clear termination status<br>
				- Reset performance metrics<br>
				- Require re-assignment to a TukTuk<br><br>
				<b>Deposit history will be preserved.</b>`,
				function() {
					frappe.prompt({
						label: 'Restoration Reason',
						fieldname: 'reason',
						fieldtype: 'Small Text',
						reqd: 1
					}, function(values) {
						frappe.call({
							method: 'tuktuk_management.api.tuktuk.restore_archived_driver',
							args: {
								original_driver_id: frm.doc.name,
								restore_reason: values.reason
							},
							callback: function(r) {
								if (r.message && r.message.success) {
									frappe.show_alert({
										message: 'Driver restored successfully',
										indicator: 'green'
									});
									frappe.set_route('Form', 'TukTuk Driver', frm.doc.original_driver_id);
								}
							}
						});
					}, 'Restore Driver', 'Restore');
				}
			);
		}, __('Actions')).addClass('btn-primary');

		// Add view transactions button
		frm.add_custom_button(__('View Transactions'), function() {
			frappe.set_route('List', 'TukTuk Transaction', {
				'driver': frm.doc.original_driver_id
			});
		}, __('Related'));

		// Add view rentals button
		frm.add_custom_button(__('View Rentals'), function() {
			frappe.set_route('List', 'TukTuk Rental', {
				'driver': frm.doc.original_driver_id
			});
		}, __('Related'));
	},

	onload(frm) {
		// Visual styling for archived status
		frm.page.wrapper.find('.layout-main-section').css({
			'background-color': '#fff9e6',
			'border-left': '4px solid #ff9800'
		});
	}
});
