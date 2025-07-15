from fastapi import Request, HTTPException
import re,httpx
from BaseModels.RepositoryDetails import RepositoryDetails
from fastapi.responses import JSONResponse as HTTPMessage
import logging


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def build_repos_url(owner: str, repo: str) -> str:
    """
    Build the URL for the GitHub repository.
    """
    return f"https://api.github.com/repos/{owner}/{repo}"

async def Parse_Validate_Url(request: Request):
    logger.info("Validating repository URL from request.")
    try:

        repo_id = await extract_repo_id(request)
        response = await validate_repo_id(repo_id)
        if(response[0] == 200):
            logger.info(f"Repository URL validated: {repo_id}")
            return (response[1])
        else:
            logger.error(f"Error validating repository URL: {response}")
            return HTTPException(status_code = response, detail="Invalid repository URL")

    except ValueError as e:
        return HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        return HTTPException(status_code=500, detail="Internal Server Error") 

async def extract_repo_id(request: Request):
    try:
        body = await request.json()
        repo_id = body.get("repoId")
        if not repo_id:
            raise ValueError("repoId is required")
        return repo_id
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal Server Error") from e
    
async def validate_repo_id(repo_id):
    match = re.match(r"^https:\/\/github\.com\/([\w\-\.]+)\/([\w\-\.]+)(\.git)?$", repo_id)
    owner, repo = match.group(1), match.group(2)
    repository_details = RepositoryDetails(owner=owner, repo=repo, repoId=repo_id)
    api_url = build_repos_url(owner, repo)
    async with httpx.AsyncClient() as client:
        response = await client.get(api_url)
        return (response.status_code,repository_details) if response.status_code == 200 else response.status_code
    

async def Has_read_permission(request: Request, repository_details: RepositoryDetails):
    logger.info(f"Checking read permission for repository: {repository_details}")
    owner = repository_details.owner
    repo = repository_details.repo
    token = (await request.json()).get("id")
    api_url = build_repos_url(owner, repo)
    
    headers = {"Authorization": f"Bearer {token}"}
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(api_url, headers=headers)
            logger.info("Read permission check successful.")
            return  HTTPMessage(status_code=response.status_code, content = "Repository has read permissions") if response.status_code == 200 else HTTPException(status_code = response.status_code, detail = response.content)
        except Exception as e:
            logger.error(f"Error checking read permission: {e}")
            return HTTPException(status_code=403, detail="Permission denied")
