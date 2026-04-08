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

# --- INICIO CORREGIDO PARA LUIS RAFAEL ---
if menu == "🏠 INICIO":
    # Definimos tu identidad real
    NOMBRE_PROPIETARIO = "LUIS RAFAEL QUEVEDO"
    
    st.header(f"📊 Panel de Control: {NOMBRE_PROPIETARIO}")
    
    c1, c2, c3 = st.columns(3)
    
    try:
        # Consultas a la base de datos para métricas reales
        df_fin = pd.read_sql_query("SELECT SUM(monto) as total FROM finanzas", conn)
        df_glu = pd.read_sql_query("SELECT valor FROM glucosa ORDER BY id DESC LIMIT 1", conn)
        
        with c1:
            st.markdown('<div class="resumen-card">', unsafe_allow_html=True)
            st.metric("💰 BALANCE TOTAL", f"RD$ {df_fin['total'][0] or 0:,.2f}")
            st.markdown('</div>', unsafe_allow_html=True)
        with c2:
            st.markdown('<div class="resumen-card">', unsafe_allow_html=True)
            # Si no hay glucosa registrada, muestra 0
            valor_g = df_glu['valor'][0] if not df_glu.empty else 0
            st.metric("🩺 ÚLTIMA GLUCOSA", f"{valor_g} mg/dL")
            st.markdown('</div>', unsafe_allow_html=True)
        with c3:
            st.markdown('<div class="resumen-card">', unsafe_allow_html=True)
            st.metric("📅 ESTADO", "OPERATIVO")
            st.markdown('</div>', unsafe_allow_html=True)
    except Exception as e:
        st.warning("Inicializando datos o error en base de datos...")

    st.divider()
    
    # --- SECCIÓN DE ENLACES REALES ---
    st.subheader("📲 Acceso Rápido y Comunicación")
    col_link1, col_link2, col_link3 = st.columns(3)
    
    # WhatsApp Personal (Configurado para República Dominicana +1)
    # Reemplaza el '8090000000' con tu número real
    mi_celular = "18090000000" 
    col_link1.link_button("💬 MI WHATSAPP", f"https://wa.me/{mi_celular}?text=Hola%20Luis%20Rafael,%20revisando%20el%20Invento%20Nuevo")
    
    # Gmail Real
    # Reemplaza 'tu_correo@gmail.com' con tu dirección real
    mi_correo = "tu_correo@gmail.com"
    col_link2.link_button("📧 MI GMAIL", f"https://mail.google.com/mail/?view=cm&fs=1&to={mi_correo}&su=Reporte%20Sistema%20Quevedo")
    
    # Enlace Directo a Clínica Referencia
    col_link3.link_button("🏥 CLÍNICA REFERENCIA", "https://www.referencia.do")


    
