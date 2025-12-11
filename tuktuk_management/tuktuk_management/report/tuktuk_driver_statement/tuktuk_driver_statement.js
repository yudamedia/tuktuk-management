// Copyright (c) 2025, Yuda Media and contributors
// For license information, please see license.txt

frappe.query_reports["TukTuk Driver Statement"] = {
	"filters": [
		{
			"fieldname": "driver",
			"label": __("Driver"),
			"fieldtype": "Link",
			"options": "TukTuk Driver",
			"reqd": 1
		},
		{
			"fieldname": "from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.add_months(frappe.datetime.get_today(), -1),
			"reqd": 1
		},
		{
			"fieldname": "to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.get_today(),
			"reqd": 1
		}
	],

	"formatter": function(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);

		// Highlight deposit transactions differently
		if (data && data.transaction_type && data.transaction_type.includes("Deposit")) {
			if (column.fieldname == "transaction_type") {
				value = `<span style="color: #007bff; font-weight: bold;">${data.transaction_type}</span>`;
			}
		}

		// Highlight negative amounts in red
		if (column.fieldname == "deposit_amount" && data && data.deposit_amount < 0) {
			value = `<span style="color: red;">${value}</span>`;
		}

		return value;
	}
};
