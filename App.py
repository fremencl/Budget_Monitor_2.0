import streamlit as st
from streamlit_option_menu import option_menu

# Configuración de la aplicación
st.set_page_config(page_title="Aplicación Multipágina", page_icon=":bar_chart:", layout="wide")

# Creación del menú de navegación
with st.sidebar:
    selected = option_menu(
        menu_title="Menú Principal",
        options=["Página Principal", "Analisis de Gastos", "Analisis de Ordenes"],
        icons=["house", "bar-chart", "graph-up"],
        menu_icon="cast",
        default_index=0,
    )

# Redirección a las páginas
if selected == "Página Principal":
    import pages.Home as Home
    Home.app()

elif selected == "Analisis de Gastos":
    import pages.Gastos as Gastos
    Gastos.app()

elif selected == "Analisis de Ordenes":
    import pages.Ordenes as Ordenes
    Ordenes.app()
