# Limpieza y unión de los datos del proyecto.
# Lee los tres CSV de la captura (Meteoclimatic, olas de Open-Meteo y AEMET)
# y mis notas de dirección, y genera data/datos_limpios.csv con una fila por
# spot y hora: viento en el spot, ola prevista, referencia oficial de AEMET,
# tipo de viento, la fuerza (base, racha y viento efectivo en nudos) y, para
# cada deporte, una nota de fuerza, una de dirección y una nota final del
# 0 al 10 (en vez de decir solo si se puede o no navegar).
# Uso:  python src/limpieza.py

import csv


# ---------- 1. Constantes ----------

FICH_METEOCLIMATIC = "data/meteoclimatic.csv"
FICH_OLAS = "data/olas.csv"
FICH_AEMET = "data/aemet_obs.csv"
FICH_NOTAS = "data/puntuacion_direcciones.csv"
FICH_SALIDA = "data/datos_limpios.csv"

# Viento mínimo (nudos) para cada deporte (Entrega 2)
UMBRALES = {"wing": 12, "kite": 15, "windsurf": 19}

# Escala de la nota de fuerza alrededor del umbral:
# 4 kn o más por debajo -> 0, en el umbral -> 5, 6 kn o más por encima -> 10
MARGEN_ABAJO = 4
MARGEN_ARRIBA = 6

# Peso de la racha en el viento efectivo: media + 0,5 * (racha - media).
# Un día de 18 de media con rachas de 25 se navega como uno de 21,5.
PESO_RACHA = 0.5

# Rosa de 16 rumbos -> grados (Meteoclimatic da la dirección en texto)
RUMBOS = {"N": 0, "NNE": 22.5, "NE": 45, "ENE": 67.5, "E": 90, "ESE": 112.5,
          "SE": 135, "SSE": 157.5, "S": 180, "SSW": 202.5, "SW": 225,
          "WSW": 247.5, "W": 270, "WNW": 292.5, "NW": 315, "NNW": 337.5}

# Las 8 direcciones de mis notas, en orden de 45 en 45 grados
SECTORES = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]

COLUMNAS = ["spot", "fecha_hora_utc",
            # Fuerza: la base, la racha y el viento efectivo, en nudos
            "viento_medio_kn", "racha_estimada_kn", "viento_efectivo_kn",
            "direccion_grados", "direccion_sector", "tipo_viento",
            # Para cada deporte: nota de fuerza (con el viento efectivo, que
            # tiene en cuenta base y racha), nota de dirección (mía) y nota final
            "fuerza_wing", "direccion_wing", "nota_wing",
            "fuerza_kite", "direccion_kite", "nota_kite",
            "fuerza_windsurf", "direccion_windsurf", "nota_windsurf",
            "ola_altura_m", "ola_periodo_s", "ola_direccion_grados",
            "max_dia_kn", "estado_estacion", "factor_racha",
            "aemet_viento_medio_kn", "aemet_racha_kn", "aemet_direccion_grados"]


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


def hora_anterior(hora):
    # "2026-11-22 13:00" -> "2026-11-22 12:00" (AEMET publica con retraso)
    from datetime import datetime, timedelta
    h = datetime.strptime(hora, "%Y-%m-%d %H:%M") - timedelta(hours=1)
    return h.strftime("%Y-%m-%d %H:%M")


def nota_fuerza(efectivo, umbral):
    # 0 si faltan 4 kn o más, 5 justo en el umbral, 10 con 6 kn o más de sobra,
    # y en línea recta entre medias
    if efectivo is None:
        return None
    if efectivo <= umbral - MARGEN_ABAJO:
        return 0.0
    if efectivo <= umbral:
        return round(5 * (efectivo - (umbral - MARGEN_ABAJO)) / MARGEN_ABAJO, 1)
    if efectivo >= umbral + MARGEN_ARRIBA:
        return 10.0
    return round(5 + 5 * (efectivo - umbral) / MARGEN_ARRIBA, 1)


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

        # AEMET va con retraso: si no hay dato de esta hora, uso el de la anterior
        oficial = aemet.get(clave) or aemet.get((clave[0], hora_anterior(clave[1])), {})
        fila["aemet_viento_medio_kn"] = a_numero(oficial.get("viento_medio_kn"))
        fila["aemet_racha_kn"] = a_numero(oficial.get("racha_kn"))
        fila["aemet_direccion_grados"] = a_numero(oficial.get("direccion_grados"))

        # Racha en el spot: Meteoclimatic no da racha horaria, así que uso el
        # "factor de racha" de AEMET (racha / media en su estación) y lo aplico
        # a la media del spot. Sin AEMET, el viento efectivo es solo la media.
        media = fila["viento_medio_kn"]
        factor = None
        if fila["aemet_viento_medio_kn"] and fila["aemet_racha_kn"]:
            factor = round(fila["aemet_racha_kn"] / fila["aemet_viento_medio_kn"], 2)
        fila["factor_racha"] = factor
        if media is None:
            fila["racha_estimada_kn"] = None
            fila["viento_efectivo_kn"] = None
        elif factor is None:
            fila["racha_estimada_kn"] = None
            fila["viento_efectivo_kn"] = media
        else:
            racha = round(media * factor, 1)
            fila["racha_estimada_kn"] = racha
            fila["viento_efectivo_kn"] = round(media + PESO_RACHA * (racha - media), 1)

        # Para cada deporte: nota de fuerza (con el viento efectivo, que ya
        # junta la base y la racha), nota de dirección (mis notas) y nota final.
        # Nota final = fuerza x dirección / 10. Hacen falta las dos: con terral
        # (dirección 0) la final es 0 aunque sople mucho.
        nota_spot = notas.get((fila["spot"], sector), {})
        for deporte, umbral in UMBRALES.items():
            fuerza = nota_fuerza(fila["viento_efectivo_kn"], umbral)
            direccion = nota_spot.get(deporte)
            fila["fuerza_" + deporte] = fuerza
            fila["direccion_" + deporte] = direccion
            if fuerza is None or direccion is None:
                fila["nota_" + deporte] = None      # falta un dato: no se puede puntuar
            else:
                fila["nota_" + deporte] = round(fuerza * direccion / 10, 1)
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
        notas_d = [f["nota_" + d] for f in filas if f["nota_" + d] is not None]
        if notas_d:
            print("Nota máxima de", d + ":", max(notas_d), "| horas con nota >= 5:",
                  sum(1 for n in notas_d if n >= 5))
    print("Guardado en", FICH_SALIDA)
