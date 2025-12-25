# -*- coding: utf-8 -*-
"""
Balance Reconciliation Utilities

This module provides functions to detect and fix discrepancies in driver
balance calculations, particularly the left_to_target field.

Created: 2025-12-25
Purpose: Address left_to_target calculation discrepancies identified in production
"""

import frappe
from frappe.utils import flt, now_datetime, today


@frappe.whitelist()
def check_balance_discrepancies(auto_fix=False):
    """
    Check for discrepancies in driver balance calculations.
    
    Args:
        auto_fix: If True, automatically fix discrepancies found
        
    Returns:
        dict: Summary of discrepancies found and fixed
    """
    try:
        frappe.flags.ignore_permissions = True
        
        # Get global daily target for calculations
        settings = frappe.get_single("TukTuk Settings")
        global_target = flt(settings.global_daily_target or 0)
        
        # Query all active drivers
        drivers = frappe.db.sql("""
            SELECT 
                name,
                driver_name,
                daily_target,
                current_balance,
                left_to_target,
                assigned_tuktuk,
                GREATEST(
                    0,
                    COALESCE(NULLIF(daily_target, 0), %s) - current_balance
                ) as calculated_left_to_target
            FROM `tabTukTuk Driver`
            WHERE assigned_tuktuk != ''
              AND assigned_tuktuk IS NOT NULL
        """, (global_target,), as_dict=True)
        
        discrepancies = []
        fixed_count = 0
        
        for driver in drivers:
            expected_left = driver.calculated_left_to_target
            actual_left = flt(driver.left_to_target or 0)
            error = actual_left - expected_left
            
            if abs(error) > 0.01:  # More than 1 cent difference
                discrepancy_info = {
                    'driver_id': driver.name,
                    'driver_name': driver.driver_name,
                    'current_balance': driver.current_balance,
                    'actual_left_to_target': actual_left,
                    'expected_left_to_target': expected_left,
                    'error': error,
                    'effective_target': driver.daily_target or global_target
                }
                discrepancies.append(discrepancy_info)
                
                # Log the discrepancy
                frappe.log_error(
                    f"""Balance Discrepancy Detected

Driver: {driver.driver_name} ({driver.name})
Current Balance: {driver.current_balance}
Expected left_to_target: {expected_left}
Actual left_to_target: {actual_left}
Error: {error} KES
Effective Target: {driver.daily_target or global_target}

Auto-fix: {'YES' if auto_fix else 'NO'}
                    """,
                    "Balance Reconciliation - Discrepancy Found"
                )
                
                # Auto-fix if requested
                if auto_fix:
                    frappe.db.sql("""
                        UPDATE `tabTukTuk Driver`
                        SET left_to_target = %s
                        WHERE name = %s
                    """, (expected_left, driver.name))
                    fixed_count += 1
        
        if auto_fix and discrepancies:
            frappe.db.commit()
        
        # Create summary report
        summary = {
            'timestamp': now_datetime(),
            'total_drivers_checked': len(drivers),
            'discrepancies_found': len(discrepancies),
            'discrepancies_fixed': fixed_count,
            'total_error_amount': sum([abs(d['error']) for d in discrepancies]),
            'details': discrepancies
        }
        
        # Log summary
        frappe.log_error(
            f"""Balance Reconciliation Summary

Date: {today()}
Drivers Checked: {len(drivers)}
Discrepancies Found: {len(discrepancies)}
Discrepancies Fixed: {fixed_count}
Total Error Amount: {summary['total_error_amount']} KES

{'=' * 60}
Details:
{'=' * 60}
{format_discrepancy_table(discrepancies)}
            """,
            "Balance Reconciliation - Summary"
        )
        
        return summary
        
    except Exception as e:
        frappe.log_error(f"Balance reconciliation failed: {str(e)}", "Balance Reconciliation - Error")
        raise


@frappe.whitelist()
def fix_all_discrepancies():
    """
    Fix all balance discrepancies found in the system.
    
    Returns:
        dict: Summary of fixes applied
    """
    return check_balance_discrepancies(auto_fix=True)


@frappe.whitelist()
def get_driver_balance_report(driver_name):
    """
    Get detailed balance report for a specific driver.
    
    Args:
        driver_name: Driver ID (e.g., 'DRV-112011')
        
    Returns:
        dict: Detailed balance information
    """
    try:
        settings = frappe.get_single("TukTuk Settings")
        global_target = flt(settings.global_daily_target or 0)
        
        driver = frappe.db.get_value(
            "TukTuk Driver",
            driver_name,
            ["name", "driver_name", "daily_target", "current_balance", "left_to_target", "assigned_tuktuk"],
            as_dict=True
        )
        
        if not driver:
            frappe.throw(f"Driver {driver_name} not found")
        
        effective_target = driver.daily_target or global_target
        expected_left = max(0, effective_target - driver.current_balance)
        error = driver.left_to_target - expected_left
        
        # Get today's payments
        payments = frappe.db.sql("""
            SELECT 
                name,
                timestamp,
                amount,
                target_contribution,
                payment_status
            FROM `tabTukTuk Transaction`
            WHERE driver = %s
              AND DATE(timestamp) = CURDATE()
            ORDER BY timestamp
        """, (driver_name,), as_dict=True)
        
        return {
            'driver_id': driver.name,
            'driver_name': driver.driver_name,
            'assigned_tuktuk': driver.assigned_tuktuk,
            'effective_target': effective_target,
            'current_balance': driver.current_balance,
            'actual_left_to_target': driver.left_to_target,
            'expected_left_to_target': expected_left,
            'error': error,
            'is_correct': abs(error) <= 0.01,
            'todays_payments': payments,
            'payment_count': len(payments),
            'total_earned_today': sum([flt(p.target_contribution) for p in payments])
        }
        
    except Exception as e:
        frappe.log_error(f"Failed to generate driver balance report: {str(e)}")
        raise


def format_discrepancy_table(discrepancies):
    """Format discrepancies as a readable table"""
    if not discrepancies:
        return "No discrepancies found"
    
    lines = []
    lines.append(f"{'Driver':<30} {'Balance':>10} {'Expected':>10} {'Actual':>10} {'Error':>10}")
    lines.append("-" * 75)
    
    for d in discrepancies:
        lines.append(
            f"{d['driver_name']:<30} "
            f"{d['current_balance']:>10.2f} "
            f"{d['expected_left_to_target']:>10.2f} "
            f"{d['actual_left_to_target']:>10.2f} "
            f"{d['error']:>10.2f}"
        )
    
    return "\n".join(lines)


def scheduled_reconciliation():
    """
    Scheduled task to check for balance discrepancies.
    Should be run via cron/scheduler.
    
    This function only logs discrepancies - does NOT auto-fix.
    Manual intervention required for fixes.
    """
    try:
        result = check_balance_discrepancies(auto_fix=False)
        
        if result['discrepancies_found'] > 0:
            # Send notification if discrepancies found
            frappe.log_error(
                f"""⚠️ ATTENTION REQUIRED: Balance Discrepancies Detected

{result['discrepancies_found']} driver(s) have balance calculation errors.
Total discrepancy amount: {result['total_error_amount']} KES

Please review the "Balance Reconciliation - Summary" error log for details.

To fix automatically, run:
bench --site {frappe.local.site} execute tuktuk_management.api.balance_reconciliation.fix_all_discrepancies
                """,
                "Balance Reconciliation - Alert"
            )
        
        return result
        
    except Exception as e:
        frappe.log_error(f"Scheduled reconciliation failed: {str(e)}")
        raise
