Quiero que me ayudes a construir paso a paso una aplicación web personal llamada **Pokémon Collection**, que funcionará como una Pokédex de mis cartas Pokémon TCG y calculará automáticamente un valor estimado de mercado de mi colección.

IMPORTANTE: quiero desarrollar este proyecto POR ETAPAS. No generes toda la aplicación de una sola vez.

Primero quiero diseñar correctamente la arquitectura y posteriormente iremos implementando y probando cada etapa.

# 1. OBJETIVO

Quiero una aplicación web donde pueda registrar las cartas Pokémon TCG que poseo y visualizar mi colección de forma similar a una Pokédex.

Además, quiero conocer aproximadamente cuánto vale cada carta y el valor total de mi colección utilizando precios actuales encontrados en Internet.

La aplicación estará orientada principalmente al mercado chileno y los precios deberán mostrarse principalmente en CLP.

La experiencia de agregar cartas debe ser sencilla.

NO quiero tener que conocer necesariamente el set de cada carta ni preocuparme por clasificar manualmente su condición.

# 2. DESARROLLO LOCAL PRIMERO

IMPORTANTE:

Antes de desplegar absolutamente nada en Fedora Server, Podman o mi homelab, quiero desarrollar y probar toda la aplicación LOCALMENTE en mi computador.

El flujo general será:

```text
FASE 1
Desarrollo local
    ↓
FastAPI local
React local
SQLite local
OpenAI API + Web Search real
    ↓
Pruebas completas

FASE 2
Containerización local
    ↓
Probar contenedores

FASE 3
Despliegue en Homelab
    ↓
Fedora Server
/srv/apps/pokemon-collection

FASE 4
Automatización
    ↓
Job independiente
/srv/jobs/pokemon-price-worker
```

Durante las primeras etapas NO quiero depender de:

* Fedora Server
* Podman
* systemd
* `/srv/apps`
* `/srv/jobs`
* infraestructura del homelab

Todo debe funcionar primero localmente.

# 3. STACK

Backend:

* Python
* FastAPI
* Pydantic
* SQLAlchemy
* SQLite inicialmente

Frontend:

* React
* TypeScript
* Tailwind CSS

Posteriormente:

* Podman rootless
* Fedora Server
* PostgreSQL opcional

Quiero comenzar con SQLite porque es una aplicación personal.

Sin embargo, la arquitectura debe permitir migrar posteriormente a PostgreSQL sin tener que reescribir la aplicación.

# 4. ESTRUCTURA LOCAL

Inicialmente quiero algo aproximadamente así:

```text
pokemon-collection/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   ├── providers/
│   │   └── main.py
│   │
│   ├── requirements.txt
│   └── ...
│
├── frontend/
│
├── data/
│   └── pokemon_collection.db
│
├── .env.example
├── .gitignore
└── README.md
```

Puedes modificar esta estructura si propones una alternativa técnicamente mejor, pero evita sobrearquitectura.

NO quiero crear todavía un directorio `jobs/` dentro de esta aplicación.

Los jobs del homelab vivirán posteriormente en `/srv/jobs`.

# 5. EJECUCIÓN LOCAL

El backend debe poder ejecutarse aproximadamente así:

```bash
cd backend

python -m venv .venv

# activar virtualenv

pip install -r requirements.txt

uvicorn app.main:app --reload
```

Por ejemplo:

```text
http://localhost:8000
```

El frontend:

```bash
cd frontend

npm install
npm run dev
```

Por ejemplo:

```text
http://localhost:5173
```

El frontend debe comunicarse con FastAPI localmente.

Configura correctamente CORS para desarrollo.

# 6. VARIABLES DE ENTORNO

La API key de OpenAI debe cargarse exclusivamente desde:

```text
OPENAI_API_KEY
```

mediante `.env`.

Nunca debe estar hardcodeada.

`.env` debe estar incluido en `.gitignore`.

Crear:

```text
.env.example
```

sin credenciales reales.

Por ejemplo:

```text
OPENAI_API_KEY=
DATABASE_URL=sqlite:///../data/pokemon_collection.db
```

Ajusta las rutas si la estructura definitiva lo requiere.

