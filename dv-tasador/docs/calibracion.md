# Calibración con cierres reales

El motor mejora con cada cierre real cargado. Usar **precio de cierre** (lo que se vendió), no de publicación.

## Cómo calibrar
1. Anotá la operación: barrio, tipología, m² cubierto, precio de cierre.
2. USD/m² de cierre = precio ÷ m² cubierto.
3. En `frontend/index.html` → `PARAMS.casaBaseOverride[barrio]` (casas) o `PARAMS.zonas[barrio]` (deptos): ajustá el valor hasta que el tasador devuelva ese cierre para una propiedad de ese estilo (estado/categoría típicos).
4. Guardá y recargá. No compila nada.

## Ancla actual
| Barrio | Tipología | m² cub | Operación | USD/m² | Fuente |
|---|---|---|---|---|---|
| La Lucila | Casa | 191 | USD 480.000 (publicación) | ~2.513 | aviso ZipCode, Díaz Vélez al 500 |

> Nota: el ancla de La Lucila es precio de **publicación**; idealmente reemplazar por el de **cierre** cuando se conozca.

## Tabla para ir cargando (completar con DV)
| Barrio | Tipología | m² cub | Precio cierre USD | USD/m² | Fecha |
|---|---|---|---|---|---|
|  |  |  |  |  |  |

Con 5-10 cierres por barrio, las bases dejan de ser estimación y pasan a ser dato propio de DV.
