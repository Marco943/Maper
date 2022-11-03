import streamlit as st
import pandas as pd
import numpy as np
import PyPDF2
import re
import io
import cv2 as cv
import fitz

# o @st.experimental_memo guarda em cache o resultado da função caso seja usado de novo futuramente

@st.experimental_memo
def extrair_notas_radar_lideranca(maper_radar):
    img = cv.imdecode(maper_radar, cv.IMREAD_COLOR)
    # Transforma a imagem numa escala cinza
    gray = cv.cvtColor(img, cv.COLOR_BGR2GRAY)

    # converter paracinza
    gray_circle = gray.copy()
    # Aplicar blur na imagem para não detectar falsos positivos
    gray_circle = cv.medianBlur(gray_circle, 7)
    # Threshold
    ret, thres_circle = cv.threshold(gray_circle, 110, 255, cv.THRESH_BINARY_INV)
    img_copy = img.copy()

    # Encontrar círculos (pontos/marcadores). Parâmetros foram testados até dar certo
    circles = cv.HoughCircles(thres_circle, cv.HOUGH_GRADIENT, dp=1, minDist=15, param1=1000, param2=1, minRadius=4, maxRadius=4)

    circles = np.uint16(np.around(circles))
    # Centro e raio do gráfico (encontrado previamente). Como as dimensões são as mesmas em todos mapers, pode ser fixo
    x0, y0, raio = np.array([349, 441, 226])
    centro = np.array([x0,y0])

    # Eliminar circulos encontrados que estão fora da região do gráfico e também eliminar circulo encontrado no centro do gráfico
    valid_circles = []
    for i in circles[0,:]:
        # Centro do ponto
        center = (i[0], i[1])
        # Distância entre o ponto e o centro do gráfico
        dist = np.linalg.norm(center - centro)
        if dist > 1.2*raio or dist < 0.05*raio:
            # Se o ponto estiver muito longe do gráfico ou no centro dele, ignora o ponto
            continue
        else:
            valid_circles.append(i)
            # cv.circle(img_copy, center, i[2], (0,100,100), 3)
    valid_circles = np.array(valid_circles)

    # print(valid_circles.shape)
    # fig, ax = plt.subplots(1, 1, figsize=(10,10))
    # ax.imshow(img_copy)
    # plt.show()

    # Fazer um dicionario com o angulo correspodnente à competencia (testado e validado previamente)
    Competencias = ['Necessidade de realização', 'Tônus vital', 'Imagem pessoal', 'Relacionamento em grupos', 'Relações de confiança', 'Controle das emoções', 'Gestão de conflitos', 'Relacionamento com superiores', 'Gestão de mudanças', 'Capacidade de Priorização e Imprevistos', 'Potencial criativo', 'Volume de trabalho', 'Administração do tempo', 'Capacidade de delegação', 'Tomada de decisão', 'Estilo de comunicação', 'Liderança Motivacional', 'Liderança COACH', 'Capacidade de organização', 'Capacidade de planejamento']
    # 360° para 20 competências = 18° por competência
    passo = int(360/20)
    angulo_competencia = {a: competencia for a, competencia in zip(range(0, 360, passo), reversed(Competencias))}

    # Para cada ponto, calcular o angulo que ele tem com o centro do gráfico, 
    # Corrigir o ângulo para um dos pré-definidos no dicionário acima, obtendo também a competência associada
    # isso é feito verificando em qual intervalo o angulo se encaixa
    dados = {}
    for point in valid_circles[:,0:2]:
        dist = point-centro
        angulo = np.degrees(np.arctan2(*dist))+180
        # Ex: se o angulo do ponto é de 91°, isso quer dizer que ele está no intervalo de 90° +/- o passo/2 (entre 81° e 99°)
        # Compreensão de lista para construir uma lista de ângulos corrigidos onde o ângulo calculado se encontra.
        # Como sempre só vai ter um valor aqui, pegamos o primeiro índice
        angulo_corrigido = [a for a in range(0, 375, passo) if angulo >= a - passo/2 and angulo <= a + passo/2][0]
        # Se o angulo corrigido for 360, é a mesma coisa que 0
        if angulo_corrigido == 360 or angulo_corrigido < 0:
            angulo_corrigido = 0
        # Puxa a competência associada pelo dicionário
        competencia = angulo_competencia[angulo_corrigido]

        # calcula a nota com base na distância entre o ponto e o centro, e o tamanho do raio
        nota = np.round(np.linalg.norm(dist)/raio*10,0)
        
        # salva num dicionario a competencia e a nota
        dados[competencia] = [int(nota)]

    df_dados = pd.DataFrame.from_dict(dados)

    return df_dados

