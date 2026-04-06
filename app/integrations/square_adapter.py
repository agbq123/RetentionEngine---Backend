from flask import current_app
from square import Square
from square.environment import SquareEnvironment
import requests


def _square_environment():
    env = current_app.config.get("SQUARE_ENV", "sandbox")
    if env == "sandbox":
        return SquareEnvironment.SANDBOX
    return SquareEnvironment.PRODUCTION


def _square_connect_base() -> str:
    return (
        "https://connect.squareupsandbox.com"
        if current_app.config.get("SQUARE_ENV", "sandbox") == "sandbox"
        else "https://connect.squareup.com"
    )


def build_square_client(access_token: str):
    return Square(
        token=access_token,
        environment=_square_environment(),
    )


def exchange_code_for_token(code: str) -> dict:
    response = requests.post(
        f"{_square_connect_base()}/oauth2/token",
        json={
            "client_id": current_app.config["SQUARE_APP_ID"],
            "client_secret": current_app.config["SQUARE_APP_SECRET"],
            "code": code,
            "grant_type": "authorization_code",
        },
        headers={"Content-Type": "application/json"},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def get_locations(access_token: str):
    client = build_square_client(access_token)
    result = client.locations.list()
    return result.locations or []


def search_customers(access_token: str):
    client = build_square_client(access_token)
    result = client.customers.search(query={})
    return result.customers or []


def list_bookings(access_token: str, location_id: str):
    client = build_square_client(access_token)
    pager = client.bookings.list(location_id=location_id)
    return list(pager)


def search_team_members(access_token: str):
    client = build_square_client(access_token)
    result = client.team_members.search(query={})
    return result.team_members or []


def retrieve_catalog_object(access_token: str, object_id: str):
    client = build_square_client(access_token)
    result = client.catalog.object.get(object_id=object_id)
    return getattr(result, "catalog_object", None)