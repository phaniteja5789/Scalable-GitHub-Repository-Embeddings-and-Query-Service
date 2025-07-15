from pydantic import BaseModel, Field, model_validator
from typing import Optional

class FileQueueMessage(BaseModel):
    
    fileName: str = Field(
        ...,
        description="The name of the file in the repository."
    )
    owner: str = Field(
        ...,
        description="The owner of the repository, typically the username or organization name on GitHub."
    )
    repo: str = Field(
        ...,
        description="The name of the repository."
    )
    branch: str = Field(
        "main",
        description="The branch of the repository where the file is located."
    )
    filePath: Optional[str] = Field(
        None,
        description="The raw URL of the file in the repository."
    )

    @model_validator(mode="after")
    def set_file_path(self):
        self.filePath = f"https://raw.githubusercontent.com/{self.owner}/{self.repo}/{self.branch}/{self.fileName}"
        return self