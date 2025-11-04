import azure.functions as func
import logging
import json
import os
import requests
from datetime import datetime, timedelta
from dateutil import tz

app = func.FunctionApp()

# Configuración de la ruta
ROUTE_CONFIG = {
    "origin": {
        "location": {
            "latLng": {
                "latitude": 42.171842,
                "longitude": -8.628590
            }
        }
    },
    "destination": {
        "location": {
            "latLng": {
                "latitude": 42.210826,
                "longitude": -8.692426
            }
        }
    },
    "travelMode": "DRIVE",
    "routingPreference": "TRAFFIC_AWARE_OPTIMAL"
}

def get_google_maps_route(departure_time: datetime, api_key: str) -> dict:
    """
    Obtiene la ruta de Google Maps para un tiempo de salida específico.

    Args:
        departure_time: Hora de salida deseada
        api_key: Clave de API de Google Maps

    Returns:
        Respuesta de la API de Google Maps
    """
    url = "https://routes.googleapis.com/directions/v2:computeRoutes"

    # Formatear el tiempo de salida en formato ISO 8601
    departure_time_str = departure_time.strftime("%Y-%m-%dT%H:%M:%SZ")

    # Preparar el payload
    payload = ROUTE_CONFIG.copy()
    payload["departureTime"] = departure_time_str

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

@app.timer_trigger(schedule="0 50 6,12 * * *", arg_name="myTimer", run_on_startup=False,
              use_monitor=False)
def google_maps_route_trigger(myTimer: func.TimerRequest) -> None:
    """
    Función de Azure que se ejecuta dos veces al día para obtener información de ruta.

    Horarios de ejecución (UTC):
    - 6:50 AM UTC (7:50 AM hora española en invierno / 8:50 AM en verano)
    - 12:50 PM UTC (1:50 PM hora española en invierno / 2:50 PM en verano)

    Nota: Para horario de verano español (CEST = UTC+2), los triggers serían:
    - 5:50 AM UTC para obtener ruta de 8:05 AM CEST
    - 11:50 AM UTC para obtener ruta de 2:05 PM CEST
    """
    utc = tz.UTC
    spanish_tz = tz.gettz('Europe/Madrid')

    # Obtener hora actual
    current_time_utc = datetime.now(utc)
    current_time_spanish = current_time_utc.astimezone(spanish_tz)

    logging.info(f'Timer trigger ejecutado a las {current_time_utc.strftime("%Y-%m-%d %H:%M:%S")} UTC')
    logging.info(f'Hora española: {current_time_spanish.strftime("%Y-%m-%d %H:%M:%S %Z")}')

    # Calcular tiempo de salida (15 minutos después)
    departure_time = calculate_departure_time()
    departure_time_spanish = departure_time.astimezone(spanish_tz)

    logging.info(f'Calculando ruta para salida a las {departure_time_spanish.strftime("%H:%M:%S")} hora española')

    # Obtener API key desde configuración
    api_key = os.environ.get('GOOGLE_MAPS_API_KEY')

    if not api_key or api_key == 'your-google-maps-api-key-here':
        logging.error('GOOGLE_MAPS_API_KEY no está configurada. Por favor, configúrela en las variables de entorno.')
        return

    # Obtener la ruta
    result = get_google_maps_route(departure_time, api_key)

    if result['success']:
        logging.info('✓ Ruta obtenida exitosamente')
        data = result['data']

        # Extraer información útil si está disponible
        if 'routes' in data and len(data['routes']) > 0:
            route = data['routes'][0]

            if 'duration' in route:
                duration = route['duration']
                logging.info(f'Duración estimada: {duration}')

            if 'distanceMeters' in route:
                distance_km = route['distanceMeters'] / 1000
                logging.info(f'Distancia: {distance_km:.2f} km')

            # Log completo de la respuesta para debugging
            logging.info(f'Respuesta completa: {json.dumps(data, indent=2)}')
        else:
            logging.warning('No se encontraron rutas en la respuesta')
    else:
        logging.error(f'✗ Error al obtener la ruta: {result["error"]}')
        if result['status_code']:
            logging.error(f'Código de estado HTTP: {result["status_code"]}')
