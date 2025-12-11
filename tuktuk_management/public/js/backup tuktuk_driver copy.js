// ~/frappe-bench/apps/tuktuk_management/tuktuk_management/public/js/tuktuk_driver.js
// Enhanced TukTuk Driver client script with type safety

// Ensure Frappe utility functions are available for type safety
if (typeof flt === 'undefined') {
    window.flt = function(value, precision = 2) {
        if (value === null || value === undefined || value === '') return 0;
        const num = parseFloat(value);
        return isNaN(num) ? 0 : parseFloat(num.toFixed(precision));
    };
}

if (typeof cint === 'undefined') {
    window.cint = function(value) {
        if (value === null || value === undefined || value === '') return 0;
        const num = parseInt(value);
        return isNaN(num) ? 0 : num;
    };
}

frappe.ui.form.on('TukTuk Driver', {
    refresh: function(frm) {
        // Set driver name if not set
        if (!frm.doc.driver_name) {
            set_driver_name(frm);
        }
        
        // Add custom buttons and indicators for existing records
        if (!frm.doc.__islocal) {
            setup_custom_buttons(frm);
            setup_indicators(frm);
            setup_deposit_indicators(frm);
            setup_account_management_buttons(frm);
        }
        
        // Handle deposit field dependencies
        handle_deposit_dependencies(frm);
    },
    
    driver_first_name: function(frm) {
        set_driver_name(frm);
    },
    
    driver_middle_name: function(frm) {
        set_driver_name(frm);
    },
    
    driver_last_name: function(frm) {
        set_driver_name(frm);
    },
    
    before_save: function(frm) {
        // Ensure driver name is set before saving
        set_driver_name(frm);
    },
    
    assigned_tuktuk: function(frm) {
        // When tuktuk assignment changes, show tuktuk details
        if (frm.doc.assigned_tuktuk) {
            frappe.call({
                method: 'frappe.client.get',
                args: {
                    doctype: 'TukTuk Vehicle',
                    name: frm.doc.assigned_tuktuk
                },
                callback: function(r) {
                    if (r.message) {
                        const tuktuk = r.message;
                        frm.dashboard.add_indicator(__('TukTuk: {0} (Battery: {1}%)', 
                            [tuktuk.tuktuk_id, flt(tuktuk.battery_level)]), 
                            flt(tuktuk.battery_level) > 50 ? 'green' : 'orange');
                    }
                }
            });
        }
    },
    
    daily_target: function(frm) {
        // Refresh indicators when target changes
        if (!frm.doc.__islocal) {
            setup_indicators(frm);
        }
    },
    
    current_balance: function(frm) {
        // Refresh indicators when balance changes
        if (!frm.doc.__islocal) {
            setup_indicators(frm);
        }
    },
    
    deposit_required: function(frm) {
        handle_deposit_dependencies(frm);
    },
    
    initial_deposit_amount: function(frm) {
        if (!frm.doc.__islocal) {
            setup_deposit_indicators(frm);
        }
    },
    
    current_deposit_balance: function(frm) {
        if (!frm.doc.__islocal) {
            setup_deposit_indicators(frm);
        }
    }
});

function set_driver_name(frm) {
    const firstName = frm.doc.driver_first_name || '';
    const middleName = frm.doc.driver_middle_name || '';
    const lastName = frm.doc.driver_last_name || '';
    
    const fullName = [firstName, middleName, lastName].filter(Boolean).join(' ');
    
    // Set the name if it's different and form is either new or saved
    if (fullName && fullName !== frm.doc.driver_name) {
        frm.set_value('driver_name', fullName);
    }
}

function handle_deposit_dependencies(frm) {
    // Show/hide deposit fields based on deposit_required
    frm.toggle_display(['initial_deposit_amount', 'allow_target_deduction_from_deposit'], 
                      frm.doc.deposit_required);
}

function setup_custom_buttons(frm) {
    // Clear existing custom buttons
    frm.clear_custom_buttons();
    
    // Add button to view driver transactions
    frm.add_custom_button(__('View Transactions'), function() {
        frappe.route_options = {
            'driver': frm.doc.name
        };
        frappe.set_route('List', 'TukTuk Transaction');
    }, __('Reports'));
    
    // Add button to view performance report
    frm.add_custom_button(__('Performance Report'), function() {
        frappe.route_options = {
            'driver': frm.doc.name,
            'from_date': frappe.datetime.add_days(frappe.datetime.get_today(), -30),
            'to_date': frappe.datetime.get_today()
        };
        frappe.set_route('query-report', 'Driver Performance Report');
    }, __('Reports'));
    
    // Add button to view rentals
    frm.add_custom_button(__('View Rentals'), function() {
        frappe.route_options = {
            'driver': frm.doc.name
        };
        frappe.set_route('List', 'TukTuk Rental');
    }, __('Reports'));
    
    // Add action buttons based on driver status
    if (!frm.doc.assigned_tuktuk) {
        frm.add_custom_button(__('Assign TukTuk'), function() {
            assign_tuktuk(frm);
        }, __('Actions'));
    } else {
        frm.add_custom_button(__('Reassign TukTuk'), function() {
            reassign_tuktuk(frm);
        }, __('Actions'));
        
        frm.add_custom_button(__('Unassign TukTuk'), function() {
            unassign_tuktuk(frm);
        }, __('Actions'));
        
        frm.add_custom_button(__('Check TukTuk Status'), function() {
            check_tuktuk_status(frm);
        }, __('Actions'));
    }
    
    // Deposit management buttons
    if (frm.doc.deposit_required && !frm.doc.exit_date) {
        frm.add_custom_button(__('Top Up Deposit'), function() {
            process_deposit_top_up(frm);
        }, __('Deposit'));
        
        frm.add_custom_button(__('View Deposit Summary'), function() {
            show_deposit_summary(frm);
        }, __('Deposit'));
        
        // Admin buttons
        if (frappe.user.has_role(['System Manager', 'Tuktuk Manager'])) {
            frm.add_custom_button(__('Damage Deduction'), function() {
                process_damage_deduction(frm);
            }, __('Deposit'));
            
            frm.add_custom_button(__('Target Miss Deduction'), function() {
                process_target_miss_deduction(frm);
            }, __('Deposit'));
        }
    }
    
    // Exit processing button (Admin only)
    if (frappe.user.has_role(['System Manager', 'Tuktuk Manager']) && !frm.doc.exit_date) {
        frm.add_custom_button(__('Process Driver Exit'), function() {
            process_driver_exit(frm);
        }, __('Admin'));
    }
    
    // Reset target balance button (for managers)
    if (frappe.user.has_role(['System Manager', 'Tuktuk Manager'])) {
        frm.add_custom_button(__('Reset Target Balance'), function() {
            reset_target_balance(frm);
        }, __('Admin'));
        
        frm.add_custom_button(__('Reset Consecutive Misses'), function() {
            reset_consecutive_misses(frm);
        }, __('Admin'));
        
        frm.add_custom_button(__('Record Overpayment Adjustment'), function() {
            record_overpayment_adjustment(frm);
        }, __('Admin'));
        
        frm.add_custom_button(__('Uncaptured Payments'), function() {
            process_uncaptured_payment(frm);
        }, __('Admin'));
        
        frm.add_custom_button(__('Transaction Verification'), function() {
            show_transaction_verification(frm);
        }, __('Admin'));
    }
    
    // SMS Driver button (visible to managers)
    if (frappe.user.has_role(['System Manager', 'Tuktuk Manager'])) {
        frm.add_custom_button(__('SMS Driver'), function() {
            send_sms_to_driver(frm);
        }, __('Communications'));
    }

    // Manual withdrawal button (visible when instant payouts are effectively disabled)
    const driverPref = frm.doc.instant_payout_override || 'Follow Global';
    frappe.call({
        method: 'frappe.client.get_value',
        args: { doctype: 'TukTuk Settings', fieldname: 'instant_payouts_enabled' },
        callback: function(r) {
            const globalInstant = (r && r.message && r.message.instant_payouts_enabled) ? 1 : 0;
            let instantEnabled = false;
            if (driverPref === 'Enable') instantEnabled = true;
            else if (driverPref === 'Disable') instantEnabled = false;
            else instantEnabled = !!globalInstant;

            if (!instantEnabled && frappe.user.has_role(['System Manager', 'Tuktuk Manager'])) {
                frm.add_custom_button(__('Withdraw Balance'), function() {
                    withdraw_balance(frm);
                }, __('Payments'));
            }
        }
    });
}

