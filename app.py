"""
Proyector de Baloncesto - Formato 40 Minutos (FIBA / Ligas Nacionales)
---------------------------------------------------------------------
Permite proyectar al Medio Tiempo (20 min) o especificando el minuto exacto
en curso durante el 3er Cuarto (del minuto 21 al 30).
"""

import streamlit as st

st.set_page_config(page_title="Proyector Basket 40 Min", page_icon="🏀", layout="centered")

st.title("🏀 Proyector de Puntos (Formato 40 Minutos)")
st.write("Calculador adaptativo para partidos FIBA (4 cuartos de 10 minutos).")

# --------------------------------------------------------------------------
# Configuración del Momento del Partido y Modo de Faltas
# --------------------------------------------------------------------------
st.subheader("⚙️ Configuración del Partido")

col_conf1, col_conf2 = st.columns(2)

with col_conf1:
    etapa = st.radio(
        "⏱️ Momento actual del partido:",
        ["Medio Tiempo (20 min jugados)", "3er Cuarto (En curso)"]
    )
    
    if "3er Cuarto" in etapa:
        minuto_q3 = st.number_input(
            "Minuto transcurrido del 3er Cuarto (1 a 10):",
            min_value=1, max_value=10, value=5, step=1
        )
        minutos_jugados = 20 + minuto_q3
    else:
        minutos_jugados = 20

minutos_restantes = 40 - minutos_jugados
es_q3 = minutos_jugados > 20

with col_conf2:
    modo_faltas = st.radio(
        "📋 ¿Cómo ingresarás las faltas?",
        ["Faltas Totales Acumuladas", "Faltas Solo del Cuarto en Curso"]
    )

# --------------------------------------------------------------------------
# Entrada de Datos
# --------------------------------------------------------------------------
st.markdown("---")
st.subheader(f"📊 Estadísticas Acumuladas ({minutos_jugados} Minutos Jugados)")

col_local, col_vis = st.columns(2)

with col_local:
    st.markdown("### 🏠 Equipo Local")
    pts_tot_loc = st.number_input("Puntos Totales (Local)", min_value=0, value=48 if es_q3 else 39, step=1)
    pts_2_loc = st.number_input("Puntos de 2 (Local)", min_value=0, value=26 if es_q3 else 20, step=2)
    pts_3_loc = st.number_input("Puntos de 3 (Local)", min_value=0, value=18 if es_q3 else 15, step=3)
    
    if modo_faltas == "Faltas Solo del Cuarto en Curso":
        lbl_fal_loc = "Faltas en el Cuarto Actual (Local)"
        val_fal_loc = 3
    else:
        lbl_fal_loc = "Faltas Totales Acumuladas (Local)"
        val_fal_loc = 9 if es_q3 else 7

    faltas_loc_input = st.number_input(lbl_fal_loc, min_value=0, value=val_fal_loc, step=1)

with col_vis:
    st.markdown("### ✈️ Equipo Visitante")
    pts_tot_vis = st.number_input("Puntos Totales (Visitante)", min_value=0, value=44 if es_q3 else 35, step=1)
    pts_2_vis = st.number_input("Puntos de 2 (Visitante)", min_value=0, value=22 if es_q3 else 18, step=2)
    pts_3_vis = st.number_input("Puntos de 3 (Visitante)", min_value=0, value=15 if es_q3 else 12, step=3)
    
    if modo_faltas == "Faltas Solo del Cuarto en Curso":
        lbl_fal_vis = "Faltas en el Cuarto Actual (Visitante)"
        val_fal_vis = 3
    else:
        lbl_fal_vis = "Faltas Totales Acumuladas (Visitante)"
        val_fal_vis = 10 if es_q3 else 8

    faltas_vis_input = st.number_input(lbl_fal_vis, min_value=0, value=val_fal_vis, step=1)

