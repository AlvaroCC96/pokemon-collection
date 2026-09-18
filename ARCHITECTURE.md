# Pokémon Collection — Arquitectura

Estado: **ETAPA 1–7.1 completadas y aprobadas**. Ver `PROJECT.md` para los requisitos originales; este documento es el diseño técnico derivado de ellos y se actualiza a medida que tomamos decisiones. Ver sección 14 (frontend Pokédex, ETAPA 6), sección 15 (checklist E2E, ETAPA 7.1) y la sección final **"Next Session — ETAPA 8"** para el estado más reciente y cómo retomar.

---

## 1. Arquitectura propuesta

```
                 Pokémon Collection
                         │
              ┌──────────┴──────────┐
              │                     │
           React (Vite)          FastAPI
                                     │
                ┌────────────────────┼─────────────────────┐
                │                    │                      │
             SQLite            CardService /           StatsService
         (SQLAlchemy)          IdentificationService        │
                │                    │                agrega snapshots
                │                    │                de card_price_snapshots
                │              IdentificationProvider
                │              (pokemontcg.io)
                │
          PriceService
                │
          PriceProvider (interfaz)
                │
        OpenAIWebSearchProvider
                │
       OpenAI Responses API + web_search
                │
        fuentes públicas (TCGmatch, etc.)
                │
           mercado chileno
```

Puntos clave:
- **CardService**: CRUD de cartas.
- **IdentificationService**: resuelve `nombre + número (+ set/idioma)` → candidatos, usando un provider de metadata (no de precios).
- **PriceService**: orquesta `PriceProvider`(s), normaliza observaciones, calcula estimado/rango/confianza, persiste histórico.
- **StatsService**: lee snapshots + cards para construir estadísticas de colección.
- Todo detrás de FastAPI; React consume solo HTTP/JSON.

### Decisión aprobada: `IdentificationProvider` separado de `PriceProvider`

OpenAI Web Search se reserva **exclusivamente** para precios (punto 13). La identificación de set/rareza/imagen usa un catálogo determinístico y gratuito, completamente desacoplado:

```text
IdentificationService
        │
        ▼
IdentificationProvider (interfaz)
        │
        ▼
routing por idioma (ver sección 13 — ETAPA 5.5)
        │
        ├── ES/EN/null → PokemonTCGIOProvider
        ├── JA         → oficial pokemon-card.com + TCGdex (fallback)
        ├── ZH-TW      → TCGdex zh-tw
        └── ZH-CN      → TCGdex zh-cn
```

`IdentificationService` y el resto de la app **nunca** conocen los providers concretos directamente, solo la interfaz `IdentificationProvider`. Agregar/quitar una fuente de catálogo significa tocar solo `get_identification_providers()`.

> **Nota histórica**: esta subsección describía el diseño original (un solo `TCGdexProvider` como fallback genérico detrás de `pokemontcg.io`, sin distinguir ZH-TW/ZH-CN ni usar una fuente oficial para Japón). Fue **reemplazado** en ETAPA 5.5 por el routing explícito por idioma descrito en la sección 13 — ver ahí el diseño vigente, la investigación de fuentes oficiales, y las limitaciones documentadas. El mecanismo de traducción vía PokeAPI y el hallazgo sobre `zh-cn` con datos vacíos en TCGdex se mantienen vigentes, solo cambió cómo se organizan los providers.

Sobre `pokemontcg.io` (a confirmar en detalle en ETAPA 3, antes de codificar el provider):
- Es una API pública y gratuita para consultas por nombre/set/número.
- Permite operar sin API key para volumen bajo, pero recomienda una key gratuita para límites de tasa más generosos — la cargaremos como variable de entorno opcional (`POKEMON_TCG_IO_API_KEY`), nunca hardcodeada.
- Si al implementar ETAPA 3 encontramos alguna limitación relevante (rate limit muy bajo, cobertura incompleta de sets recientes, etc.), lo señalo antes de avanzar y evaluamos TCGdex como alternativa.

---

## 2. Modelo de datos

### `cards`
| campo | tipo | notas |
|---|---|---|
| id | int PK | |
| name | str | requerido |
| collector_number | str | requerido, tal como lo ingresa el usuario (ej. `199/165`) |
| set_name | str, nullable | |
| language | str, nullable | |
| rarity | str, nullable | |
| image_url | str, nullable | |
| quantity | int | default 1 |
| external_card_id | str, nullable | id del provider de identificación (pokemontcg.io), para re-consultar sin re-identificar |
| identified | bool | default false — si el usuario confirmó un candidato o quedó manual |
| created_at | datetime | |
| updated_at | datetime | |

### `card_price_snapshots` (histórico de valoraciones, uno por corrida de `update-price`)
| campo | tipo | notas |
|---|---|---|
| id | int PK | |
| card_id | FK → cards.id | |
| estimated_price | numeric | mediana de observaciones válidas |
| low_price | numeric, nullable | |
| high_price | numeric, nullable | |
| currency | str | default `CLP` |
| market_scope | `CHILE` / `INTERNATIONAL` | **Implementado en ETAPA 4 sin `MIXED`** (ver nota de simplificación abajo) — de qué mercado provienen las observaciones usadas en el cálculo |
| confidence_score | float 0–1 | |
| confidence_label | enum HIGH/MEDIUM/LOW | derivado de confidence_score |
| source_count | int | observaciones efectivamente usadas en la mediana (mismo mercado + mismo idioma (si la carta lo define) + mismo moneda dominante + no-outlier) |
| provider | str | ej. `openai_web_search` |
| checked_at | datetime | |

### `price_observations` (una fila por fuente encontrada, siempre se guardan todas — incluidas las descartadas)
| campo | tipo | notas |
|---|---|---|
| id | int PK | |
| card_price_snapshot_id | FK → card_price_snapshots.id | |
| card_id | FK → cards.id | denormalizado, útil para consultar sin join |
| source_name | str | |
| source_url | str, nullable | |
| observed_price | numeric | |
| currency | str | |
| market_region | enum `CHILE` / `INTERNATIONAL` | de qué mercado es la fuente (ej. TCGmatch → CHILE; TCGPlayer/Cardmarket → INTERNATIONAL) |
| language | str, nullable | **campo agregado en ETAPA 4** — idioma/variante detectada en la fuente por el provider (ej. "ES", "EN"), cuando es identificable. `null` si no se pudo determinar. |
| observed_at | datetime, nullable | fecha que reporta la fuente, si está disponible |
| is_outlier | bool | default false — true solo si, dentro del grupo mercado+idioma+moneda usado, resultó estadísticamente extremo |
| included_in_estimate | bool | **campo agregado en ETAPA 4** (no estaba en el diseño original) — true solo para las observaciones que efectivamente entraron en la mediana/low/high del snapshot |
| created_at | datetime | |

