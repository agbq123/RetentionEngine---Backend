from datetime import datetime, timezone

from ..database import db
from ..integrations.square_adapter import (
    batch_retrieve_catalog_objects,
    list_bookings,
    search_customers,
)
from ..models.appointment import Appointment
from ..models.client import Client
from ..models.integration_account import IntegrationAccount


def _parse_square_datetime(value):
    if not value:
        return None

    if isinstance(value, datetime):
        dt = value
    else:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))

    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)

    return dt.replace(microsecond=0)


def _normalize_db_datetime(value):
    if value is None:
        return None
    if value.tzinfo is not None:
        value = value.astimezone(timezone.utc).replace(tzinfo=None)
    return value.replace(microsecond=0)


def _normalize_text(value):
    if value is None:
        return None

    enum_value = getattr(value, "value", None)
    if enum_value is not None:
        value = enum_value

    value = str(value).strip()
    return value if value else None


def _normalize_price(value):
    if value is None:
        return 0.0
    return round(float(value), 2)


def _datetime_different(a, b):
    return _normalize_db_datetime(a) != _normalize_db_datetime(b)


def _values_different(a, b):
    return a != b


def _segment_price_from_segment(segment):
    price_money = getattr(segment, "price_money", None)
    if price_money and getattr(price_money, "amount", None) is not None:
        return price_money.amount / 100.0

    amount = getattr(segment, "price", None)
    if amount is not None:
        try:
            return float(amount)
        except Exception:
            pass

    amount_cents = getattr(segment, "price_amount", None)
    if amount_cents is not None:
        try:
            return float(amount_cents) / 100.0
        except Exception:
            pass

    return None


def _extract_variation_ids(bookings):
    variation_ids = set()

    for booking in bookings:
        segments = getattr(booking, "appointment_segments", None) or []
        for segment in segments:
            variation_id = _normalize_text(getattr(segment, "service_variation_id", None))
            if variation_id:
                variation_ids.add(variation_id)

    return sorted(variation_ids)


def _chunked(items, size):
    for i in range(0, len(items), size):
        yield items[i:i + size]


def _prefetch_catalog_map(access_token, bookings):
    variation_ids = _extract_variation_ids(bookings)
    if not variation_ids:
        return {}, {}

    all_variations = {}
    all_related = {}

    for chunk in _chunked(variation_ids, 1000):
        objects_by_id, related_by_id = batch_retrieve_catalog_objects(
            access_token,
            chunk,
            include_related_objects=True,
        )
        all_variations.update(objects_by_id)
        all_related.update(related_by_id)

    return all_variations, all_related


def _variation_data_from_dict(variation_obj):
    if not variation_obj:
        return None
    return variation_obj.get("item_variation_data") or {}


def _item_name_from_related_dict(related_by_id, item_id):
    if not item_id:
        return None

    item_obj = related_by_id.get(item_id) or {}
    item_data = item_obj.get("item_data") or {}
    return _normalize_text(item_data.get("name"))


def _price_from_location_overrides(variation_data, location_id):
    overrides = variation_data.get("location_overrides") or []
    if not location_id:
        return None

    for override in overrides:
        if _normalize_text(override.get("location_id")) != _normalize_text(location_id):
            continue

        price_money = override.get("price_money") or {}
        amount = price_money.get("amount")
        if amount is not None:
            return amount / 100.0

    return None


def _price_from_variation_data(variation_data, location_id):
    override_price = _price_from_location_overrides(variation_data, location_id)
    if override_price is not None:
        return override_price

    price_money = variation_data.get("price_money") or {}
    amount = price_money.get("amount")
    if amount is not None:
        return amount / 100.0

    return None


def _service_info_from_segment(segment, location_id, variations_by_id, related_by_id):
    service_name = _normalize_text(
        getattr(segment, "service_variation_name", None)
        or getattr(segment, "service_name", None)
    )
    service_price = 0.0

    direct_price = _segment_price_from_segment(segment)
    if direct_price is not None:
        return service_name, _normalize_price(direct_price)

    variation_id = _normalize_text(getattr(segment, "service_variation_id", None))
    if not variation_id:
        return service_name, service_price

    variation_obj = variations_by_id.get(variation_id)
    if not variation_obj:
        return service_name, service_price

    variation_data = _variation_data_from_dict(variation_obj)
    if not variation_data:
        return service_name, service_price

    variation_name = _normalize_text(variation_data.get("name"))
    item_id = _normalize_text(variation_data.get("item_id"))
    item_name = _item_name_from_related_dict(related_by_id, item_id)

    if not service_name:
        service_name = item_name or variation_name

    catalog_price = _price_from_variation_data(variation_data, location_id)
    if catalog_price is not None:
        service_price = catalog_price

    return _normalize_text(service_name), _normalize_price(service_price)


def _booking_service_info(booking, location_id, variations_by_id, related_by_id):
    appointment_segments = getattr(booking, "appointment_segments", None)
    if not appointment_segments:
        return None, 0.0

    total_price = 0.0
    first_name = None

    for segment in appointment_segments:
        seg_name, seg_price = _service_info_from_segment(
            segment,
            location_id,
            variations_by_id,
            related_by_id,
        )
        seg_name = _normalize_text(seg_name)
        seg_price = _normalize_price(seg_price)

        if not first_name and seg_name:
            first_name = seg_name

        total_price += seg_price

    return _normalize_text(first_name), _normalize_price(total_price)


