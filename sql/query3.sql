USE pisos4;

SELECT * FROM age_range;

SELECT * FROM location;

SELECT * FROM property;

SELECT * FROM listing;

SELECT DISTINCT(price_kind) 
FROM listing;

SELECT *
FROM listing
WHERE price_kind = "sale_price";

SELECT * FROM energy_certificate;

SELECT * FROM property_feature;

SELECT * 
FROM property_feature
WHERE feature_id = 19;

SELECT * FROM feature_catalog;

SELECT * FROM listing
WHERE scrape_status = "Removed";

DELETE FROM location
 WHERE location_id = 271
   AND barrio  IS NULL
   AND distrito IS NULL;
   
SELECT ROW_COUNT(); -- para confirmar que has borrado 1 fila
COMMIT;

SELECT * 
FROM location
WHERE location_id = 271;


-- Número total de listings en CSV vs en la BD:
SELECT COUNT(*) FROM listing;
-- Ver los primeros 10 listings:
SELECT * FROM listing ORDER BY scraped_at DESC LIMIT 10;
-- Listar algunas propiedades y su ubicación:
SELECT p.property_id, p.property_native_id, l.barrio, l.distrito
  FROM property p
  JOIN location l ON p.location_id = l.location_id
  LIMIT 10;
-- Ver features de una propiedad concreta:
SELECT pf.property_id, fc.nombre
  FROM property_feature pf
  JOIN feature_catalog fc ON pf.feature_id = fc.feature_id
  WHERE pf.property_id = 10;
  
  
  SELECT COUNT(*) AS total_listings,
       COUNT(DISTINCT url) AS distinct_urls
  FROM listing;
  
  SELECT url, COUNT(*) AS cnt
  FROM listing
 GROUP BY url
HAVING cnt > 1
 ORDER BY cnt DESC
 LIMIT 10;
 
 
 DELETE l1
  FROM listing l1
  JOIN listing l2 
    ON l1.url = l2.url 
   AND l1.scraped_at < l2.scraped_at;
  
  
DELETE FROM listing
 WHERE listing_id NOT IN (
     SELECT max_id FROM (
         SELECT MAX(listing_id) AS max_id
           FROM listing
          GROUP BY url
     ) AS sub
 );
 
SELECT COUNT(*) 
FROM energy_certificate;
-- 1. Desactivar
SET SQL_SAFE_UPDATES = 0;

-- 2. Borrar duplicados: conservar sólo la fila más reciente por URL
DELETE l1
  FROM listing l1
  JOIN listing l2
    ON l1.url = l2.url
   AND l1.scraped_at < l2.scraped_at;

-- 3. Volver a activar (opcional)
SET SQL_SAFE_UPDATES = 1;

SELECT url, COUNT(*) c 
  FROM listing 
 GROUP BY url 
HAVING c>1;

SELECT property_id,feature_id, COUNT(*) c 
  FROM property_feature 
 GROUP BY property_id,feature_id 
HAVING c>1;
SELECT COUNT(*)
FROM property p
LEFT JOIN property_feature pf
ON p.property_id=pf.property_id
WHERE pf.property_id IS NULL;

SELECT COUNT(*) FROM property;  
SELECT COUNT(*) FROM listing;  
SELECT COUNT(*) FROM listing WHERE scrape_status='Success';  
SELECT COUNT(*) FROM listing WHERE scrape_status='Removed';  
SELECT COUNT(*) FROM energy_certificate;  
SELECT COUNT(*) FROM property_feature;  

SELECT COUNT(DISTINCT property_native_id) FROM property;

SELECT url, COUNT(*) AS cnt
  FROM listing
 GROUP BY url
HAVING cnt > 1;

SELECT property_id, feature_id, COUNT(*) AS cnt
  FROM property_feature
 GROUP BY property_id, feature_id
HAVING cnt > 1;

SELECT COUNT(*) AS no_cert
  FROM property p
LEFT JOIN energy_certificate ec
    ON p.property_id = ec.property_id
 WHERE ec.property_id IS NULL;
 
 SELECT
  p.property_id,
  COUNT(l.listing_id) AS total_listings
FROM property p
LEFT JOIN listing l
  ON p.property_id = l.property_id
GROUP BY p.property_id
ORDER BY total_listings DESC;
 
SELECT
  barrio,
  distrito,
  COUNT(*) AS veces
FROM location
GROUP BY barrio, distrito
HAVING veces > 1;

SELECT property_native_id, COUNT(*) AS veces
  FROM property
 GROUP BY property_native_id
HAVING veces > 1;

SELECT * FROM listing 
WHERE property_id = 3817; 
 
