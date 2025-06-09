import streamlit as st
import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime, timedelta
import pandas as pd

st.set_page_config(page_title="SBI మ్యూచువల్ ఫండ్ పోర్ట్‌ఫోలియో ట్రాకర్", layout="wide")

# --- Enhanced Scraper Functions ---
def get_nav_from_moneycontrol(url, fund_name):
    """Scrape NAV data from Moneycontrol"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    
    # Look for NAV value in various possible locations
    nav_selectors = [
        'span.amt',
        '.nav_val',
        '[data-nav-value]',
        '.net-asset-value',
        'span:contains("₹")',
        '.price'
    ]
    
    nav_value = None
    
    # Try different selectors
    for selector in nav_selectors:
        elements = soup.select(selector)
        for element in elements:
            text = element.get_text().strip()
            # Look for currency patterns
            if re.search(r'₹?\s*\d+\.?\d*', text):
                nav_match = re.search(r'₹?\s*(\d+\.?\d*)', text)
                if nav_match:
                    nav_value = float(nav_match.group(1))
                    break
        if nav_value:
            break
    
    # Fallback: look for any element containing rupee symbol
    if not nav_value:
        all_text = soup.get_text()
        nav_matches = re.findall(r'₹\s*(\d+\.?\d*)', all_text)
        if nav_matches:
            nav_value = float(nav_matches[0])
    
    if not nav_value:
        raise ValueError(f"NAV not found for {fund_name}")
    
    return nav_value

def get_historical_nav_from_api(isin, duration="3M"):
    """Get historical NAV data from Moneycontrol API - Weekly data for 3 months"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://www.moneycontrol.com",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "X-Requested-With": "XMLHttpRequest"
    }
    
    # Updated API URL with correct parameters
    url = f"https://www.moneycontrol.com/mc/widget/mfnavonetimeinvestment/get_chart_value"
    params = {
        'isin': isin,
        'dur': duration,
        'ind_id': '',
        'classic': 'true',
        'type': 'benchmark',
        'investmentType': 'Equity'
    }
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=15)
        response.raise_for_status()
        

        
        data = response.json()
        
        historical_data = []
        
        # Check different possible data structures
        nav_data = None
        if 'g1' in data and data['g1']:
            nav_data = data['g1']
        elif 'data' in data and data['data']:
            nav_data = data['data']
        elif 'navData' in data and data['navData']:
            nav_data = data['navData']
        else:
            # Try to find any array in the response
            for key, value in data.items():
                if isinstance(value, list) and len(value) > 0:
                    nav_data = value
                    break
        
        if not nav_data:
            raise ValueError(f"No historical data found for ISIN: {isin}. Response keys: {list(data.keys())}")
        
        # Process the data
        all_data = nav_data
        weekly_data = []
        
        # Take every 7th record to get approximately weekly data
        step = max(1, len(all_data) // 12)  # Ensure we get around 12 data points
        
        for i in range(0, len(all_data), step):
            item = all_data[i]
            
            # Handle different possible field names
            date_str = None
            nav_value = None
            
            # Try different date field names
            for date_field in ['navDate', 'date', 'Date', 'nav_date']:
                if date_field in item:
                    date_str = item[date_field]
                    break
            
            # Try different NAV field names
            for nav_field in ['navValue', 'nav', 'Nav', 'NAV', 'nav_value', 'value']:
                if nav_field in item:
                    nav_value = float(item[nav_field])
                    break
            
            if date_str and nav_value:
                # Format date from YYYY-MM-DD to DD-MM-YYYY
                if '-' in date_str:
                    date_parts = date_str.split('-')
                    if len(date_parts) == 3:
                        formatted_date = f"{date_parts[2]}-{date_parts[1]}-{date_parts[0]}"
                    else:
                        formatted_date = date_str
                else:
                    formatted_date = date_str
                
                weekly_data.append({
                    'date': formatted_date,
                    'nav': nav_value
                })
        
        if not weekly_data:
            raise ValueError(f"Could not parse historical data for ISIN: {isin}")
        
        # Get last 12 weeks (3 months) and reverse to show latest first
        historical_data = weekly_data[-12:] if len(weekly_data) >= 12 else weekly_data
        historical_data.reverse()
        
        return historical_data
        
    except requests.exceptions.RequestException as e:
        raise ValueError(f"API request failed for ISIN {isin}: {str(e)}")
    except Exception as e:
        raise ValueError(f"Error processing historical data for ISIN {isin}: {str(e)}")

def format_indian_currency(amount):
    """Format currency in Indian style with commas"""
    if amount == 0:
        return "₹0"
    return f"₹{amount:,.2f}"

# --- Portfolio Data ---
portfolio = {
    "SBI లాంగ్ టర్మ్ ఈక్విటీ ఫండ్ (ELSS)": {
        "units": 1999.972,
        "url": "https://www.moneycontrol.com/mutual-funds/nav/sbi-long-term-equity-fund-regular-plan-growth/MSB093",
        "isin": "INF200K01495",
        "english_name": "SBI Long Term Equity Fund (ELSS)",
        "type": "ELSS"
    },
    "SBI మల్టీ అసెట్ అలొకేషన్ ఫండ్": {
        "units": 10108.827,
        "url": "https://www.moneycontrol.com/mutual-funds/nav/sbi-multi-asset-allocation-fund-regular-plan-growth/MSB075",
        "isin": "INF200K01800",  # Corrected ISIN for Regular Plan Growth
        "english_name": "SBI Multi Asset Allocation Fund",
        "type": "Multi Asset"
    }
}

# --- Header with Refresh Button ---
col1, col2 = st.columns([4, 1])
with col1:
    st.title("📊 SBI మ్యూచువల్ ఫండ్ పోర్ట్‌ఫోలియో ట్రాకర్")

with col2:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🔄 రిఫ్రెష్", type="primary"):
        st.rerun()

st.markdown("---")

# Get live NAV data
with st.spinner("లైవ్ NAV లు పొందుతున్నాం..."):
    nav_data = {}
    total_value = 0
    nav_errors = []
    
    for fund_name, fund_info in portfolio.items():
        try:
            nav_final = get_nav_from_moneycontrol(fund_info["url"], fund_name)
            units = fund_info["units"]
            current_value = nav_final * units
            total_value += current_value
            nav_data[fund_name] = nav_final
        except Exception as e:
            nav_errors.append(f"❌ {fund_name}: {str(e)}")
            nav_data[fund_name] = 0

if nav_errors:
    for error in nav_errors:
        st.error(error)
else:
    st.success("✅ డేటా అప్‌డేట్ అయింది!")

# --- Portfolio Summary ---
st.subheader("💰 పోర్ట్‌ఫోలియో సారాంశం")

elss_value = nav_data.get("SBI లాంగ్ టర్మ్ ఈక్విటీ ఫండ్ (ELSS)", 0) * portfolio["SBI లాంగ్ టర్మ్ ఈక్విటీ ఫండ్ (ELSS)"]["units"]
multi_value = nav_data.get("SBI మల్టీ అసెట్ అలొకేషన్ ఫండ్", 0) * portfolio["SBI మల్టీ అసెట్ అలొకేషన్ ఫండ్"]["units"]

col1, col2, col3 = st.columns(3)
with col1:
    st.metric(
        label="📊 మొత్తం పోర్ట్‌ఫోలియో వాల్యూ",
        value=format_indian_currency(total_value),
        delta=None
    )

with col2:
    st.metric(
        label="📈 ELSS ఫండ్ వాల్యూ", 
        value=format_indian_currency(elss_value),
        delta=None
    )

with col3:
    st.metric(
        label="📈 మల్టీ అసెట్ ఫండ్ వాల్యూ",
        value=format_indian_currency(multi_value),
        delta=None
    )

# --- Current NAV Details ---
st.subheader("🔹 ప్రస్తుత NAV వివరాలు")

col1, col2 = st.columns(2)
with col1:
    elss_nav = nav_data.get("SBI లాంగ్ టర్మ్ ఈక్విటీ ఫండ్ (ELSS)", 0)
    elss_units = portfolio["SBI లాంగ్ టర్మ్ ఈక్విటీ ఫండ్ (ELSS)"]["units"]
    elss_current_value = elss_nav * elss_units
    
    st.info(f"""
    **SBI లాంగ్ టర్మ్ ఈక్విటీ ఫండ్ (ELSS)**
    - ప్రస్తుత NAV: ₹{elss_nav:.2f}
    - మీ యూనిట్లు: {elss_units:,.3f}
    - ప్రస్తుత వాల్యూ: {format_indian_currency(elss_current_value)}
    """)

with col2:
    multi_nav = nav_data.get("SBI మల్టీ అసెట్ అలొకేషన్ ఫండ్", 0)
    multi_units = portfolio["SBI మల్టీ అసెట్ అలొకేషన్ ఫండ్"]["units"]
    multi_current_value = multi_nav * multi_units
    
    st.info(f"""
    **SBI మల్టీ అసెట్ అలొకేషన్ ఫండ్**
    - ప్రస్తుత NAV: ₹{multi_nav:.2f}
    - మీ యూనిట్లు: {multi_units:,.3f}
    - ప్రస్తుత వాల్యూ: {format_indian_currency(multi_current_value)}
    """)

# --- Historical NAV Tables (Separate for each fund type) ---
st.subheader("📊 చారిత్రక NAV పట్టిక (వారానికోసారి - గత 3 నెలలు)")

with st.spinner("చారిత్రక డేటా API నుండి పొందుతున్నాం..."):
    # Get historical data for both funds
    historical_errors = []
    elss_historical = []
    multi_historical = []
    
    
    try:
        elss_historical = get_historical_nav_from_api(portfolio["SBI లాంగ్ టర్మ్ ఈక్విటీ ఫండ్ (ELSS)"]["isin"])
    except Exception as e:
        historical_errors.append(f"❌ ELSS చారిత్రక డేటా లోపం: {str(e)}")
    
    try:
        multi_historical = get_historical_nav_from_api(portfolio["SBI మల్టీ అసెట్ అలొకేషన్ ఫండ్"]["isin"])
    except Exception as e:
        historical_errors.append(f"❌ మల్టీ అసెట్ చారిత్రక డేటా లోపం: {str(e)}")

if historical_errors:
    for error in historical_errors:
        st.error(error)

# --- ELSS Fund Historical Table ---
st.subheader("📈 SBI లాంగ్ టర్మ్ ఈక్విటీ ఫండ్ (ELSS) - వారానిక చరిత్ర")

elss_table = []
if elss_historical:
    for data in elss_historical:
        nav_value = data['nav']
        portfolio_value = nav_value * portfolio["SBI లాంగ్ టర్మ్ ఈక్విటీ ఫండ్ (ELSS)"]["units"]
        
        elss_table.append({
            "వారం (తేదీ)": data['date'],
            "NAV": f"₹{nav_value:.2f}",
            "మీ పోర్ట్‌ఫోలియో వాల్యూ": format_indian_currency(portfolio_value)
        })

if elss_table:
    df_elss = pd.DataFrame(elss_table)
    st.dataframe(
        df_elss, 
        use_container_width=True, 
        hide_index=True,
        column_config={
            "వారం (తేదీ)": st.column_config.TextColumn("వారం (తేదీ)", width="medium"),
            "NAV": st.column_config.TextColumn("NAV", width="medium"),
            "మీ పోర్ట్‌ఫోలియో వాల్యూ": st.column_config.TextColumn("మీ పోర్ట్‌ఫోలియో వాల్యూ", width="large")
        }
    )
else:
    st.warning("ELSS చారిత్రక డేటా అందుబాటులో లేదు")

# --- Multi Asset Fund Historical Table ---
st.subheader("📈 SBI మల్టీ అసెట్ అలొకేషన్ ఫండ్ - వారానిక చరిత్ర")

multi_table = []
if multi_historical:
    for data in multi_historical:
        nav_value = data['nav']
        portfolio_value = nav_value * portfolio["SBI మల్టీ అసెట్ అలొకేషన్ ఫండ్"]["units"]
        
        multi_table.append({
            "వారం (తేదీ)": data['date'],
            "NAV": f"₹{nav_value:.2f}",
            "మీ పోర్ట్‌ఫోలియో వాల్యూ": format_indian_currency(portfolio_value)
        })

if multi_table:
    df_multi = pd.DataFrame(multi_table)
    st.dataframe(
        df_multi, 
        use_container_width=True, 
        hide_index=True,
        column_config={
            "వారం (తేదీ)": st.column_config.TextColumn("వారం (తేదీ)", width="medium"),
            "NAV": st.column_config.TextColumn("NAV", width="medium"),
            "మీ పోర్ట్‌ఫోలియో వాల్యూ": st.column_config.TextColumn("మీ పోర్ట్‌ఫోలియో వాల్యూ", width="large")
        }
    )
else:
    st.warning("మల్టీ అసెట్ చారిత్రక డేటా అందుబాటులో లేదు")