**Por qué se agregó `included_in_estimate`**: en pruebas reales encontramos que el fallback internacional puede traer observaciones en **monedas distintas simultáneamente** (ej. USD y EUR en la misma corrida). Mezclarlas en una sola mediana repetiría el problema que ya evitamos entre CLP/USD. `PriceService` ahora agrupa además por moneda dominante dentro del mercado elegido, y usa solo ese subgrupo para el cálculo. `is_outlier` sigue significando "outlier de precio dentro del grupo usado"; `included_in_estimate` distingue con claridad "esta fila efectivamente contribuyó al número final" de "esta fila se guardó pero no se usó" (por mercado o moneda distintos, o por ser outlier) — sin este campo, saber por qué una fila no contaba exigía cruzar mentalmente varios campos.

**Simplificación de `market_scope`**: se implementó como binario (`CHILE` o `INTERNATIONAL`, sin `MIXED`) — el documento original de ETAPA 1 dejaba abierto el diseño exacto ("no es obligatorio utilizar exactamente ese enum"). En la práctica, con la regla "si hay ≥1 observación chilena válida, úsala; si no, cae a internacional", el caso `MIXED` (ambos mercados presentes pero ninguno "suficiente" por sí solo) no tiene un umbral claro que lo distinga de un fallback simple, así que no se implementó para evitar una regla arbitraria sin justificación real. Si en el uso real surge un caso donde esto haga falta, se agrega entonces.

### Filtro por idioma (ajuste post-ETAPA 4)

`cards.language` sigue siendo opcional — el usuario nunca está obligado a indicarlo. Pero si está definido, `PriceService` lo usa como un filtro adicional entre el filtro de mercado y el de moneda:

```
observaciones
     │
  filtro mercado (CHILE si hay, si no INTERNATIONAL)
     │
  filtro idioma (solo si card.language está definido)
     │
  filtro moneda (la dominante dentro de lo que quede)
     │
  mediana / outliers / estimated
```

- Si `card.language` es `null`: no se filtra por idioma (comportamiento igual al de la primera versión de ETAPA 4) — el sistema no intenta inferir ni reconciliar variantes automáticamente, tal como se pidió ("no lógica compleja de inferencia todavía").
- Si `card.language` está definido: se conservan las observaciones cuyo `language` coincide (comparación simple, sin librería de i18n: minúsculas + primeras 2 letras, ej. "Español"≈"ES") **o** cuyo `language` es `null` (desconocido, no confirmado como otro idioma). Las observaciones con un idioma **confirmado distinto** se excluyen del cálculo — pero se siguen guardando igual, con `included_in_estimate=false`, para trazabilidad.
- Si tras filtrar por idioma no queda ninguna observación (todo lo encontrado es de otro idioma confirmado), la corrida falla con `PRICE_SEARCH_FAILED` en vez de estimar con datos del idioma equivocado.

El prompt de `OpenAIWebSearchProvider` ya no le pide al modelo "filtrar y descartar" variantes de idioma — le pide reportar **todas** las que encuentre, cada una etiquetada con su `language` si es identificable. La decisión de qué usar para el cálculo quedó enteramente en `PriceService`, no en el modelo (consistente con "OpenAI es buscador/extractor, no quien decide").

## 3. Relaciones

```
cards (1) ──< (N) card_price_snapshots (1) ──< (N) price_observations
cards (1) ──< (N) price_observations   (denormalizada, para queries directas)
```

- Borrar una carta borra en cascada sus snapshots y observaciones.
- El "precio actual" de una carta = último `card_price_snapshot` por `checked_at`.

### Sobre Alembic
Para el MVP con SQLite propongo **NO usar Alembic todavía**: `Base.metadata.create_all()` al iniciar si la tabla no existe. Es una app personal en etapa temprana y el esquema cambiará varias veces. Cuando migremos a PostgreSQL en el homelab (o si el esquema ya está estable), incorporamos Alembic para migraciones controladas. Evita infraestructura innecesaria ahora, sin bloquear el futuro.

---

## 4. Estructura de carpetas

```
pokemon-collection/
├── backend/
│   ├── app/
│   │   ├── api/                  # routers: cards.py, prices.py, collection.py, health.py
│   │   ├── core/                 # config.py (pydantic-settings), db.py, logging.py
│   │   ├── models/                # SQLAlchemy: card.py, price.py
│   │   ├── schemas/               # Pydantic: card.py, price.py, identification.py, stats.py
│   │   ├── services/              # card_service.py, identification_service.py, price_service.py, stats_service.py
│   │   ├── providers/
│   │   │   ├── price/             # base.py (PriceProvider), openai_web_search.py
│   │   │   └── identification/    # base.py (IdentificationProvider), pokemon_tcg_io.py
│   │   └── main.py
│   ├── tests/
│   └── requirements.txt
│
├── frontend/                      # ETAPA 6
│
├── data/
│   └── pokemon_collection.db      # se crea automáticamente
│
├── .env / .env.example
├── .gitignore
├── README.md
└── ARCHITECTURE.md
```

`core/` es la única adición sobre tu propuesta original (config/DB/logging centralizados); es mínima y evita duplicar setup en cada módulo.

---

## 5. Flujo: agregar carta

1. Usuario llena `name`, `collector_number` (+ opcional `quantity`, `language`, `set_name`) en el formulario, **sin guardar todavía**.
2. Frontend llama `POST /api/cards/identify` (endpoint *sin id*, ver sección de endpoints) con esos datos.
3. Backend usa `IdentificationProvider` (pokemontcg.io) para buscar por nombre+número (+set/idioma si vienen):
   - 0 resultados → `{"status": "not_found"}` → frontend permite guardar igual, manualmente.
   - 1 resultado → `{"status": "single_match", "candidate": {...}}` → UI: "¿Es esta?" [Sí] [Guardar sin identificar].
   - >1 resultado → `{"status": "multiple_matches", "candidates": [...]}` → UI muestra grid de imágenes, usuario elige una.
4. Usuario confirma un candidato (o decide omitir identificación).
5. Frontend llama `POST /api/cards` con los datos finales (incluyendo `set_name`, `rarity`, `image_url`, `external_card_id` si vino de un candidato confirmado).
6. Backend persiste la carta. **No se llama a OpenAI en ningún punto de este flujo.**

## 6. Flujo: identificar carta (re-identificación de una carta ya guardada)

Mismo mecanismo que el paso 2–4 anterior, pero vía `POST /api/cards/{id}/identify`:
- Útil si la carta se guardó manualmente sin metadata y luego se quiere completar, o si el match inicial fue incorrecto.
- Si el usuario confirma un candidato, el backend actualiza `set_name`, `rarity`, `image_url`, `language`, `external_card_id`, `identified=true` de la carta existente.

## 7. Flujo: actualizar precio

1. Usuario pulsa "Actualizar precio" → `POST /api/cards/{id}/update-price`.
2. `PriceService` arma una `PriceQuery` (name, collector_number, set_name?, language?) y llama al `PriceProvider` activo.
3. `OpenAIWebSearchProvider` llama a la Responses API con la herramienta `web_search` y le pide explícitamente:
   - confirmar que cada resultado corresponde a la misma carta (nombre + número + set si se conoce),
   - devolver, por cada fuente: `source_name`, `source_url`, `observed_price`, `currency`, `observed_at` (si está disponible),
   - usando **Structured Outputs** (`text.format` con `json_schema`) para obtener JSON parseable en vez de texto libre.
