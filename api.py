from fastapi import FastAPI

from pycargr.parser import parse_car_page, parse_search_results
from pycargr.model import to_dict


SEARCH_BASE_URL = 'https://www.car.gr/classifieds/cars/'
app = FastAPI()


@app.get("/api/car/{car_id}")
def get_car(car_id: int):
    car = to_dict(parse_car_page(car_id))
    return car


@app.get("/api/search")
def search(query: str):
    # pass the rest as search params
    search_url = SEARCH_BASE_URL + '?' + query

    results = parse_search_results(search_url)
    return results
