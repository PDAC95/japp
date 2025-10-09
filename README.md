# JAPPI Health Coach - Backend API

FastAPI backend for JAPPI Health Coach application.

## Quick Start

```bash
# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (Mac/Linux)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run development server
uvicorn app.main:app --reload --port 8000
```

## API Documentation

See [API_DOCUMENTATION.md](./API_DOCUMENTATION.md) for complete API reference.

**Interactive Docs:**
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Project Structure

```
app/
├── api/
│   └── v1/
│       └── endpoints/          # API route handlers
├── core/
│   ├── config.py              # App configuration
│   └── security.py            # Auth utilities
├── models/                    # Pydantic models
├── services/                  # Business logic
│   └── claude.py             # Claude API integration
└── main.py                   # FastAPI app entry
```

## Environment Variables

Create `.env` file:

```env
# App
APP_NAME=JAPPI Health Coach API
APP_VERSION=1.0.0
DEBUG=True

# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
SUPABASE_SERVICE_KEY=your-service-key

# Claude API
ANTHROPIC_API_KEY=sk-ant-xxx

# CORS
ALLOWED_ORIGINS=http://localhost:4000,https://jappi.app
```

## API Endpoints

### Authentication (Supabase)
- `POST /auth/v1/signup` - User registration
- `POST /auth/v1/token` - User login
- `POST /auth/v1/logout` - User logout
- `POST /auth/v1/recover` - Password reset

### Profile
- `GET /api/v1/profile` - Get user profile
- `POST /api/v1/profile` - Create/update profile

### Meals
- `GET /api/v1/meals` - Get meal history
- `POST /api/v1/meals` - Log meal entry
- `PUT /api/v1/meals/{id}` - Update meal
- `DELETE /api/v1/meals/{id}` - Delete meal

### Chat
- `POST /api/v1/chat` - Send message to AI coach
- `GET /api/v1/chat/history` - Get chat history

### Fasting
- `GET /api/v1/fasting/current` - Get fasting status
- `POST /api/v1/fasting/start` - Start fasting
- `POST /api/v1/fasting/end` - End fasting
- `GET /api/v1/fasting/history` - Get fasting history

### Analytics
- `GET /api/v1/analytics/daily` - Daily summary
- `GET /api/v1/analytics/weekly` - Weekly summary
- `GET /api/v1/analytics/progress` - Progress stats

## Tech Stack

- **Framework:** FastAPI 0.115+
- **Authentication:** Supabase Auth
- **Database:** PostgreSQL (via Supabase)
- **AI:** Anthropic Claude API
- **Validation:** Pydantic v2
- **CORS:** FastAPI middleware

## Development

```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Run tests
pytest

# Format code
black app/
isort app/

# Lint
flake8 app/
mypy app/
```

## Deployment

See deployment guide in root `/docs/DEPLOYMENT.md`

## License

Private - JAPPI Health Coach
