#!/usr/bin/env python3
"""
Test completo para verificar todas las correcciones del Alliance Selector
"""

from allianceSelector import Team, AllianceSelector

def create_comprehensive_test():
    """Test completo de todas las funcionalidades"""
    print("=== Test Completo Alliance Selector ===")
    
    # Crear equipos de prueba
    teams = []
    for i in range(1, 13):  # 12 equipos
        score_base = 50 - (i-1) * 3
        teams.append(Team(
            num=i,
            rank=i,
            total_epa=score_base,
            auto_epa=score_base * 0.4,
            teleop_epa=score_base * 0.4,
            endgame_epa=score_base * 0.2,
            defense=(i % 4 == 0),
            name=f"Team {i}",
            robot_valuation=90 - i*3,
            consistency_score=85 - i*2,
            clutch_factor=80 - i*2
        ))
    
    selector = AllianceSelector(teams)
    
    print(f"Equipos totales: {len(teams)}")
    print(f"Alianzas creadas: {len(selector.alliances)}")
    
    # Mostrar estado inicial
    print("\n--- Estado inicial ---")
    for alliance in selector.alliances:
        print(f"Alianza {alliance.allianceNumber}: Capitán {alliance.captain}")
    
    print("\n--- Test 1: Verificar que capitanes pueden ser seleccionados por otras alianzas ---")
    
    # Alianza 2 intenta seleccionar al capitán de Alianza 1
    alliance_1_captain = selector.alliances[0].captain
    alliance_2 = selector.alliances[1]
    
    available_for_alliance_2 = selector.get_available_teams(alliance_2.captainRank, 'pick1')
    captain_1_available = any(t.team == alliance_1_captain for t in available_for_alliance_2)
    print(f"¿Alianza 2 puede seleccionar al capitán de Alianza 1 (Team {alliance_1_captain})? {captain_1_available}")
    
    if captain_1_available:
        try:
            selector.set_pick(1, 'pick1', alliance_1_captain)
            print(f"✅ CORRECTO: Alianza 2 seleccionó al capitán de Alianza 1 (Team {alliance_1_captain})")
            
            # Verificar que se actualizaron los capitanes
            print(f"   Nuevo capitán de Alianza 1: {selector.alliances[0].captain}")
            print(f"   Team {alliance_1_captain} ahora es pick1 de Alianza 2")
            
        except Exception as e:
            print(f"❌ ERROR: {e}")
    else:
        print("❌ ERROR: El capitán no está disponible para selección")
    
    print("\n--- Test 2: Verificar que equipos seleccionados se quitan de opciones ---")
    
    # Obtener equipos disponibles para Alianza 3 antes de más selecciones
    alliance_3 = selector.alliances[2]
    available_before = selector.get_available_teams(alliance_3.captainRank, 'pick1')
    print(f"Equipos disponibles para Alianza 3 antes: {[t.team for t in available_before]}")
    
    # Alianza 3 selecciona un equipo
    if available_before:
        team_to_select = available_before[0].team
        selector.set_pick(2, 'pick1', team_to_select)
        print(f"Alianza 3 seleccionó Team {team_to_select}")
        
        # Verificar que este equipo ya no está disponible para Alianza 4
        alliance_4 = selector.alliances[3]
        available_for_alliance_4 = selector.get_available_teams(alliance_4.captainRank, 'pick1')
        team_still_available = any(t.team == team_to_select for t in available_for_alliance_4)
        
        print(f"¿Team {team_to_select} aún disponible para Alianza 4? {team_still_available}")
        if not team_still_available:
            print("✅ CORRECTO: Equipo seleccionado se quitó de opciones")
        else:
            print("❌ ERROR: Equipo seleccionado sigue en opciones")
    
    print("\n--- Test 3: Verificar que capitanes no pueden seleccionarse a sí mismos ---")
    
    alliance_4 = selector.alliances[3]
    alliance_4_captain = alliance_4.captain
    
    try:
        selector.set_pick(3, 'pick1', alliance_4_captain)
        print(f"❌ ERROR: Alianza 4 pudo seleccionar a su propio capitán (Team {alliance_4_captain})")
    except ValueError as e:
        print(f"✅ CORRECTO: {e}")
    
    print("\n--- Test 4: Verificar recomendaciones ---")
    
    for alliance in selector.alliances:
        pick1_rec = alliance.pick1Rec
        pick2_rec = alliance.pick2Rec
        
        # Verificar que las recomendaciones no son capitanes de la misma alianza
        is_self_captain = (pick1_rec == alliance.captain) or (pick2_rec == alliance.captain)
        
        print(f"Alianza {alliance.allianceNumber}:")
        print(f"  Capitán: {alliance.captain}")
        print(f"  Pick1: {alliance.pick1}, Recomendación: {pick1_rec}")
        print(f"  Pick2: {alliance.pick2}, Recomendación: {pick2_rec}")
        print(f"  ¿Recomienda su propio capitán? {is_self_captain}")
        
        if is_self_captain:
            print("  ❌ ERROR: Alianza recomienda su propio capitán")
        else:
            print("  ✅ Recomendaciones correctas")
    
    print("\n--- Test 5: Verificar tabla de alianzas ---")
    table = selector.get_alliance_table()
    for row in table:
        print(f"Alianza {row['Alliance #']}: Capitán {row['Captain']}, Pick1 {row['Pick 1']}, Pick2 {row['Pick 2']}, Score: {row['Alliance Score']}")
    
    print("\n--- Estado final de equipos seleccionados ---")
    selected_picks = selector.get_selected_picks()
    print(f"Equipos seleccionados como picks: {selected_picks}")
    
    all_captains = [a.captain for a in selector.alliances if a.captain]
    print(f"Capitanes actuales: {all_captains}")
    
    # Verificar que no hay duplicados
    all_selected = selected_picks + all_captains
    duplicates = [x for x in all_selected if all_selected.count(x) > 1]
    if duplicates:
        print(f"❌ ERROR: Equipos duplicados encontrados: {duplicates}")
    else:
        print("✅ No hay equipos duplicados")
    
    return selector

if __name__ == "__main__":
    selector = create_comprehensive_test()
    print("\n=== Test completado ===")
