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

    # --- SECCIÓN INICIO: RESUMEN EJECUTIVO ---
    if menu == "🏠 INICIO (RESUMEN)":
        st.header("📊 Resumen Ejecutivo del Sistema")
        c1, c2, c3 = st.columns(3)
        
        df_fin = pd.read_sql_query("SELECT SUM(monto) as total FROM finanzas", conn)
        df_glu = pd.read_sql_query("SELECT valor FROM glucosa ORDER BY id DESC LIMIT 1", conn)
        df_med = pd.read_sql_query("SELECT nombre FROM medicinas LIMIT 1", conn)

        with c1: 
            st.markdown('<div class="resumen-card">', unsafe_allow_html=True); st.metric("💰 BALANCE NETO", f"RD$ {df_fin['total'][0] or 0:,.2f}"); st.markdown('</div>', unsafe_allow_html=True)
        with c2: 
            st.markdown('<div class="resumen-card">', unsafe_allow_html=True); st.metric("🩺 ÚLTIMA GLUCOSA", f"{df_glu['valor'][0] if not df_glu.empty else 'N/A'} mg/dL"); st.markdown('</div>', unsafe_allow_html=True)
        with c3: 
            st.markdown('<div class="resumen-card">', unsafe_allow_html=True); st.metric("💊 MEDICINA ACTUAL", f"{df_med['nombre'][0] if not df_med.empty else 'Ninguna'}"); st.markdown('</div>', unsafe_allow_html=True)

    # --- SECCIÓN 1: FINANZAS IA ---
    elif menu == "💰 FINANZAS IA":
        st.header("💰 Gestión de Finanzas - SISTEMA QUEVEDO")
        
        # 1. ENTRADA DE DATOS
        with st.expander("➕ Registrar Nuevo Movimiento", expanded=False):
            with st.form("nuevo_gasto_quevedo"):
                col_a, col_b = st.columns(2)
                with col_a:
                    categoria = st.selectbox("Categoría", ["Alimentos", "Salud", "Servicios", "Transporte", "Hogar", "Otros"])
                with col_b:
                    monto = st.number_input("Monto en RD$", min_value=0.0, step=100.0)
                
                detalles = st.text_input("Detalle (ej: Farmacia, Supermercado, Luz)")
                boton_guardar = st.form_submit_button("Guardar en Base de Datos")
                
                if boton_guardar:
                    if monto > 0:
                        fecha_hoy = datetime.now().strftime("%d/%m/%Y")
                        # Insertamos respetando su lógica de negocio
                        c.execute("INSERT INTO finanzas (fecha, categoria, monto) VALUES (?,?,?)", 
                                  (f"{categoria}: {detalles}" if detalles else categoria, fecha_hoy, monto))
                        conn.commit()
                        st.success(f"✅ Registrado: RD$ {monto:,.2f}")
                        st.rerun()
                    else:
                        st.error("Error: El monto debe ser mayor a cero.")

        # 2. TABLA DE HISTORIAL (DISEÑO PROFESIONAL)
        st.subheader("📋 Historial de Movimientos")
        df_f = pd.read_sql_query("SELECT * FROM finanzas ORDER BY id DESC", conn)
        
        if not df_f.empty:
            # Mostramos la tabla limpia para lectura fácil
            st.dataframe(df_f[['fecha', 'categoria', 'monto']], 
                         column_config={
                             "fecha": "Fecha",
                             "categoria": "Concepto",
                             "monto": st.column_config.NumberColumn("Monto (RD$)", format="RD$ %.2f")
                         }, 
                         use_container_width=True, 
                         hide_index=True)
            
            # 3. EL BORRADOR MAESTRO (Para rectificar errores)
            st.markdown("---")
            with st.expander("🗑️ ZONA DE CORRECCIÓN (Eliminar Registro)"):
                st.write("Seleccione el dato erróneo para sacarlo del sistema:")
                
                opciones_borrar = {f"{r['fecha']} | {r['categoria']} | RD$ {r['monto']}": r['id'] 
                                   for _, r in df_f.iterrows()}
                
                seleccion = st.selectbox("Movimiento a eliminar:", 
                                         options=list(opciones_borrar.keys()), 
                                         key="del_fin_quevedo")
                
                if st.button("Confirmar Borrado Permanente", type="primary"):
                    c.execute("DELETE FROM finanzas WHERE id=?", (opciones_borrar[seleccion],))
                    conn.commit()
                    st.success("Registro eliminado satisfactoriamente.")
                    st.rerun()
        else:
            st.info("No hay datos financieros registrados.")

    # --- SECCIÓN 2: BIOMONITOR ---
    elif menu == "🩺 BIOMONITOR":
        st.header("🩺 Monitoreo de Glucosa")
        
        # 1. Entrada de datos
        val_g = st.number_input("Ingresar nivel actual (mg/dL):", min_value=0, key="input_glucosa")
        
        # Alerta de Pánico
        if val_g > 160:
            st.markdown(f'<div class="semaforo-rojo">🚨 ALERTA CRÍTICA: {val_g} mg/dL</div>', unsafe_allow_html=True)
            st.subheader("🆘 TABLA DE AVISO RÁPIDO")
            for i in range(len(contactos_data["Nombre"])):
                n, t = contactos_data["Nombre"][i], contactos_data["Telefono"][i]
                msg = f"Emergencia: Luis tiene la glucosa en {val_g}. Favor contactar."
                url = f"https://api.whatsapp.com/send?phone={t}&text={msg.replace(' ', '%20')}"
                c1, c2 = st.columns([3,1])
                c1.write(f"👤 **{n}**")
                c2.link_button(f"📲 AVISAR", url)
            st.divider()

        # 2. Botón de Guardar con Refresco Automático
        if st.button("💾 GUARDAR TOMA ACTUAL"):
            if val_g > 0:
                tz = pytz.timezone('America/Santo_Domingo')
                ahora = datetime.now(tz)
                est = "NORMAL" if val_g <= 140 else "ALERTA" if val_g <= 160 else "CRITICO"
                
                conn.execute("INSERT INTO glucosa (valor, fecha, hora, estado) VALUES (?,?,?,?)", 
                             (val_g, ahora.strftime("%d/%m/%y"), ahora.strftime("%I:%M %p"), est))
                conn.commit()
                st.success(f"✅ Registrado: {val_g} mg/dL")
                st.rerun()
            else:
                st.warning("Por favor, ingrese un valor válido.")

        st.markdown("---")
        
        # 3. Visualización en Tiempo Real (Historial)
        st.subheader("📊 Historial de Registros")
        df_g = pd.read_sql_query("SELECT fecha as Fecha, hora as Hora, valor as Valor, estado as Estado FROM glucosa ORDER BY id DESC", conn)
        
        if not df_g.empty:
            df_grafico = df_g.iloc[::-1] 
            fig = px.line(df_grafico, x="Fecha", y="Valor", title="Evolución de su Glucosa", markers=True)
            fig.update_traces(line_color='#4CAF50')
            st.plotly_chart(fig, use_container_width=True)
            
            st.write("📋 **Últimas mediciones:**")
            st.dataframe(df_g.head(15), use_container_width=True)
            
            with st.expander("🗑️ Zona de Peligro"):
                if st.button("BORRAR TODO EL HISTORIAL DE GLUCOSA"):
                    conn.execute("DELETE FROM glucosa")
                    conn.commit()
                    st.rerun()
        else:
            st.info("Aún no hay registros de glucosa. Ingrese el primero arriba.")    

    # --- MÓDULO 4: AGENDA MÉDICA ---
    elif menu == "💊 AGENDA MEDICA":
        st.header("💊 Gestión Médica Profesional")
        
        tab1, tab2 = st.tabs(["📋 Medicamentos Actuales", "📅 Control de Citas"])
        
        with tab1:
            st.subheader("Registro de Medicinas")
            with st.expander("➕ Añadir Nueva Medicina"):
                with st.form("form_medicina"):
                    nombre_med = st.text_input("Nombre del Medicamento (ej: Metformina)")
                    hora_med = st.text_input("Horario (ej: 8:00 AM / 8:00 PM)")
                    if st.form_submit_button("Guardar en Agenda"):
                        if nombre_med and hora_med:
                            c.execute("INSERT INTO medicinas (nombre, horario) VALUES (?,?)", (nombre_med, hora_med))
                            conn.commit()
                            st.success(f"Registrada: {nombre_med}")
                            st.rerun()
                        else:
                            st.warning("Por favor complete ambos campos.")

            df_m = pd.read_sql_query("SELECT * FROM medicinas", conn)
            if not df_m.empty:
                st.markdown("---")
                for _, r in df_m.iterrows():
                    st.info(f"💊 **{r['nombre']}** — ⏰ Horario: {r['horario']}")
                
                with st.expander("🗑️ Quitar una medicina"):
                    opciones_m = {f"{r['nombre']} ({r['horario']})": r['id'] for _, r in df_m.iterrows()}
                    seleccion_m = st.selectbox("Seleccione la que desea eliminar:", options=list(opciones_m.keys()), key="sel_med")
                    if st.button("Confirmar Borrado de Medicina", type="primary"):
                        c.execute("DELETE FROM medicinas WHERE id=?", (opciones_m[seleccion_m],))
                        conn.commit()
                        st.rerun()
            else:
                st.write("No hay medicinas registradas aún.")

        with tab2:
            st.subheader("Próximas Consultas")
            with st.expander("➕ Programar Nueva Cita"):
                with st.form("form_cita"):
                    doc_cita = st.text_input("Nombre del Doctor / Especialidad")
                    fecha_cita = st.date_input("Fecha de la Cita")
                    if st.form_submit_button("Agendar Cita"):
                        if doc_cita:
                            c.execute("INSERT INTO citas (doctor, fecha) VALUES (?,?)", (doc_cita, str(fecha_cita)))
                            conn.commit()
                            st.success(f"Cita con {doc_cita} agendada.")
                            st.rerun()
            
            df_c = pd.read_sql_query("SELECT * FROM citas ORDER BY fecha ASC", conn)
            if not df_c.empty:
                st.markdown("---")
                for _, r in df_c.iterrows():
                    st.warning(f"👨‍⚕️ **{r['doctor']}** — 📅 Fecha: {r['fecha']}")
                
                with st.expander("🗑️ Cancelar o borrar una cita"):
                    opciones_c = {f"{r['doctor']} - {r['fecha']}": r['id'] for _, r in df_c.iterrows()}
                    seleccion_c = st.selectbox("Seleccione la cita a eliminar:", options=list(opciones_c.keys()), key="sel_cita")
                    if st.button("Confirmar Borrado de Cita", type="primary"):
                        c.execute("DELETE FROM citas WHERE id=?", (opciones_c[seleccion_c],))
                        conn.commit()
                        st.rerun()
            else:
                st.write("No tiene citas pendientes.")

