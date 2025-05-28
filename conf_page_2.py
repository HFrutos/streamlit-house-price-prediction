import streamlit as st
import pandas as pd
import pydeck as pdk

# Configuración de la página
st.set_page_config(
    page_title="house-price-prediction",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="collapsed",
    menu_items={
        'Get help': 'https://docs.streamlit.io',
        'Report a bug': 'https://github.com/streamlit/streamlit/issues',
        'About': "### Streamlit App - Información\nEsta aplicación está creada con Streamlit."
    }
)

# Leer CSV
df = pd.read_csv("parafrank.csv")

# Sidebar
st.sidebar.title("Predictivo de Precios")
metros = st.sidebar.slider("Metros cuadrados", 20, 200, 70)
habitaciones = st.sidebar.slider("Habitaciones", 1, 5, 2)
barrio = st.sidebar.multiselect("Barrio", df["barrio"].dropna().unique())
tipo = st.sidebar.selectbox("Tipo de operación", df["tipo_de_operacion"].dropna().unique())

# Menú para cambiar de pestaña
seccion = st.sidebar.selectbox("Selecciona la sección", ["Mapa de pisos", "Métricas"])

def main():
    if seccion == "Mapa de pisos":
        st.title("Mapa de pisos en Madrid")

        # Filtro según los parámetros
        filtro = df[
            (df["tipo_de_operacion"] == tipo) &
            (df["Superficie construida"] >= metros) &
            (df["Habitaciones"] == habitaciones) &
            (df["barrio"].isin(barrio))
        ]

        st.subheader("Pisos que coinciden con tu búsqueda")
        st.markdown(f"**{len(filtro)} pisos encontrados**")
        st.dataframe(filtro)

        filtro = filtro.dropna(subset=["lat", "lon"])

        if not filtro.empty:
            st.metric(" Precio medio", f"{filtro['price_eur'].mean():,.0f} €")

            st.subheader("Mapa interactivo de pisos en Madrid")
            layer = pdk.Layer(
                'ScatterplotLayer',
                data=filtro,
                get_position='[lon, lat]',
                get_radius=50,
                get_fill_color='[200, 30, 0, 160]',
                pickable=True
            )

            view_state = pdk.ViewState(
                latitude=filtro["lat"].mean(),
                longitude=filtro["lon"].mean(),
                zoom=11,
                pitch=0
            )

            tooltip = {
                "html": "<b>Precio:</b> {price_eur} €<br><b>Habitaciones:</b> {Habitaciones}",
                "style": {"backgroundColor": "steelblue", "color": "white"}
            }

            st.pydeck_chart(pdk.Deck(layers=[layer], initial_view_state=view_state, tooltip=tooltip))
        else:
            st.warning("No hay resultados para los filtros seleccionados.")

    elif seccion == "Métricas":
        st.title("Métricas de los Pisos")

    filtro = df[
        (df["tipo_de_operacion"] == tipo) &
        (df["Superficie construida"] >= metros) &
        (df["Habitaciones"] == habitaciones) &
        (df["barrio"].isin(barrio))   # <-- usar .isin() aquí
    ]

    if filtro.empty:
        st.warning("No hay datos para los filtros seleccionados.")
    else:
        st.metric("Precio medio (€)", f"{filtro['price_eur'].mean():,.0f}")
        st.metric("Superficie media (m²)", f"{filtro['Superficie construida'].mean():.1f}")
        st.metric("Número de barrios", filtro["barrio"].nunique())
        st.metric("Máximo de habitaciones", filtro["Habitaciones"].max())

        st.subheader("Distribución de precios por barrio")
        st.bar_chart(filtro.groupby("barrio")["price_eur"].mean().sort_values())

if __name__ == "__main__":
    main()


