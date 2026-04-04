import streamlit as st
import pandas as pd
import sqlite3
import os
import plotly.express as px
from fpdf import FPDF
from datetime import datetime
import pytz
import unicodedata
from PIL import Image
import io

# 1. CONFIGURACIÓN INICIAL
st.set_page_config(page_title="SISTEMA QUEVEDO PRO", layout="wide", page_icon="💎")

def limpiar_texto(texto):
    if not texto: return ""
    return "".join(c for c in unicodedata.normalize('NFD', str(texto)) if unicodedata.category(c) != 'Mn')

# --- SEGURIDAD DE ACCESO ---
if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False

if not st.session_state["autenticado"]:
    st.markdown("<h1 style='text-align: center; color: #4CAF50;'>💎 SISTEMA QUEVEDO</h1>", unsafe_allow_html=True)
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
    st.stop()

# --- BASE DE DATOS Y CARPETAS ---
if not os.path.exists("archivador_quevedo"):
    os.makedirs("archivador_quevedo")

def conectar_db():
    conn = sqlite3.connect("sistema_quevedo_integral.db", check_same_thread=False)
    return conn

conn = conectar_db()
c = conn.cursor()
# Crear todas las tablas necesarias
c.execute('CREATE TABLE IF NOT EXISTS finanzas (id INTEGER PRIMARY KEY AUTOINCREMENT, tipo TEXT, concepto TEXT, monto REAL, fecha TEXT)')
c.execute('CREATE TABLE IF NOT EXISTS glucosa (id INTEGER PRIMARY KEY AUTOINCREMENT, valor INTEGER, fecha TEXT, hora TEXT, estado TEXT)')
c.execute('CREATE TABLE IF NOT EXISTS medicinas (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, horario TEXT)')
c.execute('CREATE TABLE IF NOT EXISTS citas (id INTEGER PRIMARY KEY AUTOINCREMENT, doctor TEXT, fecha TEXT)')
conn.commit()