function setup_indicators(frm) {
    // Clear existing indicators
    frm.dashboard.clear_indicators();
    
    // Add target status indicator
    const target = frm.doc.daily_target || 3000; // Default target
    const balance = frm.doc.current_balance || 0;
    const progress = Math.min((balance / target) * 100, 100);
    
    let color = 'red';
    let status = 'Behind Target';
    
    if (progress >= 100) {
        color = 'green';
        status = 'Target Met';
    } else if (progress >= 80) {
        color = 'orange';
        status = 'Near Target';
    }
    
    frm.dashboard.add_indicator(__('Target Progress: {0}% - {1}', [Math.round(progress), status]), color);
    
    // Add balance indicator
    const balanceColor = balance >= 0 ? 'green' : 'red';
    const balanceLabel = balance >= 0 ? 'Credit' : 'Debt';
    frm.dashboard.add_indicator(__('Balance: {0} KSH ({1})', [Math.abs(balance), balanceLabel]), balanceColor);
    
    // Add consecutive misses warning
    if (frm.doc.consecutive_misses > 0) {
        const missColor = frm.doc.consecutive_misses >= 2 ? 'red' : 'orange';
        const warningText = frm.doc.consecutive_misses >= 2 ? 'CRITICAL' : 'WARNING';
        frm.dashboard.add_indicator(__('Consecutive Misses: {0}/3 - {1}', [frm.doc.consecutive_misses, warningText]), missColor);
    }
    
    // Add assignment status
    if (frm.doc.assigned_tuktuk) {
        frm.dashboard.add_indicator(__('Assigned to TukTuk'), 'blue');
    } else {
        frm.dashboard.add_indicator(__('No TukTuk Assigned'), 'grey');
    }
}

function setup_deposit_indicators(frm) {
    if (!frm.doc.deposit_required) return;
    
    // Add deposit balance indicator
    const deposit_balance = frm.doc.current_deposit_balance || 0;
    let deposit_color = 'green';
    
    if (deposit_balance <= 0) {
        deposit_color = 'red';
    } else if (deposit_balance < (frm.doc.initial_deposit_amount * 0.5)) {
        deposit_color = 'orange';
    }
    
    frm.dashboard.add_indicator(__('Deposit Balance: {0} KSH', [deposit_balance]), deposit_color);
    
    // Add exit status if applicable
    if (frm.doc.exit_date) {
        const refund_color = frm.doc.refund_status === 'Completed' ? 'green' : 'orange';
        frm.dashboard.add_indicator(__('Exit Status: {0}', [frm.doc.refund_status]), refund_color);
    }
}

function assign_tuktuk(frm) {
    frappe.prompt([
        {
            label: 'Available TukTuk',
            fieldname: 'tuktuk',
            fieldtype: 'Link',
            options: 'TukTuk Vehicle',
            reqd: 1,
            get_query: function() {
                return {
                    filters: {
                        'status': 'Available'
                    }
                };
            }
        }
    ], function(values) {
        frappe.call({
            method: 'frappe.client.set_value',
            args: {
                doctype: 'TukTuk Vehicle',
                name: values.tuktuk,
                fieldname: 'status',
                value: 'Assigned'
            },
            callback: function(r) {
                if (!r.exc) {
                    frm.set_value('assigned_tuktuk', values.tuktuk);
                    frm.save();
                    frappe.msgprint(__('TukTuk assigned successfully'));
                }
            }
        });
    }, __('Assign TukTuk'), __('Assign'));
}

function unassign_tuktuk(frm) {
    frappe.confirm(
        __('Are you sure you want to unassign this driver from their TukTuk?'),
        function() {
            const current_tuktuk = frm.doc.assigned_tuktuk;
            
            // Set tuktuk status back to available
            frappe.call({
                method: 'frappe.client.set_value',
                args: {
                    doctype: 'TukTuk Vehicle',
                    name: current_tuktuk,
                    fieldname: 'status',
                    value: 'Available'
                },
                callback: function(r) {
                    if (!r.exc) {
                        frm.set_value('assigned_tuktuk', '');
                        frm.save();
                        frappe.msgprint(__('TukTuk unassigned successfully'));
                    }
                }
            });
        }
    );
}

function reassign_tuktuk(frm) {
    const current_tuktuk = frm.doc.assigned_tuktuk;
    
    frappe.prompt([
        {
            label: 'New TukTuk',
            fieldname: 'tuktuk',
            fieldtype: 'Link',
            options: 'TukTuk Vehicle',
            reqd: 1,
            get_query: function() {
                return {
                    filters: {
                        'status': 'Available',
                        'name': ['!=', current_tuktuk]  // Exclude current tuktuk
                    }
                };
            }
        }
    ], function(values) {
        if (!values.tuktuk) {
            frappe.msgprint(__('Please select a TukTuk'));
            return;
        }
        
        if (values.tuktuk === current_tuktuk) {
            frappe.msgprint(__('Please select a different TukTuk'));
            return;
        }
        
        frappe.confirm(
            __('Reassign driver to new TukTuk? Balance and target tracking will be preserved during operating hours.'),
            function() {
                // Directly update the assigned_tuktuk field
                // The backend handle_tuktuk_assignment will detect this is a reassignment
                // (old_value exists AND new_value exists) and preserve balance during operating hours
                frm.set_value('assigned_tuktuk', values.tuktuk);
                frm.save().then(function() {
                    frappe.msgprint(__('TukTuk reassigned successfully. Balance and target tracking preserved.'));
                });
            }
        );
    }, __('Reassign TukTuk'), __('Reassign'));
}

