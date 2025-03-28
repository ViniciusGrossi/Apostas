import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from wordcloud import WordCloud
import matplotlib.pyplot as plt
import psycopg2
from dotenv import load_dotenv
import os

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

st.set_page_config(
    page_title="Dashboard de Apostas Esportivas",  
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

# Inicializa o banco de dados
conn = init_db()
if not conn:
    st.stop()
cursor = conn.cursor()

# Função para carregar os dados de apostas
def load_data():
    cursor.execute("""
        SELECT id, data, tipo_aposta, valor_apostado, odd, valor_final, torneio, resultado, 
               casa_de_apostas, categoria, partida, bonus, detalhes
        FROM apostas
    """)
    data = cursor.fetchall()
    columns = ['id', 'data', 'tipo_aposta', 'valor_apostado', 'odd', 'valor_final', 
               'torneio', 'resultado', 'casa_de_apostas', 'categoria', 'partida', 'bonus', 'detalhes']
    df = pd.DataFrame(data, columns=columns)
    
    # Processamento de dados
    df['data'] = pd.to_datetime(df['data'], errors='coerce')
    df['valor_final'] = pd.to_numeric(df['valor_final'], errors='coerce')
    df['resultado'] = df['resultado'].str.strip().str.title()
    df['retorno'] = df['valor_final'] / df['valor_apostado'].replace(0, 1)  # Evitar divisão por zero
    df['odd'] = pd.to_numeric(df['odd'].str.replace(',', ''), errors='coerce')
    df['categoria'] = df['categoria'].str.split(', ')
    df['torneio'] = df['torneio'].str.split(', ')
    
    return df

# Carregar os dados
df = load_data()

# Create tabs
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
    "Visão Geral", "Análise de Mercado", "Análise de Performance", 
    "Análise Temporal", "Estatísticas Avançadas", "Registros Completos",
    "Bônus Combinadas", "Comparação de Casas"
])

# Filtros Globais
st.sidebar.header("Filtros Globais")

# Novo filtro para apostas de hoje
filtrar_hoje = st.sidebar.checkbox("Apenas apostas de hoje")

if filtrar_hoje:
    hoje = datetime.today().date()
    periodo = [hoje, hoje]
else:
    periodo = st.sidebar.date_input(
        "Selecione o período", 
        [df['data'].min().date(), df['data'].max().date()]
    )

tipo_aposta_filter = st.sidebar.multiselect("Tipo de Aposta", df['tipo_aposta'].unique(), default=df['tipo_aposta'].unique())
torneio_filter = st.sidebar.multiselect(
    "Torneio", 
    df['torneio'].explode().unique(), 
    default=df['torneio'].explode().unique())
casa_filter = st.sidebar.multiselect("Casa de Apostas", df['casa_de_apostas'].unique(), default=df['casa_de_apostas'].unique())
resultado_filter = st.sidebar.multiselect(
    "Resultado",
    options=["Ganhou", "Perdeu", "Pendente"],
    default=["Ganhou", "Perdeu"],
    format_func=lambda x: f"{x} ✅" if x == "Ganhou" else f"{x} ❌" if x == "Perdeu" else f"{x} ⏳"
)
categoria_filter = st.sidebar.multiselect(
    "Categoria", 
    df['categoria'].explode().unique(), 
    default=df['categoria'].explode().unique())

# Aplicando filtros
df_filtered = df[
    (df['data'].between(pd.to_datetime(periodo[0]), pd.to_datetime(periodo[1]))) &
    (df['tipo_aposta'].isin(tipo_aposta_filter)) &
    (df['torneio'].apply(lambda tours: any(tour in torneio_filter for tour in tours)) if torneio_filter else True) &
    (df['casa_de_apostas'].isin(casa_filter)) &
    (df['resultado'].isin(resultado_filter)) &
    (df['categoria'].apply(lambda cats: any(cat in categoria_filter for cat in cats)) if categoria_filter else True
)]

