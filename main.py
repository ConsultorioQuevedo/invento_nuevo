import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
from fpdf import FPDF
from datetime import datetime
import pytz

# 1. CONFIGURACIÓN DE INTERFAZ PROFESIONAL
st.set_page_config(page_title="SISTEMA QUEVEDO", layout="wide", page_icon="🚀")

# 2. MOTOR DE DATOS (Base de Datos Robusta)
def iniciar_db():
    conn = sqlite3.connect("sistema_quevedo_integral.db", check_same_thread=False)
    c = conn.cursor()
    # Finanzas: Presupuesto, Ingresos y Gastos
    c.execute('''CREATE TABLE IF NOT EXISTS finanzas 
                 (id INTEGER PRIMARY KEY, tipo TEXT, categoria TEXT, monto REAL)''')
    # Salud: Glucosa con Semáforo
    c.execute('''CREATE TABLE IF NOT EXISTS glucosa 
                 (id INTEGER PRIMARY KEY, valor INTEGER, fecha TEXT, hora TEXT, estado TEXT)''')
    # Salud: Medicamentos y Citas
    c.execute('''CREATE TABLE IF NOT EXISTS medicamentos 
                 (id INTEGER PRIMARY KEY, nombre TEXT, horario TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS citas 
                 (id INTEGER PRIMARY KEY, doctor TEXT, fecha TEXT, hora TEXT, motivo TEXT)''')
    conn.commit()
    return conn

conn = iniciar_db()

# 3. LÓGICA DE SEMÁFORO (90-140 Verde | 140-160 Amarillo | +160 Rojo)
def obtener_semaforo(valor):
    if valor < 140: return "🟢 NORMAL", "#28a745"
    elif 140 <= valor <= 160: return "🟡 ALERTA", "#ffc107"
    else: return "🔴 ALTO", "#dc3545"

# --- MENÚ LATERAL ---
st.sidebar.title("🚀 SISTEMA QUEVEDO")
st.sidebar.markdown("---")
opcion = st.sidebar.radio("SECCIONES", ["💰 FINANZAS", "🩺 GLUCOSA", "💊 MEDICAMENTOS", "📅 CITAS MÉDICAS", "📸 ESCÁNER & PDF"])

