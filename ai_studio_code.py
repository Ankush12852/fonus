import google.generativeai as genai

genai.configure(api_key="AIzaSyDYVF-vO_yR-7SCpX-fEwrprFPOsrTcDRs")

for m in genai.list_models():
    print(f"Name: {m.name}")
    print(f"Capabilities: {m.supported_generation_methods}\n")