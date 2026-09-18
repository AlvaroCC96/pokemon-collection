# E2E Checklist — ETAPA 7.1

Batería formal de pruebas end-to-end para validar la aplicación completa (backend FastAPI + SQLite + providers reales + frontend React/Pokédex) antes de containerizar.

Este documento es **preparación**: define escenarios y su estado inicial (`PENDING`). La ejecución de lo automatizable ocurre en ETAPA 7.2, tras tu aprobación.

Construido inspeccionando el código real (no supuestos): `backend/app/api/*.py`, `models/*.py`, `schemas/*.py`, `services/*.py`, `providers/identification/*.py`, `providers/price/*.py`, `core/config.py`, `core/language_codes.py`, los 131 tests existentes en `backend/tests/`, `frontend/src/api/*.ts`, `frontend/src/pages/*.tsx`, `README.md` y `ARCHITECTURE.md`.

---

## 1. Resumen

| | Cantidad |
|---|---|
| Escenarios totales | **137** |
| `AUTOMATED` (pytest, sin red externa, DB temporal aislada) | 77 |
| `AMBOS` (automatizable, pero depende de un proveedor externo real — pokemontcg.io / pokemon-card.com / TCGdex / PokeAPI) | 16 |
| `MANUAL` (UI visual, mobile, o incurre en costo real de OpenAI) | 44 |
| Ejecutable en 7.2 sin tu intervención (`AUTOMATED` + `AMBOS`) | **93** |

Áreas cubiertas: Health/arranque, CRUD de cartas, Identificación (ES/EN/JA/ZH-TW/ZH-CN), Regresiones de bugs ya corregidos, Paginación, Price Service, Trazabilidad, Update-all, Stats, Frontend (Home/Scan/Card Data), Mobile, Persistencia, Errores externos.

De los 137, **~35 ya están cubiertos por los 131 tests que existen hoy** en `backend/tests/` (los marco explícitamente como "ya cubierto" en la tabla, con el archivo) — los mantengo en la lista como regresión formal, no los reescribo. El resto son escenarios nuevos que redactaré como tests en 7.2.

---

## 2. Dataset de prueba temporal

**Automatizado (`AUTOMATED`/`AMBOS` vía pytest):** cero riesgo para tus datos reales. `backend/tests/conftest.py` ya crea un SQLite temporal (`tempfile.mkstemp`) por sesión de test, completamente separado de `data/pokemon_collection.db`. Todo lo que agregue en 7.2 usa ese mismo fixture — nunca toca tu base real.

**Manual (contra el servidor real, tu `data/pokemon_collection.db`):** propongo una convención para que cualquier carta de prueba sea trivial de identificar y borrar:

- `collector_number` con prefijo `E2E-` (ej. `E2E-001`, `E2E-002`, ...).
- `name` con prefijo `[E2E] ` (ej. `[E2E] Pikachu ex`).
- Limpieza al terminar: `DELETE FROM cards WHERE collector_number LIKE 'E2E-%';` (el cascade de `Card.price_snapshots` borra snapshots/observations asociadas automáticamente — confirmado en `models/card.py`).

**Cartas reales para smoke-tests de identificación por idioma** (reutilizando las que ya validamos juntos en ETAPA 5.5/6, en vez de inventar nuevas):
- ES/EN: `Charizard ex` `199/165` (Scarlet & Violet 151).
- JA: `Pikachu ex` `764/742` (ya confirmado que funciona vía `pokemon_card_com`).
- ZH-TW / ZH-CN: las que tengas a mano — si no, puedo proponer una carta común (ej. Pikachu) al ejecutar 7.2.

---

## 3. Convenciones de la tabla

- **Tipo**: `AUTOMATED` (pytest, sin intervención), `MANUAL` (requiere ojos/manos humanas o gasta cuota real de OpenAI), `AMBOS` (automatizable pero depende de un servicio externo real, por lo que puede fallar por causas ajenas al código).
- **Estado**: todos inician en `PENDING`.
- Los códigos de error citados son literales del código (`app/main.py` exception handlers): `CARD_NOT_FOUND` (404), `IDENTIFICATION_PROVIDER_ERROR` (502), `PRICE_PROVIDER_ERROR` (502), `PRICE_SEARCH_FAILED` (422), `PRICE_PROVIDER_NOT_CONFIGURED` (503), `VALIDATION_ERROR` (422), `INTERNAL_ERROR` (500).

---

## 4. Health / Arranque

