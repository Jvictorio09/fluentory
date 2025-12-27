# Fix: column myApp_teacher.bio does not exist

## Problem
The database table `myApp_teacher` exists but is missing the `bio` column, even though it's defined in the model and migration 0004.

## Solution

The migration 0004 already includes the `bio` field, so you need to ensure migrations are applied. Here are the steps:

### Option 1: Run Migrations (Recommended)
1. Activate your conda environment:
   ```bash
   conda activate myenv
   ```

2. Check migration status:
   ```bash
   python manage.py showmigrations myApp
   ```

3. If migration 0004 shows as unapplied `[ ]`, run:
   ```bash
   python manage.py migrate myApp
   ```

4. If you get an error that tables already exist, you may need to fake the migration:
   ```bash
   python manage.py migrate myApp 0004 --fake
   ```

### Option 2: Add Missing Column Manually (If migrations fail)
If migrations don't work, you can add the column directly to the database:

**For PostgreSQL:**
```sql
ALTER TABLE myapp_teacher ADD COLUMN bio TEXT;
```

**For SQLite:**
```sql
ALTER TABLE myapp_teacher ADD COLUMN bio TEXT;
```

Then mark the migration as applied:
```bash
python manage.py migrate myApp 0004 --fake
```

### Option 3: Check if Column Exists
First, check if the column actually exists in your database. The error suggests it doesn't, but verify:

**For PostgreSQL:**
```sql
SELECT column_name 
FROM information_schema.columns 
WHERE table_name='myapp_teacher' AND column_name='bio';
```

If no rows are returned, the column doesn't exist and you need to add it (use Option 1 or 2).

## After Fixing
Once the column is added, restart your Django development server and the error should be resolved.


