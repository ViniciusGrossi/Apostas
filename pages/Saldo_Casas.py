import streamlit as st
import psycopg2
from dotenv import load_dotenv
import os
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import time

# Carrega variáveis de ambiente do arquivo .env
load_dotenv()

# Configuração da página
st.set_page_config(
    page_title="Saldo nas Casas de Aposta",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilo CSS personalizado
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        margin-bottom: 1rem;
        color: #2962FF;
        text-align: center;
    }
    .card {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 1.5rem;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        margin-bottom: 1rem;
    }
    .card-positivo {
        background-color: #E1F5FE;
        border-left: 5px solid #0288D1;
        color: #01579B;
    }
    .card-negativo {
        background-color: #E3F2FD;
        border-left: 5px solid #f44336;
        color: #f44336;
    }
    .card-neutro {
        background: linear-gradient(135deg, #bdc3c7, #95a5a6);
        border-left: 4px solid #7f8c8d;
        color: #2c3e50;
    }
    .big-number {
        font-size: 1.8rem;
        font-weight: 700;
    }
    .highlight-box {
        padding: 1.5rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        font-weight: bold;
    }
    .highlight-positive {
        background: linear-gradient(135deg, #4CAF50, #2E7D32);
    }
    .highlight-negative {
        background: linear-gradient(135deg, #1A237E, #0D47A1);
    }
    .highlight-neutral {
        background: linear-gradient(135deg, #42A5F5, #1565C0);
    }
    .section-title {
        font-size: 1.5rem;
        font-weight: 600;
        margin: 1.5rem 0 1rem 0;
        color: white;
        border-bottom: 2px solid #BBDEFB;
        padding-bottom: 0.5rem;
    }
    .filter-container {
        background-color: #E3F2FD;
        padding: 1rem;
        border-radius: 10px;
        margin-bottom: 1rem;
    }
    .stat-box {
        background-color: #ffffff;
        padding: 1rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        text-align: center;
    }
    .stat-value {
        font-size: 1.6rem;
        font-weight: 700;
        margin: 0.5rem 0;
        color: #0D47A1;
    }
    .stat-label {
        font-size: 0.9rem;
        color: #42A5F5;
    }
    .transaction-item {
        padding: 0.8rem;
        border-radius: 8px;
        margin-bottom: 0.5rem;
        border-left: 4px solid #1E88E5;
        background-color: #F5F9FF;
    }
    .success-message {
        padding: 1rem;
        background-color: #E1F5FE;
        border-left: 5px solid #4CAF50;
        border-radius: 5px;
        color: #01579B;
    }
    .error-message {
        padding: 1rem;
        background-color: #E8EAF6;
        border-left: 5px solid #3F51B5;
        border-radius: 5px;
        color: #1A237E;
    }
    .tab-content {
        padding: 1.5rem;
        background-color: #ffffff;
        border-radius: 0 10px 10px 10px;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
        border-top: 3px solid #2196F3;
    }
    .categoria-title {
        font-size: 1.3rem;
        font-weight: 600;
        color: white;
        margin: 1.5rem 0 0.5rem 0;
        padding-bottom: 0.3rem;
        border-bottom: 2px solid #ecf0f1;
    }
</style>
""", unsafe_allow_html=True)

# Função para conectar ao PostgreSQL utilizando a variável DATABASE_URL
@st.cache_resource
def init_db():
    try:
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            st.error("Variável de ambiente DATABASE_URL não definida")
            return None
        
        conn = psycopg2.connect(database_url)
        conn.autocommit = True
        # Cria tabela de saldos se não existir
        with conn.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS saldo_casas (
                    id SERIAL PRIMARY KEY,
                    casa_nome TEXT UNIQUE,
                    saldo NUMERIC(10,2) DEFAULT 0,
                    ultima_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Cria tabela de histórico
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS historico_saldos (
                    id SERIAL PRIMARY KEY,
                    data TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    casa_nome TEXT,
                    operacao TEXT,
                    valor NUMERIC(10,2),
                    observacao TEXT,
                    saldo_resultante NUMERIC(10,2)
                )
            """)
            
            # Verifica e adiciona coluna saldo_resultante se não existir
            cursor.execute("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 
                        FROM information_schema.columns 
                        WHERE table_name = 'historico_saldos' 
                        AND column_name = 'saldo_resultante'
                    ) THEN
                        ALTER TABLE historico_saldos
                        ADD COLUMN saldo_resultante NUMERIC(10,2);
                    END IF;
                END $$;
            """)

            # Cria tabela de metas
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS metas (
                    id SERIAL PRIMARY KEY,
                    titulo TEXT,
                    valor_alvo NUMERIC(10,2),
                    data_limite DATE,
                    concluida BOOLEAN DEFAULT FALSE,
                    data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.commit()
            
        return conn
    except Exception as e:
        st.error(f"Erro de conexão: {e}")
        return None

conn = init_db()

# Função para popular casas iniciais
def popular_casas_iniciais():
    casas = [
        'Bet 365', 'Betano', 'Betfair', 'Superbet', 'Estrela Bet', '4Play Bet', 'PixBet',
        'Novibet', 'Sporting Bet', 'Bet7k', 'Cassino Pix', 'KTO', 'Stake', 'BR Bet', 
        'Aposta tudo', 'Casa de Apostas', 'Vera Bet', 'Bateu Bet', 'Betnacional', 
        'Jogue Facil', 'Jogo de Ouro', 'Pagol', 'Seu Bet', 'Bet Esporte', 
        'BetFast', 'Faz1Bet', 'Esportiva Bet', 'Betpix365', 'Seguro Bet', 'Outros', 'Minha Conta'
    ]
    
    with conn.cursor() as cursor:
        for casa in casas:
            cursor.execute("""
                INSERT INTO saldo_casas (casa_nome, ultima_atualizacao)
                VALUES (%s, CURRENT_TIMESTAMP)
                ON CONFLICT (casa_nome) DO NOTHING
            """, (casa,))
        conn.commit()

# Função para obter dados formatados para visualização
def get_saldos_data():
    with conn.cursor() as cursor:
        cursor.execute("SELECT casa_nome, saldo, ultima_atualizacao FROM saldo_casas ORDER BY saldo DESC")
        resultados = cursor.fetchall()
        
    df = pd.DataFrame(resultados, columns=["Casa", "Saldo", "Última Atualização"])
    df["Saldo"] = pd.to_numeric(df["Saldo"], errors='coerce')
    df["Última Atualização"] = pd.to_datetime(df["Última Atualização"], errors='coerce')
    df["Última Atualização"] = df["Última Atualização"].fillna(pd.Timestamp('2023-01-01'))
    
    # Categorização das casas
    casas_positivas = df[df["Saldo"] > 0]
    casas_negativas = df[df["Saldo"] < 0]
    casas_neutras = df[df["Saldo"] == 0]
    
    total = df["Saldo"].sum()
    media = df["Saldo"].mean()
    
    return df, total, media, casas_positivas, casas_negativas, casas_neutras

# Função para obter histórico de transações
def get_historico(limit=100, casa=None, periodo=None):
    query = """
        SELECT h.id, h.data, h.casa_nome, h.operacao, h.valor, h.observacao, h.saldo_resultante
        FROM historico_saldos h
    """
    
    conditions = []
    params = []
    
    if casa and casa != "Todas":
        conditions.append("h.casa_nome = %s")
        params.append(casa)
    
    if periodo:
        if periodo == "Hoje":
            conditions.append("h.data >= CURRENT_DATE")
        elif periodo == "Última Semana":
            conditions.append("h.data >= CURRENT_DATE - INTERVAL '7 days'")
        elif periodo == "Último Mês":
            conditions.append("h.data >= CURRENT_DATE - INTERVAL '30 days'")
    
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    
    query += " ORDER BY h.data DESC"
    
    if limit:
        query += f" LIMIT {limit}"
    
    with conn.cursor() as cursor:
        cursor.execute(query, params)
        resultados = cursor.fetchall()
        
    return resultados

# Função para atualizar saldo
def atualizar_saldo(casa, operacao, valor, observacao):
    try:
        with conn.cursor() as cursor:
            # Obtém saldo atual
            cursor.execute("SELECT saldo FROM saldo_casas WHERE casa_nome = %s", (casa,))
            saldo_atual = float(cursor.fetchone()[0])
            
            # Calcula novo saldo
            if operacao == "Depósito":
                novo_saldo = saldo_atual + valor
            elif operacao == "Saque":
                novo_saldo = saldo_atual - valor
            elif operacao == "Ganhou":
                novo_saldo = saldo_atual + valor
            elif operacao == "Perdeu":
                novo_saldo = saldo_atual - valor
            else:  # Ajuste Manual
                novo_saldo = valor
                
            # Atualiza no banco
            cursor.execute("""
                UPDATE saldo_casas
                SET saldo = %s, ultima_atualizacao = CURRENT_TIMESTAMP
                WHERE casa_nome = %s
            """, (novo_saldo, casa))
            
            # Registra histórico
            cursor.execute("""
                INSERT INTO historico_saldos (casa_nome, operacao, valor, observacao, saldo_resultante)
                VALUES (%s, %s, %s, %s, %s)
            """, (
                casa,
                operacao,
                valor if operacao != "Ajuste Manual" else abs(novo_saldo - saldo_atual),
                observacao,
                novo_saldo
            ))
            
            conn.commit()
            return True, "Saldo atualizado com sucesso!"
                
    except Exception as e:
        conn.rollback()
        return False, f"Erro na operação: {str(e)}"

# Função para obter dados para gráficos
def get_evolucao_saldo(casa=None, dias=30):
    try:
        query = """
            SELECT 
                DATE(data) as dia,
                casa_nome,
                SUM(CASE 
                    WHEN operacao = 'Depósito' OR operacao = 'Ganhou' THEN valor
                    WHEN operacao = 'Saque' OR operacao = 'Perdeu' THEN -valor
                    ELSE 0
                END) as movimentacao
            FROM historico_saldos
            WHERE data >= CURRENT_DATE - INTERVAL %s DAY
        """
        
        params = [f"{dias} DAY"]
        
        if casa and casa != "Todas":
            query += " AND casa_nome = %s"
            params.append(casa)
            
        query += " GROUP BY dia, casa_nome ORDER BY dia"
        
        with conn.cursor() as cursor:
            cursor.execute(query, params)
            resultados = cursor.fetchall()
            
        df = pd.DataFrame(resultados, columns=["Data", "Casa", "Movimentação"])
        
        # Criar uma tabela pivotada para a evolução do saldo
        if not df.empty:
            if casa and casa != "Todas":
                df_pivot = df.pivot(index='Data', values='Movimentação', columns='Casa')
                df_pivot = df_pivot.fillna(0).cumsum()
            else:
                df_pivot = df.groupby('Data')['Movimentação'].sum().cumsum().reset_index()
                df_pivot.columns = ['Data', 'Saldo Acumulado']
                
            return df_pivot
        else:
            return pd.DataFrame()
        
    except Exception as e:
        st.error(f"Erro ao obter dados para gráfico: {str(e)}")
        return pd.DataFrame()

# Função para obter distribuição de saldo por casa
def get_distribuicao_casas():
    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT casa_nome, saldo FROM saldo_casas 
            WHERE saldo <> 0
            ORDER BY saldo DESC
        """)
        resultados = cursor.fetchall()
        
    df = pd.DataFrame(resultados, columns=["Casa", "Saldo"])
    
    # Conversão segura para numérico
    df['Saldo'] = pd.to_numeric(df['Saldo'], errors='coerce')
    
    # Remove possíveis valores inválidos (opcional)
    df = df.dropna(subset=['Saldo'])
    
    return df

# Função para gerenciar metas
def get_metas():
    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT id, titulo, valor_alvo, data_limite, concluida
            FROM metas
            ORDER BY data_limite
        """)
        resultados = cursor.fetchall()
        
    return resultados

def adicionar_meta(titulo, valor_alvo, data_limite):
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO metas (titulo, valor_alvo, data_limite)
                VALUES (%s, %s, %s)
            """, (titulo, valor_alvo, data_limite))
            conn.commit()
        return True, "Meta adicionada com sucesso!"
    except Exception as e:
        conn.rollback()
        return False, f"Erro ao adicionar meta: {str(e)}"

def atualizar_meta(meta_id, concluida):
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                UPDATE metas SET concluida = %s
                WHERE id = %s
            """, (concluida, meta_id))
            conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        return False

def excluir_meta(meta_id):
    try:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM metas WHERE id = %s", (meta_id,))
            conn.commit()
            return True
    except Exception as e:
        conn.rollback()
        st.error(f"Erro ao excluir meta: {str(e)}")
        return False
# Interface principal
st.title("💰 Gerenciamento de Saldo nas Casas de Aposta")

# Criar sidebar para navegação
st.sidebar.markdown("<h3 style='text-align: center'>🎮 Saldo Casas de Aposta</h3>", unsafe_allow_html=True)
pagina = st.sidebar.radio("Navegação", [
    "📊 Dashboard", 
    "💸 Atualizar Saldo", 
    "📜 Histórico", 
    "📈 Gráficos e Análises",
    "🎯 Metas",
    "⚙️ Configurações"
])

# Popular casas iniciais se necessário
popular_casas_iniciais()

if 'last_update' not in st.session_state:
    st.session_state['last_update'] = datetime.now()

current_time = datetime.now()
if (current_time - st.session_state['last_update']) > timedelta(minutes=5):
    st.session_state['last_update'] = current_time
    st.rerun()

if pagina == "📊 Dashboard":
    st.markdown("<h1 class='main-header'>📊 Dashboard Completo de Saldos</h1>", unsafe_allow_html=True)
    
    # Obter dados categorizados
    df, total, media, positivas, negativas, neutras = get_saldos_data()
    
    # Resumo geral
    col1, col2, col3 = st.columns(3)
    
    # Seção de Saldo Total
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"""
            <div class='highlight-box {'highlight-positive' if total > 0 else 'highlight-negative' if total < 0 else 'highlight-neutral'}'>
                <p style='font-size: 1.2rem;'>Saldo Total</p>
                <p style='font-size: 2rem;'>R$ {total:,.2f}</p>
            </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
            <div class='highlight-box highlight-neutral'>
                <p style='font-size: 1.2rem;'>Casas com Movimento</p>
                <p style='font-size: 2rem;'>{len(positivas) + len(negativas)}</p>
            </div>
            """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
            <div class='highlight-box highlight-neutral'>
                <p style='font-size: 1.2rem;'>Média de Saldo</p>
                <p style='font-size: 2rem;'>R$ {media:,.2f}</p>
            </div>
        """, unsafe_allow_html=True)
    
    # Seção de Casas Positivas
    st.markdown("<div class='categoria-title'>🏦 Casas com Saldo Positivo</div>", unsafe_allow_html=True)
    if not positivas.empty:
        cols = st.columns(4)
        for idx, (_, row) in enumerate(positivas.iterrows()):
            with cols[idx % 4]:
                st.markdown(f"""
                    <div class='card card-positivo'>
                        <div style='font-weight: 600;'>{row['Casa']}</div>
                        <div class='big-number'>R$ {row['Saldo']:,.2f}</div>
                        <div style='font-size: 0.8rem; color: #ecf0f1;'>
                            Atualizado: {row['Última Atualização'].strftime('%d/%m/%Y')}
                        </div>
                    </div>
                """, unsafe_allow_html=True)
    
    # Seção de Casas Negativas
    st.markdown("<div class='categoria-title'>📉 Casas com Saldo Negativo</div>", unsafe_allow_html=True)
    if not negativas.empty:
        cols = st.columns(4)
        for idx, (_, row) in enumerate(negativas.iterrows()):
            with cols[idx % 4]:
                st.markdown(f"""
                    <div class='card card-negativo'>
                        <div style='font-weight: 600;'>{row['Casa']}</div>
                        <div class='big-number'>R$ {row['Saldo']:,.2f}</div>
                        <div style='font-size: 0.8rem; color: #f5b7b1;'>
                            Atualizado: {row['Última Atualização'].strftime('%d/%m/%Y')}
                        </div>
                    </div>
                """, unsafe_allow_html=True)
    
    # Nova Seção de Casas Neutras
    st.markdown("<div class='categoria-title'>⚖️ Casas sem Movimentação</div>", unsafe_allow_html=True)
    if not neutras.empty:
        cols = st.columns(4)
        for idx, (_, row) in enumerate(neutras.iterrows()):
            with cols[idx % 4]:
                st.markdown(f"""
                    <div class='card card-neutro'>
                        <div style='font-weight: 600;'>{row['Casa']}</div>
                        <div class='big-number'>R$ {row['Saldo']:,.2f}</div>
                        <div style='font-size: 0.8rem; color: #7f8c8d;'>
                            Última atualização: {row['Última Atualização'].strftime('%d/%m/%Y')}
                        </div>
                    </div>
                """, unsafe_allow_html=True)
    else:
        st.markdown("<div style='padding: 1rem; background-color: #f8f9fa; border-radius: 8px; color: #95a5a6;'>Todas as casas possuem movimentação registrada</div>", unsafe_allow_html=True)
    
    # Últimas transações
    st.markdown("<div class='section-title'>Últimas Transações</div>", unsafe_allow_html=True)
    historico = get_historico(limit=5)
    
    for item in historico:
        operacao_color = {
            "Depósito": "#4CAF50", 
            "Saque": "#F44336", 
            "Ganhou": "#4CAF50", 
            "Perdeu": "#F44336", 
            "Ajuste Manual": "#FF9800"
        }.get(item[3], "#9E9E9E")
        
        st.markdown(f"""
            <div class='transaction-item' style='background-color: #f9f9f9;'>
                <div style='display: flex; justify-content: space-between;'>
                    <span style='font-weight: 600;'>{item[2]}</span>
                    <span style='color: {operacao_color}; font-weight: 600;'>
                        {'+' if item[3] in ['Depósito', 'Ganhou'] else '-' if item[3] in ['Saque', 'Perdeu'] else ''}
                        R$ {abs(item[4]):,.2f}
                    </span>
                </div>
                <div style='display: flex; justify-content: space-between; font-size: 0.9rem; color: #757575;'>
                    <span>{item[3]}</span>
                    <span>{item[1].strftime('%d/%m/%Y %H:%M')}</span>
                </div>
                {f"<div style='font-size: 0.9rem; margin-top: 5px;'>{item[5]}</div>" if item[5] else ""}
            </div>
        """, unsafe_allow_html=True)
    
    if st.button("Ver Histórico Completo"):
        st.session_state['pagina'] = "📜 Histórico"
        st.rerun()

