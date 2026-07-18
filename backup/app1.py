import os
import streamlit as st
import pandas as pd
import base64
from datetime import datetime, date
import calendar
import numpy as np

st.set_page_config(layout="wide", page_title="Masson Lava Jato")

if "inicio" not in st.session_state:
    st.session_state["inicio"] = True

# ========== PREÇOS ==========
def calcular_valor(tipo, servico):
    if not tipo or not servico:
        return 0
    if servico == "Ducha":
        return 30
    elif servico == "Lavagem de Motor":
        return 80
    elif servico == "Chaci":
        return 90
    elif servico == "Lavagem de Moto":
        return 35
    elif servico == "Completa":
        return {"Comum": 250, "SUV": 300, "Caminhonete": 330}.get(tipo, 0)
    elif servico == "Simples":
        return {"Comum": 90, "SUV": 120, "Caminhonete": 150}.get(tipo, 0)
    return 0

# ========== CARREGA IMAGEM ==========
caminho = "imagem/lj.jpeg"
img_fundo = ""
if os.path.exists(caminho):
    with open(caminho, "rb") as f:
        img_fundo = base64.b64encode(f.read()).decode()

# ========== CSS PROFISSIONAL EXECUTIVO ==========
css = """
<style>
    /* Reset e fontes */
    #MainMenu, footer, header {visibility: hidden;}
    .main .block-container {max-width: 100%; padding: 1rem 2rem;}

    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    /* Background */
    .stApp {
        background: linear-gradient(135deg, #f0f2f5 0%, #e8ecf1 100%);
    }

    /* Cards */
    .card-executivo {
        background: white;
        border-radius: 16px;
        padding: 1.5rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04);
        margin-bottom: 1rem;
        border: 1px solid rgba(0,0,0,0.04);
        transition: box-shadow 0.2s ease;
    }
    .card-executivo:hover {
        box-shadow: 0 4px 12px rgba(0,0,0,0.08), 0 2px 4px rgba(0,0,0,0.04);
    }
    .card-executivo h3, .card-executivo h4 {
        margin-top: 0;
        color: #1a1a2e;
        font-weight: 600;
        font-size: 1.1rem;
        letter-spacing: -0.01em;
    }

    /* KPI Cards */
    .kpi-card {
        background: white;
        border-radius: 14px;
        padding: 1.2rem 1.5rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.06);
        border: 1px solid rgba(0,0,0,0.04);
        text-align: center;
        transition: transform 0.15s ease;
    }
    .kpi-card:hover { transform: translateY(-2px); }
    .kpi-label {
        font-size: 0.8rem;
        color: #7c7c8a;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        margin-bottom: 0.3rem;
    }
    .kpi-value {
        font-size: 1.8rem;
        font-weight: 700;
        color: #1a1a2e;
        letter-spacing: -0.02em;
    }
    .kpi-value.green { color: #10b981; }
    .kpi-value.yellow { color: #f59e0b; }
    .kpi-value.red { color: #ef4444; }

    /* Semáforo gerencial */
    .semaforo-verde { border-left: 4px solid #10b981 !important; }
    .semaforo-amarelo { border-left: 4px solid #f59e0b !important; }
    .semaforo-vermelho { border-left: 4px solid #ef4444 !important; }

    /* Botões */
    .stButton button {
        padding: 0 1.5rem !important;
        height: 48px !important;
        font-size: 1rem !important;
        font-weight: 600 !important;
        border-radius: 12px !important;
        border: none !important;
        background: linear-gradient(135deg, #2563eb, #1d4ed8) !important;
        color: white !important;
        transition: all 0.2s ease !important;
        box-shadow: 0 2px 8px rgba(37,99,235,0.2) !important;
    }
    .stButton button:hover {
        transform: translateY(-1px) !important;
        box-shadow: 0 4px 16px rgba(37,99,235,0.3) !important;
    }
    .stButton button[kind="secondary"] {
        background: white !important;
        color: #2563eb !important;
        border: 1px solid #2563eb !important;
        box-shadow: none !important;
    }

    /* Inputs */
    .stTextInput input, .stSelectbox select, .stNumberInput input {
        border-radius: 10px !important;
        border: 1px solid #e0e4ea !important;
        padding: 0.6rem 0.8rem !important;
        font-size: 0.95rem !important;
    }
    .stTextInput input:focus, .stSelectbox select:focus, .stNumberInput input:focus {
        border-color: #2563eb !important;
        box-shadow: 0 0 0 3px rgba(37,99,235,0.1) !important;
    }

    /* Abas */
    .stTabs [data-baseweb="tab-list"] {
        gap: 1rem;
        background: transparent;
        border-bottom: 1px solid #e5e7eb;
        padding-bottom: 0;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 10px 10px 0 0;
        padding: 0.7rem 1.3rem;
        font-weight: 500;
        font-size: 0.95rem;
        color: #6b7280;
        transition: all 0.15s ease;
    }
    .stTabs [aria-selected="true"] {
        background: white !important;
        color: #2563eb !important;
        font-weight: 600;
        box-shadow: 0 -2px 0 #2563eb inset;
    }

    /* DataFrame */
    .stDataFrame {
        border-radius: 12px;
        overflow: hidden;
        border: 1px solid #e5e7eb;
    }
    .stDataFrame thead tr th {
        background: #f8fafc;
        font-weight: 600;
        font-size: 0.8rem;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        color: #6b7280;
        padding: 0.6rem 0.8rem;
    }

    /* Métricas */
    div[data-testid="stMetric"] {
        background: white;
        border-radius: 12px;
        padding: 1rem 1.2rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
        border: 1px solid #e5e7eb;
    }
    div[data-testid="stMetric"] > div:first-child {
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #7c7c8a;
        font-weight: 500;
    }
    div[data-testid="stMetric"] [data-testid="stMetricValue"] {
        font-size: 1.6rem;
        font-weight: 700;
        color: #1a1a2e;
    }

    /* Expander */
    .streamlit-expanderHeader {
        font-weight: 600;
        color: #1a1a2e;
        border-radius: 10px;
        background: white;
        border: 1px solid #e5e7eb;
        padding: 0.7rem 1rem;
    }
    .streamlit-expanderContent {
        border: 1px solid #e5e7eb;
        border-top: none;
        border-radius: 0 0 10px 10px;
        padding: 1rem;
        background: white;
    }

    /* Seção Insights */
    .insight-card {
        background: white;
        border-radius: 14px;
        padding: 1.2rem 1.5rem;
        border: 1px solid #e5e7eb;
        margin-bottom: 0.8rem;
        transition: all 0.2s ease;
    }
    .insight-card:hover {
        border-color: #2563eb;
        box-shadow: 0 2px 8px rgba(37,99,235,0.08);
    }
    .insight-tag {
        display: inline-block;
        font-size: 0.7rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        padding: 0.2rem 0.6rem;
        border-radius: 6px;
        margin-bottom: 0.4rem;
    }
    .insight-tag.oportunidade { background: #d1fae5; color: #065f46; }
    .insight-tag.atencao { background: #fef3c7; color: #92400e; }
    .insight-tag.risco { background: #fee2e2; color: #991b1b; }
    .insight-tag.destaque { background: #dbeafe; color: #1e40af; }

    /* Separador */
    hr {
        margin: 1.5rem 0;
        border: none;
        height: 1px;
        background: linear-gradient(90deg, transparent, #e0e4ea, transparent);
    }

    /* Voltar */
    .btn-voltar {
        position: fixed;
        top: 1rem;
        left: 1rem;
        z-index: 9999;
        background: white;
        border: none;
        color: #2563eb;
        font-size: 1.1rem;
        font-weight: 600;
        cursor: pointer;
        padding: 0.5rem 1.2rem;
        border-radius: 10px;
        box-shadow: 0 1px 4px rgba(0,0,0,0.08);
        transition: 0.2s;
    }
    .btn-voltar:hover {
        box-shadow: 0 2px 8px rgba(0,0,0,0.12);
        background: #f8fafc;
    }
</style>"""

