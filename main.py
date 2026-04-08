import streamlit as st
import pandas as pd
import sqlite3
import os
import plotly.express as px
from fpdf import FPDF
from datetime import datetime
import pytz
from PIL import Image
import cv2
import numpy as np
import pytesseract
from pyzbar.pyzbar import decode

# ==========================================
# 1. CONFIGURACIÓN E IDENTIDAD
# ==========================================
st.set_page_config(page_title="SISTEMA QUEVEDO PRO", layout="wide", page_icon="💎")

NOMBRE_PROPIETARIO = "LUIS RAFAEL QUEVEDO"
ZONA_HORARIA = pytz.timezone('America/Santo_Domingo')

# ==========================================
# 2. BASE DE DATOS Y ESTRUCTURA
# ==========================================
def inicializar_todo():
    if not os.path.exists("archivador_quevedo"):
        os.makedirs("archivador_quevedo")
        for f in ["MEDICAL", "GASTOS", "PERSONALES", "RECETAS"]:
            os.makedirs(os.path.join("archivador_quevedo", f), exist_ok=True)
    
    conn = sqlite3.connect("sistema_quevedo_integral.db", check_same_thread=False)
    c = conn.cursor()
    # Tablas con ID autoincremental para poder borrar individualmente
    c.execute("CREATE TABLE IF NOT EXISTS glucosa (id INTEGER PRIMARY KEY AUTOINCREMENT, valor INTEGER, fecha TEXT, hora TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS citas (id INTEGER PRIMARY KEY AUTOINCREMENT, doctor TEXT, fecha TEXT, hora TEXT, centro TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS medicinas (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, dosis TEXT, frecuencia TEXT, hora_toma TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS finanzas (id INTEGER PRIMARY KEY AUTOINCREMENT, tipo TEXT, categoria TEXT, monto REAL, fecha TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS presupuesto (id INTEGER PRIMARY KEY, monto REAL)")
    c.execute("CREATE TABLE IF NOT EXISTS archivador_index (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, categoria TEXT, texto_ocr TEXT, fecha TEXT)")
    
    # Inicializar presupuesto si no existe
    c.execute("INSERT OR IGNORE INTO presupuesto (id, monto) VALUES (1, 0.0)")
    conn.commit()
    return conn, c

conn, c = inicializar_todo()

