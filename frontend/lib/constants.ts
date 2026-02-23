/**
 * 常量定义
 */
export const SUGGESTED_QUESTIONS = [
  "产假有多少天？",
  "差旅报销流程是什么？",
  "如何申请年假？",
  "办公用品怎么申领？",
  "社保公积金缴纳比例是多少？",
  "加班费如何计算？",
  "员工离职流程是什么？",
  "公司考勤制度是怎样的？",
];

export const DOCUMENT_STATUS = {
  DRAFT: "draft",
  REVIEWING: "reviewing",
  PUBLISHED: "published",
  REJECTED: "rejected",
} as const;

export const DOCUMENT_STATUS_LABEL = {
  [DOCUMENT_STATUS.DRAFT]: "草稿",
  [DOCUMENT_STATUS.REVIEWING]: "审核中",
  [DOCUMENT_STATUS.PUBLISHED]: "已发布",
  [DOCUMENT_STATUS.REJECTED]: "已拒绝",
};

export const FILE_TYPES = {
  PDF: "pdf",
  DOCX: "docx",
  XLSX: "xlsx",
  TXT: "txt",
  MD: "md",
} as const;

export const FILE_TYPE_LABEL = {
  [FILE_TYPES.PDF]: "PDF文档",
  [FILE_TYPES.DOCX]: "Word文档",
  [FILE_TYPES.XLSX]: "Excel表格",
  [FILE_TYPES.TXT]: "文本文档",
  [FILE_TYPES.MD]: "Markdown文档",
};

export const MAX_FILE_SIZE = 50 * 1024 * 1024; // 50MB