SELECT 
  (SELECT COUNT(*) FROM property)              AS n_property,
  (SELECT COUNT(*) FROM listing)               AS n_listing,
  (SELECT COUNT(*) FROM listing WHERE scrape_status='Success')    AS n_succ,
  (SELECT COUNT(*) FROM listing WHERE scrape_status='Removed')    AS n_rem,
  (SELECT COUNT(*) FROM energy_certificate)    AS n_energy,
  (SELECT COUNT(*) FROM property_feature)      AS n_pf;


SELECT COUNT(*)
FROM property p
LEFT JOIN energy_certificate ec
ON p.property_id = ec.property_id
WHERE ec.property_id IS NULL;

SELECT COUNT(*) 
  FROM property p
  LEFT JOIN listing l 
    ON p.property_id = l.property_id 
   AND l.scrape_status='Success'
 WHERE l.listing_id IS NULL;

SELECT COUNT(DISTINCT p.property_id)
  FROM property p
  JOIN listing l 
    ON p.property_id = l.property_id
 WHERE l.scrape_status='Success';

SELECT url, COUNT(*) c
  FROM listing
 WHERE scrape_status='Success'
 GROUP BY url
HAVING c>1;




-- 1) Conteo de propiedades por distrito (gráfico de barras / mapa coroplético)
SELECT
l.distrito,
COUNT(*) AS num_properties
FROM property p
JOIN location l ON p.location_id = l.location_id
GROUP BY l.distrito
ORDER BY num_properties DESC;




-- 2) Distribución de tipos de anuncio (pastel o barras)
SELECT
price_kind,
COUNT(*) AS cantidad
FROM listing
GROUP BY price_kind;

-- 3) Precio medio de venta por distrito (heat-map o barras)
SELECT
l.distrito,
AVG(lst.price_eur) AS avg_sale_price
FROM listing lst
JOIN property p ON lst.property_id = p.property_id
JOIN location l ON p.location_id = l.location_id
WHERE lst.price_kind = 'sale_price'
GROUP BY l.distrito
ORDER BY avg_sale_price DESC;

-- 4) Precio medio de alquiler por distrito (heat-map o barras)
SELECT
l.distrito,
AVG(lst.price_eur) AS avg_rent_price
FROM listing lst
JOIN property p ON lst.property_id = p.property_id
JOIN location l ON p.location_id = l.location_id
WHERE lst.price_kind = 'rent_month'
GROUP BY l.distrito
ORDER BY avg_rent_price DESC;

-- 5) Evolución mensual del nº de anuncios y precio medio (serie temporal)
SELECT
DATE_FORMAT(lst.scraped_at, '%Y-%m') AS year_month,
lst.price_kind,
COUNT(*) AS num_listings,
AVG(lst.price_eur) AS avg_price
FROM listing lst
GROUP BY year_month, lst.price_kind
ORDER BY year_month, lst.price_kind;

-- 6) Distribución de precio por m² (histograma / densidad)
SELECT
lst.price_kind,
(lst.price_eur / NULLIF(p.superficie_construida,0)) AS price_per_sqm
FROM listing lst
JOIN property p ON lst.property_id = p.property_id
WHERE p.superficie_construida > 0;

-- 7) Conteo de propiedades por rango de antigüedad (barra)
SELECT
ar.label AS age_range,
COUNT(*) AS cantidad
FROM property p
JOIN age_range ar ON p.age_range_id = ar.age_range_id
GROUP BY ar.label
ORDER BY ar.age_range_id;

-- 8) Distribución de clasificaciones energéticas (barra)
SELECT
ec.consumption_rating AS rating,
COUNT(*) AS cantidad
FROM energy_certificate ec
WHERE ec.consumption_rating IS NOT NULL
GROUP BY ec.consumption_rating
ORDER BY ec.consumption_rating;

-- 9) Precio medio por clasificación energética (barra)
SELECT
ec.consumption_rating AS rating,
AVG(lst.price_eur) AS avg_price
FROM energy_certificate ec
JOIN listing lst ON ec.property_id = lst.property_id
GROUP BY ec.consumption_rating
ORDER BY ec.consumption_rating;

-- 10) Precio medio por nº de habitaciones (línea o barras)
SELECT
p.habitaciones AS bedrooms,
AVG(lst.price_eur) AS avg_price
FROM property p
JOIN listing lst ON p.property_id = lst.property_id
GROUP BY p.habitaciones
ORDER BY p.habitaciones;

-- 11) Top 10 características más comunes (barra)
SELECT
fc.nombre,
COUNT(*) AS frecuencia
FROM property_feature pf
JOIN feature_catalog fc ON pf.feature_id = fc.feature_id
GROUP BY fc.nombre
ORDER BY frecuencia DESC
LIMIT 10;

