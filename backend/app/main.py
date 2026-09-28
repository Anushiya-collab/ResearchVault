import hashlib
import httpx
from bs4 import BeautifulSoup
from datetime import datetime
from io import BytesIO
from pypdf import PdfReader
from fastapi import (
    FastAPI,
    Depends,
    HTTPException,
    Security,
    UploadFile,
    File,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from pydantic import BaseModel
from jose import jwt, JWTError
from app import models, schemas
from app.schemas import RegisterRequest, LoginRequest, WorkspaceCreate, WorkspaceUpdate
from app.database import Base, engine
from app.ingestion import fetch_url_content, generate_text_diff
from app.dependencies import get_db
from fastapi.middleware.cors import CORSMiddleware
from app.auth import (
    hash_password,
    verify_password,
    create_access_token,
    SECRET_KEY,
    ALGORITHM,
)

Base.metadata.create_all(bind=engine)
app = FastAPI(
    title="ResearchVault API",
    description="Research management backend",
    version="1.0.0"
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://researchvault-1.onrender.com",
],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security),
    db: Session = Depends(get_db)
):
    token = credentials.credentials

    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )

        user_id = payload.get("sub")

        if user_id is None:
            raise HTTPException(
                status_code=401,
                detail="Invalid token"
            )

        user = (
            db.query(models.User)
            .filter(models.User.id == int(user_id))
            .first()
        )

        if user is None:
            raise HTTPException(
                status_code=401,
                detail="User not found"
            )

        return user

    except (JWTError, ValueError):
        raise HTTPException(
            status_code=401,
            detail="Invalid token"
        )

@app.get("/")
def root():
    return {
        "message": "ResearchVault API is running!"
    }


