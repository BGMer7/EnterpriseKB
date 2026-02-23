"""
EnterpriseKB - 简化版应用入口
用于演示和测试，不依赖外部服务（Milvus/Meilisearch/vLLM）
"""
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# 创建FastAPI应用
app = FastAPI(
    title="EnterpriseKB API (Demo)",
    description="企业内部制度查询助手 - RAG Chatbot API (简化演示版)",
    version="1.0.0",
    docs_url="/docs"
)


# ===== 数据模型 =====
class Message(BaseModel):
    role: str
    content: str
    timestamp: datetime = datetime.utcnow()


class ChatRequest(BaseModel):
    query: str


class SourceReference(BaseModel):
    document_id: str
    document_title: str
    section: Optional[str] = None
    content_preview: str


class ChatResponse(BaseModel):
    answer: str
    sources: List[SourceReference]
    suggested_questions: List[str]


class Document(BaseModel):
    id: str
    title: str
    file_name: str
    status: str
    created_at: datetime


class User(BaseModel):
    id: str
    name: str
    email: Optional[str] = None


# ===== 模拟数据 =====
MOCK_USERS = [
    User(id="1", name="张三", email="zhangsan@enterprise.com"),
    User(id="2", name="李四", email="lisi@enterprise.com"),
    User(id="3", name="王五", email="wangwu@enterprise.com"),
]

MOCK_DOCUMENTS = [
    Document(
        id="doc001",
        title="员工考勤管理办法",
        file_name="考勤制度.pdf",
        status="published",
        created_at=datetime(2024, 1, 1)
    ),
    Document(
        id="doc002",
        title="差旅报销流程",
        file_name="报销流程.pdf",
        status="published",
        created_at=datetime(2024, 1, 2)
    ),
    Document(
        id="doc003",
        title="年假申请流程",
        file_name="年假制度.pdf",
        status="published",
        created_at=datetime(2024, 1, 3)
    ),
    Document(
        id="doc004",
        title="薪酬福利管理办法",
        file_name="薪酬制度.pdf",
        status="published",
        created_at=datetime(2024, 1, 4)
    ),
]


