import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go 
import io

# Título de la aplicación
st.markdown("<h1 style='text-align: center; color: black; font-size: 24px;'>MONITOR GESTION ORDENES DE MANTENIMIENTO</h1>", unsafe_allow_html=True)

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
DATA0_URL = 'https://streamlitmaps.s3.amazonaws.com/Data_0824_2.csv'
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

# Asegurarse de que los valores en 'Valor/mon.inf.' sean enteros
data0['Valor/mon.inf.'] = data0['Valor/mon.inf.'].astype(int)

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

# Redondear valores y asegurarse de que sean enteros
data0['Valor/mon.inf.'] = data0['Valor/mon.inf.'].round(0).astype(int)

# Calcular las sumas por año y mes para Gasto Real
gasto_real = data0.groupby(['Ejercicio', 'Período'])['Valor/mon.inf.'].sum().reset_index()
gasto_real['Valor/mon.inf.'] = (gasto_real['Valor/mon.inf.'] / 1000000).round(1)  # Convertir a millones con un decimal
gasto_real = gasto_real.rename(columns={'Ejercicio': 'Año', 'Período': 'Mes'})

# Asegurarse de que las columnas son del mismo tipo
gasto_real['Año'] = gasto_real['Año'].astype(str)
gasto_real['Mes'] = gasto_real['Mes'].astype(int)  # Convertir a entero para orden correcto

# Gráfico de Columnas Apiladas con Presupuesto
st.markdown("### Gasto Real por Tipo de Orden")

filtered_data = filtered_data.merge(orders_data, how='left', left_on='Orden partner', right_on='Orden')

# Calcular las métricas para cada tipo de orden
tipo_orden_metrics = filtered_data.groupby('Clase de orden').agg(
    cantidad_ordenes=pd.NamedAgg(column='Orden partner', aggfunc='count'),
    gasto=pd.NamedAgg(column='Valor/mon.inf.', aggfunc='sum')
).reset_index()

# Calcular el valor OT medio
tipo_orden_metrics['valor_ot_media'] = tipo_orden_metrics['gasto'] / tipo_orden_metrics['cantidad_ordenes']

# Seleccionar columnas específicas para mostrar
tipo_orden_metrics_display = tipo_orden_metrics[['Clase de orden', 'cantidad_ordenes', 'gasto', 'valor_ot_media']]

# Renombrar las columnas para la visualización
tipo_orden_metrics_display.columns = ['Tipo de orden', 'Cantidad de ordenes', 'Gasto', 'Valor OT media']

# Redondear valor_ot_media a 0 decimales
tipo_orden_metrics_display['Valor OT media'] = tipo_orden_metrics_display['Valor OT media'].round(0).astype(int)

# Asegurarse de que el campo 'Mes' existe en el DataFrame filtrado
filtered_data['Mes'] = filtered_data['Período'].astype(int)

# Preparar los datos para el gráfico de columnas apiladas
data0_grouped = filtered_data.groupby(['Mes', 'Clase de orden'])['Valor/mon.inf.'].sum().reset_index()
data0_pivot = data0_grouped.pivot(index='Mes', columns='Clase de orden', values='Valor/mon.inf.').fillna(0)

# Preparar los datos para el gráfico de columnas apiladas
filtered_data_grouped = filtered_data.groupby(['Mes', 'Clase de orden'])['Valor/mon.inf.'].sum().reset_index()
filtered_data_pivot = filtered_data_grouped.pivot(index='Mes', columns='Clase de orden', values='Valor/mon.inf.').fillna(0)

# Definir los colores específicos para cada tipo de OT
colores_ot = {
    'PM01': 'red',
    'PM02': 'blue',
    'PM03': 'lightblue',
    'PM04': 'orange',
    'PM05': 'pink',
}

fig_columnas = go.Figure()

# Añadir las columnas apiladas por tipo de orden con los colores definidos
for column in filtered_data_pivot.columns:
    if column != 'Presupuesto':
        color = colores_ot.get(column, 'grey')  # Usar el color definido o 'grey' por defecto
        fig_columnas.add_trace(go.Bar(x=filtered_data_pivot.index, y=filtered_data_pivot[column], name=column, marker_color=color))

fig_columnas.update_layout(barmode='stack', title='', xaxis_title='Mes', yaxis_title='Gasto', legend_title='Tipo de Orden')
st.plotly_chart(fig_columnas)

# Sección Métricas OT
st.markdown("#### Miremos algunas métricas de nuestras Ordenes de Trabajo")

