# Proyecto viento

Monitorización del viento y las olas en spots de windsurf, kitesurf y wingfoil
de la Comunitat Valenciana. Proyecto de la asignatura **Adquisición y
Transmisión de Datos** (Grado en Ciencia de Datos, UPV, curso 2026/27).

Autor: Antonio Martínez Ripoll

## Qué hace

Cada hora recoge datos de tres fuentes y los guarda en CSV:

| Fuente | Qué da | Cómo se obtiene | Script |
|---|---|---|---|
| [Meteoclimatic](https://www.meteoclimatic.net) | Viento medido en estaciones cercanas a la playa (actual y máximo del día) | Web scraping (requests + BeautifulSoup) | `src/scraper_meteoclimatic.py` |
| [Open-Meteo Marine](https://open-meteo.com) | Previsión de olas (altura, periodo y dirección) | API REST, sin key | `src/olas_openmeteo.py` |
| [AEMET OpenData](https://opendata.aemet.es) | Viento medido en estaciones oficiales (medio, racha y dirección) | API REST con API key | `src/aemet_observaciones.py` |

Spots: Pinedo, El Saler, El Perelló, Cullera, El Puig, Sagunto y Les Marines (Dénia).

## Estructura

```
proyecto-viento/
├── src/
│   ├── scraper_meteoclimatic.py   # scraping del listado de estaciones de la Comunitat
│   ├── olas_openmeteo.py          # previsión de olas por spot
│   ├── aemet_observaciones.py     # observaciones horarias de AEMET
│   ├── captura_horaria.py         # ejecuta las tres fuentes cada hora
│   ├── prueba_aemet.py            # prueba inicial de la API de AEMET (inventario)
│   └── explorar_aemet.py          # exploración para elegir estaciones de AEMET
├── data/                          # CSV generados
├── requirements.txt
└── README.md
```

## Instalación

```bash
git clone https://github.com/AntonioMopo/proyecto-viento.git
cd proyecto-viento
pip install -r requirements.txt
```

Para AEMET hace falta una API key gratuita (https://opendata.aemet.es). Se guarda
en un fichero `.env` en la carpeta del proyecto (no se sube al repositorio):

```
AEMET_API_KEY=tu_api_key
```

## Uso

Todos los scripts se ejecutan desde la carpeta `proyecto-viento`:

```bash
python src/scraper_meteoclimatic.py     # una captura de viento
python src/olas_openmeteo.py            # una captura de olas
python src/aemet_observaciones.py       # observaciones de AEMET
python src/captura_horaria.py           # las tres, cada hora (Ctrl + C para parar)
```

En macOS, para que el ordenador no se duerma durante la captura:
`caffeinate -i python src/captura_horaria.py`

## Uso responsable de las fuentes

- **Meteoclimatic:** su `robots.txt` permite las páginas de estaciones. Se hace
  una sola petición por hora (una página trae todos los spots). Contenido con licencia Creative Commons
  BY-NC-ND: uso académico y citando la fuente.
- **Open-Meteo:** gratuito para uso no comercial. Datos de
  [Open-Meteo.com](https://open-meteo.com) (licencia CC BY 4.0).
- **AEMET:** © AEMET. Datos de AEMET OpenData; la API key no se publica.

## Entregas

- Proyecto III: adquisición de datos (scraping y APIs) y limpieza.
- Proyecto IV: modelo cliente/servidor (Flask) y visualización.
