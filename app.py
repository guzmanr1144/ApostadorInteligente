"""
Mi Libreta Inteligente de Reuniones
------------------------------------
App de Streamlit que usa la API de Gemini para:
  1) Limpiar y estructurar notas escritas a mano/teclado.
  2) Transcribir y resumir audio de reuniones, con protección
     anti-alucinación (el modelo no debe inventar contenido).
"""

from __future__ import annotations

import logging
import mimetypes
import os
import tempfile
import time
from dataclasses import dataclass

import google.genai as genai
import streamlit as st
from google.genai import types as genai_types

# --------------------------------------------------------------------------
# Configuración general
# --------------------------------------------------------------------------

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MODEL_NAME = "gemini-2.5-flash"
MAX_FILE_ACTIVE_WAIT_SECONDS = 60  # tiempo máximo esperando a que Gemini procese el audio
POLL_INTERVAL_SECONDS = 2

NOTES_PROMPT_TEMPLATE = """\
Eres un asistente ejecutivo. Toma estas notas rápidas tomadas a toda prisa durante una \
reunión y transfórmalas en un reporte pulido, sin errores ortográficos y bien estructurado.

Reglas:
- No inventes información que no esté presente o implícita en las notas originales.
- Si falta información en alguna sección (por ejemplo, no hay tareas asignadas), indícalo \
explícitamente en vez de rellenar con contenido genérico.

Notas desordenadas:
\"\"\"
{notes}
\"\"\"

Estructura el resultado con:
- 📌 **Resumen General**
- 💡 **Puntos Clave Discutidos**
- ✅ **Acuerdos Tomados**
- 📋 **Tareas y Responsables**
"""

AUDIO_PROMPT = """\
REGLA DE ORO: Escucha únicamente el audio adjunto. Queda estrictamente PROHIBIDO inventar \
nombres, temas, acuerdos o detalles que no se escuchen textualmente en la grabación.

Instrucciones:
1. Si el audio contiene silencio, ruido, música de fondo o no hay voz humana legible, \
responde ÚNICAMENTE: "⚠️ El audio no contiene una conversación clara o está en silencio."
2. Si el audio contiene voz legible, realiza lo siguiente basándote 100% en lo que escuchaste:
   - 📝 **Resumen Fiel:** Describe exactamente de qué se habló.
   - 💡 **Puntos Clave:** Detalla solo los hechos mencionados.
   - ✅ **Acuerdos y Tareas:** Lista únicamente lo asignado en el audio (si no se mencionan \
nombres ni tareas, indica "No se especificaron acuerdos").
"""


# --------------------------------------------------------------------------
# Utilidades
# --------------------------------------------------------------------------

@dataclass
class AudioResult:
    text: str


def get_api_key() -> str | None:
    """Obtiene la API key desde Secrets de Streamlit Cloud o la barra lateral."""
    api_key = st.secrets.get("GEMINI_API_KEY") if hasattr(st, "secrets") else None

    if not api_key:
        with st.sidebar:
            st.header("⚙️ Configuración")
            api_key = st.text_input(
                "Ingresa tu Gemini API Key:",
                type="password",
                help="Se recomienda configurarla en Secrets de Streamlit Cloud en lugar de "
                     "pegarla aquí cada vez.",
            )
    return api_key or None


@st.cache_resource(show_spinner=False)
def get_client(api_key: str) -> genai.Client:
    """Crea (y cachea) el cliente de Gemini para esta API key."""
    return genai.Client(api_key=api_key)


def clean_notes(client: genai.Client, raw_notes: str) -> str:
    """Envía las notas en bruto al modelo y devuelve el reporte estructurado."""
    prompt = NOTES_PROMPT_TEMPLATE.format(notes=raw_notes)
    response = client.models.generate_content(model=MODEL_NAME, contents=prompt)
    return response.text or ""


def _guess_suffix(uploaded_file) -> str:
    """Determina la extensión/mime type correctos del audio subido o grabado."""
    name = getattr(uploaded_file, "name", None)
    if name and "." in name:
        return "." + name.rsplit(".", 1)[-1]
    # st.audio_input entrega WAV por defecto
    return ".wav"


def _wait_until_active(client: genai.Client, file_obj) -> None:
    """Espera a que Gemini termine de procesar el archivo de audio subido."""
    elapsed = 0
    while file_obj.state.name == "PROCESSING" and elapsed < MAX_FILE_ACTIVE_WAIT_SECONDS:
        time.sleep(POLL_INTERVAL_SECONDS)
        elapsed += POLL_INTERVAL_SECONDS
        file_obj = client.files.get(name=file_obj.name)

    if file_obj.state.name == "FAILED":
        raise RuntimeError("Gemini no pudo procesar el archivo de audio.")
    if file_obj.state.name == "PROCESSING":
        raise TimeoutError("El audio tardó demasiado en procesarse. Intenta con un archivo más corto.")