# 7. REGISTRO DE CARTAS

Quiero que agregar una carta sea sencillo.

Idealmente debería bastar con:

* nombre
* número de coleccionista
* cantidad

Ejemplo:

```json
{
  "name": "Charizard ex",
  "collector_number": "199/165",
  "quantity": 1
}
```

Los siguientes campos deben ser OPCIONALES:

* set
* idioma
* rareza
* imagen
* condición

No quiero que `set` sea obligatorio porque muchas veces no sé a qué set pertenece la carta.

Tampoco quiero preocuparme por la condición para el MVP.

Mis cartas están generalmente bien cuidadas, por lo que para valoración podemos utilizar como referencia una carta en buen estado cuando sea necesario.

No quiero que la UI me obligue a seleccionar NM, LP, MP, etc.

# 8. MODELO DE CARTA

Quiero almacenar aproximadamente:

```text
id
name
collector_number
set_name nullable
language nullable
rarity nullable
image_url nullable
quantity
created_at
updated_at
```

Puedes agregar campos internos si son necesarios.

# 9. IDENTIFICACIÓN AUTOMÁTICA

El sistema debe intentar identificar automáticamente una carta utilizando principalmente:

```text
nombre + número de coleccionista
```

Por ejemplo:

```text
Charizard ex
199/165
```

Si posteriormente logramos determinar:

```text
Set: Pokémon 151
Rareza: Special Illustration Rare
Imagen: ...
```

quiero almacenar esos datos automáticamente.

El set ingresado por el usuario NO debe ser obligatorio.

# 10. COINCIDENCIAS MÚLTIPLES

MUY IMPORTANTE:

Si:

```text
nombre + número
```

produce múltiples cartas posibles, NO debes elegir una arbitrariamente.

El backend debe poder devolver candidatos.

Por ejemplo:

```json
{
  "status": "multiple_matches",
  "candidates": [
    {
      "name": "...",
      "collector_number": "...",
      "set": "...",
      "image_url": "..."
    }
  ]
}
```

Posteriormente el frontend mostrará las imágenes y yo seleccionaré visualmente cuál corresponde.

Quiero evitar que una identificación incorrecta termine asociando precios de otra edición.

# 11. FUTURO: IDENTIFICACIÓN POR FOTO

NO es necesario implementarlo en el MVP.

Pero quiero dejar abierta la posibilidad futura de:

```text
📷 Sacar foto
      ↓
reconocer carta
      ↓
mostrar candidatos
      ↓
usuario confirma
```

No implementes todavía reconocimiento visual salvo que yo lo solicite posteriormente.

# 12. PRECIOS

Quiero crear un sistema llamado conceptualmente:

```text
Price Service
```

que pueda obtener referencias actuales del valor de una carta.

NO quiero depender obligatoriamente de APIs especializadas pagadas de Pokémon TCG.

La idea inicial será utilizar:

**OpenAI Responses API + Web Search**

para investigar precios actuales disponibles públicamente en Internet.

# 13. IMPORTANTE SOBRE OPENAI

OpenAI NO debe simplemente responder cuánto "cree" que vale una carta.

Debe utilizar Web Search para localizar evidencia actual.

Conceptualmente:

```text
Carta
   ↓
OpenAI Responses API
   ↓
Web Search
   ↓
Fuentes públicas actuales
   ↓
extracción estructurada
   ↓
normalización
   ↓
precio estimado
```

OpenAI debe actuar principalmente como:

* buscador
* extractor
* normalizador
* clasificador de resultados

NO como fuente original del precio.

# 14. DOCUMENTACIÓN ACTUAL DE OPENAI

Antes de implementar la integración:

Consulta la documentación OFICIAL y ACTUAL de OpenAI.

Utiliza:

* SDK oficial actual
* Responses API
* Web Search

No inventes:

* nombres de modelos
* endpoints
* parámetros
* herramientas
* métodos del SDK

Quiero que la implementación corresponda a la API vigente al momento de desarrollar el proyecto.

# 15. MERCADO CHILENO

Mi principal interés es conocer aproximadamente el valor de las cartas en Chile.

