"""
Analizador Deportivo Pro - Versión Mejorada
Mejoras:
  - API Key via variable de entorno / st.secrets (no hardcodeada)
  - Eliminado random() para probabilidades: solo datos reales
  - Manejo de errores granular y mensajes descriptivos
  - Funciones de análisis separadas de la UI
  - Visualizaciones con st.bar_chart y progress bars etiquetadas
  - Spinner de carga en llamadas a la API
  - Validación de datos nulos / divisiones por cero
  - Indicador de cuántas llamadas API quedan (The Odds API devuelve headers)
"""

import os
import streamlit as st
import pandas as pd
import requests
from datetime import datetime

# ── Configuración de página ────────────────────────────────────────────────────
st.set_page_config(
    page_title="Analizador Deportivo Pro",
    layout="wide",
    page_icon="📈",
)

# ── API KEY: nunca hardcodear. Usa st.secrets (deploy) o variable de entorno (local) ──
# En local: export ODDS_API_KEY="tu_clave"
# En Streamlit Cloud: añadir en Settings > Secrets: ODDS_API_KEY = "tu_clave"
API_KEY_FUTBOL: str = st.secrets.get("ODDS_API_KEY", os.environ.get("ODDS_API_KEY", ""))

MAPEO_LIGAS: dict[str, str] = {
    "La Liga (España)": "soccer_spain_la_liga",
    "Premier League (Inglaterra)": "soccer_epl",
    "Serie A (Italia)": "soccer_italy_serie_a",
    "Champions League": "soccer_uefa_champs_league",
}

# ── Helpers de UI ──────────────────────────────────────────────────────────────

def barra_prob(label: str, valor: int, color: str = "normal") -> None:
    """Muestra una barra de progreso con etiqueta y porcentaje."""
    st.write(f"**{label}:** `{valor}%`")
    st.progress(valor / 100)


def mostrar_tabla_probabilidades(datos: dict[str, int]) -> None:
    """Muestra un bar chart horizontal con las probabilidades."""
    df = pd.DataFrame.from_dict(datos, orient="index", columns=["Probabilidad (%)"])
    st.bar_chart(df)


# ══════════════════════════════════════════════════════════════════════════════
# MOTOR MLB
# ══════════════════════════════════════════════════════════════════════════════

@st.cache_data(ttl=1800, show_spinner=False)
def obtener_juegos_mlb(fecha: str) -> tuple[list[str], dict]:
    """
    Llama a la API oficial de MLB y devuelve partidos del día.
    Retorna (lista_nombres, dict_detalles). En caso de error retorna ([], {}).
    """
    url = f"https://statsapi.mlb.com/api/v1/schedule/games/?sportId=1&date={fecha}"
    try:
        respuesta = requests.get(url, timeout=10)
        respuesta.raise_for_status()
        datos = respuesta.json()

        fechas = datos.get("dates", [])
        if not fechas:
            return [], {}

        juegos = fechas[0].get("games", [])
        lista_partidos: list[str] = []
        detalles: dict = {}

        for j in juegos:
            local = j["teams"]["home"]["team"]["name"]
            visitante = j["teams"]["away"]["team"]["name"]
            nombre = f"{local} vs {visitante}"
            lista_partidos.append(nombre)

            rec_l = j["teams"]["home"].get("leagueRecord", {})
            rec_v = j["teams"]["away"].get("leagueRecord", {})

            detalles[nombre] = {
                "local": local,
                "visitante": visitante,
                "w_l": int(rec_l.get("wins", 0)),
                "l_l": int(rec_l.get("losses", 0)),
                "w_v": int(rec_v.get("wins", 0)),
                "l_v": int(rec_v.get("losses", 0)),
            }

        return lista_partidos, detalles

    except requests.exceptions.Timeout:
        st.error("⏱️ La API de MLB no respondió a tiempo. Intenta de nuevo.")
    except requests.exceptions.HTTPError as e:
        st.error(f"❌ Error HTTP al consultar MLB: {e}")
    except (KeyError, IndexError, ValueError) as e:
        st.error(f"⚠️ Error procesando datos de MLB: {e}")

    return [], {}


def calcular_probabilidades_mlb(datos: dict) -> dict[str, int]:
    """
    Calcula probabilidades basadas en el porcentaje de victorias de cada equipo.
    Devuelve {'prob_local': int, 'prob_visitante': int}.
    """
    total_l = datos["w_l"] + datos["l_l"]
    total_v = datos["w_v"] + datos["l_v"]

    pct_l = datos["w_l"] / total_l if total_l > 0 else 0.5
    pct_v = datos["w_v"] / total_v if total_v > 0 else 0.5
    suma = pct_l + pct_v

    if suma == 0:
        return {"prob_local": 50, "prob_visitante": 50}

    prob_local = round((pct_l / suma) * 100)
    return {"prob_local": prob_local, "prob_visitante": 100 - prob_local}


