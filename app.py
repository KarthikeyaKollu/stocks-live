import streamlit as st
import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime
import pandas as pd

st.set_page_config(page_title="SBI మ్యూచువల్ ఫండ్ పోర్ట్‌ఫోలియో ట్రాకర్", layout="wide")

# --- Enhanced Scraper Functions ---
def get_nav_from_moneycontrol(url, fund_name):
    """Scrape NAV data from Moneycontrol"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    try:
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
        
        return nav_value if nav_value else None
        
    except Exception as e:
        return None

def get_nav_from_google(query):
    """Fallback scraper using Google search"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")

        # Look for currency values in spans
        spans = soup.find_all("span")
        for span in spans:
            text = span.get_text()
            if "₹" in text and re.search(r'\d+\.?\d*', text):
                nav_match = re.search(r'₹?\s*(\d+\.?\d*)', text)
                if nav_match:
                    return float(nav_match.group(1))
        
        return None
    except Exception as e:
        return None

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
        "google_query": "SBI Long Term Equity Fund Regular Growth NAV",
        "english_name": "SBI Long Term Equity Fund (ELSS)"
    },
    "SBI మల్టీ అసెట్ అలొకేషన్ ఫండ్": {
        "units": 10108.827,
        "url": "https://www.moneycontrol.com/mutual-funds/nav/sbi-multi-asset-allocation-fund-regular-plan-growth/MSB075",
        "google_query": "SBI Multi Asset Allocation Fund Regular Growth NAV",
        "english_name": "SBI Multi Asset Allocation Fund"
    }
}

# --- Header with Refresh Button ---
col1, col2 = st.columns([4, 1])
with col1:
    st.title("📊 SBI మ్యూచువల్ ఫండ్ పోర్ట్‌ఫోలియో ట్రాకర్")
    st.markdown("లైవ్ NAV డేటాతో పోర్ట్‌ఫోలియో వాల్యూ లెక్కలు")

with col2:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🔄 డేటా రిఫ్రెష్ చేయండి", type="primary"):
        st.rerun()

# --- Main Content ---
st.markdown("---")

# Get live NAV data
with st.spinner("లైవ్ NAV లు పొందుతున్నాం మరియు పోర్ట్‌ఫోలియో వాల్యూ లెక్కిస్తున్నాం..."):
    nav_data = {}
    portfolio_data = []
    total_value = 0
    
    for fund_name, fund_info in portfolio.items():
        # Primary scraping from Moneycontrol
        nav_mc = get_nav_from_moneycontrol(fund_info["url"], fund_name)
        
        # Fallback to Google if Moneycontrol fails
        if nav_mc is None:
            nav_google = get_nav_from_google(fund_info["google_query"])
            nav_final = nav_google if nav_google is not None else 0
        else:
            nav_final = nav_mc
        
        # Calculate portfolio value for this fund
        units = fund_info["units"]
        current_value = nav_final * units if nav_final > 0 else 0
        total_value += current_value
        
        nav_data[fund_name] = nav_final
        portfolio_data.append({
            "ఫండ్ పేరు": fund_name,
            "యూనిట్లు": f"{units:,.3f}",
            "ప్రస్తుత NAV": f"₹{nav_final:.2f}" if nav_final > 0 else "అందుబాటులో లేదు",
            "ప్రస్తుత వాల్యూ": format_indian_currency(current_value) if current_value > 0 else "అందుబాటులో లేదు"
        })

st.success("✅ పోర్ట్‌ఫోలియో డేటా విజయవంతంగా అప్‌డేట్ చేయబడింది!")

# --- Portfolio Summary ---
st.subheader("💰 పోర్ట్‌ఫోలియో సారాంశం")

# Calculate individual fund values
elss_value = nav_data.get("SBI లాంగ్ టర్మ్ ఈక్విటీ ఫండ్ (ELSS)", 0) * portfolio["SBI లాంగ్ టర్మ్ ఈక్విటీ ఫండ్ (ELSS)"]["units"]
multi_value = nav_data.get("SBI మల్టీ అసెట్ అలొకేషన్ ఫండ్", 0) * portfolio["SBI మల్టీ అసెట్ అలొకేషన్ ఫండ్"]["units"]

col1, col2, col3 = st.columns(3)
with col1:
    st.metric(
        label="📊 మొత్తం పోర్ట్‌ఫోలియో వాల్యూ",
        value=format_indian_currency(total_value) if total_value > 0 else "లెక్కిస్తున్నాం...",
        delta=None
    )

with col2:
    st.metric(
        label="📈 ELSS ఫండ్ వాల్యూ", 
        value=format_indian_currency(elss_value) if elss_value > 0 else "అందుబాటులో లేదు",
        delta=None
    )

with col3:
    st.metric(
        label="📈 మల్టీ అసెట్ ఫండ్ వాల్యూ",
        value=format_indian_currency(multi_value) if multi_value > 0 else "అందుబాటులో లేదు",
        delta=None
    )

# --- Detailed Portfolio Table ---
st.subheader("📋 పోర్ట్‌ఫోలియో వివరాలు")
df_portfolio = pd.DataFrame(portfolio_data)

