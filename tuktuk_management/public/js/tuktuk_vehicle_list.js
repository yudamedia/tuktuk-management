// ~/frappe-bench/apps/tuktuk_management/tuktuk_management/public/js/tuktuk_vehicle_list.js
// Enhanced TukTuk Vehicle List view with device mapping integration

frappe.listview_settings['TukTuk Vehicle'] = {
    // Add device mapping status to list view
    add_fields: ["device_id", "device_imei", "battery_level", "last_reported", "latitude", "longitude"],
    
    get_indicator: function(doc) {
        // Color code based on device mapping and battery status
        if (!doc.device_id || !doc.device_imei) {
            return [__("No Device"), "red", "device_id,is,not set"];
        } else if (doc.battery_level <= 10) {
            return [__("Critical Battery"), "red", "battery_level,<=,10"];
        } else if (doc.battery_level <= 25) {
            return [__("Low Battery"), "orange", "battery_level,<=,25"];
        } else if (doc.status === "Available") {
            return [__("Available"), "green", "status,=,Available"];
        } else if (doc.status === "Assigned") {
            return [__("Assigned"), "blue", "status,=,Assigned"];
        } else if (doc.status === "Charging") {
            return [__("Charging"), "orange", "status,=,Charging"];
        } else {
            return [__("Maintenance"), "red", "status,=,Maintenance"];
        }
    },

    formatters: {
        battery_level: function(value) {
            if (value === null || value === undefined) {
                return '<span class="text-muted">N/A</span>';
            }
            
            let color = 'success';
            let icon = '🔋';
            
            if (value <= 10) {
                color = 'danger';
                icon = '🪫';
            } else if (value <= 25) {
                color = 'warning';
            } else if (value <= 50) {
                color = 'info';
            }
            
            return `<span class="badge badge-${color}">${icon} ${value}%</span>`;
        },
        
        device_id: function(value, field, doc) {
            if (!value) {
                return '<span class="text-danger">❌ No Device</span>';
            }
            
            const connectivity = doc.last_reported ? 
                (frappe.datetime.get_diff(frappe.datetime.now_datetime(), doc.last_reported) < 1 ? 
                    '🟢' : '🟡') : '🔴';
            
            return `<span title="Device ID: ${value}\nIMEI: ${doc.device_imei || 'N/A'}">${connectivity} ${value}</span>`;
        },
        
        last_reported: function(value) {
            if (!value) {
                return '<span class="text-muted">Never</span>';
            }
            
            const diff = frappe.datetime.get_diff(frappe.datetime.now_datetime(), value);
            const hours = Math.floor(diff / 3600);
            
            let color = 'success';
            if (hours > 24) color = 'danger';
            else if (hours > 6) color = 'warning';
            
            return `<small class="text-${color}">${hours}h ago</small>`;
        }
    },

    onload: function(listview) {
        // Add bulk device mapping actions
        if (frappe.user.has_role(['System Manager', 'Tuktuk Manager'])) {
            listview.page.add_action_item(__("Auto-Map All Devices"), function() {
                bulk_auto_map_devices();
            });
            
            listview.page.add_action_item(__("Validate All Mappings"), function() {
                validate_all_device_mappings();
            });
            
            listview.page.add_action_item(__("Device Mapping Report"), function() {
                show_device_mapping_report();
            });
        }
        
        // Add refresh telematics data action
        listview.page.add_action_item(__("Refresh Telematics"), function() {
            refresh_all_telematics_data();
        });
        
        // Add battery status filter buttons
        add_battery_filter_buttons(listview);
        
        // Add device mapping filter buttons
        add_device_mapping_filters(listview);
    },

    // Custom filters for device mapping
    filters: [
        {
            fieldname: 'status',
            label: __('Status'),
            fieldtype: 'Select',
            options: ['', 'Available', 'Assigned', 'Charging', 'Maintenance', 'Out of Service']
        }
    ]
};

