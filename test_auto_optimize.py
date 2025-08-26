#!/usr/bin/env python3
"""
Test específico para el auto-optimize
"""

from allianceSelector import Team, AllianceSelector

def create_test_teams():
    """Crear equipos de prueba más realistas"""
    teams = []
    for i in range(1, 25):  # 24 equipos para simular un evento real
        score_base = 50 - (i-1) * 2  # Scores decrecientes
        teams.append(Team(
            num=i,
            rank=i,
            total_epa=score_base,
            auto_epa=score_base * 0.4,
            teleop_epa=score_base * 0.4,
            endgame_epa=score_base * 0.2,
            defense=(i % 5 == 0),  # Cada 5 equipos es defensivo
            name=f"Team {i}",
            robot_valuation=90 - i*2,
            consistency_score=85 - i,
            clutch_factor=80 - i
        ))
    return teams

def test_auto_optimize_simulation():
    """Simular el auto-optimize manualmente"""
    print("=== Test Auto-Optimize Simulation ===")
    
    teams = create_test_teams()
    selector = AllianceSelector(teams)
    
    print(f"Equipos totales: {len(teams)}")
    print(f"Alianzas creadas: {len(selector.alliances)}")
    
    # Mostrar estado inicial
    print("\n--- Estado inicial ---")
    for alliance in selector.alliances:
        print(f"Alianza {alliance.allianceNumber}: Capitán {alliance.captain}")
    
    # Simular auto-optimize: Pick 1 round (1-8)
    print("\n--- Simulando Pick 1 round ---")
    for alliance in selector.alliances:
        available_teams = selector.get_available_teams(alliance.captainRank, 'pick1')
        if available_teams:
            best_pick = available_teams[0]  # Simplificado: tomar el mejor disponible
            try:
                selector.set_pick(alliance.allianceNumber - 1, 'pick1', best_pick.team)
                print(f"Alianza {alliance.allianceNumber} seleccionó pick1: Team {best_pick.team} (Score: {best_pick.score:.1f})")
            except Exception as e:
                print(f"Error en Alianza {alliance.allianceNumber}: {e}")
    
    # Pick 2 round (8-1)
    print("\n--- Simulando Pick 2 round ---")
    for alliance in reversed(selector.alliances):
        available_teams = selector.get_available_teams(alliance.captainRank, 'pick2')
        if available_teams:
            best_pick = available_teams[0]
            try:
                selector.set_pick(alliance.allianceNumber - 1, 'pick2', best_pick.team)
                print(f"Alianza {alliance.allianceNumber} seleccionó pick2: Team {best_pick.team} (Score: {best_pick.score:.1f})")
            except Exception as e:
                print(f"Error en Alianza {alliance.allianceNumber}: {e}")
    
    # Mostrar resultado final
    print("\n--- Resultado final ---")
    table = selector.get_alliance_table()
    for row in table:
        print(f"Alianza {row['Alliance #']}: Capitán {row['Captain']}, Pick1 {row['Pick 1']}, Pick2 {row['Pick 2']}, Score: {row['Alliance Score']}")
    
    return selector

if __name__ == "__main__":
    selector = test_auto_optimize_simulation()
    print("\n=== Test completado ===")
