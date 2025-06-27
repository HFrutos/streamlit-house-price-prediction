import os
import pandas as pd
import plotly.express as px
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import folium
from folium.plugins import MarkerCluster
from streamlit_folium import folium_static
import streamlit as st
from sklearn.preprocessing import MinMaxScaler
import pickle
from math import pi
import json
import requests


# ---------------------------
# CARGA DESDE AIRTABLE
# ---------------------------
TOKEN = "patwbIvz6gTXFsl4Y.6dfe3124e999ca6d7af755c456617541256a28f1725f2a51dff9b89237c3380e"
BASE_ID = "appWlFma1nHFvUIVS"
TABLE_ID = "tbl0oRpWsFUHBIl9Z"
AIRTABLE_URL = f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_ID}"
HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

def extraer_registros(formula=None, view="Grid view", page_size=100):
    registros, offset = [], None
    while True:
        params = {"view": view, "pageSize": page_size}
        if offset: params["offset"] = offset
        if formula: params["filterByFormula"] = formula
        r = requests.get(AIRTABLE_URL, headers=HEADERS, params=params)
        data = r.json()
        registros += [rec["fields"] for rec in data.get("records", [])]
        offset = data.get("offset")
        if not offset: break
    return registros

df_venta = pd.DataFrame(extraer_registros("({listing_type}='sale')"))
df_alquiler = pd.DataFrame(extraer_registros("({listing_type}='rental')"))

# ---------------------------
# CARGA DE NIVELES CATEGÓRICOS
# ---------------------------
with open('sale_classifier_features.json', 'r', encoding='utf-8') as f:
    cat_levels = json.load(f)

def aplicar_cat_levels(df: pd.DataFrame) -> pd.DataFrame:
    for col, levels in cat_levels.items():
        if col in df.columns:
            df[col] = df[col].astype('category').cat.set_categories(levels)
    return df

df_venta = aplicar_cat_levels(df_venta)
df_alquiler = aplicar_cat_levels(df_alquiler)

for df in [df_venta, df_alquiler]:
    if 'barrio' in df.columns:
        df['barrio'] = df['barrio'].astype('category')
    if 'antigüedad' in df.columns:
        df['antigüedad'] = df['antigüedad'].astype('category')

# ---------------------------
# FUNCIONES DE FILTRADO Y PÁGINA PRINCIPAL
# ---------------------------

def filtrar_propiedades(df: pd.DataFrame, f: dict) -> pd.DataFrame:
    mask = (
        df['superficie_construida'].between(f['metros'][0], f['metros'][1]) &
        df['habitaciones'].between(f['habitaciones'][0], f['habitaciones'][1])
    )
    if f['barrios'] and 'Todos' not in f['barrios']:
        mask &= df['barrio'].isin(f['barrios'])
    if f['antiguedad'] and 'antigüedad' in df.columns:
        mask &= df['antigüedad'].isin(f['antiguedad'])
    return df.loc[mask].copy()

