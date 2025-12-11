# ~/frappe-bench/apps/tuktuk_management/tuktuk_management/tuktuk_management/report/tuktuk_driver_statement/tuktuk_driver_statement.py

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt

def execute(filters=None):
    if not filters:
        filters = {}

    # Validate mandatory filters
    if not filters.get("driver"):
        frappe.throw(_("Please select a driver"))
    if not filters.get("from_date"):
        frappe.throw(_("Please select a From Date"))
    if not filters.get("to_date"):
        frappe.throw(_("Please select a To Date"))

    columns = get_columns()
    data = get_data(filters)
    summary = get_summary(filters)
    chart_data = get_chart_data(data)

    return columns, data, None, chart_data, summary

def get_columns():
    return [
        {
            "fieldname": "posting_date",
            "label": _("Date"),
            "fieldtype": "Date",
            "width": 100
        },
        {
            "fieldname": "transaction_type",
            "label": _("Transaction Type"),
            "fieldtype": "Data",
            "width": 150
        },
        {
            "fieldname": "transaction_id",
            "label": _("Transaction ID"),
            "fieldtype": "Data",
            "width": 150
        },
        {
            "fieldname": "reference",
            "label": _("Reference"),
            "fieldtype": "Dynamic Link",
            "options": "ref_doctype",
            "width": 150
        },
        {
            "fieldname": "ref_doctype",
            "label": _("Reference Type"),
            "fieldtype": "Data",
            "width": 0,
            "hidden": 1
        },
        {
            "fieldname": "description",
            "label": _("Description"),
            "fieldtype": "Data",
            "width": 200
        },
        {
            "fieldname": "revenue",
            "label": _("Trip Revenue"),
            "fieldtype": "Currency",
            "width": 120
        },
        {
            "fieldname": "driver_share",
            "label": _("Driver Share"),
            "fieldtype": "Currency",
            "width": 120
        },
        {
            "fieldname": "target_contribution",
            "label": _("Target Contribution"),
            "fieldtype": "Currency",
            "width": 130
        },
        {
            "fieldname": "deposit_amount",
            "label": _("Deposit Amount"),
            "fieldtype": "Currency",
            "width": 120
        },
        {
            "fieldname": "balance_after",
            "label": _("Balance After"),
            "fieldtype": "Currency",
            "width": 120
        }
    ]

def get_data(filters):
    driver = filters.get("driver")
    from_date = filters.get("from_date")
    to_date = filters.get("to_date")

    # Get all transactions (rides and adjustments)
    transactions = frappe.db.sql("""
        SELECT
            DATE(tt.timestamp) as posting_date,
            CASE 
                WHEN tt.transaction_type = 'Adjustment' THEN 'Adjustment Transaction'
                WHEN tt.transaction_type = 'Driver Repayment' THEN 'Driver Repayment'
                ELSE 'Ride Payment'
            END as transaction_type,
            tt.transaction_id,
            tt.name as reference,
            'TukTuk Transaction' as ref_doctype,
            CASE 
                WHEN tt.transaction_type = 'Adjustment' THEN CONCAT('Adjustment: ', tt.customer_phone)
                WHEN tt.transaction_type = 'Driver Repayment' THEN CONCAT('Driver Repayment: ', tt.customer_phone)
                ELSE CONCAT('Customer: ', tt.customer_phone)
            END as description,
            tt.amount as revenue,
            tt.driver_share,
            tt.target_contribution,
            0 as deposit_amount,
            NULL as balance_after,
            tt.timestamp as sort_timestamp
        FROM
            `tabTukTuk Transaction` tt
        WHERE
            tt.driver = %(driver)s
            AND DATE(tt.timestamp) BETWEEN %(from_date)s AND %(to_date)s
            AND tt.payment_status = 'Completed'
        ORDER BY
            tt.timestamp
    """, {
        'driver': driver,
        'from_date': from_date,
        'to_date': to_date
    }, as_dict=1)

    # Get deposit transactions from the driver's deposit history
    deposit_transactions = frappe.db.sql("""
        SELECT
            ddt.transaction_date as posting_date,
            CONCAT('Deposit - ', ddt.transaction_type) as transaction_type,
            ddt.transaction_reference as transaction_id,
            td.name as reference,
            'TukTuk Driver' as ref_doctype,
            COALESCE(ddt.description, ddt.transaction_type) as description,
            0 as revenue,
            0 as driver_share,
            0 as target_contribution,
            ddt.amount as deposit_amount,
            ddt.balance_after_transaction as balance_after,
            CONCAT(ddt.transaction_date, ' 23:59:59') as sort_timestamp
        FROM
            `tabDriver Deposit Transaction` ddt
        JOIN
            `tabTukTuk Driver` td ON ddt.parent = td.name
        WHERE
            td.name = %(driver)s
            AND ddt.transaction_date BETWEEN %(from_date)s AND %(to_date)s
        ORDER BY
            ddt.transaction_date
    """, {
        'driver': driver,
        'from_date': from_date,
        'to_date': to_date
    }, as_dict=1)

    # Combine both transaction types and sort by timestamp
    all_transactions = transactions + deposit_transactions
    all_transactions = sorted(all_transactions, key=lambda x: x.get('sort_timestamp', ''))

    # Remove the sort_timestamp field before returning
    for row in all_transactions:
        row.pop('sort_timestamp', None)

    return all_transactions

