from datetime import datetime
import pandas as pd
import streamlit as st

# Configuração da Página
st.set_page_config(
    page_title="B. Braun - Gestão Offline de Stock (SAP)",
    page_icon="📦",
    layout="wide",
)

# Estilização CSS personalizada (Tema profissional B. Braun)
st.markdown(
    """
    <style>
    .main {
        background-color: #f8f9fa;
    }
    .stButton>button {
        width: 100%;
        border-radius: 6px;
        font-weight: bold;
    }
    .bbraun-footer {
        position: fixed;
        left: 0;
        bottom: 0;
        width: 100%;
        background-color: #003366;
        color: white;
        text-align: center;
        padding: 8px;
        font-size: 14px;
        font-weight: 600;
        z-index: 1000;
    }
    .metric-card {
        background-color: white;
        padding: 15px;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    </style>
    <div class="bbraun-footer">
        B. Braun - Sharing Expertise | Sistema Offline de Movimentação de Stock
    </div>
    """,
    unsafe_allow_html=True,
)

# Dicionário de Utilizadores permitidos
UTILIZADORES = {
    "João Rodrigues": "rodrjopt",
    "Sérgio Fernandes": "fernsept",
    "Cristina Mendes": "mendcrpt",
    "Adriano Valdes": "valdadpt",
}

# Inicialização do Estado da Sessão (Session State)
if "utilizador_atual" not in st.session_state:
    st.session_state.utilizador_atual = None

if "stock_df" not in st.session_state:
    st.session_state.stock_df = None

if "movimentos_df" not in st.session_state:
    # Criar DataFrame para histórico de movimentos
    st.session_state.movimentos_df = pd.DataFrame(
        columns=[
            "Data/Hora",
            "Utilizador",
            "ID_User",
            "Tipo_Movimento",
            "Armazem",
            "Material",
            "Lote",
            "Quantidade",
            "Localizacao",
        ]
    )

# ==========================================
# 1. ECRÃ DE LOGIN / IDENTIFICAÇÃO DE USER
# ==========================================
if st.session_state.utilizador_atual is None:
  st.markdown(
      "<h1 style='text-align: center; color: #003366;'>B. BRAUN - GESTÃO"
      " OFFLINE</h1>",
      unsafe_allow_html=True,
  )
  st.markdown(
      "<h3 style='text-align: center; color: #555;'>Identificação do"
      " Operador</h3>",
      unsafe_allow_html=True,
  )
  st.markdown("---")

  col1, col2, col3 = st.columns([1, 2, 1])
  with col2:
    st.info("Por favor, selecione o seu nome para entrar na aplicação.")
    nome_selecionado = st.selectbox(
        "Operador", ["-- Selecione o Utilizador --"] + list(UTILIZADORES.keys())
    )

    if st.button("Entrar no Sistema", type="primary"):
      if nome_selecionado != "-- Selecione o Utilizador --":
        st.session_state.utilizador_atual = {
            "nome": nome_selecionado,
            "id": UTILIZADORES[nome_selecionado],
        }
        st.rerun()
      else:
        st.warning("Tem de selecionar um utilizador válido.")

  st.stop()

# ==========================================
# 2. MENU PRINCIPAL (COM SISTEMA ATIVO)
# ==========================================
user_info = st.session_state.utilizador_atual

# Cabeçalho Superior com Info de Utilizador
col_h1, col_h2 = st.columns([3, 1])
with col_h1:
  st.markdown(
      "## 📦 B. Braun - Controlo de Stock em Modo Offline (SAP)"
  )
with col_h2:
  st.markdown(
      f"👤 **{user_info['nome']}** (`{user_info['id']}`)"
  )
  if st.button("🚪 Alterar Utilizador"):
    st.session_state.utilizador_atual = None
    st.rerun()

st.markdown("---")

