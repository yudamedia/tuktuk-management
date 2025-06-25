// ~/frappe-bench/apps/tuktuk_management/tuktuk_management/public/js/tuktuk_management.js

// Global TukTuk Management functionality
frappe.provide('tuktuk_management');

// Global constants and settings
tuktuk_management.constants = {
    BATTERY_LOW_THRESHOLD: 20,
    BATTERY_CRITICAL_THRESHOLD: 10,
    DEFAULT_DAILY_TARGET: 3000,
    DEFAULT_FARE_PERCENTAGE: 50,
    OPERATING_HOURS_START: '06:00:00',
    OPERATING_HOURS_END: '00:00:00'
};

// Utility functions used across the app
tuktuk_management.utils = {
    
    // Format phone numbers to standard Kenyan format
    format_phone_number: function(phone) {
        if (!phone) return '';
        
        // Remove all non-digit characters
        let cleaned = phone.replace(/\D/g, '');
        
        // Convert to 254XXXXXXXXX format
        if (cleaned.startsWith('0')) {
            cleaned = '254' + cleaned.substring(1);
        } else if (cleaned.startsWith('254')) {
            // Already in correct format
        } else if (cleaned.length === 9) {
            cleaned = '254' + cleaned;
        }
        
        return cleaned;
    },
    
    // Get battery status color and text
    get_battery_status: function(battery_level) {
        if (battery_level <= tuktuk_management.constants.BATTERY_CRITICAL_THRESHOLD) {
            return { color: 'red', status: 'Critical', icon: 'fa-battery-0' };
        } else if (battery_level <= tuktuk_management.constants.BATTERY_LOW_THRESHOLD) {
            return { color: 'orange', status: 'Low', icon: 'fa-battery-1' };
        } else if (battery_level <= 50) {
            return { color: 'yellow', status: 'Medium', icon: 'fa-battery-2' };
        } else if (battery_level <= 75) {
            return { color: 'blue', status: 'Good', icon: 'fa-battery-3' };
        } else {
            return { color: 'green', status: 'Excellent', icon: 'fa-battery-4' };
        }
    },
    
    // Calculate target progress
    calculate_target_progress: function(current_balance, daily_target) {
        if (!daily_target || daily_target <= 0) {
            daily_target = tuktuk_management.constants.DEFAULT_DAILY_TARGET;
        }
        
        const progress = Math.min((current_balance / daily_target) * 100, 100);
        
        let status = 'Behind Target';
        let color = 'red';
        
        if (progress >= 100) {
            status = 'Target Met';
            color = 'green';
        } else if (progress >= 80) {
            status = 'Near Target';
            color = 'orange';
        }
        
        return {
            progress: Math.round(progress),
            status: status,
            color: color
        };
    },
    
    // Check if current time is within operating hours
    is_within_operating_hours: function() {
        const now = new Date();
        const current_time = now.getHours() * 100 + now.getMinutes();
        
        // Convert operating hours to comparable format
        const start_time = 600; // 06:00
        const end_time = 0;     // 00:00 (midnight)
        
        // Handle overnight operations (6AM to midnight)
        if (end_time < start_time) {
            return current_time >= start_time || current_time <= end_time;
        }
        
        return current_time >= start_time && current_time <= end_time;
    },
    
    // Format currency for display
    format_currency: function(amount) {
        if (!amount) return 'KSH 0';
        return 'KSH ' + parseFloat(amount).toLocaleString('en-KE', {
            minimumFractionDigits: 0,
            maximumFractionDigits: 2
        });
    },
    
    // Get status color for vehicles
    get_vehicle_status_color: function(status) {
        const colors = {
            'Available': 'green',
            'Assigned': 'blue', 
            'Charging': 'orange',
            'Maintenance': 'red'
        };
        return colors[status] || 'grey';
    }
};

// Global API helper functions
tuktuk_management.api = {
    
    // Quick system status check
    get_system_status: function(callback) {
        frappe.call({
            method: 'tuktuk_management.api.tuktuk.get_system_status',
            callback: function(r) {
                if (r.message && callback) {
                    callback(r.message);
                }
            }
        });
    },
    
    // Update vehicle battery from telematics
    update_vehicle_battery: function(tuktuk_id, battery_level, callback) {
        frappe.call({
            method: 'tuktuk_management.api.telematics.update_battery',
            args: {
                tuktuk_id: tuktuk_id,
                battery_level: battery_level
            },
            callback: function(r) {
                if (callback) callback(r.message);
            }
        });
    },
    
    // Quick test data creation
    create_test_data: function(callback) {
        frappe.call({
            method: 'tuktuk_management.api.tuktuk.create_test_data',
            callback: function(r) {
                if (callback) callback(r.message);
                frappe.show_alert({
                    message: __('Test data created successfully'),
                    indicator: 'green'
                });
            }
        });
    },
    
    // Setup Daraja integration
    setup_mpesa: function(callback) {
        frappe.call({
            method: 'tuktuk_management.api.tuktuk.setup_daraja_integration',
            callback: function(r) {
                if (callback) callback(r.message);
            }
        });
    }
};

