# Setup Guide

## Prerequisites

- **Python 3.11+**
- **Node.js 18+** and npm
- **Google Gemini API Key** -- get one from [Google AI Studio](https://aistudio.google.com/apikey)

## Quick Start

```bash
# Clone the repo
git clone https://github.com/hi-naresh/godcv.git
cd godcv

# Backend setup
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -e .

# Frontend setup
cd frontend
npm install
cd ..

# Configure
echo "GEMINI_API_KEY=your_key_here" > .env

# Run (two terminals)
godcv run --dev          # Backend on :9000
cd frontend && npm run dev  # Frontend on :3000
```

Open `http://localhost:3000` in your browser.

## Detailed Setup

### Backend

The backend is a FastAPI application using SQLite for persistence.

```bash
python -m venv venv
source venv/bin/activate
pip install -e .
```

**Optional:** For server-side PDF export, install WeasyPrint:

```bash
pip install weasyprint
```

WeasyPrint requires system dependencies -- see [WeasyPrint docs](https://doc.courtbouillon.org/weasyprint/stable/first_steps.html).

### Frontend

```bash
cd frontend
npm install
```

### Environment Variables

Create a `.env` file in the project root:

| Variable | Required | Description |
|----------|----------|-------------|
| `GEMINI_API_KEY` | Yes | Google Gemini API key (can also be set per-profile in the UI) |

### Running

**Development mode** (with hot-reload and CORS):

```bash
# Terminal 1 -- Backend
godcv run --dev

# Terminal 2 -- Frontend
cd frontend
npm run dev
```

**Production mode:**

```bash
# Build frontend
cd frontend && npm run build && cd ..

# Run backend (serves built frontend)
godcv run --port 8080
```

The backend serves the built frontend from `frontend/dist/` automatically.

### Database

SQLite database is auto-created at `data/godcv.db` on first run. No migrations needed -- tables are created via `CREATE TABLE IF NOT EXISTS` on startup.

## Testing

```bash
# Backend tests
pytest

# Frontend tests
cd frontend
npm test
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `GEMINI_API_KEY not found` | Create `.env` file or set the key in Profile tab |
| `Port 9000 in use` | Use `godcv run --port 8081` |
| Frontend can't reach API | Ensure backend is running; Vite proxies `/api` to `:9000` |
| WeasyPrint errors | It's optional; client-side PDF export works without it |
| Database locked | Stop any other godcv processes; SQLite uses WAL mode for concurrent reads |