# --- DISEÑO DE INTERFAZ (CSS) ---
st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 10px; font-weight: bold; height: 3em; }
    .css-1r6slb0 { background-color: #1e2130; padding: 20px; border-radius: 15px; }
    </style>
    """, unsafe_allow_html=True)

# --- NAVEGACIÓN LATERAL ---
st.sidebar.title("💎 PANEL DE CONTROL")
st.sidebar.write(f"Bienvenido, **Luis Rafael**")
menu = st.sidebar.radio("SELECCIONE MÓDULO:", ["💰 FINANZAS", "🩺 GLUCOSA", "💊 MEDICINAS", "📅 CITAS", "📸 ESCÁNER INTELIGENTE", "📂 ARCHIVADOR"])

if st.sidebar.button("🔒 CERRAR SESIÓN"):
    st.session_state["autenticado"] = False
    st.rerun()

# --- MÓDULO 1: FINANZAS ---
if menu == "💰 FINANZAS":
    st.header("💰 Gestión Financiera")
    with st.form("form_finanzas"):
        c1, c2, c3 = st.columns(3)
        tipo = c1.selectbox("Tipo", ["GASTO", "INGRESO"])
        concepto = c2.text_input("Concepto (Ej: Supermercado)")
        monto = c3.number_input("Monto RD$", min_value=0.0)
        if st.form_submit_button("REGISTRAR MOVIMIENTO"):
            valor = -monto if tipo == "GASTO" else monto
            fecha = datetime.now().strftime("%d/%m/%Y")
            c.execute("INSERT INTO finanzas (tipo, concepto, monto, fecha) VALUES (?,?,?,?)", (tipo, concepto.upper(), valor, fecha))
            conn.commit()
            st.success("Registrado correctamente")
            st.rerun()

    st.subheader("📋 Historial de Cuentas")
    df_f = pd.read_sql_query("SELECT * FROM finanzas ORDER BY id DESC", conn)
    if not df_f.empty:
        st.dataframe(df_f, use_container_width=True)
        id_f = st.number_input("ID para borrar", min_value=1, step=1, key="del_f")
        if st.button("🗑️ Eliminar Registro Seleccionado"):
            c.execute("DELETE FROM finanzas WHERE id=?", (id_f,))
            conn.commit()
            st.rerun()

# --- MÓDULO 2: GLUCOSA ---
elif menu == "🩺 GLUCOSA":
    st.header("🩺 Control de Salud (Glucosa)")
    val_g = st.number_input("Nivel mg/dL", min_value=0)
    if st.button("💾 GUARDAR REGISTRO"):
        tz = pytz.timezone('America/Santo_Domingo')
        ahora = datetime.now(tz)
        estado = "NORMAL" if val_g <= 140 else "ALERTA" if val_g <= 160 else "CRÍTICO"
        c.execute("INSERT INTO glucosa (valor, fecha, hora, estado) VALUES (?,?,?,?)", (val_g, ahora.strftime("%d/%m/%y"), ahora.strftime("%I:%M %p"), estado))
        conn.commit()
        st.rerun()

    st.subheader("📈 Historial de Glucosa")
    df_g = pd.read_sql_query("SELECT * FROM glucosa ORDER BY id DESC", conn)
    if not df_g.empty:
        st.plotly_chart(px.line(df_g.sort_values('id'), x="id", y="valor", markers=True))
        st.table(df_g)
        id_g = st.number_input("ID para borrar", min_value=1, step=1, key="del_g")
        if st.button("🗑️ Eliminar Toma"):
            c.execute("DELETE FROM glucosa WHERE id=?", (id_g,))
            conn.commit()
            st.rerun()

# --- MÓDULO 3: MEDICINAS ---
elif menu == "💊 MEDICINAS":
    st.header("💊 Control de Medicamentos")
    with st.form("form_med"):
        nom = st.text_input("Nombre del Medicamento")
        hor = st.text_input("Frecuencia / Horario")
        if st.form_submit_button("AÑADIR A LA LISTA"):
            c.execute("INSERT INTO medicinas (nombre, horario) VALUES (?,?)", (nom.upper(), hor))
            conn.commit()
            st.rerun()

    st.subheader("📋 Medicinas Actuales")
    df_m = pd.read_sql_query("SELECT * FROM medicinas", conn)
    if not df_m.empty:
        st.table(df_m)
        id_m = st.number_input("ID para borrar", min_value=1, step=1, key="del_m")
        if st.button("🗑️ Quitar Medicamento"):
            c.execute("DELETE FROM medicinas WHERE id=?", (id_m,))
            conn.commit()
            st.rerun()

# --- MÓDULO 4: CITAS ---
elif menu == "📅 CITAS":
    st.header("📅 Agenda de Citas")
    with st.form("form_citas"):
        doc = st.text_input("Doctor o Centro Médico")
        fec = st.date_input("Fecha")
        if st.form_submit_button("AGENDAR CITA"):
            c.execute("INSERT INTO citas (doctor, fecha) VALUES (?,?)", (doc.upper(), str(fec)))
            conn.commit()
            st.rerun()

    st.subheader("📅 Próximas Citas")
    df_c = pd.read_sql_query("SELECT * FROM citas ORDER BY fecha ASC", conn)
    if not df_c.empty:
        st.table(df_c)
        id_c = st.number_input("ID para borrar", min_value=1, step=1, key="del_c")
        if st.button("🗑️ Cancelar Cita"):
            c.execute("DELETE FROM citas WHERE id=?", (id_c,))
            conn.commit()
            st.rerun()

# --- MÓDULO 5: ESCÁNER INTELIGENTE ---
elif menu == "📸 ESCÁNER INTELIGENTE":
    st.header("📸 Escáner de Facturas y Recetas")
    st.info("Tome una foto nítida para procesar el documento.")
    
    foto = st.camera_input("Capturar Documento")
    if foto:
        # Guardar imagen físicamente
        img = Image.open(foto)
        fname = f"SCAN_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        ruta = os.path.join("archivador_quevedo", fname)
        img.save(ruta)
        
        st.success(f"✅ Documento escaneado y guardado como: {fname}")
        
        # Simulación de Procesamiento OCR
        st.subheader("🔍 Análisis del Documento")
        with st.spinner("Analizando texto e importes..."):
            # Aquí es donde el sistema "lee". Por ahora mostramos la vista previa.
            st.image(img, caption="Documento Procesado", width=400)
            st.warning("IA: Se ha detectado un documento. ¿Desea clasificarlo?")
            
            tipo_doc = st.selectbox("Clasificar como:", ["Factura de Gasto", "Receta Médica", "Otro"])
            if st.button("Confirmar Clasificación"):
                st.write(f"Documento {fname} clasificado como {tipo_doc}. Los datos se enviarán al Archivador.")

# --- MÓDULO 6: ARCHIVADOR ---
elif menu == "📂 ARCHIVADOR":
    st.header("📂 Archivador Seguro")
    archivos = os.listdir("archivador_quevedo")
    if not archivos:
        st.info("No hay documentos guardados.")
    else:
        for arc in archivos:
            with st.container():
                col_a, col_b, col_c = st.columns([3, 1, 1])
                col_a.write(f"📄 {arc}")
                with open(os.path.join("archivador_quevedo", arc), "rb") as f:
                    col_b.download_button("Descargar", f, file_name=arc, key=arc)
                if col_c.button("🗑️ Eliminar", key=f"del_{arc}"):
                    os.remove(os.path.join("archivador_quevedo", arc))
                    st.rerun()

# --- PIE DE PÁGINA ---
st.sidebar.markdown("---")
st.sidebar.markdown("👨‍💻 **Sistema Quevedo PRO v2.5**")
st.sidebar.caption("Diseñado por Luis Rafael Quevedo")
