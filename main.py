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
    .stButton>button { width: 100%; border-radius: 12px; height: 3.5em; background-color: #1b5e20; color: white; font-weight: bold; border: none; }
    .card-resumen { background-color: #1e2130; padding: 20px; border-radius: 15px; border-top: 5px solid #4CAF50; text-align: center; margin-bottom: 15px; }
    .semaforo-rojo { background-color: #c62828; padding: 20px; border-radius: 15px; color: white; animation: pulse 2s infinite; text-align: center; font-weight: bold; }
    @keyframes pulse { 0% {box-shadow: 0 0 0 0px rgba(198, 40, 40, 0.7);} 70% {box-shadow: 0 0 0 15px rgba(198, 40, 40, 0);} 100% {box-shadow: 0 0 0 0px rgba(198, 40, 40, 0);} }
    </style>
    """, unsafe_allow_html=True)

# --- 2. MOTOR DE DATOS Y PERSISTENCIA REAL ---
DB_NAME = "sistema_quevedo_integral.db"
DIR_ARCHIVOS = "archivador_quevedo"

if not os.path.exists(DIR_ARCHIVOS):
    os.makedirs(DIR_ARCHIVOS)

def db_query(query, params=(), fetch=False):
    with sqlite3.connect(DB_NAME, check_same_thread=False) as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()
        return cursor.fetchall() if fetch else None

# Inicialización de Tablas (Todas las herramientas)
db_query('CREATE TABLE IF NOT EXISTS finanzas (id INTEGER PRIMARY KEY AUTOINCREMENT, tipo TEXT, cat TEXT, monto REAL, fecha TEXT)')
db_query('CREATE TABLE IF NOT EXISTS presupuesto (id INTEGER PRIMARY KEY AUTOINCREMENT, limite REAL)')
db_query('CREATE TABLE IF NOT EXISTS glucosa (id INTEGER PRIMARY KEY AUTOINCREMENT, valor INTEGER, fecha TEXT, hora TEXT)')
db_query('CREATE TABLE IF NOT EXISTS medicinas (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, hora TEXT)')
db_query('CREATE TABLE IF NOT EXISTS citas (id INTEGER PRIMARY KEY AUTOINCREMENT, doctor TEXT, fecha TEXT, hora TEXT)')
db_query('CREATE TABLE IF NOT EXISTS archivador (id INTEGER PRIMARY KEY AUTOINCREMENT, file TEXT, desc TEXT, fecha TEXT)')

# --- 3. CONTACTOS DE EMERGENCIA (LOS 7) ---
contactos = {
    "Mi Hijo": "18292061693", "Mi Hija": "18292581449", "Franklin": "16463746377",
    "Hermanito": "14077975432", "Dorka": "18298811692", "Rosa": "18293800425", "Pedro": "18097100995"
}

# --- 4. NAVEGACIÓN Y HERRAMIENTAS RÁPIDAS ---
st.sidebar.title("💎 SISTEMA QUEVEDO")
st.sidebar.write("Desarrollador: Luis Rafael Quevedo")
menu = st.sidebar.radio("MENÚ PRINCIPAL", ["🏠 DASHBOARD", "💰 FINANZAS", "🩺 SALUD", "📅 AGENDA", "📂 ARCHIVADOR"])
st.sidebar.markdown("---")
st.sidebar.link_button("📧 ABRIR MI GMAIL", "https://mail.google.com")
st.sidebar.warning("🔒 Seguridad Desactivada para Pruebas")

# --- 5. MÓDULOS DEL SISTEMA ---

if menu == "🏠 DASHBOARD":
    st.header("🏠 Resumen Ejecutivo")
    df_f = pd.read_sql_query("SELECT monto FROM finanzas", sqlite3.connect(DB_NAME))
    df_g = pd.read_sql_query("SELECT valor FROM glucosa", sqlite3.connect(DB_NAME))
    
    c1, c2, c3 = st.columns(3)
    with c1:
        bal = df_f['monto'].sum() if not df_f.empty else 0
        st.markdown(f"<div class='card-resumen'><h3>💰 Balance</h3><h2>RD$ {bal:,.2f}</h2></div>", unsafe_allow_html=True)
    with c2:
        prom = df_g['valor'].mean() if not df_g.empty else 0
        st.markdown(f"<div class='card-resumen'><h3>🩺 Glucosa Prom.</h3><h2>{prom:.1f} mg/dL</h2></div>", unsafe_allow_html=True)
    with c3:
        if prom > 0:
            a1c = (46.7 + prom) / 28.7
            st.markdown(f"<div class='card-resumen'><h3>📊 eA1c Est.</h3><h2>{a1c:.1f} %</h2></div>", unsafe_allow_html=True)

elif menu == "💰 FINANZAS":
    st.header("💰 Gestión de Dinero e IA")
    lim_data = db_query("SELECT limite FROM presupuesto ORDER BY id DESC LIMIT 1", fetch=True)
    limite = lim_data[0][0] if lim_data else 0.0
    
    with st.expander("⚙️ AJUSTAR LÍMITE DE PRESUPUESTO"):
        nuevo_lim = st.number_input("RD$ Mensual", value=float(limite))
        if st.button("Actualizar"):
            db_query("INSERT INTO presupuesto (limite) VALUES (?)", (nuevo_lim,))
            st.rerun()

    with st.form("form_f", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        t = col1.selectbox("Tipo", ["INGRESO", "GASTO"])
        c = col2.text_input("Concepto").upper()
        m = col3.number_input("Monto RD$", min_value=0.0)
        if st.form_submit_button("REGISTRAR"):
            val = m if t == "INGRESO" else -m
            db_query("INSERT INTO finanzas (tipo, cat, monto, fecha) VALUES (?,?,?,?)", (t, c, val, datetime.now().strftime("%d/%m/%Y")))
            st.rerun()
    
    df_f = pd.read_sql_query("SELECT * FROM finanzas ORDER BY id DESC", sqlite3.connect(DB_NAME))
    if not df_f.empty:
        gastos = abs(df_f[df_f['monto'] < 0]['monto'].sum())
        if limite > 0:
            st.progress(min(gastos/limite, 1.0))
            st.write(f"Consumo: RD$ {gastos:,.2f} de {limite:,.2f}")
        
        if len(df_f) > 3:
            X = np.arange(len(df_f)).reshape(-1, 1)
            y = df_f['monto'].cumsum().values
            pred = LinearRegression().fit(X, y).predict([[len(df_f) + 1]])[0]
            st.metric("PREDICCIÓN SALDO PRÓXIMO MES", f"RD$ {pred:,.2f}")
        
        st.dataframe(df_f.head(10), use_container_width=True)
        if st.button("🗑️ Borrar Último"):
            db_query("DELETE FROM finanzas WHERE id = (SELECT MAX(id) FROM finanzas)"); st.rerun()

elif menu == "🩺 SALUD":
    st.header("🩺 Monitor de Glucosa")
    val_g = st.number_input("Nivel actual (mg/dL):", min_value=0)
    
    if val_g > 160:
        st.markdown(f"<div class='semaforo-rojo'>🚨 ALERTA CRÍTICA: {val_g} mg/dL</div>", unsafe_allow_html=True)
        cols = st.columns(4)
        for i, (nom, num) in enumerate(contactos.items()):
            cols[i % 4].link_button(f"📲 {nom}", f"https://api.whatsapp.com/send?phone={num}&text=Alerta Salud Luis: Glucosa {val_g}")
    
    if st.button("💾 GUARDAR TOMA"):
        ahora = datetime.now(pytz.timezone('America/Santo_Domingo'))
        db_query("INSERT INTO glucosa (valor, fecha, hora) VALUES (?,?,?)", (val_g, ahora.strftime("%d/%m/%y"), ahora.strftime("%I:%M %p")))
        st.rerun()

    df_g = pd.read_sql_query("SELECT * FROM glucosa ORDER BY id ASC", sqlite3.connect(DB_NAME))
    if not df_g.empty:
        st.plotly_chart(px.line(df_g, x="fecha", y="valor", markers=True, title="Historial"), use_container_width=True)
        st.table(df_g.tail(10))
        if st.button("🗑️ Borrar Última"):
            db_query("DELETE FROM glucosa WHERE id = (SELECT MAX(id) FROM glucosa)"); st.rerun()

elif menu == "📅 AGENDA":
    st.header("📅 Agenda de Medicinas y Citas")
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("💊 Medicinas")
        with st.form("f_m", clear_on_submit=True):
            med = st.text_input("Medicina"); hr = st.text_input("Hora")
            if st.form_submit_button("Añadir"):
                db_query("INSERT INTO medicinas (nombre, hora) VALUES (?,?)", (med.upper(), hr)); st.rerun()
        for i, r in pd.read_sql_query("SELECT * FROM medicinas", sqlite3.connect(DB_NAME)).iterrows():
            st.info(f"💊 {r['nombre']} - {r['hora']}")
            
    with c2:
        st.subheader("👨‍⚕️ Citas")
        with st.form("f_c", clear_on_submit=True):
            dr = st.text_input("Doctor"); fca = st.date_input("Fecha"); hr_c = st.text_input("Hora")
            if st.form_submit_button("Agendar"):
                db_query("INSERT INTO citas (doctor, fecha, hora) VALUES (?,?,?)", (dr.upper(), str(fca), hr_c)); st.rerun()
        for i, r in pd.read_sql_query("SELECT * FROM citas", sqlite3.connect(DB_NAME)).iterrows():
            st.warning(f"📅 {r['doctor']} | {r['fecha']} - {r['hora']}")

elif menu == "📂 ARCHIVADOR":
    st.header("📂 Archivador de Documentos")
    foto = st.camera_input("Capturar")
    desc = st.text_input("Descripción:").upper()
    
    if foto and desc and st.button("💾 GUARDAR"):
        fname = f"doc_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        path = os.path.join(DIR_ARCHIVOS, fname)
        with open(path, "wb") as f: f.write(foto.getbuffer())
        db_query("INSERT INTO archivador (file, desc, fecha) VALUES (?,?,?)", (fname, desc, datetime.now().strftime("%d/%m/%Y")))
        st.success("Guardado"); st.rerun()

    df_a = pd.read_sql_query("SELECT * FROM archivador ORDER BY id DESC", sqlite3.connect(DB_NAME))
    for i, r in df_a.iterrows():
        with st.expander(f"📄 {r['desc']} ({r['fecha']})"):
            fpath = os.path.join(DIR_ARCHIVOS, r['file'])
            if os.path.exists(fpath):
                st.image(fpath)
                with open(fpath, "rb") as f: st.download_button("📥 Descargar", f, file_name=r['file'], key=f"dl_{r['id']}")
            if st.button("🗑️ Eliminar", key=f"del_{r['id']}"):
                db_query("DELETE FROM archivador WHERE id=?", (r['id'],))
                if os.path.exists(fpath): os.remove(fpath)
                st.rerun()

st.sidebar.info(f"Sistema Quevedo v21.0\nLuis Rafael Quevedo")