4. `PriceService` recibe las observaciones crudas (cada una ya etiquetada por el provider con `market_region`, según la fuente: TCGmatch/tiendas chilenas → `CHILE`; TCGPlayer/Cardmarket/eBay → `INTERNATIONAL`) y aplica **estrategia Chile-primero, internacional como fallback**:
   1. Filtra las observaciones con `market_region = CHILE`.
   2. ¿Hay suficientes para una mediana confiable (ej. ≥1 fuente clara, idealmente ≥2)? → calcula la valoración usando **solo** esas. `market_scope = CHILE`.
   3. Si no hay suficientes observaciones chilenas → usa las `INTERNATIONAL` como fallback. `market_scope = INTERNATIONAL`. **No se convierte moneda todavía** (queda pendiente para cuando sea necesario, ver más abajo); mientras tanto se reporta en la moneda de origen de la fuente predominante.
   4. Si hay observaciones válidas de ambos tipos pero ninguno de los dos grupos alcanza por sí solo el mínimo de fuentes, se documenta como `market_scope = MIXED` y se deja constancia explícita en el snapshot de que la valoración combina ambos mercados (nunca se calcula una mediana única mezclando monedas distintas sin conversión).
   - Dentro del grupo elegido: calcula la mediana, marca como `is_outlier` los valores fuera de un rango razonable respecto a ella (regla simple, ej. fuera de `[mediana*0.4, mediana*2.5]`), `estimated_price` = mediana de no-outliers, `low`/`high` = min/max de no-outliers.
   - calcula `confidence_score` según nº de fuentes válidas, dispersión de precios, coincidencia exacta de set/número, **y si `market_scope != CHILE` la confianza se penaliza** (una valoración internacional/mixta para "cuánto vale en Chile" es intrínsecamente menos precisa).
5. Se crea 1 `card_price_snapshot` (con su `market_scope`) + N `price_observations` (**todas** las observaciones encontradas se guardan, de ambos mercados y aunque no se hayan usado en el cálculo, incluidas las marcadas outlier, para trazabilidad completa).
6. Si no hay evidencia confiable de ningún mercado → error estructurado `PRICE_SEARCH_FAILED`, no se crea snapshot, se loggea el intento.

La UI (ETAPA 6) mostrará el `market_scope` junto al precio, por ejemplo "Mercado: Chile" vs "Mercado: Internacional (referencial)", para que nunca se confunda un precio chileno real con una estimación de respaldo.

### `update-all`
`POST /api/prices/update-all` recorre las cartas en lotes con concurrencia limitada (`asyncio.Semaphore`, ej. 3 simultáneas), procesando cada carta en su propio `try/except` para que un fallo individual no aborte el resto. Devuelve:
```json
{ "total": 100, "updated": 94, "failed": 6, "details": [ {"card_id": 12, "status": "failed", "error": "PRICE_SEARCH_FAILED"} ] }
```

---

## 8. Diseño del `PriceProvider`

```python
class PriceQuery(BaseModel):
    name: str
    collector_number: str
    set_name: str | None = None
    language: str | None = None

class PriceObservationResult(BaseModel):
    source_name: str
    source_url: str | None
    observed_price: float
    currency: str
    observed_at: datetime | None
    matched_confidence: float | None  # qué tan seguro el provider está de que es la misma carta

class PriceProviderResult(BaseModel):
    observations: list[PriceObservationResult]

class PriceProvider(Protocol):
    name: str
    async def get_price(self, query: PriceQuery) -> PriceProviderResult: ...
```

`PriceService` puede combinar resultados de más de un provider en el futuro (ej. `OpenAIWebSearchProvider` + `TCGMatchProvider` directo) sin cambiar el resto de la app — solo agregando otra implementación de `PriceProvider` y sumándola a la lista que usa el service.

`IdentificationProvider` sigue el mismo patrón (interfaz + implementación intercambiable), por consistencia.

### Condición de la carta

`condition` (NM/LP/MP/...) **no es un campo del modelo `cards` ni del formulario**. El usuario nunca la selecciona. Si un `PriceProvider` necesita asumir una condición para buscar/interpretar precios, usa internamente "buen estado / Near Mint" como referencia razonable — es un detalle de implementación del provider, no algo expuesto en la API ni en la UI.

---

## 9. Cómo usaremos OpenAI Web Search

**Verificado en ETAPA 4** contra la documentación oficial vigente en este momento (septiembre 2026), y confirmado además con llamadas reales de prueba usando la API key del proyecto:

- **SDK**: paquete `openai` para Python, **v2.52.0** (mayor vigente; la serie 1.x quedó obsoleta). `pip install openai==2.52.0`.
- **API**: Responses API — `client.responses.create(...)`, no Chat Completions.
- **Herramienta**: `tools=[{"type": "web_search"}]`.
- **Structured Outputs**: `text={"format": {"type": "json_schema", "name": "...", "schema": {...}, "strict": True}}`. **Confirmado empíricamente que `web_search` y `text.format` con `json_schema` funcionan juntos en la misma llamada** (algunas fuentes de terceros afirmaban que eran mutuamente excluyentes — eso es incorrecto para la Responses API actual, probablemente una confusión con el parámetro `response_format` legado de Chat Completions).
- **Modelo elegido**: `gpt-5-mini` (ver justificación de costo abajo), configurable vía `OPENAI_PRICE_MODEL`.
- **`max_tool_calls`**: parámetro soportado para limitar cuántas búsquedas/aperturas de página puede hacer el modelo por respuesta. Lo fijamos en un valor bajo (ver provider) para controlar costo y latencia — confirmado que el modelo respeta este límite en pruebas reales.
- **Citas inline (`annotations`/`url_citation`)**: en nuestras pruebas, al usar `text.format` con `json_schema` estricto, las anotaciones inline vinieron **vacías** — el modelo no emite prosa citada, solo el JSON. Por eso la trazabilidad de fuentes depende **enteramente** de que el propio JSON estructurado incluya `source_url` por observación (ya lo pedimos así), no de `annotations`.

### Hallazgo importante de las pruebas: el modelo puede convertir moneda por su cuenta si no se le prohíbe explícitamente

En una prueba real, al pedir precio de una carta ambigua, el modelo — sin que se lo pidiéramos — buscó el tipo de cambio USD/CLP y **convirtió una fuente internacional a CLP por su cuenta**, reportándola con un número en CLP aunque la fuente original estaba en USD. Esto rompe directamente la decisión de la sección 4 del feedback de ETAPA 1 (nunca mezclar/convertir monedas automáticamente sin que `PriceService` lo decida).

**Mitigación aplicada en el prompt**: se instruye explícitamente al modelo a reportar `observed_price` y `currency` **exactamente como aparecen en la fuente original**, sin convertir ni estimar tipos de cambio por su cuenta. `PriceService` sigue siendo el único responsable de decidir si mezcla, convierte o descarta monedas — hasta ahora, ninguna conversión automática (ver sección de mercado más abajo).