# --- MÓDULO FINANZAS: INTELIGENTE Y PERSISTENTE ---
elif menu == "💰 FINANZAS":
    st.header("💰 Gestión Financiera Inteligente")

    # 1. PERSISTENCIA REAL: Asegurar tablas
    c.execute("CREATE TABLE IF NOT EXISTS presupuesto (id INTEGER PRIMARY KEY, monto REAL)")
    c.execute("INSERT OR IGNORE INTO presupuesto (id, monto) VALUES (1, 0.0)")
    c.execute("CREATE TABLE IF NOT EXISTS finanzas (id INTEGER PRIMARY KEY AUTOINCREMENT, tipo TEXT, categoria TEXT, monto REAL, fecha TEXT)")
    conn.commit()

    # 2. INTERFAZ LIMPIA Y MENÚ INTELIGENTE
    with st.container():
        col1, col2, col3 = st.columns([1, 1, 1])
        
        tipo = col1.selectbox("Tipo", ["GASTO", "INGRESO"])
        
        # El menú cambia o desaparece según la elección
        if tipo == "GASTO":
            cat = col2.selectbox("Categoría de Gasto", ["Farmacia", "Salud", "Supermercado", "Hogar", "Transporte", "Otros"])
        else:
            cat = col2.text_input("Origen del Ingreso", placeholder="Ej: Pago, Depósito")
            
        monto = col3.number_input("Monto RD$", min_value=0.0, step=100.0)

        if st.button("🚀 REGISTRAR MOVIMIENTO"):
            if monto > 0:
                monto_final = -monto if tipo == "GASTO" else monto
                fecha_hoy = datetime.now(ZONA_HORARIA).strftime("%d/%m/%Y")
                c.execute("INSERT INTO finanzas (tipo, categoria, monto, fecha) VALUES (?,?,?,?)",
                          (tipo, cat, monto_final, fecha_hoy))
                conn.commit()
                st.rerun()

    st.divider()

    # 3. CÁLCULO DE PRESUPUESTO (SUMA Y RESTA)
    df_f = pd.read_sql_query("SELECT * FROM finanzas", conn)
    pres_base = pd.read_sql_query("SELECT monto FROM presupuesto WHERE id = 1", conn)['monto'][0]
    
    ingresos = df_f[df_f['monto'] > 0]['monto'].sum() if not df_f.empty else 0
    gastos = abs(df_f[df_f['monto'] < 0]['monto'].sum()) if not df_f.empty else 0
    balance_total = pres_base + ingresos - gastos

    m1, m2, m3 = st.columns(3)
    m1.metric("📥 INGRESOS", f"RD$ {ingresos:,.2f}")
    m2.metric("📤 GASTOS", f"RD$ {gastos:,.2f}", delta_color="inverse")
    m3.metric("💎 DISPONIBLE", f"RD$ {balance_total:,.2f}")

    st.divider()

    # 4. DISEÑO DE REGISTROS: BOTÓN AL LADO
    st.subheader("📋 Historial de Movimientos")
    if not df_f.empty:
        # Mostramos los últimos primero
        for idx, row in df_f.sort_index(ascending=False).iterrows():
            # Una sola fila para todo el registro
            r_col1, r_col2, r_col3, r_col4 = st.columns([1.5, 2.5, 2, 0.5])
            
            r_col1.write(row['fecha'])
            r_col2.write(f"**{row['categoria']}**")
            
            color = "#ff4b4b" if row['monto'] < 0 else "#4CAF50"
            r_col3.markdown(f"<span style='color:{color}; font-weight:bold;'>RD$ {abs(row['monto']):,.2f}</span>", unsafe_allow_html=True)
            
            # Botón de borrado a la derecha (mismo nivel)
            if r_col4.button("🗑️", key=f"del_{row['id']}"):
                c.execute("DELETE FROM finanzas WHERE id = ?", (row['id'],))
                conn.commit()
                st.rerun()
    else:
        st.info("No hay movimientos registrados.")

    # Ajuste de base (Para que el presupuesto tenga sentido)
    with st.expander("⚙️ AJUSTAR CAPITAL INICIAL"):
        nuevo_p = st.number_input("Capital base en cuenta RD$", value=float(pres_base))
        if st.button("Actualizar Capital"):
            c.execute("UPDATE presupuesto SET monto = ? WHERE id = 1", (nuevo_p,))
            conn.commit()
            st.rerun()


