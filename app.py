import streamlit as st
import pandas as pd
from playwright.sync_api import sync_playwright
import time
from datetime import datetime
import os
import subprocess
import sys

# Install Playwright browsers automatically if running on Streamlit Cloud
try:
    browser_path = os.path.join(os.path.expanduser('~'), '.cache', 'ms-playwright')
    if not os.path.exists(browser_path):
        print("Installing playwright browser...")
        subprocess.run(["playwright", "install", "firefox", "--with-deps"], check=True)
except Exception as e:
    st.error(f"Failed to install browser: {str(e)}")

# Set page configuration
st.set_page_config(
    page_title="Stock Tracker",
    page_icon="📈",
    layout="wide"
)

# Initialize session state if needed
if 'stocks' not in st.session_state:
    st.session_state.stocks = pd.DataFrame(
        columns=['symbol', 'last_price', 'price_change', 'last_updated']
    )

# Persistent storage using Streamlit's cache
@st.cache_data(ttl=None, persist="disk")
def get_saved_stocks():
    # If we have stocks in session state, return those
    if not st.session_state.stocks.empty:
        return st.session_state.stocks
    
    # Otherwise return an empty dataframe (for first run)
    return pd.DataFrame(columns=['symbol', 'last_price', 'price_change', 'last_updated'])

def save_stocks(df):
    # Update both the session state and cached version
    st.session_state.stocks = df
    # Force cache refresh
    get_saved_stocks.clear()

def add_stock(symbol):
    df = get_saved_stocks()
    symbol = symbol.upper()
    
    # Check if stock already exists
    if symbol in df['symbol'].values:
        return False
    
    # Add new stock
    new_row = pd.DataFrame([{
        'symbol': symbol,
        'last_price': '0',
        'price_change': '0',
        'last_updated': 'Never'
    }])
    
    # Update dataframe
    updated_df = pd.concat([df, new_row], ignore_index=True)
    save_stocks(updated_df)
    return True

def delete_stock(symbol):
    df = get_saved_stocks()
    # Filter out the stock to delete
    updated_df = df[df['symbol'] != symbol].reset_index(drop=True)
    save_stocks(updated_df)

def update_stock_price(symbol, price, change, timestamp):
    df = get_saved_stocks()
    # Find and update the stock
    mask = df['symbol'] == symbol
    if mask.any():
        df.loc[mask, 'last_price'] = price
        df.loc[mask, 'price_change'] = change
        df.loc[mask, 'last_updated'] = timestamp
        save_stocks(df)

# Playwright functions
# Removed @st.cache_resource to fix threading issues
def fetch_stock_prices(stocks):
    # Use context manager pattern for Playwright to ensure proper cleanup
    with sync_playwright() as pw:
        try:
            st.info("Fetching stock prices... This may take a moment.")
            progress_bar = st.progress(0)
            
            # Launch browser with additional options for cloud compatibility
            browser = pw.firefox.launch(
                headless=True,
                args=[
                    '--disable-dev-shm-usage',
                    '--no-sandbox',
                    '--disable-gpu'
                ],
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
                    # Search for stock with more reliable approach
                    search_bar = page.query_selector('#ctl00_AutoSuggest1_txtAutoSuggest')
                    if search_bar:
                        search_bar.focus()
                        page.keyboard.press("Control+A")  # Select all text
                        page.keyboard.press("Delete")     # Clear it
                        search_bar.type(stock, delay=100)  # Type slower
                        time.sleep(1)
                        search_bar.press("Enter")
                    else:
                        st.warning(f"Could not find search bar for {stock}")
                        continue
                    
                    # Wait for page to load
                    time.sleep(2)
                    
                    # Extract data
                    ltp = page.query_selector('#ctl00_ContentPlaceHolder1_CompanyDetail1_lblMarketPrice')
                    price_change = page.query_selector('#ctl00_ContentPlaceHolder1_CompanyDetail1_lblChange')
                    
                    if ltp and price_change:
                        ltp_text = ltp.inner_text()
                        change_text = price_change.inner_text()
                        results.append((stock, ltp_text, change_text))
                        
                        # Update in dataframe
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
            # Make sure we attempt to close the browser even if there's an error
            if 'browser' in locals() and browser:
                try:
                    browser.close()
                except:
                    pass
            return False

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
        # No need to refresh stocks_df as we're updating the session state directly
    
    # Format the dataframe for display
    display_df = stocks_df.copy()
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

# Add shutdown controls section
with st.expander("App Controls"):
    st.write("To completely stop the Streamlit server:")
    st.code("Press Ctrl+C in the terminal where you started the app", language="bash")
    
    if st.button("🛑 Release Browser Resources", type="secondary"):
        try:
            st.success("This app now uses a new instance of Playwright for each operation.")
            st.info("Resource management is handled automatically.")
            st.info("Note: The Streamlit server is still running. To completely stop it, press Ctrl+C in your terminal.")
        except Exception as e:
            st.error(f"Error: {str(e)}")
