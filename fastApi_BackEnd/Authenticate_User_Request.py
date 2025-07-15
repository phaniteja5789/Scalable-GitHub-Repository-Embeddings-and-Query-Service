from fastapi import Depends,HTTPException
from Create_JWT import create_JWT
from Secrets.secrets import secret_key
import jwt
import logging


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

async def decode_jwt(jwt_token = Depends(create_JWT)):
    logger.info("Decoding JWT token.")
    if(isinstance(jwt_token, HTTPException)):
        logger.warning("Received HTTPException instead of JWT token.")
        return jwt_token
    try:
        payload = jwt.decode(jwt_token, secret_key, algorithms=["HS256"])
        logger.info(f"JWT decoded successfully. Payload: {payload}")
        if payload.get("role") in ["admin"]:
            logger.info("Admin access granted.")
            return payload
        elif payload.get("role") in ["user"]:
            logger.warning("User role does not have permission to access this resource.")
            return HTTPException(
                status_code=403,
                detail="User role does not have permission to access this resource"
            )
    except jwt.ExpiredSignatureError:
        logger.error("JWT token has expired.")
        return HTTPException(
            status_code=401,
            detail="JWT token has expired"
        )
    except jwt.InvalidTokenError:
        logger.error("Invalid JWT token.")
        return HTTPException(
            status_code=401,
            detail="Invalid JWT token"
        )
