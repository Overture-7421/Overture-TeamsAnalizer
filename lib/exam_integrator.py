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

import os
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd


EXAM_SCHEMA_VERSION = "2.0.1"

EXAM_QUESTIONNAIRES = {
    "programming": {
        "label": "Programación",
        "field_aliases": {
            "prog_path_planner": ["prog_path_planner", "path planner"],
            "prog_auto_change": ["prog_auto_change", "cambiar un autonomo", "cambiar un autónomo"],
            "prog_auto_reliability": ["prog_auto_reliability", "si su autonomo se prueba 10 veces", "si su autónomo se prueba 10 veces"],
            "prog_odometry_type": ["prog_odometry_type", "odometria", "odometría"],
            "prog_drive_orient": ["prog_drive_orient", "orientacion de control", "orientación de control"],
        },
    },
    "mechanical": {
        "label": "Mecánica",
        "field_aliases": {
            "mech_checklist": ["mech_checklist", "checklist", "rutina del robot antes de cada partida"],
            "mech_spare_parts": ["mech_spare_parts", "repuestos de sus mecanismos", "spare parts"],
            "mech_std_bolts": ["mech_std_bolts", "tornilleria estandarizada", "tornillería estandarizada"],
            "mech_problem_mechanism": ["mech_problem_mechanism", "cual mecanismo mas les da problema", "cuál mecanismo más les da problema"],
            "mech_chassis_type": ["mech_chassis_type", "que tipo de chasis usan", "qué tipo de chasis usan"],
            "mech_ball_capacity": ["mech_ball_capacity", "cuantas pelotas le caben", "cuántas pelotas le caben"],
        },
    },
    "electrical": {
        "label": "Eléctrica",
        "field_aliases": {
            "elec_canivore": ["elec_canivore", "canivore"],
            "elec_ethernet_cables": ["elec_ethernet_cables", "cables ethernet"],
            "elec_radio_location": ["elec_radio_location", "donde se encuentra el radio del robot", "radio del robot"],
            "elec_cable_replace": ["elec_cable_replace", "que tan fácil es cambiar un cable que se rompa", "que tan facil es cambiar un cable que se rompa"],
            "elec_battery_peak": ["elec_battery_peak", "battery peak"],
        },
    },
    "competences": {
        "label": "Competencias",
        "field_aliases": {
            "comp_batteries": ["comp_batteries", "cuantas pilas cuenta el equipo", "cuántas pilas cuenta el equipo"],
            "comp_bumper_time": ["comp_bumper_time", "cuanto tiempo tardan en cambiar los bumpers", "cuánto tiempo tardan en cambiar los bumpers"],
            "comp_drivers_needed": ["comp_drivers_needed", "es necesario tener a los drivers para arreglarlo"],
            "comp_balls_per_second": ["comp_balls_per_second", "cuantas pelotas por segundo se disparan", "cuántas pelotas por segundo se disparan"],
            "comp_mentors_vs_students": ["comp_mentors_vs_students", "hay más mentores que alumnos en el pit"],
        },
    },
}

