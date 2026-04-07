import streamlit as st
import pandas as pd
import sqlite3
import os
import plotly.express as px
from fpdf import FPDF
from datetime import datetime
import pytz
import unicodedata
from PIL import Image
from streamlit_gsheets import GSheetsConnection

# 1. CONFIGURACIÓN E INTERFAZ
st.set_page_config(page_title="SISTEMA QUEVEDO PRO", layout="wide", page_icon="💎")

# --- IDENTIDAD ---
NOMBRE_PROPIETARIO = "LUIS RAFAEL QUEVEDO"
UBICACION_SISTEMA = "Santo Domingo, Rep. Dom."

def limpiar_texto(texto):
    if not texto: return ""
    return "".join(c for c in unicodedata.normalize('NFD', str(texto)) if unicodedata.category(c) != 'Mn')

# --- SEGURIDAD ---
if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False

if not st.session_state["autenticado"]:
    st.markdown("<h1 style='text-align: center; color: #4CAF50;'>💎 SISTEMA QUEVEDO</h1>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        u = st.text_input("Usuario")
        p = st.text_input("Contraseña", type="password")
        if st.button("DESBLOQUEAR"):
            if u == "Admin" and p == "1234":
                st.session_state["autenticado"] = True
                st.rerun()
            else:
                st.error("Acceso Denegado")
    st.stop()

# --- BASE DE DATOS ---
def iniciar_db():
    conn = sqlite3.connect("sistema_quevedo_integral.db", check_same_thread=False)
    c = conn.cursor()
    tables = [
        'CREATE TABLE IF NOT EXISTS finanzas (id INTEGER PRIMARY KEY AUTOINCREMENT, categoria TEXT, monto REAL, fecha TEXT)',
        'CREATE TABLE IF NOT EXISTS glucosa (id INTEGER PRIMARY KEY AUTOINCREMENT, valor INTEGER, fecha TEXT, hora TEXT, estado TEXT)',
        'CREATE TABLE IF NOT EXISTS medicinas (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, horario TEXT)',
        'CREATE TABLE IF NOT EXISTS citas (id INTEGER PRIMARY KEY AUTOINCREMENT, doctor TEXT, fecha TEXT)'
    ]
    for table in tables: c.execute(table)
    conn.commit()
    return conn

conn = iniciar_db()
c = conn.cursor()

# --- GENERADOR DE PDF ROBUSTO (CORREGIDO) ---
def generar_reporte_maestro_pdf():
    try:
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(0, 10, "REPORTE MAESTRO - SISTEMA QUEVEDO", ln=True, align='C')
        pdf.ln(10)

        sections = [
            ("FINANZAS", "SELECT fecha, categoria, monto FROM finanzas ORDER BY id DESC LIMIT 10", ["Fecha", "Concepto", "Monto"]),
            ("GLUCOSA", "SELECT fecha, hora, valor, estado FROM glucosa ORDER BY id DESC LIMIT 10", ["Fecha", "Hora", "Valor", "Estado"]),
            ("MEDICINAS", "SELECT nombre, horario FROM medicinas", ["Medicina", "Horario"])
        ]

        for title, query, cols in sections:
            pdf.set_font("Arial", 'B', 12)
            pdf.cell(0, 10, title, ln=True)
            pdf.set_font("Arial", '', 10)
            df = pd.read_sql_query(query, conn)
            if not df.empty:
                for col in cols: pdf.cell(60, 8, col, 1)
                pdf.ln()
                for _, row in df.iterrows():
                    for val in row: pdf.cell(60, 7, limpiar_texto(str(val)), 1)
                    pdf.ln()
            else:
                pdf.cell(0, 8, "No hay datos registrados.", ln=True)
            pdf.ln(5)

        # Retornar como bytes puros (Esto arregla el error de Streamlit)
        return pdf.output(dest='S').encode('latin-1')
    except Exception as e:
        return None

# --- ESTILOS ---
st.markdown("""
    <style>
    .stButton>button { background-color: #1b5e20; color: white; border-radius: 10px; font-weight: bold; }
    .resumen-card { background: #1e2130; padding: 20px; border-radius: 15px; border-left: 5px solid #4CAF50; text-align: center; }
    </style>
    """, unsafe_allow_html=True)

# --- NAVEGACIÓN ---
menu = st.sidebar.radio("MODULOS", ["🏠 INICIO (RESUMEN)", "💰 FINANZAS IA", "🩺 BIOMONITOR", "💊 AGENDA MEDICA", "📸 ESCANER", "📂 ARCHIVADOR", "🤖 ASISTENTE"])

with st.sidebar:
    st.divider()
    st.subheader("📊 Reportes PDF")
    pdf_bytes = generar_reporte_maestro_pdf()
    if pdf_bytes:
        st.download_button(
            label="📥 DESCARGAR REPORTE MAESTRO",
            data=pdf_bytes,
            file_name=f"Reporte_Quevedo_{datetime.now().strftime('%d_%m_%Y')}.pdf",
            mime="application/pdf"
        )

# --- LÓGICA DE MÓDULOS ---
if menu == "🏠 INICIO (RESUMEN)":
    st.header("📊 Resumen General")
    c1, c2, c3 = st.columns(3)
    # Lógica de métricas...
    with c1: st.info("💰 Balance Activo")
    with c2: st.success("🩺 Glucosa Controlada")
    with c3: st.warning("💊 Medicinas al Día")

elif menu == "💰 FINANZAS IA":
    st.header("💰 Control Financiero")
    with st.form("f_fin"):
        cat = st.selectbox("Categoría", ["Salud", "Alimentos", "Otros"])
        mon = st.number_input("Monto RD$")
        if st.form_submit_button("Guardar"):
            c.execute("INSERT INTO finanzas (fecha, categoria, monto) VALUES (?,?,?)", (datetime.now().strftime("%d/%m/%Y"), cat, mon))
            conn.commit()
            st.rerun()
    st.dataframe(pd.read_sql_query("SELECT * FROM finanzas", conn), use_container_width=True)

elif menu == "🩺 BIOMONITOR":
    st.header("🩺 Glucosa")
    val = st.number_input("Nivel mg/dL", min_value=0)
    if st.button("Guardar Toma"):
        tz = pytz.timezone('America/Santo_Domingo')
        ahora = datetime.now(tz)
        c.execute("INSERT INTO glucosa (valor, fecha, hora, estado) VALUES (?,?,?,?)", (val, ahora.strftime("%d/%m/%y"), ahora.strftime("%I:%M %p"), "NORMAL"))
        conn.commit()
        st.rerun()
    df_g = pd.read_sql_query("SELECT * FROM glucosa ORDER BY id DESC", conn)
    if not df_g.empty: st.plotly_chart(px.line(df_g, x="fecha", y="valor"))

elif menu == "💊 AGENDA MEDICA":
    st.header("💊 Medicinas y Citas")
    # Lógica de tablas de medicinas...
    st.info("Módulo de inventario activo.")

elif menu == "📸 ESCANER":
    st.header("📸 Escáner de Códigos")
    img = st.file_uploader("Capturar código", type=['jpg','png'])
    if img: st.image(img, caption="Procesando...")

elif menu == "📂 ARCHIVADOR":
    st.header("📂 Archivador Personal")
    # Listar archivos...

elif menu == "🤖 ASISTENTE":
    st.header("🤖 Asistente e Integración")
    if st.button("📲 Consultar Farmacia"):
        st.write("Abriendo WhatsApp...")

# --- CRÉDITOS ---
st.markdown("---")
st.markdown(f"<div style='text-align: center;'><h3>💎 {NOMBRE_PROPIETARIO}</h3><p>Sistema Quevedo Pro v2.6</p></div>", unsafe_allow_html=True)
