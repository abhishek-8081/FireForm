from fastapi import APIRouter

from app.core.errors.base import AppError
from app.services.controller import Controller

router = APIRouter(prefix="/weather", tags=["weather"])

ALL_HOURLY_FIELDS = [
    "temperature_2m",
    "relative_humidity_2m",
    "rain",
    "apparent_temperature",
    "precipitation_probability",
    "precipitation",
    "wind_direction_10m",
    "wind_speed_10m",
    "soil_temperature_0cm",
    "uv_index",
]


@router.get("/forecast")
def get_weather_forecast(
    latitude: float,
    longitude: float,
    fields: str | None = None,
):
    """
    Fetch weather forecast data for the given coordinates.

    Query params:
      - latitude, longitude: required floats
      - fields: optional comma-separated list of hourly variables to include.
                Defaults to all supported fields when omitted.
    """
    controller = Controller()
    try:
        requested = [f.strip() for f in fields.split(",") if f.strip()] if fields else []
        weather_data = controller.get_weather(latitude, longitude, hourly_fields=requested)
        return weather_data
    except Exception as e:
        raise AppError(str(e), status_code=500)