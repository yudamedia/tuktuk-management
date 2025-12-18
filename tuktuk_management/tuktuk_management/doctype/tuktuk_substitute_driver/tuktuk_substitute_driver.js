// ~/frappe-bench/apps/tuktuk_management/tuktuk_management/tuktuk_management/doctype/tuktuk_substitute_driver/tuktuk_substitute_driver.js
// Complete TukTuk Substitute Driver client script with payment management buttons

frappe.ui.form.on('TukTuk Substitute Driver', {
    refresh: function(frm) {
        // Add custom buttons
        if (!frm.is_new()) {
            // Button to show available vehicles (only if not assigned)
            if (frm.doc.status === 'Active' && !frm.doc.assigned_tuktuk) {
                frm.add_custom_button(__('Show Available Vehicles'), function() {
                    show_available_vehicles(frm);
                }, __('Actions'));
            }
            
            // Button to unassign from vehicle (only if assigned)
            if (frm.doc.assigned_tuktuk) {
                frm.add_custom_button(__('Unassign from Vehicle'), function() {
                    unassign_from_vehicle(frm);
                }, __('Actions'));
            }
            
            // Button to view transactions
            frm.add_custom_button(__('View Transactions'), function() {
                frappe.set_route('List', 'TukTuk Transaction', {
                    'substitute_driver': frm.doc.name
                });
            }, __('Reports'));
            
            // Button to view today's summary
            frm.add_custom_button(__("Today's Summary"), function() {
                show_daily_summary(frm);
            }, __('Reports'));
            
            // ADMIN BUTTONS - Only show for System Manager and Tuktuk Manager roles
            if (frappe.user.has_role(['System Manager', 'Tuktuk Manager'])) {
                // Uncaptured Payments button
                frm.add_custom_button(__('Uncaptured Payments'), function() {
                    process_uncaptured_payment_substitute(frm);
                }, __('Admin'));
                
                // Transaction Verification button
                frm.add_custom_button(__('Transaction Verification'), function() {
                    show_transaction_verification_substitute(frm);
                }, __('Admin'));
            }
        }
        
        // Set indicators
        set_status_indicator(frm);
        
        // Show target progress (uses individual daily_target when set, otherwise global_daily_target)
        if (get_effective_daily_target(frm)) {
            show_target_progress(frm);
        }
    },
    
    assigned_tuktuk: function(frm) {
        if (frm.doc.assigned_tuktuk) {
            // Validate vehicle is available for substitute assignment
            frappe.call({
                method: 'frappe.client.get',
                args: {
                    doctype: 'TukTuk Vehicle',
                    name: frm.doc.assigned_tuktuk
                },
                callback: function(r) {
                    if (r.message) {
                        const vehicle = r.message;
                        
                        // Check if vehicle has a regular driver (substitutes are for available vehicles only)
                        if (vehicle.assigned_driver) {
                            frappe.msgprint({
                                title: __('Invalid Assignment'),
                                message: __('This vehicle has a regular driver. Substitutes can only be assigned to available vehicles without regular drivers.'),
                                indicator: 'red'
                            });
                            frm.set_value('assigned_tuktuk', '');
                        }
                    }
                }
            });
        }
    }
});

// ===== ORIGINAL SUBSTITUTE DRIVER FUNCTIONS =====

function set_status_indicator(frm) {
    if (frm.doc.status === 'Active') {
        frm.dashboard.set_headline_alert('Active and Available', 'green');
    } else if (frm.doc.status === 'On Assignment') {
        frm.dashboard.set_headline_alert('Currently Assigned to Vehicle', 'blue');
    } else {
        frm.dashboard.set_headline_alert('Inactive', 'red');
    }
}

function get_effective_daily_target(frm) {
    // First priority: individual daily_target if set and > 0
    const individualTargetRaw = frm.doc.daily_target;
    if (individualTargetRaw !== undefined && individualTargetRaw !== null) {
        const individualTarget = typeof individualTargetRaw === 'number'
            ? individualTargetRaw
            : parseFloat(individualTargetRaw);

        if (!isNaN(individualTarget) && individualTarget > 0) {
            return individualTarget;
        }
    }

    // Second priority: global_daily_target from settings if > 0
    const globalTargetRaw = frappe.boot.tuktuk_settings?.global_daily_target;
    if (globalTargetRaw !== undefined && globalTargetRaw !== null) {
        const globalTarget = typeof globalTargetRaw === 'number'
            ? globalTargetRaw
            : parseFloat(globalTargetRaw);

        if (!isNaN(globalTarget) && globalTarget > 0) {
            return globalTarget;
        }
    }

    // Final fallback matches server-side default in get_daily_target()
    return 3000;
}

