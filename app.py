import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# --- CONFIGURAÇÃO DO BANCO DE DADOS (Tudo embutido no app.py) ---
NOME_BANCO = "dados_confeitaria.db"

def conectar():
    return sqlite3.connect(NOME_BANCO)

def criar_tabelas():
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ingredientes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT UNIQUE NOT NULL,
        unidade_medida TEXT NOT NULL,
        quantidade_estoque REAL DEFAULT 0,
        custo_total REAL DEFAULT 0
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS produtos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT UNIQUE NOT NULL,
        preco_venda REAL NOT NULL,
        custo_producao REAL DEFAULT 0
    )
    """)

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

# Executa a criação das tabelas automaticamente na inicialização
criar_tabelas()

# --- INTERFACE VISUAL (STREAMLIT) ---
st.set_page_config(page_title="Gestão de Sobremesas", layout="wide")
st.title("🍰 Gestão & Venda de Sobremesas")

menu = st.sidebar.radio(
    "Navegação",
    [
        "Abertura/Fechamento de Caixa",
        "PDV - Registrar Venda",
        "Estoque de Ingredientes",
        "Ficha Técnica & Custos",
        "Gestão de Fiados",
        "Relatórios & Divisão de Lucro"
    ]
)

# -------------------------------------------------------------------
# 1. ABERTURA E FECHAMENTO DE CAIXA
# -------------------------------------------------------------------
if menu == "Abertura/Fechamento de Caixa":
    st.header("🔑 Controle de Caixa")
    conn = conectar()
    
    df_caixa = pd.read_sql_query("SELECT * FROM caixa WHERE status = 'ABERTO'", conn)
    
    if df_caixa.empty:
        st.warning("O caixa está fechado no momento.")
        saldo_inicial = st.number_input("Valor inicial em carteira (espécie):", min_value=0.0, step=5.0)
        if st.button("Abrir Caixa"):
            data_atual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            conn.execute(
                "INSERT INTO caixa (data_abertura, saldo_inicial, status) VALUES (?, ?, 'ABERTO')",
                (data_atual, saldo_inicial)
            )
            conn.commit()
            st.success("Caixa aberto com sucesso!")
            st.rerun()
    else:
        caixa_atual = df_caixa.iloc[0]
        st.success(f"Caixa Aberto desde: {caixa_atual['data_abertura']}")
        st.metric("Saldo Inicial", f"R$ {caixa_atual['saldo_inicial']:.2f}")

        df_vendas = pd.read_sql_query(
            "SELECT * FROM vendas WHERE caixa_id = ? AND status_pagamento = 'PAGO'",
            conn,
            params=(caixa_atual['id'],)
        )
        
        pix_total = df_vendas[df_vendas['destino_pagamento'] == 'PIX']['valor_total'].sum() if not df_vendas.empty else 0.0
        especie_total = df_vendas[df_vendas['destino_pagamento'] == 'ESPECIE']['valor_total'].sum() if not df_vendas.empty else 0.0
        
        col1, col2 = st.columns(2)
        col1.metric("Entradas via PIX (Conta)", f"R$ {pix_total:.2f}")
        col2.metric("Entradas em Espécie (Carteira)", f"R$ {especie_total:.2f}")

        if st.button("Fechar Caixa"):
            saldo_final = caixa_atual['saldo_inicial'] + especie_total
            data_fechamento = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            conn.execute(
                "UPDATE caixa SET data_fechamento = ?, saldo_final = ?, status = 'FECHADO' WHERE id = ?",
                (data_fechamento, saldo_final, caixa_atual['id'])
            )
            conn.commit()
            st.info(f"Caixa Fechado. Total em Espécie na Carteira: R$ {saldo_final:.2f}")
            st.rerun()
            
    conn.close()

# -------------------------------------------------------------------
# 2. PDV - REGISTRAR VENDA
# -------------------------------------------------------------------
elif menu == "PDV - Registrar Venda":
    st.header("🛒 Registrar Venda")
    conn = conectar()
    
    df_caixa = pd.read_sql_query("SELECT * FROM caixa WHERE status = 'ABERTO'", conn)
    
    if df_caixa.empty:
        st.error("Abra o caixa antes de realizar vendas.")
    else:
        caixa_id = df_caixa.iloc[0]['id']
        df_produtos = pd.read_sql_query("SELECT * FROM produtos", conn)
        
        if df_produtos.empty:
            st.warning("Cadastre produtos na aba 'Ficha Técnica & Custos' primeiro.")
        else:
            produto_sel = st.selectbox("Selecione a Sobremesa:", df_produtos['nome'])
            prod_info = df_produtos[df_produtos['nome'] == produto_sel].iloc[0]
            
            qtd = st.number_input("Quantidade:", min_value=1, value=1)
            
            forma_pagamento = st.radio("Forma de Recebimento:", ["PIX (Conta Bancária)", "Espécie (Carteira)", "Fiado (A Receber)"])
            cliente = ""
            if forma_pagamento == "Fiado (A Receber)":
                cliente = st.text_input("Nome do Cliente:")

            valor_total = prod_info['preco_venda'] * qtd
            custo_total = prod_info['custo_producao'] * qtd
            taxa_operacional = valor_total * 0.10  # 10% custos operacionais
            lucro_bruto = valor_total - custo_total
            lucro_liquido = lucro_bruto - taxa_operacional

            st.write("---")
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Valor Total", f"R$ {valor_total:.2f}")
            col2.metric("Custo Ingredientes", f"R$ {custo_total:.2f}")
            col3.metric("Taxa Op. (10%)", f"R$ {taxa_operacional:.2f}")
            col4.metric("Lucro Líquido", f"R$ {lucro_liquido:.2f}")

            if st.button("Finalizar Venda"):
                if forma_pagamento == "Fiado (A Receber)" and not cliente.strip():
                    st.error("Informe o nome do cliente para registrar o fiado.")
                else:
                    destino = "PIX" if "PIX" in forma_pagamento else ("ESPECIE" if "Espécie" in forma_pagamento else "FIADO")
                    status_pag = "PENDENTE" if destino == "FIADO" else "PAGO"
                    data_venda = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                    conn.execute("""
                        INSERT INTO vendas (
                            caixa_id, data_venda, valor_total, custo_total, 
                            taxa_operacional, lucro_bruto, lucro_liquido, 
                            destino_pagamento, status_pagamento, cliente
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (caixa_id, data_venda, valor_total, custo_total, 
                          taxa_operacional, lucro_bruto, lucro_liquido, 
                          destino, status_pag, cliente))
                    conn.commit()
                    st.success("Venda registrada com sucesso!")
                    
    conn.close()

