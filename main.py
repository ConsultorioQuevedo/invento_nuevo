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
# 1. CONFIGURACIÓN E INTERFAZ DE ALTO NIVEL
st.set_page_config(page_title="SISTEMA QUEVEDO PRO", layout="wide", page_icon="💎")
# --- CONFIGURACIÓN DE IDENTIDAD MAESTRA ---
NOMBRE_PROPIETARIO = "LUIS RAFAEL QUEVEDO"
UBICACION_SISTEMA = "Santo Domingo, Rep. Dom."

# Función para limpiar acentos y evitar errores en el PDF (Seguro de caracteres)
def limpiar_texto(texto):
    if not texto: return ""
    return "".join(c for c in unicodedata.normalize('NFD', str(texto)) if unicodedata.category(c) != 'Mn')

# --- SISTEMA DE SEGURIDAD (LOGIN) ---
def verificar_acceso():
    if "autenticado" not in st.session_state:
        st.session_state["autenticado"] = False

    if not st.session_state["autenticado"]:
        st.markdown("<h1 style='text-align: center; color: #4CAF50;'>💎 SISTEMA QUEVEDO</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center;'>🔐 Acceso Privado - Luis Rafael Quevedo</p>", unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns([1,2,1])
        with col2:
            u = st.text_input("Usuario")
            p = st.text_input("Contraseña", type="password")
            if st.button("DESBLOQUEAR SISTEMA"):
                if u == "Amin" and p == "1234":
                    st.session_state["autenticado"] = True
                    st.rerun()
                else:
                    st.error("❌ Credenciales incorrectas")
        return False
    return True

if verificar_acceso():
    # Directorios y Base de Datos
    if not os.path.exists("archivador_quevedo"):
        os.makedirs("archivador_quevedo")

    def iniciar_db():
        conn = sqlite3.connect("sistema_quevedo_integral.db", check_same_thread=False)
        c = conn.cursor()
        c.execute('CREATE TABLE IF NOT EXISTS finanzas (id INTEGER PRIMARY KEY AUTOINCREMENT, tipo TEXT, categoria TEXT, monto REAL, fecha TEXT)')
        c.execute('CREATE TABLE IF NOT EXISTS presupuesto (id INTEGER PRIMARY KEY AUTOINCREMENT, limite REAL)')
        c.execute('CREATE TABLE IF NOT EXISTS glucosa (id INTEGER PRIMARY KEY AUTOINCREMENT, valor INTEGER, fecha TEXT, hora TEXT, estado TEXT)')
        c.execute('CREATE TABLE IF NOT EXISTS medicinas (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, horario TEXT)')
        c.execute('CREATE TABLE IF NOT EXISTS citas (id INTEGER PRIMARY KEY AUTOINCREMENT, doctor TEXT, fecha TEXT, hora TEXT)')
        conn.commit()
        return conn

    conn = iniciar_db()
    c = conn.cursor()

    # --- FUNCIÓN: GENERADOR REPORTE MAESTRO PDF (VERSIÓN ANTIBALAS) ---
    def generar_reporte_maestro_pdf():
        try:
            pdf = FPDF()
            pdf.add_page()
            # Cambiamos a Courier para mayor compatibilidad en la Nube
            pdf.set_font("Courier", 'B', 16)
            
            titulo = limpiar_texto("REPORTE MAESTRO - SISTEMA QUEVEDO")
            pdf.cell(0, 10, titulo, ln=True, align='C')
            pdf.ln(5)

            def agregar_seccion(titulo_sec, query, columnas):
                pdf.set_font("Courier", 'B', 12)
                pdf.set_fill_color(200, 200, 200)
                pdf.cell(0, 10, limpiar_texto(titulo_sec), ln=True, fill=True)
                pdf.ln(2)
                
                try:
                    df = pd.read_sql_query(query, conn)
                    if not df.empty:
                        pdf.set_font("Courier", 'B', 10)
                        # Cabeceras
                        for col in columnas:
                            pdf.cell(47, 8, limpiar_texto(col), 1)
                        pdf.ln()
                        # Datos: Forzamos el encode aquí mismo
                        pdf.set_font("Courier", size=9)
                        for _, row in df.iterrows():
                            for val in row:
                                # LA CLAVE: Limpiamos y forzamos el string
                                texto_celda = limpiar_texto(str(val))
                                pdf.cell(47, 7, texto_celda, 1)
                            pdf.ln()
                    else:
                        pdf.cell(0, 8, "Sin datos.", ln=True)
                except:
                    pdf.cell(0, 8, "Error en seccion.", ln=True)
                pdf.ln(5)

            # 1. Finanzas
            df_f = pd.read_sql_query("SELECT SUM(monto) as bal FROM finanzas", conn)
            bal = df_f['bal'].iloc[0] if df_f['bal'].iloc[0] else 0.0
            pdf.set_font("Courier", 'B', 11)
            pdf.cell(0, 10, f"BALANCE TOTAL: RD$ {bal:,.2f}", ln=True)
            
            agregar_seccion("FINANZAS", "SELECT fecha, categoria, monto FROM finanzas ORDER BY id DESC LIMIT 10", ["Fecha", "Concepto", "Monto"])
            agregar_seccion("GLUCOSA", "SELECT fecha, hora, valor, estado FROM glucosa ORDER BY id DESC LIMIT 10", ["Fecha", "Hora", "Valor", "Estado"])
            agregar_seccion("MEDICINAS", "SELECT nombre, horario FROM medicinas", ["Medicina", "Horario"])
            agregar_seccion("CITAS", "SELECT doctor, fecha FROM citas", ["Doctor", "Fecha"])

            # Cerramos el PDF internamente antes de pedir el output
            pdf.close()
            # El secreto: output() sin parámetros para obtener el string y luego codificar
            cuerpo_pdf = pdf.output(dest='S')
            return cuerpo_pdf.encode('latin-1', 'replace')
            
        except Exception as e:
            st.error(f"Error interno del PDF: {e}")
            return None
    
    # --- FUNCIÓN GENERAR PDF SALUD ---
    def generar_pdf_salud(df_g, df_m):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(200, 10, limpiar_texto("REPORTE MEDICO - LUIS RAFAEL QUEVEDO"), ln=True, align='C')
        pdf.ln(10)
        pdf.set_font("Arial", 'B', 12); pdf.cell(200, 10, "1. MEDICAMENTOS ACTIVOS:"); pdf.ln()
        pdf.set_font("Arial", size=10)
        for _, r in df_m.iterrows():
            pdf.cell(200, 8, limpiar_texto(f"- {r['nombre']} ({r['horario']})"), ln=True)
        pdf.ln(5); pdf.set_font("Arial", 'B', 12); pdf.cell(200, 10, "2. GLUCOSA:"); pdf.ln()
        for _, r in df_g.tail(10).iterrows():
            pdf.cell(200, 8, f"{r['fecha']} {r['hora']}: {r['valor']} mg/dL", ln=True)
        nombre = f"Salud_{datetime.now().strftime('%Y%m%d')}.pdf"
        pdf.output(os.path.join("archivador_quevedo", nombre))
        return nombre

    # DISEÑO VISUAL CSS
    st.markdown("""
        <style>
        .main { background-color: #0e1117; }
        .stButton>button { width: 100%; border-radius: 12px; background-color: #1b5e20; color: white; height: 3.5em; font-weight: bold; }
        .resumen-card { background: linear-gradient(135deg, #1e2130 0%, #1b5e20 100%); padding: 15px; border-radius: 15px; border: 1px solid #4CAF50; text-align: center; }
        .semaforo-rojo { background-color: #c62828; padding: 20px; border-radius: 15px; color: white; animation: pulse 2s infinite; text-align: center; border: 2px solid white; }
        @keyframes pulse { 0% {box-shadow: 0 0 0 0px rgba(198, 40, 40, 0.7);} 70% {box-shadow: 0 0 0 20px rgba(198, 40, 40, 0);} 100% {box-shadow: 0 0 0 0px rgba(198, 40, 40, 0);} }
        </style>
        """, unsafe_allow_html=True)

    contactos_data = {"Nombre": ["Mi Hijo", "Mi Hija", "Franklin", "Hermanito", "Dorka", "Rosa", "Pedro"],
                      "Telefono": ["18292061693", "18292581449", "16463746377", "14077975432", "18298811692", "18293800425", "18097100995"]}

    # NAVEGACIÓN
    st.sidebar.title("💎 SISTEMA QUEVEDO")
    
    # MEJORA: RECORDATORIO DE CITAS EN SIDEBAR
    df_c_prox = pd.read_sql_query("SELECT doctor, fecha FROM citas ORDER BY fecha ASC LIMIT 1", conn)
    if not df_c_prox.empty:
        st.sidebar.warning(f"🔔 PRÓXIMA CITA:\n{df_c_prox['doctor'][0]} - {df_c_prox['fecha'][0]}")

    with st.sidebar:
        st.subheader("🚀 Reportes Globales")
        if st.button("📊 GENERAR REPORTE MAESTRO"):
            pdf_data = generar_reporte_maestro_pdf()
            st.download_button("📥 Descargar Reporte", pdf_data, f"MAESTRO_{datetime.now().strftime('%Y%m%d')}.pdf", "application/pdf")
        st.divider()

    menu = st.sidebar.radio("MODULOS", ["🏠 INICIO (RESUMEN)", "💰 FINANZAS IA", "🩺 BIOMONITOR", "💊 AGENDA MEDICA", "📸 ESCANER", "📂 ARCHIVADOR", "🤖 ASISTENTE"])
if st.button("BORRAR TODO EL HISTORIAL DE GLUCOSA"):
                    conn.execute("DELETE FROM glucosa")
                    conn.commit()
                    st.rerun()

        # =========================================================
        # --- MÓDULO 4: AGENDA MÉDICA (RECONECTADO) ---
        # =========================================================
        elif menu == "💊 AGENDA MEDICA":
            st.header("💊 Gestión Médica Profesional")
            tab1, tab2 = st.tabs(["📋 Inventario de Medicinas", "📅 Control de Citas"])

            with tab1:
                st.subheader("🚀 Control de Inventario y Dosis")
                with st.expander("➕ Registrar Nuevo Medicamento", expanded=False):
                    with st.form("form_med_pro", clear_on_submit=True):
                        col_n1, col_n2 = st.columns(2)
                        nombre_m = col_n1.text_input("Nombre del Medicamento")
                        horario_m = col_n2.text_input("Horario / Frecuencia")
                        if st.form_submit_button("💎 GUARDAR EN INVENTARIO"):
                            if nombre_m and horario_m:
                                c.execute("INSERT INTO medicinas (nombre, horario) VALUES (?, ?)", (nombre_m, horario_m))
                                conn.commit()
                                st.success(f"✅ {nombre_m} añadido.")
                                st.rerun()

                df_meds = pd.read_sql_query("SELECT * FROM medicinas", conn)
                if not df_meds.empty:
                    for _, row in df_meds.iterrows():
                        with st.container(border=True):
                            c1, c2, c3 = st.columns([3, 2, 1])
                            c1.markdown(f"**Medicamento:** {row['nombre']}")
                            c2.info(f"⏰ {row['horario']}")
                            if c3.button("🗑️", key=f"del_m_{row['id']}"):
                                c.execute("DELETE FROM medicinas WHERE id=?", (row['id'],))
                                conn.commit()
                                st.rerun()

            with tab2:
                st.subheader("📅 Agenda de Consultas")
                with st.form("form_citas_pro"):
                    doc_esp = st.text_input("Doctor o Especialidad")
                    fecha_c = st.date_input("Fecha de la Cita")
                    if st.form_submit_button("📅 AGENDAR CITA MÉDICA"):
                        if doc_esp:
                            c.execute("INSERT INTO citas (doctor, fecha) VALUES (?, ?)", (doc_esp, str(fecha_c)))
                            conn.commit()
                            st.success("✅ Cita agendada.")
                            st.rerun()

        # =========================================================
        # --- MÓDULO 5: ESCÁNER INTELIGENTE ---
        # =========================================================
        elif menu == "📸 ESCANER":
            st.header("📸 Escáner de Visión Artificial")
            from pyzbar.pyzbar import decode
            img_file = st.file_uploader("📷 Subir Imagen", type=['jpg', 'png', 'jpeg'])
            if img_file:
                img = Image.open(img_file)
                st.image(img, width=400)
                datos_detectados = decode(img)
                if datos_detectados:
                    for i, d in enumerate(datos_detectados):
                        codigo_leido = d.data.decode('utf-8')
                        st.success(f"✅ Detectado: {codigo_leido}")
                        if st.button(f"💾 REGISTRAR: {codigo_leido[:10]}", key=f"sc_{i}"):
                            c.execute("INSERT INTO medicinas (nombre, horario) VALUES (?, ?)", (f"SCAN: {codigo_leido}", "Pendiente"))
                            conn.commit()
                            st.rerun()
                else:
                    st.warning("No se detectó código. Mejore la iluminación.")

        # =========================================================
        # --- MÓDULO 6: ARCHIVADOR ---
        # =========================================================
        elif menu == "📂 ARCHIVADOR":
            st.header("📂 Archivador Digital Quevedo")
            archivos = os.listdir("archivador_quevedo")
            if archivos:
                for arc in archivos:
                    with st.expander(f"📄 {arc}"):
                        if st.button("🗑️ ELIMINAR", key=f"del_file_{arc}"):
                            os.remove(os.path.join("archivador_quevedo", arc))
                            st.rerun()
            else:
                st.info("El archivador está vacío.")

        # =========================================================
        # --- MÓDULO 7: ASISTENTE (IA) ---
        # =========================================================
        elif menu == "🤖 ASISTENTE":
            st.header("🤖 Centro de Control Quevedo Pro")
            col_as1, col_as2 = st.columns(2)
            with col_as1:
                st.subheader("🌐 Nube")
                try:
                    conn_gs = st.connection("gsheets", type=GSheetsConnection)
                    st.success("✅ Sincronizado")
                except:
                    st.error("⚠️ Modo Local")
            with col_as2:
                st.subheader("📲 WhatsApp")
                if st.button("💊 COTIZAR MEDICINAS"):
                    st.info("Generando link para Farmacia GBC...")

# --- FINAL DEL SISTEMA (ESTO VA PEGADO AL BORDE IZQUIERDO) ---
st.markdown("---")
st.markdown(f"<div style='text-align: center;'>💎 {NOMBRE_PROPIETARIO} | v2.5</div>", unsafe_allow_html=True)

