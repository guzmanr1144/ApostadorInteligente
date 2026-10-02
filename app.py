"""
Eco de los Gigantes: Misión Paleontológica
-------------------------------------------
Juego de estrategia, simulación y gestión de expedición científica por turnos en Streamlit.
Usa la API de Gemini (gemini-2.5-flash) desde st.secrets["GEMINI_API_KEY"] para la narrativa.
"""

import random
import pandas as pd
import streamlit as st
import google.genai as genai

# --------------------------------------------------------------------------
# Configuración inicial de la página
# --------------------------------------------------------------------------
st.set_page_config(
    page_title="Eco de los Gigantes: Expedición Paleontológica",
    page_icon="🦴",
    layout="wide",
)

# --------------------------------------------------------------------------
# Catálogo de Fósiles y Eventos
# --------------------------------------------------------------------------
CATALOGO_FOSILES = {
    "Valle de los Titanes (Saurópodos y Terópodos)": [
        {"nombre": "Fémur de Saurópodo Gigante", "prestigio": 300, "valor": 3500, "raro": True},
        {"nombre": "Diente Serrado de Terópodo Apex", "prestigio": 220, "valor": 2200, "raro": False},
        {"nombre": "Vértebra Caudal en Concreción", "prestigio": 140, "valor": 1200, "raro": False},
        {"nombre": "Tronco de Conífera Petrificada", "prestigio": 80, "valor": 600, "raro": False},
    ],
    "Cañón de los Pterosaurios (Azhdárquidos y Pterosaurios)": [
        {"nombre": "Cráneo intacto de Hatzegopteryx", "prestigio": 500, "valor": 6000, "raro": True},
        {"nombre": "Cresta Ósea con Pigmento de Quetzalcoatlus", "prestigio": 350, "valor": 3200, "raro": True},
        {"nombre": "Falange Alar con Impresión de Membrana", "prestigio": 210, "valor": 2000, "raro": False},
        {"nombre": "Hueso Neumático Hueco Fosilizado", "prestigio": 110, "valor": 900, "raro": False},
    ],
    "Cuenca del Río Prehistórico (Peces y Ámbar)": [
        {"nombre": "Nódulo de Ámbar con Insecto Cretácico", "prestigio": 350, "valor": 4000, "raro": True},
        {"nombre": "Fósil Completo de Pez Celacanto", "prestigio": 240, "valor": 2500, "raro": False},
        {"nombre": "Losa con Huellas Fosilizadas (Icnitas)", "prestigio": 180, "valor": 1800, "raro": False},
        {"nombre": "Coprolito Fosilizado con Inclusiones", "prestigio": 90, "valor": 700, "raro": False},
    ]
}

EVENTOS_ALEATORIOS = [
    {
        "titulo": "🌪️ Tormenta de Arena Imprevista",
        "descripcion": "Una violenta ráfaga azotó el campamento base amenazando las carpas de preservación.",
        "efecto_a": lambda s: (s.update({"presupuesto": max(0, s["presupuesto"] - 400)}), "Gastaste $400 en reforzar la estructura del campamento."),
        "efecto_b": lambda s: (s.update({"integridad": max(0, s["integridad"] - 15), "moral": max(0, s["moral"] - 10)}), "El equipo y herramientas sufrieron desgastes severos.")
    },
    {
        "titulo": "💧 Escasez de Agua Potable",
        "descripcion": "Un depósito de agua sufrió una fisura debido al calor extremo del desierto.",
        "efecto_a": lambda s: (s.update({"presupuesto": max(0, s["presupuesto"] - 600), "raciones": s["raciones"] + 10}), "Compraste suministro de agua de emergencia a un convoy local."),
        "efecto_b": lambda s: (s.update({"moral": max(0, s["moral"] - 15)}), "La moral del equipo cayó debido a la sed y el racionamiento estricto.")
    },
    {
        "titulo": "🕵️ Exploradores de un Museo Rival",
        "descripcion": "Una expedición rival intenta excavar en los límites de tu concesión territorial.",
        "efecto_a": lambda s: (s.update({"presupuesto": s["presupuesto"] + 1000, "prestigio": max(0, s["prestigio"] - 100)}), "Negociaste un pacto financiero, pero cediste exclusividad científica."),
        "efecto_b": lambda s: (s.update({"prestigio": s["prestigio"] + 100, "raciones": max(0, s["raciones"] - 5)}), "Defendiste legalmente tu territorio y ganaste respeto académico.")
    },
    {
        "titulo": "🚚 Avería del Vehículo Todoterreno",
        "descripcion": "El eje del camión principal de excavación se rompió transportando rocas pesadas.",
        "efecto_a": lambda s: (s.update({"presupuesto": max(0, s["presupuesto"] - 800)}), "Contrataste reparación mecánica profesional inmediata."),
        "efecto_b": lambda s: (s.update({"integridad": max(0, s["integridad"] - 20), "moral": max(0, s["moral"] - 10)}), "La reparación artesanal agotó al personal y dañó herramientas.")
    }
]

