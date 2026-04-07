import streamlit as st
import pandas as pd
import sqlite3
import os
import plotly.express as px
from fpdf import FPDF
from datetime import datetime
import pytz
import numpy as np
import unicodedata
from PIL import Image
import io
from streamlit_gsheets import GSheetsConnection

# 1. CONFIGURACIÓN E IDENTIDAD
st.set_page_config(page_title="SISTEMA QUEVEDO PRO", layout="wide", page_icon="💎")

NOMBRE_PROPIETARIO = "LUIS RAFAEL QUEVEDO"
UBICACION_SISTEMA = "Santo Domingo, Rep. Dom."

# 2. FUNCIONES DE UTILIDAD
def limpiar_texto(texto):
    if not texto: return ""
    return "".join(c for c in unicodedata.normalize('NFD', str(texto)) if unicodedata.category(c) != 'Mn')

def inicializar_sistema():
    # Crear carpetas si no existen
    base_path = "archivador_quevedo"
    subcarpetas = ["MEDICAL", "GASTOS", "PERSONALES", "RECETAS_COCINA"]
    if not os.path.exists(base_path):
        os.makedirs(base_path)
    for sub in subcarpetas:
        os.makedirs(os.path.join(base_path, sub), exist_ok=True)
    
    # Conexión y creación de tablas robustas
    conn = sqlite3.connect("sistema_quevedo_integral.db", check_same_thread=False)
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS glucosa (id INTEGER PRIMARY KEY AUTOINCREMENT, valor INTEGER, fecha TEXT, hora TEXT, estado TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS citas (id INTEGER PRIMARY KEY AUTOINCREMENT, doctor TEXT, fecha TEXT, hora TEXT, centro TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS medicinas (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, dosis INTEGER, frecuencia TEXT, hora_toma TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS archivador_index (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, categoria TEXT, texto_ocr TEXT, fecha TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS finanzas (id INTEGER PRIMARY KEY AUTOINCREMENT, tipo TEXT, categoria TEXT, monto REAL, fecha TEXT)")
    conn.commit()
    return conn, c

conn, c = inicializar_sistema()

# 3. DISEÑO VISUAL
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .stButton>button { width: 100%; border-radius: 12px; background-color: #1b5e20; color: white; font-weight: bold; }
    .resumen-card { background: linear-gradient(135deg, #1e2130 0%, #1b5e20 100%); padding: 15px; border-radius: 15px; border: 1px solid #4CAF50; text-align: center; }
    </style>
    """, unsafe_allow_html=True)

# 4. NAVEGACIÓN
st.sidebar.title("💎 SISTEMA QUEVEDO")
menu = st.sidebar.radio("MODULOS", ["🏠 INICIO", "💰 FINANZAS", "🩺 BIOMONITOR", "💊 AGENDA", "📸 ESCANER", "📂 ARCHIVADOR", "🤖 ASISTENTE"])

# --- MODULO: INICIO ---
if menu == "🏠 INICIO":
    st.header(f"📊 Resumen: {NOMBRE_PROPIETARIO}")
    c1, c2, c3 = st.columns(3)
    
    df_fin = pd.read_sql_query("SELECT SUM(monto) as total FROM finanzas", conn)
    df_glu = pd.read_sql_query("SELECT valor FROM glucosa ORDER BY id DESC LIMIT 1", conn)
    
    with c1:
        st.markdown('<div class="resumen-card">', unsafe_allow_html=True)
        st.metric("💰 BALANCE", f"RD$ {df_fin['total'][0] or 0:,.2f}")
        st.markdown('</div>', unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="resumen-card">', unsafe_allow_html=True)
        st.metric("🩺 ÚLTIMA GLUCOSA", f"{df_glu['valor'][0] if not df_glu.empty else 'N/A'} mg/dL")
        st.markdown('</div>', unsafe_allow_html=True)

# --- MODULO: BIOMONITOR ---
elif menu == "🩺 BIOMONITOR":
    st.header("🩺 Control de Glucosa")
    val_g = st.number_input("Nivel mg/dL", min_value=0)
    if st.button("Guardar Medición"):
        ahora = datetime.now(pytz.timezone('America/Santo_Domingo'))
        c.execute("INSERT INTO glucosa (valor, fecha, hora, estado) VALUES (?,?,?,?)", 
                  (val_g, ahora.strftime("%d/%m/%y"), ahora.strftime("%I:%M %p"), "REGISTRADO"))
        conn.commit()
        st.success("¡Registrado!")
        st.rerun()

# --- MODULO: AGENDA ---
elif menu == "💊 AGENDA":
    st.header("📅 Agenda Médica y Fármacos")
    t1, t2 = st.tabs(["📝 CITAS", "💊 MEDICAMENTOS"])
    
    with t1:
        with st.form("f_citas", clear_on_submit=True):
            col1, col2 = st.columns(2)
            doc = col1.text_input("Doctor/Especialidad")
            f_cita = col2.date_input("Fecha")
            h_cita = col1.time_input("Hora")
            lug = col2.text_input("Centro Médico")
            if st.form_submit_button("AGENDAR"):
                h_fmt = h_cita.strftime("%I:%M %p").upper()
                c.execute("INSERT INTO citas (doctor, fecha, hora, centro) VALUES (?,?,?,?)", (doc, str(f_cita), h_fmt, lug))
                conn.commit()
                st.rerun()
        df_c = pd.read_sql_query("SELECT * FROM citas ORDER BY fecha ASC", conn)
        st.dataframe(df_c, use_container_width=True)

    with t2:
        with st.form("f_meds", clear_on_submit=True):
            m_nom = st.text_input("Medicamento")
            m_dos = st.number_input("Dosis", min_value=0)
            m_fre = st.selectbox("Frecuencia", ["Cada 8h", "Cada 12h", "1 al día"])
            if st.form_submit_button("GUARDAR"):
                c.execute("INSERT INTO medicinas (nombre, dosis, frecuencia) VALUES (?,?,?)", (m_nom, m_dos, m_fre))
                conn.commit()
                st.rerun()
        st.dataframe(pd.read_sql_query("SELECT * FROM medicinas", conn), use_container_width=True)

# --- MODULO: ESCANER ---
elif menu == "📸 ESCANER":
    st.header("📸 Inteligencia Visual")
    img_file = st.camera_input("SCANNER QUEVEDO")
    if img_file:
        img = Image.open(img_file)
        st.image(img, width=400)
        st.info("🤖 Procesando imagen... (Asegúrate de tener pyzbar y pytesseract instalados)")
        # Aquí va tu lógica de OCR y Nube que ya tenías configurada.

# --- MODULO: ARCHIVADOR ---
elif menu == "📂 ARCHIVADOR":
    st.header("📂 Archivador v3.0")
    t_bus, t_sub = st.tabs(["🔍 BUSCADOR", "📤 SUBIR"])
    
    with t_bus:
        q = st.text_input("Buscar en documentos")
        if q:
            res = c.execute("SELECT * FROM archivador_index WHERE texto_ocr LIKE ?", (f'%{q}%',)).fetchall()
            st.write(res if res else "No hay coincidencias.")
            
    with t_sub:
        u_file = st.file_uploader("Documento", type=["jpg", "png"])
        u_cat = st.selectbox("Carpeta", ["MEDICAL", "GASTOS", "PERSONALES"])
        if u_file and st.button("PROCESAR"):
            fname = f"{u_cat}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
            fpath = os.path.join("archivador_quevedo", u_cat, fname)
            Image.open(u_file).save(fpath)
            c.execute("INSERT INTO archivador_index (nombre, categoria, fecha) VALUES (?,?,?)", (fname, u_cat, datetime.now().strftime("%d/%m/%y")))
            conn.commit()
            st.success("Guardado localmente.")

# --- MODULO: ASISTENTE ---
elif menu == "🤖 ASISTENTE":
    st.header("🤖 Inteligencia Predictiva")
    st.subheader("🔮 Salud")
    df_g = pd.read_sql_query("SELECT valor FROM glucosa ORDER BY id DESC LIMIT 10", conn)
    if not df_g.empty:
        prom = df_g['valor'].mean()
        st.metric("Promedio Reciente", f"{int(prom)} mg/dL")
    
    st.divider()
    preg = st.text_input("Consulta al sistema")
    if preg:
        st.write("🤖 Analizando tus datos históricos...")

# --- CIERRE ---
st.sidebar.divider()
st.sidebar.markdown(f"**Propiedad de:** {NOMBRE_PROPIETARIO}")
st.sidebar.caption("Versión Robusta 2026 - RD 🇩🇴")
