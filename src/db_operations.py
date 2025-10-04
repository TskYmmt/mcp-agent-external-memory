"""
Database operations module for managing SQLite databases with metadata tracking.
Provides core functions for creating, querying, and managing databases.
"""

import sqlite3
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database directory (at project root)
DB_DIR = Path(__file__).parent.parent / "databases"
DB_DIR.mkdir(exist_ok=True)


def _get_db_path(database_name: str) -> Path:
    """Get full path to database file, ensuring .db extension."""
    if not database_name.endswith(".db"):
        database_name += ".db"
    return DB_DIR / database_name


def _ensure_metadata_table(conn: sqlite3.Connection) -> None:
    """Create metadata table if it doesn't exist."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS _metadata (
            key TEXT PRIMARY KEY,
            value TEXT,
            created_at TEXT,
            updated_at TEXT
        )
    """)
    conn.commit()


def _update_metadata(conn: sqlite3.Connection, key: str, value: str) -> None:
    """Update or insert metadata entry."""
    now = datetime.now().isoformat()
    cursor = conn.execute("SELECT created_at FROM _metadata WHERE key = ?", (key,))
    existing = cursor.fetchone()

    if existing:
        conn.execute(
            "UPDATE _metadata SET value = ?, updated_at = ? WHERE key = ?",
            (value, now, key)
        )
    else:
        conn.execute(
            "INSERT INTO _metadata (key, value, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (key, value, now, now)
        )
    conn.commit()


def _validate_schema(schema: dict[str, Any]) -> tuple[bool, str]:
    """
    Validate database schema with metadata requirements.

    Args:
        schema: Schema dictionary to validate

    Returns:
        (is_valid, error_message)
    """
    # Check database_description
    if "database_description" not in schema:
        return False, (
            "必須項目 'database_description' がありません。\n"
            "データベース全体の目的を記述してください。\n\n"
            "例: {'database_description': '2025年顧客データ分析', 'tables': [...]}"
        )

    db_desc = schema["database_description"]
    if not isinstance(db_desc, str) or len(db_desc.strip()) < 5:
        return False, (
            "'database_description' は5文字以上の文字列で指定してください。\n"
            "このデータベースが何のために作成されるのか、具体的に説明してください。\n\n"
            "例: '2025年第1四半期の売上分析データ'"
        )

    # Check tables
    if "tables" not in schema or not isinstance(schema["tables"], list):
        return False, "'tables' は配列で指定してください。"

    if len(schema["tables"]) == 0:
        return False, "少なくとも1つのテーブル定義が必要です。"

    # Validate each table
    for i, table in enumerate(schema["tables"]):
        if not isinstance(table, dict):
            return False, f"テーブル {i+1} が不正な形式です。辞書で指定してください。"

        # Check table_name
        if "table_name" not in table:
            return False, f"テーブル {i+1} の 'table_name' が必須です。"

        if not isinstance(table["table_name"], str) or not table["table_name"].strip():
            return False, f"テーブル {i+1} の 'table_name' は非空の文字列で指定してください。"

        # Check table_description
        if "table_description" not in table:
            return False, (
                f"テーブル '{table['table_name']}' の 'table_description' が必須です。\n"
                f"このテーブルが何を格納するのか説明してください。\n\n"
                f"例: 'table_description': '顧客の基本情報と連絡先'"
            )

        table_desc = table["table_description"]
        if not isinstance(table_desc, str) or len(table_desc.strip()) < 5:
            return False, (
                f"テーブル '{table['table_name']}' の 'table_description' は5文字以上で指定してください。"
            )

        # Check columns
        if "columns" not in table or not isinstance(table["columns"], list):
            return False, f"テーブル '{table['table_name']}' の 'columns' は配列で指定してください。"

        if len(table["columns"]) == 0:
            return False, f"テーブル '{table['table_name']}' に少なくとも1つのカラムが必要です。"

        # Validate each column
        for j, col in enumerate(table["columns"]):
            if not isinstance(col, dict):
                return False, (
                    f"テーブル '{table['table_name']}' のカラム {j+1} が不正な形式です。"
                )

            # Check name
            if "name" not in col or not isinstance(col["name"], str) or not col["name"].strip():
                return False, (
                    f"テーブル '{table['table_name']}' のカラム {j+1} の 'name' が必須です。"
                )

            # Check type
            if "type" not in col or not isinstance(col["type"], str) or not col["type"].strip():
                return False, (
                    f"テーブル '{table['table_name']}' のカラム '{col.get('name', j+1)}' の 'type' が必須です。"
                )

            # Check description
            if "description" not in col:
                return False, (
                    f"テーブル '{table['table_name']}' のカラム '{col['name']}' の 'description' が必須です。\n"
                    f"このカラムが何を表すのか説明してください。\n\n"
                    f"例: 'description': '顧客の登録日時（UTC）'"
                )

            col_desc = col["description"]
            if not isinstance(col_desc, str) or len(col_desc.strip()) < 5:
                return False, (
                    f"テーブル '{table['table_name']}' のカラム '{col['name']}' の 'description' は5文字以上で指定してください。"
                )

    return True, ""


