# Lista de Iconos Meteorológicos para Descargar

Descarga estos 8 iconos SVG y súbelos a tu blob storage:

## Iconos necesarios

| Archivo | URL de descarga | Uso |
|---------|----------------|-----|
| `weather-icons-01.svg` | https://www.svgrepo.com/show/427042/weather-icons-01.svg | Sol (día despejado) |
| `weather-icons-05.svg` | https://www.svgrepo.com/show/427047/weather-icons-05.svg | Luna (noche despejada) |
| `weather-icons-16.svg` | https://www.svgrepo.com/show/427056/weather-icons-16.svg | Nuboso |
| `weather-icons-17.svg` | https://www.svgrepo.com/show/427058/weather-icons-17.svg | Parcialmente nuboso (día) |
| `weather-icons-18.svg` | https://www.svgrepo.com/show/426994/weather-icons-18.svg | Parcialmente nuboso (noche) |
| `weather-icons-26.svg` | https://www.svgrepo.com/show/427000/weather-icons-26.svg | Lluvia intensa |
| `weather-icons-40.svg` | https://www.svgrepo.com/show/427010/weather-icons-40.svg | Lluvia débil / Chubascos |
| `weather-icons-41.svg` | https://www.svgrepo.com/show/427011/weather-icons-41.svg | Tormenta |

## Comandos para descargar (bash)

```bash
# Crear directorio para los iconos
mkdir -p weather_icons

# Descargar todos los iconos
curl -o weather_icons/weather-icons-01.svg https://www.svgrepo.com/show/427042/weather-icons-01.svg
curl -o weather_icons/weather-icons-05.svg https://www.svgrepo.com/show/427047/weather-icons-05.svg
curl -o weather_icons/weather-icons-16.svg https://www.svgrepo.com/show/427056/weather-icons-16.svg
curl -o weather_icons/weather-icons-17.svg https://www.svgrepo.com/show/427058/weather-icons-17.svg
curl -o weather_icons/weather-icons-18.svg https://www.svgrepo.com/show/426994/weather-icons-18.svg
curl -o weather_icons/weather-icons-26.svg https://www.svgrepo.com/show/427000/weather-icons-26.svg
curl -o weather_icons/weather-icons-40.svg https://www.svgrepo.com/show/427010/weather-icons-40.svg
curl -o weather_icons/weather-icons-41.svg https://www.svgrepo.com/show/427011/weather-icons-41.svg
```

## Comandos para descargar (PowerShell en Windows)

```powershell
# Crear directorio para los iconos
New-Item -ItemType Directory -Force -Path weather_icons

# Descargar todos los iconos
Invoke-WebRequest -Uri "https://www.svgrepo.com/show/427042/weather-icons-01.svg" -OutFile "weather_icons/weather-icons-01.svg"
Invoke-WebRequest -Uri "https://www.svgrepo.com/show/427047/weather-icons-05.svg" -OutFile "weather_icons/weather-icons-05.svg"
Invoke-WebRequest -Uri "https://www.svgrepo.com/show/427056/weather-icons-16.svg" -OutFile "weather_icons/weather-icons-16.svg"
Invoke-WebRequest -Uri "https://www.svgrepo.com/show/427058/weather-icons-17.svg" -OutFile "weather_icons/weather-icons-17.svg"
Invoke-WebRequest -Uri "https://www.svgrepo.com/show/426994/weather-icons-18.svg" -OutFile "weather_icons/weather-icons-18.svg"
Invoke-WebRequest -Uri "https://www.svgrepo.com/show/427000/weather-icons-26.svg" -OutFile "weather_icons/weather-icons-26.svg"
Invoke-WebRequest -Uri "https://www.svgrepo.com/show/427010/weather-icons-40.svg" -OutFile "weather_icons/weather-icons-40.svg"
Invoke-WebRequest -Uri "https://www.svgrepo.com/show/427011/weather-icons-41.svg" -OutFile "weather_icons/weather-icons-41.svg"
```

## Estructura esperada en blob storage

Una vez subidos, la estructura de URLs debería ser:

```
https://tudominio.blob.core.windows.net/iconos/weather-icons-01.svg
https://tudominio.blob.core.windows.net/iconos/weather-icons-05.svg
https://tudominio.blob.core.windows.net/iconos/weather-icons-16.svg
https://tudominio.blob.core.windows.net/iconos/weather-icons-17.svg
https://tudominio.blob.core.windows.net/iconos/weather-icons-18.svg
https://tudominio.blob.core.windows.net/iconos/weather-icons-26.svg
https://tudominio.blob.core.windows.net/iconos/weather-icons-40.svg
https://tudominio.blob.core.windows.net/iconos/weather-icons-41.svg
```

## Configuración después de subirlos

Después de subir los iconos a tu blob storage, configura la variable de entorno:

```
WEATHER_ICONS_BASE_URL=https://tudominio.blob.core.windows.net/iconos
```

El código añadirá automáticamente el nombre del archivo al final de esta URL base.

## Licencia

Todos estos iconos son de SVG Repo y están bajo licencia libre para uso comercial.
