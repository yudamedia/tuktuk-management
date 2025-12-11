// ~/frappe-bench/apps/tuktuk_management/tuktuk_management/tuktuk_management/doctype/tuktuk_petty_cash/tuktuk_petty_cash.js

frappe.ui.form.on('TukTuk Petty Cash', {
    refresh: function(frm) {
        // Add custom buttons based on payment status
        if (frm.doc.payment_status === "Pending" && !frm.is_new()) {
            frm.add_custom_button(__('Approve'), function() {
                approve_payment(frm);
            }, __('Actions')).addClass('btn-primary');
            
            frm.add_custom_button(__('Reject'), function() {
                reject_payment(frm);
            }, __('Actions')).addClass('btn-danger');
        }
        
        if (frm.doc.payment_status === "Approved" && !frm.is_new()) {
            frm.add_custom_button(__('Process Payment'), function() {
                process_payment(frm);
            }).addClass('btn-success');
        }
        
        // Add button to view MPesa details
        if (frm.doc.mpesa_transaction_id) {
            frm.add_custom_button(__('View MPesa Details'), function() {
                show_mpesa_details(frm);
            });
        }
        
        // Color code status
        color_code_status(frm);
        
        // Add dashboard
        if (!frm.is_new()) {
            add_payment_dashboard(frm);
        }
    },
    
    recipient_type: function(frm) {
        // Clear driver field if not Driver type
        if (frm.doc.recipient_type !== "Driver") {
            frm.set_value('driver', '');
        }
    },
    
    driver: function(frm) {
        // Auto-fill driver details when driver is selected
        if (frm.doc.driver) {
            frappe.call({
                method: 'frappe.client.get',
                args: {
                    doctype: 'TukTuk Driver',
                    name: frm.doc.driver
                },
                callback: function(r) {
                    if (r.message) {
                        frm.set_value('recipient_name', r.message.driver_name);
                        frm.set_value('recipient_phone', r.message.mpesa_number);
                    }
                }
            });
        }
    },
    
    amount: function(frm) {
        // Validate amount is positive
        if (frm.doc.amount && frm.doc.amount <= 0) {
            frappe.msgprint(__('Amount must be greater than zero'));
            frm.set_value('amount', 0);
        }
    }
});

function approve_payment(frm) {
    frappe.confirm(
        `Approve payment of KSH ${frm.doc.amount} to ${frm.doc.recipient_name}?`,
        function() {
            frappe.call({
                method: 'tuktuk_management.tuktuk_management.doctype.tuktuk_petty_cash.tuktuk_petty_cash.approve_payment',
                args: {
                    docname: frm.doc.name
                },
                callback: function(r) {
                    if (r.message) {
                        frm.reload_doc();
                        frappe.show_alert({
                            message: __('Payment Approved'),
                            indicator: 'green'
                        });
                    }
                }
            });
        }
    );
}

function reject_payment(frm) {
    frappe.prompt([
        {
            fieldname: 'reason',
            fieldtype: 'Small Text',
            label: 'Rejection Reason',
            reqd: 1
        }
    ], function(values) {
        frappe.call({
            method: 'tuktuk_management.tuktuk_management.doctype.tuktuk_petty_cash.tuktuk_petty_cash.reject_payment',
            args: {
                docname: frm.doc.name,
                reason: values.reason
            },
            callback: function(r) {
                if (r.message) {
                    frm.reload_doc();
                    frappe.show_alert({
                        message: __('Payment Rejected'),
                        indicator: 'red'
                    });
                }
            }
        });
    }, __('Reject Payment'));
}

function process_payment(frm) {
    frappe.confirm(
        `Process B2C payment of KSH ${frm.doc.amount} to ${frm.doc.recipient_name} (${frm.doc.recipient_phone})?<br><br>
        <strong>This will send real money via MPesa.</strong>`,
        function() {
            frappe.show_alert({
                message: __('Processing payment...'),
                indicator: 'blue'
            });
            
            frappe.call({
                method: 'tuktuk_management.tuktuk_management.doctype.tuktuk_petty_cash.tuktuk_petty_cash.process_payment',
                args: {
                    docname: frm.doc.name
                },
                callback: function(r) {
                    frm.reload_doc();
                    if (r.message && r.message.success) {
                        frappe.show_alert({
                            message: __('Payment initiated successfully'),
                            indicator: 'green'
                        });
                    }
                }
            });
        }
    );
}

function show_mpesa_details(frm) {
    let html = `
        <div class="mpesa-details">
            <h4>MPesa Transaction Details</h4>
            <table class="table table-bordered">
                <tr>
                    <th>Transaction ID</th>
                    <td>${frm.doc.mpesa_transaction_id || 'N/A'}</td>
                </tr>
                <tr>
                    <th>Conversation ID</th>
                    <td>${frm.doc.mpesa_conversation_id || 'N/A'}</td>
                </tr>
                <tr>
                    <th>Response Code</th>
                    <td>${frm.doc.mpesa_response_code || 'N/A'}</td>
                </tr>
                <tr>
                    <th>Response Description</th>
                    <td>${frm.doc.mpesa_response_description || 'N/A'}</td>
                </tr>
                <tr>
                    <th>Result Code</th>
                    <td>${frm.doc.mpesa_result_code || 'N/A'}</td>
                </tr>
            </table>
        </div>
    `;
    
    frappe.msgprint({
        title: __('MPesa Transaction Details'),
        message: html,
        indicator: 'blue'
    });
}

function color_code_status(frm) {
    if (!frm.doc.payment_status) return;
    
    const status_colors = {
        'Pending': 'orange',
        'Approved': 'blue',
        'Processing': 'purple',
        'Completed': 'green',
        'Failed': 'red',
        'Rejected': 'darkgrey'
    };
    
    const color = status_colors[frm.doc.payment_status] || 'grey';
    frm.set_df_property('payment_status', 'color', color);
}

function add_payment_dashboard(frm) {
    // Create a dashboard showing payment info
    let dashboard_html = `
        <div class="row">
            <div class="col-sm-6">
                <div class="form-dashboard-section">
                    <h5>Payment Information</h5>
                    <p><strong>Recipient:</strong> ${frm.doc.recipient_name}</p>
                    <p><strong>Phone:</strong> ${frm.doc.recipient_phone}</p>
                    <p><strong>Amount:</strong> KSH ${frm.doc.amount}</p>
                    <p><strong>Category:</strong> ${frm.doc.category || 'N/A'}</p>
                </div>
            </div>
            <div class="col-sm-6">
                <div class="form-dashboard-section">
                    <h5>Status</h5>
                    <p><strong>Current Status:</strong> <span class="indicator ${get_indicator_class(frm.doc.payment_status)}">${frm.doc.payment_status}</span></p>
                    ${frm.doc.approved_by ? `<p><strong>Approved By:</strong> ${frm.doc.approved_by}</p>` : ''}
                    ${frm.doc.rejected_by ? `<p><strong>Rejected By:</strong> ${frm.doc.rejected_by}</p>` : ''}
                </div>
            </div>
        </div>
    `;
    
    frm.dashboard.add_section(dashboard_html);
}

function get_indicator_class(status) {
    const indicator_map = {
        'Pending': 'orange',
        'Approved': 'blue',
        'Processing': 'purple',
        'Completed': 'green',
        'Failed': 'red',
        'Rejected': 'grey'
    };
    return indicator_map[status] || 'grey';
}