if st.session_state["inicio"] and img_fundo:
    css += ".stApp {background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);}"

css += """</style>"""

st.markdown(css, unsafe_allow_html=True)

# TELA INICIAL
if st.session_state["inicio"]:
    # Imagem como HTML puro, não como CSS
    if img_fundo:
        st.markdown(f"""
        <div style="position:fixed; top:0; left:0; width:100%; height:100%; z-index:0;
                    display:flex; align-items:center; justify-content:center; 
                    background:linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);">
            <img src="data:image/jpeg;base64,{img_fundo}"
                 style="max-width:80%; max-height:80%; object-fit:contain; opacity:0.9; border-radius:16px;
                        box-shadow: 0 20px 60px rgba(0,0,0,0.5);">
        </div>
        """, unsafe_allow_html=True)

    st.markdown("""
    <style>
    .stButton {
        position: fixed;
        bottom: 3rem;
        left: 50%;
        transform: translateX(-50%);
        z-index: 9999;
        text-align: center;
    }
    .stButton button {
        padding: 1rem 3rem !important;
        height: auto !important;
        font-size: 1.5rem !important;
        font-weight: 700 !important;
        border-radius: 16px !important;
        background: linear-gradient(135deg, #2563eb, #1d4ed8) !important;
        color: white !important;
        border: none !important;
        box-shadow: 0 4px 24px rgba(37,99,235,0.4) !important;
        transition: all 0.3s ease !important;
    }
    .stButton button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 32px rgba(37,99,235,0.5) !important;
    }
    .main .block-container {padding-top: 0 !important;}
    /* Esconde elementos do Streamlit na tela inicial */
    header {display: none !important;}
    </style>
    """, unsafe_allow_html=True)

    if st.button("🧼 Acessar Dashboard", key="btn_inicio"):
        st.session_state["inicio"] = False
        st.rerun()
    st.stop()

# ========== NAVEGAÇÃO SUPERIOR ==========
col_nav1, col_nav2 = st.columns([1, 11])
with col_nav1:
    if st.button("⬅️ Voltar", key="btn_voltar_topo"):
        st.session_state["inicio"] = True
        st.rerun()

# ========== HEADER ==========
st.markdown("""
<div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:1.5rem;">
    <div>
        <span style="font-size:0.75rem; letter-spacing:0.18em; color:#9CA3AF; text-transform:uppercase; font-weight:500;">Masson Lava Jato</span>
        <h1 style="margin:0.2rem 0 0 0; font-size:1.8rem; font-weight:700; color:#1a1a2e; letter-spacing:-0.02em;">🧼 Painel Executivo</h1>
    </div>
    <div style="text-align:right;">
        <span style="font-size:0.75rem; color:#9CA3AF;">Atualizado</span><br>
        <span style="font-size:0.85rem; font-weight:600; color:#1a1a2e;">""" + datetime.now().strftime("%d/%m/%Y %H:%M") + """</span>
    </div>
</div>
""", unsafe_allow_html=True)

# 
# FUNÇÕES AUXILIARES
# 
def carregar_lavagens():
    try:
        df = pd.read_excel("dados.xlsx")
        return df
    except:
        return pd.DataFrame()

def carregar_mensalistas():
    try:
        df = pd.read_excel("mensalistas.xlsx")
        return df
    except:
        return pd.DataFrame()

# 
# ABAS
# 
aba1, aba2, aba3 = st.tabs(["📝 Registrar Lavagem", "📋 Mensalistas", "📊 Análises Executivas"])

