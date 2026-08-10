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

# Configuración de API Key
with st.sidebar:
    st.header("⚙️ Configuración")
    api_key = st.text_input("Ingresa tu Gemini API Key:", type="password")
    st.markdown("[Consigue tu API Key GRATIS aquí](https://aistudio.google.com/)")

if not api_key:
    st.info("👋 Para empezar, ingresa tu API Key gratuita de Gemini en la barra lateral.")
    st.stop()

# Cliente de Gemini
client = genai.Client(api_key=api_key)

tab1, tab2 = st.tabs(["⌨️ Escribir Notas en Borrador", "🎙️ Escuchar / Grabar Reunión"])

# --- TAB 1: NOTAS ESCRITAS ---
with tab1:
    st.subheader("Corrección y Orden de Borradores")
    
    raw_notes = st.text_area(
        "Escribe rápido todo lo que necesites anotando en el teclado:",
        height=220,
        placeholder="Ejemplo: reunios hoy con pedro. se aprueba presupuesto de marketing. maria entrega informe viernes. proxima sesion el martes 10am..."
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

# --- TAB 2: GRABACIÓN DE AUDIO ---
with tab2:
    st.subheader("Transcripción y Resumen de Audio")
    
    audio_input = st.audio_input("Graba la conversación desde el micrófono:")
    uploaded_audio = st.file_uploader("O sube un archivo de audio grabado:", type=["mp3", "wav", "m4a"])

    selected_audio = audio_input or uploaded_audio

    if selected_audio:
        st.audio(selected_audio)
        if st.button("✨ Procesar Audio de la Reunión", key="btn_audio"):
            with st.spinner("Escuchando el audio y generando la minuta..."):
                try:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
                        tmp_file.write(selected_audio.read())
                        tmp_path = tmp_file.name

                    uploaded_file = client.files.upload(file=tmp_path)

                    prompt = """
                    Escucha esta reunión y genera un informe profesional estructurado:
                    1. Resumen ejecutivo de los temas hablados.
                    2. Compromisos tomados.
                    3. Proximos pasos y tareas pendientes.
                    """

                    response = client.models.generate_content(
                        model='gemini-2.5-flash',
                        contents=[uploaded_file, prompt]
                    )

                    st.success("¡Audio procesado!")
                    st.markdown("---")
                    st.markdown(response.text)

                    st.download_button(
                        label="📥 Descargar Minuta de Audio (.txt)",
                        data=response.text,
                        file_name="minuta_audio.txt",
                        mime="text/plain"
                    )

                    os.remove(tmp_path)
                except Exception as e:
                    st.error(f"Error al procesar el audio: {e}")
