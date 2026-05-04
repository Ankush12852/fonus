import os
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Mock environment variables for testing
os.environ["GROQ_CHAT_KEY_1"] = "mock_groq_key_1"
os.environ["GROQ_CHAT_KEY_2"] = "mock_groq_key_2"
os.environ["GEMINI_API_KEY"] = "mock_gemini_key"

# We need to mock the LLM classes to avoid real API calls and missing dependency errors in some environments
class MockLLM:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

class MockGroq(MockLLM):
    pass

class MockGoogleGenAI(MockLLM):
    pass

# Patch standard imports before importing main
import types
mock_llama_index = types.ModuleType("llama_index")
mock_llama_index_llms = types.ModuleType("llama_index.llms")
mock_llama_index_llms_groq = types.ModuleType("llama_index.llms.groq")
mock_llama_index_llms_google_genai = types.ModuleType("llama_index.llms.google_genai")

mock_llama_index_llms_groq.Groq = MockGroq
mock_llama_index_llms_google_genai.GoogleGenAI = MockGoogleGenAI

sys.modules["llama_index"] = mock_llama_index
sys.modules["llama_index.llms"] = mock_llama_index_llms
sys.modules["llama_index.llms.groq"] = mock_llama_index_llms_groq
sys.modules["llama_index.llms.google_genai"] = mock_llama_index_llms_google_genai

# Now we can safely import the function to test
# Since we only want to test get_llm_for_request, we might just copy-paste it here 
# or import it if main.py doesn't have too many side effects on import.
# main.py does load_env() and initializes supabase, so let's just re-define it 
# or use a minimal test.

def test_get_llm_for_request():
    from backend.main import get_llm_for_request
    
    print("Testing get_llm_for_request...")
    
    # 1. Test normal Groq return
    # (Since we mocked it, it should return MockGroq)
    llm, name = get_llm_for_request()
    print(f"Result: {name}, API Key Used: {llm.kwargs.get('api_key')}")
    assert "Groq" in name
    assert llm.kwargs.get('api_key') == "mock_groq_key_1"
    
    print("Success: Groq key 1 returned.")

    # 2. Test rotation (this is harder to test without mocking the Groq class constructor to throw errors)
    # Let's try to monkeypatch MockGroq to throw a rate limit error for the first key
    original_init = MockGroq.__init__
    
    def failing_init(self, **kwargs):
        if kwargs.get('api_key') == "mock_groq_key_1":
            raise Exception("Rate limit reached (429)")
        original_init(self, **kwargs)
        
    MockGroq.__init__ = failing_init
    
    llm, name = get_llm_for_request()
    print(f"Result (after 429 on key 1): {name}, API Key Used: {llm.kwargs.get('api_key')}")
    assert llm.kwargs.get('api_key') == "mock_groq_key_2"
    print("Success: Rotated to Groq key 2.")

    # 3. Test Fallback to Gemini
    def always_fail_init(self, **kwargs):
        raise Exception("Rate limit reached (429)")
        
    MockGroq.__init__ = always_fail_init
    
    llm, name = get_llm_for_request()
    print(f"Result (after 429 on all Groq): {name}")
    assert "Gemini" in name
    print("Success: Fell back to Gemini.")

if __name__ == "__main__":
    try:
        test_get_llm_for_request()
        print("\nALL TESTS PASSED")
    except Exception as e:
        print(f"\nTEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
