import azure.functions as func
import logging
import json
import os
import requests
from datetime import datetime, timedelta
from dateutil import tz

app = func.FunctionApp()

# Configuración desde variables de entorno
def get_env_config():
    """Obtiene configuración desde variables de entorno."""
    return {
        "webhook_url": os.environ.get('TRMNL_WEBHOOK_URL'),
        "coords_casa": {
            "latitude": float(os.environ.get('COORDS_CASA_LAT', '0')),
            "longitude": float(os.environ.get('COORDS_CASA_LON', '0'))
        },
        "coords_colegio": {
            "latitude": float(os.environ.get('COORDS_COLEGIO_LAT', '0')),
            "longitude": float(os.environ.get('COORDS_COLEGIO_LON', '0'))
        },
        "coords_hospital": {
            "latitude": float(os.environ.get('COORDS_HOSPITAL_LAT', '0')),
            "longitude": float(os.environ.get('COORDS_HOSPITAL_LON', '0'))
        },
        # Festivos en formato: "2025-10-31,2025-11-03,2025-12-05,2025-12-08"
        "festivos": os.environ.get('FESTIVOS', '').split(',') if os.environ.get('FESTIVOS') else []
    }

def get_google_maps_route(origin: dict, destination: dict, departure_time: datetime,
                          api_key: str, intermediates: list = None) -> dict:
    """
    Obtiene la ruta de Google Maps para un tiempo de salida específico.

    Args:
        origin: Diccionario con latitude y longitude del origen
        destination: Diccionario con latitude y longitude del destino
        departure_time: Hora de salida deseada
        api_key: Clave de API de Google Maps
        intermediates: Lista opcional de waypoints intermedios

    Returns:
        Respuesta de la API de Google Maps
    """
    url = "https://routes.googleapis.com/directions/v2:computeRoutes"

    # Formatear el tiempo de salida en formato ISO 8601
    departure_time_str = departure_time.strftime("%Y-%m-%dT%H:%M:%SZ")

    # Preparar el payload
    payload = {
        "origin": {
            "location": {
                "latLng": origin
            }
        },
        "destination": {
            "location": {
                "latLng": destination
            }
        },
        "travelMode": "DRIVE",
        "routingPreference": "TRAFFIC_AWARE_OPTIMAL",
        "departureTime": departure_time_str
    }

    # Agregar waypoints intermedios si existen
    if intermediates and len(intermediates) > 0:
        payload["intermediates"] = [
            {"location": {"latLng": coords}} for coords in intermediates
        ]

    # Headers requeridos por Google Maps API
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": "routes.duration,routes.distanceMeters,routes.polyline.encodedPolyline,routes.legs.duration,routes.legs.distanceMeters"
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return {
            "success": True,
            "data": response.json(),
            "status_code": response.status_code
        }
    except requests.exceptions.RequestException as e:
        logging.error(f"Error al llamar a Google Maps API: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "status_code": getattr(e.response, 'status_code', None) if hasattr(e, 'response') else None
        }

def calculate_departure_time() -> datetime:
    """
    Calcula el tiempo de salida (15 minutos después del tiempo actual).

    Returns:
        Tiempo de salida en UTC
    """
    # Obtener hora actual en UTC
    now_utc = datetime.now(tz.UTC)

    # Agregar 15 minutos
    departure_time = now_utc + timedelta(minutes=15)

    return departure_time