# --- MÓDULO BIOMONITOR: RECONSTRUCCIÓN ANTI-ERRORES ---
elif menu == "🩺 BIOMONITOR":
    st.header("🩺 Control de Glucosa y Biomonitoreo")

    # 1. REPARACIÓN AUTOMÁTICA DE TABLA
    c.execute("CREATE TABLE IF NOT EXISTS glucosa (id INTEGER PRIMARY KEY AUTOINCREMENT, valor REAL, unidad TEXT, estado TEXT, fecha TEXT, hora TEXT)")
    
    # Esto asegura que si la tabla existía pero era vieja, se actualice sin morir
    columnas_necesarias = ["unidad", "estado", "fecha", "hora"]
    for col in columnas_necesarias:
        try:
            c.execute(f"ALTER TABLE glucosa ADD COLUMN {col} TEXT")
        except:
            pass 
    conn.commit()

    # 2. ENTRADA DE DATOS
    with st.container():
        col_g1, col_g2, col_g3 = st.columns([1, 1, 1])
        valor_glucosa = col_g1.number_input("Nivel de Glucosa", min_value=0.0, step=0.1, format="%.1f")
        col_g2.markdown("<br><b>mg/dL</b>", unsafe_allow_html=True)
        
        if col_g3.button("💾 REGISTRAR LECTURA"):
            if valor_glucosa > 0:
                # Semáforo de salud
                if valor_glucosa > 180: est = "CRÍTICO 🔴"
                elif valor_glucosa > 130: est = "ALERTA 🟡"
                elif valor_glucosa >= 70: est = "NORMAL 🟢"
                else: est = "BAJO 🔵"
                
                f_actual = datetime.now(ZONA_HORARIA).strftime("%d/%m/%Y")
                h_actual = datetime.now(ZONA_HORARIA).strftime("%I:%M %p")
                
                c.execute("INSERT INTO glucosa (valor, unidad, estado, fecha, hora) VALUES (?,?,?,?,?)",
                          (valor_glucosa, "mg/dL", est, f_actual, h_actual))
                conn.commit()
                st.rerun()

    st.divider()

    # 3. VISUALIZACIÓN DE DATOS (Con manejo de errores para evitar pantalla en blanco)
    try:
        df_g = pd.read_sql_query("SELECT * FROM glucosa ORDER BY id DESC", conn)
        
        if not df_g.empty:
            # Gráfico con manejo de excepciones
            fig = px.line(df_g, x="fecha", y="valor", title="📈 Evolución de Glucosa", markers=True)
            st.plotly_chart(fig, use_container_width=True)

            # Historial compacto
            st.subheader("📋 Historial de Lecturas")
            for idx, row in df_g.iterrows():
                # Verificamos que los datos no sean None para que no explote
                val = row['valor'] if row['valor'] else 0.0
                uni = row['unidad'] if row['unidad'] else "mg/dL"
                est_text = row['estado'] if row['estado'] else "Sin estado"
                
                c1, c2, c3, c4, c5 = st.columns([1.5, 1.5, 1.5, 2, 0.5])
                c1.write(row['fecha'])
                c2.write(row['hora'])
                c3.write(f"**{val}** {uni}")
                c4.write(est_text)
                
                if c5.button("🗑️", key=f"del_g_{row['id']}"):
                    c.execute("DELETE FROM glucosa WHERE id = ?", (row['id'],))
                    conn.commit()
                    st.rerun()
        else:
            st.info("Aún no hay registros de glucosa.")
    except Exception as e:
        st.warning("El sistema está sincronizando la base de datos. Por favor, registre un valor para finalizar la configuración.")             
          




 
           
