# Fluentory

## Local Development Setup

### Prerequisites

- Python 3.12+
- PostgreSQL (for local development - recommended to match production)
- Virtual environment

### Database Setup

This project uses PostgreSQL for both local development and production to avoid migration incompatibilities.

1. **Install PostgreSQL** (if not already installed):
   - Windows: Download from [PostgreSQL Downloads](https://www.postgresql.org/download/windows/)
   - macOS: `brew install postgresql`
   - Linux: `sudo apt-get install postgresql` (Ubuntu/Debian)

2. **Create a local database**:
   ```sql
   CREATE DATABASE fluentory_dev;
   ```

3. **Configure environment variables**:
   - Copy `.env.example` to `.env` (if it doesn't exist)
   - Update `DATABASE_URL` in `.env` with your PostgreSQL credentials:
     ```
     DATABASE_URL=postgresql://postgres@localhost:5432/fluentory_dev
     ```
     Or with password:
     ```
     DATABASE_URL=postgresql://postgres:yourpassword@localhost:5432/fluentory_dev
     ```

4. **Run migrations**:
   ```bash
   python manage.py migrate
   ```

### Running the Server

```bash
python manage.py runserver
```

### Why PostgreSQL for Local Development?

Using PostgreSQL locally ensures:
- Migration compatibility (some migrations use PostgreSQL-specific SQL)
- Same database engine as production
- No "SQLite vs Postgres" migration issues 
