# ~/frappe-bench/apps/tuktuk_management/tuktuk_management/api/weekly_report.py

import frappe
from frappe.utils import getdate, add_days, flt
from datetime import datetime, timedelta

@frappe.whitelist()
def generate_weekly_report(week_start_date=None, week_end_date=None, save_to_db=True):
    """
    Generate a weekly report by aggregating data from Daily Report documents.
    
    Args:
        week_start_date: Start date of the week (YYYY-MM-DD). If None, defaults to last Sunday.
        week_end_date: End date of the week (YYYY-MM-DD). If None, defaults to Saturday of the same week.
        save_to_db: Whether to save the report to database (default: True)
    
    Returns:
        dict: Weekly report data
    """
    try:
        # Calculate week dates if not provided
        if not week_start_date:
            # Default to last Sunday (start of week)
            today = getdate()
            days_since_sunday = (today.weekday() + 1) % 7  # Monday=0, Sunday=6
            week_start_date = add_days(today, -days_since_sunday - 7)  # Last Sunday
        else:
            # Convert string to date if needed
            if isinstance(week_start_date, str):
                week_start_date = getdate(week_start_date)
            else:
                week_start_date = getdate(week_start_date)
        
        if not week_end_date:
            # End date is Saturday (6 days after Sunday)
            week_end_date = add_days(week_start_date, 6)
        else:
            # Convert string to date if needed
            if isinstance(week_end_date, str):
                week_end_date = getdate(week_end_date)
            else:
                week_end_date = getdate(week_end_date)
        
        # Validate date range
        if week_end_date < week_start_date:
            frappe.throw(f"week_end_date ({week_end_date}) cannot be before week_start_date ({week_start_date})")
        
        # Ensure we have date objects, not datetime
        week_start_date = getdate(week_start_date)
        week_end_date = getdate(week_end_date)
        
        # Get all daily reports for the week
        daily_reports = frappe.get_all(
            "TukTuk Daily Report",
            filters={
                "report_date": ["between", [week_start_date, week_end_date]]
            },
            fields=[
                "name", "report_date", "total_revenue", "total_driver_share",
                "total_target_contribution", "total_transactions",
                "drivers_at_target", "total_drivers", "target_achievement_rate",
                "inactive_drivers", "drivers_below_target", "drivers_below_target_list",
                "drivers_at_risk", "drivers_at_risk_list",
                "active_tuktuks", "available_tuktuks", "charging_tuktuks"
            ],
            order_by="report_date asc"
        )
        
        if not daily_reports:
            frappe.throw(f"No daily reports found for the week {week_start_date} to {week_end_date}")
        
        # Aggregate financial data
        total_revenue = sum(flt(dr.total_revenue or 0) for dr in daily_reports)
        total_driver_share = sum(flt(dr.total_driver_share or 0) for dr in daily_reports)
        total_target_contribution = sum(flt(dr.total_target_contribution or 0) for dr in daily_reports)
        total_transactions = sum(int(dr.total_transactions or 0) for dr in daily_reports)
        
        days_count = len(daily_reports)
        avg_daily_revenue = total_revenue / days_count if days_count > 0 else 0
        avg_daily_transactions = total_transactions / days_count if days_count > 0 else 0
        
        # Aggregate driver performance
        avg_drivers_at_target = sum(flt(dr.drivers_at_target or 0) for dr in daily_reports) / days_count if days_count > 0 else 0
        avg_total_drivers = sum(flt(dr.total_drivers or 0) for dr in daily_reports) / days_count if days_count > 0 else 0
        avg_target_achievement_rate = sum(flt(dr.target_achievement_rate or 0) for dr in daily_reports) / days_count if days_count > 0 else 0
        avg_inactive_drivers = sum(flt(dr.inactive_drivers or 0) for dr in daily_reports) / days_count if days_count > 0 else 0
        
        # Get unique drivers who worked during the week
        all_driver_lists = []
        for dr in daily_reports:
            if dr.drivers_below_target_list:
                drivers = [d.strip() for d in str(dr.drivers_below_target_list).split(",") if d.strip()]
                all_driver_lists.extend(drivers)
        
        unique_active_drivers = len(set(all_driver_lists)) if all_driver_lists else 0
        
        # Aggregate attention metrics
        drivers_below_target_this_week = len(set(
            d.strip() 
            for dr in daily_reports 
            if dr.drivers_below_target_list
            for d in str(dr.drivers_below_target_list).split(",")
            if d.strip()
        ))
        
        drivers_at_risk_this_week = len(set(
            d.strip()
            for dr in daily_reports
            if dr.drivers_at_risk_list
            for d in str(dr.drivers_at_risk_list).split(",")
            if d.strip()
        ))
        
        # Get unique lists
        all_below_target = set()
        for dr in daily_reports:
            if dr.drivers_below_target_list:
                drivers = [d.strip() for d in str(dr.drivers_below_target_list).split(",") if d.strip()]
                all_below_target.update(drivers)
        
        all_at_risk = set()
        for dr in daily_reports:
            if dr.drivers_at_risk_list:
                drivers = [d.strip() for d in str(dr.drivers_at_risk_list).split(",") if d.strip()]
                all_at_risk.update(drivers)
        
        drivers_below_target_list = ", ".join(sorted(all_below_target)) if all_below_target else ""
        drivers_at_risk_list = ", ".join(sorted(all_at_risk)) if all_at_risk else ""
        
        # Aggregate fleet status
        avg_active_tuktuks = sum(flt(dr.active_tuktuks or 0) for dr in daily_reports) / days_count if days_count > 0 else 0
        avg_available_tuktuks = sum(flt(dr.available_tuktuks or 0) for dr in daily_reports) / days_count if days_count > 0 else 0
        avg_charging_tuktuks = sum(flt(dr.charging_tuktuks or 0) for dr in daily_reports) / days_count if days_count > 0 else 0
        
        # Find best and worst performing days
        best_day = max(daily_reports, key=lambda x: flt(x.total_revenue or 0))
        worst_day = min(daily_reports, key=lambda x: flt(x.total_revenue or 0))
        
        best_performing_day = best_day.report_date
        best_day_revenue = flt(best_day.total_revenue or 0)
        worst_performing_day = worst_day.report_date
        worst_day_revenue = flt(worst_day.total_revenue or 0)
        
        # Days included
        days_included = ", ".join([str(dr.report_date) for dr in daily_reports])
        
        # Create daily target contributions breakdown
        daily_breakdown_lines = []
        for dr in sorted(daily_reports, key=lambda x: x.report_date, reverse=True):
            # Format date as DD-MM-YYYY
            date_str = dr.report_date.strftime("%d-%m-%Y") if hasattr(dr.report_date, 'strftime') else str(dr.report_date)
            total_drivers = int(dr.total_drivers or 0)
            target_contrib = flt(dr.total_target_contribution or 0)
            daily_breakdown_lines.append(f"{date_str} : {total_drivers} : Sh {target_contrib:,.0f}")
        
        daily_target_contributions_breakdown = "\n".join(daily_breakdown_lines)
        
        # Generate report text
        report_text = f"""
📊 SUNNY TUKTUK WEEKLY REPORT - {week_start_date} to {week_end_date}

💰 FINANCIAL SUMMARY:
- Total Weekly Revenue: {total_revenue:,.0f} KSH
- Total Weekly Driver Share: {total_driver_share:,.0f} KSH
- Total Weekly Target Contributions: {total_target_contribution:,.0f} KSH
- Total Weekly Transactions: {total_transactions}
- Average Daily Revenue: {avg_daily_revenue:,.0f} KSH
- Average Daily Transactions: {avg_daily_transactions:.1f}

👥 DRIVER PERFORMANCE:
- Average Drivers at Target: {avg_drivers_at_target:.1f}
- Average Total Drivers: {avg_total_drivers:.1f}
- Average Target Achievement Rate: {avg_target_achievement_rate:.1f}%
- Average Inactive Drivers: {avg_inactive_drivers:.1f}
- Unique Active Drivers (Week): {unique_active_drivers}

⚠️ NEEDS ATTENTION:
- Drivers Below Target This Week: {drivers_below_target_this_week}
- Drivers At Risk This Week: {drivers_at_risk_this_week}

🚗 FLEET STATUS:
- Average Active TukTuks: {avg_active_tuktuks:.1f}
- Average Available TukTuks: {avg_available_tuktuks:.1f}
- Average Charging TukTuks: {avg_charging_tuktuks:.1f}

📈 WEEKLY INSIGHTS:
- Best Performing Day: {best_performing_day} ({best_day_revenue:,.0f} KSH)
- Worst Performing Day: {worst_performing_day} ({worst_day_revenue:,.0f} KSH)
- Days Included: {days_included}
- Days Count: {days_count}
        """
        
        # Prepare return data
        report_data = {
            "week_start_date": week_start_date,
            "week_end_date": week_end_date,
            "total_revenue": total_revenue,
            "total_driver_share": total_driver_share,
            "total_target_contribution": total_target_contribution,
            "total_transactions": total_transactions,
            "avg_daily_revenue": avg_daily_revenue,
            "avg_daily_transactions": avg_daily_transactions,
            "avg_drivers_at_target": avg_drivers_at_target,
            "avg_total_drivers": avg_total_drivers,
            "avg_target_achievement_rate": avg_target_achievement_rate,
            "avg_inactive_drivers": avg_inactive_drivers,
            "unique_active_drivers": unique_active_drivers,
            "drivers_below_target_this_week": drivers_below_target_this_week,
            "drivers_below_target_list": drivers_below_target_list,
            "drivers_at_risk_this_week": drivers_at_risk_this_week,
            "drivers_at_risk_list": drivers_at_risk_list,
            "avg_active_tuktuks": avg_active_tuktuks,
            "avg_available_tuktuks": avg_available_tuktuks,
            "avg_charging_tuktuks": avg_charging_tuktuks,
            "best_performing_day": best_performing_day,
            "best_day_revenue": best_day_revenue,
            "worst_performing_day": worst_performing_day,
            "worst_day_revenue": worst_day_revenue,
            "days_included": days_included,
            "days_count": days_count,
            "daily_target_contributions_breakdown": daily_target_contributions_breakdown,
            "report_text": report_text
        }
        
        # Save to database if requested
        if save_to_db:
            try:
                # Check if report already exists for this week
                existing_report = frappe.db.exists(
                    "TukTuk Weekly Report",
                    {
                        "week_start_date": week_start_date,
                        "week_end_date": week_end_date
                    }
                )
                
                if existing_report:
                    weekly_report = frappe.get_doc("TukTuk Weekly Report", existing_report)
                else:
                    weekly_report = frappe.new_doc("TukTuk Weekly Report")
                
                # Set all fields
                weekly_report.week_start_date = week_start_date
                weekly_report.week_end_date = week_end_date
                weekly_report.total_revenue = total_revenue
                weekly_report.total_driver_share = total_driver_share
                weekly_report.total_target_contribution = total_target_contribution
                weekly_report.total_transactions = total_transactions
                weekly_report.avg_daily_revenue = avg_daily_revenue
                weekly_report.avg_daily_transactions = avg_daily_transactions
                weekly_report.avg_drivers_at_target = avg_drivers_at_target
                weekly_report.avg_total_drivers = avg_total_drivers
                weekly_report.avg_target_achievement_rate = avg_target_achievement_rate
                weekly_report.avg_inactive_drivers = avg_inactive_drivers
                weekly_report.unique_active_drivers = unique_active_drivers
                weekly_report.drivers_below_target_this_week = drivers_below_target_this_week
                weekly_report.drivers_below_target_list = drivers_below_target_list
                weekly_report.drivers_at_risk_this_week = drivers_at_risk_this_week
                weekly_report.drivers_at_risk_list = drivers_at_risk_list
                weekly_report.avg_active_tuktuks = avg_active_tuktuks
                weekly_report.avg_available_tuktuks = avg_available_tuktuks
                weekly_report.avg_charging_tuktuks = avg_charging_tuktuks
                weekly_report.best_performing_day = best_performing_day
                weekly_report.best_day_revenue = best_day_revenue
                weekly_report.worst_performing_day = worst_performing_day
                weekly_report.worst_day_revenue = worst_day_revenue
                weekly_report.days_included = days_included
                weekly_report.days_count = days_count
                weekly_report.daily_target_contributions_breakdown = daily_target_contributions_breakdown
                weekly_report.report_text = report_text
                weekly_report.generated_at = frappe.utils.now()
                
                weekly_report.save(ignore_permissions=True)
                frappe.db.commit()
                
                report_data["saved_to_db"] = True
                report_data["report_name"] = weekly_report.name
                
            except Exception as save_error:
                frappe.log_error(f"Failed to save weekly report: {str(save_error)}", "Weekly Report Save Error")
                report_data["saved_to_db"] = False
                report_data["save_error"] = str(save_error)
        
        return report_data
        
    except Exception as e:
        frappe.log_error(f"Failed to generate weekly report: {str(e)}", "Weekly Report Generation Error")
        frappe.throw(f"Failed to generate weekly report: {str(e)}")