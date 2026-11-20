# Observaciones horarias de las estaciones oficiales de AEMET (API OpenData).
# Cada petición devuelve las últimas 24 h de una estación. Lo guardo todo en
# data/aemet_obs.csv y las filas repetidas (misma estación y misma hora)
# se quitan después, en la limpieza.
# Uso:  python src/aemet_observaciones.py

import csv
import os
import time

import requests
from dotenv import load_dotenv


# ---------- 1. Constantes ----------

load_dotenv()                          # lee la API key del fichero .env
API_KEY = os.getenv("AEMET_API_KEY")

URL = "https://opendata.aemet.es/opendata/api/observacion/convencional/datos/estacion/"

# Estación de AEMET con viento más cercana a cada spot. La elegí con
# explorar_aemet.py (endpoint de observación de todas las estaciones).
# Todas están lejos de la playa: son la referencia oficial, no el viento del spot.
# Sagunto, El Puig y Les Marines no tienen ninguna cerca que mida viento
# (Sagunt 8446Y no tiene anemómetro), así que solo usan Meteoclimatic.
ESTACIONES = {
    "8416": ["Pinedo"],                    # València DT (a ~7 km)
    "8328X": ["El Saler", "El Perelló"],   # Sollana (a ~5 y ~9 km)
    "8325X": ["Cullera"],                  # Polinyà de Xúquer (a ~10 km)
}

FICHERO_CSV = "data/aemet_obs.csv"
COLUMNAS = ["spot", "fuente", "estacion", "fecha_hora_utc",
            "viento_medio_kn", "direccion_grados", "racha_kn"]


# ---------- 2. Pedir los datos de una estación (dos pasos, como en prueba_aemet.py) ----------

def pedir_observaciones(indicativo):
    try:
        # Paso 1: AEMET no da los datos, da una URL en el campo "datos"
        respuesta = requests.get(URL + indicativo, params={"api_key": API_KEY}, timeout=30)
        respuesta.raise_for_status()
        meta = respuesta.json()
        if meta.get("estado") != 200:
            print("AEMET responde con error para", indicativo, ":", meta.get("descripcion"))
            return None

        # Paso 2: descargo los datos de esa URL (vienen en latin-1)
        datos = requests.get(meta["datos"], timeout=30)
        datos.raise_for_status()
        datos.encoding = "latin-1"
        return datos.json()        # lista de diccionarios, uno por hora
    except requests.exceptions.RequestException as e:
        print("Error al pedir los datos de", indicativo, ":", e)
        return None


# ---------- 3. Unidades ----------

def ms_a_nudos(valor):
    # 1 m/s = 1,944 nudos. Si no hay dato, se queda vacío
    if valor is None:
        return None
    return round(valor * 1.944, 1)


# ---------- 4. Recorrer las estaciones ----------

def leer_aemet():
    registros = []
    for indicativo, spots in ESTACIONES.items():
        try:
            observaciones = pedir_observaciones(indicativo)
            if observaciones is None:
                continue
            for obs in observaciones:
                # "fint" es la hora de la observación, tipo "2026-11-20T18:00:00+0000"
                # Me quedo con "2026-11-20 18:00" para que coincida con mis otros CSV
                fecha = obs.get("fint", "")[:16].replace("T", " ")
                for spot in spots:
                    registros.append({
                        "spot": spot,
                        "fuente": "aemet_obs",
                        "estacion": indicativo,
                        "fecha_hora_utc": fecha,
                        "viento_medio_kn": ms_a_nudos(obs.get("vv")),
                        "direccion_grados": obs.get("dv"),
                        "racha_kn": ms_a_nudos(obs.get("vmax")),
                    })
        except Exception as e:
            print("Error con la estación", indicativo, "->", e)
        time.sleep(2)   # pausa entre estaciones para no saturar la API
    return registros


# ---------- 5. Guardar en CSV ----------

def guardar_csv(registros):
    existe = os.path.exists(FICHERO_CSV)
    with open(FICHERO_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNAS)
        if not existe:
            writer.writeheader()
        writer.writerows(registros)


# ---------- 6. Programa principal ----------

if __name__ == "__main__":
    if not API_KEY:
        raise SystemExit("No encuentro AEMET_API_KEY en el fichero .env")
    registros = leer_aemet()
    guardar_csv(registros)
    print("Guardados", len(registros), "registros en", FICHERO_CSV)
    # Enseño la última hora de cada estación para comprobar
    vistos = set()
    for r in reversed(registros):
        if r["estacion"] not in vistos:
            vistos.add(r["estacion"])
            print(r["estacion"], r["fecha_hora_utc"], "->", r["viento_medio_kn"], "kn |",
                  r["direccion_grados"], "º | racha", r["racha_kn"], "kn")
