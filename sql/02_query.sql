USE pisos3;

SELECT * FROM age_range;

SELECT * FROM location;

SELECT * FROM property;

SELECT * FROM listing;

SELECT * FROM energy_certificate;

SELECT * FROM property_feature;

SELECT * FROM feature_catalog;


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
listing_type,
COUNT(*) AS cantidad
FROM listing
GROUP BY listing_type;

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
lst.listing_type,
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