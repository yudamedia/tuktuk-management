from frappe import _

def get_data():
    return {
        "label": _("Tuktuk Management"),
        "items": [
            {
                "type": "doctype",
                "name": "TukTuk Driver",
                "label": _("TukTuk Driver"),
                "description": _("Manage TukTuk Drivers"),
            },
            {
                "type": "doctype",
                "name": "TukTuk Vehicle",
                "label": _("TukTuk Vehicle"),
                "description": _("Manage TukTuk Vehicles"),
            },
            {
                "type": "doctype",
                "name": "TukTuk Rental",
                "label": _("TukTuk Rental"),
                "description": _("Manage TukTuk Rentals"),
            },
            {
                "type": "doctype",
                "name": "TukTuk Settings",
                "label": _("TukTuk Settings"),
                "description": _("TukTuk Management Settings"),
            },
            {
                "type": "doctype",
                "name": "TukTuk Transaction",
                "label": _("TukTuk Transaction"),
                "description": _("View TukTuk Transactions"),
            },
        ]
    }
