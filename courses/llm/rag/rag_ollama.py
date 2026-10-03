import re
import os
import time
from typing import List, Dict, Any
from langchain_community.document_loaders import (
    WebBaseLoader,
    Docx2txtLoader
)
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.prompts import ChatPromptTemplate
from langchain.schema.runnable import RunnablePassthrough
from langchain.schema.output_parser import StrOutputParser
from langchain_ollama import OllamaLLM
from langchain_chroma import Chroma
from langchain_community.retrievers import BM25Retriever
from langchain.retrievers import EnsembleRetriever
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.docstore.document import Document

# 设置用户代理
os.environ["USER_AGENT"] = "OSExpertRAG/1.0"

# 操作系统专业术语映射表
OS_TERMS_MAPPING = {
    "操作系统": ["OS", "Operating System"],
    "进程管理": ["Process Management", "任务调度", "进程控制块"],
    "存储器管理": ["Memory Management", "虚拟内存", "页面置换算法"],
    "文件管理": ["File System", "目录结构", "文件控制块"],
    "设备管理": ["Device Management", "I/O控制", "缓冲技术"],
    "并发控制": ["Concurrency Control", "信号量", "管程"],
    "实时系统": ["Real-time System", "硬实时任务", "软实时任务"],
    "分布式系统": ["Distributed System", "透明性", "一致性协议"]
}


class SecurityValidator:
    """安全验证模块"""

    def __init__(self):
        self.danger_patterns = [
            r"(?i)(sudo|rm -rf|drop table|alter table)",  # 危险系统命令
            r"(https?://\S+|<\s*script)",  # 外部链接/脚本
            r"(修改成绩|考试答案|索要隐私|非法攻击)"  # 教育/安全敏感词
        ]

    def detect_injection(self, text: str) -> bool:
        for pattern in self.danger_patterns:
            if re.search(pattern, text):
                return True
        return False


class SecurityProcessor:
    """安全处理模块"""

    def __init__(self):
        self.validator = SecurityValidator()
        self.patterns = {
            'phone': r'\b1[3-9]\d{9}\b',
            'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        }

    def anonymize(self, text: str) -> str:
        """敏感信息脱敏"""
        for key, pattern in self.patterns.items():
            text = re.sub(pattern, f'[{key}_MASKED]', text)
        return text

    def validate_query(self, query: str) -> bool:
        """查询合法性验证"""
        return not self.validator.detect_injection(query)


class OSTermsEnhancer:
    """专业术语增强器"""

    def __init__(self, terms_map: Dict[str, List[str]] = None):
        self.terms_map = terms_map or OS_TERMS_MAPPING

    def enhance(self, query: str) -> str:
        """扩展查询术语"""
        for term, aliases in self.terms_map.items():
            if term in query:
                query += f" ({'|'.join(aliases)})"
        return query


class OSExpertRAG:
    """操作系统专家RAG系统"""

    def __init__(self, doc_path: str):
        self.doc_path = doc_path
        self.security = SecurityProcessor()
        self.terms_enhancer = OSTermsEnhancer()
        self.chunks = self._load_and_split()
        self.vector_store, self.retriever = self._setup_retrieval()
        self.llm = OllamaLLM(model="qwen2:7b-instruct-q4_0", temperature=0.1)
        self.rag_chain = self._build_chain()

    def _load_and_split(self) -> List[Document]:
        """加载并分块文档"""
        loader = Docx2txtLoader(self.doc_path)
        documents = loader.load()

        # 脱敏处理
        for doc in documents:
            doc.page_content = self.security.anonymize(doc.page_content)

        # 中文优化分块
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=800,
            chunk_overlap=100,
            separators=["\n\n", "\n", "。", "；", "•"]
        )
        return text_splitter.split_documents(documents)

    def _setup_retrieval(self):
        """设置检索系统"""
        embeddings = HuggingFaceEmbeddings(model_name="BAAI/bge-small-zh-v1.5")
        vector_store = Chroma.from_documents(
            self.chunks, embedding=embeddings, persist_directory="./os_db"
        )

        bm25_retriever = BM25Retriever.from_documents(self.chunks)
        ensemble_retriever = EnsembleRetriever(
            retrievers=[bm25_retriever, vector_store.as_retriever()],
            weights=[0.3, 0.7]
        )
        return vector_store, ensemble_retriever

    def _build_chain(self):
        """构建RAG链"""
        prompt = ChatPromptTemplate.from_template("""
[操作系统专家模式]
请根据以下上下文，专业地回答问题。回答需：
1. 使用标准术语（如进程、虚拟内存、SPOOLing技术）
2. 分点结构化呈现
3. 优先使用上下文中的知识

上下文：{context}
问题：{question}

专业解答：
""")

        return (
                {"context": self.retriever, "question": RunnablePassthrough()}
                | prompt
                | self.llm
                | StrOutputParser()
        )

    def query(self, question: str) -> str:
        """安全查询入口"""
        if not self.security.validate_query(question):
            return "❌ 安全警告：请求包含风险内容"

        enhanced_question = self.terms_enhancer.enhance(question)
        try:
            return self.rag_chain.invoke(enhanced_question)
        except Exception as e:
            return f"🚫 系统错误：{str(e)}"


# ======================
# 使用示例
# ======================
if __name__ == "__main__":
    # 替换为你的操作系统教材路径
    DOC_PATH = "100.docx"

    # 初始化RAG系统
    os_rag = OSExpertRAG(DOC_PATH)

    # 操作系统核心问题集
    questions = [
        "试说明什么是操作系统，其具有什么特征？其最基本特征是什么？",
        "设计现代操作系统的主要目标是什么？",

    ]

    # 执行查询
    for idx, q in enumerate(questions, 1):
        print(f"\n==== 问题 {idx} ====")
        print(f"提问：{q}")
        print("回答：")
        print(os_rag.query(q))
        print("-" * 50)