def create_database(
    database_name: str,
    schema: dict[str, Any]
) -> dict[str, Any]:
    """
    Create a new database with specified schema including metadata.

    Args:
        database_name: Database file name (without .db extension)
        schema: Database schema with metadata
            {
                "database_description": str (5+ chars),
                "tables": [
                    {
                        "table_name": str,
                        "table_description": str (5+ chars),
                        "columns": [
                            {
                                "name": str,
                                "type": str,
                                "description": str (5+ chars),
                                "constraints": str (optional)
                            }
                        ]
                    }
                ]
            }

    Returns:
        Dict with status, db_path, and created tables

    Raises:
        ValueError: If schema is invalid
        FileExistsError: If database already exists
    """
    # Validate schema
    is_valid, error_msg = _validate_schema(schema)
    if not is_valid:
        raise ValueError(error_msg)

    db_path = _get_db_path(database_name)

    # Check if database already exists
    if db_path.exists():
        raise FileExistsError(
            f"Database '{database_name}' already exists at {db_path}. "
            f"Use a different name or add data to the existing database."
        )

    logger.info(f"Creating database: {database_name}")
    logger.debug(f"Schema: {schema}")

    # Create database and tables
    conn = sqlite3.connect(db_path)
    try:
        # Create metadata table
        _ensure_metadata_table(conn)

        # Store database description
        _update_metadata(conn, "database_description", schema["database_description"])

        # Store complete schema as JSON for later retrieval
        _update_metadata(conn, "schema", json.dumps(schema, ensure_ascii=False))

        # Extract table names
        table_names = [table["table_name"] for table in schema["tables"]]
        _update_metadata(conn, "tables", json.dumps(table_names))

        # Create each table
        created_tables = []
        for table in schema["tables"]:
            table_name = table["table_name"]

            # Build CREATE TABLE statement
            column_defs = []
            for col in table["columns"]:
                col_def = f"{col['name']} {col['type']}"
                if col.get("constraints"):
                    col_def += f" {col['constraints']}"
                column_defs.append(col_def)

            create_sql = f"CREATE TABLE {table_name} ({', '.join(column_defs)})"
            logger.debug(f"Executing SQL: {create_sql}")

            conn.execute(create_sql)
            created_tables.append(table_name)

        conn.commit()

        return {
            "status": "success",
            "message": f"Database '{database_name}' created successfully with {len(created_tables)} table(s)",
            "db_path": str(db_path),
            "tables": created_tables
        }

    except Exception as e:
        # Rollback and delete database file if creation fails
        conn.close()
        if db_path.exists():
            db_path.unlink()
        logger.error(f"Failed to create database: {e}")
        raise

    finally:
        conn.close()


