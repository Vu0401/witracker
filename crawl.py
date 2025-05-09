from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time
import html2text
from datetime import datetime
import os
import re
import streamlit as st
from config import MONTH_NAMES  # Import MONTH_NAMES from config module
from agents import newspaper_summarizer  # Import summarizer function from agents module

# Function to validate the input date against the current date
def check_date(date_str, curr_date):
    try:
        # Parse date string into datetime object and check if it's in the future
        sel_date = datetime.strptime(date_str, "%d/%m/%Y")
        if sel_date > curr_date:
            raise ValueError(f"Date {date_str} is in the future.")
        # Split date string into day, month, year and format target month-year
        day, month, year = date_str.split('/')
        return day, f"{MONTH_NAMES[month]} {year}"
    except ValueError as e:
        # Handle invalid date format or future date error
        print(f"Error: {e if str(e).startswith('Date') else f'Date {date_str} is invalid.'}")
        return None, None

# Function to initialize Chrome driver in headless mode with specific options
def setup_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--log-level=3")
    chrome_options.add_argument("--silent")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.binary_location = "/usr/bin/chromium"
    # Chống chặn headless
    chrome_options.add_argument("user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)
    
    service = Service()
    driver = webdriver.Chrome(service=service, options=chrome_options)
    #driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()),options=chrome_options)
    return driver, WebDriverWait(driver, 60)  # Return driver and wait object

# Function to log into the website using provided credentials
def login(driver, wait, username, password, progress_callback=None):
    if progress_callback:
        progress_callback("Navigating to login page...")
    
    driver.maximize_window()
    driver.get("https://wichart.vn/login?redirect=%2Fdashboard")
    
    if progress_callback:
        progress_callback(f"Current URL: {driver.current_url}")
        progress_callback(f"Page source: {driver.page_source}")
    
    # Thử đợi lâu hơn hoặc linh hoạt hơn
    for _ in range(2):  # Thử 2 lần
        try:
            username_field = wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "input[type='text']")),
                message="Timeout waiting for username input"
            )
            if progress_callback:
                progress_callback("Username field found!")
            username_field.send_keys(username)
            break
        except:
            if progress_callback:
                progress_callback("Retrying to find username field...")
            time.sleep(10)  # Chờ thêm 10 giây trước khi thử lại
    
    password_field = wait.until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, "input[type='password']")),
        message="Timeout waiting for password input"
    )
    password_field.send_keys(password)
    
    time.sleep(1)
    submit_button = wait.until(
        EC.element_to_be_clickable((By.XPATH, "//button[@type='submit']")),
        message="Timeout waiting for submit button"
    )
    submit_button.click()
    
    wait.until(EC.url_contains("/dashboard"), message="Timeout waiting for dashboard redirect")
    if progress_callback:
        progress_callback("Login successful!")
        
# Function to scroll to a specific element on the page
def scroll_to(driver, wait, xpath, attempts=5):
    for _ in range(attempts):  # Try scrolling up to 'attempts' times
        try:
            elem = driver.find_element(By.XPATH, xpath)  # Locate element
            # Smoothly scroll to center the element in view
            driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", elem)
            wait.until(EC.visibility_of_element_located((By.XPATH, xpath)))  # Wait until visible
            return True
        except:
            # Scroll down 1000px if element not found
            driver.execute_script("window.scrollBy(0, 1000);")
            time.sleep(5)  # Wait for page to load
    return False  # Return False if element not found after attempts

# Function to select a specific date from the calendar
def pick_date(driver, wait, day, target):
    # Click the calendar button to open date picker
    calendar = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button[aria-label^='Choose date']")))
    calendar.click()
    time.sleep(5)  # Wait for calendar to open
    # Navigate to the target month-year by clicking left arrow
    while driver.find_element(By.CSS_SELECTOR, "div#\\:rv\\:-grid-label").text != target:
        wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "svg[data-testid='ArrowLeftIcon']"))).click()
        time.sleep(5)
    # Select the specified day
    wait.until(EC.element_to_be_clickable((By.XPATH, f"//button[contains(@class, 'MuiPickersDay-root') and text()='{day}']"))).click()
    time.sleep(5)  # Wait for selection to register