with tab1:
    st.subheader("📊 Visão Geral das Apostas")
    
    # =====================================
    # SEÇÃO 1: KPIs PRINCIPAIS
    # =====================================
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        total_apostado = df_filtered['valor_apostado'].sum()
        st.metric("Total Apostado", f"R$ {total_apostado:,.2f}",
                 help="Valor total investido em todas as apostas")
        
    with col2:
        total_ganho = df_filtered[df_filtered['resultado'] == 'Ganhou']['valor_final'].sum()
        st.metric("Total Ganho", f"R$ {total_ganho:+,.2f}",
                 delta_color="off",
                 help="Soma de todos os ganhos líquidos")
        
    with col3:
        total_perdido = df_filtered[df_filtered['resultado'] == 'Perdeu']['valor_final'].sum()
        st.metric("Total Perdido", f"R$ {total_perdido:+,.2f}",
                 delta_color="off",
                 help="Soma de todas as perdas líquidas")
        
    with col4:
        roi = ((total_ganho + total_perdido) / total_apostado * 100) if total_apostado > 0 else 0
        st.metric("ROI (%)", f"{roi:+.1f}%",
                 help="Retorno sobre o investimento total")
        
    with col5:
        qtd_apostas = len(df_filtered)
        taxa_acerto = (len(df_filtered[df_filtered['resultado'] == 'Ganhou']) / qtd_apostas * 100) if qtd_apostas > 0 else 0
        st.metric("Desempenho", 
                 f"{taxa_acerto:.1f}% de Acerto",
                 f"{qtd_apostas} apostas",
                 help="Relação entre apostas ganhas e total de apostas")

    # =====================================
    # SEÇÃO 2: ANÁLISE DE PERFORMANCE
    # =====================================
    st.divider()
    lucro_total = df_filtered['valor_final'].sum()
    cor_lucro = '#2ecc71' if lucro_total >= 0 else '#e74c3c'
    
    st.markdown(f"""
    <div style="
        border: 2px solid {cor_lucro};
        border-radius: 10px;
        padding: 20px;
        text-align: center;
        margin-bottom: 25px;
    ">
        <h2 style="color: {cor_lucro}; margin:0;">
            LUCRO TOTAL: <b>R$ {lucro_total:+,.2f}</b>
        </h2>
        <p style="margin:5px 0 0 0; font-size: 14px;">
            Resultado acumulado de todas as apostas filtradas
        </p>
    </div>
    """, unsafe_allow_html=True)

    st.divider()
    col_a, col_b = st.columns(2)
    
    with col_a:
        # Gráfico de Evolução Temporal
        st.subheader("📈 Evolução do Retorno Acumulado")
        df_temp = df_filtered.sort_values('data').assign(
            retorno_acumulado = lambda x: x['valor_final'].cumsum(),
            media_movel = lambda x: x['valor_final'].rolling(7, min_periods=1).mean()
        )
        
        fig = px.area(df_temp, x='data', y='retorno_acumulado',
                     labels={'retorno_acumulado': 'Retorno Acumulado (R$)'},
                     color_discrete_sequence=['#2ecc71'])
        
        fig.add_scatter(x=df_temp['data'], y=df_temp['media_movel'],
                       mode='lines', name='Média Móvel 7 Dias',
                       line=dict(color='#e67e22'))
        
        st.plotly_chart(fig, use_container_width=True)
        
    with col_b:
        # Gráfico Comparativo por Casa
        st.subheader("🏦 Performance por Casa de Apostas")
        fig = px.bar(df_filtered, 
                    x='casa_de_apostas', 
                    y='valor_final',
                    color='resultado',
                    barmode='group',
                    color_discrete_map={'Ganhou': '#2ecc71', 'Perdeu': '#e74c3c'},
                    labels={'valor_final': 'Resultado Financeiro (R$)'})
        
        st.plotly_chart(fig, use_container_width=True)

    # =====================================
    # SEÇÃO 3: ANÁLISE DE RISCO
    # =====================================
    st.divider()
    col_c, col_d = st.columns(2)
    
    with col_c:
        # Distribuição de Resultados
        st.subheader("🎯 Distribuição de Resultados")
        fig = px.pie(df_filtered, names='resultado', 
                    hole=0.5,
                    color='resultado',
                    color_discrete_map={'Ganhou': '#2ecc71', 'Perdeu': '#e74c3c'})
        fig.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig, use_container_width=True)
        
    with col_d:
        # Análise de Drawdown
        st.subheader("📉 Análise de Risco")
        df_sorted = df_filtered.sort_values('data').assign(
            retorno_acumulado = lambda x: x['valor_final'].cumsum(),
            max_acumulado = lambda x: x['retorno_acumulado'].cummax(),
            drawdown = lambda x: x['retorno_acumulado'] - x['max_acumulado']
        )
        
        fig = px.area(df_sorted, x='data', y=['retorno_acumulado', 'drawdown'],
                     color_discrete_sequence=['#2ecc71', '#e74c3c'],
                     labels={'value': 'Valor (R$)'})
        
        fig.update_layout(showlegend=True,
                         legend_title_text='Métrica',
                         hovermode='x unified')
        
        st.plotly_chart(fig, use_container_width=True)

    # =====================================
    # SEÇÃO 4: ESTATÍSTICAS DETALHADAS
    # =====================================
    st.divider()
    col_e, col_f = st.columns(2)
    
    with col_e:
        st.subheader("📦 Distribuição de Valores Apostados")
        fig = px.histogram(df_filtered, x='valor_apostado',
                          nbins=20,
                          color_discrete_sequence=['#3498db'],
                          labels={'valor_apostado': 'Valor Apostado (R$)'})
        st.plotly_chart(fig, use_container_width=True)
        
    with col_f:
        st.subheader("⚡ Top Performances")
        col_f1, col_f2 = st.columns(2)
        
        with col_f1:
            maior_ganho = df_filtered['valor_final'].max()
            st.metric("Maior Ganho", f"R$ {maior_ganho:,.2f}")
            
        with col_f2:
            maior_perda = df_filtered['valor_final'].min()
            st.metric("Maior Perda", f"R$ {maior_perda:,.2f}")
        
        st.metric("Odd Média das Vencedoras", 
                 f"{df_filtered[df_filtered['resultado'] == 'Ganhou']['odd'].mean():.2f}",
                 help="Média das odds nas apostas vencedoras")
        
    st.subheader("📈 Evolução do Lucro Diário")
    
    # Calcular lucro acumulado por dia
    df_lucro = df_filtered.groupby(pd.Grouper(key='data', freq='D'))['valor_final'].sum().reset_index()
    df_lucro['Lucro Acumulado'] = df_lucro['valor_final'].cumsum()
    
    fig = px.area(df_lucro, 
                 x='data', 
                 y='Lucro Acumulado',
                 labels={'data': 'Data', 'Lucro Acumulado': 'Lucro Total (R$)'},
                 color_discrete_sequence=[cor_lucro])
    
    fig.add_scatter(x=df_lucro['data'], 
                   y=df_lucro['valor_final'],
                   mode='lines+markers',
                   name='Lucro Diário',
                   line=dict(color='#3498db'))
    
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("📌 Comparativo Chave")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("ROI Total", 
                 f"{(lucro_total / df_filtered['valor_apostado'].sum() * 100):+.1f}%",
                 help="Retorno sobre o valor total apostado")
    
    with col2:
        if not df_lucro.empty:
            melhor_dia = df_lucro.loc[df_lucro['valor_final'].idxmax(), 'data'].strftime('%d/%m')
            st.metric("Melhor Dia", melhor_dia, f"R$ {df_lucro['valor_final'].max():+,.2f}")
        else:
            st.metric("Melhor Dia", "N/A", "Sem dados")

    with col3:
        if not df_lucro.empty:
            pior_dia = df_lucro.loc[df_lucro['valor_final'].idxmin(), 'data'].strftime('%d/%m')
            st.metric("Pior Dia", pior_dia, f"R$ {df_lucro['valor_final'].min():+,.2f}")
        else:
            st.metric("Pior Dia", "N/A", "Sem dados")
    
