import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import sqlite3
import plotly.express as px
import pytz
from datetime import datetime
from sklearn.linear_model import LinearRegression
import numpy as np
from PIL import Image

# 1. CONFIGURACIÓN INICIAL (CORREGIDA)
st.set_page_config(page_title="App Finanzas & Salud Quevedo", layout="wide")

# 2. CONEXIÓN A BASES DE DATOS (FUSIÓN)
# Conexión Excel (Finanzas)
URL_EXCEL = "https://docs.google.com/spreadsheets/d/1_pVn28bUNlBdBo6qd8auILG4e2p4Yj90Q8tznS9Pysk/edit?usp=sharing"
conn_gsheets = st.connection("gsheets", type=GSheetsConnection)

# Conexión SQLite (Salud e IA)
def iniciar_db_local():
    conn = sqlite3.connect("sistema_quevedo.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS glucosa (id INTEGER PRIMARY KEY, fecha TEXT, hora TEXT, momento TEXT, valor INTEGER, notas TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS medicamentos (id INTEGER PRIMARY KEY, nombre TEXT, dosis TEXT, horario TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS citas (id INTEGER PRIMARY KEY, doctor TEXT, fecha TEXT, motivo TEXT)')
    conn.commit()
    return conn

conn_sql = iniciar_db_local()

# 3. FUNCIONES DE APOYO
def obtener_tiempo_rd():
    zona = pytz.timezone('America/Santo_Domingo')
    ahora = datetime.now(zona)
    return ahora.strftime("%d/%m/%Y"), ahora.strftime("%I:%M %p")

def color_glucosa(valor):
    if valor < 70: return "background-color: #8b0000; color: white"
    if valor <= 130: return "background-color: #28a745; color: white"
    if valor < 180: return "background-color: #ffa500; color: black"
    return "background-color: #ff4b4b; color: white"

# --- INTERFAZ PRINCIPAL ---
st.title("📊💉 Dashboard Finanzas & Salud Inteligente")
st.write(f"Bienvenido, Sr. Quevedo | {obtener_tiempo_rd()[0]}")

tab1, tab2, tab3 = st.tabs(["💰 Finanzas (Excel)", "🩺 Salud (Local)", "🧠 Motor de IA"])

# --- PESTAÑA 1: FINANZAS (Google Sheets) ---
with tab1:
    st.subheader("Control Financiero en Tiempo Real")
    with st.form(key="form_finanzas", clear_on_submit=True):
        c1, c2, c3, c4 = st.columns([1, 2, 2, 1])
        with c1: tipo_f = st.selectbox("TIPO", ["GASTO", "INGRESO"])
        with c2: cat_f = st.text_input("CATEGORÍA")
        with c3: det_f = st.text_input("DETALLE")
        with c4: mon_f = st.number_input("MONTO RD$", min_value=0.0)
        btn_f = st.form_submit_button("REGISTRAR EN EXCEL")

    if btn_f and mon_f > 0:
        ahora = datetime.now()
        monto_final = -abs(mon_f) if tipo_f == "GASTO" else abs(mon_f)
        nueva_fila = pd.DataFrame([{"Fecha": ahora.strftime("%d/%m/%Y %H:%M"), "Mes": ahora.strftime("%m-%Y"), 
                                    "Tipo": tipo_f, "Categoría": cat_f.upper(), "Detalle": det_f.upper(), "Monto": float(monto_final)}])
        try:
            df_actual = conn_gsheets.read(spreadsheet=URL_EXCEL, worksheet="Hoja 1", ttl=0)
            df_final = pd.concat([df_actual, nueva_fila], ignore_index=True)
            conn_gsheets.update(spreadsheet=URL_EXCEL, data=df_final, worksheet="Hoja 1")
            st.success("✅ Sincronizado con Google Sheets")
        except Exception as e: st.error(f"Error Excel: {e}")

    # Visualización Finanzas
    try:
        df_f = conn_gsheets.read(spreadsheet=URL_EXCEL, worksheet="Hoja 1", ttl=0)
        if not df_f.empty:
            st.dataframe(df_f.sort_index(ascending=False), use_container_width=True)
            st.metric("BALANCE TOTAL", f"RD$ {df_f['Monto'].sum():,.2f}")
    except: st.info("Esperando datos de Excel...")

# --- PESTAÑA 2: SALUD (SQLite) ---
with tab2:
    col_a, col_b = st.columns([2, 1])
    with col_a:
        st.subheader("Registro de Glucosa")
        with st.form("f_salud", clear_on_submit=True):
            v_g = st.number_input("Valor mg/dL:", min_value=0)
            m_g = st.selectbox("Momento:", ["Ayunas", "Post-Desayuno", "Antes Cena", "Post-Cena"])
            if st.form_submit_button("GUARDAR SALUD"):
                f, h = obtener_tiempo_rd()
                conn_sql.execute("INSERT INTO glucosa (fecha, hora, momento, valor) VALUES (?,?,?,?)", (f, h, m_g, v_g))
                conn_sql.commit()
                st.success("✅ Guardado en base local")

    df_g = pd.read_sql_query("SELECT fecha, hora, momento, valor FROM glucosa ORDER BY id DESC", conn_sql)
    if not df_g.empty:
        st.dataframe(df_g.style.applymap(color_glucosa, subset=['valor']), use_container_width=True)
        st.plotly_chart(px.line(df_g, x="fecha", y="valor", title="Tendencia de Salud"), use_container_width=True)

# --- PESTAÑA 3: MOTOR DE IA ---
with tab3:
    st.header("Análisis Predictivo")
    # IA Finanzas
    df_f_ia = pd.read_sql_query("SELECT * FROM glucosa", conn_sql) # Ejemplo con datos locales
    if len(df_f_ia) > 2:
        st.write("### 🔮 Predicción de Próximo Valor (IA)")
        X = np.arange(len(df_f_ia)).reshape(-1, 1)
        y = df_f_ia["valor"].values
        model = LinearRegression().fit(X, y)
        pred = model.predict([[len(df_f_ia) + 1]])
        st.metric("Valor Estimado", f"{pred[0]:.2f} mg/dL")
    else:
        st.warning("Se necesitan más datos para activar el Motor de IA.")

# --- PIE DE PÁGINA (CRÉDITOS) ---
st.markdown("<br><br>", unsafe_allow_html=True)
st.divider()
st.markdown(
    """
    <div style='text-align: center; color: gray;'>
        <p><strong>PROYECTO INVENTO: App Finanzas & Salud</strong></p>
        <p>Diseñadores: Luis Rafael Quevedo</p>
    </div>
    """, 
    unsafe_allow_html=True
)
