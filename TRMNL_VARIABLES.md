# Variables TRMNL - Referencia completa

Este documento describe todas las variables que se envían al webhook de TRMNL para usar en tu plantilla Liquid.

## Variables Generales

### `show_routes` (boolean)
- Indica si las rutas deben mostrarse
- `true`: Estamos en horario de salida (7:30-9:00 o 13:30-14:45)
- `false`: Fuera del horario o es festivo

### `timestamp` (string ISO 8601)
- Timestamp UTC de cuando se generó el payload
- Formato: `"2025-11-11T18:10:34.000000+00:00"`

---

## Variables de Rutas
*Solo disponibles cuando `show_routes = true`*

### `departure_time` (string)
- Hora de salida calculada (15 minutos después del trigger)
- Formato: `"2025-11-11 08:15:00 CET"`

### `eta_directo` (string)
- Tiempo estimado de llegada por ruta directa (Casa → Colegio)
- Formato: `"12 min"` o `"N/A"` si falla

### `eta_directo_seconds` (string)
- Duración en segundos de la ruta directa
- Formato: `"720s"` (solo si la ruta fue exitosa)

### `distance_directo_km` (float)
- Distancia en kilómetros de la ruta directa
- Formato: `8.5` (solo si la ruta fue exitosa)

### `eta_con_hospital` (string)
- Tiempo estimado de llegada con parada en hospital (Casa → Hospital → Colegio)
- Formato: `"18 min"` o `"N/A"` si falla

### `eta_con_hospital_seconds` (string)
- Duración en segundos de la ruta con hospital
- Formato: `"1080s"` (solo si la ruta fue exitosa)

### `distance_hospital_km` (float)
- Distancia en kilómetros de la ruta con hospital
- Formato: `12.3` (solo si la ruta fue exitosa)

---

## Variables Meteorológicas - Casa

### `weather_casa_sky` (string)
- Estado del cielo actual en casa
- Valores posibles:
  - `"SUNNY"` - Despejado
  - `"PARTLY_CLOUDY"` - Parcialmente nuboso
  - `"CLOUDY"` - Nuboso
  - `"HIGH_CLOUDS"` - Nubes altas
  - `"OVERCAST_AND_SHOWERS"` - Cubierto con chubascos
  - `"WEAK_SHOWERS"` - Chubascos débiles
  - `"SHOWERS"` - Chubascos
  - `"RAIN"` - Lluvia
  - `"STORM_THEN_CLOUDY"` - Tormenta luego nuboso
  - `"N/A"` - No disponible

### `weather_casa_icon` (string URL)
- URL del icono meteorológico en formato SVG (compatible con TRMNL e-ink)
- Iconos optimizados para pantallas monocromas de baja resolución
- Ejemplo: `"https://tudominio.blob.core.windows.net/iconos/weather-icons-17.svg"`
- Los iconos cambian automáticamente entre día/noche
- Puede estar vacío si no hay datos
- La URL base se configura con la variable de entorno `WEATHER_ICONS_BASE_URL`

**Mapeo de iconos por estado del cielo:**

| Estado del cielo | Día | Noche | Archivo |
|-----------------|-----|-------|---------|
| SUNNY (Despejado) | ☀️ Sol | 🌙 Luna | weather-icons-01.svg / weather-icons-05.svg |
| PARTLY_CLOUDY | ⛅ Parcialmente nuboso día | 🌙☁️ Parcialmente nuboso noche | weather-icons-17.svg / weather-icons-18.svg |
| CLOUDY | ☁️ Nuboso | ☁️ Nuboso | weather-icons-16.svg |
| HIGH_CLOUDS | ⛅ Nubes altas | 🌙☁️ Nubes altas noche | weather-icons-17.svg / weather-icons-18.svg |
| WEAK_SHOWERS | 🌦️ Lluvia débil | 🌦️ Lluvia débil | weather-icons-40.svg |
| SHOWERS | 🌧️ Lluvia | 🌧️ Lluvia | weather-icons-40.svg |
| RAIN | 🌧️ Lluvia continua | 🌧️ Lluvia continua | weather-icons-26.svg |
| OVERCAST_AND_SHOWERS | 🌧️ Lluvia intensa | 🌧️ Lluvia intensa | weather-icons-26.svg |
| STORM_THEN_CLOUDY | ⛈️ Tormenta | ⛈️ Tormenta | weather-icons-41.svg |

