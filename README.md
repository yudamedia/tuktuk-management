# Sunny TukTuk Management System

A comprehensive Frappe application for managing electric tuktuks, drivers, payments, and operations in Diani Beach, Kenya.

## Overview

Sunny TukTuk is a fleet management system designed for electric-charged tuktuks operating as taxis in the Diani Beach area. The system handles everything from driver assignments and daily targets to Mpesa payment processing and battery management.

## System Architecture

### Core Components

- **Fleet Management**: Track and manage electric tuktuks
- **Driver Management**: Comprehensive driver profiles and performance tracking
- **Payment Processing**: Automatic Mpesa integration with revenue splitting
- **Battery Management**: Monitor charging cycles and optimize fleet availability
- **Rental System**: Temporary vehicle assignments during charging periods
- **Performance Analytics**: Daily targets, earnings tracking, and reporting

### Key Features

#### Dynamic Revenue Sharing
- **Pre-Target**: 50% to driver, 50% towards daily target
- **Post-Target**: 100% to driver
- Configurable percentages (global or individual)

#### Smart Battery Management
- Real-time battery level monitoring
- 2-hour charging cycle management
- Automatic low-battery notifications
- Temporary vehicle reassignment during charging

#### Performance Tracking
- Daily target monitoring (default: 3000 KSH)
- Rolling balance for unmet targets
- Automatic termination after 3 consecutive misses
- Bonus payments for target achievement

#### Mpesa Integration
- Real-time payment listening
- Automatic driver payments
- Transaction recording and audit trail
- Customer payment association

## Installation

### Prerequisites
- ERPNext 15 installation
- Python 3.8+
- Frappe Framework

### Installation Steps

1. **Navigate to your apps directory**
   ```bash
   cd ~/frappe-bench/apps
   ```

2. **Clone the repository**
   ```bash
   git clone https://github.com/yudamedia/tuktuk-management.git
   ```

3. **Install the app**
   ```bash
   cd ~/frappe-bench
   bench install-app tuktuk_management
   ```

4. **Install on your site**
   ```bash
   bench --site [your-site-name] install-app tuktuk_management
   ```

5. **Restart services**
   ```bash
   bench restart
   ```

## ⚙️ Configuration

### Initial Setup

1. **Access TukTuk Settings**
   - Navigate to TukTuk Management > Configuration > TukTuk Settings

2. **Configure Operating Hours**
   - Default: 6:00 AM to 12:00 AM (midnight)
   - Adjustable based on business needs

3. **Set Global Targets**
   - Default daily target: 3000 KSH
   - Default fare percentage: 50%
   - Configure bonus settings

4. **Mpesa Integration**
   - Set up paybill number
   - Configure API credentials
   - Enable notifications

### Vehicle Setup

1. **Add TukTuk Vehicles**
   - 3-digit Mpesa account numbers
   - Set individual rental rates (optional)

2. **Register Drivers**
   - Complete driver profiles
   - Assign vehicles
   - Set individual targets (optional)

## DocTypes

### TukTuk Vehicle
- Vehicle identification and specifications
- Battery level monitoring
- Status tracking (Available, Assigned, Charging, Maintenance)
- Individual rental rate configuration

### TukTuk Driver
- Comprehensive driver information
- Performance metrics and target tracking
- Payment details and emergency contacts
- Individual settings override

### TukTuk Transaction
- Mpesa transaction recording
- Automatic revenue splitting
- Driver payment processing
- Customer payment association

### TukTuk Rental
- Temporary vehicle assignments
- Rental fee calculation
- Duration tracking
- Status management

### TukTuk Settings
- Global configuration management
- Operating hours
- Target and percentage settings
- Mpesa integration
- Notification preferences

## Roles and Permissions

### System Manager
- Full system access
- Configuration management
- User management

### TukTuk Manager
- Fleet and driver management
- Transaction monitoring
- Report generation

### Driver
- Personal dashboard access
- Transaction history
- Performance metrics

## Reports and Analytics

### Built-in Reports
- **Driver Performance Report**: Individual and comparative analysis
- **Daily Revenue Report**: Comprehensive financial overview
- **Fleet Status Dashboard**: Real-time vehicle monitoring

### Dashboard Features
- Revenue tracking charts
- Target achievement metrics
- Battery level monitoring
- Quick access shortcuts

## Automated Workflows

### Daily Operations
- **6:00 AM**: System activation and status reset
- **Hourly**: Battery level checks and notifications
- **12:00 AM**: Daily target reset and performance evaluation

### Payment Processing
- Real-time Mpesa transaction monitoring
- Automatic revenue calculation and splitting
- Instant driver payments
- Target balance updates

### Performance Management
- Daily target tracking
- Consecutive miss monitoring
- Automatic termination procedures
- Bonus payment processing

## Key Business Rules

1. **Target Management**
   - Unmet daily targets roll over to next day
   - 3 consecutive misses result in driver termination
   - Bonus payments for meeting targets (optional)

2. **Revenue Sharing**
   - Pre-target: Configurable split (default 50/50)
   - Post-target: 100% to driver
   - Individual overrides available

3. **Battery Management**
   - 2-hour charging requirement
   - Rental options during charging
   - Low battery alerts and notifications

4. **Operating Hours**
   - Configurable business hours
   - System only processes payments during operating hours
   - Daily resets at midnight

## Security Features

- Role-based access control
- Secure Mpesa API integration
- Transaction audit trails
- Data validation and sanitization

## Support

For support and customization requests, contact:
- **Email**: yuda@graphicshop.co.ke
- **Company**: Yuda Media
- **Location**: Diani Beach, Kenya

## License

MIT License - See LICENSE file for details

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## Development

### Project Structure
```
tuktuk_management/
├── api/                    # API functions and business logic
├── config/                 # Module configuration
├── patches/                # Database migration scripts
├── public/                 # Frontend assets (CSS, JS)
├── setup/                  # Installation scripts
├── tuktuk_management/      # Core application
│   ├── doctype/           # Document type definitions
│   └── report/            # Custom reports
└── www/                   # Web pages and templates
```

### Key Files
- `hooks.py` - App configuration and scheduled tasks
- `api/tuktuk.py` - Core business logic and payment processing
- `patches.txt` - Database migration tracking

---

**Built with ❤️ for sustainable transportation in Kenya**