def transcribe_audio(client: genai.Client, selected_audio) -> AudioResult:
    """Sube el audio a Gemini, espera a que esté listo y genera el análisis."""
    suffix = _guess_suffix(selected_audio)
    mime_type, _ = mimetypes.guess_type("audio" + suffix)
    tmp_path = None
    gemini_file = None

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
            tmp_file.write(selected_audio.getvalue())
            tmp_path = tmp_file.name

        gemini_file = client.files.upload(
            file=tmp_path,
            config=genai_types.UploadFileConfig(mime_type=mime_type) if mime_type else None,
        )
        _wait_until_active(client, gemini_file)

        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=[gemini_file, AUDIO_PROMPT],
        )
        return AudioResult(text=response.text or "")
    finally:
        # Limpieza: archivo temporal local y archivo remoto en Gemini
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)
        if gemini_file is not None:
            try:
                client.files.delete(name=gemini_file.name)
            except Exception:
                logger.warning("No se pudo borrar el archivo remoto %s", gemini_file.name)


# --------------------------------------------------------------------------
# UI
# --------------------------------------------------------------------------

def render_notes_tab(client: genai.Client) -> None:
    st.subheader("Corrección y Orden de Borradores")

    raw_notes = st.text_area(
        "Escribe rápido todo lo que necesites anotando en el teclado:",
        height=220,
        placeholder="Ejemplo: reunion hoy con pedro. se aprueba presupuesto. maria entrega informe el viernes...",
    )

    if st.button("✨ Limpiar y Estructurar Notas", key="btn_text"):
        if not raw_notes.strip():
            st.warning("Escribe algo en el borrador antes de procesar.")
        else:
            with st.spinner("Procesando y corrigiendo tus notas..."):
                try:
                    st.session_state["notes_result"] = clean_notes(client, raw_notes)
                except Exception as exc:
                    logger.exception("Error al procesar notas")
                    st.error(f"Error al conectar con la IA: {exc}")

    if st.session_state.get("notes_result"):
        st.success("¡Notas estructuradas con éxito!")
        st.markdown("---")
        st.markdown(st.session_state["notes_result"])
        st.download_button(
            label="📥 Descargar Acta (.txt)",
            data=st.session_state["notes_result"],
            file_name="acta_reunion.txt",
            mime="text/plain",
        )


def render_audio_tab(client: genai.Client) -> None:
    st.subheader("Transcripción y Resumen de Audio")

    audio_input = st.audio_input("Graba la conversación desde el micrófono:")
    uploaded_audio = st.file_uploader(
        "O sube un archivo de audio grabado:", type=["mp3", "wav", "m4a"]
    )

    selected_audio = audio_input or uploaded_audio

    if selected_audio:
        st.audio(selected_audio)
        if st.button("✨ Procesar Audio de la Reunión", key="btn_audio"):
            with st.spinner("Escuchando el audio y analizando el contenido real..."):
                try:
                    result = transcribe_audio(client, selected_audio)
                    st.session_state["audio_result"] = result.text
                except Exception as exc:
                    logger.exception("Error al procesar audio")
                    st.error(f"Error al procesar el audio: {exc}")

    if st.session_state.get("audio_result"):
        st.success("¡Análisis completado!")
        st.markdown("---")
        st.markdown(st.session_state["audio_result"])
        st.download_button(
            label="📥 Descargar Minuta (.txt)",
            data=st.session_state["audio_result"],
            file_name="minuta_audio.txt",
            mime="text/plain",
        )


def main() -> None:
    st.set_page_config(
        page_title="Mi Libreta Inteligente de Reuniones",
        page_icon="📝",
        layout="wide",
    )

    st.title("📝 Mi Libreta Inteligente de Reuniones")
    st.write("Escribe rápido o graba el audio. La app organizará y corregirá todo para tus reuniones.")

    api_key = get_api_key()
    if not api_key:
        st.info("👋 Ingresa tu API Key de Gemini en los Secrets de Streamlit o en la barra lateral.")
        st.stop()

    try:
        client = get_client(api_key)
    except Exception as exc:
        st.error(f"No se pudo inicializar el cliente de Gemini: {exc}")
        st.stop()

    tab1, tab2 = st.tabs(["⌨️ Escribir Notas en Borrador", "🎙️ Escuchar / Grabar Reunión"])

    with tab1:
        render_notes_tab(client)

    with tab2:
        render_audio_tab(client)


if __name__ == "__main__":
    main()