Por eso quiero priorizar fuentes chilenas.

Una fuente especialmente interesante es:

```text
TCGmatch
```

porque representa el mercado chileno de cartas TCG y trabaja con CLP.

Sin embargo:

NO quiero que la arquitectura dependa exclusivamente de TCGmatch.

Quiero poder agregar otras fuentes posteriormente.

# 16. PRICE PROVIDERS

Diseña una abstracción sencilla de proveedores.

Conceptualmente algo como:

```python
class PriceProvider:

    async def get_price(self, card):
        ...
```

Y posteriormente poder tener:

```text
OpenAIWebSearchProvider
TCGMatchProvider
OtherProvider
```

Inicialmente implementaremos:

```text
OpenAIWebSearchProvider
```

que utilizará OpenAI + Web Search.

Si posteriormente desarrollamos un scraper específico, API o integración directa para TCGmatch, debe poder agregarse sin reescribir toda la aplicación.

# 17. BÚSQUEDA DE PRECIOS

Para buscar el precio de una carta debemos utilizar todos los identificadores disponibles.

Por ejemplo:

```text
Charizard ex
199/165
Pokémon 151
Español
```

Pero recuerda:

`set` e `idioma` pueden ser NULL.

Como mínimo normalmente tendremos:

```text
nombre
número
```

El sistema debe intentar confirmar que los resultados encontrados corresponden realmente a la misma carta.

NO mezclar precios de diferentes versiones de Charizard solamente porque comparten nombre.

# 18. PRECIO OBSERVADO VS ESTIMADO

Quiero diferenciar claramente:

```text
precio observado
precio estimado
fuente
fecha de observación
confianza
```

Ejemplo:

TCGmatch podría mostrar:

```text
$132.000
```

Eso sería:

```text
precio observado
```

Nuestra aplicación podría calcular:

```text
$131.000
```

utilizando varias referencias.

Eso sería:

```text
precio estimado
```

# 19. RESULTADO DEL PRICE SERVICE

Quiero obtener un resultado estructurado aproximadamente así:

```json
{
  "card": {
    "name": "Charizard ex",
    "collector_number": "199/165",
    "set": "151",
    "language": "ES"
  },

  "valuation": {
    "currency": "CLP",
    "estimated": 131000,
    "low": 118000,
    "high": 155000,
    "confidence": 0.91
  },

  "sources": [
    {
      "name": "TCGmatch",
      "price": 132000,
      "url": "..."
    }
  ],

  "updated_at": "..."
}
```

El schema definitivo puedes mejorarlo.

# 20. FUENTES

Cada precio encontrado debe guardar su fuente cuando sea posible.

Por ejemplo:

```text
source_name
source_url
observed_price
currency
observed_at
```

Esto es MUY importante.

Quiero poder saber:

```text
¿De dónde salió este precio?
```

No quiero guardar simplemente un número sin trazabilidad.

# 21. OUTLIERS

No quiero confiar ciegamente en una publicación extremadamente cara o barata.

Si existen suficientes referencias:

* calcular mediana
* detectar valores extremos
* ignorar outliers evidentes
* calcular un rango razonable

Evita algoritmos excesivamente complejos para el MVP.

Una mediana y reglas sencillas son suficientes inicialmente.

# 22. CONFIANZA

Quiero calcular una confianza aproximada.

Por ejemplo:

```text
HIGH
MEDIUM
LOW
```

o:

```text
0.0 - 1.0
```

La confianza puede considerar:

* cantidad de fuentes
* coincidencia exacta de carta
* antigüedad del precio
* diferencias entre precios encontrados

No quiero falsa precisión.

Si solo encontramos una fuente poco clara, debe quedar indicado que la confianza es baja.

# 23. HISTÓRICO DE PRECIOS

NO quiero sobrescribir simplemente el precio anterior.

Quiero almacenar histórico.

Por ejemplo:

```text
card_price_history

id
card_id
estimated_price
low_price
high_price
currency
confidence
checked_at
```

Y si corresponde, otra tabla para observaciones:

```text
price_observations

id
card_id
source_name
source_url
observed_price
currency
observed_at
price_history_id
```

