"""
⚾ MLB Analizador Pro — con Tracker de Apuestas en Bolívares
=============================================================
Módulos:
  1. Motor MLB: récord + pitcher (ERA/WHIP/K9) + ofensiva (OPS/runs_pg)
  2. Propuesta de apuesta con Kelly Criterion en Bs y USD
  3. Tracker: registro, historial CSV, estadísticas, sugerencia de bankroll
"""

import streamlit as st
import pandas as pd
import requests
import json
import os
from datetime import datetime
from pathlib import Path

# ── Página ────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="MLB Apuestas Pro 🇻🇪", layout="wide", page_icon="⚾")

BASE_MLB  = "https://statsapi.mlb.com/api/v1"
HOY       = datetime.now().strftime("%Y-%m-%d")
CSV_PATH  = Path("apuestas_historial.csv")
CFG_PATH  = Path("config_usuario.json")

COLUMNAS_CSV = [
    "fecha", "partido", "tipo_apuesta", "seleccion",
    "cuota_americana", "monto_bs", "tasa_usd", "monto_usd",
    "resultado",          # "Ganada" | "Perdida" | "Pendiente"
    "ganancia_bs",        # neto (positivo o negativo)
    "ganancia_usd",
    "confianza_sistema",  # nivel que sugirió el sistema
    "notas",
]

# ══════════════════════════════════════════════════════════════════════════════
# PERSISTENCIA — CSV local
# ══════════════════════════════════════════════════════════════════════════════

def cargar_historial() -> pd.DataFrame:
    if CSV_PATH.exists():
        try:
            df = pd.read_csv(CSV_PATH, parse_dates=["fecha"])
            # Garantizar que existan todas las columnas aunque el CSV sea antiguo
            for col in COLUMNAS_CSV:
                if col not in df.columns:
                    df[col] = ""
            return df
        except Exception:
            pass
    return pd.DataFrame(columns=COLUMNAS_CSV)


def guardar_historial(df: pd.DataFrame) -> None:
    df.to_csv(CSV_PATH, index=False)


def cargar_config() -> dict:
    defaults = {"bankroll_bs": 100.0, "tasa_usd": 36.0}
    if CFG_PATH.exists():
        try:
            with open(CFG_PATH) as f:
                data = json.load(f)
                defaults.update(data)
        except Exception:
            pass
    return defaults


def guardar_config(cfg: dict) -> None:
    with open(CFG_PATH, "w") as f:
        json.dump(cfg, f)


# ══════════════════════════════════════════════════════════════════════════════
# CONVERSIÓN DE CUOTAS
# ══════════════════════════════════════════════════════════════════════════════

def americana_a_decimal(cuota_am: float) -> float:
    """Convierte cuota americana a decimal."""
    if cuota_am >= 100:
        return round(cuota_am / 100 + 1, 4)
    else:
        return round(100 / abs(cuota_am) + 1, 4)


def americana_a_prob(cuota_am: float) -> float:
    """Probabilidad implícita de la cuota americana (0-1)."""
    dec = americana_a_decimal(cuota_am)
    return round(1 / dec, 4) if dec > 0 else 0.5


def calcular_ganancia_bs(monto_bs: float, cuota_am: float) -> float:
    """Ganancia neta en Bs si gana (sin incluir el monto apostado)."""
    dec = americana_a_decimal(cuota_am)
    return round(monto_bs * (dec - 1), 2)


# ══════════════════════════════════════════════════════════════════════════════
# KELLY CRITERION — sugerencia de monto
# ══════════════════════════════════════════════════════════════════════════════

def kelly_monto(bankroll_bs: float, prob_modelo: float, cuota_am: float,
                fraccion: float = 0.25) -> float:
    """
    Kelly fraccionado (25% por defecto para ser conservador).
    prob_modelo: probabilidad 0-1 estimada por nuestro modelo.
    Retorna monto sugerido en Bs.
    """
    dec = americana_a_decimal(cuota_am)
    b = dec - 1  # ganancia neta por unidad apostada
    q = 1 - prob_modelo
    kelly = (b * prob_modelo - q) / b if b > 0 else 0
    kelly = max(0.0, kelly)
    return round(bankroll_bs * kelly * fraccion, 2)


# ══════════════════════════════════════════════════════════════════════════════
# CAPA DE DATOS MLB
# ══════════════════════════════════════════════════════════════════════════════