@st.experimental_memo(show_spinner=False)
def extrair_dados_lideranca(relatorio):

    # ================ EXTRAÇÃO DADOS ESCRITOS =================== #
    arquivo = PyPDF2.PdfFileReader(relatorio)
    # Pegar texto 
    txt = arquivo.getPage(0).extractText() + arquivo.getPage(1).extractText()   # Páginas 1 e 2
    txt = txt.replace('€','').replace(' \n','\n').replace('\n\n','\n')          # tratamento básico para facilitar extração

    # Achar o nome e cargo e extrair
    nome = re.findall(r'(?:NOME|NOMBRE):\n(.*)\n', txt)[0]                # Pega os trechos que estão entre duas quebras de linhas e que pode ter NOME: ou NOMBRE: antes
    cargo = re.findall(r'(?:CARGO|PROFESIONAL):\n(.*)\n', txt)[0].strip() # Pega os trechos que estão entre duas quebras de linhas e que pode ter CARGO: ou PROFESIONAL: antes

    # Achar competências e notas e extrair
    # competencias = re.findall(r'\n\d\d?\s-\s(.*)\n', txt)               # Pega os trechos que contêm antes deles 'espaço hífen espaço' e que tem um ou dois dígitos antes (são os números das competências)
    notas = re.findall(r'\n(\d\d?)\n(?:\d\d?\s-|página|Página)', txt)   # Pega os trechos onde tem um número de um ou dois dígitos (\d\d?) que está depois de um parágrafo (\n) e antes de: Um texto que começa com um ou dois números, tem um espaço e um hífen; um texto 'página'; um texto 'Página'

    # Achar Estilo de liderança
    txt = arquivo.getPage(6).extractText()                              # Página 7
    txt = txt.replace('€','').replace(' \n','\n').replace('\n\n','\n')  # tratemento
    estilo = re.findall(r'SEU ESTILO DE LIDERANçA\n(.*)\n', txt)[0]     # Pega os trechos que estão entre duas quebras de linha e que tem SEU ESTILO DE LIDERANçA antes

    # Inicializar dataset com informações básicas
    resposta = {'Nome': [nome], 'Cargo': [cargo], 'Notas': 'Coaching', 'Estilo de Liderança': estilo}
    competencias = ['Capacidade de planejamento', 'Capacidade de organização','Liderança COACH','Liderança Motivacional','Estilo de comunicação','Tomada de decisão','Capacidade de delegação','Administração do tempo','Volume de trabalho','Potencial criativo','Capacidade de Priorização e Imprevistos','Gestão de mudanças','Relacionamento com superiores','Gestão de conflitos','Controle das emoções','Relações de confiança','Relacionamento em grupos','Imagem pessoal', 'Tônus vital','Necessidade de realização']
    # Anexar competências e notas ao dataset
    for competencia, nota in zip(competencias, notas):
        resposta[competencia] = nota

    # Transformar dataset num dataframe
    dados_coaching = pd.DataFrame.from_dict(resposta)
    
    # =============================== EXTRAÇÃO IMAGEM =================== #
    arquivo = fitz.open(stream=relatorio.getvalue())

    # Acessar página 4 e imagem 4
    imagens = arquivo.get_page_images(3)
    print(imagens)
    xref = imagens[3][0]

    # Extrair imagem
    imagem = arquivo.extract_image(xref)
    imagem_bytes = io.BytesIO((imagem['image']))
    imagem_array = np.frombuffer(imagem['image'], np.uint8)

    dados_radar = extrair_notas_radar_lideranca(imagem_array)

    dados_radar['Nome'] = nome
    dados_radar['Cargo'] = cargo
    dados_radar['Notas'] = 'Radar'
    dados_radar['Estilo de Liderança'] = estilo

    return pd.concat([dados_coaching, dados_radar], ignore_index=True)


