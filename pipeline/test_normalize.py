from normalize import (
    normalize_name,
    normalize_email,
    normalize_phone,
    normalize_city,
    normalize_status,
    normalize_verified,
)


print(normalize_name("  RITU   SHARMA "))
print(normalize_email("TEST@EXAMPLE.COM"))
print(normalize_phone("+91-9000000254"))
print(normalize_phone("919000000254"))
print(normalize_phone("9000000254"))
print(normalize_city("GURGAON"))
print(normalize_city("Bangalore"))
print(normalize_status(" ACTIVE "))
print(normalize_verified("Y"))
print(normalize_verified("No"))