import pandas as pd
import mysql.connector 

import numpy as np

import sys


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
    
print("Script de carga de la base de datos")
# cargas los datos desde el csv

df_sale = pd.read_csv("madrid_sale_properties_processed_1.csv")
df_rental = pd.read_csv("madrid_rental_properties_processed_1.csv")

# ajustamos los dfs para que coincidan
df_sale["acepta_mascotas"] = None
df_rental = df_rental.rename(
    columns={"price_eur_pm": "price_eur"}
)
df_rental["price_kind"]   = "rent_month"
df_sale["price_kind"]   = "sale_price"

# concatenamos y cambiamos nan por none
df = pd.concat([df_rental, df_sale], ignore_index=True)
df = df.drop_duplicates()
print(f"filas a insertar: {len(df)}")

df = df.replace({np.nan: None})


# conectamos con la base de datos 
print("Conectando con la base de datos..")
try:
    conn = mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME
    )
    cursor = conn.cursor()
    print("- Conexión establecida")
except Exception as e:
    print("ERROR al conectar a MySQL:", e)
    sys.exit(1)

## Insertamos los datos 

# Tabla age_range
print("1.- Insertando rangos de antigüedad..")

try:
    age_range = df["antiguedad"].dropna().unique().tolist()
    sql_age = """INSERT IGNORE INTO age_range(label) VALUES (%s)"""
    cursor.executemany(sql_age, [(label,) for label in age_range])
    conn.commit()
    print(f"- Insertados {len(age_range)} rangos en age_range")
except Exception as e:
    conn.rollback()
    print("ERROR en age_range:", e)

# mapeo rango con id
cursor.execute("SELECT * FROM age_range")
ages = cursor.fetchall()
age_map = {label: age_range_id for age_range_id, label in ages}


# Tabla feature_catalog 
print("2.- Insertando catalogo de features..")

features = [
    'ascensor',
    'balcon',
    'calefaccion',
    'chimenea',
    'exterior',
    'garaje',
    'piscina',
    'trastero',
    'jardin',
    'adaptado_pmreducida',
    'aire_acondicionado',
    'puerta_blindada',
    'vidrios_dobles',
    'sistema_seguridad',
    'terraza',
    'amueblado',
    'cocina_equipada',
    'orientacion_list',
    'gastos_comunidad_eur',
    'armarios_empotrados',
    'acepta_mascotas'
]

try:
    sql_feat = "INSERT IGNORE INTO feature_catalog(nombre) VALUES (%s)"
    cursor.executemany(sql_feat, [(f,) for f in features])
    conn.commit()
    print(f"- Insertadas {len(features)} features")
except Exception as e:
    conn.rollback()
    print("ERROR en feature_catalog:", e)

# mapeo feature con id
cursor.execute("SELECT * FROM feature_catalog")
f = cursor.fetchall()
feature_map = {nombre: feature_id for feature_id, nombre in f}


## Tabla location
print("3.- Insertando ubicaciones..")
df_location = df[["barrio","distrito"]].drop_duplicates()
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
l = cursor.fetchall()
loc_map = {
    (barrio, distrito): location_id
    for location_id, barrio, distrito in l
}


## Tabla property 

print("4.- Insertando propiedades..")
df = df.dropna(subset=["barrio","distrito"], how="any")
df_property = df[[
    "barrio","distrito",
    "latitude","longitude",
    "property_id",
    "superficie_construida","superficie_util",
    "habitaciones","banos","planta_numerica",
    "conservacion","antiguedad",
    "amueblado","cocina_equipada"
]].drop_duplicates()

df_property = df_property.rename(columns={
    "property_id":      "property_native_id",
    "planta_numerica":  "planta",
    "conservacion":     "estado_conservacion",
})

property_records = []
for _, row in df_property.iterrows():
    loc_id = loc_map.get((row.barrio, row.distrito))
    age_id = age_map.get(row.antiguedad)

    habitaciones = int(row.habitaciones) if row.habitaciones is not None else None
    banos        = int(row.banos)        if row.banos        is not None else None
    planta       = float(row.planta)     if row.planta       is not None else None

    property_records.append((
        loc_id,
        row.latitude,
        row.longitude,
        row.property_native_id,
        row.superficie_construida,
        row.superficie_util,
        habitaciones,
        banos,
        planta,
        row.estado_conservacion,
        age_id

    ))

