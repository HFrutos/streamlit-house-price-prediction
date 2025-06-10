#explico el código para que podamos aprender de los "cabezazos que me he ido dando". A mí me sirve para reutilizar.

import streamlit as stimport streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit.components.v1 as components
import os
from streamlit_folium import folium_static
import folium
from folium import Map
from folium.plugins import MarkerCluster
import requests

# Configuración de la página
st.set_page_config(
    page_title='house-price-prediction',
    page_icon='🏠',
    layout='wide',
    initial_sidebar_state='collapsed',
    menu_items={
        'Get help': 'https://docs.streamlit.io',
        'Report a bug': 'https://github.com/streamlit/streamlit/issues',
        'About': '### Streamlit App - Información\nEsta aplicación está creada con Streamlit.'
    }
)

# Leer csv´s
df_venta = pd.read_csv('madrid_sale_properties_cleaned.csv')
df_alquiler = pd.read_csv('madrid_rental_properties_cleaned.csv')

 # Foto monete (despues hay que mover cosicas al final del selector del sidebar)
if 'submitted' not in st.session_state:
    col1, col2, col3 = st.columns([1,3,1])
    with col2:
        st.image("orangutan.png", 
                caption="¡Selecciona los parámetros en el sidebar de la izquierda! →", 
                width=400)  
    
# Sidebar
with st.sidebar.form("filtros_formulario"):
    st.markdown("Vista y comparación de inmuebles")

    tipo_operacion = st.selectbox('Tipo de operación', ['venta', 'alquiler'])
    metros = st.slider('Metros cuadrados', 20, 600, 70)
    habitaciones = st.slider('Habitaciones', 1, 8, 2)

    # Barrios
    todos_barrios = sorted(df_venta['barrio'].dropna().unique() if tipo_operacion == 'venta' else df_alquiler['barrio'].dropna().unique())
    opcion_barrios = ['Todos'] + todos_barrios
    barrios_filtrados = st.multiselect(
        'Barrios elegidos', 
        opcion_barrios, 
        default=['Todos'],
        key='barrios_selector'
    )

    # Antigüedad
    df_temp = df_venta if tipo_operacion == 'venta' else df_alquiler
    if 'antigüedad' in df_temp.columns:
        opciones_antiguedad = df_temp['antigüedad'].dropna().unique()
        antiguedad_sel = st.multiselect('Antigüedad elegida', opciones_antiguedad, default=opciones_antiguedad)
    else:
        antiguedad_sel = []

    # Sección
    seccion = st.selectbox('Selecciona la sección', ['Mapa de pisos', 'Métricas', 'Gráficas'])

   

    # Botón para aplicar filtros
    submitted = st.form_submit_button("Aplicar filtros", on_click=lambda: st.session_state.update({"submitted": True}))
if 'submitted' in st.session_state and st.session_state.submitted:
    df = df_venta if tipo_operacion == 'venta' else df_alquiler
else:
    st.stop()

df = df_venta if tipo_operacion == 'venta' else df_alquiler


# Diccionario con URLs de los mapas HTML
mapas_urls = {
    'venta': {
        'Individual': 'madrid_individual_properties_map_sale.html',
        'Por zona': 'madrid_property_count_map_sale.html'
    },
    'alquiler': {
        'Individual': 'madrid_individual_properties_map_rental.html',
        'Por zona': 'madrid_property_count_map_rental.html'
    }
}
# Diccionario con las rutas de los archivos HTML para los gráficos radar
radar_html_files = {
    'venta': 'radar_venta.html',
    'alquiler': 'radar_alquiler.html'
}