# ===== 知识库（模拟） =====
KNOWLEDGE_BASE = {
    "考勤": {
        "问题": ["考勤时间是怎样的？", "上班时间", "迟到处罚", "请假怎么扣款"],
        "答案": "根据《员工考勤管理办法》，员工工作时间为：\n- 工作日：周一至周五 9:00-18:00\n- 午餐时间：12:00-13:00，17:30-18:00\n\n迟到处罚：\n- 迟到15分钟以内：口头警告\n- 迟到15-30分钟：扣除当天全勤奖\n- 迟到30分钟以上：记旷工半天\n\n请假扣款：\n- 事假：不扣基本工资，岗位工资按日计算\n- 病假：支付基本工资的80%，岗位工资按日计算\n- 病假：支付基本工资的60%，岗位工资按日计算\n\n- 病假（含节假日）：正常支付工资",
        "来源": "员工考勤管理办法 第一章 第二条"
    },
    "报销": {
        "问题": ["报销流程", "报销标准", "发票要求"],
        "答案": "根据《差旅报销流程》：\n1. 员工前提交报销申请\n2. 附上相关发票（住宿、交通、餐费）\n3. 部门主管审批（3个工作日内）\n4. 财务审核（5个工作日内）\n\n报销标准：\n- 住宿费：一线城市300元/天，二线城市250元/天，三线城市200元/天\n- 交通费：按实际发生费用报销（需有发票）\n- 餐饮费：80元/天（含早中晚餐，不含酒水）",
        "来源": "差旅报销管理办法 第三章"
    },
    "年假": {
        "问题": ["年假天数", "年假申请流程", "年假工资"],
        "答案": "根据《员工福利管理办法》：\n\n年假天数：\n- 工作满1年：5天\n- 工作满10年：10天\n- 工作满20年：15天\n\n申请流程：\n1. 提前30天向直属主管提交书面申请\n2. 部门主管签字确认\n3. 人事部门审核\n4- 批准后生效\n\n工资计算：年假期间正常支付基本工资，岗位工资按日计算",
        "来源": "员工福利管理办法 第六章"
    },
    "薪酬": {
        "问题": ["薪酬发放时间", "绩效奖金", "社保公积金"],
        "答案": "根据《薪酬福利管理办法》：\n\n发放时间：\n- 每月15日发放上月工资\n- 遇节假日顺延到最近工作日\n\n绩效奖金：\n- 按季度考核结果发放\n  - 优秀（前10%）：基本工资×20%\n  - 良好（前30%）：基本工资×15%\n  - 合格（前50%）：基本工资×10%\n\n社保公积金：\n- 按国家规定和公司标准缴纳\n- 养老保险：公司按8%比例缴纳\n- 医疗保险：公司按2%比例缴纳\n- 住房公积金：公司按12%比例缴纳",
        "来源": "薪酬福利管理办法 第二章"
    },
    "请假": {
        "问题": ["病假", "事假", "婚假", "产假"],
        "答案": "根据《请假管理办法》：\n\n病假：\n- 需提供医院证明\n- 病假期间：支付基本工资的60%，岗位工资按日计算\n- 连续病假超过3个月：发放病假工资\n\n事假：\n-  需提前1-3天申请\n- 事假3天以内：全额发放工资\n- 事假3-7天：扣除基本工资的50%\n- 事假7天以上：扣除基本工资的100%\n\n婚假：\n-  员工满1年：3天\n- 周工满10年：10天\n- 周工满20年：15天\n- 发放婚假期间工资（含岗位工资）\n\n产假：\n-  产假98天 + 15天难产假\n- 产假期间：全额发放工资\n- 符合生育津贴标准发放生育津贴",
        "来源": "请假管理制度 第四章"
    },
    "办公": {
        "问题": ["办公用品", "会议室预订", "用车申请"],
        "答案": "根据《办公管理办法》：\n\n办公用品申领：\n- 登录OA系统提交申请\n- 需说明物品名称、数量、用途\n- 一次性物品：部门管理员直接审批\n- 低值易耗品：由部门主管审批\n\n\n会议室预订：\n- 提前1个工作日预订\n- 预订成功后发送确认邮件\n- 使用完毕后需清理现场\n\n用车申请：\n- 提前1个工作日申请\n- 注明用车时间、目的地、乘车人数\n- 因公用车产生的费用公司承担",
        "来源": "办公管理办法 第二章"
    }
}


def search_knowledge(query: str) -> tuple[str, List[SourceReference]]:
    """
    搜索知识库（模拟RAG检索）

    Returns:
        tuple: (答案, 引用来源列表)
    """
    query_lower = query.lower()
    answer = ""
    sources = []

    # 简单关键词匹配
    matched_topics = []

    for topic, data in KNOWLEDGE_BASE.items():
        for question in data["问题"]:
            if question in query_lower:
                if topic not in matched_topics:
                    matched_topics.append(topic)
                    answer = data["答案"]
                    sources.append(SourceReference(
                        document_id=f"doc{hash(topic) % 10:03d}",
                        document_title=data["来源"],
                        section=data["来源"].split(" ")[0],
                        content_preview=data["答案"][:100] + "..."
                    ))

    # 如果没有匹配，返回默认回复
    if not matched_topics:
        answer = "抱歉，根据现有文档未找到相关信息。您可以尝试以下问题：\n\n- 产假有多少天？\n- 差旅报销流程是什么？\n- 如何申请年假？\n- 办公用品怎么申领？\n- 社保公积金缴纳比例是多少？"

    return answer, sources


def get_suggested_questions(query: str) -> List[str]:
    """获取建议问题"""
    # 基于用户查询提供建
    suggestions = []

    if "考勤" in query or "迟到" in query:
        suggestions = ["上班时间是怎样的？", "迟到会扣工资吗？", "请假扣款怎么算？"]
    elif "报销" in query:
        suggestions = ["发票有什么要求？", "住宿费标准是多少？", "审批需要几天？"]
    elif "年假" in query or "请假" in query:
        suggestions = ["年假有多少天？", "申请流程是怎样的？", "工资怎么发？"]
    elif "薪酬" in query or "工资" in query:
        suggestions = ["发放时间是什么时候？", "绩效奖金怎么算？", "社保公积金怎么交？"]
    elif "办公" in query or "用品" in query or "会议室" in query or "用车" in query:
        suggestions = ["怎么申请办公用品？", "会议室怎么预订？", "出差用车怎么申请？"]
    else:
        suggestions = ["产假有多少天？", "差旅报销流程是什么？", "如何申请年假？"]

    return suggestions[:3]


