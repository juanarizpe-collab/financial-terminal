import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas_datareader as pdr
import feedparser
import datetime
from datetime import datetime, timedelta

# --- CONFIGURACIÓN ---
try:
    from streamlit_autorefresh import st_autorefresh
    HAS_AUTOREFRESH = True
except ImportError:
    HAS_AUTOREFRESH = False

try:
    from tvDatafeed import TvDatafeed, Interval
    HAS_TV = True
except ImportError:
    HAS_TV = False

st.set_page_config(page_title="Terminal Quant V6.2", layout="wide")

if HAS_AUTOREFRESH:
    st_autorefresh(interval=300000, limit=None, key="auto_refresh")

# --- DICCIONARIO DE TICKERS (GDXU Agregado) ---
tickers = {
    "SPY": "SPY",
    "NASDAQ": "^IXIC",
    "DOW JONES": "^DJI",
    "BRENT OIL": "BZ=F",
    "WTI OIL": "CL=F",
    "VIX": "^VIX",
    "ORO": "GC=F",
    "BITCOIN": "BTC-USD",
    "ETHEREUM": "ETH-USD",
    "NVIDIA": "NVDA",
    "GDXU": "GDXU",  # MicroSectors Gold Miners 3X Leveraged ETN
    "HEIDELBERG": "HDD.F", # <--- Agregamos Heidelberg aquí
    "DXY": "DX-Y.NYB",
    "TESORO10Y": "^TNX"
}

@st.cache_data(ttl=60)
def load_data():
    df = yf.download(list(tickers.values()), period="1mo", interval="1d", progress=False)['Close']
    end = datetime.now()
    start = end - timedelta(days=60)
    try:
        baml = pdr.get_data_fred('BAMLH0A0HYM2', start, end)
        df['BAML'] = baml['BAMLH0A0HYM2']
    except:
        df['BAML'] = 3.15
    try:
        tv = TvDatafeed()
        tv_data = tv.get_hist(symbol='CN10Y', exchange='TVC', interval=Interval.in_daily, n_bars=10)
        df['CN10Y'] = tv_data['close'].iloc[-1] if (tv_data is not None and not tv_data.empty) else 2.25
    except:
        df['CN10Y'] = 2.25
    return df.ffill().bfill()

def get_change(ticker_name):
    current = data[tickers[ticker_name]].iloc[-1]
    prev = data[tickers[ticker_name]].iloc[-2]
    return current, ((current - prev) / prev) * 100

# --- PROCESAMIENTO ---
data = load_data()
data['Liquidez_Global'] = data[tickers['DXY']] * data['BAML']
data['Ratio_Referencia'] = data['CN10Y'] / data['Liquidez_Global']
data['CN10Y_Chg'] = data['CN10Y'].pct_change().fillna(0)
data['Ratio_Chg'] = data['Ratio_Referencia'].pct_change().fillna(0)

# Variables de Estado
val_cn10y_chg = data['CN10Y_Chg'].iloc[-1]
val_ratio_chg = data['Ratio_Chg'].iloc[-1]
riesgo_activado = bool(val_cn10y_chg > val_ratio_chg)

# ==========================================
# ALERTA ESTRATÉGICA: ROTACIÓN A DEFENSA
# ==========================================
# Calculamos los valores directamente desde la base de datos (Base 100)
ultimo_valor_hdd = (data[tickers['HEIDELBERG']].iloc[-1] / data[tickers['HEIDELBERG']].iloc[0]) * 100
ultimo_valor_spy = (data[tickers['SPY']].iloc[-1] / data[tickers['SPY']].iloc[0]) * 100
ultimo_valor_btc = (data[tickers['BITCOIN']].iloc[-1] / data[tickers['BITCOIN']].iloc[0]) * 100

# Definimos las condiciones
alerta_nivel_1 = ultimo_valor_hdd > ultimo_valor_spy 
alerta_nivel_2 = ultimo_valor_hdd > ultimo_valor_btc 

# Inicializamos el mensaje
mensaje_alerta = ""
color_alerta = ""

if alerta_nivel_2:
    mensaje_alerta = "🚨 ALERTA ROJA: HDD > BTC. Fuga masiva de capital hacia Defensa Europea. Señal de Crisis."
    color_alerta = "#FF0000"
elif alerta_nivel_1:
    mensaje_alerta = "⚠️ ALERTA AMARILLA: HDD > SPY. Rotación confirmada de Tech a Defensa (Pivot)."
    color_alerta = "#FFD700"

# ==========================================
# ==========================================
# 1. COMMAND CENTER (TOP)
# ==========================================


