// ~/frappe-bench/apps/tuktuk_management/tuktuk_management/public/js/tuktuk_tracker.js

// Telematics and tracking functionality for TukTuk vehicles
frappe.provide('tuktuk_management.tracker');

tuktuk_management.tracker = {
    init: function() {
        // Initialize tracking functionality
        console.log('TukTuk Tracker initialized');
    },
    
    update_location: function(tuktuk_id, lat, lng) {
        // Update vehicle location
        return frappe.call({
            method: 'tuktuk_management.api.tracking.update_location',
            args: {
                tuktuk_id: tuktuk_id,
                latitude: lat,
                longitude: lng
            }
        });
    },
    
    update_battery: function(tuktuk_id, battery_level) {
        // Update battery level from telematics
        return frappe.call({
            method: 'tuktuk_management.api.tracking.update_battery',
            args: {
                tuktuk_id: tuktuk_id,
                battery_level: battery_level
            }
        });
    },
    
    get_vehicle_status: function(tuktuk_id) {
        // Get current vehicle status
        return frappe.call({
            method: 'tuktuk_management.api.tracking.get_status',
            args: {
                tuktuk_id: tuktuk_id
            }
        });
    }
};

// Initialize on document ready
$(document).ready(function() {
    tuktuk_management.tracker.init();
});