@st.cache_data(ttl=1800, show_spinner=False)
def obtener_juegos(fecha: str) -> list[dict]:
    url = f"{BASE_MLB}/schedule/games/?sportId=1&date={fecha}&hydrate=probablePitcher(stats),linescore,team,record"
    try:
        r = requests.get(url, timeout=12)
        r.raise_for_status()
        fechas = r.json().get("dates", [])
        return fechas[0].get("games", []) if fechas else []
    except Exception as e:
        st.error(f"❌ Error consultando MLB: {e}")
        return []


@st.cache_data(ttl=3600, show_spinner=False)
def obtener_stats_equipo(team_id: int) -> dict:
    url = f"{BASE_MLB}/teams/{team_id}/stats?stats=season&group=hitting&season={datetime.now().year}"
    d = {"avg": 0.250, "obp": 0.320, "slg": 0.400, "ops": 0.720, "runs_pg": 4.5}
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        splits = r.json().get("stats", [{}])[0].get("splits", [])
        if not splits:
            return d
        s = splits[0].get("stat", {})
        gp = int(s.get("gamesPlayed", 1)) or 1
        return {
            "avg":     float(s.get("avg", 0.250)),
            "obp":     float(s.get("obp", 0.320)),
            "slg":     float(s.get("slg", 0.400)),
            "ops":     float(s.get("ops", 0.720)),
            "runs_pg": round(int(s.get("runs", 0)) / gp, 2),
        }
    except Exception:
        return d


@st.cache_data(ttl=3600, show_spinner=False)
def obtener_stats_pitcher(pitcher_id: int) -> dict:
    url = f"{BASE_MLB}/people/{pitcher_id}/stats?stats=season&group=pitching&season={datetime.now().year}"
    d = {"era": 4.50, "whip": 1.35, "k9": 8.0, "ip": 0}
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        splits = r.json().get("stats", [{}])[0].get("splits", [])
        if not splits:
            return d
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
        return d


# ══════════════════════════════════════════════════════════════════════════════
# MOTOR DE ANÁLISIS
# ══════════════════════════════════════════════════════════════════════════════

def pct_vic(w: int, l: int) -> float:
    t = w + l
    return w / t if t > 0 else 0.5


def score_pit(s: dict) -> float:
    era_sc  = max(0.0, min(1.0, (7.0 - s["era"])  / 5.5))
    whip_sc = max(0.0, min(1.0, (2.0 - s["whip"]) / 1.2))
    k9_sc   = max(0.0, min(1.0, (s["k9"] - 4.0)   / 10.0))
    return round(era_sc * 0.50 + whip_sc * 0.30 + k9_sc * 0.20, 3)


def score_bat(s: dict) -> float:
    ops_sc  = max(0.0, min(1.0, (s["ops"] - 0.550)    / 0.450))
    runs_sc = max(0.0, min(1.0, (s["runs_pg"] - 2.0)  / 5.0))
    return round(ops_sc * 0.60 + runs_sc * 0.40, 3)


