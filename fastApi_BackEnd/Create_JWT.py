import httpx
import jwt
from fastapi import Request
from Secrets.secrets import secret_key
from Users_Roles import Admin_Roles
from fastapi.exceptions import HTTPException
import logging


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

GITHUB_API_URL = "https://api.github.com/user"

async def create_JWT(request : Request):
    logger.info("Received request to create JWT.")
    try:
        request_body_data = await request.json()
        print(f"Request body data: {request_body_data}")
        personalaccesstoken = request_body_data.get("id")
        logger.info("Extracted personal access token from request.")
    except Exception as e:
        logger.error(f"Failed to parse request body: {e}")
        return HTTPException(status_code=400, detail="Invalid request body")
    response_json = None
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                GITHUB_API_URL,
                headers={
                    "Authorization": f"Bearer {personalaccesstoken}"
                }
            )
            logger.info(f"GitHub API response status: {response.status_code}")
        except Exception as e:
            logger.error(f"Error during GitHub API call: {e}")
            return HTTPException(status_code=500, detail="GitHub API call failed")
        if response.status_code != 200:
            logger.warning("Invalid or expired personal access token.")
            return HTTPException(
                status_code=response.status_code,
                detail="Invalid or expired personal access token"
            )
        response_json = response.json()
        logger.info(f"GitHub user info: {response_json}")
    payload = {
        "id": response_json.get("id"),
        "login": response_json.get("login"),
        "role" : "admin" if response_json.get("id") in Admin_Roles.admin_users else "user"
    }
    logger.info(f"JWT payload: {payload}")
    try:
        jwt_token = jwt.encode(payload, secret_key, algorithm="HS256")
        logger.info("JWT created successfully.")
    except Exception as e:
        logger.error(f"Failed to encode JWT: {e}")
        return HTTPException(status_code=500, detail="Failed to create JWT")
    return jwt_token