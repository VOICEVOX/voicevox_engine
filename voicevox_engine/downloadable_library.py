import requests


def fetch_downloadable_libraries():
    url = "http://localhost:50022"
    response = requests.get(url)
    return response.json()
