import streamlit as st
import pandas as pd
import random

# Configuración de la página (Debe ser la primera línea de Streamlit)
st.set_page_config(page_title="Analizador de Apuestas", layout="wide", page_icon="📊")

# --- TITULO PRINCIPAL ---
st.title("📊 Analizador Estadístico de Probabilidades")
st.write("Calculadora de porcentajes basada en rendimiento histórico reciente.")

# --- BARRA LATERAL (FILTROS) ---
st.sidebar.header("Configuración del Análisis")

# Selección de Liga y Equipos
liga = st.sidebar.selectbox("Selecciona la Liga:", ["Premier League", "La Liga", "Serie A", "LVBP / MLB", "Otra"])
equipo_local = st.sidebar.text_input("Equipo Local:", value="Real Madrid")
equipo_visitante = st.sidebar.text_input("Equipo Visitante:", value="Barcelona")

# Filtro de cantidad de partidos para la muestra
num_partidos = st.sidebar.slider("Partidos a analizar (Historial):", min_value=5, max_value=20, value=10)

st.sidebar.markdown("---")
st.sidebar.write("⚡ *Próximamente: Conexión directa con API en vivo.*")


# --- PROCESAMIENTO Y LÓGICA (Simulación temporal de datos) ---
# Esta función generará datos simulados para que veas la estructura en vivo.
# En el próximo paso la reemplazaremos con la llamada real a internet.
def simular_datos_analisis(loc, vis, n):
    # Simulamos porcentajes que sumen 100%
    p_local = random.randint(35, 55)
    p_vis = random.randint(25, 40)
    p_empate = 100 - p_local - p_vis
    
    p_ambos_anotan = random.randint(45, 75)
    p_over_25 = random.randint(40, 70)
    
    # Simulación de tabla de últimos partidos
    historial = []
    for i in range(n):
        g_l = random.randint(0, 4)
        g_v = random.randint(0, 3)
        historial.append({
            "Fecha": f"Part. -{i+1}",
            "Local": loc if i%2==0 else "Otro",
            "Goles L": g_l,
            "Goles V": g_v,
            "Visitante": vis if i%2!=0 else "Otro",
            "Resultado": "L" if g_l > g_v else ("V" if g_v > g_l else "E")
        })
    return p_local, p_empate, p_vis, p_ambos_anotan, p_over_25, pd.DataFrame(historial)

# Ejecutar los cálculos básicos
prob_L, prob_E, prob_V, ambos_anotan, over_25, df_historial = simular_datos_analisis(equipo_local, equipo_visitante, num_partidos)


# --- INTERFAZ CENTRAL (Métricas y Porcentajes) ---

st.subheader(f"🔮 Pronóstico: {equipo_local} vs {equipo_visitante}")

# Fila 1: Probabilidades del Mercado 1X2
col1, col2, col3 = st.columns(3)
with col1:
    st.metric(label=f"Gana {equipo_local} (1)", value=f"{prob_L}%")
with col2:
    st.metric(label="Empate (X)", value=f"{prob_E}%")
with col3:
    st.metric(label=f"Gana {equipo_visitante} (2)", value=f"{prob_V}%")

st.markdown("---")

# Fila 2: Mercados de Goles
st.subheader("⚽ Mercados de Goles Estimados")
col_g1, col_g2 = st.columns(2)
with col_g1:
    st.progress(ambos_anotan / 100)
    st.write(f"**Ambos Anotan (Sí):** {ambos_anotan}% de probabilidad")
with col_g2:
    st.progress(over_25 / 100)
    st.write(f"**Over 2.5 Goles:** {over_25}% de probabilidad")

st.markdown("---")

# Fila 3: Tabla de datos crudos analizados
st.subheader("📋 Historial de Rendimiento Reciente")
st.write(f"Últimos {num_partidos} partidos considerados para el cálculo:")
st.dataframe(df_historial, use_container_width=True)
