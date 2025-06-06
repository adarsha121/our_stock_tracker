# Stock Price Tracker

A streamlined Streamlit application for tracking stock prices from merolagani.com. 

![Stock Tracker Preview](https://via.placeholder.com/800x400?text=Stock+Price+Tracker)

## Features

- **Track Multiple Stocks**: Add any stock symbols from merolagani.com to your watchlist.
- **Real-time Updates**: Get the latest price and price change information with a single click.
- **Persistent Storage**: Your watchlist is saved between sessions.
- **Intuitive Interface**: User-friendly design that's easy to use.

## Usage

1. **Add Stocks**: Enter stock symbols in the sidebar and click "Add Stock".
2. **Update Prices**: Click "Refresh Prices" to get the latest data.
3. **Remove Stocks**: Use the "❌" buttons to remove stocks from your watchlist.

## Installation for Local Development

```bash
# Clone the repository
git clone https://github.com/your-username/stock-tracker.git
cd stock-tracker

# Install dependencies
pip install -r requirements.txt

# Install playwright dependencies
playwright install firefox

# Run the app
streamlit run app.py
```

## Deployment

This app is designed to be easily deployed on Streamlit Cloud:

1. Fork this repository
2. Connect your GitHub account to Streamlit Cloud
3. Deploy the app directly from the repository

## Technical Details

- Built with Streamlit and Playwright
- Uses SQLite for data persistence
- Headless browser automation for data scraping

## Limitations

- The app currently only supports stocks listed on merolagani.com
- Price updates must be manually triggered
- The app runs data scraping on public information from merolagani.com

## Acknowledgements

This project was created for educational purposes to demonstrate web scraping and building interactive dashboards with Streamlit.

## License

MIT License
