import streamlit as st
from datetime import datetime
import time 
from dotenv import load_dotenv
import os
import psycopg2

# Carrega variáveis de ambiente do arquivo .env
load_dotenv()

st.set_page_config(
    page_title="Registro de Apostas Esportivas",
    page_icon=":soccer:",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Função para conectar ao PostgreSQL utilizando o DATABASE_URL do .env
def init_db():
    try:
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            st.error("Variável de ambiente DATABASE_URL não definida")
            return None
        
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()

        # Cria a tabela 'apostas' se não existir
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS apostas (
                id SERIAL PRIMARY KEY,
                data TEXT,
                casa_de_apostas TEXT,
                tipo_aposta TEXT,
                categoria TEXT,
                resultado TEXT,
                valor_apostado REAL,
                odd TEXT, 
                valor_final REAL,
                torneio TEXT,
                partida TEXT,
                detalhes TEXT,
                bonus REAL
            )
        """)
        conn.commit()
        return conn
    except Exception as e:
        st.error(f"Erro de conexão: {e}")
        return None

# Função para subtrair o valor apostado do saldo da casa
def subtrair_saldo_casa(casa_de_aposta, valor_apostado):
    try:
        conn = init_db()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE saldo_casas
            SET saldo = saldo - %s
            WHERE casa_nome = %s
        """, (valor_apostado, casa_de_aposta))
        conn.commit()
    except Exception as e:
        st.error(f"Erro ao subtrair saldo da casa: {e}")
        conn.rollback()

# Inicializa o banco de dados
conn = init_db()

st.title("Registro de Apostas Esportivas")

# Campos de entrada
data = st.date_input("Data da Aposta")
casa_de_aposta = st.selectbox(
    'Casa de Apostas',
    ['Bet 365', 'Betano', 'Betfair', 'Superbet', 'Estrela Bet', '4Play Bet', 'PixBet','Vera Bet', 'Bet7k','Cassino Pix','McGames', 'Aposta Ganha'
     'Aposta tudo','Novibet', 'Sporting Bet','KTO','Stake', 'LotoGreen','BR Bet','Rei do Pitaco','Bulls Bet','BR4 Bet', 'Casa de Apostas',
     'Bateu Bet', 'Betnacional', 'Jogue Facil', 'Jogo de Ouro','H2 Bet', 'Pagol','MetGol','UxBet',
     'Seu Bet', 'Bet Esporte', 'BetFast', 'Faz1Bet', 'Esportiva Bet', 'Betpix365',
     'Seguro Bet', 'Outros'],
)
tipo_aposta = st.selectbox(
    "Tipo de Aposta",
    ["Simples", "Dupla", "Tripla", "Múltipla", "Super Odd"],
    placeholder="Selecione o tipo de aposta"
)
categoria = st.multiselect(
    "Categoria da Aposta",
    ['Resultado', 'Finalizações', 'Escanteios', 'HT','FT', 'Gols', 'Chutes ao Gol',
     'Ambas Equipes','Faltas cometidas', 'Faltas Sofridas', 'Cartões','Defesas', 'Desarmes', 
     'Handicap','Tiro de Linha','Impedimentos', 'Outros'],
    placeholder="Selecione as categorias de apostas"
)
valor_apostado = st.number_input(
    "Valor Apostado (R$)",
    min_value=0.0,
    format="%.2f",
    placeholder="Digite o valor apostado"
)
odd = st.text_input("Odd", placeholder="Digite as odds. Decimal . e Separador de Odd ,")
bonus_combinadas_flag = st.checkbox("Aplicar Bônus Combinadas")
bonus_percent = 0.0
if bonus_combinadas_flag:
    bonus_percent = st.number_input(
        "Porcentagem do Bônus (%)",
        min_value=0.0,
        max_value=100.0,
        value=10.0,
        step=0.1,
        format="%.1f",
        help="Ex: 10% aumenta as odds em 10% da combinada"
    )

torneio = st.multiselect(
    "Torneio",
    ['Brasileirão A', 'Champions League', 'Europa League', 'Conference League', 'Premier League',
     'La Liga', 'Bundesliga', 'Serie A', 'Ligue 1', 'Copa do Brasil', 'Serie B', 'Brasileirão B',
     'Championship', 'Pro Saudi League', 'Torneo Betano', 'Libertadores', 'Sul-Americana', 'FA Cup',
     'Liga Portugal', 'Super Lig', 'Estaduais', 'Outros'],
    placeholder="Selecione o torneio"
)
partida = st.text_input("Partida", placeholder="Digite a partida")
detalhes_aposta = st.text_area("Detalhes da Aposta", placeholder="Dê detalhes do que foi a aposta")

# Resultado inicialmente pendente
resultado = "Pendente"
valor_final = None

bonus_flag = st.checkbox("Aposta Bônus?")

if st.button("Salvar Aposta"):
    try:
        # Processar as odds
        odds_list = [float(s.strip().replace(",", ".")) for s in odd.split(",") if s.strip() != ""]
        if len(odds_list) == 0:
            st.error("Por favor, insira ao menos uma odd.")
            st.stop()
        
        # Multiplicação das odds
        multiplicacao_odds = 1
        for o in odds_list:
            multiplicacao_odds *= o
            
        # Aplicar bônus de combinadas
        if bonus_combinadas_flag and bonus_percent > 0:
            fator_bonus = 1 + (bonus_percent / 100)
            multiplicacao_odds *= fator_bonus

        # Cálculo do valor_final (lucro líquido)
        if resultado == "Ganhou":
            if bonus_flag:
                valor_final = (valor_apostado * multiplicacao_odds) - valor_apostado
            else:
                valor_final = valor_apostado * (multiplicacao_odds - 1)
        elif resultado == "Perdeu":
            if bonus_flag:
                valor_final = 0
            else:
                valor_final = -valor_apostado
        else:
            valor_final = 0

        if not bonus_flag:
            subtrair_saldo_casa(casa_de_aposta, valor_apostado)

        # Inserção no banco
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO apostas (
                data, casa_de_apostas, tipo_aposta, categoria, resultado, bonus, 
                valor_apostado, odd, valor_final, torneio, partida, detalhes
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            data.strftime("%Y-%m-%d"),
            casa_de_aposta,
            tipo_aposta,
            ", ".join(categoria) if categoria else "",
            resultado,
            1 if bonus_flag else (2 if bonus_combinadas_flag else 0),
            valor_apostado,
            f"{', '.join(map(str, odds_list))}|{bonus_percent}" if bonus_combinadas_flag else ", ".join(map(str, odds_list)),
            valor_final,
            ", ".join(torneio) if torneio else "",
            partida,
            detalhes_aposta
        ))
        conn.commit()
        st.success("Aposta salva com sucesso!")
        
    except Exception as e:
        st.error(f"Erro ao salvar aposta: {e}")
        conn.rollback()
    
    time.sleep(2)
    st.rerun()

try:
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM apostas ORDER BY id DESC")
    apostas = cursor.fetchall()
    
except Exception as e:
    st.error(f"Erro ao carregar apostas: {e}")
