# Azure Function - Google Maps Route Trigger + TRMNL Integration

Función de Azure que obtiene información de rutas de Google Maps dos veces al día y envía los datos a TRMNL.

## Descripción

Esta función se ejecuta automáticamente dos veces al día para:
1. Obtener información de tráfico y rutas de Google Maps entre dos ubicaciones
2. Enviar los datos automáticamente al webhook de TRMNL

**Rutas configuradas:**
- **Ruta 1 (Directa)**: Casa → Colegio
- **Ruta 2 (Con parada)**: Casa → Hospital → Colegio

**Configuración mediante variables de entorno:**
- Coordenadas (Casa, Colegio, Hospital)
- URL del webhook de TRMNL
- Lista de festivos del año escolar
- API Key de Google Maps

Ver `.env.example` para ejemplos de configuración.

## Horarios de Ejecución

La función está configurada con un **time trigger que se ejecuta cada 15 minutos** durante las horas relevantes:

### Schedule de Ejecución
- **Frecuencia**: Cada 15 minutos
- **Días**: Lunes a Viernes + Domingos
- **Horarios (hora española)**:
  - L-V: 6:00-8:30, 13:00-14:30, 17:30-23:30
  - Domingo: 17:30-23:30
  - Sábados: No se ejecuta
- **Cron**: `0 */15 6-8,13-14,17-23 * * 0,1-5`

**Optimización de recursos**: La función hace **early exit** si se ejecuta fuera de las ventanas exactas de visualización del plugin TRMNL, ahorrando recursos y costos.

### Ventanas de Visualización (Hora Española)

El plugin TRMNL se muestra en estas franjas horarias:

**Lunes a Viernes**:
- 6:00-8:30 (Mañana)
- 13:00-14:30 (Mediodía)
- 17:30-23:30 (Tarde/Noche)

**Domingos**:
- 17:30-23:30 (Tarde/Noche)

**Sábados**: No se muestra

### Ventanas para ETAs de Google Maps

La función solo **obtiene datos de Google Maps** durante estas ventanas más restringidas:

**Ventana Mañana**: 7:30 AM - 9:00 AM
- Actualizaciones cada 15 minutos con tráfico en tiempo real
- Ejemplo: 7:30, 7:45, 8:00, 8:15, 8:30, 8:45, 9:00

**Ventana Tarde**: 1:30 PM (13:30) - 2:45 PM (14:45)
- Actualizaciones cada 15 minutos con tráfico en tiempo real
- Ejemplo: 13:30, 13:45, 14:00, 14:15, 14:30, 14:45

### Comportamiento por Ventanas

**Dentro de ventanas de ETAs** (7:30-9:00 y 13:30-14:45):
- ✅ Llama a Google Maps API para rutas actualizadas con tráfico
- ✅ Actualiza información meteorológica
- ✅ Muestra ETAs en pantalla TRMNL
- ✅ `show_routes=true`

**Dentro de ventanas de visualización pero fuera de ventanas de ETAs**:
- ⏸️ NO hace llamadas a Google Maps API (ahorro de costos)
- ✅ Actualiza información meteorológica
- ⏸️ Oculta ETAs en pantalla TRMNL
- ⏸️ `show_routes=false`

**Fuera de ventanas de visualización**:
- ⏸️ Early exit - la función termina inmediatamente
- ⏸️ No consume recursos ni hace llamadas a APIs
- ⏸️ Máximo ahorro de costos

**En días festivos**:
- ⏸️ NO hace llamadas a Google Maps API
- ✅ Actualiza información meteorológica
- ⏸️ Las rutas se ocultan automáticamente

### Gestión de Festivos

La función verifica automáticamente si el día actual es festivo antes de mostrar rutas. Los festivos se configuran como variable de entorno:

**Formato**: Lista separada por comas en formato `YYYY-MM-DD`
**Soporta rangos**: Usa `..` para períodos (ej: `2025-12-22..2026-01-07` para vacaciones)

**Ejemplo**:
```bash
FESTIVOS=2025-10-31,2025-11-03,2025-12-05,2025-12-08,2025-12-22..2026-01-07
```

