import threading
from logging import getLogger

import requests

logger = getLogger("uvicorn")  # FastAPI / Uvicorn 内からの利用のため


def async_request(request: requests.Request) -> None:
    threading.Thread(target=_request, args=(request,)).start()


def _request(request: requests.Request) -> None:
    logger.info("request: %s", request.url)
    result = requests.Session().send(request.prepare())
    logger.info("response: %s", result.status_code)
