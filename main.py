import streamlit as st
import pandas as pd
import sqlite3
import os
import plotly.express as px
from datetime import datetime
import pytz
import numpy as np
from sklearn.linear_model import LinearRegression

# --- 1. CONFIGURACIÓN E INTERFAZ ---
st.set_page_config(page_title="SISTEMA QUEVEDO PRO", layout="wide", page_icon="💎")

# Estilos CSS para que se vea profesional en el celular
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .stButton>button { width: 100%; border-radius: 12px; height: 3.5em; background-color: #1b5e20; color: white; font-weight: bold; border: none; }
    .card-resumen { background-color: #1e2130; padding: 20px; border-radius: 15px; border-top: 5px solid #4CAF50; text-align: center; margin-bottom: 15px; }
    .semaforo-rojo { background-color: #c62828; padding: 20px; border-radius: 15px; color: white; animation: pulse 2s infinite; text-align: center; }
    @keyframes pulse { 0% {box-shadow: 0 0 0 0px rgba(198, 40, 40, 0.7);} 70% {box-shadow: 0 0 0 15px rgba(198, 40, 40, 0);} 100% {box-shadow: 0 0 0 0px rgba(198, 40, 40, 0);} }
    </style>
    """, unsafe_allow_html=True)

# --- 2. MOTOR DE DATOS Y DIRECTORIOS ---
DB_NAME = "sistema_quevedo_v13.db"
DIR_ARCHIVOS = "archivador_quevedo"

if not os.path.exists(DIR_ARCHIVOS):
    os.makedirs(DIR_ARCHIVOS)

def db_query(query, params=(), fetch=False):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()
        return cursor.fetchall() if fetch else None

# Inicialización de tablas
db_query('CREATE TABLE IF NOT EXISTS finanzas (id INTEGER PRIMARY KEY AUTOINCREMENT, tipo TEXT, cat TEXT, monto REAL, fecha TEXT)')
db_query('CREATE TABLE IF NOT EXISTS presupuesto (id INTEGER PRIMARY KEY AUTOINCREMENT, limite REAL)')
db_query('CREATE TABLE IF NOT EXISTS glucosa (id INTEGER PRIMARY KEY AUTOINCREMENT, valor INTEGER, fecha TEXT, hora TEXT)')
db_query('CREATE TABLE IF NOT EXISTS medicinas (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, hora TEXT)')
db_query('CREATE TABLE IF NOT EXISTS archivador (id INTEGER PRIMARY KEY AUTOINCREMENT, file TEXT, desc TEXT, fecha TEXT)')

# --- 3. SEGURIDAD ---
if "auth" not in st.session_state: st.session_state.auth = False

if not st.session_state.auth:
    st.title("💎 ACCESO SISTEMA QUEVEDO")
    u = st.text_input("Usuario")
    p = st.text_input("Contraseña", type="password")
    if st.button("DESBLOQUEAR"):
        if u == "admin" and p == "Quevedo2026":
            st.session_state.auth = True
            st.rerun()
        else: st.error("Acceso Denegado")
    st.stop()

# --- 4. LÓGICA DE CONTACTOS ---
contactos = {
    "Mi Hijo": "18292061693", "Mi Hija": "18292581449", "Franklin": "16463746377",
    "Hermanito": "14077975432", "Dorka": "18298811692", "Rosa": "18293800425", "Pedro": "18097100995"
}

# --- 5. MENÚ Y NAVEGACIÓN ---
menu = st.sidebar.radio("SISTEMA QUEVEDO", ["🏠 DASHBOARD", "💰 FINANZAS", "🩺 SALUD", "💊 AGENDA", "📂 ARCHIVADOR"])
if st.sidebar.button("CERRAR SESIÓN"):
    st.session_state.auth = False
    st.rerun()

# --- 6. MÓDULOS DEL SISTEMA ---

if menu == "🏠 DASHBOARD":
    st.header("🏠 Resumen Ejecutivo")
    
    # Datos para los indicadores
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
            st.markdown(f"<div class='card-resumen'><h3>📊 eA1c</h3><h2>{a1c:.1f} %</h2></div>", unsafe_allow_html=True)

elif menu == "💰 FINANZAS":
    st.header("💰 Gestión Financiera e IA")
    
    # Límite de presupuesto
    lim_data = db_query("SELECT limite FROM presupuesto ORDER BY id DESC LIMIT 1", fetch=True)
    limite = lim_data[0][0] if lim_data else 0.0
    
    with st.expander("⚙️ AJUSTAR PRESUPUESTO"):
        nuevo_lim = st.number_input("Límite Mensual RD$", value=float(limite))
        if st.button("Actualizar Límite"):
            db_query("INSERT INTO presupuesto (limite) VALUES (?)", (nuevo_lim,))
            st.rerun()

    with st.form("f_finanzas", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        tipo = col1.selectbox("Movimiento", ["INGRESO", "GASTO"])
        concepto = col2.text_input("Concepto").upper()
        monto = col3.number_input("Monto RD$", min_value=0.0)
        if st.form_submit_button("REGISTRAR"):
            val = monto if tipo == "INGRESO" else -monto
            db_query("INSERT INTO finanzas (tipo, cat, monto, fecha) VALUES (?,?,?,?)", 
                     (tipo, concepto, val, datetime.now().strftime("%d/%m/%Y")))
            st.rerun()

    df_f = pd.read_sql_query("SELECT * FROM finanzas ORDER BY id DESC", sqlite3.connect(DB_NAME))
    if not df_f.empty:
        # Barra de Presupuesto
        gastos = abs(df_f[df_f['monto'] < 0]['monto'].sum())
        if limite > 0:
            st.write(f"Consumo: RD$ {gastos:,.2f} de {limite:,.2f}")
            st.progress(min(gastos/limite, 1.0))
        
        # IA Predicción
        if len(df_f) > 3:
            X = np.arange(len(df_f)).reshape(-1, 1)
            y = df_f['monto'].cumsum().values
            pred = LinearRegression().fit(X, y).predict([[len(df_f) + 1]])[0]
            st.metric("SALDO ESTIMADO PRÓXIMO MES", f"RD$ {pred:,.2f}")

        st.table(df_f.head(10))
        if st.button("🗑️ Borrar Último"):
            db_query("DELETE FROM finanzas WHERE id = (SELECT MAX(id) FROM finanzas)")
            st.rerun()

elif menu == "🩺 SALUD":
    st.header("🩺 Biomonitor de Glucosa")
    val_g = st.number_input("Nivel (mg/dL):", min_value=0)
    
    if val_g > 160:
        st.markdown(f"<div class='semaforo-rojo'>🚨 ALERTA CRÍTICA: {val_g} mg/dL</div>", unsafe_allow_html=True)
        st.warning("Notificar a familiares:")
        cols = st.columns(4)
        for i, (nom, num) in enumerate(contactos.items()):
            cols[i % 4].link_button(f"📲 {nom}", f"https://api.whatsapp.com/send?phone={num}&text=Alerta Salud Luis: Glucosa {val_g}")

    if st.button("💾 GUARDAR TOMA"):
        tz = pytz.timezone('America/Santo_Domingo')
        ahora = datetime.now(tz)
        db_query("INSERT INTO glucosa (valor, fecha, hora) VALUES (?,?,?)", 
                 (val_g, ahora.strftime("%d/%m/%y"), ahora.strftime("%I:%M %p")))
        st.rerun()

    df_g = pd.read_sql_query("SELECT * FROM glucosa", sqlite3.connect(DB_NAME))
    if not df_g.empty:
        st.plotly_chart(px.line(df_g, x="fecha", y="valor", title="Tendencia de Salud"))
        if st.button("🗑️ Borrar Última Toma"):
            db_query("DELETE FROM glucosa WHERE id = (SELECT MAX(id) FROM glucosa)")
            st.rerun()

elif menu == "💊 AGENDA":
    st.header("📅 Agenda y Medicinas")
    with st.form("f_med", clear_on_submit=True):
        m = st.text_input("Medicina")
        h = st.text_input("Hora")
        if st.form_submit_button("Añadir"):
            db_query("INSERT INTO medicinas (nombre, hora) VALUES (?,?)", (m.upper(), h))
            st.rerun()
    
    df_m = pd.read_sql_query("SELECT * FROM medicinas", sqlite3.connect(DB_NAME))
    for i, r in df_m.iterrows():
        st.info(f"💊 {r['nombre']} a las {r['hora']}")
    if st.button("🗑️ Limpiar Agenda"):
        db_query("DELETE FROM medicinas")
        st.rerun()

elif menu == "📂 ARCHIVADOR":
    st.header("📂 Archivador de Documentos")
    
    cam, ver = st.tabs(["📸 Escanear", "📂 Galería"])
    
    with cam:
        foto = st.camera_input("Capturar")
        desc = st.text_input("Descripción del documento:").upper()
        if foto and desc:
            if st.button("💾 GUARDAR DEFINITIVAMENTE"):
                fname = f"doc_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                path = os.path.join(DIR_ARCHIVOS, fname)
                try:
                    with open(path, "wb") as f:
                        f.write(foto.getbuffer())
                    db_query("INSERT INTO archivador (file, desc, fecha) VALUES (?,?,?)", 
                             (fname, desc, datetime.now().strftime("%d/%m/%Y")))
                    st.success("Guardado con éxito")
                    st.rerun()
                except Exception as e: st.error(f"Error: {e}")

    with ver:
        df_a = pd.read_sql_query("SELECT * FROM archivador ORDER BY id DESC", sqlite3.connect(DB_NAME))
        busq = st.text_input("🔍 Buscar por descripción:").upper()
        for i, r in df_a.iterrows():
            if busq in r['desc']:
                with st.expander(f"📄 {r['desc']} ({r['fecha']})"):
                    fpath = os.path.join(DIR_ARCHIVOS, r['file'])
                    if os.path.exists(fpath):
                        st.image(fpath)
                        with open(fpath, "rb") as f:
                            st.download_button("Descargar", f, file_name=r['file'], key=f"dl_{r['id']}")
                    if st.button("Borrar", key=f"del_{r['id']}"):
                        db_query("DELETE FROM archivador WHERE id=?", (r['id'],))
                        if os.path.exists(fpath): os.remove(fpath)
                        st.rerun()

# --- CRÉDITOS ---
st.sidebar.markdown("---")
st.sidebar.info(f"Sistema Quevedo v13.0\nDesarrollador: Luis Rafael Quevedo")
