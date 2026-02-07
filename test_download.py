
import requests

def test_download():
    # We need a token. Let's assume we can get one or we just check if the endpoint is reachable.
    # But it requires authentication.
    url = "http://localhost:8000/report/user/test@example.com"
    try:
        response = requests.get(url)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text[:100]}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_download()
