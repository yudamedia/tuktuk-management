// ~/frappe-bench/apps/tuktuk_management/tuktuk_management/public/js/tuktuk_vehicle_list.js
// Fixed TukTuk Vehicle List with proper initialization and type safety
// 
// TYPE SAFETY IMPROVEMENTS:
// - All battery_level comparisons use flt() for proper float conversion
// - All time-based calculations use flt() and cint() for proper numeric conversion
// - Filter values are properly typed before comparison
// - Prevents string vs integer comparison errors that can cause filter iterations to fail

// Ensure Frappe utility functions are available
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

// FIRST: Define the listview settings with error handling - MINIMAL SAFE VERSION
frappe.listview_settings['TukTuk Vehicle'] = {
    
    // Add device mapping status to list view
    add_fields: ["device_id", "device_imei", "battery_level", "last_reported", "latitude", "longitude"],
    
    get_indicator: function(doc) {
        try {
            // Color code based on device mapping and battery status
            if (!doc.device_id || !doc.device_imei) {
                return [__("No Device"), "red"];
            } else if (doc.battery_level && flt(doc.battery_level) <= 10) {
                return [__("Critical Battery"), "red"];
            } else if (doc.battery_level && flt(doc.battery_level) <= 25) {
                return [__("Low Battery"), "orange"];
            } else if (doc.status === "Available") {
                return [__("Available"), "green"];
            } else if (doc.status === "Assigned") {
                return [__("Assigned"), "blue"];
            } else if (doc.status === "Charging") {
                return [__("Charging"), "orange"];
            } else if (doc.status === "Maintenance") {
                return [__("Maintenance"), "red"];
            } else {
                return [__("Unknown"), "gray"];
            }
        } catch (indicator_error) {
            console.error('Error in get_indicator:', indicator_error);
            return [__("Error"), "gray"];
        }
    },

    formatters: {
        battery_level: function(value) {
            if (value === null || value === undefined) {
                return '<span class="text-muted">N/A</span>';
            }
            
            // Convert to float for proper comparison
            const battery_level = flt(value);
            let color = 'success';
            let icon = '🔋';
            
            if (battery_level <= 10) {
                color = 'danger';
                icon = '🪫';
            } else if (battery_level <= 25) {
                color = 'warning';
            } else if (battery_level <= 50) {
                color = 'info';
            }
            
            return `<span class="badge badge-${color}">${icon} ${battery_level}%</span>`;
        },
        
        device_id: function(value, field, doc) {
            if (!value) {
                return '<span class="text-danger">❌ No Device</span>';
            }
            
            const connectivity = doc.last_reported ? 
                (flt(frappe.datetime.get_diff(frappe.datetime.now_datetime(), doc.last_reported)) < 1 ? 
                    '🟢' : '🟡') : '🔴';
            
            return `<span title="Device ID: ${value}\nIMEI: ${doc.device_imei || 'N/A'}">${connectivity} ${value}</span>`;
        },
        
        last_reported: function(value) {
            if (!value) {
                return '<span class="text-muted">Never</span>';
            }
            
            const diff = flt(frappe.datetime.get_diff(frappe.datetime.now_datetime(), value));
            const hours = cint(Math.floor(diff / 3600));
            
            let color = 'success';
            if (hours > 24) color = 'danger';
            else if (hours > 6) color = 'warning';
            
            return `<small class="text-${color}">${hours}h ago</small>`;
        }
    },

    onload: function(listview) {
        // Delayed initialization to avoid filter setup conflicts
        setTimeout(function() {
            try {
                console.log('🚗 TukTuk Vehicle list onload called');
                if (listview && listview.page) {
                    setup_tuktuk_vehicle_actions(listview);
                } else {
                    console.warn('⚠️ Listview not fully initialized, retrying...');
                    // Retry after another delay
                    setTimeout(function() {
                        if (listview && listview.page) {
                            setup_tuktuk_vehicle_actions(listview);
                        }
                    }, 1000);
                }
            } catch (onload_error) {
                console.error('Error in TukTuk Vehicle listview onload:', onload_error);
                // Show user-friendly message but don't break the interface
                frappe.show_alert({
                    message: __('Some advanced features may not be available'),
                    indicator: 'orange'
                });
            }
        }, 500);
    },

    // Removed problematic filters - will add back via custom buttons instead
    // filters: [] // Commenting out to avoid iteration errors
};

