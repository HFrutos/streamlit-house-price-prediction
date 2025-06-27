import streamlit as st
import graphviz


st.set_page_config(page_title="Arquitectura", page_icon="🗄️")

st.title("🗄️ Arquitectura de la Base de Datos")

st.markdown("""
En esta página se muestra toda la documentación del modelo relacional, no solo las tablas utilizadas sino también las columnas y la importancia de las mismas.

---

## 1. Tabla `location`
Almacena barrios y distritos para normalizar la ubicación,reutilizable por muchas propiedades.
Separamos la geografía en su propia entidad para evitar duplicar texto.

| Columna     | Tipo               | PK/FK | Descripción                         |
|-------------|--------------------|-------|-------------------------------------|
| location_id | INT AUTO_INCREMENT | PK    | ID único de la ubicación            |
| barrio      | VARCHAR(120)       |       | Nombre del barrio                   |
| distrito    | VARCHAR(120)       |       | Nombre del distrito                 |

---

## 2. Tabla `age_range`
Catálogo de intervalos de años de construcción.
Separamos los textos descriptivos para no repetirlos en cada propiedad.

| Columna      | Tipo                | PK/FK | Descripción                               |
|--------------|---------------------|-------|-------------------------------------------|
| age_range_id | INT AUTO_INCREMENT  | PK    | ID único del rango                        |
| label        | VARCHAR(60) NOT NULL|       | Descripción (p.ej. “0–5 años”, “>50 años”)|

---

## 3. Tabla `conservation`
Catálogo de categorias del estado de conservacion de un inmueble. 

| Columna  | Tipo                | PK/FK | Descripción                        |
|----------|---------------------|-------|------------------------------------|
| state_id | INT AUTO_INCREMENT  | PK    | ID de la categoría                 |
| state    | VARCHAR(20)         |       | Texto descriptivo (“nuevo”, “uso”)|

---

## 4. Tabla `energy_classification`
Categorias del estado del certificado de clasificacion energetico

| Columna | Tipo                | PK/FK | Descripción                    |
|---------|---------------------|-------|--------------------------------|
| cert_id | INT AUTO_INCREMENT  | PK    | ID de la categoría             |
| state   | VARCHAR(25)         |       | Texto descriptivo ("Disponible", "En trámite", …)      |

---

## 5. Tabla `property`
Características físicas e invariables de cada inmueble.
Almacena las características invariables de cada inmueble, además de ser las columnas que usaremos para el modelo.
Latitud/longitud para búsquedas geoespaciales, FK a ubicación, FK a antigüedad.
Atributos booleanos/enum pasan a property_feature para evitar muchos NULL.

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
Cada anuncio vinculado a una propiedad, guarda tipo (sale/rental) y precio.
En caso de querer escalar el proyecto a mas portales se podría añadir aquí, además de cambiar la relación entre el anuncio y la propiedad.

             

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
Rating de consumo y emisiones por propiedad. NULL si no se conoce.  

| Columna           | Tipo            | PK/FK                              | Descripción                          |
|-------------------|-----------------|------------------------------------|--------------------------------------|
| property_id       | INT             | PK, FK → property(property_id)     | ID de la propiedad                   |
| classification    | VARCHAR(40)     |                                    | Texto sobre el certificado de clasificación      |
| consumo_rating    | CHAR(1)         |                                    | Letra de consumo (A…G)               |
| emisiones_rating  | CHAR(1)         |                                    | Letra de emisiones (A…G)             |
| emision_value     | DECIMAL(9,3)    |                                    | Valor numérico de emisiones          |
| consumption_value | DECIMAL(9,3)    |                                    | Valor numérico de consumo            |

---

## 8. Tabla `feature_catalog`
Catálogo de “extras” (piscina, garaje…).
Hay características que no se encuentran en todos los inmuebles, como puede ser el tener piscina, jardín, puerta blindada, sistema de seguridad, permitir mascotas...
Esta tabla contiene dichos servicios/categorías.

| Columna    | Tipo               | PK/FK            | Descripción                       |
|------------|--------------------|------------------|-----------------------------------|
| feature_id | INT AUTO_INCREMENT | PK               | ID de la característica           |
| nombre     | VARCHAR(100)       | UNIQUE           | Nombre del extra                  |

---

## 9. Tabla `property_feature`
Unión *–*–* EAV de propiedades y sus extras.
Para no almacenar muchos nulos se almacenarán solo los valores True o que contengan información relevante.
La mayoría de valores son booleanos pero algunas categorías como gastos comunidad (numero decimal) y orientacion (abreviatura de los puntos cardinales) contienen un valor. 
            
| Columna     | Tipo       | PK/FK                                    | Descripción                     |
|-------------|------------|------------------------------------------|---------------------------------|
| property_id | INT        | PK, FK → property(property_id)           | Inmueble                        |
| feature_id  | INT        | PK, FK → feature_catalog(feature_id)     | Extra                           |
| valor       | VARCHAR(40)|                                          | Valor según la categoría (p.ej. “True”, '{N}', "0.0")|

- Esta mezcla de tipos de valores no es recomendada ni lo usual, tabla sujeta a la practicidad a la hora de utilizarla. 
---

### Relaciones principales
- **location** 1––* **property**  
- **age_range** 1––* **property**  
- **property** 1––* **listing**  
- **property** 1––1 **energy_certificate**  
- **feature_catalog** *––* **property** (vía **property_feature**)  

---

### Diagrama entidad relacion 
            
            
""", unsafe_allow_html=True)

# Diagrama en sintaxis DOT
dot = """
digraph ERD {
  rankdir=LR;
  node [shape = record, fontname="Helvetica"];

  location [ label = 
    "{ location | {location_id PK\\l barrio\\l distrito\\l} }" ];
  age_range [ label =
    "{ age_range | {age_range_id PK\\l label\\l} }" ];
  property [ label =
    "{ property | {property_id PK\\l location_id FK\\l age_range_id FK\\l latitude\\l longitude\\l property_native_id\\l superficie_construida\\l superficie_util\\l habitaciones\\l banos\\l planta\\l estado_conservacion\\l} }" ];
  listing [ label =
    "{ listing | {listing_id PK\\l property_id FK\\l url\\l listing_type\\l price_kind\\l price_eur\\l scraped_at\\l scrape_status\\l description\\l} }" ];
  energy_certificate [ label =
    "{ energy_certificate | {property_id PK/FK\\l classification\\l consumo_rating\\l emisiones_rating\\l emision_value\\l consumption_value\\l} }" ];
  feature_catalog [ label =
    "{ feature_catalog | {feature_id PK\\l nombre\\l} }" ];
  property_feature [ label =
    "{ property_feature | {property_id PK/FK\\l feature_id PK/FK\\l valor\\l} }" ];

  // Relaciones
  location       -> property          [ label="1:N", arrowhead=none ];
  age_range      -> property          [ label="1:N", arrowhead=none ];
  property       -> listing           [ label="1:N", arrowhead=none ];
  property       -> energy_certificate[ label="1:1", arrowhead=none ];
  property       -> property_feature  [ label="1:N", arrowhead=none ];
  feature_catalog-> property_feature  [ label="1:N", arrowhead=none ];
}
"""

st.graphviz_chart(graphviz.Source(dot))


st.markdown("""
            
---
            
### Airtable
           
Finalmente para poder desplegar la aplicación en remoto, se ha optado por alojar todos los datos en la plaforma Airtable, que nos permite crear una base de datos  en remoto. Esto nos permite acceder a los datos sin tener que crear una copia de la base de datos en local mejorando la accesibilidad.       
""", unsafe_allow_html=True)