| ID | Escenario | Precondición | Pasos | Resultado esperado | Tipo | Estado |
|---|---|---|---|---|---|---|
| E2E-HEALTH-001 | Backend arranca sin excepciones | venv instalado, `.env` presente | `uvicorn app.main:app` | Proceso queda escuchando en `:8000`, sin traceback en consola | AMBOS | PENDING |
| E2E-HEALTH-002 | `GET /api/health` responde 200 | Backend arriba | `curl /api/health` | `{"status":"ok","database":"ok"}` — ya cubierto por `test_health.py` | AUTOMATED | PENDING |
| E2E-HEALTH-003 | Frontend arranca sin errores de consola | `npm install` hecho | `npm run dev` | Vite sirve en `:5173`, sin error en terminal ni consola del navegador | MANUAL | PENDING |
| E2E-HEALTH-004 | CORS permite al frontend llamar al backend | Ambos arriba, `CORS_ORIGINS` default | Request con header `Origin: http://localhost:5173` a `/api/health` | Respuesta incluye `Access-Control-Allow-Origin` para ese origen | AMBOS | PENDING |
| E2E-HEALTH-005 | SQLite se crea/abre en el arranque | `data/pokemon_collection.db` no existe | Arrancar backend | Archivo `.db` se crea (`init_db()` en `lifespan`) | AUTOMATED | PENDING |
| E2E-HEALTH-006 | Tablas esperadas existen | DB inicializada | `SELECT name FROM sqlite_master WHERE type='table'` | Incluye `cards`, `card_price_snapshots`, `price_observations` | AUTOMATED | PENDING |
| E2E-HEALTH-007 | Home carga stats reales sin error de red | Backend + frontend arriba | Abrir `http://localhost:5173` | `StatsHeader` muestra datos, sin `ErrorState` | MANUAL | PENDING |

---

## 5. CRUD de cartas

Base: `POST/GET/PUT/DELETE /api/cards[/{id}]`, `schemas/card.py`, `services/card_service.py`.

| ID | Escenario | Precondición | Pasos | Resultado esperado | Tipo | Estado |
|---|---|---|---|---|---|---|
| E2E-CARD-001 | Crear carta con todos los campos | DB limpia | `POST /api/cards` con name/collector_number/set_name/language/rarity/image_url/quantity | 201, `CardResponse` con `identified=false`, `external_card_id=null` | AUTOMATED | PENDING |
| E2E-CARD-002 | Crear carta solo con campos obligatorios | — | `POST /api/cards` con solo `name`+`collector_number` | 201, opcionales quedan `null`, `quantity=1` (default) | AUTOMATED | PENDING |
| E2E-CARD-003 | Crear carta con `quantity` > 1 | — | `POST /api/cards` con `quantity=4` | 201, `quantity=4` persistido | AUTOMATED | PENDING |
| E2E-CARD-004 | Crear carta con `name` vacío | — | `POST /api/cards` con `name=""` | 422 `VALIDATION_ERROR` (`min_length=1`) | AUTOMATED | PENDING |
| E2E-CARD-005 | Crear carta con `quantity` inválida | — | `POST /api/cards` con `quantity=0` | 422 `VALIDATION_ERROR` (`ge=1`) | AUTOMATED | PENDING |
| E2E-CARD-006 | Obtener carta existente | Carta creada | `GET /api/cards/{id}` | 200, datos coinciden | AUTOMATED | PENDING |
| E2E-CARD-007 | Obtener carta inexistente | — | `GET /api/cards/999999` | 404 `CARD_NOT_FOUND` | AUTOMATED | PENDING |
| E2E-CARD-008 | Listar cartas ordenadas | 3 cartas creadas en orden | `GET /api/cards` | Orden `created_at desc` (más reciente primero) | AUTOMATED | PENDING |
| E2E-CARD-009 | Editar carta parcialmente | Carta con varios campos | `PUT /api/cards/{id}` con solo `quantity` | Solo `quantity` cambia; el resto queda igual (`exclude_unset`) | AUTOMATED | PENDING |
| E2E-CARD-010 | Editar carta inexistente | — | `PUT /api/cards/999999` | 404 `CARD_NOT_FOUND` | AUTOMATED | PENDING |
| E2E-CARD-011 | Eliminar carta | Carta creada | `DELETE /api/cards/{id}`, luego `GET` | 204, luego 404 | AUTOMATED | PENDING |
| E2E-CARD-012 | Eliminar carta inexistente | — | `DELETE /api/cards/999999` | 404 `CARD_NOT_FOUND` | AUTOMATED | PENDING |
| E2E-CARD-013 | Eliminar carta con histórico borra snapshots/observations (cascade) | Carta con ≥1 snapshot+observations | `DELETE /api/cards/{id}` | Filas de `card_price_snapshots`/`price_observations` de esa carta desaparecen (sin huérfanos) | AUTOMATED | PENDING |

---

## 6. Identificación multidioma

