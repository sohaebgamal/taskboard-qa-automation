import requests

TIMEOUT = 10


class ApiClient:
    """Thin wrapper around requests that keeps one user's session cookie."""

    def __init__(self, base_url):
        self.base_url = base_url
        self.session = requests.Session()

    def request(self, method, path, **kwargs):
        return self.session.request(method, self.base_url + path, timeout=TIMEOUT, **kwargs)

    def get(self, path, **kwargs):
        return self.request("GET", path, **kwargs)

    def post(self, path, **kwargs):
        return self.request("POST", path, **kwargs)

    def patch(self, path, **kwargs):
        return self.request("PATCH", path, **kwargs)

    def delete(self, path, **kwargs):
        return self.request("DELETE", path, **kwargs)

    def login(self, username, password):
        response = self.post("/api/login", json={"username": username, "password": password})
        assert response.status_code == 200, response.text
        return self

    def create_task(self, title="Write test report"):
        response = self.post("/api/tasks", json={"title": title})
        assert response.status_code == 201, response.text
        return response.json()
