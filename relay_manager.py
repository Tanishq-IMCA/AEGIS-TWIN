import os
import logging
from supabase import create_client, Client
from datetime import datetime

class RelayService:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RelayService, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
            
        self.db_url = os.environ.get('RELAY_DB_URL')
        self.db_key = os.environ.get('RELAY_DB_KEY')
        self.client = None
        self.active = False
        
        if self.db_url and self.db_key:
            try:
                # Basic normalization for Supabase URLs
                if not self.db_url.startswith('http'):
                    self.db_url = f"https://{self.db_url}"
                
                self.client = create_client(self.db_url, self.db_key)
                # We consider it active if the client is created and keys are present
                self.active = True
                logging.info(f"RELAY SERVICE: Initialized Supabase client for {self.db_url}")
            except Exception as e:
                logging.error(f"RELAY SERVICE: Initialization failed: {e}")
        else:
            logging.info("RELAY SERVICE: Missing RELAY_DB_URL or RELAY_DB_KEY. Staying in Local Mode.")
            
        self._initialized = True

    def push(self, target_id, sender_id, payload, msg_type):
        if not self.active:
            return False, "Relay inactive"
        
        try:
            data = {
                "target_nexus": target_id,
                "source_nexus": sender_id,
                "payload": payload,
                "type": msg_type,
                "status": 0, # Sent
                "timestamp": datetime.utcnow().isoformat()
            }
            self.client.table('packets').insert(data).execute()
            return True, None
        except Exception as e:
            return False, str(e)

    def pull(self, my_id):
        if not self.active:
            return []
            
        try:
            # Fetch pending packets for this instance
            response = self.client.table('packets').select("*").eq("target_nexus", my_id).eq("status", 0).execute()
            # Supabase response data is accessed directly
            packets = getattr(response, 'data', [])
            
            # Mark as delivered
            if packets:
                ids = [p['id'] for p in packets]
                self.client.table('packets').update({"status": 1}).in_("id", ids).execute()
            
            return packets
        except Exception as e:
            # Handle both dictionary-style errors from postgrest and standard exceptions
            error_msg = str(e)
            if "PGRST205" in error_msg or "Could not find the table" in error_msg:
                logging.warning("RELAY SERVICE: Table 'packets' missing in Supabase. Please create it.")
            else:
                logging.error(f"RELAY SERVICE PULL ERROR: {e}")
            return []

    def announce_presence(self, my_id, friendly_name):
        if not self.active:
            return
        try:
            data = {
                "nexus_id": my_id,
                "friendly_name": friendly_name,
                "last_seen": datetime.utcnow().isoformat()
            }
            # Upsert presence
            self.client.table('peers').upsert(data, on_conflict='nexus_id').execute()
        except Exception as e:
            logging.error(f"RELAY SERVICE ANNOUNCE ERROR: {e}")

    def get_peers(self):
        if not self.active:
            return []
        try:
            # Get peers seen in the last 5 minutes
            response = self.client.table('peers').select("*").execute()
            return getattr(response, 'data', [])
        except Exception as e:
            logging.error(f"RELAY SERVICE GET PEERS ERROR: {e}")
            return []
