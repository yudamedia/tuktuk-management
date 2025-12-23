// Copyright (c) 2024, Yuda Media and contributors
// For license information, please see license.txt

frappe.ui.form.on("TukTuk Driver", {
	refresh(frm) {
		// Show archive button only for terminated drivers
		if (frm.doc.exit_date && !frm.is_new()) {
			frm.add_custom_button(__('Archive Driver'), function() {
				frappe.confirm(
					`Archive driver ${frm.doc.driver_name}?<br><br>
					<b>This will:</b><br>
					- Move all driver data to archived records<br>
					- Preserve transaction history<br>
					- Allow future restoration<br><br>
					<b>Driver can be restored later if needed.</b>`,
					function() {
						frappe.prompt({
							label: 'Archival Reason',
							fieldname: 'reason',
							fieldtype: 'Small Text',
							default: 'Driver termination completed'
						}, function(values) {
							frappe.call({
								method: 'tuktuk_management.api.tuktuk.archive_terminated_driver',
								args: {
									driver_name: frm.doc.name,
									archival_reason: values.reason
								},
								callback: function(r) {
									if (r.message && r.message.success) {
										frappe.show_alert({
											message: 'Driver archived successfully',
											indicator: 'green'
										});
										frappe.set_route('Form', 'Terminated TukTuk Driver', frm.doc.name);
									}
								}
							});
						}, 'Archive Driver', 'Archive');
					}
				);
			}, __('Actions')).addClass('btn-warning');
		}

		// Visual indicator for terminated drivers
		if (frm.doc.exit_date) {
			frm.dashboard.add_indicator(__('Terminated - Ready for Archival'), 'orange');
		}
	}
});
