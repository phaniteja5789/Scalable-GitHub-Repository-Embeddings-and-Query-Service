# Dissertation GitHub Repository Analyzer

This project is a full-stack application for analyzing and querying GitHub repositories. It consists of a **React frontend** and a **FastAPI backend**. The backend handles authentication, repository configuration, webhook integration, asynchronous file processing via RabbitMQ, and user queries. The frontend provides a user interface for authentication and interaction.



## Project Structure

```
.
├── fastApi_BackEnd/         # FastAPI backend (API, webhooks, RabbitMQ, etc.)
│   ├── BaseModels/          # Pydantic models for API and queue messages
│   ├── github-chat-extension/ # VS Code extension for GitHub chat (optional)
│   ├── Embeddings_Publisher.py # Publishes file tasks to RabbitMQ
│   ├── Embeddings_Consumer.py  # Consumes file tasks from RabbitMQ
│   ├── main.py              # Main FastAPI app (API endpoints)
│   ├── Parse_Validate_Url.py
│   ├── Repository_Service.py
│   ├── RepositoryParsing.py
│   ├── Creation_Of_GitHub_Webhook.py
│   ├── requirements.txt
│   └── .env
├── react_frontend/          # React frontend (user interface)
│   ├── public/
│   ├── src/
│   │   ├── App.js
│   │   ├── App.css
│   │   ├── index.js
│   │   └── ...
│   ├── package.json
│   ├── .env
│   └── Dockerfile.frontend
└── Repository_Files/        # Directory for storing processed repository files
```

---

## Features

- **GitHub OAuth Authentication**
- **Repository Configuration & Validation**
- **Webhook Integration for GitHub Events**
- **RabbitMQ Integration for Asynchronous Processing**
- **Query API for Repository Data**
- **VS Code Extension (Optional)**

---

## Prerequisites

- **Python 3.10+**
- **Node.js 18+** (for frontend)
- **npm** (for frontend)
- **RabbitMQ** (for backend async processing)
- **Git**
- **Docker** (optional, for deployment)

---

## Environment Variables

### Backend (`fastApi_BackEnd/.env`)

```env
BASE_URL=http://localhost:8000
FRONT_END_ORIGIN=http://localhost:3000
GITHUB_CLIENT_ID=your_github_client_id
GITHUB_CLIENT_SECRET=your_github_client_secret
LOCAL_BASE_URL=http://localhost:8000
RABBITMQ_URL=amqp://guest:guest@rabbitmq/
```

### Frontend (`react_frontend/.env`)

```env
REACT_APP_BASE_URL=http://localhost:8000
GENERATE_SOURCEMAP=false
```

---

## Setup Instructions

### Backend (FastAPI)

