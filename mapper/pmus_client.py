import json

import grpc
from google.protobuf.json_format import MessageToDict, ParseDict

from mapper.paths import KEYS_PATH
from mapper.pmus_auth import GatewayAuth
from polymarket.v1 import refdata_pb2, refdata_pb2_grpc

STATES = {
    "prod": ("pmx-prod.us.auth0.com", "https://api.prod.polymarketexchange.com"),
    "preprod": ("pmx-preprod.us.auth0.com", "https://api.preprod.polymarketexchange.com"),
}
LIST_INSTRUMENTS = "/api/v1beta1/list_instruments"
GRPC_TIMEOUT = 30.0


def load_pmus_auth(state="prod", keys_path=KEYS_PATH):
    with open(keys_path) as handle:
        keys = json.load(handle)
    try:
        creds = keys["polymarket_public"][state]
        (auth_domain, api_base_url) = STATES[state]
    except KeyError as error:
        raise RuntimeError(f'{keys_path} needs ["polymarket_public"]["{state}"] with client_id, private_key_path, participant_id') from error
    return GatewayAuth(
        client_id=creds["client_id"],
        auth_domain=auth_domain,
        api_base_url=api_base_url,
        private_key_path=creds["private_key_path"],
        participant_id=creds["participant_id"],
    )


def _drop_none(value):
    if isinstance(value, dict):
        return {k: _drop_none(v) for (k, v) in value.items() if v is not None}
    if isinstance(value, list):
        return [_drop_none(v) for v in value if v is not None]
    return value


class PmusClient:

    def __init__(self, state="prod", keys_path=KEYS_PATH):
        self.auth = load_pmus_auth(state, keys_path)
        self.channel = grpc.secure_channel(
            self.auth.get_grpc_addr(),
            grpc.ssl_channel_credentials(),
            options=[("grpc.max_receive_message_length", 32 * 1024 * 1024)],
        )
        self.stub = refdata_pb2_grpc.RefDataAPIStub(self.channel)

    def post(self, path, body=None):
        if path != LIST_INSTRUMENTS:
            raise NotImplementedError(f"{path} is not part of the mapper's read surface")
        payload = json.loads(body) if isinstance(body, str) else dict(body or {})
        request = ParseDict(_drop_none(payload), refdata_pb2.ListInstrumentsRequest())
        try:
            response = self.stub.ListInstruments(request, metadata=self.auth.get_grpc_metadata(), timeout=GRPC_TIMEOUT)
        except grpc.RpcError as error:
            raise RuntimeError(f"ListInstruments failed -- {error.code()}: {error.details()}") from error
        return MessageToDict(response, preserving_proto_field_name=True)