### Costo aproximado (verificado con llamadas reales)

- **Tokens** (`gpt-5-mini`): USD $0.25 / 1M input, USD $2.00 / 1M output (cache de input a $0.025/1M).
- **Web Search**: **USD $10 / 1000 llamadas de búsqueda**, más el costo normal de tokens del contenido leído.
- **Variabilidad real observada**: para una carta bien identificada (nombre+número+set exactos, ej. Charizard ex 199/165 "151"), el modelo resolvió el precio con **1-2 llamadas de búsqueda** (~USD $0.02-0.03 total). Para una carta ambigua (Pikachu "25" sin set), llegó a hacer **7 llamadas de búsqueda** antes de responder (~USD $0.08-0.09 total) — el costo dominante es la tarifa fija por llamada de búsqueda, no los tokens. Por eso limitamos `max_tool_calls` (ver provider) en vez de dejarlo abierto.
- Con `max_tool_calls` acotado, el costo por carta debería mantenerse en el rango de **USD $0.02-0.05** en la mayoría de los casos. Para una colección de ~100-200 cartas, eso es del orden de unos pocos dólares por corrida completa (relevante quando implementemos `update-all` en ETAPA 5, no ahora).

### ¿Por qué `gpt-5-mini` y no otro?

Confirmé en la documentación de modelos que tanto `gpt-5-mini` como `gpt-5-nano` soportan `web_search` y `structured_outputs`. Dado que el costo por carta está dominado por la tarifa fija de Web Search (USD $10/1000 llamadas) y no por el precio de los tokens, la diferencia de costo entre `nano` y `mini` es marginal (fracciones de centavo) — así que no tiene sentido arriesgar calidad de extracción/desambiguación por ese ahorro mínimo. `gpt-5-mini` da mejor fiabilidad para tareas de extracción/clasificación estructurada que `nano`, sin acercarse al costo de `gpt-5` completo (5x más caro) ni de `gpt-6-astra`/`gpt-5.5` (órdenes de magnitud más caros, pensados para razonamiento complejo que esta tarea no necesita). Queda configurable vía `OPENAI_PRICE_MODEL` para cambiarlo sin tocar código si más adelante conviene otro.

Diseño de la integración:
- El prompt le pide al modelo **buscar explícitamente fuentes chilenas primero** (mencionando TCGmatch) y también fuentes internacionales, **reportar cada observación con su moneda y precio originales sin convertir**, y **etiquetar cada observación con su mercado de origen** (`CHILE` / `INTERNATIONAL`) según la fuente — esa etiqueta es la que `PriceService` usa para la estrategia Chile-primero descrita en el punto 7.
- OpenAI actúa como buscador/extractor/normalizador inicial, nunca como fuente del precio. `PriceService` decide qué observaciones son válidas, calcula outliers, estimado y `market_scope`.

### Conversión de moneda: pospuesta

Por decisión explícita, **no** se mezclan automáticamente precios CLP e internacionales usando una tasa de cambio, y ahora además se le prohíbe explícitamente al modelo hacer esa conversión por su cuenta (ver hallazgo arriba). Mientras no se implemente conversión, una valoración con `market_scope = INTERNATIONAL` se reporta en la moneda predominante de esas fuentes (normalmente USD), dejando claro en la UI que es referencial y no está en CLP. Si más adelante se decide convertir automáticamente, se agrega como un servicio pequeño y explícito (tasa fija por variable de entorno o fuente en vivo) — no antes de que sea realmente necesario.

---

## 10. Endpoints definitivos

```
GET    /api/health

GET    /api/cards
GET    /api/cards/{id}
POST   /api/cards
PUT    /api/cards/{id}
DELETE /api/cards/{id}

POST   /api/cards/identify           # NUEVO: identificación sin id (antes de guardar)
POST   /api/cards/{id}/identify      # re-identificar una carta ya guardada

POST   /api/cards/{id}/update-price
GET    /api/cards/{id}/prices        # histórico de snapshots + observations

POST   /api/prices/update-all

GET    /api/collection/stats
```

Único cambio respecto a tu lista original: se agrega `POST /api/cards/identify` (sin id) porque el flujo de "Agregar carta" (punto 32) identifica **antes** de guardar, y el endpoint con id requiere que la carta ya exista. Ambos endpoints comparten el mismo `IdentificationService` internamente.

---

## 11. Plan de implementación por etapas

- ✅ **ETAPA 2 — Backend base**: proyecto FastAPI, config (`pydantic-settings`), conexión SQLite (`data/pokemon_collection.db`), modelo `cards`, schemas, CRUD completo, `/api/health`, pruebas manuales con `curl`/HTTPie.
- ✅ **ETAPA 3 — Identificación**: `IdentificationProvider` (pokemontcg.io), `POST /api/cards/identify`, `POST /api/cards/{id}/identify`, manejo de 0/1/N candidatos.
- ✅ **ETAPA 4 — Price Service**: modelos `card_price_snapshots` y `price_observations`, `OpenAIWebSearchProvider` (verificando docs/modelo vigente en ese momento), normalización (mediana/outliers/confianza), `POST /api/cards/{id}/update-price`, pruebas con 2–3 cartas reales.
- ✅ **ETAPA 5 — Histórico y estadísticas**: `GET /api/cards/{id}/prices`, `POST /api/prices/update-all` (lotes + concurrencia limitada), `GET /api/collection/stats`.
- ✅ **ETAPA 5.5 — Identificación multidioma**: JA/ZH-TW/ZH-CN (ver sección 13).
- ✅ **ETAPA 6 — Frontend**: React + TS + Tailwind, con identidad visual Pokédex (binder desktop, carrusel mobile, Scan Mode, Card Data). Ver sección 14.
- ✅ **ETAPA 7.1 — Checklist E2E**: 137 escenarios preparados en `E2E_CHECKLIST.md`, ninguno ejecutado todavía. Ver sección 15.
- ⏳ **ETAPA 7.2 — Ejecución de pruebas E2E automatizables**: pendiente (siguiente subetapa antes de containerizar).
- ⏳ **ETAPA 7.3 (implícita) — Validación manual/visual**: el usuario la ejecuta directamente.
- 🔜 **ETAPA 8 — Containerización**: Containerfile + compose.yml para Podman, probado localmente. **No iniciada** — ver sección final "Next Session — ETAPA 8".
- **ETAPA 9 — Homelab**: despliegue en `/srv/apps/pokemon-collection` (rutas configurables, no hardcodeadas).
- **ETAPA 10 — Job**: `/srv/jobs/pokemon-price-worker`, llamando `POST /api/prices/update-all` — sin duplicar lógica.

---

## 12. ETAPA 5 — Histórico y estadísticas (detalle de implementación)