@app.post("/workspaces")
def create_workspace(
    workspace_data: WorkspaceCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    workspace = models.Workspace(
        title=workspace_data.title,
        research_question=workspace_data.research_question,
        owner_id=current_user.id
    )

    db.add(workspace)
    db.commit()
    db.refresh(workspace)

    return workspace

@app.get("/workspaces")
def get_workspaces(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    workspaces = (
        db.query(models.Workspace)
        .filter(models.Workspace.owner_id == current_user.id)
        .all()
    )

    return workspaces

@app.get("/workspaces/{workspace_id}")
def get_workspace(
    workspace_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    workspace = (
        db.query(models.Workspace)
        .filter(
            models.Workspace.id == workspace_id,
            models.Workspace.owner_id == current_user.id
        )
        .first()
    )

    if not workspace:
        raise HTTPException(
            status_code=404,
            detail="Workspace not found"
        )

    return workspace


@app.delete("/workspaces/{workspace_id}")
def delete_workspace(
    workspace_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    workspace = (
        db.query(models.Workspace)
        .filter(
            models.Workspace.id == workspace_id,
            models.Workspace.owner_id == current_user.id
        )
        .first()
    )

    if not workspace:
        raise HTTPException(
            status_code=404,
            detail="Workspace not found"
        )

    db.delete(workspace)
    db.commit()

    return {
        "message": "Workspace deleted successfully"
    }
@app.post("/workspaces/{workspace_id}/sources")
def create_source(
    workspace_id: int,
    source: schemas.SourceCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    workspace = (
        db.query(models.Workspace)
        .filter(
            models.Workspace.id == workspace_id,
            models.Workspace.owner_id == current_user.id
        )
        .first()
    )

    if not workspace:
        raise HTTPException(
            status_code=404,
            detail="Workspace not found"
        )

    new_source = models.Source(
        title=source.title,
        source_type=source.source_type,
        url=source.url,
        workspace_id=workspace_id
    )

    db.add(new_source)
    db.commit()
    db.refresh(new_source)

    return new_source

@app.post("/sources/{source_id}/versions")
def create_source_version(
    source_id: int,
    version: schemas.SourceVersionCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    source = (
        db.query(models.Source)
        .join(models.Workspace)
        .filter(
            models.Source.id == source_id,
            models.Workspace.owner_id == current_user.id
        )
        .first()
    )

    if not source:
        raise HTTPException(
            status_code=404,
            detail="Source not found"
        )

    latest_version = (
        db.query(models.SourceVersion)
        .filter(
            models.SourceVersion.source_id == source_id
        )
        .order_by(
            models.SourceVersion.version_number.desc()
        )
        .first()
    )

    if latest_version:
        next_version_number = latest_version.version_number + 1
    else:
        next_version_number = 1

    content_hash = hashlib.sha256(
        version.content.encode("utf-8")
    ).hexdigest()

    new_version = models.SourceVersion(
        version_number=next_version_number,
        content=version.content,
        content_hash=content_hash,
        source_id=source_id
    )

    db.add(new_version)
    db.commit()
    db.refresh(new_version)

    return new_version
@app.post("/sources/{source_id}/refetch")
def refetch_source(
    source_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    # Check that the source belongs to the current user
    source = (
        db.query(models.Source)
        .join(models.Workspace)
        .filter(
            models.Source.id == source_id,
            models.Workspace.owner_id == current_user.id
        )
        .first()
    )

    if not source:
        raise HTTPException(
            status_code=404,
            detail="Source not found"
        )

    if not source.url:
        raise HTTPException(
            status_code=400,
            detail="This source does not have a URL"
        )

    try:
        response = httpx.get(
            source.url,
            timeout=15.0,
            follow_redirects=True
        )
        response.raise_for_status()
    except httpx.HTTPError as error:
        raise HTTPException(
            status_code=502,
            detail=f"Could not fetch source: {error}"
        )

    # Extract readable text from the webpage
    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )

    for tag in soup(
        ["script", "style", "noscript"]
    ):
        tag.decompose()

    content = soup.get_text(
        separator=" ",
        strip=True
    )

    if not content:
        raise HTTPException(
            status_code=422,
            detail="No readable content found"
        )

    # Calculate hash of the newly fetched content
    new_hash = hashlib.sha256(
        content.encode("utf-8")
    ).hexdigest()

    # Get latest stored version
    latest_version = (
        db.query(models.SourceVersion)
        .filter(
            models.SourceVersion.source_id == source_id
        )
        .order_by(
            models.SourceVersion.version_number.desc()
        )
        .first()
    )

    # Nothing has changed
    if latest_version and latest_version.content_hash == new_hash:
        return {
            "status": "unchanged",
            "source_id": source_id,
            "version_number": latest_version.version_number,
            "message": "No changes detected"
        }

    # Create a new version
    next_version_number = (
        latest_version.version_number + 1
        if latest_version
        else 1
    )

    new_version = models.SourceVersion(
        version_number=next_version_number,
        content=content,
        content_hash=new_hash,
        source_id=source_id
    )

    db.add(new_version)
    db.commit()
    db.refresh(new_version)

    return {
        "status": "changed",
        "source_id": source_id,
        "old_version": (
            latest_version.version_number
            if latest_version
            else None
        ),
        "new_version": new_version.version_number,
        "content_length": len(content),
        "content_hash": new_hash,
        "message": "New source version created"
    }

@app.post("/versions/{version_id}/evidence")
def create_evidence(
    version_id: int,
    evidence: schemas.EvidenceCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    source_version = (
        db.query(models.SourceVersion)
        .join(models.Source)
        .join(models.Workspace)
        .filter(
            models.SourceVersion.id == version_id,
            models.Workspace.owner_id == current_user.id
        )
        .first()
    )

    if not source_version:
        raise HTTPException(
            status_code=404,
            detail="Source version not found"
        )

    new_evidence = models.Evidence(
        exact_text=evidence.exact_text,
        start_position=evidence.start_position,
        end_position=evidence.end_position,
        source_version_id=version_id
    )

    db.add(new_evidence)
    db.commit()
    db.refresh(new_evidence)

    return new_evidence

@app.post("/workspaces/{workspace_id}/claims")
def create_claim(
    workspace_id: int,
    claim: schemas.ClaimCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    workspace = (
        db.query(models.Workspace)
        .filter(
            models.Workspace.id == workspace_id,
            models.Workspace.owner_id == current_user.id
        )
        .first()
    )

    if not workspace:
        raise HTTPException(
            status_code=404,
            detail="Workspace not found"
        )

    new_claim = models.Claim(
        statement=claim.statement,
        workspace_id=workspace_id
    )

    db.add(new_claim)
    db.commit()
    db.refresh(new_claim)

    return new_claim

@app.post("/claims/{claim_id}/evidence/{evidence_id}")
def link_claim_to_evidence(
    claim_id: int,
    evidence_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    # Check that the claim belongs to the current user's workspace
    claim = (
        db.query(models.Claim)
        .join(
            models.Workspace,
            models.Claim.workspace_id == models.Workspace.id
        )
        .filter(
            models.Claim.id == claim_id,
            models.Workspace.owner_id == current_user.id
        )
        .first()
    )

    if not claim:
        raise HTTPException(
            status_code=404,
            detail="Claim not found"
        )

    # Check that the evidence belongs to the same user's workspace
    evidence = (
        db.query(models.Evidence)
        .join(
            models.SourceVersion,
            models.Evidence.source_version_id == models.SourceVersion.id
        )
        .join(
            models.Source,
            models.SourceVersion.source_id == models.Source.id
        )
        .join(
            models.Workspace,
            models.Source.workspace_id == models.Workspace.id
        )
        .filter(
            models.Evidence.id == evidence_id,
            models.Workspace.owner_id == current_user.id
        )
        .first()
    )

    if not evidence:
        raise HTTPException(
            status_code=404,
            detail="Evidence not found"
        )

    if evidence not in claim.evidence:
        claim.evidence.append(evidence)

    db.commit()

    return {
        "message": "Evidence linked to claim successfully",
        "claim_id": claim_id,
        "evidence_id": evidence_id
    }

@app.get("/claims/{claim_id}")
def get_claim(
    claim_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    claim = (
        db.query(models.Claim)
        .join(models.Workspace)
        .filter(
            models.Claim.id == claim_id,
            models.Workspace.owner_id == current_user.id
        )
        .first()
    )

    if not claim:
        raise HTTPException(
            status_code=404,
            detail="Claim not found"
        )

    return {
        "id": claim.id,
        "statement": claim.statement,
        "workspace_id": claim.workspace_id,
        "evidence": [
            {
                "id": evidence.id,
                "exact_text": evidence.exact_text,
                "source_version_id": evidence.source_version_id,
                "start_position": evidence.start_position,
                "end_position": evidence.end_position
            }
            for evidence in claim.evidence
        ]
    }

@app.get("/claims/{claim_id}/provenance")
def get_claim_provenance(
    claim_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    # Check that the claim belongs to the current user's workspace
    claim = (
        db.query(models.Claim)
        .join(
            models.Workspace,
            models.Claim.workspace_id == models.Workspace.id
        )
        .filter(
            models.Claim.id == claim_id,
            models.Workspace.owner_id == current_user.id
        )
        .first()
    )

    if not claim:
        raise HTTPException(
            status_code=404,
            detail="Claim not found"
        )

    provenance = []

    for evidence in claim.evidence:
        source_version = evidence.source_version
        source = source_version.source

        provenance.append({
            "evidence_id": evidence.id,
            "exact_text": evidence.exact_text,
            "start_position": evidence.start_position,
            "end_position": evidence.end_position,

            "source_version": {
                "id": source_version.id,
                "version_number": source_version.version_number,
                "content_hash": source_version.content_hash
            },

            "source": {
                "id": source.id,
                "title": source.title,
                "url": source.url,
                "source_type": source.source_type
            }
        })

    return {
        "claim_id": claim.id,
        "claim": claim.statement,
        "workspace_id": claim.workspace_id,
        "provenance": provenance
    }
@app.get("/sources/{source_id}/affected-claims")
def get_affected_claims(
    source_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    # Make sure the source belongs to the current user
    source = (
        db.query(models.Source)
        .join(models.Workspace)
        .filter(
            models.Source.id == source_id,
            models.Workspace.owner_id == current_user.id
        )
        .first()
    )

    if not source:
        raise HTTPException(
            status_code=404,
            detail="Source not found"
        )

    # Find the latest version of this source
    latest_version = (
        db.query(models.SourceVersion)
        .filter(
            models.SourceVersion.source_id == source_id
        )
        .order_by(
            models.SourceVersion.version_number.desc()
        )
        .first()
    )

    if not latest_version:
        return {
            "source_id": source_id,
            "latest_version": None,
            "affected_claims": []
        }

    # Find claims connected to evidence from older versions
    affected_claims = (
        db.query(models.Claim)
        .join(
            models.claim_evidence,
            models.Claim.id == models.claim_evidence.c.claim_id
        )
        .join(
            models.Evidence,
            models.Evidence.id == models.claim_evidence.c.evidence_id
        )
        .join(
            models.SourceVersion,
            models.SourceVersion.id ==
            models.Evidence.source_version_id
        )
        .join(
            models.Workspace,
            models.Workspace.id ==
            models.Claim.workspace_id
        )
        .filter(
            models.SourceVersion.source_id == source_id,
            models.SourceVersion.version_number <
            latest_version.version_number,
            models.Workspace.owner_id == current_user.id
        )
        .distinct()
        .all()
    )

    return {
        "source_id": source_id,
        "latest_version": latest_version.version_number,
        "affected_claims": [
            {
                "id": claim.id,
                "statement": claim.statement,
                "workspace_id": claim.workspace_id,
                "status": "needs_review"
            }
            for claim in affected_claims
        ]
    }

@app.get("/search")
def search_research(
    q: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    search_text = f"%{q}%"

    # Search claims only in the current user's workspaces
    claims = (
        db.query(models.Claim)
        .join(models.Workspace)
        .filter(
            models.Workspace.owner_id == current_user.id,
            models.Claim.statement.ilike(search_text)
        )
        .all()
    )

    # Search evidence only in the current user's workspaces
    evidence = (
        db.query(models.Evidence)
        .join(models.SourceVersion)
        .join(models.Source)
        .join(models.Workspace)
        .filter(
            models.Workspace.owner_id == current_user.id,
            models.Evidence.exact_text.ilike(search_text)
        )
        .all()
    )

    return {
        "query": q,

        "claims": [
            {
                "id": claim.id,
                "statement": claim.statement,
                "workspace_id": claim.workspace_id
            }
            for claim in claims
        ],

        "evidence": [
            {
                "id": item.id,
                "exact_text": item.exact_text,
                "source_version_id": item.source_version_id
            }
            for item in evidence
        ]
    }

@app.post("/register")
def register_user(
    user_data: RegisterRequest,
    db: Session = Depends(get_db)
):
    existing_user = (
        db.query(models.User)
        .filter(models.User.email == user_data.email)
        .first()
    )

    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )

    new_user = models.User(
        name=user_data.name,
        email=user_data.email,
        password_hash=hash_password(user_data.password)
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {
        "message": "User registered successfully",
        "user_id": new_user.id,
        "name": new_user.name,
        "email": new_user.email
    }

@app.post("/login")
def login_user(
    user_data: LoginRequest,
    db: Session = Depends(get_db)
):
    user = (
        db.query(models.User)
        .filter(models.User.email == user_data.email)
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    if not verify_password(
        user_data.password,
        user.password_hash
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "email": user.email
        }
    )

    return {
        "message": "Login successful",
        "access_token": access_token,
        "token_type": "bearer"
    }

@app.put("/workspaces/{workspace_id}")
def update_workspace(
    workspace_id: int,
    workspace_data: WorkspaceUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    workspace = (
        db.query(models.Workspace)
        .filter(
            models.Workspace.id == workspace_id,
            models.Workspace.owner_id == current_user.id
        )
        .first()
    )

    if not workspace:
        raise HTTPException(
            status_code=404,
            detail="Workspace not found"
        )

    workspace.title = workspace_data.title
    workspace.research_question = workspace_data.research_question

    db.commit()
    db.refresh(workspace)

    return workspace

@app.post("/workspaces/{workspace_id}/sources/import-url")
def import_url_source(
    workspace_id: int,
    url: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    # Check workspace ownership
    workspace = (
        db.query(models.Workspace)
        .filter(
            models.Workspace.id == workspace_id,
            models.Workspace.owner_id == current_user.id
        )
        .first()
    )

    if not workspace:
        raise HTTPException(
            status_code=404,
            detail="Workspace not found"
        )

    # Fetch webpage content
    try:
        content = fetch_url_content(url)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Could not fetch URL: {str(e)}"
        )

    if not content:
        raise HTTPException(
            status_code=400,
            detail="No readable content found"
        )

    # Create source
    source = models.Source(
        title=url,
        source_type="webpage",
        url=url,
        workspace_id=workspace_id
    )

    db.add(source)
    db.commit()
    db.refresh(source)

    # Create first source version
    content_hash = hashlib.sha256(
        content.encode("utf-8")
    ).hexdigest()

    source_version = models.SourceVersion(
        version_number=1,
        content=content,
        content_hash=content_hash,
        source_id=source.id
    )

    db.add(source_version)
    db.commit()
    db.refresh(source_version)

    return {
        "message": "URL imported successfully",
        "source": {
            "id": source.id,
            "title": source.title,
            "source_type": source.source_type,
            "url": source.url
        },
        "source_version": {
            "id": source_version.id,
            "version_number": source_version.version_number,
            "content_hash": source_version.content_hash,
            "content_length": len(content)
        }
    }

@app.post("/sources/{source_id}/check-for-updates")
def check_source_for_updates(
    source_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    # Find the source and make sure it belongs to the current user
    source = (
        db.query(models.Source)
        .join(models.Workspace)
        .filter(
            models.Source.id == source_id,
            models.Workspace.owner_id == current_user.id
        )
        .first()
    )

    if not source:
        raise HTTPException(
            status_code=404,
            detail="Source not found"
        )

    if not source.url:
        raise HTTPException(
            status_code=400,
            detail="This source does not have a URL"
        )

    # Fetch the current webpage
    try:
        new_content = fetch_url_content(source.url)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Could not fetch URL: {str(e)}"
        )

    if not new_content:
        raise HTTPException(
            status_code=400,
            detail="No readable content found"
        )

    # Calculate hash of the newly fetched content
    new_hash = hashlib.sha256(
        new_content.encode("utf-8")
    ).hexdigest()

    # Find the latest saved version
    latest_version = (
        db.query(models.SourceVersion)
        .filter(
            models.SourceVersion.source_id == source_id
        )
        .order_by(
            models.SourceVersion.version_number.desc()
        )
        .first()
    )

    if not latest_version:
        raise HTTPException(
            status_code=404,
            detail="No source version found"
        )

    # Compare hashes
    if new_hash == latest_version.content_hash:
        return {
            "message": "No changes detected",
            "source_id": source_id,
            "current_version": latest_version.version_number,
            "changed": False
        }

    # Content changed — create a new version
    new_version_number = latest_version.version_number + 1

    new_version = models.SourceVersion(
        version_number=new_version_number,
        content=new_content,
        content_hash=new_hash,
        source_id=source_id
    )

    db.add(new_version)
    db.commit()
    db.refresh(new_version)
    change = models.SourceChange(
    source_id=source_id,
    old_version_id=latest_version.id,
    new_version_id=new_version.id
)

    db.add(change)
    db.commit()
    db.refresh(change)

    return {
        "message": "Source changed. New version created.",
        "source_id": source_id,
        "previous_version": latest_version.version_number,
        "new_version": new_version.version_number,
        "changed": True,
        "content_hash": new_hash,
        "content_length": len(new_content)
    }

@app.get("/sources/{source_id}/changes")
def get_source_changes(
    source_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    # Check that the source belongs to the current user
    source = (
        db.query(models.Source)
        .join(models.Workspace)
        .filter(
            models.Source.id == source_id,
            models.Workspace.owner_id == current_user.id
        )
        .first()
    )

    if not source:
        raise HTTPException(
            status_code=404,
            detail="Source not found"
        )

    # Get the latest recorded change
    change = (
        db.query(models.SourceChange)
        .filter(
            models.SourceChange.source_id == source_id
        )
        .order_by(
            models.SourceChange.detected_at.desc()
        )
        .first()
    )

    if not change:
        return {
            "source_id": source_id,
            "message": "No changes recorded",
            "changes": []
        }

    # Get old and new versions
    old_version = (
        db.query(models.SourceVersion)
        .filter(
            models.SourceVersion.id == change.old_version_id
        )
        .first()
    )

    new_version = (
        db.query(models.SourceVersion)
        .filter(
            models.SourceVersion.id == change.new_version_id
        )
        .first()
    )

    if not old_version or not new_version:
        raise HTTPException(
            status_code=404,
            detail="Source versions not found"
        )

    # Generate word-level diff
    diff = generate_text_diff(
        old_version.content,
        new_version.content
    )

    return {
        "source_id": source_id,
        "old_version": old_version.version_number,
        "new_version": new_version.version_number,
        "changes": diff
    }

@app.get("/evidence/{evidence_id}/impact")
def check_evidence_impact(
    evidence_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    # Find evidence belonging to the current user
    evidence = (
        db.query(models.Evidence)
        .join(models.SourceVersion)
        .join(models.Source)
        .join(models.Workspace)
        .filter(
            models.Evidence.id == evidence_id,
            models.Workspace.owner_id == current_user.id
        )
        .first()
    )

    if not evidence:
        raise HTTPException(
            status_code=404,
            detail="Evidence not found"
        )

    # The version where the evidence was originally captured
    old_version = evidence.source_version

    # Find the next version of the same source
    new_version = (
        db.query(models.SourceVersion)
        .filter(
            models.SourceVersion.source_id == old_version.source_id,
            models.SourceVersion.version_number > old_version.version_number
        )
        .order_by(
            models.SourceVersion.version_number.asc()
        )
        .first()
    )

    if not new_version:
        return {
            "evidence_id": evidence.id,
            "affected": False,
            "message": "No newer source version exists"
        }

    # Check whether the exact evidence text still exists
    # in the newer version.
    evidence_exists_old = (
        evidence.exact_text in old_version.content
    )

    evidence_exists_new = (
        evidence.exact_text in new_version.content
    )

    affected = (
        evidence_exists_old
        and not evidence_exists_new
    )

    return {
        "evidence_id": evidence.id,
        "old_version": old_version.version_number,
        "new_version": new_version.version_number,
        "exact_text": evidence.exact_text,
        "exists_in_old_version": evidence_exists_old,
        "exists_in_new_version": evidence_exists_new,
        "affected": affected
    }

@app.get("/evidence/{evidence_id}/affected-claims")
def get_affected_claims(
    evidence_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    # Find the evidence and verify ownership
    evidence = (
        db.query(models.Evidence)
        .join(models.SourceVersion)
        .join(models.Source)
        .join(models.Workspace)
        .filter(
            models.Evidence.id == evidence_id,
            models.Workspace.owner_id == current_user.id
        )
        .first()
    )

    if not evidence:
        raise HTTPException(
            status_code=404,
            detail="Evidence not found"
        )

    # Check whether this evidence is affected
    old_version = evidence.source_version

    new_version = (
        db.query(models.SourceVersion)
        .filter(
            models.SourceVersion.source_id == old_version.source_id,
            models.SourceVersion.version_number > old_version.version_number
        )
        .order_by(
            models.SourceVersion.version_number.asc()
        )
        .first()
    )

    if not new_version:
        return {
            "evidence_id": evidence_id,
            "affected": False,
            "claims": []
        }

    evidence_affected = (
        evidence.exact_text in old_version.content
        and evidence.exact_text not in new_version.content
    )

    if not evidence_affected:
        return {
            "evidence_id": evidence_id,
            "affected": False,
            "claims": []
        }
        # Mark claims using this evidence as needing review
    claims = evidence.claims

    for claim in claims:
        claim.status = "needs_review"

    db.commit()
    
    return {
        "evidence_id": evidence_id,
        "affected": True,
        "claims": [
            {
                "claim_id": claim.id,
                "statement": claim.statement,
                "workspace_id": claim.workspace_id
            }
            for claim in claims
        ]
    }

@app.get("/workspaces/{workspace_id}/sources")
def get_workspace_sources(
    workspace_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    workspace = (
        db.query(models.Workspace)
        .filter(
            models.Workspace.id == workspace_id,
            models.Workspace.owner_id == current_user.id
        )
        .first()
    )

    if not workspace:
        raise HTTPException(
            status_code=404,
            detail="Workspace not found"
        )

    sources = (
        db.query(models.Source)
        .filter(
            models.Source.workspace_id == workspace_id
        )
        .all()
    )

    return sources

@app.get("/workspaces/{workspace_id}/claims")
def get_workspace_claims(
    workspace_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    workspace = (
        db.query(models.Workspace)
        .filter(
            models.Workspace.id == workspace_id,
            models.Workspace.owner_id == current_user.id
        )
        .first()
    )

    if not workspace:
        raise HTTPException(
            status_code=404,
            detail="Workspace not found"
        )

    claims = (
        db.query(models.Claim)
        .filter(
            models.Claim.workspace_id == workspace_id
        )
        .all()
    )

    return claims

@app.get("/sources/{source_id}/versions")
def get_source_versions(
    source_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    source = (
        db.query(models.Source)
        .join(models.Workspace)
        .filter(
            models.Source.id == source_id,
            models.Workspace.owner_id == current_user.id
        )
        .first()
    )

    if not source:
        raise HTTPException(
            status_code=404,
            detail="Source not found"
        )

    versions = (
        db.query(models.SourceVersion)
        .filter(
            models.SourceVersion.source_id == source_id
        )
        .order_by(
            models.SourceVersion.version_number.asc()
        )
        .all()
    )

    return [
        {
            "id": version.id,
            "version_number": version.version_number,
            "content_hash": version.content_hash,
            "content_length": len(version.content),
            "created_at": version.created_at
        }
        for version in versions
    ]

@app.get("/sources/{source_id}/changes")
def get_source_changes(
    source_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    source = (
        db.query(models.Source)
        .join(models.Workspace)
        .filter(
            models.Source.id == source_id,
            models.Workspace.owner_id == current_user.id
        )
        .first()
    )

    if not source:
        raise HTTPException(
            status_code=404,
            detail="Source not found"
        )

    changes = (
        db.query(models.SourceChange)
        .filter(
            models.SourceChange.source_id == source_id
        )
        .order_by(
            models.SourceChange.detected_at.desc()
        )
        .all()
    )

    return [
        {
            "id": change.id,
            "source_id": change.source_id,
            "old_version_id": change.old_version_id,
            "new_version_id": change.new_version_id,
            "detected_at": change.detected_at
        }
        for change in changes
    ]
@app.get("/workspaces/{workspace_id}/claims")
def get_workspace_claims(
    workspace_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    workspace = (
        db.query(models.Workspace)
        .filter(
            models.Workspace.id == workspace_id,
            models.Workspace.owner_id == current_user.id
        )
        .first()
    )

    if not workspace:
        raise HTTPException(
            status_code=404,
            detail="Workspace not found"
        )

    claims = (
        db.query(models.Claim)
        .filter(
            models.Claim.workspace_id == workspace_id
        )
        .order_by(models.Claim.id.asc())
        .all()
    )

    return [
        {
            "id": claim.id,
            "statement": claim.statement,
            "workspace_id": claim.workspace_id,
            "status": getattr(claim, "status", "active")
        }
        for claim in claims
    ]

@app.post("/workspaces/{workspace_id}/sources/import-pdf")
async def import_pdf(
    workspace_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    # Check workspace ownership
    workspace = (
        db.query(models.Workspace)
        .filter(
            models.Workspace.id == workspace_id,
            models.Workspace.owner_id == current_user.id
        )
        .first()
    )

    if not workspace:
        raise HTTPException(
            status_code=404,
            detail="Workspace not found"
        )

    # Check file type
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported"
        )

    # Read PDF
    try:
        pdf_bytes = await file.read()
        reader = PdfReader(BytesIO(pdf_bytes))

        extracted_text = ""

        for page in reader.pages:
            page_text = page.extract_text() or ""
            extracted_text += page_text + "\n"

    except Exception as error:
        raise HTTPException(
            status_code=400,
            detail=f"Could not read PDF: {error}"
        )

    extracted_text = extracted_text.strip()

    if not extracted_text:
        raise HTTPException(
            status_code=400,
            detail="No readable text found in PDF"
        )

    # Create source
    source = models.Source(
        title=file.filename[:255],
        source_type="pdf",
        url=None,
        workspace_id=workspace_id
    )

    db.add(source)
    db.commit()
    db.refresh(source)

    # Create Version 1
    content_hash = hashlib.sha256(
        extracted_text.encode("utf-8")
    ).hexdigest()

    version = models.SourceVersion(
        version_number=1,
        content=extracted_text,
        content_hash=content_hash,
        source_id=source.id
    )

    db.add(version)
    db.commit()
    db.refresh(version)

    return {
        "message": "PDF imported successfully",
        "source": {
            "id": source.id,
            "title": source.title,
            "source_type": source.source_type
        },
        "version": {
            "id": version.id,
            "version_number": version.version_number,
            "content_hash": version.content_hash,
            "content_length": len(extracted_text)
        }
    }