function check_tuktuk_status(frm) {
    if (frm.doc.assigned_tuktuk) {
        frappe.call({
            method: 'frappe.client.get',
            args: {
                doctype: 'TukTuk Vehicle',
                name: frm.doc.assigned_tuktuk
            },
            callback: function(r) {
                if (r.message) {
                    const tuktuk = r.message;
                    const battery_level = flt(tuktuk.battery_level);
                    const message = `
                        <h4>TukTuk Status: ${tuktuk.tuktuk_id}</h4>
                        <p><strong>Status:</strong> ${tuktuk.status}</p>
                        <p><strong>Battery Level:</strong> ${battery_level}%</p>
                        <p><strong>Mpesa Account:</strong> ${tuktuk.mpesa_account}</p>
                        ${tuktuk.last_reported ? `<p><strong>Last Updated:</strong> ${tuktuk.last_reported}</p>` : ''}
                    `;
                    
                    frappe.msgprint({
                        title: __('TukTuk Status'),
                        message: message,
                        indicator: battery_level > 50 ? 'green' : 'orange'
                    });
                }
            }
        });
    }
}

// Deposit Management Functions

function process_deposit_top_up(frm) {
    frappe.prompt([
        {
            label: 'Top Up Amount (KSH)',
            fieldname: 'amount',
            fieldtype: 'Currency',
            reqd: 1
        },
        {
            label: 'Payment Reference (Mpesa Code)',
            fieldname: 'reference',
            fieldtype: 'Data'
        },
        {
            label: 'Notes',
            fieldname: 'description',
            fieldtype: 'Small Text'
        }
    ], function(values) {
        frappe.call({
            method: 'tuktuk_management.tuktuk_management.doctype.tuktuk_driver.tuktuk_driver.process_deposit_top_up',
            args: {
                driver_name: frm.doc.name,
                amount: values.amount,
                reference: values.reference || '',
                description: values.description || ''
            },
            callback: function(r) {
                if (r.message && r.message.success) {
                    frm.reload_doc();
                    frappe.msgprint(__('Deposit top-up processed successfully. New balance: {0} KSH', [r.message.new_balance]));
                }
            }
        });
    }, __('Process Deposit Top-Up'), __('Process'));
}

function process_damage_deduction(frm) {
    frappe.prompt([
        {
            label: 'Damage Amount (KSH)',
            fieldname: 'amount',
            fieldtype: 'Currency',
            reqd: 1
        },
        {
            label: 'Damage Description',
            fieldname: 'description',
            fieldtype: 'Small Text',
            reqd: 1
        },
        {
            label: 'Reference (Report #, Photos, etc.)',
            fieldname: 'reference',
            fieldtype: 'Data'
        }
    ], function(values) {
        frappe.call({
            method: 'tuktuk_management.tuktuk_management.doctype.tuktuk_driver.tuktuk_driver.process_damage_deduction',
            args: {
                driver_name: frm.doc.name,
                amount: values.amount,
                description: values.description,
                reference: values.reference || ''
            },
            callback: function(r) {
                if (r.message && r.message.success) {
                    frm.reload_doc();
                    frappe.msgprint(__('Damage deduction processed. New balance: {0} KSH', [r.message.new_balance]));
                }
            }
        });
    }, __('Process Damage Deduction'), __('Process'));
}

function process_target_miss_deduction(frm) {
    if (!frm.doc.allow_target_deduction_from_deposit) {
        frappe.msgprint(__('Driver has not allowed target deductions from deposit'));
        return;
    }
    
    frappe.prompt([
        {
            label: 'Missed Target Amount (KSH)',
            fieldname: 'missed_amount',
            fieldtype: 'Currency',
            reqd: 1
        }
    ], function(values) {
        frappe.call({
            method: 'tuktuk_management.tuktuk_management.doctype.tuktuk_driver.tuktuk_driver.process_target_miss_deduction',
            args: {
                driver_name: frm.doc.name,
                missed_amount: values.missed_amount
            },
            callback: function(r) {
                if (r.message && r.message.success) {
                    frm.reload_doc();
                    frappe.msgprint(__('Target miss deduction processed. New balance: {0} KSH', [r.message.new_balance]));
                } else {
                    frappe.msgprint(__('Target miss deduction could not be processed'));
                }
            }
        });
    }, __('Process Target Miss Deduction'), __('Process'));
}

function process_driver_exit(frm) {
    frappe.prompt([
        {
            label: 'Exit Date',
            fieldname: 'exit_date',
            fieldtype: 'Date',
            default: frappe.datetime.get_today(),
            reqd: 1
        }
    ], function(values) {
        frappe.confirm(
            __('Are you sure you want to process driver exit? This will calculate refund and unassign the TukTuk.'),
            function() {
                frappe.call({
                    method: 'tuktuk_management.tuktuk_management.doctype.tuktuk_driver.tuktuk_driver.process_driver_exit',
                    args: {
                        driver_name: frm.doc.name,
                        exit_date: values.exit_date
                    },
                    callback: function(r) {
                        if (r.message && r.message.success) {
                            frm.reload_doc();
                            frappe.msgprint(__('Driver exit processed. Refund amount: {0} KSH', [r.message.refund_amount]));
                        }
                    }
                });
            }
        );
    }, __('Process Driver Exit'), __('Process'));
}

function show_deposit_summary(frm) {
    frappe.call({
        method: 'tuktuk_management.tuktuk_management.doctype.tuktuk_driver.tuktuk_driver.get_deposit_summary',
        args: {
            driver_name: frm.doc.name
        },
        callback: function(r) {
            if (r.message) {
                const summary = r.message;
                const message = `
                    <h4>Deposit Summary for ${summary.driver_name}</h4>
                    <table class="table table-bordered">
                        <tr><td><strong>Initial Deposit:</strong></td><td>${summary.initial_deposit} KSH</td></tr>
                        <tr><td><strong>Current Balance:</strong></td><td>${summary.current_balance} KSH</td></tr>
                        <tr><td><strong>Total Deposits:</strong></td><td>${summary.total_deposits} KSH</td></tr>
                        <tr><td><strong>Total Deductions:</strong></td><td>${summary.total_deductions} KSH</td></tr>
                        <tr><td><strong>Target Deduction Allowed:</strong></td><td>${summary.allows_target_deduction ? 'Yes' : 'No'}</td></tr>
                        <tr><td><strong>Total Transactions:</strong></td><td>${summary.transaction_count}</td></tr>
                        ${summary.exit_date ? `<tr><td><strong>Exit Date:</strong></td><td>${summary.exit_date}</td></tr>` : ''}
                        ${summary.refund_amount ? `<tr><td><strong>Refund Amount:</strong></td><td>${summary.refund_amount} KSH</td></tr>` : ''}
                        ${summary.refund_status ? `<tr><td><strong>Refund Status:</strong></td><td>${summary.refund_status}</td></tr>` : ''}
                    </table>
                `;
                
                frappe.msgprint({
                    title: __('Deposit Summary'),
                    message: message,
                    indicator: 'blue'
                });
            }
        }
    });
}

