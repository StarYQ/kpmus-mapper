import base64
import json
import time
from urllib.parse import urlencode

import httpx
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

from mapper.paths import KEYS_PATH
BASE_URL = "https://external-api.kalshi.com"
API_ROOT = "/trade-api/v2"
USER_AGENT = "curl/8.4.0"
REST_TIMEOUT = httpx.Timeout(connect=10.0, read=30.0, write=10.0, pool=10.0)


def load_kalshi_credentials(path=KEYS_PATH):
    with open(path) as handle:
        keys = json.load(handle)
    block = keys.get("kalshi") or {}
    client_id = block.get("client_id")
    key_path = block.get("private_key_path")
    if (not client_id) or (not key_path):
        raise RuntimeError(f'{path}["kalshi"] needs both "client_id" and "private_key_path"')
    with open(key_path, "rb") as handle:
        private_key = serialization.load_pem_private_key(handle.read(), password=None)
    return (client_id, private_key)


class KalshiReadClient:

    def __init__(self, base_url=BASE_URL, keys_path=KEYS_PATH):
        (self.client_id, self.private_key) = load_kalshi_credentials(keys_path)
        self.base_url = base_url

    def _sign(self, timestamp, method, path):
        message = f"{timestamp}{method}{path}".encode("utf-8")
        signature = self.private_key.sign(
            message,
            padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.DIGEST_LENGTH),
            hashes.SHA256(),
        )
        return base64.b64encode(signature).decode("utf-8")

    def _headers(self, method, path):
        timestamp = str(int(time.time() * 1000))
        return {
            "KALSHI-ACCESS-KEY": self.client_id,
            "KALSHI-ACCESS-SIGNATURE": self._sign(timestamp, method, path),
            "KALSHI-ACCESS-TIMESTAMP": timestamp,
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
        }

    def get(self, route, params=None):
        path = API_ROOT + route
        url = self.base_url + path
        query = urlencode([(k, v) for (k, v) in (params or {}).items() if (v is not None)], doseq=True)
        if query:
            url = f"{url}?{query}"

        response = httpx.get(url, headers=self._headers("GET", path), timeout=REST_TIMEOUT)
        if (response.status_code != 200):
            raise RuntimeError(f"GET {path}: status {response.status_code}: {response.text[:300]}")
        return response.json()

