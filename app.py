"""
AI English Tutor - Tu Profesor Personal con Streamlit y Gemini
--------------------------------------------------------------
Aplicación interactiva para practicar conversación, pronunciación en audio
y corrección gramatical en tiempo real.
"""

import mimetypes
import os
import tempfile
import streamlit as st
import google.genai as genai
from google.genai import types as genai_types

# --------------------------------------------------------------------------
# Configuración inicial
# --------------------------------------------------------------------------
st.set_page_config(
    page_title="AI English Tutor",
    page_icon="🎓",
    layout="wide",
)

MODEL_NAME = "gemini-2.5-flash"

def get_api_key() -> str | None:
    if hasattr(st, "secrets") and "GEMINI_API_KEY" in st.secrets:
        return st.secrets["GEMINI_API_KEY"]
    return st.session_state.get("custom_api_key")

api_key = get_api_key()

# --------------------------------------------------------------------------
# Barra Lateral - Configuración de Nivel y Tema
# --------------------------------------------------------------------------
with st.sidebar:
    st.title("🎓 AI English Tutor")
    st.caption("Práctica de inglés interactiva")

    if not api_key:
        st.warning("⚠️ Sin API Key detectada en Secrets.")
        custom_key = st.text_input("Ingresa tu Gemini API Key:", type="password")
        if custom_key:
            st.session_state["custom_api_key"] = custom_key
            st.rerun()
    else:
        st.success("✅ Gemini Conectado")

    st.markdown("---")
    st.subheader("⚙️ Configuración del Tutor")
    
    level = st.selectbox(
        "Nivel actual de inglés:",
        ["Beginner (A1-A2)", "Intermediate (B1-B2)", "Advanced (C1-C2)"],
        index=1
    )
    
    topic_interest = st.selectbox(
        "Tema de conversación preferido:",
        ["General & Daily Life", "Sports & Analytics", "Professional & Business", "Technology & Science"]
    )

    if st.button("🔄 Reiniciar Conversación"):
        st.session_state.messages = []
        st.rerun()

if not api_key:
    st.info("👋 Por favor configura tu `GEMINI_API_KEY` en los Secrets de Streamlit o en el menú lateral para empezar.")
    st.stop()

client = genai.Client(api_key=api_key)

# --------------------------------------------------------------------------
# Interfaz Principal
# --------------------------------------------------------------------------
st.title("🎓 Tu Tutor Personal de Inglés")
st.write("Practica tu fluidez escrita y hablada con retroalimentación instantánea sobre gramática y pronunciación.")

tab1, tab2, tab3 = st.tabs([
    "💬 Conversación Interactiva", 
    "🎙️ Práctica de Pronunciación (Audio)", 
    "📝 Corrector de Gramática y Estilo"
])

# --------------------------------------------------------------------------
# TAB 1: Chat de Conversación
# --------------------------------------------------------------------------
with tab1:
    st.subheader("💬 Interactive Conversation")
    st.write("Escribe en inglés. Tu tutor mantendrá la conversación y te corregirá amablemente si cometes algún error.")

    if "messages" not in st.session_state or not st.session_state.messages:
        initial_msg = f"Hello! I'm your English tutor. Let's talk about {topic_interest.lower()} or any topic you like. How are you doing today?"
        st.session_state.messages = [{"role": "model", "content": initial_msg}]

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if user_prompt := st.chat_input("Write your response in English..."):
        st.session_state.messages.append({"role": "user", "content": user_prompt})
        with st.chat_message("user"):
            st.markdown(user_prompt)

        system_instruction = f"""
        You are an encouraging, expert English tutor speaking with a student at {level} level.
        The user wants to practice English with a focus on {topic_interest}.

        Instructions for your response:
        1. Respond naturally in English to keep the conversation engaging.
        2. At the end of your response, add a section in Spanish labeled '💡 **Tutor Feedback**:'
           - If there were grammar, spelling, or vocabulary errors, point them out gently with corrections and a more natural alternative.
           - If there were no errors, compliment their fluency in 1 short sentence!
        """

        with st.chat_message("model"):
            with st.spinner("Your tutor is typing..."):
                try:
                    contents = [
                        {"role": m["role"], "parts": [{"text": m["content"]}]}
                        for m in st.session_state.messages
                    ]
                    response = client.models.generate_content(
                        model=MODEL_NAME,
                        contents=contents,
                        config=genai_types.GenerateContentConfig(
                            system_instruction=system_instruction
                        )
                    )
                    reply_text = response.text or "Could you please repeat that?"
                    st.markdown(reply_text)
                    st.session_state.messages.append({"role": "model", "content": reply_text})
                except Exception as e:
                    st.error(f"Error al conectar con la IA: {e}")

