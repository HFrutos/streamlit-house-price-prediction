DROP DATABASE realestate;
CREATE DATABASE IF NOT EXISTS realestate;

USE realestate;

/* 1. Ubicación */
DROP TABLE IF EXISTS location;
CREATE TABLE location (
  location_id     INT AUTO_INCREMENT PRIMARY KEY,
  barrio          VARCHAR(120),
  distrito        VARCHAR(120),
  latitude        DECIMAL(10,7),
  longitude       DECIMAL(10,7),
  INDEX idx_lat_lon (latitude, longitude) 
);

--  UNIQUE (latitude, longitude) puede romperse si hay más de una vivienda 
-- en el mismo edificio (misma lat/lon).
-- ALTER TABLE location DROP INDEX ux_lat_lon,
                     -- ADD INDEX idx_lat_lon (latitude, longitude);

/* 2. Vivienda física */
-- guardo aqui las variables opcionales, pero 
-- tengo que revisar para guardar aquellas que tengan 
-- muchos nulos o ceros en la tabla catalogo de extras 
DROP TABLE IF EXISTS property;
CREATE TABLE property (
  property_id     INT AUTO_INCREMENT PRIMARY KEY,
  location_id     INT NOT NULL,
  property_native_id VARCHAR(40) NULL, -- rental tiene referencia, sale no
  superficie_construida DECIMAL(8,2),
  superficie_util      DECIMAL(8,2),
  habitaciones         TINYINT,
  banos                TINYINT,
  planta               SMALLINT,
  antiguedad_raw       VARCHAR(60),
  estado_conservacion  VARCHAR(60),
  
  -- lista de atributos booleanos que revisar 
  ascensor              BOOLEAN,
  balcon                BOOLEAN,
  calefaccion           BOOLEAN,
  chimenea              BOOLEAN,
  exterior              BOOLEAN,
  garaje                BOOLEAN,
  piscina               BOOLEAN,
  trastero              BOOLEAN,
  jardin                BOOLEAN,
  adaptado_pmreducida   BOOLEAN,
  aire_acondicionado    BOOLEAN,
  amueblado             ENUM('no','semi','si'),
  puerta_blindada       BOOLEAN,
  vidrios_dobles        BOOLEAN,
  cocina_equipada       VARCHAR(200),
  sistema_seguridad     BOOLEAN,
  terraza               BOOLEAN,
  
  UNIQUE KEY ux_native_id (property_native_id),
  CONSTRAINT fk_property_location
      FOREIGN KEY (location_id) REFERENCES location(location_id)
        ON DELETE CASCADE
);


/* 3. Anuncio */
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


/* 4. Histórico económico */
DROP TABLE IF EXISTS economic_history;
CREATE TABLE economic_history (
  listing_id     INT NOT NULL,
  captured_at    DATETIME(3) NOT NULL,
  price_value    DECIMAL(15,2),
  price_kind     ENUM('sale_price','rent_month') NOT NULL,
  price_unit     ENUM('EUR') NOT NULL,
  PRIMARY KEY (listing_id, captured_at),
  CONSTRAINT fk_econ_listing
      FOREIGN KEY (listing_id) REFERENCES listing(listing_id)
        ON DELETE CASCADE
);


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
  consumo_value    DECIMAL(8,2),
  emisiones_rating CHAR(1),
  emisiones_value  DECIMAL(8,2),
  CONSTRAINT fk_cert_property
      FOREIGN KEY (property_id) REFERENCES property(property_id)
		ON DELETE CASCADE
);


/* 7. Catálogo de extras */
DROP TABLE IF EXISTS feature_catalog;
CREATE TABLE feature_catalog (
  feature_id   INT AUTO_INCREMENT PRIMARY KEY,
  nombre       VARCHAR(100) UNIQUE
);

DROP TABLE IF EXISTS property_feature;
CREATE TABLE property_feature (
  property_id  INT,
  feature_id   INT,
  valor        VARCHAR(40),
  PRIMARY KEY (property_id, feature_id),
  CONSTRAINT fk_pf_property  FOREIGN KEY (property_id)  REFERENCES property(property_id) ON DELETE CASCADE,
  CONSTRAINT fk_pf_feature   FOREIGN KEY (feature_id)   REFERENCES feature_catalog(feature_id) 
);


