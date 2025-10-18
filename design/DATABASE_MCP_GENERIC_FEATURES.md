# database-manager MCP 汎用機能追加依頼書

**作成日**: 2025-10-18
**バージョン**: 2.0
**依頼者**: UMW4プロジェクトチーム

---

## 概要

本ドキュメントは、`database-manager` MCPサーバーに対して、**汎用的かつ一般的に有用な機能**の追加を依頼するものです。

### 依頼方針

- ✅ **汎用性重視**: どのプロジェクトでも使える機能のみ
- ✅ **プロジェクト非依存**: 特定のテーブルやスキーマに依存しない
- ❌ **プロジェクト固有機能は含めない**: UMW4専用の機能はUMW-MCPに実装

---

## 追加依頼機能一覧

### 1. トランザクション管理機能【優先度: 高】

現在、`database-manager`は単一のSQL文またはデータ挿入のみをサポートしていますが、複数操作をアトミックに実行するトランザクション管理機能を追加してください。

#### 追加機能: `executeTransaction`

```typescript
interface ExecuteTransactionRequest {
  database_name: string;
  operations: Array<{
    type: "query" | "insert" | "update" | "delete";
    sql?: string;                   // type="query"の場合
    params?: any[];                 // SQLパラメータ
    table_name?: string;            // type="insert"の場合
    data?: any | any[];             // 挿入データ
    // ... その他必要なフィールド
  }>;
  isolation_level?: "DEFERRED" | "IMMEDIATE" | "EXCLUSIVE";  // デフォルト: "DEFERRED"
}

interface ExecuteTransactionResponse {
  status: "success" | "failed";
  transaction_id: string;           // トランザクション識別子
  operations_executed: number;      // 実行された操作数
  results: Array<{
    operation_index: number;
    status: "success" | "failed";
    result?: any;                   // 操作結果
    error?: string;                 // 失敗時のエラーメッセージ
  }>;
  rollback_performed?: boolean;     // ロールバックが実行されたか
  error_message?: string;           // 全体的なエラーメッセージ
}
```

#### 期待される動作

1. `BEGIN TRANSACTION [isolation_level]`でトランザクション開始
2. `operations`配列の各操作を順番に実行
3. すべて成功した場合、`COMMIT`
4. 1つでも失敗した場合、`ROLLBACK`して全変更を取り消し
5. 実行結果を詳細に返す

#### 使用例

```python
result = await db_manager.executeTransaction(
    database_name="umw_survey",
    operations=[
        {
            "type": "insert",
            "table_name": "survey_sessions",
            "data": {
                "municipality_code": "131016",
                "session_type": "full",
                "status": "active",
                "started_at": "2025-10-18T09:00:00"
            }
        },
        {
            "type": "query",
            "sql": "INSERT INTO umid_progress (session_id, umid, status, version) VALUES (?, ?, 'null', 1)",
            "params": [123, "000001"]
        },
        {
            "type": "query",
            "sql": "UPDATE municipalities SET last_survey_date = ? WHERE code = ?",
            "params": ["2025-10-18", "131016"]
        }
    ]
)

if result["status"] == "success":
    print(f"トランザクション成功: {result['operations_executed']}個の操作")
else:
    print(f"トランザクション失敗（ロールバック済み）: {result['error_message']}")
```

#### この機能が汎用的な理由

- ✅ どのデータベース、どのプロジェクトでも複数操作のアトミック実行は必須
- ✅ 特定のテーブルやスキーマに依存しない
- ✅ 標準的なSQLトランザクション機能

---

### 2. バルク操作の最適化【優先度: 中】

大量データの挿入を効率化する機能を追加してください。

#### 追加機能: `bulkInsertOptimized`

```typescript
interface BulkInsertOptimizedRequest {
  database_name: string;
  table_name: string;
  records: Array<Record<string, any>>;  // 挿入するレコードの配列
  batch_size?: number;                  // バッチサイズ（デフォルト: 1000）
  use_transaction?: boolean;            // トランザクション使用（デフォルト: true）
}

interface BulkInsertOptimizedResponse {
  status: "success" | "partial_success" | "failed";
  total_records: number;                // 総レコード数
  inserted_records: number;             // 挿入成功レコード数
  failed_records: number;               // 失敗レコード数
  batches_processed: number;
  execution_time_ms: number;
  errors?: Array<{
    record_index: number;
    error_message: string;
  }>;
}
```

#### 期待される動作

