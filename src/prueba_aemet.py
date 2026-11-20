import os
import requests
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("AEMET_API_KEY")

if not api_key:
    raise SystemExit("No se ha encontrado AEMET_API_KEY en el fichero .env")

url_inventario = (
    "https://opendata.aemet.es/opendata/api/valores/"
    "climatologicos/inventarioestaciones/todasestaciones"
)

respuesta_inventario = requests.get(
    url_inventario,
    params={"api_key": api_key},
    timeout=30,
)
respuesta_inventario.raise_for_status()
inventario = respuesta_inventario.json()

if inventario.get("estado") != 200:
    raise SystemExit(
        f"Error de AEMET: {inventario.get('descripcion', 'respuesta no válida')}"
    )

url_datos = inventario["datos"]
respuesta_datos = requests.get(url_datos, timeout=30)
respuesta_datos.raise_for_status()
respuesta_datos.encoding = "latin-1"
estaciones = respuesta_datos.json()

estaciones_valencia = [
    estacion
    for estacion in estaciones
    if estacion.get("provincia") == "VALENCIA"
]

print(f"Estaciones encontradas en VALENCIA: {len(estaciones_valencia)}")
for estacion in estaciones_valencia:
    print(
        f"{estacion.get('indicativo', 'Sin indicativo')} | "
        f"{estacion.get('nombre', 'Sin nombre')} | "
        f"latitud: {estacion.get('latitud', 'N/D')} | "
        f"longitud: {estacion.get('longitud', 'N/D')}"
    )
