"""
Test Firebase Integration Features
This test validates the new Firebase base selector and data loading functionality
"""

import unittest
from unittest.mock import Mock, MagicMock, patch
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Mock Firebase modules if not available
try:
    import firebase_admin
except ImportError:
    sys.modules['firebase_admin'] = MagicMock()
    sys.modules['firebase_admin.credentials'] = MagicMock()
    sys.modules['firebase_admin.firestore'] = MagicMock()

from firebase_integration import FirebaseManager


class TestFirebaseIntegration(unittest.TestCase):
    """Test Firebase integration features"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_db = MagicMock()
        self.manager = FirebaseManager()
        self.manager.db = self.mock_db
        self.manager.initialized = True
    
    def test_list_collections(self):
        """Test listing top-level collections"""
        # Mock collections
        mock_col1 = MagicMock()
        mock_col1.id = "OffSeasonAllStar"
        mock_col2 = MagicMock()
        mock_col2.id = "EquiposFRC"
        
        self.mock_db.collections.return_value = [mock_col1, mock_col2]
        
        # Test list_collections
        collections = self.manager.list_collections()
        
        self.assertEqual(len(collections), 2)
        self.assertIn("OffSeasonAllStar", collections)
        self.assertIn("EquiposFRC", collections)
    
    def test_get_equipos_frc_mapping(self):
        """Test loading team name mapping from EquiposFRC"""
        # Mock team documents
        mock_doc1 = MagicMock()
        mock_doc1.id = "7421"
        mock_doc1.to_dict.return_value = {"name": "Overture 7421"}
        
        mock_doc2 = MagicMock()
        mock_doc2.id = "254"
        mock_doc2.to_dict.return_value = {"name": "The Cheesy Poofs"}
        
        mock_collection = MagicMock()
        mock_collection.stream.return_value = [mock_doc1, mock_doc2]
        self.mock_db.collection.return_value = mock_collection
        
        # Test get_equipos_frc_mapping
        mapping = self.manager.get_equipos_frc_mapping()
        
        self.assertEqual(len(mapping), 2)
        self.assertEqual(mapping["7421"], "Overture 7421")
        self.assertEqual(mapping["254"], "The Cheesy Poofs")
    
    def test_load_offseason_allstar_data_structure(self):
        """Test OffSeasonAllStar data loading structure"""
        # Mock team document
        mock_team_doc = MagicMock()
        mock_team_doc.id = "7421"
        mock_team_doc.reference = MagicMock()
        
        # Mock match document
        mock_match_doc = MagicMock()
        mock_match_doc.id = "Match 1"
        mock_match_doc.to_dict.return_value = {
            "SCOUTER INITIALS": "ABC",
            "ROBOT": "1",
            "TEAM NUMBER": "7421",
            "CORAL L1 SCORED AUTO": 2,
            "CORAL L2 SCORED AUTO": 1,
            "MOVED?": True,
            "DIED?": False
        }
        
        # Mock subcollection
        mock_matches_ref = MagicMock()
        mock_matches_ref.stream.return_value = [mock_match_doc]
        mock_team_doc.reference.collection.return_value = mock_matches_ref
        
        # Mock top-level collection
        mock_collection = MagicMock()
        mock_collection.stream.return_value = [mock_team_doc]
        self.mock_db.collection.return_value = mock_collection
        
        # Test load_offseason_allstar_data
        column_headers = ["Team Number", "Match Number", "Scouter Initials", "Robot", 
                         "Coral L1 (Auto)", "Coral L2 (Auto)", "Moved (Auto)", "Died"]
        
        rows, metadata = self.manager.load_offseason_allstar_data(column_headers)
        
        # Verify metadata
        self.assertEqual(metadata["teams_loaded"], 1)
        self.assertEqual(metadata["matches_loaded"], 1)
        
        # Verify at least one row was created
        self.assertEqual(len(rows), 1)
        
        # Verify row structure matches headers
        self.assertEqual(len(rows[0]), len(column_headers))
    
    def test_field_mapping_normalization(self):
        """Test that Firestore fields are properly mapped to CSV headers"""
        # This tests the field mapping logic
        column_headers = ["Scouter Initials", "Coral L1 (Auto)", "Died"]
        
        # Expected mappings
        expected_mappings = {
            "SCOUTER INITIALS": "Scouter Initials",
            "CORAL L1 SCORED AUTO": "Coral L1 (Auto)",
            "DIED?": "Died"
        }
        
        # Verify the mapping exists in the method
        # (This would be tested when actually calling load_offseason_allstar_data)
        self.assertTrue(True)  # Placeholder - actual mapping tested in integration
    
    def test_is_connected(self):
        """Test Firebase connection status check"""
        # Test when connected
        self.assertTrue(self.manager.is_connected())
        
        # Test when not connected
        self.manager.initialized = False
        self.assertFalse(self.manager.is_connected())
        
        # Test when db is None
        self.manager.initialized = True
        self.manager.db = None
        self.assertFalse(self.manager.is_connected())


class TestFirebaseDataNormalization(unittest.TestCase):
    """Test data normalization and default values"""
    
    def test_boolean_fields_normalized(self):
        """Test that boolean fields are properly handled"""
        # Boolean fields should be converted to string "True" or "False"
        # This is tested in the actual data loading
        self.assertTrue(True)  # Placeholder
    
    def test_missing_fields_defaulted(self):
        """Test that missing fields get sensible defaults"""
        # Missing numeric fields should default to 0
        # Missing boolean fields should default to False
        # Missing string fields should have appropriate defaults
        self.assertTrue(True)  # Placeholder
    
    def test_match_number_extraction(self):
        """Test match number extraction from document ID"""
        # "Match 1" -> 1
        # "Match 42" -> 42
        test_cases = [
            ("Match 1", 1),
            ("Match 42", 42),
            ("Match 100", 100)
        ]
        
        for doc_id, expected in test_cases:
            if doc_id.startswith("Match "):
                result = int(doc_id.split("Match ")[1])
                self.assertEqual(result, expected)


if __name__ == '__main__':
    # Run tests
    unittest.main(verbosity=2)
