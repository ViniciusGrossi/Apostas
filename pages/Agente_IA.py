from dotenv import load_dotenv
import os
import psycopg2
import requests
import streamlit as st
import time
import torch
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.runnables import RunnablePassthrough

# Carrega variáveis de ambiente
load_dotenv()

# Credenciais e configurações
DATABASE_URL = os.getenv("DATABASE_URL")
DEEPSEEK_API = os.getenv("DEEPSEEK_API")
API_URL = os.getenv("API_URL")

st.set_page_config(page_title="Agente de IA para Apostas", layout="wide")
torch.classes.__path__ = []
# Função para carregar dados do Supabase
def load_data():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM apostas")
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        docs = []
        for row in rows:
            content = ", ".join([f"{columns[i]}: {row[i]}" for i in range(len(columns))])
            docs.append(Document(page_content=content, metadata={"id": row[0]}))
        cursor.close()
        conn.close()
        return docs
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        return []

# Carrega documentos e cria o vectorstore
documents = load_data()
embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
vectorstore = FAISS.from_documents(documents, embeddings)
retriever = vectorstore.as_retriever(search_kwargs={"k": 150})

# Função para chamar a API do DeepSeek
def call_deepseek_api(messages):
    headers = {
        "Authorization": f"Token {DEEPSEEK_API}",  # Alterado para "Token" em vez de "Bearer"
        "Content-Type": "application/json"
    }
    payload = {
        "model": "deepseek/deepseek-chat:free",
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 1000
    }
    try:
        response = requests.post(API_URL, json=payload, headers=headers)
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
        return f"Erro na API: {response.text}"
    except Exception as e:
        return f"Erro na conexão: {str(e)}"


# Template do prompt do sistema
system_prompt = """
Você é um especialista em apostas de futebol. Use estas informações:
{context}

Histórico da conversa:
{history}

Responda de forma precisa e detalhada à pergunta atual:
"""

# Inicializa o histórico de mensagens
if "messages" not in st.session_state:
    st.session_state.messages = [{
        "role": "assistant",
        "content": "Olá! Sou seu especialista em apostas. Como posso ajudar?"
    }]

st.title("Agente de IA para Apostas")

# Exibe o histórico do chat
for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

# Input da pergunta
question = st.chat_input("Faça uma pergunta sobre suas apostas:")
if question:
    # Busca documentos relevantes
    context_docs = retriever.invoke(question)  # Se invoke() não funcionar, use get_relevant_documents(question)
    context = "\n".join([f"Aposta ID {doc.metadata['id']}: {doc.page_content}" for doc in context_docs])
    history = "\n".join([f"{m['role'].capitalize()}: {m['content']}" for m in st.session_state.messages[:-1]])
    full_prompt = system_prompt.format(context=context, history=history) + f"\n\nPergunta atual: {question}"
    
    # Monta as mensagens para a API
    messages = [
        {"role": "system", "content": full_prompt},
        {"role": "user", "content": question}
    ]
    
    # Adiciona a pergunta ao histórico e chama a API
    st.session_state.messages.append({"role": "user", "content": question})
    st.chat_message("user").write(question)
    response = call_deepseek_api(messages)
    st.session_state.messages.append({"role": "assistant", "content": response})
    st.chat_message("assistant").write(response)
