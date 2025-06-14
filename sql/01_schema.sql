-- ============================================================================
-- 01_schema.sql
-- ============================================================================
-- Propósito:
--   Definir la base de datos MySQL “realestate” con el esquema normalizado
--   preparado para almacenar inmuebles de venta y alquiler extraídos de pisos.com,
--   junto con su histórico de precios/rentas, certificados energéticos y extras.
--
--   Este archivo incluye comentarios que justifican cada decisión de diseño
--   y explica cómo encaja con el proceso de carga de datos que se hará
--   posteriormente desde Python usando mysql.connector.
--

-- Creacion y seleccion de base de datos
CREATE DATABASE IF NOT EXISTS realestate;
USE realestate;

-- 1. Ubicación
--    • Almacena cada punto geográfico (latitud/longitud) UNA sola vez.
--    • Racionalización 3FN: evita repetir coordenadas en cada propiedad.
--    • Se crea índice UNIQUE en (latitude, longitude) para upserts rápidos.
CREATE TABLE location (
  location_id     INT AUTO_INCREMENT PRIMARY KEY,
  barrio          VARCHAR(120),
  distrito        VARCHAR(120),
  latitude        DECIMAL(9,6),
  longitude       DECIMAL(9,6),
  UNIQUE KEY ux_lat_lon (latitude, longitude)
);


-- 2. Vivienda física

--    • Representa la vivienda “física” con atributos casi inmutables.
--    • FK a location: cada propiedad está en una sola ubicación.
--    • property_native_id: clave natural que trae pisos.com (ej. 51740663097.108900).
--    • ON DUPLICATE KEY UPDATE usado en ETL para actualizar atributos si cambian.
CREATE TABLE property (
  property_id     INT AUTO_INCREMENT PRIMARY KEY,
  location_id     INT NOT NULL,
  property_native_id VARCHAR(40) NOT NULL,
  superficie_construida DECIMAL(8,2),
  superficie_util      DECIMAL(8,2),
  habitaciones         TINYINT,
  banos                TINYINT,
  planta               VARCHAR(20),
  orientacion          VARCHAR(30),
  antiguedad_raw       VARCHAR(60),
  estado_conservacion  VARCHAR(60),
  ascensor             BOOLEAN,
  garaje               BOOLEAN,
  piscina              BOOLEAN,
  trastero             BOOLEAN,
  jardin               BOOLEAN,
  UNIQUE KEY ux_native_id (property_native_id),
  CONSTRAINT fk_property_location
      FOREIGN KEY (location_id) REFERENCES location(location_id)
);


-- 3. Anuncio
--    • Cada fila representa un anuncio concreto de una propiedad en pisos.com.
--    • listing_type indica si es ‘sale’ o ‘rental’.
--    • portal por defecto 'pisos.com' (valor fijo hoy, preparada para multi‐portal).
--    • URL única: UNIQUE(url) permite upsert por URL.
CREATE TABLE listing (
  listing_id     INT AUTO_INCREMENT PRIMARY KEY,
  property_id    INT NOT NULL,
  url            TEXT NOT NULL,
  portal         VARCHAR(30)  DEFAULT 'pisos.com',
  listing_type   ENUM('sale','rental') NOT NULL,
  scraped_at     DATETIME(3),
  scrape_status  VARCHAR(40),
  descripcion    MEDIUMTEXT,
  UNIQUE KEY ux_url (url(255)),            -- se recorta para claves
  CONSTRAINT fk_listing_property
      FOREIGN KEY (property_id) REFERENCES property(property_id)
);


-- 4. Histórico económico
--    • Hecho rápido: registra cada cambio de precio o renta en el tiempo.
--    • PK compuesta (listing_id, captured_at) evita duplicar el mismo snapshot.
--    • price_kind discrimina venta (‘sale_price’) vs. renta (‘rent_month’).
--    • price_unit siempre 'EUR' después de convertir €/m² → € totales en ETL.
CREATE TABLE economic_history (
  listing_id     INT NOT NULL,
  captured_at    DATETIME(3) NOT NULL,
  price_value    DECIMAL(15,2),
  price_kind     ENUM('sale_price','rent_month') NOT NULL,
  price_unit     ENUM('EUR','EUR_M2') NOT NULL,
  surface_used   DECIMAL(8,2),
  PRIMARY KEY (listing_id, captured_at),
  CONSTRAINT fk_econ_listing
      FOREIGN KEY (listing_id) REFERENCES listing(listing_id)
);


-- 5. Condiciones de alquiler 

--    • Detalles específicos de los anuncios de alquiler.
--    • Evita llenar listing de columnas nulas en venta.
CREATE TABLE rental_term (
  listing_id           INT PRIMARY KEY,
  furnished            BOOLEAN,
  deposit_months       DECIMAL(5,2),
  guarantee_months     DECIMAL(5,2),
  min_duration_months  SMALLINT,
  max_duration_months  SMALLINT,
  pets_allowed         BOOLEAN,
  availability_date    DATE,
  CONSTRAINT fk_rental_listing
      FOREIGN KEY (listing_id) REFERENCES listing(listing_id)
);


-- 6. Certificado energético 

--    • Etiqueta energética de la vivienda (1-1 con property).
CREATE TABLE energy_certificate (
  property_id INT PRIMARY KEY,
  classification   VARCHAR(40),
  consumo_rating   VARCHAR(10),
  consumo_value    DECIMAL(8,2),
  emisiones_rating VARCHAR(10),
  emisiones_value  DECIMAL(8,2),
  CONSTRAINT fk_cert_property
      FOREIGN KEY (property_id) REFERENCES property(property_id)
);


-- 7. Catálogo de extras 
-- • feature_catalog: catálogo de posibles extras (piscina, chimenea…).
-- • property_feature: tabla puente N-M que asigna valores a cada extra.
CREATE TABLE feature_catalog (
  feature_id   INT AUTO_INCREMENT PRIMARY KEY,
  nombre       VARCHAR(100) UNIQUE
);

CREATE TABLE property_feature (
  property_id  INT,
  feature_id   INT,
  valor        VARCHAR(40),
  PRIMARY KEY (property_id, feature_id),
  CONSTRAINT fk_pf_property  FOREIGN KEY (property_id)  REFERENCES property(property_id),
  CONSTRAINT fk_pf_feature   FOREIGN KEY (feature_id)   REFERENCES feature_catalog(feature_id)
);


-- 8. HTML crudo 
-- • Página HTML completa de cada anuncio (1-1 con listing).
-- • Útil para auditoría y reprocesos de scraping.
CREATE TABLE raw_html (
  listing_id  INT PRIMARY KEY,
  scraped_at  DATETIME(3),
  page_source LONGTEXT,
  CONSTRAINT fk_html_listing
      FOREIGN KEY (listing_id) REFERENCES listing(listing_id)
);