def get_meteogalicia_forecast(latitude: float, longitude: float, api_key: str) -> dict:
    """
    Obtiene la predicción meteorológica de MeteoGalicia para unas coordenadas específicas.

    Args:
        latitude: Latitud de la ubicación
        longitude: Longitud de la ubicación
        api_key: Clave de API de MeteoGalicia

    Returns:
        Respuesta de la API de MeteoGalicia con predicciones horarias
    """
    url = "https://servizos.meteogalicia.gal/apiv4/getNumericForecastInfo"

    params = {
        "coords": f"{longitude},{latitude}",
        "variables": "sky_state,precipitation_amount,temperature",
        "lang": "gl",
        "API_KEY": api_key
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        return {
            "success": True,
            "data": response.json(),
            "status_code": response.status_code
        }
    except requests.exceptions.RequestException as e:
        logging.error(f"Error al llamar a MeteoGalicia API: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "status_code": getattr(e.response, 'status_code', None) if hasattr(e, 'response') else None
        }

def get_solar_info(latitude: float, longitude: float, api_key: str) -> dict:
    """
    Obtiene la información solar (salida/puesta del sol) de MeteoGalicia.

    Args:
        latitude: Latitud de la ubicación
        longitude: Longitud de la ubicación
        api_key: Clave de API de MeteoGalicia

    Returns:
        Respuesta de la API de MeteoGalicia con datos solares
    """
    url = "https://servizos.meteogalicia.gal/apiv4/getSolarInfo"

    params = {
        "coords": f"{longitude},{latitude}",
        "lang": "es",
        "API_KEY": api_key
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        return {
            "success": True,
            "data": response.json(),
            "status_code": response.status_code
        }
    except requests.exceptions.RequestException as e:
        logging.error(f"Error al llamar a MeteoGalicia Solar API: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "status_code": getattr(e.response, 'status_code', None) if hasattr(e, 'response') else None
        }

def parse_solar_info(solar_data: dict) -> dict:
    """
    Parsea los datos solares de MeteoGalicia y extrae sunrise/sunset del día actual.

    Args:
        solar_data: Respuesta de la API getSolarInfo de MeteoGalicia

    Returns:
        Diccionario con sunrise y sunset del día actual
    """
    if not solar_data.get('success'):
        return {
            "success": False,
            "error": solar_data.get('error', 'Unknown error')
        }

    try:
        data = solar_data['data']
        features = data.get('features', [])

        if not features or len(features) == 0:
            return {
                "success": False,
                "error": "No solar data available"
            }

        # Obtener el primer feature
        feature = features[0]
        properties = feature.get('properties', {})
        days = properties.get('days', [])

        if not days or len(days) == 0:
            return {
                "success": False,
                "error": "No daily solar data available"
            }

        spanish_tz = tz.gettz('Europe/Madrid')
        now_spanish = datetime.now(spanish_tz)
        today_date = now_spanish.strftime("%Y-%m-%d")

        # Buscar datos del día actual
        for day_data in days:
            time_period = day_data.get('timePeriod', {})
            begin_time_str = time_period.get('begin', {}).get('timeInstant', '')

            if begin_time_str:
                # Parsear la fecha del día
                day_date = datetime.fromisoformat(begin_time_str).strftime("%Y-%m-%d")

                if day_date == today_date:
                    # Encontramos el día actual
                    variables = day_data.get('variables', [])
                    for var in variables:
                        if var.get('name') == 'solar':
                            sunrise_str = var.get('sunrise', '')
                            sunset_str = var.get('sunset', '')

                            if sunrise_str and sunset_str:
                                sunrise = datetime.fromisoformat(sunrise_str)
                                sunset = datetime.fromisoformat(sunset_str)

                                return {
                                    "success": True,
                                    "sunrise": sunrise,
                                    "sunset": sunset,
                                    "duration": var.get('duration', 'N/A')
                                }

        # Si no encontramos el día actual, usar el primero disponible
        first_day = days[0]
        variables = first_day.get('variables', [])
        for var in variables:
            if var.get('name') == 'solar':
                sunrise_str = var.get('sunrise', '')
                sunset_str = var.get('sunset', '')

                if sunrise_str and sunset_str:
                    sunrise = datetime.fromisoformat(sunrise_str)
                    sunset = datetime.fromisoformat(sunset_str)

                    return {
                        "success": True,
                        "sunrise": sunrise,
                        "sunset": sunset,
                        "duration": var.get('duration', 'N/A')
                    }

        return {
            "success": False,
            "error": "Could not find solar data for today"
        }

    except Exception as e:
        logging.error(f"Error al parsear datos solares de MeteoGalicia: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

def parse_weather_forecast(forecast_data: dict, location_name: str) -> dict:
    """
    Parsea los datos de MeteoGalicia y extrae información relevante del día actual.

    Args:
        forecast_data: Respuesta de la API de MeteoGalicia
        location_name: Nombre de la ubicación (ej: "casa", "colegio")

    Returns:
        Diccionario con datos meteorológicos procesados
    """
    if not forecast_data.get('success'):
        return {
            "success": False,
            "error": forecast_data.get('error', 'Unknown error')
        }

    try:
        data = forecast_data['data']
        features = data.get('features', [])

        if not features or len(features) == 0:
            return {
                "success": False,
                "error": "No forecast data available"
            }

        # Obtener el primer feature (contiene todos los días de predicción)
        feature = features[0]
        properties = feature.get('properties', {})
        days = properties.get('days', [])

        if not days or len(days) == 0:
            return {
                "success": False,
                "error": "No daily forecast available"
            }

        spanish_tz = tz.gettz('Europe/Madrid')
        now_spanish = datetime.now(spanish_tz)

        # Extraer datos de hoy y los próximos días
        weather_info = {
            "success": True,
            "location": location_name,
            "days": []
        }

        # Procesamos solo los primeros 4 días porque:
        # - El API puede devolver más días, pero solo los próximos 4 son relevantes para nuestro caso de uso (por ejemplo, mostrar previsión a corto plazo).
        # - Si se requiere más días en el futuro, ajustar este límite.
        for day_data in days[:4]:
            time_period = day_data.get('timePeriod', {})
            begin_time_str = time_period.get('begin', {}).get('timeInstant', '')

            # Parsear la fecha del día
            if begin_time_str:
                # Normalizar timezone
                time_str_normalized = begin_time_str
                if '+' in begin_time_str and ':' not in begin_time_str.split('+')[1]:
                    parts = begin_time_str.rsplit('+', 1)
                    time_str_normalized = f"{parts[0]}+{parts[1]}:00"
                elif '-' in begin_time_str and begin_time_str.count('-') > 2:
                    parts = begin_time_str.rsplit('-', 1)
                    if ':' not in parts[1]:
                        time_str_normalized = f"{parts[0]}-{parts[1]}:00"

                day_date = datetime.fromisoformat(time_str_normalized)

                day_info = {
                    "date": day_date.strftime("%Y-%m-%d"),
                    "sky_state": [],
                    "precipitation": [],
                    "temperature": []
                }

                variables = day_data.get('variables', [])

                for var in variables:
                    var_name = var.get('name')
                    values = var.get('values', [])

                    if var_name == 'sky_state':
                        for val in values:
                            day_info['sky_state'].append({
                                "time": val.get('timeInstant', ''),
                                "value": val.get('value', ''),
                                "icon": val.get('iconURL', '')
                            })
                    elif var_name == 'precipitation_amount':
                        for val in values:
                            day_info['precipitation'].append({
                                "time": val.get('timeInstant', ''),
                                "value": val.get('value', 0)
                            })
                    elif var_name == 'temperature':
                        for val in values:
                            day_info['temperature'].append({
                                "time": val.get('timeInstant', ''),
                                "value": val.get('value', 0)
                            })

                weather_info['days'].append(day_info)

        return weather_info

    except Exception as e:
        logging.error(f"Error al parsear datos de MeteoGalicia: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

def map_weather_to_svg_icon(sky_state: str, is_night: bool = False, base_url: str = None) -> str:
    """
    Mapea el estado del cielo de MeteoGalicia a un icono SVG compatible con TRMNL.

    Args:
        sky_state: Estado del cielo de MeteoGalicia
        is_night: Si es de noche (para iconos día/noche)
        base_url: URL base del blob storage (ej: "https://tudominio.blob.core.windows.net/iconos")

    Returns:
        URL del icono SVG apropiado
    """
    # Si no se proporciona base_url, usar svgrepo.com por defecto
    if not base_url:
        base_url = "https://www.svgrepo.com/show"

    # Mapeo de estados de MeteoGalicia a nombres de archivo de iconos
    icon_mapping = {
        # Estados diurnos
        "SUNNY": "weather-icons-01.svg",  # Sol
        "PARTLY_CLOUDY": "weather-icons-17.svg",  # Parcialmente nuboso día
        "CLOUDY": "weather-icons-16.svg",  # Nuboso
        "HIGH_CLOUDS": "weather-icons-17.svg",  # Nubes altas (similar a parcialmente nuboso)
        "OVERCAST_AND_SHOWERS": "weather-icons-26.svg",  # Lluvia intensa
        "WEAK_SHOWERS": "weather-icons-40.svg",  # Lluvia débil
        "SHOWERS": "weather-icons-40.svg",  # Lluvia
        "RAIN": "weather-icons-26.svg",  # Lluvia continua
        "STORM_THEN_CLOUDY": "weather-icons-41.svg",  # Tormenta
    }

    # Mapeo de estados nocturnos (cuando difieren del día)
    night_icon_mapping = {
        "SUNNY": "weather-icons-05.svg",  # Luna
        "PARTLY_CLOUDY": "weather-icons-18.svg",  # Parcialmente nuboso noche
        "HIGH_CLOUDS": "weather-icons-18.svg",  # Nubes altas noche
    }

    # Determinar qué icono usar
    icon_filename = None
    if is_night and sky_state in night_icon_mapping:
        icon_filename = night_icon_mapping[sky_state]
    else:
        icon_filename = icon_mapping.get(sky_state, "weather-icons-01.svg")

    # Construir la URL completa
    # Si base_url es de svgrepo.com, usar el formato especial
    if "svgrepo.com" in base_url:
        # Extraer el número del ID del archivo (ej: weather-icons-01.svg -> 427042)
        svgrepo_ids = {
            "weather-icons-01.svg": "427042",
            "weather-icons-05.svg": "427047",
            "weather-icons-16.svg": "427056",
            "weather-icons-17.svg": "427058",
            "weather-icons-18.svg": "426994",
            "weather-icons-26.svg": "427000",
            "weather-icons-40.svg": "427010",
            "weather-icons-41.svg": "427011",
        }
        icon_id = svgrepo_ids.get(icon_filename, "427042")
        return f"{base_url}/{icon_id}/{icon_filename}"
    else:
        # Para blob storage u otros, simplemente concatenar
        return f"{base_url}/{icon_filename}"

def get_current_weather_summary(weather_info: dict, icons_base_url: str = None, solar_info: dict = None, target_date: str = None) -> dict:
    """
    Obtiene un resumen del tiempo actual y para las próximas horas.

    Args:
        weather_info: Datos meteorológicos parseados
        icons_base_url: URL base para los iconos meteorológicos (opcional)
        solar_info: Información solar (sunrise/sunset) parseada (opcional)
        target_date: Fecha objetivo en formato "YYYY-MM-DD" (opcional, por defecto hoy)

    Returns:
        Resumen del tiempo para mostrar en el display
    """
    if not weather_info.get('success'):
        return {
            "current_sky": "N/A",
            "current_icon": "",
            "current_temperature": None,
            "next_hours_rain": False,
            "total_precipitation_today": 0
        }

    spanish_tz = tz.gettz('Europe/Madrid')
    now_spanish = datetime.now(spanish_tz)

    # Usar fecha objetivo si se proporciona, si no usar hoy
    if target_date:
        search_date = target_date
        logging.info(f'  DEBUG: Buscando datos meteorológicos para fecha objetivo: {search_date}')
    else:
        search_date = now_spanish.strftime("%Y-%m-%d")
        logging.info(f'  DEBUG: Buscando datos meteorológicos para hoy: {search_date}')

    # Buscar el día objetivo
    today_data = None
    for day in weather_info.get('days', []):
        if day['date'] == search_date:
            today_data = day
            break

    if not today_data:
        return {
            "current_sky": "N/A",
            "current_icon": "",
            "current_temperature": None,
            "next_hours_rain": False,
            "total_precipitation_today": 0
        }

    # Encontrar el estado del cielo más cercano a la hora actual
    current_sky = "N/A"
    current_icon = ""
    sky_states = today_data.get('sky_state', [])

    logging.info(f'  DEBUG: Encontrados {len(sky_states)} valores de sky_state para hoy')

    # Buscar el valor más reciente (pasado) o el primero del futuro
    closest_past_sky = None
    closest_future_sky = None

    for sky in sky_states:
        time_str = sky.get('time', '')
        if time_str:
            # Manejar diferentes formatos de timezone (+01, +02, etc.)
            # Convertir "+01" a "+01:00", "+02" a "+02:00", etc.
            time_str_normalized = time_str
            if '+' in time_str and ':' not in time_str.split('+')[1]:
                # Si tiene + pero no tiene : después del offset, añadir :00
                parts = time_str.rsplit('+', 1)
                time_str_normalized = f"{parts[0]}+{parts[1]}:00"
            elif '-' in time_str and time_str.count('-') > 2:  # Para offsets negativos
                parts = time_str.rsplit('-', 1)
                if ':' not in parts[1]:
                    time_str_normalized = f"{parts[0]}-{parts[1]}:00"

            try:
                sky_time = datetime.fromisoformat(time_str_normalized)
                # Asegurar que ambos datetimes son aware y comparables
                if sky_time.tzinfo is None:
                    continue

                if sky_time <= now_spanish:
                    # Es del pasado, guardar el más reciente
                    closest_past_sky = sky
                elif closest_future_sky is None:
                    # Es del futuro, guardar solo el primero
                    closest_future_sky = sky
            except (ValueError, AttributeError) as e:
                logging.warning(f"Error al parsear tiempo del cielo '{time_str}': {e}")
                continue

    # Usar el valor del pasado si existe, si no, el del futuro
    selected_sky = closest_past_sky if closest_past_sky else closest_future_sky
    if selected_sky:
        current_sky = selected_sky.get('value', 'N/A')

        # Determinar si es de noche usando datos solares reales o fallback a horas fijas
        is_night = False
        if solar_info and solar_info.get('success'):
            sunrise = solar_info.get('sunrise')
            sunset = solar_info.get('sunset')
            # Es de noche si la hora actual es antes del amanecer o después del atardecer
            is_night = now_spanish < sunrise or now_spanish >= sunset
            logging.info(f'  DEBUG: Usando datos solares - Amanecer: {sunrise.strftime("%H:%M")}, Atardecer: {sunset.strftime("%H:%M")}, Es noche: {is_night}')
        else:
            # Fallback: usar horas fijas si no hay datos solares
            current_hour = now_spanish.hour
            is_night = current_hour >= 20 or current_hour < 8
            logging.info(f'  DEBUG: Usando horas fijas (fallback) - Hora: {current_hour}, Es noche: {is_night}')

        # Obtener icono SVG apropiado para TRMNL
        current_icon = map_weather_to_svg_icon(current_sky, is_night, icons_base_url)

        logging.info(f'  DEBUG: Sky seleccionado - valor: {current_sky}, hora: {selected_sky.get("time", "N/A")}, noche: {is_night}')
        logging.info(f'  DEBUG: Icono SVG: {current_icon}')
    else:
        logging.warning(f'  DEBUG: No se encontró ningún valor de sky_state válido')

    # Encontrar la temperatura más cercana a la hora actual
    current_temperature = None
    temperature_data = today_data.get('temperature', [])

    logging.info(f'  DEBUG: Encontrados {len(temperature_data)} valores de temperatura para hoy')

    # Buscar el valor más reciente (pasado) o el primero del futuro
    closest_past_temp = None
    closest_future_temp = None

    for temp in temperature_data:
        time_str = temp.get('time', '')
        if time_str:
            # Normalizar timezone igual que para sky_state
            time_str_normalized = time_str
            if '+' in time_str and ':' not in time_str.split('+')[1]:
                parts = time_str.rsplit('+', 1)
                time_str_normalized = f"{parts[0]}+{parts[1]}:00"
            elif '-' in time_str and time_str.count('-') > 2:
                parts = time_str.rsplit('-', 1)
                if ':' not in parts[1]:
                    time_str_normalized = f"{parts[0]}-{parts[1]}:00"

            try:
                temp_time = datetime.fromisoformat(time_str_normalized)
                if temp_time.tzinfo is None:
                    continue

                if temp_time <= now_spanish:
                    closest_past_temp = temp
                elif closest_future_temp is None:
                    closest_future_temp = temp
            except (ValueError, AttributeError) as e:
                logging.warning(f"Error al parsear tiempo de temperatura '{time_str}': {e}")
                continue

    # Usar el valor del pasado si existe, si no, el del futuro
    selected_temp = closest_past_temp if closest_past_temp else closest_future_temp
    if selected_temp:
        current_temperature = round(selected_temp.get('value', 0), 1)
        logging.info(f'  DEBUG: Temperatura seleccionada - valor: {current_temperature}°C, hora: {selected_temp.get("time", "N/A")}')
    else:
        logging.warning(f'  DEBUG: No se encontró ningún valor de temperatura válido')

    # Verificar si habrá lluvia en las próximas 3 horas
    next_hours_rain = False
    three_hours_later = now_spanish + timedelta(hours=3)

    precipitation_data = today_data.get('precipitation', [])
    for precip in precipitation_data:
        time_str = precip.get('time', '')
        if time_str:
            # Normalizar timezone igual que para sky_state
            time_str_normalized = time_str
            if '+' in time_str and ':' not in time_str.split('+')[1]:
                parts = time_str.rsplit('+', 1)
                time_str_normalized = f"{parts[0]}+{parts[1]}:00"
            elif '-' in time_str and time_str.count('-') > 2:
                parts = time_str.rsplit('-', 1)
                if ':' not in parts[1]:
                    time_str_normalized = f"{parts[0]}-{parts[1]}:00"

            try:
                precip_time = datetime.fromisoformat(time_str_normalized)
                if now_spanish <= precip_time <= three_hours_later:
                    if precip.get('value', 0) > 0:
                        next_hours_rain = True
                        break
            except (ValueError, AttributeError) as e:
                logging.warning(f"Error al parsear tiempo de precipitación '{time_str}': {e}")
                continue

    # Calcular precipitación total del día
    total_precipitation_today = sum(p.get('value', 0) for p in precipitation_data)

    return {
        "current_sky": current_sky,
        "current_icon": current_icon,
        "current_temperature": current_temperature,
        "next_hours_rain": next_hours_rain,
        "total_precipitation_today": round(total_precipitation_today, 1)
    }

def is_holiday(festivos_list: list) -> bool:
    """
    Verifica si el día actual es festivo.

    Args:
        festivos_list: Lista de fechas festivas en formato "YYYY-MM-DD"

    Returns:
        True si hoy es festivo, False en caso contrario
    """
    if not festivos_list:
        return False

    spanish_tz = tz.gettz('Europe/Madrid')
    today = datetime.now(spanish_tz).date()
    today_str = today.strftime("%Y-%m-%d")

    # Verificar si hoy está en la lista de festivos
    for festivo in festivos_list:
        festivo = festivo.strip()
        if not festivo:
            continue

        # Soportar rangos de fechas (ej: "2025-12-22..2026-01-07")
        if '..' in festivo:
            try:
                start_str, end_str = festivo.split('..')
                start_date = datetime.strptime(start_str.strip(), "%Y-%m-%d").date()
                end_date = datetime.strptime(end_str.strip(), "%Y-%m-%d").date()
                if start_date <= today <= end_date:
                    return True
            except ValueError as e:
                logging.warning(f'Formato de rango de festivo inválido: {festivo} - {e}')
        else:
            # Fecha única
            if festivo == today_str:
                return True

    return False

def should_show_routes(festivos_list: list = None) -> bool:
    """
    Determina si las rutas deben mostrarse basándose en la hora española actual y festivos.

    Las rutas solo se muestran si:
    1. Estamos en uno de estos horarios (hora española):
       - Entre 7:30 AM y 9:00 AM
       - Entre 1:30 PM (13:30) y 2:45 PM (14:45)
    2. NO es un día festivo

    Args:
        festivos_list: Lista de fechas festivas en formato "YYYY-MM-DD"

    Returns:
        True si las rutas deben mostrarse, False en caso contrario
    """
    # Verificar si es festivo
    if festivos_list and is_holiday(festivos_list):
        logging.info('📅 Hoy es festivo - no se mostrarán rutas')
        return False

    spanish_tz = tz.gettz('Europe/Madrid')
    now_spanish = datetime.now(spanish_tz)

    # Obtener hora y minuto actual en hora española
    current_hour = now_spanish.hour
    current_minute = now_spanish.minute

    # Convertir a minutos desde medianoche para facilitar comparación
    current_time_minutes = current_hour * 60 + current_minute

    # Definir rangos de tiempo en minutos desde medianoche
    morning_start = 7 * 60 + 30   # 7:30 AM = 450 minutos
    morning_end = 9 * 60           # 9:00 AM = 540 minutos
    afternoon_start = 13 * 60 + 30 # 1:30 PM = 810 minutos
    afternoon_end = 14 * 60 + 45   # 2:45 PM = 885 minutos

    # Verificar si está en alguno de los rangos
    in_morning_window = morning_start <= current_time_minutes <= morning_end
    in_afternoon_window = afternoon_start <= current_time_minutes <= afternoon_end

    return in_morning_window or in_afternoon_window

def is_in_display_window() -> bool:
    """
    Determina si estamos en una ventana de tiempo donde el plugin se muestra en TRMNL.

    El plugin se muestra:
    - Lunes a Viernes: 6:00-8:30, 13:00-14:30, 17:30-23:30
    - Domingos: 17:30-23:30
    - No se muestra los sábados

    Returns:
        True si estamos en una ventana de visualización, False en caso contrario
    """
    spanish_tz = tz.gettz('Europe/Madrid')
    now_spanish = datetime.now(spanish_tz)

    current_hour = now_spanish.hour
    current_minute = now_spanish.minute
    current_weekday = now_spanish.weekday()  # 0=Lunes, 6=Domingo

    # Convertir a minutos desde medianoche
    current_time_minutes = current_hour * 60 + current_minute

    # Definir ventanas de tiempo en minutos desde medianoche
    morning_start = 6 * 60           # 6:00 AM = 360 minutos
    morning_end = 8 * 60 + 30        # 8:30 AM = 510 minutos
    noon_start = 13 * 60             # 13:00 PM = 780 minutos
    noon_end = 14 * 60 + 30          # 14:30 PM = 870 minutos
    evening_start = 17 * 60 + 30     # 17:30 PM = 1050 minutos
    evening_end = 23 * 60 + 30       # 23:30 PM = 1410 minutos

    # Verificar ventanas de tiempo
    in_morning_window = morning_start <= current_time_minutes <= morning_end
    in_noon_window = noon_start <= current_time_minutes <= noon_end
    in_evening_window = evening_start <= current_time_minutes <= evening_end

    # Domingos (6): solo ventana de tarde
    if current_weekday == 6:
        return in_evening_window

    # Sábados (5): no se muestra
    if current_weekday == 5:
        return False

    # Lunes a Viernes (0-4): todas las ventanas
    return in_morning_window or in_noon_window or in_evening_window

def format_duration_as_minutes(duration_str: str) -> str:
    """
    Convierte una duración en formato "XXXs" a "XX min".

    Args:
        duration_str: Duración en formato "XXXs" (ej: "1234s")

    Returns:
        Duración formateada (ej: "21 min")
    """
    if isinstance(duration_str, str) and duration_str.endswith('s'):
        duration_seconds = int(duration_str.rstrip('s'))
        duration_minutes = round(duration_seconds / 60)
        return f"{duration_minutes} min"
    return "N/A"

def send_visibility_only_to_webhook(show_routes: bool, webhook_url: str,
                                   weather_casa: dict = None, weather_colegio: dict = None) -> dict:
    """
    Envía solo el estado de visibilidad al webhook de TRMNL sin datos de rutas.
    Se usa cuando estamos fuera de la ventana de tiempo activa.

    Args:
        show_routes: Si las rutas deben mostrarse o no
        weather_casa: Datos meteorológicos de casa (opcional)
        weather_colegio: Datos meteorológicos del colegio (opcional)
        webhook_url: URL del webhook de TRMNL donde enviar los datos

    Returns:
        Resultado del envío al webhook
    """
    merge_vars = {
        "show_routes": show_routes,
        "timestamp": datetime.now(tz.UTC).isoformat()
    }

    # Añadir datos meteorológicos si están disponibles
    if weather_casa:
        merge_vars.update({
            "weather_casa_sky": weather_casa.get('current_sky', 'N/A'),
            "weather_casa_icon": weather_casa.get('current_icon', ''),
            "weather_casa_temperature": weather_casa.get('current_temperature'),
            "weather_casa_rain_3h": weather_casa.get('next_hours_rain', False),
            "weather_casa_precipitation_today": weather_casa.get('total_precipitation_today', 0)
        })

    if weather_colegio:
        merge_vars.update({
            "weather_colegio_sky": weather_colegio.get('current_sky', 'N/A'),
            "weather_colegio_icon": weather_colegio.get('current_icon', ''),
            "weather_colegio_temperature": weather_colegio.get('current_temperature'),
            "weather_colegio_rain_3h": weather_colegio.get('next_hours_rain', False),
            "weather_colegio_precipitation_today": weather_colegio.get('total_precipitation_today', 0)
        })

    payload = {
        "merge_variables": merge_vars
    }

    # Log del payload completo para debugging
    logging.info('📋 Payload JSON enviado a TRMNL:')
    logging.info(json.dumps(payload, indent=2, ensure_ascii=False))

    try:
        headers = {"Content-Type": "application/json"}
        response = requests.post(webhook_url, json=payload, headers=headers, timeout=10)
        response.raise_for_status()

        logging.info(f'✓ Estado de visibilidad enviado al webhook TRMNL')
        logging.info(f'  - Mostrar rutas: {show_routes}')
        if weather_casa:
            logging.info(f'  - Tiempo casa: {weather_casa.get("current_sky", "N/A")}')
        if weather_colegio:
            logging.info(f'  - Tiempo colegio: {weather_colegio.get("current_sky", "N/A")}')

        return {
            "success": True,
            "status_code": response.status_code,
            "response": response.text
        }
    except requests.exceptions.RequestException as e:
        logging.error(f'✗ Error al enviar al webhook TRMNL: {str(e)}')
        return {
            "success": False,
            "error": str(e),
            "status_code": getattr(e.response, 'status_code', None) if hasattr(e, 'response') else None
        }

def send_to_trmnl_webhook(route_directo: dict, route_hospital: dict, departure_time: datetime,
                          webhook_url: str, show_routes: bool, weather_casa: dict = None, weather_colegio: dict = None) -> dict:
    """
    Envía los datos de las rutas al webhook de TRMNL en formato merge_variables.

    Args:
        route_directo: Datos de la ruta directa (Casa → Colegio)
        route_hospital: Datos de la ruta con hospital (Casa → Hospital → Colegio)
        departure_time: Hora de salida
        weather_casa: Datos meteorológicos de casa (opcional)
        weather_colegio: Datos meteorológicos del colegio (opcional)
        webhook_url: URL del webhook de TRMNL donde enviar los datos
        show_routes: Si las rutas deben mostrarse en la pantalla TRMNL

    Returns:
        Resultado del envío al webhook
    """
    spanish_tz = tz.gettz('Europe/Madrid')
    departure_time_spanish = departure_time.astimezone(spanish_tz)

    # Inicializar merge_variables
    merge_vars = {
        "departure_time": departure_time_spanish.strftime("%Y-%m-%d %H:%M:%S %Z"),
        "timestamp": datetime.now(tz.UTC).isoformat(),
        "show_routes": show_routes,
        "eta_directo": "N/A",
        "eta_con_hospital": "N/A"
    }

    # Extraer duración de ruta directa
    if route_directo and route_directo.get('success'):
        data = route_directo.get('data', {})
        if 'routes' in data and len(data['routes']) > 0:
            route = data['routes'][0]
            if 'duration' in route:
                merge_vars['eta_directo'] = format_duration_as_minutes(route['duration'])
                merge_vars['eta_directo_seconds'] = route['duration']
            if 'distanceMeters' in route:
                merge_vars['distance_directo_km'] = round(route['distanceMeters'] / 1000, 2)

    # Extraer duración de ruta con hospital
    if route_hospital and route_hospital.get('success'):
        data = route_hospital.get('data', {})
        if 'routes' in data and len(data['routes']) > 0:
            route = data['routes'][0]
            if 'duration' in route:
                merge_vars['eta_con_hospital'] = format_duration_as_minutes(route['duration'])
                merge_vars['eta_con_hospital_seconds'] = route['duration']
            if 'distanceMeters' in route:
                merge_vars['distance_hospital_km'] = round(route['distanceMeters'] / 1000, 2)

    # Añadir datos meteorológicos si están disponibles
    if weather_casa:
        merge_vars.update({
            "weather_casa_sky": weather_casa.get('current_sky', 'N/A'),
            "weather_casa_icon": weather_casa.get('current_icon', ''),
            "weather_casa_temperature": weather_casa.get('current_temperature'),
            "weather_casa_rain_3h": weather_casa.get('next_hours_rain', False),
            "weather_casa_precipitation_today": weather_casa.get('total_precipitation_today', 0)
        })

    if weather_colegio:
        merge_vars.update({
            "weather_colegio_sky": weather_colegio.get('current_sky', 'N/A'),
            "weather_colegio_icon": weather_colegio.get('current_icon', ''),
            "weather_colegio_temperature": weather_colegio.get('current_temperature'),
            "weather_colegio_rain_3h": weather_colegio.get('next_hours_rain', False),
            "weather_colegio_precipitation_today": weather_colegio.get('total_precipitation_today', 0)
        })

    # Preparar payload en formato TRMNL
    payload = {
        "merge_variables": merge_vars
    }

    # Log del payload completo para debugging
    logging.info('📋 Payload JSON completo enviado a TRMNL:')
    logging.info(json.dumps(payload, indent=2, ensure_ascii=False))

    try:
        headers = {
            "Content-Type": "application/json"
        }
        response = requests.post(webhook_url, json=payload, headers=headers, timeout=10)
        response.raise_for_status()

        logging.info(f'✓ Datos enviados exitosamente al webhook TRMNL')
        logging.info(f'  - Mostrar rutas: {merge_vars["show_routes"]}')
        logging.info(f'  - ETA directo: {merge_vars["eta_directo"]}')
        logging.info(f'  - ETA con hospital: {merge_vars["eta_con_hospital"]}')
        if weather_casa:
            logging.info(f'  - Tiempo casa: {weather_casa.get("current_sky", "N/A")}')
        if weather_colegio:
            logging.info(f'  - Tiempo colegio: {weather_colegio.get("current_sky", "N/A")}')
        logging.info(f'Status code: {response.status_code}')

        return {
            "success": True,
            "status_code": response.status_code,
            "response": response.text
        }
    except requests.exceptions.RequestException as e:
        logging.error(f'✗ Error al enviar datos al webhook TRMNL: {str(e)}')
        return {
            "success": False,
            "error": str(e),
            "status_code": getattr(e.response, 'status_code', None) if hasattr(e, 'response') else None
        }

@app.timer_trigger(schedule="0 */15 6-8,13-14,17-23 * * 0,1-5", arg_name="myTimer", run_on_startup=False,
              use_monitor=False)
def google_maps_route_trigger(myTimer: func.TimerRequest) -> None:
    """
    Función de Azure que se ejecuta cada 15 minutos durante las ventanas de visualización.

    Horarios de ejecución (hora española):
    - Lunes a Viernes: 6:00-8:30, 13:00-14:30, 17:30-23:30
    - Domingos: 17:30-23:30
    - No se ejecuta los sábados

    Cron expression: "0 */15 6-8,13-14,17-23 * * 0,1-5"
    - 0,1-5 = Domingo(0), Lunes-Viernes(1-5)
    - Rangos horarios: 6-8, 13-14, 17-23 (UTC, ajusta para hora española)

    La función hace early exit si está fuera de las ventanas exactas de visualización.
    Para ETAs específicamente, verifica ventanas más estrictas (7:30-9:00, 13:30-14:45).
    """
    utc = tz.UTC
    spanish_tz = tz.gettz('Europe/Madrid')

    # Obtener hora actual
    current_time_utc = datetime.now(utc)
    current_time_spanish = current_time_utc.astimezone(spanish_tz)

    logging.info(f'Timer trigger ejecutado a las {current_time_utc.strftime("%Y-%m-%d %H:%M:%S")} UTC')
    logging.info(f'Hora española: {current_time_spanish.strftime("%Y-%m-%d %H:%M:%S %Z")}')

    # Early exit: verificar si estamos en ventana de visualización
    if not is_in_display_window():
        logging.info('⏸️ Fuera de ventanas de visualización (L-V: 6:00-8:30, 13:00-14:30, 17:30-23:30 | Dom: 17:30-23:30)')
        logging.info('⏸️ Saltando ejecución para ahorrar recursos')
        return

    logging.info('✓ Dentro de ventana de visualización - continuando ejecución')

    # Obtener configuración desde variables de entorno
    config = get_env_config()

    # Validar configuración crítica
    if not config['webhook_url']:
        logging.error('TRMNL_WEBHOOK_URL no está configurada. Por favor, configúrela en las variables de entorno.')
        return

    if (config['coords_casa']['latitude'] == 0 or config['coords_casa']['longitude'] == 0 or
        config['coords_colegio']['latitude'] == 0 or config['coords_colegio']['longitude'] == 0 or
        config['coords_hospital']['latitude'] == 0 or config['coords_hospital']['longitude'] == 0):
        logging.error('Coordenadas no configuradas correctamente. Revisa todas las variables: COORDS_CASA_LAT, COORDS_CASA_LON, COORDS_COLEGIO_LAT, COORDS_COLEGIO_LON, COORDS_HOSPITAL_LAT, COORDS_HOSPITAL_LON')
        return

    # Obtener API key de MeteoGalicia
    meteogalicia_api_key = os.environ.get('METEOGALICIA_API_KEY')

    # Obtener URL base para iconos meteorológicos (puede ser blob storage o svgrepo por defecto)
    weather_icons_base_url = os.environ.get('WEATHER_ICONS_BASE_URL')
    if weather_icons_base_url:
        logging.info(f'🎨 Usando iconos meteorológicos desde: {weather_icons_base_url}')
    else:
        logging.info('🎨 Usando iconos meteorológicos desde svgrepo.com (por defecto)')

    # Obtener predicción meteorológica (siempre, no solo en ventanas de tiempo)
    weather_casa_summary = None
    weather_colegio_summary = None

    if meteogalicia_api_key and meteogalicia_api_key != 'your-meteogalicia-api-key-here':
        logging.info('🌤️ Obteniendo predicción meteorológica de MeteoGalicia...')

        # Obtener información solar (amanecer/atardecer) para iconos día/noche precisos
        logging.info('☀️ Obteniendo información solar (amanecer/atardecer)')
        solar_data = get_solar_info(
            latitude=config['coords_casa']['latitude'],
            longitude=config['coords_casa']['longitude'],
            api_key=meteogalicia_api_key
        )

        solar_info = None
        if solar_data['success']:
            solar_info = parse_solar_info(solar_data)
            if solar_info.get('success'):
                logging.info(f'  ✓ Amanecer: {solar_info["sunrise"].strftime("%H:%M")}')
                logging.info(f'  ✓ Atardecer: {solar_info["sunset"].strftime("%H:%M")}')
                logging.info(f'  ✓ Duración: {solar_info.get("duration", "N/A")}')
            else:
                logging.warning(f'  ⚠ Error al parsear datos solares: {solar_info.get("error")}')
                solar_info = None
        else:
            logging.warning(f'  ⚠ Error al obtener datos solares: {solar_data.get("error")}')

        # Determinar si mostrar el tiempo de hoy o mañana (a partir de las 19:00)
        spanish_tz = tz.gettz('Europe/Madrid')
        now_spanish = datetime.now(spanish_tz)
        current_hour = now_spanish.hour

        weather_target_date = None  # None = hoy
        if current_hour >= 19:
            # A partir de las 19:00, verificar si mañana hay colegio
            tomorrow = now_spanish + timedelta(days=1)
            tomorrow_weekday = tomorrow.weekday()  # 0=Lunes, 6=Domingo
            tomorrow_date_str = tomorrow.strftime("%Y-%m-%d")

            # Verificar si mañana es fin de semana (sábado=5, domingo=6)
            is_weekend = tomorrow_weekday in [5, 6]

            # Verificar si mañana es festivo
            festivos_list = config.get('festivos', [])
            # Crear una fecha temporal para is_holiday usando mañana
            original_now = datetime.now(spanish_tz)
            # is_holiday usa datetime.now(), necesitamos hacer un workaround
            is_tomorrow_holiday = False
            if festivos_list:
                for festivo in festivos_list:
                    if '..' in festivo:
                        # Rango de fechas
                        start_str, end_str = festivo.split('..')
                        start_date = datetime.strptime(start_str.strip(), '%Y-%m-%d').date()
                        end_date = datetime.strptime(end_str.strip(), '%Y-%m-%d').date()
                        if start_date <= tomorrow.date() <= end_date:
                            is_tomorrow_holiday = True
                            break
                    else:
                        # Fecha única
                        festivo_date = datetime.strptime(festivo.strip(), '%Y-%m-%d').date()
                        if tomorrow.date() == festivo_date:
                            is_tomorrow_holiday = True
                            break

            # Solo mostrar tiempo de mañana si hay colegio (no es fin de semana ni festivo)
            if not is_weekend and not is_tomorrow_holiday:
                weather_target_date = tomorrow_date_str
                logging.info(f'🌙 Hora >= 19:00 y mañana HAY colegio - Mostrando predicción para MAÑANA ({weather_target_date})')
            else:
                if is_weekend:
                    logging.info(f'🌙 Hora >= 19:00 pero mañana es FIN DE SEMANA - Mostrando predicción para HOY')
                else:
                    logging.info(f'🌙 Hora >= 19:00 pero mañana es FESTIVO - Mostrando predicción para HOY')
        else:
            logging.info(f'☀️ Hora < 19:00 - Mostrando predicción para HOY')

        # Obtener predicción para casa
        logging.info('📍 Predicción para Casa')
        forecast_casa = get_meteogalicia_forecast(
            latitude=config['coords_casa']['latitude'],
            longitude=config['coords_casa']['longitude'],
            api_key=meteogalicia_api_key
        )

        if forecast_casa['success']:
            weather_info_casa = parse_weather_forecast(forecast_casa, 'casa')
            if weather_info_casa.get('success'):
                weather_casa_summary = get_current_weather_summary(weather_info_casa, weather_icons_base_url, solar_info, weather_target_date)
                logging.info(f'  ✓ Tiempo actual: {weather_casa_summary.get("current_sky", "N/A")}')
                logging.info(f'  ✓ Precipitación: {weather_casa_summary.get("total_precipitation_today", 0)} mm')
            else:
                logging.error(f'  ✗ Error al parsear datos: {weather_info_casa.get("error")}')
        else:
            logging.error(f'  ✗ Error al obtener predicción: {forecast_casa.get("error")}')

        # Obtener predicción para colegio
        logging.info('📍 Predicción para Colegio')
        forecast_colegio = get_meteogalicia_forecast(
            latitude=config['coords_colegio']['latitude'],
            longitude=config['coords_colegio']['longitude'],
            api_key=meteogalicia_api_key
        )

        if forecast_colegio['success']:
            weather_info_colegio = parse_weather_forecast(forecast_colegio, 'colegio')
            if weather_info_colegio.get('success'):
                weather_colegio_summary = get_current_weather_summary(weather_info_colegio, weather_icons_base_url, solar_info, weather_target_date)
                logging.info(f'  ✓ Tiempo actual: {weather_colegio_summary.get("current_sky", "N/A")}')
                logging.info(f'  ✓ Precipitación: {weather_colegio_summary.get("total_precipitation_today", 0)} mm')
            else:
                logging.error(f'  ✗ Error al parsear datos: {weather_info_colegio.get("error")}')
        else:
            logging.error(f'  ✗ Error al obtener predicción: {forecast_colegio.get("error")}')
    else:
        logging.warning('METEOGALICIA_API_KEY no está configurada. No se obtendrá información meteorológica.')
    # Validar y loggear festivos configurados
    if config['festivos']:
        valid_festivos_count = len([f.strip() for f in config['festivos'] if f.strip()])
        logging.info(f'📅 Festivos configurados: {valid_festivos_count} entradas')
    else:
        logging.info('📅 No hay festivos configurados')

    # Verificar si estamos en la ventana de tiempo para mostrar rutas (incluye check de festivos)
    show_routes = should_show_routes(config['festivos'])
    logging.info(f'📊 Estado: Mostrar rutas = {show_routes}')

    if not show_routes:
        # Fuera de la ventana de tiempo o es festivo: solo actualizamos visibilidad
        logging.info('⏰ Fuera de la ventana de tiempo activa (7:30-9:00 / 13:30-14:45) o es festivo')
        logging.info('📤 Enviando solo estado de visibilidad al webhook...')
        webhook_result = send_visibility_only_to_webhook(
            show_routes=False,
            webhook_url=config['webhook_url'],
            weather_casa=weather_casa_summary,
            weather_colegio=weather_colegio_summary
        )

        if webhook_result['success']:
            logging.info(f'✓ Estado actualizado exitosamente')
        else:
            logging.error(f'✗ Error al actualizar estado: {webhook_result.get("error", "Unknown error")}')
        return

    # Dentro de la ventana de tiempo: obtener rutas de Google Maps
    logging.info('✅ Dentro de la ventana de tiempo activa - obteniendo rutas actualizadas')

    # Calcular tiempo de salida (15 minutos después)
    departure_time = calculate_departure_time()
    departure_time_spanish = departure_time.astimezone(spanish_tz)

    logging.info(f'🚗 Calculando ruta para salida a las {departure_time_spanish.strftime("%H:%M:%S")} hora española')

    # Obtener API key desde configuración
    api_key = os.environ.get('GOOGLE_MAPS_API_KEY')

    if not api_key or api_key == 'your-google-maps-api-key-here':
        logging.error('GOOGLE_MAPS_API_KEY no está configurada. Por favor, configúrela en las variables de entorno.')
        return

    # Obtener RUTA 1: Casa → Colegio (directo)
    logging.info('📍 Obteniendo ruta directa: Casa → Colegio')
    route_directo = get_google_maps_route(
        origin=config['coords_casa'],
        destination=config['coords_colegio'],
        departure_time=departure_time,
        api_key=api_key
    )

    if route_directo['success']:
        data = route_directo['data']
        if 'routes' in data and len(data['routes']) > 0:
            route = data['routes'][0]
            if 'duration' in route:
                logging.info(f'  ✓ Duración estimada (directo): {route["duration"]}')
            if 'distanceMeters' in route:
                logging.info(f'  ✓ Distancia: {route["distanceMeters"] / 1000:.2f} km')
    else:
        logging.error(f'  ✗ Error al obtener ruta directa: {route_directo.get("error")}')

    # Obtener RUTA 2: Casa → Hospital → Colegio
    logging.info('📍 Obteniendo ruta con hospital: Casa → Hospital → Colegio')
    route_hospital = get_google_maps_route(
        origin=config['coords_casa'],
        destination=config['coords_colegio'],
        departure_time=departure_time,
        api_key=api_key,
        intermediates=[config['coords_hospital']]
    )

    if route_hospital['success']:
        data = route_hospital['data']
        if 'routes' in data and len(data['routes']) > 0:
            route = data['routes'][0]
            if 'duration' in route:
                logging.info(f'  ✓ Duración estimada (con hospital): {route["duration"]}')
            if 'distanceMeters' in route:
                logging.info(f'  ✓ Distancia: {route["distanceMeters"] / 1000:.2f} km')
    else:
        logging.error(f'  ✗ Error al obtener ruta con hospital: {route_hospital.get("error")}')

    # Enviar datos completos al webhook de TRMNL (aunque una ruta falle, enviamos lo que tengamos)
    logging.info('📤 Enviando datos completos al webhook de TRMNL...')
    webhook_result = send_to_trmnl_webhook(
        route_directo,
        route_hospital,
        departure_time,
        config['webhook_url'],
        weather_casa=weather_casa_summary,
        weather_colegio=weather_colegio_summary,
        show_routes
    )

    if webhook_result['success']:
        logging.info(f'✓ Proceso completado exitosamente')
        logging.info(f'Respuesta del webhook: {webhook_result.get("response", "N/A")}')
    else:
        logging.error(f'✗ Error al enviar al webhook: {webhook_result.get("error", "Unknown error")}')
