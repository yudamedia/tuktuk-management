# Hailing Availability Toggle Button - Driver Dashboard

## Overview
Add an iOS-style toggle switch to the driver home page that allows drivers to toggle their availability for hailing rides. The button will:
- ✅ Be placed prominently at the top of the page (after header, before quick stats)
- ✅ Use existing `tuktuk_hailing` API (`set_driver_availability`)
- ✅ Start/stop GPS tracking when toggling online/offline
- ✅ Show clear visual states (Green = Online, Gray = Offline)
- ✅ Be disabled when driver has no assigned TukTuk

## Critical Files to Modify

### 1. HTML Structure
**File:** `apps/tuktuk_management/tuktuk_management/www/driver_home.html`
- **Insert location:** After line 8 (`{% else %}`), before line 9 (Quick Stats section)
- **Add:** Hailing toggle card with iOS-style switch, status indicator, loading overlay, and error messages
- **Structure:** Card container → Status info (icon + text) → Toggle switch → Loading/Error overlays

### 2. CSS Styling
**File:** `apps/tuktuk_management/tuktuk_management/public/css/driver_dashboard.css`
- **Insert location:** At end of file (after existing styles)
- **Add:** ~150 lines of CSS for:
  - Card styling with online/offline states (green/gray borders and backgrounds)
  - iOS-style toggle switch (60px × 34px with animated slider)
  - Loading overlay with spinner
  - Error/warning message styling
  - Responsive adjustments for mobile (<480px)
  - Disabled state styling

### 3. JavaScript Logic
**File:** `apps/tuktuk_management/tuktuk_management/public/js/driver_dashboard.js`
- **Insert location:** At end of file (before closing `})();`)
- **Add:** ~350 lines of JavaScript for:
  - Initialize toggle with current hailing status
  - Handle toggle clicks → call `set_driver_availability` API
  - Start/stop GPS tracking (10-second intervals when online)
  - Update driver location via `update_driver_location` API
  - Handle errors (no TukTuk, network errors, GPS permission denied)
  - Update UI states (online/offline, loading, error messages)
  - Auto-refresh status every 30 seconds

### 4. Python Backend
**File:** `apps/tuktuk_management/tuktuk_management/www/driver_home.py`
- **Modify:** `get_context()` function (lines 26-48)
- **Add:** Fetch `hailing_status` from TukTuk Driver doctype
- **Pass to template:** Include `hailing_status` in context for initial UI state

**Optional - New API endpoint:**
**File:** `apps/tuktuk_management/tuktuk_management/api/driver_auth.py`
- **Add:** `get_driver_hailing_status()` function (whitelisted API)
- **Purpose:** Lightweight endpoint to fetch just hailing status for auto-refresh

### 5. Existing API (Reference Only - No Changes)
**File:** `apps/tuktuk_hailing/tuktuk_hailing/api/location.py`
- **Line 135-168:** `set_driver_availability(driver_id, available)` - API endpoint we'll call
- **Line 8-68:** `update_driver_location()` - GPS location update API

## Implementation Details

### HTML Addition (driver_home.html, after line 8)

```html
<!-- Hailing Availability Toggle Card -->
<div class="card hailing-toggle-card" id="hailing-availability-card">
    <div class="hailing-toggle-container">
        <div class="hailing-status-info">
            <div class="hailing-icon" id="hailing-icon">
                <!-- Location/Hailing icon SVG -->
            </div>
            <div class="hailing-status-text">
                <div class="hailing-label">Hailing Status</div>
                <div class="hailing-status-value" id="hailing-status-text">{{ hailing_status or "Offline" }}</div>
            </div>
        </div>

        <!-- iOS-style Toggle Switch -->
        <label class="toggle-switch">
            <input type="checkbox" id="hailing-toggle"
                   {% if hailing_status == "Available" %}checked{% endif %}
                   {% if not tuktuk %}disabled{% endif %}>
            <span class="toggle-slider"></span>
        </label>
    </div>

    <div class="hailing-loading-overlay" id="hailing-loading" style="display: none;">
        <div class="spinner"></div><span>Updating...</span>
    </div>

    <div class="hailing-error-message" id="hailing-error" style="display: none;"></div>

    {% if not tuktuk %}
    <div class="hailing-warning">
        <span>You need an assigned TukTuk to go online for hailing</span>
    </div>
    {% endif %}
</div>
```

