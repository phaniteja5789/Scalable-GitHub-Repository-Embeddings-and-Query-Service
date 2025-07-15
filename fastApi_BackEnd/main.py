from fastapi import FastAPI, Depends, Request
import Authenticate_User_Request as auth
from Parse_Validate_Url import Parse_Validate_Url, Has_read_permission
from fastapi.exceptions import HTTPException
from fastapi.responses import RedirectResponse, JSONResponse as HTTPMessage, HTMLResponse
from Creation_Of_GitHub_Webhook import create_github_webhook, get_list_of_modified_files
from Repository_Service import get_all_files
from RepositoryParsing import publish_files_to_rabbitmq,set_repository_details
from starlette.middleware.sessions import SessionMiddleware
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import json
import os
import logging
import requests
import random
from BaseModels.QueryRequest import *
from BaseModels.QueryResponse import *
from User_Query import Fetch_Response_For_Query


dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(dotenv_path=dotenv_path)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MAIN_DIR = os.path.dirname(os.getcwd())
REPO_FILES_DIR = os.path.join(MAIN_DIR, "Repository_Files")
print(f"Repository Files Directory = {REPO_FILES_DIR}")

if not os.path.exists(REPO_FILES_DIR):
    os.makedirs(REPO_FILES_DIR)

BASE_URL = os.getenv("BASE_URL")
logging.info(f"Base URL: {BASE_URL}")

app = FastAPI()

def build_endpoint(endpoint):
    return f"{BASE_URL}{endpoint}"

FRONTEND_ORIGIN = os.getenv("FRONT_END_ORIGIN")