# --------------------------------------------------------------------------
# Estado del Juego (Session State)
# --------------------------------------------------------------------------
def inicializar_juego():
    st.session_state["presupuesto"] = 12000
    st.session_state["raciones"] = 40
    st.session_state["integridad"] = 100
    st.session_state["moral"] = 100
    st.session_state["prestigio"] = 0
    st.session_state["dia"] = 1
    st.session_state["max_dias"] = 8
    st.session_state["fosiles"] = []
    st.session_state["historial"] = []
    st.session_state["juego_terminado"] = False
    st.session_state["cronica"] = "Bienvenido a la expedición. Configura la primera jornada de excavación."

if "presupuesto" not in st.session_state:
    inicializar_juego()

# --------------------------------------------------------------------------
# Integración con Gemini AI (Game Master Narrativo vía Secrets)
# --------------------------------------------------------------------------
def obtener_api_key() -> str | None:
    if hasattr(st, "secrets") and "GEMINI_API_KEY" in st.secrets:
        return st.secrets["GEMINI_API_KEY"]
    return None

def generar_diario_campo(api_key: str | None, dia: int, zona: str, estrategia: str, hallazgo: str, evento_info: str) -> str:
    if not api_key:
        return (
            f"📖 **Diario de Campo (Día {dia}):** Hoy excavamos en **{zona}** aplicando la técnica *'{estrategia}'*. "
            f"\n\n**Incidente de la jornada:** {evento_info} "
            f"\n\n**Resultado paleontológico:** {hallazgo}"
        )
    
    try:
        client = genai.Client(api_key=api_key)
        prompt = f"""
        Eres el paleontólogo principal y narrador de una expedición científica en el desierto Cretácico.
        Redacta una entrada emotiva, realista y académica para el Diario de Campo (máximo 100 palabras) sobre la jornada del Día {dia}.

        Contexto del día:
        - Ubicación: {zona}
        - Método de trabajo: {estrategia}
        - Desafío o evento enfrentado: {evento_info}
        - Hallazgo paleontológico: {hallazgo}
        - Estado actual: Presupuesto ${st.session_state['presupuesto']}, Raciones {st.session_state['raciones']}, Moral {st.session_state['moral']}%.

        Haz énfasis en la rigurosidad científica, la emoción del descubrimiento y la dureza del entorno.
        """
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        return response.text or "Diario registrado con éxito."
    except Exception as err:
        return (
            f"📖 **Diario de Campo (Día {dia}):** Excavación en **{zona}**. "
            f"\n\n**Resultado:** {hallazgo}. *(Error al conectar con la IA: {err})*"
        )

# --------------------------------------------------------------------------
# Barra Lateral - Panel de Control & Recursos
# --------------------------------------------------------------------------
with st.sidebar:
    st.title("🏛️ Expedición Cretácica")
    st.caption("Centro de Mando de Campo")
    
    st.subheader("📊 Estado de Recursos")
    col1, col2 = st.columns(2)
    col1.metric("💵 Presupuesto", f"${st.session_state['presupuesto']}")
    col2.metric("🍖 Raciones", f"{st.session_state['raciones']} ud")
    
    st.write("**Integridad de Herramientas:**")
    st.progress(st.session_state["integridad"] / 100)
    
    st.write("**Moral del Equipo:**")
    st.progress(st.session_state["moral"] / 100)
    
    st.metric("🏆 Prestigio Científico", f"{st.session_state['prestigio']} pts")
    st.write(f"📅 **Jornada:** Día {st.session_state['dia']} de {st.session_state['max_dias']}")

    st.markdown("---")
    api_key_status = "✅ Gemini Conectado (Secrets)" if obtener_api_key() else "⚠️ Modo Narrativo Estándar"
    st.caption(f"Estado de IA: {api_key_status}")

    if st.button("🔄 Reiniciar Expedición", type="secondary", use_container_width=True):
        inicializar_juego()
        st.rerun()

