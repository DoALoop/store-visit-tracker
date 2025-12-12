import base64
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_analyze():
    # Create a small 1x1 white pixel png base64
    small_image = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+ip1sAAAAASUVORK5CYII="
    
    payload = {
        "mime_type": "image/png",
        "image_data": small_image
    }
    
    print("Sending request to /api/analyze-visit...")
    try:
        response = client.post("/api/analyze-visit", json=payload)
        print(f"Status Code: {response.status_code}")
        if response.status_code != 200:
            print("Response body:", response.text)
        else:
            print("Success! Response:", response.json())
    except Exception as e:
        print(f"Exception during request: {e}")

if __name__ == "__main__":
    test_analyze()