Base: `POST /api/cards/identify`, `services/identification_service.py`, registry de providers por idioma.

| ID | Escenario | Precondición | Pasos | Resultado esperado | Tipo | Estado |
|---|---|---|---|---|---|---|
| E2E-ID-001 | `language=null` usa provider western | Fake registry | `identify()` sin `language` | Enrutado a `registry.western` — ya cubierto por `test_identification_routing.py::test_language_none_routes_to_western` | AUTOMATED | PENDING |
| E2E-ID-002 | ES: `single_match` real | pokemontcg.io accesible | `POST /identify` con `Charizard ex` `199/165` | `single_match`, 1 candidato con set/rarity/image_url reales | AMBOS | PENDING |
| E2E-ID-003 | ES: `multiple_matches` real | — | `POST /identify` con nombre común sin acotar (ej. solo `Pikachu` + número parcial) | `multiple_matches`, ≥2 candidatos | AMBOS | PENDING |
| E2E-ID-004 | EN/ES: `not_found` real | — | `POST /identify` con carta inventada | `not_found`, `candidates=[]` | AMBOS | PENDING |
| E2E-ID-005 | JA: `single_match` real (pokemon-card.com) | — | `POST /identify` con `Pikachu ex` `764/742` `language=JA` | `single_match` o candidato correcto entre resultados, `source="pokemon-card.com"`, `collector_number=null` (limitación conocida de la fuente) | AMBOS | PENDING |
| E2E-ID-006 | JA: composite cae a TCGdex si pokemon-card.com falla | Fake: primero raise, segundo responde | `identify()` con `language=JA` | Resultado del segundo provider — ya cubierto por `test_identification_routing.py::test_japanese_provider_failure_does_not_crash_when_it_is_a_fallback_chain` | AUTOMATED | PENDING |
| E2E-ID-007 | ZH-TW real vía TCGdex | — | `POST /identify` con carta conocida `language=ZH-TW` | Candidatos con `source="tcgdex_zh_tw"`, `language` poblado | AMBOS | PENDING |
| E2E-ID-008 | ZH-CN real, incluyendo el hueco de datos conocido | — | `POST /identify` con `language=ZH-CN` para un set donde TCGdex tiene `cardCount>0` pero `cards:[]` (documentado en ARCHITECTURE.md) | `not_found` limpio, sin excepción 500 | AMBOS | PENDING |
| E2E-ID-009 | `language=Chino` genérico prueba ZH-TW y luego ZH-CN | Fake | `identify()` con `language=Chino` | Orden TW→CN respetado — ya cubierto por `test_identification_routing.py::test_generic_chinese_tries_traditional_then_simplified` | AUTOMATED | PENDING |
| E2E-ID-010 | `language` del candidato reflejа la fuente | Real TCGdex | Candidatos ZH-TW/ZH-CN | `language` no nulo cuando la fuente lo expone (TCGdex sí, pokemontcg.io/pokemon-card.com no) | AMBOS | PENDING |
| E2E-ID-011 | `source` siempre poblado | Fake + real | Cualquier búsqueda con resultados | Cada candidato trae `source` (`pokemon_tcg_io`/`pokemon-card.com`/`tcgdex_ja`/`tcgdex_zh_tw`/`tcgdex_zh_cn`) — nuevo test unitario a agregar | AUTOMATED | PENDING |
| E2E-ID-012 | `collector_number=null` para pokemon-card.com | Fake HTTP mockeado | Candidato de `PokemonCardComProvider` | `collector_number`, `set_name`, `rarity` son `null` explícitos, nunca inventados | AUTOMATED | PENDING |
| E2E-ID-013 | Re-identificar carta existente con override | Carta guardada | `POST /api/cards/{id}/identify` con `IdentifyOverride` (nuevo idioma) | Usa el override, no los datos guardados, para ese campo | AUTOMATED | PENDING |
| E2E-ID-014 | Re-identificar sin override usa datos guardados | Carta guardada | `POST /api/cards/{id}/identify` sin body | Usa `name`/`collector_number`/`language` de la carta en DB | AUTOMATED | PENDING |
| E2E-ID-015 | Todos los providers fallan → 502 | Fake: todos raise | `POST /identify` | 502 `IDENTIFICATION_PROVIDER_ERROR` — ya cubierto por `test_identification_routing.py::test_provider_failure_propagates_as_identification_provider_error_not_a_crash` | AUTOMATED | PENDING |

---

## 7. Regresiones de bugs ya corregidos

Estos bugs **no deben reaparecer**. Ver sección "Errores y correcciones" del historial del proyecto.