# 
# ABA 1 - REGISTRAR LAVAGEM
# 
with aba1:
    st.markdown('<div class="card-executivo">', unsafe_allow_html=True)
    st.markdown("### 📝 Novo Registro de Lavagem")
    st.markdown("---")

    col1, col2, col3 = st.columns(3)

    with col1:
        tipo = st.selectbox("Tipo de Veículo *", ["", "Comum", "SUV", "Caminhonete", "Moto"], key="tipo_lav")

    with col2:
        if tipo == "Moto":
            opcoes = ["Lavagem de Moto"]
        elif tipo in ["Comum", "SUV", "Caminhonete"]:
            opcoes = ["Completa", "Simples", "Ducha", "Lavagem de Motor", "Chaci"]
        else:
            opcoes = [""]
        servico = st.selectbox("Serviço *", opcoes, key="servico_lav")

    with col3:
        valor = calcular_valor(tipo, servico)
        st.metric("Valor do Serviço", f"R$ {valor:.2f}")

    with st.form("form_lavagem", clear_on_submit=True):
        col_date, col_nome, col_placa = st.columns(3)
        with col_date:
            data_registro = st.date_input("📅 Data", value=datetime.now(), format="DD/MM/YYYY")
        with col_nome:
            nome = st.text_input("👤 Nome do Cliente (opcional)").upper()
        with col_placa:
            placa = st.text_input("🚗 Placa do Veículo").upper()

        col_qtd = st.columns(1)[0]
        with col_qtd:
            quantidade = st.number_input("🔢 Quantidade", min_value=1, max_value=999, value=1, step=1)

        submit = st.form_submit_button("💾 Salvar Lavagem", use_container_width=True)

        if submit:
            erros = []
            if not tipo:
                erros.append("Selecione o Tipo de Veículo")
            if not servico:
                erros.append("Selecione o Serviço")

            if erros:
                for e in erros:
                    st.warning(f"⚠️ {e}")
            else:
                valor_final = calcular_valor(tipo, servico)
                novos_registros = []

                for i in range(quantidade):
                    nome_linha = nome.strip() if nome.strip() else f"{tipo} #{i+1}"
                    novos_registros.append({
                        "Data": data_registro.strftime("%d/%m/%Y"),
                        "Nome": nome_linha,
                        "Placa": placa.strip() if placa.strip() else "—",
                        "Tipo": tipo,
                        "Serviço": servico,
                        "Valor": valor_final
                    })

                try:
                    df = pd.read_excel("dados.xlsx")
                except:
                    df = pd.DataFrame()

                df = pd.concat([df, pd.DataFrame(novos_registros)], ignore_index=True)
                df.to_excel("dados.xlsx", index=False)

                total_geral = valor_final * quantidade
                st.success(f"✅ **{quantidade}x** {tipo} - **{servico}** registrado(s)! Total: **R$ {total_geral:.2f}**")
    st.markdown('</div>', unsafe_allow_html=True)

    # ========== HISTÓRICO ==========
    st.markdown('<div class="card-executivo">', unsafe_allow_html=True)
    st.markdown("### 📋 Histórico de Lavagens")

    col_data_filtro, col_btn_limpar = st.columns([3, 1])
    with col_data_filtro:
        data_filtro = st.date_input("📅 Filtrar por data", value=None, format="DD/MM/YYYY", key="filtro_data")
    with col_btn_limpar:
        if data_filtro and st.button("❌ Limpar filtro"):
            data_filtro = None
            st.rerun()

    df_lavagens = carregar_lavagens()
    if not df_lavagens.empty:
        if data_filtro:
            df_filtrado = df_lavagens[df_lavagens["Data"] == data_filtro.strftime("%d/%m/%Y")]
        else:
            df_filtrado = df_lavagens

        if not df_filtrado.empty:
            total = df_filtrado["Valor"].sum()
            qtd = len(df_filtrado)

            col_m1, col_m2, col_m3 = st.columns(3)
            col_m1.metric(f"Lavagens{' do dia' if data_filtro else ' - Total'}", qtd)
            col_m2.metric("Faturamento", f"R$ {total:.2f}")
            col_m3.metric("Ticket Médio", f"R$ {total/qtd:.2f}" if qtd > 0 else "R$ 0")

            df_exibir = df_filtrado.copy()
            df_exibir["Valor"] = df_exibir["Valor"].apply(lambda x: f"R$ {x:.2f}")
            st.dataframe(df_exibir, use_container_width=True)
        else:
            st.info("Nenhuma lavagem encontrada para esta data.")
    else:
        st.info("Nenhuma lavagem registrada ainda.")
    st.markdown('</div>', unsafe_allow_html=True)