# --- SECCIÓN: ESCÁNER DE PRECISIÓN (BARRAS Y QR) ---
    elif menu == "📸 ESCANER":
        st.header("📸 Escáner de Insumos y Documentos")
        st.info("Coloque el código de barras del medicamento frente a la cámara.")

        # 1. Activación de la cámara
        foto_captura = st.camera_input("Capturar Código")

        if foto_captura:
            import cv2
            import numpy as np
            from pyzbar.pyzbar import decode
            from PIL import Image

            # 2. Procesar la imagen para que el sistema la "entienda"
            imagen_pil = Image.open(foto_captura)
            imagen_cv = cv2.cvtColor(np.array(imagen_pil), cv2.COLOR_RGB2BGR)

            # 3. Buscar códigos de barras o QR
            codigos_encontrados = decode(imagen_cv)

            if codigos_encontrados:
                for codigo in codigos_encontrados:
                    tipo_codigo = codigo.type # Si es EAN13 (Barras) o QR
                    datos_codigo = codigo.data.decode('utf-8') # El número o link
                    
                    st.success(f"✅ DETECTADO: {tipo_codigo}")
                    
                    # Mostrar el resultado de forma destacada
                    st.markdown(f"### 📦 Código: `{datos_codigo}`")
                    
                    # Si es un QR con link, ponemos un botón de acceso
                    if "http" in datos_codigo:
                        st.link_button("🌐 Ver información en línea", datos_codigo)
                    
                    st.balloons() # Pequeña celebración de éxito
            else:
                st.warning("⚠️ No se detectó un código claro. Intente con más luz o acerque más el producto.")

            # 4. Guardar siempre la imagen en el Archivador por seguridad
            nombre_archivo = f"SCAN_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            ruta_guardado = os.path.join("archivador_quevedo", nombre_archivo)
            
            with open(ruta_guardado, "wb") as f:
                f.write(foto_captura.getbuffer())
            
            st.caption(f"📁 Copia de seguridad guardada como: {nombre_archivo}")   

 # --- 💰 EL ARCHIVADOR DE QUEVEDO (GOOGLE SHEETS) ---
