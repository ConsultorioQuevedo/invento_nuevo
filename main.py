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
import cv2
import pytesseract
from pyzbar.pyzbar import decode

# ==========================================
# 1. CONFIGURACIÓN E IDENTIDAD
# ==========================================
st.set_page_config(page_title="SISTEMA QUEVEDO PRO", layout="wide", page_icon="💎")

NOMBRE_PROPIETARIO = "LUIS RAFAEL QUEVEDO"
UBICACION_SISTEMA = "Santo Domingo, Rep. Dom."
ZONA_HORARIA = pytz.timezone('America/Santo_Domingo')

def limpiar_texto(texto):
    if not texto: return ""
    return "".join(c for c in unicodedata.normalize('NFD', str(texto)) if unicodedata.category(c) != 'Mn')

# ==========================================
# 2. BASE DE DATOS Y DIRECTORIOS
# ==========================================
def inicializar_todo():
    base = "archivador_quevedo"
    folders = ["MEDICAL", "GASTOS", "PERSONALES", "RECETAS_COCINA"]
    if not os.path.exists(base):
        os.makedirs(base)
    for f in folders:
        os.makedirs(os.path.join(base, f), exist_ok=True)
    
    db_conn = sqlite3.connect("sistema_quevedo_integral.db", check_same_thread=False)
    db_c = db_conn.cursor()
    
    # Tablas Integrales
    db_c.execute("CREATE TABLE IF NOT EXISTS glucosa (id INTEGER PRIMARY KEY AUTOINCREMENT, valor INTEGER, fecha TEXT, hora TEXT, estado TEXT)")
    db_c.execute("CREATE TABLE IF NOT EXISTS citas (id INTEGER PRIMARY KEY AUTOINCREMENT, doctor TEXT, fecha TEXT, hora TEXT, centro TEXT)")
    db_c.execute("CREATE TABLE IF NOT EXISTS medicinas (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, dosis INTEGER, frecuencia TEXT, hora_toma TEXT)")
    db_c.execute("CREATE TABLE IF NOT EXISTS archivador_index (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, categoria TEXT, texto_ocr TEXT, fecha TEXT)")
    db_c.execute("CREATE TABLE IF NOT EXISTS finanzas (id INTEGER PRIMARY KEY AUTOINCREMENT, tipo TEXT, categoria TEXT, monto REAL, fecha TEXT)")
    db_c.execute("CREATE TABLE IF NOT EXISTS presupuesto (id INTEGER PRIMARY KEY, monto REAL)")
    db_c.execute("INSERT OR IGNORE INTO presupuesto (id, monto) VALUES (1, 0.0)")
    
    db_conn.commit()
    return db_conn, db_c

conn, c = inicializar_todo()

