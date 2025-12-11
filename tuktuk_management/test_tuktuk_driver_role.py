#!/usr/bin/env python3
"""
Test script to verify TukTuk Driver role is properly configured
Run with: bench --site console.sunnytuktuk.com execute tuktuk_management.test_tuktuk_driver_role.test_role
"""

import frappe

def test_role():
    """Test that TukTuk Driver role exists and has correct permissions"""
    
    print("\n" + "="*60)
    print("TukTuk Driver Role Verification Test")
    print("="*60 + "\n")
    
    # Test 1: Check if role exists
    print("Test 1: Checking if TukTuk Driver role exists...")
    if frappe.db.exists('Role', 'TukTuk Driver'):
        print("✅ PASS: TukTuk Driver role exists")
        
        role = frappe.get_doc('Role', 'TukTuk Driver')
        print(f"   - Role Name: {role.role_name}")
        print(f"   - Desk Access: {role.desk_access}")
        print(f"   - Is Custom: {role.is_custom}")
    else:
        print("❌ FAIL: TukTuk Driver role does not exist")
        return False
    
    # Test 2: Check permissions
    print("\nTest 2: Checking permissions...")
    expected_permissions = {
        'TukTuk Vehicle': {'read': 1, 'create': 0},
        'TukTuk Driver': {'read': 1, 'create': 0},
        'TukTuk Transaction': {'read': 1, 'create': 0},
        'TukTuk Rental': {'read': 1, 'create': 1},
        'TukTuk Settings': {'read': 1, 'create': 0},
    }
    
    all_perms_correct = True
    for doctype, expected in expected_permissions.items():
        perms = frappe.get_all('DocPerm', 
                               filters={'parent': doctype, 'role': 'TukTuk Driver'},
                               fields=['read', 'write', 'create', 'delete'])
        
        if perms:
            perm = perms[0]
            read_ok = perm.read == expected['read']
            create_ok = perm.create == expected['create']
            write_ok = perm.write == 0  # Should always be 0
            delete_ok = perm.delete == 0  # Should always be 0
            
            if read_ok and create_ok and write_ok and delete_ok:
                print(f"✅ {doctype}: Correct (R:{perm.read}, W:{perm.write}, C:{perm.create}, D:{perm.delete})")
            else:
                print(f"❌ {doctype}: Incorrect (R:{perm.read}, W:{perm.write}, C:{perm.create}, D:{perm.delete})")
                all_perms_correct = False
        else:
            print(f"❌ {doctype}: No permissions found")
            all_perms_correct = False
    
    if all_perms_correct:
        print("\n✅ PASS: All permissions are correct")
    else:
        print("\n❌ FAIL: Some permissions are incorrect")
        return False
    
    # Test 3: Check if both roles exist
    print("\nTest 3: Checking for both Driver and TukTuk Driver roles...")
    driver_exists = frappe.db.exists('Role', 'Driver')
    tuktuk_driver_exists = frappe.db.exists('Role', 'TukTuk Driver')
    
    if driver_exists and tuktuk_driver_exists:
        print("✅ PASS: Both 'Driver' and 'TukTuk Driver' roles exist (backwards compatibility)")
    else:
        print(f"⚠️  WARNING: Driver={driver_exists}, TukTuk Driver={tuktuk_driver_exists}")
    
    # Final summary
    print("\n" + "="*60)
    print("✅ ALL TESTS PASSED - TukTuk Driver role is properly configured")
    print("="*60 + "\n")
    
    return True

if __name__ == "__main__":
    test_role()

