"""
Infobip API Service
Handles communication with Infobip API to fetch last contacted contacts
"""
import requests
import logging
import sys
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

# Also log to console if in debug mode
console_handler = None


class InfobipService:
    """Service for interacting with Infobip API"""
    
    def __init__(self):
        self.api_key = getattr(settings, 'INFOBIP_API_KEY', '')
        base_url = getattr(settings, 'INFOBIP_BASE_URL', 'https://api.infobip.com')
        # Ensure base URL has https:// scheme
        if base_url and not base_url.startswith('http://') and not base_url.startswith('https://'):
            self.base_url = f'https://{base_url}'
        else:
            self.base_url = base_url
        self.account_id = getattr(settings, 'INFOBIP_ACCOUNT_ID', '')
        self.sync_channels = getattr(settings, 'INFOBIP_SYNC_CHANNELS', ['SMS', 'WHATSAPP'])
        
        if not self.api_key:
            logger.warning("Infobip API key not configured")
    
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with authentication"""
        return {
            'Authorization': f'App {self.api_key}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
    
    def _normalize_phone(self, phone: str) -> str:
        """
        Normalize phone number to E.164 format
        Removes spaces, dashes, parentheses, and ensures + prefix
        """
        if not phone:
            return ''
        
        # Remove all non-digit characters except +
        normalized = ''.join(c for c in phone if c.isdigit() or c == '+')
        
        # Ensure + prefix
        if normalized and not normalized.startswith('+'):
            # If it starts with 00, replace with +
            if normalized.startswith('00'):
                normalized = '+' + normalized[2:]
            else:
                # Assume default country code if missing (you may want to configure this)
                normalized = '+' + normalized
        
        return normalized
    
    def get_last_contacted_profiles(self, days_back: int = 30, limit: int = 100, debug: bool = False) -> List[Dict]:
        """
        Fetch profiles from Infobip People API that were contacted in the last N days
        
        Args:
            days_back: Number of days to look back
            limit: Maximum number of profiles to fetch
            
        Returns:
            List of profile dictionaries with phone, last_contacted, channel, etc.
        """
        if not self.api_key:
            logger.error("Infobip API key not configured")
            return []
        
        try:
            # Calculate date threshold
            date_from = (timezone.now() - timedelta(days=days_back)).isoformat()
            if debug:
                print(f"\n[DEBUG] Looking for messages since: {date_from}")
                print(f"[DEBUG] Base URL: {self.base_url}")
                print(f"[DEBUG] API Key: {self.api_key[:10]}...")
            
            # Try Messages API first (to get WhatsApp interactions - sent and received)
            profiles = self._fetch_from_messages_api(date_from, limit, debug)
            
            if not profiles:
                if debug:
                    print("[DEBUG] Messages API returned no results, trying People API")
                # Fallback to People API if Messages API not available
                logger.info("Messages API returned no results, trying People API")
                profiles = self._fetch_from_people_api(date_from, limit, debug)
            
            if debug:
                print(f"[DEBUG] Total profiles fetched: {len(profiles)}")
                logger.info(f"Total profiles fetched: {len(profiles)}")
            
            return profiles
            
        except Exception as e:
            logger.error(f"Error fetching Infobip profiles: {str(e)}", exc_info=True)
            return []
    
    def _fetch_from_people_api(self, date_from: str, limit: int, debug: bool = False) -> List[Dict]:
        """
        Fetch profiles from Infobip People API
        This requires Infobip People module access
        """
        try:
            url = f"{self.base_url}/people/2/profiles"
            
            params = {
                'limit': limit,
                # Filter by last contacted date if API supports it
            }
            
            response = requests.get(
                url,
                headers=self._get_headers(),
                params=params,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                profiles = []
                
                # Log response for debugging
                logger.info(f"People API response: {data}")
                
                # Parse response based on Infobip People API structure
                # This may need adjustment based on actual API response format
                results = data.get('results', [])
                if not results and isinstance(data, list):
                    # Sometimes API returns array directly
                    results = data
                
                for profile in results:
                    phone = profile.get('phoneNumber') or profile.get('phone') or profile.get('phoneNumber')
                    last_contacted = profile.get('lastContacted') or profile.get('lastContactedAt') or profile.get('lastContactedDate')
                    
                    # If no last_contacted but phone exists, still include it
                    if phone:
                        last_contacted_dt = None
                        if last_contacted:
                            # Parse last contacted date
                            try:
                                if isinstance(last_contacted, str):
                                    # Try multiple date formats
                                    try:
                                        last_contacted_dt = datetime.fromisoformat(last_contacted.replace('Z', '+00:00'))
                                    except:
                                        from dateutil.parser import parse
                                        last_contacted_dt = parse(last_contacted)
                                else:
                                    last_contacted_dt = last_contacted
                                
                                # Check if within date range
                                date_from_dt = datetime.fromisoformat(date_from.replace('Z', '+00:00'))
                                if last_contacted_dt < date_from_dt:
                                    continue  # Skip if outside date range
                            except Exception as e:
                                logger.warning(f"Error parsing last_contacted date: {e}, value: {last_contacted}")
                                # Still include the profile even if date parsing fails
                        
                        profiles.append({
                            'phone': self._normalize_phone(phone),
                            'last_contacted': last_contacted_dt,
                            'channel': profile.get('lastContactedChannel') or profile.get('channel', 'SMS'),
                            'profile_id': profile.get('id') or profile.get('externalId') or profile.get('profileId'),
                            'name': profile.get('name') or (profile.get('firstName', '') + ' ' + profile.get('lastName', '')).strip() or '',
                        })
                
                logger.info(f"Parsed {len(profiles)} profiles from People API")
                return profiles
            elif response.status_code == 404:
                logger.info("People API endpoint not available (404) - trying Messages API")
                return []
            else:
                logger.warning(f"People API returned status {response.status_code}: {response.text[:500]}")
                return []
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error fetching from People API: {e}")
            return []
    
    def _fetch_from_messages_api(self, date_from: str, limit: int, debug: bool = False) -> List[Dict]:
        """
        Fetch message logs from Infobip Messages API
        This fetches ANY WhatsApp interaction (sent or received)
        """
        try:
            # Calculate timestamp for date_from
            try:
                date_from_dt = datetime.fromisoformat(date_from.replace('Z', '+00:00'))
                # Ensure timezone aware
                if date_from_dt.tzinfo is None:
                    date_from_dt = timezone.make_aware(date_from_dt)
                from_timestamp = int(date_from_dt.timestamp() * 1000)  # Milliseconds
            except Exception as e:
                if debug:
                    print(f"[DEBUG] Error parsing date: {e}")
                date_from_dt = timezone.now() - timedelta(days=30)
                from_timestamp = int(date_from_dt.timestamp() * 1000)
            
            all_messages = []
            
            # WhatsApp endpoints - prioritize outbound reports (messages you sent)
            # These are more reliable for getting contacts you interacted with
            whatsapp_endpoints = [
                f"{self.base_url}/whatsapp/1/outbound/reports",  # Messages you sent (most reliable)
                f"{self.base_url}/whatsapp/2/reports/outbound",  # Alternative endpoint
                f"{self.base_url}/whatsapp/1/logs",  # General logs
                f"{self.base_url}/whatsapp/2/logs",  # Logs V2
                f"{self.base_url}/whatsapp/logs",  # Generic logs
                f"{self.base_url}/whatsapp/1/inbound/reports",  # Messages you received
            ]
            
            # Try WhatsApp endpoints first (primary)
            for url in whatsapp_endpoints:
                try:
                    # Try different parameter formats
                    # Try without date filter FIRST to see if ANY messages exist
                    params_list = [
                        {'limit': limit},  # No date filter - get most recent messages
                        {'limit': limit, 'from': from_timestamp},  # With date filter
                        {'limit': limit, 'sentSince': date_from_dt.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'},  # ISO format
                    ]
                    
                    for params in params_list:
                        try:
                            response = requests.get(
                                url,
                                headers=self._get_headers(),
                                params=params,
                                timeout=30
                            )
                            
                            if debug:
                                logger.info(f"WhatsApp API URL: {url}")
                                logger.info(f"WhatsApp API Params: {params}")
                                logger.info(f"WhatsApp API Status: {response.status_code}")
                                logger.info(f"WhatsApp API Response Headers: {dict(response.headers)}")
                                if response.status_code != 200:
                                    logger.error(f"WhatsApp API Error Response: {response.text[:2000]}")
                                else:
                                    try:
                                        data = response.json()
                                        logger.info(f"WhatsApp API Response Data (first 500 chars): {str(data)[:500]}")
                                        if isinstance(data, dict):
                                            logger.info(f"Response keys: {list(data.keys())}")
                                            if 'results' in data:
                                                logger.info(f"Results count: {len(data.get('results', []))}")
                                    except:
                                        logger.warning(f"Response is not JSON: {response.text[:500]}")
                            
                            if response.status_code == 200:
                                data = response.json()
                                messages = data.get('results', [])
                                if not messages and isinstance(data, list):
                                    messages = data
                                if messages:
                                    all_messages.extend(messages)
                                    logger.info(f"Fetched {len(messages)} WhatsApp messages from {url}")
                                    if debug:
                                        print(f"[DEBUG] ✓ SUCCESS! Found {len(messages)} messages from {url}")
                                    break  # Found working endpoint/params combo
                                elif response.status_code == 200 and debug:
                                    print(f"[DEBUG] ⚠ Endpoint {url} works but returned 0 messages")
                                    print(f"[DEBUG]   This means there are NO WhatsApp messages in your account")
                                    print(f"[DEBUG]   OR no messages in the date range you specified")
                                    print(f"[DEBUG]   Try sending a test WhatsApp message first, then sync again")
                            elif response.status_code == 404:
                                continue  # Try next endpoint
                        except Exception as e:
                            if debug:
                                logger.warning(f"Error with params {params} on {url}: {e}")
                            continue
                            
                except Exception as e:
                    if debug:
                        logger.warning(f"Error fetching from {url}: {e}")
                    continue
            
            # Fallback to SMS if WhatsApp not available
            if not all_messages:
                sms_endpoints = [
                    f"{self.base_url}/sms/2/logs",
                    f"{self.base_url}/sms/1/logs",
                ]
                for url in sms_endpoints:
                    try:
                        params = {'limit': limit, 'from': from_timestamp}
                        response = requests.get(url, headers=self._get_headers(), params=params, timeout=30)
                        if response.status_code == 200:
                            data = response.json()
                            messages = data.get('results', [])
                            if not messages and isinstance(data, list):
                                messages = data
                            if messages:
                                all_messages.extend(messages)
                                logger.info(f"Fetched {len(messages)} SMS messages from {url}")
                    except:
                        continue
            
            if not all_messages:
                logger.info("No messages found from any endpoint")
                return []
            
            # Group by phone number and get latest interaction
            contacts = {}
            for message in all_messages:
                # For outbound reports: 'to' is the recipient (who you messaged)
                # For inbound reports: 'from' is the sender (who messaged you)
                # We want both - anyone you interacted with
                phone = (
                    message.get('to') or  # Outbound: recipient
                    message.get('from') or  # Inbound: sender
                    message.get('destination') or 
                    message.get('recipient') or
                    message.get('phoneNumber') or
                    message.get('fromNumber') or
                    message.get('toNumber')
                )
                
                # Get timestamp - prioritize sentAt for outbound, receivedAt for inbound
                interaction_time = (
                    message.get('sentAt') or  # When you sent (outbound)
                    message.get('receivedAt') or  # When received (inbound)
                    message.get('sentAtDateTime') or 
                    message.get('receivedAtDateTime') or
                    message.get('doneAt') or  # When message was delivered
                    message.get('timestamp') or
                    message.get('createdAt')
                )
                
                # Get channel
                channel = message.get('channel') or message.get('messageType') or 'WHATSAPP'
                
                if phone:
                    phone = self._normalize_phone(phone)
                    
                    # Parse interaction time
                    try:
                        if isinstance(interaction_time, str):
                            try:
                                interaction_dt = datetime.fromisoformat(interaction_time.replace('Z', '+00:00'))
                            except:
                                from dateutil.parser import parse
                                interaction_dt = parse(interaction_time)
                        elif isinstance(interaction_time, int):
                            # Timestamp in milliseconds
                            interaction_dt = datetime.fromtimestamp(interaction_time / 1000, tz=timezone.utc)
                        else:
                            interaction_dt = interaction_time
                        
                        # Keep only the latest interaction per phone
                        if phone not in contacts or (interaction_dt and interaction_dt > contacts[phone]['last_contacted']):
                            contacts[phone] = {
                                'phone': phone,
                                'last_contacted': interaction_dt,
                                'channel': channel,
                                'profile_id': None,
                                'name': '',
                            }
                    except Exception as e:
                        if debug:
                            logger.warning(f"Error parsing message data: {e}, message keys: {list(message.keys())}")
                        continue
            
            logger.info(f"Found {len(contacts)} unique phone numbers from {len(all_messages)} messages")
            return list(contacts.values())
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error fetching from Messages API: {e}")
            return []
    
    def get_profile_by_phone(self, phone: str) -> Optional[Dict]:
        """
        Get a single profile by phone number
        """
        if not self.api_key:
            return None
        
        try:
            normalized_phone = self._normalize_phone(phone)
            
            # Try People API
            url = f"{self.base_url}/people/2/profiles"
            params = {'phoneNumber': normalized_phone}
            
            response = requests.get(
                url,
                headers=self._get_headers(),
                params=params,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('results'):
                    profile = data['results'][0]
                    return {
                        'phone': normalized_phone,
                        'last_contacted': profile.get('lastContacted'),
                        'channel': profile.get('lastContactedChannel', 'SMS'),
                        'profile_id': profile.get('id'),
                        'name': profile.get('name', ''),
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"Error fetching profile by phone: {e}")
            return None
    
    def test_connection(self) -> Dict[str, any]:
        """
        Test Infobip API connection
        Returns dict with success status and message
        """
        if not self.api_key:
            return {
                'success': False,
                'message': 'Infobip API key not configured'
            }
        
        try:
            # Try a simple API call to test connection
            url = f"{self.base_url}/account/1/balance"
            response = requests.get(
                url,
                headers=self._get_headers(),
                timeout=10
            )
            
            if response.status_code == 200:
                return {
                    'success': True,
                    'message': 'Connection successful',
                    'data': response.json()
                }
            elif response.status_code == 401:
                return {
                    'success': False,
                    'message': 'Authentication failed - check API key'
                }
            else:
                return {
                    'success': False,
                    'message': f'API returned status {response.status_code}: {response.text[:200]}'
                }
                
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'message': f'Connection error: {str(e)}'
            }
    
    def check_whatsapp_connection(self) -> Dict[str, any]:
        """
        Check if WhatsApp is connected and configured
        Returns dict with WhatsApp connection status and details
        """
        if not self.api_key:
            return {
                'success': False,
                'message': 'Infobip API key not configured'
            }
        
        whatsapp_status = {
            'whatsapp_enabled': False,
            'senders': [],
            'can_send': False,
            'endpoint_status': {},
            'messages_count': 0
        }
        
        # Try multiple WhatsApp endpoints to check connectivity
        whatsapp_endpoints = [
            ('/whatsapp/1/senders', 'Senders'),  # Check if WhatsApp senders are registered
            ('/whatsapp/2/logs', 'Message Logs V2'),  # Check message logs
            ('/whatsapp/1/logs', 'Message Logs'),  # Alternative logs endpoint
        ]
        
        try:
            for endpoint_path, endpoint_name in whatsapp_endpoints:
                try:
                    url = f"{self.base_url}{endpoint_path}"
                    # Try with minimal params
                    params = {'limit': 1}
                    
                    response = requests.get(
                        url,
                        headers=self._get_headers(),
                        params=params,
                        timeout=10
                    )
                    
                    status_info = {
                        'status_code': response.status_code,
                        'accessible': response.status_code in [200, 400],  # 400 might mean wrong params but endpoint exists
                    }
                    
                    if response.status_code == 200:
                        data = response.json()
                        whatsapp_status['whatsapp_enabled'] = True
                        
                        # Check for senders
                        if 'senders' in endpoint_path and isinstance(data, list):
                            whatsapp_status['senders'] = data[:5]  # Get first 5
                            whatsapp_status['can_send'] = len(data) > 0
                        elif 'logs' in endpoint_path or 'reports' in endpoint_path:
                            results = data.get('results', [])
                            if not results and isinstance(data, list):
                                results = data
                            whatsapp_status['messages_count'] = len(results)
                            if len(results) > 0:
                                whatsapp_status['can_send'] = True
                        
                        status_info['message'] = 'Accessible'
                    elif response.status_code == 404:
                        status_info['message'] = 'Endpoint not found'
                    elif response.status_code == 401:
                        status_info['message'] = 'Authentication failed'
                    else:
                        status_info['message'] = response.text[:100]
                    
                    whatsapp_status['endpoint_status'][endpoint_name] = status_info
                    
                except Exception as e:
                    whatsapp_status['endpoint_status'][endpoint_name] = {
                        'status_code': None,
                        'accessible': False,
                        'message': str(e)[:100]
                    }
            
            # Overall status
            if whatsapp_status.get('whatsapp_connected'):
                return {
                    'success': True,
                    'message': f'WhatsApp is connected! Found {len(whatsapp_status.get("senders", []))} sender(s)',
                    'whatsapp': whatsapp_status
                }
            elif whatsapp_status['whatsapp_enabled']:
                return {
                    'success': True,
                    'message': 'WhatsApp endpoints are accessible',
                    'whatsapp': whatsapp_status
                }
            else:
                # Check if any endpoint responded (even with 404 means API is working)
                any_response = any(
                    ep.get('status_code') is not None 
                    for ep in whatsapp_status['endpoint_status'].values()
                )
                if any_response:
                    return {
                        'success': False,
                        'message': 'Infobip API is accessible but WhatsApp endpoints may not be enabled or configured',
                        'whatsapp': whatsapp_status
                    }
                else:
                    return {
                        'success': False,
                        'message': 'Could not connect to WhatsApp endpoints. Check API key and base URL.',
                        'whatsapp': whatsapp_status
                    }
                    
        except Exception as e:
            return {
                'success': False,
                'message': f'Error checking WhatsApp connection: {str(e)}',
                'whatsapp': whatsapp_status
            }

