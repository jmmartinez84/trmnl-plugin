# GitHub Actions - Azure Function Deployment

Este directorio contiene el workflow de GitHub Actions para desplegar automáticamente la Azure Function a Azure.

## Archivo de Workflow

### `azure-function-deploy.yml`

Este workflow realiza las siguientes acciones:

1. **Checkout del código**: Obtiene el código del repositorio
2. **Configuración de Python**: Configura el entorno Python 3.9
3. **Instalación de dependencias**: Instala las dependencias desde `requirements.txt`
4. **Despliegue a Azure**: Despliega la función a Azure Functions usando el perfil de publicación

## Triggers

El workflow se ejecuta:
- ✅ Automáticamente en cada push a la rama `main`
- ✅ Manualmente desde la pestaña Actions (workflow_dispatch)

## Secretos Requeridos

Debes configurar los siguientes secretos en tu repositorio de GitHub:

1. **AZURE_FUNCTIONAPP_NAME**
   - Tipo: Secret
   - Valor: El nombre de tu Azure Function App (ej: `MyGoogleMapsFunction`)
   - Dónde obtenerlo: Azure Portal → Function App → Overview

2. **AZURE_FUNCTIONAPP_PUBLISH_PROFILE**
   - Tipo: Secret
   - Valor: Contenido completo del archivo de perfil de publicación
   - Dónde obtenerlo: Azure Portal → Function App → Get publish profile (botón en la barra superior)

## Cómo Configurar los Secretos

1. Ve a tu repositorio en GitHub
2. Settings → Secrets and variables → Actions → New repository secret
3. Agrega cada secreto con su nombre exacto y valor correspondiente

## Variables de Entorno de Azure

Recuerda configurar todas las variables de entorno en tu Azure Function App:

```bash
az functionapp config appsettings set \
  --name <TU_FUNCTION_APP> \
  --resource-group <TU_RESOURCE_GROUP> \
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

## Verificación del Despliegue

1. Ve a la pestaña **Actions** en tu repositorio de GitHub
2. Busca el workflow "Deploy Azure Function"
3. Revisa los logs para verificar que el despliegue fue exitoso
4. Una vez completado, verifica en Azure Portal:
   - Function App → Functions → Deberías ver `google_maps_route_trigger`
   - Monitor → Para ver las ejecuciones y logs

## Despliegue Manual

Para ejecutar el workflow manualmente:

1. Ve a Actions → Deploy Azure Function
2. Haz clic en "Run workflow"
3. Selecciona la rama (normalmente `main`)
4. Haz clic en "Run workflow" (botón verde)

## Solución de Problemas

### Error: "No publish profile provided"
- Verifica que el secreto `AZURE_FUNCTIONAPP_PUBLISH_PROFILE` esté configurado correctamente
- El contenido debe incluir todo el XML del archivo `.PublishSettings`

### Error: "Function app not found"
- Verifica que el secreto `AZURE_FUNCTIONAPP_NAME` coincida exactamente con el nombre de tu Function App en Azure

### Error en la instalación de dependencias
- Verifica que `requirements.txt` esté en la raíz del repositorio
- Todas las dependencias deben ser compatibles con Python 3.9

### El deployment es exitoso pero la función no funciona
- Verifica las variables de entorno en Azure Portal
- Revisa los logs en Azure Portal → Function App → Monitor
- Verifica que la API Key de Google Maps sea válida y tenga Routes API habilitada

## Estructura del Workflow

```yaml
name: Deploy Azure Function
on:
  push:
    branches: [main]
  workflow_dispatch:

jobs:
  build-and-deploy:
    - Checkout code
    - Setup Python 3.9
    - Install dependencies
    - Deploy to Azure Functions
```

## Mejoras Futuras

Posibles mejoras al workflow:

- [ ] Agregar tests antes del despliegue
- [ ] Validar la configuración antes del despliegue
- [ ] Notificaciones de despliegue (Slack, email, etc.)
- [ ] Rollback automático en caso de error
- [ ] Despliegue en staging antes de producción

## Referencias

- [Azure Functions Action](https://github.com/Azure/functions-action)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Azure Functions Documentation](https://docs.microsoft.com/en-us/azure/azure-functions/)
