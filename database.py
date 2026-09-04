import sqlite3

def conectar():
    return sqlite3.connect("dados_confeitaria.db")

def criar_tabelas():
    conn = conectar()
    cursor = conn.cursor()

    # Tabela de Ingredientes / Estoque
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ingredientes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT UNIQUE NOT NULL,
        unidade_medida TEXT NOT NULL,
        quantidade_estoque REAL DEFAULT 0,
        custo_total REAL DEFAULT 0
    )
    """)

    # Tabela de Produtos / Ficha Técnica
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS produtos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT UNIQUE NOT NULL,
        preco_venda REAL NOT NULL,
        custo_producao REAL DEFAULT 0
    )
    """)

    # Tabela do Caixa
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS caixa (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        data_abertura TEXT NOT NULL,
        data_fechamento TEXT,
        saldo_inicial REAL DEFAULT 0,
        saldo_final REAL,
        status TEXT DEFAULT 'ABERTO'
    )
    """)

    # Tabela de Vendas
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS vendas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        caixa_id INTEGER,
        data_venda TEXT NOT NULL,
        valor_total REAL NOT NULL,
        custo_total REAL NOT NULL,
        taxa_operacional REAL NOT NULL,
        lucro_bruto REAL NOT NULL,
        lucro_liquido REAL NOT NULL,
        destino_pagamento TEXT NOT NULL,
        status_pagamento TEXT DEFAULT 'PAGO',
        cliente TEXT,
        FOREIGN KEY (caixa_id) REFERENCES caixa(id)
    )
    """)

    conn.commit()
    conn.close()

if __name__ == "__main__":
    criar_tabelas()
    print("Banco de dados configurado com sucesso!")