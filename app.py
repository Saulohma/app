import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date, timedelta
import sqlite3
from pathlib import Path
import io
from io import BytesIO
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from hashlib import sha256

DATABASE_URL = os.getenv("DATABASE_URL")   # ← ADICIONA ESTA LINHA

# ============================================================
# AUTENTICAÇÃO
# ============================================================
ADMIN_USER = "admin"
ADMIN_PASS = "admin757"

def check_password():
    if "auth" not in st.session_state:
        st.session_state.auth = False
    if st.session_state.auth:
        return True
    st.markdown(
        "<div style='text-align:center;padding:3rem 0 1rem 0;'>"
        "<h1>🚗 Lava Jato</h1>"
        "<p style='color:#888;font-size:1.1rem;'>Sistema de Gestão</p>"
        "</div>",
        unsafe_allow_html=True
    )
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.markdown("#### 🔐 Acesso Restrito")
        with st.form("login"):
            user = st.text_input("Usuário", placeholder="Digite seu usuário")
            pwd = st.text_input("Senha", type="password", placeholder="Digite sua senha")
            if st.form_submit_button("Entrar", type="primary", use_container_width=True):
                if user == ADMIN_USER and pwd == ADMIN_PASS:
                    st.session_state.auth = True
                    st.rerun()
                else:
                    st.error("❌ Usuário ou senha inválidos!")
    return False

# ============================================================
# CONFIG
# ============================================================
st.set_page_config(
    page_title="Lava Jato",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="collapsed",
    menu_items={},
)

# ============================================================
# BANCO DE DADOS
# ============================================================
DB_URL = os.environ.get("DATABASE_URL", "")

def get_conn():
    conn = psycopg2.connect(DB_URL, cursor_factory=RealDictCursor)
    conn.autocommit = True
    return conn