### CSS Key Styles (driver_dashboard.css, append)

```css
/* Hailing Toggle Card - Online/Offline states */
.hailing-toggle-card.online {
    border-color: var(--success-color);
    background: linear-gradient(135deg, #f0fff4, #e6ffed);
}

.hailing-toggle-card.offline {
    border-color: #adb5bd;
    background: linear-gradient(135deg, #ffffff, #f8f9fa);
}

/* iOS-style Toggle Switch */
.toggle-switch {
    width: 60px;
    height: 34px;
}

.toggle-slider {
    background-color: #ccc;
    border-radius: 34px;
    transition: all 0.4s;
}

.toggle-slider:before {
    width: 26px;
    height: 26px;
    background-color: white;
    border-radius: 50%;
    transition: all 0.4s;
}

.toggle-switch input:checked + .toggle-slider {
    background-color: var(--success-color);
}

.toggle-switch input:checked + .toggle-slider:before {
    transform: translateX(26px);
}
```

### JavaScript Key Functions (driver_dashboard.js, append)

```javascript
// Initialize toggle on page load
function initHailingToggle() {
    const toggle = document.getElementById('hailing-toggle');
    toggle.addEventListener('change', handleHailingToggle);
    fetchDriverHailingStatus(); // Get current status
    setInterval(fetchDriverHailingStatus, 30000); // Refresh every 30s
}

// Handle toggle click
async function handleHailingToggle(event) {
    const isGoingOnline = event.target.checked;

    // Validate TukTuk assignment
    if (!currentDriverData?.tuktuk) {
        event.target.checked = false;
        showHailingError('You need an assigned TukTuk to go online');
        return;
    }

    showHailingLoading(true);

    try {
        // Get driver ID
        const driverResponse = await frappe.call({
            method: 'tuktuk_management.api.driver_auth.get_current_tuktuk_driver'
        });

        // Call availability API
        const result = await frappe.call({
            method: 'tuktuk_hailing.api.location.set_driver_availability',
            args: {
                driver_id: driverResponse.message.name,
                available: isGoingOnline
            }
        });

        if (result.message.success) {
            updateToggleUI(result.message.status);

            if (result.message.status === 'Available') {
                startGPSTracking(driverResponse.message.name);
                showHailingSuccess('You are now online!');
            } else {
                stopGPSTracking();
                showHailingSuccess('You are now offline');
            }
        }
    } catch (error) {
        event.target.checked = !isGoingOnline; // Revert
        showHailingError(error.message);
    } finally {
        showHailingLoading(false);
    }
}

// GPS Tracking
function startGPSTracking(driverId) {
    navigator.geolocation.getCurrentPosition(
        (position) => {
            updateDriverLocation(driverId, position);

            gpsTrackingInterval = setInterval(() => {
                navigator.geolocation.getCurrentPosition(
                    (pos) => updateDriverLocation(driverId, pos)
                );
            }, 10000); // Every 10 seconds
        },
        (error) => {
            showHailingError('GPS permission denied');
        }
    );
}

function stopGPSTracking() {
    if (gpsTrackingInterval) {
        clearInterval(gpsTrackingInterval);
        gpsTrackingInterval = null;
    }
}

// Initialize when page loads
document.addEventListener('DOMContentLoaded', initHailingToggle);
```

### Python Backend Changes (driver_home.py, lines 26-48)

