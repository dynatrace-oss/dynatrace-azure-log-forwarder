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