# 
# ABA 2 - MENSALISTAS
# 
with aba2:
    try:
        df_m = pd.read_excel("mensalistas.xlsx")
        if "Telefone" in df_m.columns:
            df_m["Telefone"] = df_m["Telefone"].astype(str)
    except:
        df_m = pd.DataFrame(columns=[
            "ID", "Nome", "Telefone", "Tipo", "Placa",
            "Plano", "Valor", "Lavagens Inclusas",
            "Lavagens Realizadas", "Início", "Status"
        ]).astype({"Telefone": str})

    def novo_id():
        if df_m.empty or "ID" not in df_m.columns or df_m["ID"].empty:
            return 1
        return int(df_m["ID"].max()) + 1

    # Cards resumo no topo
    col_card1, col_card2, col_card3, col_card4 = st.columns(4)
    with col_card1:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">Total Cadastrados</div>
            <div class="kpi-value">{len(df_m)}</div>
        </div>
        """, unsafe_allow_html=True)
    with col_card2:
        ativos = len(df_m[df_m["Status"] == "Ativo"]) if not df_m.empty else 0
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">Ativos</div>
            <div class="kpi-value green">{ativos}</div>
        </div>
        """, unsafe_allow_html=True)
    with col_card3:
        inativos = len(df_m[df_m["Status"] == "Inativo"]) if not df_m.empty else 0
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">Inativos</div>
            <div class="kpi-value red">{inativos}</div>
        </div>
        """, unsafe_allow_html=True)
    with col_card4:
        total_receita = df_m[df_m["Status"] == "Ativo"]["Valor"].sum() if not df_m.empty else 0
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">Receita Mensal (Ativos)</div>
            <div class="kpi-value">R$ {total_receita:.2f}</div>
        </div>
        """, unsafe_allow_html=True)

    # Cadastro
    with st.expander("➕ Adicionar Novo Mensalista", expanded=False):
        st.markdown('<div style="padding:0.5rem 0;">', unsafe_allow_html=True)
        with st.form("form_mensalista"):
            col_m1, col_m2 = st.columns(2)
            with col_m1:
                m_nome = st.text_input("Nome *").upper()
                m_tel = st.text_input("Telefone")
                m_tipo = st.selectbox("Tipo de Veículo", ["Comum", "SUV", "Caminhonete", "Moto"])
            with col_m2:
                m_placa = st.text_input("Placa").upper()
                m_plano = st.selectbox("Plano", ["Valor Fixo Mensal", "Pacote de Lavagens"])
                if m_plano == "Valor Fixo Mensal":
                    m_valor = st.number_input("Valor Mensal (R$)", min_value=0.0, step=10.0, format="%.2f")
                    m_qtd = 0
                else:
                    col_v, col_q = st.columns(2)
                    with col_v:
                        m_valor = st.number_input("Valor do Pacote (R$)", min_value=0.0, step=10.0, format="%.2f")
                    with col_q:
                        m_qtd = st.number_input("Lavagens Inclusas", min_value=1, step=1, value=4)

            m_inicio = st.date_input("Data de Início", value=datetime.now(), format="DD/MM/YYYY")

            submit_m = st.form_submit_button("💾 Cadastrar Mensalista", use_container_width=True)

            if submit_m:
                if not m_nome.strip():
                    st.warning("⚠️ Preencha o Nome do Mensalista")
                else:
                    novo_m = {
                        "ID": novo_id(),
                        "Nome": m_nome.strip(),
                        "Telefone": m_tel.strip(),
                        "Tipo": m_tipo,
                        "Placa": m_placa.strip() if m_placa.strip() else "—",
                        "Plano": m_plano,
                        "Valor": m_valor,
                        "Lavagens Inclusas": m_qtd,
                        "Lavagens Realizadas": 0,
                        "Início": m_inicio.strftime("%d/%m/%Y"),
                        "Status": "Inativo"
                    }
                    df_m = pd.concat([df_m, pd.DataFrame([novo_m])], ignore_index=True)
                    df_m.to_excel("mensalistas.xlsx", index=False)
                    st.success(f"✅ Mensalista **{m_nome.strip()}** cadastrado com sucesso!")
                    st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    # Lista com ações
    st.markdown("### 📋 Lista de Mensalistas")

    if not df_m.empty:
        col_filtro_status, _ = st.columns([1, 3])
        with col_filtro_status:
            filtro_status = st.selectbox("Filtrar por Status", ["Todos", "Ativo", "Inativo"], key="filtro_status_mens")

        df_exibir_m = df_m.copy()
        if filtro_status != "Todos":
            df_exibir_m = df_exibir_m[df_exibir_m["Status"] == filtro_status]

        if not df_exibir_m.empty:
            for idx, row in df_exibir_m.iterrows():
                status_class = "semaforo-verde" if row["Status"] == "Ativo" else "semaforo-vermelho"
                st.markdown(f"""
                <div class="card-executivo {status_class}" style="padding:1rem 1.2rem; margin-bottom:0.5rem;">
                    <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:0.5rem;">
                        <div>
                            <span style="font-weight:600; font-size:1rem; color:#1a1a2e;">{row['Nome']}</span>
                            <span style="font-size:0.8rem; color:#9CA3AF; margin-left:0.5rem;">ID {int(row['ID'])}</span>
                            <br>
                            <span style="font-size:0.85rem; color:#6b7280;">{row['Plano']} | R$ {row['Valor']:.2f}</span>
                        </div>
                        <div>
                            <span class="insight-tag {'oportunidade' if row['Status'] == 'Ativo' else 'risco'}" style="margin-right:0.5rem;">
                                {row['Status']}
                            </span>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                col_b1, col_b2, col_b3, col_b4, _ = st.columns([1,1,1,1,4])
                with col_b1:
                    if st.button("✏️ Editar", key=f"editar_{row['ID']}"):
                        st.session_state["edit_id"] = int(row["ID"])
                        st.rerun()
                with col_b2:
                    if st.button("🗑️ Excluir", key=f"excluir_{row['ID']}"):
                        df_m = df_m[df_m["ID"] != row["ID"]]
                        df_m.to_excel("mensalistas.xlsx", index=False)
                        st.success(f"✅ Mensalista {row['Nome']} excluído!")
                        st.rerun()
                with col_b3:
                    if row["Status"] == "Inativo":
                        if st.button("✅ Ativar", key=f"ativar_{row['ID']}"):
                            df_m.loc[df_m["ID"] == row["ID"], "Status"] = "Ativo"
                            df_m.to_excel("mensalistas.xlsx", index=False)
                            st.success(f"✅ {row['Nome']} ativado! Agora conta no faturamento.")
                            st.rerun()
                with col_b4:
                    if row["Status"] == "Ativo":
                        if st.button("⏸️ Desativar", key=f"desativar_{row['ID']}"):
                            df_m.loc[df_m["ID"] == row["ID"], "Status"] = "Inativo"
                            df_m.to_excel("mensalistas.xlsx", index=False)
                            st.success(f"⏸️ {row['Nome']} desativado.")
                            st.rerun()
        else:
            st.info(f"Nenhum mensalista com status '{filtro_status}'.")
    else:
        st.info("Nenhum mensalista cadastrado ainda.")

    # Edição inline
    if "edit_id" in st.session_state and st.session_state["edit_id"] is not None:
        edit_id = st.session_state["edit_id"]
        row = df_m[df_m["ID"] == edit_id]
        if not row.empty:
            r = row.iloc[0]
            st.markdown("---")
            st.markdown(f"### ✏️ Editando: {r['Nome']}")
            with st.form("form_edit_mensalista"):
                col_e1, col_e2 = st.columns(2)
                with col_e1:
                    e_nome = st.text_input("Nome", value=r["Nome"])
                    e_tel = st.text_input("Telefone", value=r["Telefone"])
                    e_tipo = st.selectbox("Tipo de Veículo",
                        ["Comum", "SUV", "Caminhonete", "Moto"],
                        index=["Comum", "SUV", "Caminhonete", "Moto"].index(r["Tipo"]) if r["Tipo"] in ["Comum", "SUV", "Caminhonete", "Moto"] else 0)
                with col_e2:
                    e_placa = st.text_input("Placa", value=r["Placa"])
                    e_plano = st.selectbox("Plano", ["Valor Fixo Mensal", "Pacote de Lavagens"],
                        index=0 if r["Plano"] == "Valor Fixo Mensal" else 1)
                    if e_plano == "Valor Fixo Mensal":
                        e_valor = st.number_input("Valor Mensal (R$)", min_value=0.0, step=10.0, format="%.2f", value=float(r["Valor"]))
                        e_qtd = 0
                    else:
                        col_v, col_q = st.columns(2)
                        with col_v:
                            e_valor = st.number_input("Valor do Pacote (R$)", min_value=0.0, step=10.0, format="%.2f", value=float(r["Valor"]))
                        with col_q:
                            e_qtd = st.number_input("Lavagens Inclusas", min_value=1, step=1, value=int(r["Lavagens Inclusas"]))

                e_status = st.selectbox("Status", ["Ativo", "Inativo"],
                    index=0 if r["Status"] == "Ativo" else 1)

                col_s1, col_s2 = st.columns(2)
                with col_s1:
                    salvar_edit = st.form_submit_button("💾 Salvar Alterações", use_container_width=True)
                with col_s2:
                    cancelar_edit = st.form_submit_button("❌ Cancelar", use_container_width=True)

                if salvar_edit:
                    if not e_nome.strip():
                        st.warning("⚠️ Nome não pode ficar vazio")
                    else:
                        df_m.loc[df_m["ID"] == edit_id, "Nome"] = e_nome.strip().upper()
                        df_m.loc[df_m["ID"] == edit_id, "Telefone"] = str(e_tel.strip())
                        df_m.loc[df_m["ID"] == edit_id, "Tipo"] = e_tipo
                        df_m.loc[df_m["ID"] == edit_id, "Placa"] = e_placa.strip().upper() if e_placa.strip() else "—"
                        df_m.loc[df_m["ID"] == edit_id, "Plano"] = e_plano
                        df_m.loc[df_m["ID"] == edit_id, "Valor"] = e_valor
                        df_m.loc[df_m["ID"] == edit_id, "Lavagens Inclusas"] = e_qtd
                        df_m.loc[df_m["ID"] == edit_id, "Status"] = e_status
                        df_m.to_excel("mensalistas.xlsx", index=False)
                        st.session_state["edit_id"] = None
                        st.success("✅ Mensalista atualizado com sucesso!")
                        st.rerun()

                if cancelar_edit:
                    st.session_state["edit_id"] = None
                    st.rerun()

# 
# ABA 3 - ANÁLISES EXECUTIVAS
# 
with aba3:
    df_lav = carregar_lavagens()
    df_mens = carregar_mensalistas()

    # ========== FILTROS INTERATIVOS ==========
    st.markdown('<div class="card-executivo">', unsafe_allow_html=True)
    st.markdown("### 🎯 Filtros Interativos")
    st.markdown("---")

    hoje = date.today()
    mes_atual = hoje.month
    ano_atual = hoje.year

    anos_disponiveis = [ano_atual]
    if not df_lav.empty and "Data" in df_lav.columns:
        anos_lav = df_lav["Data"].str.extract(r"(\d{4})").dropna()[0].unique()
        for a in anos_lav:
            anos_disponiveis.append(int(a))
    anos_disponiveis = sorted(set(anos_disponiveis))

    # Filtros em linha
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        ano_sel = st.selectbox("📅 Ano", anos_disponiveis, index=len(anos_disponiveis)-1, key="ano_analise")
    with col_f2:
        meses_lista = [
            (1, "Janeiro"), (2, "Fevereiro"), (3, "Março"), (4, "Abril"),
            (5, "Maio"), (6, "Junho"), (7, "Julho"), (8, "Agosto"),
            (9, "Setembro"), (10, "Outubro"), (11, "Novembro"), (12, "Dezembro")
        ]
        indice_mes = mes_atual - 1 if mes_atual >= 1 else 0
        mes_sel = st.selectbox("📆 Mês", meses_lista, format_func=lambda x: x[1],
                               index=indice_mes, key="mes_analise")

    # Filtro de serviço (se houver dados)
    servicos_disponiveis = ["Todos"]
    if not df_lav.empty and "Serviço" in df_lav.columns:
        servicos_disponiveis.extend(sorted(df_lav["Serviço"].unique()))
    with col_f3:
        servico_sel = st.selectbox("🔧 Serviço", servicos_disponiveis, key="servico_filtro")

    st.markdown('</div>', unsafe_allow_html=True)

    mes_num = mes_sel[0]
    mes_nome = mes_sel[1]

    # ========== FILTRA LAVAGENS ==========
    df_lav_mes = pd.DataFrame()
    try:
        if not df_lav.empty and "Data" in df_lav.columns:
            df_temp = df_lav[df_lav["Data"].str.match(rf"\d{{2}}/\d{{2}}/{ano_sel}")]
            df_temp = df_temp[df_temp["Data"].str.extract(r"/(\d{2})/")[0].astype(int) == mes_num]
            if servico_sel != "Todos":
                df_temp = df_temp[df_temp["Serviço"] == servico_sel]
            df_lav_mes = df_temp.copy()
    except:
        df_lav_mes = pd.DataFrame()

    # ========== RECEITA MENSALISTAS ATIVOS ==========
    receita_mensalistas = 0
    qtd_mens_ativos = 0
    if not df_mens.empty and "Status" in df_mens.columns:
        ativos = df_mens[df_mens["Status"] == "Ativo"]
        qtd_mens_ativos = len(ativos)
        if not ativos.empty and "Valor" in ativos.columns:
            receita_mensalistas = ativos["Valor"].sum()

    # ========== MÉTRICAS GLOBAIS ==========
    total_lavagens_mes = len(df_lav_mes) if not df_lav_mes.empty else 0
    total_receita_lav = df_lav_mes["Valor"].sum() if not df_lav_mes.empty and "Valor" in df_lav_mes.columns else 0
    total_consolidado = total_receita_lav + receita_mensalistas

    # ========== SEMÁFOROS GERENCIAIS (KPIs) ==========
    st.markdown('<div class="card-executivo">', unsafe_allow_html=True)
    st.markdown("### 🚦 Indicadores Gerenciais")
    st.markdown("---")

    # Metas simuladas para semáforo
    meta_lavagens = 20
    meta_receita = 3000

    def semaforo(valor, meta, reverso=False):
        """Reverso=True para indicadores negativos (custos)"""
        if reverso:
            if valor <= meta * 0.9:
                return "green", "🟢"
            elif valor <= meta * 1.1:
                return "yellow", "🟡"
            else:
                return "red", "🔴"
        else:
            if valor >= meta * 0.9:
                return "green", "🟢"
            elif valor >= meta * 0.6:
                return "yellow", "🟡"
            else:
                return "red", "🔴"

    cor_lav, icone_lav = semaforo(total_lavagens_mes, meta_lavagens)
    cor_rec, icone_rec = semaforo(total_receita_lav, meta_receita)
    ticket_medio = total_receita_lav / total_lavagens_mes if total_lavagens_mes > 0 else 0

    col_k1, col_k2, col_k3, col_k4 = st.columns(4)

    with col_k1:
        st.markdown(f"""
        <div class="kpi-card semaforo-{cor_lav}">
            <div class="kpi-label">{icone_lav} Lavagens no Mês</div>
            <div class="kpi-value {cor_lav}">{total_lavagens_mes}</div>
            <div style="font-size:0.75rem; color:#9CA3AF;">Meta: {meta_lavagens}</div>
        </div>
        """, unsafe_allow_html=True)

    with col_k2:
        st.markdown(f"""
        <div class="kpi-card semaforo-{cor_rec}">
            <div class="kpi-label">{icone_rec} Receita Lavagens</div>
            <div class="kpi-value {cor_rec}">R$ {total_receita_lav:.0f}</div>
            <div style="font-size:0.75rem; color:#9CA3AF;">Meta: R$ {meta_receita}</div>
        </div>
        """, unsafe_allow_html=True)

    with col_k3:
        cor_mens = "green" if qtd_mens_ativos >= 3 else ("yellow" if qtd_mens_ativos >= 1 else "red")
        st.markdown(f"""
        <div class="kpi-card semaforo-{cor_mens}">
            <div class="kpi-label">👥 Mensalistas Ativos</div>
            <div class="kpi-value {cor_mens}">{qtd_mens_ativos}</div>
            <div style="font-size:0.75rem; color:#9CA3AF;">Receita: R$ {receita_mensalistas:.0f}</div>
        </div>
        """, unsafe_allow_html=True)

    with col_k4:
        cor_ticket = "green" if ticket_medio >= 120 else ("yellow" if ticket_medio >= 80 else "red")
        st.markdown(f"""
        <div class="kpi-card semaforo-{cor_ticket}">
            <div class="kpi-label">🎫 Ticket Médio</div>
            <div class="kpi-value {cor_ticket}">R$ {ticket_medio:.0f}</div>
            <div style="font-size:0.75rem; color:#9CA3AF;">Consolidado: R$ {total_consolidado:.0f}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

    # ========== GRÁFICO + TABELA: LAVAGENS POR DIA DA SEMANA ==========
    st.markdown('<div class="card-executivo">', unsafe_allow_html=True)
    st.markdown("### 📊 Lavagens por Dia da Semana")

    if not df_lav_mes.empty and "Data" in df_lav_mes.columns:
        df_sem = df_lav_mes.copy()
        df_sem["Dia_Num"] = df_sem["Data"].str.extract(r"(\d{2})").astype(int)
        from datetime import datetime as dt
        dias_semana = []
        for d in df_sem["Dia_Num"]:
            try:
                dia_sem = dt(ano_sel, mes_num, int(d)).weekday()
                dias_semana.append(dia_sem)
            except:
                dias_semana.append(-1)
        df_sem["Dia_Semana"] = dias_semana
        df_sem = df_sem[df_sem["Dia_Semana"].between(0, 5)]

        if not df_sem.empty and "Serviço" in df_sem.columns:
            nomes_dias = {0: "Segunda", 1: "Terça", 2: "Quarta", 3: "Quinta", 4: "Sexta", 5: "Sábado"}
            df_sem["Dia_Nome"] = df_sem["Dia_Semana"].map(nomes_dias)

            df_dia_serv = df_sem.groupby(["Dia_Nome", "Serviço"]).agg(
                Quantidade=("Valor", "count"),
                Valor_Total=("Valor", "sum"),
                Ticket_Medio=("Valor", "mean")
            ).reset_index()

            df_dia_total = df_sem.groupby("Dia_Nome").agg(
                Quantidade=("Valor", "count"),
                Valor_Total=("Valor", "sum"),
                Ticket_Medio=("Valor", "mean")
            ).reset_index()

            ordem_dias = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado"]
            df_dia_total["Dia_Nome"] = pd.Categorical(df_dia_total["Dia_Nome"], categories=ordem_dias, ordered=True)
            df_dia_total = df_dia_total.sort_values("Dia_Nome")

            col_g, col_t = st.columns([2, 1])

            with col_g:
                st.vega_lite_chart(df_dia_serv, {
                    "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
                    "mark": {"type": "bar", "tooltip": True},
                    "encoding": {
                        "x": {
                            "field": "Dia_Nome", "type": "nominal", "title": "Dia da Semana",
                            "sort": ordem_dias
                        },
                        "y": {
                            "field": "Quantidade", "type": "quantitative",
                            "title": "Quantidade de Lavagens", "aggregate": "sum"
                        },
                        "color": {
                            "field": "Serviço", "type": "nominal", "title": "Serviço",
                            "scale": {"scheme": "category10"}
                        },
                        "tooltip": [
                            {"field": "Dia_Nome", "type": "nominal", "title": "Dia"},
                            {"field": "Serviço", "type": "nominal", "title": "Serviço"},
                            {"field": "Quantidade", "type": "quantitative", "title": "Lavagens", "aggregate": "sum"},
                            {"field": "Valor_Total", "type": "quantitative", "title": "Valor Total (R$)", "aggregate": "sum", "format": ".2f"},
                            {"field": "Ticket_Medio", "type": "quantitative", "title": "Ticket Médio (R$)", "aggregate": "mean", "format": ".2f"}
                        ]
                    }
                }, use_container_width=True)

            with col_t:
                st.markdown("###### Resumo por Dia")
                df_tabela = df_dia_total[["Dia_Nome", "Quantidade", "Valor_Total", "Ticket_Medio"]].copy()
                df_tabela["Valor_Total"] = df_tabela["Valor_Total"].apply(lambda x: f"R$ {x:.2f}")
                df_tabela["Ticket_Medio"] = df_tabela["Ticket_Medio"].apply(lambda x: f"R$ {x:.2f}")
                df_tabela.columns = ["Dia", "Lavagens", "Total (R$)", "Ticket Médio"]
                st.dataframe(df_tabela, use_container_width=True, height=280, hide_index=True)
        else:
            st.info("Nenhuma lavagem registrada neste mês.")
    else:
        st.info("Nenhuma lavagem registrada neste mês.")
    st.markdown('</div>', unsafe_allow_html=True)

    # ========== RANKING DE SERVIÇOS ==========
    st.markdown('<div class="card-executivo">', unsafe_allow_html=True)
    st.markdown("### 🏆 Ranking de Serviços")

    if not df_lav_mes.empty and "Serviço" in df_lav_mes.columns:
        df_rank = df_lav_mes.groupby("Serviço").agg(
            Quantidade=("Valor", "count"),
            Receita=("Valor", "sum")
        ).reset_index().sort_values("Quantidade", ascending=False)

        col_r1, col_r2 = st.columns(2)
        with col_r1:
            st.vega_lite_chart(df_rank, {
                "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
                "mark": {"type": "bar", "tooltip": True, "color": {"expr": "datum.Quantidade > 5 ? '#10b981' : datum.Quantidade > 2 ? '#f59e0b' : '#ef4444'"}},
                "encoding": {
                    "x": {"field": "Serviço", "type": "nominal", "title": "Serviço", "sort": "-y"},
                    "y": {"field": "Quantidade", "type": "quantitative", "title": "Lavagens"}
                }
            }, use_container_width=True)

        with col_r2:
            df_rank["Receita"] = df_rank["Receita"].apply(lambda x: f"R$ {x:.2f}")
            df_rank.columns = ["Serviço", "Lavagens", "Receita"]
            st.dataframe(df_rank, use_container_width=True, hide_index=True)

        # Serviço mais popular
        top_servico = df_rank.iloc[0]["Serviço"]
        top_qtd = df_rank.iloc[0]["Lavagens"]
        st.caption(f"⭐ **Serviço mais popular:** {top_servico} — **{int(top_qtd)}** lavagens no período")
    else:
        st.info("Nenhum dado disponível para ranking.")
    st.markdown('</div>', unsafe_allow_html=True)

    # ========== EVOLUÇÃO MENSAL (ANUAL) ==========
    st.markdown('<div class="card-executivo">', unsafe_allow_html=True)
    st.markdown("### 📈 Evolução Mensal - Receita vs Quantidade")

    if not df_lav.empty and "Data" in df_lav.columns and "Serviço" in df_lav.columns:
        df_ano = df_lav[df_lav["Data"].str.match(rf"\d{{2}}/\d{{2}}/{ano_sel}")].copy()

        if not df_ano.empty:
            # Filtro de serviço para evolução
            if servico_sel != "Todos":
                df_ano = df_ano[df_ano["Serviço"] == servico_sel]

            df_ano["Mes_Num"] = df_ano["Data"].str.extract(r"/(\d{2})/")[0].astype(int)
            nomes_meses = {1:"Jan",2:"Fev",3:"Mar",4:"Abr",5:"Mai",6:"Jun",
                          7:"Jul",8:"Ago",9:"Set",10:"Out",11:"Nov",12:"Dez"}
            ordem = ["Jan","Fev","Mar","Abr","Mai","Jun","Jul","Ago","Set","Out","Nov","Dez"]

            # Dados para barras (quantidade por mês + serviço)
            servicos_ano = df_ano["Serviço"].unique() if servico_sel == "Todos" else [servico_sel]
            registros_base = []
            for m in range(1, 13):
                for s in servicos_ano:
                    registros_base.append({"Mes_Nome": nomes_meses[m], "Mes_Num": m, "Serviço": s, "Qtd": 0, "Vlr": 0})
            df_base = pd.DataFrame(registros_base)

            df_real = df_ano.groupby(["Mes_Num", "Serviço"]).agg(
                Qtd=("Valor", "count"), Vlr=("Valor", "sum")
            ).reset_index()
            df_real["Mes_Nome"] = df_real["Mes_Num"].map(nomes_meses)

            df_barras = df_base.merge(
                df_real[["Mes_Num", "Serviço", "Qtd", "Vlr"]],
                on=["Mes_Num", "Serviço"], how="left", suffixes=("", "_r")
            )
            df_barras["Qtd"] = df_barras["Qtd_r"].fillna(0).apply(lambda x: int(x))
            df_barras["Vlr"] = df_barras["Vlr_r"].fillna(0).apply(lambda x: float(x))
            df_barras = df_barras[["Mes_Nome", "Serviço", "Qtd", "Vlr"]]

            # Dados para linha de receita
            df_rec = df_ano.groupby("Mes_Num").agg(Receita=("Valor", "sum")).reset_index()
            media_rec = df_rec["Receita"].mean() if not df_rec.empty else 0
            meses_reais = set(df_rec["Mes_Num"].unique())

            rec_plot = []
            proj_plot = []
            for m in range(1, 13):
                mn = nomes_meses[m]
                if m in meses_reais:
                    r = float(df_rec[df_rec["Mes_Num"] == m]["Receita"].values[0])
                    rec_plot.append({"Mes_Nome": mn, "Receita": r})
                else:
                    rec_plot.append({"Mes_Nome": mn, "Receita": None})
                    if media_rec > 0:
                        proj_plot.append({"Mes_Nome": mn, "Proj_Rec": float(media_rec)})

            layers = []

            # Barras empilhadas
            layers.append({
                "data": {"values": df_barras.to_dict('records')},
                "mark": {"type": "bar", "tooltip": True},
                "encoding": {
                    "x": {"field": "Mes_Nome", "type": "nominal", "sort": ordem, "title": "Mês",
                          "axis": {"labelAngle": 0, "labelFontSize": 11}},
                    "y": {"field": "Qtd", "type": "quantitative", "title": "Quantidade de Lavagens"},
                    "color": {"field": "Serviço", "type": "nominal", "title": "Serviço",
                              "scale": {"scheme": "category10"}},
                    "tooltip": [
                        {"field": "Mes_Nome", "type": "nominal", "title": "Mês"},
                        {"field": "Serviço", "type": "nominal", "title": "Serviço"},
                        {"field": "Qtd", "type": "quantitative", "title": "Lavagens"},
                        {"field": "Vlr", "type": "quantitative", "title": "Valor (R$)", "format": ".2f"}
                    ]
                }
            })

            # Linha de receita real
            layers.append({
                "data": {"values": rec_plot},
                "mark": {"type": "line", "point": {"size": 60}, "color": "#FF5722",
                         "strokeWidth": 3, "tooltip": True},
                "encoding": {
                    "x": {"field": "Mes_Nome", "type": "nominal", "sort": ordem},
                    "y": {"field": "Receita", "type": "quantitative",
                          "title": "Receita (R$)", "scale": {"zero": False}},
                    "tooltip": [
                        {"field": "Mes_Nome", "type": "nominal", "title": "Mês"},
                        {"field": "Receita", "type": "quantitative", "title": "Receita (R$)", "format": ".2f"}
                    ]
                }
            })

            # Projeção tracejada
            if proj_plot:
                layers.append({
                    "data": {"values": proj_plot},
                    "mark": {"type": "line", "color": "#FF5722", "strokeWidth": 2.5,
                             "strokeDash": [6, 4], "opacity": 0.7, "point": {"size": 50}},
                    "encoding": {
                        "x": {"field": "Mes_Nome", "type": "nominal", "sort": ordem},
                        "y": {"field": "Proj_Rec", "type": "quantitative"},
                        "tooltip": [
                            {"field": "Mes_Nome", "type": "nominal", "title": "Mês"},
                            {"field": "Proj_Rec", "type": "quantitative", "title": "Projeção (R$)", "format": ".2f"}
                        ]
                    }
                })

            col_evol_g, col_evol_t = st.columns([2, 1])
            with col_evol_g:
                st.vega_lite_chart(None, {
                    "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
                    "title": {"text": f"Evolução {ano_sel}" + (f" - {servico_sel}" if servico_sel != "Todos" else ""), "fontSize": 14},
                    "layer": layers,
                    "resolve": {"scale": {"y": "independent"}}
                }, use_container_width=True)
                st.caption("🔶 Linha laranja contínua = Receita real | Linha tracejada = Projeção (média)")

            with col_evol_t:
                st.markdown("###### Resumo Mensal")
                df_tabela_m = df_rec.copy()
                df_tabela_m["Mês"] = df_tabela_m["Mes_Num"].map(nomes_meses)
                df_tabela_m["Dif (%)"] = df_rec["Receita"].pct_change() * 100

                def cor_diff(val):
                    if pd.isna(val):
                        return ''
                    return 'color: green; font-weight: bold' if val > 0 else 'color: red; font-weight: bold'

                df_estilo = df_tabela_m[["Mês", "Receita", "Dif (%)"]].style.format({
                    "Receita": "R$ {:.2f}",
                    "Dif (%)": lambda x: f"{x:+.1f}%" if pd.notna(x) else "—"
                }).map(cor_diff, subset=["Dif (%)"])

                st.dataframe(df_estilo, use_container_width=True, hide_index=True)

                if media_rec > 0:
                    st.metric("📊 Média Mensal", f"R$ {media_rec:.2f}")
                if len(df_tabela_m) > 1:
                    melhor_mes_idx = df_rec["Receita"].idxmax()
                    melhor_mes = df_tabela_m.loc[melhor_mes_idx, "Mês"]
                    st.caption(f"🏆 Melhor mês: **{melhor_mes}**")
        else:
            st.info("Nenhuma lavagem registrada neste ano.")
    else:
        st.info("Nenhuma lavagem registrada.")
    st.markdown('</div>', unsafe_allow_html=True)

    # ========== MENSALISTAS NA ABA ANÁLISES ==========
    if not df_mens.empty:
        st.markdown('<div class="card-executivo">', unsafe_allow_html=True)
        st.markdown("### 📋 Resumo Mensalistas")

        col_mres1, col_mres2 = st.columns(2)
        with col_mres1:
            df_mens_resumo = df_mens[["Nome", "Plano", "Valor", "Status"]].copy()
            df_mens_resumo["Valor"] = df_mens_resumo["Valor"].apply(lambda x: f"R$ {x:.2f}")
            df_mens_resumo.columns = ["Nome", "Plano", "Valor", "Status"]
            st.dataframe(df_mens_resumo, use_container_width=True, hide_index=True)

        with col_mres2:
            total_ativos = float(df_mens[df_mens["Status"] == "Ativo"]["Valor"].sum())
            total_inativos = float(df_mens[df_mens["Status"] == "Inativo"]["Valor"].sum())
            st.metric("💰 Receita Mensal (Ativos)", f"R$ {total_ativos:.2f}")
            st.metric("💤 Inativos", f"R$ {total_inativos:.2f}")
            st.metric("👥 Qtd Ativos", len(df_mens[df_mens["Status"] == "Ativo"]))

            if not df_mens.empty:
                df_comp_mens = df_mens.groupby("Status").agg(
                    Valor_Total=("Valor", "sum"),
                    Qtd=("ID", "count")
                ).reset_index()
                st.markdown("###### Composição por Status")
                col_c1, col_c2 = st.columns(2)
                with col_c1:
                    st.vega_lite_chart(df_comp_mens, {
                        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
                        "mark": {"type": "bar", "tooltip": True},
                        "encoding": {
                            "x": {"field": "Status", "type": "nominal"},
                            "y": {"field": "Valor_Total", "type": "quantitative", "title": "R$"},
                            "color": {"field": "Status", "type": "nominal",
                                      "scale": {"domain": ["Ativo", "Inativo"], "range": ["#10b981", "#ef4444"]}}
                        }
                    }, use_container_width=True)
                with col_c2:
                    st.vega_lite_chart(df_comp_mens, {
                        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
                        "mark": {"type": "bar", "tooltip": True},
                        "encoding": {
                            "x": {"field": "Status", "type": "nominal"},
                            "y": {"field": "Qtd", "type": "quantitative", "title": "Qtd"},
                            "color": {"field": "Status", "type": "nominal",
                                      "scale": {"domain": ["Ativo", "Inativo"], "range": ["#10b981", "#ef4444"]}}
                        }
                    }, use_container_width=True)

        st.markdown('</div>', unsafe_allow_html=True)

    # ========== INSIGHTS EXECUTIVOS ==========
    st.markdown('<div class="card-executivo">', unsafe_allow_html=True)
    st.markdown("### 💡 Insights Executivos")
    st.markdown("---")

    insights = []

    # Insight 1: Desempenho do mês
    if total_lavagens_mes > 0:
        if total_lavagens_mes >= meta_lavagens:
            insights.append(("destaque", f"📈 **Desempenho excelente!** {total_lavagens_mes} lavagens no mês — meta de {meta_lavagens} foi atingida."))
        elif total_lavagens_mes >= meta_lavagens * 0.6:
            insights.append(("atencao", f"⚠️ **Desempenho moderado.** {total_lavagens_mes} de {meta_lavagens} lavagens ({(total_lavagens_mes/meta_lavagens*100):.0f}% da meta). Foco em aumentar o fluxo."))
        else:
            insights.append(("risco", f"🔴 **Atenção!** Apenas {total_lavagens_mes} lavagens no mês — bem abaixo da meta de {meta_lavagens}. Revisar estratégias de captação."))
    else:
        insights.append(("atencao", "📭 **Nenhuma lavagem registrada** no período selecionado. Considere campanhas promocionais."))

    # Insight 2: Ticket médio
    if ticket_medio > 0:
        if ticket_medio >= 120:
            insights.append(("oportunidade", f"💎 **Ticket médio alto:** R$ {ticket_medio:.0f}. Clientes estão optando por serviços premium!"))
        elif ticket_medio >= 80:
            insights.append(("atencao", f"📊 **Ticket médio regular:** R$ {ticket_medio:.0f}. Oportunidade de upsell para serviços completos."))
        else:
            insights.append(("risco", f"📉 **Ticket médio baixo:** R$ {ticket_medio:.0f}. Avaliar estratégias para aumentar valor por cliente."))

    # Insight 3: Mensalistas
    if qtd_mens_ativos > 0:
        perc_mens = (receita_mensalistas / total_consolidado * 100) if total_consolidado > 0 else 0
        insights.append(("oportunidade", f"👥 **Mensalistas ativos:** {qtd_mens_ativos} — representam **{perc_mens:.0f}%** da receita consolidada. Base recorrente saudável."))
        if qtd_mens_ativos < 3:
            insights.append(("oportunidade", f"🚀 **Oportunidade de crescimento:** Apenas {qtd_mens_ativos} mensalistas ativos. Cada novo mensalista garante receita previsível!"))
    else:
        insights.append(("risco", "👥 **Nenhum mensalista ativo.** Recomenda-se campanha de assinatura mensal para estabilizar receita."))

    # Insight 4: Serviço mais popular
    if not df_lav_mes.empty and "Serviço" in df_lav_mes.columns:
        serv_counts = df_lav_mes["Serviço"].value_counts()
        if not serv_counts.empty:
            insights.append(("destaque", f"⭐ **Serviço campeão:** **{serv_counts.index[0]}** com {int(serv_counts.iloc[0])} lavagens. Manter estoque e preparação para esse serviço."))

    # Insight 5: Projeção
    if media_rec > 0 and len(meses_reais) < 12:
        insights.append(("atencao", f"📅 **Projeção mensal:** R$ {media_rec:.2f} baseada nos {len(meses_reais)} meses com dados. Use esta referência para planejamento."))

    # Exibe insights
    for tipo, texto in insights:
        st.markdown(f"""
        <div class="insight-card">
            <span class="insight-tag {tipo}">{tipo}</span>
            <div style="margin-top:0.2rem; font-size:0.95rem; color:#374151; line-height:1.5;">{texto}</div>
        </div>
        """, unsafe_allow_html=True)

    # Recomendações práticas
    st.markdown("---")
    st.markdown("#### 📋 Recomendações Gerenciais")

    recomendacoes = []
    if total_lavagens_mes < meta_lavagens:
        recomendacoes.append("📢 **Aumentar fluxo:** Considere promoções em dias de menor movimento (terça/quarta/quinta)")
    if qtd_mens_ativos < 5:
        recomendacoes.append("🎯 **Expandir mensalistas:** Ofereça desconto no primeiro mês para converter clientes frequentes")
    if ticket_medio < 100:
        recomendacoes.append("🔝 **Upsell:** Treine a equipe para oferecer Lavagem Completa ou motor a cada Ducha")
    if not recomendacoes:
        recomendacoes.append("✅ **Tudo nos trilhos!** Continue mantendo a qualidade e o padrão de atendimento.")

    for rec in recomendacoes:
        st.markdown(f"- {rec}")

    st.markdown('</div>', unsafe_allow_html=True)

    # ========== FOOTER ==========
    st.markdown("""
    <hr>
    <div style="text-align:center; padding:1rem 0; font-size:0.8rem; color:#9CA3AF;">
        <strong>Masson Lava Jato</strong> • Painel Executivo • Dados atualizados em """ + datetime.now().strftime("%d/%m/%Y %H:%M") + """
        <br>Desenvolvido com Streamlit
    </div>
    """, unsafe_allow_html=True)