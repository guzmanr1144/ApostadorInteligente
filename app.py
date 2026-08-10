import streamlit as st
import google.genai as genai
import tempfile
import os

st.set_page_config(
    page_title="Mi Libreta Inteligente de Reuniones",
    page_icon="📝",
    layout="wide"
)

st.title("📝 Mi Libreta Inteligente de Reuniones")
st.write("Escribe rápido o graba el audio. La app organizará y corregirá todo para tus reuniones.")

# 1. Intentar obtener la API Key desde los Secrets de Streamlit Cloud
api_key = None
if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]

# 2. Si no está en Secrets, pedirla en la barra lateral
if not api_key:
    with st.sidebar:
        st.header("⚙️ Configuración")
        api_key = st.text_input("Ingresa tu Gemini API Key:", type="password")

if not api_key:
    st.info("👋 Ingresa tu API Key de Gemini en los Secrets de Streamlit o en la barra lateral.")
    st.stop()

# Inicializar el cliente de Gemini
client = genai.Client(api_key=api_key)

tab1, tab2 = st.tabs(["⌨️ Escribir Notas en Borrador", "🎙️ Escuchar / Grabar Reunión"])

# --- TAB 1: NOTAS ESCRITAS EN TECLADO ---
with tab1:
    st.subheader("Corrección y Orden de Borradores")
    
    raw_notes = st.text_area(
        "Escribe rápido todo lo que necesites anotando en el teclado:",
        height=220,
        placeholder="Ejemplo: reunion hoy con pedro. se aprueba presupuesto. maria entrega informe el viernes..."
    )

    if st.button("✨ Limpiar y Estructurar Notas", key="btn_text"):
        if not raw_notes.strip():
            st.warning("Escribe algo en el borrador antes de procesar.")
        else:
            with st.spinner("Procesando y corrigiendo tus notas..."):
                try:
                    prompt = f"""
                    Eres un asistente ejecutivo. Toma estas notas rápidas tomadas a toda prisa durante una reunión y transfórmalas en un reporte pulido, limpio de errores ortográficos y bien estructurado:

                    Notas desordenadas:
                    \"\"\"
                    {raw_notes}
                    \"\"\"

                    Estructura el resultado con:
                    - 📌 **Resumen General**
                    - 💡 **Puntos Clave Discutidos**
                    - ✅ **Acuerdos Tomados**
                    - 📋 **Tareas y Responsables**
                    """

                    response = client.models.generate_content(
                        model='gemini-2.5-flash',
                        contents=prompt
                    )

                    st.success("¡Notas estructuradas con éxito!")
                    st.markdown("---")
                    st.markdown(response.text)

                    st.download_button(
                        label="📥 Descargar Acta (.txt)",
                        data=response.text,
                        file_name="acta_reunion.txt",
                        mime="text/plain"
                    )
                except Exception as e:
                    st.error(f"Error al conectar con la IA: {e}")

# --- TAB 2: GRABACIÓN DE AUDIO (CON PROTECCIÓN ANTI-INVENTOS) ---
with tab2:
    st.subheader("Transcripción y Resumen de Audio")
    
    audio_input = st.audio_input("Graba la conversación desde el micrófono:")
    uploaded_audio = st.file_uploader("O sube un archivo de audio grabado:", type=["mp3", "wav", "m4a"])

    selected_audio = audio_input or uploaded_audio

    if selected_audio:
        st.audio(selected_audio)
        if st.button("✨ Procesar Audio de la Reunión", key="btn_audio"):
            with st.spinner("Escuchando el audio y analizando el contenido real..."):
                try:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
                        tmp_file.write(selected_audio.read())
                        tmp_path = tmp_file.name

                    uploaded_file = client.files.upload(file=tmp_path)

                    # Prompt estricto anti-alucinación
                    prompt = """
                    REGLA DE ORO: Escucha únicamente el audio adjunto. Queda estrictamente PROHIBIDO inventar nombres, temas, acuerdos o detalles que no se escuchen textualmente en la grabación.

                    Instrucciones:
                    1. Si el audio contiene silencio, ruido, música de fondo o no hay voz humana legible, responde ÚNICAMENTE: "⚠️ El audio no contiene una conversación clara o está en silencio."
                    2. Si el audio contiene voz legible, realiza lo siguiente basándote 100% en lo que escuchaste:
                       - 📝 **Resumen Fiel:** Describe exactamente de qué se habló.
                       - 💡 **Puntos Clave:** Detalla solo los hechos mencionados.
                       - ✅ **Acuerdos y Tareas:** Lista únicamente lo asignado en el audio (si no se mencionan nombres ni tareas, indica "No se especificaron acuerdos").
                    """

                    response = client.models.generate_content(
                        model='gemini-2.5-flash',
                        contents=[uploaded_file, prompt]
                    )

                    st.success("¡Análisis completado!")
                    st.markdown("---")
                    st.markdown(response.text)

                    st.download_button(
                        label="📥 Descargar Minuta (.txt)",
                        data=response.text,
                        file_name="minuta_audio.txt",
                        mime="text/plain"
                    )

                    os.remove(tmp_path)
                except Exception as e:
                    st.error(f"Error al procesar el audio: {e}")
