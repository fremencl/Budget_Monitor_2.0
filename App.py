import streamlit as st
from PIL import Image
from pathlib import Path

def get_project_root() -> Path:
    """Returns the project root folder."""
    return Path(__file__).parent

def load_image(image_name: str) -> Image:
    """Loads an image from the specified path."""
    image_path = Path(get_project_root()) / f"assets/{image_name}"
    print(f"Trying to load image from: {image_path}")  # Agrega esto para depurar
    return Image.open(image_path)

# Configuración de la aplicación
st.set_page_config(
    page_title="Gerencia Gestión de Activos",
    page_icon=":dollar:",
    initial_sidebar_state="expanded",
)

# Crear tres columnas y mostrar la imagen en la columna central
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    st.image(load_image("Logo.jpg"), width=150)

# Títulos y subtítulos
st.write("### MONITOR DE GESTION PRESUPUESTARIA :chart_with_upwards_trend:")
st.write("#### GERENCIA GESTION DE ACTIVOS")

st.markdown("---")

# Mensaje en la barra lateral
st.sidebar.success("Selecciona un modelo de análisis de arriba")

# Contenido introductorio y descripción de la aplicación
st.write("")
st.markdown(
    """##### Exploraremos tendencias y ratios relacionados con el perfil del Gasto de Mantenimiento de nuestra Gerencia

    
En la actual etapa de desarrollo de esta aplicación, están disponibles 2 módulos: **Gastos** y **Ordenes**.

- **Modelo de Gastos**: Te permitirá comparar gasto real y presupuesto bajo diferentes perspectivas.
- **Modelo de Órdenes**: Te permitirá relacionar órdenes y sus respectivos gastos, así como una primera aproximación a KPIs asociados.

En ambos módulos cuentas con filtros dinámicos para poder ajustar las vistas de las herramientas de análisis y desagregar la información por:
- Año
- Proceso (Producción, Distribución, Recolección o Depuración)
- Tipo de gasto (Materiales o Servicios)

:moneybag::moneybag::moneybag::moneybag::moneybag::moneybag::moneybag::moneybag::moneybag::moneybag::moneybag::moneybag::moneybag::moneybag::moneybag::moneybag::moneybag:
    """
)