logging.info(f"Frontend Origin: {FRONTEND_ORIGIN}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_ORIGIN],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(SessionMiddleware, secret_key='your-secret-key')


GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET")
REDIRECT_URI = build_endpoint("/dissertation/oauth/callback")


GITHUB_AUTH_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"

@app.get("/dissertation/login")
def login(request: Request):
    logging.info("Redirecting to GitHub for authentication.")
    github_redirect_url = (
        f"{GITHUB_AUTH_URL}?client_id={GITHUB_CLIENT_ID}&redirect_uri={REDIRECT_URI}&scope=repo&prompt=login"
    )
    return RedirectResponse(github_redirect_url)


@app.get("/dissertation/oauth/callback")
def oauth_callback(request: Request, code: str):
    logging.info("Received OAuth callback with code: %s", code)
    response = requests.post(
        GITHUB_TOKEN_URL,
        data={
            "client_id": GITHUB_CLIENT_ID,
            "client_secret": GITHUB_CLIENT_SECRET,
            "code": code,
            "redirect_uri": REDIRECT_URI
        },
        headers={"Accept": "application/json"},
    )
    token = response.json().get("access_token")
    if token:
        request.session["github_token"] = token
        return RedirectResponse(f"{FRONTEND_ORIGIN}/?auth=success")
    return HTTPMessage({"error": "Token exchange failed"}, status_code=400)

@app.post("/dissertation/set_repo")
async def set_repo(request: Request):
    data = await request.json()
    token = request.session.get("github_token")
    if not token:
        return HTTPMessage({"error": "Not authenticated"}, status_code=401)
    repo_path = data.get("repo_path")
    return HTTPMessage({
        "message": f"Repository path {repo_path}",
        "repo_path": repo_path,
        "github_token": token
    })

@app.post("/dissertation/repo/configuration")
async def repo_configuration(request: Request, payload = Depends(auth.decode_jwt)):
    
    logger.info("Received /dissertation/repo/configuration request.")
    try:
        # User does not have permission to access this resource
        if isinstance(payload, HTTPException):
            logger.warning("User does not have permission to access this resource.")
            return HTTPMessage(
                status_code=payload.status_code if hasattr(payload, "status_code") else 403,
                content={"message": "Authentication failed: You do not have permission to access this resource."}
            )

        # Extract repoId from request body and validate it
        is_validated = await Parse_Validate_Url(request)
        if isinstance(is_validated, HTTPException):
            logger.warning("Repository URL validation failed.")
            return HTTPMessage(
                status_code=is_validated.status_code if hasattr(is_validated, "status_code") else 400,
                content={"message": "Repository URL validation failed. Please check the repository URL and try again."}
            )

        logger.info("Repository has been validated successfully.")

        # Repository ID has been validated successfully
        repository_details = is_validated

        # Check if the user has read permission for the repository
        has_read_permission = await Has_read_permission(request, repository_details)
        if isinstance(has_read_permission, HTTPException):
            logger.warning("User does not have read permission for the repository.")
            return HTTPMessage(
                status_code=has_read_permission.status_code if hasattr(has_read_permission, "status_code") else 403,
                content={"message": "You do not have read permission for this repository."}
            )

        has_read_permission_dict_response = json.loads(has_read_permission.body.decode('utf-8'))
        logger.info(f"User has read permission for the repository: {has_read_permission_dict_response}")

        safe_repo_name = repository_details.repo.replace("/", "_").replace("\\", "_")
        print(safe_repo_name)
        repo_dir = os.path.join(REPO_FILES_DIR, safe_repo_name)
        print(f"Repository Directory = {repo_dir}")
        logger.info(f"Checking if repo_dir exists: {repo_dir}")
        if os.path.exists(repo_dir) and os.path.isdir(repo_dir):
            logger.info(f"Repository '{repository_details.repo}' already published.")
            return HTTPMessage(
                status_code=200,
                content={"message": f"Repository '{repository_details.repo}' has already been embedded and processed."}
            )


        ## Create the Webhook for the repository, to subscribe to the latest changes

        github_webhook_response =  (response_of_github_webhook_creation_local_environment()) or (await create_github_webhook(request,repository_details))

        if isinstance(github_webhook_response, HTTPMessage):

            ## Either the webhook is created successfully or it already exists.
            if(github_webhook_response.status_code == 200 or github_webhook_response.status_code == 201):

                ## Webhook is created successfully.

                # Get all files from the repository
                files_response = await get_all_files(request, repository_details)
                if isinstance(files_response, HTTPException):
                    return HTTPMessage(
                        status_code=files_response.status_code if hasattr(files_response, "status_code") else 500,
                        content={"message": "Failed to retrieve files from the repository. Please try again later."}
                    )


                set_repository_details(repository_details)
                files_response_dict = json.loads(files_response.body.decode('utf-8'))
                list_of_repository_files = files_response_dict.get("files", [])
                print(f"List of Repository Files = {list_of_repository_files}")
                
                rabbitmq_response = await publish_files_to_rabbitmq(list_of_repository_files)
                if isinstance(rabbitmq_response, HTTPException):
                    return HTTPMessage(
                        status_code=rabbitmq_response.status_code if hasattr(rabbitmq_response, "status_code") else 500,
                        content={"message": "Failed to publish files to the processing queue. Please try again later."}
                    )

                return HTTPMessage(
                    status_code=200,
                    content={"message": f"Repository '{repository_details.repo}' has been successfully embedded and queued for processing."}
                )

    except Exception as e:
        logger.error(f"Error in /repo/configuration: {e}")
        return HTTPMessage(
            status_code=500,
            content={"message": "An unexpected error occurred during repository configuration. Please try again later."}
        )

    

@app.post("/dissertation/repo/configuration/webhook/")
async def repo_webhook(request: Request):
    logger.info("Received /webhook/ request.")
    payload = await request.json()
    ref = payload.get("ref")
    if ref == "refs/heads/main":
        logger.info("Push event triggered on the main branch.")
        ## Handling the main branch event handlers
        get_files_which_are_modified = get_list_of_modified_files(payload)
        rabbitmq_response = await publish_files_to_rabbitmq(get_files_which_are_modified)
        if isinstance(rabbitmq_response, HTTPException):
            return HTTPMessage(
                status_code=rabbitmq_response.status_code if hasattr(rabbitmq_response, "status_code") else 500,
                content={"message": "Failed to publish files to the processing queue. Please try again later."}
            )
    else:
        logger.info(f"Push event on another branch: {ref}")
    
    return HTTPMessage(status_code=200, content={"message": "Webhook received"})


@app.get("/dissertation/query")
async def respond_to_query(request:Request):

    logger.info("Recieved the query for the request")
    payload = await request.json()
    query = payload.get("query")
    repo = payload.get("repo")
    query_id = random.randint(1,100000)
    logger.info(f"User entered the query {query} with id = {query_id} against the repo = {repo}")
    query_request_obj = QueryRequest(
                queryId = query_id,
                query = query,
                repo = repo
            )
    query_publish_response = await Fetch_Response_For_Query(query_request_obj)
    
    if isinstance(query_publish_response,HTTPException):
        logger.info(f"Unable to get the response for the query: {query}")
        return query_publish_response

    return HTTPMessage(status_code=200, content= {"message" : query_publish_response.response})
    
def response_of_github_webhook_creation_local_environment():

    local_base_url = os.getenv("LOCAL_BASE_URL")

    if local_base_url == BASE_URL:
        return HTTPMessage(status_code=200, content={"message" : "Local Build cannot be used to create github webhook"})