# --------------------------------------------------------------------------
# TAB 2: Evaluación por Audio
# --------------------------------------------------------------------------
with tab2:
    st.subheader("🎙️ Pronunciation & Speaking Practice")
    st.write("Graba un audio hablando en inglés para analizar tu pronunciación, entonación y vocabulario.")

    audio_input = st.audio_input("Graba tu voz desde el micrófono:")
    uploaded_audio = st.file_uploader("O sube un archivo de audio (MP3, WAV, M4A):", type=["mp3", "wav", "m4a"])

    selected_audio = audio_input or uploaded_audio

    if selected_audio:
        st.audio(selected_audio)
        if st.button("✨ Analizar mi Pronunciación", type="primary"):
            with st.spinner("Escuchando tu audio y analizando la pronunciación..."):
                suffix = ".wav" if not getattr(selected_audio, "name", None) else "." + selected_audio.name.rsplit(".", 1)[-1]
                mime_type, _ = mimetypes.guess_type("audio" + suffix)

                tmp_path = None
                gemini_file = None

                try:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
                        tmp_file.write(selected_audio.getvalue())
                        tmp_path = tmp_file.name

                    gemini_file = client.files.upload(
                        file=tmp_path,
                        config=genai_types.UploadFileConfig(mime_type=mime_type) if mime_type else None
                    )

                    audio_prompt = f"""
                    You are an expert English pronunciation and accent coach.
                    Listen to the student's audio ({level} level).

                    Provide clear, constructive feedback in Spanish structured as follows:
                    1. 📝 **Transcripción exacta:** What you heard the student say in English.
                    2. 🎯 **Feedback de Pronunciación:** Point out mispronounced words, silent letters missed, or intonation issues. Provide phonetic examples (IPA or easy phonetics).
                    3. 💡 **Corrección Gramatical:** Fix any grammar errors in what was spoken.
                    4. 🚀 **Versión Natural (Native Level):** How a native speaker would express the same idea naturally.
                    """

                    response = client.models.generate_content(
                        model=MODEL_NAME,
                        contents=[gemini_file, audio_prompt]
                    )

                    st.markdown("---")
                    st.markdown(response.text)

                except Exception as e:
                    st.error(f"Error procesando el audio: {e}")
                finally:
                    if tmp_path and os.path.exists(tmp_path):
                        os.remove(tmp_path)
                    if gemini_file is not None:
                        try:
                            client.files.delete(name=gemini_file.name)
                        except Exception:
                            pass

# --------------------------------------------------------------------------
# TAB 3: Corrector de Gramática y Estilo
# --------------------------------------------------------------------------
with tab3:
    st.subheader("📝 Text Proofreader & Style Elevator")
    st.write("Pega un texto en inglés que hayas escrito para revisar su ortografía, gramática y nivel de vocabulario.")

    user_text = st.text_area(
        "Pega tu texto en inglés aquí:", 
        height=180, 
        placeholder="Ejemplo: Yesterday I go to the field and watch a very good game with my friends..."
    )

    target_style = st.selectbox(
        "Estilo deseado:", 
        ["Natural Conversational", "Professional & Executive", "Academic & Formal", "Sports Commentary / Media"]
    )

    if st.button("✨ Corregir y Elevar Texto"):
        if not user_text.strip():
            st.warning("Escribe o pega algún texto antes de procesar.")
        else:
            with st.spinner("Analizando texto..."):
                proofread_prompt = f"""
                You are an expert English editor and proofreader.
                Analyze the following text written by a student ({level} level) who wants a '{target_style}' style.

                Provide feedback in Spanish using this structure:
                - 🎯 **Texto Corregido:** Complete corrected version.
                - 🔍 **Análisis de Errores:** List the specific grammar/spelling errors found and explain why they were wrong.
                - ✨ **Versión Estilo {target_style}:** Re-write the text with native-level vocabulary and sentence structures fitting the requested style.
                - 📚 **Vocabulario Clave:** 2-3 useful idioms or advanced words related to the text topic with Spanish translations.

                Original Text:
                \"\"\"{user_text}\"\"\"
                """
                try:
                    res = client.models.generate_content(model=MODEL_NAME, contents=proofread_prompt)
                    st.markdown("---")
                    st.markdown(res.text)
                except Exception as e:
                    st.error(f"Error al procesar el texto: {e}")
