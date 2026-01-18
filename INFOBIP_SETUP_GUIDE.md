# Infobip Integration Setup Guide

## Overview
This integration syncs last contacted phone numbers from Infobip to your CRM (Lead model) in the admin dashboard.

## ✅ What Has Been Implemented

1. **Infobip Service Module** (`myApp/utils/infobip_service.py`)
   - API client for Infobip People API and Messages API
   - Phone number normalization
   - Connection testing
   - Error handling and retry logic

2. **Lead Model Updates**
   - Added `infobip_profile_id` field
   - Added `infobip_last_synced_at` field
   - Added `infobip_channel` field

3. **Management Command** (`sync_infobip_contacts`)
   - Manual sync via command line
   - Options for days back, limit, create new leads
   - Dry-run mode for testing

4. **Admin Dashboard Integration**
   - New page: `/dashboard/infobip-sync/`
   - Connection status display
   - Manual sync trigger
   - Sync statistics
   - Added to sidebar navigation

5. **Configuration**
   - Settings added to `myProject/settings.py`
   - Environment variable support

## 📋 Setup Steps

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

The Infobip SDK has been added to `requirements.txt`. If you prefer using the REST API directly (which is already implemented), you can remove it as the code uses `requests` library.

### 2. Configure Environment Variables

Add these to your `.env` file:

```env
# Infobip Configuration
INFOBIP_API_KEY=your_api_key_here
INFOBIP_BASE_URL=https://api.infobip.com
INFOBIP_ACCOUNT_ID=your_account_id_here  # Optional
INFOBIP_SYNC_CHANNELS=SMS,WHATSAPP  # Comma-separated list
INFOBIP_AUTO_UPDATE_STATUS_DAYS=7  # Auto-update lead status if contacted within this many days
```

**To get your Infobip API key:**
1. Log in to [Infobip Portal](https://portal.infobip.com/)
2. Go to Settings → API Keys
3. Create a new API key or use an existing one
4. Copy the API key to your `.env` file

### 3. Run Database Migration

The Lead model has been updated with new fields. You need to create and run a migration:

```bash
python manage.py makemigrations
python manage.py migrate
```

### 4. Test Connection

You can test the Infobip connection in two ways:

**Via Admin Dashboard:**
1. Go to `/dashboard/infobip-sync/`
2. Check the "Connection Status" section

**Via Management Command:**
```bash
python manage.py sync_infobip_contacts --days=30 --dry-run
```

## 🚀 Usage

### Manual Sync via Dashboard

1. Navigate to `/dashboard/infobip-sync/`
2. Configure sync options:
   - **Days to Look Back**: How many days to fetch contacts from (default: 30)
   - **Create New Leads**: Check this to create new Leads for contacts not found in CRM
3. Click "Sync Now"
4. View results in the "Sync Result" section

### Manual Sync via Command Line

```bash
# Basic sync (last 30 days, update existing leads only)
python manage.py sync_infobip_contacts

# Sync last 90 days
python manage.py sync_infobip_contacts --days=90

# Create new leads for contacts not found
python manage.py sync_infobip_contacts --create-new

# Dry run (test without saving)
python manage.py sync_infobip_contacts --dry-run

# Limit number of contacts fetched
python manage.py sync_infobip_contacts --limit=50
```

### Automatic Scheduled Sync (Optional)

If you want automatic periodic syncing, you can set up a Celery task or cron job:

**Option 1: Celery Task** (if Celery is configured)
Create a task in `myApp/tasks.py`:

```python
from celery import shared_task
from django.core.management import call_command

@shared_task
def sync_infobip_contacts_task():
    call_command('sync_infobip_contacts', '--days=30', '--create-new')
```

Then schedule it in your Celery beat configuration.

**Option 2: Cron Job**
Add to your crontab:

```bash
# Run every day at 2 AM
0 2 * * * cd /path/to/your/project && python manage.py sync_infobip_contacts --days=30 --create-new
```

## 📊 How It Works

1. **Fetch Contacts**: The system fetches contacts from Infobip that were contacted in the specified time period
   - First tries Infobip People API (if available)
   - Falls back to Messages API if People API is not available

2. **Match Leads**: For each contact, it tries to find an existing Lead by phone number
   - Matches exact phone number
   - Also tries matching last 10 digits (for different formats)

3. **Update or Create**:
   - **If Lead exists**: Updates `last_contact_date` if the contact is newer, updates Infobip metadata
   - **If Lead doesn't exist** (and `--create-new` is used): Creates a new Lead with the contact information

4. **Auto-Update Status**: If a Lead was contacted within the last 7 days (configurable), it automatically updates the status to "Contacted" if it was "New"

5. **Timeline Events**: Creates timeline events for audit trail

## 🔧 Configuration Options

### Sync Channels
Control which channels to sync by setting `INFOBIP_SYNC_CHANNELS`:
- `SMS` - SMS messages
- `WHATSAPP` - WhatsApp messages
- `EMAIL` - Email messages
- `VIBER` - Viber messages
- Or any combination: `SMS,WHATSAPP,EMAIL`

### Auto-Update Status Days
Set `INFOBIP_AUTO_UPDATE_STATUS_DAYS` to control when leads are automatically marked as "Contacted":
- Default: 7 days
- Set to 0 to disable auto-update

## 🐛 Troubleshooting

### Connection Failed
- **Check API Key**: Verify `INFOBIP_API_KEY` is set correctly in `.env`
- **Check Base URL**: Ensure `INFOBIP_BASE_URL` is correct (usually `https://api.infobip.com`)
- **Check Permissions**: Your API key needs permissions to read messages/profiles

### No Contacts Found
- **Check Date Range**: Try increasing the `--days` parameter
- **Check Channels**: Verify contacts exist in the channels you're syncing
- **Check API Access**: Ensure you have access to Infobip People API or Messages API

### Phone Number Mismatches
- The system normalizes phone numbers to E.164 format
- It also tries matching by last 10 digits
- If contacts aren't matching, check phone number formats in both systems

### Sync Takes Too Long
- Use `--limit` parameter to limit the number of contacts fetched
- Consider running sync during off-peak hours
- For large datasets, run sync in smaller batches

## 📝 Notes

- The sync creates timeline events for all updates (audit trail)
- Phone numbers are normalized to E.164 format (with + prefix)
- The system handles both Infobip People API and Messages API
- All sync operations are logged for debugging

## 🔐 Security

- **Never commit `.env` file** to version control
- Store API keys securely
- Use environment variables for all sensitive configuration
- Consider using a secrets management service in production

## 📚 API Documentation

For more information about Infobip APIs:
- [Infobip People API](https://www.infobip.com/docs/people)
- [Infobip Messages API](https://www.infobip.com/docs/api)
- [Infobip API Authorization](https://www.infobip.com/docs/essentials/api-essentials/api-authorization)

## 🆘 Support

If you encounter issues:
1. Check the sync result output in the dashboard
2. Check Django logs for error messages
3. Test connection using the dashboard test button
4. Verify API credentials in Infobip portal

