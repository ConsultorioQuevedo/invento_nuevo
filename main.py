import streamlit as st
import pandas as pd
import sqlite3
import os
import plotly.express as px
from fpdf import FPDF
from datetime import datetime
import pytz
import numpy as np
from PIL import Image
from pyzbar.pyzbar import decode
import cv2

# ==========================================
# 1. CONFIGURACIÓN E IDENTIDAD
# ==========================================
st.set_page_config(page_title="SISTEMA QUEVEDO PRO", layout="wide", page_icon="💎")

NOMBRE_PROPIETARIO = "LUIS RAFAEL QUEVEDO"
ZONA_HORARIA = pytz.timezone('America/Santo_Domingo')

# --- ESTILOS PROFESIONALES ---
st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 12px; background-color: #1b5e20; color: white; font-weight: bold; height: 3.5em; border: 1px solid #4CAF50; }
    .resumen-card { background: linear-gradient(135deg, #1e2130 0%, #1b5e20 100%); padding: 20px; border-radius: 15px; border: 1px solid #4CAF50; text-align: center; }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. MOTOR DE BASE DE DATOS (NÚCLEO)
# ==========================================
def inicializar_db():
    conn = sqlite3.connect("quevedo_master.db", check_same_thread=False)
    c = conn.cursor()
    # Tablas Unificadas
    c.execute("CREATE TABLE IF NOT EXISTS finanzas (id INTEGER PRIMARY KEY AUTOINCREMENT, tipo TEXT, categoria TEXT, monto REAL, fecha TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS presupuesto (monto_limite REAL)")
    c.execute("CREATE TABLE IF NOT EXISTS glucosa (id INTEGER PRIMARY KEY AUTOINCREMENT, valor INTEGER, fecha TEXT, hora TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS citas (id INTEGER PRIMARY KEY AUTOINCREMENT, doctor TEXT, fecha TEXT, hora TEXT, centro TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS medicinas (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, dosis TEXT, frecuencia TEXT, hora_toma TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS archivador (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, categoria TEXT, contenido TEXT, fecha TEXT)")
    conn.commit()
    return conn, c

conn, c = inicializar_db()

# ==========================================
# 3. NAVEGACIÓN
# ==========================================
st.sidebar.title("💎 QUEVEDO MASTER")
menu = st.sidebar.radio("MENÚ TÉCNICO", ["🏠 PANEL CONTROL", "💰 FINANZAS PRO", "📸 ESCÁNER IA", "🩺 SALUD", "📁 ARCHIVADOR", "🤖 ASISTENTE"])

# ==========================================
# 4. MÓDULOS FUNCIONALES
# ==========================================

# --- PANEL DE CONTROL ---
if menu == "🏠 PANEL CONTROL":
    st.header(f"📊 Estado del Sistema: {NOMBRE_PROPIETARIO}")
    col1, col2, col3 = st.columns(3)
    
    df_f = pd.read_sql_query("SELECT SUM(monto) as total FROM finanzas", conn)
    df_g = pd.read_sql_query("SELECT valor FROM glucosa ORDER BY id DESC LIMIT 1", conn)
    
    with col1:
        st.markdown('<div class="resumen-card">', unsafe_allow_html=True)
        st.metric("💰 BALANCE ACTUAL", f"RD$ {df_f['total'][0] or 0:,.2f}")
        st.markdown('</div>', unsafe_allow_html=True)
    with col2:
        st.markdown('<div class="resumen-card">', unsafe_allow_html=True)
        st.metric("🩺 ÚLTIMA GLUCOSA", f"{df_g['valor'][0] if not df_g.empty else '0'} mg/dL")
        st.markdown('</div>', unsafe_allow_html=True)
    with col3:
        st.markdown('<div class="resumen-card">', unsafe_allow_html=True)
        num_docs = pd.read_sql_query("SELECT COUNT(*) as total FROM archivador", conn)['total'][0]
        st.metric("📂 DOCUMENTOS", f"{num_docs} Archivos")
        st.markdown('</div>', unsafe_allow_html=True)

# --- FINANZAS CON SEMÁFORO ---
elif menu == "💰 FINANZAS PRO":
    st.header("💰 Gestión de Presupuesto Real")
    
    # Configuración de Límite
    res_pre = pd.read_sql_query("SELECT monto_limite FROM presupuesto", conn)
    if res_pre.empty:
        limite = st.number_input("Establecer Presupuesto Mensual RD$:", value=15000.0)
        if st.button("CONFIGURAR LÍMITE"):
            c.execute("INSERT INTO presupuesto VALUES (?)", (limite,))
            conn.commit()
            st.rerun()
    else:
        limite = res_pre['monto_limite'][0]

    with st.form("registro_fin"):
        c1, c2, c3 = st.columns(3)
        t = c1.selectbox("Tipo", ["GASTO", "INGRESO"])
        cat = c2.selectbox("Categoría", ["Salud", "Comida", "Hogar", "Transporte", "Negocio"])
        m = c3.number_input("Monto RD$", min_value=0.0)
        if st.form_submit_button("💾 REGISTRAR"):
            m_final = m if t == "INGRESO" else -m
            c.execute("INSERT INTO finanzas (tipo, categoria, monto, fecha) VALUES (?,?,?,?)",
                      (t, cat, m_final, datetime.now(ZONA_HORARIA).strftime("%Y-%m-%d")))
            conn.commit()
            st.rerun()

    df_f = pd.read_sql_query("SELECT * FROM finanzas", conn)
    if not df_f.empty:
        total_gastos = abs(df_f[df_f['monto'] < 0]['monto'].sum())
        porcentaje = min(total_gastos / limite, 1.0)
        
        # Lógica de Semáforo
        color = "green" if porcentaje < 0.6 else "orange" if porcentaje < 0.9 else "red"
        st.markdown(f"### Presupuesto: <span style='color:{color}'>{total_gastos:,.2f} / {limite:,.2f} RD$</span>", unsafe_allow_html=True)
        st.progress(porcentaje)
        
        st.dataframe(df_f.tail(5), use_container_width=True)
        id_del = st.number_input("ID para borrar", min_value=1, step=1)
        if st.button("🗑️ ELIMINAR REGISTRO"):
            c.execute(f"DELETE FROM finanzas WHERE id = {id_del}")
            conn.commit()
            st.rerun()

# --- ESCÁNER INTELIGENTE (BARRAS Y QR) ---
elif menu == "📸 ESCÁNER IA":
    st.header("📸 Escáner de Códigos y Documentos")
    foto = st.camera_input("Enfoque el Código de Barras o QR")
    
    if foto:
        img = Image.open(foto)
        detectados = decode(img)
        if detectados:
            for d in detectados:
                contenido = d.data.decode('utf-8')
                st.success(f"✅ DETECTADO ({d.type}): {contenido}")
                if st.button("📥 ARCHIVAR ESTE DATO"):
                    c.execute("INSERT INTO archivador (nombre, categoria, contenido, fecha) VALUES (?,?,?,?)",
                              (f"Scan_{d.type}", "DIGITAL", contenido, datetime.now().strftime("%Y-%m-%d")))
                    conn.commit()
                    st.balloons()
        else:
            st.warning("No se detectó código legible.")

# --- ASISTENTE Y CONECTIVIDAD ---
elif menu == "🤖 ASISTENTE":
    st.header("🤖 Centro de Mando: Luis Rafael")
    col1, col2 = st.columns(2)
    with col1:
        st.link_button("🏥 RESULTADOS REFERENCIA", "https://www.referencia.do/")
    with col2:
        st.link_button("💬 WHATSAPP DOCTOR", "https://wa.me/18095551234?text=Hola%20necesito%20asistencia")
    
    st.divider()
    st.subheader("🔍 Buscador Universal")
    q = st.text_input("¿Qué buscas en el historial?")
    if q:
        # Busca en finanzas y archivador a la vez
        res_f = pd.read_sql_query(f"SELECT * FROM finanzas WHERE categoria LIKE '%{q}%' OR concepto LIKE '%{q}%'", conn)
        res_a = pd.read_sql_query(f"SELECT * FROM archivador WHERE contenido LIKE '%{q}%'", conn)
        if not res_f.empty: st.write("En Finanzas:", res_f)
        if not res_a.empty: st.write("En Archivador:", res_a)

# --- PIE DE PÁGINA ---
st.markdown(f"<br><hr><center>🚀 <b>SISTEMA QUEVEDO v3.0</b> | {datetime.now().year}</center>", unsafe_allow_html=True)
