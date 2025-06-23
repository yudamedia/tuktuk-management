// ~/frappe-bench/apps/tuktuk_management/tuktuk_management/public/js/tuktuk_vehicle.js

frappe.ui.form.on('TukTuk Vehicle', {
    refresh: function(frm) {
        // Initialize form with error handling
        try {
            setup_form_actions(frm);
            setup_indicators(frm);
            setup_auto_fields(frm);
            setup_geolocation_handler(frm);
        } catch (error) {
            console.error('Error in form refresh:', error);
        }
    },
    
    tuktuk_id: function(frm) {
        // Auto-generate mpesa account based on tuktuk_id
        if (frm.doc.tuktuk_id && !frm.doc.mpesa_account) {
            auto_generate_mpesa_account(frm);
        }
    },
    
    battery_level: function(frm) {
        try {
            add_battery_indicator(frm);
            
            // Warn if battery is low
            if (frm.doc.battery_level <= 20) {
                frappe.msgprint({
                    title: __('Low Battery Warning'),
                    message: __('Battery level is at {0}%. Consider charging this TukTuk.', [frm.doc.battery_level]),
                    indicator: 'orange'
                });
            }
        } catch (error) {
            console.error('Error in battery_level handler:', error);
        }
    },
    
    before_save: function(frm) {
        try {
            // Validate required fields
            if (!frm.doc.tuktuk_id) {
                frappe.msgprint(__('TukTuk ID is required'));
                frappe.validated = false;
                return;
            }
            
            // Auto-generate mpesa account if not provided
            if (!frm.doc.mpesa_account) {
                auto_generate_mpesa_account(frm);
            }
        } catch (error) {
            console.error('Error in before_save:', error);
        }
    },
    
    // Enhanced geolocation handling
    current_location: function(frm) {
        if (frm.doc.current_location) {
            try {
                // Update last reported time when location changes
                frm.set_value('last_reported', frappe.datetime.now_datetime());
                
                // Trigger map refresh
                refresh_location_map(frm);
            } catch (error) {
                console.error('Error updating location timestamp:', error);
            }
        }
    },
    
    // Add handlers for latitude and longitude if they exist as separate fields
    latitude: function(frm) {
        if (frm.doc.latitude && frm.doc.longitude) {
            update_geolocation_from_coordinates(frm);
        }
    },
    
    longitude: function(frm) {
        if (frm.doc.latitude && frm.doc.longitude) {
            update_geolocation_from_coordinates(frm);
        }
    }
});

function setup_geolocation_handler(frm) {
    // Add custom button to manually update location
    if (!frm.doc.__islocal) {
        frm.add_custom_button(__('Update Location'), function() {
            show_location_update_dialog(frm);
        }, __('Location'));
        
        frm.add_custom_button(__('Get Current Location'), function() {
            get_current_browser_location(frm);
        }, __('Location'));
        
        frm.add_custom_button(__('View on Map'), function() {
            view_location_on_external_map(frm);
        }, __('Location'));
    }
}

function update_geolocation_from_coordinates(frm) {
    /**
     * Update the geolocation field when latitude/longitude are manually entered
     */
    try {
        const lat = parseFloat(frm.doc.latitude);
        const lng = parseFloat(frm.doc.longitude);
        
        if (isNaN(lat) || isNaN(lng)) {
            console.warn('Invalid latitude or longitude values');
            return;
        }
        
        // Validate coordinate ranges
        if (lat < -90 || lat > 90 || lng < -180 || lng > 180) {
            frappe.msgprint(__('Invalid coordinates. Latitude must be between -90 and 90, longitude between -180 and 180.'));
            return;
        }
        
        // Create GeoJSON format for ERPNext geolocation field
        const geojson = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {
                        "name": frm.doc.tuktuk_id || "TukTuk Location"
                    },
                    "geometry": {
                        "type": "Point",
                        "coordinates": [lng, lat] // Note: GeoJSON uses [longitude, latitude]
                    }
                }
            ]
        };
        
        // Update the geolocation field
        frm.set_value('current_location', JSON.stringify(geojson));
        
        // Update last reported time
        frm.set_value('last_reported', frappe.datetime.now_datetime());
        
        frappe.show_alert({
            message: __('Location updated to {0}, {1}', [lat.toFixed(6), lng.toFixed(6)]),
            indicator: 'green'
        });
        
    } catch (error) {
        console.error('Error updating geolocation:', error);
        frappe.msgprint(__('Error updating location: {0}', [error.message]));
    }
}

