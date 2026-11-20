# Captura periódica: cada hora ejecuta el scraper de Meteoclimatic (viento),
# pide la previsión de olas de Open-Meteo y las observaciones oficiales de AEMET,
# y los añade a data/meteoclimatic.csv, data/olas.csv y data/aemet_obs.csv.
# Uso (desde la carpeta proyecto-viento):  caffeinate -i python src/captura_horaria.py
# Para pararlo: Ctrl + C

import time
from datetime import datetime

from scraper_meteoclimatic import URL, descargar_pagina, leer_estaciones, guardar_csv
import olas_openmeteo
import aemet_observaciones

ESPERA_SEGUNDOS = 3600   # 1 hora: una petición por hora, como dije en la propuesta

while True:
    ahora = datetime.now().strftime("%d/%m %H:%M")
    try:
        html = descargar_pagina(URL)
        if html is not None:
            registros = leer_estaciones(html)
            guardar_csv(registros)
            print(ahora, "->", len(registros), "registros guardados")
        else:
            print(ahora, "-> no se pudo descargar la página, lo intento en la próxima hora")
    except Exception as e:
        print(ahora, "-> error inesperado:", e)

    # Olas: va en su propio try para que, si falla, no afecte al viento
    try:
        olas = olas_openmeteo.leer_olas()
        olas_openmeteo.guardar_csv(olas)
        print(ahora, "->", len(olas), "registros de olas guardados")
    except Exception as e:
        print(ahora, "-> error con las olas:", e)

    # AEMET: trae las últimas 24 h de cada estación; los repetidos se quitan en la limpieza
    try:
        obs = aemet_observaciones.leer_aemet()
        aemet_observaciones.guardar_csv(obs)
        print(ahora, "->", len(obs), "registros de AEMET guardados")
    except Exception as e:
        print(ahora, "-> error con AEMET:", e)

    time.sleep(ESPERA_SEGUNDOS)
