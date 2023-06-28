#   Copyright 2021 Dynatrace LLC
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

import asyncio
import json
import os
import time
from datetime import datetime, timezone
from json import JSONDecodeError
from typing import List, Dict, Optional
import re

import azure.functions as func
from dateutil import parser

from . import logging
from .dynatrace_client import send_logs
from .filtering import LogFilter
from .mapping import extract_resource_id_attributes, extract_severity, azure_properties_names
from .metadata_engine import MetadataEngine
from .monitored_entity_id import infer_monitored_entity_id
from .self_monitoring import SelfMonitoring
from .util import util_misc
from .util.util_misc import get_int_environment_value

record_age_limit = get_int_environment_value("DYNATRACE_LOG_INGEST_MAX_RECORD_AGE", 3600 * 24)
attribute_value_length_limit = get_int_environment_value("DYNATRACE_LOG_INGEST_ATTRIBUTE_VALUE_MAX_LENGTH", 250)
content_length_limit = get_int_environment_value("DYNATRACE_LOG_INGEST_CONTENT_MAX_LENGTH", 8192)
cloud_log_forwarder = os.environ.get("RESOURCE_ID", "")  # Function app id

DYNATRACE_URL = "DYNATRACE_URL"
DYNATRACE_ACCESS_KEY = "DYNATRACE_ACCESS_KEY"
DYNATRACE_LOG_INGEST_CONTENT_MARK_TRIMMED = "[TRUNCATED]"

metadata_engine = MetadataEngine()
log_filter = LogFilter()


def main(events: List[func.EventHubEvent]):
    self_monitoring = SelfMonitoring(execution_time=datetime.utcnow())
    process_logs(events, self_monitoring)


def process_logs(events: List[func.EventHubEvent], self_monitoring: SelfMonitoring):
    try:
        verify_dt_access_params_provided()
        logging.throttling_counter.reset_throttling_counter()

        start_time = time.perf_counter()

        logs_to_be_sent_to_dt = extract_logs(events, self_monitoring)

        self_monitoring.processing_time = time.perf_counter() - start_time
        logging.info(f"Successfully parsed {len(logs_to_be_sent_to_dt)} log records")

        if logs_to_be_sent_to_dt:
            asyncio.run(send_logs(os.environ[DYNATRACE_URL], os.environ[DYNATRACE_ACCESS_KEY], logs_to_be_sent_to_dt, self_monitoring))
    except Exception as e:
        logging.exception("Failed to process logs", "log-processing-exception")
        raise e
    finally:
        self_monitoring_enabled = os.environ.get("SELF_MONITORING_ENABLED", "False") in ["True", "true"]
        self_monitoring.log_self_monitoring_data()
        if self_monitoring_enabled:
            self_monitoring.push_time_series_to_azure()


def verify_dt_access_params_provided():
    if DYNATRACE_URL not in os.environ.keys() or DYNATRACE_ACCESS_KEY not in os.environ.keys():
        raise Exception(f"Please set {DYNATRACE_URL} and {DYNATRACE_ACCESS_KEY} in application settings")


