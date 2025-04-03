import streamlit as st
import psycopg2
from datetime import datetime
import time
from dotenv import load_dotenv
import os

# Carrega variáveis de ambiente do arquivo .env
load_dotenv()

# Configuração da página com tema personalizado
st.set_page_config(
    page_title="Registro de Apostas Esportivas",
    page_icon=":soccer:",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilos CSS personalizados para melhorar a aparência
st.markdown("""
    <style>
        /* Estilo global */
        .stApp {
            background-color: #0e1117;
            color: #e0e0e0;
        }
        
        /* Estilos para cabeçalhos */
        h1, h2, h3 {
            color: #4adede !important;
            font-weight: 600 !important;
            padding-bottom: 10px;
        }
        
        /* Estilo para o título principal */
        .main-title {
            background: linear-gradient(90deg, #4adede, #2e7eff);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-size: 2.5rem !important;
            margin-bottom: 20px !important;
            text-align: center;
            padding: 10px;
        }
        
        /* Estilo para cards e containers */
        .resumo-box {
            border: 2px solid #2e4a7a;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 30px;
            background: linear-gradient(145deg, #121824, #0e1117);
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
        }
        
        .resumo-title {
            color: #4adede !important;
            border-bottom: 1px solid #2e4a7a;
            padding-bottom: 10px;
            font-size: 1.4rem !important;
            font-weight: 500;
        }
        
        /* Estilo para métricas */
        .metric-container {
            background: rgba(17, 25, 40, 0.7);
            border-radius: 8px;
            padding: 15px;
            border-left: 4px solid #4adede;
            margin-top: 10px;
        }
        
        /* Estilo para seletores e inputs */
        div[data-baseweb="select"] {
            background-color: #1c2536 !important;
            border-radius: 8px !important;
            border: 1px solid #2e4a7a !important;
        }
        
        .stSelectbox, .stMultiSelect {
            background-color: #1c2536 !important;
        }
        
        /* Estilo para botões */
        .stButton > button {
            border-radius: 8px !important;
            font-weight: 600 !important;
            transition: all 0.3s ease !important;
        }
        
        .btn-primary {
            background: linear-gradient(90deg, #4adede, #2e7eff) !important;
            color: white !important;
            border: none !important;
        }
        
        .btn-primary:hover {
            box-shadow: 0 0 15px rgba(74, 222, 222, 0.5) !important;
            transform: translateY(-2px) !important;
        }
        
        .btn-secondary {
            background-color: #2e4a7a !important;
            color: white !important;
            border: none !important;
        }
        
        .btn-danger {
            background-color: #a92d2d !important;
            color: white !important;
            border: none !important;
        }
        
        /* Estilo para divisores */
        hr {
            border-color: #2e4a7a !important;
            margin: 25px 0 !important;
        }
        
        /* Estilo para expanders */
        .stExpander {
            border: 1px solid #2e4a7a !important;
            border-radius: 8px !important;
            background-color: #121824 !important;
        }
        
        /* Animações */
        @keyframes pulse {
            0% { box-shadow: 0 0 0 0 rgba(74, 222, 222, 0.4); }
            70% { box-shadow: 0 0 0 10px rgba(74, 222, 222, 0); }
            100% { box-shadow: 0 0 0 0 rgba(74, 222, 222, 0); }
        }
        
        .pulse-animation {
            animation: pulse 2s infinite;
        }
        
        /* Status de bônus */
        .bonus-active {
            color: #4adede;
            font-weight: bold;
        }
        
        .bonus-inactive {
            color: #a92d2d;
        }
        
        /* Layout para detalhes de aposta */
        .aposta-card {
            background: rgba(17, 25, 40, 0.7);
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 15px;
        }
        
        /* Status badges */
        .status-badge {
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 0.8rem;
            font-weight: bold;
        }
        
        .status-pendente {
            background-color: #ffa726;
            color: #000;
        }
        
        .status-ganhou {
            background-color: #4caf50;
            color: #fff;
        }
        
        .status-perdeu {
            background-color: #f44336;
            color: #fff;
        }
    </style>
""", unsafe_allow_html=True)

# Função para conectar ao PostgreSQL utilizando o DATABASE_URL
@st.cache_resource
def init_db():
    try:
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            st.error("Variável de ambiente DATABASE_URL não definida")
            return None
        conn = psycopg2.connect(database_url)
        return conn
    except Exception as e:
        st.error(f"Erro de conexão: {e}")
        return None

# Função para atualizar o saldo da casa de apostas
def atualizar_saldo_casa(casa_de_aposta, valor):
    try:
        conn = init_db()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE saldo_casas
            SET saldo = saldo + %s
            WHERE casa_nome = %s
        """, (valor, casa_de_aposta))
        conn.commit()
    except Exception as e:
        st.error(f"Erro ao atualizar saldo da casa: {e}")
        conn.rollback()

# Inicializa o banco de dados
conn = init_db()
if not conn:
    st.stop()
cursor = conn.cursor()

# Título principal com estilo aprimorado
st.markdown('<h1 class="main-title">📊 Atualização de Resultados de Apostas</h1>', unsafe_allow_html=True)

# =============================================
# Seção de Resumo Estilizado
# =============================================
with st.container():
    st.markdown('<div class="resumo-box">', unsafe_allow_html=True)
    
    # Consulta o total de apostas pendentes
    cursor.execute("""
        SELECT 
            SUM(valor_apostado) as total,
            COUNT(*) as quantidade
        FROM apostas 
        WHERE resultado = 'Pendente'
    """)
    resumo = cursor.fetchone()
    total = resumo[0] or 0.0
    quantidade = resumo[1] or 0

    st.markdown('<p class="resumo-title">📊 Resumo das Apostas Pendentes</p>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        st.markdown('<div class="metric-container">', unsafe_allow_html=True)
        st.metric(
            label="Valor Total em Risco",
            value=f"R$ {total:,.2f}",
            help="Soma de todas as apostas não resolvidas"
        )
        st.markdown('</div>', unsafe_allow_html=True)
    with col2:
        st.markdown('<div class="metric-container">', unsafe_allow_html=True)
        st.metric(
            label="Apostas Pendentes",
            value=quantidade,
            help="Quantidade total de apostas em aberto"
        )
        st.markdown('</div>', unsafe_allow_html=True)
    with col3:
        st.empty()  # Espaço reservado para futura expansão
    
    st.markdown('</div>', unsafe_allow_html=True)

# =============================================
# Listagem e Atualização de Apostas
# =============================================
cursor.execute("""
    SELECT id, data, tipo_aposta, valor_apostado, odd, torneio, partida, detalhes, casa_de_apostas, bonus
    FROM apostas
    WHERE resultado = 'Pendente'
    ORDER BY data DESC
""")
apostas_pendentes = cursor.fetchall()

if not apostas_pendentes:
    st.markdown("""
        <div style="text-align:center; padding:50px; background:rgba(17, 25, 40, 0.7); border-radius:10px; margin:20px 0;">
            <img src="https://www.svgrepo.com/show/407462/check-mark.svg" width="80" style="opacity:0.6; margin-bottom:20px;">
            <h3 style="color:#e0e0e0;">Não há apostas pendentes para atualizar.</h3>
            <p style="color:#aaaaaa;">Todas as apostas já foram processadas ou não existem apostas registradas.</p>
        </div>
    """, unsafe_allow_html=True)
else:
    with st.container():
        st.markdown('<div class="resumo-box">', unsafe_allow_html=True)
        st.subheader("Seleção de Aposta")
        
        apostas_list = []
        apostas_mapping = {}
        for aposta in apostas_pendentes:
            key = f"📅 {aposta[1]} | 🏆 {aposta[5]} | 🎮 {aposta[6]} | 💰 R$ {aposta[3]:.2f} | {aposta[2]} | {aposta[8]}"
            apostas_list.append(key)
            apostas_mapping[key] = aposta

        aposta_selecionada = st.selectbox("Selecione a aposta para atualizar", apostas_list, key="atualiza_select")

        # Botão de detalhes
        if 'show_details' not in st.session_state:
            st.session_state.show_details = False

        col1, col2 = st.columns([3, 1])
        with col1:
            if st.button("🔍 Mostrar Detalhes Completos", key="btn_detalhes", help="Exibe informações detalhadas sobre a aposta selecionada"):
                st.session_state.show_details = not st.session_state.show_details
        
        with col2:
            total_apostas = len(apostas_list)
            st.markdown(f"<div style='text-align:right;padding-top:8px;'><span class='status-badge status-pendente'>Total: {total_apostas} apostas</span></div>", unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)

    if st.session_state.show_details:
        aposta = apostas_mapping[aposta_selecionada]
        with st.container():
            st.markdown('<div class="resumo-box">', unsafe_allow_html=True)
            st.markdown('<h3 style="margin-top:0;">📋 Detalhes da Aposta</h3>', unsafe_allow_html=True)
            
            # Layout em grid para mostrar detalhes
            col1, col2, col3 = st.columns([2, 2, 1])
            with col1:
                st.markdown(f"**🆔 ID:** {aposta[0]}")
                st.markdown(f"**📅 Data:** {aposta[1]}")
                st.markdown(f"**🎯 Tipo:** {aposta[2]}")
                st.markdown(f"**💰 Valor Apostado:** R$ {aposta[3]:.2f}")
            with col2:
                st.markdown(f"**🏆 Torneio:** {aposta[5]}")
                st.markdown(f"**⚽ Partida:** {aposta[6]}")
                st.markdown(f"**🏢 Casa de Apostas:** {aposta[8]}")
                bonus_status = '✅ Ativo' if aposta[9] == 1 else '❌ Inativo'
                bonus_class = 'bonus-active' if aposta[9] == 1 else 'bonus-inactive'
                st.markdown(f"**🎁 Bônus:** <span class='{bonus_class}'>{bonus_status}</span>", unsafe_allow_html=True)
            with col3:
                odd_str = str(aposta[4])
                if "|" in odd_str:
                    odds_partes = odd_str.split("|")
                    odds_list = [o.strip() for o in odds_partes[0].split(",")]
                else:
                    odds_list = [o.strip() for o in odd_str.split(",")]
                
                st.markdown("**📈 Odds:**")
                for odd in odds_list:
                    st.markdown(f"• {odd}")
            
            # Detalhes adicionais em expander
            with st.expander("📝 Detalhes Adicionais", expanded=False):
                detalhes = aposta[7] or "Sem detalhes adicionais"
                st.markdown(f"```{detalhes}```")
            
            st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="resumo-box">', unsafe_allow_html=True)
    st.subheader("⚙️ Configuração do Resultado")

    # Layout de duas colunas para a configuração
    col1, col2 = st.columns(2)
    
    with col1:
        # Seleção de resultado com ícones
        resultado_options = ["Ganhou", "Perdeu"]
        resultado_icons = ["✅ Ganhou", "❌ Perdeu"]
        novo_resultado = st.selectbox(
            "Resultado Final", 
            options=range(len(resultado_options)),
            format_func=lambda x: resultado_icons[x],
            key="atualiza_resultado"
        )
        novo_resultado = resultado_options[novo_resultado]
    
    # Processamento das odds
    aposta = apostas_mapping[aposta_selecionada]
    odd_str = str(aposta[4])
    bonus_flag = aposta[9] == 1

    if "|" in odd_str:
        odds_partes = odd_str.split("|")
        odds_list = [o.strip() for o in odds_partes[0].split(",")]
    else:
        odds_list = [o.strip() for o in odd_str.split(",")]

    with col2:
        # Seleção de odds válidas
        odds_validas = st.multiselect(
            "Selecione as odds válidas para cálculo",
            options=odds_list,
            default=odds_list,
            key="atualiza_odds"
        )

    # Cálculo da multiplicação
    multiplicacao_odds = 1
    for o in odds_validas:
        multiplicacao_odds *= float(o)

    # Sistema de bônus no lucro
    with st.container():
        st.markdown('<div style="background:rgba(17, 25, 40, 0.7); border-radius:8px; padding:15px; margin-top:15px; border-left:4px solid #ffd700;">', unsafe_allow_html=True)
        st.markdown("**⚡ Ajustes de Bônus**")
        bonus_lucro = st.checkbox("Aplicar bônus sobre o lucro", key="bonus_check")
        bonus_percent = 0.0
        if bonus_lucro:
            bonus_percent = st.slider(
                "Percentual de bônus (%)",
                min_value=0.0,
                max_value=100.0,
                value=25.0,
                step=0.5,
                format="%.1f%%",
                key="bonus_slider"
            )
        st.markdown('</div>', unsafe_allow_html=True)

    # Cálculos financeiros
    valor_apostado = aposta[3]
    lucro_bruto = valor_apostado * (multiplicacao_odds - 1)
    
    if bonus_lucro and bonus_percent > 0:
        lucro_liquido = lucro_bruto * (1 + bonus_percent/100)
    else:
        lucro_liquido = lucro_bruto

    valor_final_ganhou = valor_apostado + lucro_liquido
    computed_perdeu = -valor_apostado if not bonus_flag else 0

    # Exibição dos resultados
    st.markdown("<h3 style='margin-top:20px;'>💵 Projeção Financeira</h3>", unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        st.markdown('<div class="metric-container" style="border-left:4px solid #4caf50;">', unsafe_allow_html=True)
        st.metric(
            "Retorno Total se Ganhar", 
            f"R$ {valor_final_ganhou:.2f}",
            delta=f"Lucro: R$ {lucro_liquido:.2f}" if lucro_liquido > 0 else None
        )
        st.markdown('</div>', unsafe_allow_html=True)
    with col2:
        st.markdown('<div class="metric-container" style="border-left:4px solid #f44336;">', unsafe_allow_html=True)
        st.metric(
            "Perda Total se Perder", 
            f"R$ {computed_perdeu:.2f}",
            delta_color="inverse"
        )
        st.markdown('</div>', unsafe_allow_html=True)

    # Sistema de encerramento antecipado
    st.markdown("<h3 style='margin-top:20px;'>🔄 Opções Avançadas</h3>", unsafe_allow_html=True)
    aposta_encerrada = st.checkbox("Encerramento Antecipado (Cashout)", key="cashout_check")
    if aposta_encerrada:
        valor_final_override = st.number_input(
            "Valor do Cashout",
            min_value=0.0,
            value=float(valor_final_ganhou),
            format="%.2f",
            key="cashout_input"
        )
        # Adiciona uma mini calculadora de diferença
        diferenca = valor_final_override - valor_apostado
        if diferenca > 0:
            st.markdown(f"<div style='color:#4caf50;'>Lucro calculado: R$ {diferenca:.2f}</div>", unsafe_allow_html=True)
        elif diferenca < 0:
            st.markdown(f"<div style='color:#f44336;'>Perda calculada: R$ {diferenca:.2f}</div>", unsafe_allow_html=True)
        else:
            st.markdown("<div style='color:#ffd700;'>Valor neutro (sem ganho/perda)</div>", unsafe_allow_html=True)

    # Botão de atualização
    st.markdown("<div style='margin-top:30px;'></div>", unsafe_allow_html=True)
    col1, col2 = st.columns([3, 2])
    with col1:
        if st.button("✅ Confirmar Atualização", key="btn_atualizar", type="primary", help="Confirmar e salvar o resultado da aposta"):
            try:
                aposta_id = apostas_mapping[aposta_selecionada][0]
                
                if aposta_encerrada:
                    valor_final = valor_final_override - valor_apostado
                else:
                    valor_final = lucro_liquido if novo_resultado == "Ganhou" else computed_perdeu

                # Atualiza o banco de dados
                cursor.execute("""
                    UPDATE apostas
                    SET resultado = %s, valor_final = %s, odd = %s
                    WHERE id = %s
                """, (novo_resultado, valor_final, str(multiplicacao_odds), aposta_id))
                conn.commit()

                # Atualiza o saldo da casa
                casa = apostas_mapping[aposta_selecionada][8]
                if novo_resultado == "Ganhou":
                    ajuste = valor_apostado + valor_final if not bonus_flag else valor_final
                    atualizar_saldo_casa(casa, ajuste)

                # Mensagem de sucesso animada
                st.markdown("""
                    <div class="pulse-animation" style="background-color: rgba(76, 175, 80, 0.2); border-radius: 10px; padding: 20px; text-align: center; border: 1px solid #4caf50;">
                        <h3 style="color: #4caf50; margin: 0;">✅ Resultado atualizado com sucesso!</h3>
                    </div>
                """, unsafe_allow_html=True)
                
                time.sleep(1.5)
                st.rerun()
            except Exception as e:
                st.error(f"Erro na atualização: {str(e)}")
                conn.rollback()

    # Seção de reembolso
    st.markdown("<div style='margin-top:30px;'></div>", unsafe_allow_html=True)
    with st.expander("🚨 Solicitar Reembolso Total", expanded=False):
        st.markdown("""
            <div style="background-color: rgba(244, 67, 54, 0.1); border-radius: 8px; padding: 15px; border-left: 4px solid #f44336;">
                <h4 style="color: #f44336; margin-top: 0;">Atenção!</h4>
                <p>Esta ação é irreversível e deve ser usada apenas para cancelamentos totais da aposta.</p>
            </div>
        """, unsafe_allow_html=True)
        
        reembolso_check = st.checkbox("Confirmar reembolso integral", key="reembolso_check")
        if reembolso_check:
            if st.button("🗑️ Excluir Aposta e Reembolsar", key="btn_reembolso", help="Cancela a aposta e devolve o valor apostado à casa"):
                try:
                    aposta_id = apostas_mapping[aposta_selecionada][0]
                    casa = apostas_mapping[aposta_selecionada][8]
                    valor_apostado = apostas_mapping[aposta_selecionada][3]
                    
                    cursor.execute("DELETE FROM apostas WHERE id = %s", (aposta_id,))
                    if not bonus_flag:
                        atualizar_saldo_casa(casa, valor_apostado)
                    conn.commit()
                    
                    # Mensagem de sucesso animada
                    st.markdown("""
                        <div class="pulse-animation" style="background-color: rgba(33, 150, 243, 0.2); border-radius: 10px; padding: 20px; text-align: center; border: 1px solid #2196f3;">
                            <h3 style="color: #2196f3; margin: 0;">✅ Reembolso processado com sucesso!</h3>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    time.sleep(1.5)
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro no reembolso: {str(e)}")
                    conn.rollback()
    
    st.markdown('</div>', unsafe_allow_html=True)