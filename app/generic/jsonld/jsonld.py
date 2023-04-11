import logging
from typing import Any, Dict, Optional
from aiohttp import ClientResponseError

from aries_cloudcontroller import (
    AcaPyClient,
    Doc,
    SignRequest,
    SignResponse,
    SignatureOptions,
    VerifyResponse,
)
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from uplink import (
    Consumer,
    Body,
    post,
    returns,
    json,
)

from app.dependencies import agent_selector
from app.error.cloud_api_error import CloudApiException

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/generic/jsonld", tags=["jsonld"])


class JsonLdSignRequest(BaseModel):
    credential_id: Optional[str]
    credential: Optional[Dict[str, Any]]
    verkey: Optional[str] = None
    pub_did: Optional[str] = None
    signature_options: Optional[SignatureOptions] = None


class JsonLdVerifyRequest(BaseModel):
    doc: Dict[str, Any]
    public_did: Optional[str] = None
    verkey: Optional[str] = None


@router.post("/sign", response_model=SignResponse)
async def sign_jsonld(
    body: JsonLdSignRequest,
    aries_controller: AcaPyClient = Depends(agent_selector),
):
    """
    Sign a JSON-LD structure
    """

    if body.pub_did and body.verkey:
        raise CloudApiException(
            "Please provide either or neither, but not both, public did of the verkey or the verkey for the document.",
            418,
        )
    try:
        if body.verkey:
            verkey = body.verkey
        else:
            if body.pub_did:
                pub_did = body.pub_did
            else:
                pub_did = (await aries_controller.wallet.get_public_did()).result.did
            verkey = (await aries_controller.ledger.get_did_verkey(did=pub_did)).verkey

        if not body.credential:
            if body.credential_id:
                # Can this ever be correct as in are there jsonLD credential potentially being returned?
                credential = (
                    await aries_controller.credentials.get_record(
                        credential_id=body.credential_id
                    )
                ).dict()
            else:
                raise CloudApiException(
                    "Cannot retrieve credential without credential ID."
                )
        else:
            credential = body.credential

        return await aries_controller.jsonld.sign(
            body=SignRequest(
                doc=Doc(credential=credential, options=body.signature_options),
                verkey=verkey,
            )
        )
    except ClientResponseError as e:
        raise CloudApiException(f"Failed to sign payload. {e['message']}")


@router.post("/verify", status_code=204)
async def verify_jsonld(
    body: JsonLdVerifyRequest,
    aries_controller: AcaPyClient = Depends(agent_selector),
):
    """
    Verify a JSON-LD structure
    """

    if not (bool(body.public_did) != bool(body.verkey)):
        raise CloudApiException(
            "Please provide either, but not both, public did of the verkey or the verkey for the document.",
            418,
        )
    try:
        if not body.verkey:
            verkey = (
                await aries_controller.ledger.get_did_verkey(did=body.public_did)
            ).verkey
        else:
            verkey = body.verkey

        # NOTE: Wrong/incomplete aca-py openAPI spec results in wrong/overly-strict model for controller endpoint
        # Hence, override it here
        # Custom Override api endpoint that is incorrect in aca-py
        class JsonldApi(Consumer):
            async def verify(
                self, *, body: Optional[JsonLdVerifyRequest] = None
            ) -> VerifyResponse:
                """Verify a JSON-LD structure."""
                return await self.__verify(
                    body=body,
                )

            @returns.json
            @json
            @post("/jsonld/verify")
            def __verify(self, *, body: Body(type=JsonLdVerifyRequest) = {}) -> VerifyResponse:
                """Internal uplink method for verify"""

        aries_controller.jsonld = JsonldApi(
            base_url=aries_controller.base_url, client=aries_controller.client
        )
        jsonld_verify_response = await aries_controller.jsonld.verify(
            body=JsonLdVerifyRequest(doc=body.doc, verkey=verkey)
        )
        if not jsonld_verify_response.valid:
            raise CloudApiException(
                f"Failed to verify payload with: {jsonld_verify_response.error}", 422
            )
    except ClientResponseError as e:
        raise CloudApiException(f"Failed to verify payload. {e.message}")