# Barra Lateral para Carregamento Único do Ficheiro SAP (Espelho de Stock)
with st.sidebar:
  st.image(
      "https://www.bbraun.com/content/dam/b-braun/global/b-braun-logo.svg",
      width=160,
  )
  st.markdown("### Configuração do Sistema")
  st.markdown(
      "Carregue o **espelho de stock do SAP** (.txt/.csv) obtido antes da"
      " falha de sistema."
  )

  ficheiro_carregado = st.file_uploader(
      "Ficheiro Espelho de Stock", type=["txt", "csv"]
  )

  if ficheiro_carregado is not None:
    try:
      # Leitura robusta do relatório SAP
      df_temp = pd.read_csv(
          ficheiro_carregado,
          sep=None,
          engine="python",
          encoding="latin1",
          skipinitialspace=True,
      )
      df_temp.columns = df_temp.columns.str.strip()
      st.session_state.stock_df = df_temp
      st.success("Espelho de stock carregado com sucesso!")
    except Exception as e:
      st.error(f"Erro ao ler ficheiro: {e}")

  if st.session_state.stock_df is not None:
    st.metric("Total Registos em Stock", len(st.session_state.stock_df))
  else:
    st.warning("⚠️ Nenhum espelho de stock carregado!")

  st.markdown("---")
  st.markdown(
      "*Nota: Este sistema processa estritamente saídas por FEFO para os"
      " armazéns PT01 e PT97.*"
  )

# Se não houver stock carregado, bloquear operações de saída e consulta
if st.session_state.stock_df is None:
  st.warning(
      "⚠️ **Atenção:** Para começar a utilizar as opções de saída e consulta,"
      " por favor carregue o ficheiro de espelho de stock do SAP na barra"
      " lateral esquerda."
  )
  st.stop()

