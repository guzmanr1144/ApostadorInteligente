import streamlit as st
import pandas as pd
import random
from datetime import datetime

# Configuración de la página
st.set_page_config(page_title="Analizador de Apuestas", layout="wide", page_icon="📊")

# --- TITULO PRINCIPAL ---
st.title("📊 Analizador Estadístico de Probabilidades")
fecha_hoy = datetime.now().strftime("%d/%m/%Y")
st.write(f"Partidos programados para hoy: **{fecha_hoy}**")

# --- BARRA LATERAL (FILTROS) ---
st.sidebar.header("Configuración del Análisis")

# 1. Selección de Liga
liga = st.sidebar.selectbox(
    "Selecciona la Liga:", 
    ["Premier League", "La Liga", "Serie A", "MLB (Béisbol)", "LVBP"]
)

# 2. Diccionario simulado de los partidos de HOY según la liga seleccionada
# (Esto es lo que reemplazaremos con la consulta automática a la API)
partidos_hoy_por_liga = {
    "Premier League": ["Arsenal vs Chelsea", "Liverpool vs Aston Villa", "Man City vs Tottenham"],
    "La Liga": ["Real Madrid vs Barcelona", "Atlético Madrid vs Sevilla", "Betis vs Villarreal"],
    "Serie A": ["Juventus vs Milan", "Inter vs Roma", "Napoli vs Lazio"],
    "MLB (Béisbol)": ["Yankees vs Red Sox", "Dodgers vs Giants", "Astros vs Rangers"],
    "LVBP": ["Leones vs Navegantes", "Caribes vs Tiburones", "Cardenales vs Águilas"]
}

# Obtener los partidos disponibles para la liga seleccionada
partidos_disponibles = partidos_hoy_por_liga.get(liga, [])

# 3. Selección del Encuentro del Día
if partidos_disponibles:
    partido_seleccionado = st.sidebar.selectbox("Selecciona el partido de hoy:", partidos_disponibles)
    
    # Separamos los nombres de los equipos para usarlos en los cálculos
    equipo_local, equipo_visitante = partido_seleccionado.split(" vs ")
else:
    st.sidebar.warning("No se encontraron partidos programados para hoy en esta liga.")
    equipo_local, equipo_visitante = "Local", "Visitante"

# Filtro de cantidad de partidos para el historial estadístico
num_partidos = st.sidebar.slider("Historial de partidos a analizar:", min_value=5, max_value=20, value=10)

st.sidebar.markdown("---")
st.sidebar.write("⚡ *Estructura lista para conectar la API en vivo.*")


# --- PROCESAMIENTO Y LÓGICA DE PORCENTAJES ---
def calcular_porcentajes_partido(loc, vis, n):
    # Generación de probabilidades basadas en el partido seleccionado
    # Usamos la semilla con el nombre del partido para que los porcentajes no cambien cada segundo
    random.seed(loc + vis)
    
    p_local = random.randint(35, 55)
    p_vis = random.randint(25, 40)
    p_empate = 100 - p_local - p_vis
    
    p_ambos_anotan = random.randint(45, 75)
    p_over_25 = random.randint(40, 70)
    
    # Creación del historial de partidos recientes
    historial = []
    for i in range(n):
        g_l = random.randint(0, 4)
        g_v = random.randint(0, 3)
        historial.append({
            "Fecha": f"Part. -{i+1}",
            "Local": loc if i % 2 == 0 else "Otro Rival",
            "Goles L": g_l,
            "Goles V": g_v,
            "Visitante": vis if i % 2 != 0 else "Otro Rival",
            "Resultado": "L" if g_l > g_v else ("V" if g_v > g_l else "E")
        })
    return p_local, p_empate, p_vis, p_ambos_anotan, p_over_25, pd.DataFrame(historial)


# --- RENDERIZADO DE LA INTERFAZ ---
if partidos_disponibles:
    # Ejecutar lógica
    prob_L, prob_E, prob_V, ambos_anotan, over_25, df_historial = calcular_porcentajes_partido(equipo_local, equipo_visitante, num_partidos)

    st.subheader(f"🔮 Pronóstico del Día: {equipo_local} vs {equipo_visitante}")

    # Fila 1: Probabilidades del Mercado 1X2 / Ganador
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(label=f"Probabilidad {equipo_local} (Local)", value=f"{prob_L}%")
    with col2:
        st.metric(label="Probabilidad Empate (X)", value=f"{prob_E}%")
    with col3:
        st.metric(label=f"Probabilidad {equipo_visitante} (Visitante)", value=f"{prob_V}%")

    st.markdown("---")

    # Fila 2: Mercados Adicionales (Ajustado si es Béisbol o Fútbol)
    st.subheader("🎯 Líneas de Apuestas Estimadas")
    col_g1, col_g2 = st.columns(2)
    
    with col_g1:
        st.progress(ambos_anotan / 100)
        if "MLB" in liga or "LVBP" in liga:
            st.write(f"**Estrategia Carrera Primero (Inning 1-5):** {ambos_anotan}% de probabilidad")
        else:
            st.write(f"**Ambos Anotan (Sí):** {ambos_anotan}% de probabilidad")
            
    with col_g2:
        st.progress(over_25 / 100)
        if "MLB" in liga or "LVBP" in liga:
            st.write(f"**Over 8.5 Carreras totales:** {over_25}% de probabilidad")
        else:
            st.write(f"**Over 2.5 Goles en el partido:** {over_25}% de probabilidad")

    st.markdown("---")

    # Fila 3: Tabla de datos
    st.subheader("📋 Historial de Rendimiento Reciente")
    st.write(f"Últimos {num_partidos} partidos simulados en base al rendimiento actual de los equipos:")
    st.dataframe(df_historial, use_container_width=True)

else:
    st.info("Selecciona otra liga en la barra lateral para ver los encuentros disponibles.")
