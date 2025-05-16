from typing import List, Optional, Dict
from urllib.parse import urlparse, parse_qs
from selenium.webdriver import Keys
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from utils.logger import setup_logger
import os
from bs4 import BeautifulSoup
from selenium import webdriver


SELENIUM_REMOTE_URL = os.getenv("SELENIUM_REMOTE_URL")
STATE = os.getenv("STATE")
logger = setup_logger("scraper")
async def fetch_company_details(url: str) -> dict:
    driver = None
    try:
        options = webdriver.ChromeOptions()
        options.add_argument(f'--lang=en-US')
        options.add_argument("--start-maximized")
        options.add_argument("--disable-webrtc")
        options.add_argument("--disable-features=WebRtcHideLocalIpsWithMdns")
        options.add_argument("--force-webrtc-ip-handling-policy=default_public_interface_only")
        options.add_argument("--disable-features=DnsOverHttps")
        options.add_argument("--no-default-browser-check")
        options.add_argument("--no-first-run")
        options.add_argument("--no-sandbox")
        options.add_argument("--test-type")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        options.set_capability("goog:loggingPrefs", {
            "performance": "ALL",
            "browser": "ALL"
        })
        driver = webdriver.Remote(
            command_executor=SELENIUM_REMOTE_URL,
            options=options
        )
        driver.set_page_load_timeout(30)
        driver.get("https://quickstart.sos.nh.gov/online")
        WebDriverWait(driver, 10).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
        elements = driver.find_elements("class name", "tile-primary")
        if elements:
            elements[0].click()
        else:
            return {}
        driver.execute_script(
            f"window.location.href='{url}'")
        WebDriverWait(driver, 10).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
        wait = WebDriverWait(driver, 10)
        wait.until(EC.presence_of_element_located((By.CLASS_NAME, "data_pannel")))
        html = driver.page_source
        return await parse_html_details(html)
    except Exception as e:
        logger.error(f"Error fetching data for query '{url}': {e}")
        return {}
    finally:
        if driver:
            driver.quit()

async def fetch_company_data(query: str) -> list[dict]:
    driver = None
    url = "https://quickstart.sos.nh.gov/online"
    try:

        options = webdriver.ChromeOptions()
        options.add_argument(f'--lang=en-US')
        options.add_argument("--start-maximized")
        options.add_argument("--disable-webrtc")
        options.add_argument("--disable-features=WebRtcHideLocalIpsWithMdns")
        options.add_argument("--force-webrtc-ip-handling-policy=default_public_interface_only")
        options.add_argument("--disable-features=DnsOverHttps")
        options.add_argument("--no-default-browser-check")
        options.add_argument("--no-first-run")
        options.add_argument("--no-sandbox")
        options.add_argument("--test-type")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        options.set_capability("goog:loggingPrefs", {
            "performance": "ALL",
            "browser": "ALL"
        })
        driver = webdriver.Remote(
            command_executor=SELENIUM_REMOTE_URL,
            options=options
        )
        driver.set_page_load_timeout(30)
        driver.get(url)
        WebDriverWait(driver, 10).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
        elements = driver.find_elements("class name", "tile-primary")
        if elements:
            elements[0].click()
        else:
            return []
        WebDriverWait(driver, 10).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
        wait = WebDriverWait(driver, 20)
        first_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#txtBusinessName"))
        )
        first_input.send_keys(query)
        first_input.send_keys(Keys.RETURN)
        tableResults = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "data_pannel")))
        html = tableResults.get_attribute("outerHTML")
        return await parse_html_search(html)
    except Exception as e:
        logger.error(f"Error fetching data for query '{query}': {e}")
        return []
    finally:
        if driver:
            driver.quit()

async def parse_html_search(html: str) -> List[Dict[str, Optional[str]]]:
    soup = BeautifulSoup(html, "html.parser")
    results = []

    table = soup.find("table", id="xhtml_grid")
    if not table:
        return results

    rows = table.tbody.find_all("tr")
    for row in rows:
        cols = row.find_all("td")
        if not cols or len(cols) < 8:
            continue
        name_tag = cols[0].find("a")
        name = name_tag.get_text(strip=True) if name_tag else None
        link = name_tag["href"] if name_tag and "href" in name_tag.attrs else None
        id_ = cols[1].get_text(strip=True) if len(cols) > 1 else None
        status = cols[7].get_text(strip=True) if len(cols) > 7 else None

        results.append({
            "state": STATE,
            "name": name,
            "id": id_,
            "url": "https://quickstart.sos.nh.gov" + link,
            "status": status
        })

    return results

async def parse_html_details(html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")

    def get_text(label: str) -> Optional[str]:
        td = soup.find("td", string=lambda s: s and s.strip().startswith(label))
        if td:
            next_td = td.find_next_sibling("td")
            return next_td.get_text(strip=True) if next_td else None
        return None

    def get_officers() -> List[Dict]:
        officers = []
        principals_th = soup.find("th", string=lambda s: s and "Principals Information" in s)
        if not principals_th:
            return officers

        table = principals_th.find_parent("table")
        if not table:
            return officers

        # Сканируем все строки таблицы после заголовка
        rows = table.find_all("tr")[1:]
        for row in rows:
            cols = row.find_all("td")
            if len(cols) == 2:
                name_title = cols[0].get_text(strip=True)
                address = cols[1].get_text(strip=True)
                if "/" in name_title:
                    name, title = [x.strip() for x in name_title.split("/", 1)]
                else:
                    name = name_title
                    title = None
                officers.append({
                    "name": name or None,
                    "title": title or None,
                    "address": address or None,
                })
        return officers

    def get_registered_agent_info() -> Dict[str, Optional[str]]:
        agent_th = soup.find("th", string=lambda s: s and "registered agent information" in s.lower())
        if not agent_th:
            return {"agent_name": None, "agent_address": None}

        table = agent_th.find_parent("table")
        if not table:
            return {"agent_name": None, "agent_address": None}

        name = None
        address = None
        for tr in table.find_all("tr"):
            cells = tr.find_all("td")
            if len(cells) < 2:
                continue
            label = cells[0].get_text(strip=True).lower()
            value = cells[1].get_text(strip=True)
            if "name" in label:
                name = value
            elif "registered office address" in label:
                address = value

        return {"agent_name": name or None, "agent_address": address or None}

    # Извлекаем значения
    data = {
        "business_name": get_text("Business Name:"),
        "business_id": get_text("Business ID:"),
        "business_type": get_text("Business Type:"),
        "business_status": get_text("Business Status:"),
        "business_creation_date": get_text("Business Creation Date:"),
        "principal_office_address": get_text("Principal Office Address:"),
        "mailing_address": get_text("Mailing Address:"),
        "officers": get_officers(),
        "documents": []
    }

    # Добавляем информацию об агенте
    data.update(get_registered_agent_info())

    return data