try:
    sql_property = """
        INSERT IGNORE INTO property
            (location_id, latitude, longitude,
            property_native_id,
            superficie_construida, superficie_util,
            habitaciones, banos, planta,
            estado_conservacion, age_range_id)
        VALUES
            (%s,%s,%s,
            %s,
            %s,%s,
            %s,%s,%s,
            %s,%s)
    """
    cursor.executemany(sql_property, property_records)
    conn.commit()
    print(f"- Insertadas {len(property_records)} propiedades")
except Exception as e:
    conn.rollback()
    print("ERROR en property:", e)

# mapeo property(native) con id 
cursor.execute("SELECT property_id, property_native_id FROM property")
p = cursor.fetchall()
property_map = {native: pid for pid, native in p}

## Tabla listing
print("5.- Insertando anuncios..")
df["scrape_status"] = "Success"
df['scraped_at'] = pd.to_datetime(df['scraped_at'])
df_listing = df[["property_id","url", "price_kind", "price_eur","scraped_at","scrape_status","description"]]
list_records = []
for _, row in df_listing.iterrows():
    pid = property_map.get(str(row.property_id))
    
    if pid is None:
        continue
    list_records.append((
        pid,
        row.url,
        row.price_kind,
        row.price_eur,
        row.scraped_at,
        row.scrape_status,
        row.description
    ))

try:
    sql_listing = """
                INSERT IGNORE INTO listing
                    (property_id, url, price_kind, price_eur, scraped_at, scrape_status, description)
                VALUES
                    (%s,%s,%s,%s,%s,%s,%s)
    """
    cursor.executemany(sql_listing, list_records)
    conn.commit()
    print(f"- Insertados {len(list_records)} anuncios")
except Exception as e:
    conn.rollback()
    print("ERROR en listing:", e)



## Tabla energy_certificate 
print("6.- Insertando certificados energéticos..")
df_energy = df[["property_id","energy_cert_classification","energy_consumption_rating","energy_emissions_rating","energy_emissions_kg_co2_m2_yr","energy_consumption_kwh_m2_yr"]]

energy_records = []
for _, row in df_energy.iterrows():
    pid = property_map.get(str(row.property_id))
    clasificacion = row.energy_cert_classification
    consumo  = row.energy_consumption_rating
    emisiones = row.energy_emissions_rating

    emision_value = row.energy_emissions_kg_co2_m2_yr
    consumption_value = row.energy_consumption_kwh_m2_yr

    energy_records.append((pid, clasificacion, consumo, emisiones, emision_value, consumption_value))

try:
    sql_energy = """
                    INSERT IGNORE INTO energy_certificate
                        (property_id, classification, consumo_rating, emisiones_rating, emision_value, consumption_value)
                    VALUES
                        (%s,%s,%s,%s,%s,%s)
                """
    cursor.executemany(sql_energy, energy_records)
    conn.commit()
    print(f"- Insertados {len(energy_records)} certificados")
except Exception as e:
    conn.rollback()
    print("ERROR en energy_certificate:", e)


# Tabla property_feature
print("7.- Insertando caracteristicas extras..")
df["property"] = df["property_id"].astype(str).map(property_map)

col_to_feat = {
    "adaptado_movilidad_reducida":    "adaptado_pmreducida",
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

pf_records = []
for _, row in df.iterrows():
    pid = row.property
    if pid is None:
        continue

    for df_col, feat_name in col_to_feat.items():
        val = row.get(df_col)
        if val is None:
            continue

        # orientacion_list → lista o string
        if df_col == "orientacion_list":
            if isinstance(val, (list, tuple)):
                v = ",".join(val)
            else:
                v = str(val)
            pf_records.append((pid, feature_map[feat_name], v))
        # gastos_comunidad_eur → número
        elif df_col == "gastos_comunidad_eur":
            pf_records.append((pid, feature_map[feat_name], str(val)))
        # resto: booleanos
        else:
            if val is True:
                pf_records.append((pid, feature_map[feat_name], "True"))

try: 
    sql_pf = """
                INSERT IGNORE INTO property_feature
                    (property_id, feature_id, valor)
                VALUES
                    (%s,%s,%s)
            """
    cursor.executemany(sql_pf, pf_records)
    conn.commit()
    print(f"- Insertados {len(pf_records)} extras")
except Exception as e:
    conn.rollback()
    print("ERROR en property_feature:", e)

print("Carga finalizada, cerrando conexion con la base de datos..")
cursor.close()
conn.close()