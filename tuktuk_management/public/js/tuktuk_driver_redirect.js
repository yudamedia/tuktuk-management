// ~/frappe-bench/apps/tuktuk_management/tuktuk_management/public/js/tuktuk_driver_redirect.js

// Automatic redirect for TukTuk users based on roles - WITH STRICT PRIORITY
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
    const currentPath = window.location.pathname;
    
    // Don't redirect from special pages
    if (currentPath.includes('/login') ||
        currentPath.includes('/logout') ||
        currentPath.includes('/update-password')) {
        return;
    }
    
    // Check if we have boot info with redirect preference
    if (frappe.boot && frappe.boot.tuktuk_redirect) {
        const targetUrl = frappe.boot.tuktuk_redirect;
        const redirectRole = frappe.boot.tuktuk_redirect_role;
        
        // Only redirect if currently on a redirectable page
        const redirectablePages = [
            '/app',
            '/app/',
            '/desk',
            '/app/home',
            '/app/tuktuk-management'
        ];
        
        // Check if current path matches any redirectable page
        const shouldRedirect = redirectablePages.some(page => 
            currentPath === page || currentPath.startsWith(page + '/')
        );
        
        if (shouldRedirect) {
            // Special handling for TukTuk Driver - they should NEVER see management interface
            if (redirectRole === "TukTuk Driver" && !currentPath.includes('/driver/')) {
                console.log(`TukTuk Redirect: ${redirectRole} → ${targetUrl} (forced)`);
                setTimeout(function() {
                    window.location.href = targetUrl;
                }, 300);
                return;
            }
            
            // For managers/executives, only redirect if not already on management page
            if ((redirectRole === "Tuktuk Manager" || 
                 redirectRole === "Tuktuk Executive" || 
                 redirectRole === "System Manager") && 
                currentPath !== targetUrl) {
                
                // Don't redirect if already on the management workspace
                if (!currentPath.includes('/app/tuktuk-management')) {
                    console.log(`TukTuk Redirect: ${redirectRole} → ${targetUrl}`);
                    setTimeout(function() {
                        window.location.href = targetUrl;
                    }, 300);
                }
            }
        }
    }
    
    // Fallback: Direct role check (in case boot info is missing)
    // This provides redundancy in the redirect system
    if (frappe.user_roles && frappe.user_roles.length > 0) {
        // HIGHEST PRIORITY: TukTuk Driver
        if (frappe.user_roles.includes('TukTuk Driver')) {
            if (!currentPath.includes('/driver/') && 
                !currentPath.includes('/tuktuk-driver-dashboard')) {
                
                const redirectablePages = ['/app', '/app/', '/desk', '/app/home'];
                if (redirectablePages.some(page => currentPath === page || currentPath.startsWith(page + '/'))) {
                    console.log('TukTuk Driver fallback redirect: forcing to /driver/home');
                    setTimeout(function() {
                        window.location.href = '/driver/home';
                    }, 300);
                }
            }
            return; // Don't check other roles
        }
        
        // LOWER PRIORITY: Managers and Executives
        if (frappe.user_roles.includes('Tuktuk Executive') || 
            frappe.user_roles.includes('Tuktuk Manager') ||
            frappe.user_roles.includes('System Manager')) {
            
            if (currentPath === '/app' || currentPath === '/app/' || currentPath === '/desk') {
                console.log('Manager/Executive fallback redirect to /app/tuktuk-management');
                setTimeout(function() {
                    window.location.href = '/app/tuktuk-management';
                }, 300);
            }
        }
    }
}

// Additional safety: frappe.ready event handler
frappe.ready(function() {
    // Run redirect check again when frappe is fully ready
    handleTukTukRedirect();
});