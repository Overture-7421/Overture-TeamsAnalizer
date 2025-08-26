#!/usr/bin/env python3
"""
Script de prueba para verificar las correcciones del Alliance Selector
"""

from allianceSelector import Team, AllianceSelector

def create_test_teams():
    """Crear equipos de prueba"""
    teams = [
        Team(1, 1, 50.0, 20.0, 20.0, 10.0, False, "Team 1", 95, 85, 80),
        Team(2, 2, 45.0, 18.0, 18.0, 9.0, True, "Team 2", 90, 90, 75),
        Team(3, 3, 40.0, 15.0, 17.0, 8.0, False, "Team 3", 85, 80, 85),
        Team(4, 4, 38.0, 16.0, 15.0, 7.0, False, "Team 4", 80, 75, 70),
        Team(5, 5, 35.0, 14.0, 16.0, 5.0, True, "Team 5", 88, 88, 90),
        Team(6, 6, 32.0, 12.0, 15.0, 5.0, False, "Team 6", 82, 70, 65),
        Team(7, 7, 30.0, 11.0, 14.0, 5.0, False, "Team 7", 78, 85, 80),
        Team(8, 8, 28.0, 10.0, 13.0, 5.0, False, "Team 8", 75, 80, 75),
        Team(9, 9, 25.0, 9.0, 12.0, 4.0, False, "Team 9", 70, 65, 60),
        Team(10, 10, 22.0, 8.0, 11.0, 3.0, False, "Team 10", 68, 60, 55),
    ]
    return teams

def test_alliance_selection_logic():
    """Probar la nueva lógica de selección de alianzas"""
    print("=== Test Alliance Selection Logic ===")
    
    teams = create_test_teams()
    selector = AllianceSelector(teams)
    
    print(f"Equipos totales: {len(teams)}")
    print(f"Alianzas creadas: {len(selector.alliances)}")
    
    # Mostrar capitanes
    print("\nCapitanes de alianzas:")
    for alliance in selector.alliances:
        print(f"  Alianza {alliance.allianceNumber}: Capitán {alliance.captain}")
    
    # Test 1: Verificar que capitanes pueden ser seleccionados por OTRAS alianzas
    print("\n--- Test 1: Capitanes pueden ser seleccionados por otras alianzas ---")
    alliance_1 = selector.alliances[0]  # Alianza 1
    alliance_2 = selector.alliances[1]  # Alianza 2
    
    print(f"Alianza 1 - Capitán: {alliance_1.captain}")
    print(f"Alianza 2 - Capitán: {alliance_2.captain}")
    
    # La alianza 2 debería poder seleccionar al capitán de la alianza 1
    available_for_alliance_2 = selector.get_available_teams(alliance_2.captainRank, 'pick1')
    captain_1_available = any(t.team == alliance_1.captain for t in available_for_alliance_2)
    
    print(f"¿Alianza 2 puede seleccionar al capitán de Alianza 1 ({alliance_1.captain})? {captain_1_available}")
    
    # Test 2: Verificar que capitanes NO pueden seleccionarse a sí mismos
    print("\n--- Test 2: Capitanes no pueden seleccionarse a sí mismos ---")
    available_for_alliance_1 = selector.get_available_teams(alliance_1.captainRank, 'pick1')
    captain_1_self_available = any(t.team == alliance_1.captain for t in available_for_alliance_1)
    
    print(f"¿Alianza 1 puede seleccionar a su propio capitán ({alliance_1.captain})? {captain_1_self_available}")
    
    # Test 3: Hacer selecciones y verificar que se excluyen de futuras opciones
    print("\n--- Test 3: Equipos seleccionados se excluyen de futuras opciones ---")
    
    try:
        # Alianza 1 selecciona pick1
        selector.set_pick(0, 'pick1', 3)  # Team 3
        print(f"Alianza 1 seleccionó pick1: Team 3")
        
        # Verificar que Team 3 no está disponible para otras alianzas
        available_for_alliance_2 = selector.get_available_teams(alliance_2.captainRank, 'pick1')
        team_3_available = any(t.team == 3 for t in available_for_alliance_2)
        print(f"¿Team 3 disponible para Alianza 2? {team_3_available}")
        
        # Alianza 2 selecciona pick1
        selector.set_pick(1, 'pick1', 4)  # Team 4
        print(f"Alianza 2 seleccionó pick1: Team 4")
        
        # Mostrar equipos seleccionados
        selected = selector.get_selected_picks()
        print(f"Equipos seleccionados: {selected}")
        
    except Exception as e:
        print(f"Error durante selecciones: {e}")
    
    # Test 4: Verificar recomendaciones
    print("\n--- Test 4: Verificar recomendaciones ---")
    for alliance in selector.alliances:
        print(f"Alianza {alliance.allianceNumber}:")
        print(f"  Capitán: {alliance.captain}")
        print(f"  Pick1: {alliance.pick1}, Recomendación: {alliance.pick1Rec}")
        print(f"  Pick2: {alliance.pick2}, Recomendación: {alliance.pick2Rec}")
    
    return selector

def test_captain_selection_rules():
    """Probar específicamente las reglas de selección de capitanes"""
    print("\n\n=== Test Captain Selection Rules ===")
    
    teams = create_test_teams()
    selector = AllianceSelector(teams)
    
    # Test: Intentar que un capitán se seleccione a sí mismo (debería fallar)
    print("--- Test: Capitán intentando seleccionarse a sí mismo ---")
    alliance_1 = selector.alliances[0]
    try:
        selector.set_pick(0, 'pick1', alliance_1.captain)
        print("ERROR: ¡El capitán pudo seleccionarse a sí mismo!")
    except ValueError as e:
        print(f"CORRECTO: {e}")
    
    # Test: Que otra alianza seleccione al capitán (debería funcionar)
    print("\n--- Test: Otra alianza seleccionando al capitán ---")
    alliance_2 = selector.alliances[1]
    try:
        selector.set_pick(1, 'pick1', alliance_1.captain)
        print(f"CORRECTO: Alianza 2 seleccionó al capitán de Alianza 1 (Team {alliance_1.captain})")
    except ValueError as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    # Ejecutar tests
    selector = test_alliance_selection_logic()
    test_captain_selection_rules()
    
    print("\n=== Tests completados ===")
