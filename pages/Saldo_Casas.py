import streamlit as st
import psycopg2
from dotenv import load_dotenv
import os

# Carrega variáveis de ambiente do arquivo .env
load_dotenv()

st.set_page_config(
    page_title="Saldo nas Casas de Aposta",
    page_icon="💰",
    layout="wide"
)

# Função para conectar ao PostgreSQL utilizando a variável DATABASE_URL
@st.cache_resource
def init_db():
    try:
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            st.error("Variável de ambiente DATABASE_URL não definida")
            return None
        
        conn = psycopg2.connect(database_url)
        
        # Cria tabela de saldos se não existir
        with conn.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS saldo_casas (
                    id SERIAL PRIMARY KEY,
                    casa_nome TEXT UNIQUE,
                    saldo NUMERIC(10,2) DEFAULT 0,
                    ultima_atualizacao TIMESTAMP
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
     'Novibet', 'Sporting Bet', 'Bet7k','Cassino Pix','KTO','Stake', 'BR Bet', 'Aposta tudo', 'Casa de Apostas',
     'Vera Bet', 'Bateu Bet', 'Betnacional', 'Jogue Facil', 'Jogo de Ouro', 'Pagol',
     'Seu Bet', 'Bet Esporte', 'BetFast', 'Faz1Bet', 'Esportiva Bet', 'Betpix365',
     'Seguro Bet', 'Outros','Minha Conta'
    ]
    
    with conn.cursor() as cursor:
        for casa in casas:
            cursor.execute("""
                INSERT INTO saldo_casas (casa_nome)
                VALUES (%s)
                ON CONFLICT (casa_nome) DO NOTHING
            """, (casa,))
        conn.commit()

# Interface principal
st.title("💰 Gerenciamento de Saldo nas Casas de Aposta")

# Popula casas iniciais se necessário
popular_casas_iniciais()

# Selecionar ação
acao = st.radio("Selecione a ação:", ["Visualizar Saldos", "Atualizar Saldo", "Adicionar Nova Casa"], horizontal=True)

if acao == "Visualizar Saldos":
    # Mostra saldos em cards
    with conn.cursor() as cursor:
        cursor.execute("SELECT casa_nome, saldo FROM saldo_casas ORDER BY casa_nome")
        resultados = cursor.fetchall()
        
    total = sum(float(row[1]) for row in resultados)
    
    # Montante Geral destacado
    st.subheader("Montante Geral")
    st.markdown(f"""
        <div style="
            background: #2ecc71;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
            color: white;
            font-size: 24px;
            font-weight: bold;
        ">
            R$ {total:,.2f}
        </div>
    """, unsafe_allow_html=True)
    
    st.divider()
    
    st.subheader("Saldos por Casa")
    cols = st.columns(4)
    col_idx = 0
    
    for casa, saldo in resultados:
        with cols[col_idx]:
            st.metric(
                label=casa,
                value=f"R$ {saldo:,.2f}",
                help="Clique em 'Atualizar Saldo' para modificar"
            )
        col_idx = (col_idx + 1) % 4

elif acao == "Atualizar Saldo":
    st.subheader("Atualizar Saldo")
    
    with conn.cursor() as cursor:
        cursor.execute("SELECT casa_nome FROM saldo_casas ORDER BY casa_nome")
        casas = [row[0] for row in cursor.fetchall()]
    
    casa_selecionada = st.selectbox("Selecione a casa:", casas)
    operacao = st.radio("Tipo de operação:", ["Depósito", "Saque", "Ajuste Manual"], horizontal=True)
    valor = st.number_input("Valor (R$)", min_value=0.01, format="%.2f")
    observacao = st.text_input("Observação/Motivo:")
    
    if st.button("Confirmar Operação"):
        try:
            with conn.cursor() as cursor:
                # Obtém saldo atual
                cursor.execute("SELECT saldo FROM saldo_casas WHERE casa_nome = %s", (casa_selecionada,))
                saldo_atual = float(cursor.fetchone()[0])
                
                # Calcula novo saldo
                if operacao == "Ganhou":
                    novo_saldo = saldo_atual + valor  # "valor" já deve ser (apostado + lucro)
                elif operacao == "Perdeu":
                    novo_saldo = saldo_atual - valor  # "valor" é o valor apostado
                else:
                    # Mantém para depósito/saque manual
                    if operacao == "Depósito":
                        novo_saldo = saldo_atual + valor
                    elif operacao == "Saque":
                        novo_saldo = saldo_atual - valor
                    else:  
                        novo_saldo = valor
                    
                # Atualiza no banco
                cursor.execute("""
                    UPDATE saldo_casas
                    SET saldo = %s, ultima_atualizacao = CURRENT_TIMESTAMP
                    WHERE casa_nome = %s
                """, (novo_saldo, casa_selecionada))
                
                # Registra histórico (criar tabela se necessário)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS historico_saldos (
                        id SERIAL PRIMARY KEY,
                        data TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        casa_nome TEXT,
                        operacao TEXT,
                        valor NUMERIC(10,2),
                        observacao TEXT
                    )
                """)
                
                cursor.execute("""
                    INSERT INTO historico_saldos (casa_nome, operacao, valor, observacao)
                    VALUES (%s, %s, %s, %s)
                """, (
                    casa_selecionada,
                    operacao,
                    valor if operacao != "Ajuste Manual" else (novo_saldo - saldo_atual),
                    observacao
                ))
                
                conn.commit()
                st.success("Saldo atualizado com sucesso!")
                st.rerun()
                
        except Exception as e:
            st.error(f"Erro na operação: {str(e)}")
            conn.rollback()

elif acao == "Adicionar Nova Casa":
    st.subheader("Adicionar Nova Casa de Apostas")
    nova_casa = st.text_input("Nome da nova casa de apostas:")
    
    if st.button("Cadastrar Casa"):
        if nova_casa.strip():
            try:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO saldo_casas (casa_nome)
                        VALUES (%s)
                        ON CONFLICT (casa_nome) DO NOTHING
                    """, (nova_casa.strip(),))
                    conn.commit()
                    st.success(f"Casa '{nova_casa}' cadastrada!")
                    st.rerun()
            except Exception as e:
                st.error(f"Erro ao cadastrar: {str(e)}")
        else:
            st.warning("Digite um nome válido para a casa")

# Link para o histórico
st.divider()
if st.button("📜 Ver Histórico Completo de Transações"):
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT * FROM historico_saldos
                ORDER BY data DESC
            """)
            historico = cursor.fetchall()
            
        st.subheader("Histórico de Transações")
        for registro in historico:
            st.write(f"""
                **Data:** {registro[1].strftime('%d/%m/%Y %H:%M')}  
                **Casa:** {registro[2]}  
                **Operação:** {registro[3]}  
                **Valor:** R$ {registro[4]:,.2f}  
                **Motivo:** {registro[5]}
            """)
            st.divider()
            
    except Exception as e:
        st.error(f"Erro ao carregar histórico: {str(e)}")