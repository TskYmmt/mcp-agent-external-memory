"""
Database operations module for managing SQLite databases with metadata tracking.
Provides core functions for creating, querying, and managing databases.
"""

import sqlite3
import json
import logging
import csv
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

    logger.info(f"Executing query on {database_name}: {sql_query}")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # Enable column name access

    try:
        cursor = conn.execute(sql_query)

        # Check if this is a modifying query (UPDATE, DELETE, INSERT, ALTER)
        query_upper = sql_query.strip().upper()
        is_modifying = any(query_upper.startswith(cmd) for cmd in ['UPDATE', 'DELETE', 'INSERT', 'ALTER', 'DROP', 'CREATE'])

        if is_modifying:
            conn.commit()
            affected_rows = cursor.rowcount
            logger.info(f"Modified {affected_rows} rows")

            return {
                "status": "success",
                "affected_rows": affected_rows,
                "message": f"Successfully executed. {affected_rows} rows affected."
            }
        else:
            # SELECT query - return data
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
        conn.rollback()
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


def _infer_column_type(values: list[str]) -> str:
    """
    Infer SQLite data type from a list of string values.

    Args:
        values: List of string values from CSV column

    Returns:
        SQLite type: "INTEGER", "REAL", or "TEXT"
    """
    # Filter out empty values
    non_empty = [v.strip() for v in values if v.strip()]

    if not non_empty:
        return "TEXT"

    # Try INTEGER
    try:
        for v in non_empty:
            int(v)
        return "INTEGER"
    except ValueError:
        pass

    # Try REAL
    try:
        for v in non_empty:
            float(v)
        return "REAL"
    except ValueError:
        pass

    return "TEXT"


def create_table_from_csv(
    database_name: str,
    table_name: str,
    csv_path: str,
    table_description: str,
    column_descriptions: dict[str, str],
    encoding: str = "utf-8",
    primary_key_column: str | None = None
) -> dict[str, Any]:
    """
    Create a new table from CSV file with automatic type inference.

    Args:
        database_name: Target database name (without .db extension)
        table_name: Name of table to create
        csv_path: Absolute path to CSV file
        table_description: Description of the table (5+ characters)
        column_descriptions: Dictionary mapping column names to descriptions (5+ chars each)
        encoding: CSV file encoding (default: utf-8)
        primary_key_column: Optional column name to use as PRIMARY KEY

    Returns:
        Dictionary with status, created table info, and import statistics

    Raises:
        FileNotFoundError: CSV file not found
        ValueError: Invalid metadata, CSV format, or column descriptions
        sqlite3.Error: Database operation failed
    """
    # Validate table description
    if not table_description or len(table_description) < 5:
        raise ValueError(
            "table_description must be at least 5 characters. "
            f"Got: '{table_description}' ({len(table_description)} chars)"
        )

    # Check CSV file exists
    csv_file = Path(csv_path)
    if not csv_file.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    # Read CSV and infer schema
    try:
        with open(csv_file, encoding=encoding, newline='') as f:
            reader = csv.DictReader(f)
            rows = list(reader)

            if not rows:
                raise ValueError(f"CSV file is empty: {csv_path}")

            csv_columns = list(rows[0].keys())

            # Validate column descriptions
            missing_descriptions = set(csv_columns) - set(column_descriptions.keys())
            if missing_descriptions:
                raise ValueError(
                    f"Missing descriptions for columns: {missing_descriptions}. "
                    f"All columns must have descriptions (5+ characters)."
                )

            for col_name, desc in column_descriptions.items():
                if col_name not in csv_columns:
                    raise ValueError(
                        f"Column '{col_name}' in column_descriptions not found in CSV. "
                        f"CSV columns: {csv_columns}"
                    )
                if not desc or len(desc) < 5:
                    raise ValueError(
                        f"Description for column '{col_name}' must be at least 5 characters. "
                        f"Got: '{desc}' ({len(desc)} chars)"
                    )

            # Validate primary key column if specified
            if primary_key_column and primary_key_column not in csv_columns:
                raise ValueError(
                    f"primary_key_column '{primary_key_column}' not found in CSV. "
                    f"Available columns: {csv_columns}"
                )

            # Infer types for each column
            column_types = {}
            for col_name in csv_columns:
                values = [row[col_name] for row in rows]
                column_types[col_name] = _infer_column_type(values)

            logger.info(f"Inferred column types: {column_types}")

    except UnicodeDecodeError as e:
        raise ValueError(
            f"Failed to decode CSV with encoding '{encoding}'. "
            f"Try a different encoding (e.g., 'shift_jis', 'cp932'). Error: {e}"
        )
    except csv.Error as e:
        raise ValueError(f"Invalid CSV format: {e}")

    # Build schema
    columns = []
    for col_name in csv_columns:
        col_type = column_types[col_name]
        constraints = ""

        if primary_key_column and col_name == primary_key_column:
            constraints = "PRIMARY KEY"

        columns.append({
            "name": col_name,
            "type": col_type,
            "description": column_descriptions[col_name],
            "constraints": constraints
        })

    schema = {
        "database_description": f"Database imported from CSV: {csv_file.name}",
        "tables": [{
            "table_name": table_name,
            "table_description": table_description,
            "columns": columns
        }]
    }

    # Check if database exists
    db_path = _get_db_path(database_name)
    db_exists = db_path.exists()

    if db_exists:
        # Database exists, just add the table
        conn = sqlite3.connect(db_path)
        try:
            _ensure_metadata_table(conn)

            # Check if table already exists
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (table_name,)
            )
            if cursor.fetchone():
                raise ValueError(
                    f"Table '{table_name}' already exists in database '{database_name}'. "
                    f"Please use a different table name or database."
                )

            # Create table
            column_defs = []
            for col in columns:
                col_def = f"{col['name']} {col['type']}"
                if col.get('constraints'):
                    col_def += f" {col['constraints']}"
                column_defs.append(col_def)

            create_sql = f"CREATE TABLE {table_name} ({', '.join(column_defs)})"
            conn.execute(create_sql)

            # Update metadata with new table
            metadata_json = conn.execute(
                "SELECT value FROM _metadata WHERE key = 'schema'"
            ).fetchone()

            if metadata_json:
                existing_schema = json.loads(metadata_json[0])
                existing_schema["tables"].append(schema["tables"][0])
                _update_metadata(conn, "schema", json.dumps(existing_schema, ensure_ascii=False))

            conn.commit()

        except Exception as e:
            conn.rollback()
            raise
        finally:
            conn.close()
    else:
        # Create new database
        create_database(database_name, schema)

    # Insert data
    conn = sqlite3.connect(db_path)
    try:
        placeholders = ", ".join(["?" for _ in csv_columns])
        insert_sql = f"INSERT INTO {table_name} ({', '.join(csv_columns)}) VALUES ({placeholders})"

        inserted_count = 0
        error_count = 0
        errors = []

        for i, row in enumerate(rows, start=1):
            try:
                values = [row[col] if row[col].strip() else None for col in csv_columns]
                conn.execute(insert_sql, values)
                inserted_count += 1
            except sqlite3.Error as e:
                error_count += 1
                errors.append(f"Row {i}: {e}")
                if len(errors) <= 10:  # Limit error messages
                    logger.warning(f"Failed to insert row {i}: {e}")

        conn.commit()

        logger.info(
            f"CSV import completed: {inserted_count} inserted, {error_count} errors"
        )

        return {
            "status": "success",
            "database_name": database_name,
            "table_name": table_name,
            "total_rows": len(rows),
            "inserted_rows": inserted_count,
            "error_rows": error_count,
            "errors": errors[:10],  # Return first 10 errors
            "inferred_types": column_types
        }

    except Exception as e:
        conn.rollback()
        raise
    finally:
        conn.close()