def show_main_page():
    col1, _, col_big = st.columns([2, 0.5, 5.5])
    with col1:
        st.image("orangutan.png", caption="¡Selecciona los parámetros en el sidebar!", width=325)
    with col_big:
        st.title("Predicción de Precios de Viviendas")
        st.markdown(
            "Bienvenido/a. Esta app permite predecir el precio de una propiedad según sus características."
            "\n\n- En el menú desplegable de la izquierda puedes filtrar por tipo de operación (venta o alquiler), metros cuadrados, número de habitaciones, barrios y antigüedad."
            "\n\n- En la pestaña donde se selecciona la sección podrás seleccionar mapa de pisos, métricas, gráficas o predictivo."
            "\n\n- En la sección de Mapa de pisos podrás ver un mapa interactivo con los inmuebles que cumplen con los filtros seleccionados."
            "\n\n- En la sección de métricas podrás ver estadísticas sobre los inmuebles seleccionados, como el número de barrios, el máximo de habitaciones, el número de pisos, el máximo de metros cuadrados y el rating energético más frecuente."
            "\n\n- En la sección Exploratory Data Analysis podrás ver distintas gráficas para comprender el mercado inmobiliario actual."
            "\n\n- En la sección Predictivo podrás introducir los datos de tu inmueble para que nuestro modelo de IA prediga el precio óptimo de tu vivienda."
        )
        with st.expander("ℹ️ Acerca del grupo / About Us"):
            st.markdown("""  
### 👨‍💻 Integrantes del grupo

- **Akira García** – Junior Data Scientist | Ingeniero Informático | Análisis de Datos & Machine Learning  
  [LinkedIn](https://www.linkedin.com/in/akiragarcialuis/) | [GitHub](https://github.com/akiraglhola)

- **Marta Rivas** – Porque se lo merece  
  [LinkedIn](https://www.linkedin.com/in/MartaRivas) | [GitHub](https://github.com/MartaRivas13)

- **Héctor Frutos** – Es buena gente  
  [LinkedIn](https://www.linkedin.com/in/HectorFrutos) | [GitHub](https://github.com/HFrutos)

- **Jorge Arriaga** – Porque tiene que haber de tó  
  [LinkedIn](https://www.linkedin.com/in/JorgeArriaga) | [GitHub](https://github.com/Jorge-Arriaga)

Proyecto realizado como parte del curso de *Machine Learning aplicado a Datos Inmobiliarios*.

✉️ Para más información, contacta a: pftttttt@example.com
            """, unsafe_allow_html=True)
        with st.expander("Documentación técnica"):
            st.markdown('<"Enlace a Github" a href="https://github.com/HFrutos/streamlit-house-price-prediction" target="_blank">📄 Ver documentación completa →</a>', 
            unsafe_allow_html=True
            )
            st.markdown('<"Métricas y comparativas de Modelos" a href="https://pryecto-final-vu9gcvproubhfxgm5mq9mb.streamlit.app" target="_blank">📄 Ver do</a>', 
            unsafe_allow_html=True
            )

# ---------------------------
# FUNCIÓN PRINCIPAL
# ---------------------------
def main():
    st.set_page_config(page_title='house-price-prediction', page_icon='🏠', layout='wide')

    if 'temp_filters' not in st.session_state:
        st.session_state.temp_filters = {
            'section': 'Página principal',
            'tipo_operacion': 'venta',
            'metros': (50, 150),
            'habitaciones': (1, 4),
            'barrios': ['Todos'],
            'antiguedad': []
        }

    with st.sidebar.form("filtros"):
        tf = st.session_state.temp_filters
        tf['tipo_operacion'] = st.selectbox('Tipo de operación', ['venta', 'alquiler'], index=['venta','alquiler'].index(tf['tipo_operacion']))
        tf['metros'] = st.slider('Metros cuadrados', 20, 600, tf['metros'])
        tf['habitaciones'] = st.slider('Habitaciones', 1, 8, tf['habitaciones'])
        df_temp = df_venta if tf['tipo_operacion']=='venta' else df_alquiler
        barrios = ['Todos'] + sorted(df_temp['barrio'].cat.categories) if 'barrio' in df_temp.columns else ['Todos']
        tf['barrios'] = st.multiselect('Barrios', barrios, default=tf['barrios'])
        if 'antigüedad' in df_temp.columns:
            ant = df_temp['antigüedad'].cat.categories.tolist()
            tf['antiguedad'] = st.multiselect('Antigüedad', ant, default=tf['antiguedad'])
        else:
            tf['antiguedad'] = []
        tf['section'] = st.selectbox('Sección', ['Página principal','Comparativa de pisos','Exploratory Data Analysis','Predictivo'], index=0)
        submitted = st.form_submit_button("Aplicar filtros")

    if submitted:
        st.session_state.applied_filters = st.session_state.temp_filters.copy()

    f = st.session_state.applied_filters if 'applied_filters' in st.session_state else st.session_state.temp_filters
    df_sel = df_venta if f['tipo_operacion']=='venta' else df_alquiler
    filtro = filtrar_propiedades(df_sel, f)

    if f['section']=='Página principal':
        show_main_page()
    elif f['section']=='Comparativa de pisos':
        st.title('Mapa de pisos en Madrid')
    elif f['section']=='Exploratory Data Analysis':
        if filtro.empty:
            st.warning('No hay datos para mostrar.')
    elif f['section']=='Predictivo':
        st.title("Predicción de precio de vivienda")
        


