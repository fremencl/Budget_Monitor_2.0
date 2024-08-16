import streamlit as st

def app():
    # Título de la página principal
    st.title("Bienvenido a la Aplicación de Gestión Presupuestaria")

    # Subtítulo o introducción
    st.markdown("""
    Esta aplicación te permite monitorear y analizar el gasto frente al presupuesto en diferentes áreas y procesos. 
    Utiliza el menú a la izquierda para navegar entre las diferentes secciones.
    """)

    # Resumen general
    st.markdown("### Resumen General")
    col1, col2, col3 = st.columns(3)
    col1.metric("Gasto Total Actual", "$1.2M")
    col2.metric("Presupuesto Total", "$2M")
    col3.metric("Desviación", "-$0.8M")

    # Botones de navegación rápida
    st.markdown("### Navegación Rapida")
    st.button("Ir a Analisis de Gastos")
    st.button("Ir a Analisis de Ordenes")
