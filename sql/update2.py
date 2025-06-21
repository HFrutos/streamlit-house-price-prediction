import pandas as pd
import mysql.connector

import numpy as np 
import sys


# Conectar con la base de datos
print("____ Scrip update pisos4 ____")
print("Conectando con la base de datos..")

try:
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="contraseña",
        database="pisos4"
    )
    cursor = conn.cursor()
    print("- Conexión establecida")
except Exception as e:
    print("ERROR al conectar a MySQL:", e)
    sys.exit(1)


# Cargar los csv previamente scrapeados

df_sale = pd.read_csv("../data/processed/madrid_sale_properties_processed.csv")
df_rental = pd.read_csv("../data/processed/madrid_rental_properties_processed.csv")


df_rental['price_kind']  = 'rent_month'
df_rental['price_eur']   = df_rental['price_eur_pm']
df_sale  ['price_kind']   = 'sale_price'
df_sale['acepta_mascotas'] = None

common_cols = [
    'property_id','url','price_kind','price_eur','scraped_at','description',
    'barrio','distrito','latitude','longitude',
    'superficie_construida','superficie_util','habitaciones','banos','planta_numerica',
    'antiguedad','conservacion','energy_cert_classification',
    'energy_consumption_rating','energy_emissions_rating',
    'energy_consumption_kwh_m2_yr','energy_emissions_kg_co2_m2_yr',
    # extra features:
    'ascensor','balcon','calefaccion','chimenea','cocina_equipada','exterior','garaje',
    'jardin','piscina','trastero','terraza','adaptado_movilidad_reducida',
    'aire_acondicionado','puerta_blindada','vidrios_dobles','sistema_seguridad',
    'acepta_mascotas'  # política mascotas unificada
]

df_rental = df_rental[common_cols]
df_sale   = df_sale[common_cols]

df_all = pd.concat([df_rental, df_sale], ignore_index=True)
df_all = df_all.replace({np.nan:None})


df_all['scraped_at'] = pd.to_datetime(df_all['scraped_at'])
df_all["scrape_status"] = "Success"


## Mapedos 
cursor.execute("SELECT age_range_id,label FROM age_range")
age_map = {label: aid for aid,label in cursor.fetchall()}

cursor.execute("SELECT location_id,barrio,distrito FROM location")
loc_map = {(b,d): lid for lid,b,d in cursor.fetchall()}

cursor.execute("SELECT property_native_id,property_id FROM property")
prop_map = {nat: pid for nat,pid in cursor.fetchall()}

cursor.execute("SELECT url,price_eur FROM listing")
list_map = {url: float(price) for url,price in cursor.fetchall()}

cursor.execute("SELECT nombre,feature_id FROM feature_catalog")
feat_map = {name: fid for name,fid in cursor.fetchall()}

## Separar urls nuevas, existente y eliminadas

set_new = set(df_all['url'])
set_old = set(list_map.keys())

to_insert = set_new - set_old
to_update = set_new & set_old
to_remove = set_old - set_new

print(f"{len(to_insert)} URLs nuevas, {len(to_update)} a actualizar y {len(to_remove)} a marcar como removed")


## Separamos el df en tres, nuevas filas, existentes y eliminadas

df_insert = df_all[df_all['url'].isin(to_insert)].copy()
df_update = df_all[df_all['url'].isin(to_update)].copy()
df_remove = df_all[df_all['url'].isin(to_remove)].copy()


# Marcar los anuncios borrados como borrados

if not df_remove.empty:
    old_urls = set_old - set_new
    to_remove_ids = [ map_list[url] for url in old_urls ]
    sql = f"UPDATE listing SET scrape_status='Removed' WHERE listing_id IN ({','.join(['%s']*len(to_remove_ids))})"
    cursor.execute(sql, to_remove_ids)
    conn.commit()
    print(f"Marcados {len(to_remove_ids)} listings como Removed")


## Insertar filas nuevas 


# Tabla location

print("1.- Insertando ubicaciones nuevas..")
df_location = df_insert[["barrio","distrito"]].drop_duplicates()
df_location = df_location.dropna()

locations = [tuple(x) for x in df_location.values]

try:
    sql_loc = """INSERT IGNORE INTO location (barrio, distrito) VALUES (%s, %s)"""
    cursor.executemany(sql_loc, locations)
    conn.commit()
    print(f"- Insertadas {len(locations)} ubicaciones")
except Exception as e:
    conn.rollback()
    print("ERROR en location:", e)


# mapeo location con id

