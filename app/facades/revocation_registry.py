import logging
from typing import Optional, Union
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
)
from app.dependencies import get_governance_controller

from app.error.cloud_api_error import CloudApiException
from app.webhook_listener import start_listener


logger = logging.getLogger(__name__)


async def create_revocation_registry(
    controller: AcaPyClient, credential_definition_id: str, max_cred_num: int = 32767
) -> IssuerRevRegRecord:
    """
        Create a new revocation registry

        This should be called whenever a new credential definition is created.

    Args:
        controller (AcaPyClient): aca-py client
        credential_definition_id (str): The credential definition ID.
        max_cred_num (Optional(int)): The maximum number of credentials to be stored by the registry.
            Default = 32768 (max is 32768)

    Raises:
        Exception: When the credential definition is not found or the revocation registry could not be created.

    Returns:
        result (IssuerRevRegRecord): The revocation registry record.
    """
    result = await controller.revocation.create_registry(
        body=RevRegCreateRequest(
            credential_definition_id=credential_definition_id, max_cred_num=max_cred_num
        )
    )

    if not result:
        raise CloudApiException(
            f"Error creating revocation registry for credential with ID {credential_definition_id} and max credential number {max_cred_num}\n{result}"
        )

    logger.info(f"Created revocation registry:\n{result.result}")

    return result.result


async def get_active_revocation_registry_for_credential(
    controller: AcaPyClient, credential_definition_id: str
) -> IssuerRevRegRecord:
    """
        Get the active revocation registry for a credential

    Args:
        controller (AcaPyClient): aca-py client
        credential_definition_id (str): The credential definition ID.

    Raises:
        Exception: When the active revocation registry cannot be retrieved.

    Returns:
        result (IssuerRevRegRecord): The revocation registry record.
    """
    result = await controller.revocation.get_active_registry_for_cred_def(
        cred_def_id=credential_definition_id
    )

    if not result and not isinstance(result, RevRegResult):
        raise CloudApiException(
            f"Error retrieving revocation registry for credential with ID {credential_definition_id}.\n{result}"
        )

    logger.info(
        f"Retrieved revocation registry for credential definition with ID {credential_definition_id}:\n{result.result}"
    )

    return result.result


async def get_credential_revocation_status(
    controller: AcaPyClient, credential_exchange_id: str
) -> IssuerCredRevRecord:
    """
        Get the active revocation registry for a credential

    Args:
        controller (AcaPyClient): aca-py client
        credential_definition_id (str): The credential definition ID.

    Raises:
        Exception: When the active revocation registry cannot be retrieved.

    Returns:
        IssuerRevRegRecord: The revocation registry record.
    """
    result = await controller.revocation.get_revocation_status(
        cred_ex_id=credential_exchange_id
    )

    if not result and not isinstance(result, CredRevRecordResult):
        credential_definition_id = await get_credential_definition_id_from_exchange_id(
            controller=controller, credential_exchange_id=credential_exchange_id
        )

        raise CloudApiException(
            f"Error retrieving revocation status for credential definition ID {credential_definition_id}"
        )
    else:
        result = result.result

    logger.info(
        f"Credential exchange {credential_exchange_id} has status:\n{result.state}:\n{result}"
    )

    return result


async def publish_revocation_registry_on_ledger(
    controller: AcaPyClient,
    revocation_registry_id: str,
    connection_id: Optional[str] = None,
    create_transaction_for_endorser: Optional[bool] = False,
) -> Union[IssuerRevRegRecord, TransactionRecord]:
    """
        Publish a created revocation registry to the ledger

    Args:
        controller (AcaPyClient): aca-py client
        revocation_registry_id (str): The revocation registry ID.
        connection_id (str): The connection ID of author to endorser.
        create_transaction_for_endorser (bool): Whether to create a transaction
            record to for the endorser to be endorsed.

    Raises:
        Exception: When the revocation registry could not be published.

    Returns:
        result (Union[IssuerRevRegRecord, TxnOrRevRegResult]): The revocation registry record,
            or the Revocation Register Result and the associated transaction record.
    """
    result = await controller.revocation.publish_rev_reg_def(
        rev_reg_id=revocation_registry_id,
        conn_id=connection_id if create_transaction_for_endorser else None,
        create_transaction_for_endorser=create_transaction_for_endorser,
    )

    if isinstance(result, RevRegResult) and result.result:
        result = result.result
    elif isinstance(result, TxnOrRevRegResult) and result.txn:
        result = result.txn
    else:
        raise CloudApiException(
            f"Failed to publish revocation registry to ledger.\n{result}"
        )

    logger.info(
        f"Published revocation registry for registry with ID {revocation_registry_id}:\n{result}"
    )

    return result


