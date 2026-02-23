"""
幻觉检测器
检查LLM回答中的事实是否符合检索到的上下文
"""
from typing import List, Dict, Any, Optional
import re


class HallucinationChecker:
    """
    幻觉检测器
    """

    @staticmethod
    def check_answer_facts(
        answer: str,
        context: str,
        results: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        检查答案中的事实是否在上下文中得到支持

        Args:
            answer: LLM生成的答案
            context: 检索到的上下文
            results: 检索结果列表

        Returns:
            Dict: {
                "is_factually_correct": bool,
                "confidence": float,
                "unsupported_statements": List[str],
                "details": List[Dict],
            }
        """
        # 提取答案中的陈述
        statements = HallucinationChecker._extract_statements(answer)

        if not statements:
            return {
                "is_factually_correct": True,
                "confidence": 1.0,
                "unsupported_statements": [],
                "details": []
            }

        # 检查每个陈述
        details = []
        unsupported_statements = []

        for statement in statements:
            support_score = HallucinationChecker._check_statement_support(
                statement=statement,
                context=context
            )

            details.append({
                "statement": statement,
                "supported": support_score >= 0.7,
                "confidence": support_score
            })

            if support_score < 0.7:
                unsupported_statements.append(statement)

        # 计算整体置信度
        avg_confidence = sum(d["confidence"] for d in details) / len(details) if details else 0

        return {
            "is_factually_correct": all(d["supported"] for d in details),
            "confidence": avg_confidence,
            "unsupported_statements": unsupported_statements,
            "details": details
        }

    @staticmethod
    def _extract_statements(text: str) -> List[str]:
        """
        从文本中提取陈述

        Args:
            text: 输入文本

        Returns:
            List[str]: 陈述列表
        """
        # 按句号、问号、感叹号分割
        sentences = re.split(r'[。？！?!.]', text)

        # 过滤空句和过短的句子
        statements = [s.strip() for s in sentences if len(s.strip()) > 5]

        return statements

    @staticmethod
    def _check_statement_support(
        statement: str,
        context: str
    ) -> float:
        """
        检查单个陈述是否在上下文中得到支持

        Args:
            statement: 陈述
            context: 上下文

        Returns:
            float: 支持度分数 [0, 1]
        """
        statement_lower = statement.lower()
        context_lower = context.lower()

        # 简单实现：基于关键词匹配
        # 提取陈述中的关键词
        keywords = HallucinationChecker._extract_keywords(statement)

        if not keywords:
            return 0.5  # 无法判断

        # 计算关键词在上下文中的出现情况
        matched_count = 0
        for keyword in keywords:
            if keyword in context_lower:
                matched_count += 1

        # 计算支持度
        support_ratio = matched_count / len(keywords)

        return support_ratio

    @staticmethod
    def _extract_keywords(text: str) -> List[str]:
        """
        提取关键词

        Args:
            text: 输入文本

        Returns:
            List[str]: 关键词列表
        """
        # 简单实现：提取非停用词的词汇
        # 去除标点和特殊字符
        text = re.sub(r'[^\w\s]', '', text)

        # 中文停用词
        stopwords = {
            "的", "了", "在", "是", "我", "有", "和", "就",
            "不", "人", "都", "一", "一个", "上", "也", "很",
            "到", "说", "要", "去", "你", "会", "着", "没有",
            "看", "好", "自己", "这",
            "the", "and", "or", "but", "in", "on", "at", "to",
            "a", "an", "is", "are", "was", "were"
        }

        # 分词（简单按空格分词，中文需要更复杂的处理）
        words = text.split()

        # 过滤停用词和短词
        keywords = [w for w in words if len(w) > 1 and w not in stopwords]

        return keywords

    @staticmethod
    def check_for_refusal(answer: str) -> bool:
        """
        检查回答是否为拒答

        Args:
            answer: LLM生成的答案

        Returns:
            bool: 是否为拒答
        """
        refusal_patterns = [
            "未找到相关信息",
            "没有相关信息",
            "不清楚",
            "无法确定",
            "抱歉，我无法回答"
        ]

        for pattern in refusal_patterns:
            if pattern in answer:
                return True

        return False
