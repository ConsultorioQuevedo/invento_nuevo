import streamlit as st
import pandas as pd
import sqlite3
import os
import plotly.express as px
from datetime import datetime
import pytz
import numpy as np
from sklearn.linear_model import LinearRegression

# --- 1. CONFIGURACIÓN E INTERFAZ PROFESIONAL ---
st.set_page_config(page_title="SISTEMA QUEVEDO PRO", layout="wide", page_icon="💎")

st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .stButton>button { width: 100%; border-radius: 12px; height: 3.5em; background-color: #1b5e20; color: white; font-weight: bold; }
    .card-resumen { background-color: #1e2130; padding: 20px; border-radius: 15px; border-top: 5px solid #4CAF50; text-align: center; margin-bottom: 15px; }
    .semaforo-rojo { background-color: #c62828; padding: 20px; border-radius: 15px; color: white; animation: pulse 2s infinite; text-align: center; font-weight: bold; }
    @keyframes pulse { 0% {box-shadow: 0 0 0 0px rgba(198, 40, 40, 0.7);} 70% {box-shadow: 0 0 0 15px rgba(198, 40, 40, 0);} 100% {box-shadow: 0 0 0 0px rgba(198, 40, 40, 0);} }
    </style>
    """, unsafe_allow_html=True)

# --- 2. MOTOR DE DATOS (PROTECCIÓN DE INFORMACIÓN) ---
DB_NAME = "sistema_quevedo_final.db"
DIR_ARCHIVOS = "archivador_quevedo"

if not os.path.exists(DIR_ARCHIVOS):
    os.makedirs(DIR_ARCHIVOS)

def db_query(query, params=(), fetch=False):
    with sqlite3.connect(DB_NAME, check_same_thread=False) as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()
        return cursor.fetchall() if fetch else None

# Inicialización de todas las tablas necesarias
db_query('CREATE TABLE IF NOT EXISTS finanzas (id INTEGER PRIMARY KEY AUTOINCREMENT, tipo TEXT, cat TEXT, monto REAL, fecha TEXT)')
db_query('CREATE TABLE IF NOT EXISTS presupuesto (id INTEGER PRIMARY KEY AUTOINCREMENT, limite REAL)')
db_query('CREATE TABLE IF NOT EXISTS glucosa (id INTEGER PRIMARY KEY AUTOINCREMENT, valor INTEGER, fecha TEXT, hora TEXT)')
db_query('CREATE TABLE IF NOT EXISTS medicinas (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, hora TEXT)')
db_query('CREATE TABLE IF NOT EXISTS citas (id INTEGER PRIMARY KEY AUTOINCREMENT, doctor TEXT, fecha TEXT)')
db_query('CREATE TABLE IF NOT EXISTS archivador (id INTEGER PRIMARY KEY AUTOINCREMENT, file TEXT, desc TEXT, fecha TEXT)')

# --- 3. SEGURIDAD DE ENTRADA ---
if "auth" not in st.session_state: st.session_state.auth = False

if not st.session_state.auth:
    st.title("💎 SISTEMA QUEVEDO")
    u = st.text_input("Usuario")
    p = st.text_input("Contraseña", type="password")
    if st.button("DESBLOQUEAR SISTEMA"):
        if u == "admin" and p == "Quevedo2026":
            st.session_state.auth = True
            st.rerun()
        else: st.error("Acceso Denegado")
    st.stop()

# --- 4. CONTACTOS DE EMERGENCIA ---
contactos = {
    "Mi Hijo": "18292061693", "Mi Hija": "18292581449", "Franklin": "16463746377",
    "Hermanito": "14077975432", "Dorka": "18298811692", "Rosa": "18293800425", "Pedro": "18097100995"
}

# --- 5. MENÚ Y HERRAMIENTAS RÁPIDAS ---
menu = st.sidebar.radio("MENÚ PRINCIPAL", ["🏠 DASHBOARD", "💰 FINANZAS", "🩺 SALUD", "📅 AGENDA", "📂 ARCHIVADOR"])
st.sidebar.markdown("---")
# Herramienta de Gmail Reintegrada
st.sidebar.link_button("📧 ABRIR MI GMAIL", "https://mail.google.com")
if st.sidebar.button("🔒 CERRAR SESIÓN"):
    st.session_state.auth = False
    st.rerun()

# --- 6. DESARROLLO DE MÓDULOS ---

if menu == "🏠 DASHBOARD":
    st.header("🏠 Resumen Luis Rafael Quevedo")
    df_f = pd.read_sql_query("SELECT monto FROM finanzas", sqlite3.connect(DB_NAME))
    df_g = pd.read_sql_query("SELECT valor FROM glucosa", sqlite3.connect(DB_NAME))
    
    c1, c2, c3 = st.columns(3)
    with c1:
        bal = df_f['monto'].sum() if not df_f.empty else 0
        st.markdown(f"<div class='card-resumen'><h3>💰 Balance Neto</h3><h2>RD$ {bal:,.2f}</h2></div>", unsafe_allow_html=True)
    with c2:
        prom = df_g['valor'].mean() if not df_g.empty else 0
        st.markdown(f"<div class='card-resumen'><h3>🩺 Glucosa Prom.</h3><h2>{prom:.1f} mg/dL</h2></div>", unsafe_allow_html=True)
    with c3:
        if prom > 0:
            a1c = (46.7 + prom) / 28.7
            st.markdown(f"<div class='card-resumen'><h3>📊 eA1c Estimada</h3><h2>{a1c:.1f} %</h2></div>", unsafe_allow_html=True)

elif menu == "💰 FINANZAS":
    st.header("💰 Gestión de Ingresos y Gastos")
    with st.form("form_finanzas", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        t = col1.selectbox("Tipo", ["INGRESO", "GASTO"])
        c = col2.text_input("Concepto (Ej: Supermercado)").upper()
        m = col3.number_input("Monto RD$", min_value=0.0)
        if st.form_submit_button("REGISTRAR MOVIMIENTO"):
            val = m if t == "INGRESO" else -m
            db_query("INSERT INTO finanzas (tipo, cat, monto, fecha) VALUES (?,?,?,?)", (t, c, val, datetime.now().strftime("%d/%m/%Y")))
            st.rerun()

    df_f = pd.read_sql_query("SELECT * FROM finanzas ORDER BY id DESC", sqlite3.connect(DB_NAME))
    if not df_f.empty:
        st.dataframe(df_f.head(15), use_container_width=True)
        if st.button("🗑️ Borrar Último Registro"):
            db_query("DELETE FROM finanzas WHERE id = (SELECT MAX(id) FROM finanzas)"); st.rerun()

elif menu == "🩺 SALUD":
    st.header("🩺 Monitor de Glucosa (Historial Completo)")
    val_g = st.number_input("Introducir mg/dL:", min_value=0)
    
    if val_g > 160:
        st.markdown(f"<div class='semaforo-rojo'>🚨 ALERTA: NIVEL ALTO ({val_g} mg/dL)</div>", unsafe_allow_html=True)
        cols = st.columns(4)
        for i, (nom, num) in enumerate(contactos.items()):
            cols[i % 4].link_button(f"📲 {nom}", f"https://api.whatsapp.com/send?phone={num}&text=Alerta Salud Luis: Glucosa en {val_g}")
    
    if st.button("💾 GUARDAR TOMA DE HOY"):
        ahora = datetime.now(pytz.timezone('America/Santo_Domingo'))
        db_query("INSERT INTO glucosa (valor, fecha, hora) VALUES (?,?,?)", (val_g, ahora.strftime("%d/%m/%y"), ahora.strftime("%I:%M %p")))
        st.rerun()

    # VISUALIZACIÓN DE GRÁFICO REPARADA
    df_g = pd.read_sql_query("SELECT * FROM glucosa ORDER BY id ASC", sqlite3.connect(DB_NAME))
    if not df_g.empty:
        st.plotly_chart(px.line(df_g, x="fecha", y="valor", markers=True, title="Tu Progreso de Glucosa"), use_container_width=True)
        st.subheader("📋 Datos Recientes")
        st.table(df_g.tail(10)) 
        if st.button("🗑️ Borrar Última Toma"):
            db_query("DELETE FROM glucosa WHERE id = (SELECT MAX(id) FROM glucosa)"); st.rerun()

elif menu == "📅 AGENDA":
    st.header("📅 Agenda de Medicinas y Citas Médicas")
    col_med, col_cita = st.columns(2)
    
    with col_med:
        st.subheader("💊 Control de Medicinas")
        with st.form("form_med", clear_on_submit=True):
            m = st.text_input("Nombre de Medicina"); h = st.text_input("Hora de toma")
            if st.form_submit_button("Añadir a la lista"):
                db_query("INSERT INTO medicinas (nombre, hora) VALUES (?,?)", (m.upper(), h)); st.rerun()
        for i, r in pd.read_sql_query("SELECT * FROM medicinas", sqlite3.connect(DB_NAME)).iterrows():
            st.info(f"🔹 {r['nombre']} - {r['hora']}")
            
    with col_cita:
        st.subheader("👨‍⚕️ Próximas Citas")
        with st.form("form_cita", clear_on_submit=True):
            dr = st.text_input("Nombre del Doctor"); fca = st.date_input("Fecha Programada")
            if st.form_submit_button("Agendar Cita"):
                db_query("INSERT INTO citas (doctor, fecha) VALUES (?,?)", (dr.upper(), str(fca))); st.rerun()
        for i, r in pd.read_sql_query("SELECT * FROM citas", sqlite3.connect(DB_NAME)).iterrows():
            st.warning(f"📅 Cita: {r['doctor']} el {r['fecha']}")

elif menu == "📂 ARCHIVADOR":
    st.header("📂 Archivador de Documentos y Recetas")
    foto = st.camera_input("Capturar Documento")
    desc = st.text_input("Escribe una descripción del documento:").upper()
    
    if foto and desc and st.button("💾 GUARDAR EN MI ARCHIVADOR"):
        nombre_f = f"doc_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        ruta = os.path.join(DIR_ARCHIVOS, nombre_f)
        with open(ruta, "wb") as f: f.write(foto.getbuffer())
        db_query("INSERT INTO archivador (file, desc, fecha) VALUES (?,?,?)", (nombre_f, desc, datetime.now().strftime("%d/%m/%Y")))
        st.success("Documento Guardado con éxito"); st.rerun()

    st.markdown("---")
    df_arch = pd.read_sql_query("SELECT * FROM archivador ORDER BY id DESC", sqlite3.connect(DB_NAME))
    for i, r in df_arch.iterrows():
        with st.expander(f"📄 {r['desc']} - {r['fecha']}"):
            f_ruta = os.path.join(DIR_ARCHIVOS, r['file'])
            if os.path.exists(f_ruta):
                st.image(f_ruta)
                with open(f_ruta, "rb") as f_img:
                    st.download_button("📥 Descargar", f_img, file_name=r['file'], key=f"btn_{r['id']}")
            if st.button("Eliminar Archivo", key=f"del_arch_{r['id']}"):
                db_query("DELETE FROM archivador WHERE id=?", (r['id'],))
                if os.path.exists(f_ruta): os.remove(f_ruta)
                st.rerun()

# --- PIE DE PÁGINA ---
st.sidebar.markdown(f"---")
st.sidebar.info(f"Sistema Quevedo v16.0\nUsuario: Luis Rafael Quevedo")