# -------------------------------------------------------------------
# 3. ESTOQUE DE INGREDIENTES
# -------------------------------------------------------------------
elif menu == "Estoque de Ingredientes":
    st.header("📦 Entrada/Saída de Ingredientes")
    conn = conectar()
    
    with st.form("cad_ingrediente"):
        st.subheader("Cadastrar / Atualizar Ingrediente")
        nome = st.text_input("Nome do Ingrediente (ex: Leite Condensado)")
        unidade = st.selectbox("Unidade:", ["g", "kg", "ml", "L", "unidade"])
        qtd = st.number_input("Quantidade Adicionada:", min_value=0.0, step=100.0)
        custo = st.number_input("Custo Total dessa compra (R$):", min_value=0.0, step=1.0)
        
        submitted = st.form_submit_button("Salvar no Estoque")
        if submitted and nome:
            cursor = conn.cursor()
            cursor.execute("SELECT quantidade_estoque, custo_total FROM ingredientes WHERE nome = ?", (nome,))
            row = cursor.fetchone()
            
            if row:
                nova_qtd = row[0] + qtd
                novo_custo = row[1] + custo
                cursor.execute(
                    "UPDATE ingredientes SET quantidade_estoque = ?, custo_total = ?, unidade_medida = ? WHERE nome = ?",
                    (nova_qtd, novo_custo, unidade, nome)
                )
            else:
                cursor.execute(
                    "INSERT INTO ingredientes (nome, unidade_medida, quantidade_estoque, custo_total) VALUES (?, ?, ?, ?)",
                    (nome, unidade, qtd, custo)
                )
            conn.commit()
            st.success("Estoque atualizado!")

    st.subheader("Estoque Atual")
    df_est = pd.read_sql_query("SELECT * FROM ingredientes", conn)
    st.dataframe(df_est, use_container_width=True)
    conn.close()

# -------------------------------------------------------------------
# 4. FICHA TÉCNICA & CUSTOS
# -------------------------------------------------------------------
elif menu == "Ficha Técnica & Custos":
    st.header("🍰 Cadastro de Produtos e Custo")
    conn = conectar()
    
    with st.form("cad_produto"):
        st.subheader("Cadastrar Produto Final")
        nome_prod = st.text_input("Nome da Sobremesa (ex: Copo da Felicidade)")
        custo_prod = st.number_input("Custo total estimado de ingredientes por unidade (R$):", min_value=0.0, step=0.5)
        preco_venda = st.number_input("Preço de Venda ao Cliente (R$):", min_value=0.0, step=1.0)
        
        if st.form_submit_button("Cadastrar Produto"):
            if nome_prod and preco_venda > 0:
                conn.execute(
                    "INSERT OR REPLACE INTO produtos (nome, preco_venda, custo_producao) VALUES (?, ?, ?)",
                    (nome_prod, preco_venda, custo_prod)
                )
                conn.commit()
                st.success("Produto cadastrado com sucesso!")

    st.subheader("Produtos Cadastrados")
    df_prod = pd.read_sql_query("SELECT * FROM produtos", conn)
    st.dataframe(df_prod, use_container_width=True)
    conn.close()

