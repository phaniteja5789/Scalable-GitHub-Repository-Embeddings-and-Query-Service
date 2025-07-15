import httpx
from fastapi import Request
from fastapi.responses import JSONResponse as HTTPMessage
from BaseModels import RepositoryDetails
import logging


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def build_webhook_url(owner: str, repo: str) -> str:
    return f"https://api.github.com/repos/{owner}/{repo}/hooks"

def create_webhook_url(request : Request, endpoint : str):
    
    webhook_url = request.base_url._url + endpoint
    return webhook_url





async def create_github_webhook(request : Request, repository_details : RepositoryDetails): 
    logger.info(f"Creating GitHub webhook for repo: {repository_details.owner}/{repository_details.repo}")
    owner = repository_details.owner
    repo = repository_details.repo
    data = await request.json()
    token = data.get("id")
    logger.info("Extracted token from request.")
    api_url = build_webhook_url(owner, repo)
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    
    webhook_url = create_webhook_url(request, "/webhook/")
    logger.info(f"Webhook URL to register: {webhook_url}")
    async with httpx.AsyncClient() as client:
        try:
            hooks_response = await client.get(api_url, headers=headers)
            logger.info(f"Fetched existing hooks. Status: {hooks_response.status_code}")
            hooks = hooks_response.json()
        except Exception as e:
            logger.error(f"Failed to fetch existing hooks: {e}")
            return HTTPMessage(status_code=500, content={"message": "Failed to fetch existing hooks"})
        for hook in hooks:
            if hook.get("config", {}).get("url") == webhook_url:
                logger.info("Webhook already exists.")
                return HTTPMessage(status_code=200, content={"message": "Webhook already exists", "webhook_url": webhook_url})
        data = {
            "name": "web",
            "active": True,
            "events": ["push"],
            "config": {
                "url": webhook_url,
                "content_type": "json",
                "insecure_ssl": "0"
            }
        }
        try:
            create_response = await client.post(api_url, headers=headers, json=data)
            logger.info(f"Create webhook response: {create_response.status_code} {create_response.text}")
        except Exception as e:
            logger.error(f"Failed to create webhook: {e}")
            return HTTPMessage(status_code=500, content={"message": "Failed to create webhook"})
        return HTTPMessage(
            status_code=create_response.status_code,
            content={
                "message": "Webhook created successfully" if create_response.status_code == 201 else "Failed to create webhook",
                "webhook_url": webhook_url
            }
        )

async def get_list_of_modified_files(payload):

    files = set()
    for commit in payload.get("commits", []):
        files.update(commit.get("added", []))
        files.update(commit.get("removed", []))
        files.update(commit.get("modified", []))
    return list(files)