-- 12) Impacto de tener piscina en el precio de venta (comparativo barras)
-- a) Precio medio CON piscina
SELECT
AVG(lst.price_eur) AS avg_price_with_pool
FROM listing lst
JOIN property_feature pf ON lst.property_id = pf.property_id
JOIN feature_catalog fc ON pf.feature_id = fc.feature_id
WHERE fc.nombre = 'piscina'
AND lst.price_kind = 'sale_price';

-- b) Precio medio SIN piscina
SELECT
AVG(lst.price_eur) AS avg_price_without_pool
FROM listing lst
WHERE lst.price_kind = 'sale_price'
AND lst.property_id NOT IN (
SELECT pf.property_id
FROM property_feature pf
JOIN feature_catalog fc ON pf.feature_id = fc.feature_id
WHERE fc.nombre = 'piscina'
);

-- 13) Datos para scatter-map (latitud, longitud y precio)
SELECT
p.latitude,
p.longitude,
lst.price_eur,
lst.listing_type
FROM property p
JOIN listing lst ON p.property_id = lst.property_id
WHERE p.latitude IS NOT NULL
AND p.longitude IS NOT NULL;



SELECT
  l.listing_id,
  l.url,
  l.price_eur        AS sale_price,
  l.scraped_at,
  l.description,

  p.property_id,
  p.property_native_id,
  p.latitude,
  p.longitude,
  p.superficie_construida,
  p.superficie_util,
  p.habitaciones,
  p.banos,
  p.planta,
  p.estado_conservacion,

  loc.barrio,
  loc.distrito,

  ar.label          AS age_range,

  ec.classification AS energy_class,
  ec.consumo_rating AS energy_consumo_rating,
  ec.emisiones_rating AS energy_emisiones_rating,
  ec.emision_value  AS energy_emision_value,
  ec.consumption_value AS energy_consumption_value,

  -- Extras agrupados como "nombre:valor" separados por coma
  GROUP_CONCAT(CONCAT(fc.nombre, ':', pf.valor) 
               ORDER BY fc.nombre
               SEPARATOR ',') AS extras

SELECT
  l.listing_id,
  l.url,
  l.price_eur        AS sale_price,
  l.scraped_at,
  l.description,

  p.property_id,
  p.property_native_id,
  p.latitude,
  p.longitude,
  p.superficie_construida,
  p.superficie_util,
  p.habitaciones,
  p.banos,
  p.planta,
  p.estado_conservacion,

  loc.barrio,
  loc.distrito,

  ar.label          AS age_range,

  ec.classification AS energy_class,
  ec.consumo_rating AS energy_consumo_rating,
  ec.emisiones_rating AS energy_emisiones_rating,
  ec.emision_value  AS energy_emision_value,
  ec.consumption_value AS energy_consumption_value,

  -- Extras agrupados como "nombre:valor" separados por coma
  GROUP_CONCAT(CONCAT(fc.nombre, ':', pf.valor) 
               ORDER BY fc.nombre
               SEPARATOR ',') AS extras

SELECT
  l.listing_id,
  l.url,
  l.price_eur        AS sale_price,
  l.scraped_at,
  l.description,

  p.property_id,
  p.property_native_id,
  p.latitude,
  p.longitude,
  p.superficie_construida,
  p.superficie_util,
  p.habitaciones,
  p.banos,
  p.planta,
  p.estado_conservacion,

  loc.barrio,
  loc.distrito,

  ar.label          AS age_range,

  ec.classification AS energy_class,
  ec.consumo_rating AS energy_consumo_rating,
  ec.emisiones_rating AS energy_emisiones_rating,
  ec.emision_value  AS energy_emision_value,
  ec.consumption_value AS energy_consumption_value,

  -- Extras agrupados como "nombre:valor" separados por coma
  GROUP_CONCAT(CONCAT(fc.nombre, ':', pf.valor) 
               ORDER BY fc.nombre
               SEPARATOR ',') AS extras

FROM listing l
JOIN property p
  ON l.property_id = p.property_id
JOIN location loc
  ON p.location_id = loc.location_id
JOIN age_range ar
  ON p.age_range_id = ar.age_range_id
LEFT JOIN energy_certificate ec
  ON p.property_id = ec.property_id
LEFT JOIN property_feature pf
  ON p.property_id = pf.property_id
LEFT JOIN feature_catalog fc
  ON pf.feature_id = fc.feature_id

WHERE
  l.price_kind = 'sale_price'
  AND l.scrape_status = 'Success'

GROUP BY l.listing_id
ORDER BY l.scraped_at DESC;