1. レコードを`batch_size`ごとに分割
2. 各バッチをトランザクション内でプリペアドステートメントを使って挿入
3. 大量データでもメモリ効率良く処理
4. パフォーマンス統計を返す

#### 使用例

```python
# 10,000件のレコードを効率的に挿入
result = await db_manager.bulkInsertOptimized(
    database_name="umw_survey",
    table_name="content_item_evaluations",
    records=[
        {"analytics_result_id": 501, "item_name": "対象者", "score": 3, ...},
        {"analytics_result_id": 501, "item_name": "必要書類", "score": 2, ...},
        # ... 10,000件
    ],
    batch_size=1000
)

print(f"挿入完了: {result['inserted_records']}件 / {result['total_records']}件")
print(f"実行時間: {result['execution_time_ms']}ms")
```

#### この機能が汎用的な理由

- ✅ 大量データの効率的な挿入はどのプロジェクトでも必要
- ✅ 特定のテーブルに依存しない
- ✅ パフォーマンス最適化は一般的な要求

---

### 3. Prepared Statementの再利用【優先度: 中】

同じクエリを繰り返し実行する際のパフォーマンス向上のため、Prepared Statementの明示的な管理機能を追加してください。

#### 追加機能: `prepareStat ement`

```typescript
interface PrepareStatementRequest {
  database_name: string;
  statement_id: string;             // 識別子
  sql: string;                      // SQL文（プレースホルダ付き）
}

interface PrepareStatementResponse {
  status: "success";
  statement_id: string;
  parameter_count: number;          // プレースホルダ数
}
```

#### 追加機能: `executePrepared`

```typescript
interface ExecutePreparedRequest {
  database_name: string;
  statement_id: string;
  params: any[];                    // パラメータ配列
}

interface ExecutePreparedResponse {
  status: "success";
  result: any;                      // クエリ結果
}
```

#### 追加機能: `closePrepared`

```typescript
interface ClosePreparedRequest {
  database_name: string;
  statement_id: string;
}
```

#### 使用例

```python
# Prepared Statement作成
await db_manager.prepareStatement(
    database_name="umw_survey",
    statement_id="update_progress",
    sql="UPDATE umid_progress SET status = ?, version = version + 1 WHERE session_id = ? AND umid = ? AND version = ?"
)

# 繰り返し実行（高速）
for umid in umid_list:
    await db_manager.executePrepared(
        database_name="umw_survey",
        statement_id="update_progress",
        params=["research", 123, umid, 1]
    )

# クローズ
await db_manager.closePrepared(
    database_name="umw_survey",
    statement_id="update_progress"
)
```

#### この機能が汎用的な理由

- ✅ Prepared Statementは標準的なSQL機能
- ✅ パフォーマンス最適化として一般的
- ✅ 特定のクエリに依存しない

---

### 4. バッチクエリ実行【優先度: 低】

複数のSELECTクエリを効率的に実行する機能を追加してください。

#### 追加機能: `executeBatchQueries`

```typescript
interface ExecuteBatchQueriesRequest {
  database_name: string;
  queries: Array<{
    query_id: string;               // クエリ識別子
    sql: string;
    params?: any[];
  }>;
  fail_fast?: boolean;              // 1つ失敗したら即座に中止（デフォルト: false）
}

interface ExecuteBatchQueriesResponse {
  status: "success" | "partial_success" | "failed";
  results: {
    [query_id: string]: {
      status: "success" | "failed";
      data?: any;
      error?: string;
    };
  };
  total_queries: number;
  successful_queries: number;
  execution_time_ms: number;
}
```

#### 使用例

```python
result = await db_manager.executeBatchQueries(
    database_name="umw_survey",
    queries=[
        {
            "query_id": "session_info",
            "sql": "SELECT * FROM survey_sessions WHERE session_id = ?",
            "params": [123]
        },
        {
            "query_id": "progress_summary",
            "sql": "SELECT status, COUNT(*) FROM umid_progress WHERE session_id = ? GROUP BY status",
            "params": [123]
        },
        {
            "query_id": "municipality",
            "sql": "SELECT * FROM municipalities WHERE code = ?",
            "params": ["131016"]
        }
    ]
)

session = result["results"]["session_info"]["data"]
progress = result["results"]["progress_summary"]["data"]
```

#### この機能が汎用的な理由

- ✅ 複数クエリの効率的な実行は一般的なニーズ
- ✅ 特定のテーブルに依存しない
- ✅ パフォーマンス最適化として有用

---

### 5. データベース情報の詳細取得【優先度: 低】

既存の`get_database_info_tool`を拡張し、より詳細な情報を取得できるようにしてください。