# ---------------------------
# COMPARATIVA DE PISOS
# ---------------------------
    if f['section'] == 'Comparativa de pisos':
        st.title('')
        

        st.subheader('Pisos que coinciden con tu búsqueda')
        st.markdown(f'**{len(filtro)} pisos encontrados**')

        # Resumen para selección
        filtro['Resumen'] = filtro.apply(
            lambda x: f"{x['price_eur']:,}€ - {x['habitaciones']} hab - {x['superficie_construida']} m² - {x['barrio']}",
            axis=1
        )

        st.subheader("Selecciona pisos para comparar")
        seleccion = st.multiselect(
            "Elige pisos", options=filtro.index, format_func=lambda idx: filtro.loc[idx, 'Resumen']
        )

        if filtro.empty:
            st.warning('No hay resultados para los filtros seleccionados.')
            st.stop()

        if seleccion:
            st.success(f"{len(seleccion)} piso(s) seleccionados")
        else:
            st.info("No has seleccionado ningún piso manualmente.")

        # Limpieza de coordenadas
        filtro = filtro.dropna(subset=['latitude', 'longitude'])
        filtro = filtro[(filtro['latitude'].between(-90, 90)) & (filtro['longitude'].between(-180, 180))]

        # Mapa con marcadores
        m = folium.Map(location=[40.4168, -3.7038], zoom_start=12)
        if not filtro.empty:
            marker_cluster = MarkerCluster().add_to(m)
            for _, row in filtro.iterrows():
                folium.Marker(
                    location=[row['latitude'], row['longitude']],
                    popup=f"""
                        <b>Precio:</b> {row['price_eur']:,} €<br>
                        <b>Habitaciones:</b> {row['habitaciones']}<br>
                        <b>m²:</b> {row['superficie_construida']}<br>
                        <b>Barrio:</b> {row['barrio']}
                    """,
                    icon=folium.Icon(color='blue', icon='home')
                ).add_to(marker_cluster)
        folium_static(m, width=800, height=600)

        st.subheader("")

        # Selección dinámica de columnas para comparar
        columnas_disponibles = ['price_eur', 'superficie_construida', 'habitaciones', 'banos']  
        columnas_comparar = st.multiselect("Selecciona columnas para radar", columnas_disponibles, default=columnas_disponibles[:3])

        if not columnas_comparar:
            st.warning("Por favor selecciona al menos una columna para comparar.")
            st.stop()

        # Mapear etiquetas para las columnas 
        etiquetas_map = {
            'price_eur': 'Precio (€)',
            'superficie_construida': 'Superficie (m²)',
            'habitaciones': 'Habitaciones',
            'banos': 'Baños'
        }
        etiquetas = [etiquetas_map.get(col, col) for col in columnas_comparar]

        # Selección de filas para comparar 
        if seleccion:
            comparacion_df = filtro.loc[seleccion]
        elif len(filtro) >= 3:
            comparacion_df = filtro.sample(3, random_state=42)
            st.info("Se han seleccionado 3 pisos al azar para la comparativa.")
        elif not filtro.empty:
            comparacion_df = filtro
            st.info("Menos de 3 pisos disponibles. Se compararán todos los que hay.")
        else:
            st.warning("No hay pisos disponibles para comparar.")
            st.stop()

        # Normalización de las columnas seleccionadas
        scaler = MinMaxScaler()
        valores_normalizados = scaler.fit_transform(comparacion_df[columnas_comparar])

        # Preparar etiquetas para cerrar el radar 
        etiquetas_cerradas = etiquetas + [etiquetas[0]]

        fig = go.Figure()

        for i, row in enumerate(comparacion_df.itertuples()):
            valores = list(valores_normalizados[i])
            valores_cerrados = valores + [valores[0]]  # cerrar ciclo

            fig.add_trace(go.Scatterpolar(
                r=valores_cerrados,
                theta=etiquetas_cerradas,
                fill='toself',
                name=str(getattr(row, 'Resumen', getattr(row, 'Index', i)))  # usa 'Resumen' o índice
            ))

        fig.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, 1]
                )),
            showlegend=True,
            title="Radar de características normalizadas"
        )

        st.plotly_chart(fig, use_container_width=True)