# 2. ATUALIZAR SALDO
elif pagina == "💸 Atualizar Saldo":
    st.markdown("<h1 class='main-header'>💸 Atualizar Saldo</h1>", unsafe_allow_html=True)
    
    # Criação de tabs para diferentes operações
    tabs = st.tabs(["💰 Transação Padrão", "🎲 Resultado de Aposta", "✏️ Ajuste Manual", "🏠 Nova Casa"])
    
    # Tab 1: Transação Padrão (Depósito/Saque)
    with tabs[0]:
        st.markdown("<div class='tab-content'>", unsafe_allow_html=True)
        
        with conn.cursor() as cursor:
            cursor.execute("SELECT casa_nome FROM saldo_casas ORDER BY casa_nome")
            casas = [row[0] for row in cursor.fetchall()]
        
        col1, col2 = st.columns(2)
        
        with col1:
            casa_selecionada = st.selectbox("Selecione a casa:", casas, key="casa_transacao")
            valor = st.number_input("Valor (R$):", min_value=0.01, format="%.2f", key="valor_transacao")
        
        with col2:
            operacao = st.radio("Tipo de operação:", ["Depósito", "Saque"], horizontal=True, key="op_transacao")
            observacao = st.text_area("Observação/Motivo:", key="obs_transacao", height=95)
        
        if st.button("Confirmar Transação", key="btn_transacao"):
            success, message = atualizar_saldo(casa_selecionada, operacao, valor, observacao)
            if success:
                st.markdown(f"<div class='success-message'>{message}</div>", unsafe_allow_html=True)
                time.sleep(1)
                st.rerun()
            else:
                st.markdown(f"<div class='error-message'>{message}</div>", unsafe_allow_html=True)
        
        st.markdown("</div>", unsafe_allow_html=True)
    
    # Tab 2: Resultado de Aposta
    with tabs[1]:
        st.markdown("<div class='tab-content'>", unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            casa_aposta = st.selectbox("Selecione a casa:", casas, key="casa_aposta")
            valor_apostado = st.number_input("Valor Apostado (R$):", min_value=0.01, format="%.2f", key="valor_apostado")
        
        with col2:
            resultado = st.radio("Resultado:", ["Ganhou", "Perdeu"], horizontal=True, key="resultado_aposta")
            if resultado == "Ganhou":
                lucro = st.number_input("Lucro (R$):", min_value=0.00, format="%.2f", key="lucro_aposta")
            
        observacao_aposta = st.text_area("Observação (Jogo, Odd, etc.):", key="obs_aposta")
        
        if st.button("Registrar Resultado", key="btn_aposta"):
            if resultado == "Ganhou":
                # Ao ganhar, o valor a ser adicionado é o lucro (não incluindo a stake)
                success, message = atualizar_saldo(
                    casa_aposta, 
                    "Ganhou", 
                    lucro, 
                    f"Ganhou R$ {lucro:.2f} em aposta de R$ {valor_apostado:.2f}. {observacao_aposta}"
                )
            else:
                # Ao perder, o valor a ser subtraído é o valor apostado
                success, message = atualizar_saldo(
                    casa_aposta, 
                    "Perdeu", 
                    valor_apostado, 
                    f"Perdeu aposta de R$ {valor_apostado:.2f}. {observacao_aposta}"
                )
                
            if success:
                st.markdown(f"<div class='success-message'>{message}</div>", unsafe_allow_html=True)
                time.sleep(1)
                st.rerun()
            else:
                st.markdown(f"<div class='error-message'>{message}</div>", unsafe_allow_html=True)
        
        st.markdown("</div>", unsafe_allow_html=True)
    
    # Tab 3: Ajuste Manual
    with tabs[2]:
        st.markdown("<div class='tab-content'>", unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            casa_ajuste = st.selectbox("Selecione a casa:", casas, key="casa_ajuste")
            
            # Buscar saldo atual para exibir
            with conn.cursor() as cursor:
                cursor.execute("SELECT saldo FROM saldo_casas WHERE casa_nome = %s", (casa_ajuste,))
                saldo_atual = float(cursor.fetchone()[0])
            
            st.info(f"Saldo atual: R$ {saldo_atual:.2f}")
            
        with col2:
            novo_saldo = st.number_input("Novo saldo (R$):", value=float(saldo_atual), format="%.2f", key="novo_saldo")
            obs_ajuste = st.text_area("Motivo do ajuste:", key="obs_ajuste", height=95)
        
        if st.button("Confirmar Ajuste", key="btn_ajuste"):
            success, message = atualizar_saldo(casa_ajuste, "Ajuste Manual", novo_saldo, obs_ajuste)
            if success:
                st.markdown(f"<div class='success-message'>{message}</div>", unsafe_allow_html=True)
                time.sleep(1)
                st.rerun()
            else:
                st.markdown(f"<div class='error-message'>{message}</div>", unsafe_allow_html=True)
        
        st.markdown("</div>", unsafe_allow_html=True)
    
    # Tab 4: Nova Casa
    with tabs[3]:
        st.markdown("<div class='tab-content'>", unsafe_allow_html=True)
        
        nova_casa = st.text_input("Nome da nova casa de apostas:", key="nova_casa")
        saldo_inicial = st.number_input("Saldo inicial (R$):", value=0.0, format="%.2f", key="saldo_inicial")
        
        if st.button("Cadastrar Nova Casa", key="btn_nova_casa"):
            if nova_casa.strip():
                try:
                    with conn.cursor() as cursor:
                        cursor.execute("""
                            INSERT INTO saldo_casas (casa_nome, saldo)
                            VALUES (%s, %s)
                            ON CONFLICT (casa_nome) DO NOTHING
                        """, (nova_casa.strip(), saldo_inicial))
                        
                        if saldo_inicial > 0:
                            cursor.execute("""
                                INSERT INTO historico_saldos 
                                (casa_nome, operacao, valor, observacao, saldo_resultante)
                                VALUES (%s, %s, %s, %s, %s)
                            """, (
                                nova_casa.strip(),
                                "Depósito",
                                saldo_inicial,
                                "Saldo inicial",
                                saldo_inicial
                            ))
                            
                        conn.commit()
                        st.markdown(f"<div class='success-message'>Casa '{nova_casa}' cadastrada com sucesso!</div>", unsafe_allow_html=True)
                        time.sleep(1)
                        st.rerun()
                except Exception as e:
                    st.markdown(f"<div class='error-message'>Erro ao cadastrar: {str(e)}</div>", unsafe_allow_html=True)
            else:
                st.warning("Digite um nome válido para a casa")
        
        st.markdown("</div>", unsafe_allow_html=True)

# 3. HISTÓRICO
elif pagina == "📜 Histórico":
    st.markdown("<h1 class='main-header'>📜 Histórico de Transações</h1>", unsafe_allow_html=True)
    
    # Filtros para o histórico
    st.markdown("<div class='filter-container'>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3)
    
    with col1:
        with conn.cursor() as cursor:
            cursor.execute("SELECT casa_nome FROM saldo_casas ORDER BY casa_nome")
            casas = ["Todas"] + [row[0] for row in cursor.fetchall()]
        
        filtro_casa = st.selectbox("Casa de Apostas:", casas)
    
    with col2:
        filtro_periodo = st.selectbox(
            "Período:", 
            ["Todos", "Hoje", "Última Semana", "Último Mês"]
        )
    
    with col3:
        limite_registros = st.number_input("Limite de registros:", min_value=10, max_value=500, value=100, step=10)

    st.markdown("</div>", unsafe_allow_html=True)

    # Buscar dados do histórico com os filtros aplicados
    historico = get_historico(
        limit=limite_registros,
        casa=filtro_casa if filtro_casa != "Todas" else None,
        periodo=filtro_periodo if filtro_periodo != "Todos" else None
    )

    # Exibir dados do histórico em forma de tabela
    if historico:
        # Cabeçalho para a tabela de histórico
        st.markdown("""
            <div style="display: grid; grid-template-columns: 1fr 2fr 2fr 1.5fr 1.5fr 3fr; font-weight: bold; 
                    background-color: #f0f2f6; padding: 10px; border-radius: 5px 5px 0 0;">
                <div>Data</div>
                <div>Casa</div>
                <div>Operação</div>
                <div>Valor</div>
                <div>Saldo Final</div>
                <div>Observação</div>
            </div>
        """, unsafe_allow_html=True)
        
        # Linhas da tabela
        for item in historico:
            # Define cor com base no tipo de operação
            operacao_color = {
                "Depósito": "#4CAF50", 
                "Saque": "#F44336", 
                "Ganhou": "#4CAF50", 
                "Perdeu": "#F44336", 
                "Ajuste Manual": "#FF9800"
            }.get(item[3], "#9E9E9E")
            
            # Formatação de valores
            valor_formatado = f"{'+' if item[3] in ['Depósito', 'Ganhou'] else '-' if item[3] in ['Saque', 'Perdeu'] else '±'} R$ {abs(item[4]):,.2f}"
            saldo_resultante = f"R$ {item[6]:,.2f}" if item[6] is not None else "N/A"
            
            st.markdown(f"""
                <div style="display: grid; grid-template-columns: 1fr 2fr 2fr 1.5fr 1.5fr 3fr; padding: 10px; 
                        border-bottom: 1px solid #e0e0e0; align-items: center;">
                    <div>{item[1].strftime('%d/%m/%Y %H:%M')}</div>
                    <div>{item[2]}</div>
                    <div style="color: {operacao_color}; font-weight: 500;">{item[3]}</div>
                    <div style="color: {operacao_color}; font-weight: 500;">{valor_formatado}</div>
                    <div>{saldo_resultante}</div>
                    <div style="white-space: normal;">{item[5] if item[5] else "-"}</div>
                </div>
            """, unsafe_allow_html=True)
    else:
        st.info("Nenhum registro encontrado com os filtros selecionados.")

    # Botão para exportar histórico
    if historico:
        if st.button("Exportar dados"):
            # Preparar dados para exportação
            dados_export = []
            for item in historico:
                dados_export.append({
                    "Data": item[1].strftime('%d/%m/%Y %H:%M'),
                    "Casa": item[2],
                    "Operação": item[3],
                    "Valor": abs(item[4]),
                    "Saldo Resultante": item[6] if item[6] is not None else 0,
                    "Observação": item[5] if item[5] else ""
                })
            
            # Converter para DataFrame e mostrar como CSV
            df_export = pd.DataFrame(dados_export)
            st.download_button(
                label="Baixar como CSV",
                data=df_export.to_csv(index=False).encode('utf-8'),
                file_name=f"historico_apostas_{datetime.now().strftime('%Y%m%d')}.csv",
                mime='text/csv',
            )

# 4. GRÁFICOS E ANÁLISES
elif pagina == "📈 Gráficos e Análises":
    st.markdown("<h1 class='main-header'>📈 Gráficos e Análises</h1>", unsafe_allow_html=True)
    
    # Abas para diferentes tipos de gráficos
    graf_tabs = st.tabs(["📊 Evolução do Saldo", "🍩 Distribuição por Casa", "📊 Desempenho Mensal"])
    
    # Tab 1: Evolução do Saldo
    with graf_tabs[0]:
        # Filtros
        col1, col2 = st.columns(2)
        with col1:
            with conn.cursor() as cursor:
                cursor.execute("SELECT casa_nome FROM saldo_casas WHERE saldo <> 0 ORDER BY casa_nome")
                casas_ativas = ["Todas"] + [row[0] for row in cursor.fetchall()]
            
            filtro_casa_grafico = st.selectbox("Casa de Apostas:", casas_ativas, key="casa_grafico")
        
        with col2:
            periodo_dias = st.slider("Período (dias):", min_value=7, max_value=180, value=30, step=1)
        
        # Obter dados de evolução
        df_evolucao = get_evolucao_saldo(
            casa=filtro_casa_grafico if filtro_casa_grafico != "Todas" else None,
            dias=periodo_dias
        )
        
        if not df_evolucao.empty:
            # Criar gráfico de linha
            if filtro_casa_grafico == "Todas":
                fig = px.line(
                    df_evolucao, 
                    x='Data', 
                    y='Saldo Acumulado',
                    title=f"Evolução do Saldo Total (Últimos {periodo_dias} dias)",
                    markers=True
                )
                fig.update_layout(
                    xaxis_title="Data",
                    yaxis_title="Saldo (R$)",
                    height=500
                )
            else:
                # Para casa específica
                fig = px.line(
                    df_evolucao, 
                    title=f"Evolução do Saldo - {filtro_casa_grafico} (Últimos {periodo_dias} dias)",
                    markers=True
                )
                fig.update_layout(
                    xaxis_title="Data",
                    yaxis_title="Saldo (R$)",
                    height=500
                )
            
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Não há dados suficientes para gerar o gráfico com os filtros selecionados.")
    
    # Tab 2: Distribuição por Casa
    with graf_tabs[1]:
        # Obter dados
        df_distribuicao = get_distribuicao_casas()
        
        if not df_distribuicao.empty:
            # Criar gráficos
            col1, col2 = st.columns(2)
            
            with col1:
                # Gráfico de pizza para distribuição de saldo
                fig_pie = px.pie(
                    df_distribuicao,
                    values='Saldo',
                    names='Casa',
                    title="Distribuição do Saldo por Casa",
                    hole=0.4
                )
                fig_pie.update_traces(textinfo='percent+label')
                st.plotly_chart(fig_pie, use_container_width=True)
            
            with col2:
                # Gráfico de barras horizontais para top casas
                df_top = df_distribuicao.nlargest(10, 'Saldo')
                fig_bar = px.bar(
                    df_top,
                    y='Casa',
                    x='Saldo',
                    title="Top 10 Casas por Saldo",
                    orientation='h',
                    color='Saldo',
                    color_continuous_scale='Blues'
                )
                fig_bar.update_layout(yaxis={'categoryorder':'total ascending'})
                st.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.info("Não há dados suficientes para gerar os gráficos de distribuição.")
    
    # Tab 3: Desempenho Mensal
    with graf_tabs[2]:
        # Obter dados de desempenho mensal
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        to_char(data, 'YYYY-MM') as mes,
                        SUM(CASE 
                            WHEN operacao = 'Ganhou' THEN valor
                            WHEN operacao = 'Perdeu' THEN -valor
                            ELSE 0
                        END) as resultado
                    FROM historico_saldos
                    WHERE operacao IN ('Ganhou', 'Perdeu')
                    GROUP BY mes
                    ORDER BY mes
                """)
                resultados = cursor.fetchall()
                
            if resultados:
                df_mensal = pd.DataFrame(resultados, columns=["Mês", "Resultado"])
                
                # Formatar mês para exibição
                df_mensal['Mês_Formatado'] = df_mensal['Mês'].apply(
                    lambda x: f"{x.split('-')[1]}/{x.split('-')[0]}"
                )
                
                # Criar gráfico de barras
                fig_mensal = px.bar(
                    df_mensal,
                    x='Mês_Formatado',
                    y='Resultado',
                    title="Resultado Mensal (Ganhos - Perdas)",
                    color='Resultado',
                    color_continuous_scale=['red', 'green'],
                    text_auto=True
                )
                
                fig_mensal.update_layout(
                    xaxis_title="Mês",
                    yaxis_title="Resultado (R$)",
                    height=500
                )
                
                st.plotly_chart(fig_mensal, use_container_width=True)
                
                # Resumo estatístico
                st.markdown("<div class='section-title'>Resumo Estatístico</div>", unsafe_allow_html=True)
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.markdown(f"""
                        <div class='stat-box'>
                            <div class='stat-label'>Melhor Mês</div>
                            <div class='stat-value' style='color: #4CAF50;'>
                                {df_mensal.loc[df_mensal['Resultado'].idxmax(), 'Mês_Formatado']}
                            </div>
                            <div style='font-weight: 500;'>
                                R$ {df_mensal['Resultado'].max():,.2f}
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    st.markdown(f"""
                        <div class='stat-box'>
                            <div class='stat-label'>Pior Mês</div>
                            <div class='stat-value' style='color: #F44336;'>
                                {df_mensal.loc[df_mensal['Resultado'].idxmin(), 'Mês_Formatado']}
                            </div>
                            <div style='font-weight: 500;'>
                                R$ {df_mensal['Resultado'].min():,.2f}
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
                
                with col3:
                    media_mensal = df_mensal['Resultado'].mean()
                    color = "#4CAF50" if media_mensal > 0 else "#F44336" if media_mensal < 0 else "#9E9E9E"
                    st.markdown(f"""
                        <div class='stat-box'>
                            <div class='stat-label'>Média Mensal</div>
                            <div class='stat-value' style='color: {color};'>
                                R$ {media_mensal:,.2f}
                            </div>
                            <div style='font-weight: 500;'>
                                {len(df_mensal)} meses analisados
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("Não há dados suficientes de ganhos e perdas para análise mensal.")
        except Exception as e:
            st.error(f"Erro ao gerar análise mensal: {str(e)}")

# 5. METAS
elif pagina == "🎯 Metas":
    st.markdown("<h1 class='main-header'>🎯 Metas de Apostas</h1>", unsafe_allow_html=True)
    
    # Obter saldo total atual
    _, saldo_total, _, _, _, _ = get_saldos_data()
    
    # Dividir layout
    col_principal, col_lateral = st.columns([3, 1])
    
    with col_principal:
        st.markdown("<div class='section-title'>Metas Cadastradas</div>", unsafe_allow_html=True)
        
        metas = get_metas()
        
        if metas:
            for meta in metas:
                meta_id, titulo, valor_alvo, data_limite, concluida = meta
                dias_restantes = (data_limite - datetime.now().date()).days
                
                # Container para cada meta
                with st.container():
                    col_meta, col_acoes = st.columns([4, 1])
                    
                    with col_meta:
                        # Atualização automática do status
                        if saldo_total >= valor_alvo and not concluida:
                            atualizar_meta(meta_id, True)
                            concluida = True
                        
                        progresso = min(100, (saldo_total / float(valor_alvo)) * 100 if valor_alvo > 0 else 0)
                        
                        # Determinar estilo
                        cor_barra = "#4CAF50" if concluida else "#F44336" if dias_restantes < 0 else "#FF9800"
                        status = "Concluída ✅" if concluida else f"{dias_restantes} dias restantes" if dias_restantes >= 0 else "Expirada ❌"
                        
                        # Exibição da meta
                        st.markdown(f"""
                            <div style="padding: 15px; border-radius: 10px; margin-bottom: 15px; 
                                      background: {'#e8f5e9' if concluida else '#fff'};
                                      box-shadow: 0 2px 5px rgba(0,0,0,0.1);">
                                <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
                                    <div style="font-weight: 600; font-size: 1.1rem;">{titulo}</div>
                                    <div style="color: {cor_barra}">{status}</div>
                                </div>
                                <div style="background: #e0e0e0; border-radius: 5px; height: 10px; margin-bottom: 5px;">
                                    <div style="width: {progresso}%; background: {cor_barra}; height: 10px; border-radius: 5px;"></div>
                                </div>
                                <div style="display: flex; justify-content: space-between; font-size: 0.9rem; color: #666;">
                                    <div>Meta: R$ {float(valor_alvo):,.2f}</div>
                                    <div>Atual: R$ {float(saldo_total):,.2f}</div>
                                </div>
                                <div style="display: flex; justify-content: space-between; font-size: 0.8rem; color: #999; margin-top: 5px;">
                                    <div>{progresso:.1f}% concluído</div>
                                    <div>Até {data_limite.strftime('%d/%m/%Y')}</div>
                                </div>
                            </div>
                        """, unsafe_allow_html=True)
                    
                    with col_acoes:
                        st.write("")  # Espaçamento
                        if st.button("🗑️", key=f"del_{meta_id}"):
                            if excluir_meta(meta_id):
                                st.success("Meta excluída!")
                                time.sleep(1)
                                st.rerun()
                        
                        novo_status = not concluida
                        if st.button("✅" if concluida else "🔲", key=f"check_{meta_id}"):
                            atualizar_meta(meta_id, novo_status)
                            st.rerun()
        else:
            st.info("Nenhuma meta cadastrada. Crie sua primeira meta ao lado →")

    with col_lateral:
        st.markdown("<div class='section-title'>Nova Meta</div>", unsafe_allow_html=True)
        
        with st.form("nova_meta_form"):
            titulo = st.text_input("Título:", placeholder="Ex: Meta para viagem")
            valor = st.number_input("Valor alvo (R$):", min_value=1.0, value=1000.0, step=100.0)
            data_limite = st.date_input(
                "Data limite:",
                value=datetime.now().date() + timedelta(days=30),
                min_value=datetime.now().date()
            )
            
            if st.form_submit_button("➕ Criar Meta"):
                if titulo.strip():
                    success, msg = adicionar_meta(titulo, valor, data_limite)
                    if success:
                        st.success(msg)
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(msg)
                else:
                    st.warning("Digite um título para a meta")

# 6. CONFIGURAÇÕES
elif pagina == "⚙️ Configurações":
    st.markdown("<h1 class='main-header'>⚙️ Configurações</h1>", unsafe_allow_html=True)
    
    # Dividir em tabs para diferentes configurações
    config_tabs = st.tabs(["🏠 Gerenciar Casas", "🗑️ Excluir Dados", "ℹ️ Sobre"])
    
    # Tab 1: Gerenciar Casas
    with config_tabs[0]:
        st.markdown("<div class='section-title'>Gerenciar Casas de Apostas</div>", unsafe_allow_html=True)
        
        # Listar todas as casas com opção de inativar/reativar
        with conn.cursor() as cursor:
            cursor.execute("SELECT casa_nome, saldo FROM saldo_casas ORDER BY casa_nome")
            todas_casas = cursor.fetchall()
        
        if todas_casas:
            st.markdown("<div style='font-weight: 500; margin-bottom: 10px;'>Lista de casas cadastradas:</div>", unsafe_allow_html=True)
            
            for casa, saldo in todas_casas:
                col1, col2, col3 = st.columns([3, 2, 1])
                
                with col1:
                    st.text(casa)
                
                with col2:
                    st.text(f"R$ {saldo:,.2f}")
                
                with col3:
                    if st.button("Editar", key=f"edit_{casa}"):
                        st.session_state['casa_editar'] = casa
                        st.session_state['novo_nome_casa'] = casa
            
            # Exibir formulário de edição se uma casa foi selecionada
            if 'casa_editar' in st.session_state:
                st.markdown("<div style='background-color: #f5f5f5; padding: 15px; border-radius: 10px; margin-top: 20px;'>", unsafe_allow_html=True)
                st.markdown(f"<div style='font-weight: 500; margin-bottom: 10px;'>Editando: {st.session_state['casa_editar']}</div>", unsafe_allow_html=True)
                
                novo_nome = st.text_input("Novo nome:", value=st.session_state['novo_nome_casa'], key="input_novo_nome")
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Salvar Alterações"):
                        if novo_nome and novo_nome != st.session_state['casa_editar']:
                            try:
                                with conn.cursor() as cursor:
                                    # Verificar se o novo nome já existe
                                    cursor.execute("SELECT casa_nome FROM saldo_casas WHERE casa_nome = %s", (novo_nome,))
                                    if cursor.fetchone():
                                        st.error(f"A casa '{novo_nome}' já existe.")
                                    else:
                                        # Atualizar nome na tabela de saldos
                                        cursor.execute("""
                                            UPDATE saldo_casas 
                                            SET casa_nome = %s
                                            WHERE casa_nome = %s
                                        """, (novo_nome, st.session_state['casa_editar']))
                                        
                                        # Atualizar nome no histórico
                                        cursor.execute("""
                                            UPDATE historico_saldos
                                            SET casa_nome = %s
                                            WHERE casa_nome = %s
                                        """, (novo_nome, st.session_state['casa_editar']))
                                        
                                        conn.commit()
                                        st.success(f"Casa '{st.session_state['casa_editar']}' renomeada para '{novo_nome}'.")
                                        del st.session_state['casa_editar']
                                        time.sleep(1)
                                        st.rerun()
                            except Exception as e:
                                conn.rollback()
                                st.error(f"Erro ao atualizar: {str(e)}")
                        else:
                            st.warning("O nome não foi alterado ou está em branco.")
                
                with col2:
                    if st.button("Cancelar"):
                        del st.session_state['casa_editar']
                        st.rerun()
                
                st.markdown("</div>", unsafe_allow_html=True)
    
    # Tab 2: Excluir Dados
    with config_tabs[1]:
        st.markdown("<div class='section-title'>Excluir Dados</div>", unsafe_allow_html=True)
        
        st.warning("⚠️ Atenção! A exclusão de dados é permanente e não pode ser desfeita.")
        
        opcao_exclusao = st.radio(
            "Selecione o tipo de dados a excluir:",
            ["Histórico de Transações", "Casa de Apostas Específica", "Todas as Metas"]
        )
        
        if opcao_exclusao == "Histórico de Transações":
            periodo_excluir = st.selectbox(
                "Período para excluir:",
                ["Selecione um período", "Últimos 7 dias", "Último mês", "Últimos 3 meses", "Todo o histórico"]
            )
            
            if periodo_excluir != "Selecione um período":
                confirmar = st.text_input("Digite 'CONFIRMAR' para excluir o histórico selecionado:")
                
                if st.button("Excluir Histórico") and confirmar == "CONFIRMAR":
                    try:
                        with conn.cursor() as cursor:
                            if periodo_excluir == "Todo o histórico":
                                cursor.execute("DELETE FROM historico_saldos")
                                mensagem = "Todo o histórico de transações foi excluído."
                            else:
                                dias = {
                                    "Últimos 7 dias": 7,
                                    "Último mês": 30,
                                    "Últimos 3 meses": 90
                                }[periodo_excluir]
                                
                                cursor.execute("""
                                    DELETE FROM historico_saldos
                                    WHERE data >= CURRENT_DATE - INTERVAL %s DAY
                                """, (dias,))
                                
                                mensagem = f"Histórico de transações dos {periodo_excluir.lower()} foi excluído."
                            
                            conn.commit()
                            st.success(mensagem)
                            time.sleep(1)
                            st.rerun()
                    except Exception as e:
                        conn.rollback()
                        st.error(f"Erro ao excluir histórico: {str(e)}")
        
        elif opcao_exclusao == "Casa de Apostas Específica":
            with conn.cursor() as cursor:
                cursor.execute("SELECT casa_nome FROM saldo_casas ORDER BY casa_nome")
                casas_disponiveis = [row[0] for row in cursor.fetchall()]
            
            casa_excluir = st.selectbox("Selecione a casa para excluir:", ["Selecione uma casa"] + casas_disponiveis)
            
            if casa_excluir != "Selecione uma casa":
                confirmar = st.text_input("Digite 'CONFIRMAR' para excluir a casa selecionada:")
                
                if st.button("Excluir Casa") and confirmar == "CONFIRMAR":
                    try:
                        with conn.cursor() as cursor:
                            # Excluir da tabela de saldos
                            cursor.execute("DELETE FROM saldo_casas WHERE casa_nome = %s", (casa_excluir,))
                            
                            # Opcionalmente, excluir do histórico também
                            if st.checkbox("Excluir também o histórico desta casa"):
                                cursor.execute("DELETE FROM historico_saldos WHERE casa_nome = %s", (casa_excluir,))
                            
                            conn.commit()
                            st.success(f"Casa '{casa_excluir}' excluída com sucesso.")
                            time.sleep(1)
                            st.rerun()
                    except Exception as e:
                        conn.rollback()
                        st.error(f"Erro ao excluir casa: {str(e)}")
        
        elif opcao_exclusao == "Todas as Metas":
            confirmar = st.text_input("Digite 'CONFIRMAR' para excluir todas as metas:")
            
            if st.button("Excluir Todas as Metas") and confirmar == "CONFIRMAR":
                try:
                    with conn.cursor() as cursor:
                        cursor.execute("DELETE FROM metas")
                        conn.commit()
                        st.success("Todas as metas foram excluídas com sucesso.")
                        time.sleep(1)
                        st.rerun()
                except Exception as e:
                    conn.rollback()
                    st.error(f"Erro ao excluir metas: {str(e)}")
    
    # Tab 3: Sobre o App
    with config_tabs[2]:
        st.markdown("<div class='section-title'>Sobre o Aplicativo</div>", unsafe_allow_html=True)
        
        st.markdown("""
            ### 💰 Gerenciador de Saldo de Casas de Apostas
            
            Esta aplicação permite gerenciar e acompanhar seus saldos em diferentes casas de apostas,
            registrar operações de depósito, saque e resultados de apostas, além de visualizar estatísticas
            e definir metas financeiras.
            
            **Recursos:**
            - Dashboard com visão geral dos saldos
            - Registro de operações (depósitos, saques, apostas)
            - Histórico completo de transações
            - Gráficos e análises de desempenho
            - Sistema de metas financeiras
            - Gerenciamento de casas de apostas
            
            **Dicas de uso:**
            - Atualize os resultados das apostas regularmente para manter estatísticas precisas
            - Utilize as metas para planejar seus objetivos financeiros
            - Consulte os gráficos para entender seu desempenho ao longo do tempo
            
            **Versão:** 2.0 (Abril 2025)
        """)

# Adiciona um footer
st.markdown("""
    <div style="margin-top: 3rem; text-align: center; color: #9e9e9e; font-size: 0.8rem; border-top: 1px solid #e0e0e0; padding-top: 1rem;">
        💰 Gerenciador de Saldo de Casas de Apostas | Dados atualizados em: {0}
    </div>
""".format(datetime.now().strftime('%d/%m/%Y %H:%M')), unsafe_allow_html=True)