cursor.execute("SELECT * FROM location")
map_loc = {(b,d): lid for lid,b,d in cursor.fetchall()}


## Tabla age_range
# Mapeo 

cursor.execute("SELECT age_range_id,label FROM age_range")
map_age = {lbl: aid for aid,lbl in cursor.fetchall()}


## Tabla feature_catalog 
# Mapeo 

cursor.execute("SELECT feature_id,nombre FROM feature_catalog")
map_feat = {name: fid for fid,name in cursor.fetchall()}


## Tabla property 
# actualizar 

df_props = (
    df_all[[
      'property_id','barrio','distrito','latitude','longitude',
      'superficie_construida','superficie_util','habitaciones','banos',
      'planta_numerica','antiguedad'
    ]]
    .drop_duplicates('property_id')
    .dropna(subset=['barrio','distrito'])  
    .reset_index(drop=True)
)

print("2.- Actualizando propiedades.. ")
# 2.1) Preparamos el DataFrame de propiedades:
df_props = (
    df_all[[
      'property_id', 'barrio', 'distrito',
      'latitude', 'longitude',
      'superficie_construida', 'superficie_util',
      'habitaciones', 'banos',
      'planta_numerica', 'conservacion', 'antiguedad'
    ]]
    .rename(columns={
        'property_id':      'property_native_id',
        'planta_numerica':  'planta',
        'conservacion':     'estado_conservacion'
    })
    .dropna(subset=['barrio','distrito','property_native_id'], how='any')
    .drop_duplicates(subset=['property_native_id'])
    .reset_index(drop=True)
)
print(f"   → {len(df_props)} propiedades únicas para procesar")

# 2.2) SQL de UPSERT
sql_prop = """
INSERT INTO property
  (location_id,
   latitude, longitude,
   property_native_id,
   superficie_construida, superficie_util,
   habitaciones, banos, planta,
   estado_conservacion, age_range_id)
VALUES
  (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
ON DUPLICATE KEY UPDATE
  location_id          = VALUES(location_id),
  latitude             = VALUES(latitude),
  longitude            = VALUES(longitude),
  superficie_construida= VALUES(superficie_construida),
  superficie_util      = VALUES(superficie_util),
  habitaciones         = VALUES(habitaciones),
  banos                = VALUES(banos),
  planta               = VALUES(planta),
  estado_conservacion  = VALUES(estado_conservacion),
  age_range_id         = VALUES(age_range_id)
"""

# 2.3) Ejecutamos el UPSERT por fila
n_ok = 0
try:
    for _, r in df_props.iterrows():
        pid_native = r.property_native_id
        loc_id     = map_loc[(r.barrio, r.distrito)]
        age_id     = map_age.get(r.antiguedad)

        vals = [
            loc_id,
            r.latitude, r.longitude,
            pid_native,
            r.superficie_construida, r.superficie_util,
            r.habitaciones, r.banos, r.planta,
            r.estado_conservacion,
            age_id
        ]
        # Convertir pandas NA a None para MySQL
        vals = [None if pd.isna(x) else x for x in vals]

        cursor.execute(sql_prop, vals)
        n_ok += 1

    conn.commit()
    print(f"- UPSERT completado: {n_ok} propiedades insertadas/actualizadas")
except Exception as e:
    conn.rollback()
    print("ERROR en UPSERT de property:", e)
    raise  # opcional: para detener la ejecución si hay fallo

# mapeo nuevo property id
cursor.execute("SELECT property_native_id,property_id FROM property")
map_prop = {pid_native: pid for pid_native,pid in cursor.fetchall()}

## Mapeo referencia con id propiedad

cursor.execute("SELECT property_native_id,property_id FROM property")
map_prop = { pid: propid for pid, propid in cursor.fetchall() }


## Tabla listing 
# actualizar 

print("3.- Actualizando los anuncios..")
# 3.1) UPSERT de URLs nuevas o modificadas
sql_list = """
INSERT INTO listing
  (property_id, url, price_kind, price_eur, scraped_at, scrape_status, description)
VALUES (%s,%s,%s,%s,%s,%s,%s)
ON DUPLICATE KEY UPDATE
  price_eur     = VALUES(price_eur),
  scraped_at    = VALUES(scraped_at),
  scrape_status = VALUES(scrape_status),
  description   = VALUES(description)
"""