def calcular_analisis(juego: dict, sl: dict, sv: dict, pl: dict, pv: dict) -> dict:
    el = juego["teams"]["home"]
    ev = juego["teams"]["away"]
    rl = el.get("leagueRecord", {})
    rv = ev.get("leagueRecord", {})
    wl, ll = int(rl.get("wins", 0)), int(rl.get("losses", 0))
    wv, lv = int(rv.get("wins", 0)), int(rv.get("losses", 0))

    pctl, pctv = pct_vic(wl, ll), pct_vic(wv, lv)
    spl, spv   = score_pit(pl), score_pit(pv)
    sol, sov   = score_bat(sl), score_bat(sv)

    raw_l = 0.40 * pctl + 0.35 * spl + 0.25 * sol * (1 - spv * 0.4)
    raw_v = 0.40 * pctv + 0.35 * spv + 0.25 * sov * (1 - spl * 0.4)
    tot   = raw_l + raw_v
    pl_p  = min(round((raw_l / tot) * 100) + 2, 97) if tot > 0 else 50
    pv_p  = 100 - pl_p

    fav      = "local" if pl_p >= pv_p else "visitante"
    prob_fav = pl_p if fav == "local" else pv_p
    rl_prob  = round(prob_fav * 0.72)

    runs_esp = sl["runs_pg"] + sv["runs_pg"]
    factor   = 1 - ((spl + spv) / 2) * 0.25
    total_est = round(runs_esp * factor, 1)
    linea_ou  = round(total_est * 2) / 2
    over_prob = 55 if total_est > linea_ou else 45

    dif   = abs(pl_p - pv_p)
    nivel = 3 if dif >= 18 else (2 if dif >= 10 else 1)
    conf  = {3: "🟢 ALTA", 2: "🟡 MEDIA", 1: "🔴 BAJA"}[nivel]

    return {
        "local":          el["team"]["name"],
        "visitante":      ev["team"]["name"],
        "prob_local":     pl_p,
        "prob_visitante": pv_p,
        "favorito":       el["team"]["name"] if fav == "local" else ev["team"]["name"],
        "prob_fav":       prob_fav,
        "prob_fav_dec":   round(prob_fav / 100, 4),
        "runline_prob":   rl_prob,
        "total_estimado": total_est,
        "linea_ou":       linea_ou,
        "over_prob":      over_prob,
        "confianza":      conf,
        "nivel":          nivel,
        "rec_l":          f"{wl}G-{ll}P",
        "rec_v":          f"{wv}G-{lv}P",
        "pit_l":          el.get("probablePitcher", {}).get("fullName", "Por confirmar"),
        "pit_v":          ev.get("probablePitcher", {}).get("fullName", "Por confirmar"),
        "pit_stats_l":    pl,
        "pit_stats_v":    pv,
        "bat_l":          sl,
        "bat_v":          sv,
        "pct_l":          round(pctl * 100, 1),
        "pct_v":          round(pctv * 100, 1),
    }


# ══════════════════════════════════════════════════════════════════════════════
# ESTADÍSTICAS DEL TRACKER
# ══════════════════════════════════════════════════════════════════════════════

def calcular_stats_tracker(df: pd.DataFrame, bankroll_inicial: float) -> dict:
    if df.empty:
        return {}
    cerradas = df[df["resultado"].isin(["Ganada", "Perdida"])]
    if cerradas.empty:
        return {}

    ganadas   = cerradas[cerradas["resultado"] == "Ganada"]
    perdidas  = cerradas[cerradas["resultado"] == "Perdida"]
    total_ap  = len(cerradas)
    win_rate  = round(len(ganadas) / total_ap * 100, 1) if total_ap > 0 else 0

    gan_neto_bs  = cerradas["ganancia_bs"].astype(float).sum()
    gan_neto_usd = cerradas["ganancia_usd"].astype(float).sum()
    invertido_bs = cerradas["monto_bs"].astype(float).sum()
    roi          = round(gan_neto_bs / invertido_bs * 100, 2) if invertido_bs > 0 else 0

    bankroll_actual = bankroll_inicial + gan_neto_bs

    # Racha actual
    resultados = cerradas.sort_values("fecha")["resultado"].tolist()
    racha, tipo_racha = 0, ""
    if resultados:
        ultimo = resultados[-1]
        for r in reversed(resultados):
            if r == ultimo:
                racha += 1
            else:
                break
        tipo_racha = "✅ ganando" if ultimo == "Ganada" else "❌ perdiendo"

    # Por tipo de apuesta
    por_tipo = {}
    for tipo in cerradas["tipo_apuesta"].unique():
        sub = cerradas[cerradas["tipo_apuesta"] == tipo]
        g   = sub[sub["resultado"] == "Ganada"]
        por_tipo[tipo] = {
            "jugadas": len(sub),
            "ganadas": len(g),
            "win_rate": round(len(g) / len(sub) * 100, 1),
            "neto_bs":  round(sub["ganancia_bs"].astype(float).sum(), 2),
        }

    return {
        "total_ap":        total_ap,
        "ganadas":         len(ganadas),
        "perdidas":        len(perdidas),
        "pendientes":      len(df[df["resultado"] == "Pendiente"]),
        "win_rate":        win_rate,
        "gan_neto_bs":     round(gan_neto_bs, 2),
        "gan_neto_usd":    round(gan_neto_usd, 2),
        "roi":             roi,
        "bankroll_actual": round(bankroll_actual, 2),
        "racha":           racha,
        "tipo_racha":      tipo_racha,
        "por_tipo":        por_tipo,
        "invertido_bs":    round(invertido_bs, 2),
    }


