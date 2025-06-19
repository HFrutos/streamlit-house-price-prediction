-- ============================================================================
-- 01_schema.sql
-- ============================================================================
-- Propósito:
--   Definir la base de datos MySQL “pisos4” con el esquema normalizado
--   preparado para almacenar inmuebles de venta y alquiler extraídos de pisos.com,
--   junto con sus características principales, certificados energéticos y extras.
--
--   Este archivo incluye comentarios que justifican cada decisión de diseño
--   y explica cómo encaja con el proceso de carga de datos que se hará
--   posteriormente desde Python usando mysql.connector.
--

-- Creacion y seleccion de base de datos
CREATE DATABASE IF NOT EXISTS pisos4;
USE pisos4;

-- Limpieza de las tablas (orden inverso de dependencias)
DROP TABLE IF EXISTS property_feature;
DROP TABLE IF EXISTS feature_catalog;
DROP TABLE IF EXISTS energy_certificate;
DROP TABLE IF EXISTS listing;
DROP TABLE IF EXISTS property;
DROP TABLE IF EXISTS age_range;
DROP TABLE IF EXISTS location;



-- 1. Ubicación 
-- Catálogo de barrios y distritos, reutilizable por muchas propiedades.
-- Separamos la geografía en su propia entidad para evitar duplicar texto.
--

CREATE TABLE location (
  location_id     INT AUTO_INCREMENT PRIMARY KEY,
  barrio          VARCHAR(120),
  distrito        VARCHAR(120)
);


-- 2. Rangos de antigüedad
-- Catálogo de intervalos de años de construcción.
-- Separamos los textos descriptivos para no repetirlos en cada propiedad.
--
CREATE TABLE age_range (
  age_range_id  INT AUTO_INCREMENT PRIMARY KEY,
  label         VARCHAR(60) NOT NULL UNIQUE
);


-- 3. Vivienda física 
-- Almacena las características invariables de cada inmueble.
-- Latitud/longitud para búsquedas geoespaciales, FK a ubicación, FK a antigüedad.
-- Atributos booleanos/enum se encuentran en property_feature para evitar muchos NULL.
--
CREATE TABLE property (
  property_id     INT AUTO_INCREMENT PRIMARY KEY, -- es mas ligero para hacer los joins 
  location_id     INT NOT NULL,
  
  latitude             DECIMAL(10,7),
  longitude            DECIMAL(10,7),
  INDEX idx_prop_lat_lon (latitude, longitude),
  
  property_native_id VARCHAR(60) UNIQUE, -- nos asegura que cada propiedad es unica 
  superficie_construida DECIMAL(8,2), -- m^2
  superficie_util      DECIMAL(8,2), -- m^2
  habitaciones         TINYINT,
  banos                TINYINT,
  planta               DECIMAL(3,1), -- presuelo con valor 0.5
  estado_conservacion  VARCHAR(60), 
  age_range_id         INT,
  
  CONSTRAINT fk_property_location
      FOREIGN KEY (location_id) REFERENCES location(location_id)
        ON DELETE CASCADE,
    CONSTRAINT fk_property_age 
	  FOREIGN KEY(age_range_id) REFERENCES age_range(age_range_id)
);


-- 4. Anuncio 
-- Cada anuncio vinculado a una propiedad; guarda tipo (sale/rental) y precio.
-- Las columnas de scrapeo se han eliminado porque no se dispone de ese dato.
-- 
CREATE TABLE listing (
  listing_id     INT AUTO_INCREMENT PRIMARY KEY,
  property_id    INT NOT NULL,
  url 			 varchar(120),  
  price_kind     ENUM('sale_price','rent_month') NOT NULL,
  price_eur      DECIMAL(14,2)                   NOT NULL, -- precio que aparece en el anuncio, ya sea de alquiler o venta 

  scraped_at     DATETIME(3),
  scrape_status  VARCHAR(40),

  description TEXT,

  CONSTRAINT fk_listing_property
        FOREIGN KEY (property_id) REFERENCES property(property_id)
        ON DELETE CASCADE
);


-- 5. Certificado energético
-- Rating de consumo y emisiones por propiedad. NULL si no se conoce.
--
CREATE TABLE energy_certificate (
  property_id INT PRIMARY KEY,
  classification   VARCHAR(40),
  consumo_rating   CHAR(1),
  emisiones_rating CHAR(1),
  emision_value DECIMAL(9,3),
  consumption_value DECIMAL(9,3),
  CONSTRAINT fk_cert_property
      FOREIGN KEY (property_id) REFERENCES property(property_id)
		ON DELETE CASCADE
);


-- 6. Catálogo de extras (Features)
-- Modelo EAV ligero: definimos el catálogo y luego la tabla de unión.
--
CREATE TABLE feature_catalog (
  feature_id   INT AUTO_INCREMENT PRIMARY KEY,
  nombre       VARCHAR(100) NOT NULL UNIQUE
);


CREATE TABLE property_feature (
  property_id  INT,
  feature_id   INT,
  valor        VARCHAR(40), -- este valor realmente hace falta?
  PRIMARY KEY (property_id, feature_id),
  CONSTRAINT fk_pf_property  FOREIGN KEY (property_id)  REFERENCES property(property_id) ON DELETE CASCADE,
  CONSTRAINT fk_pf_feature   FOREIGN KEY (feature_id)   REFERENCES feature_catalog(feature_id) 
);

-- insertar en el notebook
-- estos serán los valores de feature_catalog
--
-- INSERT INTO feature_catalog(nombre) VALUES
--  ('ascensor'),
--  ('balcon'),
--  ('calefaccion'),
--  ('chimenea'),
--  ('exterior'),
--  ('garaje'),
--  ('piscina'),
--  ('trastero'),
--  ('jardin'),
--  ('adaptado_pmreducida'),
--  ('aire_acondicionado'),
--  ('puerta_blindada'),
--  ('vidrios_dobles'),
--  ('sistema_seguridad'),
--  ('terraza');
