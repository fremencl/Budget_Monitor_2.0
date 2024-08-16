import streamlit as st

st.set_page_config(
    page_title="Gerencia Gestion de Activos",
    page_icon=":dollar:",
    initial_sidebar_state="expanded",
)

st.write("### MONITOR DE GESTION PRESUPUESTARIA :chart_with_upwards_trend:")
st.write("#### GERENCIA GESTION DE ACTIVOS")

st.sidebar.success("Selecciona un modelo de analisis de arriba.")

st.markdown(
    """##### Exploraremos tendencias y ratios relacionados con el perfil del Gasto de Mantenimiento de nuestra Gerencia
    
En la actual etapa de desarrollo de esta aplicacion, estan disponibles 2 modulos: Gastos y Ordenes

El Modelo de Gastos te permitirá comparar gasto real y presupuesto bajo diferentes perspectivas.

El Modelo de Ordenes te permitirá relacionar ordenes y sus respectivos gastos, así como una primera aproximacion a KPI´s asociados.

En ambos modulos cuentas con filtros dinámicos para poder ajustar las vistas de las herramientas de análisis y desagregar la informacion por:
Año
Proceso (Producción, Distribución, Recolección o Depuración)
Tipo de gasto (Materiales o Servicios)

:moneybag::moneybag::moneybag::moneybag::moneybag::moneybag::moneybag::moneybag::moneybag::moneybag::moneybag::moneybag::moneybag::moneybag::moneybag::moneybag::moneybag:

"""
)
