# Metodología del motor de tasación

Todo vive en el objeto `PARAMS` dentro de `frontend/index.html`. Editar ahí.

## Fórmula

```
supH      = sup_cubierta × 1.00 + sup_descubierta × 0.05
USD/m²base = casaBaseOverride[zona]            (si es casa y hay dato)
             | zonas[zona] × factorCasaDefault (casa sin dato)
             | zonas[zona] × factorPH          (PH)
             | zonas[zona]                      (depto)
USD/m²adj  = USD/m²base × antig × estado × categoria × atributos × (barrioCerrado?)
estimado   = supH × USD/m²adj            → valor de publicación
publicacion= round5(estimado)
cierre     = estimado × [0.88 .. 0.93]   → 7-12% por debajo de la publicación
competitivo= publicacion × [0.97 .. 1.03]
```

## Tablas (valores 2025/26, oferta — calibrables)

- **zonas**: USD/m² de departamentos por barrio (de Puerto Madero a Puertos del Lago).
- **casaBaseOverride**: USD/m² de casas por barrio donde hay dato real. Anclas actuales: La Lucila 2.400, Acassuso 2.000.
- **antig**: estrenar 1.00 · 6-15 0.99 · 16-30 0.97 · 31-50 0.93 · +50 0.88.
- **estado**: refaccionar 0.85 · bueno 0.93 · muy bueno 1.00 · excelente 1.04 · a estrenar 1.07.
- **categoria**: económica 0.95 · standard 1.00 · buena 1.03 · premium 1.07.
- **amenities** (mínimos, ya están en la oferta): cochera 0.005 · pileta 0.012 · parrilla 0.004.
- **barrioCerradoCoef**: 1.04.

## Por qué bases separadas casa/depto
Las casas cotizan distinto por m² que los deptos del mismo barrio (incluyen lote, más superficie). Derivarlas con un factor único sobre deptos descalibra (daba +19% en el caso La Lucila). La forma correcta es una tabla de casas propia, que se va llenando con cierres reales.

## Límite del modelo
Una tabla por barrio es una estimación gruesa (±10-20%) para una propiedad puntual. La precisión real la dan los **comparables en vivo** del backend, que reemplazan el promedio del barrio por la oferta de la cuadra. Próximo paso: que esos comparables recalibren el número (promedio ponderado), no que solo se muestren.