function reset_target_balance(frm) {
    frappe.prompt([
        {
            label: 'New Balance',
            fieldname: 'balance',
            fieldtype: 'Currency',
            default: 0,
            description: 'Enter 0 to reset to zero, or any other amount'
        },
        {
            label: 'Reason',
            fieldname: 'reason',
            fieldtype: 'Small Text',
            reqd: 1
        }
    ], function(values) {
        // Validate that balance field is provided (including 0)
        if (values.balance === null || values.balance === undefined || values.balance === '') {
            frappe.throw(__('Please enter a balance value'));
            return;
        }
        
        // Explicitly handle 0 values to ensure they're properly saved
        const balance = parseFloat(values.balance);
        
        // Additional validation: ensure it's a valid number
        if (isNaN(balance)) {
            frappe.throw(__('Please enter a valid number'));
            return;
        }
        
        frm.set_value('current_balance', balance);
        frm.save();

        // Add comment for audit trail
        frappe.call({
            method: 'frappe.desk.form.utils.add_comment',
            args: {
                reference_doctype: frm.doctype,
                reference_name: frm.docname,
                content: `Target balance reset to ${balance} KSH. Reason: ${values.reason}`,
                comment_email: frappe.session.user,
                comment_by: frappe.session.user_fullname
            }
        });

        frappe.msgprint(__('Target balance reset successfully'));
    }, __('Reset Target Balance'), __('Reset'));
}

function reset_consecutive_misses(frm) {
    frappe.confirm(
        __('Are you sure you want to reset consecutive misses to 0?'),
        function() {
            frm.set_value('consecutive_misses', 0);
            frm.save();
            
            // Add comment for audit trail
            frappe.call({
                method: 'frappe.desk.form.utils.add_comment',
                args: {
                    reference_doctype: frm.doctype,
                    reference_name: frm.docname,
                    content: `Consecutive misses reset by ${frappe.session.user_fullname}`,
                    comment_email: frappe.session.user,
                    comment_by: frappe.session.user_fullname
                }
            });
            
            frappe.msgprint(__('Consecutive misses reset successfully'));
        }
    );
}

// Add to: tuktuk_management/public/js/tuktuk_driver.js
// This enhances the existing file with account management features

// Add these functions to the existing tuktuk_driver.js file

function setup_account_management_buttons(frm) {
    // Add User Account button for all users (not just managers)
    if (!frm.doc.user_account) {
        // Driver doesn't have an account - show create button
        frm.add_custom_button(__('User Account'), function() {
            create_driver_account(frm);
        }, __('Actions'));
    } else {
        // Driver has an account - show button to open user document
        frm.add_custom_button(__('User Account'), function() {
            open_user_document(frm);
        }, __('Actions'));
    }
}

function create_driver_account(frm) {
    frappe.confirm(
        __('Create a user account for {0}? This will allow them to login and access the driver portal.', [frm.doc.driver_name]),
        function() {
            // Yes - create account
            frappe.call({
                method: 'tuktuk_management.api.driver_auth.create_tuktuk_driver_user_account',
                args: {
                    tuktuk_driver_name: frm.doc.name
                },
                callback: function(r) {
                    if (r.message) {
                        frm.reload_doc();
                        frappe.show_alert({
                            message: __('User account created successfully! Login credentials have been prepared for SMS.'),
                            indicator: 'green'
                        });
                        // After reload, the button will change to open user document
                    }
                },
                error: function(r) {
                    frappe.show_alert({
                        message: __('Failed to create user account: {0}', [r.message || 'Unknown error']),
                        indicator: 'red'
                    });
                }
            });
        }
    );
}

function open_user_document(frm) {
    if (frm.doc.user_account) {
        // Open the linked user document
        frappe.set_route('Form', 'User', frm.doc.user_account);
    } else {
        frappe.msgprint(__('No user account linked to this driver.'));
    }
}

function reset_driver_password(frm) {
    frappe.confirm(
        __('Reset password for {0}? A new password will be generated and prepared for SMS delivery.', [frm.doc.driver_name]),
        function() {
            frappe.call({
                method: 'tuktuk_management.api.driver_auth.reset_driver_password',
                args: {
                    driver_name: frm.doc.name
                },
                callback: function(r) {
                    if (r.message) {
                        frappe.show_alert({
                            message: __('Password reset successfully! New credentials prepared for SMS.'),
                            indicator: 'green'
                        });
                    }
                }
            });
        }
    );
}

function disable_driver_account(frm) {
    frappe.confirm(
        __('Disable user account for {0}? They will not be able to login until re-enabled.', [frm.doc.driver_name]),
        function() {
            frappe.call({
                method: 'tuktuk_management.api.driver_auth.disable_driver_account',
                args: {
                    driver_name: frm.doc.name
                },
                callback: function(r) {
                    if (r.message) {
                        frappe.show_alert({
                            message: __('Account disabled successfully'),
                            indicator: 'orange'
                        });
                    }
                }
            });
        }
    );
}

function view_login_details(frm) {
    if (frm.doc.user_account) {
        const message = `
            <h4>Driver Login Information</h4>
            <table class="table table-bordered">
                <tr><td><strong>Driver Name:</strong></td><td>${frm.doc.driver_name}</td></tr>
                <tr><td><strong>Login Email:</strong></td><td>${frm.doc.user_account}</td></tr>
                <tr><td><strong>Phone Number:</strong></td><td>${frm.doc.driver_primary_phone}</td></tr>
                <tr><td><strong>Portal URL:</strong></td><td><a href="https://console.sunnytuktuk.com/driver-dashboard" target="_blank">https://console.sunnytuktuk.com/driver-dashboard</a></td></tr>
                <tr><td><strong>Full System URL:</strong></td><td><a href="https://console.sunnytuktuk.com/app" target="_blank">https://console.sunnytuktuk.com/app</a></td></tr>
            </table>
            <div class="alert alert-info">
                <strong>Note:</strong> Password information is available in the Notification Log after account creation or reset.
            </div>
        `;
        
        frappe.msgprint({
            title: __('Login Details'),
            message: message,
            indicator: 'blue'
        });
    }
}