# ==========================================
# 3. INTERFAZ Y ESTILOS
# ==========================================
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .stButton>button { width: 100%; border-radius: 12px; background-color: #1b5e20; color: white; font-weight: bold; height: 3em; }
    .resumen-card { background: linear-gradient(135deg, #1e2130 0%, #1b5e20 100%); padding: 20px; border-radius: 15px; border: 1px solid #4CAF50; text-align: center; margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

# Navegación Sidebar
st.sidebar.title("💎 QUEVEDO INTEGRAL")
menu = st.sidebar.radio("MODULOS PRINCIPALES", 
    ["🏠 INICIO", "💰 FINANZAS", "🩺 BIOMONITOR", "💊 AGENDA MÉDICA", "📸 ESCÁNER IA", "📂 ARCHIVADOR", "🤖 ASISTENTE"])

# ==========================================
# 4. LÓGICA DE MÓDULOS
# ==========================================

# --- INICIO ---
if menu == "🏠 INICIO":
    st.header(f"📊 Panel de Control: {NOMBRE_PROPIETARIO}")
    c1, c2, c3 = st.columns(3)
    
    try:
        df_fin = pd.read_sql_query("SELECT SUM(monto) as total FROM finanzas", conn)
        df_glu = pd.read_sql_query("SELECT valor FROM glucosa ORDER BY id DESC LIMIT 1", conn)
        
        with c1:
            st.markdown('<div class="resumen-card">', unsafe_allow_html=True)
            st.metric("💰 BALANCE TOTAL", f"RD$ {df_fin['total'][0] or 0:,.2f}")
            st.markdown('</div>', unsafe_allow_html=True)
        with c2:
            st.markdown('<div class="resumen-card">', unsafe_allow_html=True)
            st.metric("🩺 ÚLTIMA GLUCOSA", f"{df_glu['valor'][0] if not df_glu.empty else '0'} mg/dL")
            st.markdown('</div>', unsafe_allow_html=True)
        with c3:
            st.markdown('<div class="resumen-card">', unsafe_allow_html=True)
            st.metric("📅 ESTADO", "OPERATIVO")
            st.markdown('</div>', unsafe_allow_html=True)
    except:
        st.warning("Inicializando datos...")

    st.divider()
    st.subheader("📲 Acceso Rápido")
    col_link1, col_link2, col_link3 = st.columns(3)
    col_link1.link_button("💬 WHATSAPP", "https://wa.me/tu_numero")
    col_link2.link_button("📧 GMAIL", "mailto:tu_correo@gmail.com")
    col_link3.link_button("🏥 CLINICA", "https://referencia.do")

# --- FINANZAS ROBUSTO ---
elif menu == "💰 FINANZAS":
    st.header("💰 Gestión Financiera Inteligente")
    
    # Configuración de Presupuesto
    with st.expander("⚙️ AJUSTAR PRESUPUESTO"):
        p_input = st.number_input("Presupuesto Mensual RD$", min_value=0.0)
        if st.button("Guardar Presupuesto"):
            c.execute("UPDATE presupuesto SET monto = ? WHERE id = 1", (p_input,))
            conn.commit()
            st.success("Presupuesto actualizado.")

    with st.form("form_finanzas", clear_on_submit=True):
        col_f1, col_f2, col_f3 = st.columns(3)
        tipo = col_f1.selectbox("Tipo", ["GASTO", "INGRESO"])
        cat = col_f2.selectbox("Categoría", ["Comida", "Salud", "Hogar", "Transporte", "Negocio", "Otros"])
        monto = col_f3.number_input("Monto RD$", min_value=0.0)
        if st.form_submit_button("🚀 REGISTRAR"):
            monto_final = monto if tipo == "INGRESO" else -monto
            c.execute("INSERT INTO finanzas (tipo, categoria, monto, fecha) VALUES (?,?,?,?)",
                      (tipo, cat, monto_final, datetime.now(ZONA_HORARIA).strftime("%d/%m/%y")))
            conn.commit()
            st.rerun()

    df_f = pd.read_sql_query("SELECT * FROM finanzas", conn)
    pres_val = pd.read_sql_query("SELECT monto FROM presupuesto WHERE id = 1", conn)['monto'][0]

    if not df_f.empty:
        ingresos = df_f[df_f['monto'] > 0]['monto'].sum()
        gastos = abs(df_f[df_f['monto'] < 0]['monto'].sum())
        balance = ingresos - gastos
        
        m1, m2, m3 = st.columns(3)
        m1.metric("📥 INGRESOS", f"RD$ {ingresos:,.2f}")
        m2.metric("📤 GASTOS", f"RD$ {gastos:,.2f}", delta_color="inverse")
        m3.metric("💎 BALANCE", f"RD$ {balance:,.2f}")

        if pres_val > 0:
            ratio = (gastos / pres_val) * 100
            if ratio > 80: st.error(f"⚠️ Alerta: Has usado el {ratio:.1f}% de tu presupuesto.")
        
        # Tabla con BOTÓN DE BORRADO individual
        st.subheader("Historial de Movimientos")
        for idx, row in df_f.iterrows():
            col_r1, col_r2, col_r3, col_r4 = st.columns([2,2,2,1])
            col_r1.write(row['fecha'])
            col_r2.write(row['categoria'])
            col_r3.write(f"RD$ {row['monto']:,.2f}")
            if col_r4.button("🗑️", key=f"del_f_{row['id']}"):
                c.execute("DELETE FROM finanzas WHERE id = ?", (row['id'],))
                conn.commit()
                st.rerun()

# --- BIOMONITOR ---
elif menu == "🩺 BIOMONITOR":
    st.header("🩺 Control Biométrico")
    col_g1, col_g2 = st.columns([1, 2])
    with col_g1:
        val_g = st.number_input("Nivel de Glucosa (mg/dL)", min_value=0, step=1)
        if st.button("💾 GUARDAR MEDICIÓN"):
            ahora = datetime.now(ZONA_HORARIA)
            c.execute("INSERT INTO glucosa (valor, fecha, hora, estado) VALUES (?,?,?,?)", 
                      (val_g, ahora.strftime("%d/%m/%y"), ahora.strftime("%I:%M %p"), "REGISTRADO"))
            conn.commit()
            st.rerun()
    with col_g2:
        df_hist = pd.read_sql_query("SELECT * FROM glucosa ORDER BY id DESC LIMIT 10", conn)
        if not df_hist.empty:
            fig = px.line(df_hist, x="fecha", y="valor", title="Tendencia de Glucosa", markers=True)
            st.plotly_chart(fig, use_container_width=True)
            for idx, row in df_hist.iterrows():
                col_b1, col_b2, col_b3 = st.columns([3,3,1])
                col_b1.write(f"{row['fecha']} - {row['hora']}")
                col_b2.write(f"{row['valor']} mg/dL")
                if col_b3.button("🗑️", key=f"del_g_{row['id']}"):
                    c.execute("DELETE FROM glucosa WHERE id = ?", (row['id'],))
                    conn.commit()
                    st.rerun()

# --- AGENDA MÉDICA ---
elif menu == "💊 AGENDA MÉDICA":
    st.header("📅 Agenda Médica y Control de Fármacos")
    tab1, tab2 = st.tabs(["📝 CITAS MÉDICAS", "💊 MEDICAMENTOS"])

    with tab1:
        with st.form("form_citas", clear_on_submit=True):
            c_doc = st.text_input("Doctor/Especialidad")
            c_fec = st.date_input("Fecha")
            c_hor = st.time_input("Hora")
            c_cen = st.text_input("Centro Médico")
            if st.form_submit_button("💾 AGENDAR"):
                c.execute("INSERT INTO citas (doctor, fecha, hora, centro) VALUES (?,?,?,?)",
                          (c_doc, str(c_fec), c_hor.strftime("%I:%M %p"), c_cen))
                conn.commit()
                st.rerun()
        
        df_c = pd.read_sql_query("SELECT * FROM citas ORDER BY fecha ASC", conn)
        for idx, row in df_c.iterrows():
            with st.container():
                col_c1, col_c2, col_c3 = st.columns([4,4,1])
                col_c1.write(f"**{row['doctor']}** - {row['fecha']}")
                col_c2.write(f"{row['centro']} ({row['hora']})")
                if col_c3.button("🗑️", key=f"del_c_{row['id']}"):
                    c.execute("DELETE FROM citas WHERE id = ?", (row['id'],))
                    conn.commit()
                    st.rerun()

    with tab2:
        with st.form("form_meds", clear_on_submit=True):
            m_nom = st.text_input("Medicamento")
            m_dos = st.number_input("Dosis", min_value=0)
            m_fre = st.selectbox("Frecuencia", ["4h", "6h", "8h", "12h", "1 día"])
            if st.form_submit_button("💾 GUARDAR"):
                c.execute("INSERT INTO medicinas (nombre, dosis, frecuencia) VALUES (?,?,?)", (m_nom, m_dos, m_fre))
                conn.commit()
                st.rerun()
        
        df_m = pd.read_sql_query("SELECT * FROM medicinas", conn)
        for idx, row in df_m.iterrows():
            col_m1, col_m2, col_m3 = st.columns([4,4,1])
            col_m1.write(f"💊 {row['nombre']}")
            col_m2.write(f"{row['dosis']} mg - {row['frecuencia']}")
            if col_m3.button("🗑️", key=f"del_m_{row['id']}"):
                c.execute("DELETE FROM medicinas WHERE id = ?", (row['id'],))
                conn.commit()
                st.rerun()

# --- ESCÁNER IA ---
elif menu == "📸 ESCÁNER IA":
    st.header("📸 Estación de Escaneo Profesional")
    img_file = st.camera_input("Capturar Documento, QR o Barras")
    if img_file:
        img = Image.open(img_file)
        img_np = np.array(img.convert('RGB'))
        
        # 1. QR/BARRAS
        codigos = decode(img)
        if codigos:
            for obj in codigos:
                st.success(f"Código {obj.type}: {obj.data.decode('utf-8')}")
        
        # 2. OCR
        with st.spinner("🤖 IA Analizando texto..."):
            gray = cv2.cvtColor(img_np, cv2.COLOR_BGR2GRAY)
            texto_ocr = pytesseract.image_to_string(gray, lang='spa')
            st.text_area("Texto Detectado", texto_ocr, height=150)
            
            cat_save = st.selectbox("Archivar en:", ["MEDICAL", "GASTOS", "PERSONALES"])
            if st.button("💾 GUARDAR EN ARCHIVADOR"):
                fname = f"SCAN_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                path = os.path.join("archivador_quevedo", cat_save, fname)
                img.save(path)
                c.execute("INSERT INTO archivador_index (nombre, categoria, texto_ocr, fecha) VALUES (?,?,?,?)",
                          (fname, cat_save, texto_ocr, datetime.now().strftime("%d/%m/%y")))
                conn.commit()
                st.success("Guardado y indexado.")

# --- ARCHIVADOR INTEGRAL (BÚSQUEDA MULTI-MÓDULO) ---
elif menu == "📂 ARCHIVADOR":
    st.header("📂 Archivador Inteligente v3.0")
    
    # 1. Entrada de búsqueda flexible
    q = st.text_input("🔍 Busca lo que sea (ej: 'glucosa', 'operación', 'gasto', 'doctor')...")
    
    if q:
        query = f"%{q.lower()}%"
        st.markdown(f"### 🔎 Resultados de búsqueda para: **{q}**")
        
        # --- COLUMNAS PARA ORGANIZAR RESULTADOS ---
        col_res_izq, col_res_der = st.columns(2)

        # 2. BÚSQUEDA EN SALUD (Biomonitor y Agenda)
        with col_res_izq:
            # Buscar en Medicamentos y Citas Médicas
            res_salud = pd.read_sql_query("""
                SELECT 'Medicamento' as Origen, nombre as Detalle, frecuencia as Info FROM medicinas 
                WHERE lower(nombre) LIKE ? 
                UNION
                SELECT 'Cita Médica' as Origen, doctor as Detalle, centro as Info FROM citas 
                WHERE lower(doctor) LIKE ? OR lower(centro) LIKE ?
            """, conn, params=(query, query, query))
            
            # Buscar en Biomonitor (Glucosa)
            res_bio = pd.read_sql_query("""
                SELECT 'Biomonitor' as Origen, valor || ' mg/dL' as Detalle, fecha as Info FROM glucosa 
                WHERE lower(estado) LIKE ? OR lower(fecha) LIKE ?
            """, conn, params=(query, query))

            if not res_salud.empty or not res_bio.empty:
                st.success("🩺 Hallazgos en Salud y Agenda")
                if not res_salud.empty: st.table(res_salud)
                if not res_bio.empty: st.table(res_bio)

        # 3. BÚSQUEDA EN DOCUMENTOS Y FINANZAS
        with col_res_der:
            # Buscar en el Archivador de Fotos/Documentos
            res_docs = pd.read_sql_query("""
                SELECT 'Documento' as Origen, nombre as Detalle, categoria as Info FROM archivador_index 
                WHERE lower(texto_ocr) LIKE ? OR lower(categoria) LIKE ?
            """, conn, params=(query, query))
            
            # Buscar en Finanzas
            res_fin = pd.read_sql_query("""
                SELECT 'Finanzas' as Origen, categoria as Detalle, 'RD$ ' || monto as Info FROM finanzas 
                WHERE lower(categoria) LIKE ? OR lower(tipo) LIKE ?
            """, conn, params=(query, query))

            if not res_docs.empty or not res_fin.empty:
                st.warning("📂 Hallazgos en Documentos y Gastos")
                if not res_docs.empty: st.table(res_docs)
                if not res_fin.empty: st.table(res_fin)

        if res_salud.empty and res_bio.empty and res_docs.empty and res_fin.empty:
            st.error(f"No se encontró rastro de '{q}' en ningún módulo.")

    st.divider()

    # --- 4. TU DISEÑO DE CARPETAS (SE MANTIENE IGUAL) ---
    st.subheader("📁 Carpetas del Archivador")
    for cat in ["MEDICAL", "GASTOS", "PERSONALES", "RECETAS_COCINA"]:
        with st.expander(f"📁 {cat}"):
            df_arch = pd.read_sql_query(f"SELECT * FROM archivador_index WHERE categoria = '{cat}'", conn)
            if df_arch.empty:
                st.info("No hay documentos aquí.")
            else:
                for idx, row in df_arch.iterrows():
                    c1, c2, c3 = st.columns([5, 2, 1])
                    c1.write(f"📄 {row['nombre']}")
                    c2.caption(f"📅 {row['fecha']}")
                    if c3.button("🗑️", key=f"del_final_{row['id']}"):
                        c.execute("DELETE FROM archivador_index WHERE id = ?", (row['id'],))
                        conn.commit()
                        st.rerun()


# --- ASISTENTE Y PDF ---
elif menu == "🤖 ASISTENTE":
    st.header("👋 Centro de Mando: Luis Rafael")
    if st.button("🚀 GENERAR REPORTE PDF TIMBRADO"):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(200, 10, "SISTEMA QUEVEDO INTEGRAL - REPORTE OFICIAL", ln=True, align='C')
        pdf.set_font("Arial", 'I', 11)
        pdf.cell(200, 10, f"Propietario: {NOMBRE_PROPIETARIO} | {datetime.now().strftime('%d/%m/%Y')}", ln=True, align='C')
        pdf.line(10, 35, 200, 35)
        pdf.ln(10)
        
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(200, 10, "RESUMEN DE FINANZAS:", ln=True)
        pdf.set_font("Arial", '', 10)
        df_pdf = pd.read_sql_query("SELECT * FROM finanzas", conn)
        for _, r in df_pdf.iterrows():
            pdf.cell(200, 7, f"- {r['fecha']} | {r['categoria']} | RD$ {r['monto']}", ln=True)
            
        pdf.output("Reporte_Quevedo.pdf")
        with open("Reporte_Quevedo.pdf", "rb") as f:
            st.download_button("📥 DESCARGAR REPORTE", f, file_name="Reporte_Quevedo.pdf")