n_upsert = 0
for i, r in df_all.iterrows():
    pid = map_prop.get(str(r.property_id))
    if not pid:
        continue
    price      = None if pd.isna(r.price_eur) else r.price_eur
    scraped_at = r.scraped_at        # ya convertido a datetime
    scrape_status = r.scrape_status
    desc       = r.description or ""
    params = (
      pid,
      r.url,
      r.price_kind,
      price,
      scraped_at,
      scrape_status,
      desc
    )
    cursor.execute(sql_list, params)
    n_upsert += 1
    if n_upsert % 200 == 0:
        conn.commit()

conn.commit()
print(f"- UPSERT ejecutado en {n_upsert} listings (nuevos + actualizados)")

## Tabla energy_certificate
# 4) Upsert de certificados energéticos
print("4.- Actualizando los certificados energeticos..")

sql_energy = """
INSERT INTO energy_certificate
  (property_id, classification, consumo_rating, emisiones_rating, emision_value, consumption_value)
VALUES (%s,%s,%s,%s,%s,%s)
ON DUPLICATE KEY UPDATE
  classification    = VALUES(classification),
  consumo_rating    = VALUES(consumo_rating),
  emisiones_rating  = VALUES(emisiones_rating),
  emision_value     = VALUES(emision_value),
  consumption_value = VALUES(consumption_value)
"""

n_energy = 0
for _, r in df_all.iterrows():
    pid = map_prop.get(str(r.property_id))
    if not pid:
        continue
    params = (
      pid,
      r.energy_cert_classification,
      r.energy_consumption_rating,
      r.energy_emissions_rating,
      r.energy_emissions_kg_co2_m2_yr,
      r.energy_consumption_kwh_m2_yr
    )
    cursor.execute(sql_energy, params)
    n_energy += 1
    if n_energy % 200 == 0:
        conn.commit()

conn.commit()
print(f"   → UPSERT ejecutado en {n_energy} energy_certificate")

## Tabla property_feature
# actualizar 

rename_feats = {
    'adaptado_movilidad_reducida' : 'adaptado_pmreducida'
}

df_all.rename(columns=rename_feats, inplace=True)

# 7.1) Mapear cada fila al property_id interno
df_all["pid"] = df_all["property_id"].astype(str).map(map_prop)


extra_feats = [
    'ascensor','balcon','calefaccion','chimenea','cocina_equipada','exterior',
    'garaje','jardin','piscina','trastero','terraza','adaptado_pmreducida',
    'aire_acondicionado','puerta_blindada','vidrios_dobles','sistema_seguridad'
]


# 7) Reconstruir property_feature para cada propiedad afectada
print("7) Reconstruyendo property_feature…")

col_to_feat = {
    "adaptado_pmreducida":           "adaptado_pmreducida",
    "aire_acondicionado":            "aire_acondicionado",
    "amueblado":                     "amueblado",
    "armarios_empotrados":           "armarios_empotrados",
    "ascensor":                      "ascensor",
    "balcon":                        "balcon",
    "calefaccion":                   "calefaccion",
    "chimenea":                      "chimenea",
    "cocina_equipada":               "cocina_equipada",
    "exterior":                      "exterior",
    "garaje":                        "garaje",
    "jardin":                        "jardin",
    "piscina":                       "piscina",
    "puerta_blindada":               "puerta_blindada",
    "sistema_seguridad":             "sistema_seguridad",
    "terraza":                       "terraza",
    "trastero":                      "trastero",
    "vidrios_dobles":                "vidrios_dobles",
    "gastos_comunidad_eur":          "gastos_comunidad_eur",
    "orientacion_list":              "orientacion_list",
    "acepta_mascotas":               "acepta_mascotas"
}

# 7.3) Preparar inserciones
pf_records = []
for _, row in df_all.iterrows():
    pid = row["pid"]
    if pd.isna(pid):
        continue

    for df_col, feat_name in col_to_feat.items():
        val = row.get(df_col)
        # descartamos None, NaN, False, 0, strings vacíos e listas vacías
        if pd.isna(val) or val in (False, 0, "", [], {}):
            continue

        # normalizamos a string
        if isinstance(val, (list, tuple)):
            v = ",".join(val)
        elif isinstance(val, bool):
            v = "True" if val else "False"
        else:
            v = str(val)

        fid = feat_map[feat_name]
        pf_records.append((int(pid), fid, v))

print(f"   → Preparados {len(pf_records)} filas para insertar en property_feature")

# 7.4) Ejecutar insert
insert_sql = """
  INSERT INTO property_feature (property_id, feature_id, valor)
  VALUES (%s, %s, %s)
  ON DUPLICATE KEY UPDATE valor = VALUES(valor)
"""
cursor.executemany(insert_sql, pf_records)
conn.commit()
print(f"   → Insertadas {len(pf_records)} filas en property_feature")