# 1. Definimos el color del semáforo basado en la lógica
# Usamos un margen pequeño (0.0001) para definir el estado "Neutral"
if abs(val_cn10y_chg - val_ratio_chg) < 0.00001:
    semaforo = "⚪"  # Blanco / Neutral
elif riesgo_activado:
    semaforo = "🔴"  # Rojo / Bajista
else:
    semaforo = "🟢"  # Verde / Alcista

# 2. Creamos tres columnas para alinear todo: [GIF, TÍTULO, SEMÁFORO]
col_t1, col_t2, col_t3 = st.columns([1, 10, 1])

with col_t1:
    st.image("1.gif", width=80)

with col_t2:
    st.title("Terminal Quant V6.2: Command Center")

with col_t3:
    # Mostramos el semáforo en grande
    st.markdown(f"<h1 style='text-align: center;'>{semaforo}</h1>", unsafe_allow_html=True)


# El resto del código de métricas sigue igual debajo...
# Indicadores Macro
m_col1, m_col2, m_col3, m_col4, m_col5, m_col6, m_col7 = st.columns(7)
m_col1.metric("CN10Y (China)", f"{data['CN10Y'].iloc[-1]:.3f}%")
m_col2.metric("Ratio Líquido", f"{data['Ratio_Referencia'].iloc[-1]:.4f}", f"{val_ratio_chg:+.2%}")
m_col3.metric("DXY (Dólar)", f"{data[tickers['DXY']].iloc[-1]:.2f}")
m_col4.metric("BAML (Spread)", f"{data['BAML'].iloc[-1]:.2f}%")
m_col5.metric("US10Y (Tesoro)", f"{data[tickers['TESORO10Y']].iloc[-1]:.2f}%")
p_brent, ch_brent = get_change("BRENT OIL")
m_col6.metric("BRENT OIL", f"${p_brent:,.2f}", f"{ch_brent:+.2f}%", delta_color="inverse")
p_wti, ch_wti = get_change("WTI OIL")
m_col7.metric("WTI OIL", f"${p_wti:,.2f}", f"{ch_wti:+.2f}%", delta_color="inverse")

# Watchlist con GDXU
st.write("")
w_col1, w_col2, w_col3, w_col4, w_col5, w_col6, w_col7 = st.columns(7)
p_spy, ch_spy = get_change("SPY")
w_col1.metric("SPY 500", f"${p_spy:,.2f}", f"{ch_spy:+.2f}%")
p_nas, ch_nas = get_change("NASDAQ")
w_col2.metric("NASDAQ", f"{p_nas:,.0f}", f"{ch_nas:+.2f}%")
p_btc, ch_btc = get_change("BITCOIN")
w_col3.metric("BITCOIN", f"${p_btc:,.0f}", f"{ch_btc:+.2f}%")
p_gdxu, ch_gdxu = get_change("GDXU")
w_col4.metric("GDXU (Minas 3X)", f"${p_gdxu:,.2f}", f"{ch_gdxu:+.2f}%")
p_nvda, ch_nvda = get_change("NVIDIA")
w_col5.metric("NVIDIA", f"${p_nvda:,.2f}", f"{ch_nvda:+.2f}%")
p_gold, ch_gold = get_change("ORO")
w_col6.metric("ORO (XAU)", f"${p_gold:,.1f}", f"{ch_gold:+.2f}%")
p_vix, ch_vix = get_change("VIX")
w_col7.metric("VIX Index", f"{p_vix:.2f}", f"{ch_vix:+.2f}%", delta_color="inverse")

st.divider()

# ==========================================
# 2. RADAR GEOPOLÍTICO (LIMPIO Y UNIFICADO)
# ==========================================
st.subheader("📰 Radar Geopolítico & Riesgo de Energía")
news_col1, news_col2, news_col3 = st.columns(3)

# --- COLUMNA 1: ESTRATEGIA FIJA ---
with news_col1:
    st.error("**Riesgo Sistémico: Ormuz**")
    st.markdown("Monitoreo de flujo físico. Si el Brent rompe máximos, la liquidez sufrirá fricción inmediata.")

# --- COLUMNA 2: GEOPOLÍTICA EN VIVO ---
with news_col2:
    st.warning("**Última Hora: Geopolítica**")
    try:
        # Búsqueda optimizada: Petróleo + Medio Oriente
        feed = feedparser.parse("https://news.google.com/rss/search?q=geopolitics+oil+market+OR+Iran+OR+Middle+East&hl=es-419&gl=MX&ceid=MX:es-419")
        if not feed.entries:
            st.write("Sin noticias críticas recientes.")
        else:
            for entry in feed.entries[:4]:
                clean_title = entry.title.split(" - ")[0]
                st.markdown(f"🔹 [{clean_title}]({entry.link})")
    except:
        st.write("Buscando señales...")

