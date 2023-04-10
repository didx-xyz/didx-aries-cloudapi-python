from aiohttp import ClientResponseError
from aries_cloudcontroller import (
    AcaPyClient,
    CredRevRecordResult,
    IssuerCredRevRecord,
    IssuerRevRegRecord,
    RevRegCreateRequest,
    RevRegResult,
    RevokeRequest,
    TransactionRecord,
    TxnOrRevRegResult,
    V10CredentialExchange,
    V20CredExRecordDetail,
    V20CredExRecordIndy,
)

import pytest
from mockito import when
from app.error.cloud_api_error import CloudApiException

import app.facades.revocation_registry as rg
from tests.util.mock import get

cred_def_id = "VagGATdBsVdBeFKeoYPe7H:3:CL:141:5d211963-3478-4de4-b8b6-9072759a71c8"
cred_ex_id = "5mJRavkcQFrqgKqKKZua3z:3:CL:30:tag"
cred_id = "c7c909f4-f670-49bd-9d81-53fba6bb23b8"
max_cred_num = 32767
revocation_registry_id = "VagGATdBsVdBeFKeoYPe7H:4:VagGATdBsVdBeFKeoYPe7H:3:CL:141:QIOPN:CL_ACCUM:5d211963-3478-4de4-b8b6-9072759a71c8"
conn_id = "12345"
transaction_id = "1234"


@pytest.mark.asyncio
async def test_create_revocation_registry(mock_agent_controller: AcaPyClient):
    when(mock_agent_controller.revocation).create_registry(
        body=RevRegCreateRequest(
            credential_definition_id=cred_def_id, max_cred_num=max_cred_num
        )
    ).thenReturn(
        get(
            RevRegResult(
                result=IssuerRevRegRecord(
                    cred_def_id=cred_def_id, max_cred_num=max_cred_num
                )
            )
        )
    )
    # Success
    create_registry_result = await rg.create_revocation_registry(
        mock_agent_controller, credential_definition_id=cred_def_id
    )

    assert isinstance(create_registry_result, IssuerRevRegRecord)
    assert create_registry_result.cred_def_id == cred_def_id
    assert create_registry_result.max_cred_num == max_cred_num

    # Failure
    with pytest.raises(
        CloudApiException,
        match="Error creating revocation registry for credential with ID",
    ) as exc:
        when(mock_agent_controller.revocation).create_registry(
            body=RevRegCreateRequest(
                credential_definition_id=cred_def_id, max_cred_num=max_cred_num
            )
        ).thenReturn(get(None))
        await rg.create_revocation_registry(
            mock_agent_controller, credential_definition_id=cred_def_id
        )
    assert exc.value.status_code == 500


@pytest.mark.asyncio
async def test_get_active_revocation_registry_for_credential(
    mock_agent_controller: AcaPyClient,
):
    # Success
    when(mock_agent_controller.revocation).get_active_registry_for_cred_def(
        cred_def_id=cred_def_id
    ).thenReturn(
        get(
            RevRegResult(
                result=IssuerRevRegRecord(
                    cred_def_id=cred_def_id, max_cred_num=max_cred_num
                )
            )
        )
    )
    get_active_revocation_registry_for_credential_result = (
        await rg.get_active_revocation_registry_for_credential(
            controller=mock_agent_controller, credential_definition_id=cred_def_id
        )
    )

    assert isinstance(
        get_active_revocation_registry_for_credential_result, IssuerRevRegRecord
    )
    assert (
        get_active_revocation_registry_for_credential_result.cred_def_id == cred_def_id
    )
    assert (
        get_active_revocation_registry_for_credential_result.max_cred_num
        == max_cred_num
    )

    # Fail
    with pytest.raises(
        CloudApiException,
        match=f"Error retrieving revocation registry for credential with ID {cred_def_id}",
    ) as exc:
        when(mock_agent_controller.revocation).get_active_registry_for_cred_def(
            cred_def_id=cred_def_id
        ).thenReturn(get(None))
        await rg.get_active_revocation_registry_for_credential(
            mock_agent_controller, credential_definition_id=cred_def_id
        )
    assert exc.value.status_code == 500


