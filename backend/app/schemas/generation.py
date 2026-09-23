from pydantic import Field
from app.schemas.uml import UMLModel


class SpringGenerationRequest(UMLModel):
    expected_version: int = Field(ge=1, le=2147483646, strict=True)

