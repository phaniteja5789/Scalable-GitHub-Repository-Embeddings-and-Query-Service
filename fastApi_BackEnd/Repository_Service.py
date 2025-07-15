import httpx
from fastapi import Request
from fastapi.responses import JSONResponse as HTTPMessage
from fastapi import HTTPException
from BaseModels import RepositoryDetails
import logging


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def get_all_files(request: Request, repositoryDetails: RepositoryDetails, branch: str = "main"):    
    logger.info("Fetching all files from repository.")
    owner = repositoryDetails.owner
    repo = repositoryDetails.repo
    token = (await request.json()).get("id")
    
    url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{branch}?recursive=1"
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)
        if response.status_code == 200:
            tree = response.json().get("tree", [])
            files = [item["path"] for item in tree if item["type"] == "blob"]
            logger.info("Successfully fetched all files.")
            return HTTPMessage(status_code=200, content={"files": files})

        else:
            logger.error(f"Error fetching files: {response.text}")
            raise HTTPException(status_code=response.status_code, detail=f"Failed to fetch files: {response.text}")

