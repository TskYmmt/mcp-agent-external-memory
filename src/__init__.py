"""
Database Manager - SQLite database management library with metadata tracking.

This package provides functions for creating, querying, and managing SQLite databases
with rich metadata tracking. It can be used both as an MCP server and as a library
for other Python applications.

Example usage as a library:
    from database_manager import insert_data, query_data, create_database
    
    # Create a database
    create_database("my_db", schema={...})
    
    # Insert data
    insert_data("my_db", "my_table", {"name": "test"})
    
    # Query data
    result = query_data("my_db", "SELECT * FROM my_table")
"""

__version__ = "0.1.0"

# Export public API functions
from .db_operations import (
    create_database,
    insert_data,
    query_data,
    get_table_schema,
    get_table_info,
    get_database_info,
    list_all_databases,
    delete_database,
    create_table_from_csv,
    export_table_to_csv,
    export_table_to_file,
    export_database,
    execute_transaction,
    bulk_insert_optimized,
    prepare_statement,
    execute_prepared,
    close_prepared,
    execute_batch_queries,
    store_markdown_to_record,
)

__all__ = [
    "create_database",
    "insert_data",
    "query_data",
    "get_table_schema",
    "get_table_info",
    "get_database_info",
    "list_all_databases",
    "delete_database",
    "create_table_from_csv",
    "export_table_to_csv",
    "export_table_to_file",
    "export_database",
    "execute_transaction",
    "bulk_insert_optimized",
    "prepare_statement",
    "execute_prepared",
    "close_prepared",
    "execute_batch_queries",
    "store_markdown_to_record",
]
