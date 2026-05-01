import streamlit as st
import cloudscraper
import requests
import html
import re
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import calendar

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

    # --- 3. Monthly Revenue Fetching (YTD + Full Prior Year via FinMind) ---
    st.markdown("### 📊 Monthly Revenue (Year-over-Year)")
    st.info("Data sourced via FinMind Open API. Showing Current Year + Full Prior Year.")
    
    with st.spinner("Fetching and processing historical revenue data..."):
        try:
            current_year = datetime.now().year
            prior_year = current_year - 1
            
            # Pull data starting from Jan 1st of TWO years ago
            start_year = current_year - 2
            start_date = f"{start_year}-01-01"
            
            finmind_url = f"https://api.finmindtrade.com/api/v4/data?dataset=TaiwanStockMonthRevenue&data_id={ticker}&start_date={start_date}"
            
            fm_resp = requests.get(finmind_url, timeout=10)
            fm_data = fm_resp.json()
            
            if fm_data.get('status') == 200 and fm_data.get('data'):
                df = pd.DataFrame(fm_data['data'])
                
                df = df.sort_values(by=['revenue_year', 'revenue_month'])
                df['Month_Name'] = df['revenue_month'].apply(lambda x: calendar.month_name[x])
                
                df_prior = df[['revenue_year', 'revenue_month', 'revenue']].copy()
                df_prior['revenue_year'] += 1  
                df_prior.rename(columns={'revenue': 'Prior Year Revenue'}, inplace=True)
                
                merged_df = pd.merge(df, df_prior, on=['revenue_year', 'revenue_month'], how='left')
                merged_df['YoY Growth'] = ((merged_df['revenue'] / merged_df['Prior Year Revenue']) - 1) * 100
                
                # Filter for Current and Prior Year only
                merged_df = merged_df[merged_df['revenue_year'].isin([current_year, prior_year])]
                merged_df = merged_df.sort_values(by=['revenue_year', 'revenue_month'], ascending=[False, False])
                
                display_df = merged_df.copy()
                display_df.rename(columns={
                    'revenue_year': 'Year',
                    'Month_Name': 'Month',
                    'revenue': 'Current Revenue (TWD)'
                }, inplace=True)
                
                display_df['Current Revenue (TWD)'] = display_df['Current Revenue (TWD)'].apply(lambda x: f"{x:,.0f}" if pd.notnull(x) else "N/A")
                display_df['Prior Year Revenue'] = display_df['Prior Year Revenue'].apply(lambda x: f"{x:,.0f}" if pd.notnull(x) else "N/A")
                display_df['YoY Growth'] = display_df['YoY Growth'].apply(lambda x: f"{x:+.2f}%" if pd.notnull(x) else "N/A")
                
                final_table = display_df[['Year', 'Month', 'Current Revenue (TWD)', 'Prior Year Revenue', 'YoY Growth']]
                
                # --- Inject a spacer row when the year changes ---
                rows = []
                prev_year = None
                for index, row in final_table.iterrows():
                    if prev_year is not None and row['Year'] != prev_year:
                        rows.append({'Year': '', 'Month': '---', 'Current Revenue (TWD)': '', 'Prior Year Revenue': '', 'YoY Growth': ''})
                    rows.append(row.to_dict())
                    prev_year = row['Year']
                
                final_spaced_table = pd.DataFrame(rows)

                # --- Color code the YoY Column ---
                def highlight_yoy(val):
                    if not isinstance(val, str) or val in ['', 'N/A', '---']:
                        return ''
                    if val.startswith('+'):
                        return 'color: #16a34a;' # Green
                    elif val.startswith('-'):
                        return 'color: #dc2626;' # Red
                    return ''
                
                # Fix: Changed applymap to map to support the latest Pandas versions
                styled_table = final_spaced_table.style.map(highlight_yoy, subset=['YoY Growth'])
                st.dataframe(styled_table, use_container_width=True, hide_index=True)

            else:
                 st.warning(f"No revenue data found for {ticker} over the requested period.")
                 
        except Exception as e:
            st.error(f"Error fetching Revenue: {e}")
