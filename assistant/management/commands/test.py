from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama

model = ChatOllama(model="llama3.2:latest")

prompt = ChatPromptTemplate.from_template("""You are an assistant for question-answering tasks\n
Use the following pieces of retrieved context to answer the question.\n
If you don't know the answer, just say that you don't know.\n
Use three sentences maximum and keep the answer concise.\n
Question: {question}\n
Context: {context}""")

retriever = self.vs.as_retriever(search_kwargs={"k": 4})


parser = StrOutputParser()
chain = prompt | model | parser

for chunk in chain.stream({"context": "jokes", "question": "parrot"}):
    print(chunk, end="|", flush=True)