# --- MÓDULO AGENDA MÉDICA: REPARACIÓN FORZADA Y LIMPIEZA ---
elif menu == "💊 AGENDA MÉDICA":
    st.header("💊 Gestión Médica Integral")

    # 1. REPARACIÓN DE TABLAS (Medicinas y Citas)
    c.execute("CREATE TABLE IF NOT EXISTS medicinas (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS citas (id INTEGER PRIMARY KEY AUTOINCREMENT, doctor TEXT)")
    
    # Reparar Medicinas
    for col, tipo in [("dosis","TEXT"), ("frecuencia","TEXT"), ("horario","TEXT"), ("periodo","TEXT")]:
        try: c.execute(f"ALTER TABLE medicinas ADD COLUMN {col} {tipo}")
        except: pass
    
    # Reparar Citas (Esto quita el OperationalError de la línea 346)
    for col, tipo in [("clinica","TEXT"), ("fecha","TEXT"), ("hora","TEXT"), ("periodo","TEXT"), ("motivo","TEXT")]:
        try: c.execute(f"ALTER TABLE citas ADD COLUMN {col} {tipo}")
        except: pass
    conn.commit()

    tab1, tab2 = st.tabs(["💊 Medicamentos", "📅 Citas Médicas"])

    # --- SECCIÓN 1: MEDICAMENTOS ---
    with tab1:
        with st.form("form_medicina", clear_on_submit=True):
            st.subheader("➕ Registrar Medicamento")
            m1, m2 = st.columns(2)
            n_med = m1.text_input("Nombre", placeholder="Ej: Metformina")
            d_med = m2.text_input("Dosis", value="500 mg")
            m3, m4, m5 = st.columns(3)
            f_med = m3.selectbox("Frecuencia", ["Cada 8h", "Cada 12h", "1 vez al día", "Según necesidad"])
            h_med = m4.selectbox("Hora ", [f"{i}:00" for i in range(1, 13)])
            p_med = m5.selectbox("Periodo ", ["AM", "PM"])
            if st.form_submit_button("💾 GUARDAR MEDICINA"):
                if n_med:
                    c.execute("INSERT INTO medicinas (nombre, dosis, frecuencia, horario, periodo) VALUES (?,?,?,?,?)",
                              (n_med, d_med, f_med, h_med, p_med))
                    conn.commit()
                    st.rerun()

        st.subheader("📋 Lista de Tratamientos")
        df_m = pd.read_sql_query("SELECT * FROM medicinas", conn)
        for idx, row in df_m.iterrows():
            c1, c2, c3 = st.columns([4, 4, 1])
            c1.write(f"💊 **{row['nombre']}** ({row['dosis']})")
            c2.write(f"⏰ {row['horario']} {row['periodo']} - {row['frecuencia']}")
            if c3.button("🗑️", key=f"del_m_{row['id']}"):
                c.execute("DELETE FROM medicinas WHERE id = ?", (row['id'],))
                conn.commit()
                st.rerun()

    # --- SECCIÓN 2: DEPARTAMENTO DE CITAS ---
    with tab2:
        with st.form("form_cita", clear_on_submit=True):
            st.subheader("➕ Agendar Cita")
            c1, c2 = st.columns(2)
            doc = c1.text_input("Doctor")
            cli = c2.text_input("Clínica")
            c3, c4, c5 = st.columns(3)
            fec = c3.date_input("Fecha")
            hor = c4.selectbox("Hora", [f"{i}:00" for i in range(1, 13)])
            per = c5.selectbox("Periodo", ["AM", "PM"])
            mot = st.text_input("Motivo")
            if st.form_submit_button("📅 REGISTRAR CITA"):
                if doc and cli:
                    c.execute("INSERT INTO citas (doctor, clinica, fecha, hora, periodo, motivo) VALUES (?,?,?,?,?,?)",
                              (doc, cli, str(fec), hor, per, mot))
                    conn.commit()
                    st.rerun()

        st.subheader("🗓️ Próximas Visitas")
        df_c = pd.read_sql_query("SELECT * FROM citas ORDER BY fecha ASC", conn)
        for idx, row in df_c.iterrows():
            r1, r2, r3 = st.columns([4, 4, 1])
            r1.markdown(f"👨‍⚕️ **{row['doctor']}**\n\n📍 {row['clinica']}")
            r2.write(f"📅 {row['fecha']} - {row['hora']} {row['periodo']}\n\n📝 {row['motivo']}")
            if r3.button("🗑️", key=f"del_c_{row['id']}"):
                c.execute("DELETE FROM citas WHERE id = ?", (row['id'],))
                conn.commit()
                st.rerun()
            st.divider()

    # Cierre de seguridad
    try: pass
    except: pass
  
