import frappe

def convert_workspace_to_custom():
    """Convert Tuktuk Management workspace from Standard to Custom"""
    try:
        workspace = frappe.get_doc("Workspace", "Tuktuk Management")

        # Change from Standard to Custom
        workspace.is_standard = 0
        workspace.module = None  # Custom workspaces don't have a module

        workspace.save(ignore_permissions=True)
        frappe.db.commit()

        print("✓ Workspace converted to Custom")
        print("  UI changes will now be preserved automatically")
        print("  NOTE: You should also remove it from fixtures in hooks.py")

    except Exception as e:
        print(f"✗ Error: {str(e)}")
        frappe.db.rollback()
