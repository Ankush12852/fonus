import os
from llama_index.core import StorageContext, load_index_from_storage, Settings
from llama_index.core.memory import ChatMemoryBuffer
# 💥 STABLE 2026 IMPORTS (Fixes Deprecation Warnings)
from llama_index.llms.google_genai import GoogleGenAI
from llama_index.embeddings.google_genai import GoogleGenAIEmbedding

# --- Configuration ---
INDEX_PERSIST_DIR = "./dgca_index_store"
API_KEY = "AIzaSyCijLgWwUUnLg1xkmUaY-3l_5faNUlDJVg"
os.environ["GOOGLE_API_KEY"] = API_KEY

def run_fonus_coach():
    print("--- 1. Initializing Fonus Chat Coach ---")
    
    # Use the stable GoogleGenAI classes
    Settings.llm = GoogleGenAI(model="models/gemini-2.5-flash")
    Settings.embed_model = GoogleGenAIEmbedding(model_name="models/text-embedding-004")

    print(f"--- 2. Loading Library from: {INDEX_PERSIST_DIR} ---")
    try:
        storage_context = StorageContext.from_defaults(persist_dir=INDEX_PERSIST_DIR)
        index = load_index_from_storage(storage_context)
        print("--- Library Loaded Successfully ---")
    except Exception as e:
        print(f"ERROR: Index not found. Run create_index.py first. Details: {e}")
        return

    # 🧠 CHAT MEMORY: This allows Fonus to remember "hi" and your name
    memory = ChatMemoryBuffer.from_defaults(token_limit=4000)

    # 🤖 CHAT ENGINE: This replaces the Query Engine
    chat_engine = index.as_chat_engine(
        chat_mode="context",
        memory=memory,
        system_prompt=(
            "You are 'Fonus', a professional DGCA AME Coach. "
            "1. If Ankush says 'Hi' or 'Hello', greet him warmly. "
            "2. For technical questions, use the index context. "
            "3. If the answer is not in the books, use your general knowledge but say so."
        )
    )

    print("\n--- Fonus Coach is Online! Type 'exit' to quit ---")
    while True:
        # If you see "Ankush:", you know you are running the NEW code
        prompt = input("Ankush: ")
        if prompt.lower() == 'exit': break
        
        # .chat() is used for conversational AI
        response = chat_engine.chat(prompt)
        print(f"\nFonus: {response}\n")

if __name__ == "__main__":
    run_fonus_coach()