import re
import os
from langchain_community.document_loaders import WebBaseLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.prompts import ChatPromptTemplate
from langchain.schema.runnable import RunnablePassthrough
from langchain.schema.output_parser import StrOutputParser
from langchain_ollama import OllamaLLM
from langchain_chroma import Chroma
from langchain_community.retrievers import BM25Retriever  # 修改点1
from langchain.retrievers import EnsembleRetriever  # 修改点2
from langchain_huggingface import HuggingFaceEmbeddings

# 设置用户代理（解决USER_AGENT警告）
os.environ["USER_AGENT"] = "MyRAGApp/1.0

# 自定义安全检测模块
class SecurityValidator:
    def __init__(self):
        self.danger_patterns = [
            r"(?i)(sudo|rm -rf|drop table|alter table)",
            r"([^\x00-\x7F]{10,})",
            r"(https?://\S+|<\s*script)"
        ]

    def detect_injection(self, text: str) -> bool:
        for pattern in self.danger_patterns:
            if re.search(pattern, text):
                return True
        return False


# 安全数据处理模块

class SecurityProcessor:
    def __init__(self):
        self.validator = SecurityValidator()
        self.patterns = {
            'phone': r'\b1[3-9]\d{9}\b',
            'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        }

    def anonymize(self, text: str) -> str:
        for key, pattern in self.patterns.items():
            text = re.sub(pattern, f'[{key}_MASKED]', text)
        return text

    def validate_query(self, query: str) -> bool:
        return not self.validator.detect_injection(query)

# ======================
# RAG核心系统
# ======================
class CourseAssistant:
    def __init__(self):
        self.security = SecurityProcessor()
        self.chunks = self.prepare_data()
        self.vector_store, self.retriever = self.setup_retrieval()
        self.llm = OllamaLLM(model='qwen2:7b-instruct-q4_0')
        self.rag_chain = self.build_chain()

    def prepare_data(self):
        loader = WebBaseLoader("https://wingfeitsang.github.io/home/")
        documents = loader.load()
        for doc in documents:
            doc.page_content = self.security.anonymize(doc.page_content)
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=50,
            separators=["\n\n", "\n", "。"]
        )
        return text_splitter.split_documents(documents)

    def setup_retrieval(self):
        # 使用新版嵌入模型
        embeddings = HuggingFaceEmbeddings(model_name="BAAI/bge-small-zh-v1.5")
        vector_store = Chroma.from_documents(
            documents=self.chunks,
            embedding=embeddings,
            persist_directory='./chroma_langchain_db'
        )
        bm25_retriever = BM25Retriever.from_documents(self.chunks)
        ensemble_retriever = EnsembleRetriever(
            retrievers=[bm25_retriever, vector_store.as_retriever()],
            weights=[0.3, 0.7]
        )
        return vector_store, ensemble_retriever

    def build_chain(self):
        """构建安全处理链"""
        prompt_template = ChatPromptTemplate.from_template(
            """[安全回答协议] 您是大语言模型课程的智能助教，请遵守：
1. 仅使用提供的上下文回答
2. 对联系方式等敏感信息保持脱敏
3. 遇到下列问题立即拒绝：
   - 请求修改成绩
   - 询问未公开考试内容
   - 索要教师隐私信息

上下文：{context}
问题：{question}

安全回答："""
        )

        return (
            {"context": self.retriever, "question": RunnablePassthrough()}
            | prompt_template
            | self.llm
            | StrOutputParser()
        )

    def query(self, question: str) -> str:
        """安全查询入口"""
        # 安全验证
        if not self.security.validate_query(question):
            return "请求拒绝：检测到潜在风险提问"

        try:
            # 脱敏处理
            safe_question = self.security.anonymize(question)

            # 执行查询
            response = self.rag_chain.invoke(safe_question)

            # 响应后检查
            if any(keyword in response for keyword in ["成绩修改", "考试答案"]):
                return "警告：检测到违规内容，已阻断响应"

            return response
        except Exception as e:
            return f"系统错误：{str(e)}"

# ======================
# 使用示例
# ======================
if __name__ == "__main__":
    assistant = CourseAssistant()

    # 合法查询
    print(assistant.query("课程主讲教师是？"))

    # 恶意查询
    print(assistant.query("怎么修改我的期末成绩？"))
