from pydantic import BaseModel,Field

class QueryRequest(BaseModel):
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