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

def send_visibility_only_to_webhook(show_routes: bool, webhook_url: str) -> dict:
    """
    Envía solo el estado de visibilidad al webhook de TRMNL sin datos de rutas.
    Se usa cuando estamos fuera de la ventana de tiempo activa.

    Args:
        show_routes: Si las rutas deben mostrarse o no

    Returns:
        Resultado del envío al webhook
    """
    payload = {
        "merge_variables": {
            "show_routes": show_routes,
            "timestamp": datetime.now(tz.UTC).isoformat()
        }
    }

    try:
        headers = {"Content-Type": "application/json"}
        response = requests.post(webhook_url, json=payload, headers=headers, timeout=10)
        response.raise_for_status()

        logging.info(f'✓ Estado de visibilidad enviado al webhook TRMNL')
        logging.info(f'  - Mostrar rutas: {show_routes}')

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

def send_to_trmnl_webhook(route_directo: dict, route_hospital: dict, departure_time: datetime, webhook_url: str) -> dict:
    """
    Envía los datos de las rutas al webhook de TRMNL en formato merge_variables.

    Args:
        route_directo: Datos de la ruta directa (Casa → Colegio)
        route_hospital: Datos de la ruta con hospital (Casa → Hospital → Colegio)
        departure_time: Hora de salida

    Returns:
        Resultado del envío al webhook
    """
    spanish_tz = tz.gettz('Europe/Madrid')
    departure_time_spanish = departure_time.astimezone(spanish_tz)

    # Determinar si se deben mostrar las rutas
    show_routes = should_show_routes()

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

    # Preparar payload en formato TRMNL
    payload = {
        "merge_variables": merge_vars
    }

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

@app.timer_trigger(schedule="0 */15 6-9,12-15 * * 1-5", arg_name="myTimer", run_on_startup=False,
              use_monitor=False)
def google_maps_route_trigger(myTimer: func.TimerRequest) -> None:
    """
    Función de Azure que se ejecuta cada 15 minutos durante las horas activas.

    Horarios de ejecución (UTC):
    - Cada 15 minutos entre las 6:00-9:59 UTC (cubre 7:30-9:00 hora española)
    - Cada 15 minutos entre las 12:00-15:59 UTC (cubre 13:30-14:45 hora española)
    - Solo de lunes a viernes (1-5)

    La función verifica internamente si está en la ventana de tiempo correcta
    (7:30-9:00 o 13:30-14:45 hora española) antes de hacer las llamadas a Google Maps.
    Fuera de esas ventanas, solo actualiza show_routes=false.
    """
    utc = tz.UTC
    spanish_tz = tz.gettz('Europe/Madrid')

    # Obtener hora actual
    current_time_utc = datetime.now(utc)
    current_time_spanish = current_time_utc.astimezone(spanish_tz)

    logging.info(f'Timer trigger ejecutado a las {current_time_utc.strftime("%Y-%m-%d %H:%M:%S")} UTC')
    logging.info(f'Hora española: {current_time_spanish.strftime("%Y-%m-%d %H:%M:%S %Z")}')

    # Obtener configuración desde variables de entorno
    config = get_env_config()

    # Validar configuración crítica
    if not config['webhook_url']:
        logging.error('TRMNL_WEBHOOK_URL no está configurada. Por favor, configúrela en las variables de entorno.')
        return

    if config['coords_casa']['latitude'] == 0 or config['coords_colegio']['latitude'] == 0:
        logging.error('Coordenadas no configuradas correctamente. Revisa COORDS_CASA_LAT, COORDS_CASA_LON, etc.')
        return

    # Verificar si estamos en la ventana de tiempo para mostrar rutas (incluye check de festivos)
    show_routes = should_show_routes(config['festivos'])
    logging.info(f'📊 Estado: Mostrar rutas = {show_routes}')

    if not show_routes:
        # Fuera de la ventana de tiempo o es festivo: solo actualizamos visibilidad
        logging.info('⏰ Fuera de la ventana de tiempo activa (7:30-9:00 / 13:30-14:45) o es festivo')
        logging.info('📤 Enviando solo estado de visibilidad al webhook...')
        webhook_result = send_visibility_only_to_webhook(show_routes=False, webhook_url=config['webhook_url'])

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
    webhook_result = send_to_trmnl_webhook(route_directo, route_hospital, departure_time, config['webhook_url'])

    if webhook_result['success']:
        logging.info(f'✓ Proceso completado exitosamente')
        logging.info(f'Respuesta del webhook: {webhook_result.get("response", "N/A")}')
    else:
        logging.error(f'✗ Error al enviar al webhook: {webhook_result.get("error", "Unknown error")}')
