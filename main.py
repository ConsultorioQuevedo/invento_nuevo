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
    
    # 1. MÉTRICAS RÁPIDAS (Tarjetas de arriba)
    col_salud, col_dinero, col_citas = st.columns(3)
    
    # Consultar último valor de glucosa
    ult_g = pd.read_sql_query("SELECT valor, estado FROM glucosa ORDER BY id DESC LIMIT 1", conn)
    with col_salud:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("🩺 Última Glucosa")
        if not ult_g.empty:
            valor = ult_g['valor'][0]
            estado = ult_g['estado'][0]
            st.metric(label="Nivel mg/dL", value=valor, delta=estado)
        else:
            st.write("Sin datos todavía")
        st.markdown('</div>', unsafe_allow_html=True)

    # Consultar total de gastos
    total_f = pd.read_sql_query("SELECT SUM(monto) as total FROM finanzas", conn)
    with col_dinero:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("💰 Gastos Totales")
        monto_total = total_f['total'][0] if total_f['total'][0] else 0
        st.metric(label="Total RD$", value=f"{monto_total:,.2f}")
        st.markdown('</div>', unsafe_allow_html=True)

    # Consultar próxima cita
    prox_cita = pd.read_sql_query("SELECT doctor, fecha FROM citas ORDER BY id DESC LIMIT 1", conn)
    with col_citas:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("📅 Próxima Cita")
        if not prox_cita.empty:
            st.write(f"**{prox_cita['doctor'][0]}**")
            st.write(f"Fecha: {prox_cita['fecha'][0]}")
        else:
            st.write("No hay citas agendadas")
        st.markdown('</div>', unsafe_allow_html=True)

    # 2. ACCESOS DIRECTOS (Botones grandes)
    st.divider()
    st.subheader("🚀 Acceso Rápido")
    c1, c2, c3 = st.columns(3)
    if c1.button("📸 ESCANEAR DOCUMENTO"):
        st.info("Ve al módulo ESCANER en el menú")
    if c2.button("💊 REGISTRAR MEDICINA"):
        st.info("Ve al módulo AGENDA MÉDICA")
    if c3.button("🤖 HABLAR CON IA"):
        st.info("Ve al módulo ASISTENTE")