with tab2:

    st.header("📈 Análise Estratégica de Mercado")
    
    # =====================================
    # SEÇÃO 1: MÉTRICAS-CHAVE
    # =====================================
    st.divider()
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_apostas = len(df_filtered)
        st.metric("Total de Apostas", f"{total_apostas}", help="Quantidade total de apostas no período selecionado")
        
    with col2:
        maior_ganho = df_filtered['valor_final'].max()
        st.metric("Maior Ganho Único", f"R$ {maior_ganho:,.2f}", 
                 help="Maior valor líquido positivo em uma única aposta")
        
    with col3:
        maior_perda = df_filtered['valor_final'].min()
        st.metric("Maior Perda Única", f"R$ {maior_perda:+,.2f}", 
                 help="Maior valor líquido negativo em uma única aposta")
        
    with col4:
        odd_media = df_filtered[df_filtered['resultado'] == 'Ganhou']['odd'].mean()
        st.metric("Odd Média das Vencedoras", f"{odd_media:.2f}", 
                 help="Média das odds nas apostas com resultado positivo")

    # =====================================
    # SEÇÃO 2: ANÁLISE DE CATEGORIAS
    # =====================================
    st.divider()
    col_a, col_b = st.columns([2, 1])
    
    with col_a:
        st.subheader("🌐 Distribuição Estratégica por Categoria")
        df_cat = df_filtered.explode('categoria').groupby('categoria', as_index=False).agg({
            'valor_final': 'sum',
            'id': 'count'
        }).rename(columns={'id': 'Qtd Apostas'})
        
        fig = px.treemap(df_cat, 
                        path=['categoria'], 
                        values='Qtd Apostas',
                        color='valor_final',
                        color_continuous_scale='RdYlGn',
                        hover_data=['valor_final'],
                        labels={'valor_final': 'Lucro Total (R$)'})
        
        fig.update_traces(texttemplate="<b>%{label}</b><br>%{value} apostas<br>R$ %{color:.2f}")
        st.plotly_chart(fig, use_container_width=True)
    
    with col_b:
        st.subheader("🏆 Top 5 Categorias")
        df_top = df_cat.nlargest(5, 'valor_final')
        fig = px.bar(df_top, 
                    y='categoria', 
                    x='valor_final',
                    orientation='h',
                    text='valor_final',
                    color='valor_final',
                    color_continuous_scale=['#e74c3c', '#2ecc71'])
        
        fig.update_traces(texttemplate='R$ %{text:.2f}', 
                         textposition='outside',
                         marker_line_width=0)
        
        fig.update_layout(showlegend=False, 
                         yaxis={'categoryorder':'total ascending'},
                         margin=dict(t=30))
        st.plotly_chart(fig, use_container_width=True)

    # =====================================
    # SEÇÃO 3: ANÁLISE DE ODDS
    # =====================================
    st.divider()
    col_c, col_d = st.columns(2)
    
    with col_c:
        st.subheader("🎯 Relação Odd vs Performance")
        fig = px.scatter(
            df_filtered,
            x='odd',
            y='retorno',
            color='resultado',
            size='valor_apostado',
            hover_data=['torneio', 'categoria'],
            color_discrete_map={'Ganhou': '#2ecc71', 'Perdeu': '#e74c3c'},
            labels={'retorno': 'Multiplicador de Retorno'}
        )
        fig.add_hline(y=1, line_dash="dot", line_color="grey")
        st.plotly_chart(fig, use_container_width=True)
        
    with col_d:
        st.subheader("📦 Distribuição de Odds por Resultado")
        fig = px.box(
            df_filtered, 
            x='resultado', 
            y='odd',
            points="all",
            color='resultado',
            color_discrete_map={'Ganhou': '#2ecc71', 'Perdeu': '#e74c3c'},
            labels={'odd': 'Valor da Odd'}
        )
        fig.update_layout(xaxis_title=None)
        st.plotly_chart(fig, use_container_width=True)

    # =====================================
    # SEÇÃO 4: EFICIÊNCIA DAS ESTRATÉGIAS
    # =====================================
    st.divider()
    col_e, col_f = st.columns(2)
    
    with col_e:
        st.subheader("📊 Lucratividade por Tipo de Aposta")
        df_tipo = df_filtered.groupby('tipo_aposta', as_index=False).agg({
            'valor_final': 'sum',
            'id': 'count'
        }).rename(columns={'id': 'volume'})
        
        fig = px.bar(df_tipo, 
                    x='tipo_aposta', 
                    y='valor_final',
                    text='valor_final',
                    color='valor_final',
                    color_continuous_scale='RdYlGn',
                    labels={'valor_final': 'Lucro Total (R$)'})
        
        fig.update_traces(texttemplate='R$ %{text:.2f}', 
                         textposition='outside',
                         marker_line_width=0)
        st.plotly_chart(fig, use_container_width=True)
    
    with col_f:
        st.subheader("⚡ Eficiência por Faixa de Odd")
        bins = [0, 1.5, 2.0, 3.0, 5.0, 20]
        labels = ['Baixo Risco (<1.5)', 'Moderado (1.5-2)', 'Médio (2-3)', 'Alto (3-5)', 'Extremo (>5)']
        
        df_odds = df_filtered.copy()
        df_odds['faixa'] = pd.cut(df_odds['odd'], bins=bins, labels=labels)
        df_odds_group = df_odds.groupby('faixa', observed=False).agg({
            'valor_final': ['sum', 'count'],
            'retorno': 'mean'
        }).reset_index()
        
        df_odds_group.columns = ['Faixa', 'Lucro Total', 'Qtd Apostas', 'Retorno Médio']
        
        fig = px.bar(df_odds_group, 
                    x='Faixa', 
                    y='Lucro Total',
                    color='Retorno Médio',
                    text='Qtd Apostas',
                    color_continuous_scale='RdYlGn',
                    labels={'Lucro Total': 'Lucro Acumulado (R$)'})
        
        fig.update_traces(texttemplate='%{text} apostas', 
                         textposition='inside',
                         marker_line_width=0)
        st.plotly_chart(fig, use_container_width=True)

    # =====================================
    # SEÇÃO 5: ANÁLISE MULTIDIMENSIONAL
    # =====================================
    st.divider()
    st.subheader("🔍 Visão Integrada de Desempenho")
    
    df_multi = df_filtered.explode('categoria').groupby(['categoria', 'tipo_aposta'], as_index=False).agg({
        'valor_final': 'sum',
        'id': 'count',
        'odd': 'mean'
    }).rename(columns={
        'id': 'Volume',
        'odd': 'Odd Média',
        'valor_final': 'Lucro'
    })
    
    fig = px.scatter_3d(
        df_multi,
        x='Volume',
        y='Odd Média',
        z='Lucro',
        color='Lucro',
        size='Volume',
        hover_name='categoria',
        color_continuous_scale='RdYlGn',
        labels={'Volume': 'Quantidade de Apostas'}
    )
    
    fig.update_layout(scene=dict(
        xaxis_title='Volume de Apostas',
        yaxis_title='Odd Média',
        zaxis_title='Lucro Total (R$)'
    ))
    
    st.plotly_chart(fig, use_container_width=True)

