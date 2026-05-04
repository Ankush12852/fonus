import os
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, Settings
from llama_index.embeddings.gemini import GeminiEmbedding
from llama_index.llms.gemini import Gemini
from llama_index.core.node_parser import SentenceSplitter

# --- Configuration Section ---
DATA_DIR = "./data"                  
INDEX_PERSIST_DIR = "./dgca_index_store" # Simplest folder name

def build_dgca_index():
    """
    Builds the Vector Index with resumable logic using native LlamaIndex persistence.
    """
    
    # 💥 CRITICAL FIX: Set the key directly
    os.environ["GEMINI_API_KEY"] = "AIzaSyCijLgWwUUnLg1xkmUaY-3l_5faNUlDJVg" # PASTE YOUR KEY HERE
    
    if os.environ["GEMINI_API_KEY"] == "YOUR_API_KEY_HERE":
        print("CRITICAL ERROR: Please update 'os.environ[\"GEMINI_API_KEY\"]' in create_index.py and save.")
        return

    # 1. Configure Global LlamaIndex Settings
    print("--- 1. Configuring LlamaIndex Settings ---")
    
    Settings.llm = Gemini(model="gemini-2.5-flash")
    Settings.embed_model = GeminiEmbedding(
        model_name="models/text-embedding-004", 
        embed_batch_size=20 
    ) 
    
    Settings.text_splitter = SentenceSplitter(
        chunk_size=256, 
        chunk_overlap=20
    )

    # 2. Load Documents
    print("--- 2. Loading EASA/DGCA Documents ---")
    if not os.path.exists(DATA_DIR) or not os.listdir(DATA_DIR):
        print(f"CRITICAL ERROR: The '{DATA_DIR}' folder is missing or empty. Cannot proceed.")
        return
        
    documents = SimpleDirectoryReader(input_dir=DATA_DIR, required_exts=[".txt"]).load_data()
    print(f"--- Successfully loaded {len(documents)} document(s) ---")

    # --- 3. Index Creation & Persistence ---
    print("--- 3. Checking for existing index... ---")
    
    # 💡 FINAL PERSISTENCE FIX (Loading): Use StorageContext
    from llama_index.core import StorageContext, load_index_from_storage 

    if os.path.exists(INDEX_PERSIST_DIR):
        print(f"--- RESUMING: Loading existing index from {INDEX_PERSIST_DIR} ---")
        
        # We need StorageContext to load the index correctly
        storage_context = StorageContext.from_defaults(persist_dir=INDEX_PERSIST_DIR)
        index = load_index_from_storage(storage_context=storage_context)
        
        # Insert nodes to trigger the resume logic 
        index.insert_nodes(documents) 
        
    else:
        # Build the index from scratch
        print("--- STARTING FRESH: Building new index with simple persistence ---")
        index = VectorStoreIndex.from_documents(
            documents,
            show_progress=True 
        )
        
    # 💥 FINAL PERSISTENCE FIX (Saving): Correct method for persistence
    index.storage_context.persist(persist_dir=INDEX_PERSIST_DIR) 
    
    print(f"--- 5. Indexing Complete! Data saved to: {INDEX_PERSIST_DIR} ---")

if __name__ == "__main__":
    build_dgca_index()