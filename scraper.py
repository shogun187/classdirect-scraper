import logging
import subprocess
import time
import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Custom exceptions
class ShipNotFound(Exception):
    """Raised when the asset details button is not found."""
    pass

class ShipDetailsFailedToLoad(Exception):
    """Raised when the registry information does not load within the timeout."""
    pass

def inject_console_error_listener(driver):
    """Injects a JS snippet that captures console.error messages."""
    script = """
        if (!window._capturedErrors) {
            window._capturedErrors = [];
            // Override console.error
            var originalConsoleError = console.error;
            console.error = function() {
                window._capturedErrors.push(Array.from(arguments).join(' '));
                originalConsoleError.apply(console, arguments);
            };

            // Global error handler for uncaught errors
            window.onerror = function(message, source, lineno, colno, error) {
                var errorMsg = message + " at " + source + ":" + lineno + ":" + colno;
                window._capturedErrors.push(errorMsg);
            };
        }
        """
    driver.execute_script(script)

def check_for_console_errors(driver, timeout=3):
    """Poll for any console errors that have been captured."""
    end_time = time.time() + timeout
    while time.time() < end_time:
        errors = driver.execute_script("return window._capturedErrors || [];")
        if errors:
            return errors
        time.sleep(0.2)
    return []





def setup_driver():
    # chrome_options = webdriver.ChromeOptions()
    # # Path to your custom user data directory (make sure this path exists)
    # profile_path = r"user-data-dir=C:\Users\shaugn\AppData\Local\Google\Chrome\User Data"
    # profile_name = 'Shaugn Tan'
    #
    # chrome_options.add_argument(f"--user-data-dir={profile_path}")
    # chrome_options.add_argument(f"--profile-directory={profile_name}")
    # # chrome_options.add_experimental_option("detach", True)
    #
    # chrome_options.binary_location = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    # chrome_options.page_load_strategy = 'eager'
    # service = Service("F:/projects/chromedriver.exe")
    # driver = webdriver.Chrome(service=service, options=chrome_options)
    # print('driver set up')
    # return driver






    logger = logging.getLogger('selenium')
    print('setting up driver')
    profile_path = r"C:\Users\shaugn\AppData\Roaming\Mozilla\Firefox\Profiles\ucrf1um4.default-release"

    options = webdriver.FirefoxOptions()
    options.profile = profile_path
    options.binary_location = r"C:\Program Files\Mozilla Firefox\firefox.exe"
    options.page_load_strategy = 'eager'

    service = Service("F:/projects/geckodriver.exe", service_args=['--log', 'error'], log_output=subprocess.STDOUT)
    driver = webdriver.Firefox(service=service, options=options)
    print('driver set up')
    return driver


def scrape_vessel_data(url, driver):
    driver.get(url)
    inject_console_error_listener(driver)
    # browserLogs = driver.get_log('driver')
    # print(browserLogs)




    # Wait until the Accept T&C button is present in the DOM
    accept_btn = WebDriverWait(driver, 8).until(
        EC.presence_of_element_located(
            (By.XPATH, "//button[contains(., 'Accept terms and conditions')]")
        )
    )

    # Scroll to bottom so that the button becomes enabled
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

    # Wait until the button is enabled (its "disabled" attribute is gone)
    WebDriverWait(driver, 5).until(lambda d: accept_btn.is_enabled())

    accept_btn.click()







    try:
        asset_details_btn = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located(
                (By.XPATH, "//a[contains(., 'Asset details')]")
            )
        )

        time.sleep(1)

        asset_details_btn.click()

    except Exception:
        print("Ship Not Found")
        raise ShipNotFound()

    try:
        # Wait for an element with class "detail" to appear (up to 10 seconds)
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, "//h3[contains(., 'Registry information')]"))
        )

    except Exception:
        print('Ship found but details failed to load')
        raise ShipDetailsFailedToLoad()

    # Get the current page source and parse it
    page_content = driver.page_source
    soup = BeautifulSoup(page_content, "html.parser")
    return scrape_fields(soup)

def scrape_fields(soup):

    data = {}

    # Extract the ship name from the md-ink-ripple element.
    ship_elem = soup.select_one("md-ink-ripple.asset-name")
    if ship_elem:
        ship_name = ship_elem.get("title", "").strip()
        if ship_name:
            data["Ship Name"] = ship_name

    # Process the "detail" sections
    detail_sections = soup.find_all("div", class_="detail")
    for section in detail_sections:
        # Top of the page fields: header in <span class="label"> and value in <strong>
        header_elem = section.find("span", class_="label")
        value_elem = section.find("strong")
        if header_elem and value_elem:
            header = header_elem.get_text(strip=True).rstrip(":")
            value = value_elem.get_text(strip=True)
            data[header] = value

        # Bottom of the page fields: header in <div class="title"> and value in <div class="content">
        bottom_header = section.find("div", class_="title")
        bottom_value = section.find("div", class_="content")
        if bottom_header and bottom_value:
            header_text = bottom_header.get_text(strip=True)
            value_text = bottom_value.get_text(strip=True)
            if header_text not in ["Asset type", "Flag", "Date of build", "Gross tonnage"]:
                data[header_text] = value_text

    print('data is', data)
    return data

def main(input_excel, output_excel, failed_urls_csv):
    url_df = pd.read_excel(input_excel)

    # Initialize the WebDriver
    driver = setup_driver()

    all_vessel_data = []
    index = 0
    failed_urls = []

    for url in url_df['links']:  # Assuming the column containing URLs is named 'links'
        index += 1
        start_time = time.time()  # Record the start time
        try:
            print(f"{index}. Scraping data for {url}")

            vessel_data = scrape_vessel_data(url, driver)
            all_vessel_data.append(vessel_data)


        except ShipDetailsFailedToLoad as e:
            failed_urls.append(url)
            continue

        except ShipNotFound as e:
            continue

        except Exception as e:
            print('failed due to', e)
            failed_urls.append(url)
            continue

        end_time = time.time()
        time_taken = end_time - start_time
        print(f"Done in {time_taken:.2f}s")

    # Close the driver
    driver.quit()

    # Create a DataFrame from the list of dictionaries
    combined_df = pd.DataFrame(all_vessel_data)

    # Save the combined DataFrame to an Excel file
    combined_df.to_excel(output_excel, index=False)

    print(f"Vessel data has been saved to {output_excel}")


    # Save the failed URLs to a CSV file
    failed_urls_df = pd.DataFrame(failed_urls, columns=['failed_url'])
    failed_urls_df.to_csv(failed_urls_csv, index=False)
    print(f"Failed URLs have been saved to {failed_urls_csv}")

if __name__ == "__main__":
    input_excel = 'failed_urls_4&5&6&7.xlsx'  # Path to the input Excel file containing URLs
    output_excel = 'output_failed_urls_4&5&6&7.xlsx'  # Path to the output Excel file
    failed_urls_csv = 'failed_urls_4&5&6&7_again.csv'
    main(input_excel, output_excel, failed_urls_csv)

    # BEST TO CLEAR CHROME BROWSER CACHE BEFORE RUNNING