// Dashboard widgets and components
tuktuk_management.dashboard = {
    
    // Create a battery indicator widget
    create_battery_widget: function(container, battery_level, tuktuk_id) {
        const safe_battery_level = flt(battery_level);
        const battery_info = tuktuk_management.utils.get_battery_status(safe_battery_level);
        
        const widget = $(`
            <div class="tuktuk-battery-widget" data-tuktuk="${tuktuk_id}">
                <div class="battery-level" style="color: ${battery_info.color}">
                    <i class="fa ${battery_info.icon}"></i>
                    <span class="battery-percentage">${safe_battery_level}%</span>
                </div>
                <div class="battery-status">${battery_info.status}</div>
            </div>
        `);
        
        container.append(widget);
        return widget;
    },
    
    // Create target progress widget  
    create_target_widget: function(container, current_balance, daily_target, driver_name) {
        const progress_info = tuktuk_management.utils.calculate_target_progress(current_balance, daily_target);
        
        const widget = $(`
            <div class="tuktuk-target-widget" data-driver="${driver_name}">
                <div class="target-progress">
                    <div class="progress-bar" style="width: ${progress_info.progress}%; background-color: ${progress_info.color}">
                        ${progress_info.progress}%
                    </div>
                </div>
                <div class="target-status" style="color: ${progress_info.color}">
                    ${progress_info.status}
                </div>
                <div class="target-details">
                    ${tuktuk_management.utils.format_currency(current_balance)} / 
                    ${tuktuk_management.utils.format_currency(daily_target)}
                </div>
            </div>
        `);
        
        container.append(widget);
        return widget;
    }
};

// Global event handlers and initialization
tuktuk_management.init = function() {
    
    // Add custom CSS classes
    $('head').append(`
        <style>
            .tuktuk-battery-widget {
                padding: 10px;
                border: 1px solid #ddd;
                border-radius: 4px;
                text-align: center;
                margin: 5px;
            }
            
            .tuktuk-target-widget {
                padding: 10px;
                border: 1px solid #ddd;
                border-radius: 4px;
                margin: 5px;
            }
            
            .progress-bar {
                height: 20px;
                border-radius: 4px;
                line-height: 20px;
                color: white;
                text-align: center;
                transition: all 0.3s ease;
            }
            
            .battery-level i {
                margin-right: 5px;
            }
            
            .tuktuk-status-indicator {
                display: inline-block;
                padding: 2px 8px;
                border-radius: 12px;
                font-size: 11px;
                font-weight: bold;
                text-transform: uppercase;
            }
        </style>
    `);
    
    // Global keyboard shortcuts
    $(document).on('keydown', function(e) {
        // Ctrl+Alt+T = Quick TukTuk status
        if (e.ctrlKey && e.altKey && e.keyCode === 84) {
            tuktuk_management.api.get_system_status(function(status) {
                frappe.msgprint({
                    title: __('TukTuk System Status'),
                    message: `
                        <p><strong>Operating Hours:</strong> ${status.operating_hours}</p>
                        <p><strong>Global Target:</strong> ${tuktuk_management.utils.format_currency(status.global_target)}</p>
                        <p><strong>Total Drivers:</strong> ${status.driver_stats.total_drivers}</p>
                        <p><strong>Today's Transactions:</strong> ${status.today_transactions}</p>
                    `,
                    indicator: 'blue'
                });
            });
        }
    });
    
    // Global utility for creating status indicators
    window.create_tuktuk_status_indicator = function(status) {
        const color = tuktuk_management.utils.get_vehicle_status_color(status);
        return `<span class="tuktuk-status-indicator" style="background-color: ${color}; color: white;">${status}</span>`;
    };
    
    console.log('🚗 TukTuk Management system initialized');
};

// Initialize when document is ready
$(document).ready(function() {
    tuktuk_management.init();
});

// Expose global functions for use in other scripts
frappe.tuktuk_management = tuktuk_management;

// Add this to tuktuk_management.js or create a new JS file

$(document).ready(function() {
    // Function to expand all sidebar menus
    function expandAllSidebarMenus() {
        // Remove hidden class from all nested containers
        $('.sidebar-child-item.nested-container.hidden').removeClass('hidden');
        
        // Optional: Add expanded class to parent items
        $('.sidebar-item.has-child').addClass('opened');
    }
    
    // Run on page load
    expandAllSidebarMenus();
    
    // Re-run when sidebar is updated (for dynamic content)
    const observer = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
            if (mutation.type === 'childList' || mutation.type === 'attributes') {
                expandAllSidebarMenus();
            }
        });
    });
    
    // Watch for changes in the sidebar
    const sidebar = document.querySelector('.desk-sidebar');
    if (sidebar) {
        observer.observe(sidebar, {
            childList: true,
            subtree: true,
            attributes: true,
            attributeFilter: ['class']
        });
    }
    
    // Prevent collapse on click (optional)
    $(document).on('click', '.sidebar-item.has-child', function(e) {
        e.preventDefault();
        // Allow navigation but prevent collapse
        const link = $(this).find('a').first();
        if (link.length && link.attr('href') && link.attr('href') !== '#') {
            window.location.href = link.attr('href');
        }
    });
});