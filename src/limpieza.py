# Limpieza y unión de los datos del proyecto.
# Lee los tres CSV de la captura (Meteoclimatic, olas de Open-Meteo y AEMET)
# y mis notas de dirección, y genera data/datos_limpios.csv con una fila por
# spot y hora: viento en el spot, ola prevista, referencia oficial de AEMET,
# tipo de viento y si es navegable para cada deporte.
# Uso:  python src/limpieza.py

import csv


# ---------- 1. Constantes ----------

FICH_METEOCLIMATIC = "data/meteoclimatic.csv"
FICH_OLAS = "data/olas.csv"
FICH_AEMET = "data/aemet_obs.csv"
FICH_NOTAS = "data/puntuacion_direcciones.csv"
FICH_SALIDA = "data/datos_limpios.csv"

# Viento medio mínimo (nudos) para cada deporte (Entrega 2)
UMBRALES = {"wing": 12, "kite": 15, "windsurf": 19}
NOTA_MINIMA = 5        # una dirección "vale" si mi nota es 5 o más

# Rosa de 16 rumbos -> grados (Meteoclimatic da la dirección en texto)
RUMBOS = {"N": 0, "NNE": 22.5, "NE": 45, "ENE": 67.5, "E": 90, "ESE": 112.5,
          "SE": 135, "SSE": 157.5, "S": 180, "SSW": 202.5, "SW": 225,
          "WSW": 247.5, "W": 270, "WNW": 292.5, "NW": 315, "NNW": 337.5}

# Las 8 direcciones de mis notas, en orden de 45 en 45 grados
SECTORES = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]

COLUMNAS = ["spot", "fecha_hora_utc",
            "viento_medio_kn", "max_dia_kn", "direccion_grados", "direccion_sector",
            "tipo_viento", "estado_estacion",
            "ola_altura_m", "ola_periodo_s", "ola_direccion_grados",
            "aemet_viento_medio_kn", "aemet_racha_kn", "aemet_direccion_grados",
            "nota_wing", "nota_kite", "nota_windsurf",
            "navegable_wing", "navegable_kite", "navegable_windsurf"]


# ---------- 2. Funciones de ayuda ----------

def leer_csv(fichero):
    # Devuelve una lista de diccionarios (vacía si el fichero no existe)
    try:
        with open(fichero, newline="", encoding="utf-8") as f:
            return list(csv.DictReader(f))
    except FileNotFoundError:
        print("No existe", fichero, "(lo salto)")
        return []


def a_numero(texto):
    # "12.5" -> 12.5 ; "" -> None
    try:
        return float(texto)
    except (TypeError, ValueError):
        return None


def a_hora(fecha):
    # "2026-11-20 18:21" -> "2026-11-20 18:00" (para juntar fuentes por hora)
    return fecha[:13] + ":00"


