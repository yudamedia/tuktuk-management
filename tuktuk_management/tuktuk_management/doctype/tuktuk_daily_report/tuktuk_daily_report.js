// Client script for TukTuk Daily Report
frappe.ui.form.on('TukTuk Daily Report', {
    refresh: function(frm) {
        // Add "Email Report" button
        if (frm.doc.report_text) {
            frm.add_custom_button(__('Email Report'), function() {
                email_report_dialog(frm);
            }, __('Actions'));
        }
    }
});

function email_report_dialog(frm) {
    let d = new frappe.ui.Dialog({
        title: __('Email Daily Report'),
        fields: [
            {
                label: __('Recipients'),
                fieldname: 'recipients',
                fieldtype: 'Small Text',
                reqd: 1,
                description: __('Enter email addresses separated by commas (e.g., email1@example.com, email2@example.com)')
            },
            {
                label: __('Subject'),
                fieldname: 'subject',
                fieldtype: 'Data',
                default: `Daily Operations Report - ${frm.doc.report_date || frappe.datetime.get_today()}`,
                reqd: 1
            }
        ],
        primary_action_label: __('Send Email'),
        primary_action(values) {
            send_report_email(frm, values, d);
        }
    });
    
    d.show();
}

function send_report_email(frm, values, dialog) {
    // Parse email addresses (split by comma and trim whitespace)
    let recipients = values.recipients
        .split(',')
        .map(email => email.trim())
        .filter(email => email.length > 0);
    
    // Validate email addresses
    let emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    let invalidEmails = recipients.filter(email => !emailRegex.test(email));
    
    if (invalidEmails.length > 0) {
        frappe.msgprint({
            title: __('Invalid Email Addresses'),
            message: __('The following email addresses are invalid:<br>' + invalidEmails.join('<br>')),
            indicator: 'red'
        });
        return;
    }
    
    frappe.call({
        method: 'tuktuk_management.api.tuktuk.send_daily_report_to_recipients',
        args: {
            report_name: frm.doc.name,
            recipients: recipients,
            subject: values.subject
        },
        freeze: true,
        freeze_message: __('Sending email...'),
        callback: function(r) {
            if (r.message && r.message.success) {
                frappe.show_alert({
                    message: __('Report emailed successfully to ') + recipients.length + __(' recipient(s)'),
                    indicator: 'green'
                }, 5);
                dialog.hide();
            } else {
                frappe.show_alert({
                    message: __('Failed to send email. Please check error logs.'),
                    indicator: 'red'
                }, 5);
            }
        },
        error: function(r) {
            frappe.show_alert({
                message: __('Error sending email: ') + (r.message || 'Unknown error'),
                indicator: 'red'
            }, 5);
        }
    });
}

