from aries_cloudcontroller import AcaPyClient
import pytest
import time
# import asyncio
from assertpy import assert_that
from httpx import AsyncClient


from app.tests.util.webhooks import (
    check_webhook_state,
)

# When using the default module scoped fixture in ./conftest.py test_oob_connect_via_public_did fails
# Setting temporary event_loop override for tests in this file.
# @pytest.fixture(scope="session")
# def event_loop():
#     loop = asyncio.get_event_loop_policy().new_event_loop()
#     yield loop
#     loop.close()


@pytest.mark.asyncio
async def test_create_invitation_oob(
    bob_member_client: AsyncClient,
):

    invitation_response = await bob_member_client.post(
        "/generic/oob/create-invitation", json={"create_connection": True}
    )
    assert_that(invitation_response.status_code).is_equal_to(200)
    invitation = invitation_response.json()

    assert_that(invitation).contains("invi_msg_id", "invitation", "invitation_url")
    assert_that(invitation["invitation"]).contains("@id", "services")


@pytest.mark.asyncio
async def test_accept_invitation_oob(
    bob_member_client: AsyncClient,
    alice_member_client: AsyncClient,
    alice_acapy_client: AcaPyClient,
):
    invitation_response = await bob_member_client.post(
        "/generic/oob/create-invitation",
        json={
            "create_connection": True,
            "use_public_did": False,
            "handshake_protocols": ["https://didcomm.org/didexchange/1.0"],
        },
    )
    assert_that(invitation_response.status_code).is_equal_to(200)
    invitation = (invitation_response.json())["invitation"]

    invitation["id"] = invitation.pop("@id")
    invitation["type"] = invitation.pop("@type")
    accept_response = await alice_member_client.post(
        "/generic/oob/accept-invitation",
        json={"invitation": invitation},
    )

    oob_record = accept_response.json()

    connection_record = await alice_acapy_client.connection.get_connection(
        conn_id=oob_record["connection_id"]
    )

    assert_that(accept_response.status_code).is_equal_to(200)
    assert_that(oob_record).contains("created_at", "oob_id", "invitation")
    assert_that(connection_record.connection_protocol).contains("didexchange/1.0")


@pytest.mark.asyncio
async def test_oob_connect_via_public_did(
    bob_member_client: AsyncClient,
    faber_client: AsyncClient,
    faber_acapy_client: AcaPyClient,
):
    time.sleep(10)

    faber_public_did = await faber_acapy_client.wallet.get_public_did()
    connect_response = await bob_member_client.post(
        "/generic/oob/connect-public-did",
        json={"public_did": faber_public_did.result.did},
    )
    bob_oob_record = connect_response.json()

    assert check_webhook_state(
        client=bob_member_client,
        topic="connections",
        filter_map={
            "state": "request-sent",
            "connection_id": bob_oob_record["connection_id"],
        },
    )

    assert_that(bob_oob_record).has_their_public_did(faber_public_did.result.did)
