import logging
from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

logger = logging.getLogger("migration")

# Column definitions for expenses table schema synchronization
EXPENSES_COLUMN_DEFINITIONS = [
    ("payment_method", "VARCHAR(50) NOT NULL DEFAULT 'UPI'"),
    ("merchant", "VARCHAR(150)"),
    ("description", "VARCHAR(255)"),
    ("transaction_type", "VARCHAR(20) NOT NULL DEFAULT 'EXPENSE'"),
    ("currency", "VARCHAR(10) NOT NULL DEFAULT 'INR'"),
    ("subcategory", "VARCHAR(100)"),
    ("source_app", "VARCHAR(100)"),
    ("transaction_timestamp", "DATETIME"),
    ("status", "VARCHAR(20) NOT NULL DEFAULT 'SUCCESS'"),
    ("confidence", "FLOAT NOT NULL DEFAULT 1.0"),
    ("is_automatically_detected", "BOOLEAN NOT NULL DEFAULT 0"),
    ("fingerprint", "VARCHAR(64)"),
    ("created_at", "DATETIME"),
    ("updated_at", "DATETIME"),
]


def run_migrations(engine: Engine):
    """
    Safely and idempotently migrates the SQLite database schema to ensure
    all SQLAlchemy model fields are present in the underlying tables.
    Preserves all existing user and expense records.
    """
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()

    if "expenses" not in existing_tables:
        logger.info("Table 'expenses' does not exist yet; Base.metadata.create_all will create it.")
        return

    existing_cols = {col["name"] for col in inspector.get_columns("expenses")}
    added_columns = []

    with engine.begin() as conn:
        # 1. Add any missing columns to expenses table
        for col_name, col_def in EXPENSES_COLUMN_DEFINITIONS:
            if col_name not in existing_cols:
                sql = f"ALTER TABLE expenses ADD COLUMN {col_name} {col_def}"
                logger.info(f"Adding missing column to expenses: {col_name}")
                conn.execute(text(sql))
                added_columns.append(col_name)

        # 2. Ensure unique index on fingerprint exists (if fingerprint column exists)
        if "fingerprint" in existing_cols or "fingerprint" in added_columns:
            conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_expenses_fingerprint ON expenses (fingerprint);"))

        # 3. Safe backfill for existing records
        if added_columns:
            # Only backfill created_at if it exists (for legacy databases)
            if "created_at" in existing_cols:
                conn.execute(text("UPDATE expenses SET updated_at = created_at WHERE updated_at IS NULL AND created_at IS NOT NULL;"))
            else:
                # For very old databases without created_at, set updated_at to current time
                conn.execute(text("UPDATE expenses SET updated_at = datetime('now') WHERE updated_at IS NULL;"))
            
            # Populate merchant from title for legacy manual records where merchant is null
            conn.execute(text("UPDATE expenses SET merchant = title WHERE merchant IS NULL AND title IS NOT NULL;"))
            # Ensure defaults on legacy records
            conn.execute(text("UPDATE expenses SET transaction_type = 'EXPENSE' WHERE transaction_type IS NULL;"))
            conn.execute(text("UPDATE expenses SET status = 'SUCCESS' WHERE status IS NULL;"))
            conn.execute(text("UPDATE expenses SET currency = 'INR' WHERE currency IS NULL;"))
            conn.execute(text("UPDATE expenses SET confidence = 1.0 WHERE confidence IS NULL;"))
            conn.execute(text("UPDATE expenses SET is_automatically_detected = 0 WHERE is_automatically_detected IS NULL;"))

    if added_columns:
        logger.info(f"Schema migration completed successfully. Added columns: {added_columns}")
    else:
        logger.info("Schema migration check completed: All columns already exist.")


if __name__ == "__main__":
    import os
    import sys

    # Allow direct execution: python backend/app/database/migration.py
    backend_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if backend_root not in sys.path:
        sys.path.insert(0, backend_root)

    logging.basicConfig(level=logging.INFO)
    from app.database.database import engine

    logger.info("Running standalone database migration...")
    run_migrations(engine)
    logger.info("Migration complete!")
