"""
Parser API 独立测试脚本
不依赖完整后端服务，直接测试解析功能
"""
import requests
import json
import os

# 测试文件路径
TEST_FILE = r"d:\Learning\Projects\EnterpriseKB\backend\tests\files\1911.05722v3.pdf"
BASE_URL = "http://127.0.0.1:8000"


def test_supported_types():
    """测试获取支持的格式列表"""
    print("\n" + "=" * 60)
    print("测试1: 获取支持的格式列表")
    print("=" * 60)

    try:
        response = requests.get(f"{BASE_URL}/api/v1/parse/supported-types")
        print(f"状态码: {response.status_code}")
        print(f"响应内容:")
        print(json.dumps(response.json(), indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"❌ 测试失败: {e}")


def test_parse_document():
    """测试完整解析接口"""
    print("\n" + "=" * 60)
    print("测试2: 完整解析PDF文档")
    print("=" * 60)

    try:
        with open(TEST_FILE, "rb") as f:
            files = {"file": ("test.pdf", f, "application/pdf")}
            data = {"use_ocr": "false"}

            response = requests.post(
                f"{BASE_URL}/api/v1/parse/document",
                files=files,
                data=data
            )

        print(f"状态码: {response.status_code}")
        result = response.json()

        if result.get("success"):
            print(f"✅ 解析成功!")
            print(f"   字符数: {len(result.get('content', ''))}")
            print(f"   页数: {result.get('metadata', {}).get('page_count')}")
            print(f"   内容预览 (前500字符):")
            print("-" * 40)
            print(result.get("content", "")[:500])
        else:
            print(f"❌ 解析失败: {result.get('error')}")

    except Exception as e:
        print(f"❌ 测试失败: {e}")


def test_parse_simple():
    """测试简化版解析接口"""
    print("\n" + "=" * 60)
    print("测试3: 简化版解析")
    print("=" * 60)

    try:
        with open(TEST_FILE, "rb") as f:
            files = {"file": ("test.pdf", f, "application/pdf")}

            response = requests.post(
                f"{BASE_URL}/api/v1/parse/document/simple",
                files=files
            )

        print(f"状态码: {response.status_code}")
        result = response.json()

        print(f"响应:")
        print(json.dumps(result, indent=2, ensure_ascii=False))

    except Exception as e:
        print(f"❌ 测试失败: {e}")


def main():
    print("=" * 60)
    print("Parser API 测试")
    print("=" * 60)

    # 先测试获取支持的格式
    test_supported_types()

    # 测试解析文档
    if os.path.exists(TEST_FILE):
        test_parse_document()
        test_parse_simple()
    else:
        print(f"\n⚠️ 测试文件不存在: {TEST_FILE}")

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
