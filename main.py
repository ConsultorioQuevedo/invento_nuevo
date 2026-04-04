import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
from fpdf import FPDF
from datetime import datetime
import pytz

# 1. CONFIGURACIÓN PROFESIONAL
st.set_page_config(page_title="SISTEMA QUEVEDO PRO", layout="wide")

# 2. BASE DE DATOS PERMANENTE (No se borra sola)
def iniciar_db():
    conn = sqlite3.connect("sistema_quevedo_final.db", check_same_thread=False)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS finanzas (id INTEGER PRIMARY KEY, tipo TEXT, categoria TEXT, monto REAL)')
    c.execute('CREATE TABLE IF NOT EXISTS glucosa (id INTEGER PRIMARY KEY, valor INTEGER, fecha TEXT, estado TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS medicamentos (id INTEGER PRIMARY KEY, nombre TEXT, hora TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS citas (id INTEGER PRIMARY KEY, doctor TEXT, fecha TEXT, hora TEXT)')
    conn.commit()
    return conn

conn = iniciar_db()

# 3. ESTILO Y MENÚ LATERAL
st.sidebar.title("🚀 SISTEMA QUEVEDO")
st.sidebar.markdown("---")
opcion = st.sidebar.radio("SECCIONES", ["💰 FINANZAS", "🩺 GLUCOSA", "💊 MEDICINAS / CITAS", "📷 ESCÁNER Y PDF"])

