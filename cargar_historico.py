"""
Quini 6 - Carga histórica
Corré este script UNA VEZ en tu PC para llenar data.json con todos los
sorteos desde enero 2026 hasta hoy.

Requisitos: Python 3.8+ (sin dependencias externas)

Uso:
    python3 cargar_historico.py
"""

import json
import re
import urllib.request
from datetime import date, timedelta
from pathlib import Path

# ─── REFERENCIA ───────────────────────────────────────────────────────────────
REF_NUM  = 3360
REF_DATE = date(2026, 3, 29)
INICIO   = date(2026, 1, 4)   # Primer sorteo enero 2026

MIS_NUMEROS       = [1, 8, 17, 21, 31, 33]
PRECIO_BOLETA     = 3000
BOLETAS_X_SORTEO  = 3

# ─── HELPERS ──────────────────────────────────────────────────────────────────
def sorteos_entre(d1, d2):
    count, d = 0, d1
    while d <= d2:
        if d.weekday() in (2, 6):
            count += 1
        d += timedelta(days=1)
    return count

def concurso_para_fecha(target):
    if target == REF_DATE: return REF_NUM
    if target < REF_DATE:  return REF_NUM - sorteos_entre(target, REF_DATE) + 1
    return REF_NUM + sorteos_entre(REF_DATE, target) - 1

def build_url(num, d):
    return f"https://www.quini-6-resultados.com.ar/quini6/sorteo-{num}-del-dia-{d.day:02d}-{d.month:02d}-{d.year}.htm"

def fetch(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.read().decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"    ✗ Error: {e}")
        return None

def parse_seccion(html, titulo):
    pat = re.escape(titulo) + r".*?(\d{2})\s*[-–]\s*(\d{2})\s*[-–]\s*(\d{2})\s*[-–]\s*(\d{2})\s*[-–]\s*(\d{2})\s*[-–]\s*(\d{2})"
    m = re.search(pat, html, re.IGNORECASE | re.DOTALL)
    return [int(x) for x in m.groups()] if m else None

DIA_ES = {"monday":"lunes","tuesday":"martes","wednesday":"miércoles",
           "thursday":"jueves","friday":"viernes","saturday":"sábado","sunday":"domingo"}

def scrape(num, d):
    url = build_url(num, d)
    html = fetch(url)
    if not html or "SORTEO TRADICIONAL" not in html.upper():
        return None

    trad  = parse_seccion(html, "SORTEO TRADICIONAL")
    seg   = parse_seccion(html, "LA SEGUNDA DEL QUINI")
    rev   = parse_seccion(html, "SORTEO REVANCHA")
    siem  = parse_seccion(html, "QUINI QUE SIEMPRE SALE")

    if not trad:
        return None

    return {
        "concurso":    num,
        "fecha":       d.isoformat(),
        "dia":         DIA_ES.get(d.strftime("%A").lower(), ""),
        "url":         url,
        "tradicional": trad,
        "segunda":     seg,
        "revancha":    rev,
        "siempre_sale":siem,
    }

# ─── MAIN ─────────────────────────────────────────────────────────────────────
def main():
    data_path = Path("data.json")
    if data_path.exists():
        with open(data_path) as f:
            data = json.load(f)
    else:
        data = {"mis_numeros": MIS_NUMEROS, "precio_boleta": PRECIO_BOLETA, "sorteos": []}

    existentes = {s["concurso"] for s in data["sorteos"]}

    # Generar todas las fechas de sorteo desde INICIO hasta hoy
    fechas, d = [], INICIO
    while d <= date.today():
        if d.weekday() in (2, 6):
            fechas.append(d)
        d += timedelta(days=1)

    print(f"Procesando {len(fechas)} sorteos desde {INICIO} hasta hoy...\n")

    nuevos = 0
    for d in fechas:
        num = concurso_para_fecha(d)
        if num in existentes:
            print(f"  [{num}] {d} → ya existe, saltando")
            continue

        print(f"  [{num}] {d} → scrapeando...")
        resultado = scrape(num, d)
        if resultado:
            data["sorteos"].append(resultado)
            existentes.add(num)
            nuevos += 1
            aciertos = []
            for mod in ["tradicional","segunda","revancha","siempre_sale"]:
                nums = resultado.get(mod) or []
                a = len([n for n in nums if n in MIS_NUMEROS])
                aciertos.append(f"{mod[:4]}:{a}")
            print(f"    ✓ OK — {' | '.join(aciertos)}")
        else:
            print(f"    ✗ Sin datos todavía")

    data["sorteos"].sort(key=lambda s: s["fecha"], reverse=True)

    with open(data_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Listo. {nuevos} sorteo(s) nuevo(s). Total en data.json: {len(data['sorteos'])}")

if __name__ == "__main__":
    main()
