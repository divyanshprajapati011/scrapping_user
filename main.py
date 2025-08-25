import streamlit as st
import pandas as pd
import hashlib, io, time, re, requests, urllib.parse
from playwright.sync_api import sync_playwright
from Shared.db import get_connection, hash_password

st.set_page_config(page_title="Maps Scraper User", layout="wide")

# ================== Session State ==================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user = None

menu = st.sidebar.radio("Menu", ["Login", "Register"])

# ================== UTILS ==================
EMAIL_RE = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.I)
PHONE_RE = re.compile(r"(?:\+?\d[\d\-\s]{7,}\d)")
HEADERS = {"User-Agent": "Mozilla/5.0"}

def df_to_excel_bytes(df: pd.DataFrame) -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Sheet1")
    buf.seek(0)
    return buf.getvalue()

def get_maps_url(user_input: str):
    user_input = user_input.strip()
    if "google.com/search" in user_input and "q=" in user_input:
        m = re.search(r"q=([^&]+)", user_input)
        if m:
            query_text = urllib.parse.unquote(m.group(1))
            return "https://www.google.com/maps/search/" + urllib.parse.quote_plus(query_text)
    elif "google.com/maps" in user_input:
        return user_input
    else:
        return "https://www.google.com/maps/search/" + urllib.parse.quote_plus(user_input)

def fetch_email_phone_from_site(url, timeout=12):
    if not url or not url.startswith("http"):
        return "", ""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=timeout)
        html = resp.text
        emails = list({e for e in EMAIL_RE.findall(html)})
        phones = list({p.strip() for p in PHONE_RE.findall(html)})
        return "; ".join(emails[:5]), "; ".join(phones[:5])
    except Exception:
        return "", ""

def scrape_maps(url, limit=50, email_lookup=True):
    rows = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox","--disable-dev-shm-usage"])
        context = browser.new_context()
        page = context.new_page()
        page.goto(url, timeout=60000)
        time.sleep(3)

        cards = page.locator("//div[contains(@class,'Nv2PK')]").all()
        count, last_name = 0, None

        for card in cards:
            if count >= limit:
                break
            try:
                card.scroll_into_view_if_needed()
                card.click()
                page.wait_for_timeout(1200)
            except:
                continue

            # Business Name
            try:
                name = page.locator('//h1[contains(@class,"DUwDvf")]').inner_text(timeout=3000)
            except:
                continue
            if name == last_name: continue
            last_name = name

            # Website
            website = ""
            try:
                if page.locator('//a[@data-item-id="authority"]').count():
                    website = page.locator('//a[@data-item-id="authority"]').get_attribute("href") or ""
            except:
                pass

            # Address
            address = ""
            try:
                if page.locator('//button[@data-item-id="address"]').count():
                    address = page.locator('//button[@data-item-id="address"]').inner_text(timeout=1000)
            except:
                pass

            # Phone
            phone = ""
            try:
                if page.locator('//button[starts-with(@data-item-id,"phone:")]').count():
                    phone = page.locator('//button[starts-with(@data-item-id,"phone:")]').inner_text(timeout=1000)
            except:
                pass

            # Rating
            rating = ""
            try:
                el = page.locator('//span[@role="img" and contains(@aria-label,"stars")]')
                if el.count():
                    aria = el.get_attribute("aria-label", timeout=1000) or ""
                    r1 = re.search(r"(\d+(?:\.\d+)?)", aria)
                    rating = r1.group(1) if r1 else ""
            except:
                pass

            # Email / Extra Phones
            email_from_site, extra_phones = ("","")
            if email_lookup and website:
                email_from_site, extra_phones = fetch_email_phone_from_site(website)

            rows.append({
                "Business Name": name,
                "Website": website,
                "Address": address,
                "Phone (Maps)": phone,
                "Email (from site)": email_from_site,
                "Extra Phones": extra_phones,
                "Rating": rating,
                "Source URL": page.url
            })
            count += 1

        context.close()
        browser.close()
    return pd.DataFrame(rows)

# ================== REGISTER ==================
if menu == "Register":
    st.subheader("📝 Create a New Account")
    username = st.text_input("Username")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    if st.button("Register"):
        if username and email and password:
            db = get_connection(); cur = db.cursor()
            try:
                cur.execute(
                    "INSERT INTO users (username,email,password) VALUES (%s,%s,%s)",
                    (username,email,hash_password(password))
                )
                db.commit()
                st.success("✅ Registered! Please login now.")
            except Exception as e:
                st.error(f"❌ Error: {e}")
            finally:
                cur.close(); db.close()
        else:
            st.warning("⚠️ Fill all fields.")

# ================== LOGIN ==================
elif menu == "Login":
    st.subheader("🔑 Login to Your Account")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        db = get_connection(); cur = db.cursor()
        cur.execute("SELECT * FROM users WHERE username=%s AND password=%s", (username, hash_password(password)))
        user = cur.fetchone()
        cur.close(); db.close()
        if user:
            st.session_state.logged_in = True
            st.session_state.user = user
            st.success(f"✅ Logged in as {username}")
        else:
            st.error("❌ Invalid credentials")

# ================== SCRAPER ==================
if st.session_state.logged_in:
    st.subheader("🚀 Google Maps Scraper")
    user_input = st.text_input("Enter query or Google Maps URL", "top coaching in Bhopal")
    max_results = st.number_input("Max results", min_value=5, max_value=100, value=20, step=5)
    do_email_lookup = st.checkbox("Fetch Emails / Phones from Website", value=True)
    save_to_db = st.checkbox("Save results to DB", value=True)

    if st.button("Start Scraping"):
        if not user_input.strip():
            st.error("Enter a valid query or URL")
        else:
            with st.spinner("Scraping..."):
                df = scrape_maps(user_input, int(max_results), bool(do_email_lookup))
                st.success(f"Scraping completed! {len(df)} results found.")
                st.dataframe(df, use_container_width=True)

                # Save to DB
                if save_to_db and not df.empty:
                    db = get_connection(); cur = db.cursor()
                    for _, r in df.iterrows():
                        try:
                            cur.execute("""
                                INSERT INTO scraping_results
                                (user_id, business_name, address, phone, email, website, rating)
                                VALUES (%s,%s,%s,%s,%s,%s,%s)
                            """, (
                                st.session_state.user[0],  # user_id
                                r["Business Name"], r["Address"], r["Phone (Maps)"],
                                r["Email (from site)"], r["Website"], r["Rating"]
                            ))
                        except:
                            pass
                    db.commit(); cur.close(); db.close()
                    st.info(f"Saved {len(df)} rows to DB.")

                # Downloads
                st.download_button("⬇️ Download CSV", data=df.to_csv(index=False).encode("utf-8-sig"), file_name="maps_scrape.csv")
                st.download_button("⬇️ Download Excel", data=df_to_excel_bytes(df), file_name="maps_scrape.xlsx")
