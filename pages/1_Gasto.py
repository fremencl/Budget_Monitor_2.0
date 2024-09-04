import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go 
import io

# Título de la aplicación
st.markdown("<h1 style='text-align: center; color: black; font-size: 24px;'>MONITOR GESTIÓN PRESUPUESTARIA</h1>", unsafe_allow_html=True)
st.markdown("<h2 style='text-align: center; color: black; font-size: 24px;'>ANALISIS AGREGADO: GASTO Y PRESUPUESTO</h2>", unsafe_allow_html=True)

# CSS para ajustar el ancho del sidebar
st.markdown(
    """
    <style>
    /* Ajustar el ancho del sidebar */
    [data-testid="stSidebar"] {
        width: 300px;
    }
    /* Ajustar el contenido del sidebar */
    [data-testid="stSidebar"] > div:first-child {
        width: 300px;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Definimos las URLs de los archivos de referencia
DATA0_URL = 'https://streamlitmaps.s3.amazonaws.com/Data_0824.csv'
BUDGET_URL = 'https://streamlitmaps.s3.amazonaws.com/Base_Presupuesto_3.csv'
ORDERS_URL = 'https://streamlitmaps.s3.amazonaws.com/Base_Ordenes_0824.csv'
BASE_UTEC_URL = 'https://streamlitmaps.s3.amazonaws.com/Base_UTEC_BudgetVersion.csv'
BASE_CECO_URL = 'https://streamlitmaps.s3.amazonaws.com/Base_Ceco_3.csv'

# Función para cargar el archivo de referencia
@st.cache_data
def load_data(url):
    data = pd.read_csv(url, encoding='ISO-8859-1', sep=';')
    if 'Valor/mon.inf.' in data.columns:
        data['Valor/mon.inf.'] = pd.to_numeric(data['Valor/mon.inf.'].str.replace(',', ''), errors='coerce').fillna(0)
    return data

# Cargar los datos
data0 = load_data(DATA0_URL)
data0['id'] = range(1, len(data0) + 1)
budget_data = load_data(BUDGET_URL)
orders_data = load_data(ORDERS_URL)
base_utec_data = load_data(BASE_UTEC_URL)
base_ceco_data = load_data(BASE_CECO_URL)

# Verificar que las columnas necesarias están presentes en los DataFrames cargados
assert 'Orden' in orders_data.columns, "La columna 'Orden' no está presente en orders_data"
assert 'Utec' in orders_data.columns, "La columna 'Utec' no está presente en orders_data"
assert 'Utec' in base_utec_data.columns, "La columna 'Utec' no está presente en base_utec_data"
assert 'Proceso' in base_utec_data.columns, "La columna 'Proceso' no está presente en base_utec_data"
assert 'Recinto' in base_utec_data.columns, "La columna 'Recinto' no está presente en base_utec_data"
assert 'Ceco' in base_ceco_data.columns, "La columna 'Ceco' no está presente en base_ceco_data"
assert 'Proceso' in base_ceco_data.columns, "La columna 'Proceso' no está presente en base_ceco_data"
assert 'Recinto' in base_ceco_data.columns, "La columna 'Recinto' no está presente en base_ceco_data"

# Asegurarse de que 'Ejercicio' y 'Período' son de tipo string
data0['Ejercicio'] = data0['Ejercicio'].astype(str)
data0['Período'] = data0['Período'].astype(str)
budget_data['Año'] = budget_data['Año'].astype(str)
budget_data['Mes'] = budget_data['Mes'].astype(str)

# Agregar nuevas columnas a data0
data0['Utec'] = None
data0['Proceso'] = None
data0['Recinto'] = None

# Convertir la columna 'Período' y 'Valor/mon.inf.' a tipo numérico
data0['Período'] = pd.to_numeric(data0['Período'], errors='coerce')
data0['Valor/mon.inf.'] = pd.to_numeric(data0['Valor/mon.inf.'], errors='coerce')

# Primer mapeo: Asignar Utec utilizando ORDERS_URL
if 'Orden partner' in data0.columns and 'Orden' in orders_data.columns:
    data0 = data0.merge(orders_data[['Orden', 'Utec']], how='left', left_on='Orden partner', right_on='Orden', suffixes=('_original', '_merged'))
    if 'Utec_merged' in data0.columns:
        data0['Utec'] = data0['Utec_merged']
        data0.drop(columns=['Utec_original', 'Utec_merged'], inplace=True)
    else:
        st.error("No se encontraron las columnas necesarias para el primer mapeo ('Utec')")
else:
    st.error("No se encontraron las columnas necesarias para el primer mapeo")

# Segundo mapeo: Asignar Proceso utilizando Base_UTEC_BudgetVersion.csv
if 'Utec' in data0.columns:
    data0 = data0.merge(base_utec_data[['Utec', 'Proceso']], how='left', on='Utec', suffixes=('_original', '_merged'))
    if 'Proceso_merged' in data0.columns:
        data0['Proceso'] = data0['Proceso_merged']
        data0.drop(columns=['Proceso_original', 'Proceso_merged'], inplace=True)
    else:
        st.error("No se encontraron las columnas necesarias para el segundo mapeo")
else:
    st.error("No se encontraron las columnas necesarias para el segundo mapeo")

# Asignar Recinto utilizando Base_UTEC_BudgetVersion.csv
if 'Utec' in data0.columns:
    data0 = data0.merge(base_utec_data[['Utec', 'Recinto']], how='left', on='Utec', suffixes=('_original', '_merged'))
    if 'Recinto_merged' in data0.columns:
        data0['Recinto'] = data0['Recinto_merged']
        data0.drop(columns=['Recinto_original', 'Recinto_merged'], inplace=True)
    else:
        st.error("No se encontraron las columnas necesarias para el tercer mapeo")

# Convertir temporalmente 'Período' a tipo numérico para eliminar pares opuestos
data0['Período'] = pd.to_numeric(data0['Período'], errors='coerce')

# Función para eliminar filas con valores específicos en "Grupo_Ceco"
def eliminar_filas_grupo_ceco(data):
    valores_excluir = ["Abastecimiento y contratos", "Finanzas", "Servicios generales"]
    return data[~data['Grupo_Ceco'].isin(valores_excluir)]

# Función para identificar y eliminar pares de valores opuestos
def eliminar_pares_opuestos(data):
    filtered_df = pd.DataFrame()
    removed_df = pd.DataFrame()
    groups = data.groupby(['Clase de coste', 'Centro de coste'])
    
    for name, group in groups:
        seen_values = {}
        rows_to_remove = set()
        
        # Ordenar el grupo por 'Período' de forma ascendente para procesar en orden temporal
        group = group.sort_values(by='Período')
        
        for index, row in group.iterrows():
            value = row['Valor/mon.inf.']
            period = row['Período']
            
            if value < 0:
                # Buscar coincidencia en el mismo período
                if (period, -value) in seen_values:
                    opposite_index = seen_values[(period, -value)]
                    rows_to_remove.add(index)
                    rows_to_remove.add(opposite_index)
                    del seen_values[(period, -value)]
                else:
                    # Buscar coincidencia en períodos anteriores
                    for past_period in range(period - 1, 0, -1):
                        if (past_period, -value) in seen_values:
                            opposite_index = seen_values[(past_period, -value)]
                            rows_to_remove.add(index)
                            rows_to_remove.add(opposite_index)
                            del seen_values[(past_period, -value)]
                            break
                    else:
                        # No se encontró coincidencia, mantener el valor negativo
                        seen_values[(period, value)] = index
            else:
                seen_values[(period, value)] = index
        
        # Convertir el set a una lista para indexar
        rows_to_remove_list = list(rows_to_remove)
        
        # Eliminar las filas identificadas y almacenar en removed_df
        group_filtered = group.drop(rows_to_remove_list)
        removed_rows = group.loc[rows_to_remove_list]
        removed_df = pd.concat([removed_df, removed_rows])
        filtered_df = pd.concat([filtered_df, group_filtered])
    
    return filtered_df, removed_df

# Asegurarse de que data0 es un DataFrame
if isinstance(data0, pd.DataFrame):
    # Convertir temporalmente 'Período' a tipo numérico para eliminar pares opuestos
    data0['Período'] = pd.to_numeric(data0['Período'], errors='coerce')
    
    # Ejecutar `eliminar_pares_opuestos`
    data0, removed_data = eliminar_pares_opuestos(data0)  # Capturar ambos DataFrames
    
    # Convertir 'Período' de vuelta a cadena si es necesario
    data0['Período'] = data0['Período'].astype(str)
else:
    st.error("data0 no es un DataFrame")

# Procesamiento de data0
if isinstance(data0, pd.DataFrame):
    data0 = eliminar_filas_grupo_ceco(data0)
else:
    st.error("data0 no es un DataFrame antes de eliminar filas con valores específicos en 'Grupo_Ceco'")

# Filtrar filas sin Proceso y Recinto completos
data0_incomplete = data0[(data0['Proceso'].isna()) & (data0['Recinto'].isna())].copy()

# Convertir columnas a string
data0_incomplete['Centro de coste'] = data0_incomplete['Centro de coste'].astype(str)
base_ceco_data['Ceco'] = base_ceco_data['Ceco'].astype(str)
base_ceco_data['Recinto'] = base_ceco_data['Recinto'].astype(str)
base_ceco_data['Proceso'] = base_ceco_data['Proceso'].astype(str)

# Verificar si data0 es un DataFrame
if not isinstance(data0_incomplete, pd.DataFrame):
    st.error("data0_incomplete no es un DataFrame después del mapeo ceco")

# Mapeo de Proceso utilizando Base_Ceco_2.csv
if 'Centro de coste' in data0_incomplete.columns:
    data0_incomplete = data0_incomplete.merge(base_ceco_data[['Ceco', 'Proceso']], how='left', left_on='Centro de coste', right_on='Ceco')
    if 'Proceso_y' in data0_incomplete.columns:
        data0_incomplete['Proceso'] = data0_incomplete['Proceso_y']
        data0_incomplete.drop(columns=['Proceso_y', 'Proceso_x', 'Ceco'], inplace=True)
else:
    st.error("No se encontraron las columnas necesarias para el mapeo de Proceso")

# Mapeo de Recinto utilizando Base_Ceco_2.csv
if 'Centro de coste' in data0_incomplete.columns:
    data0_incomplete = data0_incomplete.merge(base_ceco_data[['Ceco', 'Recinto']], how='left', left_on='Centro de coste', right_on='Ceco')
    if 'Recinto_y' in data0_incomplete.columns:
        data0_incomplete['Recinto'] = data0_incomplete['Recinto_y']
        data0_incomplete.drop(columns=['Recinto_y', 'Recinto_x', 'Ceco'], inplace=True)
else:
    st.error("No se encontraron las columnas necesarias para el mapeo de Recinto")

# Limpieza y normalización de los valores antes del merge
data0['Centro de coste'] = data0['Centro de coste'].str.strip().str.upper()
data0_incomplete['Centro de coste'] = data0_incomplete['Centro de coste'].str.strip().str.upper()

combined_data = data0.merge(
    data0_incomplete[['Centro de coste', 'Proceso', 'Recinto', 'id']],
    on=['Centro de coste', 'id'],
    how='left',
    suffixes=('', '_incomplete')
)

# Actualizar los valores de 'Proceso' y 'Recinto' en data0
combined_data['Proceso'] = combined_data['Proceso'].combine_first(combined_data['Proceso_incomplete'])
combined_data['Recinto'] = combined_data['Recinto'].combine_first(combined_data['Recinto_incomplete'])

combined_data.drop(columns=['Proceso_incomplete', 'Recinto_incomplete'], inplace=True)

# Asignar el DataFrame resultante a data0
data0 = combined_data

# Convertir todos los valores en la columna 'Proceso' a cadenas para evitar el error de ordenación
data0['Proceso'] = data0['Proceso'].astype(str)
data0['Recinto'] = data0['Recinto'].astype(str)

# Paso 1: Calcular el gasto total mensual por proceso, excluyendo "Overhead"
gasto_mensual_proceso = data0[data0['Proceso'] != 'Overhead'].groupby(['Ejercicio', 'Período', 'Proceso'])['Valor/mon.inf.'].sum().reset_index()

# Paso 2: Calcular el gasto total mensual excluyendo "Overhead"
gasto_mensual_total_sin_overhead = gasto_mensual_proceso.groupby(['Ejercicio', 'Período'])['Valor/mon.inf.'].sum().reset_index()
gasto_mensual_total_sin_overhead = gasto_mensual_total_sin_overhead.rename(columns={'Valor/mon.inf.': 'Total_sin_overhead'})

# Paso 3: Calcular las proporciones de cada proceso con respecto al gasto total mensual excluyendo "Overhead"
gasto_mensual_proceso = gasto_mensual_proceso.merge(gasto_mensual_total_sin_overhead, on=['Ejercicio', 'Período'])
gasto_mensual_proceso['Proporción'] = gasto_mensual_proceso['Valor/mon.inf.'] / gasto_mensual_proceso['Total_sin_overhead']

# Paso 4: Filtrar solo los datos de "Overhead"
gasto_overhead = data0[data0['Proceso'] == 'Overhead'].groupby(['Ejercicio', 'Período'])['Valor/mon.inf.'].sum().reset_index()

# Paso 5: Crear nuevas filas para cada proceso con el monto redistribuido de "Overhead"
filas_nuevas = []

for _, overhead_row in gasto_overhead.iterrows():
    ejercicio = overhead_row['Ejercicio']
    periodo = overhead_row['Período']
    overhead_valor = overhead_row['Valor/mon.inf.']
    
    # Obtener las proporciones de los otros procesos en el mismo período
    proporciones_procesos = gasto_mensual_proceso[(gasto_mensual_proceso['Ejercicio'] == ejercicio) & 
                                                  (gasto_mensual_proceso['Período'] == periodo)]
    
    for _, proc_row in proporciones_procesos.iterrows():
        # 50% a Materiales
        nueva_fila_materiales = {
            'Ejercicio': ejercicio,
            'Período': periodo,
            'Proceso': proc_row['Proceso'],
            'Valor/mon.inf.': overhead_valor * proc_row['Proporción'] * 0.5,
            'Familia_Cuenta': 'Materiales'
        }
        filas_nuevas.append(nueva_fila_materiales)
        
        # 50% a Servicios
        nueva_fila_servicios = {
            'Ejercicio': ejercicio,
            'Período': periodo,
            'Proceso': proc_row['Proceso'],
            'Valor/mon.inf.': overhead_valor * proc_row['Proporción'] * 0.5,
            'Familia_Cuenta': 'Servicios'
        }
        filas_nuevas.append(nueva_fila_servicios)

# Convertir la lista de nuevas filas a un DataFrame
filas_nuevas_df = pd.DataFrame(filas_nuevas)

# Paso 6: Agregar las nuevas filas al DataFrame original
data0 = pd.concat([data0, filas_nuevas_df], ignore_index=True)

# Paso 7: Eliminar las filas correspondientes a "Overhead"
data0 = data0[data0['Proceso'] != 'Overhead']

# Ajuste: Convertir 'Ejercicio' y 'Período' a string nuevamente
data0['Ejercicio'] = data0['Ejercicio'].astype(str)
data0['Período'] = data0['Período'].astype(str)

# Convertir la columna 'Familia_Cuenta' y 'Recinto' a tipo string
data0['Familia_Cuenta'] = data0['Familia_Cuenta'].astype(str)
data0['Recinto'] = data0['Recinto'].astype(str)

# FILTROS en la barra lateral
st.sidebar.markdown("### Filtros")
selected_years = st.sidebar.multiselect("Selecciona el año", data0['Ejercicio'].unique().tolist(), default=['2024'])
selected_procesos = st.sidebar.multiselect("Selecciona el proceso", data0['Proceso'].unique().tolist(), default=data0['Proceso'].unique().tolist())
selected_familias = st.sidebar.multiselect("Selecciona la Familia_Cuenta", ['Materiales', 'Servicios'], default=['Materiales', 'Servicios'])

# Verificar si todos los procesos están seleccionados
all_processes_selected = set(selected_procesos) == set(data0['Proceso'].unique().tolist())

# Aplicar los filtros después de calcular las sumatorias
filtered_data = data0[
    (data0['Ejercicio'].isin(selected_years)) & 
    (data0['Proceso'].isin(selected_procesos)) & 
    (data0['Familia_Cuenta'].isin(selected_familias)) &
    (~data0['Familia_Cuenta'].isna())  # Excluir filas con NaN en 'Familia_Cuenta'
]

# Aplicar los mismos filtros a budget_data
budget_data_filtered = budget_data[
    (budget_data['Año'].isin(selected_years)) & 
    (budget_data['Proceso'].isin(selected_procesos)) & 
    (budget_data['Familia_Cuenta'].isin(selected_familias))
]

# Si todos los procesos están seleccionados, incluir presupuesto overhead
if all_processes_selected:
    budget_data_overhead = budget_data[budget_data['Proceso'] == 'Overhead']
    budget_data_filtered = pd.concat([budget_data_filtered, budget_data_overhead], ignore_index=True)

# GRÁFICO DE TORTA
st.markdown("### Distribución del Gasto")

# Grafico de torta para materiales
gasto_materiales = filtered_data[filtered_data['Familia_Cuenta'] == 'Materiales'].groupby('Proceso')['Valor/mon.inf.'].sum().reset_index()
fig_materiales = px.pie(gasto_materiales, values='Valor/mon.inf.', names='Proceso', title='Distribución del Gasto en Materiales')

# Grafico de torta para servicios
gasto_servicios = filtered_data[filtered_data['Familia_Cuenta'] == 'Servicios'].groupby('Proceso')['Valor/mon.inf.'].sum().reset_index()
fig_servicios = px.pie(gasto_servicios, values='Valor/mon.inf.', names='Proceso', title='Distribución del Gasto en Servicios')

# Mostrar gráficos en columnas
col1, col2 = st.columns(2)
col1.plotly_chart(fig_materiales)
col2.plotly_chart(fig_servicios)

# Calculos previos tabla y widget
# Calcular las sumas por año y mes para Gasto Real usando filtered_data
gasto_real = filtered_data.groupby(['Ejercicio', 'Período'])['Valor/mon.inf.'].sum().reset_index()
gasto_real['Valor/mon.inf.'] = (gasto_real['Valor/mon.inf.'] / 1000000).round(1)  # Convertir a millones con un decimal
gasto_real = gasto_real.rename(columns={'Ejercicio': 'Año', 'Período': 'Mes'})

# Calcular las sumas por año y mes para Gasto Presupuestado usando budget_data_filtered
gasto_presupuestado = budget_data_filtered.groupby(['Año', 'Mes'])['Presupuesto'].sum().reset_index()
gasto_presupuestado['Presupuesto'] = gasto_presupuestado['Presupuesto'].round(1)

# Asegurarse de que las columnas son del mismo tipo
gasto_real['Año'] = gasto_real['Año'].astype(str)
gasto_real['Mes'] = gasto_real['Mes'].astype(int)  # Convertir a entero para orden correcto
gasto_presupuestado['Año'] = gasto_presupuestado['Año'].astype(str)
gasto_presupuestado['Mes'] = gasto_presupuestado['Mes'].astype(int)  # Convertir a entero para orden correcto

st.markdown("---")

# Nueva sección: Widgets de Gasto Acumulado
st.markdown("#### Hasta el momento llevamos...")

# Calcular el gasto acumulado real
ultimo_mes_real = gasto_real['Mes'].max()
gasto_acumulado_real = gasto_real[gasto_real['Mes'] <= ultimo_mes_real]['Valor/mon.inf.'].sum()

# Verificar si hay datos presupuestados antes de calcular el gasto acumulado presupuestado
if not gasto_presupuestado[gasto_presupuestado['Mes'] <= ultimo_mes_real].empty:
    gasto_acumulado_presupuestado = gasto_presupuestado[gasto_presupuestado['Mes'] <= ultimo_mes_real]['Presupuesto'].sum()
else:
    gasto_acumulado_presupuestado = None

# Aplicar lógica de colores
if gasto_acumulado_presupuestado is not None and gasto_acumulado_presupuestado != 0:
    diferencia_porcentaje = (gasto_acumulado_real / gasto_acumulado_presupuestado) * 100

    if diferencia_porcentaje <= 100:
        color_real = 'background-color: green;'
        color_presupuesto = 'background-color: green;'
    elif 100 < diferencia_porcentaje <= 110:
        color_real = 'background-color: yellow;'
        color_presupuesto = 'background-color: yellow;'
    else:
        color_real = 'background-color: red;'
        color_presupuesto = 'background-color: red;'
else:
    color_real = 'background-color: grey;'
    color_presupuesto = 'background-color: grey;'

# Mostrar los widgets alineados horizontalmente
col1, col2 = st.columns(2)

col1.markdown(f"<div style='{color_real} padding: 10px; border-radius: 5px; text-align: center;'>Gasto acumulado real<br><strong>${gasto_acumulado_real:.1f}M</strong></div>", unsafe_allow_html=True)
if gasto_acumulado_presupuestado is not None:
    col2.markdown(f"<div style='{color_presupuesto} padding: 10px; border-radius: 5px; text-align: center;'>Gasto acumulado presupuestado<br><strong>${gasto_acumulado_presupuestado:.1f}M</strong></div>", unsafe_allow_html=True)
else:
    col2.markdown(f"<div style='{color_presupuesto} padding: 10px; border-radius: 5px; text-align: center;'>Gasto acumulado presupuestado<br><strong>No disponible</strong></div>", unsafe_allow_html=True)

# Texto dinamico con recomendaciones
# Paso 1: Calcular el presupuesto disponible
st.write("")
st.markdown("#### Algunas Proyecciones...")
presupuesto_anual_total = budget_data_filtered['Presupuesto'].sum()
gasto_acumulado_real = gasto_real['Valor/mon.inf.'].sum()
presupuesto_disponible = presupuesto_anual_total - gasto_acumulado_real

# Paso 2: Calcular el gasto medio de los periodos con gasto real
gasto_medio = gasto_acumulado_real / len(gasto_real)  # len(gasto_real) nos da el número de meses con gasto real

# Paso 3: Calcular la proyección de fin de año
meses_restantes = 12 - len(gasto_real)
proyeccion_final = presupuesto_disponible - (gasto_medio * meses_restantes)

# Definir el presupuesto medio mensual
presupuesto_medio_mensual = 767  # En millones de pesos

# Paso 4: Mostrar los widgets con la nueva lógica de colores
col1, col2, col3 = st.columns(3)

# Presupuesto disponible - siempre verde
col1.markdown(f"<div style='background-color:green; padding: 10px; border-radius: 5px; text-align: center;'>"
              f"<strong>Presupuesto Disponible</strong><br>${presupuesto_disponible:.1f}M</div>", unsafe_allow_html=True)

# Gasto medio mensual con lógica de colores
if abs(gasto_medio - presupuesto_medio_mensual) <= presupuesto_medio_mensual * 0.05:
    color_gasto_medio = 'green'
elif abs(gasto_medio - presupuesto_medio_mensual) <= presupuesto_medio_mensual * 0.10:
    color_gasto_medio = 'yellow'
else:
    color_gasto_medio = 'red'

col2.markdown(f"<div style='background-color:{color_gasto_medio}; padding: 10px; border-radius: 5px; text-align: center;'>"
              f"<strong>Gasto Medio Mensual</strong><br>${gasto_medio:.1f}M</div>", unsafe_allow_html=True)

# Proyección de fin de año con lógica de colores basada en el presupuesto anual
if abs(proyeccion_final) <= presupuesto_anual_total * 0.05:
    color_proyeccion_final = 'green'
elif abs(proyeccion_final) <= presupuesto_anual_total * 0.10:
    color_proyeccion_final = 'yellow'
else:
    color_proyeccion_final = 'red'

col3.markdown(f"<div style='background-color:{color_proyeccion_final}; padding: 10px; border-radius: 5px; text-align: center;'>"
              f"<strong>Proyección a Fin de Año</strong><br>${proyeccion_final:.1f}M</div>", unsafe_allow_html=True)

# Paso 5: Mostrar el texto dinámico
if proyeccion_final > 0:
    st.markdown(f"Si el gasto medio mensual se mantiene, **terminarás el año con un excedente de ${proyeccion_final:.1f}M** en el presupuesto.")
else:
    st.markdown(f"Si el gasto medio mensual se mantiene, **terminarás el año con un déficit de ${-proyeccion_final:.1f}M** en el presupuesto.")

st.markdown("---")

# Gauge para mostrar consumo del presupuesto
# Calcular el presupuesto anual total basado en los filtros aplicados
st.markdown("#### Que % del presupuesto hemos gastado?")
presupuesto_anual_total = budget_data_filtered['Presupuesto'].sum()

# Calcular el porcentaje del presupuesto gastado
porcentaje_gastado = (gasto_acumulado_real / presupuesto_anual_total) * 100 if presupuesto_anual_total > 0 else 0

# Crear gráfico de indicador (gauge)
fig = go.Figure(go.Indicator(
    mode="gauge+number",  # Eliminar 'delta' para ocultar el valor diferencial
    value=porcentaje_gastado,
    number={'suffix': "%"},  # Agregar el signo de porcentaje al valor
    gauge={
        'axis': {'range': [0, 100]},
        'bar': {'color': "green"},
        'steps': [
            {'range': [0, 66], 'color': "lightgreen"},
            {'range': [66, 100], 'color': "yellow"},
        ],
        'threshold': {
            'line': {'color': "red", 'width': 4},
            'thickness': 0.75,
            'value': 100
        }
    },
    title={'text': ""}
))

# Mostrar el gráfico en Streamlit
st.plotly_chart(fig)

st.markdown("---")

# TABLA GASTO REAL VS PRESUPUESTADO
st.markdown("### Veamos un poco mas de detalle...")
st.markdown("#### Tabla de Gasto Real vs Presupuestado")

# Crear la tabla combinada
combined_data = pd.merge(gasto_real, gasto_presupuestado, on=['Año', 'Mes'], how='outer').fillna(0)
combined_data['Diferencia'] = combined_data['Valor/mon.inf.'] - combined_data['Presupuesto']

# Ordenar las columnas de manera ascendente
combined_data = combined_data.sort_values(by=['Año', 'Mes'])

# Eliminar las columnas 'Año' y 'Mes' y definir el índice temporalmente como el periodo concatenado
combined_data['Mes_Año'] = combined_data.apply(lambda x: f"{x['Mes']}_{x['Año']}", axis=1)
combined_data_display = combined_data.drop(columns=['Año', 'Mes']).set_index('Mes_Año')

# Eliminar el nombre de las columnas
combined_data_display.columns.name = None

# Renombrar las columnas para claridad
combined_data_display = combined_data_display.rename(columns={
    'Valor/mon.inf.': 'Gasto Real',
    'Presupuesto': 'Presupuesto',
    'Diferencia': 'Diferencia'
})

# Transponer el DataFrame
combined_data_transposed = combined_data_display.T

# Mostrar la tabla transpuesta en Streamlit
st.dataframe(combined_data_transposed)

# Herramienta de análisis diferencial
# Filtrar los datos solo hasta el último mes disponible con datos reales
ultimo_mes_real = combined_data[combined_data['Valor/mon.inf.'] > 0]['Mes'].max()

# Crear una copia del DataFrame filtrado para los meses con datos reales
combined_data_filtered = combined_data[combined_data['Mes'] <= ultimo_mes_real].copy()

# Asegurar que todos los meses hasta julio (o hasta el último mes con datos reales) están presentes en el eje X
todos_los_meses = pd.DataFrame({'Mes': range(1, ultimo_mes_real + 1), 'Año': '2024'})
combined_data_filtered = pd.merge(todos_los_meses, combined_data_filtered, on=['Año', 'Mes'], how='left').fillna(0)

# Calcular el diferencial acumulado correctamente sin incluir un periodo adicional
combined_data_filtered['Diferencial Acumulado'] = combined_data_filtered['Diferencia'].cumsum()

# Crear la gráfica de barras para la diferencia real vs presupuestado
fig = go.Figure()

# Gráfica de barras para la diferencia mensual
fig.add_trace(go.Bar(
    x=combined_data_filtered['Mes_Año'],
    y=combined_data_filtered['Diferencia'],
    name='Diferencia Mensual',
    marker_color='blue'
))

# Línea para el diferencial acumulado, sin desfasar
fig.add_trace(go.Scatter(
    x=combined_data_filtered['Mes_Año'],
    y=combined_data_filtered['Diferencial Acumulado'],
    mode='lines+markers',
    name='Diferencial Acumulado',
    line=dict(color='red'),
    marker=dict(size=8)
))

# Configurar el eje Y centrado en 0
fig.update_layout(
    yaxis=dict(
        title='Diferencia (Real - Presupuestado)',
        zeroline=True,
        zerolinewidth=2,
        zerolinecolor='black'
    ),
    xaxis_title='Mes y Año',
    title='Diferencia mensual entre Gasto Real y Presupuesto',
    barmode='overlay',
    xaxis=dict(
        tickmode='array',
        tickvals=[f'{i}_2024' for i in range(1, 13)],  # Mostrar todos los meses del año
        ticktext=['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'],
    )
)

# Mostrar el gráfico en Streamlit
st.plotly_chart(fig)
