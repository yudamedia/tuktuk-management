# ~/frappe-bench/apps/tuktuk_management/tuktuk_management/patches/add_location_fields.py

import frappe

def execute():
    """Add location fields to TukTuk Vehicle DocType"""
    try:
        # Get the TukTuk Vehicle DocType
        doctype_name = "TukTuk Vehicle"
        
        if not frappe.db.exists("DocType", doctype_name):
            print(f"❌ DocType {doctype_name} does not exist")
            return
        
        # Check if location fields already exist
        existing_fields = frappe.get_all("DocField", 
                                       filters={"parent": doctype_name},
                                       fields=["fieldname"])
        existing_fieldnames = [f.fieldname for f in existing_fields]
        
        # Fields to add
        new_fields = [
            {
                "fieldname": "location_tab",
                "fieldtype": "Tab Break",
                "label": "Location & Tracking",
                "insert_after": "rental_rates_tab"
            },
            {
                "fieldname": "current_location_section", 
                "fieldtype": "Section Break",
                "label": "Current Location"
            },
            {
                "fieldname": "current_location",
                "fieldtype": "Geolocation", 
                "label": "Current Location",
                "description": "Current GPS location of the TukTuk"
            },
            {
                "fieldname": "coordinates_section",
                "fieldtype": "Section Break",
                "label": "Manual Coordinates Entry",
                "collapsible": 1
            },
            {
                "fieldname": "latitude",
                "fieldtype": "Float",
                "label": "Latitude", 
                "description": "Latitude coordinate (-90 to 90)",
                "precision": "6"
            },
            {
                "fieldname": "column_break_coords",
                "fieldtype": "Column Break"
            },
            {
                "fieldname": "longitude",
                "fieldtype": "Float",
                "label": "Longitude",
                "description": "Longitude coordinate (-180 to 180)", 
                "precision": "6"
            },
            {
                "fieldname": "location_notes",
                "fieldtype": "Small Text",
                "label": "Location Notes",
                "description": "Optional notes about current location or landmarks"
            }
        ]
        
        # Add fields that don't exist
        fields_added = 0
        for field_config in new_fields:
            if field_config["fieldname"] not in existing_fieldnames:
                add_field_to_doctype(doctype_name, field_config)
                fields_added += 1
                print(f"✅ Added field: {field_config['fieldname']}")
            else:
                print(f"⚠️  Field already exists: {field_config['fieldname']}")
        
        if fields_added > 0:
            # Reload the DocType
            frappe.reload_doctype(doctype_name)
            print(f"✅ Added {fields_added} location fields to {doctype_name}")
            print("✅ DocType reloaded successfully")
        else:
            print(f"ℹ️  All location fields already exist in {doctype_name}")
        
        # Update existing records to have default coordinates (Diani Beach area)
        update_existing_records()
        
        frappe.db.commit()
        
    except Exception as e:
        print(f"❌ Error adding location fields: {str(e)}")
        frappe.log_error(f"Location fields patch error: {str(e)}")

def add_field_to_doctype(doctype_name, field_config):
    """Add a field to a doctype"""
    try:
        # Get the doctype document
        doc = frappe.get_doc("DocType", doctype_name)
        
        # Find insertion point
        insert_after = field_config.pop("insert_after", None)
        insert_idx = len(doc.fields)
        
        if insert_after:
            for idx, field in enumerate(doc.fields):
                if field.fieldname == insert_after:
                    insert_idx = idx + 1
                    break
        
        # Create new field
        new_field = frappe.new_doc("DocField")
        new_field.update(field_config)
        new_field.parent = doctype_name
        new_field.parenttype = "DocType"
        new_field.parentfield = "fields"
        new_field.idx = insert_idx + 1
        
        # Insert the field
        doc.fields.insert(insert_idx, new_field)
        
        # Update idx for all fields after insertion point
        for i in range(insert_idx + 1, len(doc.fields)):
            doc.fields[i].idx = i + 1
        
        # Save the doctype
        doc.save()
        
    except Exception as e:
        print(f"❌ Error adding field {field_config.get('fieldname')}: {str(e)}")
        raise

def update_existing_records():
    """Update existing TukTuk Vehicle records with default location data"""
    try:
        # Get all existing vehicles without location data
        vehicles = frappe.get_all("TukTuk Vehicle", 
                                 filters={"latitude": ["in", [None, ""]]},
                                 fields=["name", "tuktuk_id"])
        
        if not vehicles:
            print("ℹ️  No vehicles need location data updates")
            return
        
        # Default coordinates for Diani Beach area
        base_lat = -4.2854
        base_lng = 39.5873
        
        updated_count = 0
        for idx, vehicle in enumerate(vehicles):
            try:
                # Add small random offset to spread vehicles around Diani Beach
                import random
                lat_offset = random.uniform(-0.01, 0.01)  # About ±1km
                lng_offset = random.uniform(-0.01, 0.01)
                
                new_lat = base_lat + lat_offset
                new_lng = base_lng + lng_offset
                
                # Update the vehicle record
                frappe.db.set_value("TukTuk Vehicle", vehicle.name, {
                    "latitude": new_lat,
                    "longitude": new_lng,
                    "location_notes": "Default Diani Beach area location"
                })
                
                updated_count += 1
                
            except Exception as e:
                print(f"❌ Error updating vehicle {vehicle.tuktuk_id}: {str(e)}")
        
        if updated_count > 0:
            print(f"✅ Updated {updated_count} vehicles with default location data")
        
    except Exception as e:
        print(f"❌ Error updating existing records: {str(e)}")

if __name__ == "__main__":
    execute()