#### 拡張機能: `get_database_info_tool`（拡張）

現在の出力に以下を追加：

```typescript
interface GetDatabaseInfoResponse {
  // 既存のフィールド
  database_name: string;
  tables: string[];
  table_count: number;
  total_records: number;
  size_mb: number;

  // 追加フィールド
  indices: Array<{                  // インデックス情報
    index_name: string;
    table_name: string;
    columns: string[];
    unique: boolean;
  }>;
  foreign_keys: Array<{             // 外部キー制約
    table_name: string;
    column: string;
    referenced_table: string;
    referenced_column: string;
  }>;
  views: string[];                  // ビュー一覧
  triggers: string[];               // トリガー一覧
  pragma_info: {                    // PRAGMA情報
    page_size: number;
    cache_size: number;
    journal_mode: string;
    synchronous: string;
  };
}
```

#### この機能が汎用的な理由

- ✅ データベースのメタ情報取得は一般的な要求
- ✅ デバッグ、最適化に有用
- ✅ 特定のスキーマに依存しない

---

## 依頼しない機能（プロジェクト固有）

以下の機能は**UMW-MCP**に実装するため、database-managerには依頼しません：

❌ `page_captures`テーブル専用メソッド
❌ `umid_progress`テーブル専用メソッド
❌ 楽観的ロックの高レベルAPI
❌ UMID関連のビジネスロジック
❌ レポート生成機能

これらはすべて**UMW-MCP**が汎用的なdatabase-manager APIを使って実装します。

---

## 優先度別まとめ

### 優先度: 高
1. ✅ **トランザクション管理**: `executeTransaction`

### 優先度: 中
2. ✅ **バルク挿入最適化**: `bulkInsertOptimized`
3. ✅ **Prepared Statement管理**: `prepareStatement`, `executePrepared`, `closePrepared`

### 優先度: 低
4. ✅ **バッチクエリ実行**: `executeBatchQueries`
5. ✅ **データベース情報拡張**: `get_database_info_tool`の拡張

---

## 期待される効果

これらの汎用機能により：

✅ **トランザクション管理**: データ整合性の保証、複雑な操作の簡便化
✅ **バルク操作**: 大量データ処理のパフォーマンス向上
✅ **Prepared Statement**: 繰り返しクエリの高速化
✅ **バッチ実行**: 複数クエリの効率化
✅ **詳細情報取得**: デバッグ、最適化の支援

これらはすべて**汎用的**であり、UMW4プロジェクトだけでなく、他のプロジェクトでも有用です。

---

## 参考: UMW-MCPでの使用例

### トランザクション管理の使用

```python
# UMW-MCP内部で使用
async def initializeSession(self, municipality_code, umid_list):
    # トランザクションで複数操作をアトミックに実行
    result = await self.db_manager.executeTransaction(
        database_name="umw_survey",
        operations=[
            {
                "type": "insert",
                "table_name": "survey_sessions",
                "data": {
                    "municipality_code": municipality_code,
                    "session_type": "full",
                    "status": "active",
                    "started_at": datetime.utcnow().isoformat()
                }
            },
            {
                "type": "query",
                "sql": "INSERT INTO umid_progress (session_id, umid, status, version, created_at, updated_at) VALUES " +
                       ", ".join(["(?, ?, 'null', 1, ?, ?)"] * len(umid_list)),
                "params": [session_id, umid, now, now for umid in umid_list]
            }
        ]
    )
    return result
```

### バルク挿入の使用

```python
# UMW-MCP内部で使用
async def saveContentItemEvaluations(self, analytics_result_id, evaluations):
    # 大量の評価データを効率的に挿入
    records = [
        {
            "analytics_result_id": analytics_result_id,
            "item_name": eval["item_name"],
            "required": eval["required"],
            "score": eval["score"],
            "evaluation_details": eval["evaluation_details"]
        }
        for eval in evaluations
    ]

    result = await self.db_manager.bulkInsertOptimized(
        database_name="umw_survey",
        table_name="content_item_evaluations",
        records=records,
        batch_size=1000
    )
    return result
```

---

## まとめ

本依頼は、database-managerに**汎用的かつ一般的に有用な機能**のみを追加するものです。

プロジェクト固有の機能（UMID管理、進捗管理、レポート生成等）はすべて**UMW-MCP**に実装することで、責任分離を明確にし、database-managerの汎用性を保ちます。

---

**提出日**: 2025-10-18
**バージョン**: 2.0
**ステータス**: 依頼書作成完了