# --- MÓDULO ESCÁNER IA: INTELIGENCIA Y COMUNICACIÓN DIRECTA ---
elif menu == "📸 ESCÁNER IA":
    st.header("📸 Estación de Escaneo IA")

    # 1. CONFIGURACIÓN DE CONTACTOS (Tus datos reales)
    MI_NUMERO = "18092714672"
    FARMACIA_VALUED = "18495060398"
    FARMACIA_GBC = "18296555546"

    # 2. BASE DE DATOS
    c.execute("CREATE TABLE IF NOT EXISTS archivos (id INTEGER PRIMARY KEY AUTOINCREMENT, tipo TEXT, fecha TEXT)")
    conn.commit()

    # 3. INTERFAZ DE ESCANEO (Cámara Trasera)
    st.subheader("🔍 Lector Inteligente de Documentos")
    foto = st.camera_input("Enfoca la receta o código", key="escanner_trasero")

    if foto:
        st.info("💡 IA: Documento detectado. ¿Qué deseas hacer?")
        
        col_e1, col_e2 = st.columns(2)
        tipo_doc = col_e1.selectbox("Clasificar como:", ["Receta Médica", "Cotización", "Resultado Lab", "QR"])
        
        if col_e2.button("💾 ARCHIVAR DOCUMENTO"):
            fecha_esc = datetime.now(ZONA_HORARIA).strftime("%d/%m/%Y %H:%M")
            c.execute("INSERT INTO archivos (tipo, fecha) VALUES (?,?)", (tipo_doc, fecha_esc))
            conn.commit()
            st.success("Guardado en el historial.")

        st.divider()
        
        # 4. BOTONES DE ACCIÓN REAL (SOLICITAR COTIZACIÓN)
        st.subheader("🚀 Solicitar Cotización vía WhatsApp")
        q1, q2 = st.columns(2)
        
        mensaje_base = "Hola, soy Luis Rafael. Adjunto mi receta para cotización de medicamentos."
        
        with q1:
            st.markdown(f"""
                <a href="https://wa.me/{FARMACIA_VALUED}?text={mensaje_base}" target="_blank" style="text-decoration: none;">
                    <div style="background-color: #0047AB; color: white; padding: 15px; text-align: center; border-radius: 10px; font-weight: bold; border: 2px solid white;">
                        🏥 FARMACIA VALUED
                    </div>
                </a>
                """, unsafe_allow_html=True)
                
        with q2:
            st.markdown(f"""
                <a href="https://wa.me/{FARMACIA_GBC}?text={mensaje_base}" target="_blank" style="text-decoration: none;">
                    <div style="background-color: #E31E24; color: white; padding: 15px; text-align: center; border-radius: 10px; font-weight: bold; border: 2px solid white;">
                        💊 FARMACIA GBC
                    </div>
                </a>
                """, unsafe_allow_html=True)

    st.divider()

    # 5. HISTORIAL DE ARCHIVOS
    st.subheader("📋 Historial de Escaneos")
    df_a = pd.read_sql_query("SELECT * FROM archivos ORDER BY id DESC", conn)
    
    if not df_a.empty:
        for idx, row in df_a.iterrows():
            r1, r2, r3 = st.columns([3, 4, 1])
            r1.write(f"📅 {row['fecha']}")
            r2.write(f"📄 **{row['tipo']}**")
            if r3.button("🗑️", key=f"del_arc_{row['id']}"):
                c.execute("DELETE FROM archivos WHERE id = ?", (row['id'],))
                conn.commit()
                st.rerun()
# --- FINAL DEL ESCÁNER IA (Cierre del historial) ---
    else:
        st.info("No hay documentos en el archivador.")

    # ESTO ES LO QUE ESTÁ FALTANDO Y CAUSA EL ERROR:
    try: pass
    except: pass

       





