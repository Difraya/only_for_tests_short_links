import time
import random
import string
import json
from locust import HttpUser, task, between, tag, events

def generate_random_string(length=10):
    letters = string.ascii_lowercase + string.digits
    return ''.join(random.choice(letters) for _ in range(length))

def generate_random_url():
    domains = ["example.com", "test.org", "demo.net", "sample.io"]
    paths = ["products", "articles", "users", "posts", "categories", "news"]
    
    domain = random.choice(domains)
    path_length = random.randint(1, 3)
    path_segments = [random.choice(paths) for _ in range(path_length)]
    
    path = "/".join(path_segments)
    
    has_params = random.choice([True, False])
    url = f"https://www.{domain}/{path}"
    
    if has_params:
        params_count = random.randint(1, 3)
        params = []
        for _ in range(params_count):
            param_name = generate_random_string(5)
            param_value = generate_random_string(8)
            params.append(f"{param_name}={param_value}")
        
        url += "?" + "&".join(params)
    
    return url

active_users = []
short_codes = []

class ShortLinkUser(HttpUser):
    wait_time = between(1, 5) 
    
    def on_start(self):
        username = f"testuser_{generate_random_string(8)}"
        email = f"{username}@example.com"
        password = "Password123!"
        
        user_data = {
            "email": email,
            "password": password,
            "username": username
        }
        
        register_response = self.client.post(
            "/api/v1/auth/register",
            json=user_data,
            name="/api/v1/auth/register"
        )
        
        if register_response.status_code == 201:
            login_response = self.client.post(
                "/api/v1/auth/jwt/login",
                data={
                    "username": email,
                    "password": password
                },
                name="/api/v1/auth/jwt/login"
            )
            
            if login_response.status_code == 200:
                self.token = login_response.json()["access_token"]
                self.auth_headers = {"Authorization": f"Bearer {self.token}"}
                self.email = email
                self.password = password
                self.username = username
                
                user_info = {
                    "email": email,
                    "token": self.token,
                    "auth_headers": self.auth_headers
                }
                active_users.append(user_info)
    
    @tag("create")
    @task(5) 
    def create_short_link(self):
        if not hasattr(self, "auth_headers"):
            return
        
        original_url = generate_random_url()
        
        use_custom_alias = random.random() < 0.2
        custom_alias = generate_random_string(6) if use_custom_alias else None
        
        use_expiration = random.random() < 0.3
        expires_at = None
        if use_expiration:
            expiration_hours = random.randint(1, 30 * 24)
            current_time = time.time()
            expires_at_timestamp = current_time + expiration_hours * 3600
            import datetime
            expires_at = datetime.datetime.fromtimestamp(expires_at_timestamp).strftime("%Y-%m-%dT%H:%M:%S")
        
        link_data = {"original_url": original_url}
        if custom_alias:
            link_data["custom_alias"] = custom_alias
        if expires_at:
            link_data["expires_at"] = expires_at
        
        with self.client.post(
            "/api/v1/links/shorten",
            json=link_data,
            headers=self.auth_headers,
            name="/api/v1/links/shorten",
            catch_response=True
        ) as response:
            if response.status_code == 201:
                response_data = response.json()
                if "short_code" in response_data:
                    short_code = response_data["short_code"]
                    short_codes.append(short_code)
                    response.success()
                else:
                    response.failure("Response does not contain short_code")
            else:
                response.failure(f"Failed to create short link: {response.status_code}")
    
    @tag("redirect")
    @task(3) 
    def redirect_to_original(self):
        if not short_codes:
            return
        
        short_code = random.choice(short_codes)
        
        with self.client.get(
            f"/{short_code}",
            name="/{short_code}",
            allow_redirects=False, 
            catch_response=True
        ) as response:
            if response.status_code in [301, 302, 307, 308]:
                response.success()
            else:
                response.failure(f"Redirect failed: {response.status_code}")
    
    @tag("stats")
    @task(1)
    def get_link_stats(self):
        if not hasattr(self, "auth_headers") or not short_codes:
            return
        
        short_code = random.choice(short_codes)
        
        with self.client.get(
            f"/api/v1/links/{short_code}/stats",
            headers=self.auth_headers,
            name="/api/v1/links/{short_code}/stats",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 404:
                if short_code in short_codes:
                    short_codes.remove(short_code)
                response.success()
            else:
                response.failure(f"Failed to get stats: {response.status_code}")
    
    @tag("update")
    @task(1)
    def update_link(self):
        if not hasattr(self, "auth_headers") or not short_codes:
            return
        
        short_code = random.choice(short_codes)
        
        new_url = generate_random_url()
        
        update_data = {"original_url": new_url}
        
        with self.client.put(
            f"/api/v1/links/{short_code}",
            json=update_data,
            headers=self.auth_headers,
            name="/api/v1/links/{short_code}",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code in [403, 404]:
                if short_code in short_codes:
                    short_codes.remove(short_code)
                response.success()
            else:
                response.failure(f"Failed to update link: {response.status_code}")
    
    @tag("delete")
    @task(1) 
    def delete_link(self):
        if not hasattr(self, "auth_headers") or not short_codes:
            return
        
        short_code = random.choice(short_codes)
        
        with self.client.delete(
            f"/api/v1/links/{short_code}",
            headers=self.auth_headers,
            name="/api/v1/links/{short_code}",
            catch_response=True
        ) as response:
            if response.status_code == 204:
                if short_code in short_codes:
                    short_codes.remove(short_code)
                response.success()
            elif response.status_code in [403, 404]:
                if short_code in short_codes:
                    short_codes.remove(short_code)
                response.success()
            else:
                response.failure(f"Failed to delete link: {response.status_code}")

class RedirectOnlyUser(HttpUser):
    wait_time = between(0.5, 3)  
    
    @task
    def redirect_to_original(self):
        if not short_codes:
            return
        
        short_code = random.choice(short_codes)
        
        with self.client.get(
            f"/{short_code}",
            name="/{short_code} (RedirectOnly)",
            allow_redirects=False, 
            catch_response=True
        ) as response:
            if response.status_code in [301, 302, 307, 308]:
                response.success()
            elif response.status_code == 410:
                if short_code in short_codes:
                    short_codes.remove(short_code)
                response.success()
            elif response.status_code == 404:
                if short_code in short_codes:
                    short_codes.remove(short_code)
                response.success()
            else:
                response.failure(f"Redirect failed: {response.status_code}") 
