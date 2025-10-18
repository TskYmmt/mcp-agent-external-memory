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
    export_table_to_csv,
    get_database_info,
    get_table_info,
    execute_transaction,
    bulk_insert_optimized,
    prepare_statement,
    execute_prepared,
    close_prepared,
    execute_batch_queries,
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
    データベースの詳細情報を取得します（拡張版）。

    データベースの説明、含まれるテーブル、レコード数、作成日時に加えて、
    インデックス、外部キー、ビュー、トリガー、PRAGMA設定などの
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
            - indices: インデックス情報（テーブル名、カラム、ユニーク制約）
            - foreign_keys: 外部キー制約情報
            - views: ビュー一覧
            - triggers: トリガー一覧
            - pragma_info: PRAGMA設定（page_size, cache_size, journal_mode, synchronous）

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
    SQLクエリを実行してデータの検索・更新・削除・変更を行います。

    SELECT, UPDATE, DELETE, INSERT, ALTER TABLE など、すべてのSQL文を実行できます。
    トランザクション管理により、データの整合性が保証されます。

    Args:
        database_name: 対象データベース名
        sql_query: 実行するSQLクエリ

    Returns:
        - SELECT の場合: カラム名、行データ、行数を含む辞書
        - UPDATE/DELETE/INSERT/ALTER の場合: 影響を受けた行数を含む辞書

    Raises:
        FileNotFoundError: データベースが存在しない場合
        ValueError: クエリ構文エラー

    Examples:
        # SELECT
        query_data_tool(
            database_name="customers_2025",
            sql_query="SELECT name, email FROM customers WHERE name LIKE '山田%'"
        )

        # UPDATE
        query_data_tool(
            database_name="customers_2025",
            sql_query="UPDATE customers SET email = 'new@example.com' WHERE id = 1"
        )

        # DELETE
        query_data_tool(
            database_name="customers_2025",
            sql_query="DELETE FROM customers WHERE id = 999"
        )

        # ALTER TABLE (カラム追加)
        query_data_tool(
            database_name="customers_2025",
            sql_query="ALTER TABLE customers ADD COLUMN phone TEXT"
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
def export_table_to_csv_tool(
    database_name: str,
    table_name: str,
    csv_path: str,
    encoding: str = "utf-8"
) -> dict[str, Any]:
    """
    テーブルのデータをCSVファイルにエクスポートします。

    指定されたデータベースのテーブルから全データを取得し、CSVファイルとして出力します。
    ヘッダー行にはカラム名が含まれます。

    Args:
        database_name: データベース名（拡張子.db不要）
        table_name: エクスポートするテーブル名
        csv_path: 出力先CSVファイルの絶対パス
        encoding: CSVファイルのエンコーディング（デフォルト: utf-8）

    Returns:
        エクスポート結果を含む辞書:
        - status: "success"
        - database_name: データベース名
        - table_name: テーブル名
        - csv_path: 出力されたCSVファイルの絶対パス
        - row_count: エクスポートされた行数
        - column_count: カラム数
        - columns: カラム名のリスト

    Raises:
        FileNotFoundError: データベースが存在しない
        ValueError: テーブルが存在しない、またはファイルが既に存在する
        PermissionError: 指定されたパスに書き込み権限がない

    Example:
        export_table_to_csv_tool(
            database_name="sales_data",
            table_name="monthly_sales",
            csv_path="/path/to/export/sales_2025.csv"
        )

    Notes:
        - 既存ファイルは上書きされません（エラーになります）
        - 空のテーブルでもヘッダー行のみのCSVが作成されます
        - エンコーディングエラー時は 'shift_jis' や 'cp932' を試してください
    """
    try:
        result = export_table_to_csv(
            database_name=database_name,
            table_name=table_name,
            csv_path=csv_path,
            encoding=encoding
        )
        logger.info(
            f"CSV export successful: {result['row_count']} rows to {csv_path}"
        )
        return result
    except FileNotFoundError as e:
        logger.error(f"Database not found: {e}")
        raise
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise
    except PermissionError as e:
        logger.error(f"Permission error: {e}")
        raise
    except Exception as e:
        logger.error(f"Failed to export CSV: {e}")
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


@mcp.tool()
def execute_transaction_tool(
    database_name: str,
    operations: list[dict[str, Any]],
    isolation_level: str = "DEFERRED"
) -> dict[str, Any]:
    """
    複数の操作をアトミックに実行します（トランザクション管理）。

    複数のデータベース操作を単一のトランザクション内で実行し、
    すべての操作が成功した場合のみコミットします。
    1つでも失敗した場合は全ての変更がロールバックされます。

    Args:
        database_name: 対象データベース名
        operations: 実行する操作のリスト
            各操作は以下の形式:
            - type: "query" | "insert" | "update" | "delete"
            - sql: SQL文（type="query"、"update"、"delete"の場合）
            - params: SQLパラメータ（オプション）
            - table_name: テーブル名（type="insert"の場合）
            - data: 挿入データ（type="insert"の場合）
        isolation_level: トランザクション分離レベル
            "DEFERRED"（デフォルト）、"IMMEDIATE"、"EXCLUSIVE"のいずれか

    Returns:
        トランザクション結果を含む辞書:
        - status: "success" | "failed"
        - transaction_id: トランザクション識別子
        - operations_executed: 実行された操作数
        - results: 各操作の結果配列
        - rollback_performed: ロールバックが実行されたか
        - error_message: エラーメッセージ（失敗時）

    Raises:
        FileNotFoundError: データベースが存在しない場合
        ValueError: 操作が不正な場合

    Examples:
        # 複数テーブルへの挿入とクエリを1トランザクションで実行
        execute_transaction_tool(
            database_name="sales_data",
            operations=[
                {
                    "type": "insert",
                    "table_name": "orders",
                    "data": {"order_id": 1001, "customer_id": 5, "amount": 15000}
                },
                {
                    "type": "query",
                    "sql": "UPDATE customers SET last_order_date = ? WHERE customer_id = ?",
                    "params": ["2025-10-18", 5]
                },
                {
                    "type": "query",
                    "sql": "INSERT INTO order_history (order_id, status) VALUES (?, ?)",
                    "params": [1001, "created"]
                }
            ]
        )

        # クエリと更新を組み合わせた複雑な操作
        execute_transaction_tool(
            database_name="inventory",
            operations=[
                {
                    "type": "query",
                    "sql": "SELECT stock FROM products WHERE product_id = ?",
                    "params": [101]
                },
                {
                    "type": "update",
                    "sql": "UPDATE products SET stock = stock - ? WHERE product_id = ?",
                    "params": [5, 101]
                }
            ],
            isolation_level="IMMEDIATE"
        )

    Notes:
        - すべての操作は順番に実行されます
        - 1つでも失敗すると全てロールバックされます
        - データの整合性が自動的に保証されます
        - 複雑なビジネスロジックの実装に最適です
    """
    try:
        return execute_transaction(
            database_name=database_name,
            operations=operations,
            isolation_level=isolation_level
        )
    except Exception as e:
        logger.error(f"Error in execute_transaction_tool: {e}")
        raise


@mcp.tool()
def bulk_insert_optimized_tool(
    database_name: str,
    table_name: str,
    records: list[dict[str, Any]],
    batch_size: int = 1000,
    use_transaction: bool = True
) -> dict[str, Any]:
    """
    大量のレコードを効率的に挿入します（バッチ処理最適化）。

    バッチ処理とトランザクション管理により、大量データの挿入を
    高速かつメモリ効率良く実行します。

    Args:
        database_name: 対象データベース名
        table_name: 対象テーブル名
        records: 挿入するレコードのリスト（辞書の配列）
        batch_size: バッチサイズ（デフォルト: 1000）
            1トランザクションで挿入するレコード数
        use_transaction: トランザクション使用（デフォルト: true）
            各バッチをトランザクション内で実行するか

    Returns:
        挿入結果を含む辞書:
        - status: "success" | "partial_success" | "failed"
        - total_records: 総レコード数
        - inserted_records: 挿入成功レコード数
        - failed_records: 失敗レコード数
        - batches_processed: 処理バッチ数
        - execution_time_ms: 実行時間（ミリ秒）
        - errors: エラーメッセージリスト（最大10件）

    Raises:
        FileNotFoundError: データベースが存在しない場合
        ValueError: レコードが不正な場合

    Examples:
        # 10,000件のレコードを効率的に挿入
        bulk_insert_optimized_tool(
            database_name="sales_data",
            table_name="transactions",
            records=[
                {"transaction_id": 1, "amount": 1500, "customer_id": 101},
                {"transaction_id": 2, "amount": 2500, "customer_id": 102},
                # ... 9,998件
            ],
            batch_size=1000
        )

        # 小さいバッチサイズで挿入（メモリ制約がある場合）
        bulk_insert_optimized_tool(
            database_name="large_dataset",
            table_name="measurements",
            records=measurement_data,  # 100万件
            batch_size=500,
            use_transaction=True
        )

    Notes:
        - 通常の insert_data_tool より高速
        - 大量データでもメモリ効率が良い
        - 進捗ログが10バッチごとに出力される
        - エラーが発生しても処理を継続する
        - 全レコードが同じカラム構造である必要がある
    """
    try:
        result = bulk_insert_optimized(
            database_name=database_name,
            table_name=table_name,
            records=records,
            batch_size=batch_size,
            use_transaction=use_transaction
        )
        logger.info(
            f"Bulk insert completed: {result['inserted_records']}/{result['total_records']} "
            f"in {result['execution_time_ms']}ms"
        )
        return result
    except Exception as e:
        logger.error(f"Error in bulk_insert_optimized_tool: {e}")
        raise


@mcp.tool()
def prepare_statement_tool(
    database_name: str,
    statement_id: str,
    sql: str
) -> dict[str, Any]:
    """
    SQL文を事前準備し、繰り返し実行できるようにします（Prepared Statement）。

    同じクエリを異なるパラメータで繰り返し実行する場合、
    Prepared Statementを使うことで実行速度が大幅に向上します。

    Args:
        database_name: 対象データベース名
        statement_id: この準備文の識別子（一意である必要があります）
        sql: プレースホルダ（?）を含むSQL文

    Returns:
        準備文の情報を含む辞書:
        - status: "success"
        - statement_id: ステートメント識別子
        - parameter_count: プレースホルダ数
        - database_name: データベース名
        - sql: SQL文

    Raises:
        FileNotFoundError: データベースが存在しない場合
        ValueError: statement_idが既に存在する場合、またはSQLが不正な場合

    Example:
        # Prepared Statementを作成
        prepare_statement_tool(
            database_name="sales_data",
            statement_id="update_stock",
            sql="UPDATE products SET stock = stock - ? WHERE product_id = ? AND stock >= ?"
        )

    Notes:
        - プレースホルダには ? を使用します
        - 作成後は execute_prepared_tool で繰り返し実行できます
        - 使い終わったら close_prepared_tool でリソースを解放してください
        - 同じstatement_idは使用中は再利用できません
    """
    try:
        return prepare_statement(
            database_name=database_name,
            statement_id=statement_id,
            sql=sql
        )
    except Exception as e:
        logger.error(f"Error in prepare_statement_tool: {e}")
        raise


@mcp.tool()
def execute_prepared_tool(
    database_name: str,
    statement_id: str,
    params: list[Any]
) -> dict[str, Any]:
    """
    事前準備したSQL文をパラメータ付きで実行します。

    prepare_statement_tool で準備したSQL文を、
    異なるパラメータで高速に繰り返し実行できます。

    Args:
        database_name: 対象データベース名
        statement_id: 準備文の識別子
        params: SQLパラメータのリスト

    Returns:
        実行結果を含む辞書:
        - status: "success"
        - statement_id: ステートメント識別子
        - affected_rows: 影響を受けた行数（UPDATE/DELETE/INSERTの場合）
        - または columns, rows, row_count（SELECTの場合）

    Raises:
        ValueError: ステートメントが存在しない、またはパラメータ数が一致しない場合

    Example:
        # Prepared Statementを繰り返し実行
        for product_id, quantity in sales_list:
            execute_prepared_tool(
                database_name="sales_data",
                statement_id="update_stock",
                params=[quantity, product_id, quantity]
            )

    Notes:
        - パラメータ数は準備時のプレースホルダ数と一致する必要があります
        - UPDATEやDELETEは自動的にコミットされます
        - 高速実行のため、同じクエリを何度も実行する場合に最適です
    """
    try:
        return execute_prepared(
            database_name=database_name,
            statement_id=statement_id,
            params=params
        )
    except Exception as e:
        logger.error(f"Error in execute_prepared_tool: {e}")
        raise


@mcp.tool()
def close_prepared_tool(
    database_name: str,
    statement_id: str
) -> dict[str, Any]:
    """
    準備文をクローズし、リソースを解放します。

    使い終わったPrepared Statementをクローズすることで、
    データベース接続などのリソースを適切に解放します。

    Args:
        database_name: 対象データベース名
        statement_id: 準備文の識別子

    Returns:
        クローズ結果を含む辞書:
        - status: "success"
        - statement_id: ステートメント識別子
        - message: 成功メッセージ

    Raises:
        ValueError: ステートメントが存在しない場合

    Example:
        # Prepared Statementをクローズ
        close_prepared_tool(
            database_name="sales_data",
            statement_id="update_stock"
        )

    Notes:
        - 必ずクローズしてリソースリークを防いでください
        - クローズ後は同じstatement_idを再利用できます
        - 長時間使用しない場合は早めにクローズすることを推奨
    """
    try:
        return close_prepared(
            database_name=database_name,
            statement_id=statement_id
        )
    except Exception as e:
        logger.error(f"Error in close_prepared_tool: {e}")
        raise


@mcp.tool()
def execute_batch_queries_tool(
    database_name: str,
    queries: list[dict[str, Any]],
    fail_fast: bool = False
) -> dict[str, Any]:
    """
    複数のクエリを効率的に一括実行します。

    複数のSELECTクエリや異なる種類のクエリを
    1つのデータベース接続で効率的に実行します。

    Args:
        database_name: 対象データベース名
        queries: 実行するクエリのリスト
            各クエリは以下の形式:
            - query_id: クエリの識別子（一意）
            - sql: SQL文
            - params: SQLパラメータ（オプション）
        fail_fast: 最初の失敗で即座に中止（デフォルト: false）
            falseの場合、エラーが発生しても他のクエリを続行

    Returns:
        実行結果を含む辞書:
        - status: "success" | "partial_success" | "failed"
        - results: クエリID→結果の辞書
            各結果は status と data または error を含む
        - total_queries: 総クエリ数
        - successful_queries: 成功クエリ数
        - failed_queries: 失敗クエリ数
        - execution_time_ms: 実行時間（ミリ秒）

    Raises:
        FileNotFoundError: データベースが存在しない場合
        ValueError: クエリが不正な場合

    Examples:
        # 複数のSELECTクエリを一括実行
        execute_batch_queries_tool(
            database_name="analytics",
            queries=[
                {
                    "query_id": "daily_sales",
                    "sql": "SELECT SUM(amount) FROM orders WHERE date = ?",
                    "params": ["2025-10-18"]
                },
                {
                    "query_id": "top_products",
                    "sql": "SELECT product_id, COUNT(*) FROM orders GROUP BY product_id ORDER BY COUNT(*) DESC LIMIT 10"
                },
                {
                    "query_id": "customer_count",
                    "sql": "SELECT COUNT(DISTINCT customer_id) FROM orders"
                }
            ]
        )

        # 失敗時は即座に中止
        execute_batch_queries_tool(
            database_name="production",
            queries=[...],
            fail_fast=True
        )

    Notes:
        - 各クエリの結果はquery_idでアクセス可能
        - SELECTとUPDATE/DELETEを混在させることも可能
        - fail_fast=falseの場合、部分的な成功も返される
        - 1つのDB接続で実行されるため高速
    """
    try:
        result = execute_batch_queries(
            database_name=database_name,
            queries=queries,
            fail_fast=fail_fast
        )
        logger.info(
            f"Batch queries completed: {result['successful_queries']}/{result['total_queries']} "
            f"in {result['execution_time_ms']}ms"
        )
        return result
    except Exception as e:
        logger.error(f"Error in execute_batch_queries_tool: {e}")
        raise


if __name__ == "__main__":
    # Run the MCP server
    logger.info("Starting Database Management MCP Server")
    mcp.run()
