#explico el código para que podamos aprender de los "cabezazos que me he ido dando". A mí me sirve para reutilizar.

import streamlit as st
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