// Bulk Device Mapping Functions
function bulk_auto_map_devices() {
    frappe.confirm(
        __('Automatically map all available devices to unmapped TukTuks?<br><br>This will use the auto-mapping algorithm to assign devices.'),
        function() {
            frappe.call({
                method: 'tuktuk_management.api.device_mapping.auto_map_devices_from_telemetry',
                callback: function(r) {
                    if (r.message && r.message.success) {
                        frappe.show_alert({
                            message: r.message.message,
                            indicator: 'green'
                        });
                        
                        // Refresh the list view
                        cur_list.refresh();
                    } else {
                        frappe.msgprint(__('Auto-mapping failed: {0}', [r.message.message || 'Unknown error']));
                    }
                }
            });
        }
    );
}

function validate_all_device_mappings() {
    frappe.call({
        method: 'tuktuk_management.api.device_mapping.validate_device_mappings',
        callback: function(r) {
            if (r.message) {
                const results = r.message;
                show_validation_results_dialog(results);
            }
        }
    });
}

function show_validation_results_dialog(results) {
    let content = `
        <div class="device-mapping-validation">
            <h5>Device Mapping Validation Results</h5>
            
            <div class="row">
                <div class="col-md-6">
                    <div class="card">
                        <div class="card-body">
                            <h6>Overview</h6>
                            <p><strong>Total Vehicles:</strong> ${results.total_vehicles}</p>
                            <p><strong>Mapped:</strong> ${results.mapped_vehicles}</p>
                            <p><strong>Unmapped:</strong> ${results.unmapped_vehicles}</p>
                            <p><strong>Recent Updates:</strong> ${results.recent_updates}</p>
                        </div>
                    </div>
                </div>
                
                <div class="col-md-6">
                    <div class="card">
                        <div class="card-body">
                            <h6>Status</h6>
                            <div class="progress mb-2">
                                <div class="progress-bar bg-success" style="width: ${(results.mapped_vehicles/results.total_vehicles)*100}%">
                                    ${Math.round((results.mapped_vehicles/results.total_vehicles)*100)}%
                                </div>
                            </div>
                            <small>Mapping Completion Rate</small>
                        </div>
                    </div>
                </div>
            </div>
    `;
    
    if (results.duplicate_mappings && results.duplicate_mappings.length > 0) {
        content += `
            <div class="alert alert-danger mt-3">
                <h6>⚠️ Duplicate Mappings Found</h6>
                <ul class="mb-0">
        `;
        results.duplicate_mappings.forEach(dup => {
            content += `<li>Device ${dup.device_id || dup.imei}: ${dup.vehicles.join(', ')}</li>`;
        });
        content += '</ul></div>';
    }
    
    if (results.inactive_devices && results.inactive_devices.length > 0) {
        content += `
            <div class="alert alert-warning mt-3">
                <h6>🔴 Inactive Devices (No recent updates)</h6>
                <ul class="mb-0">
        `;
        results.inactive_devices.forEach(inactive => {
            content += `<li>${inactive.tuktuk_id}: Last seen ${inactive.hours_ago}h ago</li>`;
        });
        content += '</ul></div>';
    }
    
    content += '</div>';
    
    const dialog = new frappe.ui.Dialog({
        title: __('Device Mapping Validation'),
        fields: [
            {
                fieldtype: 'HTML',
                fieldname: 'validation_results',
                options: content
            }
        ],
        primary_action: function() {
            dialog.hide();
        },
        primary_action_label: __('Close')
    });
    
    dialog.show();
}

function show_device_mapping_report() {
    frappe.call({
        method: 'tuktuk_management.api.device_mapping.get_unmapped_devices',
        callback: function(r) {
            if (r.message) {
                const data = r.message;
                show_mapping_report_dialog(data);
            }
        }
    });
}