Evalúa cuál es el modelo más limpio.

# 24. ESTADÍSTICAS DE COLECCIÓN

Quiero obtener:

* cantidad de cartas diferentes
* cantidad total de cartas
* valor total estimado
* carta más valiosa
* cartas más valiosas
* precio actual por carta
* fecha de última actualización
* variación de precio
* evolución histórica

# 25. ENDPOINTS

Como mínimo quiero:

```text
GET    /api/health

GET    /api/cards
GET    /api/cards/{id}

POST   /api/cards
PUT    /api/cards/{id}
DELETE /api/cards/{id}

POST   /api/cards/{id}/identify

POST   /api/cards/{id}/update-price

GET    /api/cards/{id}/prices

POST   /api/prices/update-all

GET    /api/collection/stats
```

Puedes modificar/agregar endpoints si existe una razón técnica clara.

# 26. ACTUALIZACIÓN MANUAL PRIMERO

Durante desarrollo local NO quiero jobs automáticos.

Quiero actualizar manualmente mediante:

```text
POST /api/cards/{id}/update-price
```

Y posteriormente:

```text
POST /api/prices/update-all
```

El frontend debe eventualmente tener un botón:

```text
Actualizar precio
```

y otro:

```text
Actualizar colección
```

# 27. UPDATE-ALL

No quiero que:

```text
POST /api/prices/update-all
```

lance 500 solicitudes simultáneamente a OpenAI.

Implementa procesamiento controlado.

Por ejemplo:

* lotes
* concurrencia limitada
* manejo individual de errores
* logging
* resumen final

Si una carta falla, no debe abortar necesariamente toda la actualización.

Quiero algo conceptualmente como:

```json
{
  "total": 100,
  "updated": 94,
  "failed": 6
}
```

# 28. COSTOS DE OPENAI

Quiero evitar búsquedas innecesarias.

No debemos llamar OpenAI cuando simplemente:

```text
GET /api/cards
```

o cuando alguien abre una carta.

La interfaz debe utilizar el último precio almacenado.

OpenAI solamente debe ejecutarse cuando explícitamente actualizamos precios.

Posteriormente podremos agregar reglas como:

```text
no actualizar si fue consultada hace menos de X horas
```

pero no es obligatorio para el primer MVP.

# 29. FRONTEND

Quiero una interfaz moderna, limpia y responsive.

Debe funcionar bien tanto desde:

* computador
* iPhone

Quiero una estética inspirada ligeramente en una Pokédex/colección Pokémon, pero sin sobrecargar la interfaz.

# 30. HOME

Algo conceptualmente similar a:

```text
Pokémon Collection

Mi colección
127 cartas

Valor estimado
$1.842.500 CLP

Última actualización
13/09/2026 18:00

[ Buscar carta... ]

[ + Agregar carta ]
[ Actualizar colección ]

--------------------------------

Charizard ex
199/165

[imagen]

$131.000 CLP
x1

↑ 5.2%

--------------------------------

Pikachu
...

--------------------------------
```

No copies necesariamente este diseño literalmente.

Úsalo como referencia funcional.

# 31. DETALLE DE CARTA

Al abrir una carta quiero aproximadamente:

```text
Charizard ex
199/165

Pokémon 151

[imagen grande]

Valor mercado

$131.000 CLP

Rango
$118.000 - $155.000

Cantidad
1

Última actualización
13/09/2026

[ Actualizar precio ]

Histórico

$150k ┤
$140k ┤          ╭──
$130k ┤─────╭────╯
$120k ┤─────╯
      └────────────
```

También quiero poder consultar las fuentes utilizadas.

# 32. AGREGAR CARTA

Quiero algo sencillo:

```text
Agregar carta

Nombre
[ Charizard ex ]

Número
[ 199/165 ]

Cantidad
[ 1 ]

Idioma (opcional)
[ Español ]

Set (opcional)
[ ]

[ Buscar / Identificar ]
```

Después:

```text
Encontramos:

Charizard ex
199/165
Pokémon 151

[imagen]

¿Es esta?

[ Sí ] [ Ver otras ]
```

