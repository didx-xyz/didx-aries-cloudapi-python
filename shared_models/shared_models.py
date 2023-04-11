from enum import Enum
from typing import Any, Generic, List, Optional, Dict, TypeVar, Union, Tuple

from typing_extensions import TypedDict, Literal

from aries_cloudcontroller import (
    ConnRecord,
    IndyProof,
    IndyProofRequest,
    InvitationMessage,
    V10PresentationExchange,
    V10CredentialExchange,
    V20CredExRecord,
    V20PresExRecord,
)
from pydantic import BaseModel
from pydantic.generics import GenericModel

WEBHOOK_TOPIC_ALL = "ALL_WEBHOOKS"

AcaPyTopics = Literal[
    "basicmessages",
    "connections",
    "endorse_transaction",
    "forward",
    "issue_credential",
    "issue_credential_v2_0",
    "issue_credential_v2_0_dif",
    "issue_credential_v2_0_indy",
    "issuer_cred_rev",
    "out_of_band",
    "ping",
    "present_proof",
    "present_proof_v2_0",
    "revocation_registry",
]

CloudApiTopics = Literal[
    "basic-messages",
    "connections",
    "proofs",
    "credentials",
    "endorsements",
    "oob",
    "revocation",
]

# Mapping of acapy topic names to their respective cloud api topic names
topic_mapping: Dict[AcaPyTopics, CloudApiTopics] = {
    "basicmessages": "basic-messages",
    "connections": "connections",
    "endorse_transaction": "endorsements",
    "issue_credential": "credentials",
    "issue_credential_v2_0": "credentials",
    "endorse_transaction": "endorsements",
    "revocation_registry": "revocation",
    "out_of_band": "oob",
    "present_proof": "proofs",
    "present_proof_v2_0": "proofs",
}


class PresentProofProtocolVersion(Enum):
    v1 = "v1"
    v2 = "v2"


class IssueCredentialProtocolVersion(Enum):
    v1 = "v1"
    v2 = "v2"


def pres_id_no_version(proof_id: str) -> str:
    if proof_id.startswith("v2-") or proof_id.startswith("v1-"):
        return proof_id[3:]
    else:
        raise ValueError("proof_id must start with prefix v1- or v2-")


def string_to_bool(verified: Optional[str]) -> Optional[bool]:
    if verified == "true":
        return True
    elif verified == "false":
        return False
    else:
        return None


def v1_presentation_state_to_rfc_state(state: Optional[str]) -> Optional[str]:
    translation_dict = {
        "abandoned": "abandoned",
        "done": "done",
        "presentation_acked": "done",
        "presentation_received": "presentation-received",
        "presentation_sent": "presentation-sent",
        "proposal_received": "proposal-received",
        "proposal_sent": "proposal-sent",
        "request_received": "request-received",
        "request_sent": "request-sent",
        "verified": "done",
    }

    if not state or not state in translation_dict:
        return None

    return translation_dict[state]


class Endorsement(BaseModel):
    state: Literal[
        "request-received",
        "request-sent",
        "transaction-acked",
        "transaction-cancelled",
        "transaction-created",
        "transaction-endorsed",
        "transaction-refused",
        "transaction-resent",
        "transaction-resent_received",
    ]
    transaction_id: str


class ServiceDecorator(TypedDict):
    endpoint: str
    recipient_keys: List[str]
    routing_keys: Optional[List[str]]


class Oob(BaseModel):
    attach_thread_id: Optional[str] = None
    connection_id: Optional[str] = None
    created_at: Optional[str] = None
    invi_msg_id: Optional[str] = None
    invitation: InvitationMessage = None
    multi_use: Optional[bool] = False
    oob_id: Optional[str] = None
    our_recipient_key: Optional[str] = None
    our_recipient_key: Optional[str] = None
    role: Optional[Literal["sender", "receiver"]] = None
    state: Optional[
        Literal[
            "initial",
            "prepare-response",
            "await-response",
            "reuse-not-accepted",
            "reuse-accepted",
            "done",
        ]
    ] = None
    trace: Optional[bool] = None
    updated_at: Optional[str] = None


# TODO: Import this from aca-py instead of typing this here
# when aca-py version is >=0.7.5
class OobRecord(BaseModel):
    attach_thread_id: Optional[str] = None
    connection_id: Optional[str] = None
    created_at: Optional[str] = None
    invi_msg_id: Optional[str]
    invitation: Optional[InvitationMessage] = None
    oob_id: Optional[str] = None
    our_recipient_key: Optional[str] = None
    role: Optional[Literal["sender", "receiver"]] = None
    state: Optional[
        Literal[
            "initial",
            "prepare-response",
            "await-response",
            "reuse-not-accepted",
            "reuse-accepted",
            "done",
        ]
    ] = None
    their_service: Optional[ServiceDecorator] = None
    trace: Optional[bool] = None
    updated_at: Optional[str] = None


