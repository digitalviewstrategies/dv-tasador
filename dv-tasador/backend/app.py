"""
DV · Tasador Zona Norte — Backend Fase 2
=========================================
Dos servicios que NO pueden correr dentro de la landing (HTML estático):

  POST /comparables      -> busca propiedades reales por cercanía + características
                            en portales (Zonaprop, MercadoLibre, Argenprop, Remax)
                            usando scrapers de Apify, las rankea por similitud y
                            devuelve las 6 mejores.
  POST /analizar-fotos   -> manda las fotos de la propiedad a Claude (visión) y
                            devuelve estado, categoría y calidad estimados para
                            autocompletar el formulario del tasador.

Variables de entorno necesarias:
  APIFY_TOKEN            token de Apify (https://console.apify.com/account/integrations)
  ANTHROPIC_API_KEY      key de la API de Anthropic
  ACTOR_ZONAPROP         id del actor de Apify para Zonaprop  (ej: "epctex/zonaprop-scraper")
  ACTOR_MERCADOLIBRE     id del actor para MercadoLibre       (ej: "epctex/mercadolibre-scraper")
  # Argenprop / Remax / ZipCode: sumar más ACTOR_* y replicar el patrón de fetch_portal().
"""
import os, math, json, base64, httpx
from fastapi import FastAPI, UploadFile, File, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import List

