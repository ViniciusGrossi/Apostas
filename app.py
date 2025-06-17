import streamlit as st
from datetime import datetime
import time 
from dotenv import load_dotenv
import os
import psycopg2

# Carrega variáveis de ambiente do arquivo .env
load_dotenv()

# Configuração da página com tema personalizado
st.set_page_config(
    page_title="Registro de Apostas Esportivas",
    page_icon="🎲",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Aplicando CSS personalizado para melhorar a aparência
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1E88E5;
        text-align: center;
        margin-bottom: 1rem;
        padding-bottom: 0.5rem;
        border-bottom: 2px solid #1E88E5;
    }
    .section-header {
        font-size: 1.4rem;
        color: #333;
        margin-top: 1rem;
        margin-bottom: 0.5rem;
        padding-bottom: 0.2rem;
        border-bottom: 1px solid #ddd;
    }
    .success-message {
        padding: 10px;
        background-color: #D4EDDA;
        border-radius: 5px;
        margin-top: 20px;
    }
    .stSelectbox, .stMultiSelect {
        margin-bottom: 10px;
    }
    .stButton button {
        background-color: #1E88E5;
        color: white;
        font-weight: bold;
        border-radius: 5px;
        padding: 0.5rem 1rem;
        width: 100%;
    }
    .stButton button:hover {
        background-color: #1565C0;
    }
    .stDateInput, .stNumberInput, .stTextInput, .stTextArea {
        margin-bottom: 10px;
    }
    div[data-testid="stSidebarUserContent"] {
        padding: 1rem;
    }
