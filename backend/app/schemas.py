from pydantic import BaseModel


class WorkspaceCreate(BaseModel):
    title: str
    research_question: str


class SourceCreate(BaseModel):
    title: str
    source_type: str
    url: str | None = None


class SourceVersionCreate(BaseModel):
    content: str

class EvidenceCreate(BaseModel):
    exact_text: str
    start_position: int | None = None
    end_position: int | None = None

class ClaimCreate(BaseModel):
    statement: str


class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class WorkspaceCreate(BaseModel):
    title: str
    research_question: str

class WorkspaceUpdate(BaseModel):
    title: str
    research_question: str