class Connection(BaseModel):
    alias: Optional[str] = None
    connection_id: Optional[str] = None
    connection_protocol: Optional[Literal["connections/1.0", "didexchange/1.0"]] = None
    created_at: Optional[str] = None
    error_msg: Optional[str] = None
    invitation_key: Optional[str] = None
    invitation_mode: Optional[Literal["once", "multi", "static"]] = None
    invitation_msg_id: Optional[str] = None
    my_did: Optional[str]
    state: Optional[str] = None  # did-exchange state
    their_did: Optional[str] = None
    their_label: Optional[str] = None
    their_public_did: Optional[str] = None
    their_role: Optional[Literal["invitee", "requester", "inviter", "responder"]] = None
    updated_at: Optional[str] = None


class CredentialExchange(BaseModel):
    # Attributes can be None in proposed state
    attributes: Optional[Dict[str, str]] = None
    # Connection id can be None in connectionless exchanges
    connection_id: Optional[str] = None
    created_at: str
    credential_definition_id: Optional[str]
    credential_id: str
    error_msg: Optional[str] = None
    protocol_version: IssueCredentialProtocolVersion
    role: Literal["issuer", "holder"]
    schema_id: Optional[str]
    state: Optional[
        Literal[
            "abandoned",
            "credential-issued",
            "credential-received",
            "done",
            "offer-received",
            "offer-sent",
            "proposal-received",
            "proposal-sent",
            "request-received",
            "request-sent",
        ]
    ] = None
    # Attributes can be None in proposed state
    # Connection id can be None in connectionless exchanges
    thread_id: Optional[str] = None
    updated_at: str


class PresentationExchange(BaseModel):
    connection_id: Optional[str] = None
    created_at: str
    error_msg: Optional[str] = None
    parent_thread_id: Optional[str] = None
    presentation: Optional[IndyProof] = None
    presentation_request: Optional[IndyProofRequest] = None
    proof_id: str
    protocol_version: PresentProofProtocolVersion
    role: Literal["prover", "verifier"]
    state: Optional[
        Literal[
            "abandoned",
            "done",
            "presentation-received",
            "presentation-sent",
            "proposal-received",
            "proposal-sent",
            "request-received",
            "request-sent",
        ]
    ] = None
    thread_id: Optional[str] = None
    updated_at: Optional[str] = None
    verified: Optional[bool] = None


class BasicMessage(BaseModel):
    connection_id: str
    content: str
    message_id: str
    sent_time: str
    state: Optional[Literal["received"]] = None


PayloadType = TypeVar("PayloadType", bound=BaseModel)


class TopicItem(GenericModel, Generic[PayloadType]):
    topic: str
    wallet_id: str
    origin: str
    payload: PayloadType


class RedisItem(TypedDict):
    acapy_topic: str
    topic: str
    wallet_id: str
    origin: str
    payload: Dict[str, Any]


def presentation_record_to_model(
    record: Union[V20PresExRecord, V10PresentationExchange]
) -> PresentationExchange:
    if isinstance(record, V20PresExRecord):
        return PresentationExchange(
            connection_id=record.connection_id,
            created_at=record.created_at,
            error_msg=record.error_msg,
            parent_thread_id=record.pres_request.id if record.pres_request else None,
            presentation=IndyProof(**record.by_format.pres["indy"])
            if record.by_format.pres
            else None,
            presentation_request=IndyProofRequest(
                **record.by_format.pres_request["indy"]
            ),
            proof_id="v2-" + str(record.pres_ex_id),
            protocol_version=PresentProofProtocolVersion.v2.value,
            role=record.role,
            state=record.state,
            thread_id=record.thread_id,
            updated_at=record.updated_at,
            verified=string_to_bool(record.verified),
        )
    elif isinstance(record, V10PresentationExchange):
        return PresentationExchange(
            connection_id=record.connection_id,
            created_at=record.created_at,
            error_msg=record.error_msg,
            parent_thread_id=record.presentation_request_dict.id
            if record.presentation_request_dict
            else None,
            presentation=record.presentation,
            presentation_request=record.presentation_request,
            proof_id="v1-" + str(record.presentation_exchange_id),
            protocol_version=PresentProofProtocolVersion.v1.value,
            role=record.role,
            state=v1_presentation_state_to_rfc_state(record.state),
            thread_id=record.thread_id,
            updated_at=record.updated_at,
            verified=string_to_bool(record.verified),
        )
    else:
        raise ValueError("Record format unknown.")


