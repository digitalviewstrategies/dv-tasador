# DV · Tasador Zona Norte

Tasador automático de propiedades de Zona Norte GBA para **Digital View**. Geolocaliza la dirección, resuelve la micro-zona y el valor de m², estima el rango de valor y trae 6 comparables reales del barrio. Pensado como **canal de captación de vendedores**.

## Estructura

```
dv-tasador/
├── CLAUDE.md                 # contexto del proyecto (leer primero)
├── render.yaml               # blueprint de deploy del backend en Render
├── frontend/
│   └── index.html            # la landing (self-contained, sin build)
├── backend/
│   ├── app.py                # FastAPI: /comparables + /analizar-fotos
│   ├── requirements.txt
│   └── .env.example          # variables de entorno
├── docs/
│   ├── metodologia.md        # cómo calcula el motor
│   ├── calibracion.md        # cómo afinar con cierres reales
│   └── roadmap.md            # próximas mejoras priorizadas
├── .claude/skills/           # skills para Claude Code (calibrar, deploy-check, qa-visual, etc.)
└── .github/workflows/
    └── deploy-pages.yml       # publica el frontend en GitHub Pages
```

## Frontend (rápido)

Abrí `frontend/index.html` en el navegador. Funciona solo (geolocalizador, micro-zonas, USD/m² automático, tasación). Comparables y fotos pasan a vivo cuando conectás el backend: editá la constante `API_BASE` arriba del `<script>` con la URL de Render.

**Deploy:** se publica solo en GitHub Pages con el workflow incluido (push a `main` que toque `frontend/**`). En el repo: Settings → Pages → Source: **GitHub Actions**.

## Backend (rápido)

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # completá los tokens
uvicorn app:app --reload --port 8000
```

**Deploy en Render:** el repo trae `render.yaml`. En Render → New → **Blueprint** → elegí el repo → detecta el servicio con `rootDir: backend` (esto evita el error "Could not import module app"). Cargá las env vars (`APIFY_TOKEN`, `ANTHROPIC_API_KEY`, `ACTOR_ZONAPROP`, `ACTOR_MERCADOLIBRE`).

## Conectar las dos partes

1. Desplegá el backend → copiá su URL pública (`https://...onrender.com`).
2. En `frontend/index.html`: `const API_BASE = "https://...onrender.com";`
3. Commit + push → Pages se actualiza solo.

## Estado

v3 — motor calibrado con cierre real. Ver `CLAUDE.md` para decisiones y roadmap.
