import pgeocode
import numpy as np
import pandas as pd

class ZipCodeAPI:
    def __init__(self):
        pass

    def get_postal_code(self, country: str, postal_code: str):
        res = pgeocode.Nominatim(country).query_postal_code(postal_code)
        if isinstance(res, pd.Series):
            res = res.replace({np.nan: None}).to_dict()
        elif isinstance(res, pd.DataFrame):
            res = res.replace({np.nan: None}).to_dict(orient='records')
        return res

    def get_location(self, country: str, city: str):
        res = pgeocode.Nominatim(country).query_location(city)
        if isinstance(res, pd.Series):
            res = res.replace({np.nan: None}).to_dict()
        elif isinstance(res, pd.DataFrame):
            res = res.replace({np.nan: None}).to_dict(orient='records')
        return res