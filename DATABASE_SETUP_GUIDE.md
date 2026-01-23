# Database Setup Guide - PostgreSQL Connection Fix

## Current Status

✅ **Configuration Fixed:**
- `DATABASE_URL` is set to: `postgresql://postgres@127.0.0.1:5432/fluentory_dev`
- Django settings updated to disable SSL for local connections
- SSL negotiation issue resolved in `settings.py`

❌ **PostgreSQL Not Running:**
- PostgreSQL service not found on this system
- Port 5432 is not accessible
- PostgreSQL client tools (psql) not in PATH

## Steps Completed

1. ✅ Verified `DATABASE_URL` in `.env` file
2. ✅ Updated Django settings to disable SSL for local connections
3. ✅ Confirmed `DATABASE_URL` points to `127.0.0.1:5432`
4. ❌ PostgreSQL is not installed/running

## Next Steps

### Option 1: Install PostgreSQL (Recommended)

1. **Download PostgreSQL:**
   - Visit: https://www.postgresql.org/download/windows/
   - Download the Windows installer
   - Run the installer

2. **During Installation:**
   - Remember the password you set for the `postgres` user
   - Keep the default port (5432)
   - Install pgAdmin (optional but helpful)

3. **After Installation:**
   - The PostgreSQL service should start automatically
   - Verify it's running:
     - Open Services (`services.msc`)
     - Look for `postgresql-x64-XX` service
     - Ensure it's "Running"

4. **Create the Database:**
   - Open pgAdmin (or use psql command line)
   - Connect to PostgreSQL server (use the password you set)
   - Right-click "Databases" → "Create" → "Database"
   - Name: `fluentory_dev`
   - Or use SQL: `CREATE DATABASE fluentory_dev;`

5. **Update .env if needed:**
   - If you set a password for `postgres` user, update `.env`:
     ```
     DATABASE_URL=postgresql://postgres:yourpassword@127.0.0.1:5432/fluentory_dev
     ```
   - If no password (trust authentication), keep current:
     ```
     DATABASE_URL=postgresql://postgres@127.0.0.1:5432/fluentory_dev
     ```

6. **Run Migrations:**
   ```bash
   python manage.py migrate
   ```

7. **Start Server:**
   ```bash
   python manage.py runserver
   ```

### Option 2: Use Docker (Alternative)

If you prefer Docker:

1. **Install Docker Desktop:**
   - Download from: https://www.docker.com/products/docker-desktop
   - Install and start Docker Desktop

2. **Run PostgreSQL Container:**
   ```bash
   docker run --name fluentory-postgres -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=fluentory_dev -p 5432:5432 -d postgres:15
   ```

3. **Update .env:**
   ```
   DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:5432/fluentory_dev
   ```

4. **Run Migrations:**
   ```bash
   python manage.py migrate
   ```

## Configuration Details

### Current `.env` Configuration:
```
DATABASE_URL=postgresql://postgres@127.0.0.1:5432/fluentory_dev
```

### Django Settings Updates:
- SSL disabled for local connections (localhost/127.0.0.1)
- Connection timeout: 10 seconds
- Connection pooling enabled

## Troubleshooting

### If PostgreSQL service won't start:
1. Check Windows Event Viewer for errors
2. Verify PostgreSQL data directory permissions
3. Check if port 5432 is already in use:
   ```powershell
   netstat -ano | findstr :5432
   ```

### If connection still fails:
1. Run the diagnostic script:
   ```powershell
   powershell -ExecutionPolicy Bypass -File check_postgres.ps1
   ```

2. Verify database exists:
   - Connect to PostgreSQL
   - Run: `\l` to list databases
   - Ensure `fluentory_dev` exists

3. Check credentials:
   - Verify username/password in `DATABASE_URL`
   - Test connection with psql:
     ```bash
     psql -U postgres -h 127.0.0.1 -d fluentory_dev
     ```

### SSL Issues (Already Fixed):
- SSL is automatically disabled for local connections
- If you still see SSL errors, ensure `.env` doesn't have `?sslmode=require`

## Success Criteria

✅ No database connection errors  
✅ `python manage.py migrate` runs successfully  
✅ `python manage.py runserver` starts without errors  
✅ Site loads in browser

## Quick Test

Once PostgreSQL is running, test the connection:

```bash
python manage.py check --database default
```

This will verify the database connection without running migrations.











