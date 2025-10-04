# MCP機能追加依頼: CSV一括インポート機能

## 概要
database-manager MCPサーバーにCSVファイルからテーブルへの一括データインポート機能を追加する

## 背景・課題
現在、137件の自治体データをtarget_jichitaiテーブルに挿入する際、以下の課題がある：
- Agent SDKで1件ずつ処理すると時間がかかる（56件で停止）
- 自治体コード取得と挿入を繰り返す必要がある
- エラーハンドリングが複雑
- 出力が多すぎてEPIPEエラーが発生

## 要求機能

### ツール名
`import_csv_to_table_tool`

### パラメータ
```python
{
    "database_name": str,           # データベース名（必須）
    "table_name": str,              # テーブル名（必須）
    "csv_path": str,                # CSVファイルの絶対パス（必須）
    "column_mapping": dict,         # CSVカラム→テーブルカラムのマッピング（オプション）
    "skip_duplicates": bool,        # PRIMARY KEY重複時にスキップ（デフォルト: true）
    "auto_fetch_jichitai_code": bool,  # 自治体コードを自動取得（デフォルト: false）
    "jichitai_name_column": str,    # 自治体名のカラム名（auto_fetch時に必要）
    "prefecture_column": str,       # 都道府県のカラム名（auto_fetch時に補完用）
    "encoding": str                 # CSVのエンコーディング（デフォルト: "utf-8"）
}
```

### 処理フロー
1. **CSV読み込み**
   - 指定されたパスからCSVを読み込み
   - エンコーディングを指定可能

2. **自動補完機能**（`auto_fetch_jichitai_code=true`の場合）
   - 各行の`jichitai_name_column`から自治体名を取得
   - jichitai-basic-information MCPの`get_jichitai_code`を呼び出し
   - 自治体コードを取得して行に追加
   - 都道府県が空の場合、MCPの結果から補完

3. **カラムマッピング**
   - `column_mapping`が指定されていれば適用
   - 未指定の場合、CSVのヘッダーとテーブルカラムを自動マッチング

4. **重複チェック**
   - `skip_duplicates=true`の場合、PRIMARY KEY制約違反をスキップ
   - スキップした件数をカウント

5. **バッチ挿入**
   - トランザクション内で一括挿入
   - エラー発生時はロールバック

6. **結果レポート**
   ```json
   {
       "status": "success",
       "total_rows": 137,
       "inserted_rows": 81,
       "skipped_rows": 56,
       "error_rows": 0,
       "errors": []
   }
   ```

## 使用例

### 基本的な使用（自治体コード自動取得あり）
```python
mcp__database-manager__import_csv_to_table_tool(
    database_name="jichitai_research_2025",
    table_name="target_jichitai",
    csv_path="/Users/tskymmt/git/jichitaiSalesAnalyzer/preRsearch/導入済み自治体調査/03_統合自治体リスト_final.csv",
    skip_duplicates=True,
    auto_fetch_jichitai_code=True,
    jichitai_name_column="jichitai_name",
    prefecture_column="prefecture"
)
```

### カラムマッピング指定
```python
mcp__database-manager__import_csv_to_table_tool(
    database_name="jichitai_research_2025",
    table_name="target_jichitai",
    csv_path="./data.csv",
    column_mapping={
        "name": "jichitai_name",
        "pref": "prefecture",
        "type": "system_type"
    },
    skip_duplicates=True
)
```

## 技術的詳細

### 依存関係
- 既存のdatabase-manager MCP機能
- jichitai-basic-information MCPの`get_jichitai_code`ツール（オプション機能で使用）
- Python標準ライブラリ: `csv`, `sqlite3`

### エラーハンドリング
- CSVファイルが存在しない → FileNotFoundError
- データベースが存在しない → エラーメッセージ
- テーブルが存在しない → エラーメッセージ
- カラム名が一致しない → エラーメッセージ
- 自治体コード取得失敗 → その行をスキップ、エラーリストに追加
- データ型不一致 → エラーメッセージ

### パフォーマンス
- 100件以下: 即時処理
- 100件以上: 10件ごとに進捗表示（オプション）
- トランザクション単位: 全件（失敗時は全ロールバック）

## 期待される効果
1. **処理時間の短縮**: 137件が数秒で完了
2. **コード簡素化**: Agent SDKの複雑な処理が不要
3. **エラー削減**: 統一されたエラーハンドリング
4. **再利用性**: 他のテーブルへのインポートでも使用可能

## 優先度
**高**: 現在進行中のタスク（137自治体データ挿入）で即座に必要

## 補足
- 自治体コード自動取得機能により、jichitai-basic-information MCPとの連携が可能
- 都道府県の自動補完により、データ品質が向上
- 重複スキップ機能により、部分的な再実行が安全に可能
