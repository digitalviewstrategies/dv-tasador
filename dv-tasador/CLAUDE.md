# CLAUDE.md — DV Tasador Zona Norte

Contexto para retomar el proyecto. Leer esto antes de tocar nada.

## Qué es
Tasador automático de propiedades de **Zona Norte GBA** (de Puerto Madero a Puertos del Lago, entre Panamericana y el río) para **Digital View (DV)**, agencia de marketing inmobiliario. El usuario carga pocos datos + la dirección geolocalizada y el sistema devuelve un rango de valor (publicación / competitivo / cierre) y 6 comparables reales del barrio. El fin comercial es **captar vendedores** (lead de captación) y alimentar la base del Super Proyecto de DV.

## Idioma y voz
- Español rioplatense, **voseo**. Sin emojis. Tono directo, sin vueltas.
- Copy de marca DV: juvenil, humano, sin clichés inmobiliarios.

## Branding DV (mantener siempre)
- Colores: azul eléctrico `#1B38E8`, lima ácido `#CCFF00`, fondo casi-negro `#080A12`, líneas `#1E2230`, texto `#F4F6FB`, gris `#8A90A6`.
- Tipografías: **Syne ExtraBold** (titulares y logo), **Inter** (cuerpo/UI), **JetBrains Mono** (datos, badges, números).
- Logo: `[DIGITAL VIEW]` — corchetes en azul, siempre en mayúscula.
- Motivos: corchetes `[ ]`, grilla de brackets sutil de fondo, **sombras duras** (offset sólido sin blur), estética Linear/Vercel/Framer.

## Stack y arquitectura
- **frontend/index.html** — landing self-contained (HTML/CSS/JS vanilla). Sin build. Fuentes por Google Fonts CDN, Leaflet por cdnjs.
  - Geolocalizador: **Leaflet + OpenStreetMap + Nominatim** (autocomplete + reverse geocode), todo sin API key.
  - Motor de tasación client-side en el objeto `PARAMS` (ver `docs/metodologia.md`).
  - Constante `API_BASE` (arriba del `<script>`): vacía = modo demo; con URL del backend = comparables y fotos en vivo.
- **backend/app.py** — FastAPI. Dos endpoints:
  - `GET /comparables` — busca propiedades por cercanía + características vía **Apify** (Zonaprop, MercadoLibre; sumar Argenprop/Remax/ZipCode), rankea por similitud, devuelve top 6.
  - `POST /analizar-fotos` — manda las fotos a **Claude (visión)** y devuelve estado/categoría/calidad para autocompletar el form.
  - Variables: `APIFY_TOKEN`, `ANTHROPIC_API_KEY`, `ACTOR_ZONAPROP`, `ACTOR_MERCADOLIBRE` (ver `backend/.env.example`).
- Deploy: frontend en **GitHub Pages** (workflow en `.github/workflows/`), backend en **Render** (blueprint `render.yaml`, igual que el pipeline de Radar Inmobiliario).

## Estado actual (v3)
- Motor **calibrado** con un cierre real (casa La Lucila, Díaz Vélez al 500, 191 m², publicación USD 480.000). El tasador devuelve ~485.000 para ese caso (antes daba 570.000).
- Geolocalizador con autocompletado que marca solo el mejor resultado en el mapa.
- Comparables y análisis de fotos: la UI está lista pero **esperan el backend desplegado** (sin él, modo demo / mensajes de configuración).

## Decisiones y aprendizajes clave (no repetir errores)
1. **Bases separadas casa vs depto.** No derivar casas con un factor sobre el valor de deptos: las casas cotizan distinto por m². Usar `PARAMS.casaBaseOverride` por barrio, anclado con cierres reales. `factorCasaDefault` (0.72) es solo placeholder para barrios sin dato.
2. **No doble-contar amenities.** La oferta de mercado ya incluye casas con pileta/parrilla/cochera. Los coeficientes de amenities son mínimos a propósito.
3. **Descubierta pesa poco en casas** (`sup.descubierta = 0.05`): el valor de casa ya incluye el lote; sumar el jardín entero duplica la tierra.
4. **La tabla es estimación gruesa (±10-20%).** La precisión real la dan los **comparables en vivo** (reemplazan el promedio de barrio por la oferta de la cuadra). Esto es la Fase 2 y es lo que cierra el problema de precisión.
5. **Cierre = publicación × 0.88–0.93** (la oferta publicada está 7-12% sobre el cierre real).
6. **Calibrar siempre con cierres reales** (no de publicación). Ver `docs/calibracion.md`.

## Restricciones legales (inmobiliario AR)
- Toda pieza muestra "no reemplaza la tasación de un corredor matriculado" y deja lugar para **corredor responsable (matrícula CMCPSI/CUCICBA)**.
- Nunca publicar "sin comisión", tasas de financiación ni claims cerrados sin confirmación explícita de Valentín.

## Roadmap priorizado (ver docs/roadmap.md)
1. **Captura de lead** (lo de mayor retorno): pedir nombre + WhatsApp + mail para ver el resultado completo → entra a Tokko/Pipedrive + dispara el bot. Convierte la herramienta en canal de captación medible (ideal para pauta Meta).
2. **Comparables que recalibran el valor** (no solo se muestran): promedio ponderado tabla + comparables homogeneizados.
3. **Modelo de casas con incidencia de terreno** (lote × incidencia + construcción depreciada).
4. **Informe automático con branding DV** por mail (PDF) al dejar los datos.
5. **Flywheel de datos**: guardar cada tasación (inputs + resultado + comparables) como base propia.

## Skills disponibles (`.claude/skills/`)
- **grill-me** — entrevista de brainstorm que guarda cada respuesta a disco.
- **calibrar-tasador** — ajustar las bases de `PARAMS` con un cierre real.
- **agregar-microzona** — sumar un barrio nuevo (valor m² + alias del geocoder).
- **agregar-portal** — sumar una fuente de comparables (Apify / base propia) al backend.
- **deploy-check** — validar el backend antes de pushear a Render.
- **qa-visual** — renderizar la landing con Playwright y sacar screenshots para QA.
- **lead-capture** — implementar la captura de lead (mejora #1 del roadmap).
- **informe-acm** — generar el informe de valor premium en PDF con branding DV.

## Cómo trabaja Valentín (Valen)
- "Show first, then iterate": prefiere ver algo renderizado y corregir campo por campo.
- Decisiones concretas > menús de opciones. Honestidad técnica sobre qué se puede y qué no.
