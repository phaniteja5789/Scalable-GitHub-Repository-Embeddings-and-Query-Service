from pydantic import BaseModel,Field

class RepositoryDetails(BaseModel):
    repoId: str = Field(
        ...,
        description="The full URL of the GitHub repository"
    )
    owner: str = Field(
        ...,
        description="The owner of the repository, typically the username or organization name on GitHub."
    )
    repo: str = Field(
        ...,
        description="The name of the repository."
    )