# ==========================================
# 3. DISEÑO VISUAL (CSS)
# ==========================================
st.markdown("""
    <style>
    .main { background-color: #0e1117; color: white; }
    .stButton>button { width: 100%; border-radius: 12px; background-color: #1b5e20; color: white; font-weight: bold; height: 3.5em; border: 1px solid #2e7d32; }
    .stButton>button:hover { background-color: #2e7d32; border-color: #4caf50; }
    .card { background: #1e2130; padding: 20px; border-radius: 15px; border-left: 8px solid #4CAF50; margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

# BARRA LATERAL
st.sidebar.title("💎 QUEVEDO INTEGRAL")
st.sidebar.write(f"👤 {NOMBRE_PROPIETARIO}")
menu = st.sidebar.radio("MENÚ PRINCIPAL", ["🏠 INICIO", "💰 FINANZAS PRO", "🩺 BIOMONITOR", "💊 AGENDA MÉDICA", "📸 ESCÁNER IA", "📂 ARCHIVADOR", "🤖 ASISTENTE"])

# ==========================================
# 4. LÓGICA DE MÓDULOS
# ==========================================

# --- INICIO ---
if menu == "🏠 INICIO":
    st.header(f"📊 Panel de Control: {NOMBRE_PROPIETARIO}")
    col1, col2, col3 = st.columns(3)
    
    df_f = pd.read_sql_query("SELECT SUM(monto) as total FROM finanzas", conn)
    df_g = pd.read_sql_query("SELECT valor FROM glucosa ORDER BY id DESC LIMIT 1", conn)
    presup_val = pd.read_sql_query("SELECT monto FROM presupuesto WHERE id=1", conn).iloc[0]['monto']

    with col1:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.metric("💰 BALANCE NETO", f"RD$ {df_f['total'][0] or 0:,.2f}")
        st.markdown('</div>', unsafe_allow_html=True)
    with col2:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.metric("🩺 ÚLTIMA GLUCOSA", f"{df_g['valor'][0] if not df_g.empty else 0} mg/dL")
        st.markdown('</div>', unsafe_allow_html=True)
    with col3:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.metric("📉 PRESUPUESTO", f"RD$ {presup_val:,.2f}")
        st.markdown('</div>', unsafe_allow_html=True)

# --- FINANZAS PRO (CON PRESUPUESTO Y BORRADO) ---
elif menu == "💰 FINANZAS PRO":
    st.header("💰 Gestión Financiera con Presupuesto")
    
    # Configurar Presupuesto
    with st.expander("⚙️ CONFIGURAR PRESUPUESTO MENSUAL"):
        nuevo_presup = st.number_input("Definir Presupuesto RD$", min_value=0.0, step=500.0)
        if st.button("ACTUALIZAR PRESUPUESTO"):
            c.execute("UPDATE presupuesto SET monto = ? WHERE id = 1", (nuevo_presup,))
            conn.commit()
            st.success("Presupuesto actualizado.")
            st.rerun()

    # Registro de Movimiento
    with st.form("registro_fin"):
        f1, f2, f3 = st.columns(3)
        t_mov = f1.selectbox("Tipo", ["GASTO", "INGRESO"])
        cat_mov = f2.selectbox("Categoría", ["Comida", "Salud", "Hogar", "Transporte", "Otros"])
        monto_mov = f3.number_input("Monto RD$", min_value=0.0)
        if st.form_submit_button("REGISTRAR"):
            final = monto_mov if t_mov == "INGRESO" else -monto_mov
            c.execute("INSERT INTO finanzas (tipo, categoria, monto, fecha) VALUES (?,?,?,?)",
                      (t_mov, cat_mov, final, datetime.now(ZONA_HORARIA).strftime("%d/%m/%y")))
            conn.commit()
            st.rerun()

    # Análisis de Presupuesto
    df_f = pd.read_sql_query("SELECT * FROM finanzas", conn)
    presup_actual = pd.read_sql_query("SELECT monto FROM presupuesto WHERE id=1", conn).iloc[0]['monto']
    
    if not df_f.empty:
        gastos_totales = abs(df_f[df_f['monto'] < 0]['monto'].sum())
        restante = presup_actual - gastos_totales
        
        st.subheader(f"Estado del Presupuesto: RD$ {restante:,.2f} restantes")
        progreso = min(gastos_totales / presup_actual, 1.0) if presup_actual > 0 else 0
        st.progress(progreso)
        
        if restante < 0: st.error(f"🚨 Te has excedido por RD$ {abs(restante):,.2f}")
        
        # Historial con botón de BORRAR
        st.divider()
        st.subheader("📋 Historial de Movimientos")
        for i, row in df_f.iterrows():
            col_d1, col_d2, col_d3 = st.columns([3, 1, 1])
            color = "🔴" if row['monto'] < 0 else "🟢"
            col_d1.write(f"{color} {row['fecha']} - {row['categoria']}: RD$ {abs(row['monto']):,.2f}")
            if col_d2.button("🗑️ Borrar", key=f"del_fin_{row['id']}"):
                c.execute("DELETE FROM finanzas WHERE id = ?", (row['id'],))
                conn.commit()
                st.rerun()

# --- ESCÁNER IA (QR, BARRA Y OCR) ---
elif menu == "📸 ESCÁNER IA":
    st.header("📸 Escáner de Documentos y Códigos")
    img_file = st.camera_input("Capturar")
    
    if img_file:
        img = Image.open(img_file)
        img_np = np.array(img.convert('RGB'))
        
        # 1. Lector de Códigos (QR / Barras)
        codigos = decode(img)
        if codigos:
            st.subheader("🏷️ Código Detectado")
            for obj in codigos:
                st.success(f"Tipo: {obj.type} | Datos: {obj.data.decode('utf-8')}")
        
        # 2. OCR (Texto)
        gray = cv2.cvtColor(img_np, cv2.COLOR_BGR2GRAY)
        texto = pytesseract.image_to_string(gray, lang='spa')
        st.text_area("Texto Extraído", texto, height=150)
        
        if st.button("💾 ARCHIVAR"):
            fname = f"SCAN_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
            path = os.path.join("archivador_quevedo", "MEDICAL", fname)
            img.save(path)
            c.execute("INSERT INTO archivador_index (nombre, categoria, texto_ocr, fecha) VALUES (?,?,?,?)",
                      (fname, "MEDICAL", texto, datetime.now().strftime("%d/%m/%y")))
            conn.commit()
            st.success("Guardado en Archivador.")

# --- BIOMONITOR ---
elif menu == "🩺 BIOMONITOR":
    st.header("🩺 Control de Glucosa")
    v_g = st.number_input("Nivel mg/dL", min_value=0)
    if st.button("GUARDAR"):
        ahora = datetime.now(ZONA_HORARIA)
        c.execute("INSERT INTO glucosa (valor, fecha, hora) VALUES (?,?,?)",
                  (v_g, ahora.strftime("%d/%m/%y"), ahora.strftime("%I:%M %p")))
        conn.commit()
        st.rerun()
    
    df_g = pd.read_sql_query("SELECT * FROM glucosa ORDER BY id DESC", conn)
    for i, r in df_g.iterrows():
        col_g1, col_g2 = st.columns([4, 1])
        col_g1.write(f"🩸 {r['valor']} mg/dL - {r['fecha']} {r['hora']}")
        if col_g2.button("🗑️", key=f"del_g_{r['id']}"):
            c.execute("DELETE FROM glucosa WHERE id = ?", (r['id'],))
            conn.commit()
            st.rerun()

# --- ASISTENTE Y CONECTIVIDAD ---
elif menu == "🤖 ASISTENTE":
    st.header("🤖 Centro de Mando e IA")
    
    # Enlaces Vivos
    st.subheader("📲 Conectividad Directa")
    cx1, cx2, cx3 = st.columns(3)
    cx1.link_button("💬 WHATSAPP", "https://wa.me/18090000000?text=Hola%20Luis%20Rafael")
    cx2.link_button("📧 GMAIL", "https://mail.google.com/mail/?view=cm&fs=1&to=tu_correo@gmail.com")
    cx3.link_button("🏥 REFERENCIA", "https://referencia.do")

    # Generar PDF
    st.divider()
    if st.button("📄 GENERAR REPORTE PDF MAESTRO"):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(200, 10, "SISTEMA QUEVEDO - REPORTE", ln=True, align='C')
        pdf.set_font("Arial", '', 12)
        pdf.cell(200, 10, f"Propietario: {NOMBRE_PROPIETARIO}", ln=True, align='C')
        pdf.output("Reporte_Quevedo.pdf")
        with open("Reporte_Quevedo.pdf", "rb") as f:
            st.download_button("📥 Descargar PDF", f, file_name="Reporte_Quevedo.pdf")

# Footer
st.sidebar.divider()
st.sidebar.caption(f"© 2026 Sistema Quevedo Pro | Santo Domingo")
