import os
from dotenv import load_dotenv
import vertexai
from vertexai.generative_models import GenerativeModel

load_dotenv()

project_id = os.getenv("GOOGLE_PROJECT_ID")
location = os.getenv("GOOGLE_LOCATION", "us-central1")

print(f"Checking models for Project: {project_id}, Location: {location}")

vertexai.init(project=project_id, location=location)

print("\n--- Listing ALL Available Models ---")
try:
    from google.cloud import aiplatform
    aiplatform.init(project=project_id, location=location)
    models = aiplatform.Model.list()
    if not models:
        print("No custom models found (this is expected for foundation models).")
        
    # For foundation models, we can't easily "list" them via SDK in a simple way 
    # without using the Model Garden API which is complex.
    # Instead, let's try a broader list of known recent candidates including experimental ones.
    candidates = [
        # Gemini 2.0 models (production)
        "gemini-2.0-flash-001",
        "gemini-2.0-flash",
        # Gemini 2.5 preview models
        "gemini-2.5-flash-preview-05-20",
        "gemini-2.5-flash",
        # Gemini 1.5 models (legacy)
        "gemini-1.5-flash-001",
        "gemini-1.5-flash-002",
        "gemini-1.5-flash",
        "gemini-1.5-pro-001",
        "gemini-1.5-pro-002",
        "gemini-1.5-pro",
    ]

    print("\nTesting specific model candidates:")
    for model_name in candidates:
        try:
            model = GenerativeModel(model_name)
            # We need to actually call it to see if we have access
            response = model.generate_content("Hi", stream=False)
            print(f"✅ {model_name} is AVAILABLE and WORKING!")
        except Exception as e:
            # Clean up error message for brevity
            err_msg = str(e).split("For more information")[0].strip()
            if "404" in err_msg:
                print(f"❌ {model_name}: Not Found / No Access")
            else:
                print(f"❌ {model_name}: Error - {err_msg}")

except Exception as e:
    print(f"Fatal error listing models: {e}")