Si no existe identificación automática todavía, igualmente quiero poder guardar la carta manualmente.

# 33. SQLITE

Inicialmente utilizar SQLite local.

Quiero algo similar a:

```text
data/pokemon_collection.db
```

La base debe crearse automáticamente en desarrollo si no existe.

Si utilizas migraciones con Alembic, explícame por qué y mantenlas sencillas.

No quiero infraestructura innecesaria para el MVP.

# 34. LOGGING

Agregar logging útil.

Quiero poder ver cosas como:

```text
Searching price for Charizard ex 199/165

OpenAI search completed

3 observations found

Estimated price: 131000 CLP

Price history saved
```

Pero:

* nunca imprimir API keys
* nunca imprimir secretos

# 35. MANEJO DE ERRORES

Quiero respuestas API consistentes.

Por ejemplo:

```json
{
  "error": "PRICE_SEARCH_FAILED",
  "message": "Could not find reliable price information."
}
```

Evita devolver stack traces internos al frontend.

# 36. PRUEBAS LOCALES

Antes de pensar en el homelab quiero probar manualmente:

1. Levantar FastAPI.
2. Verificar `/api/health`.
3. Crear una carta.
4. Listar cartas.
5. Obtener una carta.
6. Editarla.
7. Eliminarla.
8. Identificar una carta usando nombre + número.
9. Ejecutar una búsqueda real de precio.
10. Ver las fuentes encontradas.
11. Guardar el precio.
12. Consultar histórico.
13. Levantar React.
14. Agregar una carta desde React.
15. Actualizar precio desde React.
16. Ver el valor en CLP.
17. Ver estadísticas de colección.

Cada etapa debe ser comprobable antes de continuar.

# 37. CONTAINERIZACIÓN

NO quiero comenzar por aquí.

Solamente cuando la aplicación funcione correctamente localmente quiero containerizarla.

En ese momento quiero preparar:

```text
Containerfile
compose.yml
```

compatibles con Podman.

Primero probarlos localmente.

# 38. HOMELAB

Cuando todo funcione, desplegaremos la aplicación en mi Fedora Server.

La aplicación irá conceptualmente en:

```text
/srv/apps/pokemon-collection
```

NO quiero que el código dependa de esta ruta.

Debe ser configurable.

# 39. JOBS DEL HOMELAB

IMPORTANTE:

Mi homelab tiene una estructura separada para jobs.

Los jobs NO deben vivir dentro de:

```text
/srv/apps/pokemon-collection/jobs
```

Posteriormente tendremos algo como:

```text
/srv/jobs/
├── pokemon-price-worker/
├── otros-jobs/
└── ...
```

El job de Pokémon será:

```text
/srv/jobs/pokemon-price-worker
```

Pero NO quiero implementarlo durante el desarrollo inicial.

# 40. RESPONSABILIDAD DEL JOB

MUY IMPORTANTE:

El job NO debe duplicar la lógica de búsqueda de precios.

La lógica debe permanecer dentro de:

```text
pokemon-collection backend
```

El job debe ser extremadamente sencillo.

Conceptualmente:

```text
pokemon-price-worker
        ↓
POST
/api/prices/update-all
        ↓
Pokémon Collection API
        ↓
OpenAI Web Search
        ↓
guardar precios
```

Así evitamos tener lógica duplicada.

# 41. AUTOMATIZACIÓN FUTURA

Posteriormente podremos ejecutar:

```text
pokemon-price-worker
```

por ejemplo:

```text
cada noche
```

utilizando systemd timer u otro mecanismo apropiado en Fedora.

NO implementes esto todavía.

# 42. MONITOREO FUTURO

Mi homelab tiene además un dashboard propio.

En el futuro quiero poder mostrar algo similar a:

```text
JOBS

Pokémon Prices          OK
Último run: 03:00
Duración: 42s
Actualizadas: 87
Errores: 2
Próximo run: mañana 03:00
```

Por eso sería bueno que el futuro worker pueda producir información estructurada sobre su ejecución.

Pero esto NO pertenece al MVP inicial.

# 43. SEGURIDAD

Aunque inicialmente será una aplicación personal/local:

