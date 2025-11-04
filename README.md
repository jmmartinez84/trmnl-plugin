# Azure Function - Google Maps Route Trigger + TRMNL Integration

Función de Azure que obtiene información de rutas de Google Maps dos veces al día y envía los datos a TRMNL.

## Descripción

Esta función se ejecuta automáticamente dos veces al día para:
1. Obtener información de tráfico y rutas de Google Maps entre dos ubicaciones
2. Enviar los datos automáticamente al webhook de TRMNL

**Rutas configuradas:**
- **Ruta 1 (Directa)**: Casa → Colegio
- **Ruta 2 (Con parada)**: Casa → Hospital → Colegio

**Coordenadas:**
- **Casa**: 42.171842, -8.628590
- **Colegio**: 42.210826, -8.692426
- **Hospital**: 42.214366, -8.683297 *(actualizar con coordenadas exactas)*

**Webhook TRMNL**: `https://usetrmnl.com/api/custom_plugins/3f6873b7-8fb9-43c3-a3c3-3438092d4a87`

## Horarios de Ejecución

La función está configurada con un time trigger que se ejecuta:

### Horario de Invierno (CET = UTC+1)
- **Primera ejecución**: 7:50 AM hora española (6:50 AM UTC) → Obtiene ruta para las 8:05 AM
- **Segunda ejecución**: 1:50 PM hora española (12:50 PM UTC) → Obtiene ruta para las 2:05 PM

### Horario de Verano (CEST = UTC+2)
- **Primera ejecución**: 7:50 AM hora española (5:50 AM UTC) → Obtiene ruta para las 8:05 AM
- **Segunda ejecución**: 1:50 PM hora española (11:50 AM UTC) → Obtiene ruta para las 2:05 PM

**Nota**: Para ajustar automáticamente al horario de verano, necesitarás actualizar el cron schedule en `function_app.py` o usar una zona horaria específica en la configuración de Azure.

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

3. Copia el archivo `local.settings.json` y actualiza la configuración:
   ```json
   {
     "IsEncrypted": false,
     "Values": {
       "AzureWebJobsStorage": "UseDevelopmentStorage=true",
       "FUNCTIONS_WORKER_RUNTIME": "python",
       "GOOGLE_MAPS_API_KEY": "TU_API_KEY_AQUI"
     }
   }
   ```

### 2. Obtener API Key de Google Maps

1. Ve a [Google Cloud Console](https://console.cloud.google.com/)
2. Crea un nuevo proyecto o selecciona uno existente
3. Habilita la API "Routes API"
4. Crea credenciales (API Key)
5. Copia la API Key y agrégala a tu configuración

### 3. Configuración en Azure

Para desplegar en Azure, configura la variable de entorno en tu Function App:

```bash
az functionapp config appsettings set \
  --name <nombre-de-tu-function-app> \
  --resource-group <nombre-de-tu-resource-group> \
  --settings "GOOGLE_MAPS_API_KEY=TU_API_KEY_AQUI"
```

O configúrala desde Azure Portal:
1. Ve a tu Function App
2. Configuración → Variables de entorno
3. Agrega `GOOGLE_MAPS_API_KEY` con tu API key

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

Edita las coordenadas en `function_app.py` (líneas 15-18):

```python
# Coordenadas
COORDS_CASA = {"latitude": TU_LATITUD_CASA, "longitude": TU_LONGITUD_CASA}
COORDS_COLEGIO = {"latitude": TU_LATITUD_COLEGIO, "longitude": TU_LONGITUD_COLEGIO}
COORDS_HOSPITAL = {"latitude": TU_LATITUD_HOSPITAL, "longitude": TU_LONGITUD_HOSPITAL}
```

**IMPORTANTE**: Las coordenadas del hospital (42.214366, -8.683297) son aproximadas. Actualízalas con las coordenadas exactas del hospital que necesites.

**Cómo obtener coordenadas:**
1. Ve a Google Maps
2. Haz clic derecho en la ubicación deseada
3. Selecciona las coordenadas para copiarlas
4. El formato será: `latitud, longitud` (ej: 42.214366, -8.683297)

### Cambiar Horarios

Modifica la expresión cron en el decorador `@app.timer_trigger`:

```python
@app.timer_trigger(schedule="0 50 6,12 * * *", ...)
```

Formato cron: `segundo minuto hora dia mes dia_semana`
- `0 50 6,12 * * *` = A los 50 minutos de las 6 y 12 horas (UTC)

Para horario de verano (CEST = UTC+2), usa:
```python
@app.timer_trigger(schedule="0 50 5,11 * * *", ...)
```

### Cambiar Webhook de TRMNL

Para usar un webhook diferente, edita la constante en `function_app.py`:

```python
TRMNL_WEBHOOK_URL = "https://usetrmnl.com/api/custom_plugins/TU_PLUGIN_ID"
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
- `{{ eta_directo }}`: Tiempo estimado Casa → Colegio (formato: "XX min")
- `{{ eta_con_hospital }}`: Tiempo estimado Casa → Hospital → Colegio (formato: "XX min")
- `{{ departure_time }}`: Hora de salida programada en hora española
- `{{ timestamp }}`: Timestamp UTC de cuando se ejecutó la función
- `{{ distance_directo_km }}`: Distancia de la ruta directa en km
- `{{ distance_hospital_km }}`: Distancia de la ruta con hospital en km
- `{{ eta_directo_seconds }}`: Duración en formato Google Maps (ej: "1080s")
- `{{ eta_con_hospital_seconds }}`: Duración en formato Google Maps (ej: "1680s")

### Cómo usar las variables en tu template TRMNL

```liquid
{% if materias.size > 0 and es_festivo == false %}
  <div class="eta-container">
    <div class="eta-item">
      <div class="eta-tiempo">{{ eta_directo }}</div>
      <div class="eta-label">Casa → Colegio</div>
    </div>
    <div class="eta-item">
      <div class="eta-tiempo">{{ eta_con_hospital }}</div>
      <div class="eta-label">Casa → Hospital → Colegio</div>
    </div>
  </div>
{% endif %}
```

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
- Aproximadamente 2 consultas por día = ~60 consultas/mes

### Azure Functions
- Plan de Consumo: Primeras 1M ejecuciones gratis cada mes
- Esta función: ~60 ejecuciones/mes (muy por debajo del límite gratuito)

## Licencia

MIT

## Soporte

Para reportar problemas o solicitar características, abre un issue en el repositorio.