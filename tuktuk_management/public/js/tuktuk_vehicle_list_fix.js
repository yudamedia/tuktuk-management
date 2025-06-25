// Fix for TukTuk Vehicle list view issues
// ~/frappe-bench/apps/tuktuk_management/tuktuk_management/public/js/tuktuk_vehicle_list_fix.js

frappe.listview_settings['TukTuk Vehicle'] = {
    add_fields: ["status", "battery_level", "tuktuk_id"],
    get_indicator: function(doc) {
        var indicator = [__(doc.status), "gray"];
        
        if (doc.status === "Available") {
            indicator[1] = "green";
        } else if (doc.status === "Assigned") {
            indicator[1] = "blue";
        } else if (doc.status === "Charging") {
            indicator[1] = "orange";
        } else if (doc.status === "Maintenance") {
            indicator[1] = "red";
        } else if (doc.status === "Rented") {
            indicator[1] = "purple";
        }
        
        return indicator;
    },
    
    onload: function(listview) {
        // Fix for filter issues
        if (listview.page && listview.page.add_inner_button) {
            listview.page.add_inner_button(__("Low Battery Alert"), function() {
                frappe.set_route("List", "TukTuk Vehicle", {
                    "battery_level": ["<", 20]
                });
            });
        }
        
        // Add custom filters safely
        setTimeout(function() {
            try {
                if (listview.filter_area && listview.filter_area.add) {
                    listview.filter_area.add("TukTuk Vehicle", "status", "=", "Available");
                }
            } catch (e) {
                console.log("Filter area not ready yet");
            }
        }, 1000);
    },
    
    formatters: {
        battery_level: function(value) {
            if (!value) return "";
            
            var color = "gray";
            if (value > 50) color = "green";
            else if (value > 20) color = "orange";
            else color = "red";
            
            return `<span style="color: ${color}; font-weight: bold;">${value}%</span>`;
        }
    }
};

// Ensure this runs after page load
$(document).ready(function() {
    // Additional fixes for list view errors
    if (cur_list && cur_list.doctype === "TukTuk Vehicle") {
        // Fix any undefined elements
        setTimeout(function() {
            try {
                if (cur_list.page && cur_list.page.main) {
                    console.log("TukTuk Vehicle list view loaded successfully");
                }
            } catch (e) {
                console.error("List view fix error:", e);
            }
        }, 500);
    }
});