# ===== API路由 =====


@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "EnterpriseKB API (Demo)",
        "version": "1.0.0",
        "docs": "/docs",
        "features": {
            "intelligent_qa": "基于RAG技术的智能问答",
            "source_tracing": "支持引用溯源",
            "multi_turn_chat": "支持多轮对话",
            "permission_control": "RBAC权限管理",
            "wechat_bot": "企业微信集成"
        }
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "api": "running",
            "database": "mock (using in-memory)",
            "rag": "mock (using local knowledge base)",
            "llm": "mock (not integrated)",
            "vector_db": "mock (not integrated)",
            "search": "mock (not integrated)",
            "wechat": "mock (not integrated)"
        }
    }


@app.get("/users", response_model=List[User])
async def list_users():
    """获取用户列表"""
    return MOCK_USERS


@app.get("/users/me", response_model=User)
async def get_current_user():
    """获取当前用户（模拟）"""
    return MOCK_USERS[0]


@app.get("/documents", response_model=List[Document])
async def list_documents():
    """获取文档列表"""
    return MOCK_DOCUMENTS


@app.post("/api/v1/auth/login")
async def login(request: ChatRequest):
    """用户登录（模拟）"""
    return {
        "access_token": "mock_jwt_token_xxx",
        "refresh_token": "mock_refresh_token_xxx",
        "token_type": "bearer",
        "user": MOCK_USERS[0]
    }


@app.post("/api/v1/chat/query")
async def chat_query(request: ChatRequest):
    """
    对话查询（核心功能）
    """
    query = request.query
    logger.info(f"Query: {query}")

    # 模拟处理延迟
    import asyncio
    await asyncio.sleep(0.5)

    # 搜索知识库
    answer, sources = search_knowledge(query)

    # 获取建议问题
    suggested = get_suggested_questions(query)

    return ChatResponse(
        answer=answer,
        sources=sources,
        suggested_questions=suggested
    )


@app.post("/api/v1/chat/feedback")
async def submit_feedback():
    """提交反馈（模拟）"""
    return {"message": "反馈提交成功"}


@app.get("/api/v1/chat/suggestions")
async def get_suggestions():
    """获取预设问题"""
    return {
        "questions": [
            "产假有多少天？",
            "差旅报销流程是什么？",
            "如何申请年假？",
            "办公用品怎么申领？",
            "社保公积金缴纳比例是多少？",
            "加班费如何计算？",
            "员工离职流程是什么？",
            "公司考勤制度是怎样的？"
        ]
    }


@app.get("/api/v1/conversations")
async def list_conversations():
    """获取对话列表（模拟）"""
    return {
        "conversations": [
            {
                "id": "conv1",
                "title": "关于考勤的咨询",
                "created_at": "2024-01-15T10:30:00",
                "updated_at": "2024-01-15T14:20:00",
                "message_count": 3
            },
            {
                "id": "conv2",
                "title": "报销相关咨询",
                "created_at": "2024-01-16T09:15:00",
                "updated_at": "2024-01-16T11:45:00",
                "message_count": 5
            }
        ]
    }


# ===== 启动命令 =====
if __name__ == "__main__":
    import uvicorn

    print("=" * 50)
    print("EnterpriseKB API (Demo Version)")
    print("=" * 50)
    print()
    print("功能特性：")
    print("  ✓ 智能问答（基于模拟知识库）")
    print("  ✓ 引用溯源")
    print("  ✓ 预设问题")
    print("  ✓ 多轮对话（模拟）")
    print("  ✓ 反馈机制（模拟）")
    print()
    print("API文档: http://localhost:8000/docs")
    print("健康检查: http://localhost:8000/health")
    print()
    print("=" * 50)

    uvicorn.run(
        "app.main_simple:app",
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
