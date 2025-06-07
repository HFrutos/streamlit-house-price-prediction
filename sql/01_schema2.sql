DROP DATABASE pisos2;
CREATE DATABASE IF NOT EXISTS pisos2;
USE pisos2;

-- Limpieza de las tablas
DROP TABLE IF EXISTS property_feature;
DROP TABLE IF EXISTS feature_catalog;
DROP TABLE IF EXISTS energy_certificate;
DROP TABLE IF EXISTS rental_term;
DROP TABLE IF EXISTS listing;
DROP TABLE IF EXISTS property;
DROP TABLE IF EXISTS age_range;
DROP TABLE IF EXISTS location;

SELECT * FROM age_range;
SELECT * FROM feature_catalog;
SELECT * FROM location;
SELECT * FROM property;
SELECT * FROM listing;
SELECT * FROM rental_term;
SELECT * FROM energy_certificate;

/* 1. Ubicación */
DROP TABLE IF EXISTS location;
CREATE TABLE location (
  location_id     INT AUTO_INCREMENT PRIMARY KEY,
  barrio          VARCHAR(120),
  distrito        VARCHAR(120)
);


SELECT * FROM location;

-- 2. Rangos de antigüedad
CREATE TABLE age_range (
  age_range_id  INT AUTO_INCREMENT PRIMARY KEY,
  label         VARCHAR(60) NOT NULL UNIQUE
);

-- insertar en el notebook para tener 
-- toda esta parte alli 
INSERT INTO age_range(label) VALUES
  ('Más de 50 años'),
  ('Entre 20 y 30 años'),
  ('Entre 30 y 50 años'),
  ('Entre 5 y 10 años'),
  ('Menos de 5 años'),
  ('Entre 10 y 20 años');

/* 3. Vivienda física */

DROP TABLE IF EXISTS property;
CREATE TABLE property (
  property_id     INT AUTO_INCREMENT PRIMARY KEY,
  location_id     INT NOT NULL,
  
  latitude             DECIMAL(10,7),
  longitude            DECIMAL(10,7),
  INDEX idx_prop_lat_lon (latitude, longitude),
  
  property_native_id VARCHAR(60) UNIQUE, -- rental tiene referencia, sale no
  superficie_construida DECIMAL(8,2),
  superficie_util      DECIMAL(8,2),
  habitaciones         TINYINT,
  banos                TINYINT,
  planta               SMALLINT,
  estado_conservacion  VARCHAR(60),
  age_range_id          INT,

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
  amueblado             ENUM('no','semi','si'), -- mirar que hacer con esta, quiza hacer otra tabla
--  puerta_blindada       BOOLEAN,
--  vidrios_dobles        BOOLEAN,
  cocina_equipada       VARCHAR(200), -- la dejamos aqui de momento porque no parece booleano
--  sistema_seguridad     BOOLEAN,
--  terraza               BOOLEAN,
  
  CONSTRAINT fk_property_location
      FOREIGN KEY (location_id) REFERENCES location(location_id)
        ON DELETE CASCADE,
    CONSTRAINT fk_property_age 
	  FOREIGN KEY(age_range_id) REFERENCES age_range(age_range_id)
);


/* 4. Anuncio */
DROP TABLE IF EXISTS listing;
CREATE TABLE listing (
  listing_id     INT AUTO_INCREMENT PRIMARY KEY,
  property_id    INT NOT NULL,
--  portal         VARCHAR(30)  DEFAULT 'pisos.com', -- SE PUEDE BORRAR SI TODOS SON DEL MISMO PORTAL
  listing_type   ENUM('sale','rental') NOT NULL,
  
  price_kind     ENUM('sale_price','rent_month') NOT NULL,
  price_current  DECIMAL(14,2)                   NOT NULL, -- precio que aparece en el anuncio, ya sea de alquiler o venta
														   -- para busquedas rapidas 

  scraped_at     DATETIME(3),
  scrape_status  VARCHAR(40),

  INDEX idx_list_type_price (listing_type, price_current),
  CONSTRAINT fk_listing_property
        FOREIGN KEY (property_id) REFERENCES property(property_id)
        ON DELETE CASCADE
);

ALTER TABLE listing
  DROP COLUMN scraped_at,
  DROP COLUMN scrape_status;


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


/* 5. Condiciones de alquiler */
DROP TABLE IF EXISTS rental_term;
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
        ON DELETE CASCADE
);


/* 6. Certificado energético */
DROP TABLE IF EXISTS energy_certificate;
CREATE TABLE energy_certificate (
  property_id INT PRIMARY KEY,
  classification   VARCHAR(40),
  consumo_rating   CHAR(1),
  emisiones_rating CHAR(1),
  CONSTRAINT fk_cert_property
      FOREIGN KEY (property_id) REFERENCES property(property_id)
		ON DELETE CASCADE
);
ALTER TABLE energy_certificate
  DROP COLUMN classification;

/* 7. Catálogo de extras */
DROP TABLE IF EXISTS feature_catalog;
CREATE TABLE feature_catalog (
  feature_id   INT AUTO_INCREMENT PRIMARY KEY,
  nombre       VARCHAR(100) NOT NULL UNIQUE
);

DROP TABLE IF EXISTS property_feature;
CREATE TABLE property_feature (
  property_id  INT,
  feature_id   INT,
  valor        VARCHAR(40), -- este valor realmente hace falta?
  PRIMARY KEY (property_id, feature_id),
  CONSTRAINT fk_pf_property  FOREIGN KEY (property_id)  REFERENCES property(property_id) ON DELETE CASCADE,
  CONSTRAINT fk_pf_feature   FOREIGN KEY (feature_id)   REFERENCES feature_catalog(feature_id) 
);

-- insertar en el notebook
INSERT INTO feature_catalog(nombre) VALUES
  ('ascensor'),
  ('balcon'),
  ('calefaccion'),
  ('chimenea'),
  ('exterior'),
  ('garaje'),
  ('piscina'),
  ('trastero'),
  ('jardin'),
  ('adaptado_pmreducida'),
  ('aire_acondicionado'),
  ('puerta_blindada'),
  ('vidrios_dobles'),
  ('sistema_seguridad'),
  ('terraza');
