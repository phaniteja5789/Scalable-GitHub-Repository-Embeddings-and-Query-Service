from pydantic import BaseModel,Field

class QueryResponse(BaseModel):
    queryId: int = Field(
        ...,
        description="The Id of the query which user asked"
    )

    repo: str = Field(
        ...,
        description = "The repository in which it needs to search for" 
    )

    query: str = Field(
        ...,
        description="The query which user asked"
    )
    response: str = Field(
        ...,
        description="The response of the query"
    )