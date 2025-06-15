# ~/frappe-bench/apps/tuktuk_management/tuktuk_management/tuktuk_management/report/driver_performance_report/driver_performance_report.py

from __future__ import unicode_literals
import frappe
from frappe import _

def execute(filters=None):
    if not filters:
        filters = {}

    columns = get_columns()
    data = get_data(filters)
    
    chart_data = get_chart_data(data)
    
    return columns, data, None, chart_data

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
            "fieldname": "total_trips",
            "label": _("Total Trips"),
            "fieldtype": "Int",
            "width": 100
        },
        {
            "fieldname": "total_revenue",
            "label": _("Total Revenue"),
            "fieldtype": "Currency",
            "width": 120
        },
        {
            "fieldname": "driver_earnings",
            "label": _("Driver Earnings"),
            "fieldtype": "Currency",
            "width": 120
        },
        {
            "fieldname": "target_progress",
            "label": _("Target Progress"),
            "fieldtype": "Percent",
            "width": 120
        },
        {
            "fieldname": "avg_battery_level",
            "label": _("Avg Battery Level"),
            "fieldtype": "Percent",
            "width": 120
        },
        {
            "fieldname": "charging_stops",
            "label": _("Charging Stops"),
            "fieldtype": "Int",
            "width": 120
        },
        {
            "fieldname": "missed_targets",
            "label": _("Missed Targets"),
            "fieldtype": "Int",
            "width": 120
        }
    ]

def get_data(filters):
    conditions = get_conditions(filters)
    
    data = frappe.db.sql("""
        SELECT 
            td.name as driver_name,
            COUNT(DISTINCT tt.name) as total_trips,
            SUM(tt.amount) as total_revenue,
            SUM(tt.driver_share) as driver_earnings,
            (td.current_balance / COALESCE(td.daily_target, 
                (SELECT global_daily_target FROM `tabTukTuk Settings` LIMIT 1))) * 100 
                as target_progress,
            (SELECT AVG(battery_level) 
             FROM `tabTukTuk Vehicle` 
             WHERE name = td.assigned_tuktuk) as avg_battery_level,
            (SELECT COUNT(*) 
             FROM `tabTukTuk Vehicle` tv 
             WHERE tv.name = td.assigned_tuktuk 
             AND tv.status = 'Charging') as charging_stops,
            td.consecutive_misses as missed_targets
        FROM 
            `tabTukTuk Driver` td
        LEFT JOIN 
            `tabTukTuk Transaction` tt ON td.name = tt.driver
        WHERE 
            {conditions}
        GROUP BY 
            td.name
        ORDER BY 
            td.name
    """.format(conditions=conditions), filters, as_dict=1)
    
    return data

def get_conditions(filters):
    conditions = "1=1"
    
    if filters.get("from_date"):
        conditions += " AND tt.timestamp >= %(from_date)s"
    
    if filters.get("to_date"):
        conditions += " AND tt.timestamp <= %(to_date)s"
        
    if filters.get("driver"):
        conditions += " AND td.name = %(driver)s"
        
    if filters.get("target_status"):
        if filters.get("target_status") == "Met":
            conditions += " AND td.current_balance >= COALESCE(td.daily_target, \
                (SELECT global_daily_target FROM `tabTukTuk Settings` LIMIT 1))"
        else:
            conditions += " AND td.current_balance < COALESCE(td.daily_target, \
                (SELECT global_daily_target FROM `tabTukTuk Settings` LIMIT 1))"
    
    return conditions

def get_chart_data(data):
    if not data:
        return None

    labels = [row.get("driver_name") for row in data]
    target_progress = [row.get("target_progress") for row in data]
    
    return {
        "data": {
            "labels": labels,
            "datasets": [
                {
                    "name": "Target Progress",
                    "values": target_progress
                }
            ]
        },
        "type": "bar",
        "colors": ["#5e64ff"]
    }