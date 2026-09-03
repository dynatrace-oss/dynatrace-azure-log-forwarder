#   Copyright 2026 Dynatrace LLC
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import base64

from logs_ingest.util.util_misc import to_base64_text


def test_to_base64_text_ascii_input():
    # given
    text = "hello world"

    # when
    result = to_base64_text(text)

    # then
    assert result == base64.b64encode(text.encode('utf-8')).decode('ascii')


def test_to_base64_text_non_ascii_input():
    # given - contains ® (\xae), the exact character from the customer stack trace
    text = "some log content with non-ASCII char: ® registered trademark"

    # when / then - must not raise UnicodeEncodeError
    result = to_base64_text(text)

    # and result must be valid base64 decodable back to the original string
    decoded = base64.b64decode(result).decode('utf-8')
    assert decoded == text


def test_to_base64_text_multibyte_chars():
    # given - broader coverage: accented chars, emoji
    text = "café résumé naïve 🎉"

    # when / then
    result = to_base64_text(text)
    decoded = base64.b64decode(result).decode('utf-8')
    assert decoded == text


def test_to_base64_text_truncates_long_input():
    # given - input exceeding the default 256-byte limit
    text = "a" * 300

    # when
    result = to_base64_text(text)

    # then - result must end with the truncation marker
    assert result.endswith("...[truncated]")
    # and the base64 part decodes to exactly 256 bytes
    base64_part = result.replace("...[truncated]", "")
    decoded = base64.b64decode(base64_part)
    assert len(decoded) == 256


def test_to_base64_text_no_truncation_at_limit():
    # given - input exactly at the limit (should not be truncated)
    text = "a" * 256

    # when
    result = to_base64_text(text)

    # then
    assert not result.endswith("...[truncated]")
    decoded = base64.b64decode(result).decode('utf-8')
    assert decoded == text


def test_to_base64_text_custom_max_bytes():
    # given
    text = "hello world"  # 11 bytes

    # when - limit set below the input length
    result = to_base64_text(text, max_bytes=5)

    # then
    assert result.endswith("...[truncated]")
    base64_part = result.replace("...[truncated]", "")
    decoded = base64.b64decode(base64_part)
    assert decoded == b"hello"
