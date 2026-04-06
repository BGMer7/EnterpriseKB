"""
RAG 评估命令行工具
运行方式: cd到backend目录，然后 python app/rag/evaluation/run_evaluation_cli.py
或: cd到backend目录，然后 python -m app.rag.evaluation.run_evaluation_cli
"""
import sys
import os

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, project_root)

from app.rag.evaluation import RAGEvaluator, EvaluationSample


# 示例评估数据集
SAMPLE_DATASET = [
    EvaluationSample(
        question="公司年假是怎么计算的？",
        answer="公司年假按照员工入职年限计算：入职满1年不满10年的，年休假5天；满10年不满20年的，年休假10天；满20年的，年休假15天。",
        contexts=[
            "年假按工龄计算，入职满1年不满10年享受5天年假，满10年不满20年享受10天，满20年享受15天。",
            "年假需提前一个月向部门主管申请，经审批后生效。"
        ],
        ground_truth="1-10年5天，10-20年10天，20年以上15天"
    ),
    EvaluationSample(
        question="报销流程需要多长时间？",
        answer="一般报销流程需要3-5个工作日完成审批。",
        contexts=[
            "普通报销申请提交后，财务部门将在3-5个工作日内完成审核和付款。"
        ],
        ground_truth="3-5个工作日"
    ),
    EvaluationSample(
        question="加班工资如何计算？",
        answer="工作日加班按基本工资的1.5倍计算，休息日加班按2倍计算，法定节假日加班按3倍计算。",
        contexts=[
            "工作日加班按照基本工资的150%支付，休息日加班按200%支付，法定节假日加班按300%支付。"
        ],
        ground_truth="工作日1.5倍，休息日2倍，节假日3倍"
    ),
]


