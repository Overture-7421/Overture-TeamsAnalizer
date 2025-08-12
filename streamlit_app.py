"""
Versión web del Alliance Simulator usando Streamlit
"""
import streamlit as st
import pandas as pd
import json
import io
from main import AnalizadorRobot
from school_system import TeamScoring
from allianceSelector import AllianceSelector, Team, teams_from_dicts

# Configuración de la página
st.set_page_config(
    page_title="Alliance Simulator Web",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inicializar estado de la sesión
if 'analizador' not in st.session_state:
    st.session_state.analizador = AnalizadorRobot()
if 'school_system' not in st.session_state:
    st.session_state.school_system = TeamScoring()

def main():
    st.title("🤖 Alliance Simulator Web")
    st.markdown("**Análisis de equipos de robótica y simulador de alianzas**")
    
    # Sidebar para navegación
    st.sidebar.title("📋 Navegación")
    page = st.sidebar.selectbox("Selecciona una página", [
        "📊 Datos y Configuración",
        "📈 Estadísticas de Equipos", 
        "🤝 Selector de Alianzas",
        "🏆 Honor Roll System",
        "⚙️ Configuración de Fases"
    ])
    
    if page == "📊 Datos y Configuración":
        page_data_config()
    elif page == "📈 Estadísticas de Equipos":
        page_team_stats()
    elif page == "🤝 Selector de Alianzas":
        page_alliance_selector()
    elif page == "🏆 Honor Roll System":
        page_honor_roll()
    elif page == "⚙️ Configuración de Fases":
        page_phase_config()

def page_data_config():
    st.header("📊 Carga y Configuración de Datos")
    
    # Upload de archivo CSV
    st.subheader("📁 Cargar datos CSV")
    uploaded_file = st.file_uploader("Selecciona un archivo CSV", type=['csv'])
    
    if uploaded_file is not None:
        # Leer el CSV
        df = pd.read_csv(uploaded_file)
        st.success(f"✅ Archivo cargado: {len(df)} filas, {len(df.columns)} columnas")
        
        # Mostrar preview
        st.subheader("👀 Vista previa de los datos")
        st.dataframe(df.head(10), use_container_width=True)
        
        # Convertir a formato del analizador
        if st.button("🔄 Procesar datos"):
            # Convertir DataFrame a formato del analizador
            sheet_data = [df.columns.tolist()] + df.values.tolist()
            st.session_state.analizador.sheet_data = sheet_data
            st.session_state.analizador._update_column_indices()
            st.success("✅ Datos procesados exitosamente")
    
    # Entrada manual de datos QR
    st.subheader("📱 Datos de QR Code")
    qr_data = st.text_area("Pega aquí los datos de QR codes (uno por línea):")
    if st.button("➕ Añadir datos QR") and qr_data:
        st.session_state.analizador.load_qr_data(qr_data)
        st.success("✅ Datos QR añadidos")
    
    # Mostrar datos actuales
    if st.session_state.analizador.sheet_data:
        st.subheader("📋 Datos actuales")
        current_data = st.session_state.analizador.get_raw_data()
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
        stats_rows = []
        for team_num, stats in team_stats.items():
            row = {"Equipo": team_num}
            row.update(stats)
            stats_rows.append(row)
        
        if stats_rows:
            df_stats = pd.DataFrame(stats_rows)
            st.dataframe(df_stats, use_container_width=True)
    
    # Puntajes por fase del juego
    st.subheader("🎮 Puntajes por Fase del Juego")
    team_data = st.session_state.analizador.get_team_data_grouped()
    
    if team_data:
        phase_scores = []
        for team_num in team_data.keys():
            scores = st.session_state.analizador.calculate_team_phase_scores(int(team_num))
            scores['Equipo'] = team_num
            phase_scores.append(scores)
        
        if phase_scores:
            df_phases = pd.DataFrame(phase_scores)
            df_phases = df_phases[['Equipo', 'autonomous', 'teleop', 'endgame']]
            df_phases.columns = ['Equipo', 'Autonomous', 'Teleop', 'Endgame']
            
            # Mostrar tabla
            st.dataframe(df_phases, use_container_width=True)
            
            # Gráfico de barras
            st.subheader("📊 Visualización de Puntajes por Fase")
            df_plot = df_phases.set_index('Equipo')
            st.bar_chart(df_plot)

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

if __name__ == "__main__":
    main()