def extract_logs(events: List[func.EventHubEvent], self_monitoring: SelfMonitoring):
    logs_to_be_sent_to_dt = []
    for event in events:
        timestamp = event.enqueued_time.replace(microsecond=0).replace(tzinfo=None).isoformat() + 'Z' if event.enqueued_time else None
        if is_too_old(timestamp, self_monitoring, "event"):
            continue

        event_body = """{"records":[{"Time":"2023-06-19T10:02:35.3997017Z","ResourceId":"/subscriptions/7f399306-3fa1-4fb9-8a59-7b9822ca657d/resourceGroups/my-resource-group/providers/Microsoft.Web/sites/my-app-service","Category":"load-test","OperationName":"GET /","Level":"Information","Properties":{"Message":"6CCXw3ejejD8E7ZjHAFOp5IFoYijJqbnbwqQXULJKXLhKTFjfx9Gk2Ao3ulH3wgIEgMesP9LosTfRydC81qE5YY4EvKLTsvtAhrQTkqmJBAA1jv8sOdwQ83w9uzNqAeUoCLpBm4xewDvsQBdlENSs2e5pT2LK36SnAnji0TNlivSNiguNvOwPgp8436EOYwfwa71wKYto3jA240G02PJcMCKm0ufJjquvHw2mqRnHx3RU1S9lIuxunxD6XF4sxWavLAsVD6aQBdQC60KcDglq2GJ3DsEXIbJKsils":"6WXNeO8h4XskzMiLS2ReX8NC1Fs1UGb1MNWgPjyFXSfizo5XWdVptffydMIYZi0yTieuRvyedWVIPTHuyJXpnXQduXeGJ0IusdzjeTdVnYUtURPLBwuffTzKRDFyIwQaMEqo\raNRNS1SKHzfLkThVm7EeJYm2zDPCpP1SfsPq9R\\F8vS1xZgB\\fdpQRFloVkfw6yqm\rd9WFvJg0U\\u73cd\\u54c1\\u7f51-\\u5168\\u7403\\u6f6e\\u6d41\\u5962\\u54c1\\u7f51\\u7edc\\u96f6\\u552e\\u5546 \u003Cbr \\/\u003E\\r\\nhttp:\\/\\/www.zhenpin.com\\/ \u003Cbr \\/\u003E\\r\\n\u003Cbr \\/\u003E\\r\\n200\\u591a\\u4e2a\\u56fd\\u9645\\u4e00\\u7ebf\\u54c1\\u724c\\uff0c\\u9876\\u7ea7\\u4e70\\u624b\\u5168\\u7403\\u91c7\\u8d2d\\uff0c100%\\u6b63\\u54c1\\u4fdd\\u969c\\uff0c7\\u5929\\u65e0\\u6761\\u2026T8AyawNtRRXC3QInpIWcVUwFkvke8DcvxYHY9aPXcRg0FEd8N7CEBfQXc\ryNWkwdAqdnoCWvjyLI58DRol9BG\rJ90QcE5YoaHS7oiD7LLjmvBF4sORgG9v595tRVaSpy5Y7b59\raJMZ8HtscyQlBYTAkSZR4H6YuVc\rYw0K2Jxt9GJ6H3egmRcwyQAx2Q47QD66oxquFRm2E4DV8CSHIaWXJTMnSZNVgvoHhVhBEspUaJhHlnfQOYsz8P\r\n\t","AppName":"my-app-service"}},{"Time":"2023-06-19T10:02:35.3997372Z","ResourceId":"/subscriptions/4f8d5684-0466-4bd5-b791-e617d633cd98/resourceGroups/my-resource-group/providers/Microsoft.Web/sites/my-app-service","Category":"load-test","OperationName":"GET /","Level":"Information","Properties":{"Message":"6bTqsVVjl8WbqQ7vnno4oid4Xdbp6mlhHkVtJNySC0vGfZv2xM10V\\SD2keXT3XO2WdkdQ7aCv3yOF4G9w\\Q1zKhOECoD0B8DopSX\\r8xZeRFFiLBtVBjKLMBaB5pMMC5vkRi\\I4u9hfw\rNdpt99qd3JA\\u73cd\\u54c1\\u7f51-\\u5168\\u7403\\u6f6e\\u6d41\\u5962\\u54c1\\u7f51\\u7edc\\u96f6\\u552e\\u5546 \u003Cbr \\/\u003E\\r\\nhttp:\\/\\/www.zhenpin.com\\/ \u003Cbr \\/\u003E\\r\\n\u003Cbr \\/\u003E\\r\\n200\\u591a\\u4e2a\\u56fd\\u9645\\u4e00\\u7ebf\\u54c1\\u724c\\uff0c\\u9876\\u7ea7\\u4e70\\u624b\\u5168\\u7403\\u91c7\\u8d2d\\uff0c100%\\u6b63\\u54c1\\u4fdd\\u969c\\uff0c7\\u5929\\u65e0\\u6761\\u2026wH2w8fzI4j7HLbbCajGF8vF8wzyJK31yFaSWPN9Jbsm8C6a6zVY9e6do2NbhpR4nbqLE8qy6LJGnqQ8\\Zg8Cz\\R\\QqhhWZ3GpwNZJuwlF\rdJyIub0M28CcHIoEU3SkUR47oPidFHsCipm1jWXo4s\r\r\n\t","Details":"GUEsQbj6UNdXhaQoHQ1ggvDsMxns63\rBH9bx3\\O2yJug1sUeFPPkyniBwU2bQ2VZtnTRoEyXdNIuOkZODUFuO8oT68dK5Ov0HTDnoV3nxIh33Gwis63\ruuannAvm1ew8fLS\r4yfK8egI59FHo44l9N7lWB21oDkIMOkt9z4\\rkOM\rQJmiN97i51hDqYyStLc9RVywhgZpizUk\rIn079ck9L\\pekZYRUhASLW3ZtL8l15\\X\\TN6C6pOOySj5mx\\u73cd\\u54c1\\u7f51-\\u5168\\u7403\\u6f6e\\u6d41\\u5962\\u54c1\\u7f51\\u7edc\\u96f6\\u552e\\u5546 \u003Cbr \\/\u003E\\r\\nhttp:\\/\\/www.zhenpin.com\\/ \u003Cbr \\/\u003E\\r\\n\u003Cbr \\/\u003E\\r\\n200\\u591a\\u4e2a\\u56fd\\u9645\\u4e00\\u7ebf\\u54c1\\u724c\\uff0c\\u9876\\u7ea7\\u4e70\\u624b\\u5168\\u7403\\u91c7\\u8d2d\\uff0c100%\\u6b63\\u54c1\\u4fdd\\u969c\\uff0c7\\u5929\\u65e0\\u6761\\u2026Gq3\rnz8wXMs\\hTyGU4G4EVXOsVlmRxpDWyT\rhVFT0g1H4sqg9RYeMA9aDj5Iq0oNmWfHAzyNMGVq8lxz48EK90Rgp3zBbUNC4t\\oU2ip7z82K8lMw56jS\rv0WAi5BDl31eMRtOFDjmKvE3J9mFMvLk1mvjBUPYEAQlQAPNJOvvO3bdw5ssiFXRWj30iSTZl8mIyv6uuYig61EZOeycIIuPIh\rUubynfOSSm82fodW0KuOicb9bUXPe7Zq\r\n\t","AppName":"my-app-service"}},{"Time":"2023-06-19T10:02:35.3997692Z","ResourceId":"/subscriptions/b5dd3dce-a253-4036-bf47-06c483f4540e/resourceGroups/my-resource-group/providers/Microsoft.Web/sites/my-app-service","Category":"load-test","OperationName":"GET /","Level":"Information","Properties":{"Message":"gup4zqvIKT1b4W\\L7l4pY4Qy7lv5Bq4nFHimFZUJ\rHxQZaDBCZ8KekmdGsY\\Cjox5AXOksMcvDoTtF371h0v9MbVe0nBaBq\rEQk9l\\rjCOhuTVgdvKFqXPaJ\r9f8TD6and7iOcze8kmbM2XK8u3EkzuvH\\u73cd\\u54c1\\u7f51-\\u5168\\u7403\\u6f6e\\u6d41\\u5962\\u54c1\\u7f51\\u7edc\\u96f6\\u552e\\u5546 \u003Cbr \\/\u003E\\r\\nhttp:\\/\\/www.zhenpin.com\\/ \u003Cbr \\/\u003E\\r\\n\u003Cbr \\/\u003E\\r\\n200\\u591a\\u4e2a\\u56fd\\u9645\\u4e00\\u7ebf\\u54c1\\u724c\\uff0c\\u9876\\u7ea7\\u4e70\\u624b\\u5168\\u7403\\u91c7\\u8d2d\\uff0c100%\\u6b63\\u54c1\\u4fdd\\u969c\\uff0c7\\u5929\\u65e0\\u6761\\u2026\r\rweaEnNd8c9UWUKDdam3GxF\rYBpvNtiC5cDwaRLJKmOl3sHu8yM5kZSuL08BfCDtOh9sp\rMsy6TT5eQp7wpDn405M\\1PIbkMmvp\\ws\\Z\\XL5bZxUY152u7cvJFqlfG0wbM3nHWaGzCnRyy9KQIGT\r\n\t","Details":"Uney3UoGSvdt29nxU6pUFcjW\\viZaRJtd28uyjLLtAokHADGOp52iebtQgFehii\riDZ8OhBVCgCO9DiJYjiIcFbvQBbERYZMTRasJGTPpPs4BWwjMmZ1Y6OScnZhUEblubyKEF\rkT58ggG4EWOAeNqK8ei8JM5GxUs0VTfv\\rKMst4SMUehElENxNb0h2y\\5Yu5RwgJoNjfXsdn0\\1TQbQuv\\7\\4fRXlnYx9c4R9bGWt2YyE8ajXfj1OR2tBo\\u73cd\\u54c1\\u7f51-\\u5168\\u7403\\u6f6e\\u6d41\\u5962\\u54c1\\u7f51\\u7edc\\u96f6\\u552e\\u5546 \u003Cbr \\/\u003E\\r\\nhttp:\\/\\/www.zhenpin.com\\/ \u003Cbr \\/\u003E\\r\\n\u003Cbr \\/\u003E\\r\\n200\\u591a\\u4e2a\\u56fd\\u9645\\u4e00\\u7ebf\\u54c1\\u724c\\uff0c\\u9876\\u7ea7\\u4e70\\u624b\\u5168\\u7403\\u91c7\\u8d2d\\uff0c100%\\u6b63\\u54c1\\u4fdd\\u969c\\uff0c7\\u5929\\u65e0\\u6761\\u2026PEi9SNl1qKPIkvDM00HCF6edZDd9ndGT\\nM4p0R8E1lxxyuvDxBy3PQ1llvUX\rWHFDDiEgM0RZj5DCx23w3OZ6vM7OYE4hS10njQ4JxKIxEy4bmpEk0Kq5Z\r1ETk6m22QFGFJ\rtwEZkqMzCpNuBHkXuhHgPQ8JDWeRDlHC4lFxUFy6\rE4uI4MEgY\\HO9w0GJCvd15IBMJq0qjFFMytedw52taX\rhIHMpo7AShlNjfcSPdAuzVa3O1WUCB\r\n\t","AppName":"my-app-service"}},{"Time":"2023-06-19T10:02:35.3997970Z","ResourceId":"/subscriptions/823a179c-8c5e-4163-a2f1-de9bae5273f6/resourceGroups/my-resource-group/providers/Microsoft.Web/sites/my-app-service","Category":"load-test","OperationName":"GET /","Level":"Information","Properties":{"Message":"qacpPAW1DR9uvo4jcI5Wwb8qQRyYRuVz\\lBt2z\\hvFlRY2cAdBOv1Edm2Scy5owVU4Fw\r9gdCWaVRCEdYDKh4ITWVE49pS8UJscMt\\rUUFTpl\\g3GD8Pndy\rZklZLQhaxESIBIb2GGluo9ROtpiAXJbqt\\u73cd\\u54c1\\u7f51-\\u5168\\u7403\\u6f6e\\u6d41\\u5962\\u54c1\\u7f51\\u7edc\\u96f6\\u552e\\u5546 \u003Cbr \\/\u003E\\r\\nhttp:\\/\\/www.zhenpin.com\\/ \u003Cbr \\/\u003E\\r\\n\u003Cbr \\/\u003E\\r\\n200\\u591a\\u4e2a\\u56fd\\u9645\\u4e00\\u7ebf\\u54c1\\u724c\\uff0c\\u9876\\u7ea7\\u4e70\\u624b\\u5168\\u7403\\u91c7\\u8d2d\\uff0c100%\\u6b63\\u54c1\\u4fdd\\u969c\\uff0c7\\u5929\\u65e0\\u6761\\u2026ehqFyOKx2HsONE\r1\rsux4SXFJZ0QfNh36bK\\FgRhbeqpqHuowGWNTGRVLwwKndxpXUIkGL8Rq1IbAbh0e0e6D0JpJVNBs8YdSU4gvOeL8VQoYzTUEUmLEF\rzP2i11RnV2WWhvBmOvqfk6483k1oT9\r\n\t","Details":"U8UZqZEMbRQY6HdFnAhcMxBpNOXs8K7X5StYfHYeEfRfxk9\rMkFk1lFoPm6PNNuzG\\LdD4WnjKidR\rXnNDOIJlnWG\\\r\rT3vIDtwxMncXAFkOl4\rWzLs2I5sCXz2EaEGT24Fe5B8FjbMyx08hIexUGgAcIl7edBjZIJkDvw\r\\rMEcHsx0dXp2Uc1pHBh\rbqiTXlbn0e9Y67tOyBZGWvWGYRcs41xWLGIgB3zHnEWSKlgN321dBsM\rLXMD53DQc\\u73cd\\u54c1\\u7f51-\\u5168\\u7403\\u6f6e\\u6d41\\u5962\\u54c1\\u7f51\\u7edc\\u96f6\\u552e\\u5546 \u003Cbr \\/\u003E\\r\\nhttp:\\/\\/www.zhenpin.com\\/ \u003Cbr \\/\u003E\\r\\n\u003Cbr \\/\u003E\\r\\n200\\u591a\\u4e2a\\u56fd\\u9645\\u4e00\\u7ebf\\u54c1\\u724c\\uff0c\\u9876\\u7ea7\\u4e70\\u624b\\u5168\\u7403\\u91c7\\u8d2d\\uff0c100%\\u6b63\\u54c1\\u4fdd\\u969c\\uff0c7\\u5929\\u65e0\\u6761\\u2026SKCiZv\r9fbRBft9hzl8MXmml\r6uD03MifLtRAGezKQIZPGy\\6s3Yxpy57lxVyvtZlplQGKt7ZGqiGtoMcCX1KsNvYTjgQeWoPnSCHWo1HQdcWWf9gYH8v0KOGeXXeoPOwqSiDgWDiq\\0X8LbufF4YtI3xGTkxekcKWHFceMt4TJa4tb9FSBVbpiMRNA6k6RTq2Rms3ypcuMYHw4N\rNRFOtpK5gZcZDUxh2FEJjTVt\\vmPWkbs0ZpblSlk\r\n\t","AppName":"my-app-service"}},{"Time":"2023-06-19T10:02:35.3998162Z","ResourceId":"/subscriptions/5637975a-2d9c-48ba-a69b-ee56fff3997c/resourceGroups/my-resource-group/providers/Microsoft.Web/sites/my-app-service","Category":"load-test","OperationName":"GET /","Level":"Information","Properties":{"Message":"fEi42f383wIX9BYAOD8SvXW1JiEUALuVKz85REZiZz60\\YEmhWUFJeIuUExJOTTOkCCWEyT1ngaKtqvXzimygBUsh0MxLYKxi\\yJP\\rHHEzh3Rv080hLnL3LyW5nhttgTmdfaadMIiQMZiyY\\lFfJws6E\\u73cd\\u54c1\\u7f51-\\u5168\\u7403\\u6f6e\\u6d41\\u5962\\u54c1\\u7f51\\u7edc\\u96f6\\u552e\\u5546 \u003Cbr \\/\u003E\\r\\nhttp:\\/\\/www.zhenpin.com\\/ \u003Cbr \\/\u003E\\r\\n\u003Cbr \\/\u003E\\r\\n200\\u591a\\u4e2a\\u56fd\\u9645\\u4e00\\u7ebf\\u54c1\\u724c\\uff0c\\u9876\\u7ea7\\u4e70\\u624b\\u5168\\u7403\\u91c7\\u8d2d\\uff0c100%\\u6b63\\u54c1\\u4fdd\\u969c\\uff0c7\\u5929\\u65e0\\u6761\\u20267OTLpjxmPoPjiXJ0B34pnNQx0\rqpyNRW4oF9NqcYjNmEgLa3Iz3FSvtBJAi3fxT5lv4zTq\rL0GD2kCJRpFtg2bxA\\a4nT\rsqP\rAf0R856MRH2ielQ2uBLS5wCPFWTA\\ifeDpv54hXRNj5KKozZ4AK\r\n\t","Details":"xL6KV1X6vzlmV92zaO2LvGOvvLSfB9ZgtFwQq3d5e4RfIcv1593KMC3JmBs3cb27w7OvbISlUVvfb46oZ9DMFaTwCogUYFD\\8VZvxpqOZF9I7YLEoyehTFDIBfzzH03ShQ75xL3F0bRJVlGb4i3t0f7IoNWf0tvpzsRUtgF\\rd\\k8dgJMteWYXOxo3is9UWjA2Av1UlpvJouJgBkDJmWQ0WZ8LRKDexQdKg7k702yGZq9GfOlx7zWpJSmIJMf\\u73cd\\u54c1\\u7f51-\\u5168\\u7403\\u6f6e\\u6d41\\u5962\\u54c1\\u7f51\\u7edc\\u96f6\\u552e\\u5546 \u003Cbr \\/\u003E\\r\\nhttp:\\/\\/www.zhenpin.com\\/ \u003Cbr \\/\u003E\\r\\n\u003Cbr \\/\u003E\\r\\n200\\u591a\\u4e2a\\u56fd\\u9645\\u4e00\\u7ebf\\u54c1\\u724c\\uff0c\\u9876\\u7ea7\\u4e70\\u624b\\u5168\\u7403\\u91c7\\u8d2d\\uff0c100%\\u6b63\\u54c1\\u4fdd\\u969c\\uff0c7\\u5929\\u65e0\\u6761\\u2026ZIDndi6SCRcdQJ1V6SLUAmeRa1HbFakJoLjF\\1uBVNXBZMG0Fbu2xYwOAE3AQSRw\\JnH0FkzAIilb3L4FHKn5CmdWMAR5FOgQg46VuG47Rei8XNoZVwazFdcTvGS1qTN6fE3NT9FdacOqcSF6mY1zBMTQMUEwhC\rot\rCAVyHhcfO8LBDlGS\\LBK0gW3qy6ejaeBFVitRunB3k0KhtCh8MvEFSVJjoZxxs7vCokiZBLt\rKbv6c7iR\rtye4\r\n\t","AppName":"my-app-service"}},{"Time":"2023-06-19T10:02:35.3998516Z","ResourceId":"/subscriptions/fd2c8c42-5d23-49d8-984e-ac16795bb5f3/resourceGroups/my-resource-group/providers/Microsoft.Web/sites/my-app-service","Category":"load-test","OperationName":"GET /","Level":"Information","Properties":{"Message":"tKjKIanPOgQdT4dN1WV8xzIZBIvHKPfSH\rWqP2\\RKQo86yC\rN0PjqObqOY8i6O0ymR4ewJgLGs\\xnB0sVuWB85XSEkHMW2Iv9hVyT\\ruiPcPJ9oZDKZjO6BuLZK51FQTDImtMwaFYJHXKS9NFbshgxO2P\\u73cd\\u54c1\\u7f51-\\u5168\\u7403\\u6f6e\\u6d41\\u5962\\u54c1\\u7f51\\u7edc\\u96f6\\u552e\\u5546 \u003Cbr \\/\u003E\\r\\nhttp:\\/\\/www.zhenpin.com\\/ \u003Cbr \\/\u003E\\r\\n\u003Cbr \\/\u003E\\r\\n200\\u591a\\u4e2a\\u56fd\\u9645\\u4e00\\u7ebf\\u54c1\\u724c\\uff0c\\u9876\\u7ea7\\u4e70\\u624b\\u5168\\u7403\\u91c7\\u8d2d\\uff0c100%\\u6b63\\u54c1\\u4fdd\\u969c\\uff0c7\\u5929\\u65e0\\u6761\\u2026clLkKnW8O8x2OpzT8TEaoG1Govco7fF6EqtYetqx6oQiHT1iwDwOMBElVBqLXxq6R4BERxuv0L\rf37UcjYKsQO0m\\ukTfek4l0\rsO5jXb581ynkOj\r6vcU0wB6aQVxgeJOFnkwKYzFTZyV6nN1SLh\r\n\t","Details":"WOlCG1SGTUpLu0iLZWcp1WJj\r9g4M5bevmuQiDxun77f6tD1g8GuC\r0\\npLmxeN4YF8261ftSDg04nHKQo0tfNH9\\e9LYLux\r3XhYvo1OhRz3pvxTgC4qBR3GJ7Zx5iv4JoYKd\rbk1jFMA2fDWn\ryXRJ44lqV9\\Ehux7t0i\\rS8as\rTkandSDp9yQTYnLnK8o3aGmba4XOw\\ba00nf5Xb7g7WEbwsZbAtQE8jLZW57FpmaZpb390FXQ0hJMnb\\u73cd\\u54c1\\u7f51-\\u5168\\u7403\\u6f6e\\u6d41\\u5962\\u54c1\\u7f51\\u7edc\\u96f6\\u552e\\u5546 \u003Cbr \\/\u003E\\r\\nhttp:\\/\\/www.zhenpin.com\\/ \u003Cbr \\/\u003E\\r\\n\u003Cbr \\/\u003E\\r\\n200\\u591a\\u4e2a\\u56fd\\u9645\\u4e00\\u7ebf\\u54c1\\u724c\\uff0c\\u9876\\u7ea7\\u4e70\\u624b\\u5168\\u7403\\u91c7\\u8d2d\\uff0c100%\\u6b63\\u54c1\\u4fdd\\u969c\\uff0c7\\u5929\\u65e0\\u6761\\u2026EDV9N4c87PybOH343lYcmnFNctbN6fc0jQIHleZfcbwqhcPt\rDYDjPe\\Re293g35g1l7Yg4ml84FlX8voN2llhF86PPuFnNiVQWndl\\a1uktl5RgF6bTAEsvZ4\\xf5kqaPbmVwTYBHEKC\\tZgdTPqhONTTBBkWj1R\r2hNQJuUtzYBty\rk0ceSXb471FpReHRKGqhVW60vqLuQDecH2de6\\mwf2mDaMJSe058DGBwJGIAu3keBnQ14\\uuJ\r\n\t","AppName":"my-app-service"}},{"Time":"2023-06-19T10:02:35.3998725Z","ResourceId":"/subscriptions/a4663730-50c5-4312-a2f2-9e5130bf42d7/resourceGroups/my-resource-group/providers/Microsoft.Web/sites/my-app-service","Category":"load-test","OperationName":"GET /","Level":"Information","Properties":{"Message":"mGBTFc7HO0HMul\\UpayyHauytc1kW2J9CU\rw962\\g\rvGfiNTwIuoV4IYZFWyCfwGtTlaPitCqFDApgjtTPva424uCGQhm\rA9WPFlC\\rM4KAktwuO\rZGBdSRgQ\rQvpJ8HdUcKHDAI3\\bDGePksMoVkL\rMU\\u73cd\\u54c1\\u7f51-\\u5168\\u7403\\u6f6e\\u6d41\\u5962\\u54c1\\u7f51\\u7edc\\u96f6\\u552e\\u5546 \u003Cbr \\/\u003E\\r\\nhttp:\\/\\/www.zhenpin.com\\/ \u003Cbr \\/\u003E\\r\\n\u003Cbr \\/\u003E\\r\\n200\\u591a\\u4e2a\\u56fd\\u9645\\u4e00\\u7ebf\\u54c1\\u724c\\uff0c\\u9876\\u7ea7\\u4e70\\u624b\\u5168\\u7403\\u91c7\\u8d2d\\uff0c100%\\u6b63\\u54c1\\u4fdd\\u969c\\uff0c7\\u5929\\u65e0\\u6761\\u2026Fal\r2zLvYaDnKRTqHnC4TVu4zlkXXywsWyifh3duiib\\0vii\rKgkjGoeQGJOwYkcLD\\fmvyXIUDgaGe4d4HGKY0yPdlEMW5ASgLBbTMDp5KDO2aCTdsZsEy1bAP3weBYROCsxNdVJoLcVeK\\wLwCj\r\n\t","Details":"CggA6OihlB84RkubHX51jklOUyjOWzdMDDF88N6GkHaczykIKOncgJV4POn11\\EV0pIYQk6mxAFAyhmTMDCFT2mdOf6J\\7fZfptJJUv0mQjuPZcl\\s5vohpStbZBX1wwCykamLtdCl0UP7eX4Kw8opMfta9IOA0eetpEXs1\\rwNA7UUaxdEY\rSA7KvbHbd0WpZ0XG2vp7GPb9eR0F6OG625aEBItOAtZ9RI5M9oGSQ0h5h6LSHIOaM3dqFXER\\u73cd\\u54c1\\u7f51-\\u5168\\u7403\\u6f6e\\u6d41\\u5962\\u54c1\\u7f51\\u7edc\\u96f6\\u552e\\u5546 \u003Cbr \\/\u003E\\r\\nhttp:\\/\\/www.zhenpin.com\\/ \u003Cbr \\/\u003E\\r\\n\u003Cbr \\/\u003E\\r\\n200\\u591a\\u4e2a\\u56fd\\u9645\\u4e00\\u7ebf\\u54c1\\u724c\\uff0c\\u9876\\u7ea7\\u4e70\\u624b\\u5168\\u7403\\u91c7\\u8d2d\\uff0c100%\\u6b63\\u54c1\\u4fdd\\u969c\\uff0c7\\u5929\\u65e0\\u6761\\u2026QZP1LKBRX0EA34XdvL2sx\rpoa65CKSda\\kQhu3\\Q\r\rnQweGYJ26I4J2BOw7XQ\\1u3wgxoxJRA2Py6ebxo4Gef8q1xWX52Vofot5o9bSsbObIEjhDkevq\\H9Jpt7w5KQBeUPtfDBP59HNJIeH7llZPRGNJC6uIA\\jfLM\rpuBbKozXAmdyw83W8TDiJWJOfiuwO6cu\rJkbZK\rto4j\rbeQPK\rXyR4OuPQoz43Jd3Bo\rVaU78AZA\rpH\\GE3cC\r\n\t","AppName":"my-app-service"}},{"Time":"2023-06-19T10:02:35.3998925Z","ResourceId":"/subscriptions/41c0c4fb-9b45-4148-ba85-608bd5ed76b5/resourceGroups/my-resource-group/providers/Microsoft.Web/sites/my-app-service","Category":"load-test","OperationName":"GET /","Level":"Information","Properties":{"Message":"2JlTY\\SFYP7WF3s2RRKDtsn7pN1x9z985mdogzkecvbDdWClAdJioQMdNVtNEuxpqYi6TVt6FLQk2ACyJ\rGyzqLjavSfGFFyJvDm\r\\rDnesh3CO\rQYLKpGv7WkaOPaHlRqZWzky30ITxyXDWjLpuXol5t\\u73cd\\u54c1\\u7f51-\\u5168\\u7403\\u6f6e\\u6d41\\u5962\\u54c1\\u7f51\\u7edc\\u96f6\\u552e\\u5546 \u003Cbr \\/\u003E\\r\\nhttp:\\/\\/www.zhenpin.com\\/ \u003Cbr \\/\u003E\\r\\n\u003Cbr \\/\u003E\\r\\n200\\u591a\\u4e2a\\u56fd\\u9645\\u4e00\\u7ebf\\u54c1\\u724c\\uff0c\\u9876\\u7ea7\\u4e70\\u624b\\u5168\\u7403\\u91c7\\u8d2d\\uff0c100%\\u6b63\\u54c1\\u4fdd\\u969c\\uff0c7\\u5929\\u65e0\\u6761\\u20264pRQZBXK\\NcHKXShiPKJ9Ii2O1VaOT9FX57\\\rcOQVQcKyzzGZXs5exb\\z600ystTctquKH9XKxgWZUIHRWDIWxHG4gV5c\\n4sUbLcYjOFgP2p\r66IM\rIqj6kt\\iDOXF57TJftpcPgveRxmHlip2oe\r\n\t","Details":"DIOL\rfcJ9y1l8je8fNTfhWCLSCdFjAR\\ozg0uPogux2sEbJlV4SKAsZn5SANknaRZMgbYLf7J6wVJ\\CTzbMbfLZ0p9pRblHXtiyDmiTsWtk6q4KlRL\\PGF2XNWYb2bKJnYshVhv982YegvREV1Vu8DQBOnYlXTEV1Ebc5\\R\\reiDi54OHRPK0t6h\rb7IGCf9a31Hwx\\iLN314F3npMiX11Mfn45DULzAkbEWlwe3VOAbgGZZ40lyH8eK0dcLY\\u73cd\\u54c1\\u7f51-\\u5168\\u7403\\u6f6e\\u6d41\\u5962\\u54c1\\u7f51\\u7edc\\u96f6\\u552e\\u5546 \u003Cbr \\/\u003E\\r\\nhttp:\\/\\/www.zhenpin.com\\/ \u003Cbr \\/\u003E\\r\\n\u003Cbr \\/\u003E\\r\\n200\\u591a\\u4e2a\\u56fd\\u9645\\u4e00\\u7ebf\\u54c1\\u724c\\uff0c\\u9876\\u7ea7\\u4e70\\u624b\\u5168\\u7403\\u91c7\\u8d2d\\uff0c100%\\u6b63\\u54c1\\u4fdd\\u969c\\uff0c7\\u5929\\u65e0\\u6761\\u2026TEOQ3lgwaJTWJpkAQlNmVqKT4eL8snQdcMQlhFvupZTWWLBWbS\rP4sZTZvQ61Rvub\rGgm9HTATLTXzqDiLMqGHsM\rXiaZCswwFVMzBLNcj4SVJt08AeVo\\SS5bC2vFlpACf8F2cZaosLQaV5qT0vloAOpBhCtsUpAAGc6PB2PszkHo9BGzAAU1UCWCAmLFW\\J9J1O0sGSOZGuH91utpyiLQDLp0GDuKuHAZKHwjj00wKN8SaaSuZ1\\43U\r\n\t","AppName":"my-app-service"}},{"Time":"2023-06-19T10:02:35.3999125Z","ResourceId":"/subscriptions/11957674-7631-4ee6-a42d-fcf81986958c/resourceGroups/my-resource-group/providers/Microsoft.Web/sites/my-app-service","Category":"load-test","OperationName":"GET /","Level":"Information","Properties":{"Message":"5gDI\\ATl48EqOa9nCSciWNVkn\\n\ro3mgiPvN\\8MNV8OvxuTBadXQHf1mkLladD2yKvJZcCa5qs6Nb7J0ZDexpKKDV7ZMpzmQ1nTif\\rXNK0Rf\rVT7I3QtXQXjvkxuCb80MTzhPFytKoaD\\XuBM66N4YY5\\u73cd\\u54c1\\u7f51-\\u5168\\u7403\\u6f6e\\u6d41\\u5962\\u54c1\\u7f51\\u7edc\\u96f6\\u552e\\u5546 \u003Cbr \\/\u003E\\r\\nhttp:\\/\\/www.zhenpin.com\\/ \u003Cbr \\/\u003E\\r\\n\u003Cbr \\/\u003E\\r\\n200\\u591a\\u4e2a\\u56fd\\u9645\\u4e00\\u7ebf\\u54c1\\u724c\\uff0c\\u9876\\u7ea7\\u4e70\\u624b\\u5168\\u7403\\u91c7\\u8d2d\\uff0c100%\\u6b63\\u54c1\\u4fdd\\u969c\\uff0c7\\u5929\\u65e0\\u6761\\u2026CniWisv6cUexGTl390g4jygF3UFd7O\\\rXz3jF\\tutTjIjAyXemH7sxpieQQM7e6KOqY8HvIU1B6Bg1\\hB2byuo3c0BRQj2sjozRvPiYY3iVflxlwPZF9JTIHO3\rV6ewNAFjs0LBc3\rUtnjE\rbR2nF\r\n\t","Details":"NMSXVM6p1tHtnNR0EFvqui9xb5\\8hZSu6zS\r4EyvtFo2LGQEV8iO8kKeX5WwyKW2QLcywTzS76Em0tqcsfkY0fI3LxO\rAdAgpMQEiMLpemj7DHPVHDTGOxsFy6pWp1NVQCVHLFJQ7l2bcuaHa9R8461EWkksgzjm4Mb5y5q\\rew9O5nK1tiFmiofDilWyTJ\r0a36LxRDpU20qkSNFgT\\Zt4I\\lR4CcwlDG4wBaBY8YYQxNeTTFq5OmQvEWkVo\\u73cd\\u54c1\\u7f51-\\u5168\\u7403\\u6f6e\\u6d41\\u5962\\u54c1\\u7f51\\u7edc\\u96f6\\u552e\\u5546 \u003Cbr \\/\u003E\\r\\nhttp:\\/\\/www.zhenpin.com\\/ \u003Cbr \\/\u003E\\r\\n\u003Cbr \\/\u003E\\r\\n200\\u591a\\u4e2a\\u56fd\\u9645\\u4e00\\u7ebf\\u54c1\\u724c\\uff0c\\u9876\\u7ea7\\u4e70\\u624b\\u5168\\u7403\\u91c7\\u8d2d\\uff0c100%\\u6b63\\u54c1\\u4fdd\\u969c\\uff0c7\\u5929\\u65e0\\u6761\\u2026JGgRtS744flPGzTh1Rm\\IiX6zCNO6IK0lmq8TwG4ZUSyt58yFiD4JzCV52dREOoFdzIzKCdblCwGYj\r6iVsDwQncVKPz90kn0O4s0nIAvfgWeIjASZTSuQO45iNaw\r2Tqa6iLNqJH72oPy5i5s0cQqLjNMdlTDMTBxAbS\\dXU6FA\rD39eWAPzNjk7kAwGUSfXm2pjKpGYqt9LNV5Ga5Pp9E1dZ82c2zshLVV4tTKp8J5mipql6WzQQYpl\r\n\t","AppName":"my-app-service"}},{"Time":"2023-06-19T10:02:35.3999411Z","ResourceId":"/subscriptions/4ef31c14-93cd-4375-8f97-5b6b58123777/resourceGroups/my-resource-group/providers/Microsoft.Web/sites/my-app-service","Category":"load-test","OperationName":"GET /","Level":"Information","Properties":{"Message":"ifzJnjM11y32SYAUoDDNsB1OV\rue0pi9JoUW4UUIN8f4tmgZSHBFeZzNdh3yEWffBGYXxqYUHWpsx1GWxCJKYpt0Y\\BDwzY8iHnAL\\rYOLWdydkfuSH23i\\m4yRcmfx5TlONRuV8sJGQtCWPx\\pXnleKU\\u73cd\\u54c1\\u7f51-\\u5168\\u7403\\u6f6e\\u6d41\\u5962\\u54c1\\u7f51\\u7edc\\u96f6\\u552e\\u5546 \u003Cbr \\/\u003E\\r\\nhttp:\\/\\/www.zhenpin.com\\/ \u003Cbr \\/\u003E\\r\\n\u003Cbr \\/\u003E\\r\\n200\\u591a\\u4e2a\\u56fd\\u9645\\u4e00\\u7ebf\\u54c1\\u724c\\uff0c\\u9876\\u7ea7\\u4e70\\u624b\\u5168\\u7403\\u91c7\\u8d2d\\uff0c100%\\u6b63\\u54c1\\u4fdd\\u969c\\uff0c7\\u5929\\u65e0\\u6761\\u2026x690j53XxnVsC\rggeSdioqs0hDE3W1VY4Yxmfejy90gwBzyBk7P1tUPXg1Q3\rb2R7CwyHFwIgK\r7Ckm8TNzehYzVHXAfNe4ubWPzcvQYs91Bjh\\OZ\\qwyLuN0kddDTFxaLCF8oKAY\\K0dzf5xmVox\r\n\t","Details":"BZa1tYMcVueKsxymQ6T2a7SKIvcx2lZdLS6SGGs15oKtAUVveuEfYEdRKPyR1wYxzKACbE2fowy9L1K\r06RmVfES6\\FZ8bw0JOzHSRGbJXN\ry31lFbkWRznjMlR6Z2qp6h9QFQhqbVTSURcahGMu\\eKRcPBpdT3nIO2vc7k\\rK5m4TI8qRcz\r2eHpv6OW8GZn68S3v97\rSdnKLimmL1Ni1i4sY1JRAdKsxYKw9V68jYzz2SX9WLAbPHPHaR\rU\\u73cd\\u54c1\\u7f51-\\u5168\\u7403\\u6f6e\\u6d41\\u5962\\u54c1\\u7f51\\u7edc\\u96f6\\u552e\\u5546 \u003Cbr \\/\u003E\\r\\nhttp:\\/\\/www.zhenpin.com\\/ \u003Cbr \\/\u003E\\r\\n\u003Cbr \\/\u003E\\r\\n200\\u591a\\u4e2a\\u56fd\\u9645\\u4e00\\u7ebf\\u54c1\\u724c\\uff0c\\u9876\\u7ea7\\u4e70\\u624b\\u5168\\u7403\\u91c7\\u8d2d\\uff0c100%\\u6b63\\u54c1\\u4fdd\\u969c\\uff0c7\\u5929\\u65e0\\u6761\\u2026JYO1UpeKK7OgSOhbJMB6ma58xaaEGU6YoMLJ2FzTQF3gvAX5LBBC68gaEADNg\\x3nSpT82x6oAcnAvhGwbP2X1vBiCxpf8NnbseNP0Dk2nlDPk5Ax4MDezL6NQ8foKFhvlBPwnu\r4d3ZGaYR3XqBkG\\RY8oO3PEJoGEg7f0W01vtk4IMm\r3dqqgHnNOPwe9H7JcTZ\rkB96dMPgb7mZFa7FG3XMz3Dp\\LgKVB\\tzdWCXB71ijpZjfIz\rX0\r\n\t","AppName":"my-app-service"}},{"Time":"2023-06-19T10:02:35.3999677Z","ResourceId":"/subscriptions/56bc35c7-d532-4a3e-a9de-c335ec25a341/resourceGroups/my-resource-group/providers/Microsoft.Web/sites/my-app-service","Category":"load-test","OperationName":"GET /","Level":"Information","Properties":{"Message":"PLBnPtca2mQFsovMAB6tzNTtfPkGsMY6t72Ow2c11foAEMNI9Tos4KYwVGmFdTpxP4VlykLNDLbWDWUTHHPhkNmdMUB\\R\rNIBmkND\\rgXkZVjnxGWE0EhwW7\ruWBX\r4jXnmMqQ4Pm9zb7xzozTJ4P\\dxO\\u73cd\\u54c1\\u7f51-\\u5168\\u7403\\u6f6e\\u6d41\\u5962\\u54c1\\u7f51\\u7edc\\u96f6\\u552e\\u5546 \u003Cbr \\/\u003E\\r\\nhttp:\\/\\/www.zhenpin.com\\/ \u003Cbr \\/\u003E\\r\\n\u003Cbr \\/\u003E\\r\\n200\\u591a\\u4e2a\\u56fd\\u9645\\u4e00\\u7ebf\\u54c1\\u724c\\uff0c\\u9876\\u7ea7\\u4e70\\u624b\\u5168\\u7403\\u91c7\\u8d2d\\uff0c100%\\u6b63\\u54c1\\u4fdd\\u969c\\uff0c7\\u5929\\u65e0\\u6761\\u2026N9QHMazZEntEx88q8fOusTAVLNDutZcBh3BFa7fGHbfN0YgWTq5SF1GuISB8kI9OFUv5G\rMHAAn5z8pulif1p5LcU5WTDI0URBY9UNtEqVD0Qkv\\R0\\OdbYuEebwNTlpRa\r4ASKXQoUTNGXFeCqK\\\r\n\t","Details":"lV9G4kH42Kn5lzE5gJcNRA\raEz3\\dUDhDlR6XDlBa2RMZa3uiZUuayQGVK1ocP4\\gYjods1QXqXa4Lp6n3IqiFuhfZ\rbHFZf\\8qjctskRqWyjOXcWfDPVaidRUTTuu5JRLwfUkl5VDVzkm2mkBG2qxoJIgoLISto\\9wTc8k\\rfJnWioXeOtC9SDOqFyVwimXOfH9eLb5d0zhGdDIL5Rsw1TMDRLa8yfqiCHMHBTqCow3Deo6xj1Xex6h7FH7t\\u73cd\\u54c1\\u7f51-\\u5168\\u7403\\u6f6e\\u6d41\\u5962\\u54c1\\u7f51\\u7edc\\u96f6\\u552e\\u5546 \u003Cbr \\/\u003E\\r\\nhttp:\\/\\/www.zhenpin.com\\/ \u003Cbr \\/\u003E\\r\\n\u003Cbr \\/\u003E\\r\\n200\\u591a\\u4e2a\\u56fd\\u9645\\u4e00\\u7ebf\\u54c1\\u724c\\uff0c\\u9876\\u7ea7\\u4e70\\u624b\\u5168\\u7403\\u91c7\\u8d2d\\uff0c100%\\u6b63\\u54c1\\u4fdd\\u969c\\uff0c7\\u5929\\u65e0\\u6761\\u2026\\X345vaMeo\r8Bn\\LgSCtTTuo\r3ks5oja8OmJ4wbPLcdOnpnHTCHz8sGeSgOhRkAtKM5vmO\\dCXk5oc20IkJdA6swu15jnhnRegI9RDfSTZiAUzuWDPjReBDOIV85kJCxndWgFtFJM1usBC\rzdNIPRY7h6CM\rb4VohmLjB9ISpEHi6114HbCGPdxUiiehYYVy57c\\\\90GK4D0HUfM4obKlGWDFFWFz0wUmJRpzk5PKa12nAVwI\rANQUDuQ\r\n\t","AppName":"my-app-service"}},{"Time":"2023-06-19T10:02:35.3999999Z","ResourceId":"/subscriptions/0cf06199-3616-4324-8da2-91f05501ae0f/resourceGroups/my-resource-group/providers/Microsoft.Web/sites/my-app-service","Category":"load-test","OperationName":"GET /","Level":"Information","Properties":{"Message":"sHvV9U6TEHl5tSXccVhDVNLXsjaKkO96Pzh97\r\\cRy7o3UROIm6HXqe\rWZwTI\r3PI1OBZhiWmO2pnLzCNm\\mdKmicyBG8ozh3hbcC\\rt6oCg\\JLNMsR2a86xGfn71x8wjcYq11SnJFdl57cASWN318JgQ\\u73cd\\u54c1\\u7f51-\\u5168\\u7403\\u6f6e\\u6d41\\u5962\\u54c1\\u7f51\\u7edc\\u96f6\\u552e\\u5546 \u003Cbr \\/\u003E\\r\\nhttp:\\/\\/www.zhenpin.com\\/ \u003Cbr \\/\u003E\\r\\n\u003Cbr \\/\u003E\\r\\n200\\u591a\\u4e2a\\u56fd\\u9645\\u4e00\\u7ebf\\u54c1\\u724c\\uff0c\\u9876\\u7ea7\\u4e70\\u624b\\u5168\\u7403\\u91c7\\u8d2d\\uff0c100%\\u6b63\\u54c1\\u4fdd\\u969c\\uff0c7\\u5929\\u65e0\\u6761\\u2026BcmXYIlysFevYHyHWRqydgT5wmExSo2NHeacU8xDaLSBpwmHLJG\\CSV6M1o\rO0v4wIqxhCGUAGkQm535uti1X34KSPPmZ6C3JVpFu9PmDyc6x3SqW6CVX9NOK6jZt\\cR\rvDW4iqfZamXDGRncbY1h\r\n\t","Details":"gKZ4MohZd\\wbdyRW9yDbCyKehCAp\\kIGtdclfPQjfEzzY3yfOiClQLMRjNCvAjnZJSxwiJ0Hq8mUXH9YVuJoZ7Meljt9UHiv\\IFTO1E5c7VGKsuG5nUbgz5R1s881gSYvbMQ5HTGZjtBypZoYkTfF5esRMmmxK8U\rTRbgqV\\rLQG8DIbGJDxoVHx6Kn9ggnz4klyLenWP1SWL\\0XPnlc\rPoEe4y9K9icziVQEtYZug\rQ35pviMYGJXy8H1gDY\\u73cd\\u54c1\\u7f51-\\u5168\\u7403\\u6f6e\\u6d41\\u5962\\u54c1\\u7f51\\u7edc\\u96f6\\u552e\\u5546 \u003Cbr \\/\u003E\\r\\nhttp:\\/\\/www.zhenpin.com\\/ \u003Cbr \\/\u003E\\r\\n\u003Cbr \\/\u003E\\r\\n200\\u591a\\u4e2a\\u56fd\\u9645\\u4e00\\u7ebf\\u54c1\\u724c\\uff0c\\u9876\\u7ea7\\u4e70\\u624b\\u5168\\u7403\\u91c7\\u8d2d\\uff0c100%\\u6b63\\u54c1\\u4fdd\\u969c\\uff0c7\\u5929\\u65e0\\u6761\\u2026hD6kf1TEXa4K\rTFaCJoNjM0iV1TI1lwu8\rYdoX1hA\rzeXUHJ2oxbu6DdoyU\rTeJkskXdA4mq26POkmCcsYsLQ1C6sC005WkKvp7Uoq7W9StH5Wz7Ue2KsbB412XSZPBAV6IpVzYjRqQqKKolD8t6XzclFAve9dx\\Kg\\kXIoaimuDUSnPYI6jDe9AaY3IKleaoCfciYJE\rIJ0sk5Jv8Tzgjm16F\r8QpAB\rOBy7I9djEuQA\\md5yFO\rN\\1z\r\n\t","AppName":"my-app-service"}},{"Time":"2023-06-19T10:02:35.4000200Z","ResourceId":"/subscriptions/68a96168-6065-471b-8893-068c4b2745b6/resourceGroups/my-resource-group/providers/Microsoft.Web/sites/my-app-service","Category":"load-test","OperationName":"GET /","Level":"Information","Properties":{"Message":"h\\yap2WR\rtPk8mtidPa6dHt6sxnniCinYBmHAoGXukqPLMY\\YB\\4LMRLK0Jn1yo99fxzj\\hLiX6XStk7oj93elUc9ECFZ\\joeHM0C\\r3PfkzBJFYWHK4SfWWvnq4Uz8CMZ9Uvs87oRRfoVEUqeC\\s\\aze\\u73cd\\u54c1\\u7f51-\\u5168\\u7403\\u6f6e\\u6d41\\u5962\\u54c1\\u7f51\\u7edc\\u96f6\\u552e\\u5546 \u003Cbr \\/\u003E\\r\\nhttp:\\/\\/www.zhenpin.com\\/ \u003Cbr \\/\u003E\\r\\n\u003Cbr \\/\u003E\\r\\n200\\u591a\\u4e2a\\u56fd\\u9645\\u4e00\\u7ebf\\u54c1\\u724c\\uff0c\\u9876\\u7ea7\\u4e70\\u624b\\u5168\\u7403\\u91c7\\u8d2d\\uff0c100%\\u6b63\\u54c1\\u4fdd\\u969c\\uff0c7\\u5929\\u65e0\\u6761\\u2026QDfIpzx8IHJomQE2DhJMfSRVJgwtTo\rknxAiJzyx0iq6DSv\rD2DGTz3uO6xE8KRAgIoPFmRgDctclHYXVtFJpfW\rm7TGk\ri3QBz\rt\rP3wdFSH5mBoKtdXyBJi4GL7v08glKRwyAEtFS8tj8uhbIFZ\r\n\t","Details":"HmCMVQNHfvGsgd8KMbPUDtkwPu6ecpM9Dy9AtK2MDwOXHejwib3NGbDX6AJbKvjvU\\qmq2xMpW3fSuqnpUcRSxvTRKJVfwhsq8VGw50h4QhEFGkAYMHeIPKxikTcSUOsCRQhuoMyNUWY3sOu\\s76qY0\\6cvCCs\rId7OhV3L\\rpvj1d6fuMhRVU6TuSzCgkSeNPYY2advMHuINnQbTyLw\\z2RGCEcj\\12aBwXjK\\kuwiAAOFjIaOdeXfdKC5eY\\u73cd\\u54c1\\u7f51-\\u5168\\u7403\\u6f6e\\u6d41\\u5962\\u54c1\\u7f51\\u7edc\\u96f6\\u552e\\u5546 \u003Cbr \\/\u003E\\r\\nhttp:\\/\\/www.zhenpin.com\\/ \u003Cbr \\/\u003E\\r\\n\u003Cbr \\/\u003E\\r\\n200\\u591a\\u4e2a\\u56fd\\u9645\\u4e00\\u7ebf\\u54c1\\u724c\\uff0c\\u9876\\u7ea7\\u4e70\\u624b\\u5168\\u7403\\u91c7\\u8d2d\\uff0c100%\\u6b63\\u54c1\\u4fdd\\u969c\\uff0c7\\u5929\\u65e0\\u6761\\u2026Aqik2MmYzcSivhDC2ABWpie5R068CJhJcTUbp6RxzW2OPaSpKoOKpgKPzfDLYIidCqojpXWsqSjYA2biqz\\x\r\rNICcl1e6\r8gwqcbBghG\\jAfDpPK3W3s\rEt\rEHqg0JfOkh4RNWxJwQPOmpMdXO8MW2kDQUme6z5vPx47ZpFal\rkNzEs3LU4EpZstjKBhBOZoRgVOLIvQmQ10GYxkZxYC21DTszx\\ieJseRT\rWg9\\6A0Ea4WUl1VtatTK\r\n\t","AppName":"my-app-service"}},{"Time":"2023-06-19T10:02:35.4000398Z","ResourceId":"/subscriptions/ae42a9ba-5f05-4e7f-bf88-8ceaf2d4bb67/resourceGroups/my-resource-group/providers/Microsoft.Web/sites/my-app-service","Category":"load-test","OperationName":"GET /","Level":"Information","Properties":{"Message":"eiyyRSF\\ggyVHwo4q\\GxSD2JDJ9Dq9mmRcpXolWFg5vDaNk4pbDwQOhIXRiaH2ZDDSGUOIg5KvDyVLs3UQ6y6tLR41ZnfEmncnOeX\\rJu7VbEB9YpLoTZTdCvYS91ZSnRgVG1IX\\sljt3m2XC1XOLbc4M\\u73cd\\u54c1\\u7f51-\\u5168\\u7403\\u6f6e\\u6d41\\u5962\\u54c1\\u7f51\\u7edc\\u96f6\\u552e\\u5546 \u003Cbr \\/\u003E\\r\\nhttp:\\/\\/www.zhenpin.com\\/ \u003Cbr \\/\u003E\\r\\n\u003Cbr \\/\u003E\\r\\n200\\u591a\\u4e2a\\u56fd\\u9645\\u4e00\\u7ebf\\u54c1\\u724c\\uff0c\\u9876\\u7ea7\\u4e70\\u624b\\u5168\\u7403\\u91c7\\u8d2d\\uff0c100%\\u6b63\\u54c1\\u4fdd\\u969c\\uff0c7\\u5929\\u65e0\\u6761\\u2026sFLjGV7dI\rTmn6QbElV\\q8uTxksGTOIj\rFRkkQ65W3MbJtU0BbMvRaFogLIm\\4yAW\r8lmzXnNuF7UiwDfoUDESKeHkt\rQyERWRylS2mVaV2uH7pa9F3KyUHoPL29yvcAW5yHvwk6ExGNwtK873\rhm\r\n\t","Details":"NwETf0gaWfgywtfQX\\vpi9QZDDp29FUulPj28J9ajyFuvQ\rHNWG8QF8nhKFA45tHbNihpk\rJdyLRUnbyaD2DqpvmwG7jqbnmbRqxsnGqW4au7PdXJJNTvktGwgo7UXPZFHx1v2Pu78PuvKQASge\\Bu\r4naEM\\DE4tnQSTYp\\razkv6Ats\rR9W2USt9E0ap2t1jD9JLAl606jZbsHMwvqi7acBNnv\rHDXC5q0jUh3qe5C5zxICBEDycORuKMzl\\u73cd\\u54c1\\u7f51-\\u5168\\u7403\\u6f6e\\u6d41\\u5962\\u54c1\\u7f51\\u7edc\\u96f6\\u552e\\u5546 \u003Cbr \\/\u003E\\r\\nhttp:\\/\\/www.zhenpin.com\\/ \u003Cbr \\/\u003E\\r\\n\u003Cbr \\/\u003E\\r\\n200\\u591a\\u4e2a\\u56fd\\u9645\\u4e00\\u7ebf\\u54c1\\u724c\\uff0c\\u9876\\u7ea7\\u4e70\\u624b\\u5168\\u7403\\u91c7\\u8d2d\\uff0c100%\\u6b63\\u54c1\\u4fdd\\u969c\\uff0c7\\u5929\\u65e0\\u6761\\u2026579zdDjyUIfG9OluuluB3oJcfpQTw4Qa\\OZZa\\5XaoXfhek4ig\\YBghvtQbGaI6pgUP\rjlv4PapImNXGXgJhMch3PTK\\7xbj21m5ybbgoJ6X7weNPtNZmmtY\\2IGec3\\gRY\rocWR4Ce9GQl\\FY0GA0nXxvhsYCqPEJvAWT4i2IbU7SKlg91N0EwaUHhWxYw2t8OEVvDsXOE\\C\\9xDXtS\rSPHvd\\36netpbXDJeKFx9G8J3qbobww1AsH8\r\n\t","AppName":"my-app-service"}},{"Time":"2023-06-19T10:02:35.4000598Z","ResourceId":"/subscriptions/6f6359cb-b359-4592-961d-26c9daaf57ab/resourceGroups/my-resource-group/providers/Microsoft.Web/sites/my-app-service","Category":"load-test","OperationName":"GET /","Level":"Information","Properties":{"Message":"1sutsVCNUClexiKIob0mqiqDvvvhoD9RfXlT7du5gEHMCsmNkE\rfdV3u7O3p\\Vf4ajpIC7vO6lQU20\\XliQixND32v5xa63yaxm0t\\rge2k53\rF84QUae09tE8Bg1sGvmyJOySoEjWy\rF23\\AIEq7myZ\r\\u73cd\\u54c1\\u7f51-\\u5168\\u7403\\u6f6e\\u6d41\\u5962\\u54c1\\u7f51\\u7edc\\u96f6\\u552e\\u5546 \u003Cbr \\/\u003E\\r\\nhttp:\\/\\/www.zhenpin.com\\/ \u003Cbr \\/\u003E\\r\\n\u003Cbr \\/\u003E\\r\\n200\\u591a\\u4e2a\\u56fd\\u9645\\u4e00\\u7ebf\\u54c1\\u724c\\uff0c\\u9876\\u7ea7\\u4e70\\u624b\\u5168\\u7403\\u91c7\\u8d2d\\uff0c100%\\u6b63\\u54c1\\u4fdd\\u969c\\uff0c7\\u5929\\u65e0\\u6761\\u20260P\\\re8cj5uzyw6qDPNjkb8PY5dYCdFLBgERdz9twxoEeU5McIgkgIySJYEltmChuvFq9Yi5VD1T81bWfG8obFd8iiKF\r7ppmAg24zF6zVbnZ9891QjRy2\rfXm9IWXaTCZKYsKKswFNSvmnoQ7QZRl\r\n\t","Details":"G9ZsL\\sVJnl4v2RBiKgZVK8e6sSxcdnMCq\\MZESEZSvF8pILqkZW0ajmL6vR15kc9Uw2XWRmihuJqoA08\\yAnElHiyUInhf1HmSqxEUD6b7jLLAOKbIM9tyZDaetnXEov4qh8udjlS2hJM6Jk1kuGnjsxzJuOQTCsHOKkZ2\\rqdwO3X9KXGWMKSP2MnTUTojoY40GpnK5974ID9okgF1iM\\GeD1zUCbIbN42PBJsq9jUA97nAEgNq23YY8\roR\\u73cd\\u54c1\\u7f51-\\u5168\\u7403\\u6f6e\\u6d41\\u5962\\u54c1\\u7f51\\u7edc\\u96f6\\u552e\\u5546 \u003Cbr \\/\u003E\\r\\nhttp:\\/\\/www.zhenpin.com\\/ \u003Cbr \\/\u003E\\r\\n\u003Cbr \\/\u003E\\r\\n200\\u591a\\u4e2a\\u56fd\\u9645\\u4e00\\u7ebf\\u54c1\\u724c\\uff0c\\u9876\\u7ea7\\u4e70\\u624b\\u5168\\u7403\\u91c7\\u8d2d\\uff0c100%\\u6b63\\u54c1\\u4fdd\\u969c\\uff0c7\\u5929\\u65e0\\u6761\\u2026ZjXDnviOUWEiT\rb9AiAmwAWQaH5E\r4Q\rT\\tAdUOdxtpmUcKyo\r8UE93wK15\\SDCmOFst0\r\rVJWbQTVNc5jxpKRik7uABUBmCFdETtyIdH8dhyIx5KfJx7cDUGtlDVKHK19Ome9wIulBI2vA2aYVyCQII794KgAoSOtYRfx\\1DVooY\rRs5TmIdIW04KgLFTJH59QOj2q9fmDGzxqRa1gjW1WCgmH1L0PKxc0QNqdFzSMCy1wva1txylRqL\r\n\t","AppName":"my-app-service"}},{"Time":"2023-06-19T10:02:35.4000799Z","ResourceId":"/subscriptions/e7a5d25f-c9e6-4233-a2d3-ae0734e1f041/resourceGroups/my-resource-group/providers/Microsoft.Web/sites/my-app-service","Category":"load-test","OperationName":"GET /","Level":"Information","Properties":{"Message":"87d2Eet3IsRXy\\WNLojQ1dv\ruQ7vYJ3TW73zxzvjFNsYLH80Zb9CZY8OSuQPf22uBSsGS9ix3cfu2l\\kZPjX9Iou3UlwbotmjxDJA\\rMKU2byXa\\T3KY676emDyGL7vsE5bL7LSNfkFxiKIzoDV51eHcx\\u73cd\\u54c1\\u7f51-\\u5168\\u7403\\u6f6e\\u6d41\\u5962\\u54c1\\u7f51\\u7edc\\u96f6\\u552e\\u5546 \u003Cbr \\/\u003E\\r\\nhttp:\\/\\/www.zhenpin.com\\/ \u003Cbr \\/\u003E\\r\\n\u003Cbr \\/\u003E\\r\\n200\\u591a\\u4e2a\\u56fd\\u9645\\u4e00\\u7ebf\\u54c1\\u724c\\uff0c\\u9876\\u7ea7\\u4e70\\u624b\\u5168\\u7403\\u91c7\\u8d2d\\uff0c100%\\u6b63\\u54c1\\u4fdd\\u969c\\uff0c7\\u5929\\u65e0\\u6761\\u2026TK1yzv76w\\IxplLYHLgs1A8O2ZoaVhQQLdJnd92ud3cDH13mGQhnZc3k6\\hcVovpwu62tkXUDsaJY3gYRcNpGmePR2jhSlwYmOhFW3fTcaNZdUdcU\\168R5N\\vcHFe6InLFfUI78SV\rNuNj\\2eNB2\r\n\t","Details":"6\rQklZPNXZ7jsIa5dH0tq7pA7o2w6tqsgDvblLETVw7nHpIZJuIDHKio6Vf7YqLIAgag6oNFnZQgbf370WS5\\9otqUYkiTRmb3YMw\rn3Oc3a0pUAGuaNDT\rtZ4s8M9V9HAZxu3vIJe\rce8ZDRGibGXLQCAqDq3EwgGpjAIy\\rP6o0N5QaktY8GzRhS0JdFqXJuF9p9sI3D5\r5MUP\\R2X\rxP5DGCRFsj\rglpY1f46HULK5TuRDM6yCUXLctq4c\\u73cd\\u54c1\\u7f51-\\u5168\\u7403\\u6f6e\\u6d41\\u5962\\u54c1\\u7f51\\u7edc\\u96f6\\u552e\\u5546 \u003Cbr \\/\u003E\\r\\nhttp:\\/\\/www.zhenpin.com\\/ \u003Cbr \\/\u003E\\r\\n\u003Cbr \\/\u003E\\r\\n200\\u591a\\u4e2a\\u56fd\\u9645\\u4e00\\u7ebf\\u54c1\\u724c\\uff0c\\u9876\\u7ea7\\u4e70\\u624b\\u5168\\u7403\\u91c7\\u8d2d\\uff0c100%\\u6b63\\u54c1\\u4fdd\\u969c\\uff0c7\\u5929\\u65e0\\u6761\\u2026TbOzgpimKGPW74\rOiHtclQ8Uo3jLtmC6\\7823lixoyyd4R6Zns\rowj\rgimhFbxNXhsDZCCCDz9us0NGpVpf7Ku8IKKG6m5gPu\\0gRxPsgAA7q6BILt2nvenxikswgGNnh02y7wK3\\j2lSOb0da0R5M1tvD\\\\xiB\riYspJsejwZ\rf\rNWnKMnsA7D\\St9RNGlQHSLC0kQFG9bj47EGt1Mwsh5QGCbCVaubofxveFSDIVKLCJDUOtHVLq7xu\r\n\t","AppName":"my-app-service"}},{"Time":"2023-06-19T10:02:35.4000998Z","ResourceId":"/subscriptions/5fdf4031-9274-4ab7-af52-033fa8ed754d/resourceGroups/my-resource-group/providers/Microsoft.Web/sites/my-app-service","Category":"load-test","OperationName":"GET /","Level":"Information","Properties":{"Message":"0zwWE5xL5hWstqz0GhGeb3sOE1VNImG6qAYlOm2D0yVvVv7ovkKD9dFfyyG9u1FqbRAFndEMeajzVCFvkFwBd80\rifks13Z14C6PI\\r4nbfsxsaRVlpwzA3wdSxvX4eJ9\\UqWibVSDpABgKZB4CWl5HB3\\u73cd\\u54c1\\u7f51-\\u5168\\u7403\\u6f6e\\u6d41\\u5962\\u54c1\\u7f51\\u7edc\\u96f6\\u552e\\u5546 \u003Cbr \\/\u003E\\r\\nhttp:\\/\\/www.zhenpin.com\\/ \u003Cbr \\/\u003E\\r\\n\u003Cbr \\/\u003E\\r\\n200\\u591a\\u4e2a\\u56fd\\u9645\\u4e00\\u7ebf\\u54c1\\u724c\\uff0c\\u9876\\u7ea7\\u4e70\\u624b\\u5168\\u7403\\u91c7\\u8d2d\\uff0c100%\\u6b63\\u54c1\\u4fdd\\u969c\\uff0c7\\u5929\\u65e0\\u6761\\u2026hn9p\\jiaQz1bx9dVRyI0TKWsklmu5UETVTVwPKkzqANbJSdQ3xTLGvFU45Wi5lFISow\r3gDOSMe7WH9woXvceUoCnggIC9qSWJ0tdmh\\6cIN0cIqlG\\4dGSUvTGpIfSIUaBBWc8ohTJwKpFxcyfLy\r\n\t","Details":"Z6HqhBNFk7ARwZy2M0mkYhuVybBuQD3FIlsOc7VHB7UuSE7KC2HB7G5kWd0vSXIiSNtauVGCbch3tF\rvM7HpiUDYSPE4H5aa7FT3bQL1jQnlokn27xfpUtdHwK3V7Li6eEV7YkHUcoR5J9q2bPHBL7A0FFADQ5MWAAQoSRx\\rO8y94COXwKO\\DQ5sq8KMcbUUqSaOGgKbgeo\\C9x\\WYy4QUbBMBU23AKkwW1Sbv6PUig0eY\rn2Zj6sa9uJIkS\\u73cd\\u54c1\\u7f51-\\u5168\\u7403\\u6f6e\\u6d41\\u5""" # event.get_body().decode('utf-8')
        event_json = parse_to_json(event_body)
        records = event_json.get("records", [])
        for record in records:
            try:
                extracted_record = extract_dt_record(record, self_monitoring)
                if extracted_record:
                    logs_to_be_sent_to_dt.append(extracted_record)
            except JSONDecodeError as json_e:
                self_monitoring.parsing_errors += 1
                logging.exception(
                    f"Failed to decode JSON for the record (base64 applied for safety!): {util_misc.to_base64_text(str(record))}. Exception: {json_e}",
                    "log-record-parsing-jsondecode-exception")
            except Exception as e:
                self_monitoring.parsing_errors += 1
                logging.exception(
                    f"Failed to parse log record (base64 applied for safety!): {util_misc.to_base64_text(str(record))}. Exception: {e}",
                    "log-record-parsing-exception")
    return logs_to_be_sent_to_dt