# --- SECCIÓN 1: FINANZAS (SUMA Y RESTA) ---
if opcion == "💰 FINANZAS":
    st.header("💰 Control de Finanzas e Inteligencia")
    with st.form("form_finanzas", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        with col1: t = st.selectbox("TIPO", ["INGRESO", "GASTO", "PRESUPUESTO"])
        with col2: c = st.text_input("CONCEPTO (Ej: Alquiler, Sueldo)").upper()
        with col3: m = st.number_input("MONTO RD$", min_value=0.0)
        if st.form_submit_button("REGISTRAR"):
            conn.execute("INSERT INTO finanzas (tipo, categoria, monto) VALUES (?,?,?)", (t, c, m))
            conn.commit()

    df_f = pd.read_sql_query("SELECT * FROM finanzas", conn)
    if not df_f.empty:
        ing = df_f[df_f['tipo'] == 'INGRESO']['monto'].sum()
        gas = df_f[df_f['tipo'] == 'GASTO']['monto'].sum()
        pre = df_f[df_f['tipo'] == 'PRESUPUESTO']['monto'].sum()
        
        # Panel de Resumen
        c1, c2, c3 = st.columns(3)
        c1.metric("INGRESOS", f"RD$ {ing:,.2f}")
        c2.metric("GASTOS", f"RD$ {gas:,.2f}", delta=-gas)
        c3.metric("BALANCE NETO", f"RD$ {(ing - gas):,.2f}")
        
        st.subheader("Historial de Movimientos")
        for i, r in df_f.iterrows():
            col_a, col_b = st.columns([5, 1])
            col_a.info(f"**{r['tipo']}**: {r['categoria']} - RD$ {r['monto']:,.2f}")
            if col_b.button("🗑️", key=f"f_{r['id']}"):
                conn.execute(f"DELETE FROM finanzas WHERE id={r['id']}")
                conn.commit()
                st.rerun()

# --- SECCIÓN 2: GLUCOSA (SEMÁFORO Y GRÁFICO) ---
elif opcion == "🩺 GLUCOSA":
    st.header("🩸 Bio-Monitor de Glucosa")
    val_g = st.number_input("Nivel mg/dL:", min_value=0)
    if st.button("Guardar Nivel"):
        zona = pytz.timezone('America/Santo_Domingo')
        ahora = datetime.now(zona)
        est, _ = obtener_semaforo(val_g)
        conn.execute("INSERT INTO glucosa (valor, fecha, hora, estado) VALUES (?,?,?,?)", 
                     (val_g, ahora.strftime("%d/%m/%Y"), ahora.strftime("%I:%M %p"), est))
        conn.commit()

    df_g = pd.read_sql_query("SELECT * FROM glucosa ORDER BY id DESC", conn)
    if not df_g.empty:
        st.plotly_chart(px.line(df_g, x="id", y="valor", title="Tendencia de Glucosa", markers=True))
        for i, r in df_g.iterrows():
            _, color = obtener_semaforo(r['valor'])
            st.markdown(f"""<div style="padding:10px; border-radius:5px; border-left:10px solid {color}; background:#1e1e1e; margin-bottom:10px">
                <b>{r['fecha']} | {r['hora']}</b> - Valor: <b>{r['valor']} mg/dL</b> ({r['estado']})</div>""", unsafe_allow_html=True)
            if st.button(f"Eliminar Registro {r['id']}", key=f"g_{r['id']}"):
                conn.execute(f"DELETE FROM glucosa WHERE id={r['id']}")
                conn.commit()
                st.rerun()

# --- SECCIÓN 3: MEDICAMENTOS Y CITAS ---
elif opcion == "💊 MEDICAMENTOS":
    st.header("💊 Gestión de Medicinas")
    with st.form("f_med"):
        n = st.text_input("Nombre del Medicamento:").upper()
        h = st.text_input("Horario (Ej: 8:00 AM / Cada 8h):")
        if st.form_submit_button("AÑADIR"):
            conn.execute("INSERT INTO medicamentos (nombre, horario) VALUES (?,?)", (n, h))
            conn.commit()
    
    df_m = pd.read_sql_query("SELECT * FROM medicamentos", conn)
    for i, r in df_m.iterrows():
        st.write(f"💊 **{r['nombre']}** - {r['horario']}")
        if st.button("Borrar", key=f"m_{r['id']}"):
            conn.execute(f"DELETE FROM medicamentos WHERE id={r['id']}"); conn.commit(); st.rerun()

elif opcion == "📅 CITAS MÉDICAS":
    st.header("📅 Agenda de Consultas")
    with st.form("f_citas"):
        d = st.text_input("Doctor/Especialidad:").upper()
        f = st.date_input("Fecha:")
        h = st.time_input("Hora:")
        if st.form_submit_button("AGENDAR"):
            conn.execute("INSERT INTO citas (doctor, fecha, hora) VALUES (?,?,?)", (d, str(f), str(h)))
            conn.commit()
    
    df_c = pd.read_sql_query("SELECT * FROM citas", conn)
    for i, r in df_c.iterrows():
        st.write(f"📅 **{r['doctor']}** | {r['fecha']} a las {r['hora']}")
        if st.button("Eliminar Cita", key=f"c_{r['id']}"):
            conn.execute(f"DELETE FROM citas WHERE id={r['id']}"); conn.commit(); st.rerun()

# --- SECCIÓN 4: ESCÁNER Y PDF ---
elif opcion == "📸 ESCÁNER & PDF":
    st.header("📸 Centro de Documentación")
    col1, col2 = st.columns(2)
    col1.link_button("📧 Ir a Gmail", "https://mail.google.com")
    col2.link_button("💬 WhatsApp Web", "https://web.whatsapp.com")
    
    st.divider()
    foto = st.camera_input("Escanear Receta o Factura")
    if foto:
        st.image(foto, caption="Documento Almacenado")
        st.success("Imagen capturada con éxito.")

    if st.button("📥 Generar Reporte PDF"):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(200, 10, "REPORTE SISTEMA QUEVEDO", ln=True, align='C')
        # Aquí podrías añadir lógica para volcar tablas al PDF
        pdf.output("Reporte_Quevedo.pdf")
        st.success("PDF generado y listo para descargar.")

# --- PIE DE PÁGINA ---
st.sidebar.markdown("---")
st.sidebar.write("**DISEÑADORES:**")
st.sidebar.write("Luis Rafael Quevedo")