# --- ARCHIVADOR INTEGRAL (BÚSQUEDA INTELIGENTE MULTI-MÓDULO) ---
elif menu == "📂 ARCHIVADOR":
    st.header("📂 Archivador Inteligente v3.0")
    
    # 1. Entrada de búsqueda flexible
    q = st.text_input("🔍 Busca lo que sea (ej: 'glucosa', 'Metformina', 'Farmacia', 'doctor')...")
    
    if q:
        query = f"%{q.lower()}%"
        st.markdown(f"### 🔎 Resultados para: **{q}**")
        
        # COLUMNAS PARA ORGANIZAR RESULTADOS
        col_res_izq, col_res_der = st.columns(2)

        # 2. BÚSQUEDA EN SALUD (Agenda y Biomonitor)
        with col_res_izq:
            # Buscar en Medicamentos y Citas Médicas
            try:
                res_salud = pd.read_sql_query("""
                    SELECT 'Medicamento' as Origen, nombre as Detalle, frecuencia as Info FROM medicinas 
                    WHERE lower(nombre) LIKE ? 
                    UNION
                    SELECT 'Cita Médica' as Origen, doctor as Detalle, clinica as Info FROM citas 
                    WHERE lower(doctor) LIKE ? OR lower(clinica) LIKE ?
                """, conn, params=(query, query, query))
                
                if not res_salud.empty:
                    st.success("🩺 Hallazgos en Salud y Agenda")
                    st.table(res_salud)
            except:
                pass

        # 3. BÚSQUEDA EN DOCUMENTOS Y FINANZAS
        with col_res_der:
            # Buscar en el Archivador de Fotos (la tabla 'archivos' que creamos antes)
            try:
                res_docs = pd.read_sql_query("""
                    SELECT 'Documento' as Origen, tipo as Detalle, fecha as Info FROM archivos 
                    WHERE lower(tipo) LIKE ? OR lower(fecha) LIKE ?
                """, conn, params=(query, query))
                
                if not res_docs.empty:
                    st.warning("📂 Hallazgos en Documentos")
                    st.table(res_docs)
            except:
                pass

    st.divider()

    # --- 4. DISEÑO DE CARPETAS VISUALES ---
    st.subheader("📁 Carpetas del Archivador")
    
    # Categorías que definimos para tus documentos
    categorias = ["Receta Médica", "Resultado Lab", "Cotización"]
    
    for cat in categorias:
        with st.expander(f"📁 {cat.upper()}"):
            df_arch = pd.read_sql_query("SELECT * FROM archivos WHERE tipo = ?", conn, params=(cat,))
            
            if df_arch.empty:
                st.info(f"No hay {cat.lower()} guardadas.")
            else:
                for idx, row in df_arch.iterrows():
                    c1, c2, c3 = st.columns([5, 2, 1])
                    c1.write(f"📄 {row['tipo']}")
                    c2.caption(f"📅 {row['fecha']}")
                    # El botón de borrado lateral que tanto nos importa
                    if c3.button("🗑️", key=f"del_arc_v3_{row['id']}"):
                        c.execute("DELETE FROM archivos WHERE id = ?", (row['id'],))
                        conn.commit()
                        st.rerun()

    # Cierre de seguridad anti-SyntaxError
    try: pass
    except: pass