def main():
    print("=" * 60)
    print("RAG 评估")
    print("=" * 60)

    # 初始化评估器（使用 settings 中的 LLM 配置）
    evaluator = RAGEvaluator()

    # 打印评估器配置
    print(f"\n[配置]")
    print(f"  LLM: {evaluator.llm_model}")
    print(f"  API URL: {evaluator.llm_api_url}")
    print(f"  Embeddings: {evaluator.embeddings_model}")

    # 打印每个样本的详细信息
    print(f"\n" + "=" * 60)
    print("评估数据详情")
    print("=" * 60)

    for i, sample in enumerate(SAMPLE_DATASET):
        print(f"\n--- 样本 {i+1} ---")
        print(f"问题: {sample.question}")
        print(f"RAG返回答案: {sample.answer}")
        print(f"检索到的上下文:")
        for j, ctx in enumerate(sample.contexts):
            print(f"  [上下文 {j+1}] {ctx[:150]}..." if len(ctx) > 150 else f"  [上下文 {j+1}] {ctx}")
        print(f"标准答案(Ground Truth): {sample.ground_truth}")

    # 评估样本
    print(f"\n" + "=" * 60)
    print("开始评估 - RAGAS 详细过程")
    print("=" * 60)

    print("""
评估指标说明:
  1. Faithfulness (忠实度)
     - 计算方式: 让LLM从答案中提取所有陈述，然后判断每个陈述是否能从上下文中推导出来
     - 公式: faithfulness = (有依据的陈述数) / (总陈述数)
     - 分数范围: 0-1，越高越好

  2. Answer Relevancy (答案相关性)
     - 计算方式: 让LLM根据答案生成多个相关问题，计算与原始问题的相似度
     - 公式: relevancy = 平均(生成问题与原始问题的相似度)
     - 分数范围: 0-1，越高越好

  3. Context Precision (上下文精确度)
     - 计算方式: 让LLM判断每个上下文片段与问题的相关程度
     - 公式: precision = 相关片段数 / 总片段数
     - 分数范围: 0-1，越高越好

  4. Context Recall (上下文召回率)
     - 计算方式: 让LLM判断上下文覆盖了多少标准答案中的信息
     - 公式: recall = 覆盖的标准答案信息数 / 标准答案总信息数
     - 分数范围: 0-1，越高越好（需要ground_truth）
""")

    print("\n" + "-" * 60)
    print("开始调用 LLM 进行评估...")
    print("-" * 60)

    # 逐个指标评估，显示过程
    print("\n>>> 指标1: Faithfulness (忠实度)")
    print("    目的: 检测答案是否基于检索到的上下文（是否有幻觉）")
    print("    LLM处理:")
    for i, sample in enumerate(SAMPLE_DATASET):
        print(f"\n    [样本 {i+1}] {sample.question}")
        print(f"    答案: {sample.answer[:80]}...")
        print(f"    上下文数量: {len(sample.contexts)}")
        print(f"    -> LLM会分析答案中的每个陈述是否能在上下文中找到依据")

    results = evaluator.evaluate_samples(SAMPLE_DATASET)

    print("\n>>> 指标2: Answer Relevancy (答案相关性)")
    print("    目的: 评估答案与问题的相关程度")
    print("    LLM处理:")
    for i, sample in enumerate(SAMPLE_DATASET):
        print(f"\n    [样本 {i+1}] {sample.question}")
        print(f"    -> LLM会根据答案生成多个问题，计算与原始问题的相似度")

    print("\n>>> 指标3: Context Precision (上下文精确度)")
    print("    目的: 评估检索内容与问题的相关程度")
    print("    LLM处理:")
    for i, sample in enumerate(SAMPLE_DATASET):
        print(f"\n    [样本 {i+1}] {sample.question}")
        for j, ctx in enumerate(sample.contexts):
            print(f"       上下文 {j+1}: {ctx[:60]}...")
        print(f"    -> LLM判断每个上下文与问题的相关度")

    print("\n>>> 指标4: Context Recall (上下文召回率)")
    print("    目的: 评估检索内容覆盖标准答案的程度")
    print("    LLM处理:")
    for i, sample in enumerate(SAMPLE_DATASET):
        if sample.ground_truth:
            print(f"\n    [样本 {i+1}] {sample.question}")
            print(f"    标准答案: {sample.ground_truth}")
            print(f"    上下文: {[c[:40]+'...' for c in sample.contexts]}")
            print(f"    -> LLM判断上下文覆盖了多少标准答案中的信息")

    # 打印每个样本的评估结果
    print(f"\n" + "=" * 60)
    print("各样本评估结果")
    print("=" * 60)

    for i, sample_result in enumerate(results["samples"]):
        sample = SAMPLE_DATASET[i]
        print(f"\n{'='*40}")
        print(f"样本 {i+1}: {sample.question}")
        print(f"{'='*40}")

        print(f"\n[输入]")
        print(f"  问题: {sample.question}")
        print(f"  答案: {sample.answer[:100]}...")
        print(f"  上下文: {sample.contexts}")
        print(f"  标准答案: {sample.ground_truth}")

        print(f"\n[评估过程]")

        # Faithfulness
        if sample_result.faithfulness is not None:
            print(f"  Faithfulness (忠实度): {sample_result.faithfulness:.4f}")
            print(f"    -> LLM从答案中提取陈述，验证每个陈述是否能在上下文找到依据")
            print(f"    -> 分数={sample_result.faithfulness:.4f} 表示答案完全基于上下文")
        else:
            print(f"  Faithfulness: N/A (评估失败)")

        # Answer Relevancy
        if sample_result.answer_relevancy is not None:
            print(f"  Answer Relevancy (答案相关性): {sample_result.answer_relevancy:.4f}")
            print(f"    -> LLM根据答案生成相关问题，计算与原始问题的相似度")
            print(f"    -> 分数={sample_result.answer_relevancy:.4f} 表示答案与问题高度相关")
        else:
            print(f"  Answer Relevancy: N/A (评估失败)")

        # Context Precision
        if sample_result.context_precision is not None:
            print(f"  Context Precision (上下文精确度): {sample_result.context_precision:.4f}")
            print(f"    -> 评估每个上下文与问题的相关程度")
            print(f"    -> 分数={sample_result.context_precision:.4f} 表示检索内容精准")
        else:
            print(f"  Context Precision: N/A (评估失败)")

        # Context Recall
        if sample_result.context_recall is not None:
            print(f"  Context Recall (上下文召回率): {sample_result.context_recall:.4f}")
            print(f"    -> 评估上下文覆盖标准答案信息的程度")
            print(f"    -> 分数={sample_result.context_recall:.4f} 表示检索内容全面")
        else:
            print(f"  Context Recall: N/A (无标准答案或评估失败)")

    # 打印汇总
    metrics = results["metrics"]
    print(f"\n" + "=" * 60)
    print("评估汇总")
    print("=" * 60)
    print(f"\n样本统计:")
    print(f"  总样本数: {metrics.total_samples}")
    print(f"  有检索结果的样本: {metrics.samples_with_context}")
    print(f"  无检索结果的样本: {metrics.samples_without_context}")

    print(f"\n平均指标:")
    if metrics.avg_faithfulness is not None:
        print(f"  Faithfulness (忠实度): {metrics.avg_faithfulness:.4f}")
        print(f"    -> 答案基于检索内容的程度，1.0为完全基于内容")
    else:
        print(f"  Faithfulness: N/A")

    if metrics.avg_answer_relevancy is not None:
        print(f"  Answer Relevancy (答案相关性): {metrics.avg_answer_relevancy:.4f}")
        print(f"    -> 答案与问题的相关程度，越接近1越好")
    else:
        print(f"  Answer Relevancy: N/A")

    if metrics.avg_context_precision is not None:
        print(f"  Context Precision (上下文精确度): {metrics.avg_context_precision:.4f}")
        print(f"    -> 检索内容与问题的相关程度，1.0为全部相关")
    else:
        print(f"  Context Precision: N/A")

    if metrics.avg_context_recall is not None:
        print(f"  Context Recall (上下文召回率): {metrics.avg_context_recall:.4f}")
        print(f"    -> 检索内容覆盖标准答案的程度")
    else:
        print(f"  Context Recall: N/A")

    # 保存结果
    output_path = os.path.join(os.path.dirname(__file__), "evaluation_results.json")
    evaluator.save_results(results, output_path)
    print(f"\n结果已保存到: {output_path}")


if __name__ == "__main__":
    main()
