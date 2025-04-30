import streamlit as st
import openai
import pandas as pd
import json
import ast
import io
import math
from io import BytesIO
from datetime import datetime


# Leer la API Key desde Streamlit Secrets
API_KEY = st.secrets["OPENROUTER_API_KEY"]
API_BASE = "https://openrouter.ai/api/v1"
MODEL_NAME = "deepseek/deepseek-r1:free"

# Instrucciones del sistema
INSTRUCCIONES_SISTEMA = """
Eres un asistente técnico experto en integración de sistemas mecatrónicos para la generación de matrices QFD. Recibirás cuatro entradas estructuradas: (1) contexto del socio formador, (2) pregunta esencial a resolver, (3) reto específico a resolver, y (4) necesidades del cliente. Con base en estos elementos, debes realizar lo siguiente:

1. Proponer requerimientos técnicos base principales (añade '(b)'), que representen características genéricas para un producto de este tipo, es decir, funcionalidades técnicas que cualquier producto similar debería tener. Además, propones requerimientos técnicos de valor agregado (añade '(v.a.)') que respondan al reto planteado y proporcionen ventajas adicionales.

2. Crear una matriz de relaciones QFD utilizando las necesidades del cliente como filas y los requerimientos técnicos (base y de valor agregado) como columnas. Evalúa de manera rigurosa cada intersección entre una necesidad y un requerimiento técnico, respondiendo a la pregunta: **"¿Qué tanto este requerimiento técnico contribuye a satisfacer esta necesidad del cliente?"**. Asigna valores únicamente cuando exista una relación significativa:
   - 9: Relación fuerte
   - 3: Relación moderada
   - 1: Relación débil
   - 0: Sin relación significativa

3. Asignar un valor de importancia del 1 al 5 a cada necesidad del cliente con base en el contexto del socio formador, la pregunta esencial y el reto específico. Asegúrate de usar toda la escala (del 1 al 5) para reflejar diferentes niveles de prioridad entre las necesidades.

4. Generar una lista de **targets** y **unidades** asociadas a cada requerimiento técnico (en el mismo orden en que los presentas). Los targets pueden ser valores puntuales o rangos, según la naturaleza del requerimiento. Si el requerimiento técnico puede implicar múltiples variantes (por ejemplo, sensores con diferentes resoluciones), expresa el target como un rango representativo o menciona varias opciones relevantes.

5. Regresa el resultado como un JSON con las siguientes claves:
   - 'necesidades_cliente': lista de necesidades del cliente,
   - 'importancia_cliente': lista de valores del 1 al 5,
   - 'req_tecnicos_b': lista de requerimientos técnicos base,
   - 'req_tecnicos_va': lista de requerimientos técnicos valor agregado,
   - 'matriz_qfd': matriz de relaciones con valores 0, 1, 3, 9,
   - 'targets': lista de valores objetivo para cada requerimiento técnico,
   - 'unidades': lista de unidades para cada requerimiento técnico.
"""

# Funciones

def obtener_respuesta_chat(messages):
    client = openai.OpenAI(api_key=API_KEY, base_url=API_BASE)
    completion = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[{"role": "system", "content": INSTRUCCIONES_SISTEMA}] + messages
    )
    return completion.choices[0].message.content

def extraer_info_completa(contexto, pregunta_esencial, reto_especifico, necesidades):
    prompt = f"""
A continuación se presenta la información estructurada que debes analizar para generar la matriz QFD:

Contexto del socio formador:
{contexto}

Pregunta esencial:
{pregunta_esencial}

Reto específico:
{reto_especifico}

Lista de necesidades del cliente:
{necesidades}

Genera un resultado JSON con las claves: necesidades_cliente, importancia_cliente, req_tecnicos_b, req_tecnicos_va, matriz_qfd, targets, unidades.
"""
    return obtener_respuesta_chat([{"role": "user", "content": prompt}])

def revalorar_importancia(contexto, pregunta_esencial, reto_especifico, necesidades_cliente):
    prompt = f"""
Con base en el siguiente contexto, pregunta esencial y reto específico, revalora el nivel de importancia de las siguientes necesidades del cliente. Asigna un nuevo ranking del 1 al N (donde 1 es la más importante y N la menos importante). Devuelve únicamente una lista JSON válida de enteros, sin texto adicional.

Contexto del socio formador:
{contexto}

Pregunta esencial:
{pregunta_esencial}

Reto específico:
{reto_especifico}

Necesidades del cliente:
{json.dumps(necesidades_cliente)}
"""
    return obtener_respuesta_chat([{"role": "user", "content": prompt}])

# UI
st.set_page_config(page_title="Challenge Mentor AI - Matriz QFD", layout="wide")
st.title("🤖 AI Challenge Mentor - Matriz QFD")
st.markdown("Creadores: Dra. J. Isabel Méndez Garduño & M.Sc. Miguel de J. Ramírez C., CMfgT & M.Sc. David Barrientos ")
st.subheader("Guía interactiva que te sugiere requerimientos técnicos para tu QFD.")
st.markdown("Este asistente te ayudará paso a paso a obtener tu listado de requerimientos para la matriz QFD con base en el contexto del socio formador, pregunta esencial, reto específico a resolver y lista de necesidades del cliente. Recibirás una **MATRIZ QFD** que te servirá de base para analizarla y proponer tu propia matriz QFD.")

