# ⚠️ CRITICAL DATABASE SAFETY WARNING

## Problem Found and Fixed

**The GitHub Actions deploy workflow was automatically resetting the production database when migrations failed!**

### What Happened:
- When `python3 manage.py migrate` failed during deployment
- The workflow would run `reset_database.py`
- This script **DELETES THE ENTIRE DATABASE** and creates a fresh one
- **ALL YOUR DATA WAS LOST** (customers, tailors, fabrics, orders, etc.)

### What Was Fixed:

1. **GitHub Actions Workflow** (`.github/workflows/deploy.yml`):
   - ❌ **REMOVED** automatic database reset on migration failure
   - ✅ Now **FAILS SAFELY** instead of deleting data
   - Migration failures now stop deployment and require manual investigation

2. **reset_database.py Script**:
   - ✅ Added **PRODUCTION BLOCK** - script will refuse to run in production
   - ✅ Requires explicit environment override to run in production
   - ✅ Added clear warnings about data loss

### How to Prevent This in the Future:

1. **NEVER** run `reset_database.py` in production
2. **ALWAYS** create backups before any database operations
3. **Test migrations** in development/staging first
4. **Monitor** GitHub Actions logs for migration failures
5. **Use database backups** before deploying major changes

### If Migrations Fail:

1. **DO NOT** reset the database
2. **Investigate** the migration error
3. **Fix** the migration or rollback the code
4. **Test** in development first
5. **Create backup** before attempting fix

### Database Backup Commands:

**For SQLite (development):**
```bash
cp db.sqlite3 db_backup_$(date +%Y%m%d_%H%M%S).sqlite3
```

**For PostgreSQL (production):**
```bash
pg_dump -U zthob_user -d zthob_prod > backup_$(date +%Y%m%d_%H%M%S).sql
```

### Recovery:

If your database was already reset, you may be able to recover from:
- Server backups (check `/var/backups/zthob/`)
- Database backups created by the workflow
- Manual backups you created

**Check for backups:**
```bash
ls -la /var/backups/zthob/
```