### `GET /api/cards/{id}/prices`
Devuelve los snapshots de una carta en **orden cronológico ascendente** (más antiguo primero) — pensado para alimentar directamente un gráfico de línea de tiempo en React; el frontend puede filtrar a 7d/30d/90d recortando por `checked_at` sobre esta misma lista, sin necesidad de parámetros de rango en el backend por ahora. Cada snapshot incluye sus `observations` completas (toda la evidencia, incluida la descartada). Es 100% lectura sobre SQLite: no depende de `get_price_provider`, así que funciona incluso sin `OPENAI_API_KEY` configurada.

### Variación de precio (`previous_price` / `price_change` / `price_change_percent`)
Se calcula comparando cada snapshot únicamente contra el snapshot **compatible** más reciente que lo precede — compatible significa **misma `currency` Y mismo `market_scope`** (más estricto que el "preferentemente" original, para evitar cualquier ambigüedad). Si no existe un snapshot compatible anterior (primer snapshot de esa combinación moneda/mercado), los tres campos quedan en `null`. La misma lógica se reutiliza en `GET /api/collection/stats` (campo `price_change_percent` de cada carta) a través de `price_service.get_latest_snapshot_with_change()` — sin duplicar el cálculo.

**Bug real encontrado y corregido durante las pruebas**: `checked_at` usa `CURRENT_TIMESTAMP` de SQLite, que solo tiene resolución de **1 segundo**. Dos `update-price` ejecutados dentro del mismo segundo (p.ej. en tests, o dos clics rápidos) empataban en `checked_at` y el orden entre ellos quedaba indefinido, calculando variaciones de precio invertidas. Se corrigió ordenando siempre por `(checked_at, id)`, usando el `id` autoincremental como desempate determinístico.

### `POST /api/prices/update-all`
Reutiliza `price_service.update_price()` sin duplicar lógica de búsqueda/normalización. Concurrencia limitada vía `asyncio.Semaphore(PRICE_UPDATE_CONCURRENCY)` (default `2`). **Detalle importante**: cada carta se procesa con su **propia sesión SQLAlchemy** (`SessionLocal()` nueva por tarea), no la sesión de la request — una `Session` no es segura para usarse desde corrutinas concurrentes que hacen `await` intercalados; compartirla habría corrompido el estado entre tareas. El `PriceProvider` (el cliente de OpenAI) sí se comparte entre tareas, porque está diseñado para solicitudes concurrentes. Un fallo en una carta se captura individualmente (`PRICE_SEARCH_FAILED`, `PRICE_PROVIDER_ERROR` o `UNEXPECTED_ERROR`) y no aborta el resto.

### `GET /api/collection/stats`
100% lectura sobre SQLite, nunca llama a un `PriceProvider`. Usa el **último snapshot de cada carta** (por `checked_at`+`id`). Regla de monedas: `total_estimated_value` solo suma cartas cuyo último snapshot está en **CLP**; cualquier otra moneda encontrada se reporta aparte en `other_currency_totals` (agrupado por moneda, con su propio total y cantidad de cartas) y **nunca** se mezcla con el total principal. `most_valuable_card` y `top_valuable_cards` (top 5) también se calculan solo sobre el conjunto CLP, por la misma razón — no tendría sentido rankear "la carta más valiosa" mezclando CLP con USD sin convertir.

### Simplificación consciente
No se implementó paginación ni filtros de fecha en `GET /api/cards/{id}/prices` — para una colección personal con actualizaciones manuales, el volumen de snapshots por carta será bajo por mucho tiempo. Si esto cambia, se agrega entonces.

---

## 13. ETAPA 5.5 — Identificación multidioma (Japón / China)

### Investigación de fuentes oficiales (antes de implementar)

| Región | Fuente pedida | Resultado de la investigación |
|---|---|---|
| Japón | `pokemon-card.com` | ✅ Tiene una **API JSON real, no documentada pero funcional**: `GET /card-search/resultAPI.php?keyword=...`. Se confirmó leyendo el JavaScript de producción del propio sitio (`PTC.searchRequest` llama exactamente a esa URL) — no es una suposición. Devuelve `cardID`, nombre y URL de miniatura; **no** expone número de coleccionista, set ni rareza. Solo acepta nombres en japonés (`keyword=Charizard` → 0 resultados; `keyword=リザードン` → resultados reales). |
| Chino tradicional (TW/HK) | `asia.pokemon-card.com/tw` | ❌ Sin API JSON: formulario HTML tradicional, el listado de resultados ni siquiera trae el nombre en texto (solo imagen + link a página de detalle). Conseguir número/set/rareza exigiría scrapear cada página de detalle — el "scraper frágil" que se pidió explícitamente evitar. **No se implementó sobre esta fuente.** |
| Chino simplificado (CN) | `pokemon.cn` | ❌ El sitio no tiene ninguna función de búsqueda de cartas (es un sitio de noticias/producto). Además, es inalcanzable desde este entorno (timeout de conexión). Descartado por completo. |

**Estrategia adoptada** (dado lo anterior): Japón usa la fuente oficial real; China tradicional y china simplificada usan **TCGdex** (ya integrado, gratis, sin API key) en vez de la fuente oficial pedida, documentando por qué.

### Arquitectura de providers

```text
IdentificationService.identify()
        │
        ├── routing por language (normalize_language_code, app/core/language_codes.py)
        │
        ├── JA        → CompositeIdentificationProvider([PokemonCardComProvider, TCGdexLanguageProvider("ja","ja")])
        ├── ZH-TW     → TCGdexLanguageProvider("zh-tw", "zh-hant")
        ├── ZH-CN     → TCGdexLanguageProvider("zh-cn", "zh-hans")
        ├── ZH (generico) → CompositeIdentificationProvider([zh-tw, zh-cn])   -- en ese orden, ver más abajo
        └── ES/EN/null/desconocido → PokemonTCGIOProvider (comportamiento original sin cambios)
```

`TraditionalChineseIdentificationProvider` y `SimplifiedChineseIdentificationProvider` (nombres del enunciado) son la MISMA clase `TCGdexLanguageProvider`, parametrizada por idioma — implementarlas por separado habría sido ~150 líneas casi idénticas duplicadas tres veces. `JapaneseIdentificationProvider` es conceptualmente el `Composite` de [oficial, TCGdex] armado en `get_identification_providers()`.

**Routing centralizado**: toda la decisión de qué provider usar vive en `identification_service._select_provider()` — ningún router/endpoint conoce Japón/China. Esto se resolvió con un cambio de forma en la inyección de dependencias: antes `Depends(get_identification_provider)` entregaba un único provider ya resuelto; ahora `Depends(get_identification_providers)` entrega un `IdentificationProviderRegistry` (los 4 providers construidos), y el *routing* ocurre dentro de `identify()`, porque depende del `language` de la request, que no se conoce al momento de resolver la dependencia.

### Códigos de idioma (`app/core/language_codes.py`)

