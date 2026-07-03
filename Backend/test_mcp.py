from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    model="Qwen/Qwen2.5-72B-Instruct-AWQ",
    api_key="dummy",
    base_url="http://127.0.0.1:8001/v1",
)

print(llm.invoke("Hello"))