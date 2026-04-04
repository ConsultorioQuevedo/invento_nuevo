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

# 1. CONFIGURACIÓN DE ALTO NIVEL
st.set_page_config(page_title="SISTEMA INVENTO - OMNI", layout="wide")

# 2. CONEXIONES (EXCEL + SQLITE)
URL_EXCEL = "https://docs.google.com/spreadsheets/d/1_pVn28bUNlBdBo6qd8auILG4e2p4Yj90Q8tznS9Pysk/edit?usp=sharing"
conn_gsheets = st.connection("gsheets", type=GSheetsConnection)

def iniciar_db_local():
    conn = sqlite3.connect("sistema_quevedo_pro.db", check_same_thread=False)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS glucosa (id INTEGER PRIMARY KEY, fecha TEXT, hora TEXT, momento TEXT, valor INTEGER, notas TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS medicamentos (id INTEGER PRIMARY KEY, nombre TEXT, dosis TEXT, horario TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS citas (id INTEGER PRIMARY KEY, doctor TEXT, fecha TEXT, motivo TEXT)')
    conn.commit()
    return conn
conn_sql = iniciar_db_local()

# 3. FUNCIONES DE APOYO
def obtener_tiempo_rd():
    zona = pytz.timezone('America/Santo_Domingo')
    ahora = datetime.now(zona)
    return ahora.strftime("%d/%m/%Y"), ahora.strftime("%I:%M %p")

# --- INTERFAZ ---
st.title("🌌 SISTEMA INVENTO: INTELIGENCIA INTEGRAL")
st.write(f"**Usuario:** Luis Rafael Quevedo | **Estado:** Máxima Eficiencia")

# PESTAÑAS TOTALES (SIN QUITAR NADA)
t1, t2, t3, t4, t5 = st.tabs(["💰 FINANZAS", "🩸 GLUCOSA", "💊 MEDICAMENTOS", "📅 CITAS", "🧠 NÚCLEO IA"])

# --- SECCIÓN 1: FINANZAS (CONEXIÓN GOOGLE) ---
with t1:
    st.subheader("Control Financiero Pro")
    with st.form("form_f", clear_on_submit=True):
        col1, col2, col3, col4 = st.columns([1,2,2,1])
        with col1: tipo = st.selectbox("TIPO", ["GASTO", "INGRESO"])
        with col2: cat = st.text_input("CATEGORÍA").upper()
        with col3: det = st.text_input("DETALLE").upper()
        with col4: mon = st.number_input("MONTO RD$", min_value=0.0)
        if st.form_submit_button("REGISTRAR EN NUBE"):
            ahora = datetime.now()
            m_final = -abs(mon) if tipo == "GASTO" else abs(mon)
            nueva = pd.DataFrame([{"Fecha": ahora.strftime("%d/%m/%Y %H:%M"), "Mes": ahora.strftime("%m-%Y"), "Tipo": tipo, "Categoría": cat, "Detalle": det, "Monto": float(m_final)}])
            df_a = conn_gsheets.read(spreadsheet=URL_EXCEL, worksheet="Hoja 1", ttl=0)
            conn_gsheets.update(spreadsheet=URL_EXCEL, data=pd.concat([df_a, nueva]), worksheet="Hoja 1")
            st.success("✅ Sincronizado")
    
    # Tabla de Finanzas
    df_f = conn_gsheets.read(spreadsheet=URL_EXCEL, worksheet="Hoja 1", ttl=0)
    if not df_f.empty:
        st.dataframe(df_f.sort_index(ascending=False), use_container_width=True)
        st.metric("BALANCE DISPONIBLE", f"RD$ {df_f['Monto'].sum():,.2f}")

# --- SECCIÓN 2: GLUCOSA (CON ALERTAS Y ESCÁNER) ---
with t2:
    st.subheader("Bio-Monitor de Glucosa")
    with st.form("f_g", clear_on_submit=True):
        v = st.number_input("Valor mg/dL:", min_value=0)
        m = st.selectbox("Momento:", ["Ayunas", "Post-Desayuno", "Antes Cena", "Post-Cena"])
        if st.form_submit_button("GUARDAR GLUCOSA"):
            f_rd, h_rd = obtener_tiempo_rd()
            conn_sql.execute("INSERT INTO glucosa (fecha, hora, momento, valor) VALUES (?,?,?,?)", (f_rd, h_rd, m, v))
            conn_sql.commit()
    
    st.write("---")
    st.subheader("📷 Escáner OCR de Reportes")
    img = st.file_uploader("Subir foto de examen médico", type=['png', 'jpg', 'jpeg'])
    if img:
        st.image(img, width=300)
        st.info("Imagen detectada. Motor OCR listo para procesar.")

# --- SECCIÓN 3: MEDICAMENTOS ---
with t3:
    st.subheader("💊 Gestión de Tratamientos")
    with st.form("f_m", clear_on_submit=True):
        n = st.text_input("Medicamento:"); d = st.text_input("Dosis:"); h = st.text_input("Horario:")
        if st.form_submit_button("AÑADIR"):
            conn_sql.execute("INSERT INTO medicamentos (nombre, dosis, horario) VALUES (?,?,?)", (n.upper(), d, h))
            conn_sql.commit()
    st.table(pd.read_sql_query("SELECT nombre, dosis, horario FROM medicamentos", conn_sql))

# --- SECCIÓN 4: CITAS MÉDICAS ---
with t4:
    st.subheader("📅 Agenda de Consultas")
    with st.form("f_c", clear_on_submit=True):
        doc = st.text_input("Doctor:"); fec = st.date_input("Fecha:"); mot = st.text_input("Motivo:")
        if st.form_submit_button("AGENDAR"):
            conn_sql.execute("INSERT INTO citas (doctor, fecha, motivo) VALUES (?,?,?)", (doc.upper(), str(fec), mot))
            conn_sql.commit()
    st.dataframe(pd.read_sql_query("SELECT * FROM citas", conn_sql), use_container_width=True)

# --- SECCIÓN 5: NÚCLEO IA (SÚPER INTELIGENCIA) ---
with t5:
    st.header("🧠 Análisis Predictivo IA")
    col_ia1, col_ia2 = st.columns(2)
    
    with col_ia1:
        st.write("### 📈 Futuro Financiero")
        if len(df_f) > 2:
            model_f = LinearRegression().fit(np.arange(len(df_f)).reshape(-1, 1), df_f["Monto"].values)
            pred_f = model_f.predict([[len(df_f) + 1]])
            st.metric("Próximo Movimiento Estimado", f"RD$ {pred_f[0]:,.2f}")
    
    with col_ia2:
        st.write("### ❤️ Salud Inteligente")
        df_g_ia = pd.read_sql_query("SELECT valor FROM glucosa", conn_sql)
        if not df_g_ia.empty:
            ultimo = df_g_ia["valor"].iloc[-1]
            if ultimo > 180: st.error(f"ALERTA: Glucosa alta ({ultimo}).")
            elif ultimo < 70: st.warning(f"AVISO: Glucosa baja ({ultimo}).")
            else: st.success(f"ÓPTIMO: Glucosa en {ultimo}.")

# --- PIE DE PÁGINA (CRÉDITOS) ---
st.markdown("<br><hr>", unsafe_allow_html=True)
st.markdown(
    """
    <div style='text-align: center; color: gray;'>
        <p><strong>INVENTO: SISTEMA DE FINANZAS Y SALUD INTELIGENTE</strong></p>
        <p>Diseñadores: Luis Rafael Quevedo</p>
    </div>
    """, 
    unsafe_allow_html=True
)
