# Scraper de Meteoclimatic - Proyecto viento (ATD)
# Descarga la tabla de estaciones del País Valencià y guarda el viento
# de las estaciones de mis spots en data/meteoclimatic.csv

import csv
import os
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup


# ---------- 1. Constantes ----------

URL = "https://www.meteoclimatic.net/mapinfo/ESPVA"

# spot -> código de la estación de Meteoclimatic (sale en el enlace /perfil/...)
# Pinedo y El Saler usan la misma estación (Valencia - Camins al Grau)
ESTACIONES = {
    "Cullera": "ESPVA4600000046409A",     # Cullera - Marenyet
    "El Perelló": "ESPVA4600000046420A",  # El Perelló
    "Sagunto": "ESPVA4600000046520D",     # Sagunt - Port de Sagunt
    "El Puig": "ESPVA4600000046540A",     # El Puig de Santa Maria
    "Pinedo": "ESPVA4600000046022A",      # Valencia - Camins al Grau
    "El Saler": "ESPVA4600000046022A",    # Valencia - Camins al Grau
    "Les Marines": "ESPVA0300000003700F", # Dénia - Santa Llúcia (Joan Chabàs es tpv: no publica viento)
}

FICHERO_CSV = "data/meteoclimatic.csv"


# ---------- 2. Descargar la página ----------

def descargar_pagina(url):
    try:
        respuesta = requests.get(url, timeout=20)
        respuesta.raise_for_status()
    except requests.exceptions.RequestException as e:
        print("Error al descargar la página:", e)
        return None
    respuesta.encoding = "iso-8859-15"   # la web usa esta codificación
    return respuesta.text


# ---------- 3. Pasar de km/h a nudos ----------

def km_h_a_nudos(valor):
    return round(valor * 0.54, 1)


# ---------- 4. Sacar los datos de cada estación ----------

def leer_estaciones(html):
    soup = BeautifulSoup(html, "html.parser")
    fecha = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
    registros = []

    for spot, codigo in ESTACIONES.items():
        # Si una estación trae algo raro, aviso y sigo con las demás,
        # para no perder la captura de todos los spots por culpa de una
        try:
            enlaces = soup.find_all("a", href="/perfil/" + codigo)
            if len(enlaces) == 0:
                print("No encuentro la estación de", spot)
                continue

            # La estación puede salir en varias tablas de la página. Me quedo
            # con la primera fila que tenga todas las columnas (más de 13),
            # que es la de la tabla grande
            celdas = None
            for enlace in enlaces:
                fila = enlace.find_parent("tr")
                if fila is not None and len(fila.find_all("td")) > 13:
                    celdas = fila.find_all("td")
                    break
            if celdas is None:
                print("No encuentro la fila completa de", spot)
                continue

            # Viento actual (columna 12): "8 WSW", "-" si no hay dato o "Calma"
            viento_txt = celdas[12].get_text(strip=True).replace("\xa0", " ")
            if viento_txt == "-":
                viento = None
                direccion = None
            elif viento_txt == "Calma":
                viento = 0
                direccion = None
            else:
                partes = viento_txt.split(" ")
                viento = km_h_a_nudos(float(partes[0]))
                direccion = partes[1]

            # Viento máximo del día (columna 13)
            max_txt = celdas[13].get_text(strip=True)
            if max_txt == "-":
                max_dia = None
            else:
                max_dia = km_h_a_nudos(float(max_txt.replace(",", ".")))

            # Estado de la estación: el div de la primera celda tiene una clase
            # tipo "sprite-sem_ok" o "sprite-sem_qr". Guardo lo que va después
            # de "sem_" tal cual, sin suponer que solo hay dos estados
            clase = celdas[0].find("div")["class"][0]
            estado = clase.split("sem_")[-1]

            registros.append({
                "spot": spot,
                "fuente": "meteoclimatic",
                "estacion": codigo,
                "fecha_hora_utc": fecha,
                "viento_medio_kn": viento,
                "direccion": direccion,
                "max_dia_kn": max_dia,
                "estado": estado,
            })
        except Exception as e:
            print("Error leyendo la estación de", spot, "->", e)
            continue

    return registros


# ---------- 5. Guardar en CSV ----------

def guardar_csv(registros):
    existe = os.path.exists(FICHERO_CSV)

    with open(FICHERO_CSV, "a", newline="", encoding="utf-8") as f:
        columnas = ["spot", "fuente", "estacion", "fecha_hora_utc",
                    "viento_medio_kn", "direccion", "max_dia_kn", "estado"]
        writer = csv.DictWriter(f, fieldnames=columnas)
        if not existe:
            writer.writeheader()   # la cabecera solo la primera vez
        writer.writerows(registros)


# ---------- 6. Programa principal ----------

if __name__ == "__main__":
    html = descargar_pagina(URL)
    if html is not None:
        registros = leer_estaciones(html)
        guardar_csv(registros)
        print("Guardados", len(registros), "registros en", FICHERO_CSV)
        for r in registros:
            print(r["spot"], "->", r["viento_medio_kn"], "kn", r["direccion"],
                  "| máx:", r["max_dia_kn"], "kn |", r["estado"])
