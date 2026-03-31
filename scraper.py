"""
Quini 6 Scraper
Corre via GitHub Actions cada miércoles y domingo.
Scrapea quini-6-resultados.com.ar y actualiza data.json
"""

import json
import re
import urllib.request
import urllib.error
from datetime import date, timedelta
from pathlib import Path

# ─── ANCLA DE REFERENCIA ─────────────────────────────────────────────────────
REF_NUM  = 3360
REF_DATE = date(2026, 3, 29)

# ─── NÚMEROS JUGADOS ─────────────────────────────────────────────────────────
MIS_NUMEROS = [1, 8, 17, 21, 31, 33]
PRECIO_BOLETA = 3000   # ARS por boleta (Tradicional + Revancha + Siempre Sale)
BOLETAS_POR_SORTEO = 3

# ─── HELPERS ─────────────────────────────────────────────────────────────────
def sorteos_entre(d1: date, d2: date) -> int:
    """Cuenta cuántos miércoles+domingos hay entre d1 y d2 (inclusive ambos)."""
    count = 0
    d = d1
    while d <= d2:
        if d.weekday() in (2, 6):  # 2=miércoles, 6=domingo
            count += 1
        d += timedelta(days=1)
    return count

def concurso_para_fecha(target: date) -> int:
    if target == REF_DATE:
        return REF_NUM
    if target < REF_DATE:
        return REF_NUM - sorteos_entre(target, REF_DATE) + 1
    else:
        return REF_NUM + sorteos_entre(REF_DATE, target) - 1

def build_url(sorteo_num: int, sorteo_date: date) -> str:
    return f"https://www.quini-6-resultados.com.ar/quini6/sorteo-{sorteo_num}-del-dia-{sorteo_date.day:02d}-{sorteo_date.month:02d}-{sorteo_date.year}.html"
    
def fetch_html(url: str) -> str | None:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.read().decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"  ERROR fetching {url}: {e}")
        return None

# ─── PARSER ──────────────────────────────────────────────────────────────────
def parse_numeros(html: str, titulo: str) -> list[int] | None:
    """Extrae los 6 números de una sección dada por su título."""
    pattern = re.escape(titulo) + r".*?(\d{2})\s*[-–]\s*(\d{2})\s*[-–]\s*(\d{2})\s*[-–]\s*(\d{2})\s*[-–]\s*(\d{2})\s*[-–]\s*(\d{2})"
    m = re.search(pattern, html, re.IGNORECASE | re.DOTALL)
    if not m:
        return None
    return [int(x) for x in m.groups()]

def scrape_sorteo(sorteo_num: int, sorteo_date: date) -> dict | None:
    url = build_url(sorteo_num, sorteo_date)
    print(f"  Scrapeando concurso {sorteo_num} ({sorteo_date}) → {url}")
    html = fetch_html(url)
    if not html:
        return None

    # Verificar que la página tiene datos reales
    if "SORTEO TRADICIONAL" not in html.upper():
        print(f"  Sin datos todavía para concurso {sorteo_num}")
        return None

    tradicional  = parse_numeros(html, "SORTEO TRADICIONAL")
    segunda      = parse_numeros(html, "LA SEGUNDA DEL QUINI")
    revancha     = parse_numeros(html, "SORTEO REVANCHA")
    siempre_sale = parse_numeros(html, "QUINI QUE SIEMPRE SALE")

    if not tradicional:
        print(f"  No se pudo parsear concurso {sorteo_num}")
        return None

    dia = sorteo_date.strftime("%A").lower()
    dia_es = {"monday":"lunes","tuesday":"martes","wednesday":"miércoles",
              "thursday":"jueves","friday":"viernes","saturday":"sábado","sunday":"domingo"}.get(dia, dia)

    return {
        "concurso": sorteo_num,
        "fecha": sorteo_date.isoformat(),
        "dia": dia_es,
        "url": url,
        "tradicional":  tradicional,
        "segunda":       segunda,
        "revancha":      revancha,
        "siempre_sale":  siempre_sale,
    }

# ─── FECHAS A SCRAPEAR ────────────────────────────────────────────────────────
def fechas_desde(inicio: date) -> list[date]:
    """Todos los miércoles y domingos desde inicio hasta hoy."""
    hoy = date.today()
    fechas = []
    d = inicio
    while d <= hoy:
        if d.weekday() in (2, 6):
            fechas.append(d)
        d += timedelta(days=1)
    return fechas

# ─── MAIN ────────────────────────────────────────────────────────────────────
def main():
    data_path = Path("data.json")

    # Cargar data existente
    if data_path.exists():
        with open(data_path) as f:
            data = json.load(f)
    else:
        data = {"sorteos": [], "mis_numeros": MIS_NUMEROS, "precio_boleta": PRECIO_BOLETA}

    existentes = {s["concurso"] for s in data["sorteos"]}

    inicio = date(2026, 1, 4)  # Primer sorteo de enero 2026
    fechas = fechas_desde(inicio)

    nuevos = 0
    for d in fechas:
        num = concurso_para_fecha(d)
        if num in existentes:
            continue
        print(f"Procesando sorteo {num} ({d})...")
        resultado = scrape_sorteo(num, d)
        if resultado:
            data["sorteos"].append(resultado)
            existentes.add(num)
            nuevos += 1

    # Ordenar por fecha descendente
    data["sorteos"].sort(key=lambda s: s["fecha"], reverse=True)

    # Guardar
    with open(data_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\nListo. {nuevos} sorteo(s) nuevo(s) agregado(s). Total: {len(data['sorteos'])}")

if __name__ == "__main__":
    main()
