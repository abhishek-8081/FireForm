from app.services.file_manipulator import FileManipulator
from app.services.external_apis_coordinator import ExternalAPIsCoordinator


class Controller:
    def __init__(self):
        self.file_manipulator = FileManipulator()
        self.external_apis_coordinator = ExternalAPIsCoordinator()

    def fill_form(self, user_input: str, fields: list, pdf_form_path: str, model: str = None):
        return self.file_manipulator.fill_form(user_input, fields, pdf_form_path, model=model)
    
    def prepare_fillable(self, pdf_path: str):
        return self.file_manipulator.prepare_fillable(pdf_path)

    def get_weather(self, latitude: float, longitude: float):
        return self.external_apis_coordinator.get_weather(latitude, longitude)