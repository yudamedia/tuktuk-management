# TukTuk Roster System Implementation Guide

## Overview
This guide provides step-by-step instructions to implement the Weekly Days-Off Roster system for the Sunny TukTuk Management System.

## System Requirements
- ERPNext 15
- Existing TukTuk Management app installed
- 15 Regular Drivers (TukTuk Driver DocType)
- 3 Substitute Drivers (TukTuk Substitute Driver DocType)
- SMS gateway configured (TextBee, TextSMS, or httpSMS)

## Features Implemented
1. **Bi-weekly roster generation** (14-day periods)
2. **Driver day-off preferences** with special requests support
3. **Automatic substitute assignment** when regular drivers are off
4. **Day-off switch requests** with SMS notifications
5. **Sick day tracking**
6. **Sunday staffing rules** (minimum 9 drivers, max offs flexible)
7. **Management override capabilities**
8. **Integration with performance tracking** (scheduled offs don't count as missed targets)

---

## Installation Steps

### Step 1: Create New DocTypes

You need to create 3 new DocTypes in the TukTuk Management module.

#### 1.1 Create TukTuk Roster Period DocType

```bash
cd ~/frappe-bench/apps/tuktuk_management/tuktuk_management/tuktuk_management/doctype
mkdir tuktuk_roster_period
cd tuktuk_roster_period
```

Create the files:
- Copy `tuktuk_roster_period.json` from the generated files
- Copy `tuktuk_roster_period.py` from the generated files
- Create empty `__init__.py`

```bash
touch __init__.py
```

#### 1.2 Create TukTuk Day Off Schedule DocType (Child Table)

```bash
cd ~/frappe-bench/apps/tuktuk_management/tuktuk_management/tuktuk_management/doctype
mkdir tuktuk_day_off_schedule
cd tuktuk_day_off_schedule
```

Create the files:
- Copy `tuktuk_day_off_schedule.json` from the generated files
- Create empty `tuktuk_day_off_schedule.py`:

```python
from frappe.model.document import Document

class TukTukDayOffSchedule(Document):
	pass
```

- Create empty `__init__.py`

#### 1.3 Create TukTuk Substitute Assignment DocType (Child Table)

```bash
cd ~/frappe-bench/apps/tuktuk_management/tuktuk_management/tuktuk_management/doctype
mkdir tuktuk_substitute_assignment
cd tuktuk_substitute_assignment
```

Create the files:
- Copy `tuktuk_substitute_assignment.json` from the generated files
- Create empty `tuktuk_substitute_assignment.py`:

```python
from frappe.model.document import Document

class TukTukSubstituteAssignment(Document):
	pass
```

- Create empty `__init__.py`

### Step 2: Add Roster API

Create the roster API file:

```bash
cd ~/frappe-bench/apps/tuktuk_management/tuktuk_management/api
```

Copy `roster.py` from the generated files to this directory.

### Step 3: Update Existing Driver DocTypes

Add `preferred_day_off` field to both TukTuk Driver and TukTuk Substitute Driver.

Run the setup script from bench console:

```bash
cd ~/frappe-bench
bench --site sunnytuktuk.com console
```

Then in the console:

```python
exec(open('/path/to/add_roster_fields.py').read())
```

Or manually add the field using Customize Form:
1. Go to Customize Form
2. Select DocType: TukTuk Driver
3. Add new field:
   - Label: Preferred Day Off
   - Type: Select
   - Options: MONDAY\nTUESDAY\nWEDNESDAY\nTHURSDAY\nFRIDAY\nSATURDAY\nSUNDAY\nNo Preference
4. Save

Repeat for TukTuk Substitute Driver.

### Step 4: Import Driver Preferences

Run the preference import script from bench console:

```python
import frappe
from tuktuk_management.setup.add_roster_fields import import_driver_preferences_from_csv

import_driver_preferences_from_csv()
```

This will set the preferred days off for all drivers based on the CSV data.

### Step 5: Migrate DocTypes

After creating all files, run:

```bash
cd ~/frappe-bench
bench --site sunnytuktuk.com migrate
```

This will create the database tables for the new DocTypes.

### Step 6: Set Permissions

Set permissions for the new DocTypes:

**TukTuk Roster Period:**
- System Manager: Full access
- Tuktuk Manager: Read only
- Driver: Read only

**TukTuk Day Off Schedule & TukTuk Substitute Assignment:**
- These are child tables, permissions inherit from parent

### Step 7: Clear Cache

```bash
bench --site sunnytuktuk.com clear-cache
bench --site sunnytuktuk.com clear-website-cache
```

---

## Usage Guide

### Generating the First Roster (Dec 19 - Jan 1, 2025)

From bench console:

```python
import frappe
from tuktuk_management.tuktuk_management.doctype.tuktuk_roster_period.tuktuk_roster_period import generate_roster

# Generate first roster
result = generate_roster('2024-12-19', '2025-01-01')
print(result)

# Activate the roster
from tuktuk_management.tuktuk_management.doctype.tuktuk_roster_period.tuktuk_roster_period import activate_roster
activate_result = activate_roster(result['roster_name'])
print(activate_result)
```

### Generating Future Rosters

To generate the next bi-weekly roster:

```python
result = generate_roster('2025-01-02', '2025-01-15')
```

### Switch Request Workflow

**For Drivers (via Dashboard):**

1. Driver A wants to switch their scheduled day off with Driver B
2. Driver A uses the switch request dialog:
   - Selects their scheduled off day
   - Selects Driver B
   - Selects the date they want off (Driver B's work day)
   - Provides reason
3. Driver B receives SMS notification
4. Driver B logs in and approves/rejects
5. Both drivers receive SMS confirmation

**API Usage:**

```python
# Driver requests switch
from tuktuk_management.api.roster import request_switch

result = request_switch(
    my_driver_id='DRV-112010',
    my_scheduled_off='2024-12-25',
    switch_with_driver='DRV-112011',
    requested_date='2024-12-27',
    reason='Family emergency'
)

# Other driver approves
from tuktuk_management.api.roster import approve_switch

result = approve_switch(
    roster_name='ROSTER-2024-12-19',
    requesting_driver='DRV-112010',
    my_driver_id='DRV-112011',
    their_off_date='2024-12-27',
    my_off_date='2024-12-25'
)
```

### Mark Sick Day

```python
from tuktuk_management.api.roster import mark_sick_day

result = mark_sick_day(
    driver_id='DRV-112010',
    date='2024-12-20',
    notes='Flu symptoms'
)
```

### Check Driver Schedule

```python
from tuktuk_management.api.roster import get_driver_schedule

schedule = get_driver_schedule(
    driver_id='DRV-112010',
    start_date='2024-12-19',
    end_date='2025-01-01'
)
```

---

## Integration with Existing System

### Transaction Processing Integration

The roster system needs to be integrated with the transaction processing to ensure scheduled days off don't count toward performance tracking.

**Update `tuktuk_transaction.py`:**

Add this check before updating consecutive misses:

```python
from tuktuk_management.api.roster import is_driver_scheduled_off

# In the daily reset/target check logic:
scheduled_off = is_driver_scheduled_off(driver_id, transaction_date)

if not scheduled_off['scheduled_off']:
    # Only track performance if not scheduled off
    # Update consecutive_misses logic here
    pass
```

### Dashboard Integration

Update the driver dashboard to show:
1. Next 14 days roster
2. Pending switch requests
3. Switch request form

Add to `tuktuk_driver_dashboard.py` or equivalent:

```python
@frappe.whitelist()
def get_my_roster(driver_id):
    from tuktuk_management.api.roster import get_driver_schedule, get_pending_switch_requests
    
    schedule = get_driver_schedule(driver_id)
    pending = get_pending_switch_requests(driver_id)
    
    return {
        'schedule': schedule,
        'pending_requests': pending
    }
```

---

## Roster Generation Algorithm Details

### Constraints
- Each regular driver gets exactly 1 day off per 7-day week (2 in 14-day roster)
- Each substitute driver gets exactly 1 day off per week
- Maximum 3 regular drivers off per day (except Sunday)
- Minimum 9 drivers working on Sunday
- Preferred days honored where possible
- DRV-112017 gets 4 consecutive days end of December

### Priority Order
1. Special requests (DRV-112017's 4 days)
2. Preferred day matches (if haven't had off this week)
3. Drivers who need an off day this week (round-robin)
4. Random selection for remaining slots

### Substitute Assignment
- Substitutes fill in for regular drivers who are off
- Each substitute assigned to the vehicle of the off driver
- Substitutes work all days except their scheduled day off
- If more drivers off than substitutes available, some substitutes work extra

---

## SMS Notifications

The system sends SMS notifications for:

1. **Switch Request** - sent to the driver being asked to switch
2. **Switch Approved** - sent to the requesting driver
3. **Switch Rejected** - sent to the requesting driver

Messages are sent via the configured SMS provider (TextBee, TextSMS, or httpSMS).

**Example SMS Messages:**

```
Switch Request:
"Sunny TukTuk: John Doe wants to switch days off. They offer Dec 25 for your Dec 27. Login to approve/reject."

Switch Approved:
"Sunny TukTuk: Your day off switch request was APPROVED! Your new day off is Dec 27."

Switch Rejected:
"Sunny TukTuk: Your day off switch request for Dec 27 was declined. Your original schedule remains."
```

---

## Troubleshooting

### Issue: "Need at least 3 substitute drivers"
**Solution:** Ensure you have 3 active substitute drivers in the system.

### Issue: "Roster already exists for this period"
**Solution:** Check existing rosters and either delete the duplicate or choose a different date range.

### Issue: "Switch request must be made at least 5 hours before operation start"
**Solution:** Switch requests must be made before 1 AM on the day of the requested change.

### Issue: Preferred days not being honored
**Solution:** 
1. Check that `preferred_day_off` field is set correctly
2. Verify the day name is in uppercase (MONDAY, TUESDAY, etc.)
3. Multiple drivers may have the same preference - system will honor as many as possible within constraints

### Issue: DRV-112017 not getting 4 consecutive days
**Solution:** The 4-day request only applies to December rosters. For December 2024, the days are Dec 28, 29, 30, 31.

---

## Testing Checklist

Before going live, test these scenarios:

- [ ] Generate a 14-day roster
- [ ] Activate the roster
- [ ] Verify each regular driver has exactly 2 days off
- [ ] Verify each substitute has exactly 2 days off
- [ ] Verify Sunday has minimum 9 drivers working
- [ ] Verify non-Sunday days have maximum 3 drivers off
- [ ] Request a day-off switch
- [ ] Receive SMS notification
- [ ] Approve a switch
- [ ] Reject a switch
- [ ] Mark a sick day
- [ ] Verify scheduled offs don't affect performance tracking
- [ ] Generate next roster period

---

## Maintenance

### Monthly Tasks
1. Generate rosters for upcoming periods (2-4 weeks in advance)
2. Review and approve pending switch requests
3. Clear expired rosters (mark as Completed)

### Weekly Tasks
1. Monitor substitute utilization
2. Review sick day patterns
3. Ensure adequate coverage

### Daily Tasks (Automated)
1. System checks active roster
2. Assigns substitutes based on roster
3. Processes transactions considering scheduled offs

---

## Future Enhancements

Potential features for future versions:

1. **Web interface** for roster visualization (calendar view)
2. **Mobile app** for drivers to view schedule and request switches
3. **Automated roster generation** (scheduled job to generate 2 weeks in advance)
4. **Analytics dashboard** showing:
   - Switch request patterns
   - Sick day trends
   - Substitute utilization
   - Day-off fairness metrics
5. **Preference learning** - system learns which switches are approved most often
6. **Holiday handling** - special rules for public holidays
7. **Vacation requests** - multi-day off requests
8. **Email notifications** in addition to SMS

---

## Support

For issues or questions:
1. Check Error Log in ERPNext
2. Review this documentation
3. Check project knowledge base
4. Contact system administrator

---

## Changelog

### Version 1.0.0 (December 18, 2024)
- Initial implementation
- Bi-weekly roster generation
- Driver preferences support
- Switch request system with SMS notifications
- Substitute assignment automation
- Integration with performance tracking
- Sick day marking
- Management override capabilities
