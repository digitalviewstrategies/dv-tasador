"""
DV · Tasador Zona Norte — Backend Fase 2
=========================================
Servicios que NO pueden correr dentro de la landing (HTML estático):

  GET  /comparables     -> busca propiedades reales por cercanía + características
                           en portales (Zonaprop, MercadoLibre, Argenprop, Remax)
                           usando scrapers de Apify, las rankea por similitud y
                           devuelve las 6 mejores + el promedio USD/m².
  POST /analizar-fotos  -> manda las fotos de la propiedad a Claude (visión) y
                           devuelve estado, categoría y calidad estimados para
                           autocompletar el formulario del tasador.
  POST /lead            -> guarda el lead + la tasación completa (flywheel). Persiste
                           en disco (best-effort), reenvía a un webhook y/o inserta en
                           Supabase (La Base Viva). Cada tasación = dato propio de DV.

Variables de entorno:
  APIFY_TOKEN                token de Apify (https://console.apify.com/account/integrations)
  ANTHROPIC_API_KEY          key de la API de Anthropic
  ACTOR_ZONAPROP             id del actor de Apify para Zonaprop  (ej: "epctex/zonaprop-scraper")
  ACTOR_MERCADOLIBRE         id del actor para MercadoLibre       (ej: "epctex/mercadolibre-scraper")
  # Argenprop / Remax / ZipCode: sumar más ACTOR_* y replicar el patrón de fetch_portal().

  Captura de leads (flywheel) — todas opcionales:
  LEAD_WEBHOOK_URL           si está, se hace POST del lead a esa URL (Make/Zapier/Sheets/Edge Function)
  SUPABASE_URL               si está (+ service role), se inserta el lead en Supabase
  SUPABASE_SERVICE_ROLE_KEY  service role de Supabase (NUNCA exponer en el frontend)
  LEADS_TABLE                tabla destino en Supabase (default: "tasaciones")
  DATA_DIR                   carpeta para el JSONL local de respaldo (default: "./data")
  ALLOWED_ORIGINS            orígenes CORS separados por coma (default: "*"). En prod, el dominio de Pages.
"""
import os, math, json, base64, datetime, pathlib, httpx
from fastapi import FastAPI, UploadFile, File, Query, Request
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

LEAD_WEBHOOK_URL          = os.getenv("LEAD_WEBHOOK_URL", "")
SUPABASE_URL              = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
LEADS_TABLE               = os.getenv("LEADS_TABLE", "tasaciones")
DATA_DIR                  = os.getenv("DATA_DIR", "./data")
# Alerta de WhatsApp por cada lead nuevo "a captar" (reusa la WABA del bot DV).
ALERT_WHATSAPP            = os.getenv("ALERT_WHATSAPP", "5491170669425")   # número que recibe la alerta
WABA_TOKEN                = os.getenv("WABA_TOKEN", "")
PHONE_NUMBER_ID           = os.getenv("PHONE_NUMBER_ID", "")
ALERT_WEBHOOK_URL         = os.getenv("ALERT_WEBHOOK_URL", "")             # fallback si no hay WABA (Make/Zapier → WhatsApp)
ALLOWED_ORIGINS = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "*").split(",") if o.strip()] or ["*"]

app = FastAPI(title="DV Tasador · Backend Fase 2")
app.add_middleware(CORSMiddleware, allow_origins=ALLOWED_ORIGINS,
                   allow_methods=["*"], allow_headers=["*"])


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


# ----------------------------------------------------------------------
# /lead  (captura + flywheel)
# ----------------------------------------------------------------------
def _persistir_local(registro: dict):
    """Respaldo en disco. OJO: en Render free el filesystem es efímero (se borra en cada
    deploy/restart). El destino durable real es LEAD_WEBHOOK_URL o Supabase."""
    try:
        pathlib.Path(DATA_DIR).mkdir(parents=True, exist_ok=True)
        with open(os.path.join(DATA_DIR, "leads.jsonl"), "a", encoding="utf-8") as fh:
            fh.write(json.dumps(registro, ensure_ascii=False) + "\n")
    except Exception as e:
        print(f"[lead] no se pudo persistir local: {e}")


async def _forward_webhook(registro: dict):
    if not LEAD_WEBHOOK_URL:
        return
    try:
        async with httpx.AsyncClient(timeout=20) as c:
            await c.post(LEAD_WEBHOOK_URL, json=registro)
    except Exception as e:
        print(f"[lead] webhook falló: {e}")