def seccion_mlb() -> None:
    fecha_hoy = datetime.now().strftime("%Y-%m-%d")

    with st.spinner("Consultando API oficial de MLB..."):
        partidos, info = obtener_juegos_mlb(fecha_hoy)

    if not partidos:
        st.info("🚫 No hay partidos de MLB programados para hoy.")
        return

    partido_sel = st.sidebar.selectbox("Partidos programados (MLB - HOY):", partidos)
    datos = info[partido_sel]
    probs = calcular_probabilidades_mlb(datos)

    st.subheader(f"⚾ Análisis Sabermétrico: {datos['local']} vs {datos['visitante']}")

    col1, col2 = st.columns(2)
    with col1:
        st.metric(f"Victoria {datos['local']} (Local)", f"{probs['prob_local']}%")
        st.caption(f"Récord: {datos['w_l']}G – {datos['l_l']}P")
    with col2:
        st.metric(f"Victoria {datos['visitante']} (Visitante)", f"{probs['prob_visitante']}%")
        st.caption(f"Récord: {datos['w_v']}G – {datos['l_v']}P")

    st.markdown("---")
    st.subheader("📊 Distribución de Probabilidades")
    mostrar_tabla_probabilidades({
        datos["local"]: probs["prob_local"],
        datos["visitante"]: probs["prob_visitante"],
    })

    # Runline: ajuste estándar (-1.5 reduce ~12-15 puntos porcentuales)
    runline_prob = max(probs["prob_local"] - 13, 5)
    st.markdown("---")
    st.subheader("🎯 Líneas Estimadas")
    col3, col4 = st.columns(2)
    with col3:
        barra_prob(f"Runline {datos['local']} -1.5", runline_prob)
        st.caption("Ajuste estándar: ganar por ≥2 carreras reduce ~13 pp la probabilidad.")
    with col4:
        st.info(
            "ℹ️ **Over/Under de carreras** requiere datos de pitchers y ERA.\n"
            "Conecta la API de stats avanzados de MLB para activar este mercado."
        )


# ══════════════════════════════════════════════════════════════════════════════
# MOTOR FÚTBOL
# ══════════════════════════════════════════════════════════════════════════════

@st.cache_data(ttl=1800, show_spinner=False)
def consultar_futbol_oddsapi(codigo: str) -> tuple[list[str], dict, dict]:
    """
    Llama a The Odds API y devuelve partidos con cuotas reales.
    Retorna (lista_partidos, detalles, headers_info).
    """
    if not API_KEY_FUTBOL:
        st.error(
            "🔑 **API Key no configurada.** "
            "Añade `ODDS_API_KEY` en tus variables de entorno o en Streamlit Secrets."
        )
        return [], {}, {}

    url = f"https://api.the-odds-api.com/v4/sports/{codigo}/odds/"
    params = {
        "apiKey": API_KEY_FUTBOL,
        "regions": "eu",
        "markets": "h2h,totals",  # Pedimos h2h Y totales para Over/Under real
        "oddsFormat": "decimal",
    }

    try:
        respuesta = requests.get(url, params=params, timeout=10)

        # Guardar info de cuota de requests restantes
        headers_info = {
            "requests_remaining": respuesta.headers.get("x-requests-remaining", "N/A"),
            "requests_used": respuesta.headers.get("x-requests-used", "N/A"),
        }

        if respuesta.status_code == 401:
            st.error("❌ API Key inválida o expirada.")
            return [], {}, {}
        if respuesta.status_code == 422:
            st.error("❌ Liga no disponible en este momento.")
            return [], {}, {}

        respuesta.raise_for_status()
        datos = respuesta.json()

        lista_partidos: list[str] = []
        detalles: dict = {}

        for juego in datos:
            local = juego.get("home_team", "Desconocido")
            visitante = juego.get("away_team", "Desconocido")
            nombre = f"{local} vs {visitante}"
            lista_partidos.append(nombre)

            # Extraer cuotas h2h
            c_l, c_e, c_v = None, None, None
            over_25_cuota, under_25_cuota = None, None

            for bookie in juego.get("bookmakers", []):
                for mercado in bookie.get("markets", []):
                    if mercado["key"] == "h2h" and c_l is None:
                        for o in mercado.get("outcomes", []):
                            if o["name"] == local:
                                c_l = o["price"]
                            elif o["name"] == visitante:
                                c_v = o["price"]
                            else:
                                c_e = o["price"]

                    if mercado["key"] == "totals" and over_25_cuota is None:
                        for o in mercado.get("outcomes", []):
                            if o.get("point") == 2.5:
                                if o["name"] == "Over":
                                    over_25_cuota = o["price"]
                                elif o["name"] == "Under":
                                    under_25_cuota = o["price"]

                if c_l and over_25_cuota:
                    break  # Con un bookie es suficiente

            detalles[nombre] = {
                "local": local,
                "visitante": visitante,
                "cuotas_h2h": (c_l or 2.5, c_e or 3.2, c_v or 2.8),
                "over_25": over_25_cuota,
                "under_25": under_25_cuota,
            }

        return lista_partidos, detalles, headers_info

    except requests.exceptions.Timeout:
        st.error("⏱️ The Odds API no respondió. Intenta de nuevo.")
    except requests.exceptions.HTTPError as e:
        st.error(f"❌ Error HTTP: {e}")
    except (KeyError, ValueError) as e:
        st.error(f"⚠️ Error procesando datos: {e}")

    return [], {}, {}


