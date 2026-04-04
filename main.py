import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
from fpdf import FPDF
from datetime import datetime
import pytz

# 1. CONFIGURACIÓN DEL SISTEMA
st.set_page_config(page_title="SISTEMA QUEVEDO", layout="wide", page_icon="🚀")

# 2. MOTOR DE DATOS PERMANENTE (SQLite)
def iniciar_db():
    conn = sqlite3.connect("sistema_quevedo_final.db", check_same_thread=False)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS finanzas (id INTEGER PRIMARY KEY, tipo TEXT, categoria TEXT, monto REAL)')
    c.execute('CREATE TABLE IF NOT EXISTS glucosa (id INTEGER PRIMARY KEY, valor INTEGER, fecha TEXT, hora TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS medicamentos (id INTEGER PRIMARY KEY, nombre TEXT, horario TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS citas (id INTEGER PRIMARY KEY, doctor TEXT, fecha TEXT, hora TEXT)')
    conn.commit()
    return conn

conn = iniciar_db()

# 3. LÓGICA DE SEMÁFORO GLUCÉMICO
def obtener_semaforo(valor):
    if valor < 140: return "🟢 NORMAL (90-140)", "#28a745"
    elif 140 <= valor <= 160: return "🟡 ALERTA (140-160)", "#ffc107"
    else: return "🔴 ALTO (+160)", "#dc3545"

# --- MENÚ LATERAL (SIDEBAR) ---
st.sidebar.title("🚀 SISTEMA QUEVEDO")
st.sidebar.markdown("---")
seccion = st.sidebar.radio("SECCIONES", ["💰 FINANZAS", "🩺 SALUD (GLUCOSA)", "💊 MEDICAMENTOS", "📅 CITAS MÉDICAS", "📸 ESCÁNER & PDF"])

