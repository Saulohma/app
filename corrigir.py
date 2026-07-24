with open("app.py", "r", encoding="utf-8") as f:
    codigo = f.read()

# 1) CORRIGE excluir_mensalista — troca conn.execute por conn.cursor().execute()
antigo = """def excluir_mensalista(id):
    conn.execute("DELETE FROM mensalistas WHERE id=%s", (id,))
    conn.commit()"""

novo = """def excluir_mensalista(id):
    with conn.cursor() as cur:
        cur.execute("DELETE FROM mensalistas WHERE id=%s", (id,))
    conn.commit()"""

if antigo in codigo:
    codigo = codigo.replace(antigo, novo)
    print("✅ Função excluir_mensalista corrigida!")
else:
    print("⚠️ Padrão excluir_mensalista não encontrado. Verifique manualmente.")

# 2) CORRIGE toggle_mensalista (se tiver o mesmo problema)
antigo2 = """def toggle_mensalista(id):
    conn.execute("UPDATE mensalistas SET ativo = NOT ativo WHERE id=%s", (id,))
    conn.commit()"""

novo2 = """def toggle_mensalista(id):
    with conn.cursor() as cur:
        cur.execute("UPDATE mensalistas SET ativo = NOT ativo WHERE id=%s", (id,))
    conn.commit()"""

if antigo2 in codigo:
    codigo = codigo.replace(antigo2, novo2)
    print("✅ Função toggle_mensalista corrigida!")
else:
    print("⚠️ Padrão toggle_mensalista não encontrado. Verifique manualmente.")

# 3) CORRIGE atualizar_mensalista (se tiver o mesmo problema)
antigo3 = """def atualizar_mensalista(id, nome, telefone, tipo, placa, plano, valor, data_inicio, ativo):
    conn.execute("UPDATE mensalistas SET nome=%s,telefone=%s,tipo=%s,placa=%s,plano=%s,valor_plano=%s,data_inicio=%s,ativo=%s WHERE id=%s", (nome, telefone, tipo, placa, plano, valor, data_inicio, ativo, id))
    conn.commit()"""

novo3 = """def atualizar_mensalista(id, nome, telefone, tipo, placa, plano, valor, data_inicio, ativo):
    with conn.cursor() as cur:
        cur.execute("UPDATE mensalistas SET nome=%s,telefone=%s,tipo=%s,placa=%s,plano=%s,valor_plano=%s,data_inicio=%s,ativo=%s WHERE id=%s", (nome, telefone, tipo, placa, plano, valor, data_inicio, ativo, id))
    conn.commit()"""

if antigo3 in codigo:
    codigo = codigo.replace(antigo3, novo3)
    print("✅ Função atualizar_mensalista corrigida!")
else:
    print("⚠️ Padrão atualizar_mensalista não encontrado. Verifique manualmente.")

# 4) Adiciona limpeza dos dados corrompidos no início da aba de lavagens
# Procura a função carregar_lavagens e adiciona limpeza
if "def carregar_lavagens" in codigo:
    # Adiciona uma função de limpeza
    funcao_limpeza = """
def limpar_dados_corrompidos():
    \"\"\"Remove registros com dados de migração corrompidos\"\"\"
    with conn.cursor() as cur:
        cur.execute("DELETE FROM lavagens WHERE cliente IS NULL OR cliente = '' OR cliente = 'cliente'")
        cur.execute("DELETE FROM mensalistas WHERE nome IS NULL OR nome = '' OR nome = 'nome'")
        cur.execute("DELETE FROM precos WHERE tipo_veiculo IS NULL OR tipo_veiculo = ''")
    conn.commit()
"""
    # Insere depois do último import
    if "limpar_dados_corrompidos" not in codigo:
        # Encontra um bom lugar para inserir (depois de carregar_lavagens)
        import re
        # Procura por "def carregar_" e insere antes
        match = re.search(r'(def carregar_|conn = get_connection)', codigo)
        if match:
            pos = match.start()
            # Procura uma linha em branco antes
            while pos > 0 and codigo[pos] != '\n':
                pos -= 1
            codigo = codigo[:pos] + "\n" + funcao_limpeza + codigo[pos:]
            print("✅ Função limpar_dados_corrompidos adicionada!")
    
    # Chama a limpeza antes de carregar os dados na tab3
    codigo = codigo.replace(
        "df_lav = carregar_lavagens()\n    df_mens = carregar_mensalistas()",
        "limpar_dados_corrompidos()\n    df_lav = carregar_lavagens()\n    df_mens = carregar_mensalistas()"
    )
    print("✅ Limpeza de dados corrompidos inserida antes do carregamento!")

with open("app.py", "w", encoding="utf-8") as f:
    f.write(codigo)

print("\n🎯 Todas as correções aplicadas!")