# Style the dataframe for better readability
st.dataframe(
    df_portfolio, 
    use_container_width=True, 
    hide_index=True,
    column_config={
        "ఫండ్ పేరు": st.column_config.TextColumn("ఫండ్ పేరు", width="large"),
        "యూనిట్లు": st.column_config.TextColumn("యూనిట్లు", width="medium"),
        "ప్రస్తుత NAV": st.column_config.TextColumn("ప్రస్తుత NAV", width="medium"),
        "ప్రస్తుత వాల్యూ": st.column_config.TextColumn("ప్రస్తుత వాల్యూ", width="large")
    }
)

# --- Current NAV Information ---
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

# --- Summary Table for Easy Reading ---
st.subheader("📊 సరళమైన సారాంశ పట్టిక")

summary_data = [
    {
        "వివరాలు": "మొత్తం పెట్టుబడి వాల్యూ",
        "మొత్తం": format_indian_currency(total_value),
        "స్థితి": "✅ చురుకుగా ఉంది" if total_value > 0 else "⚠️ డేటా లోడ్ అవుతున్నది"
    },
    {
        "వివరాలు": "ELSS ఫండ్ (పన్ను ఆదా)",
        "మొత్తం": format_indian_currency(elss_current_value),
        "స్థితి": f"NAV: ₹{elss_nav:.2f}" if elss_nav > 0 else "లోడ్ అవుతున్నది"
    },
    {
        "వివరాలు": "మల్టీ అసెట్ ఫండ్",
        "మొత్తం": format_indian_currency(multi_current_value),
        "స్థితి": f"NAV: ₹{multi_nav:.2f}" if multi_nav > 0 else "లోడ్ అవుతున్నది"
    }
]

df_summary = pd.DataFrame(summary_data)
st.dataframe(
    df_summary, 
    use_container_width=True, 
    hide_index=True,
    column_config={
        "వివరాలు": st.column_config.TextColumn("వివరాలు", width="large"),
        "మొత్తం": st.column_config.TextColumn("మొత్తం", width="large"),
        "స్థితి": st.column_config.TextColumn("స్థితి", width="medium")
    }
)

# --- Important Information ---
st.subheader("📝 ముఖ్యమైన సమాచారం")

col1, col2 = st.columns(2)
with col1:
    st.success("""
    **మీ పెట్టుబడి గురించి:**
    - రెండు SBI మ్యూచువల్ ఫండ్లలో పెట్టుబడి
    - ELSS ఫండ్ - పన్ను ఆదా కోసం
    - మల్టీ అసెట్ ఫండ్ - వైవిధ్యం కోసం
    - రోజువారీ NAV అప్‌డేట్లు
    """)

with col2:
    st.warning("""
    **గమనించవలసినవి:**
    - NAV రోజువారీ మారుతుంది
    - మార్కెట్ గంటలలో మాత్రమే అప్‌డేట్ అవుతుంది
    - అధికారిక NAV కోసం AMC వెబ్‌సైట్ చూడండి
    - పెట్టుబడికి ముందు సలహా తీసుకోండి
    """)

# --- Embedded Fund Pages ---
st.subheader("🌐 ఫండ్ వివరాల పేజీలు")
st.markdown("మనీకంట్రోల్ నుండి వివరమైన ఫండ్ సమాచారం:")

col1, col2 = st.columns(2)

with col1:
    st.markdown("### SBI లాంగ్ టర్మ్ ఈక్విటీ ఫండ్")
    st.markdown(f"[కొత్త ట్యాబ్‌లో తెరవండి]({portfolio['SBI లాంగ్ టర్మ్ ఈక్విటీ ఫండ్ (ELSS)']['url']})")
    
    st.components.v1.iframe(
        portfolio["SBI లాంగ్ టర్మ్ ఈక్విటీ ఫండ్ (ELSS)"]["url"],
        height=400,
        scrolling=True
    )

with col2:
    st.markdown("### SBI మల్టీ అసెట్ అలొకేషన్ ఫండ్")
    st.markdown(f"[కొత్త ట్యాబ్‌లో తెరవండి]({portfolio['SBI మల్టీ అసెట్ అలొకేషన్ ఫండ్']['url']})")
    
    st.components.v1.iframe(
        portfolio["SBI మల్టీ అసెట్ అలొకేషన్ ఫండ్"]["url"],
        height=400,
        scrolling=True
    )

# --- Footer ---
st.markdown("---")
col1, col2 = st.columns([3, 1])
with col1:
    st.caption("**డేటా మూలాలు:** ప్రధానం - Moneycontrol.com | ప్రత్యామనయం - Google శోధన")
    st.caption("⚠️ **నిరాకరణ:** NAV విలువలు పబ్లిక్ మూలాల నుండి తీసుకోబడ్డాయి మరియు రియల్-టైమ్ కాకపోవచ్చు. అధికారిక విలువల కోసం, దయచేసి AMFI లేదా ఫండ్ హౌస్ వెబ్‌సైట్లను చూడండి.")

with col2:
    st.caption(f"**చివరిసారి అప్‌డేట్:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")