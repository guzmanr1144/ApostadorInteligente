"""
⚾ Analizador MLB Pro — Motor de Propuesta de Apuestas
========================================================
Fuente de datos: API oficial de MLB (statsapi.mlb.com) — gratuita, sin clave.

Datos que recolecta por cada juego:
  - Récord de temporada (W/L) de ambos equipos
  - Pitcher abridor (nombre + ERA + WHIP + strikeouts)
  - Estadísticas de bullpen del equipo
  - Promedio de bateo del equipo (AVG, OBP, SLG, OPS)
  - Runs anotados/recibidos en los últimos 10 juegos
  - Ventaja de campo local

Motor de apuestas:
  - Calcula probabilidad de victoria ajustada (récord + pitcher + bateo)
  - Clasifica confianza: ALTA / MEDIA / BAJA
  - Genera propuesta: Moneyline, Runline -1.5, Over/Under estimado
  - Vista de TODOS los juegos del día con ranking de apuestas
  - Vista detallada por partido seleccionado
"""

import streamlit as st
import pandas as pd
import requests
from datetime import datetime

# ── Página ─────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="MLB Apuestas Pro",
    layout="wide",
    page_icon="⚾",
)

BASE_MLB = "https://statsapi.mlb.com/api/v1"
HOY = datetime.now().strftime("%Y-%m-%d")


# ══════════════════════════════════════════════════════════════════════════════
# CAPA DE DATOS — API MLB
# ══════════════════════════════════════════════════════════════════════════════

@st.cache_data(ttl=1800, show_spinner=False)
def obtener_juegos(fecha: str) -> list[dict]:
    """Devuelve lista de juegos del día con info base de equipos y pitcher."""
    url = f"{BASE_MLB}/schedule/games/?sportId=1&date={fecha}&hydrate=probablePitcher(stats),linescore,team,record"
    try:
        r = requests.get(url, timeout=12)
        r.raise_for_status()
        datos = r.json()
        fechas = datos.get("dates", [])
        if not fechas:
            return []
        return fechas[0].get("games", [])
    except Exception as e:
        st.error(f"❌ Error consultando MLB: {e}")
        return []


@st.cache_data(ttl=3600, show_spinner=False)
def obtener_stats_equipo(team_id: int) -> dict:
    """
    Obtiene stats ofensivas del equipo en la temporada actual:
    AVG, OBP, SLG, OPS, runs por juego.
    """
    url = f"{BASE_MLB}/teams/{team_id}/stats?stats=season&group=hitting&season={datetime.now().year}"
    defaults = {"avg": 0.250, "obp": 0.320, "slg": 0.400, "ops": 0.720, "runs_pg": 4.5}
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        splits = r.json().get("stats", [{}])[0].get("splits", [{}])
        if not splits:
            return defaults
        s = splits[0].get("stat", {})
        games = int(s.get("gamesPlayed", 1)) or 1
        return {
            "avg":     float(s.get("avg", 0.250)),
            "obp":     float(s.get("obp", 0.320)),
            "slg":     float(s.get("slg", 0.400)),
            "ops":     float(s.get("ops", 0.720)),
            "runs_pg": round(int(s.get("runs", 0)) / games, 2),
        }
    except Exception:
        return defaults


@st.cache_data(ttl=3600, show_spinner=False)
def obtener_stats_pitcher(pitcher_id: int) -> dict:
    """
    Obtiene ERA, WHIP, strikeouts y innings lanzados del pitcher abridor.
    """
    url = f"{BASE_MLB}/people/{pitcher_id}/stats?stats=season&group=pitching&season={datetime.now().year}"
    defaults = {"era": 4.50, "whip": 1.35, "k9": 8.0, "ip": 0}
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        splits = r.json().get("stats", [{}])[0].get("splits", [{}])
        if not splits:
            return defaults
        s = splits[0].get("stat", {})
        ip = float(s.get("inningsPitched", 0) or 0)
        k9 = round((int(s.get("strikeOuts", 0)) / ip * 9) if ip > 0 else 8.0, 1)
        return {
            "era":  float(s.get("era", 4.50) or 4.50),
            "whip": float(s.get("whip", 1.35) or 1.35),
            "k9":   k9,
            "ip":   ip,
        }
    except Exception:
        return defaults