def insert_data(
    database_name: str,
    table_name: str,
    data: dict[str, Any] | list[dict[str, Any]]
) -> dict[str, Any]:
    """
    Insert data into specified table.

    Args:
        database_name: Target database name
        table_name: Target table name
        data: Single dict or list of dicts to insert

    Returns:
        Dict with status and rows_inserted count

    Raises:
        FileNotFoundError: If database doesn't exist
        ValueError: If data format is invalid
    """
    db_path = _get_db_path(database_name)

    if not db_path.exists():
        raise FileNotFoundError(
            f"Database '{database_name}' not found. "
            f"Create it first using create_database."
        )

    # Normalize data to list
    if isinstance(data, dict):
        data = [data]
    elif not isinstance(data, list):
        raise ValueError("data must be a dict or list of dicts")

    if len(data) == 0:
        raise ValueError("data cannot be empty")

    conn = sqlite3.connect(db_path)
    try:
        # Get column names from first data entry
        columns = list(data[0].keys())
        placeholders = ', '.join(['?' for _ in columns])
        column_names = ', '.join(columns)

        insert_sql = f"INSERT INTO {table_name} ({column_names}) VALUES ({placeholders})"
        logger.debug(f"Insert SQL: {insert_sql}")

        # Insert all rows
        rows_inserted = 0
        for row in data:
            # Validate all rows have same columns
            if set(row.keys()) != set(columns):
                raise ValueError(
                    f"All data rows must have the same columns. "
                    f"Expected: {columns}, Got: {list(row.keys())}"
                )

            values = [row[col] for col in columns]
            conn.execute(insert_sql, values)
            rows_inserted += 1

        conn.commit()
        logger.info(f"Inserted {rows_inserted} rows into {table_name}")

        return {
            "status": "success",
            "rows_inserted": rows_inserted,
            "table_name": table_name,
            "database": database_name
        }

    except sqlite3.IntegrityError as e:
        conn.rollback()
        logger.error(f"Integrity error during insert: {e}")
        raise ValueError(f"Data integrity error: {e}")

    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to insert data: {e}")
        raise

    finally:
        conn.close()


def query_data(
    database_name: str,
    sql_query: str
) -> dict[str, Any]:
    """
    Query data using SQL SELECT statement.

    Args:
        database_name: Target database name
        sql_query: SELECT SQL query

    Returns:
        Dict with columns and rows

    Raises:
        FileNotFoundError: If database doesn't exist
        ValueError: If query is not a SELECT statement
    """
    db_path = _get_db_path(database_name)

    if not db_path.exists():
        raise FileNotFoundError(f"Database '{database_name}' not found")

    # Security: Only allow SELECT statements
    query_upper = sql_query.strip().upper()
    if not query_upper.startswith("SELECT"):
        raise ValueError(
            "Only SELECT queries are allowed. "
            "DROP, DELETE, UPDATE operations are prohibited for safety."
        )

    logger.info(f"Executing query on {database_name}: {sql_query}")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # Enable column name access

    try:
        cursor = conn.execute(sql_query)
        rows = cursor.fetchall()

        # Convert to list of dicts
        result = []
        columns = [description[0] for description in cursor.description] if cursor.description else []

        for row in rows:
            result.append(dict(zip(columns, row)))

        return {
            "status": "success",
            "columns": columns,
            "rows": result,
            "row_count": len(result)
        }

    except Exception as e:
        logger.error(f"Query failed: {e}")
        raise ValueError(f"Query execution failed: {e}")

    finally:
        conn.close()


