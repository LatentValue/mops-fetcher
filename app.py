import streamlit as st
import cloudscraper
import html
import re
from bs4 import BeautifulSoup

st.set_page_config(page_title="MOPS Briefing Fetcher", page_icon="📈")
st.title("Taiwan Stock MOPS PDF Fetcher")
st.write("Enter a Taiwan stock ticker to instantly retrieve the latest Institutional Investor Conference (法說會) presentation.")

ticker = st.text_input("Enter Taiwan Ticker (e.g., 6706):")

if st.button("Get Latest PDF") and ticker:
    ticker = ticker.strip()
    
    with st.spinner(f"Querying database for {ticker}..."):
        url = f"https://poorstock.com/earningcall/{ticker}"
        scraper = cloudscraper.create_scraper()
        
        try:
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
            st.error(f"Error: {e}")