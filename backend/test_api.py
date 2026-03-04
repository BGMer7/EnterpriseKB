"""
API 测试脚本

注意：本系统使用企业微信登录，登录需要有效的企业微信授权码
"""
import requests

BASE_URL = "http://localhost:8000"

def test_health():
    """测试健康检查"""
    print("=== 健康检查 ===")
    resp = requests.get(f"{BASE_URL}/health")
    print(f"状态码: {resp.status_code}")
    print(f"响应: {resp.json()}")
    print()

def test_docs():
    """获取 API 文档"""
    print("=== API 文档 ===")
    resp = requests.get(f"{BASE_URL}/openapi.json")
    print(f"状态码: {resp.status_code}")

    # 提取所有路由
    paths = resp.json().get("paths", {})
    print(f"\n可用接口 ({len(paths)} 个):")
    for path, methods in sorted(paths.items()):
        for method in methods.keys():
            print(f"  {method.upper():6} {path}")
    print()

def test_login_wechat(code: str):
    """测试企业微信登录"""
    print(f"=== 企业微信登录 (code={code}) ===")
    resp = requests.post(
        f"{BASE_URL}/api/v1/auth/login",
        json={"code": code}
    )
    print(f"状态码: {resp.status_code}")
    print(f"响应: {resp.json()}")
    return resp.json().get("access_token")

def test_chat(token: str, message: str = "你好，请介绍一下你自己"):
    """测试对话接口"""
    print(f"=== 对话测试 ===")
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.post(
        f"{BASE_URL}/api/v1/chat/query",
        headers=headers,
        json={
            "message": message,
            "conversation_id": None
        }
    )
    print(f"状态码: {resp.status_code}")
    result = resp.json()
    print(f"响应: {result}")

def test_documents(token: str):
    """测试文档列表接口"""
    print(f"=== 文档列表 ===")
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.get(
        f"{BASE_URL}/api/v1/documents",
        headers=headers
    )
    print(f"状态码: {resp.status_code}")
    result = resp.json()
    print(f"响应: {result}")

def upload_document(token: str, file_path: str, title: str = None):
    """上传文档"""
    print(f"=== 上传文档: {file_path} ===")
    headers = {"Authorization": f"Bearer {token}"}
    with open(file_path, "rb") as f:
        files = {"file": (file_path, f, "application/pdf")}
        data = {
            "title": title or file_path.split("/")[-1],
            "is_public": "false",
            "allowed_roles": "[]"
        }
        resp = requests.post(
            f"{BASE_URL}/api/v1/documents/upload",
            headers=headers,
            files=files,
            data=data
        )
    print(f"状态码: {resp.status_code}")
    result = resp.json()
    print(f"响应: {result}")
    return result


if __name__ == "__main__":
    import sys

    # 1. 健康检查
    test_health()

    # 2. 查看所有可用接口
    test_docs()

    # 3. 企业微信登录测试
    wechat_code = input("\n请输入企业微信授权码 (直接回车跳过登录测试): ").strip()
    if wechat_code:
        token = test_login_wechat(wechat_code)
        if token:
            # 4. 对话测试
            test_chat(token)

            # 5. 上传文档测试
            file_path = input("\n请输入要上传的PDF文件路径 (直接回车跳过): ").strip()
            if file_path:
                upload_document(token, file_path)
    else:
        print("\n跳过登录测试")
        print("提示：可以在数据库中手动创建用户进行测试")
