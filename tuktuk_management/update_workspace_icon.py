#!/usr/bin/env python3
"""
Script to update the Tuktuk Management workspace icon to 🚗
Run this from the frappe-bench directory: bench execute tuktuk_management.update_workspace_icon.update_icon
"""

import frappe

def update_icon():
    """Update the Tuktuk Management workspace icon to 🚗"""
    try:
        # Get the workspace
        workspace = frappe.get_doc("Workspace", "Tuktuk Management")
        
        # Update the icon
        workspace.icon = "🚗"
        
        # Save the changes
        workspace.save()
        
        print("✅ Successfully updated Tuktuk Management workspace icon to 🚗")
        
        # Commit the changes
        frappe.db.commit()
        
    except frappe.DoesNotExistError:
        print("❌ Tuktuk Management workspace not found")
    except Exception as e:
        print(f"❌ Error updating workspace icon: {str(e)}")
        frappe.log_error(f"Workspace icon update error: {str(e)}")

if __name__ == "__main__":
    update_icon()
