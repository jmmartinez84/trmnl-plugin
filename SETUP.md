# Guía Rápida: Configuración de GitHub Actions para Despliegue en Azure

## Pasos de Configuración

### 1. Crear Recursos en Azure (Si no existen)

```bash
# Login
az login

# Variables (personaliza estos valores)
RESOURCE_GROUP="trmnl-plugin-rg"
STORAGE_ACCOUNT="trmnlpluginstorage"  # debe ser único globalmente
FUNCTION_APP="trmnl-google-maps-function"
LOCATION="westeurope"

# Crear resource group
az group create --name $RESOURCE_GROUP --location $LOCATION

# Crear storage account
az storage account create \
  --name $STORAGE_ACCOUNT \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION \
  --sku Standard_LRS

# Crear Function App
az functionapp create \
  --resource-group $RESOURCE_GROUP \
  --consumption-plan-location $LOCATION \
  --runtime python \
  --runtime-version 3.9 \
  --functions-version 4 \
  --name $FUNCTION_APP \
  --storage-account $STORAGE_ACCOUNT \
  --os-type Linux
```

### 2. Configurar Variables de Entorno en Azure

```bash
# Configura tus valores reales aquí
FUNCTION_APP="trmnl-google-maps-function"
RESOURCE_GROUP="trmnl-plugin-rg"

az functionapp config appsettings set \
  --name $FUNCTION_APP \
  --resource-group $RESOURCE_GROUP \
  --settings \
    "GOOGLE_MAPS_API_KEY=TU_API_KEY_AQUI" \
    "TRMNL_WEBHOOK_URL=https://usetrmnl.com/api/custom_plugins/TU_UUID_AQUI" \
    "COORDS_CASA_LAT=40.416775" \
    "COORDS_CASA_LON=-3.703790" \
    "COORDS_COLEGIO_LAT=40.417638" \
    "COORDS_COLEGIO_LON=-3.699500" \
    "COORDS_HOSPITAL_LAT=40.420000" \
    "COORDS_HOSPITAL_LON=-3.701000" \
    "FESTIVOS=2025-10-31,2025-11-03,2025-12-05,2025-12-08,2025-12-22..2026-01-07"
```

### 3. Obtener el Perfil de Publicación

**Opción A: Desde Azure Portal**
1. Ve a tu Function App en [Azure Portal](https://portal.azure.com)
2. Haz clic en **"Get publish profile"** en la barra superior
3. Se descargará un archivo `.PublishSettings`

**Opción B: Usando Azure CLI**
```bash
az functionapp deployment list-publishing-profiles \
  --name $FUNCTION_APP \
  --resource-group $RESOURCE_GROUP \
  --xml
```

### 4. Configurar Secretos en GitHub

1. Ve a tu repositorio en GitHub
2. Settings → Secrets and variables → Actions → New repository secret
3. Agrega estos dos secretos:

| Nombre del Secreto | Valor |
|-------------------|-------|
| `AZURE_FUNCTIONAPP_NAME` | El nombre de tu Function App (ej: `trmnl-google-maps-function`) |
| `AZURE_FUNCTIONAPP_PUBLISH_PROFILE` | Contenido completo del archivo `.PublishSettings` |

**Importante**: Para `AZURE_FUNCTIONAPP_PUBLISH_PROFILE`, copia TODO el contenido del archivo XML, incluyendo las etiquetas `<publishData>` y `</publishData>`.

### 5. Activar el Workflow

1. Haz push a la rama `main`:
   ```bash
   git push origin main
   ```

2. O ejecuta manualmente:
   - Ve a Actions → Deploy Azure Function
   - Clic en "Run workflow"
   - Selecciona rama `main`
   - Clic en "Run workflow"

### 6. Verificar el Despliegue

1. **En GitHub**:
   - Ve a Actions → Busca tu workflow
   - Verifica que termine con ✅

2. **En Azure Portal**:
   - Ve a tu Function App
   - Functions → Deberías ver `google_maps_route_trigger`
   - Monitor → Logs de ejecución

## Checklist de Verificación

- [ ] Azure Function App creada
- [ ] Storage Account asociada
- [ ] Variables de entorno configuradas en Azure
- [ ] Perfil de publicación descargado
- [ ] Secreto `AZURE_FUNCTIONAPP_NAME` configurado en GitHub
- [ ] Secreto `AZURE_FUNCTIONAPP_PUBLISH_PROFILE` configurado en GitHub
- [ ] Primer despliegue ejecutado exitosamente
- [ ] Función visible en Azure Portal
- [ ] Timer trigger configurado correctamente

## Comandos Útiles

```bash
# Ver configuración actual
az functionapp config appsettings list \
  --name $FUNCTION_APP \
  --resource-group $RESOURCE_GROUP

# Ver logs en tiempo real
func azure functionapp logstream $FUNCTION_APP

# Actualizar una variable específica
az functionapp config appsettings set \
  --name $FUNCTION_APP \
  --resource-group $RESOURCE_GROUP \
  --settings "FESTIVOS=2025-12-25,2026-01-01"

# Eliminar recursos (si es necesario)
az group delete --name $RESOURCE_GROUP --yes
```

## Costos Estimados

- **Azure Functions (Consumption Plan)**: ~Gratis (dentro del tier gratuito)
  - 1M ejecuciones gratis/mes
  - Este proyecto: ~880 ejecuciones/mes
  
- **Storage Account**: ~$0.01-0.02/mes

- **Google Maps API**: ~$2.60-5.20/mes
  - Routes API: $0.005 por request
  - Este proyecto: ~520 requests/mes (solo en ventanas activas)

**Total estimado**: ~$2.60-5.25/mes

## Solución de Problemas Comunes

### "No publish profile provided"
- Verifica que copiaste TODO el contenido XML del archivo
- Debe empezar con `<publishData>` y terminar con `</publishData>`

### "Function app not found"
- Verifica que el nombre coincida exactamente (case-sensitive)
- Asegúrate de que la Function App existe en Azure

### Despliegue exitoso pero función no ejecuta
1. Verifica variables de entorno en Azure Portal
2. Revisa logs: Function App → Monitor → Live metrics
3. Verifica que Google Maps API Key sea válida
4. Verifica que Routes API esté habilitada en Google Cloud Console

### "Requirements installation failed"
- Todas las dependencias en `requirements.txt` deben ser compatibles con Python 3.9
- Verifica que no haya errores de sintaxis en `requirements.txt`

## Recursos Adicionales

- [Documentación Azure Functions](https://docs.microsoft.com/en-us/azure/azure-functions/)
- [GitHub Actions para Azure](https://github.com/Azure/actions)
- [Google Maps Routes API](https://developers.google.com/maps/documentation/routes)
- [TRMNL Custom Plugins](https://usetrmnl.com/plugins/custom)
