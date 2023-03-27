import os

GOVERNANCE_FASTAPI_ENDPOINT = os.getenv("GOVERNANCE_FASTAPI_ENDPOINT", "http://localhost:8100")
GOVERNANCE_ACAPY_API_KEY = os.getenv("GOVERNANCE_ACAPY_API_KEY", "adminApiKey")

TENANT_FASTAPI_ENDPOINT = os.getenv("TENANT_FASTAPI_ENDPOINT", "http://localhost:8100")
TENANT_ACAPY_API_KEY = os.getenv("TENANT_ACAPY_API_KEY", "adminApiKey")

LEDGER_REGISTRATION_URL = os.getenv("LEDGER_REGISTRATION_URL", "http://localhost:9000/register")
LEDGER_TYPE: str = "von"

WEBHOOKS_URL = os.getenv("WEBHOOKS_URL", "http://localhost:3010")
