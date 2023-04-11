from distutils.util import strtobool
import io
import logging
import os
import traceback

from aiohttp import ClientResponseError
from fastapi import FastAPI, Request, Response
from fastapi.exceptions import HTTPException
from fastapi.responses import JSONResponse
import pydantic
import yaml

from app.admin.tenants import tenants
from app.generic import definitions, messaging, trust_registry, webhooks
from app.generic.connections import connections
from app.generic.issuer import issuer
from app.generic.jsonld import jsonld
from app.generic.oob import oob
from app.generic.verifier import verifier
from app.generic.wallet import wallet
from app.webhook_listener import Webhooks

OPENAPI_NAME = os.getenv("OPENAPI_NAME", "OpenAPI")
PROJECT_VERSION = os.getenv("PROJECT_VERSION", "0.0.1BETA")

logger = logging.getLogger(__name__)
prod = strtobool(os.environ.get("prod", "True"))
app = FastAPI(
    debug=not prod,
    title=OPENAPI_NAME,
    description="Welcome to the Aries CloudAPI Python project",
    version=PROJECT_VERSION,
)

app.include_router(connections.router)
app.include_router(definitions.router)
app.include_router(issuer.router)
app.include_router(jsonld.router)
app.include_router(messaging.router)
app.include_router(oob.router)
app.include_router(tenants.router)
app.include_router(trust_registry.router)
app.include_router(verifier.router)
app.include_router(wallet.router)
app.include_router(webhooks.router)


@app.on_event("shutdown")
async def shutdown_event():
    await Webhooks.shutdown()


@app.on_event("startup")
async def startup_event():
    await Webhooks.listen_webhooks()


# add endpoints
# additional yaml version of openapi.json
@app.get("/openapi.yaml", include_in_schema=False)
def read_openapi_yaml() -> Response:
    openapi_json = app.openapi()
    yaml_s = io.StringIO()
    yaml.dump(openapi_json, yaml_s, allow_unicode=True, sort_keys=False)
    return Response(content=yaml_s.getvalue(), media_type="text/yaml")


@app.exception_handler(Exception)
async def client_response_error_exception_handler(
    request: Request, exception: Exception
):
    stacktrace = traceback.format_exc()

    if isinstance(exception, ClientResponseError):
        return JSONResponse(
            {"detail": exception.message, "stack": stacktrace}, exception.status or 500
        )
    if isinstance(exception, HTTPException):
        return JSONResponse(
            {**exception.detail, "stack": stacktrace},
            exception.status_code,
            exception.headers,
        )
    if isinstance(exception, pydantic.error_wrappers.ValidationError):
        return JSONResponse({"detail": exception.errors()}, status_code=422)
    else:
        return JSONResponse(
            {"detail": "Internal server error", "stack": stacktrace}, 500
        )
