import streamlit as st
import pandas as pd
from analysis import ImageQualityAnalyzer
import io
import cv2
from PIL import Image
import time
import zipfile

# --- Page Configuration ---
st.set_page_config(
    page_title="E-com Image Quality AI",
    page_icon="📸",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Custom CSS for Premium Look ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        background: -webkit-linear-gradient(45deg, #4f46e5, #06b6d4);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
    }
    
    .stMetric {
        background-color: #f8fafc;
        padding: 1rem;
        border-radius: 10px;
        border: 1px solid #e2e8f0;
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1);
    }
    
    .report-card {
        padding: 1.5rem;
        border-radius: 12px;
        margin-bottom: 1rem;
        background: white;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    
    .score-high { color: #10b981; }
    .score-med { color: #f59e0b; }
    .score-low { color: #ef4444; }
    
    /* Sidebar premium feel */
    section[data-testid="stSidebar"] {
        background-color: #0f172a;
    }
    section[data-testid="stSidebar"] h1, section[data-testid="stSidebar"] h2, section[data-testid="stSidebar"] span, section[data-testid="stSidebar"] label {
        color: #f1f5f9 !important;
    }
    
    button {
        border-radius: 8px !important;
    }
    
</style>
""", unsafe_allow_html=True)

# --- Session State for Verification Limits (Freemium) ---
if 'daily_checks' not in st.session_state:
    st.session_state.daily_checks = 0
if 'user_tier' not in st.session_state:
    st.session_state.user_tier = 'Free'

FREE_LIMIT = 5

# --- Utils ---
def get_score_color(score):
    if score >= 80: return "green"
    if score >= 50: return "orange"
    return "red"

def generate_csv(results):
    # Flatten dict for CSV
    data = {
        "Overall Score": [results['overall_score']],
        "Resolution Score": [results['resolution']['score']],
        "Blur Score": [results['blur']['score']],
        "Brightness Score": [results['brightness']['score']],
        "Resoluton Details": [f"{results['resolution']['width']}x{results['resolution']['height']}"],
        "Blur Variance": [results['blur']['value']],
        "Brightness Value": [results['brightness']['value']]
    }
    df = pd.DataFrame(data)
    return df.to_csv(index=False).encode('utf-8')

analyzer = ImageQualityAnalyzer()

# --- Sidebar ---
with st.sidebar:
    st.title("📸 Quality AI")
    st.markdown("---")
    st.markdown(f"**Current Plan:** {st.session_state.user_tier}")
    
# --- Premium Logic ---
def check_premium_status():
    """
    Checks if the user is Premium.
    For this MVP, we verify using a simple URL query parameter 'upgraded=true'.
    In a real app, you would verify a Stripe session ID or a database record.
    """
    # 1. Check if already verified in session
    if st.session_state.get('user_tier') == 'Pro':
        return True
    
    # 2. Check for success flag from Stripe Redirect
    # Example Redirect URL: https://your-app.streamlit.app/?upgraded=true
    query_params = st.query_params
    if query_params.get("upgraded") == "true":
        st.session_state.user_tier = 'Pro'
        st.toast("Welcome to Pro Plan! 🎉", icon="🚀")
        return True
        
    return False

is_premium = check_premium_status()

from auth_manager import GoogleAuth

# --- Auth Logic & Routing ---
auth = GoogleAuth()
# Handle Google OAuth redirect or Email Session
user_info = auth.get_user_info()
if user_info:
    st.session_state.user = user_info
    st.rerun()

# Determine Current Page/Mode
if 'mode' not in st.session_state:
    st.session_state.mode = st.query_params.get("mode", "landing")

def set_mode(new_mode):
    st.session_state.mode = new_mode
    st.query_params["mode"] = new_mode
    st.rerun()

# --- Landing Page vs Auth Pages vs Main App ---
if 'user' not in st.session_state or st.session_state.user is None:
    # 1. REGISTER PAGE
    if st.session_state.mode == "register":
        st.markdown('<div class="landing-title">Create Account</div>', unsafe_allow_html=True)
        with st.container():
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                with st.form("register_form"):
                    email = st.text_input("Email")
                    password = st.text_input("Password", type="password")
                    confirm_password = st.text_input("Confirm Password", type="password")
                    submit = st.form_submit_button("Create Account", use_container_width=True)
                    
                    if submit:
                        if password != confirm_password:
                            st.error("Passwords do not match.")
                        elif not email or not password:
                            st.error("Please fill all fields.")
                        else:
                            success, msg = auth.register_user(email, password)
                            if success:
                                st.success(msg)
                                time.sleep(1)
                                set_mode("login")
                            else:
                                st.error(msg)
                if st.button("Already have an account? Login"):
                    set_mode("login")

    # 2. LOGIN PAGE
    elif st.session_state.mode == "login":
        st.markdown('<div class="landing-title">Login</div>', unsafe_allow_html=True)
        with st.container():
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                with st.form("login_form"):
                    email = st.text_input("Email")
                    password = st.text_input("Password", type="password")
                    submit = st.form_submit_button("Login", use_container_width=True)
                    
                    if submit:
                        success, result = auth.login_user(email, password)
                        if success:
                            st.session_state.user = result
                            st.query_params.clear()
                            st.rerun()
                        else:
                            st.error(result)
                
                st.markdown("---")
                # Also allow Google login on login page
                login_url = auth.get_login_url()
                st.link_button("Login with Google", login_url, use_container_width=True)
                
                if st.button("Need an account? Create one"):
                    set_mode("register")
                if st.button("← Back to Home"):
                    set_mode("landing")

    # 3. LANDING PAGE
    else:
        # Landing Page
        st.markdown("""
            <style>
                .stApp { background-color: #0f172a; } 
                
                /* Hide sidebar on landing page */
                [data-testid="stSidebar"] { display: none; }
                
                .landing-title { 
                    font-size: 4rem; 
                    font-weight: 800; 
                    background: -webkit-linear-gradient(45deg, #4f46e5, #06b6d4);
                    -webkit-background-clip: text;
                    -webkit-text-fill-color: transparent;
                    text-align: center;
                    margin-top: 2rem;
                }
                .landing-subtitle {
                    font-size: 1.5rem;
                    color: #94a3b8;
                    text-align: center;
                    margin-bottom: 3rem;
                }
                .feature-card {
                    background: #1e293b;
                    padding: 2rem;
                    border-radius: 15px;
                    color: white;
                    text-align: center;
                    height: 100%;
                    border: 1px solid #334155;
                }
            </style>
        """, unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            try:
                st.image("logo.png", width=150)
            except:
                pass # Logo might not be loaded yet
                
        st.markdown('<div class="landing-title">PixelPerfect AI</div>', unsafe_allow_html=True)
        st.markdown('<div class="landing-subtitle">The Ultimate E-commerce Image Quality Auditor for Amazon & Shopify Sellers.<br>Fix Blur, Brightness, and Resolution in Seconds.</div>', unsafe_allow_html=True)
        
        # CTA & Auth Buttons
        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            # User Requirements: links for register, login, and google-login
            col_a, col_b = st.columns(2)
            with col_a:
                if st.button("🔑 Login", use_container_width=True):
                    set_mode("login")
            with col_b:
                if st.button("📝 Create Account", use_container_width=True):
                    set_mode("register")
            
            st.markdown('<p style="text-align:center; color:#94a3b8; margin: 1rem 0;">OR</p>', unsafe_allow_html=True)
            
            # Premium Google Login Button
            login_url = auth.get_login_url()
            st.link_button("🚀 Login with Google", login_url, type="primary", use_container_width=True)
            
        st.markdown("---")
        
        # Features
        fc1, fc2, fc3 = st.columns(3)
        with fc1:
            st.markdown("""
            <div class="feature-card">
                <h3>⚡ Instant Audit</h3>
                <p>Automatically detect resolution issues, blurry content, and poor lighting.</p>
            </div>
            """, unsafe_allow_html=True)
        with fc2:
            st.markdown("""
            <div class="feature-card">
                <h3>🤖 AI Correction</h3>
                <p>Fix common mistakes with one click using our advanced Computer Vision models.</p>
            </div>
            """, unsafe_allow_html=True)
        with fc3:
            st.markdown("""
            <div class="feature-card">
                <h3> Revenue Boost</h3>
                <p>Higher quality images lead to 30% higher conversion rates on e-commerce.</p>
            </div>
            """, unsafe_allow_html=True)

else:
    # --- LOGGED IN DASHBOARD ---
    
    # User Profile in Sidebar
    with st.sidebar:
        # Profile Header
        st.markdown("### Profile")
        p_col1, p_col2 = st.columns([1, 3])
        with p_col1:
             st.image(st.session_state.user.get('picture'), width=60)
        with p_col2:
             st.markdown(f"**{st.session_state.user.get('name')}**")
             st.caption(st.session_state.user.get('email'))
             
        if st.button("Sign Out", type="secondary", use_container_width=True):
            auth.sign_out()
    
    # --- Sidebar ---
    with st.sidebar:
        st.markdown("---")
        st.title("📸 Quality AI")
        
        if is_premium:
            st.success("🌟 Pro Plan Active")
            st.caption("Thank you for supporting us!")
            st.metric("Checks Left", "Unlimited")
        else:
            st.markdown(f"**Current Plan:** {st.session_state.user_tier}")
            st.progress(st.session_state.daily_checks / FREE_LIMIT)
            st.caption(f"{st.session_state.daily_checks}/{FREE_LIMIT} free daily checks used")
            
            st.markdown("### 🚀 Upgrade to Pro")
            st.markdown("- Unlimited Checks")
            st.markdown("- Bulk Upload")
            st.markdown("- 3x Faster AI Processing")
            
            # LINK TO STRIPE PAYMENT PAGE
            # Replace this URL with your actual Stripe Payment Link
            STRIPE_LINK = "https://buy.stripe.com/test_aFacN69INgcT52lad4e7m00" 
            
            st.link_button("👉 Upgrade now ($9/mo)", STRIPE_LINK, type="primary")
            st.caption("Secure payment via Stripe")
        
        st.markdown("---")
        st.markdown("### 🔧 Calibration")
        with st.expander("How this works?"):
            st.markdown(analyzer.calibration_explanation())

    # --- Main Page ---
    st.markdown('<div class="main-header">E-commerce Image Quality Checker</div>', unsafe_allow_html=True)
    st.markdown("Optimize your product listings with AI-powered quality analysis.")

    # Pro Feature: Bulk Upload
    accept_multiple = is_premium
    upload_label = "Upload Product Image(s)" if is_premium else "Upload Product Image (Upgrade for Bulk)"
    uploaded_files = st.file_uploader(upload_label, type=['jpg', 'jpeg', 'png'], accept_multiple_files=accept_multiple)

    # Normalize to list
    if uploaded_files:
        if not isinstance(uploaded_files, list):
            uploaded_files = [uploaded_files]

        # Check Limit (Free users capped at 5 daily, already checked in logic but need to enforce total count here)
        if not is_premium:
            if st.session_state.daily_checks + len(uploaded_files) > FREE_LIMIT:
                 st.error(f"Daily limit reached ({FREE_LIMIT}). Upgrade to Pro for unlimited checks.")
                 st.stop()
            
            # Enforce single file strictly if somehow multiple got through
            if len(uploaded_files) > 1:
                st.warning("Free plan supports single processing only. Analyzing the first image...")
                uploaded_files = [uploaded_files[0]]

        # Processing Setup
        results_list = []
        
        # Progress UI
        if len(uploaded_files) > 1:
            progress_bar = st.progress(0)
            status_text = st.empty()
        
        # --- ANALYSIS LOOP ---
        for idx, uploaded_file in enumerate(uploaded_files):
            
            # processing speed simulation
            if not is_premium:
                with st.spinner(f"Standard Processing ({uploaded_file.name})..."):
                    time.sleep(1.5) # Artificial delay for standard tier
            else:
                 # Pro Speed indication
                 pass # Instant

            # Load & Analyze
            image_pil, image_cv = analyzer.load_image(uploaded_file)
            result = analyzer.analyze(image_pil, image_cv)
            result['filename'] = uploaded_file.name
            results_list.append(result)
            
            # Update usage (approximate)
            if not is_premium:
                st.session_state.daily_checks += 1
                # PERSIST TO DB
                if st.session_state.user:
                    import db_manager
                    db_manager.update_user_checks(st.session_state.user.get('email'), st.session_state.daily_checks)
            if len(uploaded_files) > 1:
                progress_bar.progress((idx + 1) / len(uploaded_files))

        # --- RESULTS DISPLAY ---
        st.markdown("---")
        
        # SINGLE MODE
        if len(uploaded_files) == 1:
            result = results_list[0]
            
            # Top Score Banner
            overall = result['overall_score']
            score_color = get_score_color(overall)
            
            # Badge for Speed
            if is_premium:
                st.caption("⚡ Priority AI Processing Applied")
            
            col_img, col_score = st.columns([1, 1])
            with col_img:
                 st.image(uploaded_files[0], caption=uploaded_files[0].name, use_container_width=True)
                 
            with col_score:
                st.markdown(f"""
                <div style="text-align: center; padding: 2rem; background: #f8fafc; border-radius: 15px;">
                    <h2 style="margin:0; color: #64748b;">Overall Score</h2>
                    <h1 style="font-size: 5rem; margin: 0; color: {score_color};">{overall}/100</h1>
                </div>
                """, unsafe_allow_html=True)

            # Detailed Metrics
            m1, m2, m3 = st.columns(3)
            with m1:
                st.metric("Resolution", f"{result['resolution']['width']}x{result['resolution']['height']}", delta=f"{result['resolution']['score']}/100")
                if result['resolution']['issues']: st.warning(result['resolution']['issues'][0])
                else: st.success("Resolution Great")
            with m2:
                st.metric("Focus", f"{result['blur']['score']}/100", delta=result['blur']['status'], delta_color="inverse")
                if result['blur']['issues']: st.error(result['blur']['issues'][0])
                else: st.success("Sharp Focus")
            with m3:
                st.metric("Brightness", f"{result['brightness']['score']}/100", delta=result['brightness']['status'], delta_color="inverse")
                if result['brightness']['issues']: st.warning(result['brightness']['issues'][0])
                else: st.success("Balanced Light")

            # --- Report Download ---
            st.markdown("### 📥 Report")
            csv_data = generate_csv(result)
            st.download_button("Download Report (CSV)", csv_data, f"report_{result['filename']}.csv", "text/csv")
            
            # --- Enhancement Studio (Gated) ---
            st.markdown("---")
            st.markdown('<div class="main-header" style="font-size: 2rem;">✨ AI Enhancement Studio</div>', unsafe_allow_html=True)
            
            if is_premium:
                st.caption("⚡ Pro Features Unlocked: Auto-fix, Smart Upscale, Sharpening")
                from enhancement import ImageEnhancer
                enhancer = ImageEnhancer()
                
                # Use 'key' to avoid collisions if re-running
                # Logic: We use a session state holder for the currently processed enhanced image
                if 'enhanced_image' not in st.session_state or st.session_state.get('last_processed_file') != result['filename']:
                    st.session_state.enhanced_image = None
                    st.session_state.last_processed_file = result['filename']

                e_col1, e_col2 = st.columns([1, 2])
                with e_col1:
                    if st.button("💡 Fix Brightness", key="fix_bright"):
                        processed = enhancer.fix_brightness(image_cv)
                        st.session_state.enhanced_image = cv2.cvtColor(processed, cv2.COLOR_BGR2RGB)
                    if st.button("🔍 Smart Upscale (AI)", key="upscale"):
                        with st.spinner("AI Upscaling..."):
                            processed = enhancer.enhance_resolution(image_cv) # FSRCNN
                            st.session_state.enhanced_image = cv2.cvtColor(processed, cv2.COLOR_BGR2RGB)
                    if st.button("✨ Fix All Automatically", type="primary", key="fix_all"):
                        processed = enhancer.process_all(image_cv)
                        st.session_state.enhanced_image = cv2.cvtColor(processed, cv2.COLOR_BGR2RGB)
                
                with e_col2:
                    if st.session_state.enhanced_image is not None:
                        st.image(st.session_state.enhanced_image, caption="Enhanced Version", use_container_width=True)
                        # Image Download
                        img_out = Image.fromarray(st.session_state.enhanced_image)
                        buf = io.BytesIO()
                        img_out.save(buf, format="JPEG", quality=95)
                        st.download_button("⬇️ Download Enhanced Image", buf.getvalue(), f"enhanced_{result['filename']}", "image/jpeg")
                    else:
                        st.info("Select an enhancement tool.")
            else:
                # Gated View
                st.warning("🔒 This feature is available on the Pro Plan.")
                st.info("Unlock AI Auto-Correction, Smart Upscaling, and Sharpening.")
                
                e_col1, e_col2 = st.columns([1, 2])
                with e_col1:
                    st.button("💡 Fix Brightness", disabled=True)
                    st.button("🔍 Smart Upscale (AI)", disabled=True)
                    st.button("✨ Fix All Automatically", disabled=True, type="primary")
                with e_col2:
                    st.markdown("### Upgrade to Unlock 🔓")
                    st.markdown("- Fix dark images instantly")
                    st.markdown("- Upscale resolution by 3x")
                    st.markdown("- Restore blurry photos")
        
        # BULK MODE
        else:
            st.success(f"✅ Analyzed {len(uploaded_files)} images successfully.")
            
            # Summary Table
            summary_data = []
            for r in results_list:
                summary_data.append({
                    "Filename": r['filename'],
                    "Overall Score": r['overall_score'],
                    "Resolution": f"{r['resolution']['width']}x{r['resolution']['height']}",
                    "Blur Status": r['blur']['status'],
                    "Brightness Status": r['brightness']['status']
                })
            st.dataframe(pd.DataFrame(summary_data), use_container_width=True)
            
            # Bulk Download Reports (ZIP)
            st.markdown("### 📥 Bulk Download")
            
            # Create ZIP in memory
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w") as zf:
                # Add combined CSV
                combined_csv = pd.DataFrame(summary_data).to_csv(index=False)
                zf.writestr("summary_report.csv", combined_csv)
                
                # Add individual CSVs? Maybe just one summary is enough.
                # Let's simple add summary.
            
            st.download_button(
                label="Download Summary Report (ZIP)",
                data=zip_buffer.getvalue(),
                file_name="bulk_analysis_report.zip",
                mime="application/zip"
            )
            
            st.info("💡 Bulk AI Enhancement is available in the API version (Coming Soon).")

    else:
        # Empty State
        st.info("👆 Upload product images to begin analysis.")
        st.markdown("""
        ### Features
        - **Resolution Check**: Ensure images meet marketplace standards.
        - **AI Blur Detection**: Catch out-of-focus shots.
        - **Exposure Analysis**: Fix lighting issues.
        - **Auto-Enhancement**: (Pro) Automatically fix and upscale images.
        """)

