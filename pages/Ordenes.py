import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go 
import io

# Título de la aplicación
st.markdown("<h1 style='text-align: center; color: black; font-size: 24px;'>MONITOR GESTIÓN ORDENES</h1>", unsafe_allow_html=True)

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
DATA0_URL = 'https://streamlitmaps.s3.amazonaws.com/Data_0724.csv'
BUDGET_URL = 'https://streamlitmaps.s3.amazonaws.com/Base_Presupuesto_3.csv'
ORDERS_URL = 'https://streamlitmaps.s3.amazonaws.com/Base_Ordenes_0724.csv'
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

# Asegurarse de que los valores en 'Valor/mon.inf.' sean enteros
data0['Valor/mon.inf.'] = data0['Valor/mon.inf.'].astype(int)

# FILTROS en la barra lateral
st.sidebar.markdown("### Filtros")
selected_years = st.sidebar.multiselect("Selecciona el año", data0['Ejercicio'].unique().tolist(), default=['2024'])
selected_procesos = st.sidebar.multiselect("Selecciona el proceso", data0['Proceso'].unique().tolist(), default=data0['Proceso'].unique().tolist())
selected_familias = st.sidebar.multiselect("Selecciona la Familia_Cuenta", ['Materiales', 'Servicios'], default=['Materiales', 'Servicios'])

# Verificar si todos los procesos están seleccionados
#all_processes_selected = set(selected_procesos) == set(data0['Proceso'].unique().tolist())

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

# Redondear valores y asegurarse de que sean enteros
data0['Valor/mon.inf.'] = data0['Valor/mon.inf.'].round(0).astype(int)

# Filtrar data0 excluyendo filas donde la columna Utec esté vacía
data0_filtered = data0[~data0['Utec'].isna()].copy()

# Agregar una nueva columna "Clase de orden" a data0_filtered
data0_filtered['Clase de orden'] = None

# Mapear "Clase de orden" a data0_filtered usando la columna "Orden partner" y "Orden"
data0_filtered = data0_filtered.merge(orders_data[['Orden', 'Clase de orden']], 
                                      how='left', 
                                      left_on='Orden partner', 
                                      right_on='Orden')

# Eliminar la columna 'Orden' redundante después del merge
#data0_filtered.drop(columns=['Orden'], inplace=True)

# Verificar que la columna "Valor/mon.inf." esté en millones
data0_filtered['Valor/mon.inf.'] = (data0_filtered['Valor/mon.inf.'] / 1000000).round(1)

# Preparar los datos para el gráfico de columnas apiladas
data0['Mes'] = data0['Período'].astype(int)
data0_grouped = data0.groupby(['Mes', 'Clase de orden'])['Valor/mon.inf.'].sum().reset_index()
data0_pivot = data0_grouped.pivot(index='Mes', columns='Clase de orden', values='Valor/mon.inf.').fillna(0)

# Crear la gráfica de barras apiladas
fig_columnas = go.Figure()

# Añadir las columnas apiladas por tipo de orden
for column in data0_pivot.columns:
    fig_columnas.add_trace(go.Bar(x=data0_pivot.index, y=data0_pivot[column], name=column))

# Configuración final del gráfico
fig_columnas.update_layout(
    barmode='stack',
    title='Gasto Real por Tipo de Orden',
    xaxis_title='Mes',
    yaxis_title='Gasto (Millones)',
    legend_title='Tipo de Orden'
)

# Mostrar el gráfico en Streamlit
st.plotly_chart(fig_columnas)