# --- SECCIÓN 1: FINANZAS (Cálculo Automático) ---
if opcion == "💰 FINANZAS":
    st.header("💰 Control de Finanzas")
    
    with st.expander("➕ Registrar Nuevo Movimiento", expanded=True):
        with st.form("form_f", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            with c1: t = st.selectbox("Tipo", ["INGRESO", "GASTO", "PRESUPUESTO"])
            with c2: cat = st.text_input("Concepto (Ej: Supermercado)").upper()
            with c3: mon = st.number_input("Monto RD$", min_value=0.0)
            if st.form_submit_button("REGISTRAR"):
                conn.execute("INSERT INTO finanzas (tipo, categoria, monto) VALUES (?,?,?)", (t, cat, mon))
                conn.commit()
                st.success("Dato Guardado")

    df_f = pd.read_sql_query("SELECT * FROM finanzas", conn)
    if not df_f.empty:
        # LÓGICA DE SUMA Y RESTA
        ing = df_f[df_f['tipo'] == 'INGRESO']['monto'].sum()
        gas = df_f[df_f['tipo'] == 'GASTO']['monto'].sum()
        pre = df_f[df_f['tipo'] == 'PRESUPUESTO']['monto'].sum()
        balance = ing - gas

        col_m1, col_m2, col_m3 = st.columns(3)
        col_m1.metric("INGRESOS TOTALES", f"RD$ {ing:,.2f}")
        col_m2.metric("GASTOS TOTALES", f"RD$ {gas:,.2f}", delta=-gas, delta_color="inverse")
        col_m3.metric("DISPONIBLE (NETO)", f"RD$ {balance:,.2f}", delta=balance)

        st.markdown("### 📋 Historial Permanente")
        for i, r in df_f.iterrows():
            col_r1, col_r2 = st.columns([5, 1])
            color = "green" if r['tipo'] == "INGRESO" else "red"
            col_r1.markdown(f"**{r['tipo']}**: {r['categoria']} | <span style='color:{color}'>RD$ {r['monto']:,.2f}</span>", unsafe_allow_html=True)
            if col_r2.button("Eliminar", key=f"f_{r['id']}"):
                conn.execute(f"DELETE FROM finanzas WHERE id={r['id']}")
                conn.commit()
                st.rerun()

# --- SECCIÓN 2: SALUD (Semáforo Dinámico) ---
elif opcion == "🩺 GLUCOSA":
    st.header("🩸 Monitor Glucémico")
    
    val = st.number_input("Nivel de Glucosa mg/dL:", min_value=0)
    if st.button("Guardar Valor"):
        # LÓGICA DE SEMÁFORO
        if val <= 140: est, col = "NORMAL", "🟢"
        elif val <= 160: est, col = "ALERTA", "🟡"
        else: est, col = "ALTO", "🔴"
        
        fec = datetime.now().strftime("%d/%m %I:%M %p")
        conn.execute("INSERT INTO glucosa (valor, fecha, estado) VALUES (?,?,?)", (val, fec, f"{col} {est}"))
        conn.commit()

    df_g = pd.read_sql_query("SELECT * FROM glucosa ORDER BY id DESC", conn)
    if not df_g.empty:
        st.plotly_chart(px.line(df_g, x="fecha", y="valor", title="Gráfico de Salud", markers=True))
        
        st.subheader("Historial de Lecturas")
        for i, r in df_g.iterrows():
            c_g1, c_g2 = st.columns([5, 1])
            c_g1.write(f"📅 {r['fecha']} | **{r['valor']} mg/dL** | {r['estado']}")
            if c_g2.button("Borrar", key=f"g_{r['id']}"):
                conn.execute(f"DELETE FROM glucosa WHERE id={r['id']}")
                conn.commit()
                st.rerun()

# --- SECCIÓN 3: MEDICINAS Y CITAS ---
elif opcion == "💊 MEDICINAS / CITAS":
    st.header("💊 Gestión Médica")
    
    col_izq, col_der = st.columns(2)
    with col_izq:
        st.subheader("Medicamentos")
        with st.form("f_med", clear_on_submit=True):
            m_n = st.text_input("Nombre:")
            m_h = st.time_input("Hora de toma:")
            if st.form_submit_button("Añadir"):
                conn.execute("INSERT INTO medicamentos (nombre, hora) VALUES (?,?)", (m_n.upper(), str(m_h)))
                conn.commit()
        
        df_m = pd.read_sql_query("SELECT * FROM medicamentos", conn)
        for i, r in df_m.iterrows():
            st.write(f"💊 {r['nombre']} - {r['hora']}")
            if st.button("❌", key=f"m_{r['id']}"):
                conn.execute(f"DELETE FROM medicamentos WHERE id={r['id']}"); conn.commit(); st.rerun()

    with col_der:
        st.subheader("📅 Citas")
        with st.form("f_cit", clear_on_submit=True):
            doc = st.text_input("Doctor:")
            fec = st.date_input("Fecha:")
            hor = st.time_input("Hora:")
            if st.form_submit_button("Agendar"):
                conn.execute("INSERT INTO citas (doctor, fecha, hora) VALUES (?,?,?)", (doc.upper(), str(fec), str(hor)))
                conn.commit()
        
        df_c = pd.read_sql_query("SELECT * FROM citas", conn)
        for i, r in df_c.iterrows():
            st.write(f"👨‍⚕️ {r['doctor']} | {r['fecha']} - {r['hora']}")
            if st.button("Eliminar Cita", key=f"c_{r['id']}"):
                conn.execute(f"DELETE FROM citas WHERE id={r['id']}"); conn.commit(); st.rerun()

# --- SECCIÓN 4: ESCÁNER Y PDF ---
elif opcion == "📷 ESCÁNER Y PDF":
    st.header("📄 Herramientas de Documentación")
    
    c1, c2 = st.columns(2)
    with c1:
        st.link_button("📧 Gmail", "https://mail.google.com")
        st.link_button("💬 WhatsApp", "https://web.whatsapp.com")
    
    with c2:
        if st.button("📥 Generar Reporte PDF"):
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", 'B', 16)
            pdf.cell(200, 10, "REPORTE SISTEMA QUEVEDO", ln=True, align='C')
            pdf.output("reporte.pdf")
            st.success("PDF generado.")

    st.divider()
    st.subheader("📷 Escáner de Cámara")
    foto = st.camera_input("Capturar factura o receta")
    if foto:
        st.image(foto, caption="Documento Guardado")

# PIE DE PÁGINA
st.sidebar.markdown("---")
st.sidebar.write("**Diseñadores:** Luis Rafael Quevedo")
