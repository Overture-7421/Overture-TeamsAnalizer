"""
Firebase Integration Module for Alliance Simulator
Provides NoSQL database connectivity for storing and retrieving scouting data
"""

import json
import os
from typing import List, Dict, Optional, Any, Tuple
import pandas as pd
from datetime import datetime
from collections import defaultdict

try:
    import firebase_admin
    from firebase_admin import credentials, firestore
    FIREBASE_AVAILABLE = True
except ImportError:
    FIREBASE_AVAILABLE = False
    print("Warning: Firebase Admin SDK not installed. Firebase features will be disabled.")


class FirebaseManager:
    """Manages Firebase Firestore database connections and operations"""
    
    def __init__(self, credentials_path: Optional[str] = None):
        """
        Initialize Firebase connection
        
        Args:
            credentials_path: Path to Firebase service account credentials JSON file
        """
        self.db = None
        self.initialized = False
        self.credentials_path = credentials_path or os.getenv('FIREBASE_CREDENTIALS_PATH')
        
        if FIREBASE_AVAILABLE and self.credentials_path and os.path.exists(self.credentials_path):
            try:
                self._initialize_firebase()
            except Exception as e:
                print(f"Firebase initialization error: {e}")
    
    def _initialize_firebase(self):
        """Initialize Firebase Admin SDK"""
        if not firebase_admin._apps:
            cred = credentials.Certificate(self.credentials_path)
            firebase_admin.initialize_app(cred)
        
        self.db = firestore.client()
        self.initialized = True
        print("✓ Firebase initialized successfully")
    
    def is_connected(self) -> bool:
        """Check if Firebase is connected and ready"""
        return self.initialized and self.db is not None
    
    # ==================== Scouting Data Operations ====================
    
    def upload_scouting_data(self, data: List[Dict], collection_name: str = 'scouting_data') -> bool:
        """
        Upload scouting data to Firebase
        
        Args:
            data: List of dictionaries containing scouting data
            collection_name: Firestore collection name
            
        Returns:
            True if successful, False otherwise
        """
        if not self.is_connected():
            return False
        
        try:
            batch = self.db.batch()
            collection_ref = self.db.collection(collection_name)
            
            for idx, record in enumerate(data):
                # Generate unique document ID based on team, match, and timestamp
                team = record.get('Team Number', record.get('team', 'unknown'))
                match = record.get('Match Number', record.get('match', 'unknown'))
                timestamp = datetime.now().isoformat()
                doc_id = f"{team}_{match}_{idx}_{timestamp}"
                
                doc_ref = collection_ref.document(doc_id)
                
                # Add metadata
                record_with_metadata = record.copy()
                record_with_metadata['uploaded_at'] = firestore.SERVER_TIMESTAMP
                record_with_metadata['doc_id'] = doc_id
                
                batch.set(doc_ref, record_with_metadata)
            
            batch.commit()
            print(f"✓ Uploaded {len(data)} records to Firebase")
            return True
            
        except Exception as e:
            print(f"Error uploading data to Firebase: {e}")
            return False
    
    def get_all_scouting_data(self, collection_name: str = 'scouting_data') -> List[Dict]:
        """
        Retrieve all scouting data from Firebase
        
        Args:
            collection_name: Firestore collection name
            
        Returns:
            List of dictionaries containing scouting data
        """
        if not self.is_connected():
            return []
        
        try:
            docs = self.db.collection(collection_name).stream()
            data = []
            
            for doc in docs:
                record = doc.to_dict()
                # Remove metadata fields if present
                record.pop('uploaded_at', None)
                record.pop('doc_id', None)
                data.append(record)
            
            print(f"✓ Retrieved {len(data)} records from Firebase")
            return data
            
        except Exception as e:
            print(f"Error retrieving data from Firebase: {e}")
            return []
    
    def get_scouting_data_by_team(self, team_number: int, collection_name: str = 'scouting_data') -> List[Dict]:
        """
        Retrieve scouting data for a specific team
        
        Args:
            team_number: Team number to filter by
            collection_name: Firestore collection name
            
        Returns:
            List of dictionaries containing scouting data for the team
        """
        if not self.is_connected():
            return []
        
        try:
            # Query for both 'Team Number' and 'team' fields
            query1 = self.db.collection(collection_name).where('Team Number', '==', team_number)
            query2 = self.db.collection(collection_name).where('team', '==', team_number)
            
            data = []
            for doc in query1.stream():
                data.append(doc.to_dict())
            for doc in query2.stream():
                data.append(doc.to_dict())
            
            # Remove duplicates
            seen = set()
            unique_data = []
            for record in data:
                doc_id = record.get('doc_id', str(record))
                if doc_id not in seen:
                    seen.add(doc_id)
                    record.pop('uploaded_at', None)
                    record.pop('doc_id', None)
                    unique_data.append(record)
            
            print(f"✓ Retrieved {len(unique_data)} records for team {team_number}")
            return unique_data
            
        except Exception as e:
            print(f"Error retrieving team data from Firebase: {e}")
            return []
    
    def get_scouting_data_by_match(self, match_number: int, collection_name: str = 'scouting_data') -> List[Dict]:
        """
        Retrieve scouting data for a specific match
        
        Args:
            match_number: Match number to filter by
            collection_name: Firestore collection name
            
        Returns:
            List of dictionaries containing scouting data for the match
        """
        if not self.is_connected():
            return []
        
        try:
            # Query for both 'Match Number' and 'match' fields
            query1 = self.db.collection(collection_name).where('Match Number', '==', match_number)
            query2 = self.db.collection(collection_name).where('match', '==', match_number)
            
            data = []
            for doc in query1.stream():
                data.append(doc.to_dict())
            for doc in query2.stream():
                data.append(doc.to_dict())
            
            # Remove duplicates
            seen = set()
            unique_data = []
            for record in data:
                doc_id = record.get('doc_id', str(record))
                if doc_id not in seen:
                    seen.add(doc_id)
                    record.pop('uploaded_at', None)
                    record.pop('doc_id', None)
                    unique_data.append(record)
            
            print(f"✓ Retrieved {len(unique_data)} records for match {match_number}")
            return unique_data
            
        except Exception as e:
            print(f"Error retrieving match data from Firebase: {e}")
            return []
    
    def delete_scouting_data(self, doc_id: str, collection_name: str = 'scouting_data') -> bool:
        """
        Delete a specific scouting record
        
        Args:
            doc_id: Document ID to delete
            collection_name: Firestore collection name
            
        Returns:
            True if successful, False otherwise
        """
        if not self.is_connected():
            return False
        
        try:
            self.db.collection(collection_name).document(doc_id).delete()
            print(f"✓ Deleted document {doc_id}")
            return True
            
        except Exception as e:
            print(f"Error deleting document from Firebase: {e}")
            return False
    
    def clear_collection(self, collection_name: str = 'scouting_data') -> bool:
        """
        Clear all documents from a collection
        
        Args:
            collection_name: Firestore collection name
            
        Returns:
            True if successful, False otherwise
        """
        if not self.is_connected():
            return False
        
        try:
            docs = self.db.collection(collection_name).stream()
            batch = self.db.batch()
            count = 0
            
            for doc in docs:
                batch.delete(doc.reference)
                count += 1
                
                # Firestore batch limit is 500
                if count % 500 == 0:
                    batch.commit()
                    batch = self.db.batch()
            
            if count % 500 != 0:
                batch.commit()
            
            print(f"✓ Cleared {count} documents from {collection_name}")
            return True
            
        except Exception as e:
            print(f"Error clearing collection from Firebase: {e}")
            return False
    
    # ==================== Data Conversion ====================
    
    def firebase_to_csv_format(self, data: List[Dict]) -> pd.DataFrame:
        """
        Convert Firebase data to CSV format compatible with analyzer
        
        Args:
            data: List of dictionaries from Firebase
            
        Returns:
            Pandas DataFrame in CSV format
        """
        if not data:
            return pd.DataFrame()
        
        return pd.DataFrame(data)
    
    def csv_to_firebase_format(self, csv_data: pd.DataFrame) -> List[Dict]:
        """
        Convert CSV data to Firebase format
        
        Args:
            csv_data: Pandas DataFrame from CSV
            
        Returns:
            List of dictionaries for Firebase
        """
        return csv_data.to_dict('records')
    
    # ==================== Configuration Management ====================
    
    def save_config(self, config: Dict, config_name: str = 'app_config') -> bool:
        """
        Save application configuration to Firebase
        
        Args:
            config: Configuration dictionary
            config_name: Configuration document name
            
        Returns:
            True if successful, False otherwise
        """
        if not self.is_connected():
            return False
        
        try:
            self.db.collection('configurations').document(config_name).set(config)
            print(f"✓ Saved configuration '{config_name}'")
            return True
            
        except Exception as e:
            print(f"Error saving configuration to Firebase: {e}")
            return False
    
    def load_config(self, config_name: str = 'app_config') -> Optional[Dict]:
        """
        Load application configuration from Firebase
        
        Args:
            config_name: Configuration document name
            
        Returns:
            Configuration dictionary or None if not found
        """
        if not self.is_connected():
            return None
        
        try:
            doc = self.db.collection('configurations').document(config_name).get()
            
            if doc.exists:
                print(f"✓ Loaded configuration '{config_name}'")
                return doc.to_dict()
            else:
                print(f"Configuration '{config_name}' not found")
                return None
                
        except Exception as e:
            print(f"Error loading configuration from Firebase: {e}")
            return None
    
    # ==================== Statistics Cache ====================
    
    def cache_statistics(self, stats: Dict, cache_name: str = 'latest_stats') -> bool:
        """
        Cache computed statistics in Firebase for faster retrieval
        
        Args:
            stats: Statistics dictionary
            cache_name: Cache document name
            
        Returns:
            True if successful, False otherwise
        """
        if not self.is_connected():
            return False
        
        try:
            cache_data = {
                'stats': stats,
                'cached_at': firestore.SERVER_TIMESTAMP,
                'cache_name': cache_name
            }
            
            self.db.collection('statistics_cache').document(cache_name).set(cache_data)
            print(f"✓ Cached statistics '{cache_name}'")
            return True
            
        except Exception as e:
            print(f"Error caching statistics to Firebase: {e}")
            return False
    
    def get_cached_statistics(self, cache_name: str = 'latest_stats', max_age_minutes: int = 30) -> Optional[Dict]:
        """
        Retrieve cached statistics from Firebase
        
        Args:
            cache_name: Cache document name
            max_age_minutes: Maximum age of cache in minutes
            
        Returns:
            Statistics dictionary or None if cache is expired or not found
        """
        if not self.is_connected():
            return None
        
        try:
            doc = self.db.collection('statistics_cache').document(cache_name).get()
            
            if doc.exists:
                cache_data = doc.to_dict()
                cached_at = cache_data.get('cached_at')
                
                if cached_at:
                    # Check if cache is still valid
                    age_seconds = (datetime.now() - cached_at.replace(tzinfo=None)).total_seconds()
                    if age_seconds < max_age_minutes * 60:
                        print(f"✓ Retrieved cached statistics '{cache_name}' (age: {age_seconds:.0f}s)")
                        return cache_data.get('stats')
                    else:
                        print(f"Cache '{cache_name}' expired (age: {age_seconds:.0f}s)")
                
                return None
            else:
                print(f"Cache '{cache_name}' not found")
                return None
                
        except Exception as e:
            print(f"Error retrieving cached statistics from Firebase: {e}")
            return None
    
    # ==================== Base/Collection Management ====================
    
    def list_collections(self) -> List[str]:
        """
        List all top-level collections (bases) in Firestore
        
        Returns:
            List of collection names
        """
        if not self.is_connected():
            return []
        
        try:
            collections = self.db.collections()
            collection_names = [col.id for col in collections]
            print(f"✓ Found {len(collection_names)} collections: {collection_names}")
            return collection_names
        except Exception as e:
            print(f"Error listing collections: {e}")
            return []
    
    def get_equipos_frc_mapping(self) -> Dict[str, str]:
        """
        Load team name mapping from EquiposFRC collection
        
        Returns:
            Dictionary mapping team number (string) to team name (string)
        """
        if not self.is_connected():
            return {}
        
        try:
            team_mapping = {}
            docs = self.db.collection('EquiposFRC').stream()
            
            for doc in docs:
                team_number = doc.id  # Document ID is the team number
                team_name = doc.to_dict().get('name', doc.to_dict().get('team_name', ''))
                
                # Handle case where the entire document is just a string value
                if not team_name and isinstance(doc.to_dict(), dict):
                    # Try to get first value if it's a simple document
                    doc_dict = doc.to_dict()
                    if len(doc_dict) == 1:
                        team_name = list(doc_dict.values())[0]
                    # Or if the document has no structure, use the team number as fallback
                    if not team_name:
                        team_name = f"Team {team_number}"
                
                team_mapping[team_number] = team_name
            
            print(f"✓ Loaded {len(team_mapping)} team names from EquiposFRC")
            return team_mapping
        except Exception as e:
            print(f"Error loading EquiposFRC mapping: {e}")
            return {}
    
    def load_offseason_allstar_data(self, column_headers: List[str]) -> Tuple[List[List[Any]], Dict[str, Any]]:
        """
        Load match data from OffSeasonAllStar collection
        
        Args:
            column_headers: Expected column headers for the output CSV format
            
        Returns:
            Tuple of (rows_list, metadata_dict) where:
            - rows_list: List of rows with data matching column_headers
            - metadata_dict: Contains counts, warnings, and other load information
        """
        if not self.is_connected():
            return [], {"error": "Not connected to Firebase"}
        
        try:
            rows = []
            metadata = {
                "teams_loaded": 0,
                "matches_loaded": 0,
                "warnings": [],
                "missing_fields": defaultdict(int)
            }
            
            # Field mapping from Firestore to CSV headers
            field_mapping = {
                "SCOUTER INITIALS": "Scouter Initials",
                "ROBOT": "Robot",
                "FUTURE ALLIANCE IN QUALY?": "Future Alliance",
                "STARTING POSITION": "Starting Position",
                "NO SHOW": "No Show",
                "MOVED?": "Moved (Auto)",
                "CORAL L1 SCORED AUTO": "Coral L1 (Auto)",
                "CORAL L2 SCORED AUTO": "Coral L2 (Auto)",
                "CORAL L3 SCORED AUTO": "Coral L3 (Auto)",
                "CORAL L4 SCORED AUTO": "Coral L4 (Auto)",
                "BARGE ALGAE SCORED AUTO": "Barge Algae (Auto)",
                "PROCESSOR ALGAE SCORED AUTO": "Processor Algae (Auto)",
                "DISLODGED ALGAE? AUTO": "Dislodged Algae (Auto)",
                "AUTO FOUL": "Foul (Auto)",
                "DISLODGED ALGAE? TELEOP": "Dislodged Algae (Teleop)",
                "PICKUP LOCATION": "Pickup Location",
                "CORAL L1 SCORED TELEOP": "Coral L1 (Teleop)",
                "CORAL L2 SCORED TELEOP": "Coral L2 (Teleop)",
                "CORAL L3 SCORED TELEOP": "Coral L3 (Teleop)",
                "CORAL L4 SCORED TELEOP": "Coral L4 (Teleop)",
                "BARGE ALGAE SCORED TELEOP": "Barge Algae (Teleop)",
                "PROCESSOR ALGAE SCORED TELEOP": "Processor Algae (Teleop)",
                "CROSSED FIELD/PLAYED DEFENSE?": "Crossed Field/Defense",
                "TIPPED/FELL OVER?": "Tipped/Fell",
                "TOUCHED OPPOSING CAGE": "Touched Opposing Cage",
                "DIED?": "Died",
                "END POSITION": "End Position",
                "BROKE?": "Broke",
                "DEFENDED?": "Defended",
                "CORAL HP MISTAKE?": "Coral HP Mistake",
                "YELLOW/RED CARD": "Yellow/Red Card"
            }
            
            # Default values for missing fields
            default_values = {
                "Scouter Initials": "",
                "Robot": "1",
                "Future Alliance": "Unknown",
                "Starting Position": "Unknown",
                "No Show": False,
                "Moved (Auto)": False,
                "Coral L1 (Auto)": 0,
                "Coral L2 (Auto)": 0,
                "Coral L3 (Auto)": 0,
                "Coral L4 (Auto)": 0,
                "Barge Algae (Auto)": 0,
                "Processor Algae (Auto)": 0,
                "Dislodged Algae (Auto)": False,
                "Foul (Auto)": 0,
                "Dislodged Algae (Teleop)": False,
                "Pickup Location": "Unknown",
                "Coral L1 (Teleop)": 0,
                "Coral L2 (Teleop)": 0,
                "Coral L3 (Teleop)": 0,
                "Coral L4 (Teleop)": 0,
                "Barge Algae (Teleop)": 0,
                "Processor Algae (Teleop)": 0,
                "Crossed Field/Defense": False,
                "Tipped/Fell": False,
                "Touched Opposing Cage": 0,
                "Died": False,
                "End Position": "Unknown",
                "Broke": False,
                "Defended": False,
                "Coral HP Mistake": False,
                "Yellow/Red Card": "None"
            }
            
            # Get all team documents in OffSeasonAllStar
            team_docs = self.db.collection('OffSeasonAllStar').stream()
            
            for team_doc in team_docs:
                team_number = team_doc.id
                metadata["teams_loaded"] += 1
                
                # Get Matches subcollection for this team
                matches_ref = team_doc.reference.collection('Matches')
                match_docs = matches_ref.stream()
                
                match_count = 0
                for match_doc in match_docs:
                    match_count += 1
                    match_data = match_doc.to_dict()
                    
                    # Extract match number from document ID (e.g., "Match 1" -> 1)
                    match_id = match_doc.id
                    match_number = 0
                    try:
                        if match_id.startswith("Match "):
                            match_number = int(match_id.split("Match ")[1])
                        else:
                            match_number = int(''.join(filter(str.isdigit, match_id)) or 0)
                    except:
                        match_number = match_count
                    
                    # Build row matching column_headers
                    row = []
                    for header in column_headers:
                        if header == "Team Number":
                            row.append(team_number)
                        elif header == "Match Number":
                            row.append(match_number)
                        else:
                            # Find the Firestore field name that maps to this header
                            firestore_field = None
                            for fs_field, csv_header in field_mapping.items():
                                if csv_header == header:
                                    firestore_field = fs_field
                                    break
                            
                            if firestore_field and firestore_field in match_data:
                                value = match_data[firestore_field]
                                # Convert boolean values to string representation
                                if isinstance(value, bool):
                                    value = str(value)
                                row.append(value)
                            elif header in default_values:
                                row.append(default_values[header])
                                metadata["missing_fields"][header] += 1
                            else:
                                row.append("")
                                metadata["missing_fields"][header] += 1
                    
                    rows.append(row)
                    metadata["matches_loaded"] += 1
                
                if match_count == 0:
                    metadata["warnings"].append(f"Team {team_number} has no matches in Matches subcollection")
            
            print(f"✓ Loaded {metadata['matches_loaded']} matches from {metadata['teams_loaded']} teams")
            if metadata["missing_fields"]:
                print(f"⚠ Missing fields detected: {dict(metadata['missing_fields'])}")
            
            return rows, metadata
        except Exception as e:
            print(f"Error loading OffSeasonAllStar data: {e}")
            import traceback
            traceback.print_exc()
            return [], {"error": str(e)}


def get_firebase_manager(credentials_path: Optional[str] = None) -> FirebaseManager:
    """
    Factory function to get FirebaseManager instance
    
    Args:
        credentials_path: Path to Firebase credentials file
        
    Returns:
        FirebaseManager instance
    """
    return FirebaseManager(credentials_path)
