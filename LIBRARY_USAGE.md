# database-manager ライブラリ使用ガイド

他のMCPサーバーやPythonアプリケーションから `database-manager` をライブラリとして使用する際の実装ガイドです。

## 目次

1. [インストール](#インストール)
2. [基本的な使い方](#基本的な使い方)
3. [環境変数の設定](#環境変数の設定)
4. [実装例](#実装例)
5. [公開API一覧](#公開api一覧)
6. [よくある質問](#よくある質問)

---

## インストール

### 方法1: 開発モードでインストール（推奨）

```bash
# database-managerのリポジトリをクローンまたは配置
cd /path/to/mcp-agent-external-memory

# 開発モードでインストール（コード変更が即座に反映される）
pip install -e .

# または uv を使用する場合
uv pip install -e .
```

### 方法2: 通常インストール

```bash
cd /path/to/mcp-agent-external-memory
pip install .
```

### 方法3: パスを追加（一時的な使用）

```python
import sys
from pathlib import Path

# database-managerのsrcディレクトリをパスに追加
sys.path.insert(0, str(Path("/path/to/mcp-agent-external-memory/src")))

from db_operations import insert_data
```

---

## 基本的な使い方

### インポート

```python
from database_manager import (
    create_database,
    insert_data,
    query_data,
    get_database_info,
    execute_transaction,
    bulk_insert_optimized,
    store_markdown_to_record,
)
```

### データベース作成

```python
from database_manager import create_database

result = create_database(
    database_name="my_app",
    schema={
        "database_description": "アプリケーション用データベース",
        "tables": [
            {
                "table_name": "users",
                "table_description": "ユーザー情報を格納するテーブル",
                "columns": [
                    {
                        "name": "id",
                        "type": "INTEGER",
                        "description": "ユーザーを一意に識別するID",
                        "constraints": "PRIMARY KEY AUTOINCREMENT"
                    },
                    {
                        "name": "name",
                        "type": "TEXT",
                        "description": "ユーザー名",
                        "constraints": "NOT NULL"
                    },
                    {
                        "name": "email",
                        "type": "TEXT",
                        "description": "メールアドレス",
                        "constraints": ""
                    }
                ]
            }
        ]
    }
)
```

### データ挿入

```python
from database_manager import insert_data

# 単一レコード
insert_data(
    database_name="my_app",
    table_name="users",
    data={"name": "Alice", "email": "alice@example.com"}
)

# 複数レコード
insert_data(
    database_name="my_app",
    table_name="users",
    data=[
        {"name": "Bob", "email": "bob@example.com"},
        {"name": "Charlie", "email": "charlie@example.com"}
    ]
)
```

### クエリ実行

```python
from database_manager import query_data

# SELECT
result = query_data(
    database_name="my_app",
    sql_query="SELECT * FROM users WHERE name = 'Alice'"
)
print(result["rows"])  # [{"id": 1, "name": "Alice", "email": "alice@example.com"}]

# UPDATE
result = query_data(
    database_name="my_app",
    sql_query="UPDATE users SET email = 'new@example.com' WHERE id = 1"
)
print(result["affected_rows"])  # 1
```

### トランザクション実行

```python
from database_manager import execute_transaction

result = execute_transaction(
    database_name="my_app",
    operations=[
        {
            "type": "insert",
            "table_name": "users",
            "data": {"name": "David", "email": "david@example.com"}
        },
        {
            "type": "query",
            "sql": "UPDATE users SET email = ? WHERE name = ?",
            "params": ["updated@example.com", "David"]
        }
    ]
)

if result["status"] == "success":
    print(f"トランザクション成功: {result['operations_executed']}個の操作")
else:
    print(f"失敗（ロールバック済み）: {result['error_message']}")
```

---

## 環境変数の設定

### データベースディレクトリの設定

デフォルトでは、データベースファイルは `databases/` ディレクトリ（パッケージルートからの相対パス）に保存されます。

複数のMCPサーバーで同じデータベースを共有する場合は、環境変数 `MCP_DB_DIR` を設定してください。

```bash
# シェルで設定
export MCP_DB_DIR=/shared/databases

# Pythonコード内で設定
import os
os.environ["MCP_DB_DIR"] = "/shared/databases"

# その後、通常通りインポート
from database_manager import insert_data
```

### 注意点

- 環境変数は、`database_manager` をインポートする**前に**設定する必要があります
- 設定後は、すべての `database_manager` 関数が同じディレクトリを使用します
- ディレクトリが存在しない場合は自動的に作成されます

---

## 実装例

### 例1: MCPサーバー内で直接DB操作

```python
#!/usr/bin/env python3
"""
umw-mcp: Playwrightでページを取得してMarkdownに変換し、DBに保存
"""

from mcp.server.fastmcp import FastMCP
from database_manager import insert_data, query_data
from playwright.sync_api import sync_playwright
from datetime import datetime

mcp = FastMCP("umw-mcp")

@mcp.tool()
def capture_page_tool(url: str) -> dict:
    """
    ウェブページを取得してMarkdownに変換し、データベースに保存します。
    
    Args:
        url: 取得するページのURL
        
    Returns:
        保存結果を含む辞書
    """
    # Playwrightでページ取得
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(url)
        
        # Markdownに変換（実装は省略）
        markdown_content = page.content()  # 簡略化
        
        browser.close()
    
    # データベースに直接保存（LLM経由ではない）
    result = insert_data(
        database_name="umw_survey",
        table_name="page_captures",
        data={
            "url": url,
            "markdown": markdown_content,
            "captured_at": datetime.now().isoformat(),
            "status": "success"
        }
    )
    
    return {
        "status": "success",
        "url": url,
        "rows_inserted": result["rows_inserted"]
    }

@mcp.tool()
def get_captured_pages_tool() -> dict:
    """保存されたページ一覧を取得します。"""
    result = query_data(
        database_name="umw_survey",
        sql_query="SELECT url, captured_at FROM page_captures ORDER BY captured_at DESC LIMIT 10"
    )
    return result

if __name__ == "__main__":
    mcp.run()
```

### 例2: バルク挿入の使用

```python
from database_manager import bulk_insert_optimized

# 大量データを効率的に挿入
records = [
    {"name": f"User {i}", "email": f"user{i}@example.com"}
    for i in range(10000)
]

result = bulk_insert_optimized(
    database_name="my_app",
    table_name="users",
    records=records,
    batch_size=1000  # 1000件ずつバッチ処理
)

print(f"挿入完了: {result['inserted_records']}/{result['total_records']}件")
print(f"実行時間: {result['execution_time_ms']}ms")
```

### 例3: Prepared Statementの使用

```python
from database_manager import prepare_statement, execute_prepared, close_prepared

# Prepared Statement作成
prepare_statement(
    database_name="my_app",
    statement_id="update_user_email",
    sql="UPDATE users SET email = ? WHERE id = ?"
)

# 繰り返し実行（高速）
for user_id, new_email in user_updates:
    execute_prepared(
        database_name="my_app",
        statement_id="update_user_email",
        params=[new_email, user_id]
    )

# クローズ
close_prepared(
    database_name="my_app",
    statement_id="update_user_email"
)
```

### 例4: バッチクエリ実行

```python
from database_manager import execute_batch_queries

result = execute_batch_queries(
    database_name="my_app",
    queries=[
        {
            "query_id": "user_count",
            "sql": "SELECT COUNT(*) AS cnt FROM users"
        },
        {
            "query_id": "recent_users",
            "sql": "SELECT name, email FROM users ORDER BY id DESC LIMIT 5"
        }
    ]
)

user_count = result["results"]["user_count"]["data"]["rows"][0]["cnt"]
recent_users = result["results"]["recent_users"]["data"]["rows"]
```

### 例5: Markdownファイルをレコードに格納

```python
from database_manager import store_markdown_to_record

# 他のMCPサーバー（HTML→Markdown変換ツール）で作成されたMarkdownファイルのパスを使用
md_file_path = "/tmp/captured_pages/page_123.md"

# PRIMARY KEYでレコードを特定
result = store_markdown_to_record(
    database_name="umw_survey",
    table_name="page_captures",
    record_identifier=123,  # PRIMARY KEYの値
    column_name="markdown_content",
    md_file_path=md_file_path
)

print(f"格納完了: {result['affected_rows']}行更新, {result['content_length']}文字")

# WHERE条件でレコードを特定
result = store_markdown_to_record(
    database_name="umw_survey",
    table_name="page_captures",
    record_identifier={"url": "https://example.com", "session_id": 456},
    column_name="markdown_content",
    md_file_path="/tmp/example_page.md"
)
```

---

## 公開API一覧

### データベース操作

| 関数名 | 説明 | 戻り値 |
|--------|------|--------|
| `create_database(database_name, schema)` | データベース作成 | `{"status": "success", "db_path": "...", "tables": [...]}` |
| `delete_database(database_name, confirm)` | データベース削除 | `{"status": "deleted", ...}` |
| `list_all_databases()` | データベース一覧取得 | `{"status": "success", "databases": [...]}` |
| `get_database_info(database_name)` | データベース詳細情報取得 | `{"status": "success", "database_name": "...", ...}` |

### データ操作

| 関数名 | 説明 | 戻り値 |
|--------|------|--------|
| `insert_data(database_name, table_name, data)` | データ挿入 | `{"status": "success", "rows_inserted": N}` |
| `query_data(database_name, sql_query)` | SQLクエリ実行 | `{"status": "success", "rows": [...], "row_count": N}` または `{"affected_rows": N}` |
| `bulk_insert_optimized(database_name, table_name, records, batch_size, use_transaction)` | バルク挿入最適化 | `{"status": "success", "inserted_records": N, ...}` |

### トランザクション

| 関数名 | 説明 | 戻り値 |
|--------|------|--------|
| `execute_transaction(database_name, operations, isolation_level)` | トランザクション実行 | `{"status": "success", "operations_executed": N, "results": [...]}` |

### Prepared Statement

| 関数名 | 説明 | 戻り値 |
|--------|------|--------|
| `prepare_statement(database_name, statement_id, sql)` | Prepared Statement作成 | `{"status": "success", "statement_id": "...", "parameter_count": N}` |
| `execute_prepared(database_name, statement_id, params)` | Prepared Statement実行 | `{"status": "success", ...}` |
| `close_prepared(database_name, statement_id)` | Prepared Statementクローズ | `{"status": "success", ...}` |

### バッチクエリ

| 関数名 | 説明 | 戻り値 |
|--------|------|--------|
| `execute_batch_queries(database_name, queries, fail_fast)` | バッチクエリ実行 | `{"status": "success", "results": {...}, ...}` |

### スキーマ情報

| 関数名 | 説明 | 戻り値 |
|--------|------|--------|
| `get_table_schema(database_name, table_name)` | テーブルスキーマ取得 | `{"status": "success", "columns": [...]}` |
| `get_table_info(database_name, table_name)` | テーブル詳細情報取得 | `{"status": "success", "columns": [...], "sample_data": [...]}` |

### CSV操作

| 関数名 | 説明 | 戻り値 |
|--------|------|--------|
| `create_table_from_csv(database_name, table_name, csv_path, table_description, column_descriptions, encoding, primary_key_column)` | CSVからテーブル作成 | `{"status": "success", "inserted_rows": N, ...}` |
| `export_table_to_csv(database_name, table_name, csv_path, encoding)` | テーブルをCSVにエクスポート | `{"status": "success", "row_count": N, ...}` |

### Markdownファイル操作

| 関数名 | 説明 | 戻り値 |
|--------|------|--------|
| `store_markdown_to_record(database_name, table_name, record_identifier, column_name, md_file_path, encoding)` | Markdownファイルの内容をレコード・カラムに格納 | `{"status": "success", "affected_rows": N, "content_length": N, ...}` |

詳細なパラメータと戻り値は、各関数のdocstringを参照してください。

---

## よくある質問

### Q1: 既存のデータベースファイルは使えますか？

はい、既存のSQLiteデータベースファイルはそのまま使用できます。ただし、`database-manager` のメタデータテーブル（`_metadata`）が存在しない場合は、一部の機能（`get_database_info` など）でメタデータが取得できません。

### Q2: 複数のMCPサーバーから同時にアクセスできますか？

はい、可能です。ただし、SQLiteの同時書き込みには制限があります。頻繁な同時書き込みが発生する場合は、WALモードの有効化を検討してください（現在は未実装）。

### Q3: エラーハンドリングはどうすればいいですか？

各関数は適切な例外を発生させます：

```python
from database_manager import insert_data
from pathlib import Path

try:
    result = insert_data("my_db", "my_table", {"name": "test"})
except FileNotFoundError as e:
    print(f"データベースが見つかりません: {e}")
except ValueError as e:
    print(f"データ形式エラー: {e}")
except Exception as e:
    print(f"予期しないエラー: {e}")
```

### Q4: トランザクション内でエラーが発生した場合、ロールバックされますか？

はい、`execute_transaction` 関数は、いずれかの操作が失敗した場合、自動的にロールバックします。

```python
result = execute_transaction(
    database_name="my_app",
    operations=[...]
)

if result["status"] == "failed":
    print(f"ロールバック済み: {result['rollback_performed']}")
    print(f"エラー: {result['error_message']}")
```

### Q5: 環境変数 `MCP_DB_DIR` を設定しない場合、データベースはどこに保存されますか？

デフォルトでは、`databases/` ディレクトリ（`database-manager` パッケージのルートからの相対パス）に保存されます。パッケージをインストールした場合、このパスはインストール先によって異なります。

明示的にパスを指定したい場合は、環境変数を設定してください。

### Q6: 他のMCPサーバーとデータベースを共有するには？

1. 環境変数 `MCP_DB_DIR` を同じパスに設定
2. 同じ `database_name` を使用

```bash
# すべてのMCPサーバーで同じ設定
export MCP_DB_DIR=/shared/databases
```

### Q7: パッケージをインストールせずに使えますか？

はい、`sys.path` に追加することで使用できます：

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path("/path/to/mcp-agent-external-memory/src")))

from db_operations import insert_data
```

ただし、パッケージとしてインストールすることを推奨します。

---

## トラブルシューティング

### インポートエラー

```
ModuleNotFoundError: No module named 'database_manager'
```

**解決策**: パッケージをインストールしてください。

```bash
pip install -e /path/to/mcp-agent-external-memory
```

### データベースが見つからない

```
FileNotFoundError: Database 'my_db' not found
```

**解決策**: データベースを作成するか、正しい `database_name` を指定してください。

```python
from database_manager import create_database, get_database_info

# データベースが存在するか確認
try:
    info = get_database_info("my_db")
except FileNotFoundError:
    # データベースを作成
    create_database("my_db", schema={...})
```

### 環境変数が反映されない

**解決策**: 環境変数は、`database_manager` をインポートする**前に**設定してください。

```python
import os
os.environ["MCP_DB_DIR"] = "/shared/databases"

# その後インポート
from database_manager import insert_data
```

---

## 参考リンク

- [README.md](README.md) - プロジェクト全体の説明
- [design/DATABASE_MCP_GENERIC_FEATURES.md](design/DATABASE_MCP_GENERIC_FEATURES.md) - 機能仕様書

---

**作成日**: 2025-01-18  
**バージョン**: 0.1.0