APIFY_TOKEN       = os.getenv("APIFY_TOKEN", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ACTORS = {
    "Zonaprop":     os.getenv("ACTOR_ZONAPROP", ""),
    "MercadoLibre": os.getenv("ACTOR_MERCADOLIBRE", ""),
    # "Argenprop":  os.getenv("ACTOR_ARGENPROP", ""),
    # "Remax":      os.getenv("ACTOR_REMAX", ""),
}

app = FastAPI(title="DV Tasador · Backend Fase 2")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


# ----------------------------------------------------------------------
# Utilidades
# ----------------------------------------------------------------------
def haversine(lat1, lon1, lat2, lon2):
    """Distancia en km entre dos coordenadas."""
    R = 6371
    p = math.pi / 180
    a = (0.5 - math.cos((lat2 - lat1) * p) / 2
         + math.cos(lat1 * p) * math.cos(lat2 * p) * (1 - math.cos((lon2 - lon1) * p)) / 2)
    return 2 * R * math.asin(math.sqrt(a))


def similitud(sub_cub, sub_amb, dist_km, cub, amb):
    """Score 0-100: cercanía + parecido de superficie y ambientes."""
    d = max(0, 1 - dist_km / 3)                       # 0 a 3 km
    s = max(0, 1 - abs((cub or 0) - sub_cub) / max(sub_cub, 1))
    a = max(0, 1 - abs((amb or 0) - sub_amb) / max(sub_amb, 1))
    return round((0.5 * d + 0.35 * s + 0.15 * a) * 100)


async def fetch_portal(actor_id: str, portal: str, lat: float, lon: float, tipologia: str):
    """
    Corre un actor de Apify de forma síncrona y normaliza los resultados.
    El input exacto depende del actor elegido; acá va el patrón general:
    se le pasa una URL de búsqueda del portal por zona/tipología y se leen
    los items del dataset resultante.
    """
    if not (actor_id and APIFY_TOKEN):
        return []
    url = f"https://api.apify.com/v2/acts/{actor_id}/run-sync-get-dataset-items?token={APIFY_TOKEN}"
    # NOTA: ajustar 'startUrls'/'searchUrls' al esquema de input del actor que uses.
    payload = {"maxItems": 40, "proxyConfiguration": {"useApifyProxy": True},
               "tipologia": tipologia, "lat": lat, "lon": lon}
    out = []
    try:
        async with httpx.AsyncClient(timeout=120) as c:
            r = await c.post(url, json=payload)
            for it in r.json():
                out.append({
                    "portal":   portal,
                    "dir":      it.get("title") or it.get("address") or "Propiedad",
                    "precio":   it.get("priceUsd") or it.get("price"),
                    "cubierta": it.get("coveredAreaM2") or it.get("surfaceCovered") or it.get("m2"),
                    "amb":      it.get("rooms") or it.get("ambientes"),
                    "lat":      it.get("lat") or it.get("latitude"),
                    "lon":      it.get("lon") or it.get("longitude"),
                    "link":     it.get("url") or it.get("link"),
                })
    except Exception as e:
        print(f"[{portal}] error: {e}")
    return out


# ----------------------------------------------------------------------
# /comparables
# ----------------------------------------------------------------------
@app.get("/comparables")
async def comparables(lat: float = Query(...), lon: float = Query(...),
                      tipologia: str = "casa", cubierta: float = 0, amb: int = 0,
                      radio_km: float = 2.5):
    crudos = []
    for portal, actor in ACTORS.items():
        crudos += await fetch_portal(actor, portal, lat, lon, tipologia)

    enriquecidos = []
    for c in crudos:
        if not (c.get("lat") and c.get("lon") and c.get("precio")):
            continue
        dist = haversine(lat, lon, float(c["lat"]), float(c["lon"]))
        if dist > radio_km:
            continue
        cub = float(c.get("cubierta") or 0)
        c["dist_km"]    = round(dist, 2)
        c["usd_m2"]     = round(float(c["precio"]) / cub) if cub else None
        c["similitud"]  = similitud(cubierta, amb, dist, cub, int(c.get("amb") or 0))
        enriquecidos.append(c)

    enriquecidos.sort(key=lambda x: x["similitud"], reverse=True)
    top = enriquecidos[:6]
    return {"total_encontrados": len(enriquecidos), "comparables": top,
            "promedio_usd_m2": (round(sum(c["usd_m2"] for c in top if c["usd_m2"]) /
                                max(1, len([c for c in top if c["usd_m2"]]))) if top else None)}


# ----------------------------------------------------------------------
# /analizar-fotos  (Claude visión)
# ----------------------------------------------------------------------
PROMPT_FOTOS = (
    "Sos tasador inmobiliario en Zona Norte de Buenos Aires. A partir de estas fotos de "
    "una propiedad, estimá su estado de conservación, categoría constructiva y calidad de "
    "terminaciones. Respondé SOLO con un JSON, sin texto extra, con esta forma exacta:\n"
    '{"estado":"refaccionar|bueno|muybueno|excelente|estrenar",'
    '"categoria":"economica|standard|buena|premium",'
    '"calidad":"breve descripción","observaciones":"detalle de lo que ves en las fotos"}'
)

@app.post("/analizar-fotos")
async def analizar_fotos(fotos: List[UploadFile] = File(...)):
    if not ANTHROPIC_API_KEY:
        return {"error": "Falta ANTHROPIC_API_KEY en el backend."}
    content = [{"type": "text", "text": PROMPT_FOTOS}]
    for f in fotos[:6]:
        data = base64.b64encode(await f.read()).decode()
        content.append({"type": "image",
                        "source": {"type": "base64", "media_type": f.content_type or "image/jpeg", "data": data}})
    body = {"model": "claude-sonnet-4-6", "max_tokens": 600,
            "messages": [{"role": "user", "content": content}]}
    async with httpx.AsyncClient(timeout=90) as c:
        r = await c.post("https://api.anthropic.com/v1/messages", json=body,
                         headers={"x-api-key": ANTHROPIC_API_KEY,
                                  "anthropic-version": "2023-06-01",
                                  "content-type": "application/json"})
        txt = "".join(b.get("text", "") for b in r.json().get("content", []))
    try:
        return json.loads(txt[txt.find("{"): txt.rfind("}") + 1])
    except Exception:
        return {"error": "No se pudo parsear la respuesta", "raw": txt}


@app.get("/")
def health():
    return {"ok": True, "service": "DV Tasador · Fase 2",
            "actores_configurados": [k for k, v in ACTORS.items() if v]}