1. **Install dependencies:**

   ```sh
   cd fastApi_BackEnd
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Configure environment variables:**

   - Copy `.env` and update values as needed.

3. **Start RabbitMQ** (if not already running):

   ```sh
   docker run -d --hostname rabbitmq --name rabbitmq -p 5672:5672 -p 15672:15672 rabbitmq:3-management
   ```

4. **Run the FastAPI server:**

   ```sh
   uvicorn main:app --reload
   ```

5. **Start the Embeddings Consumer:**

   ```sh
   python Embeddings_Consumer.py
   ```

### Frontend (React)

1. **Install dependencies:**

   ```sh
   cd react_frontend
   npm install
   ```

2. **Configure environment variables:**

   - Copy `.env` and update `REACT_APP_BASE_URL` to point to your backend.

3. **Run the React app:**

   ```sh
   npm start
   ```

   The app will be available at [http://localhost:3000](http://localhost:3000).

---

## Running the Application

1. **Start RabbitMQ** (see above).
2. **Start the FastAPI backend** (`uvicorn main:app --reload`).
3. **Start the Embeddings Consumer** (`python Embeddings_Consumer.py`).
4. **Start the React frontend** (`npm start`).
5. **Open the frontend in your browser** and follow the UI to authenticate with GitHub and configure repositories.

---

## API Endpoints

### 1. Authentication

#### `GET /dissertation/login`

- **Description:** Redirects the user to GitHub's OAuth login page.
- **Request:** No parameters.
- **Response:** Redirects to GitHub OAuth.

---

#### `GET /dissertation/oauth/callback`

- **Description:** Handles the OAuth callback from GitHub. Exchanges the code for an access token and stores it in the session.
- **Request Parameters:**
  - `code` (query): The code returned by GitHub after user authorization.
- **Response:**
  - On success: Redirects to the frontend with `?auth=success`.
  - On failure:  
    ```json
    { "error": "Token exchange failed" }
    ```

---

### 2. Repository Management

#### `POST /dissertation/set_repo`

- **Description:** Sets the repository path for the session and returns the GitHub token.
- **Request Body:**
  ```json
  {
    "repo_path": "https://github.com/owner/repo"
  }
  ```
- **Response:**
  - On success:
    ```json
    {
      "message": "Repository path https://github.com/owner/repo",
      "repo_path": "https://github.com/owner/repo",
      "github_token": "<token>"
    }
    ```
  - On failure (not authenticated):
    ```json
    { "error": "Not authenticated" }
    ```

---

#### `POST /dissertation/repo/configuration`

- **Description:** Validates the repository URL, checks user permissions, creates a webhook, fetches all files, and publishes them to RabbitMQ for processing.
- **Headers:** Requires JWT authentication (handled by `Depends(auth.decode_jwt)`).
- **Request Body:**  
  The request body is parsed and validated internally. It should contain the repository identifier and authentication token.
- **Response:**
  - If already processed:
    ```json
    { "message": "Repository 'repo' has already been embedded and processed." }
    ```
  - If newly processed:
    ```json
    { "message": "Repository 'repo' has been successfully embedded and queued for processing." }
    ```
  - On error:
    ```json
    { "message": "..." }
    ```

---

#### `POST /dissertation/repo/configuration/webhook/`

- **Description:** Endpoint for GitHub webhook events. Processes push events on the main branch and publishes modified files to RabbitMQ.
- **Request Body:** Standard GitHub webhook payload.
- **Response:**
  - Always returns:
    ```json
    { "message": "Webhook received" }
    ```
  - On error (publishing files):
    ```json
    { "message": "Failed to publish files to the processing queue. Please try again later." }
    ```

---

### 3. Query

#### `GET /dissertation/query`

- **Description:** Accepts a user query and repository, processes it, and returns the response.
- **Request Body:**
  ```json
  {
    "query": "How does the authentication work?",
    "repo": "owner/repo"
  }
  ```
- **Response:**
  - On success:
    ```json
    { "message": "<response from LLM>" }
    ```
  - On failure:
    - Returns an HTTPException with error details.

---

## Asynchronous Processing with RabbitMQ

This project uses **RabbitMQ** as a message broker to enable asynchronous, decoupled processing of repository files. This is crucial for handling large repositories and for scaling the embedding and query operations.

### How RabbitMQ is Used

- When a repository is configured or a webhook event is received, the backend gathers a list of files to process.
- For each file, a message (with file metadata) is published to a RabbitMQ queue (e.g., `embedding_tasks`).
- One or more consumers listen to this queue and process each file (e.g., generating embeddings).
- This decouples the API responsiveness from heavy processing and allows for scalable, reliable background work.

---

### Embeddings_Publisher.py

**Purpose:**  
Publishes messages (tasks) to a RabbitMQ queue. Each message contains information about a repository file that needs to be processed (e.g., for embedding generation).

**Workflow:**

1. **Connection:**  
   Establishes a connection to RabbitMQ using the URL specified in your `.env` file (`RABBITMQ_URL`).

2. **Publishing:**  
   When the backend needs to process files (after repository configuration or webhook events), it calls `publish_files_to_rabbitmq` (imported in `main.py`), which delegates the actual publishing to `Embeddings_Publisher.py`.

3. **Message Format:**  
   Each message is typically a JSON object with file metadata (such as file path, repository info, etc.).

4. **Queue:**  
   Messages are published to a queue (e.g., `embedding_tasks`).

**Example Flow:**

- User configures a repository.
- Backend fetches all files.
- For each file, `publish_files_to_rabbitmq` sends a message to RabbitMQ via `Embeddings_Publisher.py`.
- The API responds to the user immediately, while processing continues in the background.

---

### Embeddings_Consumer.py

**Purpose:**  
Acts as a worker that listens to the RabbitMQ queue for new tasks. When a message arrives, it processes the file (e.g., downloads it, generates embeddings, stores results).

**Workflow:**

1. **Connection:**  
   Connects to RabbitMQ and subscribes to the same queue used by the publisher.

2. **Consuming:**  
   Waits for new messages. When a message is received, it parses the file information and performs the required processing (such as generating vector embeddings for the file content).

3. **Processing:**  
   The actual processing logic (e.g., embedding generation, storing results in a database or file system) is implemented here.

4. **Acknowledgement:**  
   After successful processing, the consumer acknowledges the message so RabbitMQ can remove it from the queue.

**How to Run:**

```sh
cd fastApi_BackEnd
python Embeddings_Consumer.py
```

You can run multiple consumers for scalability.

---

### Summary Diagram

```
User → FastAPI Backend → [publish_files_to_rabbitmq] → RabbitMQ Queue ← Embeddings_Consumer.py
```
- The backend publishes file tasks to RabbitMQ.
- The consumer(s) process these tasks asynchronously.

---

## Deployment

### Frontend

- Build the frontend for production:

  ```sh
  npm run build
  ```

- Use the provided `Dockerfile.frontend` to build and deploy with Nginx.

### Backend

- Deploy using a WSGI server (e.g., Uvicorn, Gunicorn) and configure environment variables for production.

---

## Testing

- **Frontend:**  
  Use `npm test` to run React tests.

- **Backend:**  
  Add tests using `pytest` or FastAPI's built-in testing utilities.

---

## Troubleshooting

- **CORS Issues:**  
  Ensure `FRONT_END_ORIGIN` and `REACT_APP_BASE_URL` are set correctly and match your deployment URLs.

- **GitHub OAuth:**  
  Make sure your GitHub OAuth app is configured with the correct callback URL.

- **RabbitMQ:**  
  Ensure RabbitMQ is running and accessible at the URL specified in `.env`.