def gerar_excel(df):
    dados_dim = [
        {'Competência': 'Capacidade de planejamento', 'Estilo Profissional': 'Analista', 'Índice': 1},
        {'Competência': 'Capacidade de planejamento', 'Estilo Profissional': 'Negociador', 'Índice': 1},
        {'Competência': 'Capacidade de organização', 'Estilo Profissional': 'Analista', 'Índice': 2},
        {'Competência': 'Liderança COACH', 'Estilo Profissional': 'Mobilizador', 'Índice': 3},
        {'Competência': 'Liderança Motivacional', 'Estilo Profissional': 'Mobilizador', 'Índice': 4},
        {'Competência': 'Estilo de comunicação', 'Estilo Profissional': 'Mobilizador', 'Índice': 5},
        {'Competência': 'Estilo de comunicação', 'Estilo Profissional': 'Negociador', 'Índice': 5},
        {'Competência': 'Tomada de decisão', 'Estilo Profissional': 'Mobilizador', 'Índice': 6},
        {'Competência': 'Capacidade de delegação', 'Estilo Profissional': 'Mobilizador', 'Índice': 7},
        {'Competência': 'Administração do tempo', 'Estilo Profissional': 'Produtor', 'Índice': 8},
        {'Competência': 'Volume de trabalho', 'Estilo Profissional': 'Produtor', 'Índice': 9},
        {'Competência': 'Potencial criativo', 'Estilo Profissional': 'Inovador', 'Índice': 10},
        {'Competência': 'Capacidade de Priorização e Imprevistos', 'Estilo Profissional': 'Inovador', 'Índice': 11},
        {'Competência': 'Capacidade de Priorização e Imprevistos', 'Estilo Profissional': 'Produtor', 'Índice': 11},
        {'Competência': 'Gestão de mudanças', 'Estilo Profissional': 'Inovador', 'Índice': 12},
        {'Competência': 'Relacionamento com superiores', 'Estilo Profissional': 'Analista', 'Índice': 13},
        {'Competência': 'Gestão de conflitos', 'Estilo Profissional': 'Negociador', 'Índice': 14},
        {'Competência': 'Controle das emoções', 'Estilo Profissional': 'Negociador', 'Índice': 15},
        {'Competência': 'Relações de confiança', 'Estilo Profissional': 'Negociador', 'Índice': 16},
        {'Competência': 'Relacionamento em grupos', 'Estilo Profissional': 'Negociador', 'Índice': 17},
        {'Competência': 'Imagem pessoal', 'Estilo Profissional': '', 'Índice': 18},
        {'Competência': 'Tônus vital', 'Estilo Profissional': 'Produtor', 'Índice': 19},
        {'Competência': 'Necessidade de realização', 'Estilo Profissional': 'Produtor', 'Índice': 20},
    ]

    df_dim = pd.DataFrame.from_records(dados_dim)
    arquivo_excel = io.BytesIO()
    with pd.ExcelWriter(arquivo_excel) as f:
        df.to_excel(excel_writer=f, encoding = 'utf-8', sheet_name='Dados', header = True, index_label = '#', index=False)
        df_dim.to_excel(excel_writer=f, encoding='utf-8', sheet_name='Competências', header=True, index=False)
    arquivo_excel.seek(0)
    return arquivo_excel
