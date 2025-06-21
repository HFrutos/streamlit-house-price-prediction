import pandas as pd
import mysql.connector
import numpy as np
import sys

print("=== ETL UPDATE PISOS4 ===")

# 1.- Leer CSVs
df_sale   = pd.read_csv("../data/processed/madrid_sale_properties_processed.csv")
df_rental = pd.read_csv("../data/processed/madrid_rental_properties_processed.csv")

df_rental['price_kind'] = 'rent_month'
df_rental['price_eur']  = df_rental['price_eur_pm']
df_sale['price_kind']   = 'sale_price'
df_sale['acepta_mascotas'] = None

common = [
  'property_id','url','price_kind','price_eur','scraped_at','description',
  'barrio','distrito','latitude','longitude',
  'superficie_construida','superficie_util','habitaciones','banos','planta_numerica',
  'antiguedad','conservacion',
  'energy_cert_classification','energy_consumption_rating','energy_emissions_rating',
  'energy_consumption_kwh_m2_yr','energy_emissions_kg_co2_m2_yr',
  'ascensor','balcon','calefaccion','chimenea','cocina_equipada','exterior',
  'garaje','jardin','piscina','trastero','terraza','adaptado_movilidad_reducida',
  'aire_acondicionado','puerta_blindada','vidrios_dobles','sistema_seguridad',
  'acepta_mascotas','gastos_comunidad_eur','orientacion_list'
]

df_all = pd.concat([
    df_rental[common],
    df_sale[common]
], ignore_index=True).replace({np.nan: None})

df_all['scraped_at'] = pd.to_datetime(df_all['scraped_at'])

# 2.- Conectar

from dotenv import load_dotenv
import os

# carga las vars definidas en .env al entorno
load_dotenv()

DB_HOST = os.getenv("DB_HOST")
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_NAME = os.getenv("DB_NAME")

if not all([DB_HOST, DB_USER, DB_PASS, DB_NAME]):
    print("ERROR: falta alguna variable de entorno:")
    print("DB_HOST=", DB_HOST)
    print("DB_USER=", DB_USER)
    print("DB_PASS=", DB_PASS)
    print("DB_NAME=", DB_NAME)
    sys.exit(1)

try:
    conn = mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME
    )
    cur = conn.cursor()
    print("Conectando con la base de datos..")
except Exception as e:
    print("ERROR conectando:", e)
    sys.exit(1)

# 3.- Cargar mapas
cur.execute("SELECT age_range_id,label FROM age_range")
age_map = {label: aid for aid,label in cur.fetchall()}

cur.execute("SELECT location_id,barrio,distrito FROM location")
loc_map = {(b,d): lid for lid,b,d in cur.fetchall()}

cur.execute("SELECT property_native_id,property_id FROM property")
prop_map = {nat: pid for nat,pid in cur.fetchall()}

cur.execute("SELECT url,price_eur FROM listing")
list_map = {url: float(price) for url,price in cur.fetchall()}

cur.execute("SELECT nombre,feature_id FROM feature_catalog")
feat_map = {name: fid for name,fid in cur.fetchall()}

# 4.- Upsert age_range (nuevos)
new_ages = set(df_all['antiguedad'].dropna()) - set(age_map)
if new_ages:
    cur.executemany("INSERT IGNORE INTO age_range(label) VALUES(%s)",
                    [(a,) for a in new_ages])
    conn.commit()
    cur.execute("SELECT age_range_id,label FROM age_range")
    age_map = {label: aid for aid,label in cur.fetchall()}
    print(f"- Insertados {len(new_ages)} rangos de antigüedad nuevos")

# 5.- Upsert location (nuevas)
locs = df_all[['barrio','distrito']].dropna().drop_duplicates()
new_locs = [tuple(x) for x in locs.values if tuple(x) not in loc_map]
if new_locs:
    cur.executemany("INSERT IGNORE INTO location(barrio,distrito) VALUES(%s,%s)", new_locs)
    conn.commit()
    cur.execute("SELECT location_id,barrio,distrito FROM location")
    loc_map = {(b,d): lid for lid,b,d in cur.fetchall()}
    print(f"- Insertadas {len(new_locs)} ubicaciones nuevas")

# 6.- Upsert property
sql_p = """
INSERT INTO property
  (location_id,latitude,longitude,property_native_id,
   superficie_construida,superficie_util,habitaciones,banos,planta,
   estado_conservacion,age_range_id)
VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
ON DUPLICATE KEY UPDATE
  location_id=VALUES(location_id),latitude=VALUES(latitude),
  longitude=VALUES(longitude),superficie_construida=VALUES(superficie_construida),
  superficie_util=VALUES(superficie_util),habitaciones=VALUES(habitaciones),
  banos=VALUES(banos),planta=VALUES(planta),
  estado_conservacion=VALUES(estado_conservacion),
  age_range_id=VALUES(age_range_id)
"""
dfp = df_all.rename(columns={
    'planta_numerica':'planta','conservacion':'estado_conservacion',
    'property_id':'property_native_id'
}).dropna(subset=['barrio','distrito','property_native_id']) \
  .drop_duplicates('property_native_id')

cnt = 0
for _,r in dfp.iterrows():
    lid = loc_map[(r.barrio,r.distrito)]
    aid = age_map.get(r.antiguedad)
    vals = [lid, r.latitude, r.longitude, r.property_native_id,
            r.superficie_construida, r.superficie_util,
            r.habitaciones, r.banos, r.planta,
            r.estado_conservacion, aid]
    vals = [None if pd.isna(x) else x for x in vals]
    cur.execute(sql_p, vals)
    cnt += 1