def conn_record_to_connection(connection_record: ConnRecord):
    return Connection(
        alias=connection_record.alias,
        connection_id=connection_record.connection_id,
        connection_protocol=connection_record.connection_protocol,
        created_at=connection_record.created_at,
        error_msg=connection_record.error_msg,
        invitation_key=connection_record.invitation_key,
        invitation_mode=connection_record.invitation_mode,
        invitation_msg_id=connection_record.invitation_msg_id,
        my_did=connection_record.my_did,
        state=connection_record.rfc23_state,
        their_did=connection_record.their_did,
        their_label=connection_record.their_label,
        their_public_did=connection_record.their_public_did,
        their_role=connection_record.their_role,
        updated_at=connection_record.updated_at,
    )


def credential_record_to_model_v1(record: V10CredentialExchange) -> CredentialExchange:
    attributes = attributes_from_record_v1(record)

    return CredentialExchange(
        attributes=attributes,
        connection_id=record.connection_id,
        created_at=record.created_at,
        credential_definition_id=record.credential_definition_id,
        credential_id=f"v1-{record.credential_exchange_id}",
        error_msg=record.error_msg,
        protocol_version=IssueCredentialProtocolVersion.v1,
        role=record.role,
        schema_id=record.schema_id,
        state=v1_credential_state_to_rfc_state(record.state),
        thread_id=record.thread_id,
        updated_at=record.updated_at,
    )


def attributes_from_record_v1(
    record: V10CredentialExchange,
) -> Optional[Dict[str, str]]:
    preview = None

    if (
        record.credential_proposal_dict
        and record.credential_proposal_dict.credential_proposal
    ):
        preview = record.credential_proposal_dict.credential_proposal

    return {attr.name: attr.value for attr in preview.attributes} if preview else None


def v1_credential_state_to_rfc_state(state: Optional[str]) -> Optional[str]:
    translation_dict = {
        "abandoned": "abandoned",
        "credential_acked": "done",
        "credential_issued": "credential-issued",
        "credential_received": "credential-received",
        "done": "done",
        "offer_received": "offer-received",
        "offer_sent": "offer-sent",
        "proposal_received": "proposal-received",
        "proposal_sent": "proposal-sent",
        "request_received": "request-received",
        "request_sent": "request-sent",
    }

    if not state or state not in translation_dict:
        return None

    return translation_dict[state]


def credential_record_to_model_v2(record: V20CredExRecord) -> CredentialExchange:
    attributes = attributes_from_record_v2(record)
    schema_id, credential_definition_id = schema_cred_def_from_record(record)

    return CredentialExchange(
        attributes=attributes,
        connection_id=record.connection_id,
        created_at=record.created_at,
        credential_definition_id=credential_definition_id,
        credential_id=f"v2-{record.cred_ex_id}",
        error_msg=record.error_msg,
        protocol_version=IssueCredentialProtocolVersion.v2,
        role=record.role,
        schema_id=schema_id,
        state=record.state,
        thread_id=record.thread_id,
        updated_at=record.updated_at,
    )


def schema_cred_def_from_record(
    record: V20CredExRecord,
) -> Tuple[Optional[str], Optional[str]]:
    schema_id = None
    credential_definition_id = None

    if record.by_format and record.by_format.cred_offer:
        indy = record.by_format.cred_offer.get("indy", {})
        schema_id = indy.get("schema_id", None)
        credential_definition_id = indy.get("cred_def_id", None)

    elif record.by_format and record.by_format.cred_proposal:
        indy = record.by_format.cred_proposal.get("indy", {})
        schema_id = indy.get("schema_id", None)
        credential_definition_id = indy.get("cred_def_id", None)

    return schema_id, credential_definition_id


def attributes_from_record_v2(record: V20CredExRecord) -> Optional[Dict[str, str]]:
    preview = None

    if record.cred_preview:
        preview = record.cred_preview
    elif record.cred_offer and record.cred_offer.credential_preview:
        preview = record.cred_offer.credential_preview
    elif record.cred_proposal and record.cred_proposal.credential_preview:
        preview = record.cred_proposal.credential_preview

    return {attr.name: attr.value for attr in preview.attributes} if preview else None