function show_target_progress(frm) {
    const target = get_effective_daily_target(frm);
    const contributionRaw = frm.doc.todays_target_contribution;
    const contribution = typeof contributionRaw === 'number'
        ? contributionRaw
        : parseFloat(contributionRaw) || 0;

    if (!target || isNaN(target) || target <= 0) {
        return;
    }

    const percentage = Math.min((contribution / target * 100), 100).toFixed(1);
    
    const progress_html = `
        <div class="progress" style="height: 25px; margin-top: 10px;">
            <div class="progress-bar progress-bar-success" role="progressbar" 
                 style="width: ${percentage}%" 
                 aria-valuenow="${percentage}" aria-valuemin="0" aria-valuemax="100">
                ${percentage}% (${contribution.toFixed(2)} / ${target.toFixed(2)} KSH)
            </div>
        </div>
        <small class="text-muted">Note: Target does not roll over for substitute drivers</small>
    `;
    
    frm.set_df_property('todays_target_contribution', 'description', progress_html);
}

function show_available_vehicles(frm) {
    frappe.call({
        method: 'tuktuk_management.tuktuk_management.doctype.tuktuk_substitute_driver.tuktuk_substitute_driver.get_available_vehicles_for_substitute',
        callback: function(r) {
            if (r.message && r.message.length > 0) {
                let vehicles_html = '<table class="table table-bordered"><thead><tr><th>Vehicle</th><th>Vehicle ID</th><th>Status</th><th>Battery</th><th>Action</th></tr></thead><tbody>';
                
                r.message.forEach(vehicle => {
                    vehicles_html += `
                    <tr>
                        <td>${vehicle.name}</td>
                        <td>${vehicle.tuktuk_id || 'N/A'}</td>
                        <td><span class="indicator blue">${vehicle.status}</span></td>
                        <td>${vehicle.battery_level || 'N/A'}%</td>
                        <td><button class="btn btn-xs btn-primary assign-vehicle" data-vehicle="${vehicle.name}">Assign</button></td>
                    </tr>`;
                });
                
                vehicles_html += '</tbody></table>';
                
                let d = new frappe.ui.Dialog({
                    title: 'Available Vehicles',
                    fields: [{
                        fieldtype: 'HTML',
                        fieldname: 'vehicles_list',
                        options: vehicles_html
                    }],
                    size: 'large'
                });
                
                d.show();
                
                // Add click handlers for assign buttons
                d.$wrapper.find('.assign-vehicle').on('click', function() {
                    const vehicle_name = $(this).data('vehicle');
                    assign_vehicle(frm, vehicle_name);
                    d.hide();
                });
            } else {
                frappe.msgprint(__('No vehicles available for assignment'));
            }
        }
    });
}

function assign_vehicle(frm, vehicle_name) {
    frappe.call({
        method: 'tuktuk_management.tuktuk_management.doctype.tuktuk_substitute_driver.tuktuk_substitute_driver.assign_substitute_to_vehicle',
        args: {
            substitute_driver: frm.doc.name,
            vehicle_name: vehicle_name
        },
        callback: function(r) {
            if (r.message && r.message.success) {
                frappe.msgprint({
                    title: __('Success'),
                    message: r.message.message,
                    indicator: 'green'
                });
                frm.reload_doc();
            } else {
                frappe.msgprint({
                    title: __('Error'),
                    message: r.message ? r.message.message : 'Unknown error',
                    indicator: 'red'
                });
            }
        }
    });
}

function unassign_from_vehicle(frm) {
    frappe.confirm(
        __('Are you sure you want to unassign this substitute driver from the vehicle?'),
        function() {
            frappe.call({
                method: 'tuktuk_management.tuktuk_management.doctype.tuktuk_substitute_driver.tuktuk_substitute_driver.unassign_substitute_from_vehicle',
                args: {
                    substitute_driver: frm.doc.name
                },
                callback: function(r) {
                    if (r.message && r.message.success) {
                        frappe.msgprint({
                            title: __('Success'),
                            message: r.message.message,
                            indicator: 'green'
                        });
                        frm.reload_doc();
                    } else {
                        frappe.msgprint({
                            title: __('Error'),
                            message: r.message ? r.message.message : 'Unknown error',
                            indicator: 'red'
                        });
                    }
                }
            });
        }
    );
}