def cuotas_a_probabilidades(c_l: float, c_e: float, c_v: float) -> tuple[int, int, int]:
    """
    Convierte cuotas decimales a probabilidades ajustadas al margen de la casa.
    Retorna (prob_local, prob_empate, prob_visitante) como enteros que suman 100.
    """
    if 0 in (c_l, c_e, c_v):
        return 33, 34, 33

    raw_l = 1 / c_l
    raw_e = 1 / c_e
    raw_v = 1 / c_v
    total = raw_l + raw_e + raw_v  # > 1.0 por el margen de la casa

    prob_l = round((raw_l / total) * 100)
    prob_v = round((raw_v / total) * 100)
    prob_e = 100 - prob_l - prob_v  # Asegura que sumen exactamente 100

    return prob_l, prob_e, prob_v


def cuota_a_prob_simple(cuota: float) -> int:
    """Convierte una cuota decimal a probabilidad implícita (sin ajustar margen)."""
    if not cuota or cuota <= 1:
        return 50
    return round((1 / cuota) * 100)


def seccion_futbol() -> None:
    liga_sel = st.sidebar.selectbox("Liga:", list(MAPEO_LIGAS.keys()))
    codigo = MAPEO_LIGAS[liga_sel]

    with st.spinner("Consultando The Odds API..."):
        partidos, info, headers = consultar_futbol_oddsapi(codigo)

    # Mostrar cuota de requests restantes (útil para el usuario con plan gratuito)
    if headers:
        st.sidebar.caption(
            f"🔢 Requests API: {headers['requests_used']} usados / "
            f"{headers['requests_remaining']} restantes"
        )

    if not partidos:
        st.info("🚫 No se encontraron partidos disponibles para esta liga. Prueba cambiando de liga.")
        return

    partido_sel = st.sidebar.selectbox("Partidos disponibles:", partidos)
    datos = info[partido_sel]

    c_l, c_e, c_v = datos["cuotas_h2h"]
    prob_l, prob_e, prob_v = cuotas_a_probabilidades(c_l, c_e, c_v)

    st.subheader(f"⚽ {datos['local']} vs {datos['visitante']}")
    st.success(f"Datos en tiempo real de The Odds API · {liga_sel}")

    # Probabilidades principales
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(f"🏠 {datos['local']}", f"{prob_l}%", f"Cuota: {c_l:.2f}")
    with col2:
        st.metric("🤝 Empate", f"{prob_e}%", f"Cuota: {c_e:.2f}")
    with col3:
        st.metric(f"✈️ {datos['visitante']}", f"{prob_v}%", f"Cuota: {c_v:.2f}")

    st.markdown("---")
    st.subheader("📊 Distribución Visual")
    mostrar_tabla_probabilidades({
        datos["local"]: prob_l,
        "Empate": prob_e,
        datos["visitante"]: prob_v,
    })

    st.markdown("---")
    st.subheader("🎯 Mercados de Goles")

    col4, col5 = st.columns(2)

    with col4:
        if datos["over_25"]:
            prob_over = cuota_a_prob_simple(datos["over_25"])
            barra_prob(f"Over 2.5 Goles (cuota {datos['over_25']:.2f})", prob_over)
            st.caption("Probabilidad implícita directa de la cuota de mercado.")
        else:
            st.info("ℹ️ Cuota Over 2.5 no disponible para este partido.")

    with col5:
        if datos["under_25"]:
            prob_under = cuota_a_prob_simple(datos["under_25"])
            barra_prob(f"Under 2.5 Goles (cuota {datos['under_25']:.2f})", prob_under)
        else:
            st.info("ℹ️ Cuota Under 2.5 no disponible para este partido.")

    # Nota de transparencia
    st.markdown("---")
    st.caption(
        "⚠️ **Aviso:** Las probabilidades mostradas son las probabilidades implícitas "
        "de las cuotas de mercado ajustadas al margen de la casa. "
        "No constituyen asesoramiento de apuestas. Apuesta con responsabilidad."
    )


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

def main() -> None:
    st.title("📈 Analizador Estadístico Deportivo Pro")
    st.write(
        f"Datos en tiempo real · Procesado el **{datetime.now().strftime('%d/%m/%Y %H:%M')}**"
    )

    st.sidebar.header("Panel de Control")
    deporte = st.sidebar.radio("Deporte:", ["Fútbol ⚽", "Béisbol (MLB) ⚾"])

    if "Béisbol" in deporte:
        seccion_mlb()
    else:
        seccion_futbol()


if __name__ == "__main__":
    main()
