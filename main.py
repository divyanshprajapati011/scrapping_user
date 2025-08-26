import streamlit as st
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor
import hashlib, io, time, urllib.parse, re, requests, os, subprocess, sys
from playwright.sync_api import sync_playwright

# ================== APP CONFIG ==================
st.set_page_config(page_title="Maps Scraper", layout="wide")

# ================== SESSION ROUTER ==================
if "page" not in st.session_state:
    st.session_state.page = "home"
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user" not in st.session_state:
    st.session_state.user = None

def go_to(p):
    st.session_state.page = p

# ================== DB ==================
def get_connection():
    return psycopg2.connect(
        user="postgres.jsjlthhnrtwjcyxowpza",
        password="@Deep7067",
        host="aws-1-ap-south-1.pooler.supabase.com",
        port="6543",
        dbname="postgres",
        sslmode="require",
    )

# ================== SECURITY HELPERS ==================
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

# ---------- USERS ----------
def register_user(username, password, email):
    db = get_connection()
    cur = db.cursor()
    try:
        cur.execute(
            "INSERT INTO users (username, password, email) VALUES (%s,%s,%s)",
            (username, hash_password(password), email),
        )
        db.commit()
        return True
    except Exception:
        return False
    finally:
        cur.close(); db.close()

def login_user(username, password):
    db = get_connection()
    cur = db.cursor(cursor_factory=RealDictCursor)
    cur.execute(
        "SELECT * FROM users WHERE username=%s AND password=%s",
        (username, hash_password(password)),
    )
    user = cur.fetchone()
    cur.close(); db.close()
    return user

# ================== SCRAPER PLACEHOLDER (keep your old one here) ==================
def scrape_maps(query, limit=20, email_lookup=True):
    # Dummy DataFrame (replace with your scraper logic)
    data = {
        "Business Name": [f"{query} - Business #{i+1}" for i in range(limit)],
        "Website": [f"https://example-{i+1}.com" for i in range(limit)],
        "Address": [f"Address line {i+1}, City" for i in range(limit)],
        "Phone (Maps)": [f"+91-9876543{i:02d}" for i in range(limit)],
        "Email": [f"contact{i+1}@example.com" for i in range(limit)],
        "Rating": [round(3.0 + (i%5)*0.3, 1) for i in range(limit)]
    }
    return pd.DataFrame(data)

# ================== PAGES ==================
def page_home():
    st.markdown("<h2 style='text-align:center;'>🚀 Google Maps Scraper</h2>", unsafe_allow_html=True)

    with st.container():
        col1, col2, col3 = st.columns([1,2,1])
        with col2:
            st.markdown("<div style='background:white;padding:30px;border-radius:15px;box-shadow:0 2px 8px rgba(0,0,0,0.1);'>",
                        unsafe_allow_html=True)
            
            st.markdown("<h3 style='text-align:center;'>Welcome to Maps Scraper</h3>", unsafe_allow_html=True)
            st.write("Choose an option below to continue:")

            c1, c2 = st.columns(2)
            with c1:
                if st.button("🔑 Login", use_container_width=True):
                    go_to("login")
            with c2:
                if st.button("📝 Signup", use_container_width=True):
                    go_to("signup")
            st.markdown("</div>", unsafe_allow_html=True)

def page_login():
    st.markdown("<h2 style='text-align:center;'>Login 🔑</h2>", unsafe_allow_html=True)
    with st.container():
        col1, col2, col3 = st.columns([1,2,1])
        with col2:
            with st.form("login_form"):
                username = st.text_input("Username")
                password = st.text_input("Password", type="password")
                submitted = st.form_submit_button("Login")
                if submitted:
                    user = login_user(username, password)
                    if user:
                        st.session_state.logged_in = True
                        st.session_state.user = user
                        st.success("✅ Login successful! Redirecting...")
                        time.sleep(1.2)
                        go_to("scraper")
                        st.experimental_rerun()
                    else:
                        st.error("❌ Invalid username or password")

            if st.button("⬅️ Back"):
                go_to("home")

def page_signup():
    st.markdown("<h2 style='text-align:center;'>Signup 📝</h2>", unsafe_allow_html=True)
    with st.container():
        col1, col2, col3 = st.columns([1,2,1])
        with col2:
            with st.form("signup_form"):
                new_user = st.text_input("Choose Username")
                new_email = st.text_input("Email")
                new_pass = st.text_input("Choose Password", type="password")
                submitted = st.form_submit_button("Create Account")
                if submitted:
                    if new_user and new_email and new_pass:
                        if register_user(new_user, new_pass, new_email):
                            st.success("🎉 Signup successful! Please login now.")
                            go_to("login")
                        else:
                            st.error("⚠️ User already exists or DB error.")
                    else:
                        st.warning("⚠️ Please fill all fields.")

            if st.button("⬅️ Back"):
                go_to("home")

def page_scraper():
    st.markdown("<h2 style='text-align:center;'>Google Maps Scraper 🚀</h2>", unsafe_allow_html=True)

    query = st.text_input("🔎 Enter query", "top coaching in Bhopal")
    limit = st.number_input("Maximum results to fetch", 5, 100, 20, step=5)
    lookup = st.checkbox("Also fetch Email/Phones from website", value=True)
    
    if st.button("Start Scraping", use_container_width=True):
        with st.spinner("⏳ Scraping in progress..."):
            try:
                df = scrape_maps(query, int(limit), lookup)
                st.success(f"✅ Scraping completed! Found {len(df)} results.")

                st.dataframe(df, use_container_width=True, height=400)

                csv = df.to_csv(index=False).encode("utf-8-sig")
                st.download_button("⬇️ Download CSV", csv, "maps_results.csv", "text/csv")

            except Exception as e:
                st.error(f"❌ Scraping failed: {e}")

# ================== ROUTER ==================
page = st.session_state.page
if page == "home":
    page_home()
elif page == "login":
    page_login()
elif page == "signup":
    page_signup()
elif page == "scraper":
    page_scraper()