function show_mapping_report_dialog(data) {
    let content = `
        <div class="device-mapping-report">
            <h5>Device Mapping Report</h5>
            
            <div class="row">
                <div class="col-md-4">
                    <div class="card text-center">
                        <div class="card-body">
                            <h3 class="text-danger">${data.unmapped_vehicles.length}</h3>
                            <p>Unmapped Vehicles</p>
                        </div>
                    </div>
                </div>
                
                <div class="col-md-4">
                    <div class="card text-center">
                        <div class="card-body">
                            <h3 class="text-success">${data.available_devices.length}</h3>
                            <p>Available Devices</p>
                        </div>
                    </div>
                </div>
                
                <div class="col-md-4">
                    <div class="card text-center">
                        <div class="card-body">
                            <h3 class="text-info">${data.mapping_suggestions.length}</h3>
                            <p>Suggested Mappings</p>
                        </div>
                    </div>
                </div>
            </div>
    `;
    
    if (data.unmapped_vehicles.length > 0) {
        content += `
            <div class="mt-3">
                <h6>Unmapped Vehicles:</h6>
                <div class="table-responsive">
                    <table class="table table-sm">
                        <thead>
                            <tr>
                                <th>TukTuk ID</th>
                                <th>Status</th>
                                <th>Action</th>
                            </tr>
                        </thead>
                        <tbody>
        `;
        
        data.unmapped_vehicles.forEach(vehicle => {
            content += `
                <tr>
                    <td>${vehicle.tuktuk_id}</td>
                    <td><span class="badge badge-secondary">${vehicle.status}</span></td>
                    <td>
                        <button class="btn btn-xs btn-primary" onclick="map_individual_vehicle('${vehicle.name}')">
                            Map Device
                        </button>
                    </td>
                </tr>
            `;
        });
        
        content += '</tbody></table></div></div>';
    }
    
    if (data.available_devices.length > 0) {
        content += `
            <div class="mt-3">
                <h6>Available Devices:</h6>
                <div class="table-responsive">
                    <table class="table table-sm">
                        <thead>
                            <tr>
                                <th>Device ID</th>
                                <th>IMEI</th>
                                <th>Status</th>
                            </tr>
                        </thead>
                        <tbody>
        `;
        
        data.available_devices.forEach(device => {
            const statusColor = device.status === 'Static' ? 'success' : 
                               device.status === 'Offline' ? 'danger' : 'warning';
            content += `
                <tr>
                    <td>${device.device_id}</td>
                    <td><small>${device.imei}</small></td>
                    <td><span class="badge badge-${statusColor}">${device.status}</span></td>
                </tr>
            `;
        });
        
        content += '</tbody></table></div></div>';
    }
    
    if (data.mapping_suggestions.length > 0) {
        content += `
            <div class="mt-3">
                <h6>Suggested Mappings:</h6>
                <div class="table-responsive">
                    <table class="table table-sm">
                        <thead>
                            <tr>
                                <th>TukTuk</th>
                                <th>→</th>
                                <th>Device</th>
                                <th>Confidence</th>
                                <th>Action</th>
                            </tr>
                        </thead>
                        <tbody>
        `;
        
        data.mapping_suggestions.forEach(suggestion => {
            const confidenceColor = suggestion.confidence === 'High' ? 'success' : 
                                   suggestion.confidence === 'Medium' ? 'warning' : 'secondary';
            content += `
                <tr>
                    <td>${suggestion.tuktuk_id}</td>
                    <td>→</td>
                    <td>${suggestion.suggested_device_id}</td>
                    <td><span class="badge badge-${confidenceColor}">${suggestion.confidence}</span></td>
                    <td>
                        <button class="btn btn-xs btn-success" 
                                onclick="apply_suggested_mapping('${suggestion.tuktuk_name}', '${suggestion.suggested_device_id}', '${suggestion.suggested_imei}')">
                            Apply
                        </button>
                    </td>
                </tr>
            `;
        });
        
        content += '</tbody></table></div></div>';
    }
    
    content += '</div>';
    
    const dialog = new frappe.ui.Dialog({
        title: __('Device Mapping Report'),
        size: 'large',
        fields: [
            {
                fieldtype: 'HTML',
                fieldname: 'mapping_report',
                options: content
            }
        ],
        primary_action: function() {
            dialog.hide();
        },
        primary_action_label: __('Close'),
        secondary_action: function() {
            frappe.call({
                method: 'tuktuk_management.api.device_mapping.apply_mapping_suggestions',
                callback: function(r) {
                    if (r.message && r.message.success) {
                        frappe.show_alert({
                            message: r.message.message,
                            indicator: 'green'
                        });
                        dialog.hide();
                        cur_list.refresh();
                    }
                }
            });
        },
        secondary_action_label: __('Apply All Suggestions')
    });
    
    dialog.show();
}

