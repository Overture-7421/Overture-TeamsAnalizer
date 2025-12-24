#!/usr/bin/env python3
"""
Script para inspeccionar las claves de estadísticas del analizador
"""

import sys
import os

# Add the project directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import AnalizadorRobot

def inspect_team_stats():
    """Inspecciona las claves de estadísticas disponibles"""
    print("Inspeccionando claves de estadísticas del analizador...")
    
    # Crear datos de prueba
    test_data = [
        ["Team", "Match", "Coral L1 (Auto)", "Coral L2 (Auto)", "Coral L3 (Auto)", "Coral L4 (Auto)",
         "Coral L1 (Teleop)", "Coral L2 (Teleop)", "Coral L3 (Teleop)", "Coral L4 (Teleop)",
         "Barge Algae (Auto)", "Barge Algae (Teleop)", "Processor Algae (Auto)", "Processor Algae (Teleop)",
         "Moved (Auto)", "End Position"],
        ["1000", "Q1", "2", "1", "1", "0", "3", "2", "1", "1", "1", "2", "1", "2", "True", "deep"],
        ["1000", "Q2", "3", "2", "0", "1", "4", "3", "2", "0", "0", "3", "2", "1", "True", "shallow"],
        ["2000", "Q1", "1", "0", "0", "0", "2", "1", "0", "0", "0", "1", "0", "1", "False", "park"],
        ["2000", "Q2", "2", "1", "1", "0", "3", "2", "1", "0", "1", "2", "1", "2", "True", "none"]
    ]
    
    # Inicializar analizador
    analizador = AnalizadorRobot()
    analizador.sheet_data = test_data
    analizador._update_column_indices()
    
    # Obtener estadísticas
    stats = analizador.get_detailed_team_stats()
    
    if stats:
        print(f"\nEncontrados {len(stats)} equipos")
        for team_stat in stats:
            print(f"\nEquipo {team_stat.get('team', 'Unknown')}:")
            print("Claves disponibles:")
            for key in sorted(team_stat.keys()):
                value = team_stat[key]
                if isinstance(value, (int, float)):
                    print(f"  {key}: {value}")
                else:
                    print(f"  {key}: {value} (type: {type(value)})")
    else:
        print("No se pudieron obtener estadísticas")

if __name__ == "__main__":
    inspect_team_stats()
