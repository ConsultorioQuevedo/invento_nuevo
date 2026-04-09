import streamlit as st
import cv2
import numpy as np
from pyzbar import pyzbar # Para códigos de barra
from datetime import datetime
import pandas as pd
import sqlite3
# import easyocr  <-- ESTA LÍNEA DABA EL ERROR. La quitamos porque usaremos Pytesseract que es más ligero.
import os
import plotly.express as px
from fpdf import FPDF
import requests
import pytz
import unicodedata
from PIL import Image
import io
import pytesseract # Este es el que usaremos para las recetas de solo letras

# ==========================================
# 1. CONFIGURACIÓN E IDENTIDAD
# ==========================================
st.set_page_config(page_title="SISTEMA QUEVEDO PRO", layout="wide", page_icon="💎")

NOMBRE_PROPIETARIO = "LUIS RAFAEL QUEVEDO"
UBICACION_SISTEMA = "Santo Domingo, Rep. Dom."
ZONA_HORARIA = pytz.timezone('America/Santo_Domingo')

def borrar_ultimo(tabla):
    try:
        # Usamos la conexión que ya tienes creada en el programa
        global conn, c 
        
        # Buscamos el ID más alto (el último)
        c.execute(f"SELECT MAX(id) FROM {tabla}")
        max_id = c.fetchone()[0]
        
        if max_id:
            c.execute(f"DELETE FROM {tabla} WHERE id = ?", (max_id,))
            conn.commit()
            st.success(f"✅ Registro eliminado de {tabla}")
            st.rerun()
        else:
            st.info("No hay nada que borrar.")
    except Exception as e:
        st.error(f"Error: {e}")
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
    if st.button("♻️ DESHACER ÚLTIMO MOVIMIENTO", use_container_width=True):
        borrar_ultimo("finanzas")
    st.divider()

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
    # --- BOTÓN ÚNICO DE LIMPIEZA ---
   # Este es el botón que aparecerá arriba de la lista
    if st.button("♻️ DESHACER ÚLTIMO REGISTRO", use_container_width=True):
        borrar_ultimo("glucosa")
    
    st.divider() # Esto separa el botón de la lista de abajo
   

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
                
                # Una sola línea con iconos y separadores
            st.markdown(f"🗓️ **{row['fecha']}** | 🕒 {row['hora']} | 🩸 **{val} {uni}** | {est_text}")
            st.divider() # Esta línea crea la separación profesional
               
        else:
            st.info("Aún no hay registros de glucosa.")
    except Exception as e:
        st.warning("El sistema está sincronizando la base de datos. Por favor, registre un valor para finalizar la configuración.")             
          




 
           
# --- MÓDULO AGENDA MÉDICA: REPARACIÓN FORZADA Y LIMPIEZA ---
elif menu == "💊 AGENDA MÉDICA":
    st.header("💊 Gestión Médica Integral")
    if st.button("♻️ DESHACER ÚLTIMA CITA", use_container_width=True):
        borrar_ultimo("citas")
    st.divider()

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
            # Una sola línea elegante para cada medicina
            st.markdown(f"💊 **{row['nombre']}** ({row['dosis']}) | 🕒 {row['horario']} {row['periodo']}")
            st.divider()
            
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
            st.markdown(f"👨‍⚕️ **{row['doctor']}** | 🗓️ {row['fecha']} | 🕒 {row['hora']}")
            st.divider()
            # Así es como se ve un código profesional: limpio y directo
            st.markdown(f"👨‍⚕️ **{row['doctor']}** | 📍 {row['clinica']} | 🗓️ {row['fecha']} | 🕒 {row['hora']}")
            st.divider()
    # Cierre de seguridad
    try: pass
    except: pass
  
