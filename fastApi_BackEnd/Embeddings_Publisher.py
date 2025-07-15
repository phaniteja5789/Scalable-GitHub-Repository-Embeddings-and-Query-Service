import aio_pika
import asyncio
import httpx
import os
import logging
from BaseModels.FileQueueMessage import *

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq/")
Files_Queue = "files_queue"
Embeddings_Queue = "embeddings_queue"


MAIN_DIR = os.getcwd()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.info(f"Current working directory: {MAIN_DIR}")
logger.info(f"RABBITMQ_URL: {RABBITMQ_URL}")
logger.info(f"Main_DIR = {MAIN_DIR}")
REPO_FILES_DIR = os.path.join(MAIN_DIR, "Repository_Files")
logger.info(f"Repository Files Directory = {REPO_FILES_DIR}")
if not os.path.exists(REPO_FILES_DIR):
    os.makedirs(REPO_FILES_DIR)


MAX_CONCURRENT_DOWNLOADS = 5
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds

semaphore = asyncio.Semaphore(MAX_CONCURRENT_DOWNLOADS)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def publish_to_embeddings_queue(local_path):
    logger.info(f"Publishing file to embeddings queue: {local_path}")
    connection = await aio_pika.connect_robust(RABBITMQ_URL, timeout= 300, heartbeat = 6000)
    async with connection:
        channel = await connection.channel()
        queue = await channel.declare_queue(Embeddings_Queue, durable=True)
        await channel.default_exchange.publish(
            aio_pika.Message(local_path.encode()),
            routing_key=queue.name,
        )
    logger.info(f"Published {local_path} to embeddings queue.")

async def process_file(file_message_instance: FileQueueMessage):
    async with semaphore:
        repo_name = file_message_instance.repo
        file_name = file_message_instance.fileName
        raw_url = file_message_instance.filePath
        logger.info(f"Processing file: repo={repo_name}, file={file_name}, url={raw_url}")
        timeout = httpx.Timeout(300.0)
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    response = await client.get(raw_url)
                    if response.status_code == 200:
                        local_dir = os.path.join(REPO_FILES_DIR, repo_name)
                        os.makedirs(os.path.dirname(os.path.join(local_dir, file_name)), exist_ok=True)
                        local_path = os.path.join(local_dir, file_name)
                        with open(local_path, "wb") as f:
                            f.write(response.content)
                        logger.info(f"Downloaded and saved to {local_path}")
                        # Publish to embeddings queue
                        local_path = local_path.replace("\\", "/")  # Ensure path is in Unix format
                        logger.info(f"Publishing {local_path} to embeddings queue")
                        await publish_to_embeddings_queue(local_path)
                        return  # Success, exit the function
                    else:
                        logger.warning(f"Failed to download {raw_url}: {response.status_code} {response.text}")
            except Exception as e:
                logger.error(f"Error downloading {raw_url} (attempt {attempt}): {e}")
            if attempt < MAX_RETRIES:
                logger.info(f"Retrying ({attempt}/{MAX_RETRIES}) in {RETRY_DELAY}s...")
                await asyncio.sleep(RETRY_DELAY)
        logger.error(f"File not processed after {MAX_RETRIES} attempts: {raw_url}")

async def main():
    logger.info("Starting Embeddings Publisher main loop.")
    connection = await aio_pika.connect_robust(RABBITMQ_URL, timeout= 300, heartbeat = 6000)
    async with connection:
        channel = await connection.channel()
        queue = await channel.declare_queue(Files_Queue, durable=True)
        tasks = []
        async with queue.iterator() as queue_iter:
            async for message in queue_iter:
                async with message.process():
                    file_message_instance = FileQueueMessage.model_validate_json(message.body.decode())
                    logger.info(f"Received file message: {file_message_instance}")
                    task = asyncio.create_task(process_file(file_message_instance))
                    tasks.append(task)
        if tasks:
            await asyncio.gather(*tasks)
    logger.info("Embeddings Publisher main loop finished.")

if __name__ == "__main__":
    asyncio.run(main())