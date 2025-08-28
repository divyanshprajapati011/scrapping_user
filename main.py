import streamlit as st
import pandas as pd
import re, urllib.parse, io, requests, os, time, subprocess, sys
from playwright.sync_api import sync_playwright

# ================== APP CONFIG ==================
st.set_page_config(page_title="Unlimited Maps Scraper", layout="wide")

# ================== REGEX HELPERS ==================
EMAIL_RE = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.I)
PHONE_RE = re.compile(r"(?:\+?\d[\d\-\s]{7,}\d)")
HEADERS = {"User-Agent": "Mozilla/5.0"}

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

# ================== SCRAPER ==================
def scrape_maps(url, limit=500, email_lookup=True):
    rows = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox","--disable-dev-shm-usage"])
        context = browser.new_context()
        page = context.new_page()

        page.goto(url, timeout=90_000)
        page.wait_for_timeout(3000)

        feed = page.locator('div[role="feed"]').first
        if not feed.count():
            feed = page.locator('//div[contains(@class,"m6QErb") and @role="region"]').first

        # Scroll loop until we have enough cards
        cards = page.locator('div.Nv2PK')
        prev_count = 0
        stagnant_cycles = 0

        while True:
            try:
                eh = feed.element_handle()
                for _ in range(5):
                    page.evaluate("(el) => el.scrollBy(0, el.clientHeight)", eh)
                    page.wait_for_timeout(600)
            except Exception:
                page.mouse.wheel(0, 5000)

            # Try clicking "More results"
            try:
                btn = page.locator('//button[.//span[contains(text(),"More") or contains(text(),"Show") or contains(text(),"और")]]').first
                if btn.count():
                    btn.click(timeout=2000)
                    page.wait_for_timeout(1500)
            except:
                pass

            cur_count = cards.count()
            if cur_count > prev_count:
                prev_count = cur_count
                stagnant_cycles = 0
            else:
                stagnant_cycles += 1

            if prev_count >= limit:
                break
            if stagnant_cycles >= 20:   # ज्यादा देर तक growth नहीं तो break
                break

        # Extract data
        total = cards.count()
        total = min(total, limit)

        for i in range(total):
            try:
                card = cards.nth(i)
                card.scroll_into_view_if_needed()
                card.click(timeout=4000)
                page.wait_for_timeout(1500)
            except:
                continue

            # Name
            try:
                name = page.locator('//h1[contains(@class,"DUwDvf")]').inner_text(timeout=4000)
            except:
                continue

            # Website
            website = ""
            try:
                w = page.locator('//a[@data-item-id="authority"]').first
                if w.count():
                    website = w.get_attribute("href") or ""
            except:
                pass

            # Address
            address = ""
            try:
                a = page.locator('//button[@data-item-id="address"]').first
                if a.count():
                    address = a.inner_text(timeout=2000)
            except:
                pass

            # Phone
            phone = ""
            try:
                ph = page.locator('//button[starts-with(@data-item-id,"phone:")]').first
                if ph.count():
                    phone = ph.inner_text(timeout=2000)
            except:
                pass

            # Rating
            rating = ""
            try:
                star = page.locator('//span[@role="img" and contains(@aria-label,"stars")]').first
                if star.count():
                    aria = star.get_attribute("aria-label") or ""
                    m = re.search(r"(\d+(?:\.\d+)?)", aria)
                    rating = m.group(1) if m else ""
            except:
                pass

            email_from_site, extra_phones_from_site = "", ""
            if email_lookup and website:
                email_from_site, extra_phones_from_site = fetch_email_phone_from_site(website)

            rows.append({
                "Business Name": name,
                "Website": website,
                "Address": address,
                "Phone (Maps)": phone,
                "Email (from site)": email_from_site,
                "Extra Phones (from site)": extra_phones_from_site,
                "Rating": rating,
                "Source (Maps URL)": page.url
            })

        context.close()
        browser.close()
    return pd.DataFrame(rows)

# ================== DOWNLOAD HELPERS ==================
def df_to_excel_bytes(df: pd.DataFrame) -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Sheet1")
    buf.seek(0)
    return buf.getvalue()

# ================== STREAMLIT UI ==================
st.title("🚀 Unlimited Google Maps Scraper")

user_input = st.text_input("🔎 Enter query / Google Maps URL", "top coaching in Bhopal")
max_results = st.number_input("Maximum results to fetch", min_value=20, max_value=2000, value=200, step=20)
do_email_lookup = st.checkbox("Also extract Emails / Extra Phones from websites", value=True)

if st.button("Start Scraping"):
    maps_url = get_maps_url(user_input)
    with st.spinner("Scraping in progress... Please wait"):
        df = scrape_maps(maps_url, int(max_results), bool(do_email_lookup))
        st.success(f"✅ Scraping completed! Found {len(df)} results.")
        st.dataframe(df, use_container_width=True)

        # Downloads
        csv_bytes = df.to_csv(index=False).encode("utf-8-sig")
        st.download_button("⬇️ Download CSV", data=csv_bytes, file_name="maps_data.csv", mime="text/csv")

        xlsx_bytes = df_to_excel_bytes(df)
        st.download_button("⬇️ Download Excel", data=xlsx_bytes,
                           file_name="maps_data.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