def get_table_schema(
    database_name: str,
    table_name: str
) -> dict[str, Any]:
    """
    Get schema information for a table.

    Args:
        database_name: Target database name
        table_name: Target table name

    Returns:
        Dict with table schema details

    Raises:
        FileNotFoundError: If database doesn't exist
    """
    db_path = _get_db_path(database_name)

    if not db_path.exists():
        raise FileNotFoundError(f"Database '{database_name}' not found")

    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()

        if not columns:
            raise ValueError(f"Table '{table_name}' not found in database '{database_name}'")

        schema = []
        for col in columns:
            schema.append({
                "column_id": col[0],
                "name": col[1],
                "type": col[2],
                "not_null": bool(col[3]),
                "default_value": col[4],
                "is_primary_key": bool(col[5])
            })

        return {
            "status": "success",
            "database": database_name,
            "table_name": table_name,
            "columns": schema
        }

    finally:
        conn.close()


def list_all_databases() -> dict[str, Any]:
    """
    List all databases managed by this MCP server.

    Returns:
        Dict with list of database information
    """
    databases = []

    for db_file in DB_DIR.glob("*.db"):
        try:
            stat = db_file.stat()
            conn = sqlite3.connect(db_file)

            try:
                # Get metadata
                cursor = conn.execute("SELECT key, value FROM _metadata WHERE key IN ('description', 'tables')")
                metadata = dict(cursor.fetchall())

                # Get all tables (excluding metadata and sqlite internal)
                cursor = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' AND name != '_metadata'"
                )
                tables = [row[0] for row in cursor.fetchall()]

                # Get total record count
                total_records = 0
                for table in tables:
                    cursor = conn.execute(f"SELECT COUNT(*) FROM {table}")
                    total_records += cursor.fetchone()[0]

                databases.append({
                    "database_name": db_file.name,
                    "size_mb": round(stat.st_size / (1024 * 1024), 2),
                    "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                    "updated_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "description": metadata.get("description", ""),
                    "tables": tables,
                    "table_count": len(tables),
                    "total_records": total_records
                })

            finally:
                conn.close()

        except Exception as e:
            logger.error(f"Error reading database {db_file.name}: {e}")
            databases.append({
                "database_name": db_file.name,
                "error": str(e)
            })

    return {
        "status": "success",
        "database_count": len(databases),
        "databases": databases
    }


def delete_database(
    database_name: str,
    confirm: bool = False
) -> dict[str, Any]:
    """
    Delete a database file (requires confirmation).

    Args:
        database_name: Database to delete
        confirm: Must be True to execute deletion

    Returns:
        Dict with deletion status or confirmation request

    Raises:
        FileNotFoundError: If database doesn't exist
    """
    db_path = _get_db_path(database_name)

    if not db_path.exists():
        raise FileNotFoundError(f"Database '{database_name}' not found")

    # Get database info before potential deletion
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' AND name != '_metadata'"
        )
        tables = [row[0] for row in cursor.fetchall()]

        total_records = 0
        for table in tables:
            cursor = conn.execute(f"SELECT COUNT(*) FROM {table}")
            total_records += cursor.fetchone()[0]

        db_info = {
            "database_name": database_name,
            "tables": tables,
            "table_count": len(tables),
            "total_records": total_records,
            "size_mb": round(db_path.stat().st_size / (1024 * 1024), 2)
        }

    finally:
        conn.close()

    # If not confirmed, return confirmation request
    if not confirm:
        return {
            "status": "confirmation_required",
            "message": (
                f"データベース '{database_name}' を削除します。この操作は取り消せません。\n"
                f"削除するには confirm=true を指定してください。"
            ),
            "database_info": db_info
        }

    # Confirmed - proceed with deletion
    logger.warning(f"Deleting database: {database_name}")
    logger.info(f"Database info: {db_info}")

    try:
        db_path.unlink()
        logger.info(f"Database '{database_name}' deleted successfully")

        return {
            "status": "deleted",
            "message": f"データベース '{database_name}' を削除しました。",
            "deleted_file": str(db_path),
            "deleted_info": db_info
        }

    except Exception as e:
        logger.error(f"Failed to delete database: {e}")
        raise RuntimeError(f"Failed to delete database: {e}")