| ID | Escenario | Bug original | Resultado esperado | Tipo | Estado |
|---|---|---|---|---|---|
| E2E-REGR-001 | `Charizard GX` (espacio) encuentra `Charizard-GX` (guión) en catálogo | pokemontcg.io usa guión, usuario tipeaba espacio | Candidato encontrado vía `_spacing_variants` | AMBOS | PENDING |
| E2E-REGR-002 | `Charizard-VMAX` (guión) encuentra `Charizard VMAX` (espacio) en catálogo | Caso inverso al anterior | Candidato encontrado | AMBOS | PENDING |
| E2E-REGR-003 | `074/073` matchea `74` almacenado | Ceros iniciales no se quitaban | `_normalize_number` los quita, candidato encontrado | AUTOMATED | PENDING |
| E2E-REGR-004 | `"Ingles"` (sin tilde) matchea `EN` | Heurística comparaba solo 2 letras | `_language_matches`/`normalize_language_code` — ya cubierto por `test_price_service.py::test_language_matches_ingles_without_accent_equals_en` | AUTOMATED | PENDING |
| E2E-REGR-005 | ZH-TW y ZH-CN nunca colapsan a "ZH" genérico | Antes ambos colapsaban a un bucket "Chinese" | Providers y matching de idioma los tratan distinto — ya cubierto por `test_identification_routing.py` (`test_zh_tw_routes_to_traditional_chinese_provider`, `test_zh_cn_routes_to_simplified_chinese_provider`) | AUTOMATED | PENDING |
| E2E-REGR-006 | Dos idiomas no reconocidos y distintos no matchean por accidente | Ambos normalizarían a `None` y colisionarían | `_language_matches` compara el string crudo cuando ambos son no reconocidos — nuevo test unitario a agregar | AUTOMATED | PENDING |

---

## 8. Paginación ("Cargar más")

| ID | Escenario | Precondición | Pasos | Resultado esperado | Tipo | Estado |
|---|---|---|---|---|---|---|
| E2E-PAGE-001 | `has_more=true` cuando `thisPage<maxPage` | Fake HTTP con `maxPage=3` | `find_candidates()` | `has_more=True` | AUTOMATED | PENDING |
| E2E-PAGE-002 | `has_more=false` para providers sin paginación real | pokemontcg.io/TCGdex | Cualquier búsqueda | `has_more=False` siempre | AUTOMATED | PENDING |
| E2E-PAGE-003 | `page=2` real trae candidatos distintos a `page=1` | JA, nombre común (ej. Pikachu) | `POST /identify` `page=1` luego `page=2` | Sin `external_id` repetidos entre páginas | AMBOS | PENDING |
| E2E-PAGE-004 | Frontend "Cargar más" acumula sin resetear selección | Scan Mode, `multiple_matches` | Seleccionar un candidato de la página 1, luego "Cargar más" | Selección se mantiene, nuevos candidatos se agregan al final | MANUAL | PENDING |
| E2E-PAGE-005 | Sin colisión de `key` entre páginas | Scan Mode | Cargar 2+ páginas | React no arroja warning de `key` duplicada (`external_id-index`) | AMBOS | PENDING |
| E2E-PAGE-006 | Fin real de resultados oculta "Cargar más" | Última página | Cargar hasta el final | Botón desaparece cuando `has_more=false` | AMBOS | PENDING |
| E2E-PAGE-007 | Guardar carta seleccionada de una página cargada después de la 1 | Scan Mode, página 2+ | Seleccionar candidato de pág. 2, "Agregar a mi colección" | Carta creada con los datos exactos de ese candidato | MANUAL | PENDING |
| E2E-PAGE-008 | Nombre japonés común dispara paginación real | JA | Buscar un Pokémon muy reimpreso | `hitCnt` > tamaño de página, `has_more=true` en página 1 | AMBOS | PENDING |

---

## 9. Price Service

Base: `services/price_service.py`. La mayoría de la lógica pura ya tiene cobertura en `test_price_service.py` / `test_price_api.py` / `test_price_history.py` — listada aquí como regresión formal.

