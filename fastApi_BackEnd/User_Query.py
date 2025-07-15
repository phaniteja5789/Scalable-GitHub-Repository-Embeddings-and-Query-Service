from BaseModels.QueryResponse import *
from BaseModels.QueryRequest import *
from fastapi.responses import JSONResponse as HTTPMessage
from fastapi import HTTPException
import logging
import openai
import chromadb
from langchain.schema import Document
from langchain.prompts import ChatPromptTemplate
from langchain_openai.chat_models import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser

from dotenv import load_dotenv
load_dotenv()

OPENAI_API_KEY = "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"
openai.api_key = OPENAI_API_KEY
embeddings_model = "text-embedding-3-small"

chroma_client = chromadb.PersistentClient(path="./Chroma_db")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

repository_owner = None
repository_name = None



async def Fetch_Response_For_Query(query_request_obj : QueryRequest):

    try:
        
        generated_response_obj = await generate_the_response_for_the_query(query_request_obj)
        return generated_response_obj
    
    except Exception as e:
        
        logger.error(f"Failed to publish files to RabbitMQ: {str(e)}", exc_info=True)
        return HTTPException(
            status_code=500,
            detail=f"Failed to publish files to RabbitMQ: {str(e)}"
        )

async def generate_response(relevant_docs, query):

    logger.info(f"Generating the response...")

    logger.info(f"Relevant docs {relevant_docs} and query {query}")

    docs = [Document(page_content=doc) for doc in relevant_docs]

    llm = ChatOpenAI(
        model = "gpt-4.1-mini", 
        temperature=0.2,
        api_key=OPENAI_API_KEY
    )



    context = "\n\n".join([doc.page_content for doc in docs])
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are an expert in understanding the repository. Use the provided context to answer the user's question as accurately as possible.\n\nContext:\n{context}"),
        ("human", "{question}")
    ])

    chain = prompt | llm | StrOutputParser()

    response = await chain.ainvoke({"context": context, "question": query})
    logger.info(f"The final result {response}")
    return response


async def generate_the_response_for_the_query(user_entered_query : QueryRequest):

    logger.info(f"Entered the method for generating the embedding response for the query")
    repo_name = user_entered_query.repo
    query = user_entered_query.query
    queryId = user_entered_query.queryId

    collection = chroma_client.get_collection(repo_name)

    logger.info(f"Retrieved the chromadb collection {collection}")

    embeddings_response = openai.embeddings.create(
     input = query,
     model= embeddings_model
    )

    query_embedding = [embeddings_response.data[0].embedding]

    logger.info(f"Generated the embedding response for the query {query_embedding}")

    relevant_docs = collection.query(

        query_embeddings= query_embedding,
        n_results= 10
    )

    logger.info(f"Fetched Relevant Docs {relevant_docs}")

    for doc, score in zip(relevant_docs["documents"][0], relevant_docs["distances"][0]):
        logger.info(f"Document: {doc}\nSimilarity Score: {score}\n")
        
    llm_generated_response = await generate_response(relevant_docs=relevant_docs, query= query)

    logger.info(f"Generated the llm response {llm_generated_response}")

    response_obj = QueryResponse(

        queryId = queryId,
        query = query,
        repo = repo_name,
        response = llm_generated_response
    )

    return response_obj