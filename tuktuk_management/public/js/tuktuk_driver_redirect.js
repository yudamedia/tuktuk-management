// ~/frappe-bench/apps/tuktuk_management/tuktuk_management/public/js/tuktuk_driver_redirect.js

// Automatic redirect for TukTuk users based on roles - SIMPLIFIED AND FIXED
(function() {
    'use strict';
    
    let redirectProcessed = false; // Prevent double execution
    
    function handleTukTukRedirect() {
        // Prevent multiple executions
        if (redirectProcessed) {
            return;
        }
        
        // Wait for frappe to be ready
        if (typeof frappe === 'undefined' || !frappe.boot || !frappe.user_roles) {
            return;
        }
        
        const currentPath = window.location.pathname;
        
        // NEVER redirect from these pages
        if (currentPath.includes('/login') ||
            currentPath.includes('/logout') ||
            currentPath.includes('/update-password') ||
            currentPath.includes('/driver/') ||
            currentPath.includes('/tuktuk-driver-dashboard')) {
            return;
        }
        
        // NEVER redirect if already on the correct page
        if (currentPath.includes('/app/tuktuk-management') && 
            !frappe.user_roles.includes('TukTuk Driver')) {
            // Already on management page and not a driver - don't redirect
            return;
        }
        
        // Get redirect info from boot (set by boot.py)
        const targetUrl = frappe.boot.tuktuk_redirect;
        const redirectRole = frappe.boot.tuktuk_redirect_role;
        
        if (!targetUrl) {
            // No redirect needed
            return;
        }
        
        // Define pages where redirect should happen
        const needsRedirect = (
            currentPath === '/app' || 
            currentPath === '/app/' || 
            currentPath === '/desk' ||
            currentPath === '/app/home'
        );
        
        // Special case: Drivers on management pages
        if (redirectRole === "TukTuk Driver" && currentPath.includes('/app/')) {
            redirectProcessed = true;
            console.log(`TukTuk Redirect: ${redirectRole} → ${targetUrl} (driver on app page)`);
            window.location.href = targetUrl;
            return;
        }
        
        // Normal redirect for initial pages
        if (needsRedirect && currentPath !== targetUrl) {
            redirectProcessed = true;
            console.log(`TukTuk Redirect: ${redirectRole} → ${targetUrl}`);
            setTimeout(function() {
                window.location.href = targetUrl;
            }, 200);
        }
    }
    
    // Run on document ready
    $(document).ready(function() {
        setTimeout(handleTukTukRedirect, 500);
    });
    
})();