`cards.language` sigue siendo **texto libre y nullable** — no hubo migración de datos ni cambio de schema. Se agregó un módulo central (`normalize_language_code`) que mapea variantes de texto libre (`"Español"`, `"Ingles"` sin tilde, `"Chino"`, `"ZH-TW"`, etc.) a códigos canónicos `ES / EN / JA / ZH-TW / ZH-CN` (+ `ZH` como pseudo-código interno de routing para "chino, variante sin especificar" — nunca se devuelve como resultado final, solo se usa para decidir qué providers probar). Este módulo lo usan **tanto** la identificación (routing) **como** `price_service._language_matches` (que antes tenía su propia tabla separada, con un bug latente: colapsaba `ZH-TW`/`ZH-CN` en un genérico `"ZH"` para el matching de precios, lo cual ya no es correcto ahora que distinguimos variantes). Al consolidar, un observación de precio en `"JP"` ahora normaliza a `"JA"` (antes era `"JP"`) — cambio interno sin efecto visible, solo consistencia de nombres.

### "Chino" genérico (sin variante)

Si `language` normaliza a `ZH` genérico (el usuario escribió "Chino" sin distinguir TW/CN), el sistema **no adivina** una región: prueba `ZH-TW` primero y `ZH-CN` después, en ese orden documentado (TCGdex tiene mejor cobertura de datos en `zh-tw`, ver más abajo), usando el mismo `CompositeIdentificationProvider` que ya existía. No se agregó un nuevo status "se requiere elegir variante" para no cambiar el contrato de la API (`not_found` / `single_match` / `multiple_matches` se mantiene igual).

### `IdentificationCandidate`: cambios de schema (aditivos, no rompen nada)

- `collector_number` pasó de `str` obligatorio a `str | None`: `pokemon-card.com` genuinamente no expone número de coleccionista, y el enunciado es explícito ("los campos no disponibles deben ser `null`; no inventar metadata"). Los providers existentes (`PokemonTCGIOProvider`, TCGdex) siguen devolviendo el número siempre que lo tienen.
- Se agregó `source: str | None` (ej. `"pokemontcg.io"`, `"pokemon-card.com"`, `"tcgdex:zh-tw"`) para trazabilidad — de dónde salió cada candidato, visible en logs y en la respuesta.

### Traducción de nombres para buscar (nunca para mostrar)

Tanto `pokemon-card.com` como los catálogos no-ingleses de TCGdex guardan el nombre en el **idioma local** (`リザードン`, `噴火龍`, no "Charizard"). Buscar el nombre que el usuario escribe en español/inglés no encuentra nada. Se resuelve traduciendo el nombre de la especie vía **PokeAPI** (`pokeapi.co`, gratis, sin key, nombres oficiales en ~14 idiomas) **solo para construir la búsqueda** — el nombre que se guarda/devuelve en el `IdentificationCandidate` es siempre el que entrega el catálogo original (`リザードンGX`, nunca traducido de vuelta). Esta lógica vive en `app/providers/identification/species_translation.py`, compartida entre `PokemonCardComProvider` y `TCGdexLanguageProvider`.

### Limitaciones conocidas, documentadas explícitamente (no se intentó ocultarlas)

- **Japón**: sin número de coleccionista, set ni rareza desde la fuente oficial (solo nombre + imagen). El fallback a TCGdex `ja` (completo, verificado con datos reales) sí los provee cuando el nombre coincide. **Además**, al no poder filtrar por número, un nombre común (Pikachu, Charizard...) puede tener cientos de impresiones — solo se devuelve la primera página (~40) de resultados de `pokemon-card.com`. Verificado con un caso real: "Pikachu ex 764/742" (una carta de numeración muy alta) no apareció entre los primeros 40 resultados de "ピカチュウ" (327 en total, 9 páginas) porque el sitio no permite acotar por número y revisar la página de detalle de cada una de las 327 para filtrar manualmente sería el scraping masivo que se pidió evitar. Si la impresión exacta no aparece entre los candidatos, la única opción hoy es guardar la carta manualmente sin metadata de catálogo.
- **China tradicional**: sin fuente oficial viable; se usa TCGdex `zh-tw`, verificado con datos reales como completo.
- **China simplificada**: sin fuente oficial viable (el sitio ni siquiera tiene buscador) y además inalcanzable; se usa TCGdex `zh-cn`, cuyos datos a nivel de carta están **mayormente vacíos** en pruebas reales (el set existe con su metadata, pero sin cartas cargadas) — este provider devolverá `not_found` en la mayoría de los casos hasta que TCGdex complete esa cobertura. Es una limitación de los datos de una fuente externa, no de nuestro código; si TCGdex mejora su cobertura de `zh-cn`, funcionará automáticamente sin cambios de nuestro lado.

### Precios (sin cambios de lógica)

`price_service` no cambió su lógica de valoración. Lo único tocado fue el matching de idioma (`_language_matches`) para usar la tabla canónica compartida, de modo que una carta con `language="ZH-TW"` (nuevo código posible) se compare correctamente contra observaciones de precio en ese mismo idioma, sin colapsarla con `ZH-CN`.

---

## 14. ETAPA 6 — Frontend Pokédex (Binder desktop + Carrusel mobile + Scan Mode + Card Data)

React 19 + TypeScript + Vite + Tailwind CSS v4, consumiendo la API existente sin ningún cambio de contrato (identify/CRUD/prices/stats). Pasó por varias iteraciones puramente visuales dentro de la misma ETAPA 6 (dashboard genérico → identidad Pokédex sutil → dirección definitiva) antes de quedar aprobada.

### Metáfora y dirección visual definitiva

```
POKÉDEX = identidad de la app (shell, LEDs, paleta)
PANTALLA = contenido real (screen oscuro dentro del shell)
BINDER = colección en desktop (grid auto-fill existente, sin cambios de fondo)
CARRUSEL = colección en mobile (una carta grande a la vez, swipe)
SCAN MODE = Agregar carta (panel de búsqueda + panel TARGET + grid MATCHES)
CARD DATA = detalle de carta
PORTFOLIO = StatsHeader (valor CLP hero + métricas)
```

Explícitamente **no** es una Pokédex roja clásica ocupando toda la pantalla, ni tiene Poké Balls, personajes o animaciones constantes — la identidad viene de tokens de color + un puñado de componentes reutilizables, no de decoración.

### Theme centralizado (`frontend/src/index.css`, `@theme` de Tailwind v4)

Un solo lugar para la paleta — cambiar el rojo o el fondo a futuro es una línea, no 25 archivos:

```
pokedex-bg #0B0B0D · pokedex-surface #141416 · pokedex-surface-2 #1A1A1E
pokedex-border #2A2A30 · pokedex-red #E33535 · pokedex-red-dark #A61E2A
pokemon-yellow #FFCB05 · price-gold #E5A900 · pokedex-text #F5F5F5 · pokedex-muted #A3A3A3
```

Reemplazó por completo la paleta `slate`/`amber` (navy/SaaS genérico) de las iteraciones anteriores. El único azul deliberado en toda la app es el "lente" de `PokedexHeader` — decisión explícita del usuario ("el azul puede aparecer de forma puntual en el lente/LED característico").