// Update the main refresh function to include account management
frappe.ui.form.on('TukTuk Driver', {
    refresh: function(frm) {
        // Set driver name if not set
        if (!frm.doc.driver_name) {
            set_driver_name(frm);
        }
        
        // Add custom buttons and indicators for existing records
        if (!frm.doc.__islocal) {
            setup_custom_buttons(frm);
            setup_indicators(frm);
            setup_deposit_indicators(frm);
            setup_account_management_buttons(frm); // Add this line
        }
        
        // Handle deposit field dependencies
        handle_deposit_dependencies(frm);
        
        // Show account status indicator
        if (frm.doc.user_account) {
            frm.dashboard.add_indicator(__('Has User Account'), 'green');
        } else {
            frm.dashboard.add_indicator(__('No User Account'), 'orange');
        }
    }
});

// Add this to tuktuk_management/public/js/tuktuk_driver_list.js
// Enhanced list view for driver account management

frappe.listview_settings['TukTuk Driver'] = {
    onload: function(listview) {
        // Add breadcrumb
        frappe.breadcrumbs.add({
            type: 'Custom',
            label: 'Tuktuk Management',
            route: '/app/tuktuk-management'
        });
        
        // Add SMS Drivers button (prominently in action dropdown)
        if (frappe.user.has_role(['System Manager', 'Tuktuk Manager'])) {
            listview.page.add_action_item(__('SMS Drivers'), function() {
                show_bulk_sms_dialog(listview);
            });
        }
        
        // Add bulk account creation button
        if (frappe.user.has_role(['System Manager', 'Tuktuk Manager'])) {
            listview.page.add_menu_item(__('Create All Driver Accounts'), function() {
                frappe.confirm(
                    __('Create user accounts for all drivers who don\'t have one? This will generate login credentials for each driver.'),
                    function() {
                        frappe.call({
                            method: 'tuktuk_management.api.driver_auth.create_all_driver_accounts',
                            callback: function(r) {
                                if (r.message) {
                                    const result = r.message;
                                    let message = `✅ Created ${result.created.length} accounts`;
                                    if (result.failed.length > 0) {
                                        message += `\n❌ ${result.failed.length} failed`;
                                    }
                                    
                                    frappe.msgprint({
                                        title: __('Bulk Account Creation Complete'),
                                        message: message,
                                        indicator: result.failed.length > 0 ? 'orange' : 'green'
                                    });
                                    
                                    listview.refresh();
                                }
                            }
                        });
                    }
                );
            });
            
            listview.page.add_menu_item(__('View All Driver Accounts'), function() {
                frappe.call({
                    method: 'tuktuk_management.api.driver_auth.get_all_driver_accounts',
                    callback: function(r) {
                        if (r.message) {
                            show_driver_accounts_dialog(r.message);
                        }
                    }
                });
            });
        }
        
        // Existing menu items...
        listview.page.add_menu_item(__('Deposit Management Report'), function() {
            frappe.set_route('query-report', 'Deposit Management Report');
        });
        
        listview.page.add_menu_item(__('Driver Performance Report'), function() {
            frappe.set_route('query-report', 'Driver Performance Report');
        });
    },
    
    // Enhanced list view settings
    add_fields: ["assigned_tuktuk", "current_balance", "consecutive_misses", "deposit_required", "current_deposit_balance", "user_account"],
    
    get_indicator: function(doc) {
        // Priority indicators based on account status and performance
        if (!doc.user_account) {
            return [__("No Account"), "red", "user_account,=,"];
        } else if (doc.consecutive_misses >= 2) {
            return [__("Critical"), "red", "consecutive_misses,>=,2"];
        } else if (doc.deposit_required && doc.current_deposit_balance <= 0) {
            return [__("No Deposit"), "orange", "current_deposit_balance,<=,0"];
        } else if (doc.assigned_tuktuk) {
            return [__("Assigned"), "green", "assigned_tuktuk,!=,"];
        } else {
            return [__("Unassigned"), "grey", "assigned_tuktuk,=,"];
        }
    },
    
    // Add custom columns
    formatters: {
        user_account: function(value, df, options, doc) {
            if (value) {
                return `<span class="text-success" title="Has user account">✓ ${value}</span>`;
            } else {
                return '<span class="text-muted" title="No user account">—</span>';
            }
        }
    }
};

function show_driver_accounts_dialog(accounts) {
    let html = `
        <div style="max-height: 400px; overflow-y: auto;">
            <table class="table table-bordered table-striped">
                <thead>
                    <tr>
                        <th>Driver Name</th>
                        <th>Email/Account</th>
                        <th>Phone</th>
                        <th>TukTuk</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
    `;
    
    accounts.forEach(driver => {
        const hasAccount = driver.user_account ? '✅' : '❌';
        const accountText = driver.user_account || 'No Account';
        const tuktukText = driver.assigned_tuktuk || 'Unassigned';
        
        html += `
            <tr>
                <td><a href="/app/tuktuk-driver/${driver.name}">${driver.driver_name}</a></td>
                <td>${accountText}</td>
                <td>${driver.driver_primary_phone || '—'}</td>
                <td>${tuktukText}</td>
                <td>${hasAccount}</td>
            </tr>
        `;
    });
    
    html += '</tbody></table></div>';
    
    frappe.msgprint({
        title: __('All Driver Accounts'),
        message: html,
        indicator: 'blue'
    });
}

function record_overpayment_adjustment(frm) {
    frappe.prompt([
        {
            label: 'Adjustment Amount (KSH)',
            fieldname: 'amount',
            fieldtype: 'Currency',
            reqd: 1,
            description: 'Enter negative amount for overpayment corrections (e.g., -1250)'
        },
        {
            label: 'Description/Reason',
            fieldname: 'description',
            fieldtype: 'Small Text',
            reqd: 1,
            description: 'Explain the reason for this adjustment'
        }
    ], function(values) {
        if (!values.amount || values.amount == 0) {
            frappe.msgprint(__('Please enter a valid adjustment amount'));
            return;
        }
        
        frappe.confirm(
            __('Create adjustment transaction for {0} KSH? This will not trigger any payment to the driver.', [values.amount]),
            function() {
                frappe.call({
                    method: 'tuktuk_management.api.tuktuk.create_adjustment_transaction',
                    args: {
                        driver: frm.doc.name,
                        tuktuk: frm.doc.assigned_tuktuk || '',
                        amount: values.amount,
                        description: values.description
                    },
                    callback: function(r) {
                        if (r.message && r.message.success) {
                            frappe.msgprint({
                                title: __('Adjustment Transaction Created'),
                                message: r.message.message,
                                indicator: 'green'
                            });
                            
                            // Refresh the form to show updated data
                            frm.reload_doc();
                        } else {
                            frappe.msgprint(__('Failed to create adjustment transaction'));
                        }
                    }
                });
            }
        );
    }, __('Record Overpayment Adjustment'), __('Create'));
}

