# ~/frappe-bench/apps/tuktuk_management/tuktuk_management/patches/create_workspace.py

import frappe
from frappe import _

def execute():
    """Create Tuktuk Management workspace"""
    
    workspace_name = "Tuktuk Management"
    
    # Try to get existing workspace or create new one
    try:
        workspace = frappe.get_doc("Workspace", workspace_name)
    except frappe.DoesNotExistError:
        workspace = frappe.new_doc("Workspace")
        workspace.name = workspace_name
        
    # Update workspace properties
    workspace.update({
        "label": workspace_name,
        "category": "Modules",
        "extends": "",
        "module": "Tuktuk Management",
        "icon": "vehicle",
        "is_standard": 1,
        "public": 1,
        "title": workspace_name,
        "sequence_id": "1.0",
        "charts": [],
        "shortcuts": [
            {
                "type": "DocType",
                "link_to": "TukTuk Vehicle",
                "label": "Total Tuktuks",
                "color": "blue",
                "stats_filter": "{}"
            },
            {
                "type": "DocType",
                "link_to": "TukTuk Vehicle",
                "label": "Assigned Tuktuks",
                "color": "green",
                "stats_filter": "{\"status\": \"Assigned\"}"
            },
            {
                "type": "DocType",
                "link_to": "TukTuk Rental",
                "label": "Active Rentals",
                "color": "orange",
                "stats_filter": "{\"status\": \"Active\"}"
            }
        ],
        "links": [
            {
                "label": "Operations",
                "type": "Card Break",
                "hidden": 0,
                "items": [
                    {
                        "type": "doctype",
                        "name": "TukTuk Vehicle",
                        "label": "TukTuk Vehicle"
                    },
                    {
                        "type": "doctype",
                        "name": "TukTuk Driver",
                        "label": "TukTuk Driver"
                    },
                    {
                        "type": "doctype",
                        "name": "TukTuk Rental",
                        "label": "TukTuk Rental"
                    },
                    {
                        "type": "doctype",
                        "name": "TukTuk Settings",
                        "label": "TukTuk Settings"
                    }
                ]
            },
            {
                "label": "Transactions",
                "type": "Card Break",
                "hidden": 0,
                "items": [
                    {
                        "type": "doctype",
                        "name": "TukTuk Transaction",
                        "label": "TukTuk Transaction"
                    },
                    {
                        "type": "doctype",
                        "name": "TukTuk Daily Report",
                        "label": "TukTuk Daily Report"
                    }
                ]
            }
        ]
    })

    # Save the workspace
    workspace.save(ignore_permissions=True)
    frappe.db.commit()
