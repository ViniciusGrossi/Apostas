import streamlit as st
import psycopg2
from datetime import datetime
import time
from dotenv import load_dotenv
import os

# Carrega variáveis de ambiente do arquivo .env
load_dotenv()

st.set_page_config(
    page_title="Registro de Apostas Esportivas",
    page_icon=":soccer:",
    layout="wide",
    initial_sidebar_state="expanded"
)

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

st.title("Atualizar Resultado das Apostas")

# =============================================
# Seção de Resumo Estilizado
# =============================================
st.markdown("""
    <style>
        .resumo-box {
            border: 2px solid #2e4a7a;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 30px;
            background: #0e1117;
        }
        .resumo-title {
            color: #4adede !important;
            border-bottom: 1px solid #2e4a7a;
            padding-bottom: 10px;
        }
    </style>
""", unsafe_allow_html=True)

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
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric(
            label="Valor Total em Risco",
            value=f"R$ {total:,.2f}",
            help="Soma de todas as apostas não resolvidas"
        )
    with col2:
        st.metric(
            label="Apostas Pendentes",
            value=quantidade,
            help="Quantidade total de apostas em aberto"
        )
    
    st.markdown('</div>', unsafe_allow_html=True)

# =============================================
# Listagem e Atualização de Apostas
# =============================================
cursor.execute("""
    SELECT id, data, tipo_aposta, valor_apostado, odd, torneio, partida, detalhes, casa_de_apostas, bonus
    FROM apostas
    WHERE resultado = 'Pendente'
""")
apostas_pendentes = cursor.fetchall()

if not apostas_pendentes:
    st.info("Não há apostas pendentes para atualizar.")
else:
    apostas_list = []
    apostas_mapping = {}
    for aposta in apostas_pendentes:
        key = f"Data: {aposta[1]} | Odd(s): {aposta[4]} | Valor: R$ {aposta[3]:.2f} | Tipo: {aposta[2]} | Partida: {aposta[6]} | Casa: {aposta[8]}"
        apostas_list.append(key)
        apostas_mapping[key] = aposta

    st.subheader("Seleção de Aposta")
    aposta_selecionada = st.selectbox("Selecione a aposta para atualizar", apostas_list, key="atualiza_select")

    # Botão de detalhes
    if 'show_details' not in st.session_state:
        st.session_state.show_details = False

    if st.button("🔍 Mostrar Detalhes Completos", key="btn_detalhes"):
        st.session_state.show_details = not st.session_state.show_details

    if st.session_state.show_details:
        aposta = apostas_mapping[aposta_selecionada]
        with st.expander("📋 Detalhes da Aposta", expanded=True):
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**ID:** {aposta[0]}")
                st.markdown(f"**Data:** {aposta[1]}")
                st.markdown(f"**Tipo:** {aposta[2]}")
                st.markdown(f"**Valor Apostado:** R$ {aposta[3]:.2f}")
            with col2:
                st.markdown(f"**Torneio:** {aposta[5]}")
                st.markdown(f"**Partida:** {aposta[6]}")
                st.markdown(f"**Casa de Apostas:** {aposta[8]}")
                st.markdown(f"**Status Bônus:** {'✅ Ativo' if aposta[9] == 1 else '❌ Inativo'}")
            st.markdown(f"**Detalhes Adicionais:** {aposta[7] or 'Sem detalhes adicionais'}")

    st.divider()
    st.subheader("Configuração do Resultado")

    # Seleção de resultado
    novo_resultado = st.selectbox("Resultado Final", ["Ganhou", "Perdeu"], key="atualiza_resultado")

    # Processamento das odds
    aposta = apostas_mapping[aposta_selecionada]
    odd_str = str(aposta[4])
    bonus_flag = aposta[9] == 1

    if "|" in odd_str:
        odds_partes = odd_str.split("|")
        odds_list = [o.strip() for o in odds_partes[0].split(",")]
    else:
        odds_list = [o.strip() for o in odd_str.split(",")]

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
    col1, col2 = st.columns(2)
    with col1:
        st.metric(
            "Retorno Total se Ganhar", 
            f"R$ {valor_final_ganhou:.2f}",
            delta=f"Lucro: R$ {lucro_liquido:.2f}" if lucro_liquido > 0 else None
        )
    with col2:
        st.metric(
            "Perda Total se Perder", 
            f"R$ {computed_perdeu:.2f}",
            delta_color="inverse"
        )

    # Sistema de encerramento antecipado
    st.divider()
    aposta_encerrada = st.checkbox("Encerramento Antecipado (Cashout)", key="cashout_check")
    if aposta_encerrada:
        valor_final_override = st.number_input(
            "Valor do Cashout",
            min_value=0.0,
            value=float(valor_final_ganhou),
            format="%.2f",
            key="cashout_input"
        )

    # Botão de atualização
    if st.button("✅ Confirmar Atualização", key="btn_atualizar", type="primary"):
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

            st.success("Resultado atualizado com sucesso!")
            time.sleep(1.5)
            st.rerun()
        except Exception as e:
            st.error(f"Erro na atualização: {str(e)}")
            conn.rollback()

    # Seção de reembolso
    st.divider()
    with st.expander("🚨 Solicitar Reembolso Total", expanded=False):
        st.warning("Esta ação é irreversível e deve ser usada apenas para cancelamentos totais.")
        if st.checkbox("Confirmar reembolso integral"):
            if st.button("🗑️ Excluir Aposta e Reembolsar"):
                try:
                    cursor.execute("DELETE FROM apostas WHERE id = %s", (aposta_id,))
                    if not bonus_flag:
                        atualizar_saldo_casa(casa, valor_apostado)
                    conn.commit()
                    st.success("Reembolso processado com sucesso!")
                    time.sleep(1.5)
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro no reembolso: {str(e)}")
                    conn.rollback()