def main():
    filtro = df[
        (df['superficie construida'] >= metros) &
        (df['habitaciones'] == habitaciones) ] #nos permite filtrar el dataframe según los parámetros seleccionados
    # Filtrar por barrios (manejar caso "Todos")
    if 'Todos' in barrios_filtrados or not barrios_filtrados:
        # para que "todos esté elgido por defecto y seleccione todos los barrios"
        pass
    else:
        barrios_a_filtrar = [b for b in barrios_filtrados if b != 'Todos']
        if barrios_a_filtrar:
            filtro = filtro[filtro['barrio'].isin(barrios_a_filtrar)]
    if antiguedad_sel and 'antigüedad' in df.columns:
        filtro = filtro[filtro['antigüedad'].isin(antiguedad_sel)] #nos añade la antigüedad a la selección

#mapas 

    if seccion == 'Mapa de pisos':
        st.title('Mapa de pisos en Madrid')
        modo_busqueda = st.radio('Modo de búsqueda', ['Individual', 'Por zona'], horizontal=True)
        
        st.subheader('Pisos que coinciden con tu búsqueda')
        st.markdown(f'**{len(filtro)} pisos encontrados**')

        if filtro.empty:
            st.warning('No hay resultados para los filtros seleccionados.')
        else:
            filtro = filtro.dropna(subset=['lat', 'lon'])
            filtro = filtro[(filtro['lat'].between(-90, 90)) & (filtro['lon'].between(-180, 180))]
            
            m = folium.Map(location=[40.4168, -3.7038], zoom_start=12)
            
            # sustituir aquí (y el mapa creado)
            if modo_busqueda == 'Individual':
                marker_cluster = MarkerCluster().add_to(m)
                for _, row in filtro.iterrows():
                    folium.Marker(
                        location=[row['lat'], row['lon']],
                        popup=f"""
                            <b>Precio:</b> {row['price_eur']:,} €<br>
                            <b>Habitaciones:</b> {row['habitaciones']}<br>
                            <b>m²:</b> {row['superficie construida']}<br>
                            <b>Barrio:</b> {row['barrio']}
                        """,
                        icon=folium.Icon(color='blue', icon='home')
                    ).add_to(marker_cluster)
            
            folium_static(m, width=800, height=600)

#sustotuir desde aquí
#        mapa_url = mapas_urls.get(tipo_operacion, {}).get(modo_busqueda)
#
#        if mapa_url:
#            st.subheader(f'Mapa: {modo_busqueda.lower()} - {tipo_operacion}')
#            # Mostrar el HTML del mapa
#            with open(mapa_url, 'r', encoding='utf-8') as f:
#                components.html(f.read(), height=600, scrolling=True)
#        else:
#            st.error('No se encontró el mapa para la combinación seleccionada.')
            
#    if seccion == 'Mapa de pisos':
#        st.title('Mapa de pisos en Madrid')
#        modo_busqueda = st.radio('Modo de búsqueda', ['Individual', 'Por zona'], horizontal=True)
#        
#        st.subheader('Pisos que coinciden con tu búsqueda')
#        st.markdown(f'**{len(filtro)} pisos encontrados**')
#
#        if filtro.empty:
#            st.warning('No hay resultados para los filtros seleccionados.')
#        else:
#            # Verificación y limpieza de coordenadas
#            filtro = filtro.dropna(subset=['lat', 'lon'])
#            filtro = filtro[(filtro['lat'].between(-90, 90)) & (filtro['lon'].between(-180, 180))]
#-------------------------------------------------------------------------------------------------------            

            
#Métricas

    elif seccion == 'Métricas':
        st.title('Métricas de los Pisos')

        if filtro.empty:
            st.warning('No hay datos para los filtros seleccionados.')
        else:
            st.metric('Número de barrios con las características seleccionadas', filtro['barrio'].nunique())
            st.metric('Máximo de habitaciones seleccionadas', filtro['habitaciones'].max())
            st.metric('Número de pisos seleccionados', len(filtro))
            st.metric('Máximo de metros cuadrados seleccionados (m²)', f'{metros:.1f}')
            if 'energy_consumption_rating' in filtro.columns and not filtro['energy_consumption_rating'].dropna().empty:
                st.metric('Rating energético más frecuente', filtro['energy_consumption_rating'].mode()[0])
            else:
                st.info("No hay datos suficientes sobre rating energético.")

            st.subheader('Precio y superficie media por barrio')
            medias = filtro.groupby('barrio')[['price_eur', 'superficie construida']].mean().sort_values('price_eur')
            st.dataframe(medias.rename(columns={'price_eur': 'Precio medio (€)','superficie construida': 'Superficie media (m²)'}).style.format({
                'Precio medio (€)': '{:,.0f} €',
                'Superficie media (m²)': '{:.1f}'
        }))

        st.subheader('Precio por barrio')
        fig = px.bar(filtro.groupby('barrio')['price_eur'].mean().sort_values().reset_index(),x='barrio', y='price_eur', title='Precio medio por barrio')
        st.plotly_chart(fig)
        