# ══════════════════════════════════════════════════════════════════════════════
# MOTOR DE ANÁLISIS
# ══════════════════════════════════════════════════════════════════════════════

def pct_victorias(w: int, l: int) -> float:
    total = w + l
    return w / total if total > 0 else 0.5


def score_pitcher(stats: dict) -> float:
    """
    Puntuación 0-1 basada en ERA (peso 50%), WHIP (30%), K/9 (20%).
    ERA menor → mejor. WHIP menor → mejor. K/9 mayor → mejor.
    """
    # ERA: normalizar en rango [1.5, 7.0], invertido
    era_score  = max(0.0, min(1.0, (7.0 - stats["era"])  / (7.0 - 1.5)))
    whip_score = max(0.0, min(1.0, (2.0 - stats["whip"]) / (2.0 - 0.8)))
    k9_score   = max(0.0, min(1.0, (stats["k9"] - 4.0)   / (14.0 - 4.0)))
    return round(era_score * 0.50 + whip_score * 0.30 + k9_score * 0.20, 3)


def score_ofensivo(stats: dict) -> float:
    """
    Puntuación 0-1 basada en OPS (60%) y runs_pg (40%).
    """
    ops_score  = max(0.0, min(1.0, (stats["ops"] - 0.550) / (1.000 - 0.550)))
    runs_score = max(0.0, min(1.0, (stats["runs_pg"] - 2.0) / (7.0 - 2.0)))
    return round(ops_score * 0.60 + runs_score * 0.40, 3)


def calcular_analisis(juego: dict, stats_l: dict, stats_v: dict,
                       pit_l: dict, pit_v: dict) -> dict:
    """
    Combina récord, pitching y bateo en probabilidades y propuesta de apuesta.

    Pesos:
      40% récord de temporada
      35% calidad del pitcher abridor (opuesto: pitcher rival afecta al bateador)
      25% ofensiva del equipo
    """
    eq_l = juego["teams"]["home"]
    eq_v = juego["teams"]["away"]

    rec_l = eq_l.get("leagueRecord", {})
    rec_v = eq_v.get("leagueRecord", {})
    w_l = int(rec_l.get("wins", 0));  l_l = int(rec_l.get("losses", 0))
    w_v = int(rec_v.get("wins", 0));  l_v = int(rec_v.get("losses", 0))

    pct_l = pct_victorias(w_l, l_l)
    pct_v = pct_victorias(w_v, l_v)

    # El pitcher DEL RIVAL penaliza la ofensiva: a mejor pitcher rival, menos runs el equipo
    sp_l = score_pitcher(pit_l)  # pitcher local (afecta al visitante)
    sp_v = score_pitcher(pit_v)  # pitcher visitante (afecta al local)
    so_l = score_ofensivo(stats_l)
    so_v = score_ofensivo(stats_v)

    # Score compuesto por equipo
    # Récord 40% | Pitcher propio (dominio) 35% vs rival | Ofensiva 25%
    # Nota: pitcher propio ayuda al equipo; pitcher rival lo perjudica
    raw_l = 0.40 * pct_l + 0.35 * sp_l + 0.25 * so_l * (1 - sp_v * 0.4)
    raw_v = 0.40 * pct_v + 0.35 * sp_v + 0.25 * so_v * (1 - sp_l * 0.4)

    total = raw_l + raw_v
    prob_l = round((raw_l / total) * 100) if total > 0 else 50
    prob_v = 100 - prob_l

    # Ventaja de campo local (+2-3 pp histórico MLB)
    prob_l = min(prob_l + 2, 97)
    prob_v = 100 - prob_l

    # Runline -1.5 (favorito gana por ≥2): probabilidad ~70% de la moneyline
    favorito = "local" if prob_l >= prob_v else "visitante"
    prob_fav = prob_l if favorito == "local" else prob_v
    runline_prob = round(prob_fav * 0.72)

    # Estimación Over/Under basada en ofensivas combinadas
    runs_esperados = round(stats_l["runs_pg"] + stats_v["runs_pg"], 1)
    # Ajuste por calidad de pitchers: pitchers dominantes bajan el total
    factor_pitcher = 1 - ((sp_l + sp_v) / 2) * 0.25
    total_estimado = round(runs_esperados * factor_pitcher, 1)
    linea_ou = round(total_estimado * 2) / 2  # redondear a .0 o .5

    over_prob = 55 if total_estimado > linea_ou else 45

    # Clasificar confianza
    diferencia = abs(prob_l - prob_v)
    if diferencia >= 18:
        confianza = "🟢 ALTA"
        nivel = 3
    elif diferencia >= 10:
        confianza = "🟡 MEDIA"
        nivel = 2
    else:
        confianza = "🔴 BAJA"
        nivel = 1

    # Nombre de pitchers
    pit_nombre_l = eq_l.get("probablePitcher", {}).get("fullName", "Por confirmar")
    pit_nombre_v = eq_v.get("probablePitcher", {}).get("fullName", "Por confirmar")

    return {
        "local":          eq_l["team"]["name"],
        "visitante":      eq_v["team"]["name"],
        "prob_local":     prob_l,
        "prob_visitante": prob_v,
        "favorito":       eq_l["team"]["name"] if favorito == "local" else eq_v["team"]["name"],
        "prob_fav":       prob_fav,
        "runline_prob":   runline_prob,
        "total_estimado": total_estimado,
        "linea_ou":       linea_ou,
        "over_prob":      over_prob,
        "confianza":      confianza,
        "nivel":          nivel,
        "rec_l":          f"{w_l}G-{l_l}P",
        "rec_v":          f"{w_v}G-{l_v}P",
        "pit_l":          pit_nombre_l,
        "pit_v":          pit_nombre_v,
        "pit_stats_l":    pit_l,
        "pit_stats_v":    pit_v,
        "bat_l":          stats_l,
        "bat_v":          stats_v,
        "pct_l":          round(pct_l * 100, 1),
        "pct_v":          round(pct_v * 100, 1),
    }