if "resultado_qfd" not in st.session_state:
    st.session_state.resultado_qfd = None

with st.form("formulario_qfd"):
    st.subheader("🧩 Información contextual")
    contexto = st.text_area("🏢 Contexto del socio formador")
    pregunta_esencial = st.text_area("❓ Pregunta esencial a resolver")
    reto_especifico = st.text_area("🚩 Reto específico a resolver")
    necesidades = st.text_area("📋 Lista de necesidades del cliente (conforme a la entrevista)")
    submitted = st.form_submit_button("Generar matriz QFD")

if submitted:
    if not contexto or not pregunta_esencial or not reto_especifico or not necesidades:
        st.warning("Por favor completa todos los campos.")
    else:
        with st.spinner("🔍 Analizando información con OpenAI..."):
            resultado_texto = extraer_info_completa(contexto, pregunta_esencial, reto_especifico, necesidades)
        try:
            inicio_json = resultado_texto.find('{')
            fin_json = resultado_texto.rfind('}') + 1
            resultado_limpio = resultado_texto[inicio_json:fin_json].replace("'", '"')
            resultado = json.loads(resultado_limpio)
        except:
            try:
                resultado = ast.literal_eval(resultado_texto)
            except Exception as e:
                st.error("❌ No se pudo interpretar la respuesta del modelo como JSON.")
                st.code(str(e))
                st.stop()

        st.session_state.resultado_qfd = resultado

if st.session_state.resultado_qfd:
    resultado = st.session_state.resultado_qfd
    columnas = resultado["req_tecnicos_b"] + resultado["req_tecnicos_va"]
    num_cols = len(columnas)
    data = resultado["matriz_qfd"]
    importancias = resultado["importancia_cliente"]
    data_padded = [fila + [""] * (num_cols - len(fila)) if len(fila) < num_cols else fila[:num_cols] for fila in data]

    df = pd.DataFrame(data_padded, columns=columnas)
    symbol_map = {"9": "●", 9: "●", "3": "○", 3: "○", "1": "▽", 1: "▽", "0": " ", 0: " ", "": " "}
    df_visual = df.applymap(lambda x: symbol_map.get(x, x))
    df_visual.insert(0, "Necesidades del cliente", resultado["necesidades_cliente"])
    df_visual.insert(0, "Importancia del cliente", importancias)

    df_numeric = pd.DataFrame(data_padded, columns=columnas).apply(pd.to_numeric, errors='coerce').fillna(0)
    df_numeric.insert(0, "Necesidades del cliente", resultado["necesidades_cliente"])
    df_numeric.insert(0, "Importancia del cliente", importancias)

    importancia_tecnica = df_numeric[columnas].multiply(importancias, axis=0).sum(axis=0)
    df_visual.loc["Target"] = ["", "Target"] + resultado["targets"] + [""] * (num_cols - len(resultado["targets"]))
    df_visual.loc["Unidades"] = ["", "Unidades"] + resultado["unidades"] + [""] * (num_cols - len(resultado["unidades"]))
    df_visual.loc["Calificación técnica"] = ["", "Calificación de importancia técnica"] + list(importancia_tecnica) + [""] * (num_cols - len(importancia_tecnica))

    # Cálculo justo del peso relativo en porcentaje
    pesos_relativos_raw = (importancia_tecnica / importancia_tecnica.sum()) * 100
    pesos_redondeados = pesos_relativos_raw.round(1)
    diferencia = 100 - pesos_redondeados.sum()
    if abs(diferencia) > 0:
        decimas = int(round(diferencia * 10))
        indices_ordenados = pesos_redondeados.sort_values(ascending=False).index.tolist()
        for i in range(abs(decimas)):
            idx = indices_ordenados[i % len(indices_ordenados)]
            if diferencia > 0:
                pesos_redondeados[idx] += 0.1
            else:
                pesos_redondeados[idx] -= 0.1
        pesos_redondeados = pesos_redondeados.round(1)


    df_visual.loc["Peso relativo (%)"] = ["", "Peso relativo (%)"] + list(pesos_redondeados) + [""] * (num_cols - len(pesos_redondeados))
    max_blocks = 50
    def barra_unicode(v):
       blocks = max(1, math.ceil(v / 100 * max_blocks)) if v > 0 else 0
       return '█' * blocks
    df_visual.loc["Gráfica relativa"] = ["", "Gráfica relativa"] + [barra_unicode(v) for v in pesos_redondeados] + [""] * (num_cols - len(pesos_redondeados))


   

    st.markdown("""
    ### 🔍 Leyenda de la matriz:
    - **●** : Relación fuerte  
    - **○** : Relación moderada  
    - **▽** : Relación débil  
    - *(espacio en blanco)* : Sin relación significativa
    """)

    st.markdown("### ✅ Matriz QFD Generada")
    st.dataframe(df_visual, use_container_width=True)

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df_visual.to_excel(writer, index=False, sheet_name='QFD')
    buffer.seek(0)
    nombre_archivo = f"{datetime.now().strftime('%Y%m%d-%H%M')}-matriz_qfd.xlsx"
    st.markdown("### 📥 Descargar Matriz")
    st.download_button("📂 Descargar como Excel", data=buffer, file_name=nombre_archivo, mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")






