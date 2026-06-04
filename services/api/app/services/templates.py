import re

SUPPORTED_TRADES = ("plumber", "electrician", "roofer", "locksmith", "gas_engineer", "builder")
TEMPLATE_VARIABLES = ["business_name", "callback_window", "appointment_window"]

DEFAULT_TEMPLATES: dict[str, str] = {
    "plumber": (
        "Hi, this is {business_name}. Sorry we missed your call. If it's an emergency we can "
        "have someone call you back in {callback_window}. Otherwise reply with your address, "
        "a short description of the job, and when you'd like an appointment. We'll aim for a "
        "{appointment_window}. Thanks."
    ),
    "locksmith": (
        "Hi, this is {business_name}. Sorry we missed your call. Locked out? Reply with your "
        "location and we'll call you back in {callback_window}. For non-urgent jobs, let us "
        "know and we'll book you in."
    ),
    "electrician": (
        "Hi, this is {business_name}. Sorry we missed your call. Power out or urgent? We'll "
        "call back in {callback_window}. Otherwise reply with your address, what's needed, "
        "and when suits for a {appointment_window} visit."
    ),
    "roofer": (
        "Hi, this is {business_name}. Sorry we missed your call. We'll call back within "
        "{callback_window}. For a quote, reply with your address and a description of the "
        "issue. We'll book a {appointment_window} inspection."
    ),
    "gas_engineer": (
        "Hi, this is {business_name}. Sorry we missed your call. If you can smell gas, leave "
        "the house and call National Grid on 0800 111 999. For other gas work, we'll call "
        "back in {callback_window} or book a {appointment_window} visit."
    ),
    "builder": (
        "Hi, this is {business_name}. Sorry we missed your call. We'll call back within "
        "{callback_window}. For a quote, reply with your address and a short description. "
        "We can usually visit within a {appointment_window}."
    ),
}

PLACEHOLDER_PATTERN = re.compile(r"{([a-zA-Z_][a-zA-Z0-9_]*)}")


def normalize_trade(trade: str) -> str:
    normalized = trade.strip().lower().replace(" ", "_").replace("-", "_")
    if normalized in {"gas", "gas_engineer", "gas_engineers"}:
        return "gas_engineer"
    if normalized in {"builder", "handyman", "builder_handyman"}:
        return "builder"
    return normalized


def validate_trade(trade: str) -> str:
    normalized = normalize_trade(trade)
    if normalized not in SUPPORTED_TRADES:
        raise ValueError(f"Unsupported trade '{trade}'")
    return normalized


def validate_template_body(body: str) -> None:
    placeholders = set(PLACEHOLDER_PATTERN.findall(body))
    unsupported = placeholders.difference(TEMPLATE_VARIABLES)
    if unsupported:
        raise ValueError(f"Unsupported template variables: {', '.join(sorted(unsupported))}")


def appointment_window_label(value: str) -> str:
    labels = {
        "4-hour": "4-hour window",
        "same_day": "same day",
        "same day": "same day",
        "next_day": "next day",
        "next day": "next day",
        "1_week": "1 week",
        "1 week": "1 week",
    }
    return labels.get(value, value)


def render_template(
    body: str,
    *,
    business_name: str,
    callback_window_minutes: int,
    appointment_window: str,
) -> str:
    validate_template_body(body)
    values = {
        "business_name": business_name,
        "callback_window": f"{callback_window_minutes} minutes",
        "appointment_window": appointment_window_label(appointment_window),
    }
    return body.format(**values)

