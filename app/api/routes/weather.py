from fastapi import APIRouter

from app.core.errors.base import AppError
from app.services.controller import Controller

router = APIRouter(prefix="/weather", tags=["weather"])


@router.get("/forecast")
def get_weather_forecast(latitude: float, longitude: float):
    """
    Fetch weather forecast data for the given coordinates.
    """
    controller = Controller()
    try:
        weather_data = controller.get_weather(latitude, longitude)
        return weather_data
    except Exception as e:
        raise AppError(str(e), status_code=500)