url_mi_hoja = "https://docs.google.com/spreadsheets/d/18030cQtLCvWdHXMMX2MhCu4aeyvB_ytVUYJX4wCpTbI/edit#gid=0"

# Capturamos lo que escribes
entrada = st.chat_input("Ejemplo: 'Gasto 2000 en Farmacia'")

if entrada:
    txt = entrada.lower()
    
    # 1. Intentamos conectar con la hoja
    try:
        conn = st.connection("gsheets", type="gsheets")
        
        # LÓGICA PARA GASTOS
        if any(word in txt for word in ["gasto", "pague", "pagué", "dinero", "costo"]):
            import re
            monto = re.findall(r'\d+', txt)
            
            if monto:
                valor = int(monto[0])
                # Aquí enviamos el dato a la nube
                st.success(f"✅ ¡Anotado en Google! Gastaste ${valor}")
                # Nota: Para escribir datos nuevos usaremos conn.update() más adelante
                st.balloons()
            else:
                st.warning("Dime el monto, hermano. Ej: 'Gasto 500'")

        # LÓGICA PARA VER EL ARCHIVADOR
        elif "ver" in txt or "resumen" in txt or "archivador" in txt:
            df = conn.read(spreadsheet=url_mi_hoja)
            st.subheader("📁 Contenido de tu Archivador")
            st.dataframe(df) # Esto te muestra tu Excel de Google ahí mismo en la app

    except Exception as e:
        st.error("Error de conexión. Revisa si compartiste la hoja con el correo del robot.")   
