import os
import ssl
import http
import requests
import socket
from urllib import error

from langchain_huggingface.embeddings import HuggingFaceEmbeddings
from langchain_core.runnables import RunnablePassthrough
from langchain_chroma import Chroma
from langchain_ollama.llms import OllamaLLM
from langchain_core.output_parsers import StrOutputParser
from langchain.prompts import PromptTemplate
from langchain_community.document_loaders import WebBaseLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from notes.models import Note

class NotesAssistant():

    vs = None
    llm = None
    llm_model = "llama3.2:latest"
    collection_name = "notes"
    embedding_model = "sentence-transformers/all-mpnet-base-v2"
    vs_data_dir = "./vs-data"
    chunk_size = 1000
    chunk_overlap = 200

    def __init__(self):
        self.vs = Chroma(
            collection_name=self.collection_name,
            embedding_function=HuggingFaceEmbeddings(model_name=self.embedding_model),
            persist_directory=self.vs_data_dir
        )

    def load_url(self,url):
        try:
            loader = WebBaseLoader(web_paths=(url,), )
            docs = loader.load()
            text_splitter = RecursiveCharacterTextSplitter(chunk_size=self.chunk_size, chunk_overlap=self.chunk_overlap)
            splits = text_splitter.split_documents(docs)
            print("added")
            return True, splits
        except (ssl.CertificateError,
                http.client.RemoteDisconnected,
                ConnectionResetError,
                socket.timeout,
                http.client.BadStatusLine,
                error.URLError,
                error.HTTPError,
                requests.exceptions.ConnectTimeout,
                socket.gaierror):
            print("failed to connect to {}".format(url))
            return False, None

    def init_chat(self):
        self.llm = OllamaLLM(model=self.llm_model, temperature=0)

    def pre_populate(self):
        # get all urls
        notes = Note.objects.filter(url__isnull=False)
        for note in notes:
            self.add_note(note.url)

    def add_note(self, url):
        success, splits = self.load_url(url)
        if success:
            self.vs.add_documents(splits)

    def get_prompt_template(self, template):
        with os.open("./prompttemplates/"+ template + ".txt") as file:
            return file.read_lines()

    def format_docs(docs):
        return "\n\n".join(doc.page_content for doc in docs)

    def query(self, question, template='recommend'):
        rag_prompt = PromptTemplate.from_template(self.get_prompt_template(template))
        retriever = self.vs.as_retriever(search_type="similarity")
        retrieved_docs = retriever.invoke(question)

        rag_chain = (
                {"context": retriever | self.format_docs, "question": RunnablePassthrough()}
                | rag_prompt
                | self.llm
                | StrOutputParser()
        )

        return rag_chain.invoke(question)