YES_VALUES = {"si", "sí", "yes", "true", "1", "cumple"}
NO_VALUES = {"no", "false", "0", "no cumple"}


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

    def _normalize_text(self, value: Any) -> str:
        text = "" if value is None else str(value).strip().lower()
        text = unicodedata.normalize("NFKD", text)
        text = "".join(char for char in text if not unicodedata.combining(char))
        return re.sub(r"\s+", " ", text)

    def _parse_number(self, value: Any) -> Optional[float]:
        try:
            text = self._normalize_text(value).replace(",", ".")
            match = re.search(r"-?\d+(?:\.\d+)?", text)
            if match:
                return float(match.group(0))
        except (TypeError, ValueError):
            pass
        return None

    def _find_matching_column(self, columns: List[str], aliases: List[str]) -> str:
        normalized_columns = {self._normalize_text(column): column for column in columns}
        for alias in aliases:
            alias_norm = self._normalize_text(alias)
            if alias_norm in normalized_columns:
                return normalized_columns[alias_norm]
            for normalized_column, original_column in normalized_columns.items():
                if alias_norm and (alias_norm in normalized_column or normalized_column in alias_norm):
                    return original_column
        return ""

    def _get_field_value(self, row: pd.Series, columns: List[str], aliases: List[str]) -> Tuple[Any, str]:
        column = self._find_matching_column(columns, aliases)
        if column:
            return row[column], column
        return None, ""

    def _parse_yes_no(self, value: Any, yes_scores_high: bool = True) -> Optional[float]:
        normalized = self._normalize_text(value)
        if normalized in YES_VALUES:
            return 100.0 if yes_scores_high else 0.0
        if normalized in NO_VALUES:
            return 0.0 if yes_scores_high else 100.0
        return None

    def _score_from_option_map(self, value: Any, score_map: Dict[str, float]) -> Optional[float]:
        normalized = self._normalize_text(value)
        return score_map.get(normalized)

    def _score_numeric_range(self, value: Any, minimum: float, maximum: float, reverse: bool = False) -> Optional[float]:
        parsed = self._parse_number(value)
        if parsed is None:
            return None
        if maximum <= minimum:
            return 0.0
        bounded = max(minimum, min(maximum, parsed))
        ratio = (bounded - minimum) / (maximum - minimum)
        if reverse:
            ratio = 1.0 - ratio
        return ratio * 100.0

    def _collect_questionnaire_fields(self, exam_type: str, row: pd.Series, columns: List[str]) -> Tuple[Dict[str, Dict[str, Any]], List[float], Dict[str, Any]]:
        questionnaire = EXAM_QUESTIONNAIRES.get(exam_type, {})
        field_aliases = questionnaire.get("field_aliases", {})
        answers: Dict[str, Dict[str, Any]] = {}
        field_scores: List[float] = []
        score_map: Dict[str, Any] = {}

        def store(field_key: str, column: str, value: Any, score: Optional[float]) -> None:
            answers[field_key] = {
                "column": column,
                "value": value,
                "score": score,
            }
            if score is not None:
                field_scores.append(score)
                score_map[field_key] = score

        if exam_type == "programming":
            value, column = self._get_field_value(row, columns, field_aliases.get("prog_path_planner", []))
            store("prog_path_planner", column, value, self._parse_yes_no(value))

            value, column = self._get_field_value(row, columns, field_aliases.get("prog_auto_change", []))
            store("prog_auto_change", column, value, self._score_from_option_map(value, {
                self._normalize_text("Sencillo"): 100.0,
                self._normalize_text("Difícil"): 0.0,
            }))

            value, column = self._get_field_value(row, columns, field_aliases.get("prog_auto_reliability", []))
            store("prog_auto_reliability", column, value, self._score_from_option_map(value, {
                self._normalize_text("Menos de 5"): 0.0,
                self._normalize_text("Menos de 10"): 50.0,
                self._normalize_text("10 veces siempre"): 100.0,
            }))

            value, column = self._get_field_value(row, columns, field_aliases.get("prog_odometry_type", []))
            store("prog_odometry_type", column, value, self._score_from_option_map(value, {
                self._normalize_text("Encoders de llanta"): 40.0,
                self._normalize_text("Estimación por swerve"): 60.0,
                self._normalize_text("Corrección por april tag"): 80.0,
                self._normalize_text("Fusión de sensores"): 100.0,
            }))

            value, column = self._get_field_value(row, columns, field_aliases.get("prog_drive_orient", []))
            store("prog_drive_orient", column, value, self._score_from_option_map(value, {
                self._normalize_text("Orientación de robot"): 60.0,
                self._normalize_text("Orientación de Cancha"): 85.0,
                self._normalize_text("Ambas"): 100.0,
            }))

        elif exam_type == "mechanical":
            value, column = self._get_field_value(row, columns, field_aliases.get("mech_checklist", []))
            store("mech_checklist", column, value, self._parse_yes_no(value))

            value, column = self._get_field_value(row, columns, field_aliases.get("mech_spare_parts", []))
            store("mech_spare_parts", column, value, self._score_from_option_map(value, {
                self._normalize_text("Tenemos para todos los mecanismos"): 100.0,
                self._normalize_text("Tenemos solo para varios"): 50.0,
                self._normalize_text("No tenemos ningún repuesto"): 0.0,
            }))

            value, column = self._get_field_value(row, columns, field_aliases.get("mech_std_bolts", []))
            store("mech_std_bolts", column, value, self._parse_yes_no(value))

            value, column = self._get_field_value(row, columns, field_aliases.get("mech_problem_mechanism", []))
            store("mech_problem_mechanism", column, value, None)

            value, column = self._get_field_value(row, columns, field_aliases.get("mech_chassis_type", []))
            store("mech_chassis_type", column, value, self._score_from_option_map(value, {
                self._normalize_text("Tank"): 65.0,
                self._normalize_text("Mecanum"): 75.0,
                self._normalize_text("Swerve"): 100.0,
            }))

            value, column = self._get_field_value(row, columns, field_aliases.get("mech_ball_capacity", []))
            store("mech_ball_capacity", column, value, self._score_numeric_range(value, 0.0, 12.0))

        elif exam_type == "electrical":
            value, column = self._get_field_value(row, columns, field_aliases.get("elec_canivore", []))
            store("elec_canivore", column, value, self._parse_yes_no(value))

            value, column = self._get_field_value(row, columns, field_aliases.get("elec_ethernet_cables", []))
            store("elec_ethernet_cables", column, value, self._score_from_option_map(value, {
                self._normalize_text("Hechos por nosotros"): 100.0,
                self._normalize_text("Comprados"): 60.0,
            }))

            value, column = self._get_field_value(row, columns, field_aliases.get("elec_radio_location", []))
            store("elec_radio_location", column, value, self._score_from_option_map(value, {
                self._normalize_text("Expuesto como el nuestro"): 40.0,
                self._normalize_text("Escondido de muchas cosas"): 100.0,
            }))

            value, column = self._get_field_value(row, columns, field_aliases.get("elec_cable_replace", []))
            store("elec_cable_replace", column, value, self._score_from_option_map(value, {
                self._normalize_text("Sencillo"): 100.0,
                self._normalize_text("Difícil"): 0.0,
            }))

            value, column = self._get_field_value(row, columns, field_aliases.get("elec_battery_peak", []))
            store("elec_battery_peak", column, value, self._parse_yes_no(value))

        elif exam_type == "competences":
            value, column = self._get_field_value(row, columns, field_aliases.get("comp_batteries", []))
            store("comp_batteries", column, value, self._score_from_option_map(value, {
                self._normalize_text("Menos de 5"): 30.0,
                self._normalize_text("Menos de 10"): 65.0,
                self._normalize_text("Más de 10"): 100.0,
            }))

            value, column = self._get_field_value(row, columns, field_aliases.get("comp_bumper_time", []))
            store("comp_bumper_time", column, value, self._score_from_option_map(value, {
                self._normalize_text("Menos de 1 minuto"): 100.0,
                self._normalize_text("Menos de 2 minutos"): 70.0,
                self._normalize_text("Más de 2 minutos"): 20.0,
            }))

            value, column = self._get_field_value(row, columns, field_aliases.get("comp_drivers_needed", []))
            store("comp_drivers_needed", column, value, self._parse_yes_no(value, yes_scores_high=False))

            value, column = self._get_field_value(row, columns, field_aliases.get("comp_balls_per_second", []))
            store("comp_balls_per_second", column, value, self._score_numeric_range(value, 0.0, 3.0))

            value, column = self._get_field_value(row, columns, field_aliases.get("comp_mentors_vs_students", []))
            store("comp_mentors_vs_students", column, value, self._score_from_option_map(value, {
                self._normalize_text("Son más mentores"): 60.0,
                self._normalize_text("Son más alumnos"): 100.0,
            }))

        questionnaire_score = sum(field_scores) / len(field_scores) if field_scores else None
        return answers, field_scores, {"questionnaire_score": questionnaire_score, "score_map": score_map}

    def _extract_common_fields(self, row: pd.Series, columns: List[str]) -> Dict[str, Any]:
        team_value, team_column = self._get_field_value(row, columns, [
            "Team NUMBER",
            "Team Number",
            "Número de equipo",
            "Numero de equipo",
            "team_number",
        ])
        examiner_value, examiner_column = self._get_field_value(row, columns, [
            "Nombre del examinador",
            "examiner_name",
            "Examiner Name",
        ])
        feeling_value, feeling_column = self._get_field_value(row, columns, [
            "Como examinador, ¿cómo te sentiste evaluando a este equipo?",
            "examiner_feeling",
            "Examiner Feeling",
        ])

        return {
            "team_number": str(team_value).strip() if team_value is not None else "",
            "team_column": team_column,
            "examiner_name": examiner_value,
            "examiner_column": examiner_column,
            "examiner_feeling": feeling_value,
            "feeling_column": feeling_column,
        }
    
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
        columns = list(df.columns)
        timestamp_col = self._find_matching_column(columns, [
            "Marca temporal",
            "Timestamp",
            "marca temporal",
        ])
        team_col = self._find_matching_column(columns, [
            "Team NUMBER",
            "Team Number",
            "Número de equipo",
            "Numero de equipo",
            "team_number",
        ])

        if not team_col:
            raise ValueError("Required columns not found. Expected a team number column.")

        if timestamp_col:
            df["_parsed_timestamp"] = df[timestamp_col].apply(self._parse_timestamp)
        else:
            df["_parsed_timestamp"] = datetime.min

        df[team_col] = df[team_col].astype(str)
        df = df.sort_values("_parsed_timestamp", ascending=False)
        df = df.drop_duplicates(subset=[team_col], keep="first")

        if not timestamp_col:
            df = df.reset_index(drop=True)
        
        return df
    
    def _get_feedback_column(self, df: pd.DataFrame) -> str:
        """Find the feedback column (usually the last question about examiner experience)"""
        feedback_keywords = ["examinador", "sentiste", "evaluar", "examiner_feeling"]
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
        columns = list(df.columns)
        common = self._extract_common_fields(df.iloc[0] if not df.empty else pd.Series(dtype=object), columns) if not df.empty else {
            "team_number": "",
            "team_column": "",
            "examiner_feeling": "",
            "feeling_column": "",
        }
        team_col = common["team_column"] or self._find_matching_column(columns, [
            "Team NUMBER",
            "Team Number",
            "Número de equipo",
            "Numero de equipo",
            "team_number",
        ])
        score_col = self._find_matching_column(columns, ["Puntuación", "Puntuacion", "Score", "score"])
        feedback_col = common["feeling_column"] or self._get_feedback_column(df)
        
        results = {}
        
        for _, row in df.iterrows():
            common_fields = self._extract_common_fields(row, columns)
            team_number = common_fields["team_number"]
            if not team_number and team_col:
                team_number = str(row[team_col]).strip()
            raw_score, max_score = self._parse_score(row[score_col]) if score_col else (0.0, 1.0)
            normalized = self._normalize_score(raw_score, max_score) if score_col else 0.0

            feedback = str(row[feedback_col]) if feedback_col else common_fields.get("examiner_feeling", "")
            self._add_comment(team_number, f"[Programación] {feedback}")

            answers, field_scores, derived = self._collect_questionnaire_fields("programming", row, columns)
            questionnaire_score = derived.get("questionnaire_score")

            details = {
                "schema_version": EXAM_SCHEMA_VERSION,
                "questionnaire": EXAM_QUESTIONNAIRES["programming"]["label"],
                "reported_score": normalized,
                "questionnaire_score": questionnaire_score,
                "field_scores": derived.get("score_map", {}),
                "answers": answers,
                "common_fields": common_fields,
            }
            for col in df.columns:
                if col not in [team_col, score_col, "Marca temporal", "Timestamp", "_parsed_timestamp"]:
                    details.setdefault("raw_columns", {})[col] = row[col]

            final_score = questionnaire_score if questionnaire_score is not None else normalized
            result = ExamResult(
                team_number=team_number,
                score=final_score,
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
        columns = list(df.columns)
        common = self._extract_common_fields(df.iloc[0] if not df.empty else pd.Series(dtype=object), columns) if not df.empty else {
            "team_number": "",
            "team_column": "",
            "examiner_feeling": "",
            "feeling_column": "",
        }
        team_col = common["team_column"] or self._find_matching_column(columns, [
            "Team NUMBER",
            "Team Number",
            "Número de equipo",
            "Numero de equipo",
            "team_number",
        ])
        score_col = self._find_matching_column(columns, ["Puntuación", "Puntuacion", "Score", "score"])
        feedback_col = common["feeling_column"] or self._get_feedback_column(df)
        
        results = {}
        
        for _, row in df.iterrows():
            common_fields = self._extract_common_fields(row, columns)
            team_number = common_fields["team_number"]
            if not team_number and team_col:
                team_number = str(row[team_col]).strip()
            raw_score, max_score = self._parse_score(row[score_col]) if score_col else (0.0, 1.0)
            normalized = self._normalize_score(raw_score, max_score) if score_col else 0.0

            feedback = str(row[feedback_col]) if feedback_col else common_fields.get("examiner_feeling", "")
            self._add_comment(team_number, f"[Mecánica] {feedback}")

            answers, field_scores, derived = self._collect_questionnaire_fields("mechanical", row, columns)
            questionnaire_score = derived.get("questionnaire_score")
            score_lookup = derived.get("score_map", {})

            details = {
                "schema_version": EXAM_SCHEMA_VERSION,
                "questionnaire": EXAM_QUESTIONNAIRES["mechanical"]["label"],
                "reported_score": normalized,
                "questionnaire_score": questionnaire_score,
                "field_scores": score_lookup,
                "answers": answers,
                "common_fields": common_fields,
            }
            for col in df.columns:
                if col not in [team_col, score_col, "Marca temporal", "Timestamp", "_parsed_timestamp"]:
                    details.setdefault("raw_columns", {})[col] = row[col]

            final_score = questionnaire_score if questionnaire_score is not None else normalized
            
            result = ExamResult(
                team_number=team_number,
                score=final_score,
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
        columns = list(df.columns)
        common = self._extract_common_fields(df.iloc[0] if not df.empty else pd.Series(dtype=object), columns) if not df.empty else {
            "team_number": "",
            "team_column": "",
            "examiner_feeling": "",
            "feeling_column": "",
        }
        team_col = common["team_column"] or self._find_matching_column(columns, [
            "Team NUMBER",
            "Team Number",
            "Número de equipo",
            "Numero de equipo",
            "team_number",
        ])
        score_col = self._find_matching_column(columns, ["Puntuación", "Puntuacion", "Score", "score"])
        feedback_col = common["feeling_column"] or self._get_feedback_column(df)
        
        results = {}
        
        for _, row in df.iterrows():
            common_fields = self._extract_common_fields(row, columns)
            team_number = common_fields["team_number"]
            if not team_number and team_col:
                team_number = str(row[team_col]).strip()
            raw_score, max_score = self._parse_score(row[score_col]) if score_col else (0.0, 1.0)
            normalized = self._normalize_score(raw_score, max_score) if score_col else 0.0

            feedback = str(row[feedback_col]) if feedback_col else common_fields.get("examiner_feeling", "")
            self._add_comment(team_number, f"[Eléctrica] {feedback}")

            answers, field_scores, derived = self._collect_questionnaire_fields("electrical", row, columns)
            questionnaire_score = derived.get("questionnaire_score")
            score_lookup = derived.get("score_map", {})

            layout_scores = [
                score_lookup.get("elec_radio_location"),
                score_lookup.get("elec_cable_replace"),
                score_lookup.get("elec_canivore"),
            ]
            layout_scores = [score for score in layout_scores if score is not None]
            driver_station_score = sum(layout_scores) / len(layout_scores) if layout_scores else questionnaire_score

            details = {
                "schema_version": EXAM_SCHEMA_VERSION,
                "questionnaire": EXAM_QUESTIONNAIRES["electrical"]["label"],
                "reported_score": normalized,
                "questionnaire_score": questionnaire_score,
                "field_scores": score_lookup,
                "driver_station_score": driver_station_score,
                "answers": answers,
                "common_fields": common_fields,
            }
            for col in df.columns:
                if col not in [team_col, score_col, "Marca temporal", "Timestamp", "_parsed_timestamp"]:
                    details.setdefault("raw_columns", {})[col] = row[col]

            final_score = questionnaire_score if questionnaire_score is not None else normalized
            
            result = ExamResult(
                team_number=team_number,
                score=final_score,
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
        columns = list(df.columns)
        common = self._extract_common_fields(df.iloc[0] if not df.empty else pd.Series(dtype=object), columns) if not df.empty else {
            "team_number": "",
            "team_column": "",
            "examiner_feeling": "",
            "feeling_column": "",
        }
        team_col = common["team_column"] or self._find_matching_column(columns, [
            "Team NUMBER",
            "Team Number",
            "Número de equipo",
            "Numero de equipo",
            "team_number",
        ])
        score_col = self._find_matching_column(columns, ["Puntuación", "Puntuacion", "Score", "score"])
        feedback_col = common["feeling_column"] or self._get_feedback_column(df)
        
        results = {}
        
        for _, row in df.iterrows():
            common_fields = self._extract_common_fields(row, columns)
            team_number = common_fields["team_number"]
            if not team_number and team_col:
                team_number = str(row[team_col]).strip()
            raw_score, max_score = self._parse_score(row[score_col]) if score_col else (0.0, 1.0)
            normalized = self._normalize_score(raw_score, max_score) if score_col else 0.0

            feedback = str(row[feedback_col]) if feedback_col else common_fields.get("examiner_feeling", "")
            self._add_comment(team_number, f"[Competencias] {feedback}")

            answers, field_scores, derived = self._collect_questionnaire_fields("competences", row, columns)
            questionnaire_score = derived.get("questionnaire_score")
            score_lookup = derived.get("score_map", {})

            details = {
                "schema_version": EXAM_SCHEMA_VERSION,
                "questionnaire": EXAM_QUESTIONNAIRES["competences"]["label"],
                "reported_score": normalized,
                "questionnaire_score": questionnaire_score,
                "field_scores": score_lookup,
                "answers": answers,
                "common_fields": common_fields,
            }
            for col in df.columns:
                if col not in [team_col, score_col, "Marca temporal", "Timestamp", "_parsed_timestamp"]:
                    details.setdefault("raw_columns", {})[col] = row[col]

            final_score = questionnaire_score if questionnaire_score is not None else normalized
            
            result = ExamResult(
                team_number=team_number,
                score=final_score,
                max_score=max_score,
                raw_score=raw_score,
                timestamp=row["_parsed_timestamp"],
                feedback=feedback,
                details=details
            )
            results[team_number] = result
        
        self.exam_results["competencies"] = results
        return results
    
    def integrate_unified_exam(self, csv_path: str) -> Dict[str, Dict[str, "ExamResult"]]:
        """
        Integrate a single unified CSV containing all exam sections.

        The CSV must follow the PITSCOUTING_FORMATSAMPLE format where all
        mech_*, prog_*, elec_*, and comp_* columns live in one file.

        Returns a dict with keys 'programming', 'mechanical', 'electrical',
        'competencies', each mapping team_number -> ExamResult.
        """
        df = pd.read_csv(csv_path)
        df = self._clean_and_deduplicate(df)
        columns = list(df.columns)

        team_col = self._find_matching_column(columns, [
            "Team NUMBER", "Team Number", "Número de equipo",
            "Numero de equipo", "team_number",
        ])
        score_col = self._find_matching_column(columns, ["Puntuación", "Puntuacion", "Score", "score"])

        exam_types = ["programming", "mechanical", "electrical", "competences"]
        results: Dict[str, Dict[str, "ExamResult"]] = {et: {} for et in exam_types}

        for _, row in df.iterrows():
            common_fields = self._extract_common_fields(row, columns)
            team_number = common_fields["team_number"]
            if not team_number and team_col:
                team_number = str(row[team_col]).strip()
            if not team_number:
                continue

            raw_score, max_score = self._parse_score(row[score_col]) if score_col else (0.0, 1.0)
            normalized = self._normalize_score(raw_score, max_score) if score_col else 0.0
            timestamp = row.get("_parsed_timestamp", datetime.min)

            feedback = str(common_fields.get("examiner_feeling", "") or "")
            self._add_comment(team_number, feedback)

            for exam_type in exam_types:
                answers, field_scores, derived = self._collect_questionnaire_fields(exam_type, row, columns)
                questionnaire_score = derived.get("questionnaire_score")
                score_map = derived.get("score_map", {})

                details = {
                    "schema_version": EXAM_SCHEMA_VERSION,
                    "questionnaire": EXAM_QUESTIONNAIRES.get(exam_type, {}).get("label", exam_type.title()),
                    "reported_score": normalized,
                    "questionnaire_score": questionnaire_score,
                    "field_scores": score_map,
                    "answers": answers,
                    "common_fields": common_fields,
                }

                final_score = questionnaire_score if questionnaire_score is not None else normalized
                result = ExamResult(
                    team_number=team_number,
                    score=final_score,
                    max_score=max_score,
                    raw_score=raw_score,
                    timestamp=timestamp,
                    feedback=feedback,
                    details=details,
                )
                results[exam_type][team_number] = result

        # Store under canonical keys (competences -> competencies for storage)
        self.exam_results["programming"] = results["programming"]
        self.exam_results["mechanical"] = results["mechanical"]
        self.exam_results["electrical"] = results["electrical"]
        self.exam_results["competencies"] = results["competences"]

        return {
            "programming": results["programming"],
            "mechanical": results["mechanical"],
            "electrical": results["electrical"],
            "competencies": results["competences"],
        }

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
                    "questionnaire": result.details.get("questionnaire", exam_type.title()),
                    "score": result.score,
                    "questionnaire_score": result.details.get("questionnaire_score"),
                    "raw_score": result.raw_score,
                    "max_score": result.max_score,
                    "feedback": result.feedback,
                    "field_scores": result.details.get("field_scores", {}),
                    "answers": result.details.get("answers", {}),
                }
        
        # Combine all feedback
        summary["combined_feedback"] = " | ".join(summary["comments"])
        
        return summary
    
    def assign_default_competencies(self, scoring_system) -> int:
        """
        Assigns default competencies to teams present in the scoring system
        but not found in any of the processed exam files.
        """
        all_teams_in_exams = self.get_all_teams()
        if not all_teams_in_exams:
            print("No exam data processed, skipping default competency assignment.")
            return 0

        all_teams_in_scoring = set(scoring_system.teams.keys())
        teams_without_exam_data = all_teams_in_scoring - set(all_teams_in_exams)
        
        if not teams_without_exam_data:
            return 0

        default_competencies = ["reliability", "driving_skills"]
        default_subcompetency = "knows_the_rules"
        
        for team_num in teams_without_exam_data:
            # Check if the team already has these competencies, to avoid overwriting
            # This is a safeguard in case they were set manually
            team_comp = scoring_system.teams[team_num].competencies
            
            # Assign default competencies
            for comp in default_competencies:
                if not getattr(team_comp, comp, False):
                    scoring_system.update_competency(team_num, comp, True)
            
            # Assign default subcompetency
            if not getattr(team_comp, default_subcompetency, False):
                scoring_system.update_competency(team_num, default_subcompetency, True)

        print(f"Assigned default competencies to {len(teams_without_exam_data)} teams: {teams_without_exam_data}")
        return len(teams_without_exam_data)

    def apply_to_scoring_system(self, scoring_system) -> None:
        """
        Apply all integrated exam results to a TeamScoring instance.
        NOW also assigns default competencies to teams without exam data.
        
        Args:
            scoring_system: Instance of TeamScoring from school_system
        """
        # Apply programming exam results
        for team_number, result in self.exam_results["programming"].items():
            field_scores = result.details.get("field_scores", {})
            programming_score = result.details.get("questionnaire_score", result.score)
            scoring_system.update_autonomous_score(team_number, programming_score)

            if programming_score >= 70 or field_scores.get("prog_auto_reliability", 0) >= 100:
                scoring_system.update_competency(team_number, "driving_skills", True)
            if field_scores.get("prog_path_planner", 0) >= 100 or field_scores.get("prog_odometry_type", 0) >= 80:
                scoring_system.update_competency(team_number, "reliability", True)
        
        # Apply mechanical exam results
        for team_number, result in self.exam_results["mechanical"].items():
            field_scores = result.details.get("field_scores", {})
            mechanical_score = result.details.get("questionnaire_score", result.score)
            scoring_system.update_mechanical_score(team_number, mechanical_score)

            tools_candidates = [field_scores.get("mech_checklist"), field_scores.get("mech_std_bolts")]
            tools_candidates = [score for score in tools_candidates if score is not None]
            tools_score = sum(tools_candidates) / len(tools_candidates) if tools_candidates else mechanical_score
            scoring_system.update_tools_score(team_number, tools_score)

            spare_parts_score = field_scores.get("mech_spare_parts", mechanical_score)
            scoring_system.update_spare_parts_score(team_number, spare_parts_score)

            if field_scores.get("mech_checklist", 0) >= 100 and field_scores.get("mech_std_bolts", 0) >= 100:
                scoring_system.update_competency(team_number, "pasar_inspeccion_primera", True)
        
        # Apply electrical exam results
        for team_number, result in self.exam_results["electrical"].items():
            field_scores = result.details.get("field_scores", {})
            electrical_score = result.details.get("questionnaire_score", result.score)
            scoring_system.update_electrical_score(team_number, electrical_score)

            driver_station_candidates = [
                field_scores.get("elec_radio_location"),
                field_scores.get("elec_cable_replace"),
                field_scores.get("elec_canivore"),
            ]
            driver_station_candidates = [score for score in driver_station_candidates if score is not None]
            driver_station_score = (
                sum(driver_station_candidates) / len(driver_station_candidates)
                if driver_station_candidates else electrical_score
            )
            scoring_system.update_driver_station_layout_score(team_number, driver_station_score)

            if field_scores.get("elec_canivore", 0) >= 100 and field_scores.get("elec_battery_peak", 0) >= 100:
                scoring_system.update_competency(team_number, "reliability", True)
        
        # Apply competencies exam results
        for team_number, result in self.exam_results["competencies"].items():
            field_scores = result.details.get("field_scores", {})
            competencies_score = result.details.get("questionnaire_score", result.score)
            scoring_system.update_team_organization_score(team_number, competencies_score)

            if field_scores.get("comp_drivers_needed", 0) >= 100:
                scoring_system.update_competency(team_number, "necessary_drivers_fix", True)
            if field_scores.get("comp_batteries", 0) >= 65 and field_scores.get("comp_bumper_time", 0) >= 70:
                scoring_system.update_competency(team_number, "commitment", True)
            if field_scores.get("comp_balls_per_second", 0) >= 70:
                scoring_system.update_competency(team_number, "human_player", True)
            if field_scores.get("comp_mentors_vs_students", 0) >= 100:
                scoring_system.update_competency(team_number, "team_communication", True)

            if field_scores.get("comp_drivers_needed", 0) >= 100 and field_scores.get("comp_bumper_time", 0) >= 70:
                scoring_system.update_competency(team_number, "reliability", True)
            if field_scores.get("comp_balls_per_second", 0) >= 70:
                scoring_system.update_competency(team_number, "driving_skills", True)
        
        # Add scouting comments to team scores
        for team_number, comments in self.scouting_comments.items():
            if team_number in scoring_system.teams:
                # Store comments in the team's competencies or as a separate field
                if hasattr(scoring_system.teams[team_number], 'scouting_comments'):
                    scoring_system.teams[team_number].scouting_comments = comments
        
        # NEW: After applying all exam data, assign defaults to the rest
        self.assign_default_competencies(scoring_system)
    
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