# ---------------------------
# SECCIÓN EDA
# ---------------------------
    elif f['section'] == 'Exploratory Data Analysis':
        st.title('')

        if filtro.empty:
            st.warning('No hay datos para mostrar gráficos.')
        else:
            st.subheader("Distribución de precios")
            with st.expander("¿Qué está mostrando el gráfico?"):
                st.markdown('En este gráfico podrás ver la cantidad de propiedades que hay en cada rango de precios para las propiedades que coincidan con el filtro de la izquierda', 
            unsafe_allow_html=True)
                
            fig1 = px.histogram(filtro, x='price_eur', nbins=50, title='Distribución del precio en euros')
            st.plotly_chart(fig1, use_container_width=True, key="eda_fig1")

            st.subheader("Precio promedio por barrio")
            with st.expander("¿Qué está mostrando el gráfico?"):
                st.markdown('En este gráfico podrás ver el precio medio de las propiedades seleccionadas en el filtro de la izquierda', 
            unsafe_allow_html=True)
            precio_barrio = filtro.groupby('barrio')['price_eur'].mean().sort_values()
            fig2 = px.bar(precio_barrio, title='Precio promedio por barrio')
            st.plotly_chart(fig2, use_container_width=True, key="eda_fig2")

            # Mostrar tabla resumen por barrio
            with st.expander("¿Qué está mostrando el gráfico?"):
                st.markdown('Aquí tienes una tabla comparativa para las propiedades que coincidan con el filtro de la izquierda', 
            unsafe_allow_html=True)
                
            resumen_barrio = filtro.groupby('barrio').agg({
                'price_eur': ['mean', 'median', 'count'],
                'superficie_construida': 'mean'
            }).round(2)
            resumen_barrio.columns = ['Precio medio (€)', 'Precio mediano (€)', 'Nº propiedades', 'Superficie media (m²)']
            st.dataframe(resumen_barrio.sort_values('Precio medio (€)', ascending=False))

            if 'antigüedad' in filtro.columns:
                st.subheader("Boxplot de precio según antigüedad")
                with st.expander("¿Qué está mostrando el gráfico?"):
                    st.markdown('En este gráfico podrás ver la relación entre la antiguedad de los inmuebles y el precio para las propiedades que coincidan con el filtro de la izquierda', 
                unsafe_allow_html=True)
                    
                fig3 = px.box(filtro, x='antigüedad', y='price_eur', title='Precio según antigüedad')
                st.plotly_chart(fig3, use_container_width=True, key="eda_fig3")

            if 'superficie_construida' in filtro.columns:
                st.subheader("Distribución de superficie_construida")
                with st.expander("¿Qué está mostrando el gráfico?"):
                    st.markdown('En este gráfico podrás ver la superficie construida para las propiedades que coincidan con el filtro de la izquierda', 
                unsafe_allow_html=True)
                fig4 = px.histogram(filtro, x='superficie_construida', nbins=50, title='superficie_construida')
                st.plotly_chart(fig4, use_container_width=True, key="eda_fig4")

            if 'barrio' in filtro.columns and 'superficie_construida' in filtro.columns:
                st.subheader("superficie_construida promedio por barrio")
                with st.expander("¿Qué está mostrando el gráfico?"):
                    st.markdown('En este gráfico podrás el promedio de superficie construida para las propiedades que coincidan con el filtro de la izquierda', 
                unsafe_allow_html=True)
                superficie_barrio = filtro.groupby('barrio')['superficie_construida'].mean().sort_values()
                fig5 = px.bar(superficie_barrio, title='superficie_construida promedio por barrio')
                st.plotly_chart(fig5, use_container_width=True, key="eda_fig5")

            if 'num_habitaciones' in filtro.columns:
                st.subheader("Precio según número de habitaciones")
                with st.expander("¿Qué está mostrando el gráfico?"):
                    st.markdown('En este gráfico podrás ver el precio medio según las habitaciones elegidas en el filtro de la izquierda', 
                unsafe_allow_html=True)
                fig6 = px.box(filtro, x='num_habitaciones', y='price_eur', title='Precio por número de habitaciones')
                st.plotly_chart(fig6, use_container_width=True, key="eda_fig6")

            if 'num_banos' in filtro.columns:
                st.subheader("Distribución de número de baños")
                with st.expander("¿Qué está mostrando el gráfico?"):
                    st.markdown('En este gráfico podrás ver el precio el número de baños para las propiedades que coincidan con el filtro de la izquierda', 
                unsafe_allow_html=True)
                fig7 = px.histogram(filtro, x='num_banos', nbins=10, title='Distribución de baños')
                st.plotly_chart(fig7, use_container_width=True, key="eda_fig7")

            if 'planta' in filtro.columns:
                st.subheader("Precio por planta")
                with st.expander("¿Qué está mostrando el gráfico?"):
                    st.markdown('En este gráfico podrás ver el precio medio según la planta en el barrio elegido en el filtro de la izquierda', 
                unsafe_allow_html=True)
                fig8 = px.box(filtro, x='planta', y='price_eur', title='Precio según planta')
                st.plotly_chart(fig8, use_container_width=True, key="eda_fig8")

            if 'estado' in filtro.columns:
                st.subheader("Distribución del estado de las propiedades")
                with st.expander("¿Qué está mostrando el gráfico?"):
                    st.markdown('En este gráfico podrás ver la antiguedad de las propiedades para el barrio elegido en el filtro de la izquierda', 
                unsafe_allow_html=True)               
                fig9 = px.histogram(filtro, x='estado', title='Estado de las propiedades')
                st.plotly_chart(fig9, use_container_width=True, key="eda_fig9")



