// ~/frappe-bench/apps/tuktuk_management/tuktuk_management/public/js/tuktuk_driver.js

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
                            [tuktuk.tuktuk_id, tuktuk.battery_level]), 
                            tuktuk.battery_level > 50 ? 'green' : 'orange');
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
    }
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
                    const message = `
                        <h4>TukTuk Status: ${tuktuk.tuktuk_id}</h4>
                        <p><strong>Status:</strong> ${tuktuk.status}</p>
                        <p><strong>Battery Level:</strong> ${tuktuk.battery_level}%</p>
                        <p><strong>Mpesa Account:</strong> ${tuktuk.mpesa_account}</p>
                        ${tuktuk.last_reported ? `<p><strong>Last Updated:</strong> ${tuktuk.last_reported}</p>` : ''}
                    `;
                    
                    frappe.msgprint({
                        title: __('TukTuk Status'),
                        message: message,
                        indicator: tuktuk.battery_level > 50 ? 'green' : 'orange'
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
            reqd: 1
        },
        {
            label: 'Reason',
            fieldname: 'reason',
            fieldtype: 'Small Text',
            reqd: 1
        }
    ], function(values) {
        frm.set_value('current_balance', values.balance);
        frm.save();
        
        // Add comment for audit trail
        frappe.call({
            method: 'frappe.desk.form.utils.add_comment',
            args: {
                reference_doctype: frm.doctype,
                reference_name: frm.docname,
                content: `Target balance reset to ${values.balance} KSH. Reason: ${values.reason}`,
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
    // Only show for System Manager and Tuktuk Manager
    if (frappe.user.has_role(['System Manager', 'Tuktuk Manager'])) {
        
        if (!frm.doc.user_account) {
            // Driver doesn't have an account - show create button
            frm.add_custom_button(__('Create User Account'), function() {
                create_driver_account(frm);
            }, __('Account Management'));
        } else {
            // Driver has an account - show management options
            frm.add_custom_button(__('Reset Password'), function() {
                reset_driver_password(frm);
            }, __('Account Management'));
            
            frm.add_custom_button(__('Disable Account'), function() {
                disable_driver_account(frm);
            }, __('Account Management'));
            
            frm.add_custom_button(__('View Login Details'), function() {
                view_login_details(frm);
            }, __('Account Management'));
        }
    }
}

function create_driver_account(frm) {
    frappe.confirm(
        __('Create a user account for {0}? This will allow them to login and access the driver portal.', [frm.doc.driver_name]),
        function() {
            frappe.call({
                method: 'tuktuk_management.api.driver_auth.create_driver_user_account',
                args: {
                    driver_name: frm.doc.name,
                    email: frm.doc.driver_email,
                    phone: frm.doc.driver_primary_phone
                },
                callback: function(r) {
                    if (r.message) {
                        frm.reload_doc();
                        frappe.show_alert({
                            message: __('User account created successfully! Login credentials have been prepared for SMS.'),
                            indicator: 'green'
                        });
                    }
                }
            });
        }
    );
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
                <tr><td><strong>Portal URL:</strong></td><td><a href="https://sunnytuktuk.com/driver-dashboard" target="_blank">https://sunnytuktuk.com/driver-dashboard</a></td></tr>
                <tr><td><strong>Full System URL:</strong></td><td><a href="https://sunnytuktuk.com/app" target="_blank">https://sunnytuktuk.com/app</a></td></tr>
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