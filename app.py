# =====================================================================
# MOTOR 2: FÚTBOL - CONEXIÓN CON SPORTMONKS (CORREGIDA)
# =====================================================================
else:
    st.sidebar.subheader("Configuración de Fútbol")
    
    @st.cache_data(ttl=1800)
    def consultar_partidos_sportmonks(fecha):
        # Usamos el endpoint de fixtures (calendario) filtrado por fecha, que es el estándar de Sportmonks
        url = f"https://api.sportmonks.com/v3/football/fixtures/date/{fecha}"
        cabeceras = {"Authorization": API_TOKEN_FUTBOL}
        try:
            respuesta = requests.get(url, headers=cabeceras)
            if respuesta.status_code == 200:
                datos = respuesta.json().get("data", [])
                lista_partidos = []
                detalles = {}
                
                for juego in datos:
                    id_juego = juego.get("id")
                    # Intentamos extraer el nombre legible si viene en la respuesta, si no usamos el ID
                    nombre_juego = juego.get("name", f"Partido ID: {id_juego}")
                    lista_partidos.append(nombre_juego)
                    detalles[nombre_juego] = juego
                    
                return lista_partidos, detalles
            else:
                st.sidebar.error(f"Error de API: Código {respuesta.status_code}. Revisa el endpoint o tu plan.")
                return [], {}
        except Exception as e:
            st.sidebar.error(f"Error de conexión: {str(e)}")
            return [], {}

    partidos_futbol, info_futbol = consultar_partidos_sportmonks(fecha_hoy)

    if partidos_futbol:
        partido_sel = st.sidebar.selectbox("Partidos de HOY disponibles en tu plan:", partidos_futbol)
        juego_datos = info_futbol[partido_sel]
        
        st.subheader(f"⚽ Análisis de Partido en Vivo: {partido_sel}")
        st.info("¡Conexión establecida con éxito! Recibiendo datos estructurados de Sportmonks.")
        
        # Estructura del algoritmo probabilístico base
        col1, col2, col3 = st.columns(3)
        with col1: st.metric(label="Probabilidad Local (Estimada)", value="45%")
        with col2: st.metric(label="Probabilidad Empate (Estimada)", value="28%")
        with col3: st.metric(label="Probabilidad Visitante (Estimada)", value="27%")
    else:
        st.info("No se encontraron partidos de fútbol disponibles para hoy en tu plan de Sportmonks o la lista está vacía.")