function process_uncaptured_payment(frm) {
    // Check if driver has assigned TukTuk
    if (!frm.doc.assigned_tuktuk) {
        frappe.msgprint(__('Driver must have an assigned TukTuk to record uncaptured payments'));
        return;
    }
    
    frappe.prompt([
        {
            label: 'M-Pesa Transaction Number',
            fieldname: 'transaction_id',
            fieldtype: 'Data',
            reqd: 1,
            description: 'Enter the M-Pesa transaction code (e.g., SH12ABC3XY)'
        },
        {
            label: 'Customer Phone Number',
            fieldname: 'customer_phone',
            fieldtype: 'Data',
            reqd: 1,
            description: 'Enter customer phone number (e.g., 254712345678)'
        },
        {
            label: 'Amount Paid (KSH)',
            fieldname: 'amount',
            fieldtype: 'Currency',
            reqd: 1,
            description: 'Enter the amount paid by the customer'
        }
    ], function(values) {
        // Validate inputs
        if (!values.transaction_id || !values.customer_phone || !values.amount || values.amount <= 0) {
            frappe.msgprint(__('Please provide valid transaction details'));
            return;
        }
        
        // Show dialog with two action buttons
        let d = new frappe.ui.Dialog({
            title: __('Process Uncaptured Payment'),
            fields: [
                {
                    fieldtype: 'HTML',
                    fieldname: 'payment_details',
                    options: `
                        <div style="padding: 15px; background-color: #f8f9fa; border-radius: 5px; margin-bottom: 15px;">
                            <h4 style="margin-top: 0;">Payment Details</h4>
                            <table style="width: 100%;">
                                <tr>
                                    <td style="padding: 5px;"><strong>Transaction ID:</strong></td>
                                    <td style="padding: 5px;">${values.transaction_id}</td>
                                </tr>
                                <tr>
                                    <td style="padding: 5px;"><strong>Customer Phone:</strong></td>
                                    <td style="padding: 5px;">${values.customer_phone}</td>
                                </tr>
                                <tr>
                                    <td style="padding: 5px;"><strong>Amount:</strong></td>
                                    <td style="padding: 5px;">KSH ${values.amount}</td>
                                </tr>
                                <tr>
                                    <td style="padding: 5px;"><strong>Driver:</strong></td>
                                    <td style="padding: 5px;">${frm.doc.driver_name}</td>
                                </tr>
                                <tr>
                                    <td style="padding: 5px;"><strong>TukTuk:</strong></td>
                                    <td style="padding: 5px;">${frm.doc.assigned_tuktuk}</td>
                                </tr>
                            </table>
                        </div>
                        <div style="padding: 10px; background-color: #fff3cd; border-radius: 5px; margin-bottom: 15px;">
                            <strong>Choose Action:</strong>
                            <ul style="margin: 10px 0;">
                                <li><strong>Send Driver Share:</strong> Calculate driver share based on fare percentage and send via M-Pesa B2C</li>
                                <li><strong>Deposit Driver Share:</strong> Add full amount to driver's target balance (no M-Pesa payment)</li>
                            </ul>
                        </div>
                    `
                }
            ],
            primary_action_label: __('Send Driver Share'),
            primary_action: function() {
                d.hide();
                process_uncaptured_payment_action(frm, values, 'send_share');
            },
            secondary_action_label: __('Deposit Driver Share'),
            secondary_action: function() {
                d.hide();
                process_uncaptured_payment_action(frm, values, 'deposit_share');
            }
        });
        
        d.show();
    }, __('Uncaptured Payment'), __('Next'));
}

function process_uncaptured_payment_action(frm, payment_data, action_type) {
    let action_label = action_type === 'send_share' ? 'Send Driver Share' : 'Deposit Driver Share';
    let confirmation_msg = action_type === 'send_share' 
        ? __('This will calculate the driver share and send payment via M-Pesa B2C. Continue?')
        : __('This will add the full amount to the driver\'s target balance without sending M-Pesa payment. Continue?');
    
    frappe.confirm(
        confirmation_msg,
        function() {
            frappe.call({
                method: 'tuktuk_management.api.tuktuk.process_uncaptured_payment',
                args: {
                    driver: frm.doc.name,
                    tuktuk: frm.doc.assigned_tuktuk,
                    transaction_id: payment_data.transaction_id,
                    customer_phone: payment_data.customer_phone,
                    amount: payment_data.amount,
                    action_type: action_type
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
                            message: r.message ? r.message.error : __('Failed to process uncaptured payment'),
                            indicator: 'red'
                        });
                    }
                },
                error: function(r) {
                    frappe.msgprint({
                        title: __('Error'),
                        message: __('An error occurred while processing the payment'),
                        indicator: 'red'
                    });
                }
            });
        }
    );
}