def _row_tasacion(registro: dict) -> dict:
    """Mapea el payload del tasador a las columnas de la tabla `tasaciones` (La Base Viva).
    Ver migración 20260625120000_tasaciones.sql. Entra con estado 'a_captar'."""
    l = registro.get("lead") or {}
    t = registro.get("tasacion") or {}
    return {
        "estado": "a_captar",
        "origen": l.get("origen") or "tasador",
        "nombre": l.get("nombre"), "whatsapp": l.get("whatsapp"), "email": l.get("email"),
        "zona": t.get("zona"), "tipologia": t.get("tipologia"),
        "lat": t.get("lat"), "lon": t.get("lon"),
        "cubierta": t.get("cubierta"), "descubierta": t.get("descubierta"), "lote": t.get("lote"),
        "ambientes": t.get("ambientes"), "dormitorios": t.get("dormitorios"), "banos": t.get("banos"),
        "antiguedad": t.get("antiguedad"), "estado_conservacion": t.get("estado"), "categoria": t.get("categoria"),
        "barrio_cerrado": t.get("barrioCerrado"),
        "usd_m2_base": t.get("usd_m2_base"), "usd_m2_ajustado": t.get("usd_m2_ajustado"),
        "publicacion": t.get("publicacion"), "cierre_min": t.get("cierre_min"), "cierre_max": t.get("cierre_max"),
        "comparables_usd_m2": t.get("comparables_usd_m2"),
        "payload": registro,
    } if t else {
        "estado": "a_captar", "origen": l.get("origen") or "tasador",
        "nombre": l.get("nombre"), "whatsapp": l.get("whatsapp"), "email": l.get("email"),
        "payload": registro,
    }


async def _forward_supabase(registro: dict):
    """Inserta el lead como fila en `tasaciones` (estado 'a_captar') vía PostgREST.
    El backend usa SERVICE_ROLE → saltea RLS. La tabla destino es LEADS_TABLE (default 'tasaciones')."""
    if not (SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY):
        return
    url = f"{SUPABASE_URL}/rest/v1/{LEADS_TABLE}"
    try:
        async with httpx.AsyncClient(timeout=20) as c:
            r = await c.post(url, json=_row_tasacion(registro), headers={
                "apikey": SUPABASE_SERVICE_ROLE_KEY,
                "authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
                "content-type": "application/json",
                "prefer": "return=minimal"})
            if r.status_code >= 300:
                print(f"[lead] supabase {r.status_code}: {r.text[:300]}")
    except Exception as e:
        print(f"[lead] supabase falló: {e}")


async def _alert_whatsapp(registro: dict):
    """Avisa por WhatsApp a ALERT_WHATSAPP que entró un lead 'a captar'.
    Usa la WhatsApp Business API (igual que el bot DV). OJO: para iniciar conversación
    fuera de la ventana de 24h, Meta exige un template aprobado; el texto libre solo
    funciona si el número de alerta ya tiene sesión abierta con el número del negocio.
    Fallback: ALERT_WEBHOOK_URL (Make/Zapier → WhatsApp)."""
    l = registro.get("lead") or {}
    t = registro.get("tasacion") or {}
    msg = (f"[A CAPTAR] Nueva tasación\n"
           f"{l.get('nombre','?')} · wa {l.get('whatsapp','?')}\n"
           f"{t.get('zona','?')} · {t.get('tipologia','?')} {t.get('cubierta','?')}m²\n"
           f"Publicación: USD {t.get('publicacion','?')}")
    if WABA_TOKEN and PHONE_NUMBER_ID and ALERT_WHATSAPP:
        try:
            async with httpx.AsyncClient(timeout=20) as c:
                await c.post(f"https://graph.facebook.com/v21.0/{PHONE_NUMBER_ID}/messages",
                             headers={"authorization": f"Bearer {WABA_TOKEN}",
                                      "content-type": "application/json"},
                             json={"messaging_product": "whatsapp", "to": ALERT_WHATSAPP,
                                   "type": "text", "text": {"body": msg}})
            return
        except Exception as e:
            print(f"[alert] WABA falló: {e}")
    if ALERT_WEBHOOK_URL:
        try:
            async with httpx.AsyncClient(timeout=20) as c:
                await c.post(ALERT_WEBHOOK_URL, json={"to": ALERT_WHATSAPP, "text": msg, "lead": l, "tasacion": t})
        except Exception as e:
            print(f"[alert] webhook falló: {e}")


@app.post("/lead")
async def lead(req: Request):
    """Recibe {lead:{...}, tasacion:{...}} desde el frontend. Persiste y reenvía."""
    try:
        body = await req.json()
    except Exception:
        return {"ok": False, "error": "JSON inválido"}
    lead_data = body.get("lead") or {}
    if not lead_data.get("whatsapp") and not lead_data.get("email"):
        return {"ok": False, "error": "Falta whatsapp o email"}

    registro = {
        "recibido_at": datetime.datetime.utcnow().isoformat() + "Z",
        "lead": lead_data,
        "tasacion": body.get("tasacion"),
    }
    _persistir_local(registro)
    await _forward_webhook(registro)
    await _forward_supabase(registro)
    await _alert_whatsapp(registro)
    return {"ok": True}


@app.get("/")
def health():
    return {"ok": True, "service": "DV Tasador · Fase 2",
            "actores_configurados": [k for k, v in ACTORS.items() if v],
            "lead_sinks": {"webhook": bool(LEAD_WEBHOOK_URL),
                           "supabase": bool(SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY)}}
