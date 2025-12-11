// ~/frappe-bench/apps/tuktuk_management/tuktuk_management/public/js/tuktuk_driver_redirect.js

// Automatic redirect for TukTuk users based on roles
$(document).ready(function() {
    // Wait for frappe to be fully loaded
    if (typeof frappe === 'undefined' || !frappe.boot) {
        setTimeout(function() {
            handleTukTukRedirect();
        }, 1000);
        return;
    }
    
    handleTukTukRedirect();
});

function handleTukTukRedirect() {
    // PRIORITY CHECK: If user is a TukTuk Driver, always redirect to dashboard
    // This overrides any other redirect that might have been set
    if (frappe.user_roles && frappe.user_roles.includes('TukTuk Driver')) {
        const currentPath = window.location.pathname;
        if (!currentPath.includes('/tuktuk-driver-dashboard') &&
            !currentPath.includes('/login') &&
            !currentPath.includes('/logout') &&
            !currentPath.includes('/update-password')) {
            if (currentPath === '/app' || 
                currentPath === '/app/' || 
                currentPath === '/desk' ||
                currentPath === '/app/home' ||
                currentPath.startsWith('/app/tuktuk-management')) {
                console.log('TukTuk Driver priority redirect: forcing redirect to dashboard');
                setTimeout(function() {
                    window.location.href = '/tuktuk-driver-dashboard';
                }, 500);
                return; // Exit early, don't process other redirects
            }
        }
    }
    
    // Check if we have redirect information from boot
    if (frappe.boot && frappe.boot.tuktuk_redirect) {
        const targetUrl = frappe.boot.tuktuk_redirect;
        const currentPath = window.location.pathname;
        
        // Don't redirect if already on target page or login/logout pages
        if (currentPath === targetUrl || 
            currentPath.includes('/login') || 
            currentPath.includes('/logout') ||
            currentPath.includes('/update-password')) {
            return;
        }
        
        // Only redirect from main app pages
        if (currentPath === '/app' || 
            currentPath === '/app/' || 
            currentPath === '/desk' ||
            currentPath === '/app/home') {
            
            console.log(`TukTuk Redirect: ${frappe.boot.tuktuk_redirect_role} → ${targetUrl}`);
            
            // Small delay to ensure page is fully loaded
            setTimeout(function() {
                window.location.href = targetUrl;
            }, 500);
        }
    }
}

// Alternative approach using frappe's ready event
frappe.ready(function() {
    // Check user roles for redirect
    if (frappe.user_roles) {
        const currentPath = window.location.pathname;
        
        // Don't redirect if already on correct page or special pages
        if (currentPath.includes('/login') || 
            currentPath.includes('/logout') ||
            currentPath.includes('/update-password')) {
            return;
        }
        
        // TukTuk Driver redirect (HIGHEST PRIORITY - check this first)
        // Drivers should ALWAYS go to dashboard, regardless of other roles
        if (frappe.user_roles.includes('TukTuk Driver')) {
            if (!currentPath.includes('/tuktuk-driver-dashboard')) {
                // Redirect from any app page to driver dashboard
                if (currentPath === '/app' || 
                    currentPath === '/app/' || 
                    currentPath === '/desk' ||
                    currentPath === '/app/home' ||
                    currentPath.startsWith('/app/tuktuk-management')) {
                    console.log('TukTuk Driver redirect: redirecting to dashboard');
                    setTimeout(function() {
                        window.location.href = '/tuktuk-driver-dashboard';
                    }, 300);
                }
            }
        }
        // TukTuk Manager redirect (only if NOT a driver)
        else if (frappe.user_roles.includes('Tuktuk Manager')) {
            if (!currentPath.includes('/app/tuktuk-management')) {
                if (currentPath === '/app' || currentPath === '/app/' || currentPath === '/desk') {
                    setTimeout(function() {
                        window.location.href = '/app/tuktuk-management';
                    }, 300);
                }
            }
        }
    }
});

// Additional check for workspace redirects
$(document).on('app_ready', function() {
    // This runs after the desk is fully loaded
    // PRIORITY: Check if user is a TukTuk Driver first
    if (frappe.user_roles && frappe.user_roles.includes('TukTuk Driver')) {
        const currentPath = window.location.pathname;
        if (currentPath === '/app' && !currentPath.includes('/tuktuk-driver-dashboard')) {
            console.log('TukTuk Driver app_ready redirect: forcing redirect to dashboard');
            setTimeout(function() {
                window.location.href = '/tuktuk-driver-dashboard';
            }, 200);
            return; // Exit early
        }
    }
    
    // Otherwise, use boot redirect
    if (frappe.boot && frappe.boot.tuktuk_redirect && window.location.pathname === '/app') {
        setTimeout(function() {
            window.location.href = frappe.boot.tuktuk_redirect;
        }, 200);
    }
});