# --- SECCIÓN FINANZAS ---
if seccion == "💰 FINANZAS":
    st.header("💰 Gestión de Finanzas e Inteligencia")
    with st.form("form_finanzas", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        with col1: t = st.selectbox("TIPO", ["PRESUPUESTO", "INGRESO", "GASTO"])
        with col2: c = st.text_input("CONCEPTO").upper()
        with col3: m = st.number_input("MONTO RD$", min_value=0.0)
        if st.form_submit_button("REGISTRAR DATO"):
            conn.execute("INSERT INTO finanzas (tipo, categoria, monto) VALUES (?,?,?)", (t, c, m))
            conn.commit()

    df_f = pd.read_sql_query("SELECT * FROM finanzas", conn)
    if not df_f.empty:
        # Cálculos en tiempo real
        ing = df_f[df_f['tipo'] == 'INGRESO']['monto'].sum()
        gas = df_f[df_f['tipo'] == 'GASTO']['monto'].sum()
        pre = df_f[df_f['tipo'] == 'PRESUPUESTO']['monto'].sum()
        
        c1, c2, c3 = st.columns(3)
        c1.metric("TOTAL INGRESOS", f"RD$ {ing:,.2f}")
        c2.metric("TOTAL GASTOS", f"RD$ {gas:,.2f}", delta=-gas)
        c3.metric("BALANCE NETO", f"RD$ {(ing - gas):,.2f}")

        st.subheader("Registros Almacenados")
        for i, r in df_f.iterrows():
            col_a, col_b = st.columns([5, 1])
            col_a.info(f"**{r['tipo']}**: {r['categoria']} - RD$ {r['monto']:,.2f}")
            if col_b.button("🗑️", key=f"f_{r['id']}"):
                conn.execute(f"DELETE FROM finanzas WHERE id={r['id']}")
                conn.commit()
                st.rerun()

# --- SECCIÓN GLUCOSA ---
elif seccion == "🩺 SALUD (GLUCOSA)":
    st.header("🩸 Bio-Monitor de Glucosa")
    with st.form("form_glucosa", clear_on_submit=True):
        val = st.number_input("Nivel mg/dL:", min_value=0)
        if st.form_submit_button("GUARDAR VALOR"):
            zona = pytz.timezone('America/Santo_Domingo')
            ahora = datetime.now(zona)
            conn.execute("INSERT INTO glucosa (valor, fecha, hora) VALUES (?,?,?)", 
                         (val, ahora.strftime("%d/%m/%Y"), ahora.strftime("%I:%M %p")))
            conn.commit()

    df_g = pd.read_sql_query("SELECT * FROM glucosa ORDER BY id DESC", conn)
    if not df_g.empty:
        st.plotly_chart(px.line(df_g, x="id", y="valor", title="Gráfico de Tendencia Glucémica", markers=True))
        
        for i, r in df_g.iterrows():
            label, color = obtener_semaforo(r['valor'])
            st.markdown(f"""<div style="padding:10px; border-radius:5px; border-left: 10px solid {color}; background:#1e1e1e; margin-bottom:5px">
                <b>{r['fecha']} | {r['hora']}</b> - Valor: <b>{r['valor']} mg/dL</b> <br> <small>{label}</small></div>""", unsafe_allow_html=True)
            if st.button(f"Eliminar Registro #{r['id']}", key=f"g_{r['id']}"):
                conn.execute(f"DELETE FROM glucosa WHERE id={r['id']}")
                conn.commit()
                st.rerun()

# --- SECCIÓN MEDICAMENTOS Y CITAS ---
elif seccion == "💊 MEDICAMENTOS":
    st.header("💊 Control de Tratamientos")
    with st.form("f_med"):
        n = st.text_input("Nombre del Medicamento:")
        h = st.time_input("Hora de toma:")
        if st.form_submit_button("AGREGAR"):
            conn.execute("INSERT INTO medicamentos (nombre, horario) VALUES (?,?)", (n.upper(), str(h)))
            conn.commit()
    
    df_m = pd.read_sql_query("SELECT * FROM medicamentos", conn)
    for i, r in df_m.iterrows():
        st.write(f"💊 **{r['nombre']}** - Horario: {r['horario']}")
        if st.button("Borrar", key=f"m_{r['id']}"):
            conn.execute(f"DELETE FROM medicamentos WHERE id={r['id']}"); conn.commit(); st.rerun()

elif seccion == "📅 CITAS MÉDICAS":
    st.header("📅 Agenda de Consultas")
    with st.form("f_citas"):
        d = st.text_input("Doctor/Especialidad:")
        f = st.date_input("Fecha:")
        h = st.time_input("Hora:")
        if st.form_submit_button("AGENDAR"):
            conn.execute("INSERT INTO citas (doctor, fecha, hora) VALUES (?,?,?)", (d.upper(), str(f), str(h)))
            conn.commit()
    
    df_c = pd.read_sql_query("SELECT * FROM citas", conn)
    for i, r in df_c.iterrows():
        st.write(f"📅 **{r['doctor']}** - {r['fecha']} a las {r['hora']}")
        if st.button("Eliminar Cita", key=f"c_{r['id']}"):
            conn.execute(f"DELETE FROM citas WHERE id={r['id']}"); conn.commit(); st.rerun()

# --- SECCIÓN ESCÁNER Y PDF ---
elif seccion == "📸 ESCÁNER & PDF":
    st.header("📸 Centro de Documentación")
    col_x, col_y = st.columns(2)
    with col_x: st.link_button("📧 Gmail", "https://mail.google.com")
    with col_y: st.link_button("💬 WhatsApp", "https://web.whatsapp.com")
    
    st.divider()
    cam = st.camera_input("Escanear Documento (Recetas/Facturas)")
    if cam:
        st.image(cam, caption="Vista Previa del Escaneo")
        st.download_button("Guardar Imagen Escaneada", cam, file_name="escaneo_quevedo.png")

    if st.button("📥 Generar Reporte General en PDF"):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(200, 10, "SISTEMA QUEVEDO: REPORTE INTEGRAL", ln=True, align='C')
        pdf.output("Reporte_Quevedo.pdf")
        st.success("PDF Generado con éxito.")

# --- CRÉDITOS ---
st.sidebar.markdown("---")
st.sidebar.write("**DISEÑADORES:**")
st.sidebar.write("Luis Rafael Quevedo")