def extract_dt_record(record: Dict, self_monitoring: SelfMonitoring) -> Optional[Dict]:
    deserialize_properties(record)

    parsed_record = parse_record(record, self_monitoring)
    if not parsed_record:
        return None

    timestamp = parsed_record.get("timestamp", None)
    if is_too_old(timestamp, self_monitoring, "record"):
        return None

    return parsed_record


def is_too_old(timestamp: str, self_monitoring: SelfMonitoring, log_part: str):
    if timestamp:
        try:
            date = parser.parse(timestamp)
            # LINT won't accept any log line older than one day, 60 seconds of margin to send
            if (datetime.now(timezone.utc) - date).total_seconds() > (record_age_limit - 60):
                logging.info(f"Skipping too old {log_part} with timestamp '{timestamp}'")
                self_monitoring.too_old_records += 1
                return True
        except Exception:
            # Not much we can do when we can't parse the timestamp
            logging.exception(f"Failed to parse timestamp {timestamp}", "timestamp-parsing-exception")
            self_monitoring.parsing_errors += 1
    return False


def deserialize_properties(record: Dict):
    properties_name = next((properties for properties in azure_properties_names if properties in record.keys()), "")
    properties = record.get(properties_name, {})
    if properties and isinstance(properties, str):
        record["properties"] = parse_to_json(properties)