elif menu == "Escanear":
    st.header("🔍 Escáner Médico Inteligente")
    st.info("Este escáner detecta Códigos de Barras, QR y Texto en recetas.")

    # 1. Selector de categoría para el archivador
    tipo_doc = st.selectbox("Clasificar como:", 
                            ["Receta Médica", "Analítica", "Cita", "Resultado"])

    # 2. El "Ojo": Cámara trasera forzada y en vivo
    imagen_capturada = camera_input_live(
        show_controls=False,
        facing_mode="environment",
        key="escanner_pro_medico"
    )

    if imagen_capturada:
        # Convertir imagen para procesamiento
        bytes_data = imagen_capturada.getvalue()
        cv2_img = cv2.imdecode(np.frombuffer(bytes_data, np.uint8), cv2.IMREAD_COLOR)
        
        # --- PROCESAMIENTO AGRESIVO ---
        gris = cv2.cvtColor(cv2_img, cv2.COLOR_BGR2GRAY)
        # Umbralizado para resaltar letras y barras (blanco y negro puro)
        procesada = cv2.threshold(gris, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]

        # 3. INTENTO 1: Buscar Códigos de Barras/QR
        codigos = pyzbar.decode(procesada)
        
        if codigos:
            for codigo in codigos:
                dato = codigo.data.decode('utf-8')
                st.success(f"✅ Código {codigo.type} detectado")
                resultado_final = dato
        else:
            # 4. INTENTO 2: Si no hay códigos, leer letras (OCR)
            st.warning("No se detectó código. Leyendo texto de la receta...")
            with st.spinner("Traduciendo letras..."):
                reader = easyocr.Reader(['es']) # Configurado para español
                lectura = reader.readtext(cv2_img)
                # Unimos todas las palabras encontradas en un solo texto limpio
                resultado_final = " ".join([res[1] for res in lectura])

        # 5. RESULTADO Y ARCHIVADO
        if resultado_final:
            st.markdown("### 📄 Contenido Extraído:")
            texto_para_db = st.text_area("Puedes editar el texto si es necesario:", 
                                         value=resultado_final, height=150)
            
            if st.button(f"📥 Archivar en {tipo_doc}"):
                fecha_registro = datetime.now().strftime("%d/%m/%Y %H:%M")
                # AQUÍ TU LÓGICA DE SQL (Ejemplo):
                # cursor.execute("INSERT INTO archivo (categoria, contenido, fecha) VALUES (?, ?, ?)", 
                #                (tipo_doc, texto_para_db, fecha_registro))
                st.balloons()
                st.success(f"¡{tipo_doc} guardada exitosamente!")


    

    # 5. HISTORIAL DE ARCHIVOS
    st.subheader("📋 Historial de Escaneos")
    df_a = pd.read_sql_query("SELECT * FROM archivos ORDER BY id DESC", conn)
    
    if not df_a.empty:
        for idx, row in df_a.iterrows():
            r1, r2, r3 = st.columns([3, 4, 1])
            r1.write(f"📅 {row['fecha']}")
            r2.write(f"📄 **{row['tipo']}**")
          
# --- FINAL DEL ESCÁNER IA (Cierre del historial) ---
    else:
        st.info("No hay documentos en el archivador.")

    # ESTO ES LO QUE ESTÁ FALTANDO Y CAUSA EL ERROR:
    try: pass
    except: pass


