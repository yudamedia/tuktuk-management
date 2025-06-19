# ~/frappe-bench/apps/tuktuk_management/tuktuk_management/tuktuk_management/report/deposit_management_report/deposit_management_report.py

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt, getdate

def execute(filters=None):
    if not filters:
        filters = {}

    columns = get_columns()
    data = get_data(filters)
    
    chart_data = get_chart_data(data)
    summary = get_summary(data)
    
    return columns, data, None, chart_data, summary

def get_columns():
    return [
        {
            "fieldname": "driver_name",
            "label": _("Driver Name"),
            "fieldtype": "Link",
            "options": "TukTuk Driver",
            "width": 150
        },
        {
            "fieldname": "driver_national_id",
            "label": _("National ID"),
            "fieldtype": "Data",
            "width": 100
        },
        {
            "fieldname": "deposit_required",
            "label": _("Deposit Required"),
            "fieldtype": "Check",
            "width": 80
        },
        {
            "fieldname": "initial_deposit",
            "label": _("Initial Deposit"),
            "fieldtype": "Currency",
            "width": 120
        },
        {
            "fieldname": "current_balance",
            "label": _("Current Balance"),
            "fieldtype": "Currency",
            "width": 120
        },
        {
            "fieldname": "total_deposits",
            "label": _("Total Deposits"),
            "fieldtype": "Currency",
            "width": 120
        },
        {
            "fieldname": "total_deductions",
            "label": _("Total Deductions"),
            "fieldtype": "Currency",
            "width": 120
        },
        {
            "fieldname": "allows_target_deduction",
            "label": _("Allows Target Deduction"),
            "fieldtype": "Check",
            "width": 80
        },
        {
            "fieldname": "assigned_tuktuk",
            "label": _("Assigned TukTuk"),
            "fieldtype": "Link",
            "options": "TukTuk Vehicle",
            "width": 120
        },
        {
            "fieldname": "target_balance",
            "label": _("Target Balance"),
            "fieldtype": "Currency",
            "width": 120
        },
        {
            "fieldname": "consecutive_misses",
            "label": _("Consecutive Misses"),
            "fieldtype": "Int",
            "width": 80
        },
        {
            "fieldname": "exit_date",
            "label": _("Exit Date"),
            "fieldtype": "Date",
            "width": 100
        },
        {
            "fieldname": "refund_status",
            "label": _("Refund Status"),
            "fieldtype": "Data",
            "width": 100
        },
        {
            "fieldname": "refund_amount",
            "label": _("Refund Amount"),
            "fieldtype": "Currency",
            "width": 120
        }
    ]

def get_data(filters):
    conditions = get_conditions(filters)
    
    # Main query to get driver data
    data = frappe.db.sql(f"""
        SELECT 
            d.name as driver_name,
            d.driver_national_id,
            d.deposit_required,
            d.initial_deposit_amount as initial_deposit,
            d.current_deposit_balance as current_balance,
            d.allow_target_deduction_from_deposit as allows_target_deduction,
            d.assigned_tuktuk,
            d.current_balance as target_balance,
            d.consecutive_misses,
            d.exit_date,
            d.refund_status,
            d.refund_amount
        FROM 
            `tabTukTuk Driver` d
        WHERE 
            {conditions}
        ORDER BY 
            d.driver_name
    """, filters, as_dict=1)
    
    # Calculate totals for each driver
    for row in data:
        if row.driver_name:
            # Get transaction totals
            transaction_totals = frappe.db.sql("""
                SELECT 
                    SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END) as total_deposits,
                    SUM(CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END) as total_deductions
                FROM `tabDriver Deposit Transaction`
                WHERE parent = %s
            """, (row.driver_name,), as_dict=1)
            
            if transaction_totals:
                row.total_deposits = transaction_totals[0].total_deposits or 0
                row.total_deductions = transaction_totals[0].total_deductions or 0
            else:
                row.total_deposits = 0
                row.total_deductions = 0
    
    return data

def get_conditions(filters):
    conditions = "1=1"
    
    if filters.get("driver"):
        conditions += " AND d.name = %(driver)s"
    
    if filters.get("deposit_status"):
        if filters.get("deposit_status") == "Required":
            conditions += " AND d.deposit_required = 1"
        elif filters.get("deposit_status") == "Not Required":
            conditions += " AND d.deposit_required = 0"
    
    if filters.get("exit_status"):
        if filters.get("exit_status") == "Active":
            conditions += " AND (d.exit_date IS NULL OR d.exit_date = '')"
        elif filters.get("exit_status") == "Exited":
            conditions += " AND d.exit_date IS NOT NULL"
    
    if filters.get("refund_status"):
        conditions += " AND d.refund_status = %(refund_status)s"
    
    if filters.get("allows_target_deduction"):
        if filters.get("allows_target_deduction") == "Yes":
            conditions += " AND d.allow_target_deduction_from_deposit = 1"
        elif filters.get("allows_target_deduction") == "No":
            conditions += " AND d.allow_target_deduction_from_deposit = 0"
    
    return conditions

def get_chart_data(data):
    if not data:
        return None

    # Chart showing deposit status distribution
    deposit_required = len([d for d in data if d.deposit_required])
    no_deposit = len([d for d in data if not d.deposit_required])
    
    return {
        "data": {
            "labels": ["Deposit Required", "No Deposit"],
            "datasets": [
                {
                    "name": "Driver Count",
                    "values": [deposit_required, no_deposit]
                }
            ]
        },
        "type": "pie",
        "colors": ["#5e64ff", "#36a2eb"]
    }

def get_summary(data):
    if not data:
        return []
    
    # Calculate summary statistics
    active_drivers = [d for d in data if not d.exit_date]
    exited_drivers = [d for d in data if d.exit_date]
    
    total_initial_deposits = sum([flt(d.initial_deposit) for d in data if d.deposit_required])
    total_current_balances = sum([flt(d.current_balance) for d in data if d.deposit_required])
    total_refunds_pending = sum([flt(d.refund_amount) for d in exited_drivers if d.refund_status == 'Pending'])
    
    drivers_allow_deduction = len([d for d in active_drivers if d.allows_target_deduction])
    drivers_with_negative_target = len([d for d in active_drivers if flt(d.target_balance) < 0])
    
    return [
        {
            "label": _("Total Drivers"),
            "value": len(data),
            "indicator": "Blue"
        },
        {
            "label": _("Active Drivers"),
            "value": len(active_drivers),
            "indicator": "Green"
        },
        {
            "label": _("Exited Drivers"),
            "value": len(exited_drivers),
            "indicator": "Grey"
        },
        {
            "label": _("Total Initial Deposits"),
            "value": f"{total_initial_deposits:,.0f} KSH",
            "indicator": "Blue"
        },
        {
            "label": _("Total Current Balances"),
            "value": f"{total_current_balances:,.0f} KSH",
            "indicator": "Green" if total_current_balances >= total_initial_deposits * 0.8 else "Orange"
        },
        {
            "label": _("Pending Refunds"),
            "value": f"{total_refunds_pending:,.0f} KSH",
            "indicator": "Orange" if total_refunds_pending > 0 else "Green"
        },
        {
            "label": _("Drivers Allow Target Deduction"),
            "value": f"{drivers_allow_deduction}/{len(active_drivers)}",
            "indicator": "Blue"
        },
        {
            "label": _("Drivers with Negative Target Balance"),
            "value": drivers_with_negative_target,
            "indicator": "Red" if drivers_with_negative_target > 0 else "Green"
        }
    ]