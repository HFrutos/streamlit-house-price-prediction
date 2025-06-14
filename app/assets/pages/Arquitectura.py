import streamlit as st

# Opcional: cada página puede tener su propio page_title
st.set_page_config(page_title="Arquitectura", page_icon="🗄️")

st.title("🗄️ Arquitectura de la Base de Datos")

st.markdown("""
En esta página tienes toda la documentación de tu modelo relacional.

---

## 1. Tabla `location`
Almacena barrios y distritos para normalizar la ubicación.

| Columna     | Tipo               | PK/FK | Descripción                         |
|-------------|--------------------|-------|-------------------------------------|
| location_id | INT AUTO_INCREMENT | PK    | ID único de la ubicación            |
| barrio      | VARCHAR(120)       |       | Nombre del barrio                   |
| distrito    | VARCHAR(120)       |       | Nombre del distrito                 |

---

## 2. Tabla `age_range`
Catálogo de rangos de edad de la edificación.

| Columna      | Tipo                | PK/FK | Descripción                               |
|--------------|---------------------|-------|-------------------------------------------|
| age_range_id | INT AUTO_INCREMENT  | PK    | ID único del rango                        |
| label        | VARCHAR(60) NOT NULL|       | Descripción (p.ej. “0–5 años”, “>50 años”)|

---

## 3. Tabla `conservation`
Catálogo de estados de conservación.

| Columna  | Tipo                | PK/FK | Descripción                        |
|----------|---------------------|-------|------------------------------------|
| state_id | INT AUTO_INCREMENT  | PK    | ID de la categoría                 |
| state    | VARCHAR(20)         |       | Texto descriptivo (“nuevo”, “uso”)|

---

## 4. Tabla `energy_classification`
Catálogo de categorías energéticas.

| Columna | Tipo                | PK/FK | Descripción                    |
|---------|---------------------|-------|--------------------------------|
| cert_id | INT AUTO_INCREMENT  | PK    | ID de la categoría             |
| state   | VARCHAR(25)         |       | Letra/rango (“A”, “B”, …)      |

---

## 5. Tabla `property`
Características físicas e invariables de cada inmueble.

| Columna                   | Tipo              | PK/FK                              | Descripción                                      |
|---------------------------|-------------------|------------------------------------|--------------------------------------------------|
| property_id               | INT AUTO_INCREMENT| PK                                 | ID interno                                       |
| location_id               | INT               | FK → location(location_id)         | Barrio / distrito                                |
| age_range_id              | INT               | FK → age_range(age_range_id)       | Rango de antigüedad                              |
| latitude, longitude       | DECIMAL(10,7)     |                                    | Coordenadas GPS                                   |
| property_native_id        | VARCHAR(60)       | UNIQUE                             | ID original en el portal                         |
| superficie_construida     | DECIMAL(8,2)      |                                    | m² construidos                                   |
| superficie_util           | DECIMAL(8,2)      |                                    | m² útiles                                        |
| habitaciones              | TINYINT           |                                    | Nº dormitorios                                   |
| banos                     | TINYINT           |                                    | Nº baños                                         |
| planta                    | SMALLINT          |                                    | Planta del inmueble                              |
| estado_conservacion       | VARCHAR(60)       |                                    | Texto libre (podría ligarse a `conservation`)    |

---

## 6. Tabla `listing`
Anuncios vinculados a propiedades, con precio y scrapeo.

| Columna       | Tipo                          | PK/FK                              | Descripción                              |
|---------------|-------------------------------|------------------------------------|------------------------------------------|
| listing_id    | INT AUTO_INCREMENT            | PK                                 | ID del anuncio                           |
| property_id   | INT                           | FK → property(property_id)         | Inmueble asociado                        |
| url           | VARCHAR(120)                  |                                    | Enlace al anuncio                        |
| listing_type  | ENUM('sale','rental')        |                                    | Tipo: venta o alquiler                   |
| price_kind    | ENUM('sale_price','rent_month') |                                  | Unidad del precio                        |
| price_eur     | DECIMAL(14,2)                |                                    | Importe en euros                         |
| scraped_at    | DATETIME(3)                  |                                    | Fecha/hora de captura                    |
| scrape_status | VARCHAR(40)                  |                                    | Estado del proceso de scrapeo           |
| description   | TEXT                         |                                    | Descripción libre                        |

---

## 7. Tabla `energy_certificate`
Certificado energético por propiedad (1:1).

| Columna           | Tipo            | PK/FK                              | Descripción                          |
|-------------------|-----------------|------------------------------------|--------------------------------------|
| property_id       | INT             | PK, FK → property(property_id)     | ID de la propiedad                   |
| classification    | VARCHAR(40)     |                                    | Texto libre de la clasificación      |
| consumo_rating    | CHAR(1)         |                                    | Letra de consumo (A…G)               |
| emisiones_rating  | CHAR(1)         |                                    | Letra de emisiones (A…G)             |
| emision_value     | DECIMAL(9,3)    |                                    | Valor numérico de emisiones          |
| consumption_value | DECIMAL(9,3)    |                                    | Valor numérico de consumo            |

---

## 8. Tabla `feature_catalog`
Catálogo de “extras” (piscina, garaje…).

| Columna    | Tipo               | PK/FK            | Descripción                       |
|------------|--------------------|------------------|-----------------------------------|
| feature_id | INT AUTO_INCREMENT | PK               | ID de la característica           |
| nombre     | VARCHAR(100)       | UNIQUE           | Nombre del extra                  |

---

## 9. Tabla `property_feature`
Unión *–*–* EAV de propiedades y sus extras.

| Columna     | Tipo       | PK/FK                                    | Descripción                     |
|-------------|------------|------------------------------------------|---------------------------------|
| property_id | INT        | PK, FK → property(property_id)           | Inmueble                        |
| feature_id  | INT        | PK, FK → feature_catalog(feature_id)     | Extra                           |
| valor       | VARCHAR(40)|                                          | Valor libre si aplica (p.ej. “sí”)|

---

### Relaciones principales
- **location** 1––* **property**  
- **age_range** 1––* **property**  
- **property** 1––* **listing**  
- **property** 1––1 **energy_certificate**  
- **feature_catalog** *––* **property** (vía **property_feature**)  
""", unsafe_allow_html=True)