// SECOND: Define the setup function with comprehensive error handling
function setup_tuktuk_vehicle_actions(listview) {
    try {
        console.log('🔧 Setting up TukTuk Vehicle actions...');
        
        if (!listview || !listview.page) {
            console.log('❌ Listview or listview.page not available');
            return;
        }
        
        // Safety check for filter area to prevent iteration errors
        if (listview.filter_area && typeof listview.filter_area.clear === 'function') {
            try {
                // Test filter area functionality with a safe operation
                const test_filters = listview.filter_area.get();
                console.log('✅ Filter area is functional, found', test_filters.length, 'existing filters');
            } catch (filter_error) {
                console.warn('⚠️ Filter area has issues, will skip advanced filtering:', filter_error);
                // Continue without advanced filtering features
            }
        }
        
        // Add bulk device mapping actions
        if (frappe.user.has_role(['System Manager', 'Tuktuk Manager'])) {
            console.log('✅ User has required roles, adding buttons...');
            
            try {
                listview.page.add_action_item(__("🔄 Auto-Map All Devices"), function() {
                    bulk_auto_map_devices();
                });
                
                listview.page.add_action_item(__("✅ Validate All Mappings"), function() {
                    validate_all_device_mappings();
                });
                
                listview.page.add_action_item(__("📊 Device Mapping Report"), function() {
                    show_device_mapping_report();
                });
                
                // CSV UPLOAD BUTTON - with error handling
                listview.page.add_action_item(__("📁 CSV Upload"), function() {
                    console.log('CSV Upload button clicked');
                    try {
                        if (typeof tuktuk_management !== 'undefined' && 
                            tuktuk_management.csv_upload && 
                            typeof tuktuk_management.csv_upload.show_upload_dialog === 'function') {
                            
                            console.log('✅ Opening CSV upload dialog');
                            tuktuk_management.csv_upload.show_upload_dialog();
                        } else {
                            console.log('❌ CSV upload module not available, showing fallback');
                            show_csv_upload_fallback();
                        }
                    } catch (error) {
                        console.error('Error opening CSV upload:', error);
                        frappe.msgprint({
                            title: __('CSV Upload Error'),
                            message: __('There was an error opening the CSV upload dialog. Check console for details.'),
                            indicator: 'red'
                        });
                    }
                });
                
                console.log('✅ All action buttons added successfully');
            } catch (button_error) {
                console.error('Error adding action buttons:', button_error);
                frappe.show_alert({
                    message: __('Some action buttons could not be loaded'),
                    indicator: 'orange'
                });
            }
        } else {
            console.log('❌ User does not have required roles');
        }
        
        // Add refresh telematics data action (for all users) - with error handling
        try {
            listview.page.add_action_item(__("🔄 Refresh Telematics"), function() {
                refresh_all_telematics_data();
            });
        } catch (telematics_error) {
            console.error('Error adding telematics refresh button:', telematics_error);
        }
        
        // Add filter buttons with enhanced error handling
        try {
            if (listview.filter_area && typeof listview.filter_area.clear === 'function') {
                add_battery_filter_buttons(listview);
                add_device_mapping_filters(listview);
                console.log('✅ Filter buttons added');
            } else {
                console.log('⚠️ Skipping filter buttons due to filter area issues');
            }
        } catch (error) {
            console.error('Error adding filter buttons:', error);
            // Continue without filter buttons rather than breaking the entire setup
        }
        
    } catch (setup_error) {
        console.error('Critical error in setup_tuktuk_vehicle_actions:', setup_error);
        frappe.show_alert({
            message: __('TukTuk Vehicle actions setup encountered an error. Basic functionality preserved.'),
            indicator: 'red'
        });
    }
}

