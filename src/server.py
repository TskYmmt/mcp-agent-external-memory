#!/usr/bin/env python3
"""
MCP Server for Database Management

This MCP server provides tools for AI agents to autonomously create and manage
SQLite databases.

Key features:
- Dynamic database and table creation
- Secure data insertion with transaction support
- SQL query capabilities for data analysis
- Metadata tracking for all databases
- Safe database deletion with confirmation
"""

import logging
from typing import Any

from mcp.server.fastmcp import FastMCP

# Import database operations
from db_operations import (
    create_database,
    insert_data,
    query_data,
    get_table_schema,
    list_all_databases,
    delete_database,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastMCP server
mcp = FastMCP("database-manager")


@mcp.tool()
def create_database_tool(
    database_name: str,
    table_schema: dict[str, Any],
    description: str
) -> dict[str, Any]:
    """
    新しいデータベースとテーブルを作成します。

    このツールはデータ内容に最適化されたデータベース構造を作成します。
    各データベースには自動的にメタデータテーブルが追加され、作成日時や目的が記録されます。

    Args:
        database_name: データベース名（拡張子.db不要）。調査テーマに基づいた分かりやすい名前を推奨
        table_schema: テーブル定義を含む辞書
            - table_name (str): テーブル名
            - columns (dict): カラム定義 {"カラム名": "型と制約"}
            例: {
                "table_name": "companies",
                "columns": {
                    "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
                    "company_name": "TEXT NOT NULL",
                    "market_cap": "REAL"
                }
            }
        description: このデータベースの目的・説明（後で参照可能）

    Returns:
        作成成功メッセージ、データベースパス、テーブル名を含む辞書

    Raises:
        ValueError: スキーマが不正な場合
        FileExistsError: 同名のデータベースが既に存在する場合

    Example:
        create_database(
            database_name="tech_companies_2025",
            table_schema={
                "table_name": "companies",
                "columns": {
                    "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
                    "name": "TEXT NOT NULL",
                    "industry": "TEXT",
                    "market_cap": "REAL",
                    "created_date": "TEXT"
                }
            },
            description="テクノロジー企業の市場調査データ"
        )
    """
    try:
        return create_database(database_name, table_schema, description)
    except Exception as e:
        logger.error(f"Error in create_database: {e}")
        raise


@mcp.tool()
def insert_data_tool(
    database_name: str,
    table_name: str,
    data: dict[str, Any] | list[dict[str, Any]]
) -> dict[str, Any]:
    """
    データをデータベースに挿入します。

    単一レコードまたは複数レコードを一度に挿入できます。
    トランザクション管理により、データの整合性が保証されます。

    Args:
        database_name: 対象データベース名
        table_name: 対象テーブル名
        data: 挿入するデータ（単一の辞書または辞書のリスト）
            例（単一）: {"company_name": "Apple", "market_cap": 3000000000000}
            例（複数）: [
                {"company_name": "Apple", "market_cap": 3000000000000},
                {"company_name": "Microsoft", "market_cap": 2800000000000}
            ]

    Returns:
        挿入された行数とステータスを含む辞書

    Raises:
        FileNotFoundError: データベースが存在しない場合
        ValueError: データ形式が不正な場合、または整合性エラー

    Example:
        insert_data(
            database_name="tech_companies_2025",
            table_name="companies",
            data=[
                {"name": "Apple", "industry": "Technology", "market_cap": 3.0e12},
                {"name": "Microsoft", "industry": "Technology", "market_cap": 2.8e12}
            ]
        )
    """
    try:
        return insert_data(database_name, table_name, data)
    except Exception as e:
        logger.error(f"Error in insert_data: {e}")
        raise


@mcp.tool()
def query_data_tool(
    database_name: str,
    sql_query: str
) -> dict[str, Any]:
    """
    蓄積されたデータをSQL検索・分析します。

    SELECT文を使用してデータを柔軟に抽出・分析できます。
    セキュリティのため、SELECT文のみが許可されています。

    Args:
        database_name: 対象データベース名
        sql_query: SELECT文によるクエリ
            例: "SELECT * FROM companies WHERE industry = 'Technology' ORDER BY market_cap DESC LIMIT 10"

    Returns:
        カラム名、行データ、行数を含む辞書

    Raises:
        FileNotFoundError: データベースが存在しない場合
        ValueError: SELECT以外のクエリを実行しようとした場合、またはクエリ構文エラー

    Example:
        query_data(
            database_name="tech_companies_2025",
            sql_query="SELECT name, market_cap FROM companies WHERE market_cap > 1000000000000 ORDER BY market_cap DESC"
        )
    """
    try:
        return query_data(database_name, sql_query)
    except Exception as e:
        logger.error(f"Error in query_data: {e}")
        raise


@mcp.tool()
def get_schema_tool(
    database_name: str,
    table_name: str
) -> dict[str, Any]:
    """
    テーブルのスキーマ情報を取得します。

    既存のテーブルにデータを追加する際に、カラム構成を確認するために使用します。

    Args:
        database_name: 対象データベース名
        table_name: 対象テーブル名

    Returns:
        カラム情報の詳細（名前、型、NULL許可、デフォルト値、主キーフラグ）を含む辞書

    Raises:
        FileNotFoundError: データベースが存在しない場合
        ValueError: テーブルが存在しない場合

    Example:
        get_schema(
            database_name="tech_companies_2025",
            table_name="companies"
        )
    """
    try:
        return get_table_schema(database_name, table_name)
    except Exception as e:
        logger.error(f"Error in get_schema: {e}")
        raise


@mcp.tool()
def list_databases_tool() -> dict[str, Any]:
    """
    MCPサーバーが管理するすべてのデータベースを一覧表示します。

    各データベースの詳細情報（サイズ、作成日時、テーブル数、レコード数など）を取得できます。

    Args:
        なし

    Returns:
        データベース情報の配列を含む辞書
        各データベースには以下の情報が含まれます:
        - database_name: データベースファイル名
        - size_mb: ファイルサイズ（MB）
        - created_at: 作成日時（ISO形式）
        - updated_at: 最終更新日時（ISO形式）
        - description: データベースの説明
        - tables: テーブル名のリスト
        - table_count: テーブル数
        - total_records: 全テーブルの合計レコード数

    Example:
        list_databases()
        # Returns:
        # {
        #     "status": "success",
        #     "database_count": 2,
        #     "databases": [
        #         {
        #             "database_name": "tech_companies_2025.db",
        #             "size_mb": 2.5,
        #             "created_at": "2025-01-15T10:30:00",
        #             "description": "テクノロジー企業の市場調査",
        #             "tables": ["companies", "market_data"],
        #             "table_count": 2,
        #             "total_records": 150
        #         },
        #         ...
        #     ]
        # }
    """
    try:
        return list_all_databases()
    except Exception as e:
        logger.error(f"Error in list_databases: {e}")
        raise


@mcp.tool()
def delete_database_tool(
    database_name: str,
    confirm: bool = False
) -> dict[str, Any]:
    """
    指定したデータベースファイルを削除します（危険な操作）。

    この操作は取り消せないため、必ず2段階確認が必要です。
    - confirm=false: 削除対象の情報を表示し、確認を要求
    - confirm=true: 実際に削除を実行

    Args:
        database_name: 削除対象のデータベース名
        confirm: 削除確認フラグ（trueの場合のみ実行）

    Returns:
        削除結果メッセージまたは確認要求メッセージを含む辞書

    Raises:
        FileNotFoundError: データベースが存在しない場合
        RuntimeError: 削除に失敗した場合

    Example:
        # Step 1: 確認
        delete_database_tool(database_name="old_data.db", confirm=False)
        # Returns confirmation request with database info

        # Step 2: 実行
        delete_database_tool(database_name="old_data.db", confirm=True)
        # Actually deletes the database
    """
    try:
        return delete_database(database_name, confirm)
    except Exception as e:
        logger.error(f"Error in delete_database_tool: {e}")
        raise


if __name__ == "__main__":
    # Run the MCP server
    logger.info("Starting Database Management MCP Server")
    mcp.run()