def init_db():
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS precos (
            id SERIAL PRIMARY KEY,
            tipo_veiculo TEXT NOT NULL,
            servico TEXT NOT NULL,
            valor REAL NOT NULL,
            UNIQUE(tipo_veiculo, servico)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS lavagens (
            id SERIAL PRIMARY KEY,
            data DATE NOT NULL,
            tipo_veiculo TEXT NOT NULL,
            servico TEXT NOT NULL,
            valor REAL NOT NULL,
            cliente TEXT DEFAULT '',
            placa TEXT DEFAULT '',
            quantidade INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS mensalistas (
            id SERIAL PRIMARY KEY,
            nome TEXT NOT NULL,
            telefone TEXT DEFAULT '',
            tipo TEXT DEFAULT 'Comum',
            placa TEXT DEFAULT '',
            plano TEXT DEFAULT 'Valor Fixo Mensal',
            valor_plano REAL DEFAULT 0,
            data_inicio DATE,
            ativo INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    precos_padrao = [
        ('Comum', 'Completa', 250.0), ('Comum', 'Simples', 90.0),
        ('Comum', 'Ducha', 30.0), ('Comum', 'Motor', 80.0),
        ('Comum', 'Chaci', 90.0), ('Comum', 'Moto', 35.0),
        ('SUV', 'Completa', 300.0), ('SUV', 'Simples', 120.0),
        ('SUV', 'Ducha', 30.0), ('SUV', 'Motor', 80.0),
        ('SUV', 'Chaci', 90.0), ('SUV', 'Moto', 35.0),
        ('Caminhonete', 'Completa', 330.0), ('Caminhonete', 'Simples', 150.0),
        ('Caminhonete', 'Ducha', 30.0), ('Caminhonete', 'Motor', 80.0),
        ('Caminhonete', 'Chaci', 90.0), ('Caminhonete', 'Moto', 35.0),
        ('Moto', 'Completa', 150.0), ('Moto', 'Simples', 60.0),
        ('Moto', 'Ducha', 30.0), ('Moto', 'Motor', 80.0),
        ('Moto', 'Chaci', 90.0), ('Moto', 'Moto', 35.0),
    ]
    for tipo, servico, valor in precos_padrao:
        cursor.execute(
            "INSERT INTO precos (tipo_veiculo, servico, valor) VALUES (%s, %s, %s) ON CONFLICT (tipo_veiculo, servico) DO NOTHING",
            (tipo, servico, valor)
        )
    conn.commit()
    conn.close()

def migrar_excel():
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) AS total FROM lavagens")
    if list(cursor.fetchone().values())[0] > 0:
        conn.close()
        return

    # --- LAVAGENS ---
    xlsx = Path(__file__).parent / "dados.xlsx"
    if xlsx.exists():
        try:
            df = pd.read_excel(str(xlsx))
            # Remove linha que contém cabeçalhos repetidos como dados
            if not df.empty:
                first_row = df.iloc[0].astype(str).str.lower().tolist()
                expected = ['data', 'tipo', 'serviço', 'servico', 'valor', 'cliente', 'placa', 'quantidade']
                if any(f in first_row for f in expected):
                    df = df.iloc[1:].reset_index(drop=True)

            for _, r in df.iterrows():
                d = r.get('data') or r.get('Data') or ''
                if isinstance(d, (datetime, pd.Timestamp)): d = d.strftime('%Y-%m-%d')
                elif isinstance(d, str):
                    try: d = datetime.strptime(d.strip(), '%d/%m/%Y').strftime('%Y-%m-%d')
                    except: d = date.today().strftime('%Y-%m-%d')
                else: d = date.today().strftime('%Y-%m-%d')
                t = str(r.get('tipo_veiculo') or r.get('Tipo') or 'Comum').strip()
                s = str(r.get('servico') or r.get('Serviço') or '').strip()
                v = float(r.get('valor') or r.get('Valor') or 0)
                c = str(r.get('cliente') or r.get('Cliente') or '').strip().upper()
                p = str(r.get('placa') or r.get('Placa') or '').strip().upper()
                q = int(r.get('quantidade') or r.get('Quantidade') or 1)
                cursor.execute("""INSERT INTO lavagens (data,tipo_veiculo,servico,valor,cliente,placa,quantidade) VALUES (%s,%s,%s,%s,%s,%s,%s)""", (d,t,s,v,c,p,q))
            conn.commit()
        except Exception as e:
            print(f"Erro migração lavagens: {e}")

    # --- MENSALISTAS ---
    xlsxm = Path(__file__).parent / "mensalistas.xlsx"
    if xlsxm.exists():
        try:
            df = pd.read_excel(str(xlsxm))
            # Remove linha que contém cabeçalhos repetidos
            if not df.empty:
                first_row = df.iloc[0].astype(str).str.lower().tolist()
                expected = ['nome', 'telefone', 'tipo', 'placa', 'plano', 'valor', 'data', 'ativo']
                if any(f in first_row for f in expected):
                    df = df.iloc[1:].reset_index(drop=True)

            for _, r in df.iterrows():
                n = str(r.get('nome') or r.get('Nome') or '').strip().upper()
                t = str(r.get('telefone') or r.get('Telefone') or '')
                tp = str(r.get('tipo') or r.get('Tipo') or 'Comum')
                p = str(r.get('placa') or r.get('Placa') or '').upper()
                pl = str(r.get('plano') or r.get('Plano') or 'Valor Fixo Mensal')
                v = float(r.get('valor_plano') or r.get('Valor Plano') or r.get('valor') or 0)
                di = r.get('data_inicio') or r.get('Data Início') or r.get('data') or ''
                if isinstance(di, (datetime, pd.Timestamp)): di = di.strftime('%Y-%m-%d')
                elif isinstance(di, str):
                    try: di = datetime.strptime(di.strip(), '%d/%m/%Y').strftime('%Y-%m-%d')
                    except: di = date.today().strftime('%Y-%m-%d')
                else: di = date.today().strftime('%Y-%m-%d')
                a = int(r.get('ativo') or r.get('Ativo') or 0)
                cursor.execute("""INSERT INTO mensalistas (nome,telefone,tipo,placa,plano,valor_plano,data_inicio,ativo) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""", (n,t,tp,p,pl,v,di,a))
            conn.commit()
        except Exception as e:
            print(f"Erro migração mensalistas: {e}")

    conn.close()



# ============================================================
# FUNÇÕES
# ============================================================

def get_conn():
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)

def init_db():
    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS lavagens (
                id SERIAL PRIMARY KEY, data DATE, tipo_veiculo TEXT,
                servico TEXT, valor NUMERIC, cliente TEXT,
                placa TEXT, quantidade INTEGER
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS mensalistas (
                id SERIAL PRIMARY KEY, nome TEXT, telefone TEXT,
                tipo TEXT, placa TEXT, plano TEXT,
                valor_plano NUMERIC, data_inicio DATE, ativo INTEGER DEFAULT 0
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS precos (
                id SERIAL PRIMARY KEY, tipo_veiculo TEXT,
                servico TEXT, valor NUMERIC
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS _migracao_feita (
                id SERIAL PRIMARY KEY, concluida BOOLEAN DEFAULT TRUE
            )
        """)
    conn.commit()
    conn.close()

def migracao_ja_feita():
    """Retorna True se a migração já foi executada alguma vez"""
    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) AS total FROM _migracao_feita")
        r = cur.fetchone()
    conn.close()
    return list(r.values())[0] > 0

def is_header_row(r, col_names):
    """Detecta se a linha do Excel é cabeçalho repetido"""
    vals = [str(r.get(c, '')).strip().lower() for c in col_names if r.get(c)]
    if not vals:
        return False
    expected = [c.lower() for c in col_names]
    return any(v in expected for v in vals)

def migrar_excel():
    if migracao_ja_feita():
        return  # Já migrou uma vez, NUNCA mais repete

    conn = get_conn()
    cursor = conn.cursor()

    # --- LAVAGENS ---
    xlsx = Path(__file__).parent / "dados.xlsx"
    if xlsx.exists():
        try:
            df = pd.read_excel(str(xlsx))
            col_map = {'data':'data','Data':'data','tipo_veiculo':'tipo_veiculo','Tipo':'tipo_veiculo',
                       'servico':'servico','Serviço':'servico','valor':'valor','Valor':'valor',
                       'cliente':'cliente','Cliente':'cliente','placa':'placa','Placa':'placa',
                       'quantidade':'quantidade','Quantidade':'quantidade'}
            cols_lav = ['data','tipo_veiculo','servico','valor','cliente','placa','quantidade']
            for _, r in df.iterrows():
                if is_header_row(r, cols_lav):
                    continue  # Pula linha de cabeçalho
                d = r.get('data') or r.get('Data') or date.today()
                if isinstance(d, (datetime, pd.Timestamp)): d = d.strftime('%Y-%m-%d')
                elif isinstance(d, str):
                    try: d = datetime.strptime(d.strip(), '%d/%m/%Y').strftime('%Y-%m-%d')
                    except: d = date.today().strftime('%Y-%m-%d')
                else: d = date.today().strftime('%Y-%m-%d')
                t = str(r.get('tipo_veiculo') or r.get('Tipo') or 'Comum').strip()
                s = str(r.get('servico') or r.get('Serviço') or '').strip()
                try: v = float(r.get('valor') or r.get('Valor') or 0)
                except: v = 0
                c = str(r.get('cliente') or r.get('Cliente') or '').strip().upper()
                p = str(r.get('placa') or r.get('Placa') or '').strip().upper()
                try: q = int(r.get('quantidade') or r.get('Quantidade') or 1)
                except: q = 1
                # Usa INSERT com verificação ON CONFLICT (funciona com chave única)
                cursor.execute("""INSERT INTO lavagens (data,tipo_veiculo,servico,valor,cliente,placa,quantidade) VALUES (%s,%s,%s,%s,%s,%s,%s)""", (d,t,s,v,c,p,q))
            conn.commit()
        except Exception as e:
            print(f"Migração lavagens: {e}")

    # --- MENSALISTAS ---
    xlsxm = Path(__file__).parent / "mensalistas.xlsx"
    if xlsxm.exists():
        try:
            df = pd.read_excel(str(xlsxm))
            cols_mens = ['nome','telefone','tipo','placa','plano','valor_plano','data_inicio','ativo']
            for _, r in df.iterrows():
                if is_header_row(r, cols_mens):
                    continue  # Pula linha de cabeçalho
                n = str(r.get('nome') or r.get('Nome') or '').strip().upper()
                if not n or n == 'NOME':
                    continue  # Pula vazio/cabeçalho
                t = str(r.get('telefone') or r.get('Telefone') or '')
                tp = str(r.get('tipo') or r.get('Tipo') or 'Comum').strip()
                if tp.lower() in ('tipo', ''):
                    tp = 'Comum'
                p = str(r.get('placa') or r.get('Placa') or '').upper()
                pl = str(r.get('plano') or r.get('Plano') or 'Valor Fixo Mensal').strip()
                if pl.lower() in ('plano', ''):
                    pl = 'Valor Fixo Mensal'
                try: v = float(r.get('valor_plano') or r.get('Valor Plano') or r.get('valor') or 0)
                except: v = 0
                di = r.get('data_inicio') or r.get('Data Início') or r.get('data') or date.today()
                if isinstance(di, (datetime, pd.Timestamp)): di = di.strftime('%Y-%m-%d')
                elif isinstance(di, str):
                    try: di = datetime.strptime(di.strip(), '%d/%m/%Y').strftime('%Y-%m-%d')
                    except: di = date.today().strftime('%Y-%m-%d')
                else: di = date.today().strftime('%Y-%m-%d')
                try: a = int(r.get('ativo') or r.get('Ativo') or 1)
                except: a = 1  # DEFAULT: ATIVO
                cursor.execute("""INSERT INTO mensalistas (nome,telefone,tipo,placa,plano,valor_plano,data_inicio,ativo) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""", (n,t,tp,p,pl,v,di,a))
            conn.commit()
        except Exception as e:
            print(f"Migração mensalistas: {e}")

    # --- PRECOS ---
    if not xlsx.exists() and not xlsxm.exists():
        precos_default = [
            ('Comum', 'Lavagem Simples', 20), ('Comum', 'Lavagem Completa', 35),
            ('SUV', 'Lavagem Simples', 30), ('SUV', 'Lavagem Completa', 50),
            ('Caminhonete', 'Lavagem Simples', 35), ('Caminhonete', 'Lavagem Completa', 55),
            ('Moto', 'Lavagem Simples', 15), ('Moto', 'Lavagem Completa', 25),
        ]
        for tp, sv, vl in precos_default:
            cursor.execute("SELECT COUNT(*) AS total FROM precos WHERE tipo_veiculo=%s AND servico=%s", (tp, sv))
            if list(cursor.fetchone().values())[0] == 0:
                cursor.execute("INSERT INTO precos (tipo_veiculo,servico,valor) VALUES (%s,%s,%s)", (tp, sv, vl))
        conn.commit()

    # Marca migração como concluída (NUNCA mais roda)
    cursor.execute("INSERT INTO _migracao_feita (concluida) VALUES (TRUE)")
    conn.commit()
    conn.close()

def limpar_dados_corrompidos():
    """Remove registros com dados de migração corrompidos"""
    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute("DELETE FROM lavagens WHERE cliente IS NULL OR cliente = '' OR cliente = 'cliente'")
        cur.execute("DELETE FROM lavagens WHERE data IS NULL")
        cur.execute("DELETE FROM mensalistas WHERE nome IS NULL OR nome = '' OR nome = 'nome'")
        cur.execute("DELETE FROM mensalistas WHERE id::text !~ '^[0-9]+$'")
        cur.execute("DELETE FROM mensalistas WHERE telefone = 'telefone' OR plano = 'plano'")
        cur.execute("DELETE FROM precos WHERE tipo_veiculo IS NULL OR tipo_veiculo = ''")
    conn.commit()
    conn.close()

def get_preco(tipo_veiculo, servico):
    """Retorna o valor do serviço para o tipo de veículo"""
    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute("SELECT valor FROM precos WHERE tipo_veiculo=%s AND servico=%s", (tipo_veiculo, servico))
        r = cur.fetchone()
    conn.close()
    if r:
        return float(r['valor'])
    # Fallback: precos padrão
    precos_fallback = {
        ('Comum', 'Lavagem Simples'): 20, ('Comum', 'Lavagem Completa'): 35,
        ('SUV', 'Lavagem Simples'): 30, ('SUV', 'Lavagem Completa'): 50,
        ('Caminhonete', 'Lavagem Simples'): 35, ('Caminhonete', 'Lavagem Completa'): 55,
        ('Moto', 'Lavagem Simples'): 15, ('Moto', 'Lavagem Completa'): 25,
    }
    return precos_fallback.get((tipo_veiculo, servico), 0)

def carregar_lavagens():
    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM lavagens ORDER BY data DESC")
        rows = cur.fetchall()
    conn.close()
    if not rows: return pd.DataFrame()
    return pd.DataFrame(rows)

def carregar_mensalistas():
    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM mensalistas ORDER BY nome")
        rows = cur.fetchall()
    conn.close()
    if not rows: return pd.DataFrame()
    return pd.DataFrame(rows)

def registrar_lavagem(data, tipo_veiculo, servico, valor, cliente, placa, quantidade):
    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute("""INSERT INTO lavagens (data,tipo_veiculo,servico,valor,cliente,placa,quantidade) VALUES (%s,%s,%s,%s,%s,%s,%s)""", (data,tipo_veiculo,servico,valor,cliente,placa,quantidade))
    conn.commit()
    conn.close()

def get_preco(tipo_veiculo, servico):
    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute("SELECT valor FROM precos WHERE tipo_veiculo=%s AND servico=%s", (tipo_veiculo, servico))
        r = cur.fetchone()
    conn.close()
    if r:
        return float(r['valor'])
    precos_fallback = {
        ('Comum', 'Lavagem Simples'): 20, ('Comum', 'Lavagem Completa'): 35,
        ('SUV', 'Lavagem Simples'): 30, ('SUV', 'Lavagem Completa'): 50,
        ('Caminhonete', 'Lavagem Simples'): 35, ('Caminhonete', 'Lavagem Completa'): 55,
        ('Moto', 'Lavagem Simples'): 15, ('Moto', 'Lavagem Completa'): 25,
    }
    return precos_fallback.get((tipo_veiculo, servico), 0)

def adicionar_mensalista(nome, telefone, tipo, placa, plano, valor_plano, data_inicio):
    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute("""INSERT INTO mensalistas (nome,telefone,tipo,placa,plano,valor_plano,data_inicio,ativo) VALUES (%s,%s,%s,%s,%s,%s,%s,1)""", (nome,telefone,tipo,placa,plano,valor_plano,data_inicio))
    conn.commit()
    conn.close()

def atualizar_mensalista(id, nome, telefone, tipo, placa, plano, valor_plano, data_inicio, ativo):
    try:
        id_int = int(id)
    except (ValueError, TypeError):
        st.error("ID inválido para atualização")
        return
    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute("""UPDATE mensalistas SET nome=%s,telefone=%s,tipo=%s,placa=%s,plano=%s,valor_plano=%s,data_inicio=%s,ativo=%s WHERE id=%s""", (nome,telefone,tipo,placa,plano,valor_plano,data_inicio,ativo,id_int))
    conn.commit()
    conn.close()

def toggle_mensalista(id):
    try:
        id_int = int(id)
    except (ValueError, TypeError):
        st.error("ID inválido para alternar status")
        return
    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute("SELECT ativo FROM mensalistas WHERE id=%s", (id_int,))
        r = cur.fetchone()
        if r:
            cur.execute("UPDATE mensalistas SET ativo=%s WHERE id=%s", (0 if r['ativo'] else 1, id_int))
    conn.commit()
    conn.close()

def excluir_mensalista(id):
    try:
        id_int = int(id)
    except (ValueError, TypeError):
        st.error("ID inválido para exclusão")
        return
    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute("DELETE FROM mensalistas WHERE id=%s", (id_int,))
    conn.commit()
    conn.close()

init_db()
migrar_excel()
limpar_dados_corrompidos() 
# ============================================================
# CSS
# ============================================================
st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>
    * { font-family: 'Inter', sans-serif !important; }
    .main > div { padding: 1rem 1.5rem; }
    .card-executivo {
        background: white; border-radius: 16px; padding: 1.5rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.06); transition: all 0.2s ease;
        border-left: 5px solid #e5e7eb; margin-bottom: 1rem;
    }
    .card-executivo:hover { box-shadow: 0 4px 12px rgba(0,0,0,0.1); transform: translateY(-2px); }
    .card-executivo.verde { border-left-color: #10b981; }
    .card-executivo.amarelo { border-left-color: #f59e0b; }
    .card-executivo.vermelho { border-left-color: #ef4444; }
    .card-executivo .kpi-label { font-size: 0.8rem; color: #6b7280; font-weight: 500; text-transform: uppercase; letter-spacing: 0.05em; }
    .card-executivo .kpi-value { font-size: 1.8rem; font-weight: 800; color: #111827; margin: 0.2rem 0; }
    .card-executivo .kpi-meta { font-size: 0.75rem; color: #9ca3af; }
    .semaforo { display: inline-flex; gap: 6px; align-items: center; padding: 4px 12px; border-radius: 20px; font-size: 0.75rem; font-weight: 600; }
    .semaforo.verde { background: #d1fae5; color: #065f46; }
    .semaforo.amarelo { background: #fef3c7; color: #92400e; }
    .semaforo.vermelho { background: #fee2e2; color: #991b1b; }
    .stButton > button { border-radius: 10px !important; font-weight: 600 !important; transition: all 0.2s !important; }
    .stButton > button:hover { transform: translateY(-1px); box-shadow: 0 2px 8px rgba(0,0,0,0.15); }
    .stTabs [data-baseweb="tab-list"] { gap: 0; border-radius: 12px; overflow: hidden; }
    .stTabs [data-baseweb="tab"] { padding: 0.75rem 1.5rem; font-weight: 600; font-size: 0.9rem; }
    .stTabs [aria-selected="true"] { background: #1e3a5f; color: white !important; }
    .tag { display: inline-block; padding: 2px 10px; border-radius: 12px; font-size: 0.7rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; }
    .tag.destaque { background: #dbeafe; color: #1e40af; }
    .tag.oportunidade { background: #d1fae5; color: #065f46; }
    .tag.atencao { background: #fef3c7; color: #92400e; }
    .tag.risco { background: #fee2e2; color: #991b1b; }
    .card-mensalista { background: white; border-radius: 14px; padding: 1.2rem; box-shadow: 0 1px 3px rgba(0,0,0,0.06); border: 2px solid #e5e7eb; transition: all 0.2s; margin-bottom: 1rem; }
    .card-mensalista.ativo { border-color: #10b981; }
    .card-mensalista.inativo { border-color: #ef4444; opacity: 0.85; }
    .card-mensalista .nome { font-weight: 700; font-size: 1.1rem; color: #111827; }
    .card-mensalista .info { font-size: 0.85rem; color: #6b7280; margin: 2px 0; }
    @media (max-width: 768px) {
        .main > div { padding: 0.75rem; }
        .card-executivo .kpi-value { font-size: 1.4rem; }
        .row-widget.stButton { width: 100%; }
        .row-widget.stButton > button { width: 100%; }
    }
    h1, h2, h3 { color: #111827; font-weight: 700; }
</style>
""", unsafe_allow_html=True)

# ============================================================
# HEADER
# ============================================================
col_logo, col_title = st.columns([1, 5])
with col_logo:
    logo_path = Path(__file__).parent / "imagem" / "lj.jpeg"
    if logo_path.exists():
        st.image(str(logo_path), width=80)
    else:
        st.markdown("## 🚗")
with col_title:
    st.markdown("<h1 style='margin:0;'>Lava Jato</h1>", unsafe_allow_html=True)
    st.markdown("<p style='color:#6b7280;margin-top:-5px;'>Sistema de Gestão</p>", unsafe_allow_html=True)
st.markdown("---")

if not check_password():
    st.stop()

# ============================================================
# ABAS
# ============================================================
tab1, tab2, tab3 = st.tabs(["📝 Registrar Lavagem", "👥 Mensalistas", "📊 Análises Executivas"])

# -------- ABA 1: REGISTRAR LAVAGEM --------
with tab1:
    col_form, col_history = st.columns([1, 1.5])
    with col_form:
        st.markdown("#### ✏️ Dados da Lavagem")
        tipo_veiculo = st.selectbox("Tipo de Veículo", ["Comum","SUV","Caminhonete","Moto"], key="tv")
        servicos_por_tipo = {
            "Comum": ["Completa", "Simples", "Ducha", "Motor", "Chaci", "Moto"],
            "SUV": ["Completa", "Simples", "Ducha", "Motor", "Chaci", "Moto"],
            "Caminhonete": ["Completa", "Simples", "Ducha", "Motor", "Chaci", "Moto"],
            "Moto": ["Moto"],
        }
        servico = st.selectbox("Serviço", servicos_por_tipo[tipo_veiculo], key="sv")
        valor_base = get_preco(tipo_veiculo, servico)
        quantidade = st.number_input("Quantidade", min_value=1, value=1, step=1, key="qtd")
        valor_total = valor_base * quantidade
        st.markdown(f"""<div style="background:#f3f4f6;border-radius:12px;padding:1rem;margin-bottom:1rem;"><p style="margin:0;color:#6b7280;font-size:0.85rem;">Valor Unitário</p><p style="margin:0;font-size:1.5rem;font-weight:800;color:#111827;">R$ {float(valor_base):.2f}</p><p style="margin:0;color:#6b7280;font-size:0.85rem;margin-top:0.5rem;">Valor Total ({quantidade}x)</p><p style="margin:0;font-size:1.8rem;font-weight:800;color:#1e3a5f;">R$ {float(valor_total):.2f}</p></div>""", unsafe_allow_html=True)
        data_lavagem = st.date_input("Data", value=date.today(), key="dl")
        cliente = st.text_input("Nome do Cliente", key="cl", placeholder="Nome (ou deixe vazio)")
        placa = st.text_input("Placa", key="pl", placeholder="Placa").upper()
        if st.button("💾 Registrar Lavagem", type="primary", use_container_width=True):
            nome_cliente = cliente.strip().upper() if cliente.strip() else f"{tipo_veiculo} #1"
            registrar_lavagem(data_lavagem.strftime("%Y-%m-%d"), tipo_veiculo, servico, valor_total, nome_cliente, placa.strip().upper(), quantidade)
            st.success(f"✅ Lavagem registrada: {nome_cliente} - {servico} - R$ {float(valor_total):.2f}")
            st.rerun()
    with col_history:
        st.markdown("#### 📋 Últimas Lavagens")
        df_lav = carregar_lavagens()
        if not df_lav.empty:
            df_lav['data'] = pd.to_datetime(df_lav['data'], errors='coerce')
            df_lav = df_lav.dropna(subset=['data']).reset_index(drop=True)

            cols = [c for c in ['data','cliente','tipo_veiculo','servico','quantidade','valor','placa'] if c in df_lav.columns]
            st.dataframe(df_lav[cols].head(20), use_container_width=True, hide_index=True)

            # Totalizador
            total = len(df_lav)
            qtd_total = int(df_lav['quantidade'].sum()) if 'quantidade' in df_lav.columns and not df_lav['quantidade'].isna().all() else total
            valor_total_lav = float(df_lav['valor'].sum()) if 'valor' in df_lav.columns else 0
            st.markdown(f"**Total: {total} lavagens | Quantidade total: {qtd_total} | Valor total: R$ {valor_total_lav:,.2f}**")
        else:
            st.info("Nenhuma lavagem registrada ainda.")

# -------- ABA 2: MENSALISTAS --------
with tab2:
    col_cad, col_lista = st.columns([1, 2])
    with col_cad:
        st.markdown("#### ➕ Novo Mensalista")
        if 'refresh_key' not in st.session_state:
            st.session_state.refresh_key = 0

    df_mens = carregar_mensalistas()
    with st.form("form_mens"):
            nome_m = st.text_input("Nome", key="nm").strip().upper()
            tel_m = st.text_input("Telefone", key="tm", placeholder="(99) 99999-9999")
            tipo_m = st.selectbox("Tipo", ["Comum","SUV","Caminhonete","Moto"], key="tpm")
            placa_m = st.text_input("Placa", key="pm").upper()
            plano_m = st.selectbox("Plano", ["Valor Fixo Mensal","Pacote de Lavagens"], key="plm")
            valor_m = st.number_input("Valor do Plano (R$)", min_value=0.0, step=10.0, key="vm")
            data_m = st.date_input("Data de Início", value=date.today(), key="dm")
            if st.form_submit_button("📥 Cadastrar", type="primary", use_container_width=True):
                if nome_m:
                    adicionar_mensalista(nome_m, tel_m, tipo_m, placa_m, plano_m, valor_m, data_m.strftime("%Y-%m-%d"))
                    st.success(f"✅ {nome_m} cadastrado como INATIVO")
                    st.rerun()
                else:
                    st.warning("Nome é obrigatório")
    with col_lista:
        df_mens = carregar_mensalistas()
        st.markdown("#### 📋 Mensalistas")
        if not df_mens.empty:
            total = len(df_mens); ativos = len(df_mens[df_mens['ativo']==1]); inativos = total - ativos
            receita_mensal = pd.to_numeric(df_mens.loc[df_mens['ativo']==1, 'valor_plano'], errors='coerce').sum()
            mk1, mk2, mk3, mk4 = st.columns(4)
            mk1.metric("Total", total); mk2.metric("Ativos", ativos); mk3.metric("Inativos", inativos)
            mk4.metric("Receita Mensal", f"R${float(receita_mensal):,.0f}".replace(",","X").replace(".",",").replace("X","."))
    st.markdown("---")
    df_mens['valor_plano'] = pd.to_numeric(df_mens['valor_plano'], errors='coerce').fillna(0)
    df_mens = df_mens.reset_index(drop=True)
    if df_mens.empty:
        st.info("Nenhum mensalista cadastrado.")
    else:
        for idx, row in df_mens.iterrows():
            ativo_val = int(row['ativo']) if row['ativo'] is not None else 0
            ativo_bool = bool(ativo_val)
            sc = "ativo" if ativo_bool else "inativo"
            stxt = "🟢 Ativo" if ativo_bool else "🔴 Inativo"
            cor_borda = "#10b981" if ativo_bool else "#ef4444"

            st.markdown(f"""<div class="card-mensalista {sc}" style="border: 2px solid {cor_borda} !important; opacity: {'1' if ativo_bool else '0.85'} !important;"><div style="display:flex;justify-content:space-between;align-items:start;"><div><div class="nome">{row['nome']}</div><div class="info">📞 {row['telefone']}</div><div class="info">{row['tipo']} | {row['placa']}</div><div class="info">{row['plano']} — R$ {float(row['valor_plano']):.2f}</div><div class="info">📅 Início: {row['data_inicio']}</div></div><div style="color:{cor_borda};font-weight:700;">{stxt}</div></div></div>""", unsafe_allow_html=True)

            c1, c2, c3 = st.columns([1,1,1])
            with c1:
                if st.button("🔄 Ativar/Desativar", key=f"t_{idx}", use_container_width=True):
                    toggle_mensalista(row['id'])
                    st.session_state.refresh_key = st.session_state.get('refresh_key', 0) + 1
                    st.rerun()
            with c2:
                if st.button("📝 Editar", key=f"e_{idx}", use_container_width=True):
                    st.session_state[f'ed_{idx}'] = True
            with c3:
                if st.button("🗑️ Excluir", key=f"d_{idx}", use_container_width=True):
                    excluir_mensalista(row['id'])
                    st.session_state.refresh_key = st.session_state.get('refresh_key', 0) + 1
                    st.rerun()

            if st.session_state.get(f'ed_{idx}', False):
                with st.form(f"ef_{idx}"):
                    en = st.text_input("Nome", value=row['nome'], key=f"en_{idx}")
                    et = st.text_input("Telefone", value=row['telefone'], key=f"et_{idx}")
                    etp = st.selectbox("Tipo", ["Comum","SUV","Caminhonete","Moto"], index=["Comum","SUV","Caminhonete","Moto"].index(row['tipo']) if row['tipo'] in ["Comum","SUV","Caminhonete","Moto"] else 0, key=f"etp_{idx}")
                    ep = st.text_input("Placa", value=row['placa'], key=f"ep_{idx}")
                    epl = st.selectbox("Plano", ["Valor Fixo Mensal","Pacote de Lavagens"], index=0 if row['plano']=="Valor Fixo Mensal" else 1, key=f"epl_{idx}")
                    ev = st.number_input("Valor", value=float(row['valor_plano']), key=f"ev_{idx}")
                    ed = st.date_input("Data", value=datetime.strptime(row['data_inicio'],"%Y-%m-%d").date() if row['data_inicio'] else date.today(), key=f"ed_{idx}")
                    ea = st.checkbox("Ativo", value=bool(row['ativo']), key=f"ea_{idx}")
                    if st.form_submit_button("💾 Salvar", use_container_width=True):
                        atualizar_mensalista(row['id'], en, et, etp, ep, epl, ev, ed.strftime("%Y-%m-%d"), 1 if ea else 0)
                        st.session_state[f'ed_{idx}'] = False
                        st.rerun()

            st.markdown("---")

# -------- ABA 3: ANÁLISES EXECUTIVAS --------
with tab3:
    st.markdown("#### 📊 Análises Executivas")
    df_lav = carregar_lavagens()
    df_mens = carregar_mensalistas()

    # Valores padrão
    if 'refresh_key' not in st.session_state:
        st.session_state.refresh_key = 0
    mes_sel = None
    ano_sel = None
    serv_sel = "Todos"
    df_filtro = pd.DataFrame()
    total_lav = 0
    receita_lav = 0
    ticket_medio = 0

    if not df_lav.empty:
        df_lav['data'] = pd.to_datetime(df_lav['data'], errors='coerce')
        df_lav = df_lav.dropna(subset=['data']).reset_index(drop=True)
        if not df_lav.empty:
            df_lav['mes'] = df_lav['data'].dt.month
            df_lav['ano'] = df_lav['data'].dt.year
            df_lav['mes_ano'] = df_lav['data'].dt.strftime('%Y-%m')
            df_lav['dia_semana'] = df_lav['data'].dt.dayofweek

            anos_disp = sorted(df_lav['ano'].unique(), reverse=True)
            meses_disp = sorted(int(m) for m in df_lav['mes'].unique() if pd.notna(m))
            flt1, flt2, flt3 = st.columns(3)
            with flt1:
                ano_sel = st.selectbox("Ano", anos_disp, key="as")
            with flt2:
                if meses_disp:
                    mes_sel = st.selectbox("Mês", [f"{int(m):02d}" for m in meses_disp], key="ms")
                else:
                    mes_sel = None
                    st.selectbox("Mês", ["—"], key="ms")
            with flt3:
                servs = sorted(df_lav['servico'].unique())
                serv_sel = st.selectbox("Serviço", ["Todos"] + servs, key="ss")

            if mes_sel is not None:
                df_filtro = df_lav[(df_lav['ano'] == ano_sel) & (df_lav['mes'] == int(mes_sel))]
            else:
                df_filtro = df_lav.copy()
            if serv_sel != "Todos":
                df_filtro = df_filtro[df_filtro['servico'] == serv_sel]

            qtd_total_lav = int(df_filtro['quantidade'].sum()) if 'quantidade' in df_filtro.columns and not df_filtro.empty else (len(df_filtro) if not df_filtro.empty else 0)
            total_lav = qtd_total_lav  # Agora total_lav = quantidade total
            receita_lav = float(df_filtro['valor'].sum()) if not df_filtro.empty else 0
            ticket_medio = receita_lav / qtd_total_lav if qtd_total_lav > 0 else 0
        else:
            st.info("Nenhuma lavagem com data válida.")
    else:
        st.info("Nenhuma lavagem registrada ainda.")

    # --- KPIs ---
    mens_ativos = len(df_mens[df_mens['ativo'] == 1]) if not df_mens.empty else 0
    meta_lav = 20; meta_rec = 3000; meta_mens = 3; meta_ticket = 120

    def sf(v, m):
        if v >= m: return "verde"
        elif v >= m * 0.7: return "amarelo"
        else: return "vermelho"

    s_lav = sf(total_lav, meta_lav)
    s_rec = sf(receita_lav, meta_rec)
    s_mens = sf(mens_ativos, meta_mens)
    s_tick = sf(ticket_medio, meta_ticket)

    k1, k2, k3, k4 = st.columns(4)
    for c, s, t, v, meta in [
        (k1, s_lav, "Lavagens no Mês", total_lav, meta_lav),
        (k2, s_rec, "Receita Lavagens", f"R$ {receita_lav:,.2f}", f"R$ {meta_rec:,.0f}"),
        (k3, s_mens, "Mensalistas Ativos", mens_ativos, meta_mens),
        (k4, s_tick, "Ticket Médio", f"R$ {ticket_medio:,.2f}", f"R$ {meta_ticket:,.0f}")
    ]:
        c.markdown(f"""<div class="card-executivo {s}"><div class="kpi-label">{t}</div><div class="kpi-value">{v}</div><div class="kpi-meta">Meta: {meta}</div><div class="semaforo {s}">{s.upper()}</div></div>""", unsafe_allow_html=True)

    st.markdown("---")

        # --- GRÁFICOS COLORIDOS (Altair) ---
    if not df_filtro.empty and 'data' in df_filtro.columns:
        
        col1, col2 = st.columns(2)

        with col1:
            # 📈 Receita Diária (colunas verdes)
            st.markdown("##### 📈 Receita Diária")
            df_dia = df_filtro.groupby(df_filtro['data'].dt.strftime('%d/%m')).agg({'valor': 'sum', 'quantidade': 'sum'}).reset_index().rename(columns={'data': 'dia'})
            if not df_dia.empty:
                import altair as alt
                chart = alt.Chart(df_dia).mark_bar(color='#10b981', size=20).encode(
                    x=alt.X('dia:N', title='', axis=alt.Axis(labelAngle=0)),
                    y=alt.Y('valor:Q', title='R$'),
                    tooltip=['dia', 'valor']
                ).properties(height=250)
                st.altair_chart(chart, use_container_width=True)

        with col2:
            # 🏆 Ranking de Serviços (cada serviço com uma cor)
            st.markdown("##### 🏆 Ranking de Serviços")
            df_serv = df_filtro.groupby('servico').agg({'quantidade': 'sum', 'valor': 'sum'}).reset_index().sort_values('quantidade', ascending=False)
            if not df_serv.empty:
                import altair as alt
                cores_servico_scale = alt.Scale(domain=['Completa','Simples','Ducha','Motor','Chaci','Moto'],
                                                 range=['#10b981','#3b82f6','#f59e0b','#ef4444','#8b5cf6','#ec4899'])
                chart = alt.Chart(df_serv).mark_bar(size=30).encode(
                    x=alt.X('quantidade:Q', title='Qtd'),
                    y=alt.Y('servico:N', title='', sort='-x'),
                    color=alt.Color('servico:N', scale=cores_servico_scale, legend=None),
                    tooltip=['servico', 'quantidade', 'valor']
                ).properties(height=250)
                st.altair_chart(chart, use_container_width=True)

        st.markdown("---")

        col3, col4 = st.columns(2)

        with col3:
            # 🚗 Lavagens por Tipo (cada tipo com uma cor)
            st.markdown("##### 🚗 Lavagens por Tipo")
            df_tipo = df_filtro.groupby('tipo_veiculo').agg({'quantidade': 'sum', 'valor': 'sum'}).reset_index().sort_values('quantidade', ascending=False)
            if not df_tipo.empty:
                import altair as alt
                cores_tipo_scale = alt.Scale(domain=['Comum','SUV','Caminhonete','Moto'],
                                              range=['#3b82f6','#10b981','#f59e0b','#ec4899'])
                chart = alt.Chart(df_tipo).mark_bar(size=30).encode(
                    x=alt.X('quantidade:Q', title='Qtd'),
                    y=alt.Y('tipo_veiculo:N', title='', sort='-x'),
                    color=alt.Color('tipo_veiculo:N', scale=cores_tipo_scale, legend=None),
                    tooltip=['tipo_veiculo', 'quantidade', 'valor']
                ).properties(height=250)
                st.altair_chart(chart, use_container_width=True)

        with col4:
            # 💰 Receita por Tipo
            st.markdown("##### 💰 Receita por Tipo")
            if not df_tipo.empty:
                import altair as alt
                cores_tipo_scale = alt.Scale(domain=['Comum','SUV','Caminhonete','Moto'],
                                              range=['#3b82f6','#10b981','#f59e0b','#ec4899'])
                chart = alt.Chart(df_tipo).mark_bar(size=30).encode(
                    x=alt.X('valor:Q', title='R$'),
                    y=alt.Y('tipo_veiculo:N', title='', sort='-x'),
                    color=alt.Color('tipo_veiculo:N', scale=cores_tipo_scale, legend=None),
                    tooltip=['tipo_veiculo', 'valor', 'quantidade']
                ).properties(height=250)
                st.altair_chart(chart, use_container_width=True)

                st.markdown("---")

        # 📊 INSIGHTS EXECUTIVOS
        st.markdown("##### 💡 Insights do Período")
        if not df_filtro.empty:
            col_i1, col_i2, col_i3 = st.columns(3)
            
            with col_i1:
                # Serviço mais vendido
                top_serv = df_filtro.groupby('servico')['quantidade'].sum().sort_values(ascending=False)
                if not top_serv.empty:
                    nome_top = top_serv.index[0]
                    qtd_top = int(top_serv.iloc[0])
                    st.markdown(f"""<div style="background:#f0fdf4;border-radius:12px;padding:1rem;border-left:4px solid #10b981;"><div style="font-size:0.75rem;color:#6b7280;font-weight:600;">🏆 SERVIÇO TOP</div><div style="font-size:1.3rem;font-weight:800;color:#111827;">{nome_top}</div><div style="font-size:0.9rem;color:#6b7280;">{qtd_top} unidades</div></div>""", unsafe_allow_html=True)
            
            with col_i2:
                # Tipo de veículo que mais lavou
                top_tipo = df_filtro.groupby('tipo_veiculo')['quantidade'].sum().sort_values(ascending=False)
                if not top_tipo.empty:
                    nome_tipo = top_tipo.index[0]
                    qtd_tipo = int(top_tipo.iloc[0])
                    st.markdown(f"""<div style="background:#eff6ff;border-radius:12px;padding:1rem;border-left:4px solid #3b82f6;"><div style="font-size:0.75rem;color:#6b7280;font-weight:600;">🚗 VEÍCULO TOP</div><div style="font-size:1.3rem;font-weight:800;color:#111827;">{nome_tipo}</div><div style="font-size:0.9rem;color:#6b7280;">{qtd_tipo} lavagens</div></div>""", unsafe_allow_html=True)
            
            with col_i3:
                # Ticket médio com análise
                cor_ticket = "#10b981" if ticket_medio >= meta_ticket else ("#f59e0b" if ticket_medio >= meta_ticket * 0.7 else "#ef4444")
                sinal_ticket = "🟢" if ticket_medio >= meta_ticket else ("🟡" if ticket_medio >= meta_ticket * 0.7 else "🔴")
                st.markdown(f"""<div style="background:#fefce8;border-radius:12px;padding:1rem;border-left:4px solid {cor_ticket};"><div style="font-size:0.75rem;color:#6b7280;font-weight:600;">{sinal_ticket} TICKET MÉDIO</div><div style="font-size:1.3rem;font-weight:800;color:#111827;">R$ {ticket_medio:.2f}</div><div style="font-size:0.9rem;color:#6b7280;">Meta: R$ {meta_ticket:.2f}</div></div>""", unsafe_allow_html=True)

            st.markdown("---")

            # 📊 Comparativo - Dia mais forte
            col_c1, col_c2 = st.columns(2)
            
            with col_c1:
                st.markdown("##### 📅 Dia da Semana com Mais Lavagens")
                df_dia_sem = df_filtro.groupby('dia_semana').agg({'quantidade': 'sum', 'valor': 'sum'}).reset_index()
                dias_nomes = {0:'Seg',1:'Ter',2:'Qua',3:'Qui',4:'Sex',5:'Sáb',6:'Dom'}
                if not df_dia_sem.empty:
                    df_dia_sem['dia'] = df_dia_sem['dia_semana'].map(dias_nomes)
                    st.bar_chart(df_dia_sem.set_index('dia')['quantidade'], use_container_width=True)

            with col_c2:
                st.markdown("##### 💰 Performance vs Meta")
                metas_df = pd.DataFrame({
                'Indicador': ['Lavagens', 'Receita', 'Mensalistas', 'Ticket'],
                'Atual': [qtd_total_lav, receita_lav, mens_ativos, ticket_medio],
                'Meta': [meta_lav, meta_rec, meta_mens, meta_ticket],
            })
                # Mostra como texto formatado
                for _, r in metas_df.iterrows():
                    pct = (r['Atual'] / r['Meta'] * 100) if r['Meta'] > 0 else 0
                    cor = "#10b981" if pct >= 100 else ("#f59e0b" if pct >= 70 else "#ef4444")
                    st.markdown(f"""<div style="display:flex;justify-content:space-between;padding:0.3rem 0;"><span style="font-weight:600;">{r['Indicador']}</span><span style="color:{cor};font-weight:700;">{r['Atual']:.1f} / {r['Meta']:.0f} ({pct:.0f}%)</span></div>""", unsafe_allow_html=True)
        else:
            st.info("Nenhum dado disponível para gerar insights no período selecionado.")

        

# ============================================================
# 📥 EXPORTAR RELATÓRIO
# ============================================================
st.markdown("---")
st.markdown("#### 📥 Exportar Relatório")
col_exp1, col_exp2 = st.columns(2)
with col_exp1:
    if st.button("📊 Baixar Excel", type="primary", use_container_width=True):
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_lav.to_excel(writer, sheet_name='Lavagens', index=False)
            if not df_mens.empty:
                df_mens.to_excel(writer, sheet_name='Mensalistas', index=False)
            if 'df_ano' in locals() and not df_ano.empty:
                resumo_export = df_ano.groupby('mes').agg(Lavagens=('id','count'),Receita=('valor','sum')).reset_index()
                resumo_export.columns = ['Mês', 'Lavagens', 'Receita']
                resumo_export.to_excel(writer, sheet_name='Resumo Mensal', index=False)
            if 'ranking' in locals() and not ranking.empty:
                ranking.to_excel(writer, sheet_name='Ranking Serviços', index=False)
        output.seek(0)
        st.download_button(
            label="💾 Salvar arquivo",
            data=output,
            file_name=f"relatorio_lava_jato_{datetime.now().strftime('%Y%m')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="dl_excel"
        )
with col_exp2:
    if st.button("📄 Baixar PDF", type="primary", use_container_width=True):
        try:
            from fpdf import FPDF
            pdf = FPDF()
            pdf.add_page()
            pdf.set_auto_page_break(auto=True, margin=15)
            pdf.set_font("Helvetica", "B", 18)
            pdf.cell(0, 15, "Relatorio Lava Jato", new_x="LMARGIN", new_y="NEXT", align="C")
            pdf.set_font("Helvetica", "", 10)
            pdf.cell(0, 8, f"Periodo: {mes_sel}/{ano_sel}  |  Gerado em {datetime.now().strftime('%d/%m/%Y %H:%M')}", new_x="LMARGIN", new_y="NEXT", align="C")
            pdf.ln(8)
            pdf.set_font("Helvetica", "B", 12)
            pdf.cell(0, 10, "Indicadores do Mes", new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", "", 10)
            pdf.cell(0, 7, f"Lavagens: {total_lav}  |  Receita: R$ {float(receita_lav):.2f}  |  Ticket Medio: R$ {float(ticket_medio):.2f}", new_x="LMARGIN", new_y="NEXT")
            pdf.cell(0, 7, f"Mensalistas Ativos: {mens_ativos}", new_x="LMARGIN", new_y="NEXT")
            pdf.ln(5)
            if 'ranking' in locals() and not ranking.empty:
                pdf.set_font("Helvetica", "B", 12)
                pdf.cell(0, 10, "Ranking de Servicos", new_x="LMARGIN", new_y="NEXT")
                pdf.set_font("Helvetica", "B", 10)
                col_w = [60, 40, 50]
                headers = ["Servico", "Lavagens", "Receita (R$)"]
                for i, h in enumerate(headers):
                    pdf.cell(col_w[i], 8, h, border=1, align="C")
                pdf.ln()
                pdf.set_font("Helvetica", "", 10)
                for _, r in ranking.head(10).iterrows():
                    pdf.cell(col_w[0], 7, str(r['servico']), border=1)
                    pdf.cell(col_w[1], 7, str(r['Lavagens']), border=1, align="C")
                    pdf.cell(col_w[2], 7, f"{float(r['Receita']):.2f}", border=1, align="R")
                    pdf.ln()
                pdf.ln(5)
            if 'df_ano' in locals() and not df_ano.empty:
                pdf.set_font("Helvetica", "B", 12)
                pdf.cell(0, 10, "Resumo Mensal", new_x="LMARGIN", new_y="NEXT")
                pdf.set_font("Helvetica", "B", 10)
                col_w2 = [40, 35, 45, 40]
                headers2 = ["Mes", "Lavagens", "Receita (R$)", "Dif. (%)"]
                for i, h in enumerate(headers2):
                    pdf.cell(col_w2[i], 8, h, border=1, align="C")
                pdf.ln()
                pdf.set_font("Helvetica", "", 10)
                res_comp = df_ano.groupby('mes').agg(Lavagens=('id','count'),Receita=('valor','sum')).reset_index()
                meses_nomes = {1:'Jan',2:'Fev',3:'Mar',4:'Abr',5:'Mai',6:'Jun',7:'Jul',8:'Ago',9:'Set',10:'Out',11:'Nov',12:'Dez'}
                res_comp['Dif.'] = res_comp['Receita'].pct_change() * 100
                for _, r in res_comp.iterrows():
                    pdf.cell(col_w2[0], 7, meses_nomes.get(int(r['mes']), str(r['mes'])), border=1, align="C")
                    pdf.cell(col_w2[1], 7, str(r['Lavagens']), border=1, align="C")
                    pdf.cell(col_w2[2], 7, f"{float(r['Receita']):.2f}", border=1, align="R")
                    dif = r['Dif.'] if pd.notna(r['Dif.']) else 0
                    pdf.cell(col_w2[3], 7, f"{dif:+.1f}%" if dif else "-", border=1, align="C")
                    pdf.ln()
                pdf.ln(5)
            pdf.set_font("Helvetica", "I", 8)
            pdf.cell(0, 10, "Relatorio gerado automaticamente pelo Sistema Lava Jato", new_x="LMARGIN", new_y="NEXT", align="C")
            pdf_bytes = pdf.output()
            st.download_button(
                label="💾 Salvar PDF",
                data=bytes(pdf_bytes),
                file_name=f"relatorio_lava_jato_{datetime.now().strftime('%Y%m')}.pdf",
                mime="application/pdf",
                key="dl_pdf"
            )
        except ImportError:
            st.warning("⚠️ Biblioteca fpdf2 necessária. Instale com: `pip install fpdf2` e tente novamente.")