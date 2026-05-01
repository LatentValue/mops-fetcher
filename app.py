import streamlit as st
import cloudscraper
import requests
import html
import re
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime, timedelta

# --- 1. Web App User Interface Setup ---
st.set_page_config(page_title="MOPS Briefing & Revenue Fetcher", page_icon="📈")
st.title("Taiwan Stock MOPS Fetcher")
st.write("Retrieve the latest Institutional Investor Conference (法說會) PDF and recent Monthly Revenue.")

ticker = st.text_input("Enter Taiwan Ticker (e.g., 6706):")

if st.button("Get Data") and ticker:
    ticker = ticker.strip()
    
    # --- 2. PDF Fetching (Poorstock uses Cloudflare -> Needs cloudscraper) ---
    st.markdown("### 📄 Latest Briefing PDF")
    with st.spinner(f"Querying Poorstock database for {ticker}..."):
        try:
            scraper = cloudscraper.create_scraper()
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

    # --- 3. Monthly Revenue Fetching (Using FinMind API to bypass MOPS WAF) ---
    st.markdown("### 📊 Monthly Revenue (Trailing 12 Months)")
    st.info("Data sourced via FinMind Open API (Aggregated from MOPS)")
    
    with st.spinner("Fetching revenue data..."):
        try:
            # Calculate the date exactly 1 year (365 days) ago
            start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
            
            # Query FinMind's API for the specific dataset
            finmind_url = f"https://api.finmindtrade.com/api/v4/data?dataset=TaiwanStockMonthRevenue&data_id={ticker}&start_date={start_date}"
            
            fm_resp = requests.get(finmind_url, timeout=10)
            fm_data = fm_resp.json()
            
            if fm_data.get('status') == 200 and fm_data.get('data'):
                # Convert the JSON data directly into a Pandas DataFrame
                df = pd.DataFrame(fm_data['data'])
                
                # Format the table to be clean and readable
                if 'date' in df.columns and 'revenue' in df.columns:
                    # Select only the relevant columns and rename them
                    display_df = df[['date', 'revenue_year', 'revenue_month', 'revenue']].copy()
                    display_df.rename(columns={
                        'date': 'Report Date',
                        'revenue_year': 'Year',
                        'revenue_month': 'Month',
                        'revenue': 'Revenue (TWD)'
                    }, inplace=True)
                    
                    # Add commas to the revenue numbers (e.g., 1000000 -> 1,000,000)
                    display_df['Revenue (TWD)'] = display_df['Revenue (TWD)'].apply(lambda x: f"{x:,.0f}")
                    
                    # Sort so the newest month is at the very top
                    display_df = display_df.sort_values(by='Report Date', ascending=False).reset_index(drop=True)
                    
                    # Display the final, polished table
                    st.dataframe(display_df, use_container_width=True)
                else:
                    st.warning("Data format from API was unexpected.")
            else:
                 st.warning(f"No revenue data found for {ticker} over the last 12 months.")
                 
        except Exception as e:
            st.error(f"Error fetching Revenue: {e}")
