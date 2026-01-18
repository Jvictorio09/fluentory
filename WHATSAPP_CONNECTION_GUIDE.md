# How to Connect Your WhatsApp Business Account to Infobip

## Overview
To sync WhatsApp messages to your CRM, you need to connect your actual WhatsApp Business Account (WABA) to Infobip. This allows Infobip to send and receive messages on your behalf.

## Step-by-Step Guide

### 1. **Prerequisites**
- A WhatsApp Business Account (WABA) registered with Meta/Facebook
- Access to your Meta Business Manager
- Infobip account (you already have this)

### 2. **In Infobip Dashboard**

1. **Go to Infobip Portal**: https://portal.infobip.com/
2. **Navigate to WhatsApp Setup**:
   - Go to: **Channels** → **WhatsApp** → **Getting Started**
   - Or: **Developer Tools** → **WhatsApp**

3. **Register Your WhatsApp Sender**:
   - Click on "Register WhatsApp Sender" or "Add WhatsApp Number"
   - You'll need:
     - Your WhatsApp Business Account ID (from Meta)
     - Your phone number (the one you want to use for WhatsApp)
     - Business verification documents (if required)

### 3. **In Meta Business Manager**

1. **Go to Meta Business Manager**: https://business.facebook.com/
2. **Navigate to WhatsApp Accounts**:
   - Go to: **Accounts** → **WhatsApp Accounts**
   - Find your WhatsApp Business Account

3. **Get Your WhatsApp Business Account ID**:
   - Copy the Account ID (WABA ID)
   - You'll need this for Infobip registration

4. **Connect Infobip as a Provider**:
   - In your WABA settings, look for "Connected Apps" or "Business Providers"
   - Add Infobip as a provider
   - Authorize Infobip to access your WhatsApp account

### 4. **Complete Registration in Infobip**

1. **Enter Your Details**:
   - WhatsApp Business Account ID (from Meta)
   - Display name (how your business appears)
   - Phone number
   - Business category

2. **Verify Your Number**:
   - Infobip will send a verification code
   - Enter the code to verify ownership

3. **Wait for Approval**:
   - Meta/WhatsApp will review your application
   - This can take 24-48 hours
   - You'll receive an email when approved

### 5. **Verify Connection**

Once connected, you can verify in Infobip:

1. **Check WhatsApp Senders**:
   - Go to: **Channels** → **WhatsApp** → **Senders**
   - You should see your WhatsApp number listed
   - Status should be "Active" or "Verified"

2. **Test the Connection**:
   - Send a test WhatsApp message from Infobip
   - Check if it appears in your WhatsApp
   - Check if it appears in message logs

### 6. **After Connection**

Once your WhatsApp is connected:

1. **Messages will flow through Infobip**:
   - Messages you send via Infobip API → appear in WhatsApp
   - Messages received in WhatsApp → appear in Infobip logs

2. **Run the Sync**:
   ```bash
   python manage.py sync_infobip_contacts --days=30
   ```
   - This will now find your WhatsApp messages!

3. **Set Up Webhooks (Optional)**:
   - Configure webhooks to receive messages in real-time
   - This allows automatic CRM updates when messages arrive

## Troubleshooting

### "WhatsApp Sender Not Found"
- Make sure you've completed the registration process
- Check if your application is still pending approval
- Verify your WhatsApp Business Account is active in Meta

### "No Messages Found"
- Make sure you've sent/received at least one message after connecting
- Check the date range (try `--days=365` to see older messages)
- Verify messages are appearing in Infobip dashboard

### "Connection Failed"
- Verify your API key has WhatsApp permissions
- Check if your WhatsApp account is still connected in Infobip
- Ensure your Meta Business Manager connection is active

## Quick Check Command

After connecting, verify it's working:

```bash
python manage.py sync_infobip_contacts --check-whatsapp
```

This will show:
- If WhatsApp is enabled
- Your WhatsApp senders
- Message counts
- Endpoint accessibility

## Next Steps

1. **Connect your WhatsApp account** (follow steps above)
2. **Send a test message** through Infobip
3. **Run the sync** to see messages appear in your CRM
4. **Set up webhooks** for real-time updates (optional)

## Need Help?

- **Infobip Support**: Check their documentation or contact support
- **Meta Business Support**: For WhatsApp Business Account issues
- **Infobip API Docs**: https://www.infobip.com/docs/api

---

**Note**: The free trial account may have limitations. Make sure you have:
- A verified WhatsApp Business Account
- Proper permissions in Meta Business Manager
- Completed the Infobip registration process