// Global functions for dialog buttons
window.map_individual_vehicle = function(vehicle_name) {
    frappe.set_route('Form', 'TukTuk Vehicle', vehicle_name);
};

window.apply_suggested_mapping = function(tuktuk_name, device_id, imei) {
    frappe.call({
        method: 'tuktuk_management.api.device_mapping.manual_device_mapping',
        args: {
            tuktuk_vehicle: tuktuk_name,
            device_id: device_id,
            device_imei: imei
        },
        callback: function(r) {
            if (r.message && r.message.success) {
                frappe.show_alert({
                    message: r.message.message,
                    indicator: 'green'
                });
                cur_list.refresh();
            }
        }
    });
};

function refresh_all_telematics_data() {
    frappe.confirm(
        __('Refresh telematics data for all vehicles with mapped devices?<br><br>This may take a few moments.'),
        function() {
            frappe.call({
                method: 'tuktuk_management.api.telematics.update_all_vehicle_statuses',
                callback: function(r) {
                    if (r.message) {
                        frappe.show_alert({
                            message: __('Telematics refresh initiated'),
                            indicator: 'blue'
                        });
                        
                        // Refresh list after a delay
                        setTimeout(() => {
                            cur_list.refresh();
                        }, 3000);
                    }
                }
            });
        }
    );
}

function add_battery_filter_buttons(listview) {
    // Add battery level filter buttons
    listview.page.sidebar.find('.list-tags').append(`
        <div class="battery-filters mt-3">
            <h6>Battery Levels</h6>
            <div class="btn-group-vertical btn-group-sm w-100" role="group">
                <button type="button" class="btn btn-outline-danger btn-sm battery-filter" data-filter="critical">
                    🪫 Critical (≤10%)
                </button>
                <button type="button" class="btn btn-outline-warning btn-sm battery-filter" data-filter="low">
                    🔋 Low (≤25%)
                </button>
                <button type="button" class="btn btn-outline-info btn-sm battery-filter" data-filter="medium">
                    🔋 Medium (26-50%)
                </button>
                <button type="button" class="btn btn-outline-success btn-sm battery-filter" data-filter="good">
                    🔋 Good (>50%)
                </button>
                <button type="button" class="btn btn-outline-secondary btn-sm battery-filter" data-filter="unknown">
                    ❓ Unknown
                </button>
            </div>
        </div>
    `);
    
    // Handle battery filter clicks
    listview.page.sidebar.on('click', '.battery-filter', function() {
        const filter_type = $(this).data('filter');
        let filters = [];
        
        switch(filter_type) {
            case 'critical':
                filters = [['TukTuk Vehicle', 'battery_level', '<=', 10]];
                break;
            case 'low':
                filters = [['TukTuk Vehicle', 'battery_level', '<=', 25]];
                break;
            case 'medium':
                filters = [
                    ['TukTuk Vehicle', 'battery_level', '>', 25],
                    ['TukTuk Vehicle', 'battery_level', '<=', 50]
                ];
                break;
            case 'good':
                filters = [['TukTuk Vehicle', 'battery_level', '>', 50]];
                break;
            case 'unknown':
                filters = [['TukTuk Vehicle', 'battery_level', 'is', 'not set']];
                break;
        }
        
        listview.filter_area.clear();
        filters.forEach(filter => {
            listview.filter_area.add(filter);
        });
        
        // Update button states
        $('.battery-filter').removeClass('active');
        $(this).addClass('active');
    });
}