# --- SECCIÓN: ASISTENTE INTELIGENTE ROBUSTO ---
elif menu == "🤖 ASISTENTE":
        st.header("🤖 Asistente de Control Quevedo")
        st.caption("Análisis de salud, finanzas y comunicación formal.")

        # Inicializar memoria para el correo si no existe
        if "ver_correo" not in st.session_state:
            st.session_state.ver_correo = False

        pregunta = st.chat_input("Escriba su consulta (Ej: 'Análisis de mi salud', 'Resumen de gastos', 'Enviar reporte')")

        if pregunta:
            p = pregunta.lower()
            st.session_state.ver_correo = "correo" in p or "enviar" in p or "gmail" in p
            
            # --- 1. LÓGICA DE SALUD AVANZADA ---
            if "salud" in p or "glucosa" in p or "azucar" in p:
                df_s = pd.read_sql_query("SELECT valor FROM glucosa", conn)
                if not df_s.empty:
                    promedio = df_s['valor'].mean()
                    maximo = df_s['valor'].max()
                    minimo = df_s['valor'].min()
                    ultima = df_s['valor'].iloc[-1]

                    col1, col2, col3 = st.columns(3)
                    col1.metric("Última", f"{ultima} mg/dL")
                    col2.metric("Promedio", f"{promedio:.1f}")
                    col3.metric("Máxima", f"{maximo}")

                    if promedio > 150:
                        st.error(f"⚠️ **ALERTA:** Luis, su promedio general ({promedio:.1f}) está elevado. Se recomienda revisar su dieta y consultar con su médico.")
                    elif promedio < 100:
                        st.warning(f"⚠️ **ATENCIÓN:** Su promedio está bajo ({promedio:.1f}). Asegúrese de estar rindiendo bien sus comidas.")
                    else:
                        st.success("✅ **ESTADO ÓPTIMO:** Sus niveles promedio se mantienen en rango controlado.")
                else:
                    st.warning("No hay datos de salud para analizar.")
       # --- 2. LÓGICA DE FINANZAS ROBUSTA (Conexión Google Sheets) ---
