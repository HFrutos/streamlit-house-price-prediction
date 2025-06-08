import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit.components.v1 as components
import os
from streamlit_folium import folium_static
import folium
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

        st.subheader('Pisos que coinciden con tu búsqueda')
        st.markdown(f'**{len(filtro)} pisos encontrados**')

        if filtro.empty:
            st.warning('No hay resultados para los filtros seleccionados.')
            return

        filtro_reset = filtro.reset_index()
        seleccion_ids = st.multiselect(
            'Selecciona pisos para comparar',
            options=filtro_reset.index,
            format_func=lambda i: f'ID {filtro_reset.at[i, "id"]} - {filtro_reset.at[i, "price_eur"]:,.0f} €'
            if 'id' in filtro_reset.columns else f'Piso {i + 1} - {filtro_reset.at[i, "price_eur"]:,.0f} €',
            key="comparar_pisos"
        )

        if seleccion_ids:
            st.subheader('Comparativa de pisos seleccionados')
            st.dataframe(filtro_reset.loc[seleccion_ids])

        filtro = filtro.dropna(subset=['lat', 'lon'])
        st.metric('Precio medio', f'{filtro["price_eur"].mean():,.0f} €')

        # Aquí la opción para cambiar modo de búsqueda y cargar el mapa desde URL
        modo_busqueda = st.sidebar.radio('Modo de búsqueda', ['Individual', 'Por zona'])

        # Cargar mapa desde URL
        m = folium.Map(location=[40.4168, -3.7038], zoom_start=12)

        for _, row in filtro.iterrows():
            folium.Marker(
                location=[row['lat'], row['lon']],
                popup=f"Precio: {row['price_eur']:,} €<br>Habitaciones: {row['habitaciones']}",
                icon=folium.Icon(color='blue', icon='home')
            ).add_to(m)

        st.title("Mapa interactivo de pisos en Madrid")
        folium_static(m)

#cargar mapa desde local
#       archivo_mapa = mapas_urls[tipo_operacion][modo_busqueda]
#        try:
#            with open(archivo_mapa, 'r', encoding='utf-8') as f:
#                mapa_html = f.read()
#            st.components.v1.html(mapa_html, width=1000, height=600, scrolling=True)
#        except Exception as e:
#            st.error(f"No se pudo cargar el mapa desde el archivo: {e}")

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
        ruta_radar = f'radar_{tipo_operacion}.jpg'
        if os.path.exists(ruta_radar):
            st.image(ruta_radar, 
                    caption=f'Análisis de características - {tipo_operacion.capitalize()}',
                    use_column_width=True)
        else:
            st.error(f"Archivo no encontrado: {ruta_radar}")

if __name__ == '__main__':
    main()
