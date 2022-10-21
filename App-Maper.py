import streamlit as st
import pandas as pd
from funcoes import *

st.set_page_config(
    page_title='Maper - Extração de dados',
    page_icon='icone.png',
    menu_items={
        'About': 'Aplicação Web desenvolvida pela Sucesso em Vendas para extração de dados de relatórios Maper',
        'Get help': None,
        'Report a Bug': None
    }
)

cabecalho = st.container()
corpo = st.container()

with cabecalho:
    st.image('logo_sv.svg')
    st.header('WebApp - Extração de dados do Maper')

with corpo:
    arquivos = st.file_uploader(
        label='Insira aqui relatórios Maper de Liderança (PDF)',
        type='pdf',
        accept_multiple_files=True
    )
    
    if len(arquivos) != 0:
        progresso = st.progress(0)
        dados = []
        for n, maper in enumerate(arquivos):
            dados.append(extrair_dados_lideranca(maper))
            progresso.progress((n+1)/len(arquivos))
        df = pd.concat(dados)
        df = df.reset_index(drop = True)
        df = df.apply(pd.to_numeric, axis=1, errors='ignore')
        df = df.fillna(0)
        st.download_button(
            label = 'Baixar dados (Excel)',
            data = gerar_excel(df),
            file_name = 'Dados Maper.xlsx',
            mime = 'application/vnd.ms-excel'
        )
    
    with st.expander('Pré-Visualização dos dados extraídos', expanded = False):
        if len(arquivos) == 0:
            st.write('Insira relatórios para visualizar os dados extraídos.')
        else:
            st.dataframe(df.astype(str).set_index('Nome'))

        