function refresh_location_map(frm) {
    /**
     * Force refresh the geolocation map display
     */
    try {
        // If current_location field exists and has data
        if (frm.doc.current_location && frm.fields_dict.current_location) {
            const field = frm.fields_dict.current_location;
            
            // Trigger field refresh
            if (field.df && field.df.fieldtype === 'Geolocation') {
                field.refresh();
                
                // Additional method to force map redraw
                setTimeout(() => {
                    if (field.map) {
                        field.map.invalidateSize();
                        field.set_value(frm.doc.current_location);
                    }
                }, 100);
            }
        }
    } catch (error) {
        console.error('Error refreshing location map:', error);
    }
}

function show_location_update_dialog(frm) {
    /**
     * Show dialog to manually update coordinates
     */
    const d = new frappe.ui.Dialog({
        title: __('Update TukTuk Location'),
        fields: [
            {
                fieldtype: 'Float',
                fieldname: 'latitude',
                label: __('Latitude'),
                reqd: 1,
                default: get_current_latitude(frm),
                description: __('Latitude coordinate (-90 to 90)')
            },
            {
                fieldtype: 'Float',
                fieldname: 'longitude',
                label: __('Longitude'),
                reqd: 1,
                default: get_current_longitude(frm),
                description: __('Longitude coordinate (-180 to 180)')
            },
            {
                fieldtype: 'Small Text',
                fieldname: 'location_notes',
                label: __('Location Notes'),
                description: __('Optional notes about this location')
            }
        ],
        primary_action_label: __('Update Location'),
        primary_action: function(values) {
            try {
                // Validate coordinates
                const lat = parseFloat(values.latitude);
                const lng = parseFloat(values.longitude);
                
                if (lat < -90 || lat > 90) {
                    frappe.msgprint(__('Latitude must be between -90 and 90'));
                    return;
                }
                
                if (lng < -180 || lng > 180) {
                    frappe.msgprint(__('Longitude must be between -180 and 180'));
                    return;
                }
                
                // Update form fields if they exist
                if (frm.fields_dict.latitude) {
                    frm.set_value('latitude', lat);
                }
                if (frm.fields_dict.longitude) {
                    frm.set_value('longitude', lng);
                }
                
                // Update geolocation
                update_geolocation_from_coordinates_direct(frm, lat, lng);
                
                // Add location note if provided
                if (values.location_notes) {
                    frm.add_comment('Comment', `Location updated: ${values.location_notes}`);
                }
                
                d.hide();
                frappe.show_alert({
                    message: __('Location updated successfully'),
                    indicator: 'green'
                });
                
            } catch (error) {
                frappe.msgprint(__('Error updating location: {0}', [error.message]));
            }
        }
    });
    
    d.show();
}

function update_geolocation_from_coordinates_direct(frm, lat, lng) {
    /**
     * Direct update of geolocation field from coordinates
     */
    const geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {
                    "name": frm.doc.tuktuk_id || "TukTuk Location",
                    "description": `Updated on ${frappe.datetime.str_to_user(frappe.datetime.now_datetime())}`
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [lng, lat]
                }
            }
        ]
    };
    
    frm.set_value('current_location', JSON.stringify(geojson));
    frm.set_value('last_reported', frappe.datetime.now_datetime());
}

function get_current_browser_location(frm) {
    /**
     * Get current location from browser geolocation API
     */
    if (!navigator.geolocation) {
        frappe.msgprint(__('Geolocation is not supported by this browser'));
        return;
    }
    
    frappe.show_alert({
        message: __('Getting current location...'),
        indicator: 'blue'
    });
    
    navigator.geolocation.getCurrentPosition(
        function(position) {
            const lat = position.coords.latitude;
            const lng = position.coords.longitude;
            const accuracy = position.coords.accuracy;
            
            // Update form with current location
            if (frm.fields_dict.latitude) {
                frm.set_value('latitude', lat);
            }
            if (frm.fields_dict.longitude) {
                frm.set_value('longitude', lng);
            }
            
            update_geolocation_from_coordinates_direct(frm, lat, lng);
            
            frappe.show_alert({
                message: __('Location updated from GPS (accuracy: {0}m)', [Math.round(accuracy)]),
                indicator: 'green'
            });
        },
        function(error) {
            let message = __('Unable to get location');
            switch(error.code) {
                case error.PERMISSION_DENIED:
                    message = __('Location access denied by user');
                    break;
                case error.POSITION_UNAVAILABLE:
                    message = __('Location information unavailable');
                    break;
                case error.TIMEOUT:
                    message = __('Location request timed out');
                    break;
            }
            frappe.msgprint(message);
        },
        {
            enableHighAccuracy: true,
            timeout: 10000,
            maximumAge: 60000
        }
    );
}

