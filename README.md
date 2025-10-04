# MCP Server for Database Management

AIエージェントがデータを自律的に蓄積・管理するためのMCPサーバーです。

## 概要

このMCPサーバーは、AIエージェントがデータ収集を実施した際に、その場で最適なデータベース構造を設計し、データを自動的に蓄積していくためのツールを提供します。

### 重要な設計思想

- **データ管理に特化**: このサーバーはデータベース操作に特化しています。実際のデータ収集（Web検索など）は別のツールで実施してください。
- **完全自律型**: AIがデータ内容に応じて最適なDB/テーブル構造を判断し、動的に作成します。
- **セキュアな設計**: SQLインジェクション対策、書き込み制限、2段階削除確認など、安全性を重視しています。

## 技術スタック

- **言語**: Python 3.10+
- **フレームワーク**: FastMCP
- **データベース**: SQLite
- **パッケージマネージャ**: uv

## セットアップ

### 1. 依存関係のインストール

```bash
# uvを使用してインストール
uv sync
```

### 2. Claude Desktop設定

`~/Library/Application Support/Claude/claude_desktop_config.json` に以下を追加:

```json
{
  "mcpServers": {
    "database-manager": {
      "command": "uv",
      "args": [
        "--directory",
        "/absolute/path/to/mcp-agent-external-memory",
        "run",
        "src/server.py"
      ]
    }
  }
}
```

**重要**: `/absolute/path/to/mcp-agent-external-memory` を実際の絶対パスに置き換えてください。

例:
```json
{
  "mcpServers": {
    "database-manager": {
      "command": "uv",
      "args": [
        "--directory",
        "/Users/tskymmt/mcp/mcp-agent-external-memory",
        "run",
        "src/server.py"
      ]
    }
  }
}
```

### 3. Claude Desktopを再起動

設定を反映させるため、Claude Desktopを完全に終了して再起動してください。

## 提供するツール

### 1. `create_database`
新しいデータベースとテーブルを作成します。

**パラメータ**:
- `database_name` (str): データベース名（拡張子不要）
- `table_schema` (dict): テーブル定義
- `description` (str): データベースの目的

**例**:
```python
create_database(
    database_name="tech_companies_2025",
    table_schema={
        "table_name": "companies",
        "columns": {
            "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
            "company_name": "TEXT NOT NULL",
            "industry": "TEXT",
            "market_cap": "REAL",
            "research_date": "TEXT"
        }
    },
    description="テクノロジー企業の市場調査データ"
)
```

### 2. `insert_data`
調査結果データをデータベースに挿入します。

**パラメータ**:
- `database_name` (str): 対象データベース
- `table_name` (str): 対象テーブル
- `data` (dict | list[dict]): 挿入データ

**例**:
```python
insert_data(
    database_name="tech_companies_2025",
    table_name="companies",
    data=[
        {
            "company_name": "Apple Inc.",
            "industry": "Technology",
            "market_cap": 3000000000000,
            "research_date": "2025-01-15"
        },
        {
            "company_name": "Microsoft Corp.",
            "industry": "Technology",
            "market_cap": 2800000000000,
            "research_date": "2025-01-15"
        }
    ]
)
```

### 3. `query_data`
蓄積されたデータをSQL検索・分析します。

**パラメータ**:
- `database_name` (str): 対象データベース
- `sql_query` (str): SELECT文

**例**:
```python
query_data(
    database_name="tech_companies_2025",
    sql_query="SELECT company_name, market_cap FROM companies WHERE industry = 'Technology' ORDER BY market_cap DESC"
)
```

**セキュリティ**: SELECT文のみ許可されています。DROP、DELETE、UPDATEは拒否されます。

### 4. `get_schema`
テーブルのスキーマ情報を取得します。

**パラメータ**:
- `database_name` (str): 対象データベース
- `table_name` (str): 対象テーブル

**例**:
```python
get_schema(
    database_name="tech_companies_2025",
    table_name="companies"
)
```

### 5. `list_databases`
すべてのデータベースを一覧表示します。

**パラメータ**: なし