| ID | Escenario | Resultado esperado | Ya cubierto por | Tipo | Estado |
|---|---|---|---|---|---|
| E2E-PRICE-001 | Solo observaciones Chile → `market_scope=CHILE` | Snapshot con scope Chile | `test_price_service.py::test_select_market_group_prefers_chile` | AUTOMATED | PENDING |
| E2E-PRICE-002 | Chile + internacional mezclados → Chile gana, internacional se guarda pero no se usa | `market_scope=CHILE`, obs. internacional con `included_in_estimate=false` | `test_price_api.py` (Chile-first) | AUTOMATED | PENDING |
| E2E-PRICE-003 | Solo internacional → fallback | `market_scope=INTERNATIONAL` | `test_select_market_group_falls_back_to_international` | AUTOMATED | PENDING |
| E2E-PRICE-004 | Monedas mezcladas → se usa la dominante | `_select_currency_group` | `test_select_currency_group_picks_dominant_currency` | AUTOMATED | PENDING |
| E2E-PRICE-005 | Outlier excluido del cálculo pero persistido | `is_outlier=true`, `included_in_estimate=false`, sigue en la tabla | `test_mark_outliers_*` | AUTOMATED | PENDING |
| E2E-PRICE-006 | Todas las observaciones son outliers | 422 `PRICE_SEARCH_FAILED` | Nuevo test a nivel API a confirmar/agregar | AUTOMATED | PENDING |
| E2E-PRICE-007 | Provider no encuentra nada | 422 `PRICE_SEARCH_FAILED` ("no se encontró ninguna referencia") | Nuevo test a nivel API a confirmar/agregar | AUTOMATED | PENDING |
| E2E-PRICE-008 | Ninguna observación indica mercado reconocible | 422 `PRICE_SEARCH_FAILED` | Nuevo test a agregar | AUTOMATED | PENDING |
| E2E-PRICE-009 | Filtro de idioma mantiene coincidencias + idioma desconocido | `_select_language_group` | `test_select_language_group_keeps_matching_and_unknown_language` | AUTOMATED | PENDING |
| E2E-PRICE-010 | Idioma de la carta sin ninguna coincidencia → falla con mensaje específico | 422 con mensaje sobre idioma | `test_update_price_language_with_no_matching_observations_fails` | AUTOMATED | PENDING |
| E2E-PRICE-011 | Confidence sube con más fuentes/menos dispersión, baja ×0.7 si es internacional | Scores correctos | `test_confidence_score_*` | AUTOMATED | PENDING |
| E2E-PRICE-012 | Redondeo: CLP entero, otras monedas 2 decimales | `_round_price` | Nuevo test unitario directo a `_round_price` (hoy solo probado indirectamente) | AUTOMATED | PENDING |
| E2E-PRICE-013 | `price_change`/`price_change_percent` solo vs. snapshot compatible (misma moneda+scope) | `_find_previous_compatible_snapshot` | `test_price_history_only_compares_compatible_snapshots` | AUTOMATED | PENDING |
| E2E-PRICE-014 | `PRICE_PROVIDER_NOT_CONFIGURED` sin `OPENAI_API_KEY` | 503 | Nuevo test a agregar (override `get_price_provider` para simular ausencia de key) | AUTOMATED | PENDING |
| E2E-PRICE-015 | Actualización real de precio para una carta barata/común conocida | Precio CLP plausible, `source_url` real, snapshot persistido | — (requiere `OPENAI_API_KEY`, gasta cuota real) | MANUAL | PENDING |
| E2E-PRICE-016 | Actualización real para una carta sin mercado chileno esperado | `market_scope=INTERNATIONAL` plausible | — (gasta cuota real) | MANUAL | PENDING |

---

## 10. Trazabilidad (snapshots + observations)

| ID | Escenario | Resultado esperado | Tipo | Estado |
|---|---|---|---|---|
| E2E-TRACE-001 | Dos `update-price` seguidos crean 2 snapshots distintos | Histórico tiene ambos, el viejo no se sobrescribe | AUTOMATED | PENDING |
| E2E-TRACE-002 | Observaciones excluidas (idioma/mercado/outlier) igual se guardan | Nunca se borran, `included_in_estimate=false` | AUTOMATED | PENDING |
| E2E-TRACE-003 | `is_outlier` solo aplica dentro del grupo de cálculo | Una obs. de otro mercado/idioma nunca es `is_outlier=true` | AUTOMATED | PENDING |
| E2E-TRACE-004 | `included_in_estimate` consistente con la mediana usada | Solo las usadas en `statistics.median` quedan `true` | AUTOMATED | PENDING |
| E2E-TRACE-005 | `source_url` se conserva verbatim (incluyendo `null`) | Provider → DB → `GET /prices` sin alteración | AUTOMATED | PENDING |
| E2E-TRACE-006 | Borrar carta elimina snapshots/observations (sin huérfanos) | Cruzar con E2E-CARD-013 | AUTOMATED | PENDING |
| E2E-TRACE-007 | `GET /api/cards/{id}/prices` nunca invoca al PriceProvider | Mock del provider con 0 llamadas tras el GET | AUTOMATED | PENDING |
| E2E-TRACE-008 | Dos snapshots creados en el mismo segundo ordenan bien | Orden correcto vía tiebreak `(checked_at, id)` | AUTOMATED | PENDING |

---

## 11. Update-all