def export_table_to_csv(
    database_name: str,
    table_name: str,
    csv_path: str,
    encoding: str = "utf-8"
) -> dict[str, Any]:
    """
    Export table data to CSV file.

    Args:
        database_name: Database name (without .db extension)
        table_name: Table name to export
        csv_path: Absolute path for output CSV file
        encoding: CSV file encoding (default: utf-8)

    Returns:
        Dictionary with export status and statistics

    Raises:
        FileNotFoundError: Database not found
        ValueError: Table not found or invalid path
        PermissionError: Cannot write to specified path
    """
    db_path = _get_db_path(database_name)
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {database_name}")

    # Validate output path
    output_path = Path(csv_path)
    if output_path.exists():
        raise ValueError(f"CSV file already exists: {csv_path}")

    # Check parent directory exists and is writable
    if not output_path.parent.exists():
        raise ValueError(f"Parent directory does not exist: {output_path.parent}")

    if not output_path.parent.is_dir():
        raise ValueError(f"Parent path is not a directory: {output_path.parent}")

    conn = sqlite3.connect(db_path)
    try:
        # Check table exists
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table_name,)
        )
        if not cursor.fetchone():
            raise ValueError(
                f"Table '{table_name}' not found in database '{database_name}'"
            )

        # Get all data from table
        cursor = conn.execute(f"SELECT * FROM {table_name}")
        rows = cursor.fetchall()

        if not rows:
            logger.warning(f"Table '{table_name}' is empty")

        # Get column names
        column_names = [description[0] for description in cursor.description]

        # Write to CSV
        with open(output_path, 'w', encoding=encoding, newline='') as f:
            writer = csv.writer(f)
            writer.writerow(column_names)  # Header
            writer.writerows(rows)  # Data

        logger.info(
            f"Exported {len(rows)} rows from {database_name}.{table_name} to {csv_path}"
        )

        return {
            "status": "success",
            "database_name": database_name,
            "table_name": table_name,
            "csv_path": str(output_path.absolute()),
            "row_count": len(rows),
            "column_count": len(column_names),
            "columns": column_names
        }

    except PermissionError as e:
        raise PermissionError(f"Cannot write to {csv_path}: {e}")
    finally:
        conn.close()
