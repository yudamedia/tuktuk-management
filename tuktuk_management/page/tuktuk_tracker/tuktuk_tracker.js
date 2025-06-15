// Create file: tuktuk_management/tuktuk_management/page/tuktuk_tracker/tuktuk_tracker.js

frappe.pages['tuktuk-tracker'].on_page_load = function(wrapper) {
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'TukTuk Tracker',
        single_column: true
    });
    
    // Initialize the tracker page
    new TukTukTracker(page);
}

class TukTukTracker {
    constructor(page) {
        this.page = page;
        this.map = null;
        this.markers = {};
        this.setup();
        this.refresh();
        
        // Set up auto-refresh every 2 minutes
        this.refreshInterval = setInterval(() => this.refresh(), 120000);
    }
    
    setup() {
        // Add refresh button handler
        this.page.set_primary_action('Refresh', () => this.refresh(), 'octicon octicon-sync');
        
        // Initialize map
        this.initMap();
        
        // Setup filters
        this.setupFilters();
    }
    
    initMap() {
        // Load the map using Leaflet.js (you'll need to include the library)
        this.map = L.map($('.tuktuk-map-container')[0]).setView([-4.3439, 39.5636], 13); // Diani Beach coordinates
        
        // Add OpenStreetMap tile layer
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        }).addTo(this.map);
    }
    
    setupFilters() {
        $('.status-filter').on('change', () => this.applyFilters());
        $('.battery-filter').on('change', () => this.applyFilters());
    }
    
    refresh() {
        frappe.call({
            method: 'tuktuk_management.api.telematics.get_all_vehicle_locations',
            callback: (r) => {
                if (r.message) {
                    this.updateMap(r.message);
                    this.updateList(r.message);
                }
            }
        });
    }
    
    updateMap(vehicles) {
        // Clear existing markers
        Object.values(this.markers).forEach(marker => this.map.removeLayer(marker));
        this.markers = {};
        
        // Add new markers
        vehicles.forEach(vehicle => {
            if (vehicle.current_location) {
                const [lat, lng] = vehicle.current_location.split(',').map(coord => parseFloat(coord.trim()));
                if (!isNaN(lat) && !isNaN(lng)) {
                    // Create marker with custom icon based on battery level
                    const icon = this.getMarkerIcon(vehicle);
                    
                    // Add marker to map
                    const marker = L.marker([lat, lng], { icon }).addTo(this.map);
                    
                    // Add popup with vehicle info
                    marker.bindPopup(this.createPopupContent(vehicle));
                    
                    // Store marker reference
                    this.markers[vehicle.name] = marker;
                }
            }
        });
    }
    
    getMarkerIcon(vehicle) {
        // Choose icon color based on battery level
        let color = 'green';
        if (vehicle.battery_level <= 20) {
            color = 'red';
        } else if (vehicle.battery_level <= 70) {
            color = 'orange';
        }
        
        // Return Leaflet icon
        return L.divIcon({
            html: `<div class="tuktuk-marker ${color}" title="${vehicle.tuktuk_id}">
                    <span>${vehicle.tuktuk_id}</span>
                  </div>`,
            className: '',
            iconSize: [40, 40]
        });
    }
    
    createPopupContent(vehicle) {
        return `
            <div class="tuktuk-popup">
                <h4>${vehicle.tuktuk_id}</h4>
                <p><strong>Status:</strong> ${vehicle.status}</p>
                <p><strong>Battery:</strong> ${vehicle.battery_level}%</p>
                <p><strong>Last Updated:</strong> ${frappe.datetime.str_to_user(vehicle.last_reported || '')}</p>
                ${vehicle.status === 'Assigned' ? 
                    `<p><strong>Driver:</strong> ${vehicle.driver_name || 'Unknown'}</p>` : ''}
                <div class="tuktuk-popup-actions">
                    <a href="/app/tuktuk-vehicle/${vehicle.name}">View Details</a>
                </div>
            </div>
        `;
    }
    
    updateList(vehicles) {
        const $list = $('.tuktuk-list');
        $list.empty();
        
        vehicles.forEach(vehicle => {
            const batteryClass = vehicle.battery_level <= 20 ? 'text-danger' : 
                               vehicle.battery_level <= 70 ? 'text-warning' : 'text-success';
            
            const $item = $(`
                <div class="tuktuk-list-item" data-id="${vehicle.name}">
                    <div class="row">
                        <div class="col-md-6">
                            <strong>${vehicle.tuktuk_id}</strong>
                            <div class="text-muted">${vehicle.status}</div>
                        </div>
                        <div class="col-md-6 text-right">
                            <div class="battery-indicator ${batteryClass}">
                                <i class="fa fa-battery-${Math.ceil(vehicle.battery_level / 25)}"></i> ${vehicle.battery_level}%
                            </div>
                            <div class="text-muted small">
                                ${frappe.datetime.str_to_user(vehicle.last_reported || '')}
                            </div>
                        </div>
                    </div>
                </div>
            `);
            
            // Add click handler to focus on map
            $item.on('click', () => {
                const marker = this.markers[vehicle.name];
                if (marker) {
                    this.map.setView(marker.getLatLng(), 15);
                    marker.openPopup();
                }
            });
            
            $list.append($item);
        });
    }
    
    applyFilters() {
        const statusFilter = $('.status-filter').val();
        const batteryFilter = $('.battery-filter').val();
        
        $('.tuktuk-list-item').each((i, el) => {
            const $item = $(el);
            const id = $item.data('id');
            const vehicle = this.vehicles.find(v => v.name === id);
            
            if (!vehicle) return;
            
            let show = true;
            
            // Apply status filter
            if (statusFilter !== 'All' && vehicle.status !== statusFilter) {
                show = false;
            }
            
            // Apply battery filter
            if (batteryFilter === 'Low' && vehicle.battery_level > 20) {
                show = false;
            } else if (batteryFilter === 'Medium' && (vehicle.battery_level <= 20 || vehicle.battery_level > 70)) {
                show = false;
            } else if (batteryFilter === 'High' && vehicle.battery_level <= 70) {
                show = false;
            }
            
            // Show/hide item
            $item.toggle(show);
            
            // Show/hide marker
            const marker = this.markers[id];
            if (marker) {
                if (show) {
                    if (!this.map.hasLayer(marker)) {
                        this.map.addLayer(marker);
                    }
                } else {
                    this.map.removeLayer(marker);
                }
            }
        });
    }
}