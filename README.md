# MCP Database Manager

**AIエージェントが自律的にデータを蓄積・管理できる、セルフドキュメンティング型MCPサーバー**

## 特徴

### 🤖 AIファースト設計
- **事前知識不要**: AIエージェントがMCPに接続するだけで、使い方を完全に理解できる
- **セルフドキュメンティング**: 全ツールに詳細な日本語説明、使用例、エラーガイド付き
- **メタデータ必須**: データベース/テーブル/カラムすべてに説明が必須（5文字以上）

### 🔍 発見可能性
- **使い方ガイドツール**: `get_usage_guide_tool` で全体像を即座に把握
- **情報階層ツール**: DB一覧 → DB詳細 → テーブル詳細と段階的に探索可能
- **サンプルデータ表示**: テーブル情報取得時に実データ3件を自動表示

### 🔒 セキュリティ
- SQLインジェクション対策（パラメータ化クエリ）
- SELECT文のみ許可（破壊的操作は制限）
- ファイルシステム隔離（`databases/`ディレクトリ内のみ）
- 削除時の2段階確認

## クイックスタート

### 1. インストール

```bash
# 依存関係のインストール
uv sync
```

### 2. Claude Desktop設定

`~/Library/Application Support/Claude/claude_desktop_config.json`:

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

**重要**: `/absolute/path/to/mcp-agent-external-memory` を実際のパスに置き換えてください。

### 3. 再起動

Claude Desktopを再起動して設定を反映させます。

## AIエージェント向けガイド

### Step 1: 使い方を理解する

MCPに接続したら、まず `get_usage_guide_tool()` を呼び出してください。このツール1つで、サーバーの全体像、スキーマ形式、ワークフロー、ベストプラクティスが分かります。

### Step 2: 既存DBを確認する

`list_databases_tool()` でDB一覧を取得できます。各DBの目的、テーブル数、レコード数が表示されます。

### Step 3: DB詳細を理解する

気になるDBがあれば、`get_database_info_tool(database_name)` で詳細を取得。データベースの説明、スキーマ情報、作成日時などが分かります。

### Step 4: テーブル構造を把握する

`get_table_info_tool(database_name, table_name)` でテーブルの詳細を確認。各カラムの説明と実際のサンプルデータ（最大3件）が表示されます。

### Step 5: 新規DBを作成する

メタデータ（説明文）を**必ず含めて**作成してください。スキーマ形式は `get_usage_guide_tool()` で確認できます。

```python
create_database_tool(
    database_name="book_collection",
    schema={
        "database_description": "個人の蔵書を管理するデータベース",
        "tables": [{
            "table_name": "books",
            "table_description": "所有している書籍の情報を格納するテーブル",
            "columns": [
                {
                    "name": "id",
                    "type": "INTEGER",
                    "description": "書籍を一意に識別するID",
                    "constraints": "PRIMARY KEY AUTOINCREMENT"
                },
                {
                    "name": "title",
                    "type": "TEXT",
                    "description": "書籍のタイトル名",
                    "constraints": "NOT NULL"
                }
            ]
        }]
    }
)
```

## 提供ツール（全9種）

| ツール名 | 用途 | 必須パラメータ |
|---------|------|--------------|
| `get_usage_guide_tool` | 使い方ガイドを取得 | なし |
| `list_databases_tool` | DB一覧を取得 | なし |
| `get_database_info_tool` | DB詳細情報を取得 | `database_name` |
| `get_table_info_tool` | テーブル詳細とサンプルデータを取得 | `database_name`, `table_name` |
| `create_database_tool` | 新規DB作成（メタデータ必須） | `database_name`, `schema` |
| `insert_data_tool` | データ挿入 | `database_name`, `table_name`, `data` |
| `query_data_tool` | SELECT検索 | `database_name`, `sql_query` |
| `get_schema_tool` | スキーマ取得（非推奨、`get_table_info_tool`推奨） | `database_name`, `table_name` |
| `delete_database_tool` | DB削除（2段階確認） | `database_name`, `confirm` |

## メタデータ必須ポリシー

このサーバーでは、**すべてのデータベース、テーブル、カラムに5文字以上の説明が必須**です。これにより、1週間後や他のAIエージェントでも、DBの目的と構造を即座に理解できます。

### 必須項目
- ✅ `database_description`: データベースの目的（5文字以上）
- ✅ `table_description`: テーブルの役割（5文字以上）
- ✅ `column.description`: 各カラムの意味（5文字以上）

### バリデーション
メタデータが不足している場合、詳細なエラーメッセージで修正方法を案内します。

## 使用例

### シナリオ1: 蔵書管理

```
ユーザー: 「私の本をデータベースで管理したい」

AIの動作:
1. create_database_tool で book_collection を作成
2. insert_data_tool で書籍データを挿入
3. query_data_tool で「読了」した本を検索
4. 結果をユーザーに報告
```

### シナリオ2: 既存DBの再利用

```
ユーザー: 「1週間前に作ったDBに追加データを入れて」

AIの動作:
1. list_databases_tool でDB一覧確認
2. get_database_info_tool で目的のDBを特定
3. get_table_info_tool でスキーマ確認
4. insert_data_tool で新データ追加
```

## 検証結果

外部AIエージェント（Claude Sonnet 4.5）による検証テスト結果:

- ✅ **事前知識**: ゼロ
- ✅ **所要時間**: 8分
- ✅ **完了シナリオ**: 4/4（全成功）
- ✅ **評価**: 5点/5点（全項目満点）
- ✅ **推奨度**: 強く推奨

**主なフィードバック**:
- "get_usage_guide_toolが秀逸。これ一つで全体像を完全に把握できた"
- "メタデータ必須設計により、後から見ても理解できる"
- "サンプルデータ表示が実用的。説明だけでなく実例で理解できる"

詳細: [`tests/validation/MCP_TEST_REQUEST_COMPLETED.md`](tests/validation/MCP_TEST_REQUEST_COMPLETED.md)

## ディレクトリ構成

```
mcp-agent-external-memory/
├── src/
│   ├── server.py          # MCPサーバー（FastMCP）
│   └── db_operations.py   # DB操作ロジック
├── tests/
│   ├── test_server.py     # 単体テスト
│   └── validation/        # 外部検証テスト結果
│       ├── MCP_TEST_REQUEST.md
│       └── MCP_TEST_REQUEST_COMPLETED.md
├── databases/             # DBファイル保存先（.gitignore）
├── design/
│   └── 設計書.md
├── pyproject.toml
└── README.md
```

## トラブルシューティング

### MCPサーバーが起動しない

```bash
# uvが正しくインストールされているか確認
uv --version

# 依存関係を再インストール
uv sync

# 設定ファイルのパスを確認（src/server.py を含める）
```

### スキーマ定義エラー

エラーメッセージに従って修正してください。よくあるエラー:
- メタデータが5文字未満
- `database_description` が未定義
- `columns` 配列に `description` フィールドがない

`get_usage_guide_tool()` でスキーマ形式の例を確認できます。

### データベースが見つからない

```python
# すべてのDBを確認
list_databases_tool()

# 特定のDBの詳細を確認
get_database_info_tool(database_name="your_database")
```

## 技術スタック

- **Python**: 3.10+
- **MCP Framework**: FastMCP
- **Database**: SQLite
- **Package Manager**: uv

## ライセンス

MIT License