function show_daily_summary(frm) {
    const target = get_effective_daily_target(frm);

    const earningsRaw = frm.doc.todays_earnings;
    const earnings = typeof earningsRaw === 'number'
        ? earningsRaw
        : parseFloat(earningsRaw) || 0;

    const contributionRaw = frm.doc.todays_target_contribution;
    const contribution = typeof contributionRaw === 'number'
        ? contributionRaw
        : parseFloat(contributionRaw) || 0;

    const balanceRaw = frm.doc.target_balance;
    const balance = typeof balanceRaw === 'number'
        ? balanceRaw
        : parseFloat(balanceRaw) || 0;

    const percentage = target > 0 ? Math.min((contribution / target * 100), 100).toFixed(1) : 0;

    const summary_html = `
        <div style="padding: 20px;">
            <h3>Today's Performance Summary</h3>
            <hr>
            <table class="table table-bordered">
                <tr>
                    <td><strong>Today's Earnings (Driver Share):</strong></td>
                    <td>KSH ${earnings.toFixed(2)}</td>
                </tr>
                <tr>
                    <td><strong>Today's Target Contribution:</strong></td>
                    <td>KSH ${contribution.toFixed(2)}</td>
                </tr>
                <tr>
                    <td><strong>Daily Target:</strong></td>
                    <td>KSH ${target.toFixed(2)}</td>
                </tr>
                <tr>
                    <td><strong>Target Progress:</strong></td>
                    <td>${percentage}%</td>
                </tr>
                <tr>
                    <td><strong>Current Target Balance:</strong></td>
                    <td>KSH ${balance.toFixed(2)}</td>
                </tr>
            </table>
            <div class="progress" style="height: 30px; margin-top: 20px;">
                <div class="progress-bar ${percentage >= 100 ? 'progress-bar-success' : 'progress-bar-info'}" 
                     role="progressbar" 
                     style="width: ${percentage}%" 
                     aria-valuenow="${percentage}" 
                     aria-valuemin="0" 
                     aria-valuemax="100">
                    ${percentage}%
                </div>
            </div>
            <p class="text-muted" style="margin-top: 10px;">
                <small>Note: Target balances do not roll over for substitute drivers</small>
            </p>
        </div>
    `;

    let d = new frappe.ui.Dialog({
        title: __("Today's Summary - {0}", [frm.doc.first_name + ' ' + frm.doc.last_name]),
        fields: [{
            fieldtype: 'HTML',
            fieldname: 'summary',
            options: summary_html
        }],
        size: 'large'
    });

    d.show();
}

// ===== NEW PAYMENT MANAGEMENT FUNCTIONS =====

/**
 * Process uncaptured payments for substitute drivers
 * Similar to regular drivers but ONLY allows "Send Driver Share" option
 */
function process_uncaptured_payment_substitute(frm) {
    // Check if substitute has assigned tuktuk
    if (!frm.doc.assigned_tuktuk) {
        frappe.msgprint({
            title: __('Cannot Process Payment'),
            message: __('Substitute driver must have an assigned TukTuk to record uncaptured payments.'),
            indicator: 'red'
        });
        return;
    }
    
    // Create dialog to collect payment details
    let d = new frappe.ui.Dialog({
        title: __('Record Uncaptured Payment'),
        fields: [
            {
                fieldname: 'transaction_id',
                fieldtype: 'Data',
                label: __('M-Pesa Transaction Number'),
                reqd: 1,
                description: __('The M-Pesa transaction code from the customer SMS')
            },
            {
                fieldname: 'customer_phone',
                fieldtype: 'Data',
                label: __('Customer Phone Number'),
                reqd: 1,
                description: __('Customer who made the payment (format: 254XXXXXXXXX)')
            },
            {
                fieldname: 'amount',
                fieldtype: 'Currency',
                label: __('Amount Paid (KSH)'),
                reqd: 1,
                description: __('Total amount paid by customer')
            }
        ],
        primary_action_label: __('Review Payment'),
        primary_action: function(values) {
            // Validate inputs
            if (!values.transaction_id || !values.customer_phone || !values.amount) {
                frappe.msgprint(__('All fields are required'));
                return;
            }
            
            if (values.amount <= 0) {
                frappe.msgprint(__('Amount must be greater than zero'));
                return;
            }
            
            d.hide();
            
            // Show confirmation dialog with payment details
            show_payment_confirmation_substitute(frm, values);
        }
    });
    
    d.show();
}

