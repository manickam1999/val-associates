# Vel PDF API

Backend service for converting Malaysian STR PDFs to Excel format with real-time progress tracking.

## Features

- Upload single or multiple PDF files
- Upload ZIP files containing PDFs
- Extract structured data from Malaysian STR forms
- Real-time progress updates via WebSocket
- Generate consolidated Excel file with all data
- RESTful API with CORS support

## Tech Stack

- **FastAPI** - Modern Python web framework
- **WebSocket** - Real-time progress updates
- **pdfplumber** - PDF text and table extraction
- **pandas** - Data manipulation and Excel generation

## Setup

### 1. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Environment Configuration

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

Default configuration:
```
PORT=8000
HOST=0.0.0.0
CORS_ORIGINS=http://localhost:3000,http://localhost:3001
MAX_FILE_SIZE=104857600
UPLOAD_DIR=uploads
OUTPUT_DIR=outputs
```

### 4. Run Server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

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
WS /ws/progress/{session_id}

Messages:
{
  "current": 3,
  "total": 5,
  "status": "processing",
  "message": "Processing file3.pdf"
}
```

### Download Excel
```
GET /api/download/{session_id}

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

## Data Structure

Each PDF is converted to a row with columns:
- `pemohon_*` - Applicant information
- `pasangan_*` - Spouse information
- `waris_*` - Beneficiary information
- `anak_*` - Children information (up to 10)
- `document_*` - Document metadata
- `source_file` - Original PDF filename

## Development

### Project Structure
```
vel-pdf-api/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app
│   ├── models.py            # Pydantic models
│   ├── str_extractor.py     # PDF extraction logic
│   └── batch_processor.py   # Multi-file processing
├── uploads/                 # Temp upload storage
├── outputs/                 # Generated Excel files
├── requirements.txt
├── .env
└── README.md
```

### API Documentation

Once running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## License

MIT