# gráficas
    elif seccion == 'Gráficas':
        st.title('Visualización de datos')

        if filtro.empty:
            st.warning('No hay datos para los filtros seleccionados.')
            return

        st.subheader('Histograma de precios con outliers resaltados')
        q1 = filtro['price_eur'].quantile(0.25)
        q3 = filtro['price_eur'].quantile(0.75)
        iqr = q3 - q1
        outlier_threshold = q3 + 1.5 * iqr

        fig1 = px.histogram(filtro, x='price_eur', nbins=30,
                            title='Distribución de precios (outliers en rojo)',
                            color_discrete_sequence=['lightblue'])

        outliers = filtro[filtro['price_eur'] > outlier_threshold]
        fig1.add_trace(go.Histogram(x=outliers['price_eur'],
                                    marker_color='red'))
        st.plotly_chart(fig1)

        st.subheader('Precio por metro cuadrado por barrio')
        if 'superficie construida' in filtro.columns:
            filtro = filtro.copy()
            filtro['precio_m2'] = filtro['price_eur'] / filtro['superficie construida']
            fig2 = px.box(filtro, x='barrio', y='precio_m2',
                          title='Precio por m² por barrio')
            fig2.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig2)

        st.subheader('Relación entre precio y antigüedad')
        if 'antigüedad' in filtro.columns and 'price_eur' in filtro.columns:
            filtro['antigüedad'] = filtro['antigüedad'].fillna('Desconocida').astype(str)
            fig3 = px.box(filtro, x='antigüedad', y='price_eur', title='Boxplot de precio por antigüedad')
            fig3.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig3)
        else:
            st.error('Parámetros incorrectos para graficar antigüedad.')

        # Imagenes radar

