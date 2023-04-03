import base64
import json
import time
from typing import Any, Dict

import jwt
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

from hummingbot.core.web_assistant.auth import AuthBase
from hummingbot.core.web_assistant.connections.data_types import RESTMethod, RESTRequest, WSRequest


class EntropyAuth(AuthBase):

    def __init__(self, uid: str, apikey_id: str, private_key: str):
        self.uid = uid
        self.apikey_id = apikey_id
        self.private_key = base64.b64decode(private_key)
        self.uuid = None

    async def rest_authenticate(self, request: RESTRequest) -> RESTRequest:
        if request.method == RESTMethod.POST:
            request.data = self.construct_request_body(request.data)
        else:
            request.params = self.construct_request_body(request.params)
        print(request.data)
        return request

    async def ws_authenticate(self, request: WSRequest) -> WSRequest:
        return request

    def construct_request_body(self, data):
        pay_load = {
            "uid": self.uid,
            "apikey_id": self.apikey_id,
            "data": data
        }
        jwt_token = jwt.encode(pay_load, self.private_key, algorithm="RS256")
        if type(jwt_token) != str:
            jwt_token = jwt_token.decode('utf-8')
        request_body = {
            "user_jwt": jwt_token
        }
        return json.dumps(request_body)

    def ws_login_parameters(self) -> Dict[str, Any]:
        cur = int(time.time() * 1000)
        return {
            "identifier": json.dumps({"handler": "AuthHandler"}),
            "command": "message",
            "data": json.dumps({
                "action": "login",
                "uuid": "69ac1055-147f-460d-b170-5e035bbde74f",
                "args": {},
                "header": {
                    "uid": self.uid,
                    "api_key": self.apikey_id,
                    "signature": self.ws_generate_signature(cur=cur),
                    "nonce": cur,
                    "verb": "GET",
                    "path": "/ws/v1"
                }
            })
        }

    def ws_generate_signature(self, cur: str) -> str:
        private_key = serialization.load_pem_private_key(
            self.private_key.encode('ascii'),
            password=None,
            backend=default_backend()
        )
        path = "GET|/ws/v1|{}|".format(cur)
        sign = private_key.sign(
            path.encode('utf-8'),
            padding.PKCS1v15(),
            hashes.SHA256()
        )
        signature = base64.b64encode(sign).decode()
        return signature

    def header_for_authentication(self) -> Dict[str, str]:
        return {"Content-Type": "application/json"}
