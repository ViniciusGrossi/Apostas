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

# Busca apostas com resultado pendente, incluindo o campo bonus (índice 9)
cursor.execute("""
    SELECT id, data, tipo_aposta, valor_apostado, odd, torneio, partida, detalhes, casa_de_apostas, bonus
    FROM apostas
    WHERE resultado = 'Pendente'
""")
apostas_pendentes = cursor.fetchall()

if not apostas_pendentes:
    st.info("Não há apostas pendentes para atualizar.")
else:
    # Cria uma lista para exibir as apostas pendentes e um mapeamento para recuperá-las
    apostas_list = []
    apostas_mapping = {}
    for aposta in apostas_pendentes:
        # Índices: 0=id, 1=data, 2=tipo_aposta, 3=valor_apostado, 4=odd, 5=torneio,
        # 6=partida, 7=detalhes, 8=casa_de_apostas, 9=bonus
        key = f"Data: {aposta[1]} | Odd(s): {aposta[4]} | Valor: R$ {aposta[3]:.2f} | Tipo: {aposta[2]} | Partida: {aposta[6]} | Casa: {aposta[8]}"
        apostas_list.append(key)
        apostas_mapping[key] = aposta

    st.subheader("Atualizar Resultado da Aposta")
    aposta_selecionada = st.selectbox("Selecione a aposta para atualizar", apostas_list, key="atualiza_select")
    novo_resultado = st.selectbox("Resultado", ["Ganhou", "Perdeu"], key="atualiza_resultado")

    # Recupera a aposta selecionada e define o flag bônus (1 para bônus, 0 para normal)
    aposta = apostas_mapping[aposta_selecionada]
    bonus_flag = (aposta[9] == 1)

    # Processa as odds armazenadas (formato: "1.5, 1.8, 1.72" ou "1.5, 1.8|10")
    odd_str = str(aposta[4])
    if "|" in odd_str:
        odds_partes = odd_str.split("|")
        odds_list = [o.strip() for o in odds_partes[0].split(",") if o.strip() != ""]
        bonus_percent = float(odds_partes[1]) if len(odds_partes) > 1 else 0.0
    else:
        odds_list = [o.strip() for o in odd_str.split(",") if o.strip() != ""]
        bonus_percent = 0.0

    # Widget para selecionar as odds válidas
    odds_validas = st.multiselect("Selecione as odds válidas", options=odds_list, default=odds_list, key="atualiza_odds")

    # Multiplica as odds válidas selecionadas
    multiplicacao_odds = 1
    for o in odds_validas:
        try:
            multiplicacao_odds *= float(o)
        except ValueError:
            st.error("Erro ao converter odds para número.")
            st.stop()

    if bonus_percent > 0:
        fator_bonus = 1 + (bonus_percent / 100)
        multiplicacao_odds *= fator_bonus

    valor_apostado = aposta[3]
    # Cálculo dos valores finais conforme se é bônus ou não
    if bonus_flag:
        computed_ganhou = (valor_apostado * multiplicacao_odds) - valor_apostado
        computed_perdeu = 0
    else:
        computed_ganhou = valor_apostado * (multiplicacao_odds - 1)
        computed_perdeu = -valor_apostado

    # Exibe os valores calculados em três colunas
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Valor Final se Ganhou", f"R$ {computed_ganhou:.2f}")
    with col2:
        st.metric("Valor Final se Perdeu", f"R$ {computed_perdeu:.2f}")
    with col3:
        st.metric("Multiplicação das Odds", f"{multiplicacao_odds:.2f}")

    # Checkbox para indicar se a aposta foi encerrada antes do fim
    aposta_encerrada = st.checkbox("Encerrar Aposta?", key="atualiza_encerrar")
    if aposta_encerrada:
        if novo_resultado == "Ganhou":
            valor_final_override = st.number_input("Valor Final Encerrado", value=computed_ganhou, format="%.2f", key="override_ganhou")
        else:
            valor_final_override = st.number_input("Valor Final Encerrado", value=computed_perdeu, format="%.2f", key="override_perdeu")

    # Botão para atualizar resultado (fluxo de atualização)
    if st.button("Atualizar Resultado", key="botao_atualizar"):
        try:
            # Recupera o ID da aposta selecionada
            aposta = apostas_mapping[aposta_selecionada]
            aposta_id = aposta[0]

            # Define o valor final com base no resultado
            if aposta_encerrada:
                valor_final = valor_final_override
            else:
                if novo_resultado == "Ganhou":
                    valor_final = computed_ganhou
                elif novo_resultado == "Perdeu":
                    valor_final = computed_perdeu

            # Atualiza o resultado da aposta no banco de dados
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE apostas
                SET resultado = %s, valor_final = %s, odd = %s
                WHERE id = %s
            """, (novo_resultado, valor_final, str(multiplicacao_odds), aposta_id))
            conn.commit()

            # ===================================================
            # BLOCO MODIFICADO: Atualização condicional do saldo
            # ===================================================
            casa_de_aposta = aposta[8]
            if novo_resultado == "Ganhou":
                if bonus_flag:
                    # Bônus: adiciona apenas o lucro (valor_final já é líquido)
                    atualizar_saldo_casa(casa_de_aposta, valor_final)
                else:
                    # Aposta normal: adiciona lucro + valor apostado (que foi subtraído no registro)
                    atualizar_saldo_casa(casa_de_aposta, valor_apostado + valor_final)

            st.success("Aposta atualizada com sucesso!")
        except Exception as e:
            st.error(f"Erro ao atualizar aposta: {e}")
            conn.rollback()
    
    time.sleep(2)
    st.rerun()

    # --- Bloco de Reembolso ---
    st.divider()
    st.subheader("⚙️ Reembolso de Aposta")
    reembolso_flag = st.checkbox(
        "Solicitar reembolso total (excluir aposta)",
        help="Marque APENAS se a casa de apostas cancelou a aposta e devolveu o valor integral. Esta ação é irreversível!",
        key="reembolso_flag"
    )
    if reembolso_flag:
        col_reembolso1, col_reembolso2 = st.columns(2)
        with col_reembolso1:
            confirmacao1 = st.checkbox("Confirmo que desejo solicitar reembolso total", key="confirmacao1")
        with col_reembolso2:
            confirmacao2 = st.button("Estou ciente de que essa ação é irreversível", key="confirmacao2")
        if confirmacao1 and confirmacao2:
            try:
                if not bonus_flag:
                    atualizar_saldo_casa(aposta[8], aposta[3])
                aposta = apostas_mapping[aposta_selecionada]
                aposta_id = aposta[0]
                cursor = conn.cursor()
                cursor.execute("DELETE FROM apostas WHERE id = %s", (aposta_id,))
                conn.commit()
                st.success("Aposta removida e reembolso processado com sucesso!")
            except Exception as e:
                st.error(f"Erro ao processar reembolso: {e}")
                conn.rollback()
            time.sleep(2)
            st.rerun()
