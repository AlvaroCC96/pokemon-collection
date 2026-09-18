# Pokémon Collection

Pokédex personal de cartas Pokémon TCG con valoración de mercado (foco en Chile). Ver `PROJECT.md` para los requisitos originales y `ARCHITECTURE.md` para el diseño técnico completo.

Estado actual: **ETAPA 1–7.1 completadas**. Backend (ETAPAS 2–5) + identificación multidioma ES/EN/JA/ZH-TW/ZH-CN (ETAPA 5.5) + frontend con identidad Pokédex (binder desktop, carrusel mobile, Scan Mode, Card Data — ETAPA 6) + checklist formal de pruebas E2E (`E2E_CHECKLIST.md`, ETAPA 7.1, 137 escenarios, 93 automatizables). La ejecución automatizada (ETAPA 7.2) y la validación manual/visual quedan pendientes para una próxima sesión. Ver la sección **"Next Session — ETAPA 8"** al final de `ARCHITECTURE.md` para retomar el trabajo (containerización con Podman).

## Requisitos

- Python 3.12+ (probado con 3.12.0)
- Node.js 18+ (probado con Node 22)

## Instalación

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1   # Windows PowerShell
# .venv\Scripts\activate.bat  # Windows cmd.exe
# source .venv/bin/activate   # macOS/Linux
pip install -r requirements.txt
```

> Si tienes otro Python en el PATH (ej. Laragon, Anaconda), verifica que el prompt quede con el prefijo `(.venv)` tras activar. Si tienes dudas, usa siempre la ruta explícita del venv: `.venv\Scripts\python.exe -m pip install -r requirements.txt`.

Copiar variables de entorno (desde la raíz del proyecto):

```bash
cp .env.example .env
```

## Variables de entorno

Definidas en `.env` (raíz del proyecto), ver `.env.example`:

| Variable | Obligatoria | Descripción |
|---|---|---|
| `OPENAI_API_KEY` | Sí, para `update-price` | Usada por el Price Service. Nunca hardcodear. |
| `OPENAI_PRICE_MODEL` | No | Modelo para la búsqueda de precios (default `gpt-5-mini`). |
| `OPENAI_PRICE_MAX_TOOL_CALLS` | No | Máximo de búsquedas/aperturas de página por carta (default `5`). Controla costo. |
| `PRICE_UPDATE_CONCURRENCY` | No | Cartas actualizadas en paralelo en `update-all` (default `2`). |
| `POKEMON_TCG_IO_API_KEY` | No | Recomendada para evitar límites de tasa bajos de pokemontcg.io sin autenticar (ver ARCHITECTURE.md). |
| `DATABASE_URL` | No | Por defecto usa `data/pokemon_collection.db` en la raíz del proyecto. |
| `CORS_ORIGINS` | No | Orígenes permitidos para el frontend local, separados por coma. |
| `LOG_LEVEL` | No | Nivel de logging (`INFO` por defecto). |

## Ejecutar el backend

```powershell
cd backend
.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload
```

Si `uvicorn` no se reconoce o ejecuta un Python distinto al del venv (por ejemplo, otro Python en el PATH del sistema como Laragon/Anaconda), usa la ruta explícita del entorno virtual en su lugar:

```powershell
cd backend
.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Disponible en `http://localhost:8000`. Documentación interactiva (Swagger) en `http://localhost:8000/docs`.

La base SQLite (`data/pokemon_collection.db`) se crea automáticamente al iniciar si no existe.

## Ejecutar pruebas (backend)

```powershell
cd backend
.venv\Scripts\python.exe -m pytest
```

## Frontend

```powershell
cd frontend
npm install
cp .env.example .env   # o copiarlo manualmente en Windows
npm run dev
```

Disponible en `http://localhost:5173`. Necesita el backend corriendo en `http://localhost:8000` (CORS ya está configurado para `localhost:5173`).

Variable de entorno (`frontend/.env`, ver `.env.example`):

| Variable | Obligatoria | Descripción |
|---|---|---|
| `VITE_API_BASE_URL` | No | URL del backend (default `http://localhost:8000`). |

Build de producción y lint:

