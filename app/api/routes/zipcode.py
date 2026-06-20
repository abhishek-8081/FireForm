from fastapi import APIRouter

from app.core.errors.base import AppError
from app.services.controller import Controller

router = APIRouter(prefix="/zipcode", tags=["zipcode"])

@router.get("/postal-code")
def get_postal_code(
    country: str,
    postal_code: str,
):
    """
    Fetch data for the given postal code.

    Query params:
      - country: required string
      - postal_code: required string
    """
    controller = Controller()
    try:
        return controller.get_postal_code(country, postal_code)
    except Exception as e:
        raise AppError(str(e), status_code=500)

@router.get("/location")
def get_location(
    country: str,
    city: str,
):
    """
    Fetch data for the given location.

    Query params:
      - country: required string
      - city: required string
    """
    controller = Controller()
    try:
        return controller.get_location(country, city)
    except Exception as e:
        raise AppError(str(e), status_code=500)