# --------------------------------------------------------------------------
# Pantalla Principal
# --------------------------------------------------------------------------
st.title("🦴 Eco de los Gigantes: Misión Paleontológica")
st.write("Dirige una expedición científica en busca de fósiles Cretácicos. Administra tus recursos, enfréntate a los desafíos del clima hostil y demuestra tu valor científico al Museo Nacional.")

# Verificar derrota prematura
if (st.session_state["presupuesto"] <= 0 or st.session_state["raciones"] <= 0 or 
    st.session_state["integridad"] <= 0 or st.session_state["moral"] <= 0) and not st.session_state["juego_terminado"]:
    st.session_state["juego_terminado"] = True
    st.session_state["motivo_derrota"] = "La expedición colapsó por agotamiento extremo de recursos o pérdida total del equipo."

# --- PANTALLA DE JUEGO TERMINADO ---
if st.session_state["juego_terminado"]:
    st.markdown("---")
    if st.session_state.get("motivo_derrota"):
        st.error(f"❌ **Misión Fracasada:** {st.session_state['motivo_derrota']}")
    else:
        st.balloons()
        st.success("🎉 **¡Expedición Completada con Éxito!**")

    puntos = st.session_state["prestigio"] + (st.session_state["presupuesto"] // 10)
    st.subheader("📈 Evaluación Científica Final del Museo")
    
    col_a, col_b, col_c = st.columns(3)
    col_a.metric("Puntos de Prestigio", st.session_state["prestigio"])
    col_b.metric("Fósiles Recolectados", len(st.session_state["fosiles"]))
    col_c.metric("Puntuación Total", puntos)

    if puntos >= 1200:
        st.header("🏆 Rango: Medalla de Oro - Doctor Honoris Causa")
        st.write("¡Tus descubrimientos han reescrito la paleontología! Tu nombre quedará grabado en la historia de la ciencia.")
    elif puntos >= 700:
        st.header("🥈 Rango: Medalla de Plata - Expedición Excepcional")
        st.write("Conseguiste una colección fosilífera de enorme valor y mantuviste a tu equipo a salvo.")
    else:
        st.header("🥉 Rango: Medalla de Bronce - Retorno Modesto")
        st.write("La expedición sobrevivió, pero los hallazgos apenas cubren los gastos operativos del Museo.")

    if st.session_state["fosiles"]:
        st.subheader("🔍 Catálogo de Fósiles Descubiertos")
        df_fosiles = pd.DataFrame(st.session_state["fosiles"])
        st.dataframe(df_fosiles, use_container_width=True)

    if st.button("🚀 Comenzar Nueva Expedición", type="primary"):
        inicializar_juego()
        st.rerun()

    st.stop()

# --- PANTALLA DE JUEGO ACTIVO ---
st.markdown("---")
st.subheader(f"📍 Planificación de la Jornada - Día {st.session_state['dia']}")

col_main1, col_main2 = st.columns([2, 1])

with col_main1:
    zona_seleccionada = st.selectbox(
        "🎯 Elige la zona de excavación para hoy:",
        list(CATALOGO_FOSILES.keys()),
        help="Cada yacimiento contiene fósiles característicos con distinto nivel de rareza y valor."
    )

    estrategia = st.radio(
        "🛠️ Técnica y ritmo de excavación:",
        [
            "Excavación Meticulosa con Pincel (Lenta, preserva fósiles raros, consume +3 raciones)",
            "Excavación Estándar con Cincel (Equilibrada)",
            "Excavación Mecanizada Intensiva (Rápida, riesgosa para las muestras, -$300)"
        ]
    )

    enfoque_campamento = st.selectbox(
        "🏕️ Tarea del Campamento al atardecer:",
        [
            "Racionamiento y Descanso (+10% Moral del equipo, -3 Raciones)",
            "Mantenimiento de Herramientas (+15% Integridad, -$200)",
            "Consolidación y Catalogación (+50 Prestigio Científico, -2 Raciones)"
        ]
    )

with col_main2:
    st.info("💡 **Consejo Táctico:** Usa la *Excavación Meticulosa* si buscas piezas de gran valor científico. Asegúrate de hacer mantenimiento antes de que la integridad de tus herramientas caiga a cero.")

# Ejecutar Turno
if st.button("⛏️ Iniciar Excavación y Avanzar Día", type="primary", use_container_width=True):
    # 1. Consumo base de recursos diarios
    st.session_state["raciones"] = max(0, st.session_state["raciones"] - 4)
    st.session_state["integridad"] = max(0, st.session_state["integridad"] - random.randint(3, 8))
    
    # 2. Aplicar Enfoque de Campamento
    if "Racionamiento" in enfoque_campamento:
        st.session_state["moral"] = min(100, st.session_state["moral"] + 10)
        st.session_state["raciones"] = max(0, st.session_state["raciones"] - 3)
    elif "Mantenimiento" in enfoque_campamento:
        st.session_state["integridad"] = min(100, st.session_state["integridad"] + 15)
        st.session_state["presupuesto"] = max(0, st.session_state["presupuesto"] - 200)
    elif "Consolidación" in enfoque_campamento:
        st.session_state["prestigio"] += 50
        st.session_state["raciones"] = max(0, st.session_state["raciones"] - 2)

    if "Meticulosa" in estrategia:
        st.session_state["raciones"] = max(0, st.session_state["raciones"] - 3)
    elif "Mecanizada" in estrategia:
        st.session_state["presupuesto"] = max(0, st.session_state["presupuesto"] - 300)

    # 3. Probabilidad de Hallazgo Fosilífero
    prob_hallazgo = 0.85 if "Meticulosa" in estrategia else 0.70
    hallazgo_texto = "No se descubrieron fósiles relevantes hoy."
    
    if random.random() < prob_hallazgo:
        opciones = CATALOGO_FOSILES[zona_seleccionada]
        if "Meticulosa" in estrategia:
            fosil_hallado = random.choice(opciones)
        else:
            fosil_hallado = random.choice([f for f in opciones if not f["raro"]] or opciones)
            
        st.session_state["fosiles"].append(fosil_hallado)
        st.session_state["prestigio"] += fosil_hallado["prestigio"]
        hallazgo_texto = f"¡DESCUBRIMIENTO! {fosil_hallado['nombre']} (+{fosil_hallado['prestigio']} pts prestigio)."
        st.toast(f"🦴 {hallazgo_texto}")

    # 4. Evento Aleatorio del Día
    evento = random.choice(EVENTOS_ALEATORIOS)
    if st.session_state["moral"] > 50 or st.session_state["presupuesto"] > 1000:
        msg_evento = evento["efecto_a"](st.session_state)[1]
    else:
        msg_evento = evento["efecto_b"](st.session_state)[1]
        
    evento_desc = f"{evento['titulo']}: {msg_evento}"

    # 5. Generar Narrativa con Gemini
    api_key = obtener_api_key()
    cronica = generar_diario_campo(
        api_key, 
        st.session_state["dia"], 
        zona_seleccionada, 
        estrategia, 
        hallazgo_texto, 
        evento_desc
    )
    st.session_state["cronica"] = cronica

    # 6. Avanzar Turno
    st.session_state["dia"] += 1
    if st.session_state["dia"] > st.session_state["max_dias"]:
        st.session_state["juego_terminado"] = True

    st.rerun()

# --- MOSTRAR DIARIO DE CAMPO ---
st.markdown("---")
st.subheader("📖 Diario de Campo e Historial de la Misión")
st.markdown(st.session_state["cronica"])

if st.session_state["fosiles"]:
    with st.expander("🦴 Muestras Fosilíferas Recolectadas hasta el momento"):
        df_temp = pd.DataFrame(st.session_state["fosiles"])
        st.dataframe(df_temp, use_container_width=True)