```powershell
cd frontend
npm run build   # tsc -b && vite build
npm run lint    # oxlint
```

## Arquitectura (resumen)

```
React (ETAPA 6) → FastAPI → CardService / IdentificationService / PriceService / StatsService → SQLite
                                     │                    │
                          IdentificationProvider     PriceProvider
                          (pokemontcg.io, ETAPA 3)   (OpenAI Web Search, ETAPA 4)

StatsService y el histórico (ETAPA 5) leen directamente de SQLite -- nunca invocan un provider.
```

Detalle completo, modelo de datos y decisiones de diseño en `ARCHITECTURE.md`.

## Endpoints principales (implementados hasta ETAPA 5)

```
GET    /api/health

GET    /api/cards
GET    /api/cards/{id}
POST   /api/cards
PUT    /api/cards/{id}
DELETE /api/cards/{id}

POST   /api/cards/identify           # identificar antes de guardar (no persiste nada)
POST   /api/cards/{id}/identify      # re-identificar una carta ya guardada (no persiste nada)

POST   /api/cards/{id}/update-price  # busca precio real vía OpenAI Web Search y guarda snapshot + observations
GET    /api/cards/{id}/prices        # histórico de snapshots + observations (solo SQLite, sin OpenAI)
POST   /api/prices/update-all        # actualiza precio de TODAS las cartas, concurrencia limitada

GET    /api/collection/stats         # estadísticas de la colección (solo SQLite, sin OpenAI)
```

Los endpoints de `identify` **solo devuelven candidatos**; no modifican la base de datos. Para guardar el resultado elegido se reutiliza `POST /api/cards` (carta nueva) o `PUT /api/cards/{id}` (carta existente).

`update-price` y `update-all` SÍ persisten: crean `CardPriceSnapshot` (el resultado) y sus `PriceObservation` asociadas (toda la evidencia encontrada, incluida la descartada). Requieren `OPENAI_API_KEY` configurada — si falta, responden `503 PRICE_PROVIDER_NOT_CONFIGURED`. **Ambos consumen cuota real de OpenAI** — `update-all` la multiplica por cada carta de tu colección.

`GET /api/cards/{id}/prices` y `GET /api/collection/stats` son de solo lectura sobre SQLite — nunca llaman a OpenAI, sin importar cuántas veces los consultes.

Pendientes (etapas siguientes): containerización, homelab, job.

## Estructura del proyecto

```
pokemon-collection/
├── backend/
│   ├── app/
│   │   ├── api/            # routers (health, cards, prices, collection)
│   │   ├── core/           # config, db, logging
│   │   ├── models/         # SQLAlchemy
│   │   ├── schemas/        # Pydantic
│   │   ├── services/       # lógica de negocio
│   │   ├── providers/
│   │   │   ├── identification/  # PokemonTCGIOProvider (ETAPA 3)
│   │   │   └── price/           # OpenAIWebSearchProvider (ETAPA 4)
│   │   └── main.py
│   ├── tests/
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── api/             # cliente HTTP centralizado + tipos (VITE_API_BASE_URL)
│   │   ├── components/      # UI reutilizable: Pokedex.tsx (shell/header/screen/LED/labels
│   │   │                    # centralizados), CardTile, CardCarousel (mobile, Embla),
│   │   │                    # IdentificationPanel (Scan Mode), PriceChart, badges, estados
│   │   ├── hooks/           # useAsync, useCardsWithPrices, useMediaQuery
│   │   ├── pages/           # HomePage (Collection Mode), CardDetailPage (Card Data),
│   │   │                    # AddCardPage (Scan Mode)
│   │   └── utils/           # formato CLP/porcentaje/fecha
│   ├── .env / .env.example
│   └── package.json         # incluye embla-carousel-react (carrusel mobile, ver ARCHITECTURE.md ETAPA 6)
├── data/
│   └── pokemon_collection.db
├── .env / .env.example
├── .gitignore
├── PROJECT.md
├── ARCHITECTURE.md
├── E2E_CHECKLIST.md        # ETAPA 7.1: batería de pruebas E2E (preparada, ejecución pendiente)
└── README.md
```
