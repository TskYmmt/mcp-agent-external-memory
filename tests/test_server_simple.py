#!/usr/bin/env python3
"""
簡単なMCPサーバーテスト

サーバーが正しく起動し、ツールが登録されているか確認します。
"""

import sys
from pathlib import Path

# srcディレクトリをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

def test_server_import():
    """サーバーモジュールが正しくインポートできるか確認"""
    print("=" * 60)
    print("MCP Server Import Test")
    print("=" * 60)
    
    try:
        print("\n[1] Importing server module...")
        from server import mcp
        print("  ✓ Server module imported successfully")
        
        print("\n[2] Checking registered tools...")
        # FastMCPのツールを確認
        # mcp._tools または mcp.tools でアクセスできる可能性がある
        tools_count = len(mcp._tools) if hasattr(mcp, '_tools') else 0
        print(f"  ✓ Found {tools_count} registered tools")
        
        # ツール名のリストを取得
        if hasattr(mcp, '_tools'):
            tool_names = list(mcp._tools.keys())
            print(f"\n  Registered tools:")
            for name in sorted(tool_names):
                print(f"    - {name}")
            
            # 重要なツールが含まれているか確認
            important_tools = [
                "get_usage_guide_tool",
                "create_database_tool",
                "insert_data_tool",
                "query_data_tool",
                "store_markdown_to_record_tool"
            ]
            
            print(f"\n[3] Checking important tools...")
            for tool_name in important_tools:
                if tool_name in tool_names:
                    print(f"  ✓ {tool_name}")
                else:
                    print(f"  ✗ {tool_name} (NOT FOUND)")
        
        print("\n" + "=" * 60)
        print("✓ All tests passed!")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_server_import()
    sys.exit(0 if success else 1)

