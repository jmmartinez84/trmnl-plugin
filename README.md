# Azure Function - Google Maps Route Trigger

Función de Azure que obtiene información de rutas de Google Maps dos veces al día usando la API de Google Maps Routes.

## Descripción

Esta función se ejecuta automáticamente dos veces al día para obtener información de tráfico y rutas entre dos ubicaciones:
- **Origen**: Casa (42.171842, -8.628590)
- **Destino**: Colegio (42.210826, -8.692426)

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

Edita las coordenadas en `function_app.py`:

```python
ROUTE_CONFIG = {
    "origin": {
        "location": {
            "latLng": {
                "latitude": TU_LATITUD_ORIGEN,
                "longitude": TU_LONGITUD_ORIGEN
            }
        }
    },
    "destination": {
        "location": {
            "latLng": {
                "latitude": TU_LATITUD_DESTINO,
                "longitude": TU_LONGITUD_DESTINO
            }
        }
    },
    # ...
}
```

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