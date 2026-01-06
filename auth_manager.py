import streamlit as st
import google.oauth2.credentials
from google_auth_oauthlib.flow import Flow
import os
from werkzeug.security import generate_password_hash, check_password_hash
import db_manager

# --- Google OAuth Configuration ---
# Redirect URI must match what is in Google Console and secrets.toml
AUTH_REDIRECT_URI = "http://localhost:8501" 

class GoogleAuth:
    def __init__(self):
        # Allow insecure localhost for testing
        os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
        self.auth_redirect_uri = "http://localhost:8501"
        
        try:
            self.client_config = st.secrets["google_auth"]
            if "web" in self.client_config and "redirect_uris" in self.client_config["web"]:
                uris = self.client_config["web"]["redirect_uris"]
                
                # Intelligent Redirect URI Selection
                # 1. If running in Codespaces, find the codespace URI
                if os.getenv("CODESPACES") == "true":
                    for uri in uris:
                        if "github.dev" in uri or "preview.app" in uri:
                            self.auth_redirect_uri = uri
                            break
                else:
                    # 2. Prefer localhost if not in codespaces
                    for uri in uris:
                        if "localhost" in uri:
                            self.auth_redirect_uri = uri
                            break
        except Exception as e:
            self.client_config = None
            st.error(f"Config Error: {e}")

    def get_login_url(self):
        if not self.client_config:
            return f"{self.auth_redirect_uri}/?mock_login=true"
            
        try:
            flow = Flow.from_client_config(
                self.client_config,
                scopes=[
                    'openid', 
                    'https://www.googleapis.com/auth/userinfo.email', 
                    'https://www.googleapis.com/auth/userinfo.profile'
                ],
                redirect_uri=self.auth_redirect_uri
            )
            auth_url, _ = flow.authorization_url(prompt='consent', access_type='offline')
            return auth_url
        except Exception as e:
            st.error(f"Error generating login URL: {e}")
            return "#"

    def get_user_info(self):
        # 1. Check Mock Login
        if st.query_params.get("mock_login") == "true":
            st.query_params.clear()
            return {
                "name": "Demo User",
                "email": "demo@example.com",
                "picture": "https://www.gravatar.com/avatar/00000000000000000000000000000000?d=mp&f=y"
            }

        if not self.client_config:
            return None

        # 2. Check Real OAuth Code exchange
        code = st.query_params.get("code")
        if code:
            try:
                flow = Flow.from_client_config(
                    self.client_config,
                    scopes=[
                        'openid', 
                        'https://www.googleapis.com/auth/userinfo.email', 
                        'https://www.googleapis.com/auth/userinfo.profile'
                    ],
                    redirect_uri=self.auth_redirect_uri
                )
                flow.fetch_token(code=code)
                credentials = flow.credentials
                
                # Fetch User Info
                import requests
                
                response = requests.get(
                    'https://www.googleapis.com/oauth2/v3/userinfo',
                    headers={'Authorization': f'Bearer {credentials.token}'}
                )
                
                if response.status_code != 200:
                    st.error(f"Failed to fetch user info: {response.text}")
                    return None
                    
                user_info = response.json()
                
                # Sync with DB and Load Persistence
                db_user = db_manager.sync_user_data(
                    user_info.get('email'), 
                    user_info.get('name'), 
                    user_info.get('picture')
                )
                st.session_state.daily_checks = db_user.get('daily_checks', 0)
                
                # Clean URL
                st.query_params.clear()
                
                return user_info
            except Exception as e:
                st.error(f"Auth Error: {e}")
                st.info(f"Using Redirect URI: {self.auth_redirect_uri}")
                return None
        return None

    def sign_out(self):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

    # --- Email/Password Auth Methods ---
    
    def register_user(self, email, password):
        """Hashes password and saves user to DB."""
        if db_manager.get_user_by_email(email):
            return False, "Email already exists."
        
        hashed_pw = generate_password_hash(password)
        success = db_manager.create_user(email, hashed_pw)
        if success:
            return True, "Account created successfully! Please login."
        return False, "An error occurred during registration."

    def login_user(self, email, password):
        """Verifies credentials and sets user session."""
        user = db_manager.get_user_by_email(email)
        if user and check_password_hash(user['password_hash'], password):
            # Sync to reset daily checks if a new day
            db_user = db_manager.sync_user_data(email)
            st.session_state.daily_checks = db_user.get('daily_checks', 0)
            
            # Convert SQLite row to dictionary for consistency with Google Auth
            user_data = {
                "id": db_user['id'],
                "email": db_user['email'],
                "name": db_user['name'],
                "picture": db_user['picture']
            }
            return True, user_data
        return False, "Invalid email or password."