# --- COLUMNA 3: REFUGIOS EN VIVO (ORO/GDXU) ---
with news_col3:
    st.info("**Radar de Refugios (Oro/GDXU)**")
    try:
        # Búsqueda optimizada para tu tesis: Oro + Minería + GDXU
        feed_oro = feedparser.parse("https://news.google.com/rss/search?q=gold+price+OR+GDXU+OR+mining+stocks&hl=es-419&gl=MX&ceid=MX:es-419")
        if not feed_oro.entries:
            st.write("Sin movimientos de capital reportados.")
        else:
            for entry in feed_oro.entries[:4]:
                clean_title_oro = entry.title.split(" - ")[0]
                st.markdown(f"🔸 [{clean_title_oro}]({entry.link})")
    except:
        st.write("Sincronizando flujos...")

st.divider()


# ==========================================
# 3. ANÁLISIS VISUAL (GDXU INTEGRADO)
# ==========================================
st.subheader("🌊 Marea de Liquidez vs Activos (Incluye GDXU)")

# Normalización Base 100
norm_ratio = data['Ratio_Referencia'] / data['Ratio_Referencia'].iloc[0] * 100
norm_brent = data[tickers['BRENT OIL']] / data[tickers['BRENT OIL']].iloc[0] * 100
norm_btc   = data[tickers['BITCOIN']] / data[tickers['BITCOIN']].iloc[0] * 100
norm_spy   = data[tickers['SPY']] / data[tickers['SPY']].iloc[0] * 100
norm_gdxu  = data[tickers['GDXU']] / data[tickers['GDXU']].iloc[0] * 100
norm_hdd   = data[tickers['HEIDELBERG']] / data[tickers['HEIDELBERG']].iloc[0] * 100 # <--- Nueva variable

# ==========================================
# ALERTA ESTRATÉGICA: ROTACIÓN A DEFENSA
# ==========================================
# Capturamos el valor más reciente de cada línea base 100
ultimo_valor_hdd = norm_hdd.iloc[-1]
ultimo_valor_spy = norm_spy.iloc[-1]
ultimo_valor_btc = norm_btc.iloc[-1]

# Definimos las condiciones de alerta
alerta_nivel_1 = ultimo_valor_hdd > ultimo_valor_spy # Heidelberg supera a las 500 empresas de USA
alerta_nivel_2 = ultimo_valor_hdd > ultimo_valor_btc # Heidelberg supera a la liquidez pura (Crypto)

# Creamos un mensaje dinámico para el Command Center
mensaje_alerta = ""
color_alerta = ""

if alerta_nivel_2:
    mensaje_alerta = "🚨 ALERTA ROJA: HDD > BTC. Fuga masiva de capital hacia Defensa Europea. Señal de Crisis."
    color_alerta = "#FF0000" # Rojo intenso
elif alerta_nivel_1:
    mensaje_alerta = "⚠️ ALERTA AMARILLA: HDD > SPY. Rotación confirmada de Tech a Defensa (Pivot)."
    color_alerta = "#FFD700" # Amarillo

fig_liq = make_subplots(specs=[[{"secondary_y": True}]])

# Capa de Liquidez (Eje Izquierdo)
fig_liq.add_trace(go.Scatter(x=data.index, y=norm_ratio, name="Marea Liquidez", line=dict(color='royalblue', width=4), fill='tozeroy'), secondary_y=False)

# Activos de Riesgo y Apalancados (Eje Derecho)
fig_liq.add_trace(go.Scatter(x=data.index, y=norm_brent, name="Presión Energía", fill='tozeroy', line=dict(color='rgba(255, 75, 75, 0.15)', width=1, dash='dot')), secondary_y=True)
fig_liq.add_trace(go.Scatter(x=data.index, y=norm_btc, name="BITCOIN", line=dict(color='#F7931A', width=3)), secondary_y=True)
fig_liq.add_trace(go.Scatter(x=data.index, y=norm_spy, name="SPY", line=dict(color='white', width=2)), secondary_y=True)

# NUEVA LÍNEA: GDXU (En color dorado brillante para diferenciarlo del Oro)
fig_liq.add_trace(go.Scatter(x=data.index, y=norm_gdxu, name="GDXU (Minas 3X)", line=dict(color='#FFD700', width=2.5, dash='dash')), secondary_y=True)