conn.commit()
print(f"- {cnt} propiedades upserteadas")

# 7.- Upsert listing + marcar Removed
print("- Actualizando listing…")
old_urls = set(list_map)
new_urls = set(df_all['url'])

# 7.1.- Removed
to_rem = list(old_urls - new_urls)
if to_rem:
    sql_r = "UPDATE listing SET scrape_status='Removed', scraped_at=NOW() WHERE url IN ({})" \
            .format(",".join("%s" for _ in to_rem))
    cur.execute(sql_r, to_rem)
    conn.commit()
    print(f"   - Marcados {len(to_rem)} anuncios como Removed")

# 7.2.- Upsert Success
sql_l = """
INSERT INTO listing
  (property_id,url,price_kind,price_eur,scraped_at,scrape_status,description)
VALUES (%s,%s,%s,%s,%s,%s,%s)
ON DUPLICATE KEY UPDATE
  price_eur=VALUES(price_eur),scraped_at=VALUES(scraped_at),
  scrape_status=VALUES(scrape_status),description=VALUES(description)
"""
cnt = 0
for _,r in df_all.iterrows():
    pid = prop_map.get(str(r.property_id))
    if not pid: continue
    cur.execute(sql_l, (
      pid, r.url, r.price_kind,
      None if pd.isna(r.price_eur) else r.price_eur,
      r.scraped_at, 'Success', r.description or ''
    ))
    cnt += 1
    if cnt % 500 == 0: conn.commit()
conn.commit()
print(f"   - Upsert en {cnt} eventos “Success”")

# 8.- Upsert energy_certificate
print("- Actualizando certificados energéticos…")
sql_e = """
INSERT INTO energy_certificate
  (property_id,classification,consumo_rating,emisiones_rating,emision_value,consumption_value)
VALUES (%s,%s,%s,%s,%s,%s)
ON DUPLICATE KEY UPDATE
  classification=VALUES(classification),
  consumo_rating=VALUES(consumo_rating),
  emisiones_rating=VALUES(emisiones_rating),
  emision_value=VALUES(emision_value),
  consumption_value=VALUES(consumption_value)
"""
cnt = 0
for _,r in df_all.iterrows():
    pid = prop_map.get(str(r.property_id))
    if not pid: continue
    cur.execute(sql_e, (
      pid, r.energy_cert_classification,
      r.energy_consumption_rating, r.energy_emissions_rating,
      r.energy_emissions_kg_co2_m2_yr, r.energy_consumption_kwh_m2_yr
    ))
    cnt += 1
    if cnt % 500 == 0: conn.commit()
conn.commit()
print(f"   - Upsert en {cnt} certificados energéticos")

# 9.- Reconstruir property_feature
print("- Reconstruyendo property_feature…")
# Borrar todo de las props en df_all
pids = df_all['property_id'].astype(str).map(prop_map).dropna().unique().tolist()
cur.executemany("DELETE FROM property_feature WHERE property_id=%s", 
                [(int(pid),) for pid in pids])
conn.commit()
# Re-insertar
sql_pf = """
INSERT INTO property_feature(property_id,feature_id,valor)
VALUES(%s,%s,%s)
ON DUPLICATE KEY UPDATE valor=VALUES(valor)
"""
cnt = 0
for _,r in df_all.iterrows():
    pid = prop_map.get(str(r.property_id))
    if not pid: continue
    for col,feat in {
      'ascensor':'ascensor','balcon':'balcon','calefaccion':'calefaccion',
      'chimenea':'chimenea','cocina_equipada':'cocina_equipada','exterior':'exterior',
      'garaje':'garaje','jardin':'jardin','piscina':'piscina','trastero':'trastero',
      'terraza':'terraza','adaptado_movilidad_reducida':'adaptado_pmreducida',
      'aire_acondicionado':'aire_acondicionado','puerta_blindada':'puerta_blindada',
      'vidrios_dobles':'vidrios_dobles','sistema_seguridad':'sistema_seguridad',
      'gastos_comunidad_eur':'gastos_comunidad_eur','orientacion_list':'orientacion_list',
      'acepta_mascotas':'acepta_mascotas'
    }.items():
        val = r.get(col)
        if pd.isna(val) or val in (False,0,'','[]'): 
            continue
        if isinstance(val,(list,tuple)):
            v = ",".join(val)
        elif isinstance(val,bool):
            v = "True"
        else:
            v = str(val)
        fid = feat_map[feat]
        cur.execute(sql_pf,(pid,fid,v))
        cnt += 1
        if cnt % 500 == 0: conn.commit()
conn.commit()
print(f"   - Insertadas/actualizadas {cnt} property_feature")

print("=== ETL UPDATE COMPLETADO ===")



cur.execute("SELECT COUNT(*) FROM property");              print("property:", cur.fetchone()[0])
cur.execute("SELECT COUNT(*) FROM listing");               print("listing:",  cur.fetchone()[0])
cur.execute("SELECT COUNT(*) FROM listing WHERE scrape_status='Success'"); print("success:", cur.fetchone()[0])
cur.execute("SELECT COUNT(*) FROM listing WHERE scrape_status='Removed'"); print("removed:", cur.fetchone()[0])
cur.execute("SELECT COUNT(*) FROM energy_certificate");    print("energy:",   cur.fetchone()[0])
cur.execute("SELECT COUNT(*) FROM property_feature");      print("features:", cur.fetchone()[0])


cur.close()
conn.close()