</style>
""", unsafe_allow_html=True)

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

# Título principal com estilo melhorado
st.markdown('<h1 class="main-header">📊 Registro de Apostas Esportivas</h1>', unsafe_allow_html=True)

# Criando abas para melhor organização
tab1, tab2 = st.tabs(["📝 Nova Aposta", "📋 Apostas Registradas"])

with tab1:
    # Organizando em colunas para melhor layout
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown('<h3 class="section-header">Informações Básicas</h3>', unsafe_allow_html=True)
        
        data = st.date_input(
            "📅 Data da Aposta",
            help="Selecione a data em que a aposta foi realizada"
        )
        
        casas_de_apostas = [
            'Bet 365', 'Betano', 'Betfair', 'Superbet', 'Estrela Bet', 
            '4Play Bet', 'PixBet', 'Vera Bet', 'Bet7k', 'Cassino Pix',  'Bet MGM',
            'McGames', 'Aposta Ganha', 'Aposta tudo', 'Novibet', 'Sporting Bet',
            'KTO', 'Stake', 'LotoGreen', 'BR Bet', 'Rei do Pitaco',
            'Bulls Bet', 'BR4 Bet', 'Casa de Apostas', 'Bateu Bet', 
            'Betnacional', 'Jogue Facil', 'Jogo de Ouro', 'H2 Bet', 
            'Pagol', 'MetGol', 'UxBet', 'HiperBet', 'Seu Bet', 
            'Bet Esporte', 'BetFast', 'Faz1Bet', 'Esportiva Bet', 
            'Betpix365', 'Seguro Bet', 'Outros'
        ]
        
        casa_de_aposta = st.selectbox(
            '🏢 Casa de Apostas',
            options=casas_de_apostas,
            help="Selecione a casa de apostas onde a aposta foi realizada"
        )
        
        tipos_aposta = ["Simples", "Dupla", "Tripla", "Múltipla", "Super Odd"]
        tipo_aposta = st.selectbox(
            "🎯 Tipo de Aposta",
            options=tipos_aposta,
            help="Selecione o tipo de aposta realizada"
        )
        
        categorias_aposta = [
            'Resultado', 'Finalizações', 'Escanteios', 'HT', 'FT', 
            'Gols', 'Chutes ao Gol', 'Ambas Equipes', 'Faltas cometidas', 
            'Faltas Sofridas', 'Cartões', 'Defesas', 'Desarmes', 
            'Handicap', 'Tiro de Linha', 'Impedimentos', 'Desempenho', 'Outros'
        ]
        
        categoria = st.multiselect(
            "🔍 Categoria da Aposta",
            options=categorias_aposta,
            help="Selecione todas as categorias aplicáveis a esta aposta"
        )
    
    with col2:
        st.markdown('<h3 class="section-header">Detalhes da Aposta</h3>', unsafe_allow_html=True)
        
        valor_apostado = st.number_input(
            "💰 Valor Apostado (R$)",
            min_value=0.0,
            format="%.2f",
            help="Digite o valor apostado em reais"
        )
        
        odd = st.text_input(
            "🔢 Odd", 
            placeholder="Digite as odds. Decimal . e Separador de Odd ,",
            help="Digite as odds separadas por vírgula (ex: 1.5, 2.3)"
        )
        
        # Agrupando os componentes relacionados a bônus
        st.markdown('<h4 style="font-size: 1.1rem; color: #555;">Opções de Bônus</h4>', unsafe_allow_html=True)
        
        col_bonus1, col_bonus2 = st.columns(2)
        with col_bonus1:
            bonus_combinadas_flag = st.checkbox(
                "🎁 Aplicar Bônus Combinadas",
                help="Marque para aplicar bônus em apostas combinadas"
            )
        with col_bonus2:
            bonus_flag = st.checkbox(
                "🎁 Aposta Bônus?",
                help="Marque se esta é uma aposta com bônus promocional"
            )
        
        if bonus_combinadas_flag:
            bonus_percent = st.number_input(
                "Porcentagem do Bônus (%)",
                min_value=0.0,
                max_value=100.0,
                value=25.0,
                step=0.1,
                format="%.1f",
                help="Ex: 10% aumenta as odds em 10% da combinada"
            )
        else:
            bonus_percent = 0.0
    
    # Nova linha para informações de torneio/partida
    st.markdown('<h3 class="section-header">Informações do Evento</h3>', unsafe_allow_html=True)
    
    col3, col4 = st.columns(2)
    
    with col3:
        torneios = [
            'Brasileirão A', 'Champions League', 'Europa League', 'Conference League', 
            'Premier League', 'La Liga', 'Bundesliga', 'Serie A', 'Ligue 1', 'Mundial de Clubes',
            'Copa do Brasil', 'Serie B', 'Brasileirão B', 'Championship', 
            'Pro Saudi League', 'Torneo Betano', 'Libertadores', 'Sul-Americana', 
            'FA Cup', 'Liga Portugal', 'Super Lig', 'Estaduais', 'Data Fifa', 'Outros'
        ]
        
        torneio = st.multiselect(
            "🏆 Torneio",
            options=torneios,
            help="Selecione o(s) torneio(s) relacionado(s) à aposta"
        )
        
        partida = st.text_input(
            "⚽ Partida", 
            placeholder="Ex: Barcelona vs Real Madrid",
            help="Digite o nome das equipes/participantes"
        )
    
    with col4:
        detalhes_aposta = st.text_area(
            "📝 Detalhes da Aposta", 
            placeholder="Dê detalhes específicos da aposta...",
            help="Inclua informações adicionais sobre a aposta"
        )
    
    # Resultado inicialmente pendente
    resultado = "Pendente"
    valor_final = None
    
    # Botão de salvar com estilo melhorado
    if st.button("💾 SALVAR APOSTA", use_container_width=True):
        try:
            # Feedback visual durante o processamento
            with st.spinner("Processando..."):
                # Processar as odds
                odds_list = [float(s.strip().replace(",", ".")) for s in odd.split(",") if s.strip() != ""]
                if len(odds_list) == 0:
                    st.error("⚠️ Por favor, insira ao menos uma odd.")
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
                
                # Mensagem de sucesso personalizada
                st.markdown(
                    f"""
                    <div class="success-message">
                        ✅ <b>Aposta salva com sucesso!</b><br>
                        📅 Data: {data.strftime("%d/%m/%Y")}<br>
                        🏢 Casa: {casa_de_aposta}<br>
                        💰 Valor: R$ {valor_apostado:.2f}
                    </div>
                    """, 
                    unsafe_allow_html=True
                )
                
                time.sleep(1)
                st.rerun()
            
        except Exception as e:
            st.error(f"❌ Erro ao salvar aposta: {e}")
            conn.rollback()

with tab2:
    st.markdown('<h3 class="section-header">Histórico de Apostas</h3>', unsafe_allow_html=True)
    
    # Adicionando filtros para o histórico
    filtro_col1, filtro_col2, filtro_col3 = st.columns(3)
    
    with filtro_col1:
        filtro_resultado = st.selectbox(
            "Filtrar por resultado",
            options=["Todos", "Pendente", "Ganhou", "Perdeu"],
            index=0
        )
    
    with filtro_col2:
        filtro_casa = st.selectbox(
            "Filtrar por casa de apostas",
            options=["Todas"] + casas_de_apostas,
            index=0
        )
    
    with filtro_col3:
        filtro_data = st.date_input(
            "Filtrar por data",
            value=None,
            help="Deixe vazio para ver todas as datas"
        )
    
    try:
        cursor = conn.cursor()
        
        # Base da consulta SQL
        query = "SELECT * FROM apostas WHERE 1=1"
        params = []
        
        # Aplicar filtros se selecionados
        if filtro_resultado != "Todos":
            query += " AND resultado = %s"
            params.append(filtro_resultado)
            
        if filtro_casa != "Todas":
            query += " AND casa_de_apostas = %s"
            params.append(filtro_casa)
            
        if filtro_data:
            query += " AND data = %s"
            params.append(filtro_data.strftime("%Y-%m-%d"))
            
        query += " ORDER BY id DESC"
        
        # Executar a consulta com os filtros
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
            
        apostas = cursor.fetchall()
        
        if apostas:
            # Exibindo em formato de tabela estilizada
            st.markdown(
                """
                <style>
                .dataframe {
                    font-size: 0.9rem;
                    border-collapse: collapse;
                    width: 100%;
                }
                .dataframe th {
                    background-color: #f1f1f1;
                    padding: 8px;
                    text-align: left;
                    border-bottom: 2px solid #ddd;
                    color: #1E88E5;
                    font-weight: 600; 
                }
                .dataframe td {
                    padding: 8px;
                    border-bottom: 1px solid #ddd;
                }
                .dataframe tr:nth-child(even) {
                    background-color: #f0f0f0;  
                    color: #333;                
                }
                .ganhou {
                    color: green;
                    font-weight: bold;
                }
                .perdeu {
                    color: red;
                }
                .pendente {
                    color: orange;
                }
                </style>
                """, 
                unsafe_allow_html=True
            )
            
            # Definindo colunas para a visualização
            colunas = ["ID", "Data", "Casa", "Tipo", "Valor (R$)", "Odd", "Resultado", "Partida"]
            
            # Preparando os dados
            dados = []
            for a in apostas:
                # Formatando o resultado com cor
                if a[5] == "Ganhou":
                    resultado_format = f'<span class="ganhou">{a[5]}</span>'
                elif a[5] == "Perdeu":
                    resultado_format = f'<span class="perdeu">{a[5]}</span>'
                else:
                    resultado_format = f'<span class="pendente">{a[5]}</span>'
                
                dados.append([
                    a[0],  # ID
                    datetime.strptime(a[1], "%Y-%m-%d").strftime("%d/%m/%Y") if a[1] else "",  # Data formatada
                    a[2],  # Casa de apostas
                    a[3],  # Tipo de aposta
                    f"{a[6]:.2f}",  # Valor apostado formatado
                    a[7],  # Odd
                    resultado_format,  # Resultado formatado
                    a[10]  # Partida
                ])
            
            # Exibindo a tabela
            st.markdown(
                f"""
                <table class="dataframe">
                    <thead>
                        <tr>{''.join([f'<th>{col}</th>' for col in colunas])}</tr>
                    </thead>
                    <tbody>
                        {''.join([f'<tr>{"".join([f"<td>{cell}</td>" for cell in linha])}</tr>' for linha in dados])}
                    </tbody>
                </table>
                """, 
                unsafe_allow_html=True
            )
            
            # Estatísticas resumidas
            st.markdown('<h3 class="section-header">Estatísticas</h3>', unsafe_allow_html=True)
            
            # Calculando estatísticas
            total_apostas = len(apostas)
            total_apostado = sum(a[6] for a in apostas if a[6] is not None)
            
            # Exibindo estatísticas em cards
            stat_col1, stat_col2, stat_col3 = st.columns(3)
            
            with stat_col1:
                st.markdown(
                    f"""
                    <div style="padding: 1rem; background-color: #f0f7ff; border-radius: 0.5rem; text-align: center;">
                        <h3 style="margin-bottom: 0.5rem; color: #1E88E5;">Total de Apostas</h3>
                        <p style="font-size: 1.8rem; font-weight: bold; margin: 0;">{total_apostas}</p>
                    </div>
                    """, 
                    unsafe_allow_html=True
                )
            
            with stat_col2:
                st.markdown(
                    f"""
                    <div style="padding: 1rem; background-color: #fff4e6; border-radius: 0.5rem; text-align: center;">
                        <h3 style="margin-bottom: 0.5rem; color: #FF9800;">Valor Total Apostado</h3>
                        <p style="font-size: 1.8rem; font-weight: bold; margin: 0;">R$ {total_apostado:.2f}</p>
                    </div>
                    """, 
                    unsafe_allow_html=True
                )
            
            with stat_col3:
                st.markdown(
                    f"""
                    <div style="padding: 1rem; background-color: #f3f3f3; border-radius: 0.5rem; text-align: center;">
                        <h3 style="margin-bottom: 0.5rem; color: #555;">Valor Médio por Aposta</h3>
                        <p style="font-size: 1.8rem; font-weight: bold; margin: 0;">R$ {(total_apostado/total_apostas if total_apostas > 0 else 0):.2f}</p>
                    </div>
                    """, 
                    unsafe_allow_html=True
                )
        else:
            st.info("Nenhuma aposta encontrada com os filtros aplicados.")
        
    except Exception as e:
        st.error(f"Erro ao carregar apostas: {e}")

# Adiciona um footer
st.markdown(
    """
    <div style="text-align: center; margin-top: 3rem; padding-top: 1rem; border-top: 1px solid #ddd; color: #777;">
        <p>Sistema de Registro de Apostas Esportivas © 2025</p>
    </div>
    """, 
    unsafe_allow_html=True
)