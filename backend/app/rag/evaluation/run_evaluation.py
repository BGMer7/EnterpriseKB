"""
RAG评估示例脚本
展示如何使用RAGAS评估RAG系统
"""
import sys
import os
import asyncio

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.rag.evaluation import RAGEvaluator
from app.rag.evaluation.models import EvaluationSample
from app.rag.pipeline import RAGPipeline


# 示例评估数据集
SAMPLE_DATASET = [
    EvaluationSample(
        question="公司年假是怎么计算的？",
        answer="公司年假按照员工入职年限计算：入职满1年不满10年的，年休假5天；满10年不满20年的，年休假10天；满20年的，年休假15天。",
        contexts=[
            "【文档1】员工手册\n来源：第一章 考勤制度\n页码：5\n内容：年假按工龄计算，入职满1年不满10年享受5天年假，满10年不满20年享受10天，满20年享受15天。",
            "【文档2】考勤管理制度\n来源：第二章 假期规定\n页码：12\n内容：年假需提前一个月向部门主管申请，经审批后生效。"
        ],
        ground_truth="公司年假按入职年限计算：1-10年5天，10-20年10天，20年以上15天。"
    ),
    EvaluationSample(
        question="报销流程需要多长时间？",
        answer="一般报销流程需要3-5个工作日完成审批，特殊情况下可能需要更长时间。",
        contexts=[
            "【文档1】财务报销制度\n来源：第三章 报销流程\n页码：8\n内容：普通报销申请提交后，财务部门将在3-5个工作日内完成审核和付款。"
        ],
        ground_truth="报销流程通常3-5个工作日完成。"
    ),
    EvaluationSample(
        question="加班工资如何计算？",
        answer="工作日加班按基本工资的1.5倍计算，休息日加班按2倍计算，法定节假日加班按3倍计算。",
        contexts=[
            "【文档1】薪酬福利制度\n来源：第四章 加班工资\n页码：15\n内容：工作日加班按照基本工资的150%支付，休息日加班按200%支付，法定节假日加班按300%支付。"
        ],
        ground_truth="加班工资：工作日1.5倍，休息日2倍，节假日3倍。"
    ),
    EvaluationSample(
        question="如何申请离职？",
        answer="员工需要提前30天提交书面离职申请，经部门负责人和人力资源部审批后完成离职手续。",
        contexts=[
            "【文档1】员工手册\n来源：第八章 离职管理\n页码：25\n内容：试用期员工提前3天提交申请，正式员工提前30天提交书面离职申请。"
        ],
        ground_truth="正式员工需提前30天书面申请离职。"
    ),
    EvaluationSample(
        question="公司有哪些福利？",
        answer="公司提供五险一金、带薪年假、节日福利、定期体检等。",
        contexts=[
            "【文档1】员工手册\n来源：第六章 福利待遇\n页码：18\n内容：公司为员工缴纳五险一金，提供带薪年假、节日礼品、定期健康体检等福利。"
        ],
        ground_truth="福利包括五险一金、带薪年假、节日福利、体检等。"
    ),
]


async def run_evaluation():
    """运行评估示例"""
    print("=" * 60)
    print("RAG系统评估示例")
    print("=" * 60)

    # 初始化评估器
    evaluator = RAGEvaluator()

    # 方式1：直接评估样本
    print("\n[1] 评估预设样本...")
    results = evaluator.evaluate_samples(SAMPLE_DATASET)

    # 打印汇总指标
    metrics = results["metrics"]
    print(f"\n评估指标汇总:")
    print(f"  - 样本数量: {metrics.total_samples}")
    print(f"  - 有检索结果的样本: {metrics.samples_with_context}")
    print(f"  - 无检索结果的样本: {metrics.samples_without_context}")
    print(f"  - 平均 Faithfulness: {metrics.avg_faithfulness:.4f}" if metrics.avg_faithfulness else "  - 平均 Faithfulness: N/A")
    print(f"  - 平均 Answer Relevancy: {metrics.avg_answer_relevancy:.4f}" if metrics.avg_answer_relevancy else "  - 平均 Answer Relevancy: N/A")
    print(f"  - 平均 Context Precision: {metrics.avg_context_precision:.4f}" if metrics.avg_context_precision else "  - 平均 Context Precision: N/A")
    print(f"  - 平均 Context Recall: {metrics.avg_context_recall:.4f}" if metrics.avg_context_recall else "  - 平均 Context Recall: N/A")

    # 打印每个样本的结果
    print("\n各样本评估结果:")
    for i, sample_result in enumerate(results["samples"]):
        print(f"\n  问题: {sample_result.question[:30]}...")
        if sample_result.faithfulness is not None:
            print(f"    Faithfulness: {sample_result.faithfulness:.4f}")
        if sample_result.answer_relevancy is not None:
            print(f"    Answer Relevancy: {sample_result.answer_relevancy:.4f}")
        if sample_result.context_precision is not None:
            print(f"    Context Precision: {sample_result.context_precision:.4f}")
        print(f"    检索结果数: {sample_result.retrieval_count}")

    # 保存结果
    output_path = os.path.join(os.path.dirname(__file__), "evaluation_results.json")
    evaluator.save_results(results, output_path)
    print(f"\n评估结果已保存到: {output_path}")

    # 方式2：从RAG Pipeline评估（需要完整的RAG系统）
    print("\n" + "=" * 60)
    print("[2] 从RAG Pipeline评估")
    print("=" * 60)

    # 这里展示如何使用Pipeline结果进行评估
    # 实际使用时需要传入真实的query、answer和contexts

    # 示例：评估单个查询
    test_query = "年假怎么计算？"
    test_answer = "入职满1年不满10年的，年休假5天..."
    test_contexts = [
        "年假按工龄计算，入职满1年不满10年享受5天年假..."
    ]

    single_result = evaluator.evaluate_from_rag_result(
        question=test_query,
        answer=test_answer,
        contexts=test_contexts,
        ground_truth="1-10年5天年假"
    )

    print(f"\n单次评估结果:")
    print(f"  问题: {single_result.question}")
    print(f"  Faithfulness: {single_result.faithfulness}")
    print(f"  Answer Relevancy: {single_result.answer_relevancy}")


if __name__ == "__main__":
    asyncio.run(run_evaluation())
