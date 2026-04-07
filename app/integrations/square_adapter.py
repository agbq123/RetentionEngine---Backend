from flask import current_app
from square import Square
from square.environment import SquareEnvironment
import requests


def _square_environment():
    env = current_app.config.get("SQUARE_ENV", "sandbox")
    if str(env).lower() == "sandbox":
        return SquareEnvironment.SANDBOX
    return SquareEnvironment.PRODUCTION


def _square_connect_base() -> str:
    return (
        "https://connect.squareupsandbox.com"
        if str(current_app.config.get("SQUARE_ENV", "sandbox")).lower() == "sandbox"
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


def retrieve_catalog_object(access_token: str, object_id: str, include_related_objects: bool = False):
    client = build_square_client(access_token)
    result = client.catalog.object.get(
        object_id=object_id,
        include_related_objects=include_related_objects,
    )

    obj = getattr(result, "object", None)
    if obj is None:
        obj = getattr(result, "catalog_object", None)

    related_objects = getattr(result, "related_objects", None) or []
    return obj, related_objects


def batch_retrieve_catalog_objects(access_token: str, object_ids: list[str], include_related_objects: bool = True):
    if not object_ids:
        return {}, {}

    response = requests.post(
        f"{_square_connect_base()}/v2/catalog/batch-retrieve",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
        json={
            "object_ids": object_ids,
            "include_related_objects": include_related_objects,
        },
        timeout=60,
    )
    response.raise_for_status()

    payload = response.json()
    objects = payload.get("objects") or []
    related_objects = payload.get("related_objects") or []

    objects_by_id = {obj.get("id"): obj for obj in objects if obj.get("id")}
    related_by_id = {obj.get("id"): obj for obj in related_objects if obj.get("id")}

    return objects_by_id, related_by_id