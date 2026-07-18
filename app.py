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
        else:
            st.info("Nenhuma lavagem registrada ainda.")

# -------- ABA 2: MENSALISTAS --------
with tab2:
    col_cad, col_lista = st.columns([1, 2])
    with col_cad:
        st.markdown("#### ➕ Novo Mensalista")
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
    for idx, row in df_mens.iterrows():
        sc = "ativo" if row['ativo'] else "inativo"
        stxt = "🟢 Ativo" if row['ativo'] else "🔴 Inativo"
        st.markdown(f"""<div class="card-mensalista {sc}"><div style="display:flex;justify-content:space-between;align-items:start;"><div><div class="nome">{row['nome']}</div><div class="info">📞 {row['telefone'] or '—'}</div><div class="info">🚗 {row['tipo']} | {row['placa'] or '—'}</div><div class="info">📋 {row['plano']} — R$ {row['valor_plano']:.2f}</div><div class="info">📅 Início: {row['data_inicio'] or '—'}</div><div style="margin-top:6px;">{stxt}</div></div></div></div>""", unsafe_allow_html=True)
        c1, c2, c3 = st.columns([1,1,1])
        with c1:
            if st.button("🔄 Ativar/Desativar", key=f"t_{idx}", use_container_width=True):
                toggle_mensalista(row['id']); st.rerun()
        with c2:
            if st.button("✏️ Editar", key=f"e_{idx}", use_container_width=True):
                st.session_state[f'ed_{idx}'] = True
        with c3:
            if st.button("🗑️ Excluir", key=f"d_{idx}", use_container_width=True):
                excluir_mensalista(row['id']); st.rerun()
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
                    st.session_state[f'ed_{idx}'] = False; st.rerun()
        st.markdown("---")
    else:
        st.info("Nenhum mensalista cadastrado.")

