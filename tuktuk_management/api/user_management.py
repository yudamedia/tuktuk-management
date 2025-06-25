import frappe
from frappe import _
from frappe.utils import now_datetime, get_url, cstr
import json

# Override the default welcome email method
def override_send_welcome_mail_to_user(original_method):
    """
    Decorator to override ERPNext's default send_welcome_mail_to_user method
    to prevent default welcome emails for Tuktuk Managers
    """
    def wrapper(user, password, **kwargs):
        try:
            # Check if this user has Tuktuk Manager role
            user_doc = frappe.get_doc("User", user)
            if has_tuktuk_manager_role(user_doc):
                # Skip default welcome email for Tuktuk Managers
                frappe.log_error(
                    "Default Welcome Email Blocked", 
                    f"Blocked default welcome email for Tuktuk Manager: {user}"
                )
                return
        except Exception as e:
            frappe.log_error(f"Error in override_send_welcome_mail_to_user: {str(e)}")
        
        # Call original method for non-Tuktuk Manager users
        return original_method(user, password, **kwargs)
    
    return wrapper

def apply_welcome_email_override():
    """
    Apply the override to ERPNext's default welcome email method
    """
    try:
        import frappe.utils.user
        if hasattr(frappe.utils.user, 'send_welcome_mail_to_user'):
            original_method = frappe.utils.user.send_welcome_mail_to_user
            frappe.utils.user.send_welcome_mail_to_user = override_send_welcome_mail_to_user(original_method)
            frappe.log_error("Welcome Email Override Applied", "Successfully overrode send_welcome_mail_to_user for Tuktuk Managers")
    except Exception as e:
        frappe.log_error(f"Failed to apply welcome email override: {str(e)}")

def disable_default_welcome_for_tuktuk_managers(doc, method=None):
    """
    Hook function called BEFORE User creation
    Disables default welcome email for users with Tuktuk Manager role
    """
    try:
        if has_tuktuk_manager_role(doc):
            # Disable all default welcome email mechanisms
            doc.send_welcome_email = 0
            doc.flags.send_welcome_email = False
            doc.flags.ignore_welcome_email = True
            
            # Also disable password reset email
            doc.flags.ignore_password_policy = True
            
            frappe.log_error("Default Welcome Email Disabled", f"Disabled for Tuktuk Manager: {doc.email}")
    except Exception as e:
        frappe.log_error(f"Failed to disable default welcome email: {str(e)}")
        

def check_and_send_tuktuk_manager_welcome(doc, method=None):
    """
    Hook function called after User creation
    Automatically sends welcome email if user has Tuktuk Manager role
    """
    try:
        # Check if user has Tuktuk Manager role
        if has_tuktuk_manager_role(doc):
            # Ensure we don't trigger default welcome emails even after insertion
            doc.flags.ignore_welcome_email = True
            
            # Get the password from the session if it's a new user creation
            password = frappe.local.response.get('temp_password') or get_temp_password_from_session()
            
            if not password:
                # If no password available, generate a new one and update user
                password = generate_secure_password()
                doc.new_password = password
                doc.flags.ignore_welcome_email = True  # Ensure no default email on save
                doc.save(ignore_permissions=True)
                frappe.db.commit()
            
            # Send custom welcome email using commit after to ensure it's sent
            frappe.enqueue(
                'tuktuk_management.api.user_management.send_tuktuk_manager_welcome_email',
                email=doc.email,
                full_name=doc.full_name,
                password=password,
                queue='default',
                timeout=300,
                is_async=True
            )
            
            # Log the action
            frappe.log_error(
                "Tuktuk Manager Welcome Email Triggered",
                f"Queued welcome email to {doc.email} with Tuktuk Manager role"
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
            header=["Welcome to Sunny Tuktuk", "green"],
            reference_doctype="User",
            reference_name=email
        )
        
        # Also create a communication record for tracking
        communication = frappe.get_doc({
            "doctype": "Communication",
            "communication_type": "Communication",
            "communication_medium": "Email",
            "sent_or_received": "Sent",
            "email_status": "Sent",
            "subject": "Welcome to Sunny Tuktuk Management System",
            "sender": frappe.session.user,
            "recipients": email,
            "content": f"Welcome email sent to {full_name} ({email})",
            "reference_doctype": "User",
            "reference_name": email,
            "email_template": "tuktuk_manager_welcome"
        })
        communication.insert(ignore_permissions=True)
        
        frappe.log_error("Tuktuk Manager Welcome Email Sent", f"Welcome email sent to {email}")
        
    except Exception as e:
        frappe.log_error(f"Failed to send welcome email to {email}: {str(e)}")
        # Don't throw error - user is created, just email failed
        if frappe.flags.in_request:
            frappe.msgprint(f"⚠️ User created but welcome email failed. Please send login details manually to {email}")
