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
DROP DATABASE pisos3;
CREATE DATABASE IF NOT EXISTS pisos3;
USE pisos3;

-- Limpieza de las tablas (orden inverso de dependencias)
DROP TABLE IF EXISTS property_feature;
DROP TABLE IF EXISTS feature_catalog;
DROP TABLE IF EXISTS energy_certificate;
DROP TABLE IF EXISTS rental_term;
DROP TABLE IF EXISTS listing;
DROP TABLE IF EXISTS property;
DROP TABLE IF EXISTS age_range;
DROP TABLE IF EXISTS location;


-- Comprobacion de la insercion de las tablas 
-- SELECT * FROM age_range;
-- SELECT * FROM feature_catalog;
-- SELECT * FROM location;
-- SELECT * FROM property;
-- SELECT * FROM listing;
-- SELECT * FROM rental_term;
-- SELECT * FROM energy_certificate;

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

-- 2.1 Categorias conservacion
-- Catálogo de categorias del estado de conservacion de un inmueble 
-- 
CREATE TABLE conservation (
    state_id INT AUTO_INCREMENT PRIMARY KEY,
    state VARCHAR(20)
);

-- 2.2 Categorias del estado del certificado de clasificacion energetico
-- 
CREATE TABLE energy_classification (
	cert_id INT AUTO_INCREMENT PRIMARY KEY,
    state VARCHAR(25)
);

-- 3. Vivienda física 
-- Almacena las características invariables de cada inmueble.
-- Latitud/longitud para búsquedas geoespaciales, FK a ubicación, FK a antigüedad.
-- Atributos booleanos/enum pasan luego a property_feature para evitar muchos NULL.
--
DROP TABLE property;
CREATE TABLE property (
  property_id     INT AUTO_INCREMENT PRIMARY KEY,
  location_id     INT NOT NULL,
  
  latitude             DECIMAL(10,7),
  longitude            DECIMAL(10,7),
  INDEX idx_prop_lat_lon (latitude, longitude),
  
  property_native_id VARCHAR(60) UNIQUE, -- este deberia ser el identificador 
  superficie_construida DECIMAL(8,2), -- m^2
  superficie_util      DECIMAL(8,2), -- m^2
  habitaciones         TINYINT,
  banos                TINYINT,
  planta               SMALLINT,
  estado_conservacion  VARCHAR(60), --
  age_range_id         INT,

  -- lista de atributos booleanos que pasar a Feature 
--  ascensor              BOOLEAN,
--  balcon                BOOLEAN,
--  calefaccion           BOOLEAN,
--  chimenea              BOOLEAN,
--  exterior              BOOLEAN,
--  garaje                BOOLEAN,
--  piscina               BOOLEAN,
--  trastero              BOOLEAN,
--  jardin                BOOLEAN,
--  adaptado_pmreducida   BOOLEAN,
--  aire_acondicionado    BOOLEAN,
--  amueblado             ENUM('no','semi','si'), -- mirar que hacer con esta, quiza hacer otra tabla
--  puerta_blindada       BOOLEAN,
--  vidrios_dobles        BOOLEAN,
--  cocina_equipada       VARCHAR(200), -- la dejamos aqui de momento porque no parece booleano
--  sistema_seguridad     BOOLEAN,
--  terraza               BOOLEAN,
  
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
DROP TABLE listing;
CREATE TABLE listing (
  listing_id     INT AUTO_INCREMENT PRIMARY KEY,
  property_id    INT NOT NULL,
--  portal         VARCHAR(30)  DEFAULT 'pisos.com', -- SE PUEDE BORRAR SI TODOS SON DEL MISMO PORTAL
  url 			 varchar(120),
  listing_type   ENUM('sale','rental') NOT NULL, -- tipo de anuncio, necesario?
  
  price_kind     ENUM('sale_price','rent_month') NOT NULL,
  price_eur      DECIMAL(14,2)                   NOT NULL, -- precio que aparece en el anuncio, ya sea de alquiler o venta 

  scraped_at     DATETIME(3),
  scrape_status  VARCHAR(40),

  description TEXT,
  
  INDEX idx_list_type_price (listing_type, price_eur),
  CONSTRAINT fk_listing_property
        FOREIGN KEY (property_id) REFERENCES property(property_id)
        ON DELETE CASCADE
);

-- se han borrado estas columnas porque no se disponía de 
-- esta informacion, seguramente se añadan
-- ALTER TABLE listing
--  DROP COLUMN scraped_at,
--  DROP COLUMN scrape_status;


/* 4. Histórico económico */ 
-- si el precio y la fecha de revision lo guardo en listing, esta tabla no tiene sentido
-- tendría sentido si consultamos varios portales
-- DROP TABLE IF EXISTS economic_history; 
-- CREATE TABLE economic_history (
--  listing_id     INT NOT NULL,
--  captured_at    DATETIME(3) NOT NULL,
--  price_value    DECIMAL(15,2),
--  price_kind     ENUM('sale_price','rent_month') NOT NULL,
--  price_unit     ENUM('EUR') NOT NULL,
--  PRIMARY KEY (listing_id, captured_at),
--  CONSTRAINT fk_econ_listing
--      FOREIGN KEY (listing_id) REFERENCES listing(listing_id)
--        ON DELETE CASCADE
-- );


-- 5. Condiciones de alquiler (opcional)
-- Si se dispone de datos de alquiler (fianza, mascotas, duración...),
-- van aquí. Si no se usan, la tabla puede quedar vacía o eliminarse.
--
-- DROP TABLE IF EXISTS rental_term;
-- CREATE TABLE rental_term (
--  listing_id           INT PRIMARY KEY,
-- furnished            BOOLEAN,
--  deposit_months       DECIMAL(5,2),
--  guarantee_months     DECIMAL(5,2),
--  min_duration_months  SMALLINT,
--  max_duration_months  SMALLINT,
--  pets_allowed         BOOLEAN,
--  availability_date    DATE,
--  CONSTRAINT fk_rental_listing
--      FOREIGN KEY (listing_id) REFERENCES listing(listing_id)
--        ON DELETE CASCADE
-- );


-- 6. Certificado energético
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
-- no disponemos de valor, puede que si sea añadido 
-- ALTER TABLE energy_certificate
--  DROP COLUMN classification;


-- 7. Catálogo de extras (Features)
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
