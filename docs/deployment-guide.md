# PlanWeaver Deployment Guide

This guide covers deploying PlanWeaver in various environments.

## Table of Contents

- [Quick Start (Local)](#quick-start-local)
- [Docker Deployment](#docker-deployment)
- [Docker Compose](#docker-compose)
- [Environment Configuration](#environment-configuration)
- [Production Considerations](#production-considerations)
- [Troubleshooting](#troubleshooting)

---

## Quick Start (Local)

### Prerequisites

- Python 3.10+
- API keys for LLM providers (see [Environment Configuration](#environment-configuration))

### Installation

```bash
# Clone repository
git clone https://github.com/your-org/planweaver.git
cd planweaver

# Install dependencies with uv
pip install uv
uv sync

# Set up environment
cp .env.example .env
# Edit .env with your API keys

# Run the server
uv run planweaver serve
```

The API server will be available at `http://localhost:8000`

---

## Docker Deployment

### Building the Image

```bash
# Build backend image
docker build -t planweaver-backend .

# Build frontend image
docker build -t planweaver-frontend ./frontend
```

### Running with Docker

**Backend only:**
```bash
docker run -d \
  --name planweaver-api \
  -p 8000:8000 \
  --env-file .env \
  -v planweaver-data:/app/data \
  planweaver-backend
```

**Frontend only:**
```bash
docker run -d \
  --name planweaver-frontend \
  -p 5173:5173 \
  planweaver-frontend
```

---

## Docker Compose

The easiest way to run PlanWeaver with all components.

### Basic Usage

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Stop and remove volumes
docker-compose down -v
```

### Docker Compose Configuration

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  backend:
    build: .
    container_name: planweaver-api
    ports:
      - "8000:8000"
    environment:
      - GOOGLE_API_KEY=${GOOGLE_API_KEY}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - DATABASE_URL=sqlite:///./data/planweaver.db
    volumes:
      - planweaver-data:/app/data
    restart: unless-stopped

  frontend:
    build: ./frontend
    container_name: planweaver-frontend
    ports:
      - "5173:5173"
    depends_on:
      - backend
    environment:
      - VITE_API_URL=http://localhost:8000
    restart: unless-stopped

volumes:
  planweaver-data:
```

---

## Environment Configuration

### Required Environment Variables

Create a `.env` file from `.env.example`:

```bash
# .env.example

# Primary API Keys (Required)
GOOGLE_API_KEY=your-google-api-key          # For Gemini models (recommended)
ANTHROPIC_API_KEY=your-anthropic-key       # For Claude models

# Optional API Keys
OPENAI_API_KEY=your-openai-key             # For GPT models
OPENROUTER_API_KEY=your-openrouter-key     # For DeepSeek and other models

# External Context Features (Optional)
GITHUB_TOKEN=your-github-pat               # For private repos
TAVILY_API_KEY=your-tavily-key             # For web search
SEARCH_PROVIDER=tavily                     # tavily, serper, or duckduckgo
MAX_FILE_SIZE_MB=10                        # File upload limit

# Model Configuration
DEFAULT_PLANNER_MODEL=gemini-2.5-flash
DEFAULT_EXECUTOR_MODEL=gemini-3-flash

# Database
DATABASE_URL=sqlite:///./planweaver.db

# Server Configuration
HOST=0.0.0.0
PORT=8000
RELOAD=false
```

### API Key Sources

| Provider | Key Source | Cost (approx.) |
|----------|------------|----------------|
| **Google Gemini** | [Google AI Studio](https://makersuite.google.com/app/apikey) | Free tier available |
| **Anthropic Claude** | [Anthropic Console](https://console.anthropic.com/) | Paid |
| **OpenAI** | [OpenAI Platform](https://platform.openai.com/api-keys) | Paid |
| **OpenRouter** | [OpenRouter Keys](https://openrouter.ai/keys) | Pay-per-use |

---

## Production Considerations

### Database

**Development:** SQLite (default)
```bash
DATABASE_URL=sqlite:///./planweaver.db
```

**Production:** PostgreSQL (recommended)
```bash
# Install PostgreSQL adapter
uv add psycopg2-binary

# Update DATABASE_URL
DATABASE_URL=postgresql://user:password@host:port/database
```

### Security

1. **API Keys:**
   - Never commit `.env` files
   - Use environment variable injection in production
   - Rotate keys regularly

2. **CORS:**
   ```python
   # In src/planweaver/api/main.py
   from fastapi.middleware.cors import CORSMiddleware

   app.add_middleware(
       CORSMiddleware,
       allow_origins=["https://yourdomain.com"],
       allow_credentials=True,
       allow_methods=["*"],
       allow_headers=["*"],
   )
   ```

3. **Rate Limiting:**
   - Implement rate limiting for API endpoints
   - Consider using `slowapi` or similar

4. **HTTPS:**
   - Always use HTTPS in production
   - Set up reverse proxy with nginx or traefik

### Performance

1. **Caching:**
   - Cache LLM responses where appropriate
   - Consider Redis for distributed caching

2. **Connection Pooling:**
   - Configure database connection pool
   - Reuse LLM client connections

3. **Monitoring:**
   - Set up logging aggregation
   - Monitor API usage and costs
   - Track execution times

### Scaling

1. **Horizontal Scaling:**
   - Use PostgreSQL for shared database
   - Implement session affinity if needed
   - Consider message queue for async jobs

2. **Load Balancing:**
   - Place API servers behind load balancer
   - Use nginx or cloud load balancer

---

## Cloud Deployment

### AWS

1. **ECS/Fargate:**
   - Use Docker Compose configuration as base
   - Store environment variables in AWS Secrets Manager
   - Use RDS for PostgreSQL

2. **Lambda:**
   - Requires custom runtime or container image
   - Not recommended for long-running tasks

### Google Cloud

1. **Cloud Run:**
   ```bash
   gcloud run deploy planweaver \
     --image gcr.io/PROJECT_ID/planweaver \
     --platform managed \
     --region us-central1 \
     --allow-unauthenticated
   ```

2. **Cloud SQL:**
   - Managed PostgreSQL database
   - Private IP connection for security

### Azure

1. **Container Instances:**
   - Similar to Cloud Run
   - Quick deployment option

2. **Azure Database for PostgreSQL:**
   - Managed database service

---

## Reverse Proxy (nginx)

Example nginx configuration:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

---

## Troubleshooting

### Common Issues

**1. API Connection Errors**

```bash
# Check API key is set
echo $GOOGLE_API_KEY

# Test API key
curl -H "x-api-key: $GOOGLE_API_KEY" \
  https://generativelanguage.googleapis.com/v1beta/models
```

**2. Database Lock Errors**

```bash
# SQLite doesn't handle concurrent writes well
# Consider PostgreSQL for production
rm planweaver.db  # Reset database (development only)
```

**3. Docker Volume Permissions**

```bash
# Fix permission issues
sudo chown -R $USER:$USER ./data
```

**4. Port Already in Use**

```bash
# Find process using port
lsof -i :8000

# Kill process
kill -9 <PID>
```

### Health Checks

```bash
# Check API health
curl http://localhost:8000/health

# Check database
sqlite3 planweaver.db ".tables"

# View logs
docker-compose logs -f backend
```

### Debug Mode

Enable debug logging:

```bash
# .env
LOG_LEVEL=debug

# Or pass via CLI
uv run planweaver serve --log-level debug
```

---

## Backup and Recovery

### Database Backup

**SQLite:**
```bash
# Backup
cp planweaver.db planweaver.db.backup

# Or use sqlite3
sqlite3 planweaver.db ".backup planweaver.db.backup"
```

**PostgreSQL:**
```bash
# Backup
pg_dump -U user -h host dbname > backup.sql

# Restore
psql -U user -h host dbname < backup.sql
```

### Automated Backups

Use cron jobs or cloud-native backup solutions:

```bash
# Cron job for daily backups
0 2 * * * cp /app/data/planweaver.db /backups/planweaver-$(date +\%Y\%m\%d).db
```

---

## Monitoring and Logging

### Application Logs

```bash
# View logs
docker-compose logs -f backend

# Save logs
docker-compose logs backend > logs.txt
```

### Metrics to Track

- API response times
- LLM usage and costs
- Database query performance
- Error rates
- Active sessions

### Tools

- **Logging**: structlog, loguru
- **Metrics**: Prometheus, Grafana
- **APM**: Sentry, Datadog

---

## Support

For deployment issues:

1. Check [troubleshooting.md](troubleshooting.md)
2. Search existing [GitHub Issues](https://github.com/your-org/planweaver/issues)
3. Create new issue with details

---

## Next Steps

- Read [architecture.md](architecture.md) for system design
- See [CONTRIBUTING.md](../CONTRIBUTING.md) for development setup
- Check [external-context-guide.md](external-context-guide.md) for advanced features