| ID | Escenario | Ya cubierto por | Resultado esperado | Tipo | Estado |
|---|---|---|---|---|---|
| E2E-BULK-001 | 0 cartas | `test_update_all_empty_collection` | `total=updated=failed=0` | AUTOMATED | PENDING |
| E2E-BULK-002 | N cartas, todas OK | `test_update_all_updates_every_card` | `updated=N` | AUTOMATED | PENDING |
| E2E-BULK-003 | 1 falla, resto sigue | `test_update_all_one_card_failing_does_not_abort_the_rest` | `updated=N-1, failed=1` | AUTOMATED | PENDING |
| E2E-BULK-004 | Error por carta identificable | `test_update_all_reports_price_search_failed_per_card` | `details[].error` con código correcto | AUTOMATED | PENDING |
| E2E-BULK-005 | Concurrencia nunca excede `PRICE_UPDATE_CONCURRENCY` (default 2) | — **hueco, no existe hoy** | Fake provider que cuenta llamadas simultáneas nunca supera el límite | AUTOMATED | PENDING |
| E2E-BULK-006 | Cada carta usa su propia sesión de DB | Implícito en 002/003 repetidos | Sin errores de sesión compartida bajo concurrencia | AUTOMATED | PENDING |
| E2E-BULK-007 | Sin duplicar requests por carta | — **hueco, no existe hoy** | Exactamente 1 llamada a `get_price()` por carta | AUTOMATED | PENDING |
| E2E-BULK-008 | `update-all` real con 2-3 cartas reales | — | Resultado plausible, cuota de OpenAI multiplicada por carta | MANUAL | PENDING |

---

## 12. Stats

Base: `services/stats_service.py`. Verificar contra SQLite directamente, no solo HTTP 200.

| ID | Escenario | Resultado esperado | Tipo | Estado |
|---|---|---|---|---|
| E2E-STATS-001 | Colección vacía | Todo en 0, `most_valuable_card=null` | AUTOMATED | PENDING |
| E2E-STATS-002 | `distinct_card_count` vs `total_card_count` con `quantity>1` | `total_card_count = Σquantity` | AUTOMATED | PENDING |
| E2E-STATS-003 | `cards_with_valuation + cards_without_valuation = distinct_card_count` | Suma exacta | AUTOMATED | PENDING |
| E2E-STATS-004 | `total_estimated_value` (CLP) coincide con cálculo manual en SQLite | Comparar contra `SELECT` directo de últimos snapshots × quantity | AUTOMATED | PENDING |
| E2E-STATS-005 | Monedas no-CLP excluidas del total, agrupadas en `other_currency_totals` | `card_count` y `total_value` por moneda correctos | AUTOMATED | PENDING |
| E2E-STATS-006 | `top_valuable_cards` máximo 5, orden desc | Límite y orden respetados (`TOP_VALUABLE_LIMIT`) | AUTOMATED | PENDING |
| E2E-STATS-007 | `last_price_update` = máximo `checked_at` real | Coincide con `MAX(checked_at)` en SQLite | AUTOMATED | PENDING |
| E2E-STATS-008 | `price_change_percent` en stats coincide con el de `/prices` para la misma carta | Mismo valor en ambos endpoints | AUTOMATED | PENDING |

---

## 13. Frontend — Home / Collection Mode

| ID | Escenario | Resultado esperado | Tipo | Estado |
|---|---|---|---|---|
| E2E-UI-HOME-001 | StatsHeader coincide con `/api/collection/stats` | Valor hero + 4 métricas correctas | MANUAL | PENDING |
| E2E-UI-HOME-002 | Binder desktop renderiza todas las cartas | Imagen, badge `xN`, precio, variación por tile | MANUAL | PENDING |
| E2E-UI-HOME-003 | Búsqueda filtra por nombre/número/set en tiempo real | Resultado correcto, "Sin resultados" si no matchea | MANUAL | PENDING |
| E2E-UI-HOME-004 | "+ Agregar carta" navega a Scan Mode | Ruta `/cards/new` | MANUAL | PENDING |
| E2E-UI-HOME-005 | "Actualizar precios" corre `update-all` | Botón deshabilitado mientras corre, "Updated/Failed" al final, refresca stats+grid | MANUAL | PENDING |
| E2E-UI-HOME-006 | Click en carta abre Card Data | Ruta `/cards/{id}` | MANUAL | PENDING |
| E2E-UI-HOME-007 | Colección vacía | "No cards registered" + CTA, sin grid/carrusel roto | MANUAL | PENDING |
| E2E-UI-HOME-008 | Carta sin valoración se distingue visualmente | Badge dorado punteado "Sin valoración" | MANUAL | PENDING |

---

## 14. Frontend — Scan Mode

