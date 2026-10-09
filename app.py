"""
Proyector de Baloncesto - Formato 40 Minutos (100% Automático)
--------------------------------------------------------------
Calcula automáticamente tiros libres, dependencia de triples y 
proyecciones finales sin necesidad de menús ni configuraciones.
"""

import streamlit as st

st.set_page_config(page_title="Proyector Basket 40 Min", page_icon="🏀", layout="centered")

st.title("🏀 Proyector de Puntos (Formato 40 Minutos)")
st.write("Herramienta de cálculo automático para partidos FIBA y ligas de 4 cuartos de 10 minutos.")

# --------------------------------------------------------------------------
# Entrada de Datos Simplificada
# --------------------------------------------------------------------------
st.subheader("📊 Marcador al Medio Tiempo (20 Min)")

col_local, col_vis = st.columns(2)

with col_local:
    st.markdown("### 🏠 Equipo Local")
    pts_tot_loc = st.number_input("Puntos Totales 1ª Mitad (Local)", min_value=0, value=39, step=1)
    pts_2_loc = st.number_input("Puntos de 2 (Local)", min_value=0, value=20, step=2)
    pts_3_loc = st.number_input("Puntos de 3 (Local)", min_value=0, value=15, step=3)
    faltas_loc = st.number_input("Faltas Cometidas (Local)", min_value=0, value=7, step=1)

with col_vis:
    st.markdown("### ✈️ Equipo Visitante")
    pts_tot_vis = st.number_input("Puntos Totales 1ª Mitad (Visitante)", min_value=0, value=35, step=1)
    pts_2_vis = st.number_input("Puntos de 2 (Visitante)", min_value=0, value=18, step=2)
    pts_3_vis = st.number_input("Puntos de 3 (Visitante)", min_value=0, value=12, step=3)
    faltas_vis = st.number_input("Faltas Cometidas (Visitante)", min_value=0, value=8, step=1)

# --------------------------------------------------------------------------
# Cálculo Automático
# --------------------------------------------------------------------------
if st.button("📐 Calcular Proyección Final", type="primary", use_container_width=True):
    # 1. Deducción automática de Tiros Libres
    pts_tl_loc = pts_tot_loc - (pts_2_loc + pts_3_loc)
    pts_tl_vis = pts_tot_vis - (pts_2_vis + pts_3_vis)

    if pts_tl_loc < 0 or pts_tl_vis < 0:
        st.error("❌ Los puntos de 2 y 3 no pueden sumar más que el total ingresado. Verifica los datos.")
        st.stop()

    total_1h = pts_tot_loc + pts_tot_vis

    # 2. Cálculo automático de Dependencia de Triples
    pct_3_loc = (pts_3_loc / pts_tot_loc) if pts_tot_loc > 0 else 0
    pct_3_vis = (pts_3_vis / pts_tot_vis) if pts_tot_vis > 0 else 0

    # Si más del 40% de sus puntos son triples, aplica corrección del 12% automáticamente
    factor_3_loc = 0.88 if pct_3_loc >= 0.40 else 1.0
    factor_3_vis = 0.88 if pct_3_vis >= 0.40 else 1.0

    # 3. Ajuste automático por Faltas acumuladas
    faltas_totales = faltas_loc + faltas_vis
    if faltas_totales >= 18:
        bono_faltas = 5
    elif faltas_totales >= 14:
        bono_faltas = 3
    else:
        bono_faltas = 0

    # 4. Proyección de la 2ª Mitad
    proj_2h_loc = pts_2_loc + (pts_3_loc * factor_3_loc) + pts_tl_loc + (bono_faltas / 2)
    proj_2h_vis = pts_2_vis + (pts_3_vis * factor_3_vis) + pts_tl_vis + (bono_faltas / 2)

    final_loc = round(pts_tot_loc + proj_2h_loc)
    final_vis = round(pts_tot_vis + proj_2h_vis)
    total_proyectado = final_loc + final_vis

    # --------------------------------------------------------------------------
    # Muestra de Resultados
    # --------------------------------------------------------------------------
    st.markdown("---")
    st.subheader("🎯 Marcador Proyectado")

    c1, c2, c3 = st.columns(3)
    c1.metric("Puntos 1ª Mitad", f"{total_1h} pts", f"{pts_tot_loc} - {pts_tot_vis}")
    c2.metric("Proyección Final", f"{total_proyectado} pts", f"{final_loc} - {final_vis}")
    c3.metric("Rango Estimado (±4)", f"{total_proyectado - 4} - {total_proyectado + 4} pts")

    st.success(f"**Resultado Final Estimado:** Local **{final_loc}** — **{final_vis}** Visitante")

    # Diagnóstico automático simplificado
    st.markdown("### 📋 Diagnóstico Calculado:")
    col_a, col_b = st.columns(2)
    col_a.info(f"🏠 **Local:** {pts_tl_loc} pts de TL | Dependencia de 3PT: **{pct_3_loc:.0%}**")
    col_b.info(f"✈️ **Visitante:** {pts_tl_vis} pts de TL | Dependencia de 3PT: **{pct_3_vis:.0%}**")

    if pct_3_loc >= 0.40:
        st.warning(f"⚠️ **Local:** Dependencia alta de triples ({pct_3_loc:.0%}). Se aplicó ajuste de desaceleración para la 2ª mitad.")
    if pct_3_vis >= 0.40:
        st.warning(f"⚠️ **Visitante:** Dependencia alta de triples ({pct_3_vis:.0%}). Se aplicó ajuste de desaceleración para la 2ª mitad.")

    if faltas_totales >= 14:
        st.info(f"🏀 **Impacto de Faltas ({faltas_totales} totales):** Juego físico. Se agregaron +{bono_faltas} pts proyectados desde la línea de tiros libres.")
