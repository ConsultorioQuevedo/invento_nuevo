import streamlit as st
import pandas as pd
import sqlite3
import os
import plotly.express as px
from fpdf import FPDF
from datetime import datetime
import pytz
import numpy as np
from sklearn.linear_model import LinearRegression
import unicodedata
from PIL import Image
import io

# 1. CONFIGURACIÓN E INTERFAZ DE ALTO NIVEL
st.set_page_config(page_title="SISTEMA QUEVEDO PRO", layout="wide", page_icon="💎")

# Función para limpiar acentos y evitar errores en el PDF
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
                if u == "admin" and p == "Quevedo2026":
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

    # --- NUEVA FUNCIÓN: GENERADOR REPORTE MAESTRO PDF ---
    def generar_reporte_maestro_pdf():
        pdf = FPDF()
        pdf.add_page()
        
        # Encabezado Principal
        pdf.set_font("Arial", 'B', 18)
        pdf.set_text_color(31, 73, 125)
        pdf.cell(0, 15, limpiar_texto("REPORTE MAESTRO - SISTEMA QUEVEDO"), ln=True, align='C')
        pdf.set_font("Arial", 'I', 10)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(0, 10, f"Fecha de emision: {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=True, align='R')
        pdf.ln(5)

        def agregar_seccion(titulo, query, columnas_alias):
            pdf.set_font("Arial", 'B', 14)
            pdf.set_fill_color(240, 240, 240)
            pdf.cell(0, 10, limpiar_texto(titulo), ln=True, fill=True)
            pdf.ln(2)
            
            try:
                df = pd.read_sql_query(query, conn)
                if df.empty:
                    pdf.set_font("Arial", size=10)
                    pdf.cell(0, 8, "No hay registros disponibles.", ln=True)
                else:
                    pdf.set_font("Arial", 'B', 10)
                    # Dibujar cabeceras
                    for col in columnas_alias:
                        pdf.cell(47, 8, limpiar_texto(col), 1)
                    pdf.ln()
                    # Dibujar datos
                    pdf.set_font("Arial", size=9)
                    for _, row in df.iterrows():
                        for val in row:
                            pdf.cell(47, 7, limpiar_texto(str(val)), 1)
                        pdf.ln()
            except:
                pdf.cell(0, 8, "Error al cargar esta seccion.", ln=True)
            pdf.ln(8)

        # 1. Finanzas: Balance y últimos movimientos
        df_f = pd.read_sql_query("SELECT SUM(monto) as bal FROM finanzas", conn)
        balance = df_f['bal'].iloc[0] if df_f['bal'].iloc[0] else 0.0
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, f"BALANCE TOTAL ACUMULADO: RD$ {balance:,.2f}", ln=True)
        agregar_seccion("FINANZAS: ULTIMOS MOVIMIENTOS", 
                        "SELECT fecha, categoria, monto FROM finanzas ORDER BY id DESC LIMIT 10", 
                        ["Fecha", "Concepto", "Monto"])

        # 2. Glucosa: Historial Completo
        agregar_seccion("GLUCOSA: HISTORIAL COMPLETO", 
                        "SELECT fecha, hora, valor, estado FROM glucosa ORDER BY id DESC", 
                        ["Fecha", "Hora", "Valor", "Estado"])

        # 3. Agenda: Medicamentos
        agregar_seccion("AGENDA: MEDICAMENTOS ACTIVOS", 
                        "SELECT nombre, horario FROM medicinas", 
                        ["Medicina", "Horario"])

        # 4. Citas: Consultas Programadas
        agregar_seccion("CITAS: CONSULTAS MEDICAS", 
                        "SELECT doctor, fecha FROM citas", 
                        ["Doctor", "Fecha"])

        return pdf.output(dest='S').encode('latin-1')

    # --- FUNCIÓN GENERAR PDF SALUD (Existente) ---
    def generar_pdf_salud(df_g, df_m):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(200, 10, limpiar_texto("REPORTE MEDICO - LUIS RAFAEL QUEVEDO"), ln=True, align='C')
        pdf.ln(10)
        pdf.set_font("Arial", 'B', 12); pdf.cell(200, 10, "1. MEDICAMENTOS ACTIVOS:", ln=True)
        pdf.set_font("Arial", size=10)
        if df_m.empty: pdf.cell(200, 8, "No hay medicamentos registrados.", ln=True)
        else:
            for _, r in df_m.iterrows():
                linea = f"- {r['nombre']} (Horario: {r['horario']})"; pdf.cell(200, 8, limpiar_texto(linea), ln=True)
        pdf.ln(5); pdf.set_font("Arial", 'B', 12); pdf.cell(200, 10, "2. ULTIMOS REGISTROS DE GLUCOSA:", ln=True)
        pdf.set_font("Arial", size=10)
        if df_g.empty: pdf.cell(200, 8, "No hay registros de glucosa.", ln=True)
        else:
            for _, r in df_g.tail(15).iterrows():
                linea = f"{r['fecha']} {r['hora']}: {r['valor']} mg/dL - {r['estado']}"; pdf.cell(200, 8, limpiar_texto(linea), ln=True)
        nombre = f"Reporte_Salud_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        ruta = os.path.join("archivador_quevedo", nombre)
        pdf.output(ruta)
        return nombre

    # DISEÑO VISUAL CSS
    st.markdown("""
        <style>
        .main { background-color: #0e1117; }
        .stButton>button { width: 100%; border-radius: 12px; background-color: #1b5e20; color: white; height: 3.5em; font-weight: bold; }
        .card-datos { background-color: #1e2130; padding: 12px; border-radius: 10px; border-left: 5px solid #4CAF50; margin-bottom: 8px; display: flex; justify-content: space-between; align-items: center; }
        .semaforo-rojo { background-color: #c62828; padding: 15px; border-radius: 10px; color: white; animation: pulse 2s infinite; text-align: center; font-weight: bold; }
        @keyframes pulse { 0% {box-shadow: 0 0 0 0px rgba(198, 40, 40, 0.7);} 70% {box-shadow: 0 0 0 10px rgba(198, 40, 40, 0);} 100% {box-shadow: 0 0 0 0px rgba(198, 40, 40, 0);} }
        </style>
        """, unsafe_allow_html=True)

    contactos = {"Mi Hijo": "18292061693", "Mi Hija": "18292581449", "Franklin": "16463746377", "Hermanito": "14077975432", "Dorka": "18298811692", "Rosa": "18293800425", "Pedro": "18097100995"}

    # NAVEGACIÓN
    st.sidebar.title("💎 SISTEMA QUEVEDO")
    
    # --- INSTALACIÓN: BOTÓN DE REPORTE MAESTRO EN SIDEBAR ---
    with st.sidebar:
        st.subheader("🚀 Reportes Globales")
        if st.button("📊 GENERAR REPORTE MAESTRO"):
            try:
                pdf_data = generar_reporte_maestro_pdf()
                st.download_button(
                    label="📥 Descargar Reporte Maestro",
                    data=pdf_data,
                    file_name=f"MAESTRO_QUEVEDO_{datetime.now().strftime('%Y%m%d')}.pdf",
                    mime="application/pdf"
                )
                st.success("Reporte Maestro generado.")
            except Exception as e:
                st.error(f"Error: {e}")
        st.divider()

    menu = st.sidebar.radio("MODULOS", ["💰 FINANZAS IA", "🩺 BIOMONITOR", "💊 AGENDA MEDICA", "📸 ESCANER", "📂 ARCHIVADOR", "🤖 ASISTENTE"])
    st.sidebar.link_button("📧 ABRIR MI GMAIL", "https://mail.google.com")

    # --- SECCIÓN 1: FINANZAS ---
    if menu == "💰 FINANZAS IA":
        st.header("💰 Finanzas Inteligentes")
        res_pre = pd.read_sql_query("SELECT limite FROM presupuesto ORDER BY id DESC LIMIT 1", conn)
        limite = res_pre['limite'].iloc[0] if not res_pre.empty else 0.0
        
        with st.expander("⚙️ Presupuesto Mensual"):
            n_limite = st.number_input("RD$ Limite Maximo", value=float(limite))
            if st.button("Guardar Presupuesto"):
                conn.execute("INSERT INTO presupuesto (limite) VALUES (?)", (n_limite,))
                conn.commit(); st.rerun()

        with st.form("finanzas_form", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            tipo = c1.selectbox("TIPO", ["INGRESO", "GASTO"])
            cat = c2.text_input("CONCEPTO").upper()
            mon = c3.number_input("RD$", min_value=0.0)
            if st.form_submit_button("REGISTRAR"):
                val = mon if tipo == "INGRESO" else -mon
                conn.execute("INSERT INTO finanzas (tipo, categoria, monto, fecha) VALUES (?,?,?,?)", (tipo, cat, val, datetime.now().strftime("%d/%m/%Y")))
                conn.commit(); st.rerun()

        df_f = pd.read_sql_query("SELECT * FROM finanzas ORDER BY id DESC", conn)
        if not df_f.empty:
            bal = df_f['monto'].sum(); gastos_t = abs(df_f[df_f['monto'] < 0]['monto'].sum())
            m1, m2 = st.columns(2)
            m1.metric("BALANCE NETO", f"RD$ {bal:,.2f}")
            m2.metric("GASTOS TOTALES", f"RD$ {gastos_t:,.2f}")
            st.dataframe(df_f, use_container_width=True)
            
            if st.button("🗑️ Borrar Historial de Finanzas"):
                conn.execute("DELETE FROM finanzas"); conn.commit(); st.rerun()

    # --- SECCIÓN 2: BIOMONITOR ---
    elif menu == "🩺 BIOMONITOR":
        st.header("🩺 Salud Inteligente")
        val_g = st.number_input("Glucosa mg/dL:", min_value=0)
        
        df_g = pd.read_sql_query("SELECT * FROM glucosa ORDER BY id DESC", conn)
        
        if not df_g.empty and val_g > 0:
            promedio = df_g['valor'].mean()
            cambio = ((val_g - promedio) / promedio) * 100
            if abs(cambio) > 20:
                st.warning(f"⚠️ Variacion detectada: {cambio:.1f}% respecto al promedio.")

        if val_g > 160:
            st.markdown(f'<div class="semaforo-rojo">🚨 ALERTA CRITICA: {val_g} mg/dL</div>', unsafe_allow_html=True)
            cols_w = st.columns(4)
            for i, (nombre, num) in enumerate(contactos.items()):
                msg = f"Emergencia: Luis tiene la glucosa en {val_g}"
                link = f"https://api.whatsapp.com/send?phone={num}&text={msg.replace(' ', '%20')}"
                cols_w[i % 4].link_button(f"👤 {nombre}", link)

        if st.button("💾 GUARDAR TOMA"):
            if val_g > 0:
                tz = pytz.timezone('America/Santo_Domingo'); ahora = datetime.now(tz)
                est = "NORMAL" if val_g <= 140 else "ALERTA" if val_g <= 160 else "CRITICO"
                conn.execute("INSERT INTO glucosa (valor, fecha, hora, estado) VALUES (?,?,?,?)", (val_g, ahora.strftime("%d/%m/%y"), ahora.strftime("%I:%M %p"), est))
                conn.commit(); st.rerun()

        if not df_g.empty:
            st.plotly_chart(px.line(df_g, x="fecha", y="valor", title="Historial Glucosa", markers=True))
            st.dataframe(df_g, use_container_width=True)
            if st.button("🗑️ Borrar Historial de Glucosa"):
                conn.execute("DELETE FROM glucosa"); conn.commit(); st.rerun()

    # --- SECCIÓN 3: AGENDA MÉDICA ---
    elif menu == "💊 AGENDA MEDICA":
        st.header("💊 Gestion Medica")
        
        if st.button("📄 GENERAR REPORTE MEDICO PDF"):
            dg = pd.read_sql_query("SELECT * FROM glucosa", conn)
            dm = pd.read_sql_query("SELECT * FROM medicinas", conn)
            archivo = generar_pdf_salud(dg, dm)
            st.success(f"✅ Reporte guardado: {archivo}")

        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Medicinas")
            m_nom = st.text_input("Nombre:"); m_hor = st.text_input("Hora:")
            if st.button("Añadir Medicina"):
                conn.execute("INSERT INTO medicinas (nombre, horario) VALUES (?,?)", (m_nom.upper(), m_hor)); conn.commit(); st.rerun()
            
            df_m = pd.read_sql_query("SELECT * FROM medicinas", conn)
            if not df_m.empty:
                st.dataframe(df_m, use_container_width=True)
                if st.button("🗑️ Borrar Medicinas"):
                    conn.execute("DELETE FROM medicinas"); conn.commit(); st.rerun()

        with c2:
            st.subheader("Citas")
            c_doc = st.text_input("Doctor:"); c_fec = st.date_input("Fecha")
            if st.button("Agendar Cita"):
                conn.execute("INSERT INTO citas (doctor, fecha) VALUES (?,?)", (c_doc.upper(), str(c_fec))); conn.commit(); st.rerun()
            
            df_c = pd.read_sql_query("SELECT * FROM citas", conn)
            if not df_c.empty:
                st.dataframe(df_c, use_container_width=True)
                if st.button("🗑️ Borrar Citas"):
                    conn.execute("DELETE FROM citas"); conn.commit(); st.rerun()

    # --- SECCIÓN 4: ESCÁNER CON LECTURA DE TEXTO (OCR) ---
    elif menu == "📸 ESCANER":
        st.header("📸 Escaner de Documentos e IA")
        foto = st.camera_input("Capturar")
        if foto:
            fname = f"doc_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            ruta_img = os.path.join("archivador_quevedo", fname)
            with open(ruta_img, "wb") as f: f.write(foto.getbuffer())
            st.success(f"Guardado como: {fname}")
            
            try:
                import pytesseract
                if os.path.exists(r'C:\Program Files\Tesseract-OCR\tesseract.exe'):
                    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
                
                img = Image.open(foto)
                with st.spinner("🔍 Leyendo el documento..."):
                    texto = pytesseract.image_to_string(img, lang='spa')
                if texto.strip():
                    st.subheader("📝 Texto Leído:")
                    st.text_area("Contenido extraído:", texto, height=250)
                else:
                    st.warning("⚠️ No se detectó texto claro. Asegúrate de que haya buena luz.")
            except Exception as e:
                st.info("💡 Nota: El lector de letras estará listo en unos segundos mientras la Nube se actualiza.")

    # --- SECCIÓN 5: ARCHIVADOR ---
    elif menu == "📂 ARCHIVADOR":
        st.header("📂 Archivador")
        archivos = os.listdir("archivador_quevedo")
        if not archivos: st.info("Vacio")
        for a in archivos:
            col_a, col_b = st.columns([3,1])
            with open(os.path.join("archivador_quevedo", a), "rb") as f:
                col_a.download_button(f"💾 {a}", f, file_name=a)
            if col_b.button("❌", key=a):
                os.remove(os.path.join("archivador_quevedo", a))
                st.rerun()

    # --- SECCIÓN 6: ASISTENTE ---
    elif menu == "🤖 ASISTENTE":
        st.header("🤖 Consultas al Sistema")
        pregunta = st.text_input("Preguntame algo (Ej: gasto total, glucosa maxima)")
        if pregunta:
            pregunta = pregunta.lower()
            if "gasto" in pregunta:
                r = pd.read_sql_query("SELECT SUM(monto) as total FROM finanzas WHERE monto < 0", conn)
                valor = r['total'].iloc[0] if r['total'].iloc[0] else 0
                st.write(f"💸 Gasto total registrado: RD$ {abs(valor):,.2f}")
            elif "glucosa" in pregunta:
                r = pd.read_sql_query("SELECT MAX(valor) as maximo FROM glucosa", conn)
                valor = r['maximo'].iloc[0] if r['maximo'].iloc[0] else 0
                st.write(f"🩺 Nivel maximo de glucosa: {valor} mg/dL")
            else:
                st.write("Prueba con 'gasto' o 'glucosa'.")

    # --- PIE DE PÁGINA Y CRÉDITOS ---
    st.sidebar.markdown("---")
    st.sidebar.markdown("👨‍💻 **Diseño y Desarrollo:**")
    st.sidebar.write("Luis Rafael Quevedo")