@pytest.mark.asyncio
async def test_get_credential_revocation_status(mock_agent_controller: AcaPyClient):
    cred_ex_id = "db9d7025-b276-4c32-ae38-fbad41864112"
    # Success
    when(mock_agent_controller.revocation).get_revocation_status(
        cred_ex_id=cred_ex_id
    ).thenReturn(
        get(
            CredRevRecordResult(
                result=IssuerCredRevRecord(
                    cred_ex_id=cred_ex_id, cred_def_id=cred_def_id
                )
            )
        )
    )
    get_credential_revocation_status_result = await rg.get_credential_revocation_status(
        controller=mock_agent_controller, credential_exchange_id=cred_ex_id
    )
    assert isinstance(get_credential_revocation_status_result, IssuerCredRevRecord)
    assert get_credential_revocation_status_result.cred_def_id == cred_def_id
    assert get_credential_revocation_status_result.cred_ex_id == cred_ex_id

    # Fail
    with pytest.raises(
        CloudApiException,
        match=f"Error retrieving revocation status for credential definition ID {cred_def_id}",
    ) as exc:
        when(mock_agent_controller.revocation).get_revocation_status(
            cred_ex_id=cred_ex_id
        ).thenReturn(get(None))
        when(rg).get_credential_definition_id_from_exchange_id(
            controller=mock_agent_controller, credential_exchange_id=cred_ex_id
        ).thenReturn(get(cred_def_id))
        await rg.get_credential_revocation_status(
            controller=mock_agent_controller, credential_exchange_id=cred_ex_id
        )
    assert exc.value.status_code == 500


@pytest.mark.asyncio
async def test_publish_revocation_registry_on_ledger(
    mock_agent_controller: AcaPyClient,
):

    # With endorsement
    when(mock_agent_controller.revocation).publish_rev_reg_def(
        rev_reg_id=revocation_registry_id,
        conn_id=conn_id,
        create_transaction_for_endorser=True,
    ).thenReturn(
        get(
            TxnOrRevRegResult(
                sent=None,
                txn=TransactionRecord(
                    connection_id=conn_id, transaction_id=transaction_id
                ),
            )
        )
    )

    publish_revocation_registry_on_ledger_result = (
        await rg.publish_revocation_registry_on_ledger(
            controller=mock_agent_controller,
            revocation_registry_id=revocation_registry_id,
            connection_id=conn_id,
            create_transaction_for_endorser=True,
        )
    )
    assert isinstance(publish_revocation_registry_on_ledger_result, TransactionRecord)
    assert publish_revocation_registry_on_ledger_result.connection_id == conn_id
    assert publish_revocation_registry_on_ledger_result.transaction_id == transaction_id

    # Without endorsement
    when(mock_agent_controller.revocation).publish_rev_reg_def(
        rev_reg_id=revocation_registry_id,
        conn_id=None,
        create_transaction_for_endorser=False,
    ).thenReturn(
        get(
            RevRegResult(
                result=IssuerRevRegRecord(
                    cred_def_id=cred_def_id, max_cred_num=max_cred_num
                )
            )
        )
    )

    publish_revocation_registry_on_ledger_result = (
        await rg.publish_revocation_registry_on_ledger(
            controller=mock_agent_controller,
            revocation_registry_id=revocation_registry_id,
            connection_id=conn_id,
            create_transaction_for_endorser=False,
        )
    )
    assert isinstance(publish_revocation_registry_on_ledger_result, IssuerRevRegRecord)
    assert publish_revocation_registry_on_ledger_result.cred_def_id == cred_def_id
    assert publish_revocation_registry_on_ledger_result.max_cred_num == max_cred_num

    # Fail
    with pytest.raises(
        CloudApiException,
        match="Failed to publish revocation registry to ledger",
    ) as exc:
        when(mock_agent_controller.revocation).publish_rev_reg_def(
            rev_reg_id=revocation_registry_id,
            conn_id=None,
            create_transaction_for_endorser=False,
        ).thenReturn(get(None))
        publish_revocation_registry_on_ledger_result = (
            await rg.publish_revocation_registry_on_ledger(
                controller=mock_agent_controller,
                revocation_registry_id=revocation_registry_id,
                connection_id=conn_id,
                create_transaction_for_endorser=False,
            )
        )
    assert exc.value.status_code == 500


