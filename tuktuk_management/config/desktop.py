from frappe import _

def get_data():
    return [
        {
            "module_name": "Tuktuk Management",
            "type": "module",
            "label": _("Tuktuk Management"),
            "icon": "octicon octicon-file-directory",  # You can use any valid icon class
            "color": "blue",
            "onboard_present": 1,
            "link": "modules/Tuktuk Management"
        }
    ]