**Regla de color aplicada en todo el frontend**: rojo = identidad/escaneo/interacción (focus rings, botón "Scan", LEDs de estado); amarillo/dorado = valor y dinero (precio hero, badges de valoración, CTA de "Agregar a mi colección"); emerald/rose = variación de precio y confidence (sin cambios, ya eran semánticos); sky solo en el link "Ver fuente" y en el lente.

### Componentes centralizados (`frontend/src/components/Pokedex.tsx`)

`Led`, `SectionLabel`, `ScanlineTopBar`, `ModeTag`, `PokedexShell`, `PokedexHeader`, `PokedexScreen` — las tres páginas (`HomePage`, `AddCardPage`, `CardDetailPage`) se arman con estas mismas piezas en vez de reinventar el layout. `PokedexShell` da un bisel rojo sutil alrededor de todo en desktop; en mobile es solo una franja roja de 4px arriba (explícitamente **no** un borde grueso que robe espacio de pantalla).

### Etiquetas "readout" en inglés vs. contenido real en español

Siguiendo los mocks del usuario: los labels de modo/estado son en inglés mayúsculas como texto de "dispositivo" (`COLLECTION MODE`, `SCAN MODE`, `CARD DATA`, `SEARCH DATA`, `TARGET`, `MATCHES`, `READY`, `SEARCHING`, `MATCH FOUND`, `MULTIPLE MATCHES`, `NOT FOUND`, `VALUE`, `HISTORICAL DATA`, `SOURCES`, `SYSTEM ERROR`, `NO CARDS REGISTERED`, `UPDATING MARKET DATA...`/`UPDATED: N · FAILED: N`), mientras que los campos de formulario, botones de acción real y mensajes explicativos siguen en español (Nombre, Número, Idioma, Cantidad, "Agregar a mi colección", "Actualizar precio", errores, etc.). Es una decisión deliberada, no una inconsistencia — imita cómo un dispositivo con HUD en inglés puede convivir con una app en español.

### Home = Collection Mode: grid desktop sin cambios, carrusel nuevo en mobile

El grid auto-fill de desktop (`CardGrid.tsx`, `grid-template-columns: repeat(auto-fill, minmax(...))`) no cambió de comportamiento en esta iteración. El cambio real fue en mobile (`<768px`, breakpoint `md`): se reemplazó la grilla de 2 columnas por un **carrusel horizontal** (`components/CardCarousel.tsx`).

**Librería elegida: Embla Carousel** (`embla-carousel-react`, única dependencia nueva del frontend). Razones: sin dependencias propias, core hecho específicamente para drag/swipe (no hizo falta ningún plugin), bindings y tipos TypeScript de primera clase para React, mantenimiento activo, bundle pequeño (~28KB gzip agregados). Se evaluaron Swiper (más pesado, trae mucho sin usar) y keen-slider (tamaño similar, menos tracción en React) y se descartaron.

Comportamiento del carrusel: sin autoplay, sin límite de reposicionamiento artificial — al buscar, si el conjunto de resultados cambia de verdad el índice se recalcula (clamp) para no quedar fuera de rango, pero una actualización de precios (mismo set de cartas) no resetea la posición. Indicador: puntos si hay ≤12 cartas, contador "N / total" si hay más. Navegación por teclado (flechas) y `aria-live` anunciando la carta activa. El FAB "+" mobile de una iteración anterior de ETAPA 6.1 se **eliminó**: con el carrusel ya no hay scroll largo que aleje "Agregar carta" del toolbar, así que perdió su justificación de UX original.

`useMediaQuery('(min-width: 768px)')` (`frontend/src/hooks/useMediaQuery.ts`) decide qué vista montar — deliberadamente **no** se renderizan ambas ocultando una con CSS, porque Embla mediría un contenedor de ancho 0 si arrancara oculto.

### Scan Mode (Agregar carta)

Layout de dos paneles en desktop (`lg:` en adelante; una sola columna hasta esa medida, incluyendo 768px): panel izquierdo "SEARCH DATA" (formulario, botón rojo "Scan"), panel derecho "TARGET" (`components/IdentificationPanel.tsx`) que resuelve un único componente para los 5 estados (`READY` / `SEARCHING` / `MATCH FOUND` / `MULTIPLE MATCHES` / `NOT FOUND`) sin porcentajes de progreso falsos. Debajo, sección "MATCHES" de ancho completo con la grilla de candidatos existente, "Cargar más" y el conteo real de `has_more`.

### Card Data (detalle)

Mismo layout responsive de dos columnas en desktop / una en mobile de iteraciones previas (breakpoint subido de `sm` a `lg` para que 768px siga siendo una columna). Agregado: LED real (no decorativo) que lee `card.identified` de la base de datos ("Identified"/"Unverified"), labels "VALUE"/"HISTORICAL DATA"/"SOURCES".

### Accesibilidad y performance

Focus visible con anillo rojo en tarjetas/candidatos/carrusel, `aria-label` en controles del carrusel, contraste verificado sobre los tokens oscuros nuevos, ningún estado depende solo del color. `loading="lazy"` se mantiene en todas las imágenes; no se agregó virtualización ni precarga — el lazy-loading nativo ya evita cargar cartas fuera de vista, incluso dentro del carrusel.

---

## 15. ETAPA 7.1 — Checklist E2E

Documento completo: **`E2E_CHECKLIST.md`** (raíz del proyecto). Preparado inspeccionando el código real (endpoints, modelos, schemas, services, providers, los 131 tests ya existentes en `backend/tests/`, y el cliente HTTP del frontend) — no se asumió ningún contrato.

- **137 escenarios** en 15 áreas: Health/arranque, CRUD de cartas, Identificación (ES/EN/JA/ZH-TW/ZH-CN), Regresiones de bugs ya corregidos, Paginación, Price Service, Trazabilidad, Update-all, Stats, Frontend (Home/Scan Mode/Card Data), Mobile (375/390/430/768px), Persistencia, Errores externos.
- **93 automatizables** (77 `AUTOMATED` puros con pytest + SQLite temporal aislado; 16 `AMBOS` — automatizables pero dependen de un proveedor externo real y por eso pueden fallar por causas ajenas). **44 `MANUAL`** — todo lo visual/mobile (el frontend no tiene ningún framework de test automatizado instalado hoy) más los casos que gastarían cuota real de OpenAI.
- **Regla de seguridad para 7.2, confirmada explícitamente por el usuario**: cualquier prueba automatizada que cree/modifique/elimine datos usa **exclusivamente** SQLite temporal (el patrón ya existente en `backend/tests/conftest.py`, un `tempfile.mkstemp()` por sesión de test). **Nunca** `data/pokemon_collection.db`. Para pruebas manuales contra el servidor real, la convención propuesta es prefijo `E2E-` en `collector_number` y `[E2E] ` en `name`, fácil de identificar y borrar.
- Huecos de cobertura detectados (detalle en la sección 19 de `E2E_CHECKLIST.md`): sin test de tope real de concurrencia de `update-all`, sin assert de "una sola llamada por carta", `_round_price` solo probado indirectamente, sin test dedicado para `PRICE_PROVIDER_NOT_CONFIGURED` (503), y cero cobertura automatizada de frontend (no hay Vitest/RTL instalado — decisión de infraestructura a evaluar aparte si se quiere más adelante).
- **Estado**: 7.1 aprobada por el usuario. **7.2 (ejecución) no se inició** — se llegó a inspeccionar el estilo de los tests existentes (`helpers.py`, fakes de providers) pero no se escribió ni ejecutó ningún test nuevo, y no se tocó código.

