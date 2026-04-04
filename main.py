import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
from fpdf import FPDF
from datetime import datetime
import pytz
import numpy as np
from sklearn.linear_model import LinearRegression

# 1. CONFIGURACIÓN E INTERFAZ
st.set_page_config(page_title="SISTEMA QUEVEDO OMNI-IA", layout="wide", page_icon="🧠")

# 2. MOTOR DE DATOS PERMANENTE (SQLite)
def iniciar_db():
    conn = sqlite3.connect("sistema_quevedo_total.db", check_same_thread=False)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS finanzas (id INTEGER PRIMARY KEY, tipo TEXT, categoria TEXT, monto REAL)')
    c.execute('CREATE TABLE IF NOT EXISTS glucosa (id INTEGER PRIMARY KEY, valor INTEGER, fecha TEXT, estado TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS medicamentos (id INTEGER PRIMARY KEY, nombre TEXT, hora TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS citas (id INTEGER PRIMARY KEY, doctor TEXT, fecha TEXT, hora TEXT, motivo TEXT)')
    conn.commit()
    return conn

conn = iniciar_db()

# 3. NÚCLEO DE INTELIGENCIA ARTIFICIAL
def motor_ia_predictivo(df):
    if len(df) > 3:
        # La IA analiza la tendencia de tu balance acumulado
        X = np.arange(len(df)).reshape(-1, 1)
        y = df['monto'].cumsum().values 
        modelo = LinearRegression().fit(X, y)
        prediccion = modelo.predict([[len(df) + 1]])[0]
        return round(prediccion, 2)
    return None

# 4. LÓGICA DE SEMÁFORO (90-140 Verde | 140-160 Amarillo | +160 Rojo)
def obtener_semaforo(v):
    if v < 140: return "🟢 NORMAL", "#28a745"
    if v <= 160: return "🟡 ALERTA", "#ffc107"
    return "🔴 RIESGO", "#dc3545"

# --- MENÚ LATERAL ---
st.sidebar.title("🚀 SISTEMA QUEVEDO")
st.sidebar.markdown("---")
seccion = st.sidebar.radio("SECCIONES", ["💰 FINANZAS & IA", "🩺 SALUD (GLUCOSA)", "💊 MEDICAMENTOS", "📅 CITAS MÉDICAS", "📸 ESCÁNER & PDF"])

