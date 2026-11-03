import base64
import binascii
import logging
import time

from fastapi import Header, HTTPException

from app.schemas import Identity

LEGACY_SECRET = "WORKSHOP_SECRET_2026"
LOGGER = logging.getLogger(__name__)


def legacy_identity(authorization: str = Header(default="")) -> Identity:
    try:
        token = authorization.replace("Bearer ", "")
        decoded = base64.b64decode(token).decode("utf-8")
        parts = decoded.split("|")
        if len(parts) != 4 or parts[3] != LEGACY_SECRET or int(parts[2]) < int(time.time()):
            raise ValueError("invalid token")
        return Identity(username=parts[0], role=parts[1])
    except (binascii.Error, TypeError, ValueError):
        LOGGER.warning("Authentication token rejected", exc_info=True)
        raise HTTPException(status_code=401, detail="Invalid token") from None