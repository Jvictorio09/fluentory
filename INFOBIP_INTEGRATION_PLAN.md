# Infobip Integration Plan - Last Contacted Numbers to CRM

## Overview
This integration will fetch phone numbers of people last contacted via Infobip and sync them into the Fluentory CRM (Lead model) on the admin side.

---

## What I Need From You

### 1. **Infobip API Credentials** (Required)
Please provide:
- **Infobip API Key** (or API Token)
- **Infobip Base URL** (e.g., `https://api.infobip.com` or your regional endpoint)
- **Infobip Account ID** (if required)

You can find these in your Infobip dashboard:
- Go to: https://portal.infobip.com/
- Navigate to: Settings → API Keys

### 2. **Infobip People Module Access** (Required)
- Do you have access to the **Infobip People** module?
- Can you access customer profiles and their "Last Contacted" attribute?
- If not, we may need to use message logs/events API instead

### 3. **Integration Scope** (Please Clarify)
- **Which channels should count as "contact"?**
  - SMS only?
  - WhatsApp?
  - Email?
  - All channels?
  - Any message sent (inbound/outbound)?

- **Time Range**: 
  - How far back should we fetch? (e.g., last 30 days, last 90 days, all time?)
  - Should we only sync contacts from a specific date forward?

- **Sync Frequency**:
  - Real-time (webhook-based)?
  - Scheduled (hourly, daily, weekly)?
  - Manual trigger only?

### 4. **Data Mapping** (Please Confirm)
- **Phone Number Format**: 
  - How are phone numbers stored in Infobip? (E164 format, national format?)
  - Should we normalize them before storing?

- **Matching Logic**:
  - How should we match Infobip contacts to existing Leads?
    - By exact phone number match?
    - Create new Leads if phone doesn't exist?
    - Update existing Leads only?

- **Last Contact Date**:
  - Should we update the `last_contact_date` field in the Lead model?
  - Should we update the Lead status automatically? (e.g., set to "contacted" if last_contact_date is recent?)

### 5. **Additional Data** (Optional)
Would you like to sync any additional information from Infobip?
- Contact name (if available in Infobip)?
- Channel used (SMS, WhatsApp, etc.)?
- Message count?
- Last message content preview?

---

## What I Will Build

### 1. **Infobip Service Module** (`myApp/utils/infobip_service.py`)
   - API client for Infobip People API
   - Functions to fetch last contacted profiles
   - Error handling and retry logic
   - Phone number normalization

### 2. **Management Command** (`myApp/management/commands/sync_infobip_contacts.py`)
   - Command to manually sync contacts: `python manage.py sync_infobip_contacts`
   - Options for date range, dry-run mode, etc.
   - Logging and error reporting

### 3. **Admin Dashboard Integration**
   - New page: `/dashboard/infobip-sync/`
   - Manual sync button
   - Sync status and history
   - Last sync timestamp
   - Error logs

### 4. **Scheduled Task** (Optional - if using Celery)
   - Automatic periodic sync
   - Configurable schedule (hourly/daily)

### 5. **Database Updates** (If Needed)
   - Add fields to Lead model for Infobip metadata:
     - `infobip_profile_id` (optional)
     - `infobip_last_synced_at` (optional)
     - `infobip_channel` (optional - last channel used)

### 6. **Configuration**
   - Add Infobip settings to `settings.py`
   - Environment variables for credentials
   - Configuration for sync behavior

---

## Implementation Steps

1. ✅ Add Infobip Python SDK to `requirements.txt`
2. ✅ Create Infobip service utility module
3. ✅ Add configuration to Django settings
4. ✅ Create management command for syncing
5. ✅ Add admin dashboard views
6. ✅ Update Lead model (if needed)
7. ✅ Create scheduled task (if automatic sync is needed)

---

## Security & Best Practices

- API credentials stored in environment variables (`.env` file)
- Never commit credentials to version control
- Rate limiting to respect Infobip API limits
- Error handling and logging
- Data validation before database updates
- Phone number normalization and validation

---

## Testing Plan

1. **Unit Tests**: Test Infobip API client functions
2. **Integration Tests**: Test sync command with mock data
3. **Manual Testing**: Test with real Infobip account (with limited data)
4. **Admin Dashboard**: Test UI and manual sync functionality

---

## Next Steps

**Please provide the information requested above**, especially:
1. Infobip API credentials
2. Which channels count as "contact"
3. Sync frequency preference
4. Matching logic preference

Once I have this information, I'll proceed with the implementation!

---

## Questions?

If anything is unclear or you need clarification on any point, please let me know!