with tab3:
    st.header("📊 Análise Avançada de Performance")
    
    # =====================================
    # SEÇÃO 1: VISÃO MULTIDIMENSIONAL
    # =====================================
    st.divider()
    col1, col2 = st.columns([3, 2])
    
    with col1:
        st.subheader("🌐 Relação Tridimensional de Performance")
        df_3d = df_filtered.explode('categoria').explode('torneio')
        
        fig = px.scatter_3d(
            df_3d,
            x='odd',
            y='valor_apostado',
            z='valor_final',
            color='resultado',
            size='valor_apostado',
            hover_name='categoria',
            symbol='torneio',
            opacity=0.7,
            color_discrete_map={'Ganhou': '#2ecc71', 'Perdeu': '#e74c3c'},
            labels={
                'odd': 'Risco (Odd)',
                'valor_apostado': 'Investimento (R$)',
                'valor_final': 'Resultado (R$)'
            }
        )
        
        fig.update_layout(
            scene=dict(
                xaxis_title='<b>ODD</b> (Probabilidade Implícita)',
                yaxis_title='<b>VALOR APOSTADO</b>',
                zaxis_title='<b>RESULTADO FINAL</b>'
            ),
            margin=dict(l=0, r=0, b=0, t=30)
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # =====================================
        # SEÇÃO 2: KPIs COMPORTAMENTAIS
        # =====================================
        st.subheader("📌 Indicadores-Chave")
        
        # Estatísticas de Sequência
        df_surv = df_filtered.sort_values('data')
        df_surv['lucro_positivo'] = df_surv['valor_final'] > 0
        sequencia_atual = df_surv['lucro_positivo'].iloc[-5:].value_counts()
        
        # Layout de métricas
        with st.container():
            col_a, col_b = st.columns(2)
            with col_a:
                strike_rate = df_surv['lucro_positivo'].mean() * 100
                st.metric("Taxa de Acerto Contínuo", f"{strike_rate:.1f}%")
                
            with col_b:
                current_streak = sequencia_atual.idxmax() if not sequencia_atual.empty else 0
                streak_type = "✅ Positiva" if current_streak else "❌ Negativa"
                st.metric("Sequência Atual", streak_type)
        
        # =====================================
        # SEÇÃO 3: PROBABILIDADE TEMPORAL
        # =====================================
        st.subheader("📈 Tendência de Performance")
        df_evolution = df_surv.groupby('data')['lucro_positivo'].expanding().mean().reset_index()
        
        fig = px.area(
            df_evolution,
            x='data',
            y='lucro_positivo',
            labels={'lucro_positivo': 'Probabilidade de Lucro', 'data': 'Data'},
            color_discrete_sequence=['#27ae60']
        )
        
        fig.add_hline(
            y=0.5, 
            line_dash="dot", 
            line_color="grey",
            annotation_text="Linha de Equilíbrio", 
            annotation_position="bottom right"
        )
        
        fig.update_layout(
            yaxis_tickformat=".0%",
            showlegend=False,
            hovermode="x unified"
        )
        st.plotly_chart(fig, use_container_width=True)

        # =====================================
        # SEÇÃO 4: ANÁLISE DE PADRÕES
        # =====================================
        st.subheader("🔍 Padrões de Retorno")
        df_pattern = df_filtered.groupby(
            pd.Grouper(key='data', freq='W-MON')
        )['valor_final'].sum().reset_index()
        
        fig = px.bar(
            df_pattern,
            x='data',
            y='valor_final',
            color='valor_final',
            color_continuous_scale=['#e74c3c', '#2ecc71'],
            labels={'valor_final': 'Lucro Semanal (R$)'}
        )
        
        fig.update_layout(
            xaxis_title="Semana",
            yaxis_title="Resultado Financeiro",
            coloraxis_showscale=False
        )
        st.plotly_chart(fig, use_container_width=True)

    # =====================================
    # SEÇÃO 5: ANÁLISE DE RISCO-RETORNO
    # =====================================
    st.divider()
    st.subheader("⚖️ Relação Risco-Retorno por Categoria")
    
    df_risk = df_filtered.explode('categoria').groupby('categoria', as_index=False).agg({
        'valor_final': 'sum',
        'odd': 'mean',
        'id': 'count'
    }).rename(columns={
        'valor_final': 'Lucro Total',
        'odd': 'Risco Médio',
        'id': 'Volume'
    })
    
    fig = px.scatter(
        df_risk,
        x='Risco Médio',
        y='Lucro Total',
        size='Volume',
        color='Lucro Total',
        hover_name='categoria',
        color_continuous_scale='RdYlGn',
        labels={'Risco Médio': 'Odd Média (↔ Risco)'}
    )
    
    fig.add_vline(
        x=2.0, 
        line_dash="dot", 
        line_color="grey",
        annotation_text="Limite de Risco", 
        annotation_position="top"
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
with tab4:
    st.header("📅 Análise Temporal Estratégica")
    
    # =====================================
    # SEÇÃO 1: HEATMAP DE FREQUÊNCIA
    # =====================================
    st.divider()
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.subheader("🗓️ Padrões de Apostas por Dia/Torneio")
        df_heatmap = df_filtered.copy().explode('torneio')
        
        # Processamento de datas
        df_heatmap['dia_semana'] = df_heatmap['data'].dt.day_name().map({
            'Monday': 'Segunda', 'Tuesday': 'Terça', 'Wednesday': 'Quarta',
            'Thursday': 'Quinta', 'Friday': 'Sexta', 'Saturday': 'Sábado',
            'Sunday': 'Domingo'
        })
        
        # Ordenação personalizada dos dias
        dias_ordenados = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo']
        df_heatmap['dia_semana'] = pd.Categorical(
            df_heatmap['dia_semana'], 
            categories=dias_ordenados, 
            ordered=True
        )
        
        # Criação da matriz de calor
        heat_data = df_heatmap.pivot_table(
            index='dia_semana',
            columns='torneio',
            values='id',
            aggfunc='count',
            fill_value=0
        )
        
        fig = px.imshow(
            heat_data,
            color_continuous_scale='YlGnBu',
            labels=dict(x="Torneio", y="Dia da Semana", color="Apostas"),
            aspect="auto"
        )
        
        fig.update_xaxes(side="top")
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # =====================================
        # SEÇÃO 2: KPIs TEMPORAIS
        # =====================================
        st.subheader("📌 Indicadores Chave")
        
        # Volume Diário Médio
        volume_diario = df_filtered.resample('D', on='data')['id'].count().mean()
        st.metric("Média Diária de Apostas", f"{volume_diario:.1f}")
        
        # Dia de Maior Movimento
        dia_pico = df_filtered['data'].dt.date.value_counts().idxmax()
        st.metric("Dia com Mais Apostas", dia_pico.strftime('%d/%m/%Y'))
        
        # Sazonalidade Semanal
        st.markdown("**Distribuição Semanal:**")
        semana_total = df_heatmap['dia_semana'].value_counts().reindex(dias_ordenados, fill_value=0)
        semana_total.plot(kind='bar', color='#3498db')
        st.pyplot(plt.gcf())
        plt.clf()

    # =====================================
    # SEÇÃO 3: TENDÊNCIAS TEMPORAIS
    # =====================================
    st.divider()
    st.subheader("📈 Evolução Temporal do Desempenho")
    
    col3, col4 = st.columns(2)
    
    with col3:
        # Tendência de Lucro Acumulado
        df_trend = df_filtered.sort_values('data').assign(
            lucro_acumulado = lambda x: x['valor_final'].cumsum(),
            media_movel = lambda x: x['valor_final'].rolling(7, min_periods=1).mean()
        )
        
        fig = px.area(
            df_trend,
            x='data',
            y='lucro_acumulado',
            labels={'lucro_acumulado': 'Lucro Acumulado (R$)'},
            color_discrete_sequence=['#2ecc71']
        )
        
        fig.add_scatter(
            x=df_trend['data'],
            y=df_trend['media_movel'],
            mode='lines',
            name='Média Móvel 7 Dias',
            line=dict(color='#e67e22')
        )
        st.plotly_chart(fig, use_container_width=True)
    
with tab5:
    st.subheader("Estatísticas Avançadas")
    col1, col2 = st.columns(2)
    with col1:
        # Análise de Risco
        st.subheader("📉 Métricas de Risco")
        var_95 = df_filtered['valor_final'].quantile(0.05)
        sharpe = df_filtered['valor_final'].mean() / df_filtered['valor_final'].std() if df_filtered['valor_final'].std() != 0 else 0
        st.metric("Value at Risk (95%)", f"R$ {var_95:.2f}")
        st.metric("Sharpe Ratio", f"{sharpe:.2f}")
        
        # Distribuição de Valores
        fig = px.violin(df_filtered, y='valor_apostado', box=True, points="all")
        st.plotly_chart(fig)
    
    with col2:
        # Correlações
        st.subheader("🔗 Matriz de Correlação")
        numeric_cols = df_filtered.select_dtypes(include='number').columns
        fig = px.imshow(df_filtered[numeric_cols].corr(), text_auto=True)
        st.plotly_chart(fig)

    st.subheader("Mapa de Correlação Interativo")
# Remover registros com valores ausentes nas colunas usadas para o scatter matrix
    df_corr = df_filtered.dropna(subset=['valor_apostado', 'odd', 'valor_final'])
    fig = px.scatter_matrix(
        df_corr, 
        dimensions=['valor_apostado', 'odd', 'valor_final'], 
        color='resultado',
        title="Mapa de Correlação Interativo"
    )
    st.plotly_chart(fig)


        # Nova seção de probabilidade condicional
    st.subheader("🎲 Probabilidade Condicional")
    col_cond1, col_cond2 = st.columns(2)
    
    with col_cond1:
        odd_min = st.number_input("Odd Mínima", value=2.0)
    with col_cond2:
        categoria_alvo = st.selectbox("Categoria Alvo", df['categoria'].explode().unique())
    
    condicao = (df_filtered['odd'] > odd_min) & (df_filtered['categoria'].str.contains(categoria_alvo))
    total_cond = len(df_filtered[condicao])
    acertos_cond = len(df_filtered[condicao & (df_filtered['resultado'] == 'Ganhou')])
    prob = (acertos_cond / total_cond * 100) if total_cond > 0 else 0
    
    st.metric(f"P(Ganhou | Odd > {odd_min} & {categoria_alvo})", f"{prob:.1f}%")

    # Wordcloud de detalhes
    st.subheader("☁️ Palavras-Chave nas Apostas Vencedoras")
    text = ' '.join(df_filtered[df_filtered['resultado'] == 'Ganhou']['detalhes'].astype(str))
    wordcloud = WordCloud(width=800, height=400).generate(text)
    fig, ax = plt.subplots()
    ax.imshow(wordcloud, interpolation='bilinear')
    ax.axis('off')
    st.pyplot(fig)

with tab6:
    st.subheader("Registros Detalhados de Apostas")
    
    # Filtros específicos para a tabela
    col_filtro1, col_filtro2 = st.columns(2)
    with col_filtro1:
        sort_by = st.selectbox("Ordenar por", df_filtered.columns, index=1)
    with col_filtro2:
        sort_order = st.radio("Ordem", ["Ascendente", "Descendente"], horizontal=True)
    
    # Aplicar ordenação
    df_sorted = df_filtered.sort_values(
        by=sort_by, 
        ascending=(sort_order == "Ascendente")
    )
    
    # Formatar colunas numéricas
    styled_df = df_sorted.style.format({
        'valor_apostado': 'R$ {:.2f}',
        'valor_final': 'R$ {:.2f}',
        'odd': '{:.2f}',
        'data': lambda x: x.strftime('%d/%m/%Y')
    })
    
    # Exibir tabela com recursos de busca
    search_term = st.text_input("Buscar em todas as colunas:")
    
    if search_term:
        mask = df_sorted.apply(lambda row: row.astype(str).str.contains(search_term, case=False).any(), axis=1)
        filtered_df = df_sorted[mask]
    else:
        filtered_df = df_sorted
    
    # Paginação
    page_size = st.selectbox("Registros por página", [10, 25, 50, 100], index=0)
    page_number = st.number_input("Página", min_value=1, max_value=int(len(filtered_df)/page_size)+1, value=1)
    
    # Exibir dados paginados
    start_idx = (page_number-1) * page_size
    end_idx = start_idx + page_size
    
    st.dataframe(
        filtered_df.iloc[start_idx:end_idx],
        use_container_width=True,
        column_config={
            "valor_final": st.column_config.NumberColumn(
                "Resultado Financeiro",
                format="R$ %.2f",
                help="Valor positivo = Ganho | Valor negativo = Perda"
            ),
            "detalhes": st.column_config.TextColumn(
                width="large"
            )
        },
        hide_index=True
    )
    
    # Estatísticas rápidas
    st.caption(f"Exibindo {len(filtered_df)} registros filtrados de {len(df)} totais")
    st.download_button(
        label="Exportar para CSV",
        data=filtered_df.to_csv(index=False).encode('utf-8'),
        file_name='registros_apostas.csv',
        mime='text/csv'
    )

with tab7:
    st.header("Visão Estratégica dos Bônus")
    
    # Análise de Bônus
    st.subheader("🎁 Utilização de Bônus")
    bonus_usage = df_filtered.groupby('casa_de_apostas')['bonus'].mean()
    fig = px.bar(bonus_usage, title='Percentual de Bônus por Casa')
    st.plotly_chart(fig)

    # Filtro para apostas com bônus
    df_bonus = df_filtered[df_filtered['bonus'] == 2]  # 2 = bônus combinadas
    
    col1, col2 = st.columns(2)
    with col1:
        fig = px.bar(df_bonus, x='casa_de_apostas', y='valor_final', 
                    title='Lucro por Casa com Bônus')
    
    with col2:
        st.metric("ROI com Bônus", f"{df_bonus['retorno'].mean()*100:.1f}%")

    # KPIs Principais
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        total_bonus = df_bonus['valor_final'].sum()
        st.metric("Lucro Total com Bônus", f"R$ {total_bonus:.2f}", 
                 help="Soma de todos os ganhos/perdas em apostas com bônus")
    
    with col2:
        qtd_bonus = len(df_bonus)
        st.metric("Apostas com Bônus", qtd_bonus)
    
    with col3:
        roi_geral = (df_bonus['valor_final'].sum() / df_bonus['valor_apostado'].sum()) * 100
        st.metric("ROI Geral com Bônus", f"{roi_geral:.1f}%")
    
    with col4:
        st.metric("Melhor Casa", 
                 df_bonus.groupby('casa_de_apostas')['valor_final'].sum().idxmax(),
                 help="Casa com maior lucro em apostas com bônus")

    # ----------------------------
    # SEÇÃO 2: ANÁLISE COMPARATIVA
    # ----------------------------
    st.header("Comparativo Bônus vs Sem Bônus")
    
    # Dados comparativos
    df_comparativo = df_filtered.groupby(df_filtered['bonus'] == 2).agg({
        'valor_final': ['sum', 'mean'],
        'odd': 'mean',
        'id': 'count'
    }).rename(index={True: 'Com Bônus', False: 'Sem Bônus'})

    col1, col2 = st.columns(2)
    with col1:
        st.dataframe(
            df_comparativo.style.format({
                ('valor_final', 'sum'): 'R$ {:.2f}',
                ('valor_final', 'mean'): 'R$ {:.2f}',
                ('odd', 'mean'): '{:.2f}'
            }),
            use_container_width=True
        )
    
    with col2:
        fig = px.bar(df_comparativo, x=df_comparativo.index, y=('valor_final', 'sum'), 
                    title='Lucro Total: Bônus vs Normal',
                    color=df_comparativo.index,
                    labels={'value': 'Valor (R$)'})
        st.plotly_chart(fig)

    # ----------------------------
    # SEÇÃO 3: DESEMPENHO POR CASA
    # ----------------------------
    st.header("Análise por Casa de Apostas")

    # Métricas detalhadas por casa (usando df_bonus)
    df_casas = df_bonus.groupby('casa_de_apostas').agg({
        'valor_final': ['sum', 'mean'],
        'odd': 'mean',
        'id': 'count'
    }).sort_values(('valor_final', 'sum'), ascending=False)

    # Achatar as colunas MultiIndex e resetar o índice
    df_casas.columns = ['valor_final_sum', 'valor_final_mean', 'odd_mean', 'id_count']
    df_casas.reset_index(inplace=True)

    col1, col2 = st.columns([2, 1])
    with col1:
        fig = px.bar(
            df_casas, 
            x='casa_de_apostas', 
            y='valor_final_sum',
            title='Lucro por Casa com Bônus',
            color='valor_final_mean',
            labels={'valor_final_sum': 'Lucro Total (R$)', 'casa_de_apostas': 'Casa de Apostas'}
        )
        st.plotly_chart(fig)

    with col2:
        st.subheader("Top 3 Casas")
        for idx, row in enumerate(df_casas.head(3).itertuples(), 1):
            st.markdown(f"""
            **{idx}º {row.casa_de_apostas}**  
            🏆 Lucro: R$ {row.valor_final_sum:.2f}  
            ⚡ Média/Aposta: R$ {row.valor_final_mean:.2f}  
            🎯 Odd Média: {row.odd_mean:.2f}
            """)

    # ----------------------------
    # SEÇÃO 4: EFICIÊNCIA DOS BÔNUS
    # ----------------------------
    st.header("Eficiência das Apostas com Bônus")
    
    col1, col2 = st.columns(2)
    with col1:
        fig = px.scatter(df_bonus, 
                        x='valor_apostado', 
                        y='valor_final',
                        color='casa_de_apostas',
                        size='odd',
                        title='Relação Valor Apostado x Retorno')
        st.plotly_chart(fig)
    
    with col2:
        fig = px.box(df_bonus, 
                    x='casa_de_apostas', 
                    y='valor_final',
                    title='Distribuição de Resultados por Casa',
                    color='casa_de_apostas')
        st.plotly_chart(fig)

with tab8:

    st.header("🏆 Análise Comparativa entre Casas de Aposta")

# SEÇÃO 1: KPIs COMPARATIVOS
# Cálculo de métricas avançadas
    metricas = df_filtered.groupby('casa_de_apostas').agg({
    'valor_final': ['sum', 'mean', 'max', 'count'],
    'odd': ['mean', 'max'],
    'bonus': ['sum', 'mean'],
    'valor_apostado': 'sum'
}).reset_index()  

# Achatar o MultiIndex e renomear as colunas
    metricas.columns = [
    'casa_de_apostas', 'lucro_total', 'lucro_medio', 'maior_lucro', 'qtd_apostas',
    'odd_media', 'odd_maxima', 'total_bonus', 'freq_bonus', 'total_apostado'
    ]

# Top 3 métricas em cards
    col1, col2, col3 = st.columns(3)
    with col1:
        melhor_idx = metricas['lucro_total'].idxmax()
        melhor_casa = metricas.loc[melhor_idx, 'casa_de_apostas']
        st.metric("🏅 Casa Mais Lucrativa", melhor_casa, 
                help="Maior lucro total acumulado")
        
    with col2:
        maior_idx = metricas['odd_maxima'].idxmax()
        casa_maior_odd = metricas.loc[maior_idx, 'casa_de_apostas']
        maior_odd_valor = metricas.loc[maior_idx, 'odd_maxima']
        st.metric("🎰 Maior Odd Oferecida", casa_maior_odd,
                f"{maior_odd_valor:.2f}")
        
    with col3:
        eficiente_idx = metricas['lucro_medio'].idxmax()
        casa_eficiente = metricas.loc[eficiente_idx, 'casa_de_apostas']
        st.metric("📈 Melhor ROI Médio", casa_eficiente,
                f"R$ {metricas.loc[eficiente_idx, 'lucro_medio']:.2f}/aposta")

    # SEÇÃO 2: VISUALIZAÇÕES ESTRATÉGICAS
    st.header("Análise Visual Comparativa")

    col1, col2 = st.columns(2)

    with col1:
        # Gráfico de Barras Interativo
        fig = px.bar(
            metricas, 
            x='casa_de_apostas',
            y='lucro_total',
            color='lucro_medio',
            title='Lucro Total vs Média por Casa',
            labels={'lucro_total': 'Lucro Total (R$)', 'lucro_medio': 'Média/Aposta'},
            hover_data=['odd_media', 'total_bonus']
        )
        st.plotly_chart(fig)

    # --------------------------------------
    # SEÇÃO 4: TABELA DETALHADA COM INSIGHTS
    # --------------------------------------
    st.header("Relatório Completo")
    
    # Formatação avançada da tabela
    styled_metricas = metricas.style.format({
    'lucro_total': 'R$ {:.2f}',
    'lucro_medio': 'R$ {:.2f}',
    'odd_media': '{:.2f}',
    'total_bonus': '{:.0f} apostas'
    }).highlight_max(subset=['lucro_total', 'lucro_medio'], color='#90EE90').highlight_min(subset=['lucro_total'], color='#ffcccc')
    
    st.dataframe(styled_metricas, 
                column_config={
                     'lucro_total': st.column_config.NumberColumn(  # Nome corrigido
        "Lucro Total",
        help="Soma acumulada de todos os resultados"
    ),
                    'odd_media': st.column_config.NumberColumn(  # Nome corrigido
        "Risco Médio",
        help="Média das odds oferecidas"
    )
                },
                use_container_width=True)

    # --------------------------------------
    # SEÇÃO 5: ANÁLISE DE BÔNUS
    # --------------------------------------
    st.header("Estratégias de Bônus por Casa")
    
    col1, col2 = st.columns(2)
    
    with col1:
        fig = px.pie(df_filtered, 
                    names='casa_de_apostas',
                    values='bonus',
                    title='Distribuição de Apostas com Bônus',
                    hole=0.4)
        st.plotly_chart(fig)
    
    with col2:
        bonus_effect = df_filtered.groupby('casa_de_apostas').apply(
            lambda x: x[x['bonus'] == 2]['valor_final'].mean() / x['valor_final'].mean() * 100
        ).reset_index(name='Eficiência')
        
        fig = px.bar(bonus_effect, 
                    x='casa_de_apostas',
                    y='Eficiência',
                    title='Eficácia dos Bônus (% de Impacto no Lucro)',
                    color='Eficiência')
        st.plotly_chart(fig)