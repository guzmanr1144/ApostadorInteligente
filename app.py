import streamlit as st

st.title("¡Mi primera aplicación en la nube! 🚀")

st.write("Esta app corre directamente desde GitHub.")

# Un pequeño saludo interactivo
nombre = st.text_input("Escribe tu nombre:")
if nombre:
    st.write(f"¡Hola, {nombre}! Qué bueno ver que la app funciona.")
