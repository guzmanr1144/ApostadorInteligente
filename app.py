"""
Proyector de Baloncesto - Formato 40 Minutos (FIBA / Ligas Nacionales)
---------------------------------------------------------------------
Calculado para partidos de 4 cuartos de 10 minutos.
"""

import streamlit as st

st.set_page_config(page_title="Proyector Basket 40 Min", page_icon="🏀", layout="centered")

st.title("🏀 Proyector de Puntos (Formato 40 Minutos)")
st.write("Herramienta calibrada para partidos FIBA y ligas de 4 cuartos de 10 minutos.")

# --------------------------------------------------------------------------
# Configuración de Sensibilidad (Barra Lateral)
# --------------------------------------------------------------------------
with st.sidebar:
    st.header("⚙️ Ajustes del Modelo")
    
    penalizacion_3pt = st.slider(
        "Penalización por regresión de triples (%):",
        min_value=5, max_value=25, value=12, step=1,
        help="Porcentaje que se reducirá la anotación de 3PT en la 2ª mitad si un equipo dependió demasiado del triple en la 1ª mitad."
    )
    
    umbral_dep_3pt = st.slider(
        "Umbral de dependencia de 3PT (% del total de pts):",
        min_value=35, max_value=55, value=40, step=5,
        help="Si los triples representan más de este porcentaje en la 1ª mitad, se aplica la regresión."
    )

# --------------------------------------------------------------------------
# Entrada de Datos
# --------------------------------------------------------------------------
st.subheader("📊 Marcador y Estadísticas al Medio Tiempo (20 Min)")

col_local, col_vis = st.columns(2)

with col_local:
    st.markdown("### 🏠 Equipo Local")
    pts_2_loc = st.number_input("Puntos de 2 (Local)", min_value=0, value=20, step=2)
    pts_3_loc = st.number_input("Puntos de 3 (Local)", min_value=0, value=15, step=3)
    pts_tl_loc = st.number_input("Puntos de TL (Local)", min_value=0, value=4, step=1)
    faltas_loc = st.number_input("Faltas Cometidas (Local)", min_value=0, value=7, step=1)

with col_vis:
    st.markdown("### ✈️ Equipo Visitante")
    pts_3_vis = st.number_input("Puntos de 3 (Visitante)", min_value=0, value=12, step=3)
    pts_2_vis = st.number_input("Puntos de 2 (Visitante)", min_value=0, value=18, step=2)
    pts_tl_vis = st.number_input("Puntos de TL (Visitante)", min_value=0, value=5, step=1)
    faltas_vis = st.number_input("Faltas Cometidas (Visitante)", min_value=0, value=8, step=1)

# --------------------------------------------------------------------------
# Lógica de Cálculo (Calibración 40 Minutos)
# --------------------------------------------------------------------------
if st.button("📐 Calcular Proyección Final", type="primary", use_container_width=True):
    total_loc_1h = pts_2_loc + pts_3_loc + pts_tl_loc
    total_vis_1h = pts_2_vis + pts_3_vis + pts_tl_vis
    total_1h = total_loc_1h + total_vis_1h

    # 1. Porcentaje de puntos provenientes del triple
    pct_3_loc = (pts_3_loc / total_loc_1h) if total_loc_1h > 0 else 0
    pct_3_vis = (pts_3_vis / total_vis_1h) if total_vis_1h > 0 else 0

    # Factores de regresión configurables
    factor_3_loc = (1.0 - (penalizacion_3pt / 100)) if (pct_3_loc * 100) > umbral_dep_3pt else 1.0
    factor_3_vis = (1.0 - (penalizacion_3pt / 100)) if (pct_3_vis * 100) > umbral_dep_3pt else 1.0

    # 2. Ajuste por Faltas en Formato 40 Min (En 20 min, >=15 faltas ya es ritmo alto)
    faltas_totales = faltas_loc + faltas_vis
    if faltas_totales >= 18:
        bono_faltas = 5  # Juego muy cortado, muchos tiros libres
    elif faltas_totales >= 14:
        bono_faltas = 3
    else:
        bono_faltas = 0

    # 3. Proyección de la 2ª Mitad (20 Min restantes)
    proj_2h_loc = pts_2_loc + (pts_3_loc * factor_3_loc) + pts_tl_loc + (bono_faltas / 2)
    proj_2h_vis = pts_2_vis + (pts_3_vis * factor_3_vis) + pts_tl_vis + (bono_faltas / 2)

    final_loc = round(total_loc_1h + proj_2h_loc)
    final_vis = round(total_vis_1h + proj_2h_vis)
    total_proyectado = final_loc + final_vis

    # --------------------------------------------------------------------------
    # Resultados
    # --------------------------------------------------------------------------
    st.markdown("---")
    st.subheader("🎯 Marcador Proyectado (40 Minutos)")

    c1, c2, c3 = st.columns(3)
    c1.metric("Puntos 1ª Mitad", f"{total_1h} pts", f"{total_loc_1h} - {total_vis_1h}")
    c2.metric("Proyección Final", f"{total_proyectado} pts", f"{final_loc} - {final_vis}")
    c3.metric("Rango FIBA (±4)", f"{total_proyectado - 4} - {total_proyectado + 4} pts")

    st.success(f"**Marcador Estimado:** Local **{final_loc}** — **{final_vis}** Visitante")

    # Diagnóstico del partido
    st.markdown("### 💡 Análisis del Cálculo:")
    
    if (pct_3_loc * 100) > umbral_dep_3pt:
        st.warning(f"⚠️ **Local:** El {pct_3_loc:.0%} de sus puntos vinieron de triples. Se aplicó un ajuste de -{penalizacion_3pt}% a sus triples proyectados.")
    if (pct_3_vis * 100) > umbral_dep_3pt:
        st.warning(f"⚠️ **Visitante:** El {pct_3_vis:.0%} de sus puntos vinieron de triples. Se aplicó un ajuste de -{penalizacion_3pt}% a sus triples proyectados.")
    
    if faltas_totales >= 14:
        st.info(f"🏀 **Impacto de Faltas ({faltas_totales} acumuladas):** Se proyecta un cierre con bastantes tiros libres (+{bono_faltas} pts totales).")
