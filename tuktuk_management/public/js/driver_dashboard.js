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

})();
