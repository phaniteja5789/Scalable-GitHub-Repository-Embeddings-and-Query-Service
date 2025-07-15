import aio_pika
from BaseModels.FileQueueMessage import *
from BaseModels.QueryResponse import *
from BaseModels.QueryRequest import *
from fastapi.responses import JSONResponse as HTTPMessage
from fastapi import HTTPException
import logging
import os
import random
from dotenv import load_dotenv
load_dotenv()

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq/")
Files_Queue = "files_queue"
Query_Queue = "query_queue"
Query_Response_Queue = "query_response_queue"


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

repository_owner = None
repository_name = None


def set_repository_details(repository_details):

    global repository_owner,repository_name

    repository_owner = repository_details.owner
    repository_name = repository_details.repo



async def publish_files_to_rabbitmq(file_list):
    try:
        connection = await aio_pika.connect_robust(RABBITMQ_URL, timeout= 300, heartbeat = 6000)
        async with connection:
            channel = await connection.channel()
            logger.info(f"Channel opened. Declaring queue '{Files_Queue}'")
            queue = await channel.declare_queue(Files_Queue, durable=True)
            for file_name in file_list:
                file_message = FileQueueMessage(
                    fileName=file_name,
                    owner=repository_owner,
                    repo=repository_name,
                )
                message_body = file_message.json().encode()
                await channel.default_exchange.publish(
                    aio_pika.Message(message_body),
                    routing_key=queue.name,
                )
                
        logger.info(f"Successfully published {len(file_list)} files to RabbitMQ queue '{Files_Queue}'")
        return HTTPMessage(
            content={
                "message": f"Published {len(file_list)} files to RabbitMQ queue '{Files_Queue}'"
            },
            status_code=200
        )
    except Exception as e:
        logger.error(f"Failed to publish files to RabbitMQ: {str(e)}", exc_info=True)
        return HTTPException(
            status_code=500,
            detail=f"Failed to publish files to RabbitMQ: {str(e)}"
        )