@pytest.mark.asyncio
async def test_publish_revocation_entry_to_ledger(mock_agent_controller: AcaPyClient):
    # Success
    when(mock_agent_controller.revocation).publish_rev_reg_entry(
        rev_reg_id=revocation_registry_id,
        conn_id=None,
        create_transaction_for_endorser=False,
    ).thenReturn(
        get(
            RevRegResult(
                result=IssuerRevRegRecord(
                    cred_def_id=cred_def_id, max_cred_num=max_cred_num
                )
            )
        )
    )

    publish_revocation_entry_to_ledger_result = (
        await rg.publish_revocation_entry_to_ledger(
            controller=mock_agent_controller,
            connection_id=conn_id,
            credential_definition_id=cred_def_id,
            revocation_registry_id=revocation_registry_id,
            create_transaction_for_endorser=False,
        )
    )

    assert isinstance(publish_revocation_entry_to_ledger_result, IssuerRevRegRecord)
    assert publish_revocation_entry_to_ledger_result.cred_def_id == cred_def_id
    assert publish_revocation_entry_to_ledger_result.max_cred_num == max_cred_num

    # Error insufficient params supplied
    with pytest.raises(
        CloudApiException,
        match="Please, provide either a revocation registry id OR credential definition id.",
    ) as exc:
        await rg.publish_revocation_entry_to_ledger(
            controller=mock_agent_controller,
            connection_id=conn_id,
            create_transaction_for_endorser=False,
        )
    assert exc.value.status_code == 400

    # Error no result
    with pytest.raises(
        CloudApiException,
        match="Failed to publish revocation entry to ledger.\nNone",
    ) as exc:
        when(mock_agent_controller.revocation).publish_rev_reg_entry(
            rev_reg_id=revocation_registry_id,
            conn_id=None,
            create_transaction_for_endorser=False,
        ).thenReturn(get(None))
        await rg.publish_revocation_entry_to_ledger(
            controller=mock_agent_controller,
            connection_id=conn_id,
            credential_definition_id=cred_def_id,
            revocation_registry_id=revocation_registry_id,
            create_transaction_for_endorser=False,
        )
    assert exc.value.status_code == 500


@pytest.mark.asyncio
async def test_revoke_credential(mock_agent_controller: AcaPyClient):
    # Success
    when(mock_agent_controller.revocation).revoke_credential(
        body=RevokeRequest(cred_ex_id=cred_id, publish=False)
    ).thenReturn(get({}))

    when(mock_agent_controller.revocation).get_active_registry_for_cred_def(
        cred_def_id=cred_def_id
    ).thenReturn(
        get(
            RevRegResult(
                result=IssuerRevRegRecord(
                    cred_def_id=cred_def_id, max_cred_num=max_cred_num
                )
            )
        )
    )
    when(mock_agent_controller.revocation).publish_rev_reg_entry(
        rev_reg_id=revocation_registry_id,
        conn_id=None,
        create_transaction_for_endorser=False,
    ).thenRaise(ClientResponseError({}, ("x", "x")))

    when(rg).endorser_revoke().thenReturn(get(None))

    revoke_credential_result = await rg.revoke_credential(
        controller=mock_agent_controller,
        credential_definition_id=cred_def_id,
        credential_exchange_id=cred_id,
        auto_publish_to_ledger=False,
    )

    assert revoke_credential_result is None


@pytest.mark.asyncio
async def test_get_credential_definition_id_from_exchange_id(
    mock_agent_controller: AcaPyClient,
):
    # Success v1
    when(mock_agent_controller.issue_credential_v1_0).get_record(
        cred_ex_id=cred_ex_id
    ).thenReturn(
        get(
            V10CredentialExchange(
                credential_exchange_id=cred_ex_id, credential_definition_id=cred_def_id
            )
        )
    )

    get_credential_definition_id_from_exchange_id_result = (
        await rg.get_credential_definition_id_from_exchange_id(
            controller=mock_agent_controller, credential_exchange_id=cred_ex_id
        )
    )

    assert get_credential_definition_id_from_exchange_id_result
    assert isinstance(get_credential_definition_id_from_exchange_id_result, str)
    assert get_credential_definition_id_from_exchange_id_result == cred_def_id

    # Success v2
    when(mock_agent_controller.issue_credential_v1_0).get_record(
        cred_ex_id=cred_ex_id
    ).thenRaise(ClientResponseError({}, ("x", "x")))
    when(mock_agent_controller.issue_credential_v2_0).get_record(
        cred_ex_id=cred_ex_id
    ).thenReturn(
        get(
            V20CredExRecordDetail(
                indy=V20CredExRecordIndy(rev_reg_id=revocation_registry_id)
            )
        )
    )

    get_credential_definition_id_from_exchange_id_result = (
        await rg.get_credential_definition_id_from_exchange_id(
            controller=mock_agent_controller, credential_exchange_id=cred_ex_id
        )
    )

    assert get_credential_definition_id_from_exchange_id_result
    assert isinstance(get_credential_definition_id_from_exchange_id_result, str)
    assert get_credential_definition_id_from_exchange_id_result == cred_def_id

    # Not found
    when(mock_agent_controller.issue_credential_v1_0).get_record(
        cred_ex_id=cred_ex_id
    ).thenRaise(ClientResponseError({}, ("y", "y")))
    when(mock_agent_controller.issue_credential_v2_0).get_record(
        cred_ex_id=cred_ex_id
    ).thenRaise(ClientResponseError({}, ("z", "z")))

    get_credential_definition_id_from_exchange_id_result = (
        await rg.get_credential_definition_id_from_exchange_id(
            controller=mock_agent_controller, credential_exchange_id=cred_ex_id
        )
    )

    assert get_credential_definition_id_from_exchange_id_result is None