# ---------------------------
# SECCIÓN PREDICTIVO
# ---------------------------
    elif f['section'] == 'Predictivo':
        st.title("")

        bin_map = {'Sí': 1, 'No': 0}

        # Selección de archivos según tipo de operación
        if f['tipo_operacion'] == 'venta':
            model_file = 'modelo_rf_regressor.pkl'
            classifier_file = 'sale_property_classifier.pkl'
        else:
            model_file = 'modelo_renta_entrenado.pkl'
            classifier_file = 'rental_property_classifier.pkl'

        # Cargar modelos y encoders
        try:
            # Cargar modelo de clúster
            with open(classifier_file, 'rb') as f_clf:
                classifier = pickle.load(f_clf)

            # Cargar encoders
            with open('le_distrito.pkl', 'rb') as f_le_dist:
                le_distrito = pickle.load(f_le_dist)

            with open('le_antiguedad.pkl', 'rb') as f_le_ant:
                le_antiguedad = pickle.load(f_le_ant)

            # Cargar modelo de precio
            with open(model_file, 'rb') as f_reg:
                reg_data = pickle.load(f_reg)
                model = reg_data['model']

        except Exception as e:
            st.error(f"No se pudo cargar el modelo o encoder: {e}")
            st.stop()

            # Mapeo manual de antigüedad 
        map_antiguedad = {
            0: "Obra nueva",
            1: "Menos de 10 años",
            2: "Entre 10 y 20 años",
            3: "Entre 20 y 50 años",
            4: "Más de 50 años"
        }
        inv_map_antiguedad = {v: k for k, v in map_antiguedad.items()}

        with st.form('form_prediccion'):
            st.markdown("Introduce las características de tu inmueble:")

            superficie_construida = st.number_input('Superficie construida (m²)', min_value=10, max_value=1000, value=70)
            baños = st.number_input('Número de baños', min_value=0, max_value=10, value=1)

            distrito = st.selectbox('Selecciona el distrito', sorted(le_distrito.classes_))
            habitaciones = st.number_input('Número de habitaciones', min_value=1, max_value=8, value=2)

            planta_opciones = ['Bajo', '1ª', '2ª', '3ª', '4ª', '5ª', '6ª', '7ª', '8ª', '9ª', '10ª o más']
            planta_numerica_str = st.selectbox('Planta numérica', planta_opciones)
            planta_numerica = 0 if planta_numerica_str == 'Bajo' else 10 if planta_numerica_str == '10ª o más' else int(planta_numerica_str[:-1])

            exterior = st.selectbox('Exterior', ['Sí', 'No'])

            antiguedad_opciones = list(map_antiguedad.values())
            antiguedad = st.selectbox('Antigüedad', antiguedad_opciones)

            terraza = st.selectbox('Terraza', ['Sí', 'No'])
            garaje = st.selectbox('Garaje', ['Sí', 'No'])
            calefaccion = st.selectbox('Calefacción', ['Sí', 'No'])

            submitted_pred = st.form_submit_button('Predecir precio')

        if submitted_pred:
            try:
                distrito_encoded = le_distrito.transform([distrito])[0]
                antiguedad_encoded = inv_map_antiguedad.get(antiguedad, -1)

                input_data = pd.DataFrame([{
                    "superficie_construida": superficie_construida,
                    "banos": baños,
                    "distrito_encoded": distrito_encoded,
                    "habitaciones": habitaciones,
                    "planta_numerica": planta_numerica,
                    "exterior": bin_map[exterior],
                    "antiguedad_encoded": antiguedad_encoded,
                    "terraza": bin_map[terraza],
                    "garaje": bin_map[garaje],
                    "calefaccion": bin_map[calefaccion]
                }])

                cluster = classifier.predict(input_data)[0]
                cluster_label_map = {
                    0: "",
                    1: "",
                    2: "",
                    3: "",
                    4: ""
                }
                cluster_label = cluster_label_map.get(cluster, "Desconocido")
                st.info(f" Esta propiedad pertenece al grupo: **{cluster} - {cluster_label}**")

                precio_pred = model.predict(input_data)[0]
                st.success(f"💶 Precio estimado: **{precio_pred:,.2f} €**")

            except Exception as e:
                st.error(f"Error durante la predicción: {e}")

        # Tabla de clústeres de ventas
        clusters_venta = pd.DataFrame({
            "Etiqueta": [
                "Piso Señorial Clásico",
                "Apartamento Estándar",
                "Propiedad Singular (Outlier)",
                "Lujo Moderno (Full Equip)",
                "Premium Reformado"
            ],
            "Características Clave": [
                "Grande, precio elevado, finca antigua, con ascensor, pero sin piscina/garaje.",
                "El más económico, tamaño reducido y menos extras. El apartamento 'típico' de Madrid.",
                "Anomalía. Extremadamente grande y caro. (Se recomienda excluir del entrenamiento del clasificador).",
                "El más caro, grande, obra nueva o reciente, y equipado con piscina, garaje y terraza.",
                "Precio elevado, ubicación prime, finca antigua pero reformado y amueblado."
            ]
        })

        # Tabla de clústeres de alquiler
        clusters_alquiler = pd.DataFrame({
            "Etiqueta": [
                "Residencial Familiar con Extras",
                "Piso Básico y Económico",
                "Apartamento Céntrico Amueblado",
                "Vivienda de Lujo Exclusivo",
                "Apartamento Premium (Ubicación Prime)"
            ],
            "Características Clave": [
                "Grande, precio elevado, nuevo, en urbanización con piscina y garaje.",
                "El más barato, ubicación menos céntrica, pequeño, antiguo y con pocos extras (sin amueblar).",
                "Tamaño mediano/pequeño, 100% amueblado, en barrios de alquiler alto, con ascensor.",
                "El más caro y grande, ubicación y calidades de lujo, con todos los extras.",
                "Precio elevado, ubicación prime, excelente estado (reformado/nuevo), exterior y con ascensor."
            ]
        })

        with st.expander("Leyenda de cases de inmuebles(clusters)"):
            st.markdown("### Clústeres de Propiedades en Venta")
            st.dataframe(clusters_venta, use_container_width=True)

            st.markdown("### Clústeres de Propiedades en Alquiler")
            st.dataframe(clusters_alquiler, use_container_width=True)

        with st.expander("¿Qué son los clústeres de propiedades? (clases)"):
            st.markdown("""
        Los clústeres son grupos de propiedades con características similares. Elegidos así por la inteligencia artificial que predice el precio de tu vivienda. Puede que tu vivienda no se ajuste al 100% al clúster asignado, pero seguro que se asemeja mucho y te dará una idea de cómo son los precios de los demás inmuebles con características parecidas.
        
        **¿Cómo se asignan estos clústeres y por qué?**
        
        Los clústeres se asignan a través del modelo que, tras un estudio de los datos más relevantes para predecir el precio (feature importance), nos dice las características más comunes entre las propiedades parecidas a la tuya. Por eso alguna característica puede ser algo distinta, pero la mayoría serán correctas.
        
        Si tienes interés, podrás estudiar el porqué de estos clústeres y la feature importance en la sección de detalles técnicos de la página principal.
        """, unsafe_allow_html=True)


if __name__ == '__main__':
    main()
