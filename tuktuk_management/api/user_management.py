import frappe
from frappe import _
from frappe.utils import now_datetime, get_url, cstr
import json

def check_and_send_tuktuk_manager_welcome(doc, method=None):
    """
    Hook function called after User creation
    Automatically sends welcome email if user has Tuktuk Manager role
    """
    try:
        # Check if user has Tuktuk Manager role
        if has_tuktuk_manager_role(doc):
            # Get the password from the session if it's a new user creation
            password = frappe.local.response.get('temp_password') or get_temp_password_from_session()
            
            if not password:
                # If no password available, generate a new one and update user
                password = generate_secure_password()
                doc.new_password = password
                doc.save(ignore_permissions=True)
                frappe.db.commit()
            
            # Send custom welcome email
            send_tuktuk_manager_welcome_email(doc.email, doc.full_name, password)
            
            # Log the action
            frappe.log_error(
                "Tuktuk Manager Welcome Email Triggered",
                f"Auto-sent welcome email to {doc.email} with Tuktuk Manager role"
            )
            
    except Exception as e:
        frappe.log_error(f"Failed to auto-send welcome email: {str(e)}")
        # Don't throw error - just log it so user creation doesn't fail

def check_role_change_and_send_welcome(doc, method=None):
    """
    Hook function called when User is updated
    Sends welcome email if Tuktuk Manager role is newly added
    """
    try:
        # Only check if this is not a new document
        if not doc.is_new():
            # Get old document to compare roles
            old_doc = doc.get_doc_before_save()
            
            if old_doc:
                old_roles = set([role.role for role in old_doc.roles])
                new_roles = set([role.role for role in doc.roles])
                
                # Check if Tuktuk Manager role was just added
                if "Tuktuk Manager" in new_roles and "Tuktuk Manager" not in old_roles:
                    # Generate new password for security
                    password = generate_secure_password()
                    doc.new_password = password
                    
                    # Send welcome email
                    send_tuktuk_manager_welcome_email(doc.email, doc.full_name, password)
                    
                    frappe.msgprint(
                        f"✅ Tuktuk Manager welcome email sent to {doc.email}",
                        title="Welcome Email Sent",
                        indicator="green"
                    )
                    
    except Exception as e:
        frappe.log_error(f"Failed to send welcome email on role change: {str(e)}")

def has_tuktuk_manager_role(user_doc):
    """Check if user has Tuktuk Manager role"""
    for role in user_doc.roles:
        if role.role == "Tuktuk Manager":
            return True
    return False

def get_temp_password_from_session():
    """Try to get temporary password from various sources"""
    # Check if password was set in the current form/session
    if hasattr(frappe.local, 'form_dict') and frappe.local.form_dict.get('new_password'):
        return frappe.local.form_dict.get('new_password')
    
    # Check session
    if frappe.session.get('temp_password'):
        return frappe.session.get('temp_password')
    
    return None

def generate_secure_password():
    """Generate a secure 12-character password"""
    import secrets
    import string
    
    # Create password with mix of letters, numbers, and special chars
    chars = string.ascii_letters + string.digits + "!@#$%^&*"
    password = ''.join(secrets.choice(chars) for _ in range(12))
    return password

@frappe.whitelist()
def create_tuktuk_manager_user(email, first_name, last_name, mobile_no=None):
    """
    Create a new Tuktuk Manager user manually
    This will trigger the automatic welcome email via hooks
    """
    try:
        # Check if user already exists
        if frappe.db.exists("User", email):
            frappe.throw(f"User {email} already exists")
        
        # Generate password
        password = generate_secure_password()
        
        # Store password in session for the hook to access
        frappe.session['temp_password'] = password
        
        # Create user account - this will trigger the after_insert hook
        user = frappe.get_doc({
            "doctype": "User",
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
            "full_name": f"{first_name} {last_name}",
            "mobile_no": mobile_no,
            "user_type": "System User",
            "send_welcome_email": 0,  # Disable default welcome email
            "new_password": password,
            "roles": [
                {"role": "Tuktuk Manager"}
            ]
        })
        
        user.insert(ignore_permissions=True)
        
        # Clear temp password from session
        if 'temp_password' in frappe.session:
            del frappe.session['temp_password']
        
        frappe.msgprint(f"✅ Tuktuk Manager account created successfully for {email}")
        return {
            "success": True,
            "email": user.email,
            "message": "User created and welcome email sent automatically"
        }
        
    except Exception as e:
        # Clear temp password on error
        if 'temp_password' in frappe.session:
            del frappe.session['temp_password']
        frappe.log_error(f"Failed to create Tuktuk Manager user: {str(e)}")
        frappe.throw(f"Failed to create user: {str(e)}")

@frappe.whitelist()
def resend_welcome_email(user_email):
    """Manually resend welcome email to a Tuktuk Manager"""
    try:
        user = frappe.get_doc("User", user_email)
        
        if not has_tuktuk_manager_role(user):
            frappe.throw("User does not have Tuktuk Manager role")
        
        # Generate new password
        password = generate_secure_password()
        user.new_password = password
        user.save(ignore_permissions=True)
        
        # Send welcome email
        send_tuktuk_manager_welcome_email(user.email, user.full_name, password)
        
        frappe.msgprint(f"✅ Welcome email resent to {user_email}")
        return {"success": True, "message": "Welcome email resent successfully"}
        
    except Exception as e:
        frappe.log_error(f"Failed to resend welcome email: {str(e)}")
        frappe.throw(f"Failed to resend welcome email: {str(e)}")

def send_tuktuk_manager_welcome_email(email, full_name, password):
    """Send custom welcome email to Tuktuk Manager"""
    try:
        # Get site URL
        site_url = "https://console.sunnytuktuk.com"
        manual_url = "https://console.sunnytuktuk.com/files/manual.pdf"
        
        # Prepare email context
        context = {
            "full_name": full_name,
            "email": email,
            "password": password,
            "site_url": site_url,
            "manual_url": manual_url,
            "company_name": "Sunny Tuktuk"
        }
        
        # Send email using custom template
        frappe.sendmail(
            recipients=[email],
            subject="Welcome to Sunny Tuktuk Management System",
            template="tuktuk_manager_welcome",
            args=context,
            header=["Welcome to Sunny Tuktuk", "green"]
        )
        
        frappe.log_error("Tuktuk Manager Welcome Email Sent", f"Welcome email sent to {email}")
        
    except Exception as e:
        frappe.log_error(f"Failed to send welcome email to {email}: {str(e)}")
        # Don't throw error - user is created, just email failed
        frappe.msgprint(f"⚠️ User created but welcome email failed. Please send login details manually to {email}")