# Formatear las columnas "Gasto" y "Valor OT media"
tipo_orden_metrics_display['Gasto'] = tipo_orden_metrics_display['Gasto'].apply(lambda x: f"{x:,.0f}")
tipo_orden_metrics_display['Valor OT media'] = tipo_orden_metrics_display['Valor OT media'].apply(lambda x: f"{x:,.0f}")

# Resetear el índice para eliminar la columna de índices y luego mostrar la tabla
tipo_orden_metrics_display_reset = tipo_orden_metrics_display.reset_index(drop=True)

# Mostrar la tabla sin la columna de índices
st.table(tipo_orden_metrics_display_reset)

# Nueva sección: Tabla de los 5 mayores gastos
st.markdown("#### Top 5 Mayores Gastos del Año")

# Filtrar filas con 'Centro de coste' no vacío
data0_filtered = filtered_data[filtered_data['Centro de coste'].notna() & (filtered_data['Centro de coste'] != '')]

# Filtrar y ordenar data0 para obtener los 5 mayores gastos
data0_sorted = data0_filtered.sort_values(by='Valor/mon.inf.', ascending=False)
top_5_gastos = data0_sorted.head(5)

# Seleccionar columnas específicas para mostrar y formatear la columna "Valor/mon.inf."
top_5_gastos_display = top_5_gastos[['Centro de coste', 'Denominación del objeto', 'Grupo_Ceco', 'Fe.contabilización', 'Valor/mon.inf.']]
top_5_gastos_display['Valor/mon.inf.'] = top_5_gastos_display['Valor/mon.inf.'].apply(lambda x: f"{x:,.0f}")

# Resetear el índice para eliminar la columna de índices y luego mostrar la tabla
top_5_gastos_display_reset = top_5_gastos_display.reset_index(drop=True)

# Mostrar la tabla sin la columna de índices
st.table(top_5_gastos_display_reset)

# Nueva sección: Tabla de los 5 mayores gastos del ULTIMO MES
st.markdown("#### Top 5 Mayores Gastos del Último Mes")

# Identificar el último mes con gastos reales
ultimo_mes_con_gastos = data0_filtered['Mes'].max()

# Filtrar para obtener solo los gastos del último mes con datos
data0_filtered_ultimo_mes = data0_filtered[data0_filtered['Mes'] == ultimo_mes_con_gastos]

# Ordenar y obtener los 5 mayores gastos del último mes
data0_sorted_ultimo_mes = data0_filtered_ultimo_mes.sort_values(by='Valor/mon.inf.', ascending=False)
top_5_gastos_ultimo_mes = data0_sorted_ultimo_mes.head(5)

# Seleccionar columnas específicas para mostrar y formatear la columna "Valor/mon.inf."
top_5_gastos_ultimo_mes_display = top_5_gastos_ultimo_mes[['Centro de coste', 'Denominación del objeto', 'Grupo_Ceco', 'Fe.contabilización', 'Valor/mon.inf.']]
top_5_gastos_ultimo_mes_display['Valor/mon.inf.'] = top_5_gastos_ultimo_mes_display['Valor/mon.inf.'].apply(lambda x: f"{x:,.0f}")

# Resetear el índice para eliminar la columna de índices y luego mostrar la tabla
top_5_gastos_ultimo_mes_display_reset = top_5_gastos_ultimo_mes_display.reset_index(drop=True)

# Mostrar la tabla sin la columna de índices
st.table(top_5_gastos_ultimo_mes_display_reset)

#Widget para mostrar % del gasto con OT
# Paso 1: Calcular la suma del gasto total en data0
gasto_total = filtered_data['Valor/mon.inf.'].sum()

# Paso 2: Filtrar las filas con OT asociada (donde "Orden partner" no está vacío)
data_con_ot = filtered_data[filtered_data['Orden partner'].notna() & (filtered_data['Orden partner'] != '')].copy()

# Paso 3: Calcular la suma del gasto con OT
gasto_con_ot = data_con_ot['Valor/mon.inf.'].sum()

# Paso 4: Calcular el porcentaje del gasto con OT respecto al gasto total
porcentaje_con_ot = (gasto_con_ot / gasto_total) * 100

# Paso 5: Definir el color basado en el porcentaje
if porcentaje_con_ot > 80:
    color = "green"
elif 70 <= porcentaje_con_ot <= 80:
    color = "yellow"
else:
    color = "red"

# Paso 6: Mostrar el widget con estilos personalizados
st.markdown(
    f"""
    <div style="text-align: center; border: 2px solid #ddd; padding: 10px; border-radius: 10px; background-color: {color};">
        <h3 style="color: white;">Porcentaje de Gasto con OT</h3>
        <p style="font-size: 32px; color: white;"><b>{porcentaje_con_ot:.2f}%</b></p>
    </div>
    """,
    unsafe_allow_html=True
)
