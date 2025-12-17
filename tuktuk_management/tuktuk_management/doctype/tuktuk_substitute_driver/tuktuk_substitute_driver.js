// ~/frappe-bench/apps/tuktuk_management/tuktuk_management/tuktuk_management/doctype/tuktuk_substitute_driver/tuktuk_substitute_driver.js
// Complete TukTuk Substitute Driver client script

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
        }
        
        // Set indicators
        set_status_indicator(frm);
        
        // Show target progress
        if (frm.doc.todays_target_contribution && frm.doc.daily_target) {
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
                        if (r.message.current_substitute_driver && 
                            r.message.current_substitute_driver !== frm.doc.name) {
                            frappe.msgprint(__('This vehicle already has a substitute driver assigned'));
                            frm.set_value('assigned_tuktuk', '');
                        }
                    }
                }
            });
        }
    }
});

function set_status_indicator(frm) {
    const status_colors = {
        'Active': 'green',
        'Inactive': 'red',
        'On Assignment': 'blue'
    };
    
    frm.set_df_property('status', 'options', 
        Object.keys(status_colors).map(status => 
            `<span class="indicator ${status_colors[status]}">${status}</span>`
        ).join('\n')
    );
}

function show_target_progress(frm) {
    const target = frm.doc.daily_target || 3000;
    const contribution = frm.doc.todays_target_contribution || 0;
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
                let vehicles_html = '<table class="table table-bordered"><thead><tr><th>Vehicle</th><th>Vehicle ID</th><th>Status</th><th>Regular Driver</th><th>Battery</th><th>Action</th></tr></thead><tbody>';
                
                r.message.forEach(vehicle => {
                    vehicles_html += `
                    <tr>
                        <td>${vehicle.name}</td>
                        <td>${vehicle.tuktuk_id || 'N/A'}</td>
                        <td><span class="indicator blue">${vehicle.status}</span></td>
                        <td>${vehicle.assigned_driver_name || 'N/A'}</td>
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
    const target = frm.doc.daily_target || 3000;
    const earnings = frm.doc.todays_earnings || 0;
    const contribution = frm.doc.todays_target_contribution || 0;
    const balance = frm.doc.target_balance || target;
    const rides = frm.doc.total_rides || 0;
    
    const summary_html = `
        <div class="row">
            <div class="col-sm-6">
                <h5>Today's Earnings</h5>
                <h3>${earnings.toFixed(2)} KSH</h3>
            </div>
            <div class="col-sm-6">
                <h5>Target Contribution</h5>
                <h3>${contribution.toFixed(2)} KSH</h3>
            </div>
        </div>
        <hr>
        <div class="row">
            <div class="col-sm-6">
                <h5>Daily Target</h5>
                <h3>${target.toFixed(2)} KSH</h3>
            </div>
            <div class="col-sm-6">
                <h5>Target Balance</h5>
                <h3>${balance.toFixed(2)} KSH</h3>
            </div>
        </div>
        <hr>
        <div class="row">
            <div class="col-sm-12">
                <h5>Total Rides (All Time)</h5>
                <h3>${rides}</h3>
            </div>
        </div>
        <hr>
        <div class="alert alert-info">
            <strong>Note:</strong> As a substitute driver, you receive ${frm.doc.fare_percentage_to_driver || 50}% of all fares regardless of target status. Target shortfalls do not roll over to the next day.
        </div>
    `;
    
    frappe.msgprint({
        title: __("Today's Summary - ") + frm.doc.first_name + ' ' + frm.doc.last_name,
        message: summary_html,
        wide: true
    });
}