function get_current_latitude(frm) {
    /**
     * Extract current latitude from geolocation field
     */
    try {
        if (frm.doc.current_location) {
            const location = JSON.parse(frm.doc.current_location);
            if (location.features && location.features[0] && location.features[0].geometry) {
                return location.features[0].geometry.coordinates[1]; // Latitude is second coordinate
            }
        }
        
        // Fallback to separate latitude field if exists
        if (frm.doc.latitude) {
            return frm.doc.latitude;
        }
        
        // Default to Diani Beach coordinates
        return -4.3297;
    } catch (error) {
        return -4.3297; // Default Diani Beach latitude
    }
}

function get_current_longitude(frm) {
    /**
     * Extract current longitude from geolocation field
     */
    try {
        if (frm.doc.current_location) {
            const location = JSON.parse(frm.doc.current_location);
            if (location.features && location.features[0] && location.features[0].geometry) {
                return location.features[0].geometry.coordinates[0]; // Longitude is first coordinate
            }
        }
        
        // Fallback to separate longitude field if exists
        if (frm.doc.longitude) {
            return frm.doc.longitude;
        }
        
        // Default to Diani Beach coordinates
        return 39.5773;
    } catch (error) {
        return 39.5773; // Default Diani Beach longitude
    }
}

function view_location_on_external_map(frm) {
    /**
     * Open location in external map service
     */
    try {
        const lat = get_current_latitude(frm);
        const lng = get_current_longitude(frm);
        
        if (lat && lng) {
            const url = `https://www.google.com/maps?q=${lat},${lng}&z=15`;
            window.open(url, '_blank');
        } else {
            frappe.msgprint(__('No location data available'));
        }
    } catch (error) {
        frappe.msgprint(__('Error opening map: {0}', [error.message]));
    }
}

// Keep all existing functions from the original file
function setup_form_actions(frm) {
    // Add custom buttons based on status
    if (frm.doc.status === 'Available') {
        frm.add_custom_button(__('Assign to Driver'), function() {
            assign_to_driver(frm);
        }, __('Actions'));
    }
    
    if (frm.doc.status === 'Assigned') {
        frm.add_custom_button(__('Set to Charging'), function() {
            set_charging(frm);
        }, __('Actions'));
        
        frm.add_custom_button(__('Set to Maintenance'), function() {
            set_maintenance(frm);
        }, __('Actions'));
    }
    
    if (frm.doc.status === 'Charging') {
        frm.add_custom_button(__('Complete Charging'), function() {
            complete_charging(frm);
        }, __('Actions'));
    }
    
    // Add telematics actions if device is configured
    if (frm.doc.device_id && frm.doc.device_imei) {
        frm.add_custom_button(__('Update from Device'), function() {
            update_from_telematics(frm);
        }, __('Telematics'));
        
        frm.add_custom_button(__('View Location History'), function() {
            view_location_history(frm);
        }, __('Telematics'));
    }
}

function setup_indicators(frm) {
    // Add battery level indicator
    if (frm.doc.battery_level !== undefined) {
        add_battery_indicator(frm);
    }
    
    // Add status indicator
    let status_color = get_status_color(frm.doc.status);
    frm.dashboard.add_indicator(__('Status: {0}', [frm.doc.status]), status_color);
    
    // Add last reported indicator if available
    if (frm.doc.last_reported) {
        let time_diff = frappe.datetime.get_diff(frappe.datetime.now_datetime(), frm.doc.last_reported);
        let hours_ago = Math.floor(time_diff / 3600);
        let indicator_color = hours_ago > 24 ? 'red' : (hours_ago > 6 ? 'orange' : 'green');
        frm.dashboard.add_indicator(__('Last Report: {0}h ago', [hours_ago]), indicator_color);
    }
    
    // Add location indicator
    if (frm.doc.current_location) {
        frm.dashboard.add_indicator(__('Location Available'), 'green');
    } else {
        frm.dashboard.add_indicator(__('No Location Data'), 'orange');
    }
}

function setup_auto_fields(frm) {
    // Auto-generate mpesa account if not set
    if (!frm.doc.mpesa_account && !frm.doc.__islocal && frm.doc.tuktuk_id) {
        auto_generate_mpesa_account(frm);
    }
}

