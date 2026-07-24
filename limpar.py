import psycopg2
import os

DATABASE_URL = os.getenv("DATABASE_URL")
conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

# Remove registros onde id não é número (corrompidos)
cur.execute("DELETE FROM mensalistas WHERE id IS NULL OR id::text ~ '^[a-zA-Z]'")
# Remove lavagens corrompidas
cur.execute("DELETE FROM lavagens WHERE cliente = 'cliente' OR tipo_veiculo = 'tipo_veiculo'")
# Remove precos corrompidos
cur.execute("DELETE FROM precos WHERE tipo_veiculo IS NULL OR tipo_veiculo = ''")

conn.commit()
cur.close()
conn.close()

print("✅ Dados corrompidos removidos!")