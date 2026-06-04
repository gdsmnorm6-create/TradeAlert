import phonenumbers

from app.config import get_settings


def normalize_phone(phone: str, region: str | None = None) -> str:
    settings = get_settings()
    parsed = phonenumbers.parse(phone, region or settings.default_region)
    if not phonenumbers.is_possible_number(parsed):
        raise ValueError("Phone number is not valid")
    return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
