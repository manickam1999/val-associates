# Vel PDF Converter

A full-stack application for converting Malaysian STR (Statutory Reports) PDFs to Excel format with real-time progress tracking.

## Overview

This project consists of two main services:
- **vel-pdf-api**: FastAPI backend for PDF processing and data extraction
- **vel-pdf-web**: Next.js frontend with modern React UI

## Features

- Upload single or multiple PDF files
- Support for ZIP files containing multiple PDFs
- Extract structured data from Malaysian STR forms
- Real-time progress updates via WebSocket
- Download consolidated Excel output in multiple formats
- Dark/Light theme support
- Responsive modern UI

## Quick Start with Docker Compose

### Prerequisites

- Docker (20.10 or higher)
- Docker Compose (2.0 or higher)

### 1. Clone the Repository

```bash
git clone <repository-url>
cd val-associates
```

### 2. Configure Environment

The `.env` file in the root directory contains all configuration:

```bash
# Port Configuration
API_PORT=8000
WEB_PORT=3000

# API Configuration
CORS_ORIGINS=http://localhost:3000
MAX_FILE_SIZE=104857600

# Frontend API URLs
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000
```

### 3. Build and Run

Start all services:

```bash
docker-compose up --build
```

Or run in detached mode:

```bash
docker-compose up -d
```

### 4. Access the Application

- **Web Interface**: http://localhost:3000
- **API Documentation**: http://localhost:8000/docs
- **API Health Check**: http://localhost:8000/health

### 5. Stop Services

```bash
docker-compose down
```

To remove volumes as well:

```bash
docker-compose down -v
```

## Docker Compose Services

### vel-pdf-api

- **Port**: 8000 (configurable via `API_PORT`)
- **Health Check**: `/health` endpoint
- **Volumes**:
  - `api_uploads`: Temporary file storage
  - `api_outputs`: Generated Excel files

### vel-pdf-web

- **Port**: 3000 (configurable via `WEB_PORT`)
- **Dependencies**: Waits for `vel-pdf-api` to be healthy
- **Environment**: Production-optimized Next.js build

## Development

### Running Services Individually

#### Backend (vel-pdf-api)

```bash
cd vel-pdf-api
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

See [vel-pdf-api/README.md](vel-pdf-api/README.md) for more details.

#### Frontend (vel-pdf-web)

```bash
cd vel-pdf-web
npm install
npm run dev
```

See [vel-pdf-web/README.md](vel-pdf-web/README.md) for more details.

## Tech Stack

### Backend
- FastAPI (Python web framework)
- WebSocket (real-time communication)
- pdfplumber (PDF extraction)
- pandas (data manipulation)
- openpyxl (Excel generation)

### Frontend
- Next.js 15.5 (React framework)
- React 19 (UI library)
- TypeScript (type safety)
- Tailwind CSS v4 (styling)
- shadcn/ui (component library)
- next-themes (theme management)

## API Endpoints

### Health Check
```
GET /health
```

### Upload Files
```
POST /api/upload
Content-Type: multipart/form-data

Form Data:
  files: [PDF or ZIP files]

Response:
{
  "session_id": "uuid",
  "message": "Files uploaded successfully",
  "total_files": 5
}
```

### WebSocket Progress
```
WS /ws/progress/{session_id}?modes=everything,minimal

Messages:
{
  "current": 3,
  "total": 5,
  "status": "processing",
  "message": "Processing file3.pdf",
  "elapsed_time": 12.5
}
```

### Download Excel
```
GET /api/download/{session_id}?mode=everything

Response: Excel file download
```

### Cleanup Session
```
DELETE /api/cleanup/{session_id}

Response:
{
  "message": "Session cleaned up successfully"
}
```

## Data Formats

The service supports two Excel output formats:

1. **Everything Mode**: Complete data with all fields
2. **Minimal Mode**: Essential fields only

Each PDF is converted to a row with columns for:
- Applicant information (`pemohon_*`)
- Spouse information (`pasangan_*`)
- Beneficiaries (`waris_*`)
- Children (up to 10, `anak_*`)
- Document metadata (`document_*`)
- Source file information

## Volumes and Data Persistence

Docker volumes are used to persist data:

- `api_uploads`: Stores uploaded PDF/ZIP files
- `api_outputs`: Stores generated Excel files

To inspect volumes:

```bash
docker volume ls
docker volume inspect val-associates_api_uploads
```

## Networking

Services communicate via the `vel-pdf-network` bridge network:

- Frontend connects to backend using container name `vel-pdf-api`
- External access is through exposed ports

## Troubleshooting

### Check Service Logs

```bash
# All services
docker-compose logs

# Specific service
docker-compose logs vel-pdf-api
docker-compose logs vel-pdf-web

# Follow logs
docker-compose logs -f
```

### Check Service Health

```bash
# API health
curl http://localhost:8000/health

# Web accessibility
curl http://localhost:3000
```

### Rebuild Services

```bash
# Rebuild without cache
docker-compose build --no-cache

# Rebuild and restart
docker-compose up --build --force-recreate
```

### Port Conflicts

If ports 3000 or 8000 are already in use, change them in `.env`:

```bash
API_PORT=8001
WEB_PORT=3001
```

Then update `NEXT_PUBLIC_API_URL` and `NEXT_PUBLIC_WS_URL` accordingly.

## Production Deployment

For production deployment:

1. Update `.env` with your domain:
```bash
NEXT_PUBLIC_API_URL=https://api.yourdomain.com
NEXT_PUBLIC_WS_URL=wss://api.yourdomain.com
CORS_ORIGINS=https://yourdomain.com
```

2. Use a reverse proxy (nginx/traefik) for SSL termination

3. Configure proper volume backups

4. Set up monitoring and logging

5. Review security settings and CORS origins

## License

MIT

## Support

For issues and feature requests, please open an issue in the repository.