# --------------------------------------------------------------------------
# Cálculo Automático
# --------------------------------------------------------------------------
if st.button("📐 Calcular Proyección Final", type="primary", use_container_width=True):
    # 1. Deducción automática de Tiros Libres
    pts_tl_loc = pts_tot_loc - (pts_2_loc + pts_3_loc)
    pts_tl_vis = pts_tot_vis - (pts_2_vis + pts_3_vis)

    if pts_tl_loc < 0 or pts_tl_vis < 0:
        st.error("❌ Los puntos de 2 y 3 no pueden sumar más que el total ingresado. Verifica los números.")
        st.stop()

    total_actual = pts_tot_loc + pts_tot_vis

    # 2. Estimación de Faltas Totales
    if modo_faltas == "Faltas Solo del Cuarto en Curso":
        cuartos_equiv = minutos_jugados / 10.0
        faltas_totales_est = round((faltas_loc_input + faltas_vis_input) * cuartos_equiv)
    else:
        faltas_totales_est = faltas_loc_input + faltas_vis_input

    # 3. Cálculo de Dependencia de Triples
    pct_3_loc = (pts_3_loc / pts_tot_loc) if pts_tot_loc > 0 else 0
    pct_3_vis = (pts_3_vis / pts_tot_vis) if pts_tot_vis > 0 else 0

    factor_3_loc = 0.88 if pct_3_loc >= 0.40 else 1.0
    factor_3_vis = 0.88 if pct_3_vis >= 0.40 else 1.0

    # 4. Ajuste por Faltas ponderado al tiempo restante
    ritmo_faltas_por_min = faltas_totales_est / minutos_jugados if minutos_jugados > 0 else 0
    if ritmo_faltas_por_min >= 0.8:
        bono_faltas = 5 * (minutos_restantes / 20.0)
    elif ritmo_faltas_por_min >= 0.6:
        bono_faltas = 3 * (minutos_restantes / 20.0)
    else:
        bono_faltas = 0

    # 5. Proyección exacta por ratio de tiempo restante
    ratio_tiempo = minutos_restantes / minutos_jugados

    proj_restante_loc = (pts_2_loc * ratio_tiempo) + ((pts_3_loc * ratio_tiempo) * factor_3_loc) + (pts_tl_loc * ratio_tiempo) + (bono_faltas / 2)
    proj_restante_vis = (pts_2_vis * ratio_tiempo) + ((pts_3_vis * ratio_tiempo) * factor_3_vis) + (pts_tl_vis * ratio_tiempo) + (bono_faltas / 2)

    final_loc = round(pts_tot_loc + proj_restante_loc)
    final_vis = round(pts_tot_vis + proj_restante_vis)
    total_proyectado = final_loc + final_vis

    # Margen dinámico (a menos tiempo restante, menor es la ventana de variación)
    margen_error = max(2, round(4 * (minutos_restantes / 20.0)))

    # --------------------------------------------------------------------------
    # Muestra de Resultados
    # --------------------------------------------------------------------------
    st.markdown("---")
    st.subheader("🎯 Marcador Proyectado")

    c1, c2, c3 = st.columns(3)
    c1.metric(f"Puntos ({minutos_jugados} min)", f"{total_actual} pts", f"{pts_tot_loc} - {pts_tot_vis}")
    c2.metric("Proyección Final", f"{total_proyectado} pts", f"{final_loc} - {final_vis}")
    c3.metric(f"Rango Estimado (±{margen_error})", f"{total_proyectado - margen_error} - {total_proyectado + margen_error} pts")

    st.success(f"**Resultado Final Estimado:** Local **{final_loc}** — **{final_vis}** Visitante")

    # Diagnóstico automático
    st.markdown("### 📋 Diagnóstico Calculado:")
    col_a, col_b = st.columns(2)
    col_a.info(f"🏠 **Local:** {pts_tl_loc} pts de TL | Dependencia 3PT: **{pct_3_loc:.0%}**")
    col_b.info(f"✈️ **Visitante:** {pts_tl_vis} pts de TL | Dependencia 3PT: **{pct_3_vis:.0%}**")

    if pct_3_loc >= 0.40:
        st.warning(f"⚠️ **Local:** Alta dependencia de triples ({pct_3_loc:.0%}). Ajuste aplicado a los {minutos_restantes} min restantes.")
    if pct_3_vis >= 0.40:
        st.warning(f"⚠️ **Visitante:** Alta dependencia de triples ({pct_3_vis:.0%}). Ajuste aplicado a los {minutos_restantes} min restantes.")

    if modo_faltas == "Faltas Solo del Cuarto en Curso":
        st.info(f"🏀 **Faltas Estimadas:** Se estiman {faltas_totales_est} faltas hasta el min {minutos_jugados}. Ajuste por tiros libres: +{bono_faltas:.1f} pts.")
    elif ritmo_faltas_por_min >= 0.6:
        st.info(f"🏀 **Impacto de Faltas ({faltas_totales_est} acumuladas):** Ritmo alto de faltas. Se agregan +{bono_faltas:.1f} pts proyectados desde la línea.")