**Nota**: La función ajusta automáticamente al horario de verano/invierno español usando la zona horaria `Europe/Madrid`.

## Requisitos

- Python 3.9 o superior
- Azure Functions Core Tools (para desarrollo local)
- Una cuenta de Azure
- API Key de Google Maps con acceso a Routes API

## Configuración

### 1. Configuración Local

1. Clona este repositorio
2. Instala las dependencias:
   ```bash
   pip install -r requirements.txt
   ```

3. Copia `local.settings.example.json` a `local.settings.json` y configura todas las variables:
   ```json
   {
     "IsEncrypted": false,
     "Values": {
       "AzureWebJobsStorage": "UseDevelopmentStorage=true",
       "FUNCTIONS_WORKER_RUNTIME": "python",
       "GOOGLE_MAPS_API_KEY": "tu-api-key-aqui",
       "TRMNL_WEBHOOK_URL": "https://usetrmnl.com/api/custom_plugins/tu-plugin-uuid",
       "COORDS_CASA_LAT": "40.416775",
       "COORDS_CASA_LON": "-3.703790",
       "COORDS_COLEGIO_LAT": "40.417638",
       "COORDS_COLEGIO_LON": "-3.699500",
       "COORDS_HOSPITAL_LAT": "40.420000",
       "COORDS_HOSPITAL_LON": "-3.701000",
       "FESTIVOS": "2025-10-31,2025-11-03,2025-12-22..2026-01-07"
     }
   }
   ```

4. Actualiza las coordenadas con tus ubicaciones reales (ver sección "Cómo obtener coordenadas" más abajo)

### 2. Obtener API Key de Google Maps

