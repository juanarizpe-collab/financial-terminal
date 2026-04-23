import google.generativeai as genai

# Pon tu clave entre las comillas
genai.configure(api_key="AIzaSyDgPYUn_XHKvOvVVfjrw7FIHRIKw1DRfns")

print("🔍 Preguntándole a Google qué modelos tienes disponibles hoy...")

try:
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f"✅ {m.name}")
except Exception as e:
    print(f"Error de conexión: {e}")