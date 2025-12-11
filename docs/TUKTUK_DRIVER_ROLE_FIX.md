# TukTuk Driver Role Fix

## Problem Identified

The system had a role naming inconsistency:
- **Created role**: "Driver" (in `setup/install.py` and patches)
- **Expected role**: "TukTuk Driver" (in `driver_auth.py`, `boot.py`, dashboard, etc.)

This caused:
- Driver account creation to fail or assign wrong role
- Driver dashboard access checks to fail
- Automatic redirects for drivers not to work

## Solution Implemented

Created two patches to fix the issue:

### 1. `create_tuktuk_driver_role.py`
Creates the "TukTuk Driver" role with:
- Desk access enabled
- Notifications enabled
- Proper description
- Custom role flag

Also:
- Migrates existing users with "Driver" role to "TukTuk Driver" role
- Adds permissions to relevant doctypes

### 2. `fix_tuktuk_driver_permissions.py`
Corrects the permissions to be read-only (as intended):
- **TukTuk Vehicle**: Read only
- **TukTuk Driver**: Read only
- **TukTuk Transaction**: Read only
- **TukTuk Rental**: Read + Create (allows drivers to request rentals)
- **TukTuk Settings**: Read only

## Current State

Both roles now exist in the system:
- **Driver**: Original role (kept for backwards compatibility)
- **TukTuk Driver**: New role with correct naming

### TukTuk Driver Role Permissions

| DocType | Read | Write | Create | Delete |
|---------|------|-------|--------|--------|
| TukTuk Vehicle | ✅ | ❌ | ❌ | ❌ |
| TukTuk Driver | ✅ | ❌ | ❌ | ❌ |
| TukTuk Transaction | ✅ | ❌ | ❌ | ❌ |
| TukTuk Rental | ✅ | ❌ | ✅ | ❌ |
| TukTuk Settings | ✅ | ❌ | ❌ | ❌ |

## Files Modified

1. **Created**: `tuktuk_management/patches/create_tuktuk_driver_role.py`
2. **Created**: `tuktuk_management/patches/fix_tuktuk_driver_permissions.py`
3. **Updated**: `tuktuk_management/patches.txt` (added both patches)

## How It Works

### Driver Account Creation
When managers create a driver account via `create_tuktuk_driver_user_account()`:
```python
user = frappe.get_doc({
    "doctype": "User",
    "email": user_email,
    "roles": [
        {"role": "TukTuk Driver"}  # Now this role exists!
    ]
})
```

### Driver Dashboard Access
When drivers log in:
1. `boot.py` checks for "TukTuk Driver" role
2. Redirects to `/tuktuk-driver-dashboard`
3. Dashboard verifies "TukTuk Driver" role
4. Shows personalized driver interface

### Driver Permissions
Drivers can:
- ✅ View their own driver record
- ✅ View their assigned vehicle
- ✅ View their transactions
- ✅ Request TukTuk rentals
- ✅ View operating settings
- ❌ Cannot edit or delete anything
- ❌ Cannot view other drivers' data

## Migration Status

✅ **Completed**: Patches executed successfully on `console.sunnytuktuk.com`

### Verification Commands

Check role exists:
```bash
bench --site console.sunnytuktuk.com mariadb -e "SELECT * FROM \`tabRole\` WHERE role_name = 'TukTuk Driver';"
```

Check permissions:
```bash
bench --site console.sunnytuktuk.com mariadb -e "SELECT parent, \`read\`, \`write\`, \`create\`, \`delete\` FROM \`tabDocPerm\` WHERE role = 'TukTuk Driver';"
```

## Next Steps

1. **Test driver account creation**: Create a new driver user account
2. **Test driver login**: Verify automatic redirect to dashboard
3. **Test driver permissions**: Ensure read-only access works correctly
4. **Monitor**: Check for any role-related errors in logs

## Backwards Compatibility

The original "Driver" role is kept to ensure:
- Existing references continue to work
- No breaking changes for custom code
- Smooth transition period

Future updates should standardize on "TukTuk Driver" throughout the codebase.

