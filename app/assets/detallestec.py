import streamlit as st
from PIL import Image

st.set_page_config(page_title="Detalles Técnicos", layout="wide")

st.title("🔧 Detalles Técnicos del Proyecto")

st.markdown("""
En esta sección se presentan resultados detallados de los modelos utilizados en los distintos clústeres de viviendas.
""")

# Imagen de resultados de métricas por modelo y clúster
st.subheader("📊 Comparativa de Modelos por Clúster")
imagen_resultados = Image.open("comparativoclusventas.jpg")
st.image(imagen_resultados, caption="Resultados de evaluación de modelos por clúster", use_column_width=True)

# Puedes seguir añadiendo más secciones e imágenes:
# st.subheader("Otro resultado")
# st.image("ruta/a/otra_imagen.png", caption="Descripción")

