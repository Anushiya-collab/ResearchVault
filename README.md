# ResearchVault – Personal Research Workspace

ResearchVault is a full-stack personal research workspace designed to help users
collect research sources, preserve source versions, track evidence, create
claims, and maintain a clear provenance trail between conclusions and their
original sources.

## Overview

Research often involves information from multiple webpages and sources.
Over time, webpages can change, making it difficult to determine whether an
existing conclusion is still supported by the original evidence.

ResearchVault addresses this problem by connecting:

Workspace → Source → Source Version → Evidence → Claim → Provenance

The application allows users to organize research in workspaces, import
web sources, track versions, detect changes, connect evidence to claims, and
trace claims back to their original source.

## Features

- User registration and login
- JWT-based authentication
- Research workspace management
- Create, update, and delete workspaces
- Web URL ingestion
- PDF document ingestion and text extraction
- Automatic webpage content extraction
- Source versioning
- SHA-256 content hashing
- Source re-fetching
- Source change detection
- Evidence tracking
- Claim management
- Claim-to-evidence linking
- Provenance tracking
- Research search
- Source version history
- Active / Needs Review indicators
- Responsive frontend interface

## Core Research Flow

```text
Research Workspace
        ↓
      Source
        ↓
  Source Version
        ↓
     Evidence
        ↓
      Claim
        ↓
    Provenance

┌─────────────────────┐
│      React UI       │
│  TypeScript + CSS   │
└──────────┬──────────┘
           │
           │ REST API
           ↓
┌─────────────────────┐
│       FastAPI       │
│       Backend       │
└──────────┬──────────┘
           │
     ┌─────┼─────┐
     ↓     ↓     ↓
   Web    PDF   Auth
 Import  Parser  JWT
     │     │
     └─────┼─────┘
           ↓
┌─────────────────────┐
│     SQLAlchemy      │
└──────────┬──────────┘
           ↓
┌─────────────────────┐
│     PostgreSQL      │
└─────────────────────┘

Technology Stack
Frontend
React
TypeScript
Vite
CSS
Backend
Python
FastAPI
SQLAlchemy
Pydantic
Uvicorn
Database
PostgreSQL
Authentication
JWT
Passlib
bcrypt
Data Processing
HTTPX
BeautifulSoup
pypdf
SHA-256 hashing

Source Versioning

ResearchVault preserves different versions of a source instead of overwriting previously stored content.

Source
 ├── Version 1
 ├── Version 2
 └── Version 3

Each source version stores:

Version number
Extracted content
Content hash
Creation timestamp
Source relationship

Source Change Detection

When a web source is re-fetched, ResearchVault extracts its content and calculates a SHA-256 hash.

The new hash is compared with the latest stored version.

Web Source
    ↓
Fetch Content
    ↓
Extract Text
    ↓
SHA-256 Hash
    ↓
Compare with Previous Hash
    ↓
 ┌───────────────┐
 │               │
Same           Different
 │               │
 ↓               ↓
Unchanged     New Version
                  ↓
            Change Detected
PDF Processing

ResearchVault supports importing text-based PDF documents.

PDF File
   ↓
FastAPI Upload
   ↓
pypdf
   ↓
Text Extraction
   ↓
SHA-256 Hash
   ↓
Source Version
   ↓
PostgreSQL

Note: Scanned or image-only PDFs requiring OCR are not currently supported.

Evidence and Claims

Evidence represents an exact passage extracted from a source version.

Claims represent research conclusions created within a workspace.

A claim can be connected to one or more evidence records.

Claim
  ↓
Evidence
  ↓
Source Version
  ↓
Source
  ↓
Original URL / PDF

This provides traceability between a conclusion and its supporting research material.

Search

ResearchVault provides a search interface for finding:

Claims
Evidence

Users can search research content directly from the dashboard.

Main API Endpoints
Authentication
POST /register
POST /login
Workspaces
POST   /workspaces
GET    /workspaces
GET    /workspaces/{workspace_id}
PUT    /workspaces/{workspace_id}
DELETE /workspaces/{workspace_id}
Sources
POST /workspaces/{workspace_id}/sources
POST /workspaces/{workspace_id}/sources/import-url
POST /workspaces/{workspace_id}/sources/import-pdf
Versions
POST /sources/{source_id}/versions
GET  /sources/{source_id}/versions
POST /sources/{source_id}/refetch
GET  /sources/{source_id}/changes
Evidence and Claims
POST /versions/{version_id}/evidence
POST /workspaces/{workspace_id}/claims
POST /claims/{claim_id}/evidence/{evidence_id}
GET  /claims/{claim_id}/provenance
Search
GET /search
Project Structure
ResearchVault/
│
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── database.py
│   │   ├── dependencies.py
│   │   ├── auth.py
│   │   └── ingestion.py
│   │
│   ├── venv/
│   ├── .env
│   └── test_source.html
│
├── frontend/
│   ├── src/
│   │   ├── App.tsx
│   │   ├── App.css
│   │   ├── index.css
│   │   └── main.tsx
│   ├── public/
│   └── package.json
│
├── screenshots/
│   ├── dashboard.png
│   ├── search.png
│   ├── url-import.png
│   ├── pdf-import.png
│   ├── change-detection.png
│   └── provenance.png
│
└── README.md
Screenshots
Dashboard

Research Search

Web Source Import

PDF Import

Source Change Detection

Evidence and Provenance

Running the Project
Backend
cd backend
.\venv\Scripts\activate
python -m uvicorn app.main:app --reload

Backend:

http://127.0.0.1:8000

Swagger documentation:

http://127.0.0.1:8000/docs
Frontend

Open another terminal:

cd frontend
npm install
npm run dev

Then open the URL provided by Vite, usually:

http://localhost:5173
Security

Sensitive configuration files are excluded from version control.

.env
venv/
__pycache__/
*.pyc

Database credentials are stored in the local .env file and should not be committed to GitHub.

Future Enhancements
OCR support for scanned PDFs
Background processing with Celery and Redis
Advanced full-text search
Semantic search
Embedding-based search
AI-assisted research summaries
Automatic claim generation
Visual source diffing
Source change notifications
Research export functionality
Cloud deployment
Docker support
Project Goal

ResearchVault demonstrates practical full-stack development concepts including:

REST API development
JWT authentication
PostgreSQL database design
React frontend development
Web content extraction
PDF processing
Source versioning
Hash-based change detection
Evidence management
Claim management
Data provenance
Search

The project combines these concepts into a single research management workflow.

Author

Anushiya D

B.Sc. Computer Science

ResearchVault — Personal Research Workspace