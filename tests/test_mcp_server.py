#!/usr/bin/env python3
"""
MCPサーバーの動作テストスクリプト

MCPプロトコルを使ってサーバーに接続し、ツールが正しく動作するか確認します。
"""

import json
import sys
import subprocess
from pathlib import Path

def test_mcp_server():
    """MCPサーバーを起動して基本的な動作をテスト"""
    
    print("=" * 60)
    print("MCP Server Test")
    print("=" * 60)
    
    # サーバーのパス
    server_path = Path(__file__).parent.parent / "src" / "server.py"
    
    # MCPプロトコルの初期化メッセージ
    init_message = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {
                "name": "test-client",
                "version": "1.0.0"
            }
        }
    }
    
    # ツール一覧取得
    list_tools_message = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/list"
    }
    
    # get_usage_guide_toolを呼び出す
    call_tool_message = {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {
            "name": "get_usage_guide_tool",
            "arguments": {}
        }
    }
    
    print("\n[1] Starting MCP server...")
    try:
        # サーバーを起動
        process = subprocess.Popen(
            ["uv", "run", "python", str(server_path)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=str(server_path.parent.parent)
        )
        
        # 初期化メッセージを送信
        print("\n[2] Sending initialize message...")
        process.stdin.write(json.dumps(init_message) + "\n")
        process.stdin.flush()
        
        # 応答を読み取る（タイムアウト付き）
        import select
        import time
        
        responses = []
        timeout = 5
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if process.stdout.readable():
                line = process.stdout.readline()
                if line:
                    try:
                        response = json.loads(line.strip())
                        responses.append(response)
                        print(f"  Received: {response.get('method', response.get('id', 'unknown'))}")
                        
                        # 初期化完了を待つ
                        if response.get("method") == "notifications/initialized":
                            break
                    except json.JSONDecodeError:
                        pass
        
        if not responses:
            print("  ⚠ No response received")
            process.terminate()
            return False
        
        # ツール一覧を取得
        print("\n[3] Requesting tools list...")
        process.stdin.write(json.dumps(list_tools_message) + "\n")
        process.stdin.flush()
        
        time.sleep(1)
        line = process.stdout.readline()
        if line:
            try:
                tools_response = json.loads(line.strip())
                if "result" in tools_response and "tools" in tools_response["result"]:
                    tools = tools_response["result"]["tools"]
                    print(f"  ✓ Found {len(tools)} tools:")
                    for tool in tools[:5]:  # 最初の5つを表示
                        print(f"    - {tool.get('name', 'unknown')}")
                    if len(tools) > 5:
                        print(f"    ... and {len(tools) - 5} more")
                    
                    # store_markdown_to_record_toolが含まれているか確認
                    tool_names = [t.get("name") for t in tools]
                    if "store_markdown_to_record_tool" in tool_names:
                        print("  ✓ store_markdown_to_record_tool is available")
                    else:
                        print("  ⚠ store_markdown_to_record_tool not found")
                else:
                    print(f"  ⚠ Unexpected response: {tools_response}")
            except json.JSONDecodeError as e:
                print(f"  ⚠ Failed to parse response: {e}")
        
        # サーバーを終了
        process.terminate()
        process.wait(timeout=2)
        
        print("\n" + "=" * 60)
        print("✓ Test completed")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        if 'process' in locals():
            process.terminate()
        return False


if __name__ == "__main__":
    success = test_mcp_server()
    sys.exit(0 if success else 1)