# ══════════════════════════════════════════════════════════════════════════════
# UI PRINCIPAL
# ══════════════════════════════════════════════════════════════════════════════

def main() -> None:
    # ── Config usuario (sidebar) ───────────────────────────────────────────────
    cfg = cargar_config()

    with st.sidebar:
        st.header("⚙️ Configuración")
        tasa = st.number_input(
            "💵 Tasa USD → Bs (hoy)",
            min_value=1.0, value=float(cfg.get("tasa_usd", 36.0)),
            step=0.5, format="%.2f",
            help="Ingresa la tasa del día para todas las conversiones"
        )
        bankroll_bs = st.number_input(
            "🏦 Bankroll actual (Bs)",
            min_value=1.0, value=float(cfg.get("bankroll_bs", 100.0)),
            step=10.0, format="%.2f",
            help="Tu capital total disponible para apuestas"
        )
        if st.button("💾 Guardar configuración"):
            guardar_config({"tasa_usd": tasa, "bankroll_bs": bankroll_bs})
            st.success("Guardado ✓")

        st.markdown("---")
        st.caption(
            f"**{datetime.now().strftime('%d/%m/%Y %H:%M')}**\n\n"
            f"Bs {bankroll_bs:,.2f} = USD {bankroll_bs/tasa:,.2f}"
        )

    st.title("⚾ MLB Apuestas Pro 🇻🇪")
    st.caption("Datos: statsapi.mlb.com · Solo informativo · Apuesta responsablemente.")

    # ── Tabs ───────────────────────────────────────────────────────────────────
    tab_juegos, tab_detalle, tab_registro, tab_tracker = st.tabs([
        "📋 Juegos del Día",
        "🔍 Análisis Detallado",
        "➕ Registrar Apuesta",
        "📊 Mi Tracker",
    ])

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 1 — JUEGOS DEL DÍA
    # ══════════════════════════════════════════════════════════════════════════
    with tab_juegos:
        with st.spinner("⏳ Cargando juegos del día..."):
            juegos_raw = obtener_juegos(HOY)

        if not juegos_raw:
            st.warning("🚫 No hay juegos de MLB para hoy.")
            st.stop()

        analisis_todos: list[dict] = []
        barra = st.progress(0, text="Procesando estadísticas...")
        for i, j in enumerate(juegos_raw):
            barra.progress((i + 1) / len(juegos_raw),
                           text=f"Procesando {i+1}/{len(juegos_raw)} juegos...")
            try:
                tid_l = j["teams"]["home"]["team"]["id"]
                tid_v = j["teams"]["away"]["team"]["id"]
                sl = obtener_stats_equipo(tid_l)
                sv = obtener_stats_equipo(tid_v)
                pid_l = j["teams"]["home"].get("probablePitcher", {}).get("id")
                pid_v = j["teams"]["away"].get("probablePitcher", {}).get("id")
                pl = obtener_stats_pitcher(pid_l) if pid_l else {"era":4.50,"whip":1.35,"k9":8.0,"ip":0}
                pv = obtener_stats_pitcher(pid_v) if pid_v else {"era":4.50,"whip":1.35,"k9":8.0,"ip":0}
                analisis_todos.append(calcular_analisis(j, sl, sv, pl, pv))
            except Exception as e:
                st.warning(f"⚠️ No se pudo procesar un juego: {e}")
        barra.empty()

        # Guardar en session_state para otros tabs
        st.session_state["analisis_todos"] = analisis_todos
        st.session_state["tasa"]           = tasa
        st.session_state["bankroll_bs"]    = bankroll_bs

        analisis_todos.sort(key=lambda x: (x["nivel"], x["prob_fav"]), reverse=True)

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Juegos", len(analisis_todos))
        c2.metric("🟢 Confianza Alta",  sum(1 for a in analisis_todos if a["nivel"]==3))
        c3.metric("🟡 Confianza Media", sum(1 for a in analisis_todos if a["nivel"]==2))
        c4.metric("🔴 Confianza Baja",  sum(1 for a in analisis_todos if a["nivel"]==1))

        st.markdown("---")

        # Tabla con sugerencia de monto Kelly por partido
        # Cuota americana de referencia: favorito al -130 (aprox para confianza alta)
        CUOTA_REF = {3: -150, 2: -120, 1: -110}
        filas = []
        for a in analisis_todos:
            cuota_ref = CUOTA_REF[a["nivel"]]
            kelly_bs  = kelly_monto(bankroll_bs, a["prob_fav_dec"], cuota_ref)
            kelly_usd = round(kelly_bs / tasa, 2)
            filas.append({
                "Partido":            f"{a['local']} vs {a['visitante']}",
                "Favorito":           a["favorito"],
                "Prob. ML":           f"{a['prob_fav']}%",
                "Runline -1.5":       f"{a['runline_prob']}%",
                "O/U sugerido":       f"{'Over' if a['over_prob']>50 else 'Under'} {a['linea_ou']}",
                "Confianza":          a["confianza"],
                "Kelly sugerido Bs":  f"Bs {kelly_bs:,.2f}",
                "Kelly sugerido USD": f"$ {kelly_usd:,.2f}",
            })

        st.dataframe(pd.DataFrame(filas), use_container_width=True, hide_index=True)

        st.markdown("---")
        st.subheader("🏆 Top Apuestas del Día")
        top = [a for a in analisis_todos if a["nivel"] == 3] or analisis_todos[:3]
        for idx, a in enumerate(top, 1):
            cuota_ref = CUOTA_REF[a["nivel"]]
            kelly_bs  = kelly_monto(bankroll_bs, a["prob_fav_dec"], cuota_ref)
            with st.expander(
                f"#{idx}  {a['local']} vs {a['visitante']} — {a['confianza']}",
                expanded=(idx == 1)
            ):
                ca, cb, cc = st.columns([2, 1, 1])
                with ca:
                    st.write(f"**Favorito:** {a['favorito']} ({a['prob_fav']}%)")
                    st.write(f"**Runline -1.5:** {a['runline_prob']}%")
                    st.write(f"**{'Over' if a['over_prob']>50 else 'Under'} {a['linea_ou']}:** {a['over_prob']}%")
                with cb:
                    st.write("**Pitchers**")
                    st.caption(f"🏠 {a['pit_l']}\nERA {a['pit_stats_l']['era']} · WHIP {a['pit_stats_l']['whip']}")
                    st.caption(f"✈️ {a['pit_v']}\nERA {a['pit_stats_v']['era']} · WHIP {a['pit_stats_v']['whip']}")
                with cc:
                    st.metric("Kelly sugerido", f"Bs {kelly_bs:,.2f}")
                    st.caption(f"≈ USD {kelly_bs/tasa:,.2f}")
                    st.caption("Kelly fraccionado 25%")

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 2 — ANÁLISIS DETALLADO
    # ══════════════════════════════════════════════════════════════════════════
    with tab_detalle:
        analisis = st.session_state.get("analisis_todos", [])
        if not analisis:
            st.info("Primero carga los juegos en la pestaña 📋 Juegos del Día.")
        else:
            opciones = [f"{a['local']} vs {a['visitante']}" for a in analisis]
            sel = st.selectbox("Selecciona un partido:", opciones, key="sel_detalle")
            a   = next(x for x in analisis if f"{x['local']} vs {x['visitante']}" == sel)

            st.subheader(f"⚾ {a['local']} vs {a['visitante']}")
            c1, c2, c3 = st.columns(3)
            c1.metric(f"🏠 {a['local']}",    f"{a['prob_local']}%",     f"Récord: {a['rec_l']}")
            c2.metric("Win% temporada",      f"{a['pct_l']}% / {a['pct_v']}%")
            c3.metric(f"✈️ {a['visitante']}", f"{a['prob_visitante']}%", f"Récord: {a['rec_v']}")

            st.markdown("---")
            st.subheader("🧢 Pitchers Abridores")
            pc1, pc2 = st.columns(2)
            with pc1:
                st.write(f"**{a['local']}:** {a['pit_l']}")
                st.dataframe(pd.DataFrame([a["pit_stats_l"]]), hide_index=True, use_container_width=True)
            with pc2:
                st.write(f"**{a['visitante']}:** {a['pit_v']}")
                st.dataframe(pd.DataFrame([a["pit_stats_v"]]), hide_index=True, use_container_width=True)

            st.markdown("---")
            st.subheader("🔥 Ofensiva")
            bc1, bc2 = st.columns(2)
            with bc1:
                st.write(f"**{a['local']}**")
                st.dataframe(pd.DataFrame([a["bat_l"]]), hide_index=True, use_container_width=True)
            with bc2:
                st.write(f"**{a['visitante']}**")
                st.dataframe(pd.DataFrame([a["bat_v"]]), hide_index=True, use_container_width=True)

            st.markdown("---")
            st.subheader("📊 Probabilidades")
            st.bar_chart(pd.DataFrame({
                "Probabilidad (%)": {a["local"]: a["prob_local"], a["visitante"]: a["prob_visitante"]}
            }))

            st.markdown("---")
            st.subheader("💡 Propuesta y Sugerencia de Monto")

            tipos = {
                "Moneyline favorito": (a["prob_fav_dec"], -130),
                "Runline -1.5":       (a["runline_prob"] / 100, -115),
                f"{'Over' if a['over_prob']>50 else 'Under'} {a['linea_ou']}":
                                      (a["over_prob"] / 100, -110),
            }
            for nombre, (prob, cuota_def) in tipos.items():
                with st.container():
                    kbs  = kelly_monto(bankroll_bs, prob, cuota_def)
                    kusd = round(kbs / tasa, 2)
                    g    = calcular_ganancia_bs(kbs, cuota_def)
                    st.write(
                        f"**{nombre}** — Prob: `{round(prob*100)}%` | "
                        f"Kelly: `Bs {kbs:,.2f}` (≈ USD {kusd:,.2f}) | "
                        f"Ganancia potencial: `Bs {g:,.2f}`"
                    )

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 3 — REGISTRAR APUESTA
    # ══════════════════════════════════════════════════════════════════════════
    with tab_registro:
        st.subheader("➕ Registrar Nueva Apuesta")

        historial = cargar_historial()

        analisis = st.session_state.get("analisis_todos", [])
        opciones_partido = (
            [f"{a['local']} vs {a['visitante']}" for a in analisis]
            if analisis else []
        )
        opciones_partido = ["(Otro / escribir manualmente)"] + opciones_partido

        with st.form("form_apuesta", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                fecha_ap   = st.date_input("Fecha", value=datetime.now().date())
                partido_op = st.selectbox("Partido", opciones_partido)
                partido_manual = ""
                if partido_op == "(Otro / escribir manualmente)":
                    partido_manual = st.text_input("Escribe el partido (ej: Yankees vs Red Sox)")
                partido_final = partido_manual if partido_op == "(Otro / escribir manualmente)" else partido_op

                tipo_ap = st.selectbox(
                    "Tipo de apuesta",
                    ["Moneyline", "Runline -1.5", "Over", "Under", "Primera carrera", "Otro"]
                )
                seleccion = st.text_input(
                    "Selección (ej: Yankees, Over 8.5)",
                    placeholder="¿Qué apostaste?"
                )

            with col2:
                cuota_am  = st.number_input(
                    "Cuota americana", value=-110.0, step=5.0, format="%.0f",
                    help="Positiva (+150) o negativa (-110)"
                )
                monto_bs  = st.number_input(
                    "Monto apostado (Bs)", min_value=0.01, value=50.0,
                    step=5.0, format="%.2f"
                )
                tasa_reg  = st.number_input(
                    "Tasa USD del día", min_value=1.0,
                    value=float(tasa), step=0.5, format="%.2f"
                )
                resultado = st.selectbox("Resultado", ["Pendiente", "Ganada", "Perdida"])
                conf_manual = st.selectbox(
                    "Confianza del sistema (al momento de apostar)",
                    ["🟢 ALTA", "🟡 MEDIA", "🔴 BAJA", "No consultado"]
                )
                notas = st.text_input("Notas (opcional)")

            submitted = st.form_submit_button("💾 Guardar apuesta", type="primary")

        if submitted:
            if not partido_final or not seleccion:
                st.error("Completa el partido y la selección.")
            else:
                monto_usd = round(monto_bs / tasa_reg, 2)
                dec       = americana_a_decimal(cuota_am)

                if resultado == "Ganada":
                    ganancia_bs  = round(monto_bs * (dec - 1), 2)
                    ganancia_usd = round(ganancia_bs / tasa_reg, 2)
                elif resultado == "Perdida":
                    ganancia_bs  = -monto_bs
                    ganancia_usd = -monto_usd
                else:
                    ganancia_bs  = 0.0
                    ganancia_usd = 0.0

                nueva = pd.DataFrame([{
                    "fecha":             str(fecha_ap),
                    "partido":           partido_final,
                    "tipo_apuesta":      tipo_ap,
                    "seleccion":         seleccion,
                    "cuota_americana":   cuota_am,
                    "monto_bs":          monto_bs,
                    "tasa_usd":          tasa_reg,
                    "monto_usd":         monto_usd,
                    "resultado":         resultado,
                    "ganancia_bs":       ganancia_bs,
                    "ganancia_usd":      ganancia_usd,
                    "confianza_sistema": conf_manual,
                    "notas":             notas,
                }])
                historial = pd.concat([historial, nueva], ignore_index=True)
                guardar_historial(historial)

                emoji = "✅" if resultado == "Ganada" else ("❌" if resultado == "Perdida" else "⏳")
                st.success(
                    f"{emoji} Apuesta registrada: **{seleccion}** en **{partido_final}** — "
                    f"Bs {monto_bs:,.2f} (≈ USD {monto_usd:,.2f})"
                )
                if resultado == "Ganada":
                    st.balloons()

        # ── Actualizar resultado de apuesta pendiente ──────────────────────────
        st.markdown("---")
        st.subheader("🔄 Actualizar resultado de apuesta pendiente")
        pendientes = historial[historial["resultado"] == "Pendiente"]
        if pendientes.empty:
            st.info("No hay apuestas pendientes.")
        else:
            idx_pend = st.selectbox(
                "Selecciona apuesta pendiente:",
                pendientes.index,
                format_func=lambda i: (
                    f"{historial.loc[i,'fecha']} | {historial.loc[i,'partido']} | "
                    f"{historial.loc[i,'seleccion']} | Bs {float(historial.loc[i,'monto_bs']):,.2f}"
                )
            )
            nuevo_resultado = st.radio(
                "Resultado real:", ["Ganada", "Perdida"], horizontal=True, key="upd_res"
            )
            if st.button("✅ Confirmar resultado"):
                fila  = historial.loc[idx_pend]
                dec   = americana_a_decimal(float(fila["cuota_americana"]))
                mb    = float(fila["monto_bs"])
                tasa_r = float(fila["tasa_usd"])
                if nuevo_resultado == "Ganada":
                    gb = round(mb * (dec - 1), 2)
                    gu = round(gb / tasa_r, 2)
                else:
                    gb = -mb
                    gu = round(-mb / tasa_r, 2)

                historial.loc[idx_pend, "resultado"]    = nuevo_resultado
                historial.loc[idx_pend, "ganancia_bs"]  = gb
                historial.loc[idx_pend, "ganancia_usd"] = gu
                guardar_historial(historial)
                st.success(f"Actualizado: {nuevo_resultado} · Ganancia: Bs {gb:,.2f}")
                st.rerun()

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 4 — TRACKER
    # ══════════════════════════════════════════════════════════════════════════
    with tab_tracker:
        st.subheader("📊 Mi Tracker de Apuestas")
        historial = cargar_historial()

        if historial.empty:
            st.info("Aún no registraste ninguna apuesta. Ve a ➕ Registrar Apuesta.")
        else:
            stats = calcular_stats_tracker(historial, bankroll_bs)

            if stats:
                # ── KPIs principales ──────────────────────────────────────────
                k1, k2, k3, k4, k5 = st.columns(5)
                k1.metric("Apuestas cerradas",   stats["total_ap"])
                k2.metric("Win Rate",            f"{stats['win_rate']}%",
                          f"{stats['ganadas']}G / {stats['perdidas']}P")
                k3.metric("ROI",                 f"{stats['roi']}%")
                k4.metric("Neto Bs",
                          f"{'+'if stats['gan_neto_bs']>=0 else ''}Bs {stats['gan_neto_bs']:,.2f}",
                          f"≈ {'+'if stats['gan_neto_usd']>=0 else ''}USD {stats['gan_neto_usd']:,.2f}")
                k5.metric("Bankroll actual",
                          f"Bs {stats['bankroll_actual']:,.2f}",
                          f"≈ USD {stats['bankroll_actual']/tasa:,.2f}")

                st.markdown("---")
                col_a, col_b = st.columns(2)

                with col_a:
                    # Racha
                    st.subheader("🔥 Racha actual")
                    st.metric(
                        f"{stats['racha']} seguidas {stats['tipo_racha']}",
                        f"Pendientes: {stats['pendientes']}"
                    )

                    # Evolución del bankroll
                    st.subheader("📈 Evolución del Bankroll (Bs)")
                    cerradas = historial[historial["resultado"].isin(["Ganada","Perdida"])].copy()
                    cerradas["fecha"] = pd.to_datetime(cerradas["fecha"])
                    cerradas = cerradas.sort_values("fecha")
                    cerradas["ganancia_bs"] = cerradas["ganancia_bs"].astype(float)
                    cerradas["bankroll_acum"] = bankroll_bs + cerradas["ganancia_bs"].cumsum() - cerradas["ganancia_bs"].iloc[0]
                    st.line_chart(cerradas.set_index("fecha")[["bankroll_acum"]])

                with col_b:
                    # Por tipo de apuesta
                    st.subheader("🎯 Rendimiento por Tipo")
                    if stats["por_tipo"]:
                        df_tipo = pd.DataFrame(stats["por_tipo"]).T
                        df_tipo.index.name = "Tipo"
                        st.dataframe(df_tipo, use_container_width=True)

                    # Sugerencia de próxima apuesta basada en historial
                    st.subheader("🤖 Sugerencia de monto (próxima apuesta)")
                    mejor_tipo = max(
                        stats["por_tipo"].items(),
                        key=lambda x: x[1]["win_rate"],
                        default=(None, None)
                    )
                    if mejor_tipo[0]:
                        wt = mejor_tipo[1]["win_rate"] / 100
                        # Kelly conservador con win_rate histórico propio
                        kelly_hist = kelly_monto(stats["bankroll_actual"], wt, -120, fraccion=0.20)
                        st.write(
                            f"Tu mejor tipo: **{mejor_tipo[0]}** "
                            f"({mejor_tipo[1]['win_rate']}% win rate en {mejor_tipo[1]['jugadas']} jugadas)."
                        )
                        st.metric(
                            "Monto sugerido próxima apuesta",
                            f"Bs {kelly_hist:,.2f}",
                            f"≈ USD {kelly_hist/tasa:,.2f}"
                        )
                        st.caption(
                            "Calculado con Kelly fraccionado (20%) sobre tu bankroll actual "
                            "y tu win rate histórico personal."
                        )

                st.markdown("---")

            # ── Historial completo ─────────────────────────────────────────────
            st.subheader("📋 Historial Completo")

            col_f1, col_f2, col_f3 = st.columns(3)
            filtro_res  = col_f1.selectbox("Filtrar por resultado:",
                                           ["Todos","Ganada","Perdida","Pendiente"])
            filtro_tipo = col_f2.selectbox("Filtrar por tipo:",
                                           ["Todos"] + list(historial["tipo_apuesta"].unique()))
            buscar = col_f3.text_input("Buscar partido:")

            df_show = historial.copy()
            if filtro_res  != "Todos": df_show = df_show[df_show["resultado"]    == filtro_res]
            if filtro_tipo != "Todos": df_show = df_show[df_show["tipo_apuesta"] == filtro_tipo]
            if buscar:                 df_show = df_show[df_show["partido"].str.contains(buscar, case=False, na=False)]

            # Formatear para mostrar
            df_show_disp = df_show[[
                "fecha","partido","tipo_apuesta","seleccion",
                "cuota_americana","monto_bs","ganancia_bs","resultado","confianza_sistema","notas"
            ]].copy()
            df_show_disp["monto_bs"]    = df_show_disp["monto_bs"].apply(lambda x: f"Bs {float(x):,.2f}")
            df_show_disp["ganancia_bs"] = df_show_disp["ganancia_bs"].apply(
                lambda x: f"{'+'if float(x)>=0 else ''}Bs {float(x):,.2f}"
            )
            st.dataframe(df_show_disp, use_container_width=True, hide_index=True)

            # Exportar CSV
            st.download_button(
                "⬇️ Descargar historial CSV",
                data=historial.to_csv(index=False).encode("utf-8"),
                file_name=f"apuestas_mlb_{HOY}.csv",
                mime="text/csv",
            )


if __name__ == "__main__":
    main()