def parse_record(record: Dict, self_monitoring: SelfMonitoring):
    parsed_record = {
        "cloud.provider": "Azure"
    }
    extract_severity(record, parsed_record)
    extract_cloud_log_forwarder(parsed_record)

    if "resourceId" in record:
        extract_resource_id_attributes(parsed_record, record["resourceId"])

    if log_filter.should_filter_out_record(parsed_record):
        return None

    metadata_engine.apply(record, parsed_record)
    convert_date_format(parsed_record)
    category = record.get("category", "").lower()
    infer_monitored_entity_id(category, parsed_record)

    for attribute_key, attribute_value in parsed_record.items():
        if attribute_key not in ["content", "severity", "timestamp"] and attribute_value:
            string_attribute_value = attribute_value
            if not isinstance(attribute_value, str):
                string_attribute_value = str(attribute_value)
            parsed_record[attribute_key] = string_attribute_value[: attribute_value_length_limit]

    content = parsed_record.get("content", None)
    if content:
        if not isinstance(content, str):
            parsed_record["content"] = json.dumps(parsed_record["content"])
        if len(parsed_record["content"]) > content_length_limit:
            self_monitoring.too_long_content_size.append(len(parsed_record["content"]))
            trimmed_len = content_length_limit - len(DYNATRACE_LOG_INGEST_CONTENT_MARK_TRIMMED)
            parsed_record["content"] = parsed_record["content"][
                                       :trimmed_len] + DYNATRACE_LOG_INGEST_CONTENT_MARK_TRIMMED
    return parsed_record


def extract_cloud_log_forwarder(parsed_record):
    if cloud_log_forwarder:
        parsed_record["cloud.log_forwarder"] = cloud_log_forwarder


def parse_to_json(text):
    try:
        logging.info(f"Text to be parse ======== {text} *********")
        event_json = json.loads(text)
    except Exception:
        try:
            event_json = json.loads(text.replace("\'", "\""), strict=False)
            logging.info(f"Parsed event with strict mode off: {text}")
        except Exception:
            logging.info(f"Failed to parse event: {text}")
    return event_json


def convert_date_format(record):
    timestamp = record.get("timestamp", None)
    if timestamp and re.findall('[0-9]{2}/[0-9]{2}/[0-9]{4} [0-9]{2}:[0-9]{2}:[0-9]{2}', timestamp):
        record["timestamp"] = str(datetime.strptime(timestamp, '%m/%d/%Y %H:%M:%S').isoformat()) + "Z"
