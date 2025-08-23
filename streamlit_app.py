"""
Versión web del Alliance Simulator usando Streamlit
"""
import streamlit as st
import pandas as pd
import json
import io
from main_web import AnalizadorRobotWeb
from school_system import TeamScoring
from allianceSelector import AllianceSelector, Team, teams_from_dicts
from foreshadowing_web import predict_match  # nuevo para foreshadowing
from config_manager import ConfigManager
from csv_converter import CSVFormatConverter, convert_csv_file

# Configuración de la página
st.set_page_config(
    page_title="Alliance Simulator Web",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inicializar estado de la sesión
if 'analizador' not in st.session_state:
    st.session_state.analizador = AnalizadorRobotWeb()
if 'school_system' not in st.session_state:
    st.session_state.school_system = TeamScoring()
if 'config_manager' not in st.session_state:
    st.session_state.config_manager = ConfigManager()
if 'csv_converter' not in st.session_state:
    st.session_state.csv_converter = CSVFormatConverter(st.session_state.config_manager)

def main():
    st.title("🤖 Alliance Simulator Web")
    st.markdown("**Análisis de equipos de robótica y simulador de alianzas**")
    
    # Sidebar para navegación
    st.sidebar.title("📋 Navegación")
    page = st.sidebar.selectbox("Selecciona una página", [
        "📊 Datos y Configuración",
        "📈 Estadísticas de Equipos", 
        "🤝 Selector de Alianzas",
        "🔮 Foreshadowing",
        "🏆 Honor Roll System",
        "⚙️ Configuración de Sistema",
        "🔄 Conversión de CSV"
    ])
    
    if page == "📊 Datos y Configuración":
        page_data_config()
    elif page == "📈 Estadísticas de Equipos":
        page_team_stats()
    elif page == "🤝 Selector de Alianzas":
        page_alliance_selector()
    elif page == "🔮 Foreshadowing":
        page_foreshadowing()
    elif page == "🏆 Honor Roll System":
        page_honor_roll()
    elif page == "⚙️ Configuración de Sistema":
        page_system_configuration()
    elif page == "🔄 Conversión de CSV":
        page_csv_conversion()

def page_data_config():
    st.header("📊 Carga y Configuración de Datos")
    
    # Upload de archivo CSV
    st.subheader("📁 Cargar datos CSV")
    uploaded_file = st.file_uploader("Selecciona un archivo CSV", type=['csv'])
    
    if uploaded_file is not None:
        # Leer el contenido del CSV
        content = uploaded_file.getvalue().decode('utf-8')
        
        # Load using the web analyzer
        st.session_state.analizador.load_csv_from_text(content)
        
        # Mostrar información del archivo
        df = pd.read_csv(uploaded_file)
        st.success(f"✅ Archivo cargado: {len(df)} filas, {len(df.columns)} columnas")
        
        # Mostrar preview
        st.subheader("👀 Vista previa de los datos")
        st.dataframe(df.head(10), use_container_width=True)
    
    # Entrada manual de datos QR
    st.subheader("📱 Datos de QR Code")
    qr_data = st.text_area("Pega aquí los datos de QR codes (uno por línea):")
    if st.button("➕ Añadir datos QR") and qr_data:
        # For now, treat QR data as CSV text
        st.session_state.analizador.load_csv_from_text(qr_data)
        st.success("✅ Datos QR añadidos")
    
    # Mostrar datos actuales
    if st.session_state.analizador.sheet_data:
        st.subheader("📋 Datos actuales")
        current_data = st.session_state.analizador.sheet_data
        if len(current_data) > 1:
            df_current = pd.DataFrame(current_data[1:], columns=current_data[0])
            st.dataframe(df_current, use_container_width=True)
            st.info(f"Total: {len(current_data)-1} registros")

def page_team_stats():
    st.header("📈 Estadísticas de Equipos")
    
    if not st.session_state.analizador.sheet_data or len(st.session_state.analizador.sheet_data) <= 1:
        st.warning("⚠️ No hay datos cargados. Ve a la página 'Datos y Configuración' para cargar datos.")
        return
    
    # Estadísticas detalladas por equipo
    team_stats = st.session_state.analizador.get_detailed_team_stats()
    if team_stats:
        st.subheader("📊 Estadísticas detalladas por equipo")
        
        # Convertir a DataFrame para mejor visualización
        if team_stats:
            df_stats = pd.DataFrame(team_stats)
            st.dataframe(df_stats, use_container_width=True)
    
    # Información de configuración de columnas
    st.subheader("🎮 Configuración de Fases del Juego")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("**Autonomous**")
        auto_cols = st.session_state.analizador.get_autonomous_columns()
        if auto_cols:
            for col in auto_cols:
                st.write(f"• {col}")
        else:
            st.write("No configurado")
    
    with col2:
        st.markdown("**Teleop**")
        teleop_cols = st.session_state.analizador.get_teleop_columns()
        if teleop_cols:
            for col in teleop_cols:
                st.write(f"• {col}")
        else:
            st.write("No configurado")
    
    with col3:
        st.markdown("**Endgame**")
        endgame_cols = st.session_state.analizador.get_endgame_columns()
        if endgame_cols:
            for col in endgame_cols:
                st.write(f"• {col}")
        else:
            st.write("No configurado")

def page_alliance_selector():
    st.header("🤝 Selector de Alianzas")
    
    if not st.session_state.analizador.sheet_data:
        st.warning("⚠️ No hay datos cargados.")
        return
    
    st.subheader("⚙️ Configurar Equipos para Alliance Selector")
    
    # Obtener equipos disponibles
    team_data = st.session_state.analizador.get_team_data_grouped()
    if not team_data:
        st.warning("⚠️ No hay datos de equipos disponibles.")
        return
    
    # Crear equipos con puntajes calculados
    teams_for_selector = []
    for i, (team_num, _) in enumerate(team_data.items()):
        phase_scores = st.session_state.analizador.calculate_team_phase_scores(int(team_num))
        
        team_dict = {
            "num": int(team_num),
            "rank": i + 1,  # Ranking temporal
            "total_epa": phase_scores["autonomous"] + phase_scores["teleop"] + phase_scores["endgame"],
            "auto_epa": phase_scores["autonomous"],
            "teleop_epa": phase_scores["teleop"], 
            "endgame_epa": phase_scores["endgame"],
            "defense": False,  # Se puede configurar
            "name": f"Team {team_num}"
        }
        teams_for_selector.append(team_dict)
    
    # Crear selector de alianzas
    if st.button("🎯 Crear Alliance Selector"):
        teams = teams_from_dicts(teams_for_selector)
        selector = AllianceSelector(teams)
        st.session_state.alliance_selector = selector
        st.success("✅ Alliance Selector creado")
    
    # Mostrar selector si existe
    if 'alliance_selector' in st.session_state:
        selector = st.session_state.alliance_selector
        
        st.subheader("🏆 Tabla de Alianzas")
        alliance_table = selector.get_alliance_table()
        df_alliances = pd.DataFrame(alliance_table)
        st.dataframe(df_alliances, use_container_width=True)
        
        # Información del selector
        info = selector.get_selector_info()
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Equipos", info["total_teams"])
        with col2:
            st.metric("Alianzas Activas", info["active_alliances"])
        with col3:
            st.metric("Picks Seleccionados", len(info["selected_picks"]))
        with col4:
            st.metric("Disponibles", info["available_for_picks"])

def page_honor_roll():
    st.header("🏆 Honor Roll System")
    
    if not st.session_state.analizador.sheet_data:
        st.warning("⚠️ No hay datos cargados.")
        return
    
    # Auto-poblar con datos reales
    if st.button("🔄 Auto-poblar SchoolSystem con datos reales"):
        team_data = st.session_state.analizador.get_team_data_grouped()
        
        teams_added = 0
        teams_with_calculated_scores = 0
        
        for team_number in team_data.keys():
            st.session_state.school_system.add_team(team_number)
            
            # Calcular puntajes reales de fases del juego
            phase_scores = st.session_state.analizador.calculate_team_phase_scores(int(team_number))
            
            if any(score > 0 for score in phase_scores.values()):
                st.session_state.school_system.update_autonomous_score(team_number, phase_scores["autonomous"])
                st.session_state.school_system.update_teleop_score(team_number, phase_scores["teleop"])
                st.session_state.school_system.update_endgame_score(team_number, phase_scores["endgame"])
                teams_with_calculated_scores += 1
            else:
                # Valores por defecto
                st.session_state.school_system.update_autonomous_score(team_number, 75.0)
                st.session_state.school_system.update_teleop_score(team_number, 80.0)
                st.session_state.school_system.update_endgame_score(team_number, 70.0)
            
            # Puntajes por defecto para pit scouting
            st.session_state.school_system.update_electrical_score(team_number, 85.0)
            st.session_state.school_system.update_mechanical_score(team_number, 80.0)
            st.session_state.school_system.update_driver_station_layout_score(team_number, 75.0)
            st.session_state.school_system.update_tools_score(team_number, 70.0)
            st.session_state.school_system.update_spare_parts_score(team_number, 65.0)
            st.session_state.school_system.update_team_organization_score(team_number, 80.0)
            st.session_state.school_system.update_collaboration_score(team_number, 85.0)
            
            teams_added += 1
        
        st.success(f"✅ {teams_added} equipos añadidos. {teams_with_calculated_scores} con puntajes calculados.")
    
    # Mostrar ranking
    if st.session_state.school_system.teams:
        st.subheader("🏆 Honor Roll Ranking")
        
        rankings = st.session_state.school_system.get_honor_roll_ranking()
        
        if rankings:
            ranking_data = []
            for rank, (team_num, results) in enumerate(rankings, 1):
                ranking_data.append({
                    "Rank": rank,
                    "Equipo": team_num,
                    "Puntos Finales": results.final_points,
                    "Honor Roll Score": f"{results.honor_roll_score:.1f}",
                    "Score Curvado": f"{results.curved_score:.1f}",
                    "Match Performance": f"{results.match_performance_score:.1f}",
                    "Pit Scouting": f"{results.pit_scouting_score:.1f}",
                    "During Event": f"{results.during_event_score:.1f}"
                })
            
            df_ranking = pd.DataFrame(ranking_data)
            st.dataframe(df_ranking, use_container_width=True)
            
            # Estadísticas resumen
            stats = st.session_state.school_system.get_summary_stats()
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Equipos Calificados", stats.get('qualified_teams', 0))
            with col2:
                st.metric("Promedio Honor Roll", f"{stats.get('avg_honor_roll_score', 0):.1f}")
            with col3:
                st.metric("Promedio Puntos Finales", f"{stats.get('avg_final_points', 0):.1f}")

def page_phase_config():
    st.header("⚙️ Configuración de Fases del Juego")
    
    if not st.session_state.analizador.sheet_data:
        st.warning("⚠️ No hay datos cargados.")
        return
    
    headers = st.session_state.analizador.get_current_headers()
    
    # Auto-detectar columnas
    if st.button("🔍 Auto-detectar Columnas por Fase"):
        st.session_state.analizador._auto_detect_game_phase_columns()
        st.success("✅ Auto-detección completada")
    
    # Mostrar configuración actual
    st.subheader("📋 Configuración Actual")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.write("**🤖 Autonomous**")
        auto_cols = st.session_state.analizador.get_autonomous_columns()
        if auto_cols:
            for col in auto_cols:
                st.write(f"• {col}")
        else:
            st.write("*No configurado*")
    
    with col2:
        st.write("**🎮 Teleop**")
        teleop_cols = st.session_state.analizador.get_teleop_columns()
        if teleop_cols:
            for col in teleop_cols:
                st.write(f"• {col}")
        else:
            st.write("*No configurado*")
    
    with col3:
        st.write("**🏁 Endgame**")
        endgame_cols = st.session_state.analizador.get_endgame_columns()
        if endgame_cols:
            for col in endgame_cols:
                st.write(f"• {col}")
        else:
            st.write("*No configurado*")
    
    # Configuración manual
    st.subheader("✏️ Configuración Manual")
    
    with st.expander("Configurar Columnas Manualmente"):
        # Autonomous
        st.write("**Columnas Autonomous:**")
        selected_auto = st.multiselect("Selecciona columnas para Autonomous", 
                                     headers, 
                                     default=auto_cols,
                                     key="auto_select")
        
        # Teleop  
        st.write("**Columnas Teleop:**")
        selected_teleop = st.multiselect("Selecciona columnas para Teleop",
                                       headers,
                                       default=teleop_cols,
                                       key="teleop_select")
        
        # Endgame
        st.write("**Columnas Endgame:**")
        selected_endgame = st.multiselect("Selecciona columnas para Endgame",
                                        headers,
                                        default=endgame_cols,
                                        key="endgame_select")
        
        if st.button("💾 Aplicar Configuración Manual"):
            st.session_state.analizador.set_autonomous_columns(selected_auto)
            st.session_state.analizador.set_teleop_columns(selected_teleop)
            st.session_state.analizador.set_endgame_columns(selected_endgame)
            st.success("✅ Configuración aplicada")
            st.rerun()
    
    # Exportar/Importar configuración
    st.subheader("💾 Exportar/Importar Configuración")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📤 Exportar Configuración"):
            config = {
                "version": "1.0",
                "headers": headers,
                "column_configuration": {
                    "autonomous_columns": st.session_state.analizador.get_autonomous_columns(),
                    "teleop_columns": st.session_state.analizador.get_teleop_columns(),
                    "endgame_columns": st.session_state.analizador.get_endgame_columns(),
                }
            }
            
            config_json = json.dumps(config, indent=2)
            st.download_button(
                label="⬇️ Descargar configuración.json",
                data=config_json,
                file_name="phase_config.json",
                mime="application/json"
            )
    
    with col2:
        uploaded_config = st.file_uploader("📥 Importar Configuración", type=['json'])
        if uploaded_config is not None:
            try:
                config = json.load(uploaded_config)
                
                if "column_configuration" in config:
                    col_config = config["column_configuration"]
                    
                    if "autonomous_columns" in col_config:
                        st.session_state.analizador.set_autonomous_columns(col_config["autonomous_columns"])
                    if "teleop_columns" in col_config:
                        st.session_state.analizador.set_teleop_columns(col_config["teleop_columns"])
                    if "endgame_columns" in col_config:
                        st.session_state.analizador.set_endgame_columns(col_config["endgame_columns"])
                    
                    st.success("✅ Configuración importada exitosamente")
                    st.rerun()
                else:
                    st.error("❌ Formato de archivo inválido")
            except Exception as e:
                st.error(f"❌ Error al importar: {e}")

def page_foreshadowing():
    st.header("🔮 Foreshadowing – Predicción de Match")
    if not st.session_state.analizador.sheet_data or len(st.session_state.analizador.sheet_data) <= 1:
        st.warning("⚠️ Carga datos primero en 'Datos y Configuración'.")
        return
    team_data = st.session_state.analizador.get_team_data_grouped()
    if not team_data:
        st.warning("⚠️ No hay datos de equipos.")
        return
    teams_sorted = sorted(team_data.keys(), key=lambda t: int(t))
    st.subheader("Selecciona equipos (3 y 3)")
    col_r, col_b = st.columns(2)
    with col_r:
        red_sel = st.multiselect("Red Alliance", teams_sorted, key="fo_red", max_selections=3)
    with col_b:
        blue_sel = st.multiselect("Blue Alliance", teams_sorted, key="fo_blue", max_selections=3)
    col_btn1, col_btn2 = st.columns([1,1])
    with col_btn1:
        run = st.button("Predecir", type="primary")
    with col_btn2:
        rerun = st.button("Re-predecir (forzar modelo)")
    if run or rerun:
        if len(red_sel) != 3 or len(blue_sel) != 3:
            st.error("Debes elegir exactamente 3 equipos por alianza")
        else:
            result = predict_match(st.session_state.analizador, red_sel, blue_sel)
            red_stats = result['red']; blue_stats = result['blue']; sim = result['simulation']
            st.subheader("Resultado esperado")
            c1,c2,c3 = st.columns(3)
            with c1: st.metric("Red Mean Pts", f"{sim['red_mean']:.1f}")
            with c2: st.metric("Blue Mean Pts", f"{sim['blue_mean']:.1f}")
            with c3: st.metric("Δ", f"{sim['red_mean']-sim['blue_mean']:.1f}")
            st.markdown("### Detalle por Equipo")
            def team_table(alliance_stats, color_name):
                rows=[]
                climb_rows=[]
                for t in alliance_stats['teams']:
                    auto_levels = [t['auto_L1'], t['auto_L2'], t['auto_L3'], t['auto_L4']]
                    tele_levels = [t['tele_L1'], t['tele_L2'], t['tele_L3'], t['tele_L4']]
                    auto_total = sum(auto_levels)
                    tele_total = sum(tele_levels)
                    total_coral = auto_total + tele_total
                    climb_dist = t['climb_dist']
                    exp_climb_pts = 0.0
                    for cat, p in climb_dist.items():
                        exp_climb_pts += p * result['config'].climb_points.get(cat, 0)
                    rows.append({
                        'Equipo': t['team'],
                        'Auto L1': round(t['auto_L1'],2), 'Auto L2': round(t['auto_L2'],2), 'Auto L3': round(t['auto_L3'],2), 'Auto L4': round(t['auto_L4'],2),
                        'Tele L1': round(t['tele_L1'],2), 'Tele L2': round(t['tele_L2'],2), 'Tele L3': round(t['tele_L3'],2), 'Tele L4': round(t['tele_L4'],2),
                        'Auto Total': round(auto_total,2), 'Tele Total': round(tele_total,2), 'Total Coral': round(total_coral,2),
                        'pAuto': round(t['p_auto'],2), 'CoopProb': round(t['coop_prob'],2),
                        'Best Climb': t['best_climb'], 'Exp ClimbPts': round(exp_climb_pts,2)
                    })
                    # Climb distribution normalized %
                    climb_rows.append({
                        'Equipo': t['team'],
                        'Deep %': round(climb_dist.get('deep',0)*100,1),
                        'Shallow %': round(climb_dist.get('shallow',0)*100,1),
                        'Park %': round(climb_dist.get('park',0)*100,1),
                        'None %': round(climb_dist.get('none',0)*100,1)
                    })
                st.markdown(f"**{color_name} Alliance**")
                st.dataframe(pd.DataFrame(rows), use_container_width=True)
                with st.expander(f"Distribución de Climb {color_name}"):
                    st.dataframe(pd.DataFrame(climb_rows), use_container_width=True)
            col_red, col_blue = st.columns(2)
            with col_red: team_table(red_stats, "RED")
            with col_blue: team_table(blue_stats, "BLUE")
            st.markdown("### Totales de Alianza (Esperados)")
            agg_rows=[]
            for label, stats in (('RED', red_stats), ('BLUE', blue_stats)):
                agg_rows.append({
                    'Alianza': label,
                    'L1 Total': round(stats['agg_total']['L1'],2),
                    'L2 Total': round(stats['agg_total']['L2'],2),
                    'L3 Total': round(stats['agg_total']['L3'],2),
                    'L4 Total': round(stats['agg_total']['L4'],2),
                    'Auto L1': round(stats['agg_auto']['L1'],2),
                    'Auto L2': round(stats['agg_auto']['L2'],2),
                    'Auto L3': round(stats['agg_auto']['L3'],2),
                    'Auto L4': round(stats['agg_auto']['L4'],2),
                    'Exp Climb Pts': round(stats['expected_climb_points'],2)
                })
            st.dataframe(pd.DataFrame(agg_rows), use_container_width=True)
            with st.expander("Distribución Monte Carlo (primeros 50 samples)"):
                mc_df = pd.DataFrame({
                    'Red': sim['red_samples'][:50],
                    'Blue': sim['blue_samples'][:50]
                })
                st.dataframe(mc_df)
                st.caption("Muestras truncadas a 50 para visualización rápida")
            st.success("Predicción generada")

def page_system_configuration():
    """Page for system configuration management"""
    st.header("⚙️ Configuración de Sistema")
    
    config_manager = st.session_state.config_manager
    
    # Configuration Presets
    st.subheader("📋 Presets de Configuración")
    presets = config_manager.get_configuration_presets()
    
    preset_names = list(presets.keys())
    if preset_names:
        selected_preset = st.selectbox("Seleccionar preset:", preset_names)
        
        if st.button("Aplicar Preset", type="primary"):
            config_manager.apply_preset(selected_preset)
            st.session_state.analizador.apply_configuration_preset(selected_preset)
            st.success(f"✅ Preset '{presets[selected_preset]['name']}' aplicado correctamente")
            st.rerun()
        
        # Show preset details
        if selected_preset:
            preset_info = presets[selected_preset]
            st.info(f"**{preset_info['name']}**: {preset_info['description']}")
    
    st.divider()
    
    # Current Configuration
    st.subheader("🔧 Configuración Actual")
    
    # Column Configuration
    column_config = config_manager.get_column_config()
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Columnas Numéricas (Overall)**")
        st.write(f"Total: {len(column_config.numeric_for_overall)}")
        with st.expander("Ver columnas"):
            for col in column_config.numeric_for_overall:
                st.write(f"• {col}")
    
    with col2:
        st.markdown("**Columnas de Estadísticas**")
        st.write(f"Total: {len(column_config.stats_columns)}")
        with st.expander("Ver columnas"):
            for col in column_config.stats_columns:
                st.write(f"• {col}")
    
    # Game Phase Configuration
    st.subheader("🎮 Configuración de Fases del Juego")
    
    phase_col1, phase_col2, phase_col3 = st.columns(3)
    
    with phase_col1:
        st.markdown("**Autonomous**")
        st.write(f"Columnas: {len(column_config.autonomous_columns)}")
        with st.expander("Ver columnas"):
            for col in column_config.autonomous_columns:
                st.write(f"• {col}")
    
    with phase_col2:
        st.markdown("**Teleop**")
        st.write(f"Columnas: {len(column_config.teleop_columns)}")
        with st.expander("Ver columnas"):
            for col in column_config.teleop_columns:
                st.write(f"• {col}")
    
    with phase_col3:
        st.markdown("**Endgame**")
        st.write(f"Columnas: {len(column_config.endgame_columns)}")
        with st.expander("Ver columnas"):
            for col in column_config.endgame_columns:
                st.write(f"• {col}")
    
    # Robot Valuation Configuration
    st.subheader("🤖 Configuración de Valuación de Robots")
    
    robot_config = config_manager.get_robot_valuation_config()
    
    st.write("**Pesos de Fases:**")
    for i, (phase, weight) in enumerate(zip(robot_config.phase_names, robot_config.phase_weights)):
        st.write(f"• {phase}: {weight}")
    
    # Save Configuration
    st.divider()
    if st.button("💾 Guardar Configuración Actual", type="secondary"):
        st.session_state.analizador.save_configuration()
        st.success("✅ Configuración guardada correctamente")

def page_csv_conversion():
    """Page for CSV format conversion"""
    st.header("🔄 Conversión de Formato CSV")
    
    st.markdown("""
    Esta herramienta permite convertir archivos CSV del formato antiguo al nuevo formato estándar.
    El sistema detecta automáticamente el formato y realiza la conversión necesaria.
    """)
    
    # File Upload
    st.subheader("📁 Subir Archivo CSV")
    uploaded_file = st.file_uploader("Selecciona un archivo CSV", type=['csv'])
    
    if uploaded_file is not None:
        # Save uploaded file temporarily
        import tempfile
        import os
        
        with tempfile.NamedTemporaryFile(mode='w+', suffix='.csv', delete=False) as tmp_file:
            content = uploaded_file.getvalue().decode('utf-8')
            tmp_file.write(content)
            tmp_file_path = tmp_file.name
        
        try:
            # Detect format
            csv_converter = st.session_state.csv_converter
            
            # Read headers for format detection
            with open(tmp_file_path, 'r', encoding='utf-8') as f:
                import csv
                reader = csv.reader(f)
                headers = next(reader)
            
            detected_format = st.session_state.config_manager.detect_csv_format(headers)
            
            st.subheader("📊 Información del Archivo")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Formato Detectado", detected_format.replace('_', ' ').title())
            with col2:
                st.metric("Columnas", len(headers))
            with col3:
                # Count data rows
                with open(tmp_file_path, 'r', encoding='utf-8') as f:
                    reader = csv.reader(f)
                    data_rows = sum(1 for row in reader) - 1  # Exclude header
                st.metric("Filas de Datos", data_rows)
            
            # Show first few headers
            st.subheader("🗂️ Primeras Columnas del Archivo")
            st.write(", ".join(headers[:10]) + ("..." if len(headers) > 10 else ""))
            
            if detected_format == "legacy_format":
                st.warning("⚠️ Archivo en formato antiguo detectado. Se recomienda conversión.")
                
                if st.button("🔄 Convertir a Nuevo Formato", type="primary"):
                    try:
                        # Perform conversion
                        with st.spinner("Convirtiendo archivo..."):
                            converted_file_path = tmp_file_path.replace('.csv', '_converted.csv')
                            detected_format, output_file = csv_converter.detect_and_convert_file(
                                tmp_file_path, converted_file_path
                            )
                        
                        # Validate conversion
                        validation_report = csv_converter.validate_converted_data(output_file)
                        
                        st.success("✅ Conversión completada exitosamente!")
                        
                        # Show validation results
                        st.subheader("📋 Reporte de Validación")
                        
                        val_col1, val_col2, val_col3, val_col4 = st.columns(4)
                        with val_col1:
                            st.metric("Filas Totales", validation_report.get('total_rows', 0))
                        with val_col2:
                            st.metric("Columnas", validation_report.get('total_columns', 0))
                        with val_col3:
                            st.metric("Filas Vacías", validation_report.get('empty_rows', 0))
                        with val_col4:
                            st.metric("Filas Incompletas", validation_report.get('incomplete_rows', 0))
                        
                        # Data quality
                        if validation_report.get('data_quality'):
                            st.subheader("📈 Calidad de Datos")
                            quality_data = []
                            for col, info in validation_report['data_quality'].items():
                                quality_data.append({
                                    'Columna': col,
                                    'Completitud (%)': f"{info['completion_rate']:.1f}%",
                                    'Valores Vacíos': info['empty_count']
                                })
                            
                            if quality_data:
                                st.dataframe(pd.DataFrame(quality_data), use_container_width=True)
                        
                        # Download converted file
                        with open(output_file, 'r', encoding='utf-8') as f:
                            converted_content = f.read()
                        
                        st.download_button(
                            label="📥 Descargar Archivo Convertido",
                            data=converted_content,
                            file_name=f"{uploaded_file.name.replace('.csv', '_converted.csv')}",
                            mime='text/csv'
                        )
                        
                    except Exception as e:
                        st.error(f"❌ Error durante la conversión: {e}")
                        
            elif detected_format == "new_format":
                st.success("✅ El archivo ya está en el formato correcto.")
                
                # Option to load directly
                if st.button("📊 Cargar Datos en el Sistema", type="primary"):
                    try:
                        st.session_state.analizador.load_csv(tmp_file_path)
                        st.success("✅ Datos cargados exitosamente en el sistema!")
                        st.info("Ve a la página 'Datos y Configuración' para ver los datos cargados.")
                    except Exception as e:
                        st.error(f"❌ Error al cargar datos: {e}")
                        
            else:
                st.warning("⚠️ Formato desconocido. El archivo podría no ser compatible.")
                st.info("Puedes intentar cargarlo de todas formas, pero algunas funciones podrían no funcionar correctamente.")
        
        finally:
            # Clean up temporary file
            if os.path.exists(tmp_file_path):
                os.unlink(tmp_file_path)
    
    # Manual CSV Format Converter
    st.divider()
    st.subheader("🛠️ Convertidor Manual")
    st.markdown("""
    Si tienes un archivo CSV en tu computadora, puedes usar esta herramienta para convertirlo.
    """)
    
    # Format mapping information
    with st.expander("📖 Información de Mapeo de Formatos"):
        st.markdown("""
        **Formato Antiguo → Nuevo Formato:**
        
        - `Lead Scouter` → `Scouter Initials`
        - `Future Alliance in Qualy?` → `Future Alliance`
        - `Coral L1 Scored` → `Coral L1 (Teleop)`
        - `Coral L2 Scored` → `Coral L2 (Teleop)`
        - `Coral L3 Scored` → `Coral L3 (Teleop)`
        - `Coral L4 Scored` → `Coral L4 (Teleop)`
        - `Algae Scored in Barge` → `Barge Algae (Teleop)`
        - `Crossed Feild/Played Defense?` → `Crossed Field/Defense`
        - `Did auton worked?` → `Moved (Auto)`
        - `Did Foul?` → `Foul (Auto)`
        - Y más...
        
        **Valores por Defecto para Columnas Nuevas:**
        - `Robot`: 1
        - `Starting Position`: Unknown
        - `No Show`: False
        - `End Position`: Unknown
        """)

if __name__ == "__main__":
    main()