# Abas Principais da Aplicação
aba_saida_amostra, aba_saida_geral, aba_consulta, aba_movimentos = st.tabs([
    "🧪 Saída Amostra (PT97)",
    "📦 Saída Geral (PT01)",
    "🔍 Consulta Stock",
    "📋 Histórico de Movimentos",
)


# Função auxiliar para executar a lógica FEFO de baixa de stock
def executar_saida_fefo(material, quantidade_pretendida, armazem_alvo):
  df = st.session_state.stock_df

  # Filtrar colunas relevantes (ajustar conforme nomenclaturas padrão SAP se necessário)
  # Assumimos colunas comuns: 'Material', 'Armazém' (ou 'Centro/Arm.'), 'Lote', 'Stock', 'Validade', 'Localização'
  # Vamos procurar colunas correspondentes de forma flexível ou assumir nomes padronizados do SAP.
  colunas = [c.lower() for c in df.columns]

  # Tentativa de mapeamento inteligente de colunas comuns do SAP Depot View
  def achar_coluna(termos):
    for t in termos:
      for col in df.columns:
        if t in col.lower():
          return col
    return None

  col_mat = achar_coluna(["material", "artigo", "mat."])
  col_arm = achar_coluna(["armazém", "armazem", "storage location", "sloc", "lgort"])
  col_qtd = achar_coluna(["stock", "quantidade", "qtd", "unidades", "libre"])
  col_lote = achar_coluna(["lote", "batch", "charg"])
  col_val = achar_coluna(["validade", "shelf life", "data", "fefo", "best before"])
  col_loc = achar_coluna(["localização", "localizacao", "pos."])

  if not col_mat or not col_qtd or not col_arm:
    st.error(
        "O formato do ficheiro SAP não contém colunas reconhecíveis para"
        " Material, Armazém ou Quantidade."
    )
    return False

  # Filtrar por armazém pretendido (PT97 ou PT01) e material
  # Normalizar texto para busca
  df_mat = df[
      (df[col_mat].astype(str).str.contains(str(material), case=False, na=False))
      & (df[col_arm].astype(str).str.contains(str(armazem_alvo), case=False, na=False))
  ].copy()

  if df_mat.empty:
    st.error(f"Não existe stock registado para o material {material} no armazém {armazem_alvo}.")
    return False

  # Converter coluna de quantidade para numérica
  df_mat[col_qtd] = pd.to_numeric(
      df_mat[col_qtd].astype(str).str.replace(",", "."), errors="coerce"
  ).fillna(0)

  # Verificar stock total disponível neste armazém para este material
  stock_total_disponivel = df_mat[col_qtd].sum()

  if stock_total_disponivel < quantidade_pretendida:
    st.error(
        f"❌ **Stock Insuficiente!** O armazém **{armazem_alvo}** apenas dispõe de"
        f" **{stock_total_disponivel} unidades** para o material **{material}**"
        f" (Solicitado: {quantidade_pretendida}). Movimento bloqueado."
    )
    return False

  # Ordenar por Validade para aplicar FEFO (se coluna de validade existir)
  if col_val:
    df_mat[col_val] = pd.to_datetime(df_mat[col_val], errors="coerce")
    df_mat = df_mat.sort_values(by=col_val, ascending=True, na_position="last")
  else:
    # Se não houver validade explícita, mantemos a ordem original do relatório
    pass

  # Executar baixa FEFO linha a linha até esgotar a quantidade pretendida
  qtd_a_abater = quantidade_pretendida
  movimentos_efetuados = []

  for idx, row in df_mat.iterrows():
    if qtd_a_abater <= 0:
      break

    stock_atual_linha = row[col_qtd]
    lote_val = row[col_lote] if col_lote else "N/D"
    loc_val = row[col_loc] if col_loc else "N/D"

    if stock_atual_linha <= 0:
      continue

    if stock_atual_linha >= qtd_a_abater:
      # Esta linha consegue absorver toda a quantidade restante
      quantidade_retirada = qtd_a_abater
      st.session_state.stock_df.loc[idx, col_qtd] = stock_atual_linha - qtd_a_abater
      qtd_a_abater = 0
    else:
      # Consome o stock todo desta linha e passa para a seguinte
      quantidade_retirada = stock_atual_linha
      st.session_state.stock_df.loc[idx, col_qtd] = 0
      qtd_a_abater -= stock_atual_linha

    movimentos_efetuados.append({
        "Lote": lote_val,
        "Localização": loc_val,
        "Quantidade Retirada": quantidade_retirada,
    })

  return movimentos_efetuados


# ==========================================
# ABA 1: SAÍDA AMOSTRA (PT97)
# ==========================================
with aba_saida_amostra:
  st.subheader("🧪 Registo de Saída para Amostra - Armazém PT97")
  st.markdown("Registo automático por ordem **FEFO** (Primeiro a expirar, primeiro a sair).")

  with st.form("form_pt97"):
    col_f1, col_f2 = st.columns(2)
    with col_f1:
      mat_pt97 = st.text_input("Código do Material (PT97)")
    with col_f2:
      qtd_pt97 = st.number_input(
          "Quantidade Pretendida", min_value=0.01, step=1.0
      )

    btn_pt97 = st.form_submit_button(
        "Registar Saída PT97 (Amostra)", type="primary"
    )

    if btn_pt97:
      if not mat_pt97:
        st.warning("Insira o código do material.")
      else:
        resultado_fefo = executar_saida_fefo(mat_pt97, qtd_pt97, "PT97")
        if resultado_fefo:
          st.success(
              f"✅ Saída de Amostra (PT97) registada com sucesso para o"
              f" material {mat_pt97}!"
          )
          # Mostrar tabela de alocação FEFO efetuada
          df_resumo = pd.DataFrame(resultado_fefo)
          st.dataframe(df_resumo, use_container_width=True)

          # Registar no histórico global de movimentos
          for item in resultado_fefo:
            novo_reg = {
                "Data/Hora": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Utilizador": user_info["nome"],
                "ID_User": user_info["id"],
                "Tipo_Movimento": "Amostra (PT97)",
                "Armazem": "PT97",
                "Material": mat_pt97,
                "Lote": item["Lote"],
                "Quantidade": item["Quantidade Retirada"],
                "Localizacao": item["Localização"],
            }
            st.session_state.movimentos_df = pd.concat(
                [
                    st.session_state.movimentos_df,
                    pd.DataFrame([novo_reg]),
                ],
                ignore_index=True,
            )

# ==========================================
# ABA 2: SAÍDA GERAL / FATURAÇÃO (PT01)
# ==========================================
with aba_saida_geral:
  st.subheader("📦 Registo de Saída Faturação Geral - Armazém PT01")
  st.markdown("Registo automático por ordem **FEFO** (Primeiro a expirar, primeiro a sair).")

  with st.form("form_pt01"):
    col_g1, col_g2 = st.columns(2)
    with col_g1:
      mat_pt01 = st.text_input("Código do Material (PT01)")
    with col_g2:
      qtd_pt01 = st.number_input(
          "Quantidade Pretendida", min_value=0.01, step=1.0, key="qtd_geral"
      )

    btn_pt01 = st.form_submit_button(
        "Registar Saída PT01 (Geral)", type="primary"
    )

    if btn_pt01:
      if not mat_pt01:
        st.warning("Insira o código do material.")
      else:
        resultado_fefo = executar_saida_fefo(mat_pt01, qtd_pt01, "PT01")
        if resultado_fefo:
          st.success(
              f"✅ Saída Geral (PT01) registada com sucesso para o material"
              f" {mat_pt01}!"
          )
          df_resumo = pd.DataFrame(resultado_fefo)
          st.dataframe(df_resumo, use_container_width=True)

          # Registar no histórico global de movimentos
          for item in resultado_fefo:
            novo_reg = {
                "Data/Hora": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Utilizador": user_info["nome"],
                "ID_User": user_info["id"],
                "Tipo_Movimento": "Geral (PT01)",
                "Armazem": "PT01",
                "Material": mat_pt01,
                "Lote": item["Lote"],
                "Quantidade": item["Quantidade Retirada"],
                "Localizacao": item["Localização"],
            }
            st.session_state.movimentos_df = pd.concat(
                [
                    st.session_state.movimentos_df,
                    pd.DataFrame([novo_reg]),
                ],
                ignore_index=True,
            )

# ==========================================
# ABA 3: CONSULTA STOCK
# ==========================================
with aba_consulta:
  st.subheader("🔍 Consulta de Stock (PT01 e PT97)")
  st.markdown("Consulte rapidamente o stock atualizado em tempo real para cada armazém.")

  mat_consulta = st.text_input("Introduza o Código do Material para Consulta")

  if st.button("Consulta Stock", type="primary"):
    if not mat_consulta:
      st.warning("Insira um código de material para consultar.")
    else:
      df = st.session_state.stock_df
      # Encontrar colunas relevantes dinamicamente
      col_mat = next(
          (c for c in df.columns if "material" in c.lower() or "artigo" in c.lower()),
          None,
      )
      col_arm = next(
          (c for c in df.columns if "armazém" in c.lower() or "armazem" in c.lower() or "sloc" in c.lower()),
          None,
      )
      col_qtd = next(
          (c for c in df.columns if "stock" in c.lower() or "quantidade" in c.lower()),
          None,
      )

      if col_mat and col_arm and col_qtd:
        df_filtrado = df[
            df[col_mat].astype(str).str.contains(str(mat_consulta), case=False, na=False)
        ].copy()

        if df_filtrado.empty:
          st.info(f"O material '{mat_consulta}' não foi encontrado no espelho de stock.")
        else:
          df_filtrado[col_qtd] = pd.to_numeric(
              df_filtrado[col_qtd].astype(str).str.replace(",", "."), errors="coerce"
          ).fillna(0)

          # Agrupar por armazém para mostrar o total em PT01 e PT97
          resumo_arm = (
              df_filtrado.groupby(col_arm)[col_qtd].sum().reset_index()
          )

          st.markdown("#### Resumo por Armazém")
          c1, c2 = st.columns(2)

          stock_pt01 = 0
          stock_pt97 = 0

          for _, row in resumo_arm.iterrows():
            nome_arm = str(row[col_arm])
            valor_stock = row[col_qtd]
            if "pt01" in nome_arm.lower():
              stock_pt01 = valor_stock
            elif "pt97" in nome_arm.lower():
              stock_pt97 = valor_stock

          with c1:
            st.metric("Stock em PT01 (Geral)", f"{stock_pt01} unidades")
          with c2:
            st.metric("Stock em PT97 (Amostras)", f"{stock_pt97} unidades")

          st.markdown("#### Detalhe Completo por Lote e Localização")
          st.dataframe(df_filtrado, use_container_width=True)
      else:
        st.error("Erro interno: Estrutura de colunas do SAP não identificada corretamente.")

# ==========================================
# ABA 4: HISTÓRICO DE MOVIMENTOS
# ==========================================
with aba_movimentos:
  st.subheader("📋 Histórico de Movimentos Efetuados Offline")
  st.markdown("Registo de todas as saídas efetuadas sem sistema para posterior regularização no SAP.")

  df_movs = st.session_state.movimentos_df

  if df_movs.empty:
    st.info("Ainda não foi efetuado nenhum movimento de saída nesta sessão.")
  else:
    st.dataframe(df_movs, use_container_width=True)

    # Botão para exportar o histórico de movimentos em CSV
    csv_movimentos = df_movs.to_csv(index=False).encode("latin1")
    st.download_button(
        label="📥 Descarregar Histórico de Movimentos (CSV para Regularização)",
        data=csv_movimentos,
        file_name=f"movimentos_offline_bbraun_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
        mime="text/csv",
    )

    if st.button("🗑️ Limpar Histórico de Movimentos"):
      st.session_state.movimentos_df = pd.DataFrame(
          columns=[
              "Data/Hora",
              "Utilizador",
              "ID_User",
              "Tipo_Movimento",
              "Armazem",
              "Material",
              "Lote",
              "Quantidade",
              "Localizacao",
          ]
      )
      st.rerun()

# Espaçamento inferior para o rodapé fixo
st.markdown("<br><br>", unsafe_allow_html=True)