/**
 * Show payment confirmation dialog for substitute
 * Only shows "Send Driver Share" option (no deposit option for substitutes)
 */
function show_payment_confirmation_substitute(frm, payment_data) {
    let d = new frappe.ui.Dialog({
        title: __('Confirm Uncaptured Payment'),
        fields: [
            {
                fieldtype: 'HTML',
                fieldname: 'payment_summary',
                options: `
                    <div style="padding: 10px; background-color: #f0f4f7; border-radius: 5px; margin-bottom: 15px;">
                        <h4 style="margin-top: 0;">Payment Details</h4>
                        <table style="width: 100%;">
                            <tr>
                                <td style="padding: 5px;"><strong>Transaction ID:</strong></td>
                                <td style="padding: 5px;">${payment_data.transaction_id}</td>
                            </tr>
                            <tr>
                                <td style="padding: 5px;"><strong>Customer Phone:</strong></td>
                                <td style="padding: 5px;">${payment_data.customer_phone}</td>
                            </tr>
                            <tr>
                                <td style="padding: 5px;"><strong>Amount:</strong></td>
                                <td style="padding: 5px;">KSH ${parseFloat(payment_data.amount).toFixed(2)}</td>
                            </tr>
                            <tr>
                                <td style="padding: 5px;"><strong>Substitute Driver:</strong></td>
                                <td style="padding: 5px;">${frm.doc.first_name} ${frm.doc.last_name}</td>
                            </tr>
                            <tr>
                                <td style="padding: 5px;"><strong>TukTuk:</strong></td>
                                <td style="padding: 5px;">${frm.doc.assigned_tuktuk}</td>
                            </tr>
                        </table>
                    </div>
                    <div style="padding: 10px; background-color: #fff3cd; border-radius: 5px; margin-bottom: 15px;">
                        <strong>Action:</strong>
                        <ul style="margin: 10px 0;">
                            <li><strong>Send Driver Share:</strong> Calculate driver share based on fare percentage and send via M-Pesa B2C to the substitute driver</li>
                        </ul>
                        <p style="margin: 10px 0; color: #856404;">
                            <strong>Note:</strong> For substitute drivers, only "Send Driver Share" is available. 
                            The deposit option is not available for substitutes.
                        </p>
                    </div>
                `
            }
        ],
        primary_action_label: __('Send Driver Share'),
        primary_action: function() {
            d.hide();
            process_uncaptured_payment_action_substitute(frm, payment_data);
        }
    });
    
    d.show();
}

/**
 * Process the uncaptured payment action for substitute (send driver share only)
 */
function process_uncaptured_payment_action_substitute(frm, payment_data) {
    frappe.confirm(
        __('This will calculate the driver share and send payment via M-Pesa B2C to the substitute driver. Continue?'),
        function() {
            frappe.call({
                method: 'tuktuk_management.api.tuktuk.process_uncaptured_payment_substitute',
                args: {
                    substitute_driver: frm.doc.name,
                    tuktuk: frm.doc.assigned_tuktuk,
                    transaction_id: payment_data.transaction_id,
                    customer_phone: payment_data.customer_phone,
                    amount: payment_data.amount
                },
                callback: function(r) {
                    if (r.message && r.message.success) {
                        frappe.msgprint({
                            title: __('Uncaptured Payment Processed'),
                            message: r.message.message,
                            indicator: 'green'
                        });
                        
                        // Refresh the form to show updated data
                        frm.reload_doc();
                    } else {
                        frappe.msgprint({
                            title: __('Processing Failed'),
                            message: r.message ? r.message.message : __('An error occurred while processing the payment'),
                            indicator: 'red'
                        });
                    }
                }
            });
        }
    );
}

/**
 * Show transaction verification dialog for substitute driver
 */
function show_transaction_verification_substitute(frm) {
    // Call API to get balance reconciliation data
    frappe.call({
        method: 'tuktuk_management.api.tuktuk.reconcile_substitute_balance',
        args: {
            substitute_driver: frm.doc.name
        },
        callback: function(r) {
            if (r.message) {
                display_verification_dialog_substitute(frm, r.message);
            }
        }
    });
}