| ID | Escenario | Resultado esperado | Tipo | Estado |
|---|---|---|---|---|
| E2E-UI-SCAN-001 | Validación de formulario | "Scan" deshabilitado hasta llenar nombre+número | MANUAL | PENDING |
| E2E-UI-SCAN-002 | Selector de idioma envía el valor correcto | ES/EN/JA/ZH-TW/ZH-CN/etc. llegan correctamente a `identify()` | MANUAL | PENDING |
| E2E-UI-SCAN-003 | `single_match` muestra TARGET con preview completo | Imagen, número, set, rareza, idioma, source | MANUAL | PENDING |
| E2E-UI-SCAN-004 | `multiple_matches` muestra grid MATCHES, selección actualiza TARGET | Preview cambia al elegir candidato | MANUAL | PENDING |
| E2E-UI-SCAN-005 | "Cargar más" trae siguiente página sin resetear selección | Acumulación correcta | MANUAL | PENDING |
| E2E-UI-SCAN-006 | `not_found` permite guardar manualmente | Carta creada con datos tipeados | MANUAL | PENDING |
| E2E-UI-SCAN-007 | Crear carta navega a su Card Data | Redirección a `/cards/{id}` | MANUAL | PENDING |
| E2E-UI-SCAN-008 | Error de red/proveedor muestra ErrorState, no `alert()` nativo | Mensaje dentro del theme Pokédex | MANUAL | PENDING |

---

## 15. Frontend — Card Data

| ID | Escenario | Resultado esperado | Tipo | Estado |
|---|---|---|---|---|
| E2E-UI-CARD-001 | Metadata completa renderiza | Imagen, nombre, número, set, rareza, idioma, cantidad | MANUAL | PENDING |
| E2E-UI-CARD-002 | VALUE muestra precio+variación o "Sin valoración todavía" | Según exista snapshot | MANUAL | PENDING |
| E2E-UI-CARD-003 | Badges de confidence/market scope correctos | Color y label según `confidence_label`/`market_scope` | MANUAL | PENDING |
| E2E-UI-CARD-004 | "Actualizar precio" — ciclo completo | Deshabilitado mientras corre, refresca al éxito, error inline si falla | MANUAL | PENDING |
| E2E-UI-CARD-005 | HISTORICAL DATA — gráfico y vacío | Gráfico con ≥2 snapshots, mensaje si 0 | MANUAL | PENDING |
| E2E-UI-CARD-006 | SOURCES lista observaciones con su estado | Incluida/outlier/excluida distinguibles, link si hay `source_url` | MANUAL | PENDING |
| E2E-UI-CARD-007 | "Eliminar carta" pide confirmación y borra | Navega a Home tras confirmar | MANUAL | PENDING |
| E2E-UI-CARD-008 | LED Identified/Unverified refleja `card.identified` real | Coincide con el valor de la DB | MANUAL | PENDING |

---

## 16. Mobile (375 / 390 / 430 / 768px)

| ID | Escenario | Resultado esperado | Tipo | Estado |
|---|---|---|---|---|
| E2E-MOBILE-001 | Sin overflow horizontal en ningún ancho | Home/Scan/Card Data, los 4 anchos | MANUAL | PENDING |
| E2E-MOBILE-002 | Carrusel muestra una carta grande con aspect ratio correcto | Peek visible en 390/430 | MANUAL | PENDING |
| E2E-MOBILE-003 | Swipe izquierda/derecha fluido, sin autoplay | Cambia de carta al deslizar | MANUAL | PENDING |
| E2E-MOBILE-004 | Botones ‹/› funcionan y se deshabilitan en los extremos | `loop:false` respetado | MANUAL | PENDING |
| E2E-MOBILE-005 | Indicador de posición: dots vs "N/total" | Dots si ≤12 cartas, contador si más | MANUAL | PENDING |
| E2E-MOBILE-006 | Búsqueda + carrusel: índice nunca inválido | Reposiciona sin slide en blanco al filtrar | MANUAL | PENDING |
| E2E-MOBILE-007 | Tocar la carta activa abre Card Data | Navegación correcta | MANUAL | PENDING |
| E2E-MOBILE-008 | 768px exactamente usa grid, no carrusel | Breakpoint `md` respetado | MANUAL | PENDING |
| E2E-MOBILE-009 | Scan Mode vertical, orden Nombre/Número/Idioma/Cantidad | Sin dos columnas | MANUAL | PENDING |
| E2E-MOBILE-010 | Grid de candidatos usable (≥2 por fila) | Comparación visual posible | MANUAL | PENDING |
| E2E-MOBILE-011 | "Cargar más" no rompe el layout mobile | Sin overflow al cargar más candidatos | MANUAL | PENDING |
| E2E-MOBILE-012 | Card Data una columna, imagen a todo el ancho | Sin compresión del layout desktop | MANUAL | PENDING |

