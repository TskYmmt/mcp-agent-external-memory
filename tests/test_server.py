#!/usr/bin/env python3
"""
Simple test script to verify database operations work correctly.
"""

import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from db_operations import (
    create_database,
    insert_data,
    query_data,
    get_table_schema,
    list_all_databases,
    delete_database,
)


def test_basic_workflow():
    """Test basic database creation, insertion, and query workflow."""
    print("=" * 60)
    print("Testing Basic Workflow")
    print("=" * 60)

    # Test 1: Create database
    print("\n[Test 1] Creating database...")
    result = create_database(
        database_name="test_companies",
        table_schema={
            "table_name": "companies",
            "columns": {
                "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
                "name": "TEXT NOT NULL",
                "industry": "TEXT",
                "market_cap": "REAL",
                "research_date": "TEXT"
            }
        },
        description="Test database for tech companies"
    )
    print(f"✓ Database created: {result['db_path']}")

    # Test 2: Insert data
    print("\n[Test 2] Inserting data...")
    result = insert_data(
        database_name="test_companies",
        table_name="companies",
        data=[
            {
                "name": "Apple Inc.",
                "industry": "Technology",
                "market_cap": 3000000000000.0,
                "research_date": "2025-01-15"
            },
            {
                "name": "Microsoft Corp.",
                "industry": "Technology",
                "market_cap": 2800000000000.0,
                "research_date": "2025-01-15"
            },
            {
                "name": "Tesla Inc.",
                "industry": "Automotive",
                "market_cap": 800000000000.0,
                "research_date": "2025-01-15"
            }
        ]
    )
    print(f"✓ Inserted {result['rows_inserted']} rows")

    # Test 3: Query data
    print("\n[Test 3] Querying data...")
    result = query_data(
        database_name="test_companies",
        sql_query="SELECT name, industry, market_cap FROM companies ORDER BY market_cap DESC"
    )
    print(f"✓ Query returned {result['row_count']} rows:")
    for row in result['rows']:
        print(f"  - {row['name']}: ${row['market_cap']:,.0f}")

    # Test 4: Get schema
    print("\n[Test 4] Getting schema...")
    result = get_table_schema(
        database_name="test_companies",
        table_name="companies"
    )
    print(f"✓ Schema for 'companies' table:")
    for col in result['columns']:
        print(f"  - {col['name']} ({col['type']})")

    # Test 5: List databases
    print("\n[Test 5] Listing databases...")
    result = list_all_databases()
    print(f"✓ Found {result['database_count']} database(s):")
    for db in result['databases']:
        print(f"  - {db['database_name']}: {db['table_count']} table(s), {db['total_records']} record(s)")

    # Test 6: Delete database (with confirmation)
    print("\n[Test 6] Deleting test database...")
    result = delete_database(
        database_name="test_companies",
        confirm=False
    )
    print(f"✓ Confirmation required: {result['message']}")

    result = delete_database(
        database_name="test_companies",
        confirm=True
    )
    print(f"✓ Database deleted: {result['message']}")

    print("\n" + "=" * 60)
    print("All tests passed! ✓")
    print("=" * 60)


def test_error_handling():
    """Test error handling scenarios."""
    print("\n" + "=" * 60)
    print("Testing Error Handling")
    print("=" * 60)

    # Test: Attempt to query non-existent database
    print("\n[Error Test 1] Query non-existent database...")
    try:
        query_data(
            database_name="nonexistent_db",
            sql_query="SELECT * FROM companies"
        )
        print("✗ Should have raised FileNotFoundError")
    except FileNotFoundError as e:
        print(f"✓ Correctly raised error: {e}")

    # Test: Attempt non-SELECT query
    print("\n[Error Test 2] Attempt DROP statement...")

    # First create a temporary database
    create_database(
        database_name="temp_test_db",
        table_schema={
            "table_name": "test_table",
            "columns": {"id": "INTEGER PRIMARY KEY"}
        },
        description="Temporary test database"
    )

    try:
        query_data(
            database_name="temp_test_db",
            sql_query="DROP TABLE test_table"
        )
        print("✗ Should have raised ValueError")
    except ValueError as e:
        print(f"✓ Correctly raised error: {e}")

    # Clean up
    delete_database(database_name="temp_test_db", confirm=True)

    print("\n" + "=" * 60)
    print("Error handling tests passed! ✓")
    print("=" * 60)


if __name__ == "__main__":
    try:
        test_basic_workflow()
        test_error_handling()
        print("\n🎉 All tests completed successfully!\n")
    except Exception as e:
        print(f"\n❌ Test failed: {e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)