def get_database_info(database_name: str) -> dict[str, Any]:
    """
    Get detailed information about a specific database.

    Args:
        database_name: Target database name

    Returns:
        Dict with database details including description, tables, and metadata

    Raises:
        FileNotFoundError: If database doesn't exist
    """
    db_path = _get_db_path(database_name)

    if not db_path.exists():
        raise FileNotFoundError(f"Database '{database_name}' not found")

    conn = sqlite3.connect(db_path)
    try:
        # Get metadata
        cursor = conn.execute("SELECT key, value FROM _metadata")
        metadata = dict(cursor.fetchall())

        # Get tables (excluding metadata and sqlite internal)
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' AND name != '_metadata'"
        )
        tables = [row[0] for row in cursor.fetchall()]

        # Get total record count
        total_records = 0
        for table in tables:
            cursor = conn.execute(f"SELECT COUNT(*) FROM {table}")
            total_records += cursor.fetchone()[0]

        # Parse stored schema if available
        schema_json = metadata.get("schema")
        schema_info = None
        if schema_json:
            try:
                schema_info = json.loads(schema_json)
            except:
                pass

        return {
            "status": "success",
            "database_name": database_name,
            "database_description": metadata.get("database_description", metadata.get("description", "")),
            "tables": tables,
            "table_count": len(tables),
            "total_records": total_records,
            "size_mb": round(db_path.stat().st_size / (1024 * 1024), 2),
            "created_at": datetime.fromtimestamp(db_path.stat().st_ctime).isoformat(),
            "updated_at": datetime.fromtimestamp(db_path.stat().st_mtime).isoformat(),
            "schema": schema_info
        }

    finally:
        conn.close()


def get_table_info(database_name: str, table_name: str) -> dict[str, Any]:
    """
    Get detailed information about a specific table including column descriptions.

    Args:
        database_name: Target database name
        table_name: Target table name

    Returns:
        Dict with table details, column info with descriptions, and sample data

    Raises:
        FileNotFoundError: If database doesn't exist
        ValueError: If table doesn't exist
    """
    db_path = _get_db_path(database_name)

    if not db_path.exists():
        raise FileNotFoundError(f"Database '{database_name}' not found")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    try:
        # Check if table exists
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name = ?",
            (table_name,)
        )
        if not cursor.fetchone():
            raise ValueError(f"Table '{table_name}' not found in database '{database_name}'")

        # Get stored schema to retrieve descriptions
        cursor = conn.execute("SELECT value FROM _metadata WHERE key = 'schema'")
        schema_row = cursor.fetchone()

        table_description = ""
        column_descriptions = {}

        if schema_row:
            try:
                schema = json.loads(schema_row[0])
                # Find this table in the schema
                for table in schema.get("tables", []):
                    if table["table_name"] == table_name:
                        table_description = table.get("table_description", "")
                        # Build column descriptions map
                        for col in table.get("columns", []):
                            column_descriptions[col["name"]] = col.get("description", "")
                        break
            except:
                pass

        # Get table schema using PRAGMA
        cursor = conn.execute(f"PRAGMA table_info({table_name})")
        columns_info = []
        for col in cursor.fetchall():
            col_name = col[1]
            columns_info.append({
                "name": col_name,
                "type": col[2],
                "not_null": bool(col[3]),
                "default_value": col[4],
                "is_primary_key": bool(col[5]),
                "description": column_descriptions.get(col_name, "")
            })

        # Get record count
        cursor = conn.execute(f"SELECT COUNT(*) FROM {table_name}")
        record_count = cursor.fetchone()[0]

        # Get sample data (up to 3 rows)
        cursor = conn.execute(f"SELECT * FROM {table_name} LIMIT 3")
        sample_rows = cursor.fetchall()
        sample_data = [dict(row) for row in sample_rows]

        return {
            "status": "success",
            "database_name": database_name,
            "table_name": table_name,
            "table_description": table_description,
            "columns": columns_info,
            "record_count": record_count,
            "sample_data": sample_data
        }

    finally:
        conn.close()
