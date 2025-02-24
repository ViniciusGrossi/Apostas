from dotenv import load_dotenv
import os
import psycopg2
import requests
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.vectorstores import FAISS
from langchain_core.runnables import RunnablePassthrough
from langchain_core.documents import Document
import streamlit as st
import time

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

# Configuração das credenciais a partir do .env
DATABASE_URL = os.getenv("DATABASE_URL")
DEEPSEEK_API = os.getenv("DEEPSEEK_API")
API_URL = os.getenv("API_URL")

# Verifica se o pacote sentence-transformers está instalado
try:
    from langchain_community.embeddings import HuggingFaceEmbeddings
except ImportError:
    st.error("O pacote `sentence-transformers` não está instalado. Instale-o com `pip install sentence-transformers`.")
    st.stop()

# Função para conectar ao banco de dados e carregar os dados
@st.cache_data(ttl=300, show_spinner="Carregando dados atualizados...")
def load_data_from_supabase():
    if not DATABASE_URL:
        st.error("Variável de ambiente DATABASE_URL não definida.")
        return []
    
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM apostas")
        columns = [desc[0] for desc in cursor.description]
        data = cursor.fetchall()
        
        documents = []
        for row in data:
            try:
                content = ", ".join([f"{columns[i]}: {row[i]}" for i in range(len(columns))])
                doc = Document(
                    page_content=content,
                    metadata={"id": row[0]}
                )
                documents.append(doc)
            except Exception as e:
                print(f"Erro na linha {row}: {e}")  # Log de erro no console
        
        cursor.close()
        conn.close()
        return documents
    
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        return []

# Carrega os dados e cria o vetorstore (mantido igual)
documents = load_data_from_supabase()
embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
vectorstore = FAISS.from_documents(documents, embeddings)
vectorstore.save_local("faiss_index")
retriever = vectorstore.as_retriever(search_kwargs={"k": 150})
# Função para chamar a API do DeepSeek
def call_deepseek_api(messages):
    st.write(f"API Key: {DEEPSEEK_API}")
    st.write(f"API URL: {API_URL}")
    headers = {
    "Authorization": f"Bearer {DEEPSEEK_API}",  # Ou "Token" conforme documentação
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

# Template do sistema RAG
system_prompt = """
Você é um especialista em apostas de futebol. Use estas informações:
{context}

Histórico da conversa:
{history}

Responda de forma precisa e detalhada à pergunta atual:
"""

# Interface do Streamlit
st.title("Agente de IA para Apostas Esportivas")

with st.sidebar:
    st.header("Configurações do Chat")
    
    # Botão para apagar histórico
    st.subheader("Gerenciar Histórico")
    if st.button("🧹 Apagar Todas as Conversas"):
        # Confirmação antes de apagar
        confirmacao = st.checkbox("Confirmar exclusão permanente de todo o histórico")
        if confirmacao:
            st.session_state.messages = [{
                "role": "assistant",
                "content": "Olá! Sou seu especialista em apostas. Como posso ajudar?"
            }]
            st.success("Histórico de conversas apagado com sucesso!")
            st.rerun()
        else:
            st.warning("Marque a caixa de confirmação para apagar")
with st.sidebar:
    if st.button("🔄 Atualizar Dados do Zero", type="primary"):
        st.cache_data.clear()
        st.success("Cache limpo! Recarregando...")
        time.sleep(2)
        st.rerun()

# Inicializa o histórico
if "messages" not in st.session_state:
    st.session_state.messages = [{
        "role": "assistant",
        "content": "Olá! Sou seu especialista em apostas. Como posso ajudar?"
    }]

# Exibe histórico
for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

# Input da pergunta
if question := st.chat_input("Faça uma pergunta sobre suas apostas:"):
    # Busca contexto relevante
    context_docs = retriever.get_relevant_documents(question)
    context = "\n".join([f"Aposta ID {doc.metadata['id']}: {doc.page_content}" for doc in context_docs])
    
    # Formata histórico
    history = "\n".join(
        [f"{m['role'].capitalize()}: {m['content']}" 
         for m in st.session_state.messages[:-1]]
    )
    
    # Cria prompt completo
    full_prompt = system_prompt.format(
        context=context,
        history=history
    ) + f"\n\nPergunta atual: {question}"
    
    # Monta mensagens para API
    messages = [
        {"role": "system", "content": full_prompt},
        {"role": "user", "content": question}
    ]
    
    # Adiciona ao histórico e exibe
    st.session_state.messages.append({"role": "user", "content": question})
    st.chat_message("user").write(question)
    
    # Obtém resposta
    response = call_deepseek_api(messages)
    
    # Adiciona e exibe resposta
    st.session_state.messages.append({"role": "assistant", "content": response})
    st.chat_message("assistant").write(response)
    