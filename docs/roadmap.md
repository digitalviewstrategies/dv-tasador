# Roadmap

Priorizado por retorno para DV. El tasador no es una calculadora suelta: es una máquina de captación de vendedores y la puerta de entrada a la base del Super Proyecto.

## 1. Captura de lead (máxima prioridad) — ✅ IMPLEMENTADO (v4)
Para ver el resultado completo / los comparables / el informe, el dueño deja **nombre + WhatsApp + mail**. Cada tasación = lead de captación caliente (alguien que piensa vender, con la propiedad ya cargada) → entra a Tokko/Pipedrive → dispara el bot de seguimiento. Convierte la herramienta en canal medible, ideal para pauta de Meta ("Tasá tu casa en Zona Norte en 1 minuto").
- Hecho: gate en el resultado (teaser del valor + form), `POST /lead` en el backend, persistencia local + reenvío a `LEAD_WEBHOOK_URL` y/o inserción en Supabase. Fallback `LEAD_ENDPOINT` (Formspree) si no hay backend.
- Pendiente de Valen: elegir el sink real (webhook a Tokko/Pipedrive o tabla de dbsuper), cargar `DV_WHATSAPP`, conectar el disparo del bot de seguimiento.

## 2. Comparables que recalibran el valor — ✅ IMPLEMENTADO (v4, base)
Hoy se muestran al costado pero no entran al número. Siguiente: el valor final = **promedio ponderado entre la tabla y los 6 comparables homogeneizados** que trae el backend. Ahí la tasación queda respaldada por la oferta vigente del barrio.
- Hecho: blend tabla 60% / comparables 40% (`PARAMS.compWeight`) usando `promedio_usd_m2` del backend; el header pasa a "recalibrado".
- Pendiente: homogeneizar cada comparable a las condiciones de la propiedad (hoy se usa el promedio crudo USD/m²), no solo promediar.

## 3. Modelo de casas con incidencia de terreno
Reemplazar el factor casa por **lote (incidencia × m²) + construcción (m² cubierto × costo depreciado)**. Es lo más correcto para Zona Norte, donde la tierra manda.

## 4. Informe automático con branding DV
Al dejar los datos, mandar por mail el **informe de valor en PDF** (mismo formato premium ya usado en ACM). Da valor real, posiciona a DV como experto del barrio, sube la conversión a exclusiva.

## 5. Flywheel de datos
Guardar cada tasación (inputs + resultado + comparables) en una base. Con el tiempo es el activo que ninguna herramienta genérica tiene: precios y demanda reales de la zona, que retroalimentan el motor y el Super Proyecto.

## Técnico pendiente
- Sumar Argenprop / Remax / ZipCode como actores en `backend/app.py` (`ACTORS`).
- Enchufar la base propia de DV como una fuente más de comparables.
- Completar corredor matriculado responsable antes de exponer a clientes.