```python
# Get hailing_status from driver record
hailing_status = "Offline"
if tuktuk_driver:
    driver = tuktuk_driver[0]
    context.driver_name = driver.driver_name
    context.current_deposit_balance = driver.current_deposit_balance or 0
    context.left_to_target = driver.left_to_target or 0

    # NEW: Fetch hailing_status
    driver_doc = frappe.get_doc("TukTuk Driver", driver.name)
    hailing_status = driver_doc.get("hailing_status", "Offline")
else:
    context.driver_name = "Driver"
    context.current_deposit_balance = 0
    context.left_to_target = 0

context.update({
    # ... existing fields ...
    "hailing_status": hailing_status  # NEW: Add to context
})
```

## Implementation Sequence

### Phase 1: HTML & CSS (30 min)
1. Add HTML structure to `driver_home.html` (after line 8)
2. Add CSS styles to `driver_dashboard.css` (at end)
3. Clear cache: `bench clear-cache`
4. Test visual appearance (static, no functionality)

### Phase 2: Python Backend (15 min)
5. Modify `driver_home.py` to pass `hailing_status` to template
6. (Optional) Add `get_driver_hailing_status()` API to `driver_auth.py`
7. Test that hailing_status appears correctly in template

### Phase 3: JavaScript Core (45 min)
8. Add initialization and toggle handler to `driver_dashboard.js`
9. Implement API calls to `set_driver_availability`
10. Implement UI update functions
11. Test toggle functionality end-to-end

### Phase 4: GPS Integration (30 min)
12. Implement GPS tracking start/stop functions
13. Implement location update API calls
14. Test GPS permission and location updates

### Phase 5: Error Handling & Polish (30 min)
15. Add all error handlers (no TukTuk, network errors, GPS denied)
16. Add loading states and animations
17. Test all edge cases

### Phase 6: Testing (30 min)
18. Full functional testing on mobile and desktop
19. Test GPS tracking and location updates
20. Verify database updates (TukTuk Driver.hailing_status, Driver Location)

**Total Estimated Time:** 3 hours

## Testing Checklist

- [ ] Toggle switches from Offline → Online correctly
- [ ] Toggle switches from Online → Offline correctly
- [ ] API call to `set_driver_availability` succeeds
- [ ] Database field `hailing_status` updates correctly
- [ ] GPS tracking starts when going online (permission prompt)
- [ ] Location updates every 10 seconds while online
- [ ] GPS tracking stops when going offline
- [ ] Toggle disabled when no TukTuk assigned
- [ ] Warning message shown when no TukTuk
- [ ] Error message shown when API fails
- [ ] Loading overlay appears during API call
- [ ] Visual states clear (green=online, gray=offline)
- [ ] Works on mobile Safari (iOS)
- [ ] Works on Chrome (Android)
- [ ] Status persists across page refreshes
- [ ] Auto-refresh updates status every 30 seconds

## Edge Cases Handled

1. **No assigned TukTuk:** Toggle disabled, warning message shown
2. **Network error:** Error message, toggle reverts to previous state
3. **GPS permission denied:** Error message, tracking fails gracefully
4. **Browser doesn't support GPS:** Warning shown, toggle still works
5. **Already "En Route":** API prevents going offline, error shown
6. **Session timeout:** Frappe redirects to login automatically
7. **Multiple rapid clicks:** Loading overlay prevents concurrent API calls

## Key Dependencies

- `tuktuk_hailing` app must be installed and in the bench
- `set_driver_availability` API at `tuktuk_hailing.api.location`
- `update_driver_location` API at `tuktuk_hailing.api.location`
- Browser geolocation API support
- Active driver session (logged in with "TukTuk Driver" role)

## Rollback Plan

**Quick hide toggle:**
```css
.hailing-toggle-card { display: none !important; }
```

**Full rollback:**
1. Revert HTML changes in `driver_home.html`
2. Revert CSS changes in `driver_dashboard.css`
3. Revert JavaScript changes in `driver_dashboard.js`
4. Revert Python changes in `driver_home.py`
5. Run `bench clear-cache && bench restart`
