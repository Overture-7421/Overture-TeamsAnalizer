"""
Exam Data Integrator - Integrates exam CSV files into the SchoolSystem scoring.

Handles 4 types of exams:
- Programming Exam (Examen de Programación)
- Mechanical Exam (Examen Mecánico)  
- Electrical Exam (Examen Eléctrico)
- Competencies Exam (Examen de Competencias)

Each exam CSV has:
- Marca temporal: Timestamp for deduplication (keep latest)
- Puntuación: Score in "X / Y" format
- Team NUMBER: Team number
- Multiple question columns with specific answers
- Final feedback column
"""

import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
import os


@dataclass
class ExamResult:
    """Container for a single exam result after processing"""
    team_number: str
    score: float  # Normalized 0-100
    max_score: float
    raw_score: float
    timestamp: datetime
    feedback: str = ""
    details: Dict = field(default_factory=dict)


class ExamDataIntegrator:
    """
    Integrates exam CSV data into the SchoolSystem scoring.
    Handles deduplication, score parsing, and competency mapping.
    """
    
    def __init__(self):
        self.exam_results: Dict[str, Dict[str, ExamResult]] = {
            "programming": {},
            "mechanical": {},
            "electrical": {},
            "competencies": {}
        }
        self.scouting_comments: Dict[str, List[str]] = {}  # team_number -> list of comments
    
    def _parse_score(self, score_str: str) -> Tuple[float, float]:
        """
        Parse score from "X / Y" format.
        Returns (raw_score, max_score)
        """
        try:
            parts = str(score_str).split("/")
            if len(parts) == 2:
                raw = float(parts[0].strip())
                max_val = float(parts[1].strip())
                return raw, max_val
        except (ValueError, AttributeError):
            pass
        return 0.0, 1.0
    
    def _normalize_score(self, raw: float, max_val: float) -> float:
        """Normalize score to 0-100 scale"""
        if max_val <= 0:
            return 0.0
        return (raw / max_val) * 100
    
    def _parse_timestamp(self, ts_str: str) -> datetime:
        """Parse timestamp from various formats"""
        formats = [
            "%d/%m/%Y %H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
            "%d/%m/%Y %H:%M",
            "%Y-%m-%d %H:%M"
        ]
        for fmt in formats:
            try:
                return datetime.strptime(str(ts_str), fmt)
            except ValueError:
                continue
        return datetime.min
    
    def _clean_and_deduplicate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Clean CSV data and deduplicate by team number, keeping latest entry.
        """
        # Standard column names
        timestamp_col = "Marca temporal"
        team_col = "Team NUMBER"
        score_col = "Puntuación"
        
        if timestamp_col not in df.columns or team_col not in df.columns:
            raise ValueError(f"Required columns not found. Expected: {timestamp_col}, {team_col}")
        
        # Parse timestamps
        df["_parsed_timestamp"] = df[timestamp_col].apply(self._parse_timestamp)
        
        # Convert team number to string
        df[team_col] = df[team_col].astype(str)
        
        # Sort by timestamp descending and keep first (latest) for each team
        df = df.sort_values("_parsed_timestamp", ascending=False)
        df = df.drop_duplicates(subset=[team_col], keep="first")
        
        return df
    
    def _get_feedback_column(self, df: pd.DataFrame) -> str:
        """Find the feedback column (usually the last question about examiner experience)"""
        feedback_keywords = ["examinador", "sentiste", "evaluar"]
        for col in df.columns:
            col_lower = col.lower()
            if any(keyword in col_lower for keyword in feedback_keywords):
                return col
        return ""
    
    def _add_comment(self, team_number: str, comment: str) -> None:
        """Add a scouting comment for a team"""
        if not comment or str(comment).lower() in ["nan", "none", ""]:
            return
        if team_number not in self.scouting_comments:
            self.scouting_comments[team_number] = []
        if comment not in self.scouting_comments[team_number]:
            self.scouting_comments[team_number].append(comment)
    
    def integrate_programming_exam(self, csv_path: str) -> Dict[str, ExamResult]:
        """
        Integrate Programming Exam data.
        
        Maps to:
        - autonomous_score (normalized from exam score)
        - driving_skills competency (if score >= 6/9)
        
        Columns:
        - Software, Language, Vision, Cameras, Autonomous success rate,
          Odometry, Code knowledge, Route change ease, Control orientation
        """
        df = pd.read_csv(csv_path)
        df = self._clean_and_deduplicate(df)
        
        team_col = "Team NUMBER"
        score_col = "Puntuación"
        feedback_col = self._get_feedback_column(df)
        
        results = {}
        
        for _, row in df.iterrows():
            team_number = str(row[team_col])
            raw_score, max_score = self._parse_score(row[score_col])
            normalized = self._normalize_score(raw_score, max_score)
            
            feedback = str(row[feedback_col]) if feedback_col else ""
            self._add_comment(team_number, f"[Programación] {feedback}")
            
            # Extract additional details from specific columns
            details = {}
            for col in df.columns:
                if col not in [team_col, score_col, "Marca temporal", "_parsed_timestamp"]:
                    details[col] = row[col]
            
            result = ExamResult(
                team_number=team_number,
                score=normalized,
                max_score=max_score,
                raw_score=raw_score,
                timestamp=row["_parsed_timestamp"],
                feedback=feedback,
                details=details
            )
            results[team_number] = result
        
        self.exam_results["programming"] = results
        return results
    
    def integrate_mechanical_exam(self, csv_path: str) -> Dict[str, ExamResult]:
        """
        Integrate Mechanical Exam data.
        
        Maps to:
        - mechanical_score
        - tools_score (from equipment question)
        - spare_parts_score (from spare parts question)
        
        Columns:
        - Bumper change time, Checklist, Spare parts, Critical specs,
          Standardized hardware, Robust structure, Battery change, Equipment, Maintenance
        """
        df = pd.read_csv(csv_path)
        df = self._clean_and_deduplicate(df)
        
        team_col = "Team NUMBER"
        score_col = "Puntuación"
        feedback_col = self._get_feedback_column(df)
        
        results = {}
        
        for _, row in df.iterrows():
            team_number = str(row[team_col])
            raw_score, max_score = self._parse_score(row[score_col])
            normalized = self._normalize_score(raw_score, max_score)
            
            feedback = str(row[feedback_col]) if feedback_col else ""
            self._add_comment(team_number, f"[Mecánico] {feedback}")
            
            # Extract details
            details = {}
            for col in df.columns:
                if col not in [team_col, score_col, "Marca temporal", "_parsed_timestamp"]:
                    details[col] = row[col]
            
            result = ExamResult(
                team_number=team_number,
                score=normalized,
                max_score=max_score,
                raw_score=raw_score,
                timestamp=row["_parsed_timestamp"],
                feedback=feedback,
                details=details
            )
            results[team_number] = result
        
        self.exam_results["mechanical"] = results
        return results
    
    def integrate_electrical_exam(self, csv_path: str) -> Dict[str, ExamResult]:
        """
        Integrate Electrical Exam data.
        
        Maps to:
        - electrical_score
        - driver_station_layout_score (from modem placement question)
        
        Columns:
        - CANivore, Cable protection, Switch protection, Exposed components,
          Wiring quality, Cable condition, Wagos vs soldered, CAN issues, Modem placement
        """
        df = pd.read_csv(csv_path)
        df = self._clean_and_deduplicate(df)
        
        team_col = "Team NUMBER"
        score_col = "Puntuación"
        feedback_col = self._get_feedback_column(df)
        
        results = {}
        
        for _, row in df.iterrows():
            team_number = str(row[team_col])
            raw_score, max_score = self._parse_score(row[score_col])
            normalized = self._normalize_score(raw_score, max_score)
            
            feedback = str(row[feedback_col]) if feedback_col else ""
            self._add_comment(team_number, f"[Eléctrico] {feedback}")
            
            # Check modem placement for driver station score
            modem_score = 0
            for col in df.columns:
                if "módem" in col.lower() or "modem" in col.lower():
                    if str(row[col]).lower().strip() == "cumple":
                        modem_score = 100
                    break
            
            details = {"modem_score": modem_score}
            for col in df.columns:
                if col not in [team_col, score_col, "Marca temporal", "_parsed_timestamp"]:
                    details[col] = row[col]
            
            result = ExamResult(
                team_number=team_number,
                score=normalized,
                max_score=max_score,
                raw_score=raw_score,
                timestamp=row["_parsed_timestamp"],
                feedback=feedback,
                details=details
            )
            results[team_number] = result
        
        self.exam_results["electrical"] = results
        return results
    
    def integrate_competencies_exam(self, csv_path: str) -> Dict[str, ExamResult]:
        """
        Integrate Competencies Exam data.
        
        Maps to:
        - reliability competency (from confidence question)
        - commitment competency (from commitment question)
        - team_organization_score (based on overall evaluation)
        - pasar_inspeccion_primera (from inspection question)
        
        Columns:
        - Batteries, Drive team fix problems, First inspection, Commitment observed,
          Reliability, Student/mentor ratio, Repairing on arrival, Examiner experience
        """
        df = pd.read_csv(csv_path)
        df = self._clean_and_deduplicate(df)
        
        team_col = "Team NUMBER"
        score_col = "Puntuación"
        feedback_col = self._get_feedback_column(df)
        
        results = {}
        
        for _, row in df.iterrows():
            team_number = str(row[team_col])
            raw_score, max_score = self._parse_score(row[score_col])
            normalized = self._normalize_score(raw_score, max_score)
            
            feedback = str(row[feedback_col]) if feedback_col else ""
            self._add_comment(team_number, f"[Competencias] {feedback}")
            
            # Extract competency details
            details = {
                "reliability": False,
                "commitment": False,
                "inspection_first": False
            }
            
            for col in df.columns:
                col_lower = col.lower()
                value = str(row[col]).lower().strip()
                
                # Reliability check
                if "confiable" in col_lower or "confiables" in col_lower:
                    details["reliability"] = "inspiran confianza" in value
                
                # Commitment check  
                if "compromiso" in col_lower:
                    details["commitment"] = "cumple" in value or "inspiran" in value
                
                # First inspection
                if "inspección" in col_lower or "inspeccion" in col_lower:
                    details["inspection_first"] = value == "sí" or value == "si"
                
                if col not in [team_col, score_col, "Marca temporal", "_parsed_timestamp"]:
                    details[col] = row[col]
            
            result = ExamResult(
                team_number=team_number,
                score=normalized,
                max_score=max_score,
                raw_score=raw_score,
                timestamp=row["_parsed_timestamp"],
                feedback=feedback,
                details=details
            )
            results[team_number] = result
        
        self.exam_results["competencies"] = results
        return results
    
    def integrate_all_exams(self, exam_files: Dict[str, str]) -> None:
        """
        Integrate all exam files at once.
        
        Args:
            exam_files: Dict with keys 'programming', 'mechanical', 'electrical', 'competencies'
                       and values as file paths
        """
        if "programming" in exam_files and os.path.exists(exam_files["programming"]):
            self.integrate_programming_exam(exam_files["programming"])
        
        if "mechanical" in exam_files and os.path.exists(exam_files["mechanical"]):
            self.integrate_mechanical_exam(exam_files["mechanical"])
        
        if "electrical" in exam_files and os.path.exists(exam_files["electrical"]):
            self.integrate_electrical_exam(exam_files["electrical"])
        
        if "competencies" in exam_files and os.path.exists(exam_files["competencies"]):
            self.integrate_competencies_exam(exam_files["competencies"])
    
    def get_team_exam_summary(self, team_number: str) -> Dict:
        """Get a summary of all exam results for a team"""
        summary = {
            "team_number": team_number,
            "exams": {},
            "comments": self.scouting_comments.get(team_number, []),
            "combined_feedback": ""
        }
        
        for exam_type, results in self.exam_results.items():
            if team_number in results:
                result = results[team_number]
                summary["exams"][exam_type] = {
                    "score": result.score,
                    "raw_score": result.raw_score,
                    "max_score": result.max_score,
                    "feedback": result.feedback
                }
        
        # Combine all feedback
        summary["combined_feedback"] = " | ".join(summary["comments"])
        
        return summary
    
    def apply_to_scoring_system(self, scoring_system) -> None:
        """
        Apply all integrated exam results to a TeamScoring instance.
        
        Args:
            scoring_system: Instance of TeamScoring from school_system
        """
        # Apply programming exam results
        for team_number, result in self.exam_results["programming"].items():
            scoring_system.update_autonomous_score(team_number, result.score)
            # Set driving_skills if score >= 66% (6/9)
            if result.score >= 66.67:
                scoring_system.update_competency(team_number, "driving_skills", True)
        
        # Apply mechanical exam results
        for team_number, result in self.exam_results["mechanical"].items():
            scoring_system.update_mechanical_score(team_number, result.score)
            # Tools and spare parts are embedded in the overall score
            scoring_system.update_tools_score(team_number, result.score)
            scoring_system.update_spare_parts_score(team_number, result.score)
        
        # Apply electrical exam results
        for team_number, result in self.exam_results["electrical"].items():
            scoring_system.update_electrical_score(team_number, result.score)
            # Driver station from modem placement
            modem_score = result.details.get("modem_score", 0)
            scoring_system.update_driver_station_layout_score(team_number, modem_score)
        
        # Apply competencies exam results
        for team_number, result in self.exam_results["competencies"].items():
            scoring_system.update_team_organization_score(team_number, result.score)
            
            # Set competencies from details
            if result.details.get("reliability"):
                scoring_system.update_competency(team_number, "reliability", True)
            if result.details.get("commitment"):
                scoring_system.update_competency(team_number, "commitment", True)
            if result.details.get("inspection_first"):
                scoring_system.update_competency(team_number, "pasar_inspeccion_primera", True)
        
        # Add scouting comments to team scores
        for team_number, comments in self.scouting_comments.items():
            if team_number in scoring_system.teams:
                # Store comments in the team's competencies or as a separate field
                if hasattr(scoring_system.teams[team_number], 'scouting_comments'):
                    scoring_system.teams[team_number].scouting_comments = comments
    
    def get_all_teams(self) -> List[str]:
        """Get list of all team numbers that have exam data"""
        teams = set()
        for results in self.exam_results.values():
            teams.update(results.keys())
        return sorted(list(teams))
    
    def get_exam_statistics(self) -> Dict:
        """Get statistics about the integrated exam data"""
        stats = {}
        for exam_type, results in self.exam_results.items():
            if results:
                scores = [r.score for r in results.values()]
                stats[exam_type] = {
                    "count": len(results),
                    "avg_score": sum(scores) / len(scores) if scores else 0,
                    "min_score": min(scores) if scores else 0,
                    "max_score": max(scores) if scores else 0
                }
            else:
                stats[exam_type] = {"count": 0, "avg_score": 0, "min_score": 0, "max_score": 0}
        
        stats["total_teams"] = len(self.get_all_teams())
        stats["total_comments"] = sum(len(c) for c in self.scouting_comments.values())
        
        return stats


if __name__ == "__main__":
    # Example usage
    print("Exam Data Integrator - Test")
    print("=" * 50)
    
    integrator = ExamDataIntegrator()
    
    # Define exam file paths (adjust paths as needed)
    base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    example_dir = os.path.join(base_path, "archivos ejemplo")
    
    exam_files = {
        "programming": os.path.join(example_dir, "Examen de Programación (OVER) (Respuestas) - Respuestas de formulario 1.csv"),
        "mechanical": os.path.join(example_dir, "Examen Mecánico (OVER) (Respuestas) - Respuestas de formulario 1.csv"),
        "electrical": os.path.join(example_dir, "Examen Eléctrico (OVER) (Respuestas) - Respuestas de formulario 1.csv"),
        "competencies": os.path.join(example_dir, "Examen de Competencias (OVER) (Respuestas) - Respuestas de formulario 1.csv")
    }
    
    # Check which files exist
    print("\nChecking exam files:")
    for exam_type, path in exam_files.items():
        exists = "✓" if os.path.exists(path) else "✗"
        print(f"  {exists} {exam_type}: {os.path.basename(path)}")
    
    # Integrate all exams
    integrator.integrate_all_exams(exam_files)
    
    # Show statistics
    stats = integrator.get_exam_statistics()
    print(f"\nExam Statistics:")
    print(f"  Total teams with exam data: {stats['total_teams']}")
    print(f"  Total scouting comments: {stats['total_comments']}")
    
    for exam_type in ["programming", "mechanical", "electrical", "competencies"]:
        s = stats[exam_type]
        print(f"\n  {exam_type.title()} Exam:")
        print(f"    Count: {s['count']}")
        print(f"    Avg Score: {s['avg_score']:.1f}")
        print(f"    Range: {s['min_score']:.1f} - {s['max_score']:.1f}")
    
    # Show sample team summary
    all_teams = integrator.get_all_teams()
    if all_teams:
        sample_team = all_teams[0]
        summary = integrator.get_team_exam_summary(sample_team)
        print(f"\nSample Team Summary ({sample_team}):")
        for exam_type, data in summary["exams"].items():
            print(f"  {exam_type}: {data['raw_score']:.0f}/{data['max_score']:.0f} ({data['score']:.1f}%)")
        if summary["comments"]:
            print(f"  Comments: {len(summary['comments'])}")