// THIRD: Fallback CSV upload function
function show_csv_upload_fallback() {
    const dialog = new frappe.ui.Dialog({
        title: __('CSV Upload'),
        fields: [
            {
                fieldtype: 'HTML',
                fieldname: 'fallback_info',
                options: `
                    <div class="alert alert-info">
                        <h6>CSV Upload Functionality</h6>
                        <p>The CSV upload module is not fully loaded. You can still upload CSV files using the basic method:</p>
                        <ol>
                            <li>Use the File Manager to upload your CSV</li>
                            <li>Use the API method to process it</li>
                            <li>Or try refreshing the page</li>
                        </ol>
                    </div>
                `
            },
            {
                fieldtype: 'Attach',
                fieldname: 'csv_file',
                label: __('CSV File'),
                description: 'Upload your telemetry CSV file'
            }
        ],
        primary_action: function(values) {
            if (values.csv_file) {
                process_csv_via_api(values.csv_file);
                dialog.hide();
            } else {
                frappe.msgprint(__('Please select a CSV file'));
            }
        },
        primary_action_label: __('Process CSV')
    });
    
    dialog.show();
}

function process_csv_via_api(file_url) {
    frappe.show_alert({
        message: __('Processing CSV file...'),
        indicator: 'blue'
    });
    
    frappe.call({
        method: 'tuktuk_management.api.csv_integration.process_uploaded_file',
        args: {
            file_url: file_url,
            mapping_type: 'auto'
        },
        callback: function(r) {
            if (r.message) {
                const results = r.message;
                frappe.msgprint({
                    title: __('CSV Processing Results'),
                    message: `
                        <div>
                            <p><strong>Total Rows:</strong> ${results.total_rows}</p>
                            <p><strong>Updated:</strong> ${results.updated}</p>
                            <p><strong>Failed:</strong> ${results.failed}</p>
                            <p><strong>Skipped:</strong> ${results.skipped}</p>
                        </div>
                    `,
                    indicator: results.updated > 0 ? 'green' : 'orange'
                });
                
                if (cur_list) {
                    cur_list.refresh();
                }
            }
        },
        error: function(error) {
            frappe.msgprint({
                title: __('CSV Processing Failed'),
                message: error.message,
                indicator: 'red'
            });
        }
    });
}

// FOURTH: Force initialization on document ready with comprehensive error handling
$(document).ready(function() {
    try {
        console.log('🚀 Document ready - checking for TukTuk Vehicle list');
        
        // Wait a bit for page to load, then force setup if needed
        setTimeout(function() {
            try {
                if (window.location.href.includes('TukTuk%20Vehicle') || 
                    window.location.href.includes('TukTuk Vehicle') ||
                    (cur_list && cur_list.doctype === 'TukTuk Vehicle')) {
                    
                    console.log('📍 TukTuk Vehicle list detected');
                    
                    // Check if actions are already loaded
                    if (cur_list && cur_list.page && cur_list.page.menu) {
                        try {
                            const existing_actions = cur_list.page.menu.find('a:contains("CSV Upload")');
                            
                            if (existing_actions.length === 0) {
                                console.log('🔧 Actions not found, forcing setup...');
                                setup_tuktuk_vehicle_actions(cur_list);
                            } else {
                                console.log('✅ Actions already exist');
                            }
                        } catch (menu_error) {
                            console.error('Error checking existing actions:', menu_error);
                            // Try setup anyway
                            setup_tuktuk_vehicle_actions(cur_list);
                        }
                    }
                }
            } catch (timeout_error) {
                console.error('Error in first timeout setup:', timeout_error);
            }
        }, 1000);
        
        // Also try again after a longer delay
        setTimeout(function() {
            try {
                if (cur_list && cur_list.doctype === 'TukTuk Vehicle') {
                    try {
                        const existing_actions = cur_list.page.menu.find('a:contains("CSV Upload")');
                        if (existing_actions.length === 0) {
                            console.log('🔧 Second attempt - forcing setup...');
                            setup_tuktuk_vehicle_actions(cur_list);
                        }
                    } catch (second_menu_error) {
                        console.error('Error in second attempt menu check:', second_menu_error);
                        // Try setup anyway
                        setup_tuktuk_vehicle_actions(cur_list);
                    }
                }
            } catch (second_timeout_error) {
                console.error('Error in second timeout setup:', second_timeout_error);
            }
        }, 3000);
        
    } catch (document_ready_error) {
        console.error('Critical error in document.ready for TukTuk Vehicle list:', document_ready_error);
    }
});