1. Ve a [Google Cloud Console](https://console.cloud.google.com/)
2. Crea un nuevo proyecto o selecciona uno existente
3. Habilita la API "Routes API"
4. Crea credenciales (API Key)
5. Copia la API Key y agrégala a tu configuración

### 3. Configuración en Azure

Para desplegar en Azure, configura **todas** las variables de entorno en tu Function App:

```bash
az functionapp config appsettings set \
  --name <nombre-de-tu-function-app> \
  --resource-group <nombre-de-tu-resource-group> \
  --settings \
    "GOOGLE_MAPS_API_KEY=tu-api-key" \
    "TRMNL_WEBHOOK_URL=https://usetrmnl.com/api/custom_plugins/tu-uuid" \
    "COORDS_CASA_LAT=40.416775" \
    "COORDS_CASA_LON=-3.703790" \
    "COORDS_COLEGIO_LAT=40.417638" \
    "COORDS_COLEGIO_LON=-3.699500" \
    "COORDS_HOSPITAL_LAT=40.420000" \
    "COORDS_HOSPITAL_LON=-3.701000" \
    "FESTIVOS=2025-10-31,2025-11-03,2025-12-22..2026-01-07"
```

O configúrala desde Azure Portal:
1. Ve a tu Function App
2. Configuración → Variables de entorno (Environment variables)
3. Agrega cada variable individualmente

**IMPORTANTE**: Las coordenadas en los ejemplos son de Madrid (públicas). Actualiza con tus ubicaciones reales.

## Estructura del Proyecto

```
.
├── function_app.py           # Función principal con timer trigger
├── host.json                 # Configuración del host de Azure Functions
├── requirements.txt          # Dependencias de Python
├── local.settings.json       # Configuración local (no incluida en git)
├── .gitignore               # Archivos ignorados por git
└── README.md                # Este archivo
```

## Desarrollo Local

Para ejecutar la función localmente:

```bash
# Instalar Azure Functions Core Tools si no lo tienes
# En Linux/Mac:
brew tap azure/functions
brew install azure-functions-core-tools@4

# En Windows:
# Descarga desde https://aka.ms/azfunc-install

# Ejecutar la función localmente
func start
```

## Despliegue a Azure

### Usando Azure CLI

```bash
# Login a Azure
az login

# Crear un resource group (si no existe)
az group create --name MyResourceGroup --location westeurope

# Crear una storage account
az storage account create \
  --name mystorageaccount \
  --resource-group MyResourceGroup \
  --location westeurope \
  --sku Standard_LRS

# Crear la Function App
az functionapp create \
  --resource-group MyResourceGroup \
  --consumption-plan-location westeurope \
  --runtime python \
  --runtime-version 3.9 \
  --functions-version 4 \
  --name MyGoogleMapsFunction \
  --storage-account mystorageaccount \
  --os-type Linux

# Configurar la API Key
az functionapp config appsettings set \
  --name MyGoogleMapsFunction \
  --resource-group MyResourceGroup \
  --settings "GOOGLE_MAPS_API_KEY=TU_API_KEY_AQUI"

# Desplegar
func azure functionapp publish MyGoogleMapsFunction
```

### Usando VS Code

1. Instala la extensión "Azure Functions" en VS Code
2. Haz clic en el icono de Azure en la barra lateral
3. Despliega la función usando el botón "Deploy to Function App"

## Personalización

### Cambiar Ubicaciones

Las ubicaciones se configuran mediante **variables de entorno** (no en el código):

**En local** (`local.settings.json`):
```json
{
  "Values": {
    "COORDS_CASA_LAT": "tu-latitud-casa",
    "COORDS_CASA_LON": "tu-longitud-casa",
    "COORDS_COLEGIO_LAT": "tu-latitud-colegio",
    "COORDS_COLEGIO_LON": "tu-longitud-colegio",
    "COORDS_HOSPITAL_LAT": "tu-latitud-hospital",
    "COORDS_HOSPITAL_LON": "tu-longitud-hospital"
  }
}
```

**En Azure** (Application Settings):
```bash
az functionapp config appsettings set \
  --name <tu-function-app> \
  --resource-group <tu-resource-group> \
  --settings \
    "COORDS_CASA_LAT=40.416775" \
    "COORDS_CASA_LON=-3.703790" \
    "COORDS_COLEGIO_LAT=40.417638" \
    "COORDS_COLEGIO_LON=-3.699500" \
    "COORDS_HOSPITAL_LAT=40.420000" \
    "COORDS_HOSPITAL_LON=-3.701000"
```

**Cómo obtener coordenadas:**
1. Ve a Google Maps
2. Haz clic derecho en la ubicación deseada
3. Selecciona las coordenadas para copiarlas
4. El formato será: `latitud, longitud` (ej: 40.416775, -3.703790)
5. Usa latitud en `*_LAT` y longitud en `*_LON`

### Cambiar Horarios

Modifica la expresión cron en el decorador `@app.timer_trigger` en `function_app.py`:

```python
@app.timer_trigger(schedule="0 */15 6-8,13-14,17-23 * * 0,1-5", ...)
```

**Formato cron**: `segundo minuto hora dia mes dia_semana`

**Expresión actual**:
- `0` = En el segundo 0
- `*/15` = Cada 15 minutos
- `6-8,13-14,17-23` = Horas 6-8, 13-14, 17-23 (rangos horarios)
- `*` = Todos los días del mes
- `*` = Todos los meses
- `0,1-5` = Domingo (0) y Lunes-Viernes (1-5)

**Ejemplo**: Para ejecutar solo cada 30 minutos:
```python
@app.timer_trigger(schedule="0 */30 6-8,13-14,17-23 * * 0,1-5", ...)
```

**IMPORTANTE**: También debes actualizar la función `is_in_display_window()` para que coincida con las ventanas de tiempo que configures en el cron.

### Cambiar Webhook de TRMNL

El webhook se configura mediante variable de entorno:

```bash
# En local.settings.json
"TRMNL_WEBHOOK_URL": "https://usetrmnl.com/api/custom_plugins/tu-plugin-uuid"

# En Azure
az functionapp config appsettings set \
  --name <tu-function-app> \
  --resource-group <tu-resource-group> \
  --settings "TRMNL_WEBHOOK_URL=https://usetrmnl.com/api/custom_plugins/tu-uuid"
```

### Actualizar Lista de Festivos

Actualiza la lista al inicio de cada año escolar:

```bash
# Formato: YYYY-MM-DD separados por comas
# Soporta rangos con ".."
FESTIVOS="2025-10-31,2025-11-03,2025-12-05,2025-12-08,2025-12-22..2026-01-07,2026-02-16..2026-02-18"
```

### Obtener Más Información de la Ruta

Puedes solicitar más campos en la respuesta modificando el header `X-Goog-FieldMask` en `function_app.py`:

```python
"X-Goog-FieldMask": "routes.duration,routes.distanceMeters,routes.polyline.encodedPolyline,routes.legs,routes.travelAdvisory"
```

Campos disponibles:
- `routes.duration` - Duración del viaje
- `routes.distanceMeters` - Distancia en metros
- `routes.polyline.encodedPolyline` - Polilínea codificada de la ruta
- `routes.legs` - Información detallada de cada tramo
- `routes.travelAdvisory` - Advertencias de tráfico

Ver [documentación completa](https://developers.google.com/maps/documentation/routes/reference/rest/v2/TopLevel/computeRoutes).

## Formato del Payload al Webhook

La función envía un POST request con JSON al webhook de TRMNL usando el formato `merge_variables` requerido por la plataforma:

```json
{
  "merge_variables": {
    "departure_time": "2025-11-04 08:05:00 CET",
    "timestamp": "2025-11-04T07:50:00.123456Z",
    "eta_directo": "18 min",
    "eta_con_hospital": "28 min",
    "eta_directo_seconds": "1080s",
    "eta_con_hospital_seconds": "1680s",
    "distance_directo_km": 12.5,
    "distance_hospital_km": 15.3
  }
}
```

**Variables disponibles en la template de TRMNL:**
- `{{ show_routes }}`: Boolean - true solo entre 7:30-9:00 y 13:30-14:45 (controla visibilidad)
- `{{ eta_directo }}`: Tiempo estimado Casa → Colegio (formato: "XX min") *
- `{{ eta_con_hospital }}`: Tiempo estimado Casa → Hospital → Colegio (formato: "XX min") *
- `{{ departure_time }}`: Hora de salida programada en hora española *
- `{{ timestamp }}`: Timestamp UTC de cuando se ejecutó la función
- `{{ distance_directo_km }}`: Distancia de la ruta directa en km *
- `{{ distance_hospital_km }}`: Distancia de la ruta con hospital en km *
- `{{ eta_directo_seconds }}`: Duración en formato Google Maps (ej: "1080s") *
- `{{ eta_con_hospital_seconds }}`: Duración en formato Google Maps (ej: "1680s") *

\* *Solo presentes cuando `show_routes=true`*

### Cómo usar las variables en tu template TRMNL

**IMPORTANTE**: Usa la variable `show_routes` para controlar la visibilidad:

```liquid
{% comment %} Control de visibilidad basado en hora {% endcomment %}
{% if show_routes and eta_directo %}
  {% assign mostrar_etas = true %}
  {% assign eta_directo_display = eta_directo %}
  {% assign eta_con_hospital_display = eta_con_hospital %}
{% else %}
  {% assign mostrar_etas = false %}
{% endif %}

{% comment %} Mostrar ETAs solo si show_routes=true, hay materias y no es festivo {% endcomment %}
{% if materias.size > 0 and es_festivo == false and mostrar_etas %}
  <div class="eta-container">
    <div class="eta-item">
      <div class="eta-tiempo">{{ eta_directo_display }}</div>
      <div class="eta-label">Casa → Colegio</div>
    </div>
    <div class="eta-item">
      <div class="eta-tiempo">{{ eta_con_hospital_display }}</div>
      <div class="eta-label">Casa → Hospital → Colegio</div>
    </div>
  </div>
{% endif %}
```

Ver archivo `trmnl_template_updated.liquid` para instrucciones completas de integración.

## Monitoreo

### Ver Logs en Azure

```bash
# Ver logs en tiempo real
func azure functionapp logstream MyGoogleMapsFunction
```

O desde Azure Portal:
1. Ve a tu Function App
2. Functions → google_maps_route_trigger → Monitor
3. Ver logs e invocaciones

### Application Insights

Para monitoreo avanzado, habilita Application Insights en tu Function App:
1. Azure Portal → Tu Function App
2. Settings → Application Insights
3. Turn on Application Insights

## Solución de Problemas

### Error: "GOOGLE_MAPS_API_KEY no está configurada"

Asegúrate de que la variable de entorno esté configurada correctamente en Azure.

### Error 403 o 401 de Google Maps API

- Verifica que tu API Key sea válida
- Asegúrate de que Routes API esté habilitada en tu proyecto de Google Cloud
- Verifica las restricciones de tu API Key

### La función no se ejecuta a las horas esperadas

- Recuerda que el cron schedule está en UTC
- Ajusta según horario de verano/invierno
- Verifica los logs para confirmar las horas de ejecución

## Costos

### Google Maps API
- Routes API: Consulta la [página de precios](https://developers.google.com/maps/billing-and-pricing/pricing)
- **2 rutas por ejecución** (directa + hospital)
- **Solo se ejecuta en ventanas de ETAs** (7:30-9:00 y 13:30-14:45, L-V)
- **Ventana mañana** (7:30-9:00): 6 ejecuciones × 2 rutas = 12 llamadas/día
- **Ventana tarde** (13:30-14:45): 5 ejecuciones × 2 rutas = 10 llamadas/día
- **Total**: ~22 llamadas/día × 5 días/semana = **~110 llamadas/semana** ≈ **~470 llamadas/mes**

### MeteoGalicia API
- API gratuita de la Xunta de Galicia
- **2 ubicaciones por ejecución** (casa + colegio)
- Se ejecuta en todas las ventanas de visualización
- **L-V**: 40 ejecuciones/día × 2 ubicaciones = 80 llamadas/día
- **Domingo**: 24 ejecuciones/día × 2 ubicaciones = 48 llamadas/día
- **Total**: ~590 llamadas/semana ≈ **~2540 llamadas/mes** (GRATIS)

### Azure Functions
- Plan de Consumo: Primeras 1M ejecuciones gratis cada mes
- **Ventanas de visualización optimizadas**:
  - L-V: 6:00-8:30, 13:00-14:30, 17:30-23:30 (10h/día = 40 ejecuciones/día)
  - Domingo: 17:30-23:30 (6h/día = 24 ejecuciones/día)
  - Sábados: 0 ejecuciones
- **Total**: ~224 ejecuciones/semana ≈ **~963 ejecuciones/mes**
- Muy por debajo del límite gratuito de 1M

### Optimización de Costos
- ✅ **Early exit** fuera de ventanas de visualización (ahorra ~66% de ejecuciones)
- ✅ Solo llama a Google Maps en ventanas de ETAs (7:30-9:00, 13:30-14:45)
- ✅ No se ejecuta sábados (día sin visualización)
- ✅ Actualización meteorológica gratuita con MeteoGalicia
- ✅ Ahorra ~80% de costos vs ejecutar 24/7

## Seguridad

### Datos Sensibles

**IMPORTANTE**: Este repositorio NO contiene datos sensibles en el código. Toda la información privada se gestiona mediante variables de entorno:

- ✅ **Coordenadas**: Configuradas por variables de entorno
- ✅ **Webhook UUID**: No incluido en el código
- ✅ **API Keys**: Gestionadas por Azure/local.settings
- ✅ **Lista de festivos**: Configurable sin exponer información personal

### local.settings.json

El archivo `local.settings.json` está en `.gitignore` y **NUNCA** se debe commitear. Usa `local.settings.example.json` como plantilla.

### Coordenadas de Ejemplo

Todas las coordenadas en la documentación son de **ubicaciones públicas de Madrid**:
- Puerta del Sol (40.416775, -3.703790)
- Plaza Mayor (40.417638, -3.699500)

Actualiza con tus ubicaciones reales en las variables de entorno.

### Buenas Prácticas

1. **Nunca** commites `local.settings.json`
2. **Usa** variables de entorno en Azure para producción
3. **Rota** las API keys periódicamente
4. **Restringe** las API keys de Google Maps por dominio/IP si es posible
5. **Revisa** los logs en Azure para detectar accesos no autorizados

## Licencia

MIT

## Soporte

Para reportar problemas o solicitar características, abre un issue en el repositorio.