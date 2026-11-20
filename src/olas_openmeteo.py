# Previsión de olas de Open-Meteo (API Marine) para mis spots.
# Para cada spot pide la previsión horaria de hoy y se queda con la de la
# hora actual (UTC). Lo guarda en data/olas.csv.
# API gratuita para uso no comercial, sin API key. Hay que citar a Open-Meteo.
# Uso:  python src/olas_openmeteo.py

import csv
import os
import time
from datetime import datetime, timezone

import requests


# ---------- 1. Constantes ----------

URL = "https://marine-api.open-meteo.com/v1/marine"

# Coordenadas aproximadas de cada spot (latitud, longitud).
# Si caen en tierra no pasa nada: la API coge el punto de mar más cercano
# (parámetro cell_selection, que por defecto es "sea").
COORDENADAS = {
    "Cullera": (39.14, -0.23),
    "El Perelló": (39.28, -0.26),
    "Sagunto": (39.65, -0.21),
    "El Puig": (39.59, -0.28),
    "Pinedo": (39.42, -0.33),
    "El Saler": (39.36, -0.31),
    "Les Marines": (38.86, 0.08),
}

FICHERO_CSV = "data/olas.csv"
COLUMNAS = ["spot", "fuente", "fecha_hora_utc",
            "ola_altura_m", "ola_periodo_s", "ola_direccion_grados"]


# ---------- 2. Pedir la previsión de un punto ----------

def pedir_olas(lat, lon):
    parametros = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "wave_height,wave_period,wave_direction",
        "forecast_days": 1,      # solo hoy: me basta con la hora actual
        "timezone": "GMT",       # horas en UTC, como en el resto del proyecto
    }
    # A veces la API tarda en contestar (timeout): lo intento 2 veces
    # antes de dar el spot por perdido hasta la hora siguiente
    for intento in range(2):
        try:
            respuesta = requests.get(URL, params=parametros, timeout=30)
            respuesta.raise_for_status()
            return respuesta.json()
        except requests.exceptions.RequestException as e:
            print("Error al pedir las olas (intento", intento + 1, "de 2):", e)
            time.sleep(5)
    return None


# ---------- 3. Quedarme con la hora actual ----------

def ola_de_esta_hora(datos, hora):
    # datos["hourly"]["time"] es una lista de horas tipo "2026-11-20T18:00"
    # y cada variable es otra lista en el mismo orden. Busco la posición
    # de la hora que quiero y saco el valor de cada lista en esa posición.
    horas = datos["hourly"]["time"]
    if hora not in horas:
        return None
    i = horas.index(hora)
    return {
        "ola_altura_m": datos["hourly"]["wave_height"][i],
        "ola_periodo_s": datos["hourly"]["wave_period"][i],
        "ola_direccion_grados": datos["hourly"]["wave_direction"][i],
    }


# ---------- 4. Recorrer todos los spots ----------

def leer_olas():
    ahora = datetime.now(timezone.utc)
    hora_api = ahora.strftime("%Y-%m-%dT%H:00")    # formato de la API
    hora_csv = ahora.strftime("%Y-%m-%d %H:00")    # formato de mis CSV
    registros = []

    for spot, (lat, lon) in COORDENADAS.items():
        try:
            datos = pedir_olas(lat, lon)
            if datos is None:
                continue
            ola = ola_de_esta_hora(datos, hora_api)
            if ola is None:
                print("No hay previsión para esta hora en", spot)
                continue
            registro = {"spot": spot, "fuente": "openmeteo_marine",
                        "fecha_hora_utc": hora_csv}
            registro.update(ola)
            registros.append(registro)
        except Exception as e:
            print("Error con las olas de", spot, "->", e)
        time.sleep(1)   # una pequeña pausa entre peticiones

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
    registros = leer_olas()
    guardar_csv(registros)
    print("Guardados", len(registros), "registros en", FICHERO_CSV)
    for r in registros:
        print(r["spot"], "->", r["ola_altura_m"], "m |",
              r["ola_periodo_s"], "s |", r["ola_direccion_grados"], "º")
