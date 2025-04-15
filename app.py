import time
import threading
import random
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException

# Danh sách các cổng debug của Chrome
DEBUG_PORTS = [
    "127.0.0.1:9222",
    "127.0.0.1:9223",
    "127.0.0.1:9224",
    "127.0.0.1:9225",
    "127.0.0.1:9226",
    "127.0.0.1:9227"]

# Danh sách User-Agent ngẫu nhiên
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15"
]

# Danh sách trang web cần xử lý
URLS = [
    "https://fmcpay.com/dashboard",
    "https://fmcpay.com/markets",
    "https://fmcpay.com/stakings",
    "https://fmcpay.com/exchange",
    "https://fmcpay.com/wallet/spot"
]

# Thời gian chờ (giây)
PAGE_LOAD_DELAY = 5
CAPTCHA_DELAY = 10
CLICK_DELAY = 3
CYCLE_DELAY = 210  # Chu kỳ lặp lại, có thể đổi thành 320 nếu cần
THREAD_START_DELAY = 30  # Độ trễ giữa các luồng

def initialize_driver(port, user_agent):
    """Khởi tạo trình duyệt Chrome với cổng debug và User-Agent."""
    chrome_options = webdriver.ChromeOptions()
    chrome_options.debugger_address = port
    chrome_options.add_argument(f'--user-agent={user_agent}')
    return webdriver.Chrome(options=chrome_options)

def handle_captcha(driver, port):
    """Xử lý Cloudflare CAPTCHA nếu có."""
    try:
        captcha_iframe = driver.find_element(By.XPATH, '//iframe[contains(@title, "Cloudflare security challenge")]')
        driver.switch_to.frame(captcha_iframe)
        checkbox_element = driver.find_element(By.XPATH, '//input[@type="checkbox"]')
        checkbox_element.click()
        print(f"✅ Click vào checkbox Cloudflare thành công trên cổng {port}!")
        time.sleep(CAPTCHA_DELAY)
        driver.switch_to.default_content()
    except NoSuchElementException:
        print(f"⚠️ Không tìm thấy Cloudflare CAPTCHA trên cổng {port}, tiếp tục...")

def click_gift_image(driver, port):
    """Tìm và click vào ảnh gift.svg."""
    try:
        img_element = driver.find_element(By.XPATH, '//img[@src="/assets/gift.svg"]')
        div_element = img_element.find_element(By.XPATH, './parent::div')
        div_element.click()
        print(f"🎉 Click vào ảnh thành công trên cổng {port}!")
        time.sleep(CLICK_DELAY)
    except NoSuchElementException:
        print(f"⏩ Không tìm thấy ảnh trên cổng {port}, bỏ qua...")

def process_url(driver, url, port):
    """Xử lý một URL cụ thể."""
    try:
        print(f"\n🚀 Đang mở trang: {url} trên cổng {port}")
        driver.get(url)
        time.sleep(PAGE_LOAD_DELAY)
        handle_captcha(driver, port)
        click_gift_image(driver, port)
    except Exception as e:
        print(f"❌ Lỗi khi xử lý trang {url} trên cổng {port}: {str(e)}")

def process_chrome_instance(port, user_agent, initial_delay):
    """Hàm xử lý từng instance Chrome với độ trễ ban đầu."""
    try:
        # Thêm độ trễ ban đầu để các luồng chạy cách nhau
        print(f"\n⏳ Đợi {initial_delay} giây trước khi khởi động cổng {port}...")
        time.sleep(initial_delay)

        print(f"\n🌐 Kết nối tới Chrome tại cổng {port}...")
        driver = initialize_driver(port, user_agent)
        while True:
            print(f"\n⏳ Bắt đầu chu trình mới cho cổng {port}...")
            for url in URLS:
                process_url(driver, url, port)
            print(f"\n🔄 Đợi {CYCLE_DELAY} giây trước khi chạy lại trên cổng {port}...")
            time.sleep(CYCLE_DELAY)
    except Exception as e:
        print(f"❌ Lỗi khi kết nối tới Chrome tại cổng {port}: {str(e)}")
    finally:
        try:
            driver.quit()
        except:
            pass

def main():
    """Hàm chính để khởi động các luồng với độ trễ giữa chúng."""
    threads = []

    for i, port in enumerate(DEBUG_PORTS):
        user_agent = random.choice(USER_AGENTS)
        initial_delay = i * THREAD_START_DELAY  # Độ trễ tăng dần: 0s, 30s, 60s, ...
        thread = threading.Thread(target=process_chrome_instance, args=(port, user_agent, initial_delay))
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

if __name__ == "__main__":
    main()