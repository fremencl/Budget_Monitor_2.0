import streamlit as st
import pandas as pd
import plotly.express as px
import io

# Título de la aplicación
st.markdown("<h1 style='text-align: center; color: black; font-size: 24px;'>MONITOR GESTIÓN PRESUPUESTARIA</h1>", unsafe_allow_html=True)
st.markdown("<h2 style='text-align: center; color: black; font-size: 24px;'>ANALISIS AGREGADO: GASTO Y PRESUPUESTO</h2>", unsafe_allow_html=True)

# Definimos las URLs de los archivos de referencia
DATA0_URL = 'https://streamlitmaps.s3.amazonaws.com/Data_0624.csv'
BUDGET_URL = 'https://streamlitmaps.s3.amazonaws.com/Base_Presupuesto_2.csv'
ORDERS_URL = 'https://streamlitmaps.s3.amazonaws.com/Base_Ordenes_0624.csv'
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
    # data0['Período'] = data0['Período'].astype(str)
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
        nueva_fila = {
            'Ejercicio': ejercicio,
            'Período': periodo,
            'Proceso': proc_row['Proceso'],
            'Valor/mon.inf.': overhead_valor * proc_row['Proporción']
        }
        filas_nuevas.append(nueva_fila)

# Convertir la lista de nuevas filas a un DataFrame
filas_nuevas_df = pd.DataFrame(filas_nuevas)

# Paso 6: Agregar las nuevas filas al DataFrame original
data0 = pd.concat([data0, filas_nuevas_df], ignore_index=True)

# Paso 7: Eliminar las filas correspondientes a "Overhead"
data0 = data0[data0['Proceso'] != 'Overhead']

# Convertir la columna 'Familia_Cuenta' y 'Recinto' a tipo string
data0['Familia_Cuenta'] = data0['Familia_Cuenta'].astype(str)
data0['Recinto'] = data0['Recinto'].astype(str)

# FILTROS
# Definir los filtros dinámicamente a partir de los valores únicos en las columnas correspondientes
years = data0['Ejercicio'].unique().tolist()
procesos = data0['Proceso'].unique().tolist()  # Obtener valores únicos de la columna 'Proceso'
familias_cuenta = data0['Familia_Cuenta'].dropna().unique().tolist()  # Obtener valores únicos de la columna 'Familia_Cuenta' excluyendo NaN

# Asegurarse de que los valores únicos no incluyan valores nulos (para procesos, si es necesario)
procesos = [proc for proc in procesos if pd.notna(proc)]

# Filtros de Streamlit
st.markdown("### Filtros")
selected_years = st.multiselect("Selecciona el año", years, default=['2024'])
selected_procesos = st.multiselect("Selecciona el proceso", procesos, default=procesos)
selected_familias = st.multiselect("Selecciona la Familia_Cuenta", familias_cuenta, default=familias_cuenta)

# Aplicar los filtros, incluyendo el filtro de año
filtered_data = data0[(data0['Ejercicio'].isin(selected_years)) &
                     (data0['Proceso'].isin(selected_procesos)) &
                     (data0['Familia_Cuenta'].isin(selected_familias))]

budget_data_filtered = budget_data[budget_data['Año'].isin(selected_years)]

# Función para convertir DataFrame a CSV
def convertir_a_csv(df):
    buffer = io.StringIO()
    df.to_csv(buffer, index=False, sep=';')
    buffer.seek(0)
    return buffer.getvalue()

# Generar el enlace de descarga para las filas procesadas
csv_filtered_data = convertir_a_csv(filtered_data)

# Agregar un botón de descarga en la aplicación
st.download_button(
    label="Descargar_filtered_data",
    data=csv_filtered_data,
    file_name='filas_filtered_data.csv',
    mime='text/csv',
)

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

# TABLA GASTO REAL VS PRESUPUESTADO
st.markdown("#### Tabla de Gasto Real vs Presupuestado")

# Calcular las sumas por año y mes para Gasto Real usando filtered_data
gasto_real = filtered_data.groupby(['Ejercicio', 'Período'])['Valor/mon.inf.'].sum().reset_index()
gasto_real['Valor/mon.inf.'] = (gasto_real['Valor/mon.inf.'] / 1000000).round(1)  # Convertir a millones con un decimal
gasto_real = gasto_real.rename(columns={'Ejercicio': 'Año', 'Período': 'Mes'})

# Calcular las sumas por año y mes para Gasto Presupuestado
gasto_presupuestado = budget_data.groupby(['Año', 'Mes'])['Presupuesto'].sum().reset_index()
gasto_presupuestado['Presupuesto'] = gasto_presupuestado['Presupuesto'].round(1)

# Asegurarse de que las columnas son del mismo tipo
gasto_real['Año'] = gasto_real['Año'].astype(str)
gasto_real['Mes'] = gasto_real['Mes'].astype(int)  # Convertir a entero para orden correcto
gasto_presupuestado['Año'] = gasto_presupuestado['Año'].astype(str)
gasto_presupuestado['Mes'] = gasto_presupuestado['Mes'].astype(int)  # Convertir a entero para orden correcto

# Crear la tabla combinada
combined_data = pd.merge(gasto_real, gasto_presupuestado, on=['Año', 'Mes'], how='outer').fillna(0)
combined_data['Diferencia'] = combined_data['Valor/mon.inf.'] - combined_data['Presupuesto']
combined_data = combined_data.sort_values(by=['Año', 'Mes'])

# Imprimir el encabezado de la tabla combined_data
st.write("Encabezado de la tabla combined_data:")
st.write(combined_data.head())

# Aplicar los filtros después de calcular las sumatorias
filtered_combined_data = combined_data[
    (combined_data['Año'].isin(selected_years)) & 
    (combined_data['Proceso'].isin(selected_procesos)) & 
    (combined_data['Familia_Cuenta'].isin(selected_familias))
]

# Evitar duplicación de columnas y preparar para la transposición
combined_data_display = filtered_combined_data.copy()
combined_data_display.columns = combined_data_display.columns.map(str)
combined_data_display = combined_data_display.set_index(['Mes'])

# Renombrar las columnas para claridad
combined_data_display = combined_data_display.rename(columns={
    'Valor/mon.inf.': 'Gasto Real',
    'Presupuesto': 'Gasto Presupuestado',
    'Diferencia': 'Diferencia'
})

# Eliminar la columna de año antes de la transposición
combined_data_display = combined_data_display.drop(columns=['Año'])
combined_data_transposed = combined_data_display.T.reset_index().rename(columns={'index': 'Descripción'})

# Mostrar la tabla transpuesta en Streamlit
st.dataframe(combined_data_transposed)

# Nueva sección: Widgets de Gasto Acumulado
st.markdown("#### Gasto Acumulado")

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