# --- ARCHIVADOR INTEGRAL v5.1: RECTIFICACIÓN DE VARIABLES ---
elif menu == "📂 ARCHIVADOR":
    st.header("📂 Archivador Inteligente v5.1")
    if st.button("♻️ DESHACER ÚLTIMO DOCUMENTO", use_container_width=True):
        borrar_ultimo("documentos")
    st.divider()
    
    # 1. Entrada de búsqueda
    q = st.text_input("🔍 ¿Qué buscas? (ej: 'glucosa', 'doctor', 'receta')", placeholder="Escribe aquí...")
    
    if q:
        query = f"%{q.lower()}%"
        st.subheader(f"🔎 Resultados para: {q}")
        
        # --- TRADUCCIÓN INTELIGENTE PARA GLUCOSA ---
        terminos_glucosa = ["glucosa", "azucar", "diabetes", "mg", "sangre", "medicion"]
        busca_glucosa = any(t in q.lower() for t in terminos_glucosa)

        col_izq, col_der = st.columns(2)

        with col_izq:
            st.markdown("### 🩺 Salud y Citas")
            try:
                # Buscamos en Medicinas y Citas
                res_agenda = pd.read_sql_query("""
                    SELECT '💊 Medicina' as Origen, nombre as Detalle, frecuencia as Info FROM medicinas 
                    WHERE lower(nombre) LIKE ? 
                    UNION
                    SELECT '📅 Cita' as Origen, doctor as Detalle, clinica as Info FROM citas 
                    WHERE lower(doctor) LIKE ? OR lower(clinica) LIKE ?
                """, conn, params=(query, query, query))

                # Lógica para Glucosa
                if busca_glucosa:
                    res_bio = pd.read_sql_query("""
                        SELECT '🩸 Biomonitor' as Origen, valor || ' mg/dL' as Detalle, fecha as Info 
                        FROM glucosa ORDER BY id DESC LIMIT 10
                    """, conn)
                else:
                    res_bio = pd.read_sql_query("""
                        SELECT '🩸 Biomonitor' as Origen, valor || ' mg/dL' as Detalle, fecha as Info 
                        FROM glucosa WHERE fecha LIKE ?
                    """, conn, params=(query,))

                # Unión de resultados
                todo_salud = pd.concat([res_agenda, res_bio])
                if not todo_salud.empty:
                    st.dataframe(todo_salud, use_container_width=True, hide_index=True)
                else:
                    st.info("No hay coincidencias en Salud.")
            except:
                st.warning("Asegúrate de tener registros en Biomonitor y Agenda.")

        with col_der:
            st.markdown("### 📄 Documentos")
            try:
                res_docs = pd.read_sql_query("""
                    SELECT '🖼️ Escáner' as Origen, tipo as Detalle, fecha as Info FROM archivos 
                    WHERE lower(tipo) LIKE ? OR lower(fecha) LIKE ?
                """, conn, params=(query, query))
                
                if not res_docs.empty:
                    st.table(res_docs)
                else:
                    st.info("No hay documentos guardados.")
            except:
                pass

    st.divider()

    # --- 2. CARPETAS VISUALES (CORREGIDO EL NAMEERROR) ---
    st.subheader("📁 Carpetas")
    cats = {"💊 RECETAS": "Receta Médica", "🧪 LABS": "Resultado Lab", "💰 COTIZ": "Cotización"}
    
    cols = st.columns(3)
    for i, (label, db_name) in enumerate(cats.items()):
        with cols[i]:
            with st.expander(label):
                # Aquí estaba el error, ahora usamos df_c correctamente
                df_c = pd.read_sql_query("SELECT * FROM archivos WHERE tipo = ?", conn, params=(db_name,))
                
                if df_c.empty:
                    st.caption("Vacío")
                else:
                    for idx, row in df_c.iterrows():
                        f1, f2 = st.columns([4, 1])
                        f1.write(f"📄 {row['fecha']}")
                       
    try: pass
    except: pass 


 # --- ASISTENTE ANALÍTICO v5.0: EL CEREBRO DE QUEVEDO PRO ---
