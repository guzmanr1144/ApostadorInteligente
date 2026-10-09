"""
Proyector de Baloncesto Avanzado (2PT, 3PT y Faltas)
---------------------------------------------------
Calcula la proyección del partido basándose en la estabilidad de los 2PT,
la regresión de los 3PT y el impacto de las faltas para los tiros libres.
"""

import streamlit as st

st.set_page_config(page_title="Proyector de Baloncesto", page_icon="🏀", layout="centered")

st.title("🏀 Proyector de Puntos con 2PT, 3PT y Faltas")
st.write("Ingresa las estadísticas detalladas de la primera mitad para ajustar la proyección del partido.")

# --------------------------------------------------------------------------
# Entrada de Datos
# --------------------------------------------------------------------------
col_local, col_vis = st.columns(2)

with col_local:
    st.markdown("### 🏠 Equipo Local")
    pts_2_loc = st.number_input("Puntos de 2 (Local)", min_value=0, value=28, step=2)
    pts_3_loc = st.number_input("Puntos de 3 (Local)", min_value=0, value=18, step=3)
    pts_tl_loc = st.number_input("Puntos de Tiro Libre (Local)", min_value=0, value=6, step=1)
    faltas_loc = st.number_input("Faltas Cometidas (Local)", min_value=0, value=9, step=1)

with col_vis:
    st.markdown("### ✈️ Equipo Visitante")
    pts_2_vis = st.number_input("Puntos de 2 (Visitante)", min_value=0, value=24, step=2)
    pts_3_vis = st.number_input("Puntos de 3 (Visitante)", min_value=0, value=15, step=3)
    pts_tl_vis = st.number_input("Puntos de Tiro Libre (Visitante)", min_value=0, value=5, step=1)
    faltas_vis = st.number_input("Faltas Cometidas (Visitante)", min_value=0, value=10, step=1)

# --------------------------------------------------------------------------
# Lógica del Modelo Matemático
# --------------------------------------------------------------------------
if st.button("📐 Calcular Proyección de la 2ª Mitad", type="primary", use_container_width=True):
    total_loc_1h = pts_2_loc + pts_3_loc + pts_tl_loc
    total_vis_1h = pts_2_vis + pts_3_vis + pts_tl_vis
    total_1h = total_loc_1h + total_vis_1h

    # 1. Ajuste por dependencia de Triples (Regresión)
    pct_3_loc = (pts_3_loc / total_loc_1h) if total_loc_1h > 0 else 0
    pct_3_vis = (pts_3_vis / total_vis_1h) if total_vis_1h > 0 else 0

    # Si anotan más del 40% de sus puntos en triples, se proyecta un ajuste a la baja en la 2da mitad
    factor_3_loc = 0.88 if pct_3_loc > 0.42 else 1.0
    factor_3_vis = 0.88 if pct_3_vis > 0.42 else 1.0

    # 2. Ajuste por Faltas (Puntos extra en la línea de TL)
    faltas_totales = faltas_loc + faltas_vis
    bono_faltas = 4 if faltas_totales >= 20 else (2 if faltas_totales >= 16 else 0)

    # 3. Cálculo Proyectado 2da Mitad
    proj_2h_loc = pts_2_loc + (pts_3_loc * factor_3_loc) + pts_tl_loc + (bono_faltas / 2)
    proj_2h_vis = pts_2_vis + (pts_3_vis * factor_3_vis) + pts_tl_vis + (bono_faltas / 2)

    final_loc = round(total_loc_1h + proj_2h_loc)
    final_vis = round(total_vis_1h + proj_2h_vis)
    total_proyectado = final_loc + final_vis

    # --------------------------------------------------------------------------
    # Resultados
    # --------------------------------------------------------------------------
    st.markdown("---")
    st.subheader("🎯 Marcador Proyectado")

    c1, c2, c3 = st.columns(3)
    c1.metric("Total 1ª Mitad", f"{total_1h} pts", f"{total_loc_1h} - {total_vis_1h}")
    c2.metric("Proyección Final", f"{total_proyectado} pts", f"{final_loc} - {final_vis}")
    c3.metric("Rango Estimado", f"{total_proyectado - 6} - {total_proyectado + 6} pts")

    st.success(f"**Resultado Final Proyectado:** Local **{final_loc}** — **{final_vis}** Visitante")

    # Explicación de los ajustes aplicados
    st.markdown("### 💡 Diagnóstico de la Proyección:")
    
    if pct_3_loc > 0.42:
        st.warning(f"⚠️ **Local:** El {pct_3_loc:.0%} de sus puntos vinieron de triples. Se proyecta una pequeña baja de efectividad en la 2ª mitad.")
    if pct_3_vis > 0.42:
        st.warning(f"⚠️ **Visitante:** El {pct_3_vis:.0%} de sus puntos vinieron de triples. Se proyecta una pequeña baja de efectividad en la 2ª mitad.")
    
    if faltas_totales >= 18:
        st.info(f"🏀 **Ritmo por Faltas:** Se registraron {faltas_totales} faltas en la 1ª mitad. Un juego físico aumentará los tiros libres en la 2ª mitad (+{bono_faltas} pts proyectados).")