def sync_square_data(user):
    account = IntegrationAccount.query.filter_by(
        user_id=user.id,
        provider="square",
    ).first()

    if not account:
        raise Exception("Square not connected")

    customers = search_customers(account.access_token)
    bookings = list_bookings(account.access_token, account.location_id)
    variations_by_id, related_by_id = _prefetch_catalog_map(account.access_token, bookings)

    customer_map = {}
    customers_created = 0
    customers_updated = 0
    appointments_created = 0
    appointments_updated = 0

    for customer in customers:
        square_customer_id = _normalize_text(getattr(customer, "id", None))
        email = _normalize_text(getattr(customer, "email_address", None))
        phone = _normalize_text(getattr(customer, "phone_number", None))
        name = _normalize_text(
            " ".join(
                part for part in [
                    getattr(customer, "given_name", None),
                    getattr(customer, "family_name", None),
                ]
                if part
            )
        ) or "Unknown"

        client = None
        if square_customer_id:
            client = Client.query.filter_by(square_customer_id=square_customer_id).first()

        if not client:
            client = Client(
                user_id=user.id,
                square_customer_id=square_customer_id,
                name=name,
                email=email,
                phone=phone,
                visit_count=0,
                lifetime_value=0.0,
            )
            db.session.add(client)
            db.session.flush()
            customers_created += 1
        else:
            changed = False

            if square_customer_id and _values_different(_normalize_text(client.square_customer_id), square_customer_id):
                client.square_customer_id = square_customer_id
                changed = True

            if _values_different(_normalize_text(client.name), name):
                client.name = name
                changed = True

            if _values_different(_normalize_text(client.email), email):
                client.email = email
                changed = True

            if _values_different(_normalize_text(client.phone), phone):
                client.phone = phone
                changed = True

            if changed:
                customers_updated += 1

        if square_customer_id:
            customer_map[square_customer_id] = client

    for booking in bookings:
        square_booking_id = _normalize_text(getattr(booking, "id", None))
        square_customer_id = _normalize_text(getattr(booking, "customer_id", None))
        start_at = _parse_square_datetime(getattr(booking, "start_at", None))
        status = _normalize_text(getattr(booking, "status", None))
        location_id = _normalize_text(getattr(booking, "location_id", None))

        service_name, service_price = _booking_service_info(
            booking,
            location_id,
            variations_by_id,
            related_by_id,
        )
        service_name = _normalize_text(service_name)
        service_price = _normalize_price(service_price)

        if not square_customer_id or square_customer_id not in customer_map or not start_at:
            continue

        client = customer_map[square_customer_id]

        appointment = None
        if square_booking_id:
            appointment = Appointment.query.filter_by(square_booking_id=square_booking_id).first()

        if not appointment:
            appointment = Appointment(
                client_id=client.id,
                square_booking_id=square_booking_id,
                appointment_date=start_at,
                start_at=start_at,
                status=status,
                location_id=location_id,
                service_name=service_name,
                service_price=service_price,
            )
            db.session.add(appointment)
            appointments_created += 1
        else:
            changed = False

            if _values_different(appointment.client_id, client.id):
                appointment.client_id = client.id
                changed = True

            if square_booking_id and _values_different(_normalize_text(appointment.square_booking_id), square_booking_id):
                appointment.square_booking_id = square_booking_id
                changed = True

            if _datetime_different(appointment.appointment_date, start_at):
                appointment.appointment_date = start_at
                changed = True

            if _datetime_different(appointment.start_at, start_at):
                appointment.start_at = start_at
                changed = True

            if _values_different(_normalize_text(appointment.status), status):
                appointment.status = status
                changed = True

            if _values_different(_normalize_text(appointment.location_id), location_id):
                appointment.location_id = location_id
                changed = True

            if _values_different(_normalize_text(appointment.service_name), service_name):
                appointment.service_name = service_name
                changed = True

            if _values_different(_normalize_price(appointment.service_price), service_price):
                appointment.service_price = service_price
                changed = True

            if changed:
                appointments_updated += 1

    db.session.commit()

    all_clients = Client.query.filter_by(user_id=user.id).all()

    for client in all_clients:
        appointments = (
            Appointment.query.filter_by(client_id=client.id)
            .order_by(Appointment.appointment_date.asc())
            .all()
        )

        if appointments:
            first_visit = _normalize_db_datetime(appointments[0].appointment_date)
            last_visit = _normalize_db_datetime(appointments[-1].appointment_date)
            visit_count = len(appointments)
            lifetime_value = _normalize_price(sum((appt.service_price or 0.0) for appt in appointments))

            client.first_visit = first_visit
            client.last_visit = last_visit
            client.visit_count = visit_count
            client.lifetime_value = lifetime_value
        else:
            client.first_visit = None
            client.last_visit = None
            client.visit_count = 0
            client.lifetime_value = 0.0

    db.session.commit()

    return {
        "customers_created": customers_created,
        "customers_updated": customers_updated,
        "appointments_created": appointments_created,
        "appointments_updated": appointments_updated,
        "catalog_variations_prefetched": len(variations_by_id),
    }