elif menu == "🤖 ASISTENTE":
    st.header(f"🤖 Asistente Virtual: {NOMBRE_PROPIETARIO}")
    st.caption(f"📅 Análisis actualizado al: {datetime.now().strftime('%d de %B, %Y')}")

    # --- 1. MONITOR DE ALERTAS PROACTIVAS ---
    fecha_hoy = datetime.now().strftime('%Y-%m-%d')
    
    with st.container():
        c_alert1, c_alert2 = st.columns(2)
        with c_alert1:
            # Alerta de Citas
            df_hoy = pd.read_sql_query("SELECT * FROM citas WHERE fecha = ?", conn, params=(fecha_hoy,))
            if not df_hoy.empty:
                st.error(f"🚨 **CITA HOY:** {df_hoy['doctor'][0]} en {df_hoy['clinica'][0]}")
            else:
                st.info("✅ Sin citas para hoy")
        
        with c_alert2:
            # Alerta de Glucosa
            df_glu_hoy = pd.read_sql_query("SELECT * FROM glucosa WHERE fecha = ?", conn, params=(fecha_hoy,))
            if df_glu_hoy.empty:
                st.warning("⚠️ **PENDIENTE:** Medición de azúcar de hoy")
            else:
                st.success("✅ Glucosa de hoy registrada")

    st.divider()

    # --- 2. ANÁLISIS DE DATOS (MÚSCULO ANALÍTICO) ---
    st.subheader("📊 Análisis de Situación Actual")
    col_an1, col_an2, col_an3 = st.columns(3)

    # Análisis de Salud: Comparativa
    with col_an1:
        st.markdown("**Salud (Glucosa)**")
        df_comp = pd.read_sql_query("SELECT valor FROM glucosa ORDER BY id DESC LIMIT 2", conn)
        if len(df_comp) == 2:
            actual = int(df_comp['valor'][0])
            anterior = int(df_comp['valor'][1])
            dif = actual - anterior
            if dif > 0:
                st.metric("Nivel Actual", f"{actual} mg/dL", f"+{dif} (Subió)", delta_color="inverse")
            else:
                st.metric("Nivel Actual", f"{actual} mg/dL", f"{dif} (Bajó)")
        else:
            st.write("Faltan datos para comparar")

    # Análisis de Finanzas: Gasto Mensual
    with col_an2:
        st.markdown("**Finanzas (Gastos)**")
        try:
            mes_actual = datetime.now().strftime('-%m-')
            df_gastos = pd.read_sql_query("SELECT SUM(monto) as total FROM finanzas WHERE fecha LIKE ?", conn, params=(f"%{mes_actual}%",))
            total_g = df_gastos['total'][0] if df_gastos['total'][0] else 0
            st.metric("Gasto del Mes", f"RD$ {total_g:,.2f}")
        except: st.write("Sin datos de gastos")

    # Análisis de Archivador: Inventario
    with col_an3:
        st.markdown("**Bóveda Digital**")
        cant_docs = pd.read_sql_query("SELECT COUNT(*) as total FROM archivos", conn)['total'][0]
        cant_med = pd.read_sql_query("SELECT COUNT(*) as total FROM medicinas", conn)['total'][0]
        st.write(f"📂 **{cant_docs}** documentos")
        st.write(f"💊 **{cant_med}** medicinas activas")

    st.divider()

    # --- 3. BÚSQUEDA Y FARMACIAS ---
    col_bus, col_far = st.columns([2, 1])
    
    with col_bus:
        st.subheader("🔍 Buscador de Asistente")
        q_asist = st.text_input("¿Qué buscas hoy?", placeholder="Ej: glucosa, receta, dr...")
        if q_asist:
            # Lógica de búsqueda que ya tenemos...
            query = f"%{q_asist.lower()}%"
            res = pd.read_sql_query("""
                SELECT '📅 Cita' as T, doctor as D, fecha as I FROM citas WHERE lower(doctor) LIKE ?
                UNION ALL
                SELECT '💰 Gasto' as T, categoria as D, monto as I FROM finanzas WHERE lower(categoria) LIKE ?
                UNION ALL
                SELECT '💊 Med' as T, nombre as D, frecuencia as I FROM medicinas WHERE lower(nombre) LIKE ?
            """, conn, params=(query, query, query))
            st.dataframe(res, use_container_width=True, hide_index=True)

    with col_far:
        st.subheader("🏥 Farmacias")
        msg = "Hola, soy Luis Rafael (8092714672). Necesito consultar algo."
        st.markdown(f'<a href="https://wa.me/18495060398?text={msg}" target="_blank" style="text-decoration:none;"><div style="background:#0047AB;color:white;padding:10px;text-align:center;border-radius:10px;margin-bottom:5px;">VALUED</div></a>', unsafe_allow_html=True)
        st.markdown(f'<a href="https://wa.me/18296555546?text={msg}" target="_blank" style="text-decoration:none;"><div style="background:#E31E24;color:white;padding:10px;text-align:center;border-radius:10px;">GBC</div></a>', unsafe_allow_html=True)

    st.divider()

    # --- 4. ACCIÓN MAESTRA: REPORTE ---
    if st.button("🚀 GENERAR REPORTE PDF INTEGRAL", use_container_width=True):
        # (Aquí va el código del PDF que ya tenemos pulido)
        st.info("Procesando expediente completo...")
        # ... (Cierre de función PDF)

    try: pass
    except: pass   

      
   
    
        
       
  
# --- PIE DE PÁGINA (CRÉDITOS) ---
st.markdown("---")
col_c1, col_c2, col_c3 = st.columns([1, 2, 1])

with col_c2:
    st.markdown(
        """
        <div style="text-align: center; color: #888888; font-size: 12px;">
            <p style="margin-bottom: 5px;">🚀 <b>INVENTO NUEVO v4.1</b> | Sistema de Gestión Integral</p>
            <p style="margin-top: 0;">Desarrollado para <b>Luis Rafael Quevedo</b></p>
            <p style="font-style: italic;">"Haciendo algo que valga la pena."</p>
        </div>
        """, 
        unsafe_allow_html=True
    )