# -------- ABA 3: ANÁLISES EXECUTIVAS --------
with tab3:
    st.markdown("#### 📊 Análises Executivas")
    df_lav = carregar_lavagens()
    df_mens = carregar_mensalistas()

    # Valores padrão ANTES de qualquer IF
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

            # FILTROS - tudo DENTRO do bloco interno
            if mes_sel is not None:
                df_filtro = df_lav[(df_lav['ano'] == ano_sel) & (df_lav['mes'] == int(mes_sel))]
            else:
                df_filtro = df_lav.copy()
            if serv_sel != "Todos":
                df_filtro = df_filtro[df_filtro['servico'] == serv_sel]

            total_lav = len(df_filtro)
            receita_lav = df_filtro['valor'].sum() if total_lav > 0 else 0
            ticket_medio = receita_lav / total_lav if total_lav > 0 else 0
        else:
            st.info("Nenhuma lavagem com data válida.")
    else:
        st.info("Nenhuma lavagem registrada ainda.")

    # --- KPIs (executa SEMPRE) ---
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

    # GRÁFICO - só se tiver dados
    if not df_filtro.empty and 'data' in df_filtro.columns:
        try:
            df_dia = df_filtro.groupby(df_filtro['data'].dt.strftime('%d/%m')).agg({'valor': 'sum', 'cliente': 'count'}).reset_index().rename(columns={'cliente': 'qtd', 'valor': 'receita'})
            st.markdown("##### 📈 Receita Diária")
            st.line_chart(df_dia.set_index('data')['receita'])
        except:
            pass

    st.markdown("---")
    st.markdown("##### 📋 Últimas Lavagens")
    if not df_filtro.empty:
        cols = [c for c in ['data', 'cliente', 'tipo_veiculo', 'servico', 'valor', 'placa', 'quantidade'] if c in df_filtro.columns]
        st.dataframe(df_filtro[cols].head(20), use_container_width=True, hide_index=True)
    else:
        st.info("Nenhuma lavagem para exibir.")

    # --- KPIs (executa sempre, mesmo vazio) ---
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

    # --- GRÁFICO (só se tiver dados filtrados) ---
    if not df_filtro.empty and 'data' in df_filtro.columns:
        try:
            df_dia = df_filtro.groupby(df_filtro['data'].dt.strftime('%d/%m')).agg({'valor': 'sum', 'cliente': 'count'}).reset_index().rename(columns={'cliente': 'qtd', 'valor': 'receita'})
            st.markdown("##### 📈 Receita Diária")
            st.line_chart(df_dia.set_index('data')['receita'])
        except:
            pass

    st.markdown("---")
    st.markdown("##### 📋 Últimas Lavagens")
    if not df_filtro.empty:
        cols = [c for c in ['data', 'cliente', 'tipo_veiculo', 'servico', 'valor', 'placa', 'quantidade'] if c in df_filtro.columns]
        st.dataframe(df_filtro[cols].head(20), use_container_width=True, hide_index=True)
    else:
        st.info("Nenhuma lavagem para exibir.")


    # Filtro seguro — sempre gera df_filtro
    if mes_sel is not None:
        df_filtro = df_lav[(df_lav['ano']==ano_sel)&(df_lav['mes']==int(mes_sel))]
    else:
        df_filtro = df_lav.copy()

    if serv_sel!="Todos":
        df_filtro = df_filtro[df_filtro['servico']==serv_sel]

        total_lav = len(df_filtro)
        receita_lav = df_filtro['valor'].sum() if total_lav>0 else 0
        ticket_medio = receita_lav/total_lav if total_lav>0 else 0
        mens_ativos = len(df_mens[df_mens['ativo']==1]) if not df_mens.empty else 0
        k1,k2,k3,k4 = st.columns(4)
        for c,s,t,v,meta in [(k1,s_lav,"Lavagens no Mês",total_lav,meta_lav),(k2,s_rec,"Receita Lavagens",f"R$ {receita_lav:,.2f}",f"R$ {meta_rec:,.0f}"),(k3,s_mens,"Mensalistas Ativos",mens_ativos,meta_mens),(k4,s_tick,"Ticket Médio",f"R$ {ticket_medio:,.2f}",f"R$ {meta_ticket:,.0f}")]:
            c.markdown(f"""<div class="card-executivo {s}"><div class="kpi-label">{t}</div><div class="kpi-value">{v}</div><div class="kpi-meta">Meta: {meta}</div><div class="semaforo {s}">{s.upper()}</div></div>""", unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("#### 📅 Lavagens por Dia da Semana")
        df_sem = df_filtro.copy()
        df_sem['dia_ordem'] = df_sem['data'].dt.dayofweek
        df_sem = df_sem[df_sem['dia_ordem']<=5]
        if not df_sem.empty:
            agg = df_sem.groupby(['dia_ordem','servico']).agg(Lavagens=('id','count'),Receita=('valor','sum')).reset_index()
            agg['dia_nome'] = agg['dia_ordem'].map({0:'Seg',1:'Ter',2:'Qua',3:'Qui',4:'Sex',5:'Sáb'})
            fig1 = px.bar(agg, x='dia_nome', y='Lavagens', color='servico', title="Lavagens por Dia da Semana", color_discrete_sequence=px.colors.qualitative.Bold, category_orders={'dia_nome':['Seg','Ter','Qua','Qui','Sex','Sáb']}, text='Lavagens')
            fig1.update_layout(height=350, margin=dict(l=10,r=10,t=40,b=30), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1), plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font=dict(family="Inter",size=12))
            fig1.update_traces(textposition='outside', textfont=dict(family="Arial Black",size=11))
            fig1.update_xaxes(title=None, showgrid=False); fig1.update_yaxes(title="Lavagens", showgrid=True, gridcolor='#f3f4f6')
            st.plotly_chart(fig1, use_container_width=True)

        st.markdown("---")
        st.markdown("#### 🏆 Ranking de Serviços")
        cg, ct = st.columns([1.5,1])
        ranking = df_filtro.groupby('servico').agg(Lavagens=('id','count'),Receita=('valor','sum')).reset_index().sort_values('Lavagens',ascending=False)
        with cg:
            if not ranking.empty:
                fig2 = px.bar(ranking, x='servico', y='Lavagens', color='servico', color_discrete_sequence=px.colors.qualitative.Bold, title="Serviços mais realizados", text='Lavagens')
                fig2.update_layout(height=300, showlegend=False, margin=dict(l=10,r=10,t=40,b=30), plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font=dict(family="Inter",size=12))
                fig2.update_traces(textposition='outside', textfont=dict(family="Arial Black",size=12))
                fig2.update_xaxes(title=None); fig2.update_yaxes(showgrid=True,gridcolor='#f3f4f6')
                st.plotly_chart(fig2, use_container_width=True)
        with ct:
            if not ranking.empty:
                rd = ranking.copy()
                rd['Receita'] = rd['Receita'].apply(lambda v: f"R$ {v:,.2f}".replace(",","X").replace(".",",").replace("X","."))
                rd.columns = ['Serviço','Lavagens','Receita']
                st.dataframe(rd, use_container_width=True, hide_index=True)
                melhor = ranking.iloc[0]
                st.markdown(f"""<div style="background:#eff6ff;border-radius:10px;padding:1rem;margin-top:0.5rem;"><span class="tag destaque">DESTAQUE</span><p style="margin:0.5rem 0 0 0;font-weight:600;">🏆 {melhor['servico']}</p><p style="margin:0;color:#6b7280;font-size:0.85rem;">{melhor['Lavagens']} lavagens — R$ {melhor['Receita']:,.2f}</p></div>""", unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("#### 📈 Evolução Mensal")
        col_graf, col_res = st.columns([2,1])
        with col_graf:
            df_ano = df_lav[df_lav['ano']==ano_sel].copy()
            if not df_ano.empty:
                evol = df_ano.groupby(['mes','servico']).agg(Lavagens=('id','count'),Receita=('valor','sum')).reset_index()
                rec_mes = df_ano.groupby('mes')['valor'].sum().reset_index()
                fig3 = go.Figure()
                for s in evol['servico'].unique():
                    ds = evol[evol['servico']==s]
                    fig3.add_trace(go.Bar(name=s, x=ds['mes'], y=ds['Lavagens'], text=ds['Lavagens'], textposition='outside'))
                fig3.add_trace(go.Scatter(x=rec_mes['mes'], y=rec_mes['valor'], mode='lines+markers', name='Receita (R$)', line=dict(color='#f59e0b',width=3), marker=dict(size=8), yaxis='y2'))
                if len(rec_mes)>0:
                    media = rec_mes['valor'].mean()
                    fig3.add_hline(y=media, line_dash="dash", line_color="#f59e0b", opacity=0.5, annotation_text=f"Média: R$ {media:,.0f}", annotation_position="bottom right")
                fig3.update_layout(height=350, barmode='stack', margin=dict(l=10,r=10,t=30,b=30), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1), plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font=dict(family="Inter",size=12), yaxis=dict(title="Lavagens",showgrid=True,gridcolor='#f3f4f6'), yaxis2=dict(title="Receita (R$)",overlaying='y',side='right',showgrid=False), hovermode='x unified')
                st.plotly_chart(fig3, use_container_width=True)
        with col_res:
            if not df_ano.empty:
                res = df_ano.groupby('mes').agg(Lavagens=('id','count'),Receita=('valor','sum')).reset_index()
                res['Mês'] = res['mes'].apply(lambda m: datetime(2000,int(m),1).strftime('%b'))
                res['Dif.'] = 0.0
                for i in range(1,len(res)):
                    ant = res.iloc[i-1]['Receita']
                    atu = res.iloc[i]['Receita']
                    if ant>0: res.loc[res.index[i],'Dif.'] = ((atu-ant)/ant)*100
                res['Rec.'] = res['Receita'].apply(lambda v: f"R$ {v:,.2f}".replace(",","X").replace(".",",").replace("X","."))
                def fd(v):
                    if v>0: return f"🟢 +{float(v):.1f}%"
                    elif v<0: return f"🔴 {float(v):.1f}%"
                    else: return "—"
                res['Dif.'] = res['Dif.'].apply(fd)
                th = "<table style='width:100%;border-collapse:collapse;font-size:0.8rem;'><thead><tr style='background:#1e3a5f;color:white;'><th style='padding:6px 8px;text-align:left;'>Mês</th><th style='padding:6px 8px;text-align:center;'>Lav.</th><th style='padding:6px 8px;text-align:right;'>Receita</th><th style='padding:6px 8px;text-align:center;'>Dif.</th></tr></thead><tbody>"
                for _, r in res.iterrows():
                    th += f"<tr style='border-bottom:1px solid #f3f4f6;'><td style='padding:6px 8px;font-weight:600;'>{r['Mês']}</td><td style='padding:6px 8px;text-align:center;'>{r['Lavagens']}</td><td style='padding:6px 8px;text-align:right;'>{r['Rec.']}</td><td style='padding:6px 8px;text-align:center;'>{r['Dif.']}</td></tr>"
                th += "</tbody></table>"
                st.markdown("#### 📋 Resumo Mensal")
                st.markdown(th, unsafe_allow_html=True)
                media_val = res['Receita'].mean()
                melhor = res.loc[res['Receita'].idxmax()]
                st.markdown(f"""<div style="background:#f0fdf4;border-radius:10px;padding:0.8rem;margin-top:0.8rem;"><p style="margin:0;color:#6b7280;font-size:0.75rem;">📊 Média Mensal</p><p style="margin:0;font-size:1.3rem;font-weight:800;color:#111827;">R$ {media_val:,.2f}</p><p style="margin:0;color:#6b7280;font-size:0.75rem;margin-top:0.5rem;">🏆 Melhor Mês</p><p style="margin:0;font-size:1rem;font-weight:700;color:#059669;">{melhor['Mês']} — R$ {float(melhor['Receita']):,.2f}</p><p style="margin:0;color:#6b7280;font-size:0.75rem;margin-top:0.5rem;">📅 Total: {res['Lavagens'].sum()} lavagens no ano</p></div>""", unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("#### 💡 Insights Executivos")
        insights = []
        if total_lav<meta_lav:
            insights.append(("atencao",f"📉 Lavagens abaixo da meta: {total_lav}/{meta_lav} no mês. Considere ações de marketing."))
        elif total_lav>=meta_lav*1.5:
            insights.append(("destaque",f"🔥 Lavagens muito acima da meta! {total_lav} no mês. Ótimo desempenho!"))
        else:
            insights.append(("oportunidade",f"✅ Meta de lavagens atingida: {total_lav}/{meta_lav}. Busque superar!"))
        if ticket_medio<meta_ticket:
            insights.append(("risco",f"💸 Ticket médio baixo: R$ {float(ticket_medio):.2f}. Ofereça serviços adicionais."))
        else:
            insights.append(("destaque",f"💰 Ticket médio saudável: R$ {float(ticket_medio):.2f}. Continue assim!"))
        if mens_ativos<meta_mens:
            insights.append(("atencao",f"👥 Poucos mensalistas ativos: {mens_ativos}/{meta_mens}. Crie promoções de fidelidade."))
        else:
            insights.append(("oportunidade",f"👥 Mensalistas ativos: {mens_ativos}. Base sólida!"))
        if not ranking.empty:
            insights.append(("destaque",f"🏆 Serviço mais popular: {ranking.iloc[0]['servico']} ({ranking.iloc[0]['Lavagens']} lavagens)."))
        if len(rec_mes)>=2:
            ultimos = rec_mes.sort_values('mes').tail(2)
            if len(ultimos)==2:
                var = ((ultimos.iloc[1]['valor']-ultimos.iloc[0]['valor'])/ultimos.iloc[0]['valor'])*100
                if var>10: insights.append(("destaque",f"📈 Faturamento cresceu {float(var):.1f}% em relação ao mês anterior!"))
                elif var<-10: insights.append(("risco",f"📉 Faturamento caiu {float(abs(var)):.1f}%. Atenção!"))
                else: insights.append(("oportunidade",f"📊 Faturamento estável ({var:+.1f}%). Busque crescimento."))
        for t, txt in insights:
            st.markdown(f"""<div style="background:white;border-radius:12px;padding:1rem;box-shadow:0 1px 3px rgba(0,0,0,0.06);margin-bottom:0.5rem;display:flex;align-items:center;gap:0.5rem;"><span class="tag {t}">{t.upper()}</span><span style="color:#374151;font-size:0.95rem;">{txt}</span></div>""", unsafe_allow_html=True)
    else:
        st.info("💡 Nenhum dado de lavagem ainda. Registre lavagens para ver as análises.")

    # ---- RESETAR BANCO (sempre visível na tab3) ----
    st.markdown("---")
    with st.expander("⚠️ **Administrador — Resetar Banco de Dados**"):
        col1, col2 = st.columns([1, 1])
        with col1:
            senha_reset = st.text_input("Digite a senha de administrador para resetar:", type="password", key="senha_reset")
        with col2:
            st.markdown("###  ")
            st.markdown("###  ")
            if st.button("🗑️ Resetar TODOS os dados", type="primary", use_container_width=True):
                if senha_reset == "admin757":
                    st.warning("⚠️ **ATENÇÃO!** Isso vai apagar TODAS as lavagens e mensalistas!")
                    col_confirm, _ = st.columns([1, 3])
                    with col_confirm:
                        if st.button("✅ CONFIRMAR RESET", type="primary", use_container_width=True):
                            try:
                                conn = get_conn()
                                with conn.cursor() as cur:
                                    cur.execute("DELETE FROM lavagens")
                                    cur.execute("DELETE FROM mensalistas")
                                conn.commit()
                                conn.close()
                                st.success("✅ Banco resetado com sucesso! Todos os dados foram apagados.")
                                st.cache_data.clear()
                                st.rerun()
                            except Exception as e:
                                st.error(f"Erro ao resetar: {e}")
                elif senha_reset:
                    st.error("❌ Senha incorreta!")

st.markdown(f"""<div style="text-align:center;color:#9ca3af;font-size:0.8rem;">🚗 Lava Jato Dashboard v2.0 · {datetime.now().strftime('%d/%m/%Y %H:%M')}</div>""", unsafe_allow_html=True)

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