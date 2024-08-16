import streamlit as st
from PIL import Image
from pathlib import Path

def get_project_root() -> Path:
    """Returns the project root folder."""
    return Path(__file__).parent

def load_image(image_name: str) -> Image:
    """Loads an image from the specified path.

    Parameters
    ----------
    image_name : str
        Local path of the image.

    Returns
    -------
    Image
        Image to be displayed.
    """
    return Image.open(Path(get_project_root()) / f"assets/{image_name}")

# Configuración de la aplicación
st.set_page_config(
    page_title="Gerencia Gestión de Activos",
    page_icon=":dollar:",
    initial_sidebar_state="expanded",
)

# Mostrar el logo de la compañía en el área principal
st.image(load_image("Logo.jpg"), width=300)  # Ajusta el 'width' según sea necesario

# Títulos y subtítulos
st.write("### MONITOR DE GESTIÓN PRESUPUESTARIA :chart_with_upwards_trend:")
st.write("#### GERENCIA GESTIÓN DE ACTIVOS")

# Mensaje en la barra lateral
st.sidebar.success("Selecciona un modelo de análisis de arriba.")

# Contenido introductorio y descripción de la aplicación
st.markdown(
    """##### Exploraremos tendencias y ratios relacionados con el perfil del Gasto de Mantenimiento de nuestra Gerencia
    
En la actual etapa de desarrollo de esta aplicación, están disponibles 2 módulos: **Gastos** y **Órdenes**.

- **Modelo de Gastos**: Te permitirá comparar gasto real y presupuesto bajo diferentes perspectivas.
- **Modelo de Órdenes**: Te permitirá relacionar órdenes y sus respectivos gastos, así como una primera aproximación a KPIs asociados.

En ambos módulos cuentas con filtros dinámicos para poder ajustar las vistas de las herramientas de análisis y desagregar la información por:
- Año
- Proceso (Producción, Distribución, Recolección o Depuración)
- Tipo de gasto (Materiales o Servicios)

:moneybag::moneybag::moneybag::moneybag::moneybag::moneybag::moneybag::moneybag::moneybag::moneybag::moneybag::moneybag::moneybag::moneybag::moneybag::moneybag::moneybag:
    """
)
