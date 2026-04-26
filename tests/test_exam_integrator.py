import os
import sys
import unittest
from datetime import datetime

# Add root project dir to python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from lib.exam_integrator import ExamDataIntegrator
from lib.school_system import TeamScoring

class TestExamIntegrator(unittest.TestCase):
    def setUp(self):
        self.integrator = ExamDataIntegrator()
        self.scoring_system = TeamScoring()
        self.programming_csv = os.path.join(os.path.dirname(__file__), "test_pit_scouting_programming.csv")

    def test_integrate_programming_exam(self):
        # Read the test CSV
        results = self.integrator.integrate_programming_exam(self.programming_csv)
        
        # Verify both teams were processed
        self.assertIn("4400", results)
        self.assertIn("4401", results)

        # Check results for Team 4400
        team_4400 = results["4400"]
        self.assertEqual(team_4400.team_number, "4400")
        self.assertEqual(team_4400.max_score, 10.0)
        self.assertEqual(team_4400.raw_score, 8.0)
        self.assertEqual(team_4400.score, 95.0) # Calculated questionnaire_score (100+100+100+80)/4 = 95.0
        
        # Check specific field scores
        field_scores = team_4400.details["field_scores"]
        self.assertEqual(field_scores.get("prog_path_planner"), 100.0) # 'si' -> 100
        self.assertEqual(field_scores.get("prog_auto_change"), 100.0) # 'Sencillo' -> 100
        self.assertEqual(field_scores.get("prog_auto_reliability"), 100.0) # '10 veces siempre' -> 100
        self.assertEqual(field_scores.get("prog_odometry_type"), 80.0) # 'Corrección por april tag' -> 80

        # Check results for Team 4401
        team_4401 = results["4401"]
        self.assertEqual(team_4401.score, 10.0) # Calculated questionnaire_score (0+0+0+40)/4 = 10.0
        field_scores_4401 = team_4401.details["field_scores"]
        self.assertEqual(field_scores_4401.get("prog_path_planner"), 0.0) # 'no' -> 0
        self.assertEqual(field_scores_4401.get("prog_auto_change"), 0.0) # 'Difícil' -> 0
        self.assertEqual(field_scores_4401.get("prog_auto_reliability"), 0.0) # 'Menos de 5' -> 0
        self.assertEqual(field_scores_4401.get("prog_odometry_type"), 40.0) # 'Encoders de llanta' -> 40

    def test_apply_to_scoring_system(self):
        # We need to make sure the teams exist in scoring system before applying scores
        # Usually they are created dynamically or loaded beforehand
        self.scoring_system.update_autonomous_score("4400", 0.0)
        self.scoring_system.update_autonomous_score("4401", 0.0)
        
        # Load the programming exam
        self.integrator.integrate_programming_exam(self.programming_csv)
        
        # Apply to the scoring system
        self.integrator.apply_to_scoring_system(self.scoring_system)
        
        # Check if the scoring system was updated
        team_4400_score = self.scoring_system.teams["4400"]
        self.assertEqual(team_4400_score.autonomous_score, 95.0)
        # It also sets competencies: programming_score >= 70
        self.assertTrue(team_4400_score.competencies.driving_skills)
        self.assertTrue(team_4400_score.competencies.reliability)

        team_4401_score = self.scoring_system.teams["4401"]
        self.assertEqual(team_4401_score.autonomous_score, 10.0)
        self.assertFalse(team_4401_score.competencies.driving_skills)

if __name__ == "__main__":
    unittest.main()
