# How to Enable Real Google Sign-In 🔐

To switch from the "Mock Login" to real Google Authentication, you need to create credentials in the Google Cloud Console.

## Step 1: Create a Google Cloud Project
1. Go to [console.cloud.google.com](https://console.cloud.google.com/).
2. Click **Create Project** (Name it "E-com Image Quality Analyzer").
3. Click **Create**.

## Step 2: Configure OAuth Consent Screen
1. In the sidebar, go to **APIs & Services > OAuth consent screen**.
2. Select **External** (unless you have a G-Suite organization).
3. Fill in the required fields:
   - **App Name**: "PixelPerfect AI"
   - **User Support Email**: Your email.
   - **Developer Contact Email**: Your email.
4. Click **Save and Continue**.
5. **Scopes**: Click "Add or Remove Scopes". Select:
   - `.../auth/userinfo.email`
   - `.../auth/userinfo.profile`
   - `openid`
6. Click **Update** -> **Save and Continue**.
7. **Test Users**: Add your own Gmail address so you can log in during testing.

## Step 3: Create Credentials
1. Go to **APIs & Services > Credentials**.
2. Click **+ Create Credentials** -> **OAuth client ID**.
3. **Application Type**: "Web application".
4. **Name**: "Streamlit App".
5. **Authorized redirect URIs**:
   - `http://localhost:8501`
   - *(If you deploy later, add your deployed URL here too, e.g., `https://my-app.streamlit.app`)*
6. Click **Create**.

## Step 4: Copy Keys to Your App
1. You will see a popup with "Client ID" and "Client Secret".
2. Open the file `.streamlit/secrets.toml` in this project.
3. Replace the placeholders:
   ```toml
   [google_auth.web]
   client_id = "paste_your_client_id_here"
   client_secret = "paste_your_client_secret_here"
   ...
   ```
4. Save the file.

## Step 5: Restart the App
1. Go to your terminal.
2. Press `Ctrl+C` to stop the app.
3. Run `streamlit run app.py` again.
4. Click "Sign in with Google" -> It will now open the REAL Google Login page!