async def publish_revocation_entry_to_ledger(
    controller: AcaPyClient,
    revocation_registry_id: Optional[str] = None,
    credential_definition_id: Optional[str] = None,
    connection_id: Optional[str] = None,
    create_transaction_for_endorser: Optional[bool] = False,
) -> IssuerRevRegRecord:
    """
        Publish a created revocation entry to the ledger

    Args:
        controller (AcaPyClient): aca-py client
        credential_definition_id (str): The credential definition ID.
        revocation_registry_id (str): The revocation registry ID.
            Default is None
        connection_id (str): The connection ID of author to endorser.
            Default is None
        create_transaction_for_endorser (bool): Whether to create a transaction
            record to for the endorser to be endorsed.
            Default is False

    Raises:
        Exception: When the revocation registry entry could not be published.

    Returns:
        result (IssuerRevRegRecord): The revocation registry record.
    """
    if not revocation_registry_id and not credential_definition_id:
        raise CloudApiException(
            "Please, provide either a revocation registry id OR credential definition id.",
            400,
        )
    if not revocation_registry_id:
        revocation_registry_id = await get_active_revocation_registry_for_credential(
            controller=controller, credential_definition_id=credential_definition_id
        )
    try:
        result = await controller.revocation.publish_rev_reg_entry(
            rev_reg_id=revocation_registry_id,
            conn_id=connection_id if create_transaction_for_endorser else None,
            create_transaction_for_endorser=create_transaction_for_endorser,
        )
    except Exception as e:
        return e

    if not result and not isinstance(result, RevRegResult):
        raise CloudApiException(
            f"Failed to publish revocation entry to ledger.\n{result}"
        )

    logger.info(
        f"Published revocation entry for registry with ID {revocation_registry_id}:\n{result.result}"
    )

    return result.result


async def revoke_credential(
    controller: AcaPyClient,
    credential_exchange_id: str,
    auto_publish_to_ledger: bool = False,
    credential_definition_id: str = None,
) -> None:
    """
        Revoke an issued credential

    Args:
        controller (AcaPyClient): aca-py client
        credential_exchange_id (str): The credential exchange ID.
        credential_definition_id (str): The credential definition ID.
        auto_publish_to_ledger (bool): Whether to directly publish the revocation to the ledger.
            This should only be true when invoked by an endorser.
            Default is False

    Raises:
        Exception: When the credential could not be revoked

    Returns:
        result (None): Successful execution returns None.
    """

    try:
        await controller.revocation.revoke_credential(
            body=RevokeRequest(
                cred_ex_id=credential_exchange_id,
                publish=auto_publish_to_ledger,
            )
        )
    except ClientResponseError as e:
        raise CloudApiException(f"Failed to revoke credential.{e.message}", 418)

    if not auto_publish_to_ledger:
        active_revocation_registry_id = (
            await get_active_revocation_registry_for_credential(
                controller=controller,
                credential_definition_id=credential_definition_id,
            )
        )

        try:
            # Publish the revocation to ledger
            await publish_revocation_entry_to_ledger(
                controller=controller,
                revocation_registry_id=active_revocation_registry_id.revoc_reg_id,
                create_transaction_for_endorser=True,
            )
        except Exception:
            # FIXME: Using create_transaction_for_endorser nothing is returned from aca-py
            # This is unexpected and throws and error in the controller validating the pydantic model.
            # It still creates the transaction record though that can be endorsed below.
            await endorser_revoke()

    logger.info(
        f"Revoked credential  with ID {credential_definition_id} for exchange ID {credential_exchange_id}."
    )


async def endorser_revoke():
    endorser_wait_for_transaction, stop_listener = await start_listener(
        topic="endorsements", wallet_id="admin"
    )
    async with get_governance_controller() as endorser_controller:
        try:
            txn_record = await endorser_wait_for_transaction(
                filter_map={
                    "state": "request-received",
                }
            )
        except TimeoutError:
            raise CloudApiException(
                "Failed to retrieve transaction record for endorser", 500
            )
        finally:
            await stop_listener()

        await endorser_controller.endorse_transaction.endorse_transaction(
            tran_id=txn_record["transaction_id"]
        )


async def get_credential_definition_id_from_exchange_id(
    controller: AcaPyClient, credential_exchange_id: str
) -> Union[str, None]:
    """
        Get the credential definition id from the credential exchange id.

    Args:
        controller (AcaPyClient): aca-py client
        credential_exchange_id (RevokeRequest): The credential exchange ID.

    Returns:
        credential_definition_id (Union[str,None]): The credential definition ID or None.
    """
    try:
        credential_definition_id = (
            await controller.issue_credential_v1_0.get_record(
                cred_ex_id=credential_exchange_id
            )
        ).credential_definition_id
    except ClientResponseError:
        try:
            rev_reg_parts = (
                await controller.issue_credential_v2_0.get_record(
                    cred_ex_id=credential_exchange_id
                )
            ).indy.rev_reg_id.split(":")
            credential_definition_id = ":".join(
                [
                    rev_reg_parts[2],
                    "3",
                    "CL",  # NOTE: Potentially replace this with other possible signature type in future
                    rev_reg_parts[-4],
                    rev_reg_parts[-1],
                ]
            )
        except Exception:
            credential_definition_id = None
    return credential_definition_id