function assign_to_driver(frm) {
    frappe.prompt([
        {
            label: 'Driver',
            fieldname: 'driver',
            fieldtype: 'Link',
            options: 'TukTuk Driver',
            reqd: 1,
            get_query: function() {
                return {
                    filters: {
                        'assigned_tuktuk': ['in', ['', null]]
                    }
                };
            }
        }
    ], function(values) {
        frappe.call({
            method: 'frappe.client.set_value',
            args: {
                doctype: 'TukTuk Driver',
                name: values.driver,
                fieldname: 'assigned_tuktuk',
                value: frm.doc.name
            },
            callback: function(r) {
                if (!r.exc) {
                    frm.set_value('status', 'Assigned');
                    frm.save();
                    frappe.msgprint(__('Driver assigned successfully'));
                }
            }
        });
    }, __('Assign Driver'), __('Assign'));
}

function set_charging(frm) {
    frappe.confirm(
        __('Set this TukTuk to charging status? This will free up the driver to rent another vehicle.'),
        function() {
            frm.set_value('status', 'Charging');
            frm.save();
        }
    );
}

function complete_charging(frm) {
    frappe.prompt([
        {
            label: 'Battery Level After Charging',
            fieldname: 'battery_level',
            fieldtype: 'Percent',
            default: 100,
            reqd: 1
        }
    ], function(values) {
        frm.set_value('battery_level', values.battery_level);
        frm.set_value('status', 'Assigned');
        frm.save();
        frappe.msgprint(__('Charging completed. Vehicle is ready for service.'));
    }, __('Complete Charging'), __('Complete'));
}

function set_maintenance(frm) {
    frappe.prompt([
        {
            label: 'Maintenance Notes',
            fieldname: 'notes',
            fieldtype: 'Small Text',
            reqd: 1
        }
    ], function(values) {
        frm.set_value('status', 'Maintenance');
        frm.save();
        
        // Add comment with maintenance notes
        frappe.call({
            method: 'frappe.desk.form.utils.add_comment',
            args: {
                reference_doctype: frm.doctype,
                reference_name: frm.docname,
                content: 'Maintenance: ' + values.notes,
                comment_email: frappe.session.user,
                comment_by: frappe.session.user_fullname
            }
        });
    }, __('Maintenance Details'), __('Set to Maintenance'));
}

function add_battery_indicator(frm) {
    if (frm.doc.battery_level !== undefined) {
        let color = 'green';
        let status = 'Good';
        
        if (frm.doc.battery_level <= 20) {
            color = 'red';
            status = 'Low - Charge Required';
        } else if (frm.doc.battery_level <= 50) {
            color = 'orange';
            status = 'Medium';
        }
        
        frm.dashboard.add_indicator(__('Battery: {0}% - {1}', [frm.doc.battery_level, status]), color);
    }
}

function get_status_color(status) {
    switch (status) {
        case 'Available': return 'green';
        case 'Assigned': return 'blue';
        case 'Charging': return 'orange';
        case 'Maintenance': return 'red';
        default: return 'gray';
    }
}

function auto_generate_mpesa_account(frm) {
    if (frm.doc.tuktuk_id) {
        // Extract number from tuktuk_id or use a simple incrementing number
        let account_number = '';
        
        // If tuktuk_id contains numbers, extract them
        let numbers = frm.doc.tuktuk_id.match(/\d+/g);
        if (numbers && numbers.length > 0) {
            account_number = numbers[0].padStart(3, '0').slice(-3);
        } else {
            // Fallback: use last 3 characters if they're digits, or generate
            let lastThree = frm.doc.tuktuk_id.slice(-3);
            if (/^\d{3}$/.test(lastThree)) {
                account_number = lastThree;
            } else {
                // Generate based on creation order or random
                account_number = String(Math.floor(Math.random() * 900) + 100);
            }
        }
        
        frm.set_value('mpesa_account', account_number);
    }
}

function update_from_telematics(frm) {
    if (!frm.doc.device_id) {
        frappe.msgprint(__('Device ID is required for telematics update'));
        return;
    }
    
    frappe.call({
        method: 'tuktuk_management.api.telematics.update_from_device',
        args: {
            vehicle_name: frm.doc.name,
            device_id: frm.doc.device_id
        },
        callback: function(r) {
            if (r.message) {
                frm.refresh();
                frappe.msgprint(__('Vehicle data updated from telematics device'));
            }
        }
    });
}

function view_location_history(frm) {
    frappe.route_options = {
        'vehicle': frm.doc.name
    };
    frappe.set_route('query-report', 'Vehicle Location History');
}