function add_device_mapping_filters(listview) {
    // Add device mapping filter buttons
    listview.page.sidebar.find('.list-tags').append(`
        <div class="device-filters mt-3">
            <h6>Device Mapping</h6>
            <div class="btn-group-vertical btn-group-sm w-100" role="group">
                <button type="button" class="btn btn-outline-success btn-sm device-filter" data-filter="mapped">
                    📱 Mapped
                </button>
                <button type="button" class="btn btn-outline-danger btn-sm device-filter" data-filter="unmapped">
                    ❌ Unmapped
                </button>
                <button type="button" class="btn btn-outline-info btn-sm device-filter" data-filter="recent">
                    🕒 Recent Updates
                </button>
                <button type="button" class="btn btn-outline-warning btn-sm device-filter" data-filter="stale">
                    ⚠️ Stale Data
                </button>
            </div>
        </div>
    `);
    
    // Handle device filter clicks
    listview.page.sidebar.on('click', '.device-filter', function() {
        const filter_type = $(this).data('filter');
        let filters = [];
        
        switch(filter_type) {
            case 'mapped':
                filters = [
                    ['TukTuk Vehicle', 'device_id', 'is', 'set'],
                    ['TukTuk Vehicle', 'device_imei', 'is', 'set']
                ];
                break;
            case 'unmapped':
                filters = [['TukTuk Vehicle', 'device_id', 'is', 'not set']];
                break;
            case 'recent':
                // Updates within last 6 hours
                const six_hours_ago = frappe.datetime.add_to_date(new Date(), {hours: -6});
                filters = [['TukTuk Vehicle', 'last_reported', '>', six_hours_ago]];
                break;
            case 'stale':
                // No updates in last 24 hours
                const day_ago = frappe.datetime.add_to_date(new Date(), {days: -1});
                filters = [['TukTuk Vehicle', 'last_reported', '<', day_ago]];
                break;
        }
        
        listview.filter_area.clear();
        filters.forEach(filter => {
            listview.filter_area.add(filter);
        });
        
        // Update button states
        $('.device-filter').removeClass('active');
        $(this).addClass('active');
    });
}

// Custom column formatting for enhanced display
frappe.listview_settings['TukTuk Vehicle'].columns = [
    {
        field: 'tuktuk_id',
        width: '120px'
    },
    {
        field: 'status',
        width: '100px'
    },
    {
        field: 'device_id',
        width: '120px'
    },
    {
        field: 'battery_level',
        width: '100px'
    },
    {
        field: 'last_reported',
        width: '100px'
    }
];

// Add custom CSS for enhanced styling
$(document).ready(function() {
    if (!$('#tuktuk-vehicle-list-styles').length) {
        $('head').append(`
            <style id="tuktuk-vehicle-list-styles">
                .battery-filters .btn,
                .device-filters .btn {
                    margin-bottom: 2px;
                    text-align: left;
                }
                
                .battery-filters .btn.active,
                .device-filters .btn.active {
                    background-color: var(--primary-color);
                    color: white;
                    border-color: var(--primary-color);
                }
                
                .device-mapping-validation .card {
                    margin-bottom: 1rem;
                }
                
                .device-mapping-report .card {
                    margin-bottom: 1rem;
                }
                
                .list-row-container {
                    position: relative;
                }
                
                .list-row-container::before {
                    content: '';
                    position: absolute;
                    left: 0;
                    top: 0;
                    bottom: 0;
                    width: 4px;
                    background: transparent;
                }
                
                .list-row-container[data-device-status="unmapped"]::before {
                    background: #dc3545;
                }
                
                .list-row-container[data-device-status="mapped"]::before {
                    background: #28a745;
                }
                
                .list-row-container[data-device-status="stale"]::before {
                    background: #ffc107;
                }
            </style>
        `);
    }
});