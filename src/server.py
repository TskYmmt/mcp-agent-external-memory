#!/usr/bin/env python3
"""
MCP Server for Database Management

This MCP server provides tools for AI agents to autonomously create and manage
SQLite databases with rich metadata.

Key features:
- Dynamic database and table creation with required metadata
- Secure data insertion with transaction support
- SQL query capabilities for data analysis
- Metadata tracking for all databases, tables, and columns
- Safe database deletion with confirmation
- Self-documenting API with usage guides
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
    create_table_from_csv,
    get_database_info,
    get_table_info,
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
def get_usage_guide_tool() -> dict[str, Any]:
    """
    このデータベース管理サーバーの使い方ガイドを取得します。

    データベースの作成方法、スキーマ定義の形式、典型的なワークフローなど、
    このサーバーを効果的に使用するための包括的な情報を提供します。

    Returns:
        使い方ガイド（概要、スキーマ形式、ワークフロー例、ベストプラクティス）
    """
    return {
        "status": "success",
        "overview": {
            "purpose": "AIエージェントがデータを自律的に蓄積・管理するためのデータベースサーバー",
            "key_features": [
                "メタデータ必須のデータベース作成",
                "CSVファイルからの一括インポート（型自動推測）",
                "カラムごとの詳細な説明を保持",
                "データベース・テーブル情報の詳細取得",
                "セキュアなデータ挿入と検索",
                "2段階確認による安全な削除"
            ]
        },
        "schema_format": {
            "description": "データベース作成時は以下の形式でスキーマを指定します",
            "required_structure": {
                "database_description": "データベース全体の目的（5文字以上必須）",
                "tables": [
                    {
                        "table_name": "テーブル名（必須）",
                        "table_description": "テーブルの説明（5文字以上必須）",
                        "columns": [
                            {
                                "name": "カラム名（必須）",
                                "type": "データ型（必須、例: INTEGER, TEXT, REAL）",
                                "description": "カラムの説明（5文字以上必須）",
                                "constraints": "制約（オプション、例: PRIMARY KEY, NOT NULL）"
                            }
                        ]
                    }
                ]
            },
            "example": {
                "database_description": "2025年顧客データ分析プロジェクト",
                "tables": [
                    {
                        "table_name": "customers",
                        "table_description": "顧客の基本情報と連絡先",
                        "columns": [
                            {
                                "name": "id",
                                "type": "INTEGER",
                                "description": "顧客の一意識別子",
                                "constraints": "PRIMARY KEY AUTOINCREMENT"
                            },
                            {
                                "name": "name",
                                "type": "TEXT",
                                "description": "顧客の氏名（フルネーム）",
                                "constraints": "NOT NULL"
                            },
                            {
                                "name": "email",
                                "type": "TEXT",
                                "description": "連絡先メールアドレス",
                                "constraints": ""
                            },
                            {
                                "name": "created_at",
                                "type": "TEXT",
                                "description": "顧客登録日時（ISO8601形式）",
                                "constraints": ""
                            }
                        ]
                    }
                ]
            }
        },
        "typical_workflows": {
            "新しいDBを作成する場合": [
                "1. get_usage_guide_tool() でスキーマ形式を確認",
                "2. create_database_tool(database_name, schema) で作成",
                "3. insert_data_tool() でデータ挿入",
                "4. query_data_tool() でデータ確認"
            ],
            "CSVファイルからテーブルを作成する場合": [
                "1. CSVファイルのヘッダー行を確認",
                "2. 各カラムの説明文（5文字以上）を準備",
                "3. create_table_from_csv_tool() で一括インポート",
                "4. get_table_info_tool() でインポート結果を確認",
                "注意: 既存テーブルへのインポートは不可、必ず新規テーブルが作成されます"
            ],
            "既存DBにデータを追加する場合": [
                "1. list_databases_tool() でDB一覧確認",
                "2. get_database_info_tool(database_name) でDB詳細確認",
                "3. get_table_info_tool(database_name, table_name) でテーブル構造とサンプルデータ確認",
                "4. insert_data_tool() でデータ挿入"
            ],
            "データを検索・分析する場合": [
                "1. get_table_info_tool() でカラム構造確認",
                "2. query_data_tool() でSQL検索実行"
            ]
        },
        "best_practices": [
            "database_description には、このDBが何のために作られたか明確に記述する",
            "table_description には、このテーブルが何を格納するか具体的に記述する",
            "column description には、カラムの意味と単位（該当する場合）を記述する",
            "constraints は適切に設定する（PRIMARY KEY, NOT NULL, UNIQUE など）",
            "データ挿入前に get_table_info_tool() でスキーマを確認する"
        ],
        "validation_rules": {
            "database_description": "5文字以上の文字列（必須）",
            "table_description": "5文字以上の文字列（必須）",
            "column description": "5文字以上の文字列（必須）",
            "その他のフィールド": "非空の文字列（必須、constraintsを除く）"
        }
    }


@mcp.tool()
def create_database_tool(
    database_name: str,
    schema: dict[str, Any]
) -> dict[str, Any]:
    """
    新しいデータベースとテーブルを作成します。

    **重要**: メタデータが必須です。database_description、table_description、
    各カラムの description を必ず5文字以上で指定してください。

    Args:
        database_name: データベース名（拡張子.db不要）
        schema: データベーススキーマ（database_description, tables を含む）
            詳細な形式は get_usage_guide_tool() で確認してください。

    Returns:
        作成成功メッセージ、データベースパス、作成されたテーブル一覧

    Raises:
        ValueError: スキーマが不正、またはメタデータが不足している場合
        FileExistsError: 同名のデータベースが既に存在する場合

    Example:
        create_database_tool(
            database_name="customers_2025",
            schema={
                "database_description": "2025年顧客データ",
                "tables": [{
                    "table_name": "customers",
                    "table_description": "顧客の基本情報",
                    "columns": [
                        {
                            "name": "id",
                            "type": "INTEGER",
                            "description": "顧客ID（一意）",
                            "constraints": "PRIMARY KEY"
                        },
                        {
                            "name": "name",
                            "type": "TEXT",
                            "description": "顧客氏名",
                            "constraints": "NOT NULL"
                        }
                    ]
                }]
            }
        )
    """
    try:
        return create_database(database_name, schema)
    except Exception as e:
        logger.error(f"Error in create_database_tool: {e}")
        raise


@mcp.tool()
def get_database_info_tool(database_name: str) -> dict[str, Any]:
    """
    データベースの詳細情報を取得します。

    データベースの説明、含まれるテーブル、レコード数、作成日時などの
    包括的な情報を取得できます。

    Args:
        database_name: 対象データベース名

    Returns:
        データベースの詳細情報
            - database_name: DB名
            - database_description: DBの目的・説明
            - tables: テーブル名の一覧
            - table_count: テーブル数
            - total_records: 全レコード数
            - size_mb: ファイルサイズ
            - created_at: 作成日時
            - updated_at: 最終更新日時
            - schema: 完全なスキーマ情報（利用可能な場合）

    Raises:
        FileNotFoundError: データベースが存在しない場合

    Example:
        get_database_info_tool("customers_2025")
    """
    try:
        return get_database_info(database_name)
    except Exception as e:
        logger.error(f"Error in get_database_info_tool: {e}")
        raise


@mcp.tool()
def get_table_info_tool(database_name: str, table_name: str) -> dict[str, Any]:
    """
    テーブルの詳細情報を取得します。

    テーブルの説明、カラム構造（型、制約、説明）、レコード数、
    サンプルデータ（最大3件）を取得できます。

    Args:
        database_name: 対象データベース名
        table_name: 対象テーブル名

    Returns:
        テーブルの詳細情報
            - database_name: DB名
            - table_name: テーブル名
            - table_description: テーブルの説明
            - columns: カラム情報の配列
                - name: カラム名
                - type: データ型
                - description: カラムの説明
                - not_null: NULL許可フラグ
                - default_value: デフォルト値
                - is_primary_key: 主キーフラグ
            - record_count: レコード数
            - sample_data: サンプルデータ（最大3件）

    Raises:
        FileNotFoundError: データベースが存在しない場合
        ValueError: テーブルが存在しない場合

    Example:
        get_table_info_tool("customers_2025", "customers")
    """
    try:
        return get_table_info(database_name, table_name)
    except Exception as e:
        logger.error(f"Error in get_table_info_tool: {e}")
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

    Returns:
        挿入された行数とステータス

    Raises:
        FileNotFoundError: データベースが存在しない場合
        ValueError: データ形式が不正な場合、または整合性エラー

    Example:
        insert_data_tool(
            database_name="customers_2025",
            table_name="customers",
            data=[
                {"name": "山田太郎", "email": "yamada@example.com"},
                {"name": "佐藤花子", "email": "sato@example.com"}
            ]
        )
    """
    try:
        return insert_data(database_name, table_name, data)
    except Exception as e:
        logger.error(f"Error in insert_data_tool: {e}")
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

    Returns:
        カラム名、行データ、行数を含む辞書

    Raises:
        FileNotFoundError: データベースが存在しない場合
        ValueError: SELECT以外のクエリを実行しようとした場合、またはクエリ構文エラー

    Example:
        query_data_tool(
            database_name="customers_2025",
            sql_query="SELECT name, email FROM customers WHERE name LIKE '山田%'"
        )
    """
    try:
        return query_data(database_name, sql_query)
    except Exception as e:
        logger.error(f"Error in query_data_tool: {e}")
        raise


@mcp.tool()
def get_schema_tool(
    database_name: str,
    table_name: str
) -> dict[str, Any]:
    """
    テーブルのスキーマ情報を取得します。

    **非推奨**: このツールは後方互換性のために残されています。
    より詳細な情報が必要な場合は get_table_info_tool() を使用してください。

    Args:
        database_name: 対象データベース名
        table_name: 対象テーブル名

    Returns:
        カラム情報の詳細（名前、型、NULL許可、デフォルト値、主キーフラグ）

    Raises:
        FileNotFoundError: データベースが存在しない場合
        ValueError: テーブルが存在しない場合
    """
    try:
        return get_table_schema(database_name, table_name)
    except Exception as e:
        logger.error(f"Error in get_schema_tool: {e}")
        raise


@mcp.tool()
def list_databases_tool() -> dict[str, Any]:
    """
    MCPサーバーが管理するすべてのデータベースを一覧表示します。

    各データベースの概要情報（サイズ、作成日時、テーブル数、レコード数など）を取得できます。
    詳細情報が必要な場合は get_database_info_tool() を使用してください。

    Returns:
        データベース情報の配列

    Example:
        list_databases_tool()
    """
    try:
        return list_all_databases()
    except Exception as e:
        logger.error(f"Error in list_databases_tool: {e}")
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
        削除結果メッセージまたは確認要求メッセージ

    Raises:
        FileNotFoundError: データベースが存在しない場合
        RuntimeError: 削除に失敗した場合

    Example:
        # Step 1: 確認
        delete_database_tool(database_name="old_data.db", confirm=False)

        # Step 2: 実行
        delete_database_tool(database_name="old_data.db", confirm=True)
    """
    try:
        return delete_database(database_name, confirm)
    except Exception as e:
        logger.error(f"Error in delete_database_tool: {e}")
        raise