* API keys mediante variables de entorno
* `.env` ignorado por Git
* validación de inputs
* no ejecutar contenido obtenido desde Internet
* timeouts en llamadas externas
* manejo de errores
* no exponer secretos mediante endpoints
* sanitizar/validar URLs cuando corresponda

No necesito implementar autenticación de usuarios en el primer MVP.

# 44. README

Quiero mantener un README actualizado con:

* requisitos
* instalación
* variables de entorno
* cómo iniciar backend
* cómo iniciar frontend
* cómo ejecutar pruebas
* arquitectura
* endpoints principales

Cuando lleguemos a Podman/homelab, actualizarlo con esa información.

# 45. FORMA DE TRABAJAR

Quiero que trabajemos POR ETAPAS.

No quiero que en tu primera respuesta generes:

* backend completo
* frontend completo
* containers
* jobs

todo de golpe.

Quiero este orden:

### ETAPA 1 — Diseño

Primero entrégame:

1. Arquitectura propuesta.
2. Modelo de datos.
3. Relaciones entre tablas.
4. Estructura de carpetas.
5. Flujo para agregar una carta.
6. Flujo para identificar una carta.
7. Flujo para actualizar precio.
8. Diseño del `PriceProvider`.
9. Cómo utilizaremos OpenAI Web Search.
10. Endpoints definitivos.
11. Plan completo de implementación por etapas.

NO escribas todavía toda la aplicación.

Quiero revisar contigo esta arquitectura primero.

### ETAPA 2 — Backend base

Después de mi aprobación:

* proyecto FastAPI
* configuración
* SQLite
* modelos
* schemas
* CRUD
* health
* pruebas

### ETAPA 3 — Identificación

Implementar:

```text
nombre + número
      ↓
identificación
      ↓
candidatos
```

### ETAPA 4 — Price Service

Implementar:

```text
OpenAIWebSearchProvider
```

y probarlo con unas pocas cartas reales.

### ETAPA 5 — Histórico y estadísticas

Implementar:

* histórico
* observaciones
* estadísticas
* valoración total

### ETAPA 6 — Frontend

Construir React.

### ETAPA 7 — Pruebas completas locales

Validar todo el flujo.

### ETAPA 8 — Containerización

Podman.

### ETAPA 9 — Homelab

Desplegar en:

```text
/srv/apps/pokemon-collection
```

### ETAPA 10 — Job

Crear:

```text
/srv/jobs/pokemon-price-worker
```

que consuma:

```text
POST /api/prices/update-all
```

# 46. PRINCIPIOS DEL PROYECTO

Durante todo el desarrollo:

* simplicidad primero
* evitar sobrearquitectura
* archivos completos cuando corresponda
* indicar siempre ruta del archivo
* comandos exactos para ejecutar
* comandos exactos para probar
* type hints
* logging
* manejo de errores
* secretos en variables de entorno
* no asumir dependencias instaladas
* explicar decisiones importantes
* no avanzar varias etapas sin que yo confirme
* si encuentras un problema en mi planteamiento, indícalo antes de implementarlo

# 47. OBJETIVO FINAL

Quiero terminar teniendo:

```text
             Pokémon Collection
                     │
          ┌──────────┴──────────┐
          │                     │
       React                 FastAPI
                                 │
                   ┌─────────────┼──────────────┐
                   │             │              │
                 SQLite      PriceService   StatsService
                                  │
                          PriceProvider
                                  │
                     OpenAI Web Search
                                  │
                   fuentes públicas actuales
                                  │
                       mercado chileno
```

Y posteriormente en mi homelab:

```text
/srv/apps/
└── pokemon-collection
          ↑
          │ HTTP
          │
/srv/jobs/
└── pokemon-price-worker
```

El resultado debe ser una aplicación personal estilo Pokédex donde pueda registrar fácilmente mis cartas Pokémon TCG, aunque no conozca el set, visualizar mi colección y conocer aproximadamente su valor actual en el mercado chileno.

## COMIENZA AHORA ÚNICAMENTE CON LA ETAPA 1

No generes todavía el backend ni el frontend.

Quiero que primero diseñemos y revisemos la arquitectura completa.
