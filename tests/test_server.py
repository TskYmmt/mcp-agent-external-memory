#!/usr/bin/env python3
"""
Comprehensive smoke tests for database-manager MCP features.

This script exercises the generic capabilities requested in
`design/DATABASE_MCP_GENERIC_FEATURES.md` so that engineers can
manually verify behaviour without launching the MCP server.
"""

import sys
from pathlib import Path
from pprint import pprint

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from db_operations import (
    create_database,
    insert_data,
    query_data,
    get_table_schema,
    get_table_info,
    get_database_info,
    list_all_databases,
    delete_database,
    execute_transaction,
    bulk_insert_optimized,
    prepare_statement,
    execute_prepared,
    close_prepared,
    execute_batch_queries,
)


print("=" * 60)
print("Database Manager MCP Smoke Tests")
print("=" * 60)


def _cleanup_database(database_name: str) -> None:
    """Delete the specified database if it already exists."""
    try:
        delete_database(database_name=database_name, confirm=True)
        print(f"  - Removed pre-existing database '{database_name}'")
    except FileNotFoundError:
        pass


def _print_title(title: str) -> None:
    print("\n" + "-" * 60)
    print(title)
    print("-" * 60)


def run_basic_workflow() -> None:
    """End-to-end happy path covering the new generic features."""
    db_name = "test_companies"
    _cleanup_database(db_name)

    _print_title("[1] Creating database with metadata")
    schema = {
        "database_description": "技術企業の指標を管理するテスト用データベース",
        "tables": [
            {
                "table_name": "companies",
                "table_description": "主要企業の基本情報と市場データを格納",
                "columns": [
                    {
                        "name": "id",
                        "type": "INTEGER",
                        "description": "企業を一意に識別するID",
                        "constraints": "PRIMARY KEY AUTOINCREMENT",
                    },
                    {
                        "name": "name",
                        "type": "TEXT",
                        "description": "企業名（正式名称）",
                        "constraints": "NOT NULL",
                    },
                    {
                        "name": "industry",
                        "type": "TEXT",
                        "description": "業種カテゴリ",
                        "constraints": "",
                    },
                    {
                        "name": "market_cap",
                        "type": "REAL",
                        "description": "時価総額（USD）",
                        "constraints": "",
                    },
                    {
                        "name": "research_date",
                        "type": "TEXT",
                        "description": "調査日（ISO8601）",
                        "constraints": "",
                    },
                ],
            }
        ],
    }
    creation_result = create_database(database_name=db_name, schema=schema)
    print(f"  - Created database at {creation_result['db_path']}")

    _print_title("[2] Inserting seed records")
    seed_result = insert_data(
        database_name=db_name,
        table_name="companies",
        data=[
            {
                "name": "Apple Inc.",
                "industry": "Technology",
                "market_cap": 3000000000000.0,
                "research_date": "2025-10-18",
            },
            {
                "name": "Microsoft Corp.",
                "industry": "Technology",
                "market_cap": 2800000000000.0,
                "research_date": "2025-10-18",
            },
            {
                "name": "Toyota Motor",
                "industry": "Automotive",
                "market_cap": 250000000000.0,
                "research_date": "2025-10-18",
            },
        ],
    )
    print(f"  - Inserted {seed_result['rows_inserted']} initial rows")

    _print_title("[3] Running query_data for ordering")
    query_result = query_data(
        database_name=db_name,
        sql_query="SELECT name, industry, market_cap FROM companies ORDER BY market_cap DESC",
    )
    for row in query_result["rows"]:
        print(f"  - {row['name']}: ${row['market_cap']:,.0f}")

    _print_title("[4] Inspecting schema and metadata")
    table_schema = get_table_schema(database_name=db_name, table_name="companies")
    for col in table_schema["columns"]:
        print(f"  - {col['name']} ({col['type']})")

    table_info = get_table_info(database_name=db_name, table_name="companies")
    print("  - Table description:", table_info["table_description"])
    print("  - Column descriptions:")
    for col in table_info["columns"]:
        description = col["description"] or "(no description)"
        print(f"      * {col['name']}: {description}")
    print("  - Sample data:")
    pprint(table_info["sample_data"])

    db_info = get_database_info(database_name=db_name)
    print("  - Database description:", db_info["database_description"])
    print("  - Indices:")
    pprint(db_info["indices"])
    print("  - PRAGMA info:")
    pprint(db_info["pragma_info"])

    _print_title("[5] Listing all databases")
    db_list = list_all_databases()
    print(f"  - Total databases managed: {db_list['database_count']}")
    for db in db_list["databases"]:
        if "error" in db:
            print(f"    ! {db['database_name']}: {db['error']}")
        else:
            print(
                f"    * {db['database_name']}: {db['table_count']} tables, {db['total_records']} records"
            )

    _print_title("[6] Executing transaction with mixed operations")
    txn_result = execute_transaction(
        database_name=db_name,
        operations=[
            {
                "type": "insert",
                "table_name": "companies",
                "data": {
                    "name": "NVIDIA Corp.",
                    "industry": "Technology",
                    "market_cap": 2500000000000.0,
                    "research_date": "2025-10-18",
                },
            },
            {
                "type": "query",
                "sql": "UPDATE companies SET market_cap = market_cap * 1.05 WHERE name = ?",
                "params": ["NVIDIA Corp."],
            },
            {
                "type": "query",
                "sql": "SELECT name, market_cap FROM companies WHERE name = ?",
                "params": ["NVIDIA Corp."],
            },
        ],
    )
    print(f"  - Transaction status: {txn_result['status']}")
    for step in txn_result["results"]:
        print(f"      step {step['operation_index']}: {step['status']}")

    _print_title("[7] Bulk insert optimized")
    bulk_payload = [
        {
            "name": f"Sample Corp {i:02d}",
            "industry": "Sample",
            "market_cap": float(1_000_000 + i * 10_000),
            "research_date": "2025-10-18",
        }
        for i in range(25)
    ]
    bulk_result = bulk_insert_optimized(
        database_name=db_name,
        table_name="companies",
        records=bulk_payload,
        batch_size=8,
    )
    print(
        f"  - Bulk status: {bulk_result['status']} ({bulk_result['inserted_records']}/"
        f"{bulk_result['total_records']} inserted)"
    )
    if bulk_result["errors"]:
        print("    Errors:")
        pprint(bulk_result["errors"])

    _print_title("[8] Prepared statement workflow")
    prepare_statement(
        database_name=db_name,
        statement_id="select_by_industry",
        sql="SELECT name, market_cap FROM companies WHERE industry = ? ORDER BY market_cap DESC LIMIT 3",
    )
    prepared_result = execute_prepared(
        database_name=db_name,
        statement_id="select_by_industry",
        params=["Technology"],
    )
    print(f"  - Prepared statement returned {prepared_result['row_count']} rows")
    for row in prepared_result.get("rows", []):
        print(f"      * {row['name']} (${row['market_cap']:,.0f})")
    close_prepared(database_name=db_name, statement_id="select_by_industry")

    _print_title("[9] Batch query execution")
    batch_result = execute_batch_queries(
        database_name=db_name,
        queries=[
            {
                "query_id": "count_all",
                "sql": "SELECT COUNT(*) AS cnt FROM companies",
            },
            {
                "query_id": "top_company",
                "sql": "SELECT name, market_cap FROM companies ORDER BY market_cap DESC LIMIT 1",
            },
        ],
    )
    print(f"  - Batch status: {batch_result['status']}")
    for key, value in batch_result["results"].items():
        print(f"      {key}: {value['status']}")
    pprint(batch_result["results"]["count_all"].get("data"))

    _print_title("[10] Cleaning up database")
    confirmation = delete_database(database_name=db_name, confirm=False)
    print("  - Confirmation message:", confirmation["message"])
    deletion = delete_database(database_name=db_name, confirm=True)
    print("  - Deleted:", deletion["deleted_file"])


