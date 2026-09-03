import base64
import os


def to_base64_text(text: str, max_bytes: int = 256) -> str:
    encoded_input = text.encode('utf-8')
    truncated = len(encoded_input) > max_bytes
    if truncated:
        encoded_input = encoded_input[:max_bytes]
    encoded_text = base64.b64encode(encoded_input).decode('ascii')
    return encoded_text + ("...[truncated]" if truncated else "")


def get_int_environment_value(key: str, default_value: int) -> int:
    environment_value = os.environ.get(key, None)
    return int(environment_value) if environment_value and environment_value.isdigit() else default_value
