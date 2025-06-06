import streamlit as st
import pandas as pd
import sqlite3
from playwright.sync_api import sync_playwright
import time
from datetime import datetime
import os
import subprocess
import sys

# Install Playwright browsers automatically if running on Streamlit Cloud
if not os.path.exists("/home/appuser/.cache/ms-playwright") and os.environ.get("STREAMLIT_SHARING", "") == "true":
    subprocess.run(["playwright", "install", "firefox"], check=True)

# Set page configuration
st.set_page_config(
    page_title="Stock Tracker",
    page_icon="📈",
    layout="wide"
)

# Database functions
def init_db():
    # Use a folder that persists in Streamlit Cloud
    conn = sqlite3.connect('./.streamlit/stock_tracker.db')
    c = conn.cursor()
    c.execute('''
    CREATE TABLE IF NOT EXISTS stocks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT UNIQUE,
        last_price TEXT,
        price_change TEXT,
        last_updated TEXT
    )
    ''')
    conn.commit()
    conn.close()

def get_saved_stocks():
    # Make sure directory exists for Streamlit Cloud
    os.makedirs('./.streamlit', exist_ok=True)
    conn = sqlite3.connect('./.streamlit/stock_tracker.db')
    
    # Create table if it doesn't exist (helpful after fresh deploy)
    c = conn.cursor()
    c.execute('''
    CREATE TABLE IF NOT EXISTS stocks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT UNIQUE,
        last_price TEXT,
        price_change TEXT,
        last_updated TEXT
    )
    ''')
    conn.commit()
    
    # Now read the data
    try:
        df = pd.read_sql_query("SELECT * FROM stocks", conn)
    except:
        df = pd.DataFrame(columns=['id', 'symbol', 'last_price', 'price_change', 'last_updated'])
    conn.close()
    return df

def add_stock(symbol):
    os.makedirs('./.streamlit', exist_ok=True)
    conn = sqlite3.connect('./.streamlit/stock_tracker.db')
    c = conn.cursor()
    try:
        c.execute("INSERT INTO stocks (symbol, last_price, price_change, last_updated) VALUES (?, '0', '0', 'Never')", 
                 (symbol.upper(),))
        conn.commit()
        success = True
    except sqlite3.IntegrityError:
        success = False
    conn.close()
    return success

def delete_stock(symbol):
    os.makedirs('./.streamlit', exist_ok=True)
    conn = sqlite3.connect('./.streamlit/stock_tracker.db')
    c = conn.cursor()
    c.execute("DELETE FROM stocks WHERE symbol = ?", (symbol,))
    conn.commit()
    conn.close()

def update_stock_price(symbol, price, change, timestamp):
    os.makedirs('./.streamlit', exist_ok=True)
    conn = sqlite3.connect('./.streamlit/stock_tracker.db')
    c = conn.cursor()
    c.execute("UPDATE stocks SET last_price = ?, price_change = ?, last_updated = ? WHERE symbol = ?", 
             (price, change, timestamp, symbol))
    conn.commit()
    conn.close()

# Playwright functions
@st.cache_resource
def get_playwright():
    return sync_playwright().start()

def fetch_stock_prices(stocks):
    pw = get_playwright()
    
    try:
        st.info("Fetching stock prices... This may take a moment.")
        progress_bar = st.progress(0)
        
        # Launch browser with additional options for cloud compatibility
        browser = pw.firefox.launch(
            headless=True,
            firefox_user_prefs={
                "browser.cache.disk.enable": False,
                "browser.cache.memory.enable": False
            }
        )
        page = browser.new_page()
        
        # Navigate to the site
        page.goto("https://merolagani.com")
        
        results = []
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        for i, stock in enumerate(stocks):
            progress_bar.progress((i+1)/len(stocks))
            
            try:
                # Search for stock
                search_bar = page.query_selector('#ctl00_AutoSuggest1_txtAutoSuggest')
                search_bar.fill("")  # Clear first - this is important
                search_bar.type(stock)
                search_bar.press("Enter")
                
                # Wait for page to load
                time.sleep(2)
                
                # Extract data
                ltp = page.query_selector('#ctl00_ContentPlaceHolder1_CompanyDetail1_lblMarketPrice')
                price_change = page.query_selector('#ctl00_ContentPlaceHolder1_CompanyDetail1_lblChange')
                
                if ltp and price_change:
                    ltp_text = ltp.inner_text()
                    change_text = price_change.inner_text()
                    results.append((stock, ltp_text, change_text))
                    
                    # Update in database
                    update_stock_price(stock, ltp_text, change_text, timestamp)
                else:
                    st.warning(f"Could not find data for {stock}")
                
            except Exception as e:
                st.error(f"Error processing {stock}: {str(e)}")
        
        # Close browser
        browser.close()
        progress_bar.empty()
        st.success(f"Updated prices for {len(results)} stocks!")
        
        return True
    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
        return False

# Initialize database
init_db()

# App UI
st.title("📈 Stock Price Tracker")

# Sidebar for adding stocks
with st.sidebar:
    st.header("Manage Stocks")
    
    # Create the text input field
    new_stock = st.text_input("Add a new stock symbol:", key="new_stock")
    add_button = st.button("Add Stock")
    
    if add_button and new_stock:
        if add_stock(new_stock):
            st.success(f"Added {new_stock.upper()} to your watchlist!")
            # Instead of directly modifying session state, use this approach:
            st.rerun()  # This will rerun the app, effectively clearing the input
        else:
            st.warning(f"{new_stock.upper()} is already in your watchlist.")

# Main area - show stock data
stocks_df = get_saved_stocks()

if not stocks_df.empty:
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.subheader("Your Stock Watchlist")
    
    with col2:
        refresh = st.button("🔄 Refresh Prices", type="primary")
        
    if refresh:
        fetch_stock_prices(stocks_df['symbol'].tolist())
        stocks_df = get_saved_stocks()  # Refresh the data
    
    # Format the dataframe for display
    if not stocks_df.empty:
        # Drop ID column and rename others
        display_df = stocks_df.drop(columns=['id'])
        display_df.columns = ['Symbol', 'Last Price', 'Price Change', 'Last Updated']
        
        # Apply styling based on price change
        def highlight_price_change(val):
            if isinstance(val, str):
                if val.startswith('+'):
                    return 'background-color: #c6f6d5; color: #22543d'  # Green background
                elif val.startswith('-'):
                    return 'background-color: #fed7d7; color: #822727'  # Red background
            return ''
        
        # Apply styling
        styled_df = display_df.style.applymap(
            highlight_price_change, 
            subset=['Price Change']
        )
        
        # Display the table
        st.dataframe(styled_df, use_container_width=True)
        
        # Option to delete stocks
        st.subheader("Remove stocks")
        cols = st.columns(5)
        for i, (_, row) in enumerate(stocks_df.iterrows()):
            col_index = i % 5
            with cols[col_index]:
                if st.button(f"❌ {row['symbol']}", key=f"delete_{row['symbol']}"):
                    delete_stock(row['symbol'])
                    st.rerun()
else:
    st.info("Your watchlist is empty. Add stocks using the sidebar.")
    st.caption("Example stock symbols: NGPL, RADHI, HRL, etc.")

# Footer
st.markdown("---")
st.caption("Data source: merolagani.com | Last refresh attempt: " + 
          datetime.now().strftime("%Y-%m-%d %H:%M:%S"))