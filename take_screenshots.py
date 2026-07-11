from playwright.sync_api import sync_playwright
import time
import os

def take_screenshots():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        
        # Navigate to Streamlit app
        page.goto("http://localhost:8501")
        
        # Wait for Streamlit to load completely
        time.sleep(5)
        
        # Screenshot 1: Runs Overview
        page.screenshot(path=os.path.join("docs", "screenshots", "overview.png"))
        
        # Scroll down to Trend Chart
        page.mouse.wheel(0, 500)
        time.sleep(1)
        page.screenshot(path=os.path.join("docs", "screenshots", "trends.png"))
        
        # Scroll down to Regression Viewer
        page.mouse.wheel(0, 1000)
        time.sleep(1)
        
        # Select the 9-regression diff
        # In Streamlit, selectbox inputs can be tricky.
        # We can just use the exact diff ID we know.
        try:
            page.click("text=Select a Diff ID to view report:")
            time.sleep(0.5)
            # Type the diff ID to filter and press Enter
            page.keyboard.type("180ed156")
            time.sleep(0.5)
            page.keyboard.press("Enter")
            time.sleep(2)
        except Exception as e:
            print(f"Could not select diff: {e}")
            
        page.screenshot(path=os.path.join("docs", "screenshots", "regression_viewer.png"))
        
        browser.close()

if __name__ == "__main__":
    take_screenshots()