// FIFTH: Listen for route changes with enhanced error handling
$(document).on('page-change', function() {
    setTimeout(function() {
        try {
            if (cur_list && cur_list.doctype === 'TukTuk Vehicle') {
                console.log('📍 Page changed to TukTuk Vehicle list');
                
                try {
                    const existing_actions = cur_list.page.menu.find('a:contains("CSV Upload")');
                    if (existing_actions.length === 0) {
                        console.log('🔧 Page change - forcing setup...');
                        setup_tuktuk_vehicle_actions(cur_list);
                    }
                } catch (menu_check_error) {
                    console.error('Error checking menu on page change:', menu_check_error);
                    // Try setup anyway to ensure functionality
                    setup_tuktuk_vehicle_actions(cur_list);
                }
            }
        } catch (page_change_error) {
            console.error('Error handling page change for TukTuk Vehicle list:', page_change_error);
        }
    }, 500);
    
    // Additional safety check with longer delay
    setTimeout(function() {
        try {
            if (cur_list && cur_list.doctype === 'TukTuk Vehicle') {
                // Double-check setup after page change
                if (cur_list.page && !cur_list.page.menu.find('a:contains("CSV Upload")').length) {
                    console.log('🔧 Secondary page change setup...');
                    setup_tuktuk_vehicle_actions(cur_list);
                }
            }
        } catch (secondary_check_error) {
            console.error('Error in secondary page change check:', secondary_check_error);
        }
    }, 1500);
});

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
            const hours_ago = cint(inactive.hours_ago);
            content += `<li>${inactive.tuktuk_id}: Last seen ${hours_ago}h ago</li>`;
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
    try {
        // Safety check for required elements
        if (!listview || !listview.page || !listview.page.sidebar) {
            console.warn('⚠️ Missing required elements for battery filter buttons');
            return;
        }
        
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
        
        // FIXED: Handle battery filter clicks with proper filter format
        listview.page.sidebar.on('click', '.battery-filter', function() {
            try {
                const filter_type = $(this).data('filter');
                
                // Clear existing filters first
                if (listview.filter_area && typeof listview.filter_area.clear === 'function') {
                    listview.filter_area.clear();
                    
                    // FIXED: Apply filters directly, not through forEach loop
                    switch(filter_type) {
                        case 'critical':
                            listview.filter_area.add('TukTuk Vehicle', 'battery_level', '<=', 10);
                            break;
                        case 'low':
                            listview.filter_area.add('TukTuk Vehicle', 'battery_level', '<=', 25);
                            break;
                        case 'medium':
                            // For range filters, apply them separately
                            listview.filter_area.add('TukTuk Vehicle', 'battery_level', '>', 25);
                            listview.filter_area.add('TukTuk Vehicle', 'battery_level', '<=', 50);
                            break;
                        case 'good':
                            listview.filter_area.add('TukTuk Vehicle', 'battery_level', '>', 50);
                            break;
                        case 'unknown':
                            listview.filter_area.add('TukTuk Vehicle', 'battery_level', 'is', 'not set');
                            break;
                    }
                    
                    // Update button states
                    $('.battery-filter').removeClass('active');
                    $(this).addClass('active');
                    
                    console.log('✅ Battery filter applied:', filter_type);
                    
                } else {
                    console.warn('⚠️ Filter area not available for battery filtering');
                    frappe.show_alert({
                        message: __('Advanced filtering is not available in your current view'),
                        indicator: 'orange'
                    });
                }
            } catch (filter_apply_error) {
                console.error('Error applying battery filter:', filter_apply_error);
                frappe.show_alert({
                    message: __('Filter could not be applied due to system restrictions'),
                    indicator: 'orange'
                });
            }
        });
        
    } catch (battery_filter_error) {
        console.error('Error adding battery filter buttons:', battery_filter_error);
    }
}