SELECT
  l.listing_id,
  l.url,
  l.price_eur        AS sale_price,
  l.scraped_at,
  l.description,

  p.property_id,
  p.property_native_id,
  p.latitude,
  p.longitude,
  p.superficie_construida,
  p.superficie_util,
  p.habitaciones,
  p.banos,
  p.planta,
  p.estado_conservacion,

  loc.barrio,
  loc.distrito,

  ar.label          AS age_range,

  ec.classification AS energy_class,
  ec.consumo_rating AS energy_consumo_rating,
  ec.emisiones_rating AS energy_emisiones_rating,
  ec.emision_value  AS energy_emision_value,
  ec.consumption_value AS energy_consumption_value,

  -- Extras agrupados como "nombre:valor" separados por coma
  GROUP_CONCAT(CONCAT(fc.nombre, ':', pf.valor) 
               ORDER BY fc.nombre
               SEPARATOR ',') AS extras

FROM listing l
JOIN property p
  ON l.property_id = p.property_id
JOIN location loc
  ON p.location_id = loc.location_id
JOIN age_range ar
  ON p.age_range_id = ar.age_range_id
LEFT JOIN energy_certificate ec
  ON p.property_id = ec.property_id
LEFT JOIN property_feature pf
  ON p.property_id = pf.property_id
LEFT JOIN feature_catalog fc
  ON pf.feature_id = fc.feature_id

WHERE
  l.price_kind = 'sale_price'
  AND l.scrape_status = 'Success'

GROUP BY l.listing_id
ORDER BY l.scraped_at DESC;


SELECT
  l.listing_id,
  l.url,
  l.price_eur        AS sale_price,
  l.scraped_at,
  l.description,
  
  p.property_id,
  p.property_native_id,
  p.latitude,
  p.longitude,
  p.superficie_construida,
  p.superficie_util,
  p.habitaciones,
  p.banos,
  p.planta,
  p.estado_conservacion,
  
  loc.barrio,
  loc.distrito,
  
  ar.label          AS age_range,
  
  ec.classification       AS energy_classification,
  ec.consumo_rating       AS energy_consumo_rating,
  ec.emisiones_rating     AS energy_emisiones_rating,
  ec.emision_value        AS energy_emision_value,
  ec.consumption_value    AS energy_consumption_value,
  
  fc.nombre         AS feature_name,
  pf.valor          AS feature_value

FROM listing l
JOIN property p
  ON l.property_id = p.property_id
JOIN location loc
  ON p.location_id = loc.location_id
JOIN age_range ar
  ON p.age_range_id = ar.age_range_id
LEFT JOIN energy_certificate ec
  ON p.property_id = ec.property_id
LEFT JOIN property_feature pf
  ON p.property_id = pf.property_id
LEFT JOIN feature_catalog fc
  ON pf.feature_id = fc.feature_id

WHERE
  l.price_kind    = 'sale_price'
  AND l.scrape_status = 'Success'

ORDER BY
  l.listing_id,
  fc.nombre;
  
  
  
SELECT
  l.listing_id,
  l.url,
  l.price_eur       AS sale_price,
  l.scraped_at,
  l.description,

  p.property_id,
  p.property_native_id,
  p.latitude,
  p.longitude,
  p.superficie_construida,
  p.superficie_util,
  p.habitaciones,
  p.banos,
  p.planta,
  p.estado_conservacion,

  loc.barrio,
  loc.distrito,

  ar.label          AS age_range,

  ec.classification       AS energy_classification,
  ec.consumo_rating       AS energy_consumo_rating,
  ec.emisiones_rating     AS energy_emisiones_rating,
  ec.emision_value        AS energy_emision_value,
  ec.consumption_value    AS energy_consumption_value

FROM listing l
JOIN property p
  ON l.property_id = p.property_id
JOIN location loc
  ON p.location_id = loc.location_id
JOIN age_range ar
  ON p.age_range_id = ar.age_range_id
LEFT JOIN energy_certificate ec
  ON p.property_id = ec.property_id

WHERE
  l.price_kind    = 'sale_price'
  AND l.scrape_status = 'Success'

ORDER BY
  l.scraped_at DESC;
  
  
  
SELECT *
FROM listing l
JOIN property p   ON l.property_id = p.property_id
JOIN location loc ON p.location_id = loc.location_id
JOIN age_range ar ON p.age_range_id = ar.age_range_id
LEFT JOIN energy_certificate ec ON p.property_id = ec.property_id
WHERE l.price_kind='sale_price'
  AND l.scrape_status='Success';
  
  
SELECT *
        FROM listing l
        JOIN property p   ON l.property_id = p.property_id
        JOIN location loc ON p.location_id = loc.location_id
        JOIN age_range ar ON p.age_range_id = ar.age_range_id
        LEFT JOIN energy_certificate ec ON p.property_id = ec.property_id
        WHERE l.price_kind='rent_month'
        AND l.scrape_status='Success';