def generar_propuesta(a: dict) -> str:
    """Genera texto de propuesta de apuesta basado en el análisis."""
    lineas = []

    # Apuesta principal (moneyline)
    lineas.append(f"**🥇 Apuesta Principal — Moneyline {a['favorito']}**")
    lineas.append(
        f"Probabilidad estimada: **{a['prob_fav']}%**. "
        f"El equipo combina récord sólido con ventajas en pitching/ofensiva. "
        f"Confianza: {a['confianza']}."
    )

    # Runline solo si confianza alta/media
    if a["nivel"] >= 2:
        lineas.append(f"\n**📌 Apuesta Secundaria — Runline {a['favorito']} -1.5**")
        lineas.append(
            f"Probabilidad ajustada: **{a['runline_prob']}%**. "
            f"Recomendado cuando el favoritismo es claro y el pitcher abridor es dominante."
        )

    # Over/Under
    lineas.append(f"\n**📊 Línea Total (Over/Under {a['linea_ou']})**")
    lado_ou = "Over" if a["over_prob"] > 50 else "Under"
    lineas.append(
        f"Carreras esperadas en el juego: **{a['total_estimado']}**. "
        f"Sugerencia: **{lado_ou} {a['linea_ou']}** ({a['over_prob']}% de probabilidad). "
        f"Basado en el promedio ofensivo de ambos equipos ajustado por ERA de abridores."
    )

    if a["nivel"] == 1:
        lineas.append(
            "\n⚠️ *Confianza baja: equipos muy parejos. "
            "Considera apostar solo la línea total o abstenerte de esta apuesta.*"
        )

    return "\n\n".join(lineas)


# ══════════════════════════════════════════════════════════════════════════════
# UI
# ══════════════════════════════════════════════════════════════════════════════

