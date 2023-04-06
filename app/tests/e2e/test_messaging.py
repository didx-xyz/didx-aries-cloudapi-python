import pytest
from assertpy.assertpy import assert_that
from httpx import AsyncClient

from app.generic.messaging import Message, TrustPingMsg

from app.tests.util.member_personas import (
    BobAliceConnect,
)


@pytest.mark.asyncio()
async def test_send_trust_ping(
    bob_and_alice_connection: BobAliceConnect, alice_member_client: AsyncClient
):
    trustping_msg = TrustPingMsg(
        connection_id=bob_and_alice_connection["alice_connection_id"], comment="Donda"
    )

    response = await alice_member_client.post(
        "/generic/messaging/trust-ping", json=trustping_msg.dict()
    )
    response_data = response.json()

    assert_that(response.status_code).is_equal_to(200)
    assert_that(response_data).contains("thread_id")


@pytest.mark.asyncio()
async def test_send_message(
    bob_and_alice_connection: BobAliceConnect, alice_member_client: AsyncClient
):
    message = Message(
        connection_id=bob_and_alice_connection["alice_connection_id"], content="Donda"
    )

    # debug logging to print the response and URL
    url = "/generic/messaging/send-message"
    print(f"Request URL: {alice_member_client.base_url}{url}")  # Print the request URL

    response = await alice_member_client.post(url, json=message.dict())

    print(f"Response content: {response.text}")  # Print the response content

    assert_that(response.status_code).is_equal_to(204)