// FIXED: Device mapping filter function - replace lines 677-750 in your file  
function add_device_mapping_filters(listview) {
    try {
        // Safety check for required elements
        if (!listview || !listview.page || !listview.page.sidebar) {
            console.warn('⚠️ Missing required elements for device mapping filter buttons');
            return;
        }
        
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
        
        // FIXED: Handle device filter clicks with proper filter format
        listview.page.sidebar.on('click', '.device-filter', function() {
            try {
                const filter_type = $(this).data('filter');
                
                // Clear existing filters first
                if (listview.filter_area && typeof listview.filter_area.clear === 'function') {
                    listview.filter_area.clear();
                    
                    // FIXED: Apply filters directly, not through forEach loop
                    switch(filter_type) {
                        case 'mapped':
                            listview.filter_area.add('TukTuk Vehicle', 'device_id', 'is', 'set');
                            break;
                        case 'unmapped':
                            listview.filter_area.add('TukTuk Vehicle', 'device_id', 'is', 'not set');
                            break;
                        case 'recent':
                            try {
                                // Updates within last 6 hours
                                const six_hours_ago = frappe.datetime.add_to_date(new Date(), {hours: -6});
                                listview.filter_area.add('TukTuk Vehicle', 'last_reported', '>', six_hours_ago);
                            } catch (date_error) {
                                console.error('Error calculating recent date filter:', date_error);
                                frappe.show_alert({
                                    message: __('Could not apply recent updates filter'),
                                    indicator: 'orange'
                                });
                                return;
                            }
                            break;
                        case 'stale':
                            try {
                                // No updates in last 24 hours
                                const day_ago = frappe.datetime.add_to_date(new Date(), {days: -1});
                                listview.filter_area.add('TukTuk Vehicle', 'last_reported', '<', day_ago);
                            } catch (date_error) {
                                console.error('Error calculating stale date filter:', date_error);
                                frappe.show_alert({
                                    message: __('Could not apply stale data filter'),
                                    indicator: 'orange'
                                });
                                return;
                            }
                            break;
                    }
                    
                    // Update button states
                    $('.device-filter').removeClass('active');
                    $(this).addClass('active');
                    
                    console.log('✅ Device mapping filter applied:', filter_type);
                    
                } else {
                    console.warn('⚠️ Filter area not available for device mapping filtering');
                    frappe.show_alert({
                        message: __('Advanced filtering is not available in your current view'),
                        indicator: 'orange'
                    });
                }
            } catch (filter_apply_error) {
                console.error('Error applying device mapping filter:', filter_apply_error);
                frappe.show_alert({
                    message: __('Filter could not be applied due to system restrictions'),
                    indicator: 'orange'
                });
            }
        });
        
    } catch (device_filter_error) {
        console.error('Error adding device mapping filter buttons:', device_filter_error);
    }
}

// Custom column formatting for enhanced display - TEMPORARILY DISABLED
// frappe.listview_settings['TukTuk Vehicle'].columns = [
//     {
//         field: 'tuktuk_id',
//         width: '120px'
//     },
//     {
//         field: 'status',
//         width: '100px'
//     },
//     {
//         field: 'device_id',
//         width: '120px'
//     },
//     {
//         field: 'battery_level',
//         width: '100px'
//     },
//     {
//         field: 'last_reported',
//         width: '100px'
//     }
// ];

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