# Reemplazo para el gráfico radar
    st.subheader('Análisis de características')
    
    # Verificar si existe el archivo HTML correspondiente
    radar_file = radar_html_files.get(tipo_operacion)
    if radar_file and os.path.exists(radar_file):
        try:
            with open(radar_file, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            # Mostrar el contenido HTML con un contenedor de tamaño adecuado
            st.components.v1.html(html_content, height=500, scrolling=False)
            
        except Exception as e:
            st.error(f"Error al cargar el gráfico interactivo: {str(e)}")
            # Opcional: Mostrar versión estática de respaldo si existe
            ruta_radar_jpg = f'radar_{tipo_operacion}.jpg'
            if os.path.exists(ruta_radar_jpg):
                st.image(ruta_radar_jpg, 
                        caption=f'Versión estática - {tipo_operacion.capitalize()}',
                        use_column_width=True)
    else:
        st.error(f"No se encontró el archivo HTML interactivo para {tipo_operacion}")

if __name__ == '__main__':
    main()
import pandas as pd
import pydeck as pdk
import plotly.express as px
import plotly.graph_objects as go

# Configuración de la página
st.set_page_config(
    page_title='house-price-prediction',
    page_icon='🏠',
    layout='wide',
    initial_sidebar_state='collapsed',
    menu_items={
        'Get help': 'https://docs.streamlit.io',
        'Report a bug': 'https://github.com/streamlit/streamlit/issues',
        'About': '### Streamlit App - Información\nEsta aplicación está creada con Streamlit.'
    }
)

# Leer csv´s
df_venta = pd.read_csv('madrid_sale_properties_cleaned.csv')
df_alquiler = pd.read_csv('madrid_rental_properties_cleaned.csv')

# Sidebar
st.sidebar.title('Predictivo de Precios')
tipo_operacion = st.sidebar.selectbox('Tipo de operación', ['venta', 'alquiler'])

df = df_venta if tipo_operacion == 'venta' else df_alquiler #Si no esventa tiene que ser alquiler

# Parámetros del sidebar
metros = st.sidebar.slider('Metros cuadrados', 20, 600, 70) # Rango de metros cuadrados entre 20 y 600, valor por defecto 70
habitaciones = st.sidebar.slider('Habitaciones', 1, 8, 2) # Rango de habitaciones entre 1 y 8, valor por defecto 2

# Selección de barrios con opción 'Todos'
todos_barrios = sorted(df['barrio'].dropna().unique()) # Ordenamos los barrios para que aparezcan en orden alfabético
opcion_barrios = ['Todos'] + todos_barrios # Añadimos la opción 'Todos' al principio de la lista (con la función de arriba)
barrio_seleccionado = st.sidebar.multiselect('Barrio', opcion_barrios, default=['Todos'])

if 'Todos' in barrio_seleccionado or not barrio_seleccionado: # Si se selecciona 'Todos' o no se selecciona ningún barrio
    barrios_filtrados = todos_barrios
else:
    barrios_filtrados = barrio_seleccionado

# Selección de antigüedad, igual que barrios pero con antigúedad

if 'antigüedad' in df.columns:
    opciones_antiguedad = df['antigüedad'].dropna().unique()
    antiguedad_sel = st.sidebar.multiselect('antigüedad', opciones_antiguedad, default=opciones_antiguedad)
else:
    antiguedad_sel = []

# Menú de sección

seccion = st.sidebar.selectbox('Selecciona la sección', ['Mapa de pisos', 'Métricas', 'Gráficas'])

def main():
    filtro = df[
        (df['superficie construida'] >= metros) &
        (df['habitaciones'] == habitaciones) &
        (df['barrio'].isin(barrios_filtrados))
    ] #nos permite filtrar el dataframe según los parámetros seleccionados
    if antiguedad_sel and 'antigüedad' in df.columns:
        filtro = filtro[filtro['antigüedad'].isin(antiguedad_sel)] #nos añade la antigüedad a la selección

    if seccion == 'Mapa de pisos': # Si la sección seleccionada es 'Mapa de pisos'
        st.title('Mapa de pisos en Madrid')

        st.subheader('Pisos que coinciden con tu búsqueda')
        st.markdown(f'**{len(filtro)} pisos encontrados**')

        if filtro.empty:
            st.warning('No hay resultados para los filtros seleccionados.')
            return

        filtro_reset = filtro.reset_index() #da las opciones de pisos que entran en los parametros seleccionados
        seleccion_ids = st.multiselect(
            'Selecciona pisos para comparar',
            options=filtro_reset.index,
            format_func=lambda i: f'ID {filtro_reset.at[i, "id"]} - {filtro_reset.at[i, "price_eur"]:,.0f} €'
            if 'id' in filtro_reset.columns else f'Piso {i + 1} - {filtro_reset.at[i, "price_eur"]:,.0f} €'
        )

        if seleccion_ids:
            st.subheader('Comparativa de pisos seleccionados')
            st.dataframe(filtro_reset.loc[seleccion_ids])

        filtro = filtro.dropna(subset=['lat', 'lon']) # Elimina filas sin coordenadas geográficas
        st.metric('Precio medio', f'{filtro["price_eur"].mean():,.0f} €') # Calcula el precio medio de los pisos filtrados

        st.subheader('Mapa interactivo de pisos en Madrid') # Muestra un mapa interactivo de los pisos filtrados
        layer = pdk.Layer(
            'ScatterplotLayer',
            data=filtro,
            get_position='[lon, lat]',
            get_radius=50,
            get_fill_color='[200, 30, 0, 160]',
            pickable=True
        )

        view_state = pdk.ViewState(
            latitude=filtro['lat'].mean(),
            longitude=filtro['lon'].mean(),
            zoom=11,
            pitch=0
        )

        tooltip = {
            'html': '<b>Precio:</b> {price_eur} €<br><b>Habitaciones:</b> {habitaciones}',
            'style': {'backgroundColor': 'steelblue', 'color': 'white'}
        }

        st.pydeck_chart(pdk.Deck(layers=[layer], initial_view_state=view_state, tooltip=tooltip))

    elif seccion == 'Métricas':
        st.title('Métricas de los Pisos')

        if filtro.empty:
            st.warning('No hay datos para los filtros seleccionados.')
        else:
            st.metric('Número de barrios con las características seleccionadas', filtro['barrio'].nunique()) # número de barrios que cumplen los filtros
            st.metric('Máximo de habitaciones seleccionadas', filtro['habitaciones'].max()) # habitaciones máximas seleccionadas
            st.metric('Número de pisos seleccionados', len(filtro)) # número de pisos que cumplen los filtros
            st.metric('Máximo de metros cuadrados seleccionados (m²)', f'{metros:.1f}') # metros cuadrados máximos seleccionados
            st.metric('Rating energético más frecuente', filtro['energy_consumption_rating'].mode()[0]) # rating energético

            st.subheader('Precio y superficie media por barrio')
            medias = filtro.groupby('barrio')[['price_eur', 'superficie construida']].mean().sort_values('price_eur')
            st.dataframe(medias.rename(columns={
                'price_eur': 'Precio medio (€)',
                'superficie construida': 'Superficie media (m²)'
            }).style.format({
                'Precio medio (€)': '{:,.0f} €',
                'Superficie media (m²)': '{:.1f}'
            }))

            st.subheader('Distribución de precios por barrio')
            fig = px.bar(filtro.groupby('barrio')['price_eur'].mean().sort_values().reset_index(),
                        x='barrio', y='price_eur', title='Precio medio por barrio')
            st.plotly_chart(fig)

    elif seccion == 'Gráficas': #sección de gráficas nos da las gráficas según los filtros seleccionados
        st.title('Visualización de datos')

        if filtro.empty:
            st.warning('No hay datos para los filtros seleccionados.')
            return

        st.subheader('Histograma de precios con outliers resaltados')
        q1 = filtro['price_eur'].quantile(0.25)
        q3 = filtro['price_eur'].quantile(0.75)
        iqr = q3 - q1
        outlier_threshold = q3 + 1.5 * iqr
        
        fig1 = px.histogram(filtro, x='price_eur', nbins=30,
                          title='Distribución de precios (outliers en rojo)',
                          color_discrete_sequence=['lightblue'])
        
        # Añadir outliers en rojo
        outliers = filtro[filtro['price_eur'] > outlier_threshold]
        fig1.add_trace(go.Histogram(x=outliers['price_eur'],
                      marker_color='red'))
        st.plotly_chart(fig1)

        st.subheader('Precio por metro cuadrado por barrio')
        if 'superficie construida' in filtro.columns:
            filtro['precio_m2'] = filtro['price_eur'] / filtro['superficie construida']
            fig2 = px.box(filtro, x='barrio', y='precio_m2',
                         title='Precio por m² por barrio')
            fig2.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig2)

        st.subheader('Relación entre precio y antigüedad')
        if 'antigüedad' in filtro.columns:
            fig3 = px.box(filtro, x='antigüedad', y='price_eur',
                         title='Boxplot de precio por antigüedad')
            fig3.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig3)

if __name__ == '__main__':
    main()
