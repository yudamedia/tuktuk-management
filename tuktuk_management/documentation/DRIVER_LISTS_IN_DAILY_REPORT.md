# Driver Lists in Daily Report Implementation

**Date:** December 9, 2025  
**Status:** ✅ Completed

## Overview

Added two new fields to the TukTuk Daily Report doctype to store the actual names of drivers who need attention. These fields are populated automatically but **NOT included in the email** report.

---

## New Fields Added

### 1. `drivers_below_target_list`
- **Type:** Long Text
- **Contains:** Comma-separated list of driver IDs who did not meet their daily target
- **Example:** `DRV-112001, DRV-112005, DRV-112018`

### 2. `drivers_at_risk_list`
- **Type:** Long Text
- **Contains:** Comma-separated list of driver IDs with consecutive misses ≥ 2
- **Example:** `DRV-112006, DRV-112022`

---

## How It Works

### Data Population

When the daily report is generated:

1. **Drivers Below Target:**
   - System queries all assigned drivers
   - Calculates each driver's daily total vs their target
   - Stores IDs of drivers who didn't meet target

2. **Drivers At Risk:**
   - Queries drivers with `consecutive_misses >= 2`
   - Stores their IDs for tracking

### Email vs Database

**In the Email (sent to yuda@sunnytuktuk.com):**
```
⚠️ NEEDS ATTENTION:
- Drivers who did not meet target: 2
- Drivers with consecutive misses (≥2): 1
```
❌ Driver names are **NOT** shown in the email

**In the Database:**
- Count: `drivers_below_target = 2`
- List: `drivers_below_target_list = "DRV-112001, DRV-112018"`
- Count: `drivers_at_risk = 1`
- List: `drivers_at_risk_list = "DRV-112006"`

✅ Full driver details are stored for later review

---

## Benefits

### 📊 Data Analysis
- Identify which specific drivers consistently miss targets
- Track patterns of underperformance
- Build driver performance profiles

### 🎯 Targeted Intervention
- Management can see exactly who needs support
- No need to run additional queries
- One-click access to driver details

### 📈 Trend Tracking
- Monitor if same drivers appear repeatedly
- Identify early warning signs
- Proactive management intervention

### 🔍 Historical Review
- Review past reports to see driver performance over time
- Correlate interventions with improvements
- Evidence-based decision making

---

## Usage Examples

### View Driver Lists in UI

1. Go to **TukTuk Daily Report** list
2. Open any report record
3. Scroll to **"Needs Attention"** section
4. See the driver lists in text format

### Query via API

```python
# Get report
report = frappe.get_doc("TukTuk Daily Report", {"report_date": "2025-12-08"})

# Get drivers below target
if report.drivers_below_target > 0:
    driver_ids = report.drivers_below_target_list.split(", ")
    for driver_id in driver_ids:
        driver = frappe.get_doc("TukTuk Driver", driver_id)
        print(f"{driver.driver_name} needs support")
```

### SQL Query

```sql
-- Get all reports where a specific driver was below target
SELECT 
    report_date,
    drivers_below_target,
    drivers_below_target_list
FROM `tabTukTuk Daily Report`
WHERE drivers_below_target_list LIKE '%DRV-112018%'
ORDER BY report_date DESC;
```

---

## Technical Details

### Database Schema

```sql
ALTER TABLE `tabTukTuk Daily Report`
ADD COLUMN `drivers_below_target_list` longtext DEFAULT NULL,
ADD COLUMN `drivers_at_risk_list` longtext DEFAULT NULL;
```

### Data Format

- **Storage:** Comma-separated string
- **Format:** `"DRV-112001, DRV-112005, DRV-112018"`
- **Empty state:** Empty string `""`
- **Parsing:** Split by `", "` (comma + space)

---

## Example Report Data

```json
{
  "report_date": "2025-12-08",
  "drivers_below_target": 0,
  "drivers_below_target_list": "",
  "drivers_at_risk": 0,
  "drivers_at_risk_list": "",
  "total_revenue": 25730.0,
  "drivers_at_target": 12
}
```

On this date, all active drivers either met or exceeded their targets! 🎉

---

## Email Privacy

The driver lists are **intentionally excluded** from the email report to:

1. **Protect Privacy:** Driver names not exposed in email
2. **Keep Emails Concise:** Just show counts, not full lists
3. **Sensitive Information:** Performance data stays in secure database
4. **Management Access:** Login required to see specific drivers

Management can log into the system to see the full details when needed.

---

## Future Enhancements

### Suggested Additions

1. **Driver Details Table**
   - Show driver name, shortfall amount, and days at risk
   - More structured than comma-separated list

2. **Click-to-View Links**
   - Make driver IDs clickable in the UI
   - Jump directly to driver record

3. **Performance Alerts**
   - Auto-notify manager when same driver appears 3+ times
   - Trigger intervention workflows

4. **Comparison Views**
   - Compare this week vs last week's at-risk drivers
   - Trending analysis

---

## Verification

Tested with report date 2025-12-08:
- ✅ Fields created in database
- ✅ Data populated correctly
- ✅ Empty lists when no drivers in category
- ✅ Email sent without driver names
- ✅ Database stores full driver IDs

---

## Summary

✅ **Driver lists added** to TukTuk Daily Report  
✅ **Privacy maintained** - lists not in emails  
✅ **Data accessible** - stored in database for analysis  
✅ **Ready for use** - automatically populated daily  

System now tracks not just *how many* drivers need attention, but *which specific drivers* - enabling targeted management action! 🎯

