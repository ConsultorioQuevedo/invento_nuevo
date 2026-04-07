import streamlit as st
import pandas as pd
import sqlite3
import os
from datetime import datetime
import pytz
from PIL import Image
import unicodedata
from fpdf import FPDF

# 1. ARRANQUE DIRECTO
st.set_page_config(page_title="SISTEMA QUEVEDO PRO", layout="wide", page_icon="💎")

# BYPASS DE SEGURIDAD (Entrada libre para Luis)
if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = True

# 2. LA ZAPATA (Base de Datos y Carpetas)
if not os.path.exists("archivador_quevedo"):
    os.makedirs("archivador_quevedo")
    for folder in ["MEDICAL", "GASTOS", "PERSONALES", "RECETAS"]:
        os.makedirs(os.path.join("archivador_quevedo", folder), exist_ok=True)

conn = sqlite3.connect("sistema_quevedo_integral.db", check_same_thread=False)
c = conn.cursor()

# Creación de tablas inteligentes
tablas = [
    "glucosa (id INTEGER PRIMARY KEY, valor INTEGER, fecha TEXT, hora TEXT, estado TEXT)",
    "finanzas (id INTEGER PRIMARY KEY, tipo TEXT, categoria TEXT, monto REAL, fecha TEXT)",
    "citas (id INTEGER PRIMARY KEY, doctor TEXT, fecha TEXT, hora TEXT, centro TEXT)",
    "medicinas (id INTEGER PRIMARY KEY, nombre TEXT, dosis TEXT, frecuencia TEXT, hora_toma TEXT)",
    "archivador_index (id INTEGER PRIMARY KEY, nombre TEXT, categoria TEXT, texto_ocr TEXT, fecha TEXT)"
]
for t in tablas:
    c.execute(f"CREATE TABLE IF NOT EXISTS {t}")
conn.commit()

if menu == "🏠 INICIO":
    st.header("🏠 Panel de Control - Luis Rafael Quevedo")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("🩺 Salud")
        ult_g = pd.read_sql_query("SELECT valor FROM glucosa ORDER BY id DESC LIMIT 1", conn)
        if not ult_g.empty:
            st.metric("Última Glucosa", f"{ult_g['valor'][0]} mg/dL")
        else:
            st.write("Sin datos")
        st.markdown('</div>', unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("💰 Finanzas")
        total_f = pd.read_sql_query("SELECT SUM(monto) as total FROM finanzas", conn)
        monto = total_f['total'][0] if total_f['total'][0] else 0
        st.metric("Total Gastos", f"RD$ {monto:,.2f}")
        st.markdown('</div>', unsafe_allow_html=True)

    with col3:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("📅 Citas")
        prox_c = pd.read_sql_query("SELECT doctor, fecha FROM citas ORDER BY id DESC LIMIT 1", conn)
        if not prox_c.empty:
            st.write(f"{prox_c['doctor'][0]}")
            st.caption(f"Fecha: {prox_c['fecha'][0]}")
        else:
            st.write("No hay citas")
        st.markdown('</div>', unsafe_allow_html=True)
