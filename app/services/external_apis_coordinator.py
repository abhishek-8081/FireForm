from app.services.external_apis.weather_api import WeatherAPI

class ExternalAPIsCoordinator:
    def __init__(self):
        self.weather_api = WeatherAPI()
    
    def get_weather(self, latitude: float, longitude: float, start_date: str, end_date: str, hourly_fields: list[str] | None = None):
        return self.weather_api.get_weather(latitude, longitude, start_date, end_date, hourly_fields)
