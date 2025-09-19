import os, time, json
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from config import UPWORK_EMAIL, UPWORK_PASSWORD

COOKIE_FILE = "./cookies/upwork.json"

class AuthManager:
    def __init__(self, headless=True):
        options = Options()
        options = Options()
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--start-maximized")
        # options.add_argument("--headless=new")  # optional headless
        if headless:
            options.add_argument("--headless=new")
        self.driver = webdriver.Chrome(options=options)

    def login(self):
        """
        First try to load cookies.
        If cookies missing or invalid → fallback to email/password login.
        """
        # --- Step 1: Try cookies ---
        if os.path.exists(COOKIE_FILE):
            self.driver.get("https://www.upwork.com/")
            try:
                self.driver.delete_all_cookies()
                with open(COOKIE_FILE, "r") as f:
                    cookies = json.load(f)
                for cookie in cookies:
                    # Selenium expects 'expiry', not 'expirationDate'
                    if "expirationDate" in cookie:
                        cookie["expiry"] = int(cookie["expirationDate"])
                        del cookie["expirationDate"]
                    # Remove keys not accepted by Selenium
                    for k in ["hostOnly", "sameSite", "storeId", "session"]:
                        cookie.pop(k, None)
                    # Add cookie only for correct domain
                    try:
                        self.driver.add_cookie(cookie)
                    except Exception as e:
                        pass
                self.driver.refresh()
                # Check if auth token is present after loading cookies
                cookies_dict = {c['name']: c['value'] for c in self.driver.get_cookies()}
                auth_token = (
                    cookies_dict.get("XSRF-TOKEN")
                    or cookies_dict.get("upwork_auth")
                    or cookies_dict.get("oDeskAuth")
                )
                if auth_token:
                    print("🔄 Logged in using existing cookies.")
                    return
                else:
                    print("⚠️ Cookies loaded but no auth token found. Will try login.")
            except Exception as e:
                print(f"⚠️ Failed to use cookies: {e}")

        # --- Step 2: Login with credentials ---
        print("🔑 Logging in with email/password...")
        self.driver.get("https://www.upwork.com/ab/account-security/login")

        try:
            username = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "login_username"))
            )
            username.send_keys(UPWORK_EMAIL)

            self.driver.find_element(By.ID, "login_password_continue").click()

            password = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "login_password"))
            )
            password.send_keys(UPWORK_PASSWORD)
            self.driver.find_element(By.ID, "login_control_continue").click()

            time.sleep(5)

            # Save cookies for next time
            os.makedirs(os.path.dirname(COOKIE_FILE), exist_ok=True)
            with open(COOKIE_FILE, "w") as f:
                json.dump(self.driver.get_cookies(), f)
            print("✅ Login successful, cookies saved.")

        except Exception as e:
            print(f"❌ Login failed: {e}")
            print(self.driver.page_source[:2000])  # print snippet for debugging
            raise

    def get_driver(self):
        """Return a driver with authenticated session ready for scraping."""
        self.login()
        return self.driver

    def get_auth_headers(self):
        """Return headers with authorization token extracted from cookies or localStorage."""
        self.login()  # ensures session is loaded

        # --- 1. Collect cookies ---
        cookies_dict = {c['name']: c['value'] for c in self.driver.get_cookies()}

        # Try common cookie names
        auth_token = (
            cookies_dict.get("XSRF-TOKEN")
            or cookies_dict.get("upwork_auth")
            or cookies_dict.get("oDeskAuth")
        )

        # --- 2. If not found, check localStorage ---
        if not auth_token:
            try:
                auth_token = self.driver.execute_script(
                    "return window.localStorage.getItem('accessToken') || "
                    "window.localStorage.getItem('authToken') || "
                    "window.localStorage.getItem('token');"
                )
            except Exception as e:
                print(f"⚠️ Could not read localStorage for token: {e}")

        # --- 3. If still not found, force re-login ---
        if not auth_token:
            print("⚠️ No auth token found, forcing re-login...")
            if os.path.exists(COOKIE_FILE):
                os.remove(COOKIE_FILE)
            self.login()
            cookies_dict = {c['name']: c['value'] for c in self.driver.get_cookies()}
            auth_token = (
                cookies_dict.get("XSRF-TOKEN")
                or cookies_dict.get("upwork_auth")
                or cookies_dict.get("oDeskAuth")
            )
            if not auth_token:
                try:
                    auth_token = self.driver.execute_script(
                        "return window.localStorage.getItem('accessToken') || "
                        "window.localStorage.getItem('authToken') || "
                        "window.localStorage.getItem('token');"
                    )
                except:
                    pass

        if not auth_token:
            raise Exception("❌ Could not extract auth token from Upwork session.")
        
        headers = {
            "Authorization": f"Bearer {auth_token}",
            "User-Agent": "Mozilla/5.0",
        }
        return headers, cookies_dict