/**
 * Display verification dialog with balance details for substitute
 */
function display_verification_dialog_substitute(frm, verification_data) {
    let has_discrepancy = verification_data.discrepancy_amount !== 0;
    let discrepancy_type = verification_data.discrepancy_amount > 0 ? 'extra' : 'missing';
    let discrepancy_color = discrepancy_type === 'extra' ? '#d4edda' : '#f8d7da';
    
    // Build transactions table HTML
    let transactions_html = '';
    if (verification_data.transactions && verification_data.transactions.length > 0) {
        transactions_html = `
            <h4>Today's Transactions (${verification_data.transaction_count})</h4>
            <table class="table table-bordered" style="font-size: 12px;">
                <thead>
                    <tr>
                        <th>Time</th>
                        <th>Transaction ID</th>
                        <th>Amount</th>
                        <th>Target Contribution</th>
                    </tr>
                </thead>
                <tbody>
        `;
        
        verification_data.transactions.forEach(function(txn) {
            transactions_html += `
                <tr>
                    <td>${txn.timestamp}</td>
                    <td>${txn.transaction_id}</td>
                    <td>KSH ${txn.amount.toFixed(2)}</td>
                    <td>KSH ${txn.target_contribution.toFixed(2)}</td>
                </tr>
            `;
        });
        
        transactions_html += `
                </tbody>
            </table>
        `;
    } else {
        transactions_html = '<p><em>No transactions recorded today.</em></p>';
    }
    
    let dialog_fields = [
        {
            fieldtype: 'HTML',
            fieldname: 'verification_summary',
            options: `
                <div style="padding: 15px; background-color: #f8f9fa; border-radius: 5px; margin-bottom: 15px;">
                    <h4 style="margin-top: 0;">Balance Verification</h4>
                    <table style="width: 100%; margin-bottom: 10px;">
                        <tr>
                            <td style="padding: 5px;"><strong>Current Balance:</strong></td>
                            <td style="padding: 5px;">KSH ${verification_data.current_balance.toFixed(2)}</td>
                        </tr>
                        <tr>
                            <td style="padding: 5px;"><strong>Calculated Balance:</strong></td>
                            <td style="padding: 5px;">KSH ${verification_data.calculated_balance.toFixed(2)}</td>
                        </tr>
                        <tr style="background-color: ${discrepancy_color};">
                            <td style="padding: 5px;"><strong>Discrepancy:</strong></td>
                            <td style="padding: 5px;">
                                ${has_discrepancy 
                                    ? `KSH ${Math.abs(verification_data.discrepancy_amount).toFixed(2)} (${discrepancy_type})`
                                    : 'None - Balance is correct ✓'
                                }
                            </td>
                        </tr>
                    </table>
                    ${has_discrepancy 
                        ? `<p style="color: #721c24; margin: 0;"><strong>⚠ Balance mismatch detected</strong></p>`
                        : `<p style="color: #155724; margin: 0;"><strong>✓ Balance is accurate</strong></p>`
                    }
                </div>
                <div style="padding: 15px; background-color: #fff; border: 1px solid #dee2e6; border-radius: 5px;">
                    ${transactions_html}
                </div>
            `
        }
    ];
    
    let d = new frappe.ui.Dialog({
        title: __('Transaction Verification - Substitute Driver'),
        fields: dialog_fields,
        size: 'large'
    });
    
    // Add "Fix Balance" button if there's a discrepancy
    if (has_discrepancy) {
        d.set_primary_action(__('Fix Balance'), function() {
            frappe.confirm(
                __('This will update the balance from KSH {0} to KSH {1}. Continue?', 
                    [verification_data.current_balance.toFixed(2), verification_data.calculated_balance.toFixed(2)]
                ),
                function() {
                    frappe.call({
                        method: 'tuktuk_management.api.tuktuk.fix_substitute_balance',
                        args: {
                            substitute_driver: frm.doc.name,
                            correct_balance: verification_data.calculated_balance
                        },
                        callback: function(r) {
                            if (r.message && r.message.success) {
                                frappe.msgprint({
                                    title: __('Balance Fixed'),
                                    message: __('Balance has been corrected to KSH {0}', 
                                        [verification_data.calculated_balance.toFixed(2)]),
                                    indicator: 'green'
                                });
                                d.hide();
                                frm.reload_doc();
                            }
                        }
                    });
                }
            );
        });
    }
    
    d.show();
}