# NUEVA LÍNEA: HEIDELBERG (En un tono cian para contraste industrial)
fig_liq.add_trace(go.Scatter(x=data.index, y=norm_hdd, name="HEIDELBERG (HDD.F)", line=dict(color='#00FFFF', width=2)), secondary_y=True) # <--- Agregamos la línea

fig_liq.update_layout(template="plotly_dark", hovermode="x unified", height=600, margin=dict(l=0, r=0, t=30, b=0), legend=dict(orientation="h", y=1.05))
st.plotly_chart(fig_liq, use_container_width=True)  

import google.generativeai as genai

# ==========================================
# 3. IA WAR ROOM: DICTAMEN FINAL (LIMPIO)
# ==========================================
st.divider()
st.subheader("🤖 IA War Room: Comité de Análisis")

# 1. LA CLAVE PURA (Sin comandos extra)
RAW_KEY = st.secrets.get("GEMINI_API_KEY", "AIzaSyDgPYUn_XHKvOvVVfjrw7FIHRIKw1DRfns")

def conectar_comite():
    try:
        genai.configure(api_key=RAW_KEY)
        model = genai.GenerativeModel('models/gemini-2.5-flash')
        
        # Le agregué round(variable, 2) para que solo mande 2 decimales y se vea más limpio
        prompt = f"Como experto del Comité Quant, analiza: Oro ${round(p_gold, 2)}, GDXU ${round(p_gdxu, 2)}. Contexto: Crisis industrial alemana. 2 frases potentes."
        
        resp = model.generate_content(prompt)
        
        # Esta línea evita que Streamlit se vuelva loco con los símbolos de dólar
        texto_limpio = resp.text.replace("$", "\$")
        
        return texto_limpio
        
    except Exception as e:
        # El mensaje de error va hasta acá abajo, en su propia sección
        return f"ERROR: {e}"
    
# 2. BOTÓN DE ACTIVACIÓN
if st.button("🚀 Consultar al Comité"):
    with st.spinner("Estableciendo conexión encriptada..."):
        resultado = conectar_comite()
        
        if "ERROR_TECNICO" in resultado:
            st.error(f"Fallo de conexión: {resultado}")
        else:
            st.markdown(f"""
            <div style="background-color: #0e1117; padding: 25px; border-radius: 15px; border: 1px solid #ff4b4b; border-left: 5px solid #ff4b4b;">
                <h4 style="color: #ff4b4b; margin-top: 0; font-family: monospace;">📡 TRANSMISIÓN RECIBIDA:</h4>
                <div style="color: #e0e0e0; font-size: 1.1em; white-space: pre-wrap;">
                    {resultado}
                </div>
            </div>
            """, unsafe_allow_html=True)

# --- SECCIÓN DE INTELIGENCIA ESTRATÉGICA ---
st.markdown("---")

# Generamos la fecha (asegúrate de haber puesto 'import datetime' al inicio del archivo)
fecha_actual = datetime.now().strftime('%d/%m/%Y | %H:%M')

st.subheader(f"🧠 REPORTE DE INTELIGENCIA – {fecha_actual}")
st.caption("Eje Analítico: Crisis Industrial Alemania / Reconfiguración de Cadenas de Suministro")

col1, col2 = st.columns(2)

with col1:
    st.markdown("""
    ### 🏭 Manroland & Sector Industrial
    * **Estado:** Cierre en Offenbach (Insolvencia fallida).
    * **IG Metall:** Alerta por "desindustrialización silenciosa".
    * **Impacto:** Pérdida de 750 empleos; fin de la era offset tradicional.
    
    ### 📈 Heidelberg & ONBERG (El Pivot)
    * **Giro Crítico:** Reconversión a **Defense Tech**.
    * **Tecnología:** Comunicaciones resilientes y Anti-jamming.
    """)

with col2:
    st.markdown("""
    ### ✂️ Polar Cutting Technologies (PCT)
    * **Situación:** Segunda insolvencia. Mudanza a Eschborn.
    * **Riesgo:** Disrupción en suministro y fuga de talento.
    * **Suministro:** Giro hacia proveedores asiáticos.

    ### 🌍 Sentimiento del Mercado
    * **Narrativa:** "La imprenta muere; la defensa digital crece".
    * **Oportunidad:** Valor migrando a drones y guerra electrónica.
    """)

st.success(f"**💡 Conclusión Estratégica:** Juan, el valor ya no está en el peso del hierro, sino en la resiliencia digital.")