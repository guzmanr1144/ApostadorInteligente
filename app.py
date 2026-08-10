# --- TAB 2: GRABACIÓN DE AUDIO ---
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
                       - 📝 **Transcripción o Resumen Fiel:** Describe exactamente qué se habló.
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
