#!/usr/bin/env python3
"""
直接ツール関数を呼び出してテスト
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

def test_tools():
    """ツール関数を直接呼び出してテスト"""
    print("=" * 60)
    print("Direct Tool Function Test")
    print("=" * 60)
    
    # ツール関数をインポート
    from server import (
        get_usage_guide_tool,
        list_databases_tool,
        store_markdown_to_record_tool,
    )
    
    print("\n[1] Testing get_usage_guide_tool...")
    try:
        result = get_usage_guide_tool()
        print(f"  ✓ Success: {result.get('status', 'unknown')}")
        print(f"  - Overview keys: {list(result.get('overview', {}).keys())}")
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        return False
    
    print("\n[2] Testing list_databases_tool...")
    try:
        result = list_databases_tool()
        print(f"  ✓ Success: {result.get('status', 'unknown')}")
        print(f"  - Database count: {result.get('database_count', 0)}")
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        return False
    
    print("\n[3] Testing store_markdown_to_record_tool (with test data)...")
    # テスト用のMarkdownファイルを作成
    test_md = Path("/tmp/test_markdown.md")
    test_md.write_text("# Test Markdown\n\nThis is a test.", encoding="utf-8")
    
    # テスト用のDBとテーブルを作成
    from server import create_database_tool, insert_data_tool
    
    try:
        # DB作成
        create_result = create_database_tool(
            database_name="test_md_storage",
            schema={
                "database_description": "Markdownストレージテスト用データベース",
                "tables": [{
                    "table_name": "test_pages",
                    "table_description": "テスト用ページデータを格納",
                    "columns": [
                        {
                            "name": "id",
                            "type": "INTEGER",
                            "description": "ページID",
                            "constraints": "PRIMARY KEY AUTOINCREMENT"
                        },
                        {
                            "name": "url",
                            "type": "TEXT",
                            "description": "ページURL",
                            "constraints": ""
                        },
                        {
                            "name": "markdown_content",
                            "type": "TEXT",
                            "description": "Markdown形式のコンテンツ",
                            "constraints": ""
                        }
                    ]
                }]
            }
        )
        print(f"  ✓ Database created: {create_result.get('status')}")
        
        # テストレコードを挿入
        insert_result = insert_data_tool(
            database_name="test_md_storage",
            table_name="test_pages",
            data={"url": "https://example.com/test"}
        )
        print(f"  ✓ Record inserted: {insert_result.get('rows_inserted', 0)} rows")
        
        # Markdownを格納
        store_result = store_markdown_to_record_tool(
            database_name="test_md_storage",
            table_name="test_pages",
            record_identifier={"url": "https://example.com/test"},
            column_name="markdown_content",
            md_file_path=str(test_md)
        )
        print(f"  ✓ Markdown stored: {store_result.get('status')}")
        print(f"  - Affected rows: {store_result.get('affected_rows', 0)}")
        print(f"  - Content length: {store_result.get('content_length', 0)} chars")
        
        # クリーンアップ
        from server import delete_database_tool
        delete_database_tool("test_md_storage", confirm=True)
        test_md.unlink()
        
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n" + "=" * 60)
    print("✓ All tests passed!")
    print("=" * 60)
    return True

if __name__ == "__main__":
    success = test_tools()
    sys.exit(0 if success else 1)

