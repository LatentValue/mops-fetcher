import streamlit as st
import cloudscraper
import html
import re
from bs4 import BeautifulSoup
import pandas as pd
import io

# --- 1. Web App User Interface Setup ---
st.set_page_config(page_title="MOPS Briefing & Revenue Fetcher", page_icon="📈")
st.title("Taiwan Stock MOPS Fetcher")
st.write("Retrieve the latest Institutional Investor Conference (法說會) PDF and recent Monthly Revenue.")

ticker = st.text_input("Enter Taiwan Ticker (e.g., 6706):")

if st.button("Get Data") and ticker:
    ticker = ticker.strip()
    scraper = cloudscraper.create_scraper()
    
    # --- 2. PDF Fetching (Poorstock) ---
    st.markdown("### 📄 Latest Briefing PDF")
    with st.spinner(f"Querying Poorstock database for {ticker}..."):
        try:
            url = f"https://poorstock.com/earningcall/{ticker}"
            response = scraper.get(url)
            clean_html = html.unescape(response.text)
            
            soup = BeautifulSoup(clean_html, 'html.parser')
            time_tag = soup.find('time')
            date_label = time_tag.text.strip() if time_tag else "Date Not Found"
            
            pdf_regex = r'https://mopsov\.twse\.com\.tw/nas/STR/' + ticker + r'[^\'"]+\.pdf'
            matches = re.findall(pdf_regex, clean_html, re.IGNORECASE)
            
            if matches:
                pdf_link = matches[0]
                st.success("Success! Found the latest briefing document.")
                st.markdown(f"**Briefing Date/Time:** `{date_label}`")
                st.markdown(f"👉 [**Click here to download the PDF for {ticker}**]({pdf_link})")
            else:
                st.error(f"No briefing PDF found for ticker {ticker}.")
                
        except Exception as e:
            st.error(f"Error connecting to Poorstock: {e}")

    st.divider()

    # --- 3. Monthly Revenue Fetching (Direct from MOPS) ---
    st.markdown("### 📊 Monthly Revenue")
    st.info("Data pulled directly from MOPS. Note: MOPS groups data by the current calendar year.")
    
    with st.spinner("Bypassing MOPS firewall and parsing revenue tables..."):
        try:
            mops_main = "https://mops.twse.com.tw/mops/web/t05st10_ifrs"
            mops_ajax = "https://mops.twse.com.tw/mops/web/ajax_t05st10_ifrs"
            
            # Step A: Visit main page to get the session cookie (Bypasses WAF)
            scraper.get(mops_main)
            
            # Step B: Query the AJAX endpoint for the table
            payload = {
                'encodeURIComponent': '1',
                'step': '1',
                'firstin': '1',
                'off': '1',
                'queryName': 'co_id',
                'inpuType': 'co_id',
                'TYPEK': 'all',
                'isnew': 'true',
                'co_id': ticker
            }
            
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'Origin': 'https://mops.twse.com.tw',
                'Referer': mops_main
            }
            
            mops_resp = scraper.post(mops_ajax, data=payload, headers=headers)
            
            if "FOR SECURITY REASONS" in mops_resp.text:
                st.error("MOPS Firewall blocked the request.")
            elif "查無資料" in mops_resp.text:
                st.warning("No revenue data found for this ticker on MOPS.")
            else:
                # Step C: Use Pandas to read the raw HTML table
                tables = pd.read_html(io.StringIO(mops_resp.text))
                
                target_table = None
                for df in tables:
                    # MOPS revenue tables usually have multiple columns (Month, current year, last year, YoY change)
                    if len(df.columns) >= 4 and len(df) > 1:
                        target_table = df
                        break
                        
                if target_table is not None:
                    # Display the extracted table cleanly in Streamlit
                    st.dataframe(target_table, use_container_width=True)
                else:
                    st.warning("Could not extract a valid table from the MOPS page.")
                    
        except Exception as e:
            st.error(f"Error fetching Revenue: {e}")
