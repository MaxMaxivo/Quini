"""
Quini 6 Scraper
Corre via GitHub Actions cada miércoles y domingo.
Scrapea quini-6-resultados.com.ar y actualiza data.json
"""

import json
import re
import urllib.request
from datetime import date, timedelta
from pathlib import Path

# ─── REFERENCIA ──────────────────────────────────────────────────────────────
REF_NUM  = 3360
REF_DATE = date(2026, 3, 29)

# ─── CONFIG ──────────────────────────────────────────────────────────────────
MIS_NUMEROS        = [1, 8, 17, 21, 31, 33]
PRECIO_BOLETA      = 3000
BOLETAS_POR_SORTEO = 3
INICIO             = date(2026, 1, 4)

# ─── HELPERS ─────────────────────────────────────────────────────────────────
def sorteos_entre(d1, d2):
    count, d = 0, d1
    while d <= d2:
        if d.weekday() in (2, 6):
            count += 1
        d += timedelta(days=1)
    return count

def concurso_para_fecha(target):
    if target == REF_DATE:
        return REF_NUM
    if target < REF_DATE:
        return REF_NUM - sorteos_entre(target, REF_DATE) + 1
    return REF_NUM + sorteos_entre(REF_DATE, target) - 1

def build_url(num, d):
    return f"https://www.quini-6-resultados.com.ar/quini6/sorteo-{num}-del-dia-{d.day:02d}-{d.month:02d}-{d.year}.htm"

def fetch_html(url):
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "es-AR,es;q=0.9",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
        })
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.read().decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"  ERROR: {e}")
        return None

def parse_seccion(html, titulo):
    pat = re.escape(titulo) + r".*?(\d{2})\s*[-–]\s*(\d{2})\s*[-–]\s*(\d{2})\s*[-–]\s*(\d{2})\s*[-–]\s*(\d{2})\s*[-–]\s*(\d{2})"
    m = re.search(pat, html, re.IGNORECASE | re.DOTALL)
    return [int(x) for x in m.groups()] if m else None

DIA_ES = {
    "monday": "lunes", "tuesday": "martes", "wednesday": "miercoles",
    "thursday": "jueves", "friday": "viernes", "saturday": "sabado", "sunday": "domingo"
}

def scrape_sorteo(num, d):
    url = build_url(num, d)
    print(f"  [{num}] {d} -> {url}")
    html = fetch_html(url)
    if not html:
        return None
    if "SORTEO TRADICIONAL" not in html.upper():
        print(f"  Sin datos todavia")
        return None

    trad = parse_seccion(html, "SORTEO TRADICIONAL")
    if not trad:
        print(f"  No se pudo parsear")
        return None

    return {
        "concurso":    num,
        "fecha":       d.isoformat(),
        "dia":         DIA_ES.get(d.strftime("%A").lower(), ""),
        "url":         url,
        "tradicional": trad,
        "segunda":     parse_seccion(html, "LA SEGUNDA DEL QUINI"),
        "revancha":    parse_seccion(html, "SORTEO REVANCHA"),
        "siempre_sale":parse_seccion(html, "QUINI QUE SIEMPRE SALE"),
    }

# ─── MAIN ────────────────────────────────────────────────────────────────────
def main():
    data_path = Path("data.json")

    if data_path.exists():
        with open(data_path) as f:
            data = json.load(f)
    else:
        data = {"mis_numeros": MIS_NUMEROS, "precio_boleta": PRECIO_BOLETA, "sorteos": []}

    existentes = {s["concurso"] for s in data["sorteos"]}

    fechas, d = [], INICIO
    while d <= date.today():
        if d.weekday() in (2, 6):
            fechas.append(d)
        d += timedelta(days=1)

    print(f"Procesando {len(fechas)} sorteos...\n")
    nuevos = 0

    for d in fechas:
        num = concurso_para_fecha(d)
        if num in existentes:
            print(f"  [{num}] {d} -> ya existe")
            continue
        resultado = scrape_sorteo(num, d)
        if resultado:
            data["sorteos"].append(resultado)
            existentes.add(num)
            nuevos += 1
            print(f"  OK")
        else:
            print(f"  Sin datos")

    data["sorteos"].sort(key=lambda s: s["fecha"], reverse=True)

    with open(data_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\nListo. {nuevos} nuevo(s). Total: {len(data['sorteos'])}")

if __name__ == "__main__":
    main()
