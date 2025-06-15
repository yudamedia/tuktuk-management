from frappe import _

def get_modules_dict():
    return {
        "Tuktuk Management": {
            "color": "blue",
            "icon": "octicon octicon-file-directory",
            "type": "module",
            "label": _("Tuktuk Management"),
            "link": "List/TukTuk Vehicle",
            "doctype": [
                "TukTuk Vehicle",
                "TukTuk Driver",
                "TukTuk Transaction",
                "TukTuk Rental",
                "TukTuk Settings"
            ]
        }
    }
