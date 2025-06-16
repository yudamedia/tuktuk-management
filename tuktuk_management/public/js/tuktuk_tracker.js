// ~/frappe-bench/apps/tuktuk_management/tuktuk_management/public/js/tuktuk_tracker.js

// Telematics and tracking functionality for TukTuk vehicles
frappe.provide('tuktuk_management.tracker');

tuktuk_management.tracker = {
    init: function() {
        // Initialize tracking functionality
        console.log('TukTuk Tracker initialized');
    },
    
    update_location: function(tuktuk_id, lat, lng) {
        // Update vehicle location - FIXED: correct API method
        return frappe.call({
            method: 'tuktuk_management.api.telematics.update_location',
            args: {
                tuktuk_id: tuktuk_id,
                latitude: lat,
                longitude: lng
            },
            callback: function(r) {
                if (r.message && r.message.success) {
                    console.log('Location updated:', r.message.message);
                } else {
                    console.error('Location update failed:', r.message);
                }
            }
        });
    },
    
    update_battery: function(tuktuk_id, battery_level) {
        // Update battery level from telematics - FIXED: correct API method
        return frappe.call({
            method: 'tuktuk_management.api.telematics.update_battery',
            args: {
                tuktuk_id: tuktuk_id,
                battery_level: battery_level
            },
            callback: function(r) {
                if (r.message && r.message.success) {
                    console.log('Battery updated:', r.message.message);
                    
                    // Show alert if battery is low
                    if (battery_level <= 20) {
                        frappe.show_alert({
                            message: `Low battery warning: TukTuk ${tuktuk_id} at ${battery_level}%`,
                            indicator: 'orange'
                        });
                    }
                } else {
                    console.error('Battery update failed:', r.message);
                }
            }
        });
    },
    
    get_vehicle_status: function(tuktuk_id, callback) {
        // Get current vehicle status - FIXED: correct API method
        return frappe.call({
            method: 'tuktuk_management.api.telematics.get_status',
            args: {
                tuktuk_id: tuktuk_id
            },
            callback: function(r) {
                if (r.message && r.message.success) {
                    console.log('Vehicle status:', r.message.data);
                    if (callback) callback(r.message.data);
                } else {
                    console.error('Status check failed:', r.message);
                    if (callback) callback(null);
                }
            }
        });
    },
    
    // Additional helper function to update from telematics device
    update_from_device: function(vehicle_name, device_id, callback) {
        return frappe.call({
            method: 'tuktuk_management.api.telematics.update_from_device',
            args: {
                vehicle_name: vehicle_name,
                device_id: device_id
            },
            callback: function(r) {
                if (r.message && r.message.success) {
                    console.log('Device update successful:', r.message.message);
                    if (callback) callback(r.message.data);
                } else {
                    console.error('Device update failed:', r.message);
                    if (callback) callback(null);
                }
            }
        });
    },
    
    // Bulk update all vehicles from telematics
    update_all_vehicles: function() {
        return frappe.call({
            method: 'tuktuk_management.api.telematics.update_all_vehicle_statuses',
            callback: function(r) {
                console.log('All vehicles updated from telematics');
                frappe.show_alert({
                    message: 'All vehicle statuses updated',
                    indicator: 'green'
                });
            }
        });
    }
};

// Initialize on document ready
$(document).ready(function() {
    tuktuk_management.tracker.init();
});