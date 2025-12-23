## Driver Termination Process

### 1. Termination Trigger (terminate_driver_with_deposit_refund())

Located in: tuktuk_management/api/tuktuk.py (lines 1574-1604)

When a driver is terminated (automatically after 3 consecutive target misses or manually), the system:

### 2. Vehicle Release

- Releases the assigned TukTuk vehicle:

- Sets vehicle status to "Available"

- Clears the driver's assigned_tuktuk field

### 3. Exit Processing (process_exit_refund())

Located in: tuktuk_management/tuktuk_management/doctype/tuktuk_driver/tuktuk_driver.py (lines 219-247)

The driver record is updated with termination markers:

- Sets exit_date to the termination date

- Sets refund_amount to the current deposit balance

- Sets refund_status to "Pending"

- Adds a "Refund" transaction record to the deposit transactions

- Zeros out current_deposit_balance

### 4. Notification

- Sends an email to yuda@sunnytuktuk.com with termination details and refund information

### 5. Record Preservation

The driver record is not deleted or archived. It remains in the database with:

- exit_date set (marks as terminated)

- refund_status set to "Pending" (or updated to "Processed"/"Completed" later)

- refund_amount stored for reference

- All historical data preserved (transactions, performance, etc.)

### 6. Filtering in Reports

Terminated drivers are filtered out of active driver lists using:

exit_date IS NULL  # For active drivers

exit_date IS NOT NULL  # For terminated/exited drivers

### 7. Restoration Capability

The system includes restore_terminated_driver() which can reverse the termination if needed.

### Important Note

The user account is not automatically disabled during termination. There's a separate function disable_tuktuk_driver_account() in driver_auth.py, but it's not called automatically. You may want to manually disable the user account or add this to the termination process.

The driver record is preserved for audit and historical purposes, and terminated drivers are identified by the exit_date field rather than deletion.