function show_transaction_verification(frm) {
    frappe.call({
        method: 'tuktuk_management.api.tuktuk.reconcile_driver_balance',
        args: {
            driver_name: frm.doc.name
        },
        callback: function(r) {
            if (r.message) {
                const result = r.message;
                const has_discrepancy = result.discrepancy !== 0;
                
                // Fetch transactions
                frappe.call({
                    method: 'frappe.client.get_list',
                    args: {
                        doctype: 'TukTuk Transaction',
                        filters: {
                            driver: frm.doc.name,
                            timestamp: ['>=', frappe.datetime.get_today() + ' 06:00:00'],
                            payment_status: 'Completed',
                            transaction_type: ['not in', ['Adjustment', 'Driver Repayment']]
                        },
                        fields: ['transaction_id', 'amount', 'target_contribution', 'timestamp'],
                        order_by: 'timestamp asc',
                        limit_page_length: 500
                    },
                    callback: function(txn_r) {
                        let message = `
                            <div style="padding: 15px;">
                                <h4>Balance Verification</h4>
                                <table class="table table-bordered" style="margin-top: 10px;">
                                    <tr>
                                        <td><strong>Current Balance:</strong></td>
                                        <td>${result.old_balance} KSH</td>
                                    </tr>
                                    <tr>
                                        <td><strong>Calculated Balance:</strong></td>
                                        <td>${result.calculated_balance} KSH</td>
                                    </tr>
                                    <tr>
                                        <td><strong>Discrepancy:</strong></td>
                                        <td style="color: ${has_discrepancy ? 'red' : 'green'}; font-weight: bold;">
                                            ${Math.abs(result.discrepancy)} KSH ${result.discrepancy !== 0 ? (result.discrepancy > 0 ? 'extra' : 'missing') : ''}
                                        </td>
                                    </tr>
                                    <tr>
                                        <td><strong>Transactions Today:</strong></td>
                                        <td>${result.transactions_count}</td>
                                    </tr>
                                </table>
                        `;
                        
                        if (txn_r.message && txn_r.message.length > 0) {
                            message += `
                                <h5 style="margin-top: 20px;">Today's Transactions</h5>
                                <table class="table table-bordered table-sm" style="margin-top: 10px; font-size: 0.9em;">
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
                            
                            txn_r.message.forEach(txn => {
                                const time = frappe.datetime.str_to_user(txn.timestamp).split(' ')[1];
                                message += `
                                    <tr>
                                        <td>${time}</td>
                                        <td>${txn.transaction_id}</td>
                                        <td>${txn.amount} KSH</td>
                                        <td><strong>${txn.target_contribution} KSH</strong></td>
                                    </tr>
                                `;
                            });
                            
                            message += `
                                    </tbody>
                                </table>
                            `;
                        } else {
                            message += `
                                <div class="alert alert-info" style="margin-top: 15px;">
                                    No transactions found for today.
                                </div>
                            `;
                        }
                        
                        if (has_discrepancy) {
                            message += `
                                <div class="alert alert-warning" style="margin-top: 15px;">
                                    <strong>⚠️ Discrepancy Detected:</strong><br>
                                    ${result.message}
                                </div>
                            `;
                        }
                        
                        message += `</div>`;
                        
                        const d = new frappe.ui.Dialog({
                            title: __('Transaction Verification - {0}', [frm.doc.driver_name]),
                            size: 'large',
                            fields: [
                                {
                                    fieldtype: 'HTML',
                                    fieldname: 'verification_results',
                                    options: message
                                }
                            ],
                            primary_action_label: has_discrepancy ? __('Fix Balance') : __('Close'),
                            primary_action: function() {
                                if (has_discrepancy) {
                                    frappe.confirm(
                                        __('Fix this driver\'s balance? This will update from {0} KSH to {1} KSH',
                                           [result.old_balance, result.calculated_balance]),
                                        function() {
                                            frappe.call({
                                                method: 'tuktuk_management.api.tuktuk.fix_driver_balance',
                                                args: {
                                                    driver_name: frm.doc.name,
                                                    auto_fix: true
                                                },
                                                callback: function(fix_r) {
                                                    if (fix_r.message && fix_r.message.success) {
                                                        frappe.msgprint({
                                                            title: __('Balance Fixed'),
                                                            message: fix_r.message.message,
                                                            indicator: 'green'
                                                        });
                                                        frm.reload_doc();
                                                        d.hide();
                                                    }
                                                }
                                            });
                                        }
                                    );
                                } else {
                                    d.hide();
                                }
                            }
                        });
                        d.show();
                    }
                });
            }
        }
    });
}

// SMS Communication Functions

function send_sms_to_driver(frm) {
    // Check if driver has mpesa number
    if (!frm.doc.mpesa_number) {
        frappe.msgprint(__('Driver does not have an M-Pesa number configured'));
        return;
    }
    
    // Create dialog for SMS composition
    let d = new frappe.ui.Dialog({
        title: __('Send SMS to {0}', [frm.doc.driver_name]),
        fields: [
            {
                fieldtype: 'HTML',
                fieldname: 'available_fields',
                options: `
                    <div style="padding: 10px; background-color: #f8f9fa; border-radius: 5px; margin-bottom: 15px;">
                        <strong>Available Fields:</strong>
                        <p style="margin: 5px 0; font-size: 0.9em;">
                            <code>{driver_name}</code>, 
                            <code>{left_to_target}</code>, 
                            <code>{current_balance}</code>, 
                            <code>{daily_target}</code>, 
                            <code>{assigned_tuktuk}</code>, 
                            <code>{mpesa_number}</code>, 
                            <code>{mpesa_paybill}</code>, 
                            <code>{mpesa_account}</code>, 
                            <code>{current_deposit_balance}</code>
                        </p>
                        <p style="margin: 5px 0; font-size: 0.85em; color: #666;">
                            Use these placeholders in your message. They will be replaced with actual values.
                        </p>
                    </div>
                `
            },
            {
                label: 'Message',
                fieldname: 'message',
                fieldtype: 'Small Text',
                reqd: 1,
                description: 'Compose your SMS message. Use field placeholders like {driver_name} or {left_to_target}'
            },
            {
                fieldtype: 'HTML',
                fieldname: 'preview',
                options: '<div id="sms-preview" style="padding: 10px; background-color: #e9ecef; border-radius: 5px; margin-top: 10px;"></div>'
            }
        ],
        primary_action_label: __('Send SMS'),
        primary_action: function(values) {
            if (!values.message || !values.message.trim()) {
                frappe.msgprint(__('Please enter a message'));
                return;
            }
            
            frappe.call({
                method: 'tuktuk_management.api.sms_notifications.send_driver_sms_with_fields',
                args: {
                    driver_name: frm.doc.name,
                    message_template: values.message
                },
                callback: function(r) {
                    if (r.message && r.message.success) {
                        frappe.msgprint({
                            title: __('SMS Sent'),
                            message: __('SMS sent successfully to {0}', [frm.doc.driver_name]),
                            indicator: 'green'
                        });
                        d.hide();
                    } else {
                        frappe.msgprint({
                            title: __('SMS Failed'),
                            message: r.message ? r.message.message : __('Failed to send SMS'),
                            indicator: 'red'
                        });
                    }
                }
            });
        }
    });
    
    // Fetch additional data for preview
    frappe.call({
        method: 'frappe.client.get_value',
        args: {
            doctype: 'TukTuk Settings',
            fieldname: 'mpesa_paybill'
        },
        callback: function(r) {
            if (r.message && r.message.mpesa_paybill) {
                frm.doc.mpesa_paybill = r.message.mpesa_paybill;
            }
        }
    });
    
    if (frm.doc.assigned_tuktuk) {
        frappe.call({
            method: 'frappe.client.get_value',
            args: {
                doctype: 'TukTuk Vehicle',
                name: frm.doc.assigned_tuktuk,
                fieldname: 'mpesa_account'
            },
            callback: function(r) {
                if (r.message && r.message.mpesa_account) {
                    frm.doc.mpesa_account = r.message.mpesa_account;
                }
            }
        });
    }
    
    // Add message preview functionality
    d.fields_dict.message.$input.on('input', function() {
        const message = $(this).val();
        const preview = interpolate_fields(message, frm.doc);
        $('#sms-preview').html(`<strong>Preview:</strong><br>${preview}`);
    });
    
    d.show();
}

function interpolate_fields(message, doc) {
    // Replace field placeholders with actual values
    let result = message;
    result = result.replace(/\{driver_name\}/g, doc.driver_name || '');
    result = result.replace(/\{left_to_target\}/g, flt(doc.left_to_target, 0).toLocaleString());
    result = result.replace(/\{current_balance\}/g, flt(doc.current_balance, 0).toLocaleString());
    result = result.replace(/\{daily_target\}/g, flt(doc.daily_target || 3000, 0).toLocaleString());
    result = result.replace(/\{assigned_tuktuk\}/g, doc.assigned_tuktuk || 'None');
    result = result.replace(/\{mpesa_number\}/g, doc.mpesa_number || '');
    result = result.replace(/\{mpesa_paybill\}/g, doc.mpesa_paybill || '');
    result = result.replace(/\{mpesa_account\}/g, doc.mpesa_account || '');
    result = result.replace(/\{current_deposit_balance\}/g, flt(doc.current_deposit_balance, 0).toLocaleString());
    return result;
}

function show_bulk_sms_dialog(listview) {
    // Get selected drivers or show selector
    frappe.call({
        method: 'frappe.client.get_list',
        args: {
            doctype: 'TukTuk Driver',
            fields: ['name', 'driver_name', 'mpesa_number', 'assigned_tuktuk', 'left_to_target', 'current_balance', 'current_deposit_balance'],
            order_by: 'driver_name asc',
            limit_page_length: 500
        },
        callback: function(r) {
            if (r.message) {
                const drivers = r.message;
                
                // Create dialog
                let d = new frappe.ui.Dialog({
                    title: __('Send SMS to Drivers'),
                    size: 'large',
                    fields: [
                        {
                            label: 'Select Recipients',
                            fieldname: 'recipient_type',
                            fieldtype: 'Select',
                            options: 'All Drivers\nAll Assigned Drivers\nAll Unassigned Drivers\nDrivers with Remaining Target\nSelect Specific Drivers',
                            default: 'All Drivers',
                            reqd: 1,
                            onchange: function() {
                                const type = d.get_value('recipient_type');
                                d.get_field('selected_drivers').df.hidden = (type !== 'Select Specific Drivers');
                                d.get_field('selected_drivers').refresh();
                            }
                        },
                        {
                            label: 'Select Drivers',
                            fieldname: 'selected_drivers',
                            fieldtype: 'MultiSelectList',
                            hidden: 1,
                            options: drivers.map(d => ({
                                value: d.name,
                                label: `${d.driver_name} (${d.mpesa_number || 'No Phone'})`
                            })),
                            get_data: function() {
                                return drivers.map(d => ({
                                    value: d.name,
                                    label: `${d.driver_name} - ${d.assigned_tuktuk || 'Unassigned'} - Target Left: ${flt(d.left_to_target, 0)} KSH`,
                                    description: d.mpesa_number || 'No phone number'
                                }));
                            }
                        },
                        {
                            fieldtype: 'HTML',
                            fieldname: 'available_fields',
                            options: `
                                <div style="padding: 10px; background-color: #f8f9fa; border-radius: 5px; margin: 15px 0;">
                                    <strong>Available Fields:</strong>
                                    <p style="margin: 5px 0; font-size: 0.9em;">
                                        <code>{driver_name}</code>, 
                                        <code>{left_to_target}</code>, 
                                        <code>{current_balance}</code>, 
                                        <code>{daily_target}</code>, 
                                        <code>{assigned_tuktuk}</code>, 
                                        <code>{mpesa_number}</code>, 
                                        <code>{mpesa_paybill}</code>, 
                                        <code>{mpesa_account}</code>, 
                                        <code>{current_deposit_balance}</code>
                                    </p>
                                    <p style="margin: 5px 0; font-size: 0.85em; color: #666;">
                                        These placeholders will be replaced with each driver's actual values.
                                    </p>
                                </div>
                            `
                        },
                        {
                            label: 'Message',
                            fieldname: 'message',
                            fieldtype: 'Small Text',
                            reqd: 1,
                            description: 'Compose your SMS message. Use field placeholders like {driver_name} or {left_to_target}'
                        },
                        {
                            fieldtype: 'HTML',
                            fieldname: 'recipient_count',
                            options: '<div id="recipient-count" style="padding: 10px; background-color: #e9ecef; border-radius: 5px; margin-top: 10px;"></div>'
                        }
                    ],
                    primary_action_label: __('Send SMS'),
                    primary_action: function(values) {
                        if (!values.message || !values.message.trim()) {
                            frappe.msgprint(__('Please enter a message'));
                            return;
                        }
                        
                        // Determine driver IDs based on selection
                        let driver_ids = [];
                        const type = values.recipient_type;
                        
                        if (type === 'All Drivers') {
                            driver_ids = drivers.map(d => d.name);
                        } else if (type === 'All Assigned Drivers') {
                            driver_ids = drivers.filter(d => d.assigned_tuktuk).map(d => d.name);
                        } else if (type === 'All Unassigned Drivers') {
                            driver_ids = drivers.filter(d => !d.assigned_tuktuk).map(d => d.name);
                        } else if (type === 'Drivers with Remaining Target') {
                            driver_ids = drivers.filter(d => flt(d.left_to_target) > 0).map(d => d.name);
                        } else if (type === 'Select Specific Drivers') {
                            driver_ids = values.selected_drivers || [];
                        }
                        
                        if (driver_ids.length === 0) {
                            frappe.msgprint(__('No drivers selected'));
                            return;
                        }
                        
                        frappe.confirm(
                            __('Send SMS to {0} driver(s)?', [driver_ids.length]),
                            function() {
                                frappe.call({
                                    method: 'tuktuk_management.api.sms_notifications.send_bulk_sms_with_fields',
                                    args: {
                                        driver_ids: driver_ids,
                                        message_template: values.message
                                    },
                                    callback: function(r) {
                                        if (r.message && r.message.success) {
                                            frappe.msgprint({
                                                title: __('SMS Sent'),
                                                message: __('Successfully sent: {0}<br>Failed: {1}', 
                                                    [r.message.success_count, r.message.failure_count]),
                                                indicator: r.message.failure_count > 0 ? 'orange' : 'green'
                                            });
                                            d.hide();
                                        } else {
                                            frappe.msgprint({
                                                title: __('SMS Failed'),
                                                message: r.message ? r.message.message : __('Failed to send SMS'),
                                                indicator: 'red'
                                            });
                                        }
                                    }
                                });
                            }
                        );
                    }
                });
                
                // Update recipient count when selection changes
                d.fields_dict.recipient_type.$input.on('change', function() {
                    update_recipient_count(d, drivers);
                });
                
                d.show();
                update_recipient_count(d, drivers);
            }
        }
    });
}

function update_recipient_count(dialog, drivers) {
    const type = dialog.get_value('recipient_type');
    let count = 0;
    
    if (type === 'All Drivers') {
        count = drivers.length;
    } else if (type === 'All Assigned Drivers') {
        count = drivers.filter(d => d.assigned_tuktuk).length;
    } else if (type === 'All Unassigned Drivers') {
        count = drivers.filter(d => !d.assigned_tuktuk).length;
    } else if (type === 'Drivers with Remaining Target') {
        count = drivers.filter(d => flt(d.left_to_target) > 0).length;
    } else if (type === 'Select Specific Drivers') {
        const selected = dialog.get_value('selected_drivers') || [];
        count = selected.length;
    }
    
    $('#recipient-count').html(`<strong>Recipients:</strong> ${count} driver(s) will receive this SMS`);
}
