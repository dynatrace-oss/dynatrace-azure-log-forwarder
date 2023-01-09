import base64
import os


def to_base64_text(text: str) -> str:
    encoded_bytes = base64.b64encode(text.encode('ascii'))
    encoded_text = encoded_bytes.decode('ascii')
    return encoded_text


def get_int_environment_value(key: str, default_value: int) -> int:
    environment_value = os.environ.get(key, None)
    return int(environment_value) if environment_value and environment_value.isdigit() else default_value