@mcp.tool()
def create_table_from_csv_tool(
    database_name: str,
    table_name: str,
    csv_path: str,
    table_description: str,
    column_descriptions: dict[str, str],
    encoding: str = "utf-8",
    primary_key_column: str | None = None
) -> dict[str, Any]:
    """
    CSVファイルから新しいテーブルを作成し、データを一括インポートします。

    このツールは、CSVファイルの各カラムのデータ型を自動判定し、テーブルを作成して
    全データを一括挿入します。メタデータ必須ポリシーに従い、テーブルと各カラムの
    説明文（5文字以上）が必要です。

    **重要**: 既存テーブルへのインポートはできません。必ず新しいテーブルを作成します。

    Args:
        database_name: データベース名（拡張子.db不要）
        table_name: 作成するテーブル名
        csv_path: CSVファイルの絶対パス
        table_description: テーブルの説明（5文字以上、必須）
        column_descriptions: カラム名→説明文の辞書（各5文字以上、全カラム必須）
        encoding: CSVファイルのエンコーディング（デフォルト: utf-8）
        primary_key_column: PRIMARY KEYとして使用するカラム名（オプション）

    Returns:
        インポート結果を含む辞書:
        - status: "success"
        - database_name: データベース名
        - table_name: テーブル名
        - total_rows: CSV総行数
        - inserted_rows: 挿入成功行数
        - error_rows: エラー行数
        - errors: エラーメッセージリスト（最大10件）
        - inferred_types: 推測されたカラム型の辞書

    Raises:
        FileNotFoundError: CSVファイルが存在しない
        ValueError: メタデータ不足、CSV形式エラー、テーブル重複
        sqlite3.Error: データベース操作失敗

    Example:
        create_table_from_csv_tool(
            database_name="sales_data",
            table_name="monthly_sales",
            csv_path="/path/to/sales.csv",
            table_description="月次売上データを格納するテーブル",
            column_descriptions={
                "month": "売上月（YYYY-MM形式）",
                "revenue": "売上金額（円）",
                "customer_count": "顧客数"
            },
            primary_key_column="month"
        )

    Notes:
        - データ型は自動推測されます（INTEGER, REAL, TEXT）
        - 空文字列はNULLとして挿入されます
        - エンコーディングエラー時は 'shift_jis' や 'cp932' を試してください
        - 既存テーブルへのインポートが必要な場合は insert_data_tool を使用してください
    """
    try:
        result = create_table_from_csv(
            database_name=database_name,
            table_name=table_name,
            csv_path=csv_path,
            table_description=table_description,
            column_descriptions=column_descriptions,
            encoding=encoding,
            primary_key_column=primary_key_column
        )
        logger.info(
            f"CSV import successful: {result['inserted_rows']}/{result['total_rows']} rows"
        )
        return result
    except FileNotFoundError as e:
        logger.error(f"CSV file not found: {e}")
        raise
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise
    except Exception as e:
        logger.error(f"Failed to import CSV: {e}")
        raise


if __name__ == "__main__":
    # Run the MCP server
    logger.info("Starting Database Management MCP Server")
    mcp.run()
