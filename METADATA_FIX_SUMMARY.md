# Fix for SQLAlchemy Metadata Column Conflict

## Problem
The application was encountering a SQLAlchemy error:
```
Attribute name 'metadata' is reserved for the MetaData instance when using a declarative base
```

This error occurs because SQLAlchemy's declarative base already defines `metadata` as a reserved property that holds the schema's MetaData object. Any model attribute or column named `metadata` will conflict with this reserved name.

## Root Cause
The `RawFetchQueue` model in both `app_postgres.py` and `src/app_postgres.py` had a column defined as:
```python
metadata = db.Column(db.JSON, default={})
```

This conflicts with SQLAlchemy's reserved `Base.metadata` attribute.

## Solution
Renamed the problematic column from `metadata` to `meta_info` in the following files:

### 1. Model Definitions
- **File**: `app_postgres.py`
- **Change**: `metadata = db.Column(db.JSON, default={})` → `meta_info = db.Column(db.JSON, default={})`

### 2. Code References
- **File**: `app_postgres.py`
- **Change**: `metadata={'source': 'web_scraper'}` → `meta_info={'source': 'web_scraper'}`

- **File**: `src/services/ai_summarization.py`  
- **Change**: 
  ```python
  # Before
  item.metadata = {
      **item.metadata,
      'ai_insights': ai_result['key_insights'],
      'ai_tags': ai_result['tags'],
      'ai_processed_at': datetime.utcnow().isoformat()
  }
  
  # After
  item.meta_info = {
      **item.meta_info,
      'ai_insights': ai_result['key_insights'],
      'ai_tags': ai_result['tags'],
      'ai_processed_at': datetime.utcnow().isoformat()
  }
  ```

- **File**: `ai_summarization.py`
- **Change**: Same pattern as above

### 3. Database Schema
- **File**: `sql/schema.sql`
- **Change**: `metadata JSONB DEFAULT '{}'::jsonb` → `meta_info JSONB DEFAULT '{}'::jsonb`

## Migration Required
When deploying this fix to an existing database, you'll need to run a migration to rename the column:

```sql
ALTER TABLE raw_fetch_queue RENAME COLUMN metadata TO meta_info;
```

## Verification
The fix was tested successfully with a standalone test script that:
1. Created all models with SQLAlchemy
2. Successfully created database tables without the metadata conflict
3. Created and saved test records using the new `meta_info` column
4. Confirmed that the column works as expected for storing JSON data

## Files Changed
1. `app_postgres.py` - Model definition and usage
2. `src/services/ai_summarization.py` - Column references  
3. `ai_summarization.py` - Column references
4. `sql/schema.sql` - Database schema definition

The application should now work without the SQLAlchemy metadata attribute conflict.
