# Changelog

All notable changes to the Sunny TukTuk Management System will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.1] - 2025-06-20

### Added
- **general**: Initialize App

### Other
- **general**: Driver Deposit Report
- **general**: Remove deprecated tuktuk.py file containing driver management, payment processing, and rental functionalities.
- **general**: New README.md
- **general**: Add comprehensive README documentation

## [Unreleased]

### Added
- Automated changelog generation system
- Version management integration with pyproject.toml
- Conventional commit support for automatic changelog updates

### Changed
- Updated project configuration to include changelog references
- Enhanced versioning strategy for better release management

## [0.1.0] - 2024-12-15

### Added
- **Core Fleet Management System**
  - TukTuk Vehicle management with battery monitoring
  - Real-time vehicle status tracking (Available, Assigned, Charging, Maintenance)
  - Individual vehicle rental rate configuration
  - 3-digit Mpesa account number integration

- **Driver Management System**
  - Comprehensive driver profiles with validation
  - Performance metrics and target tracking
  - Payment details and emergency contact management
  - Individual settings override capabilities
  - Age, phone number, email, and license validation

- **Mpesa Payment Integration**
  - Real-time payment listening and processing
  - Automatic revenue splitting (50% driver, 50% target pre-target; 100% driver post-target)
  - Driver payment processing via Mpesa B2C
  - Transaction recording and audit trail
  - Customer payment association
  - Sandbox and production environment support

- **Smart Battery Management**
  - Real-time battery level monitoring
  - 2-hour charging cycle management
  - Automatic low-battery notifications (SMS/Email)
  - Temporary vehicle reassignment during charging
  - Battery warning threshold (20%) with notifications

- **Performance Tracking System**
  - Daily target monitoring (default: 3000 KSH)
  - Rolling balance for unmet targets
  - Consecutive miss tracking (3 misses = termination)
  - Bonus payments for target achievement
  - Driver termination with deposit refund

- **Rental System**
  - Temporary vehicle assignments during charging periods
  - Rental fee calculation (initial + hourly rates)
  - Duration tracking and status management
  - Automatic rental fee processing

- **Deposit Management System**
  - Driver deposit tracking and management
  - Multiple transaction types (Initial, Top Up, Target Deduction, Damage, Refund, Adjustment)
  - Balance tracking and transaction history
  - Bulk refund processing capabilities

- **Telematics Integration**
  - Real-time vehicle location tracking
  - Battery level monitoring via device integration
  - Speed and status monitoring
  - Webhook support for external telematics systems
  - Mock data support for development/testing

- **Reporting and Analytics**
  - Driver Performance Report with comparative analysis
  - Daily Revenue Report with comprehensive financial overview
  - Deposit Management Report for financial tracking
  - Fleet Status Dashboard with real-time monitoring
  - Revenue tracking charts and target achievement metrics

- **Automated Workflows**
  - Daily target reset at midnight
  - Operating hours management (6:00 AM to 12:00 AM)
  - Hourly battery level checks
  - Automatic system activation/deactivation
  - Scheduled report generation

- **Configuration Management**
  - Global settings for operating hours, targets, and percentages
  - Mpesa integration configuration
  - Notification preferences (SMS/Email)
  - Bonus settings and rental rate configuration

- **Security and Permissions**
  - Role-based access control (System Manager, TukTuk Manager, Driver, etc.)
  - Document-level permissions
  - API security with whitelist protection
  - Audit trail for all transactions

- **User Interface**
  - Modern dashboard with quick access shortcuts
  - Mobile-responsive design
  - Custom JavaScript for enhanced user experience
  - List views with filtering and sorting

### Technical Features
- **API Endpoints**
  - Mpesa validation and confirmation webhooks
  - Telematics webhook integration
  - Payment processing endpoints
  - Vehicle status update APIs
  - Driver management APIs

- **Database Design**
  - 6 core DocTypes with comprehensive field definitions
  - Proper indexing and constraints
  - Audit trail and change tracking
  - Optimized queries for performance

- **Scheduled Tasks**
  - Cron-based scheduling for daily operations
  - Hourly battery monitoring
  - Real-time status updates every 5 minutes
  - Automated report generation

- **Error Handling**
  - Comprehensive error logging
  - Graceful fallbacks for API failures
  - User-friendly error messages
  - Transaction rollback on failures

### Infrastructure
- **ERPNext 15 Integration**
  - Full compatibility with ERPNext framework
  - Custom module integration
  - Workspace and navigation setup
  - Permission system integration

- **Development Tools**
  - Test data generation scripts
  - Development environment setup
  - Mock API support for testing
  - Comprehensive logging system

## [0.0.1] - 2024-11-26
### Added
- Initial project setup and structure
- Basic DocType definitions
- Core application framework
- ERPNext integration foundation

---

## Versioning Strategy

This project follows [Semantic Versioning](https://semver.org/) (MAJOR.MINOR.PATCH):

- **MAJOR** version for incompatible API changes
- **MINOR** version for backwards-compatible functionality additions
- **PATCH** version for backwards-compatible bug fixes

### Release Schedule
- **Patch releases**: As needed for critical bug fixes
- **Minor releases**: Monthly for new features
- **Major releases**: Quarterly for significant architectural changes

### Pre-release Versions
- **Alpha**: Early development versions (0.x.x-alpha)
- **Beta**: Feature-complete testing versions (0.x.x-beta)
- **RC**: Release candidates (0.x.x-rc)

---

## Contributing

When contributing to this project, please follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

- `feat:` for new features
- `fix:` for bug fixes
- `docs:` for documentation changes
- `style:` for formatting changes
- `refactor:` for code refactoring
- `test:` for adding tests
- `chore:` for maintenance tasks

This ensures automatic changelog generation and proper version management. 