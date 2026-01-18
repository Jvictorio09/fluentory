"""
Management command to sync last contacted contacts from Infobip to CRM
Usage: python manage.py sync_infobip_contacts [--days=30] [--dry-run] [--limit=100]
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Q
from datetime import timedelta
from myApp.models import Lead, LeadTimelineEvent
from myApp.utils.infobip_service import InfobipService
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Sync last contacted phone numbers from Infobip to CRM Leads'

    def add_arguments(self, parser):
        parser.add_argument(
            '--check-whatsapp',
            action='store_true',
            help='Check WhatsApp connection status instead of syncing'
        )
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Number of days to look back for contacts (default: 30)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Run without making database changes (test mode)'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=100,
            help='Maximum number of contacts to fetch (default: 100)'
        )
        parser.add_argument(
            '--create-new',
            action='store_true',
            help='Create new Leads for contacts not found in CRM'
        )
        parser.add_argument(
            '--debug',
            action='store_true',
            help='Show detailed API responses for debugging'
        )

    def handle(self, *args, **options):
        # Check WhatsApp connection if requested
        if options.get('check_whatsapp'):
            self.stdout.write(self.style.SUCCESS('\n=== Checking WhatsApp Connection ===\n'))
            infobip = InfobipService()
            result = infobip.check_whatsapp_connection()
            
            if result['success']:
                self.stdout.write(self.style.SUCCESS(f"[OK] {result['message']}\n"))
            else:
                self.stdout.write(self.style.ERROR(f"[ERROR] {result['message']}\n"))
            
            whatsapp = result.get('whatsapp', {})
            self.stdout.write(f"\nWhatsApp Status:")
            self.stdout.write(f"  Enabled: {whatsapp.get('whatsapp_enabled', False)}")
            self.stdout.write(f"  Can Send: {whatsapp.get('can_send', False)}")
            self.stdout.write(f"  Messages Found: {whatsapp.get('messages_count', 0)}")
            
            if whatsapp.get('senders'):
                self.stdout.write(f"\nWhatsApp Senders:")
                for sender in whatsapp['senders']:
                    sender_name = sender.get('displayName') or sender.get('name') or 'Unknown'
                    sender_id = sender.get('id') or sender.get('senderId') or 'N/A'
                    self.stdout.write(f"  - {sender_name} ({sender_id})")
            
            self.stdout.write(f"\nEndpoint Status:")
            for endpoint_name, status in whatsapp.get('endpoint_status', {}).items():
                status_code = status.get('status_code', 'N/A')
                accessible = 'YES' if status.get('accessible') else 'NO'
                message = status.get('message', '')
                self.stdout.write(f"  {endpoint_name}: Status {status_code} (Accessible: {accessible})")
                if message and status_code != 200:
                    self.stdout.write(f"    -> {message}")
            
            self.stdout.write('\n')
            return
        
        days_back = options['days']
        dry_run = options['dry_run']
        limit = options['limit']
        create_new = options['create_new']
        
        self.stdout.write(self.style.SUCCESS('\n=== Infobip Contact Sync ===\n'))
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be saved\n'))
        
        # Initialize Infobip service
        infobip = InfobipService()
        
        # Test connection
        self.stdout.write('Testing Infobip connection...')
        connection_test = infobip.test_connection()
        if not connection_test['success']:
            self.stdout.write(self.style.ERROR(f"Connection failed: {connection_test['message']}"))
            return
        
        self.stdout.write(self.style.SUCCESS('[OK] Connection successful\n'))
        
        # Fetch contacts from Infobip
        debug_mode = options.get('debug', False)
        self.stdout.write(f'Fetching contacts from last {days_back} days (limit: {limit})...')
        
        if debug_mode:
            self.stdout.write(self.style.WARNING('\n[DEBUG MODE] Detailed output:\n'))
            import logging
            logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
        
        contacts = infobip.get_last_contacted_profiles(days_back=days_back, limit=limit, debug=debug_mode)
        
        if debug_mode:
            self.stdout.write(f'\n[DEBUG] Total contacts found: {len(contacts)}')
            if contacts:
                self.stdout.write('[DEBUG] Sample contact:')
                for i, contact in enumerate(contacts[:3], 1):
                    self.stdout.write(f'  {i}. Phone: {contact.get("phone")}, Channel: {contact.get("channel")}, Date: {contact.get("last_contacted")}')
        
        if not contacts:
            self.stdout.write(self.style.WARNING('No contacts found in Infobip'))
            self.stdout.write('\nTroubleshooting:')
            self.stdout.write('  1. Check if you have messages/contacts in Infobip within the specified date range')
            self.stdout.write('  2. Verify your API key has permissions to read messages/profiles')
            self.stdout.write('  3. Check if Infobip People API is enabled for your account')
            self.stdout.write('  4. Try increasing --days parameter (e.g., --days=90 or --days=365)')
            self.stdout.write('  5. Check Django logs for detailed API responses\n')
            return
        
        self.stdout.write(self.style.SUCCESS(f'[OK] Found {len(contacts)} contacts\n'))
        
        # Statistics
        stats = {
            'updated': 0,
            'created': 0,
            'skipped': 0,
            'errors': 0
        }
        
        # Process each contact
        self.stdout.write('Processing contacts...\n')
        for i, contact in enumerate(contacts, 1):
            phone = contact.get('phone', '').strip()
            if not phone:
                stats['skipped'] += 1
                continue
            
            try:
                # Normalize phone for matching - extract digits only
                phone_digits = ''.join(c for c in phone if c.isdigit())
                
                # Find existing Lead by phone number (more flexible matching)
                # Match by: exact match, last 10 digits, or any overlap of significant digits
                leads_query = Lead.objects.filter(phone__isnull=False).exclude(phone='')
                lead = None
                
                # Try exact match first
                lead = leads_query.filter(phone=phone).first()
                
                if not lead and len(phone_digits) >= 10:
                    # Try matching by last 10 digits (most reliable)
                    last_10 = phone_digits[-10:]
                    for candidate in leads_query:
                        candidate_digits = ''.join(c for c in candidate.phone if c.isdigit())
                        if candidate_digits.endswith(last_10) or last_10 in candidate_digits:
                            lead = candidate
                            break
                
                last_contacted = contact.get('last_contacted')
                channel = contact.get('channel', 'SMS')
                profile_id = contact.get('profile_id')
                
                if lead:
                    # Update existing Lead
                    updated = False
                    
                    # Update last_contact_date if newer
                    if last_contacted:
                        if not lead.last_contact_date or last_contacted > lead.last_contact_date:
                            if not dry_run:
                                lead.last_contact_date = last_contacted
                            updated = True
                    
                    # Update Infobip metadata
                    if not dry_run:
                        if profile_id:
                            lead.infobip_profile_id = profile_id
                        lead.infobip_channel = channel
                        lead.infobip_last_synced_at = timezone.now()
                        
                        # Auto-update status if contacted recently
                        auto_update_days = getattr(settings, 'INFOBIP_AUTO_UPDATE_STATUS_DAYS', 7)
                        if last_contacted and (timezone.now() - last_contacted).days <= auto_update_days:
                            if lead.status == 'new':
                                lead.status = 'contacted'
                                updated = True
                        
                        lead.save(update_fields=[
                            'last_contact_date', 'infobip_profile_id', 
                            'infobip_channel', 'infobip_last_synced_at', 'status', 'updated_at'
                        ])
                        
                        # Create timeline event
                        if updated:
                            LeadTimelineEvent.objects.create(
                                lead=lead,
                                event_type='LEAD_UPDATED',
                                actor=None,  # System action
                                summary=f"Updated from Infobip sync - Last contacted via {channel}",
                                metadata={
                                    'source': 'infobip_sync',
                                    'channel': channel,
                                    'last_contacted': last_contacted.isoformat() if last_contacted else None,
                                    'profile_id': profile_id
                                }
                            )
                    
                    stats['updated'] += 1
                    self.stdout.write(f"  [{i}/{len(contacts)}] Updated: {lead.name or 'Unknown'} ({phone})")
                    
                elif create_new:
                    # Create new Lead
                    if not dry_run:
                        name = contact.get('name', '').strip() or f"Contact {phone[-4:]}"
                        lead = Lead.objects.create(
                            name=name,
                            phone=phone,
                            source='other',
                            status='new',
                            last_contact_date=last_contacted,
                            infobip_profile_id=profile_id,
                            infobip_channel=channel,
                            infobip_last_synced_at=timezone.now(),
                            notes=f"Auto-created from Infobip sync - Last contacted via {channel}"
                        )
                        
                        # Create timeline event
                        LeadTimelineEvent.objects.create(
                            lead=lead,
                            event_type='LEAD_CREATED',
                            actor=None,
                            summary=f"Created from Infobip sync - Last contacted via {channel}",
                            metadata={
                                'source': 'infobip_sync',
                                'channel': channel,
                                'last_contacted': last_contacted.isoformat() if last_contacted else None,
                                'profile_id': profile_id
                            }
                        )
                    
                    stats['created'] += 1
                    self.stdout.write(f"  [{i}/{len(contacts)}] Created: {name} ({phone})")
                else:
                    stats['skipped'] += 1
                    self.stdout.write(f"  [{i}/{len(contacts)}] Skipped: {phone} (not found, use --create-new to create)")
                    
            except Exception as e:
                stats['errors'] += 1
                self.stdout.write(self.style.ERROR(f"  [{i}/{len(contacts)}] Error processing {phone}: {str(e)}"))
                logger.error(f"Error processing contact {phone}: {e}", exc_info=True)
        
        # Print summary
        self.stdout.write('\n' + '=' * 50)
        self.stdout.write(self.style.SUCCESS('\nSync Summary:'))
        self.stdout.write(f"  Updated: {stats['updated']}")
        self.stdout.write(f"  Created: {stats['created']}")
        self.stdout.write(f"  Skipped: {stats['skipped']}")
        if stats['errors'] > 0:
            self.stdout.write(self.style.ERROR(f"  Errors: {stats['errors']}"))
        self.stdout.write('\nDone!\n')

