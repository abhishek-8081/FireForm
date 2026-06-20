from app.services.external_apis.zipcode_api import ZipCodeAPI
from app.services.external_apis.weather_api import WeatherAPI

class ExternalAPIsCoordinator:
    def __init__(self):
        self.weather_api = WeatherAPI()
        self.zipcode_api = ZipCodeAPI()
    
    def get_weather(self, latitude: float, longitude: float, start_date: str, end_date: str, hourly_fields: list[str] | None = None):
        return self.weather_api.get_weather(latitude, longitude, start_date, end_date, hourly_fields)

    def get_postal_code(self, country: str, postal_code: str):
        return self.zipcode_api.get_postal_code(country, postal_code)
        
    def get_location(self, country: str, city: str):
        return self.zipcode_api.get_location(country, city)