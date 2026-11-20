# Exploración (no forma parte de la captura): lista las estaciones de AEMET
# que tienen observación horaria cerca de mis spots y dice si miden viento.
# Lo uso para elegir los indicativos de aemet_observaciones.py.

import os
import requests
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("AEMET_API_KEY")
URL = "https://opendata.aemet.es/opendata/api/observacion/convencional/todas"

meta = requests.get(URL, params={"api_key": API_KEY}, timeout=30).json()
datos = requests.get(meta["datos"], timeout=60)
datos.encoding = "latin-1"
observaciones = datos.json()      # una fila por estación y hora

vistas = {}
for obs in observaciones:
    # Solo la franja de costa entre Dénia y Sagunto
    if 38.8 <= obs.get("lat", 0) <= 39.75 and -0.6 <= obs.get("lon", 0) <= 0.2:
        vistas[obs["idema"]] = obs   # me quedo con la última hora de cada estación

for idema, obs in sorted(vistas.items(), key=lambda x: -x[1]["lat"]):
    viento = "SÍ" if obs.get("vv") is not None else "no"
    print(f"{idema:<6} {obs.get('ubi', ''):<28} lat {obs['lat']:.3f} lon {obs['lon']:.3f}  viento: {viento}")