def run_error_scenarios() -> None:
    """Exercise failure modes for rollback and validation."""
    _print_title("[E1] Querying non-existent database raises error")
    try:
        query_data(database_name="nonexistent_db", sql_query="SELECT 1")
        print("  ✗ Expected FileNotFoundError but query succeeded")
    except FileNotFoundError as exc:
        print(f"  ✓ Correctly raised FileNotFoundError: {exc}")

    _print_title("[E2] Transaction rollback on integrity error")
    db_name = "temp_txn_db"
    _cleanup_database(db_name)
    create_database(
        database_name=db_name,
        schema={
            "database_description": "トランザクションロールバック検証用",
            "tables": [
                {
                    "table_name": "items",
                    "table_description": "テスト用アイテム一覧",
                    "columns": [
                        {
                            "name": "id",
                            "type": "INTEGER",
                            "description": "アイテム識別子ID",
                            "constraints": "PRIMARY KEY",
                        },
                        {
                            "name": "name",
                            "type": "TEXT",
                            "description": "アイテムの名称文字列",
                            "constraints": "NOT NULL",
                        },
                    ],
                }
            ],
        },
    )

    txn_failure = execute_transaction(
        database_name=db_name,
        operations=[
            {
                "type": "insert",
                "table_name": "items",
                "data": {"id": 1, "name": "first"},
            },
            {
                "type": "insert",
                "table_name": "items",
                "data": {"id": 1, "name": "duplicate"},
            },
        ],
    )
    print(f"  - Transaction status: {txn_failure['status']}")
    print(f"    Rollback performed: {txn_failure['rollback_performed']}")

    count_check = query_data(
        database_name=db_name,
        sql_query="SELECT COUNT(*) AS cnt FROM items",
    )
    count = count_check["rows"][0]["cnt"] if count_check["rows"] else 0
    print(f"  - Rows remaining after rollback: {count}")

    delete_database(database_name=db_name, confirm=True)


if __name__ == "__main__":
    try:
        run_basic_workflow()
        run_error_scenarios()
        print("\n🎉 All smoke tests completed successfully!\n")
    except Exception as exc:  # pragma: no cover - printable diagnostics
        print(f"\n❌ Smoke tests failed: {exc}\n")
        import traceback

        traceback.print_exc()
        sys.exit(1)