---

## Decisiones aprobadas (ETAPA 1)

1. **Identificación separada de precios**: `IdentificationProvider` (inicialmente `PokemonTCGIOProvider`) para set/rareza/imagen; OpenAI Web Search reservado exclusivamente para precios (ETAPA 4, no antes).
2. **Endpoint** `POST /api/cards/identify` (sin id) para el flujo de alta, además de `POST /api/cards/{id}/identify` para re-identificar.
3. **Sin Alembic por ahora**: `Base.metadata.create_all()` en desarrollo.
4. **Sin conversión USD→CLP automática**: estrategia Chile-primero con fallback internacional (`market_scope`), sin mezclar monedas en una misma mediana. Conversión se implementa después, solo si se vuelve necesaria.
5. **Condición de la carta**: no es un campo expuesto; decisión interna del `PriceProvider` si la necesita.
6. **Trazabilidad completa**: se guardan todas las `price_observations`, incluidas las descartadas como outlier o de mercado no usado.

ETAPA 2 (backend base) no depende de ninguna de las piezas de precios/identificación reales — solo CRUD de `cards` sobre SQLite.

---

## Next Session — ETAPA 8: Containerización con Podman

**Punto de partida real**: no existe ningún `Containerfile`, `Dockerfile` ni `compose.yml`/`compose.yaml` en el proyecto todavía (verificado). ETAPA 8 empieza desde cero.

### Objetivo de ETAPA 8 (según `PROJECT.md` secciones 37–43 y 45)

- Preparar `Containerfile` (backend y frontend) + `compose.yml`, **compatibles con Podman**, y probarlos **localmente** antes de tocar el homelab.
- NO implementar todavía el despliegue en Fedora Server ni el job — eso es ETAPA 9 y 10, respectivamente.

### Restricciones ya decididas por el usuario (no renegociables sin volver a preguntar)

1. **Target de despliegue posterior**: Fedora Server, con Podman (rootless, según `PROJECT.md`).
2. **Ruta futura de la app**: `/srv/apps/pokemon-collection`. El código **no debe depender de esta ruta hardcodeada** en ningún punto — debe seguir siendo configurable (ya lo es en gran parte vía `.env`/`pydantic-settings`; revisar que la containerización no introduzca ninguna ruta absoluta nueva).
3. **SQLite debe persistir fuera del contenedor**: `data/pokemon_collection.db` necesita un volumen/bind-mount, nunca quedar dentro de la imagen ni perderse al recrear el contenedor. `DATABASE_URL` ya es configurable (`core/config.py`) — la ruta efectiva dentro del contenedor deberá apuntar a ese volumen.
4. **Secrets exclusivamente vía variables de entorno, nunca dentro de la imagen**: `OPENAI_API_KEY`, `POKEMON_TCG_IO_API_KEY`, etc. — ya vienen de `.env`/entorno (`Settings` de `pydantic-settings`), así que el patrón ya es compatible; solo falta asegurarse de que el `Containerfile` no copie `.env` dentro de la imagen y que el `compose.yml` los inyecte vía `environment:`/`env_file:` en tiempo de ejecución.
5. **Job separado, futuro, NO en esta etapa**: `/srv/jobs/pokemon-price-worker` (ETAPA 10) llamará `POST /api/prices/update-all` sin duplicar lógica de precios — no diseñar ni mencionar en el Containerfile de ETAPA 8, solo tenerlo presente para no tomar decisiones que lo compliquen después (ej. no asumir que el backend y el futuro job comparten el mismo contenedor).

### Contexto mínimo para retomar sin releer toda la conversación

- **Stack**: backend FastAPI (Python 3.12+, `requirements.txt` en `backend/`), frontend React 19 + Vite 8 + TypeScript (Node 18+, `package.json` en `frontend/`, incluye `embla-carousel-react` desde ETAPA 6).
- **Cómo se corre hoy en local** (sin contenedores): `uvicorn app.main:app --reload` en `backend/` (puerto `8000`) + `npm run dev` en `frontend/` (puerto `5173`, Vite). CORS ya configurado para `localhost:5173`.
- **Variables de entorno** (ver `.env.example` en la raíz y `frontend/.env.example`): `OPENAI_API_KEY`, `OPENAI_PRICE_MODEL`, `OPENAI_PRICE_MAX_TOOL_CALLS`, `PRICE_UPDATE_CONCURRENCY`, `POKEMON_TCG_IO_API_KEY`, `DATABASE_URL`, `CORS_ORIGINS`, `LOG_LEVEL` (backend); `VITE_API_BASE_URL` (frontend, **es un valor de build-time de Vite**, algo a tener presente al containerizar el frontend — no se puede cambiar solo con una variable de entorno del contenedor en runtime sin un paso extra, ej. reemplazo en el entry point o servir el frontend detrás del mismo origen que el backend).
- **Frontend en producción**: hoy solo existe `npm run build` (genera estático en `frontend/dist/`) — no hay decidido todavía si el contenedor del frontend sirve ese estático con nginx/caddy, o si se sirve desde el mismo backend, o si van en el mismo `compose.yml` como dos servicios. **Esto queda abierto para decidir al iniciar ETAPA 8**, no asumir nada.
- **Base de datos**: SQLite en archivo (`data/pokemon_collection.db`, ruta calculada relativa a `backend/app/core/config.py::PROJECT_ROOT`). No hay Postgres ni ningún otro motor — no introducir uno en esta etapa.
- **Tests**: `backend/tests/` con `pytest`, 131 tests existentes (más los que se agreguen en ETAPA 7.2) usan una DB SQLite temporal vía `conftest.py` — no requieren red externa salvo los explícitamente marcados como reales en `E2E_CHECKLIST.md`. Útil para correr dentro del contenedor como smoke test antes de dar por buena la imagen.
- **Qué NO hacer al empezar ETAPA 8**: no avanzar a ETAPA 9 (homelab) ni ETAPA 10 (job) en la misma sesión sin aprobación explícita; no hardcodear `/srv/apps/pokemon-collection`; no meter secrets en el `Containerfile`/imagen; no reemplazar SQLite; no tocar la lógica de negocio (`services/`, `providers/`) salvo que containerizar revele un bug real de rutas/paths — en ese caso, explicarlo antes de tocar código, igual que en toda la conversación anterior.
- **Pendiente de decidir junto al usuario al iniciar ETAPA 8** (no asumir): número y forma de los servicios en `compose.yml` (¿backend y frontend por separado, o el backend sirve el build estático del frontend?), estrategia exacta de volumen para `data/`, y si el `VITE_API_BASE_URL` se resuelve en build-time del frontend o se inyecta en runtime.