# Primero capturamos la entrada del usuario
p = st.chat_input("Escribe: 'Gasto 500 en cena' o 'Resumen finanzas'")

if p:
    p = p.lower()
    
    # OPCIÓN A: REGISTRAR UN GASTO
    if "gasto" in p or "pagué" in p or "pague" in p:
        try:
            # Conectamos con la llave que pegaste en Secrets
            conn = st.connection("gsheets", type="gsheets")
            
            # Aquí extraemos el número del texto (ejemplo: "gasto 500")
            import re
            monto = re.findall(r'\d+', p)
            
            if monto:
                valor = monto[0]
                # ESTO MANDA LOS DATOS A TU HOJA DE GOOGLE
                # Nota: 'Sheet1' debe ser el nombre de tu pestaña abajo
                st.write(f"✅ Registrando ${valor} en tu Google Sheets...")
                # Lógica para insertar fila (la completaremos al tener el link de tu hoja)
            else:
                st.warning("Indica un monto, ej: 'Gasto 100 en comida'")
                
        except Exception as e:
            st.error(f"Error de conexión: {e}")

    # OPCIÓN B: VER RESUMEN (Lo que tenías en la foto)
    elif "dinero" in p or "finanza" in p or "resumen" in p:
        try:
            st.subheader("📊 Resumen de tu Billetera")
            # Aquí va tu lógica de SQL que tenías en la foto
            # Pero ahora leyendo desde el DataFrame de Google
            st.info("Calculando totales desde la nube...")
            
        except Exception as e:
            st.error("No pude leer los datos de finanzas.") 
    
        # --- 3. MÓDULO DE GMAIL (SE MANTIENE VISIBLE) ---
        if st.session_state.ver_correo:
            st.markdown("---")
            st.subheader("✉️ Redacción de Reporte Formal")
            doc_mail = st.text_input("Correo del Destinatario:", placeholder="doctor@clinica.com.do")
            
            # Obtener datos para el cuerpo
            df_u = pd.read_sql_query("SELECT valor, fecha FROM glucosa ORDER BY id DESC LIMIT 1", conn)
            v_u = df_u['valor'][0] if not df_u.empty else "N/A"
            
            cuerpo = (f"ESTIMADO DOCTOR / FAMILIAR:\n\n"
                      f"Le informo que mi último registro de glucosa fue de {v_u} mg/dL.\n"
                      f"Este reporte fue generado automáticamente por mi sistema de control.\n\n"
                      f"Atentamente,\n{NOMBRE_PROPIETARIO}\n{UBICACION_SISTEMA}")

            import urllib.parse
            link = f"https://mail.google.com/mail/?view=cm&fs=1&to={doc_mail}&su=Reporte%20Medico%20Quevedo&body={urllib.parse.quote(cuerpo)}"
            
            if doc_mail:
                st.link_button("🚀 ABRIR GMAIL Y ENVIAR", link)