def get_summary(filters):
    """Get summary statistics for the driver statement"""
    driver = filters.get("driver")
    from_date = filters.get("from_date")
    to_date = filters.get("to_date")

    # Get driver information
    driver_info = frappe.db.get_value(
        "TukTuk Driver",
        driver,
        ["driver_name", "current_balance", "current_deposit_balance"],
        as_dict=1
    )

    # Get transaction summaries (excluding adjustments and repayments from earnings)
    trip_summary = frappe.db.sql("""
        SELECT
            COUNT(CASE WHEN transaction_type NOT IN ('Adjustment', 'Driver Repayment') THEN 1 END) as total_trips,
            SUM(CASE WHEN transaction_type NOT IN ('Adjustment', 'Driver Repayment') THEN amount ELSE 0 END) as total_revenue,
            SUM(CASE WHEN transaction_type NOT IN ('Adjustment', 'Driver Repayment') THEN driver_share ELSE 0 END) as total_driver_earnings,
            SUM(CASE WHEN transaction_type NOT IN ('Adjustment', 'Driver Repayment') THEN target_contribution ELSE 0 END) as total_target_contribution,
            COUNT(CASE WHEN transaction_type = 'Adjustment' THEN 1 END) as total_adjustments,
            SUM(CASE WHEN transaction_type = 'Adjustment' THEN amount ELSE 0 END) as total_adjustment_amount,
            COUNT(CASE WHEN transaction_type = 'Driver Repayment' THEN 1 END) as total_repayments,
            SUM(CASE WHEN transaction_type = 'Driver Repayment' THEN amount ELSE 0 END) as total_repayment_amount
        FROM
            `tabTukTuk Transaction`
        WHERE
            driver = %(driver)s
            AND DATE(timestamp) BETWEEN %(from_date)s AND %(to_date)s
            AND payment_status = 'Completed'
    """, {
        'driver': driver,
        'from_date': from_date,
        'to_date': to_date
    }, as_dict=1)[0]

    # Get deposit transaction summary
    deposit_summary = frappe.db.sql("""
        SELECT
            SUM(CASE WHEN ddt.transaction_type IN ('Initial Deposit', 'Top Up')
                THEN ddt.amount ELSE 0 END) as total_deposits,
            SUM(CASE WHEN ddt.transaction_type IN ('Target Deduction', 'Damage Deduction')
                THEN ddt.amount ELSE 0 END) as total_deductions,
            SUM(CASE WHEN ddt.transaction_type = 'Refund'
                THEN ddt.amount ELSE 0 END) as total_refunds
        FROM
            `tabDriver Deposit Transaction` ddt
        JOIN
            `tabTukTuk Driver` td ON ddt.parent = td.name
        WHERE
            td.name = %(driver)s
            AND ddt.transaction_date BETWEEN %(from_date)s AND %(to_date)s
    """, {
        'driver': driver,
        'from_date': from_date,
        'to_date': to_date
    }, as_dict=1)[0]

    summary = [
        {
            "value": driver_info.get("driver_name"),
            "label": _("Driver Name"),
            "datatype": "Data"
        },
        {
            "value": trip_summary.get("total_trips") or 0,
            "label": _("Total Trips"),
            "datatype": "Int",
            "indicator": "Blue"
        },
        {
            "value": flt(trip_summary.get("total_revenue") or 0),
            "label": _("Total Revenue"),
            "datatype": "Currency",
            "indicator": "Green"
        },
        {
            "value": flt(trip_summary.get("total_driver_earnings") or 0),
            "label": _("Total Driver Earnings"),
            "datatype": "Currency",
            "indicator": "Green"
        },
        {
            "value": flt(trip_summary.get("total_target_contribution") or 0),
            "label": _("Total Target Contribution"),
            "datatype": "Currency",
            "indicator": "Orange"
        },
        {
            "value": flt(deposit_summary.get("total_deposits") or 0),
            "label": _("Total Deposits"),
            "datatype": "Currency",
            "indicator": "Blue"
        },
        {
            "value": flt(deposit_summary.get("total_deductions") or 0),
            "label": _("Total Deductions"),
            "datatype": "Currency",
            "indicator": "Red"
        },
        {
            "value": flt(driver_info.get("current_balance") or 0),
            "label": _("Current Target Balance"),
            "datatype": "Currency",
            "indicator": "Purple"
        },
        {
            "value": flt(driver_info.get("current_deposit_balance") or 0),
            "label": _("Current Deposit Balance"),
            "datatype": "Currency",
            "indicator": "Purple"
        },
        {
            "value": trip_summary.get("total_adjustments") or 0,
            "label": _("Total Adjustments"),
            "datatype": "Int",
            "indicator": "Orange"
        },
        {
            "value": flt(trip_summary.get("total_adjustment_amount") or 0),
            "label": _("Total Adjustment Amount"),
            "datatype": "Currency",
            "indicator": "Orange"
        },
        {
            "value": trip_summary.get("total_repayments") or 0,
            "label": _("Total Repayments"),
            "datatype": "Int",
            "indicator": "Green"
        },
        {
            "value": flt(trip_summary.get("total_repayment_amount") or 0),
            "label": _("Total Repayment Amount"),
            "datatype": "Currency",
            "indicator": "Green"
        }
    ]

    return summary

def get_chart_data(data):
    """Generate chart data for visualization"""
    if not data:
        return None

    # Group data by date and sum earnings
    date_earnings = {}
    for row in data:
        date = row.get("posting_date")
        if date:
            if date not in date_earnings:
                date_earnings[date] = {
                    "driver_share": 0,
                    "target_contribution": 0,
                    "deposit_amount": 0
                }
            date_earnings[date]["driver_share"] += flt(row.get("driver_share", 0))
            date_earnings[date]["target_contribution"] += flt(row.get("target_contribution", 0))
            date_earnings[date]["deposit_amount"] += flt(row.get("deposit_amount", 0))

    # Sort dates
    sorted_dates = sorted(date_earnings.keys())

    driver_shares = [date_earnings[date]["driver_share"] for date in sorted_dates]
    target_contributions = [date_earnings[date]["target_contribution"] for date in sorted_dates]

    return {
        "data": {
            "labels": [str(date) for date in sorted_dates],
            "datasets": [
                {
                    "name": "Driver Earnings",
                    "values": driver_shares
                },
                {
                    "name": "Target Contribution",
                    "values": target_contributions
                }
            ]
        },
        "type": "line",
        "colors": ["#28a745", "#ffa500"]
    }