**Iconos SVG necesarios (8 archivos):**
- `weather-icons-01.svg` - Sol (día despejado)
- `weather-icons-05.svg` - Luna (noche despejada)
- `weather-icons-16.svg` - Nuboso
- `weather-icons-17.svg` - Parcialmente nuboso (día)
- `weather-icons-18.svg` - Parcialmente nuboso (noche)
- `weather-icons-26.svg` - Lluvia intensa
- `weather-icons-40.svg` - Lluvia débil / Chubascos
- `weather-icons-41.svg` - Tormenta

**Configuración de iconos:**

Puedes usar iconos desde:
1. **Tu blob storage** (recomendado): Configura `WEATHER_ICONS_BASE_URL=https://tudominio.blob.core.windows.net/iconos`
2. **SVG Repo** (por defecto): Si no configuras `WEATHER_ICONS_BASE_URL`, se usarán automáticamente

Ver `weather_icons_download_list.md` para instrucciones de descarga de los iconos.

### `weather_casa_temperature` (float o null)
- Temperatura actual en casa (en grados Celsius)
- Formato: `15.2` (grados Celsius con 1 decimal)
- Ejemplo: `18.5` = 18.5°C
- Puede ser `null` si no hay datos disponibles

### `weather_casa_rain_3h` (boolean)
- Indica si habrá lluvia en las próximas 3 horas en casa
- `true`: Se espera precipitación
- `false`: No se espera precipitación

### `weather_casa_precipitation_today` (float)
- Precipitación total del día en casa (en mm)
- Formato: `1.9` (milímetros)

---

## Variables Meteorológicas - Colegio

### `weather_colegio_sky` (string)
- Estado del cielo actual en el colegio
- Mismos valores posibles que `weather_casa_sky`

### `weather_colegio_icon` (string URL)
- URL del icono meteorológico del colegio en formato SVG
- Mismo formato y mapeo que `weather_casa_icon`
- Los iconos son compatibles con TRMNL e-ink y cambian entre día/noche automáticamente

### `weather_colegio_temperature` (float o null)
- Temperatura actual en el colegio (en grados Celsius)
- Mismo formato que `weather_casa_temperature`
- Puede ser `null` si no hay datos disponibles

### `weather_colegio_rain_3h` (boolean)
- Indica si habrá lluvia en las próximas 3 horas en el colegio
- Mismo formato que `weather_casa_rain_3h`

### `weather_colegio_precipitation_today` (float)
- Precipitación total del día en el colegio (en mm)
- Mismo formato que `weather_casa_precipitation_today`

---

## Traducciones de Estados del Cielo (Gallego → Español)

Para mostrar los estados en español en tu plantilla Liquid:

```liquid
{% case weather_casa_sky %}
  {% when "SUNNY" %}
    Despejado
  {% when "PARTLY_CLOUDY" %}
    Parcialmente nuboso
  {% when "CLOUDY" %}
    Nuboso
  {% when "HIGH_CLOUDS" %}
    Nubes altas
  {% when "OVERCAST_AND_SHOWERS" %}
    Cubierto con chubascos
  {% when "WEAK_SHOWERS" %}
    Chubascos débiles
  {% when "SHOWERS" %}
    Chubascos
  {% when "RAIN" %}
    Lluvia
  {% when "STORM_THEN_CLOUDY" %}
    Tormenta
  {% else %}
    {{ weather_casa_sky }}
{% endcase %}
```

---

## Ejemplo de Plantilla Liquid

```liquid
<div class="weather">
  <h3>Tiempo en Casa</h3>
  <img src="{{ weather_casa_icon }}" alt="Tiempo">
  <p>{{ weather_casa_sky }}</p>
  {% if weather_casa_temperature %}
    <p>Temperatura: {{ weather_casa_temperature }}°C</p>
  {% endif %}
  {% if weather_casa_rain_3h %}
    <p>⚠️ Lluvia próximas 3h</p>
  {% endif %}
  <p>Precipitación hoy: {{ weather_casa_precipitation_today }} mm</p>
</div>

{% if show_routes %}
  <div class="routes">
    <h3>Rutas al Colegio</h3>
    <p>Salida: {{ departure_time }}</p>
    <p>Directo: {{ eta_directo }} ({{ distance_directo_km }} km)</p>
    <p>Con hospital: {{ eta_con_hospital }} ({{ distance_hospital_km }} km)</p>
  </div>
{% endif %}
```

---

## Notas Importantes

1. Las variables meteorológicas están **siempre disponibles** (se actualizan cada 15 minutos todo el día)
2. Las variables de rutas **solo están disponibles cuando `show_routes = true`**
3. Verifica siempre que las variables existan antes de usarlas en tu plantilla
4. Los iconos de MeteoGalicia son diferentes para día/noche (incluido en la URL)