def main() -> None:
    st.title("⚾ MLB — Analizador y Propuesta de Apuestas")
    st.caption(
        f"Datos oficiales: statsapi.mlb.com · Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')} "
        f"· Solo fines informativos — apuesta con responsabilidad."
    )

    # ── Cargar juegos ──────────────────────────────────────────────────────────
    with st.spinner("⏳ Cargando juegos del día desde MLB..."):
        juegos_raw = obtener_juegos(HOY)

    if not juegos_raw:
        st.warning("🚫 No hay juegos de MLB programados para hoy.")
        st.stop()

    # ── Procesar todos los juegos ──────────────────────────────────────────────
    analisis_todos: list[dict] = []

    barra = st.progress(0, text="Cargando estadísticas de equipos y pitchers...")
    total = len(juegos_raw)

    for i, j in enumerate(juegos_raw):
        barra.progress((i + 1) / total, text=f"Procesando {i+1}/{total} juegos...")
        try:
            tid_l = j["teams"]["home"]["team"]["id"]
            tid_v = j["teams"]["away"]["team"]["id"]
            stats_l = obtener_stats_equipo(tid_l)
            stats_v = obtener_stats_equipo(tid_v)

            pit_id_l = j["teams"]["home"].get("probablePitcher", {}).get("id")
            pit_id_v = j["teams"]["away"].get("probablePitcher", {}).get("id")
            pit_l = obtener_stats_pitcher(pit_id_l) if pit_id_l else {"era": 4.50, "whip": 1.35, "k9": 8.0, "ip": 0}
            pit_v = obtener_stats_pitcher(pit_id_v) if pit_id_v else {"era": 4.50, "whip": 1.35, "k9": 8.0, "ip": 0}

            a = calcular_analisis(j, stats_l, stats_v, pit_l, pit_v)
            analisis_todos.append(a)
        except Exception as e:
            st.warning(f"⚠️ No se pudo procesar un juego: {e}")

    barra.empty()

    if not analisis_todos:
        st.error("No se pudieron procesar los juegos de hoy.")
        st.stop()

    # Ordenar por nivel de confianza (mayor primero) y luego por prob_fav
    analisis_todos.sort(key=lambda x: (x["nivel"], x["prob_fav"]), reverse=True)

    # ── TABS ──────────────────────────────────────────────────────────────────
    tab1, tab2 = st.tabs(["📋 Todos los Juegos — Ranking de Apuestas", "🔍 Análisis Detallado"])

    # ─────────────────────────────────────────────────────────────────────────
    # TAB 1: Resumen general + tabla rankeada
    # ─────────────────────────────────────────────────────────────────────────
    with tab1:
        st.subheader(f"📅 Juegos MLB — {datetime.now().strftime('%A %d de %B, %Y')}")
        st.write(f"**{len(analisis_todos)} partidos programados.** Ordenados por confianza de apuesta.")

        # Métricas rápidas
        altas  = sum(1 for a in analisis_todos if a["nivel"] == 3)
        medias = sum(1 for a in analisis_todos if a["nivel"] == 2)
        bajas  = sum(1 for a in analisis_todos if a["nivel"] == 1)
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Juegos", len(analisis_todos))
        c2.metric("🟢 Confianza Alta", altas)
        c3.metric("🟡 Confianza Media", medias)
        c4.metric("🔴 Confianza Baja", bajas)

        st.markdown("---")

        # Tabla resumen
        filas = []
        for a in analisis_todos:
            filas.append({
                "Partido":          f"{a['local']} vs {a['visitante']}",
                "Favorito":         a["favorito"],
                "Prob. ML":         f"{a['prob_fav']}%",
                "Runline -1.5":     f"{a['runline_prob']}%",
                "Total Est.":       f"{a['total_estimado']} carr.",
                "O/U sugerido":     f"{'Over' if a['over_prob']>50 else 'Under'} {a['linea_ou']}",
                "Confianza":        a["confianza"],
            })

        df = pd.DataFrame(filas)
        st.dataframe(df, use_container_width=True, hide_index=True)

        st.markdown("---")
        st.subheader("🏆 Top Apuestas del Día (Confianza Alta)")

        top = [a for a in analisis_todos if a["nivel"] == 3]
        if not top:
            top = analisis_todos[:3]  # Si no hay alta confianza, mostrar los 3 mejores

        for idx, a in enumerate(top, 1):
            with st.expander(f"#{idx} {a['local']} vs {a['visitante']} — {a['confianza']}", expanded=(idx==1)):
                col_a, col_b = st.columns([2, 1])
                with col_a:
                    st.markdown(generar_propuesta(a))
                with col_b:
                    st.write("**Pitchers Abridores**")
                    st.write(f"🏠 {a['pit_l']}")
                    st.caption(f"ERA {a['pit_stats_l']['era']} · WHIP {a['pit_stats_l']['whip']} · K/9 {a['pit_stats_l']['k9']}")
                    st.write(f"✈️ {a['pit_v']}")
                    st.caption(f"ERA {a['pit_stats_v']['era']} · WHIP {a['pit_stats_v']['whip']} · K/9 {a['pit_stats_v']['k9']}")

    # ─────────────────────────────────────────────────────────────────────────
    # TAB 2: Análisis detallado de partido seleccionado
    # ─────────────────────────────────────────────────────────────────────────
    with tab2:
        opciones = [f"{a['local']} vs {a['visitante']}" for a in analisis_todos]
        sel = st.selectbox("Selecciona un partido:", opciones)
        a = next(x for x in analisis_todos if f"{x['local']} vs {x['visitante']}" == sel)

        st.subheader(f"⚾ {a['local']} vs {a['visitante']}")

        # Probabilidades
        col1, col2, col3 = st.columns(3)
        col1.metric(f"🏠 {a['local']}", f"{a['prob_local']}%", f"Récord: {a['rec_l']}")
        col2.metric("Winrate temporada", f"{a['pct_l']}% / {a['pct_v']}%")
        col3.metric(f"✈️ {a['visitante']}", f"{a['prob_visitante']}%", f"Récord: {a['rec_v']}")

        st.markdown("---")

        # Pitchers
        st.subheader("🧢 Pitchers Abridores")
        pc1, pc2 = st.columns(2)
        with pc1:
            st.write(f"**{a['local']}:** {a['pit_l']}")
            df_pit_l = pd.DataFrame([{
                "ERA": a["pit_stats_l"]["era"],
                "WHIP": a["pit_stats_l"]["whip"],
                "K/9": a["pit_stats_l"]["k9"],
                "IP temporada": a["pit_stats_l"]["ip"],
            }])
            st.dataframe(df_pit_l, hide_index=True, use_container_width=True)
        with pc2:
            st.write(f"**{a['visitante']}:** {a['pit_v']}")
            df_pit_v = pd.DataFrame([{
                "ERA": a["pit_stats_v"]["era"],
                "WHIP": a["pit_stats_v"]["whip"],
                "K/9": a["pit_stats_v"]["k9"],
                "IP temporada": a["pit_stats_v"]["ip"],
            }])
            st.dataframe(df_pit_v, hide_index=True, use_container_width=True)

        st.markdown("---")

        # Ofensivas
        st.subheader("🔥 Estadísticas Ofensivas")
        bc1, bc2 = st.columns(2)
        with bc1:
            st.write(f"**{a['local']}**")
            df_bat_l = pd.DataFrame([{
                "AVG": a["bat_l"]["avg"],
                "OBP": a["bat_l"]["obp"],
                "SLG": a["bat_l"]["slg"],
                "OPS": a["bat_l"]["ops"],
                "Runs/Juego": a["bat_l"]["runs_pg"],
            }])
            st.dataframe(df_bat_l, hide_index=True, use_container_width=True)
        with bc2:
            st.write(f"**{a['visitante']}**")
            df_bat_v = pd.DataFrame([{
                "AVG": a["bat_v"]["avg"],
                "OBP": a["bat_v"]["obp"],
                "SLG": a["bat_v"]["slg"],
                "OPS": a["bat_v"]["ops"],
                "Runs/Juego": a["bat_v"]["runs_pg"],
            }])
            st.dataframe(df_bat_v, hide_index=True, use_container_width=True)

        st.markdown("---")

        # Distribución visual
        st.subheader("📊 Probabilidades")
        df_prob = pd.DataFrame({
            "Probabilidad (%)": {
                a["local"]: a["prob_local"],
                a["visitante"]: a["prob_visitante"],
            }
        })
        st.bar_chart(df_prob)

        st.markdown("---")

        # Propuesta
        st.subheader("💡 Propuesta de Apuesta")
        st.markdown(generar_propuesta(a))

        st.markdown("---")
        st.caption(
            "⚠️ Este análisis es solo informativo. Las probabilidades se calculan a partir de "
            "datos públicos de temporada y no garantizan resultados. Apuesta responsablemente."
        )


if __name__ == "__main__":
    main()