# -------------------------------------------------------------------
# 5. GESTÃO DE FIADOS
# -------------------------------------------------------------------
elif menu == "Gestão de Fiados":
    st.header("📋 Contas a Receber (Fiados)")
    conn = conectar()
    
    df_fiados = pd.read_sql_query("SELECT * FROM vendas WHERE status_pagamento = 'PENDENTE'", conn)
    
    if df_fiados.empty:
        st.info("Nenhum fiado pendente!")
    else:
        st.dataframe(df_fiados[['id', 'data_venda', 'cliente', 'valor_total']], use_container_width=True)
        
        venda_id = st.selectbox("Selecione a venda para quitar:", df_fiados['id'])
        meio_quitacao = st.radio("Recebido via:", ["PIX (Conta Bancária)", "Espécie (Carteira)"])
        
        if st.button("Confirmar Pagamento"):
            destino = "PIX" if "PIX" in meio_quitacao else "ESPECIE"
            conn.execute(
                "UPDATE vendas SET status_pagamento = 'PAGO', destino_pagamento = ? WHERE id = ?",
                (destino, venda_id)
            )
            conn.commit()
            st.success("Fiado quitado com sucesso!")
            st.rerun()
            
    conn.close()

# -------------------------------------------------------------------
# 6. RELATÓRIOS & DIVISÃO DE LUCRO
# -------------------------------------------------------------------
elif menu == "Relatórios & Divisão de Lucro":
    st.header("📊 Relatórios Financeiros")
    conn = conectar()
    
    df_vendas_todas = pd.read_sql_query("SELECT * FROM vendas WHERE status_pagamento = 'PAGO'", conn)
    
    if df_vendas_todas.empty:
        st.info("Nenhuma venda paga encontrada para gerar relatórios.")
    else:
        tot_faturado = df_vendas_todas['valor_total'].sum()
        tot_custo = df_vendas_todas['custo_total'].sum()
        tot_operacional = df_vendas_todas['taxa_operacional'].sum()
        tot_bruto = df_vendas_todas['lucro_bruto'].sum()
        tot_liquido = df_vendas_todas['lucro_liquido'].sum()

        col1, col2, col3 = st.columns(3)
        col1.metric("Faturamento Total", f"R$ {tot_faturado:.2f}")
        col2.metric("Custo Ingredientes", f"R$ {tot_custo:.2f}")
        col3.metric("Fundo Operacional (10%)", f"R$ {tot_operacional:.2f}")

        col4, col5 = st.columns(2)
        col4.metric("Lucro Bruto", f"R$ {tot_bruto:.2f}")
        col5.metric("Lucro Líquido Disponível", f"R$ {tot_liquido:.2f}")

        st.write("---")
        st.subheader("🏦 Destino do Dinheiro")
        pix_total = df_vendas_todas[df_vendas_todas['destino_pagamento'] == 'PIX']['valor_total'].sum()
        especie_total = df_vendas_todas[df_vendas_todas['destino_pagamento'] == 'ESPECIE']['valor_total'].sum()
        
        c1, c2 = st.columns(2)
        c1.metric("Total em Conta Bancária (PIX)", f"R$ {pix_total:.2f}")
        c2.metric("Total em Carteira (Espécie)", f"R$ {especie_total:.2f}")

        st.write("---")
        st.subheader("💰 Divisão do Lucro Líquido & Reserva")
        
        col_res1, col_res2 = st.columns(2)
        perc_reserva = col_res1.slider("Porcentagem para Reserva de Emergência (%)", 0, 50, 20)
        num_pessoas = col_res2.number_input("Número de pessoas para dividir o lucro:", min_value=1, value=2)

        reserva_valor = tot_liquido * (perc_reserva / 100)
        lucro_distribuivel = tot_liquido - reserva_valor
        valor_por_pessoa = lucro_distribuivel / num_pessoas

        st.info(f"**Reserva de Emergência ({perc_reserva}%):** R$ {reserva_valor:.2f}")
        st.success(f"**Valor a distribuir ({100 - perc_reserva}%):** R$ {lucro_distribuivel:.2f}")
        st.write(f"👉 **Cada pessoa recebe:** **R$ {valor_por_pessoa:.2f}**")

        st.write("---")
        st.subheader("📈 Evolução das Vendas")
        df_vendas_todas['data'] = pd.to_datetime(df_vendas_todas['data_venda']).dt.date
        grafico_data = df_vendas_todas.groupby('data')['valor_total'].sum()
        st.line_chart(grafico_data)

    conn.close()