---

## 17. Persistencia

| ID | Escenario | Resultado esperado | Tipo | Estado |
|---|---|---|---|---|
| E2E-PERSIST-001 | Reconectar el engine SQLAlchemy al mismo archivo preserva todo | `dispose()` + reconectar, releer cards/snapshots/observations sin pérdida | AUTOMATED | PENDING |
| E2E-PERSIST-002 | Detener y reiniciar el proceso `uvicorn` real preserva todo | Crear carta + precio, `Ctrl+C`, reiniciar, verificar en la UI | MANUAL | PENDING |
| E2E-PERSIST-003 | `init_db()` no destruye datos existentes al reiniciar | `create_all` no dropea tablas con datos | AUTOMATED | PENDING |
| E2E-PERSIST-004 | Histórico ordena bien tras un reinicio real | Card Data muestra el orden correcto de snapshots tras reiniciar | MANUAL | PENDING |

---

## 18. Errores externos (mocks/stubs, sin atacar servicios reales)

| ID | Escenario | Resultado esperado | Tipo | Estado |
|---|---|---|---|---|
| E2E-ERR-001 | Timeout/conexión caída en identificación | 502 `IDENTIFICATION_PROVIDER_ERROR` | AUTOMATED | PENDING |
| E2E-ERR-002 | pokemontcg.io devuelve 500 repetido | Reintenta `MAX_ATTEMPTS` (4) veces, luego falla | AUTOMATED | PENDING |
| E2E-ERR-003 | pokemontcg.io devuelve 4xx | Falla inmediato, sin reintentos | AUTOMATED | PENDING |
| E2E-ERR-004 | Un provider de un composite falla, otro responde | Se usa el que respondió — ya cubierto por `test_identification_composite.py::test_skips_provider_that_errors_and_uses_next` | AUTOMATED | PENDING |
| E2E-ERR-005 | Todos los providers de un composite fallan | Re-lanza el último error, no "not_found" silencioso — ya cubierto por `test_raises_when_every_provider_errors` | AUTOMATED | PENDING |
| E2E-ERR-006 | OpenAI: `APIConnectionError`/`APITimeoutError` | 502 `PRICE_PROVIDER_ERROR` | AUTOMATED | PENDING |
| E2E-ERR-007 | OpenAI devuelve `output_text` no parseable | 502 `PRICE_PROVIDER_ERROR` | AUTOMATED | PENDING |
| E2E-ERR-008 | pokemon-card.com/TCGdex caídos fallan "suave" (candidates=[]), no excepción | Diferente del fail-hard de pokemontcg.io, por diseño | AUTOMATED | PENDING |

---

## 19. Huecos de cobertura detectados

1. **No hay framework de tests automatizados en el frontend** (`frontend/package.json` no tiene script `test`, no hay Vitest/RTL instalado). Todo lo de Home/Scan Mode/Card Data/Mobile es 100% manual hoy. Si más adelante quieres cobertura automatizada ahí, es una decisión de infraestructura aparte (agregar Vitest) — no la tomo por mi cuenta.
2. **Concurrencia real de `update-all` nunca se verificó con un test** (E2E-BULK-005) — reviso que respete `PRICE_UPDATE_CONCURRENCY` con un fake que cuenta llamadas simultáneas.
3. **No hay assert de "una sola llamada por carta"** en `update-all` (E2E-BULK-007) — riesgo silencioso de duplicar gasto de OpenAI si algo llama dos veces sin querer.
4. **`_round_price` solo se prueba indirectamente** (E2E-PRICE-012) — vale la pena un test directo dado que gobierna cómo se ve cada precio en CLP vs. otras monedas.
5. **`PRICE_PROVIDER_NOT_CONFIGURED` (503) no tiene test dedicado** (E2E-PRICE-014) que yo haya encontrado.
6. El límite real de ZH-CN (TCGdex con `cardCount>0` pero `cards:[]` para ciertos sets) es una limitación de la **fuente de datos**, no de nuestro código — E2E-ID-008 solo confirma que fallamos "limpio" (`not_found`), no que lo resolvamos (no se puede).
7. Todo lo que gasta cuota real de OpenAI (E2E-PRICE-015/016, E2E-BULK-008) queda `MANUAL` a propósito — no lo ejecutaré en 7.2 sin que me digas explícitamente "corre este caso puntual", igual que hicimos en ETAPA 5.

---

## 20. Fuera de alcance de 7.1

- No se ejecutó ningún test todavía (solo inspección + comandos pequeños: `pytest --collect-only`, lectura de `.env.example`).
- No se modificó backend ni frontend.
- No se tocaron tus datos reales en `data/pokemon_collection.db`.