# --- ASISTENTE INTELIGENTE PRO ---
elif menu == "🤖 ASISTENTE":
    st.header(f"🤖 Asistente Virtual: {NOMBRE_PROPIETARIO}")
    
    # 1. BUSCADOR DENTRO DEL ASISTENTE
    st.subheader("🔍 Consulta Rápida al Sistema")
    q_asist = st.text_input("¿Qué deseas encontrar hoy? (ej: 'cita', 'azucar', 'enero')")
    
    if q_asist:
        query = f"%{q_asist.lower()}%"
        # Busca en todo simultáneamente
        res_total = pd.read_sql_query("""
            SELECT 'Médico' as Tipo, doctor as Detalle, fecha as Fecha FROM citas WHERE lower(doctor) LIKE ?
            UNION ALL
            SELECT 'Gasto' as Tipo, categoria as Detalle, monto as Fecha FROM finanzas WHERE lower(categoria) LIKE ?
            UNION ALL
            SELECT 'Medicina' as Tipo, nombre as Detalle, frecuencia as Fecha FROM medicinas WHERE lower(nombre) LIKE ?
        """, conn, params=(query, query, query))
        
        if not res_total.empty:
            st.dataframe(res_total, use_container_width=True)
        else:
            st.warning("No encontré registros con ese nombre.")

    st.divider()

    # 2. GENERADOR DE REPORTE INTEGRAL (PDF)
    st.subheader("📄 Generación de Expediente Oficial")
    if st.button("🚀 GENERAR REPORTE COMPLETO (PDF)"):
        pdf = FPDF()
        pdf.add_page()
        
        # Encabezado con Identidad
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(200, 10, "EXPEDIENTE INTEGRAL - QUEVEDO PRO", ln=True, align='C')
        pdf.set_font("Arial", '', 10)
        pdf.cell(200, 10, f"Generado el: {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=True, align='C')
        pdf.line(10, 30, 200, 30)
        pdf.ln(10)

        # SECCIÓN 1: SALUD (Esto es lo que te faltaba)
        pdf.set_font("Arial", 'B', 12)
        pdf.set_fill_color(230, 230, 230)
        pdf.cell(190, 10, " I. RESUMEN MÉDICO Y BIOMONITOR", ln=True, fill=True)
        pdf.set_font("Arial", '', 10)
        
        # Glucosa
        df_g = pd.read_sql_query("SELECT * FROM glucosa ORDER BY id DESC LIMIT 5", conn)
        pdf.cell(200, 7, "Últimos niveles de Glucosa:", ln=True)
        for _, r in df_g.iterrows():
            pdf.cell(200, 7, f" - {r['fecha']}: {r['valor']} mg/dL ({r['estado']})", ln=True)
        
        # Citas
        df_c = pd.read_sql_query("SELECT * FROM citas ORDER BY fecha DESC LIMIT 5", conn)
        pdf.ln(5)
        pdf.cell(200, 7, "Próximas Citas Médicas:", ln=True)
        for _, r in df_c.iterrows():
            pdf.cell(200, 7, f" - {r['fecha']} con {r['doctor']} en {r['centro']}", ln=True)

        pdf.ln(10)

        # SECCIÓN 2: FINANZAS
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(190, 10, " II. ESTADO FINANCIERO", ln=True, fill=True)
        pdf.set_font("Arial", '', 10)
        df_f = pd.read_sql_query("SELECT * FROM finanzas ORDER BY id DESC LIMIT 10", conn)
        for _, r in df_f.iterrows():
            pdf.cell(200, 7, f" - {r['fecha']} | {r['categoria']} | RD$ {r['monto']}", ln=True)

        # Salvar y Descargar
        pdf.output("Reporte_Quevedo_Total.pdf")
        with open("Reporte_Quevedo_Total.pdf", "rb") as f:
            st.download_button("📥 DESCARGAR EXPEDIENTE COMPLETO", f, file_name=f"Reporte_Quevedo_{datetime.now().strftime('%d_%m')}.pdf")



# --- PIE DE PÁGINA Y CRÉDITOS ---
st.markdown("---")  # Línea divisoria visual

# Estilo para fijar el pie de página (opcional, se ve más profesional)
footer_style = """
    <style>
    .footer {
        position: fixed;
        left: 0;
        bottom: 0;
        width: 100%;
        background-color: #0e1117;
        color: #4CAF50;
        text-align: center;
        padding: 10px;
        font-size: 14px;
        border-top: 1px solid #4CAF50;
        z-index: 999;
    }
    </style>
    <div class="footer">
        <b>SISTEMA QUEVEDO PRO v3.5</b> | Diseñado por: <b>LUIS RAFAEL QUEVEDO</b> | 
        📍 Santo Domingo, Rep. Dom. | © 2026 Todos los derechos reservados
    </div>
"""

# Renderizar el pie de página
st.markdown(footer_style, unsafe_allow_html=True)

# Si prefieres un pie de página sencillo que ruede con el texto, usa este:
# st.info("💎 **Diseño y Desarrollo:** Luis Rafael Quevedo | Santo Domingo, R.D. 2026")
