import re


def normalize_name(name):
    """Normalize a person's name for matching."""
    if name is None:
        return ""

    name = str(name).strip().lower()
    name = re.sub(r"\s+", " ", name)

    return name


def normalize_email(email):
    """Normalize an email address."""
    if email is None:
        return ""

    return str(email).strip().lower()


def normalize_phone(phone):
    """Convert Indian phone numbers into a consistent 10-digit format."""
    if phone is None:
        return ""

    digits = re.sub(r"\D", "", str(phone))

    # Remove India's country code.
    if digits.startswith("91") and len(digits) == 12:
        digits = digits[2:]

    # Remove leading zero from numbers such as 09000000123.
    if digits.startswith("0") and len(digits) == 11:
        digits = digits[1:]

    return digits


def normalize_city(city):
    """Normalize city names."""
    if city is None:
        return ""

    city = str(city).strip().lower()

    city_mapping = {
        "gurgaon": "gurugram",
        "gurugram": "gurugram",
        "bangalore": "bengaluru",
        "bengaluru": "bengaluru",
        "bombay": "mumbai",
        "mumbai": "mumbai",
        "new delhi": "new delhi",
        "delhi": "delhi",
        "pune": "pune",
        "noida": "noida",
    }

    return city_mapping.get(city, city)


def normalize_status(status):
    """Normalize worker status."""
    if status is None:
        return ""

    return str(status).strip().lower()


def normalize_verified(value):
    """Convert different verification values to True/False."""
    if value is None:
        return None

    value = str(value).strip().lower()

    if value in {"yes", "y", "true", "1"}:
        return True

    if value in {"no", "n", "false", "0"}:
        return False

    return None