# --- SECCIÓN 1: FINANZAS CON IA ---
if seccion == "💰 FINANZAS & IA":
    st.header("💰 Gestión Financiera Inteligente")
    with st.form("f_fin", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        with col1: t = st.selectbox("TIPO", ["INGRESO", "GASTO", "PRESUPUESTO"])
        with col2: c = st.text_input("CONCEPTO").upper()
        with col3: m = st.number_input("MONTO RD$", min_value=0.0)
        if st.form_submit_button("REGISTRAR DATO"):
            val = m if t != "GASTO" else -m
            conn.execute("INSERT INTO finanzas (tipo, categoria, monto) VALUES (?,?,?)", (t, c, val))
            conn.commit()

    df_f = pd.read_sql_query("SELECT * FROM finanzas", conn)
    if not df_f.empty:
        balance = df_f['monto'].sum()
        pred = motor_ia_predictivo(df_f)
        
        c1, c2 = st.columns(2)
        c1.metric("BALANCE ACTUAL", f"RD$ {balance:,.2f}")
        if pred is not None:
            c2.metric("IA: PROYECCIÓN FUTURA", f"RD$ {pred:,.2f}", delta=round(pred-balance, 2))
            if pred < 1500:
                st.warning(f"⚠️ IA ALERT: Se proyecta balance bajo (RD$ {pred})")
                msg = f"Sistema Quevedo: Alerta IA de balance bajo proyectado: RD$ {pred}"
                st.link_button("📲 ENVIAR ALERTA WHATSAPP", f"https://wa.me/18490000000?text={msg}")
        
        st.subheader("Historial de Movimientos")
        for i, r in df_f.iterrows():
            col_a, col_b = st.columns([6, 1])
            col_a.info(f"{r['tipo']}: {r['categoria']} | RD$ {r['monto']:,.2f}")
            if col_b.button("🗑️", key=f"f_{r['id']}"):
                conn.execute(f"DELETE FROM finanzas WHERE id={r['id']}"); conn.commit(); st.rerun()

# --- SECCIÓN 2: SALUD (GLUCOSA Y SEMÁFORO) ---
elif seccion == "🩺 SALUD (GLUCOSA)":
    st.header("🩸 Monitor de Glucosa con Semáforo")
    val_g = st.number_input("Nivel mg/dL:", min_value=0)
    if st.button("Guardar Nivel"):
        est, _ = obtener_semaforo(val_g)
        fecha = datetime.now().strftime("%d/%m %H:%M")
        conn.execute("INSERT INTO glucosa (valor, fecha, estado) VALUES (?,?,?)", (val_g, fecha, est))
        conn.commit()

    df_g = pd.read_sql_query("SELECT * FROM glucosa ORDER BY id DESC", conn)
    if not df_g.empty:
        st.plotly_chart(px.line(df_g, x="fecha", y="valor", title="Tendencia Glucémica IA", markers=True))
        for i, r in df_g.iterrows():
            _, color = obtener_semaforo(r['valor'])
            st.markdown(f'<div style="border-left: 10px solid {color}; padding:10px; background:#1e1e1e; margin-bottom:10px; border-radius:5px"><b>{r["fecha"]}</b> - {r["valor"]} mg/dL ({r["estado"]})</div>', unsafe_allow_html=True)
            if st.button(f"Eliminar #{r['id']}", key=f"g_{r['id']}"):
                conn.execute(f"DELETE FROM glucosa WHERE id={r['id']}"); conn.commit(); st.rerun()

# --- SECCIÓN 3: MEDICAMENTOS ---
elif seccion == "💊 MEDICAMENTOS":
    st.header("💊 Control de Tratamientos")
    with st.form("f_med"):
        n = st.text_input("Nombre del Medicamento:").upper()
        h = st.text_input("Horario / Frecuencia:")
        if st.form_submit_button("AÑADIR A LA LISTA"):
            conn.execute("INSERT INTO medicamentos (nombre, hora) VALUES (?,?)", (n, h)); conn.commit()
    
    df_m = pd.read_sql_query("SELECT * FROM medicamentos", conn)
    for i, r in df_m.iterrows():
        st.write(f"💊 **{r['nombre']}** - Horario: {r['hora']}")
        if st.button("Borrar", key=f"m_{r['id']}"):
            conn.execute(f"DELETE FROM medicamentos WHERE id={r['id']}"); conn.commit(); st.rerun()

# --- SECCIÓN 4: CITAS MÉDICAS ---
elif seccion == "📅 CITAS MÉDICAS":
    st.header("📅 Agenda de Consultas")
    with st.form("f_citas"):
        doc = st.text_input("Doctor/Especialidad:").upper()
        fec = st.date_input("Fecha")
        hor = st.time_input("Hora")
        mot = st.text_input("Motivo")
        if st.form_submit_button("AGENDAR CITA"):
            conn.execute("INSERT INTO citas (doctor, fecha, hora, motivo) VALUES (?,?,?,?)", (doc, str(fec), str(hor), mot)); conn.commit()
    
    df_c = pd.read_sql_query("SELECT * FROM citas", conn)
    for i, r in df_c.iterrows():
        st.write(f"📅 **{r['doctor']}** | {r['fecha']} a las {r['hora']} - Motivo: {r['motivo']}")
        if st.button("Eliminar Cita", key=f"c_{r['id']}"):
            conn.execute(f"DELETE FROM citas WHERE id={r['id']}"); conn.commit(); st.rerun()

# --- SECCIÓN 5: ESCÁNER, PDF Y REDES ---
elif seccion == "📸 ESCÁNER & PDF":
    st.header("📄 Herramientas y Documentación")
    c1, c2 = st.columns(2)
    c1.link_button("📧 Abrir Gmail", "https://mail.google.com")
    c2.link_button("💬 WhatsApp Web", "https://web.whatsapp.com")
    
    st.divider()
    st.subheader("📸 Escáner de Documentos")
    foto = st.camera_input("Capturar Receta o Factura")
    if foto:
        st.image(foto, caption="Documento en Memoria")
        st.download_button("Guardar Imagen Escaneada", foto, file_name="escaneo_quevedo.png")

    st.divider()
    st.subheader("📥 Generador de Reportes")
    if st.button("Generar Reporte Integral PDF"):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(200, 10, "REPORTE SISTEMA QUEVEDO OMNI-IA", ln=True, align='C')
        pdf.set_font("Arial", '', 12)
        pdf.cell(200, 10, f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=True)
        pdf.cell(200, 10, "--------------------------------------------------", ln=True)
        pdf_bin = pdf.output(dest='S').encode('latin-1')
        st.download_button("⬇️ DESCARGAR PDF", data=pdf_bin, file_name="Reporte_Quevedo.pdf", mime="application/pdf")

# --- PIE DE PÁGINA (CRÉDITOS) ---
st.sidebar.markdown("---")
st.sidebar.write("**DISEÑADORES:**")
st.sidebar.write("Luis Rafael Quevedo")
