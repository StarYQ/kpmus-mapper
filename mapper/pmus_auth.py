import httpx
import jwt
import threading
import time
import uuid
import logging
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class GatewayAuth:

    def __init__(self, client_id, auth_domain, api_base_url, private_key_path, participant_id):
        self.client_id = client_id
        self.auth_domain = auth_domain
        self.api_base_url = api_base_url
        self.participant_id = participant_id
        self.token_url = f"https://{auth_domain}/oauth/token"

        with open(private_key_path, "r") as f:
            self.private_key = f.read()

        self.token = None
        self.token_expiry = 0
        self._lock = threading.Lock()

    def _create_client_assertion(self):
        now = time.time()
        payload = {
            "iss": self.client_id,
            "sub": self.client_id,
            "aud": self.token_url,
            "iat": int(now),
            "exp": int(now + 300),
            "jti": str(uuid.uuid4())
        }
        return jwt.encode(payload, self.private_key, algorithm="RS256")

    def _request_token(self):
        assertion = self._create_client_assertion()
        body = {
            "client_id": self.client_id,
            "client_assertion_type": "urn:ietf:params:oauth:client-assertion-type:jwt-bearer",
            "client_assertion": assertion,
            "audience": self.api_base_url,
            "grant_type": "client_credentials"
        }

        try:
            with httpx.Client(http2=True) as client:
                response = client.post(
                    self.token_url,
                    json=body,
                    timeout=15.0
                )

            if (response.status_code not in range(200, 300)):
                logger.error(f"Token request failed: {response.status_code} {response.text}")
                raise Exception(f"Token request failed: {response.status_code}")

            data = response.json()
            with self._lock:
                self.token = data["access_token"]
                self.token_expiry = time.time() + data.get("expires_in", 86400)

        except Exception as e:
            logger.error(f"Failed to request access token: {e}")
            raise

    def get_access_token(self):
        with self._lock:
            if (not self.token) or (time.time() >= self.token_expiry - 60):
                needs_refresh = True
            else:
                needs_refresh = False

        if (needs_refresh):
            self._request_token()

        with self._lock:
            return self.token

    def get_grpc_addr(self):
        parsed = urlparse(self.api_base_url)
        host = parsed.netloc or parsed.path
        if host.startswith("api."):
            return f"grpc-api.{host[4:]}:443"
        return f"grpc-api.{host}:443"

    def get_grpc_metadata(self):
        token = self.get_access_token()
        return [
            ("authorization", f"Bearer {token}"),
            ("x-participant-id", self.participant_id),
        ]