# Function to extract article content from the page source
def extract_article_content(driver):
    markdown = html2text.HTML2Text()  # Initialize HTML to Markdown converter
    markdown.ignore_links = False  # Keep links in the output
    text = markdown.handle(driver.page_source)  # Convert page source to Markdown
    lines = text.splitlines()  # Split into lines
    target = "3. Tất cả tin tức"  # Target section to extract content from
    for i, line in enumerate(lines):
        if target in line:
            return "\n".join(lines[i + 1:]).strip()  # Return content after target
    return None  # Return None if target not found

# Function to process an article and append its summary to results
def save_article(driver, wait, xpath, count, results):
    if not scroll_to(driver, wait, xpath):  # Scroll to article element
        print(f"Article {count}: Not found.")
        return False
    
    wait.until(EC.element_to_be_clickable((By.XPATH, xpath))).click()  # Click article
    time.sleep(5)  # Wait for content to load
    wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "div.MuiBox-root div.MuiTypography-body1")))  # Wait for content visibility
    
    text = extract_article_content(driver)
    text = re.sub(r'(?<!\n)\n(?!\n)', ' ', text) # Extract raw content
    title = text.split("\n")[0].replace("#", "").strip()
    summarized_content = newspaper_summarizer(text)  # Summarize the content
    summarized_content["title"] = title
    if text:  # If content exists, append summarized text
        results.append(summarized_content)
        print(f"Article {count}: Added to results.")
    else:
        print(f"Article {count}: '3. Tất cả tin tức' not found.")
    
    try:
        # Try to close the modal
        wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "svg.MuiSvgIcon-root.css-tlf7xk"))).click()
        # time.sleep(1)
    except:
        # Reload news page if modal cannot be closed
        print(f"Article {count}: Could not close modal.")
        driver.get("https://wichart.vn/news")
        time.sleep(3)
    return True

# Function to fetch a specified number of articles
def fetch_articles(driver, wait, max_articles=None, progress_callback=None):
    results = []
    k = 2
    count = 1
    while True:
        for i in range(1, 16):
            try:
                xpath = f'/html/body/div[2]/div[1]/div[3]/div/div/div[2]/div[{k}]/div/div[{i}]/div[3]/p'
                if save_article(driver, wait, xpath, count, results):
                    if progress_callback:
                        progress_callback(f'Article {count}: "{results[-1]["title"]}" has been added to results.')
                    count += 1
                    if max_articles is not None and count > max_articles:
                        if progress_callback:
                            progress_callback(f"Stopped after fetching {max_articles} articles.")
                        return results
                else:
                    break
            except Exception as e:
                if progress_callback:
                    progress_callback(f"Error processing article {count} (k={k}, i={i}): {e}")
                break
        
        if i == 15:
            more_xpath = "/html/body/div[2]/div[1]/div[3]/div/div/div[3]/button"
            if scroll_to(driver, wait, more_xpath):
                wait.until(EC.element_to_be_clickable((By.XPATH, more_xpath))).click()
                time.sleep(5)
                k += 1
            else:
                if progress_callback:
                    progress_callback("No more articles or 'Load more' button not found.")
                break
        else:
            if progress_callback:
                progress_callback("All articles fetched.")
            break
    
    if progress_callback:
        progress_callback(f"Completed fetching {len(results)} articles.")
    return results

# Main function to scrape articles and return results
def scrape_articles(username, password, selected_date, max_articles, progress_callback=None):


    # Validate selected date
    current_date = datetime.now()
    day, target_month_year = check_date(selected_date, current_date)
    if day is None:
        if progress_callback:
            progress_callback("Invalid date selected!")
        return None

    # Initialize Chrome driver
    driver, wait = setup_driver()


    login(driver, wait, username, password)
    driver.get("https://wichart.vn/news")
    driver.maximize_window()
    time.sleep(120)

    pick_date(driver, wait, day, target_month_year)
    results = fetch_articles(driver, wait, max_articles, progress_callback)
    driver.quit()
    return results

   
        

    