def grados_a_sector(grados):
    # Cada sector abarca 45 grados centrados en su dirección:
    # N = 337.5-22.5, NE = 22.5-67.5, ... Sumo 22.5 y divido entre 45 con
    # división entera (//). No uso round() porque en Python redondea los .5
    # al par (round(4.5) = 4), y entonces SSW (202.5) caería en S pero
    # NNE (22.5) en N: las fronteras no irían siempre al mismo lado.
    # Con // la frontera va siempre al sector siguiente en sentido horario.
    if grados is None:
        return None
    return SECTORES[int((grados + 22.5) // 45) % 8]


def tipo_de_viento(grados):
    # Los cuatro vientos de Valencia, con los rangos de la Entrega 2
    if grados is None:
        return None
    if grados >= 330 or grados <= 30:
        return "Norte"
    if 60 <= grados <= 120:
        return "Levante"
    if 200 <= grados < 240:
        return "Garbí"
    if 240 <= grados <= 300:
        return "Poniente"
    return "Otro"


# ---------- 3. Meteoclimatic: una fila por spot y hora ----------

def limpiar_meteoclimatic(filas):
    # Si en la misma hora hay varias capturas de un spot (por pruebas),
    # me quedo con la última que tenga viento. Uso un diccionario con clave
    # (spot, hora): cada fila nueva sobrescribe a la anterior, salvo que la
    # nueva venga sin viento y ya tuviera una con dato.
    resultado = {}
    for f in filas:
        clave = (f["spot"], a_hora(f["fecha_hora_utc"]))
        if f["viento_medio_kn"] == "" and clave in resultado:
            continue
        grados = RUMBOS.get(f["direccion"])
        resultado[clave] = {
            "spot": f["spot"],
            "fecha_hora_utc": clave[1],
            "viento_medio_kn": a_numero(f["viento_medio_kn"]),
            "max_dia_kn": a_numero(f["max_dia_kn"]),
            "direccion_grados": grados,
            "estado_estacion": f["estado"],
        }
    return resultado


# ---------- 4. Olas y AEMET indexadas por (spot, hora) ----------

def indexar_olas(filas):
    olas = {}
    for f in filas:
        olas[(f["spot"], a_hora(f["fecha_hora_utc"]))] = f
    return olas


def indexar_aemet(filas):
    # AEMET repite las mismas horas en cada captura: al meterlas en un
    # diccionario con clave (spot, hora) los duplicados desaparecen solos
    aemet = {}
    for f in filas:
        aemet[(f["spot"], a_hora(f["fecha_hora_utc"]))] = f
    return aemet


def leer_notas(filas):
    # {(spot, sector): {"wing": 9, "kite": 10, "windsurf": 10}}
    notas = {}
    for f in filas:
        notas[(f["spot"], f["direccion"])] = {d: int(f[d]) for d in UMBRALES}
    return notas


# ---------- 5. Unir todo y decidir si es navegable ----------

def unir(viento, olas, aemet, notas):
    filas = []
    for clave, fila in sorted(viento.items(), key=lambda x: (x[0][1], x[0][0])):
        sector = grados_a_sector(fila["direccion_grados"])
        fila["direccion_sector"] = sector
        fila["tipo_viento"] = tipo_de_viento(fila["direccion_grados"])

        ola = olas.get(clave, {})
        fila["ola_altura_m"] = a_numero(ola.get("ola_altura_m"))
        fila["ola_periodo_s"] = a_numero(ola.get("ola_periodo_s"))
        fila["ola_direccion_grados"] = a_numero(ola.get("ola_direccion_grados"))

        oficial = aemet.get(clave, {})
        fila["aemet_viento_medio_kn"] = a_numero(oficial.get("viento_medio_kn"))
        fila["aemet_racha_kn"] = a_numero(oficial.get("racha_kn"))
        fila["aemet_direccion_grados"] = a_numero(oficial.get("direccion_grados"))

        nota_spot = notas.get((fila["spot"], sector), {})
        for deporte, umbral in UMBRALES.items():
            nota = nota_spot.get(deporte)
            fila["nota_" + deporte] = nota
            # Navegable = hay viento suficiente Y la dirección vale en ese spot.
            # Si falta algún dato no puedo decidirlo y lo dejo vacío.
            if fila["viento_medio_kn"] is None or nota is None:
                fila["navegable_" + deporte] = None
            else:
                fila["navegable_" + deporte] = (fila["viento_medio_kn"] >= umbral
                                                and nota >= NOTA_MINIMA)
        filas.append(fila)
    return filas


# ---------- 6. Programa principal ----------

if __name__ == "__main__":
    viento = limpiar_meteoclimatic(leer_csv(FICH_METEOCLIMATIC))
    olas = indexar_olas(leer_csv(FICH_OLAS))
    aemet = indexar_aemet(leer_csv(FICH_AEMET))
    notas = leer_notas(leer_csv(FICH_NOTAS))

    filas = unir(viento, olas, aemet, notas)

    with open(FICH_SALIDA, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNAS)
        writer.writeheader()
        writer.writerows(filas)

    print("Filas de viento (spot y hora):", len(filas))
    print("Con ola:", sum(1 for f in filas if f["ola_altura_m"] is not None))
    print("Con referencia de AEMET:", sum(1 for f in filas if f["aemet_viento_medio_kn"] is not None))
    for d in UMBRALES:
        print("Horas navegables de", d + ":", sum(1 for f in filas if f["navegable_" + d]))
    print("Guardado en", FICH_SALIDA)
