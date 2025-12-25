// Driver Dashboard Shared JavaScript

(function() {
    'use strict';

    // Initialize on DOM ready
    document.addEventListener('DOMContentLoaded', function() {
        initNavigation();
        initAutoRefresh();
        initTouchGestures();
    });

    // Navigation handling
    function initNavigation() {
        const navItems = document.querySelectorAll('.nav-item');
        
        navItems.forEach(item => {
            item.addEventListener('click', function(e) {
                // Add active state
                navItems.forEach(nav => nav.classList.remove('active'));
                this.classList.add('active');
                
                // Prevent default if using SPA behavior
                // For now, let browser handle navigation normally
            });
        });
    }

    // Auto-refresh functionality
    function initAutoRefresh() {
        // Refresh data every 30 seconds
        setInterval(function() {
            // Only refresh if page is visible
            if (!document.hidden) {
                refreshCurrentPage();
            }
        }, 30000); // 30 seconds
    }

    // Refresh current page data
    function refreshCurrentPage() {
        const currentPage = getCurrentPage();
        
        if (currentPage) {
            // Use Frappe's call method if available
            if (typeof frappe !== 'undefined' && frappe.call) {
                const methodMap = {
                    'home': 'tuktuk_management.api.driver_auth.get_tuktuk_driver_dashboard_data',
                    'target': 'tuktuk_management.api.driver_auth.get_driver_target_data',
                    'transactions': 'tuktuk_management.api.driver_auth.get_driver_transactions',
                    'deposit': 'tuktuk_management.api.driver_auth.get_driver_deposit_data',
                    'performance': 'tuktuk_management.api.driver_auth.get_driver_performance_data'
                };
                
                const method = methodMap[currentPage];
                if (method) {
                    frappe.call({
                        method: method,
                        callback: function(r) {
                            if (r.message) {
                                updatePageData(currentPage, r.message);
                            }
                        },
                        error: function(r) {
                            console.error('Error refreshing data:', r);
                        }
                    });
                }
            }
        }
    }

    // Get current page from URL
    function getCurrentPage() {
        const path = window.location.pathname;
        if (path.includes('/driver/home')) return 'home';
        if (path.includes('/driver/target')) return 'target';
        if (path.includes('/driver/transactions')) return 'transactions';
        if (path.includes('/driver/deposit')) return 'deposit';
        if (path.includes('/driver/performance')) return 'performance';
        return null;
    }

    // Update page data (to be implemented per page)
    function updatePageData(page, data) {
        // This will be customized per page
        console.log('Updating data for page:', page, data);
    }

    // Touch gestures for mobile
    function initTouchGestures() {
        let touchStartX = 0;
        let touchEndX = 0;
        
        document.addEventListener('touchstart', function(e) {
            touchStartX = e.changedTouches[0].screenX;
        }, { passive: true });
        
        document.addEventListener('touchend', function(e) {
            touchEndX = e.changedTouches[0].screenX;
            handleSwipe();
        }, { passive: true });
        
        function handleSwipe() {
            const swipeThreshold = 50;
            const diff = touchStartX - touchEndX;
            
            if (Math.abs(diff) > swipeThreshold) {
                if (diff > 0) {
                    // Swipe left - go to next page
                    navigateToNextPage();
                } else {
                    // Swipe right - go to previous page
                    navigateToPreviousPage();
                }
            }
        }
    }

    // Navigate to next page in sequence
    function navigateToNextPage() {
        const pages = ['home', 'target', 'transactions', 'deposit', 'performance'];
        const current = getCurrentPage();
        const currentIndex = pages.indexOf(current);
        
        if (currentIndex >= 0 && currentIndex < pages.length - 1) {
            window.location.href = '/driver/' + pages[currentIndex + 1];
        }
    }

    // Navigate to previous page in sequence
    function navigateToPreviousPage() {
        const pages = ['home', 'target', 'transactions', 'deposit', 'performance'];
        const current = getCurrentPage();
        const currentIndex = pages.indexOf(current);
        
        if (currentIndex > 0) {
            window.location.href = '/driver/' + pages[currentIndex - 1];
        }
    }

    // Format currency
    function formatCurrency(amount) {
        return 'KSH ' + parseFloat(amount || 0).toLocaleString('en-KE', {
            minimumFractionDigits: 0,
            maximumFractionDigits: 0
        });
    }

    // Format date
    function formatDate(dateString) {
        if (!dateString) return '';
        const date = new Date(dateString);
        return date.toLocaleDateString('en-KE', {
            day: 'numeric',
            month: 'short',
            year: 'numeric'
        });
    }

    // Format datetime
    function formatDateTime(dateString) {
        if (!dateString) return '';
        const date = new Date(dateString);
        return date.toLocaleString('en-KE', {
            day: 'numeric',
            month: 'short',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    }

    // Show loading state
    function showLoading(element) {
        if (element) {
            element.innerHTML = '<div class="loading"><div class="spinner"></div><p>Loading...</p></div>';
        }
    }

    // Show error state
    function showError(element, message) {
        if (element) {
            element.innerHTML = '<div class="alert alert-danger">' + (message || 'An error occurred') + '</div>';
        }
    }

    // Expose utility functions globally
    window.DriverDashboard = {
        formatCurrency: formatCurrency,
        formatDate: formatDate,
        formatDateTime: formatDateTime,
        showLoading: showLoading,
        showError: showError,
        refreshCurrentPage: refreshCurrentPage
    };

    // ============================================
    // HAILING AVAILABILITY TOGGLE FUNCTIONALITY
    // ============================================

    // Global variables for hailing toggle
    let currentDriverData = null;
    let gpsTrackingInterval = null;
    let hailingStatusRefreshInterval = null;
    let isTogglingHailing = false;

    // Initialize hailing toggle on DOM ready
    document.addEventListener('DOMContentLoaded', function() {
        initHailingToggle();
    });

    /**
     * Initialize the hailing toggle button
     */
    function initHailingToggle() {
        const toggleElement = document.getElementById('hailing-toggle');
        
        // Only initialize if toggle exists on the page (driver home page)
        if (!toggleElement) {
            return;
        }

        // Add event listener for toggle changes
        toggleElement.addEventListener('change', handleHailingToggle);

        // Fetch initial driver data and status
        fetchCurrentDriverData();

        // Set up auto-refresh of hailing status every 30 seconds
        hailingStatusRefreshInterval = setInterval(fetchDriverHailingStatus, 30000);

        // Initialize UI state based on current toggle state
        updateToggleUI(toggleElement.checked ? 'Available' : 'Offline');
    }

    /**
     * Fetch current driver data including TukTuk assignment
     */
    async function fetchCurrentDriverData() {
        try {
            const response = await frappe.call({
                method: 'tuktuk_management.api.driver_auth.get_current_tuktuk_driver'
            });

            if (response && response.message) {
                currentDriverData = response.message;
            }
        } catch (error) {
            console.error('Failed to fetch driver data:', error);
        }
    }

    /**
     * Fetch current hailing status from server (for auto-refresh)
     */
    async function fetchDriverHailingStatus() {
        try {
            const response = await frappe.call({
                method: 'tuktuk_management.api.driver_auth.get_driver_hailing_status'
            });

            if (response && response.message && response.message.success) {
                const status = response.message.hailing_status;
                const toggleElement = document.getElementById('hailing-toggle');
                
                // Update toggle state if different from current
                if (toggleElement) {
                    const shouldBeChecked = status === 'Available';
                    if (toggleElement.checked !== shouldBeChecked) {
                        toggleElement.checked = shouldBeChecked;
                        updateToggleUI(status);
                    }
                }

                // Update driver data with latest TukTuk assignment
                if (response.message.assigned_tuktuk) {
                    if (!currentDriverData) {
                        currentDriverData = {};
                    }
                    currentDriverData.assigned_tuktuk = response.message.assigned_tuktuk;
                }
            }
        } catch (error) {
            console.error('Failed to refresh hailing status:', error);
        }
    }

    /**
     * Handle toggle switch change event
     */
    async function handleHailingToggle(event) {
        // Prevent concurrent toggle operations
        if (isTogglingHailing) {
            event.preventDefault();
            return;
        }

        const isGoingOnline = event.target.checked;

        // Validate TukTuk assignment
        if (isGoingOnline && (!currentDriverData || !currentDriverData.assigned_tuktuk)) {
            event.target.checked = false;
            showHailingError('You need an assigned TukTuk to go online for hailing');
            return;
        }

        isTogglingHailing = true;
        showHailingLoading(true);
        hideHailingMessages();

        try {
            // Get current driver ID
            const driverResponse = await frappe.call({
                method: 'tuktuk_management.api.driver_auth.get_current_tuktuk_driver'
            });

            if (!driverResponse || !driverResponse.message) {
                throw new Error('Failed to fetch driver information');
            }

            const driverId = driverResponse.message.name;

            // Call set_driver_availability API from tuktuk_hailing app
            const result = await frappe.call({
                method: 'tuktuk_hailing.api.location.set_driver_availability',
                args: {
                    driver_id: driverId,
                    available: isGoingOnline
                }
            });

            if (result && result.message && result.message.success) {
                const newStatus = result.message.status;
                updateToggleUI(newStatus);

                if (newStatus === 'Available') {
                    // Start GPS tracking when going online
                    await startGPSTracking(driverId);
                    showHailingSuccess('You are now online for hailing rides!');
                } else {
                    // Stop GPS tracking when going offline
                    stopGPSTracking();
                    showHailingSuccess('You are now offline');
                }
            } else {
                throw new Error(result.message?.message || 'Failed to update availability');
            }
        } catch (error) {
            // Revert toggle on error
            event.target.checked = !isGoingOnline;
            updateToggleUI(isGoingOnline ? 'Offline' : 'Available');
            
            const errorMessage = error.message || 'Failed to update hailing status';
            showHailingError(errorMessage);
            console.error('Hailing toggle error:', error);
        } finally {
            showHailingLoading(false);
            isTogglingHailing = false;
        }
    }

    /**
     * Start GPS tracking for the driver
     */
    async function startGPSTracking(driverId) {
        // Check if geolocation is available
        if (!navigator.geolocation) {
            showHailingError('GPS is not supported by your browser');
            return;
        }

        // Stop any existing tracking
        stopGPSTracking();

        // Request initial location
        try {
            const position = await getCurrentPosition();
            await updateDriverLocation(driverId, position);

            // Set up interval to update location every 10 seconds
            gpsTrackingInterval = setInterval(async () => {
                try {
                    const pos = await getCurrentPosition();
                    await updateDriverLocation(driverId, pos);
                } catch (error) {
                    console.error('GPS tracking update error:', error);
                }
            }, 10000); // 10 seconds

            console.log('GPS tracking started');
        } catch (error) {
            if (error.code === 1) {
                showHailingError('GPS permission denied. Please enable location access.');
            } else if (error.code === 2) {
                showHailingError('GPS position unavailable. Please check your device settings.');
            } else if (error.code === 3) {
                showHailingError('GPS timeout. Please check your connection.');
            } else {
                showHailingError('Failed to start GPS tracking: ' + error.message);
            }
            console.error('GPS error:', error);
        }
    }

    /**
     * Stop GPS tracking
     */
    function stopGPSTracking() {
        if (gpsTrackingInterval) {
            clearInterval(gpsTrackingInterval);
            gpsTrackingInterval = null;
            console.log('GPS tracking stopped');
        }
    }

    /**
     * Get current GPS position (promisified)
     */
    function getCurrentPosition() {
        return new Promise((resolve, reject) => {
            navigator.geolocation.getCurrentPosition(
                (position) => resolve(position),
                (error) => reject(error),
                {
                    enableHighAccuracy: true,
                    timeout: 10000,
                    maximumAge: 0
                }
            );
        });
    }

    /**
     * Update driver location on the server
     */
    async function updateDriverLocation(driverId, position) {
        try {
            const result = await frappe.call({
                method: 'tuktuk_hailing.api.location.update_driver_location',
                args: {
                    driver_id: driverId,
                    latitude: position.coords.latitude,
                    longitude: position.coords.longitude,
                    accuracy: position.coords.accuracy
                }
            });

            if (result && result.message && result.message.success) {
                console.log('Location updated:', position.coords.latitude, position.coords.longitude);
            } else {
                console.warn('Location update failed:', result.message);
            }
        } catch (error) {
            console.error('Failed to update location:', error);
        }
    }

    /**
     * Update toggle UI based on status
     */
    function updateToggleUI(status) {
        const card = document.getElementById('hailing-availability-card');
        const statusText = document.getElementById('hailing-status-text');

        if (!card || !statusText) {
            return;
        }

        const isOnline = status === 'Available';

        // Update card classes
        card.classList.remove('online', 'offline');
        card.classList.add(isOnline ? 'online' : 'offline');

        // Update status text
        statusText.textContent = isOnline ? 'Online' : 'Offline';
    }

    /**
     * Show loading overlay
     */
    function showHailingLoading(show) {
        const loadingOverlay = document.getElementById('hailing-loading');
        if (loadingOverlay) {
            loadingOverlay.style.display = show ? 'flex' : 'none';
        }
    }

    /**
     * Show error message
     */
    function showHailingError(message) {
        const errorElement = document.getElementById('hailing-error');
        if (errorElement) {
            errorElement.textContent = message;
            errorElement.style.display = 'block';

            // Auto-hide after 5 seconds
            setTimeout(() => {
                errorElement.style.display = 'none';
            }, 5000);
        }
    }

    /**
     * Show success message
     */
    function showHailingSuccess(message) {
        const errorElement = document.getElementById('hailing-error');
        if (errorElement) {
            // Temporarily change styling to success
            errorElement.style.backgroundColor = '#d4edda';
            errorElement.style.borderColor = '#c3e6cb';
            errorElement.style.color = '#155724';
            errorElement.textContent = '✓ ' + message;
            errorElement.style.display = 'block';

            // Hide after 3 seconds and reset styling
            setTimeout(() => {
                errorElement.style.display = 'none';
                errorElement.style.backgroundColor = '';
                errorElement.style.borderColor = '';
                errorElement.style.color = '';
            }, 3000);
        }
    }

    /**
     * Hide all hailing messages
     */
    function hideHailingMessages() {
        const errorElement = document.getElementById('hailing-error');
        if (errorElement) {
            errorElement.style.display = 'none';
        }
    }

    /**
     * Clean up on page unload
     */
    window.addEventListener('beforeunload', function() {
        stopGPSTracking();
        if (hailingStatusRefreshInterval) {
            clearInterval(hailingStatusRefreshInterval);
        }
    });

    // Expose hailing functions globally for debugging
    window.HailingToggle = {
        startGPSTracking: startGPSTracking,
        stopGPSTracking: stopGPSTracking,
        fetchDriverHailingStatus: fetchDriverHailingStatus,
        updateToggleUI: updateToggleUI
    };

})();