**例**:
```python
list_databases()
```

**戻り値には以下が含まれます**:
- データベース名
- ファイルサイズ
- 作成日時・更新日時
- 説明
- テーブル一覧
- 総レコード数

### 6. `delete_database_tool`
データベースを削除します（2段階確認必須）。

**パラメータ**:
- `database_name` (str): 削除対象データベース
- `confirm` (bool): 削除確認フラグ

**例**:
```python
# Step 1: 確認
delete_database_tool(database_name="old_data.db", confirm=False)

# Step 2: 実行
delete_database_tool(database_name="old_data.db", confirm=True)
```

## 使用例シナリオ

### シナリオ1: GAFAM企業の市場調査

```
ユーザー: 「GAFAM各社の時価総額を調査してデータベースに保存して」

AIの動作:
1. create_database でデータベース作成
2. （Web検索などで調査実施 ← 別ツール）
3. insert_data で調査結果を挿入
4. query_data で結果を分析
5. ユーザーに報告
```

### シナリオ2: 既存DBへの追加調査

```
ユーザー: 「昨日作った企業データベースにNetflixとTeslaのデータも追加して」

AIの動作:
1. list_databases で既存DB確認
2. get_schema でスキーマ確認
3. （調査実施 ← 別ツール）
4. insert_data で新データ追加
```

### シナリオ3: データベース管理

```
ユーザー: 「今までに作った調査データベースを全部見せて」

AIの動作:
1. list_databases を呼び出し
2. 結果を整形してユーザーに表示
```

## ディレクトリ構成

```
mcp-agent-external-memory/
├── src/
│   ├── __init__.py
│   ├── server.py          # MCPサーバーメイン
│   └── db_operations.py   # データベース操作ロジック
├── tests/
│   └── test_server.py     # 動作テスト
├── databases/             # 作成されるDBファイルの保存先
│   └── .gitkeep
├── design/
│   └── 設計書.md          # 設計仕様書
├── pyproject.toml         # プロジェクト設定
├── .gitignore
├── ai-memo.md             # 実装メモ
└── README.md              # このファイル
```

## セキュリティ機能

### SQLインジェクション対策
すべてのクエリでパラメータ化クエリを使用しています。

### 操作制限
- **許可**: CREATE TABLE, INSERT, SELECT
- **禁止**: DROP, DELETE, UPDATE（基本的に）

### ファイルシステム隔離
データベースファイルは `databases/` ディレクトリ内のみに作成されます。

### 削除の安全性
- 2段階確認必須（`confirm=true` が明示的に必要）
- 削除前に対象の詳細情報をログ出力
- 削除操作の監査ログを記録

## メタデータ管理

各データベースには `_metadata` テーブルが自動的に作成され、以下の情報が記録されます:
- データベースの説明
- 作成日時
- 最終更新日時
- テーブルリスト

## トラブルシューティング

### MCPサーバーが起動しない

1. uvが正しくインストールされているか確認
   ```bash
   uv --version
   ```

2. 依存関係がインストールされているか確認
   ```bash
   uv sync
   ```

3. Claude Desktop設定ファイルのパスが正しいか確認（`src/server.py`を含める）

4. テストスクリプトで動作確認
   ```bash
   uv run python tests/test_server.py
   ```

### データベースが見つからない

`list_databases()` を使用して既存のデータベースを確認してください。

### SQLエラーが発生する

- SELECT文のみが許可されています
- テーブル名・カラム名が正しいか確認してください
- `get_schema()` でスキーマを確認してください

## 開発・テスト

### テストスクリプトで動作確認

```bash
uv run python tests/test_server.py
```

すべてのテストがパスすることを確認してください。

### MCPインスペクターでテスト

```bash
npx @modelcontextprotocol/inspector uv --directory /path/to/mcp-agent-external-memory run src/server.py
```

### ログの確認

サーバーは標準出力にログを出力します。Claude Desktopのログから確認できます。

## ライセンス

MIT License

## 貢献

プルリクエストを歓迎します。大きな変更の場合は、まずissueを開いて変更内容を議論してください。
