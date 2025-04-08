import requests
url = "http://smarthit.top:5000/api/push_frame/1"
# url = "http://localhost:5000/api/push_frame/1"
file_path = "test.png"

with open(file_path, 'rb') as file:
    files = {'file': file}
    response = requests.post(url, files=files)

print(response.status_code)
print(response.json())