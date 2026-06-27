"""TikTok Creator Studio scraper - pulls user's own video analytics."""

import re
import json
import os
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException

SESSIONS_DIR = "memory/tiktok_sessions"

def _get_session_file(username: str) -> str:
    """Get session file path for a username"""
    os.makedirs(SESSIONS_DIR, exist_ok=True)
    safe_username = username.replace("@", "").replace("/", "_")
    return os.path.join(SESSIONS_DIR, f"{safe_username}.json")

def _save_session_cookies(username: str, cookies: list):
    """Save browser cookies to file"""
    session_file = _get_session_file(username)
    try:
        with open(session_file, 'w') as f:
            json.dump(cookies, f)
    except Exception as e:
        print(f"Could not save session: {e}")

def _load_session_cookies(username: str) -> list:
    """Load browser cookies from file"""
    session_file = _get_session_file(username)
    try:
        if os.path.exists(session_file):
            with open(session_file, 'r') as f:
                return json.load(f)
    except Exception as e:
        print(f"Could not load session: {e}")
    return None

async def get_user_tiktok_analytics(username: str, password: str, force_login: bool = False) -> dict:
    """
    Log into user's TikTok Creator Studio
    Pull their video analytics
    Return list of videos with metrics or error dict

    Uses saved session if available to avoid repeated 2FA
    """

    # Setup Selenium Chrome options
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")

    driver = None

    try:
        driver = webdriver.Chrome(options=chrome_options)

        # Try to use saved session first (unless force_login)
        if not force_login:
            saved_cookies = _load_session_cookies(username)
            if saved_cookies:
                try:
                    driver.get("https://www.tiktok.com")
                    for cookie in saved_cookies:
                        try:
                            driver.add_cookie(cookie)
                        except Exception:
                            pass

                    # Go directly to Creator Studio
                    driver.get("https://www.tiktok.com/creator/studio/videos")
                    time.sleep(3)

                    # Check if session still valid
                    if "creator/studio" in driver.current_url or "videos" in driver.current_url:
                        videos = extract_videos_from_page(driver)
                        if videos:
                            return videos
                except Exception as e:
                    print(f"Saved session expired or invalid: {e}")

        # Fresh login
        driver.get("https://www.tiktok.com/login")
        time.sleep(3)

        # Find and fill username/email - try multiple selectors
        username_input = None
        selectors = [
            'input[name*="login"]',
            'input[name*="user"]',
            'input[placeholder*="Username"]',
            'input[placeholder*="Email"]',
            'input[placeholder*="Phone"]',
            'input[aria-label*="username"]',
            'input[aria-label*="email"]',
            'input[type="text"]'
        ]

        for selector in selectors:
            try:
                username_input = WebDriverWait(driver, 3).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                )
                if username_input:
                    print(f"Found username input with selector: {selector}")
                    break
            except TimeoutException:
                continue

        if not username_input:
            print(f"Page HTML (first 2000 chars): {driver.page_source[:2000]}")
            return {"error": "Could not find username field"}

        username_input.send_keys(username)
        time.sleep(1)

        # Find and fill password
        try:
            password_input = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'input[type="password"]'))
            )
            password_input.send_keys(password)
            time.sleep(1)
        except TimeoutException:
            return {"error": "Could not find password field"}

        # Click login button
        try:
            login_button = driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]')
            login_button.click()
        except NoSuchElementException:
            # Try pressing Enter
            password_input.submit()

        # Wait for page load
        time.sleep(5)

        # Check if login failed
        if "login" in driver.current_url and "error" in driver.current_url:
            return {"error": "Login failed. Check username and password"}

        # Navigate to Creator Studio
        driver.get("https://www.tiktok.com/creator/studio/videos")
        time.sleep(3)

        # Wait for videos to load
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, '[data-e2e*="video"], [class*="VideoItem"]'))
            )
        except TimeoutException:
            time.sleep(2)

        # Extract videos
        videos = extract_videos_from_page(driver)

        # Save cookies for future logins
        if videos:
            try:
                cookies = driver.get_cookies()
                _save_session_cookies(username, cookies)
            except Exception as e:
                print(f"Could not save session cookies: {e}")

        if not videos:
            return {"error": "No videos found. Make sure you have published videos in Creator Studio"}

        return videos

    except TimeoutException:
        print(f"TIMEOUT ERROR in TikTok scraper")
        return {"error": "Timeout - TikTok took too long to load"}

    except Exception as e:
        error_msg = f"Error during login: {str(e)}"
        print(f"TIKTOK SCRAPER ERROR: {error_msg}")
        print(f"ERROR TYPE: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        return {"error": error_msg}

    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass

def extract_videos_from_page(driver) -> list:
    """Extract video data from Creator Studio page"""

    videos = []

    try:
        # Get all video rows
        video_rows = driver.find_elements(By.CSS_SELECTOR, '[data-e2e*="video-item"], tr[data-row*="video"], [class*="VideoItem"]')

        if not video_rows:
            # Try to get from table
            table_rows = driver.find_elements(By.CSS_SELECTOR, 'table tr')
            video_rows = table_rows[1:] if table_rows else []

        for row in video_rows[:50]:  # Limit to 50 most recent
            try:
                text = row.text

                if not text or len(text) < 10:
                    continue

                # Extract metrics from text
                views = extract_number(text, "views")
                likes = extract_number(text, "likes")
                comments = extract_number(text, "comments")
                shares = extract_number(text, "shares")

                # Need at least views and likes
                if views == 0 or likes == 0:
                    continue

                # Try to find video title/link
                try:
                    link = row.find_element(By.CSS_SELECTOR, 'a[href*="/video/"]')
                    video_url = link.get_attribute('href')
                    video_id = None
                    if video_url and "/video/" in video_url:
                        video_id = video_url.split("/video/")[-1].split("?")[0]
                except NoSuchElementException:
                    video_url = None
                    video_id = None

                engagement_rate = round((likes / views * 100), 2) if views > 0 else 0

                videos.append({
                    "video_id": video_id or f"video_{len(videos)}",
                    "views": views,
                    "likes": likes,
                    "comments": comments,
                    "shares": shares,
                    "engagement_rate": engagement_rate,
                    "url": video_url,
                })

            except Exception as e:
                continue

        return videos

    except Exception as e:
        return []

def extract_number(text: str, keyword: str) -> int:
    """Extract number from text like '1.2K views' or '1200 Likes'"""

    if not text:
        return 0

    # Create pattern to find numbers before keyword
    pattern = rf'([\d,.]+)\s*([KMB])?[^\d]*{keyword}'
    match = re.search(pattern, text, re.IGNORECASE)

    if match:
        num_str = match.group(1).replace(',', '').replace('.', '', num_str.count('.') - 1 if num_str.count('.') > 0 else 0)
        multiplier_str = match.group(2) or ''

        try:
            num = float(num_str)

            if 'K' in multiplier_str.upper():
                return int(num * 1000)
            elif 'M' in multiplier_str.upper():
                return int(num * 1000000)
            elif 'B' in multiplier_str.upper():
                return int(num * 1000000000)
            else:
                return int(num)
        except:
            return 0

    return 0
