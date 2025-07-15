import aio_pika
import asyncio
import openai
import chromadb
import os
from pathlib import Path
import logging
from BaseModels.QueryRequest import *
from BaseModels.QueryResponse import *
from langchain.schema import Document
from langchain.prompts import ChatPromptTemplate
from langchain_openai.chat_models import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


logger.info(f"Current working directory: {os.getcwd()}")

MAIN_DIR = os.getcwd()
REPO_FILES_DIR = os.path.join(MAIN_DIR, "Repository_Files")

if not os.path.exists("./Chroma_db"):
    os.makedirs("./Chroma_db")
    


RABBITMQ_URL = "amqp://guest:guest@rabbitmq/"
RABBITMQ_URL = os.getenv("RABBITMQ_URL", RABBITMQ_URL)
Embeddings_Queue = "embeddings_queue"
Query_Queue = "query_queue"
Query_Response_Queue = "query_response_queue"
OPENAI_API_KEY = "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"
openai.api_key = OPENAI_API_KEY
embeddings_model = "text-embedding-3-small"

chroma_client = chromadb.PersistentClient(path="./Chroma_db")



logger.info(f"RABBITMQ_URL: {RABBITMQ_URL}")
logger.info(f"Main_DIR = {MAIN_DIR}")
logger.info(f"Repository Files Directory = {REPO_FILES_DIR}")




def get_repository_name_from_path(local_path):
    repo_base = Path(REPO_FILES_DIR).resolve()
    local_path = Path(local_path).resolve()
    relative = local_path.relative_to(repo_base)
    base_dir = relative.parts[0]
    logger.info(f"chromadb collection with name {base_dir}")
    return chroma_client.get_or_create_collection(base_dir)




async def generate_and_store_embedding(local_path):
    # Read file content (assuming text file)
    try:
        with open(local_path, "r", encoding="utf-8") as f:
            content = f.read()
        logger.info(f"Read file: {local_path}")
    except Exception as e:
        logger.error(f"Failed to read {local_path}: {e}")
        return

    # Generate embedding using OpenAI
    try:
        response = openai.embeddings.create(
            input = content,
            model = embeddings_model
        )
        embedding = response.data[0].embedding
        logger.info(f"Generated embedding for {local_path}")
    except Exception as e:
        logger.error(f"Failed to generate embedding for {local_path}: {e}")
        return

    # Store embedding in ChromaDB
    try:
        collection = get_repository_name_from_path(local_path)
        collection.upsert(
            documents=[content],
            embeddings=[embedding],
            ids=[os.path.basename(local_path)]
        )
        logger.info(f"Stored embedding for {local_path} in ChromaDB.")
    except Exception as e:
        logger.error(f"Failed to store embedding for {local_path}: {e}")



async def consume_messages_from_embeddings_queue(channel):

    queue = await channel.declare_queue(Embeddings_Queue, durable=True)
    logger.info(f"Waiting for messages in queue '{Embeddings_Queue}'")
    async with queue.iterator() as queue_iter:
        async for message in queue_iter:
            async with message.process():
                local_path = message.body.decode()
                logger.info(f"Processing file for embedding: {local_path}")
                try:
                    await generate_and_store_embedding(local_path)
                except Exception as e:
                    logger.error(f"Error processing {local_path}: {e}")




        
    




async def main():
    logger.info(f"Connecting to RabbitMQ at {RABBITMQ_URL}")
    connection = await aio_pika.connect_robust(RABBITMQ_URL, timeout= 300, heartbeat = 6000)
    async with connection:
        
        channel = await connection.channel()

        await asyncio.gather(
            consume_messages_from_embeddings_queue(channel),
        )

        
if __name__ == "__main__":
    asyncio.run(main())