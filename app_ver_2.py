# chrome_automation.py
import os
import time
import threading
import random
import pyotp
import subprocess
import logging
import shutil
import platform
from dataclasses import dataclass, field
from typing import List, Optional, Dict
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    WebDriverException,
    ElementClickInterceptedException,
    StaleElementReferenceException,
)
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from pathlib import Path

# ====== Cấu hình Logging ======
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [%(threadName)s] - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# ====== Tìm Chrome Executable ======
def find_chrome_executable() -> Optional[str]:
    """Tự động tìm đường dẫn đến file thực thi của Google Chrome."""
    system = platform.system()
    possible_paths: List[Optional[str]] = []

    if system == "Windows":
        program_files = os.environ.get("ProgramFiles", "C:\\Program Files")
        program_files_x86 = os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)")
        local_app_data = os.environ.get("LocalAppData", "")
        possible_paths = [
            os.path.join(program_files, "Google", "Chrome", "Application", "chrome.exe"),
            os.path.join(program_files_x86, "Google", "Chrome", "Application", "chrome.exe"),
            os.path.join(local_app_data, "Google", "Chrome", "Application", "chrome.exe") if local_app_data else None,
        ]
    elif system == "Darwin":  # macOS
        possible_paths = ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"]
    elif system == "Linux":
        possible_paths = [
            shutil.which("google-chrome"),
            shutil.which("google-chrome-stable"),
            shutil.which("chrome"),
            shutil.which("chromium-browser"),
            shutil.which("chromium"),
        ]
    else:
        logging.warning(f"Hệ điều hành '{system}' không được hỗ trợ tự động tìm Chrome.")
        return None

    for path in possible_paths:
        if path and os.path.exists(path) and os.path.isfile(path):
            logging.info(f"Tìm thấy Chrome tại: {path}")
            return path

    logging.warning("Không thể tự động tìm thấy Chrome.")
    return None

# ====== Cấu hình ======
@dataclass
class Config:
    """Lớp chứa các thông số cấu hình cho script."""
    PAGE_LOAD_TIMEOUT: int = 30  # Thời gian chờ tối đa tải trang
    ELEMENT_WAIT_TIMEOUT: int = 15  # Thời gian chờ phần tử xuất hiện
    CAPTCHA_DELAY: int = 10  # Chờ sau khi giải CAPTCHA
    CLICK_DELAY: float = 0.5  # Chờ ngắn sau khi nhấn
    CYCLE_DELAY: int = 210  # Nghỉ giữa các chu kỳ
    THREAD_START_DELAY: int = 10  # Chờ giữa các luồng
    PROFILE_BASE_PATH: str = os.path.expanduser("~/chrome_profiles")  # Thư mục hồ sơ
    BASE_DEBUG_PORT: int = 9223  # Cổng debug mặc định
    LOGIN_URL: str = "https://fmcpay.com/auth/login"  # URL đăng nhập
    TARGET_URLS: List[str] = field(default_factory=lambda: [
        "https://fmcpay.com/dashboard",
        "https://fmcpay.com/markets",
        "https://fmcpay.com/stakings",
        "https://fmcpay.com/exchange",
        "https://fmcpay.com/wallet/spot",
    ])  # Danh sách URL mục tiêu
    CHROME_EXECUTABLE_PATH: Optional[str] = None  # Đường dẫn Chrome, nhập từ người dùng

# ====== Tiện ích đọc file ======
def read_lines(filepath: str) -> List[str]:
    """Đọc các dòng không rỗng từ file."""
    try:
        with open(filepath, "r", encoding='utf-8') as f:
            return [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        logging.error(f"Lỗi nghiêm trọng: Không tìm thấy file '{filepath}'")
        raise
    except Exception as e:
        logging.error(f"Lỗi khi đọc file '{filepath}': {e}")
        raise

def load_accounts(filepath: str = "accounts.txt") -> List[Dict[str, str]]:
    """Tải tài khoản từ file theo định dạng email,mật_khẩu,mã_bí_mật."""
    accounts = []
    lines = read_lines(filepath)
    if not lines:
        logging.error(f"File '{filepath}' trống.")
        return []
    for idx, line in enumerate(lines):
        parts = line.split(",")
        if len(parts) == 3:
            accounts.append({"email": parts[0].strip(), "password": parts[1].strip(), "secret": parts[2].strip()})
        else:
            logging.warning(f"⚠️ Định dạng tài khoản không hợp lệ ở dòng {idx+1}: '{line}'")
    if accounts:
        logging.info(f"Đã tải {len(accounts)} tài khoản từ '{filepath}'.")
    else:
        logging.error("Không tải được tài khoản hợp lệ nào.")
    return accounts

# ====== Quản lý Chrome ======
def get_chrome_ports(count: int, base_port: int) -> List[str]:
    """Tạo danh sách cổng debug cho Chrome."""
    return [f"127.0.0.1:{base_port + i}" for i in range(max(0, count))]

def open_chrome_with_profile(port_number: int, profile_name: str, config: Config) -> bool:
    """Mở Chrome với hồ sơ riêng và cổng debug."""
    if not config.CHROME_EXECUTABLE_PATH or not os.path.exists(config.CHROME_EXECUTABLE_PATH):
        logging.error(f"Lỗi: Đường dẫn Chrome không hợp lệ: '{config.CHROME_EXECUTABLE_PATH}'")
        return False

    user_data_dir = Path(config.PROFILE_BASE_PATH) / profile_name
    try:
        user_data_dir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        logging.error(f"Không thể tạo thư mục hồ sơ {user_data_dir}: {e}")
        return False

    if any(user_data_dir.iterdir()):
        logging.info(f"✅ Sử dụng hồ sơ hiện có '{profile_name}' trên cổng {port_number}")
    else:
        logging.info(f"🆕 Tạo hồ sơ mới '{profile_name}' trên cổng {port_number}")

    chrome_cmd = [
        config.CHROME_EXECUTABLE_PATH,
        f"--remote-debugging-port={port_number}",
        f"--user-data-dir={user_data_dir}",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-extensions",
        "--disable-features=Translate",
    ]
    try:
        subprocess.Popen(chrome_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        logging.info(f"Đã gửi lệnh khởi chạy Chrome cho '{profile_name}' trên cổng {port_number}")
        return True
    except Exception as e:
        logging.error(f"Lỗi khi khởi chạy Chrome cho '{profile_name}': {e}")
        return False

# ====== Thiết lập WebDriver ======
def initialize_driver(debugger_address: str, user_agent: str, proxy: Optional[str] = None) -> Optional[webdriver.Chrome]:
    """Khởi tạo WebDriver kết nối tới Chrome."""
    options = Options()
    options.add_experimental_option("debuggerAddress", debugger_address)
    options.add_argument(f"--user-agent={user_agent}")
    if proxy:
        options.add_argument(f"--proxy-server={proxy}")
        logging.info(f"Sử dụng proxy: {proxy} cho cổng {debugger_address.split(':')[-1]}")
    try:
        driver = webdriver.Chrome(options=options)
        logging.info(f"✅ WebDriver kết nối thành công tới cổng {debugger_address.split(':')[-1]}")
        return driver
    except WebDriverException as e:
        logging.error(f"❌ Lỗi kết nối WebDriver tới {debugger_address}: {e}")
        return None

# ====== Tương tác web ======
def handle_captcha(driver: webdriver.Chrome, port_str: str, config: Config) -> bool:
    """Xử lý CAPTCHA Cloudflare bằng cách nhấn checkbox thủ công."""
    try:
        captcha_iframe = driver.find_element(By.XPATH, '//iframe[contains(@title, "Cloudflare security challenge")]')
        driver.switch_to.frame(captcha_iframe)
        checkbox = driver.find_element(By.XPATH, '//input[@type="checkbox"]')
        checkbox.click()
        logging.info(f"✅ Đã nhấn checkbox CAPTCHA trên cổng {port_str}")
        time.sleep(config.CAPTCHA_DELAY)
        driver.switch_to.default_content()
        return True
    except NoSuchElementException:
        logging.info(f"⚠️ Không tìm thấy CAPTCHA trên cổng {port_str}")
        driver.switch_to.default_content()
        return True
    except Exception as e:
        logging.warning(f"❌ Lỗi xử lý CAPTCHA trên cổng {port_str}: {e}")
        driver.switch_to.default_content()
        return False

def click_gift_image(driver: webdriver.Chrome, port_str: str, config: Config) -> bool:
    """Nhấn vào ảnh quà tặng nếu có."""
    try:
        img = driver.find_element(By.XPATH, '//img[@src="/assets/gift.svg"]')
        div = img.find_element(By.XPATH, './parent::div')
        div.click()
        logging.info(f"🎉 Đã nhấn quà tặng trên cổng {port_str}")
        time.sleep(config.CLICK_DELAY)
        return True
    except NoSuchElementException:
        logging.info(f"⏩ Không tìm thấy quà tặng trên cổng {port_str}")
        return True
    except Exception as e:
        logging.error(f"❌ Lỗi khi nhấn quà tặng trên cổng {port_str}: {e}")
        return False

def perform_login(driver: webdriver.Chrome, account: Dict[str, str], port_str: str, config: Config) -> bool:
    """Thực hiện đăng nhập với 2FA."""
    try:
        logging.info(f"Bắt đầu đăng nhập cho {account['email']} trên cổng {port_str}")
        driver.get(config.LOGIN_URL)
        time.sleep(config.PAGE_LOAD_TIMEOUT)

        driver.find_element(By.ID, "username").send_keys(account["email"])
        driver.find_element(By.ID, "password").send_keys(account["password"])
        driver.find_element(By.XPATH, '//*[@id="__next"]/div/div[1]/div/div[2]/div[2]/div/div/div/form/button').click()
        time.sleep(config.PAGE_LOAD_TIMEOUT)

        code = pyotp.TOTP(account["secret"]).now()
        inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='tel']")
        for i, digit in enumerate(code):
            inputs[i].send_keys(digit)
            time.sleep(random.uniform(0.1, 0.4))

        verify_button = driver.find_element(By.XPATH, '//*[@id="__next"]/div/div[1]/div/div/div[2]/div/form/div[2]/button')
        verify_button.click()
        logging.info(f"🔐 Đăng nhập thành công cho {account['email']} trên cổng {port_str}")
        time.sleep(config.PAGE_LOAD_TIMEOUT)
        return True
    except Exception as e:
        logging.error(f"❌ Lỗi đăng nhập {account['email']} trên cổng {port_str}: {e}")
        return False

def process_url(driver: webdriver.Chrome, url: str, port_str: str, config: Config) -> bool:
    """Xử lý một URL: truy cập, CAPTCHA, quà tặng."""
    try:
        logging.info(f"🌐 Truy cập {url} trên cổng {port_str}")
        driver.get(url)
        time.sleep(config.PAGE_LOAD_TIMEOUT)
        handle_captcha(driver, port_str, config)
        click_gift_image(driver, port_str, config)
        logging.info(f"✅ Hoàn tất xử lý {url} trên cổng {port_str}")
        return True
    except Exception as e:
        logging.error(f"❌ Lỗi khi xử lý {url} trên cổng {port_str}: {e}")
        return False

# ====== Xử lý instance Chrome ======
def process_chrome_instance(
    debugger_address: str,
    user_agent: str,
    proxy: Optional[str],
    account: Dict[str, str],
    initial_delay: int,
    config: Config,
    instance_id: int,
) -> None:
    """Quản lý một instance Chrome: đăng nhập, duyệt URL."""
    threading.current_thread().name = f"Instance-{instance_id}({account['email'][:6]}..)"
    port_str = debugger_address.split(":")[-1]
    logging.info(f"⏳ Chờ {initial_delay} giây trước khi kết nối WebDriver...")
    time.sleep(initial_delay)

    driver = None
    try:
        driver = initialize_driver(debugger_address, user_agent, proxy)
        if not driver:
            logging.error(f"Không thể khởi tạo WebDriver cho cổng {port_str}")
            return

        if perform_login(driver, account, port_str, config):
            cycle_count = 0
            while True:
                cycle_count += 1
                logging.info(f"🔄 Bắt đầu chu kỳ {cycle_count} trên cổng {port_str}")
                for url in config.TARGET_URLS:
                    process_url(driver, url, port_str, config)
                logging.info(f"⏸️ Tạm nghỉ {config.CYCLE_DELAY} giây...")
                time.sleep(config.CYCLE_DELAY)
        else:
            logging.error(f"Đăng nhập thất bại cho {account['email']}. Luồng kết thúc.")
    except Exception as e:
        logging.error(f"❌ Lỗi luồng trên cổng {port_str}: {e}")
    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass
        logging.info(f"🏁 Luồng cổng {port_str} kết thúc.")

# ====== Thực thi chính ======
def main():
    """Hàm chính điều phối script."""
    # Prompt for Chrome executable path
    detected_chrome = find_chrome_executable()
    default_chrome = detected_chrome or "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    print(f"🔍 Đường dẫn Chrome tự động: {detected_chrome or 'Không tìm thấy'}")
    chrome_path = input(f"📁 Nhập đường dẫn Chrome (Enter để dùng {default_chrome}): ").strip()
    chrome_path = chrome_path or default_chrome
    if not os.path.exists(chrome_path):
        logging.error(f"Lỗi: Đường dẫn Chrome không hợp lệ: {chrome_path}")
        return

    config = Config(CHROME_EXECUTABLE_PATH=chrome_path)
    try:
        # Prompt for number of instances
        num_instances = 0
        while True:
            try:
                num_instances = int(input("🔢 Nhập số lượng instance Chrome: "))
                if num_instances > 0:
                    break
                logging.error("Lỗi: Số instance phải là số dương.")
            except ValueError:
                logging.error("Lỗi: Vui lòng nhập số nguyên hợp lệ.")

        # Prompt for starting debug port
        while True:
            try:
                port_input = input(f"🔢 Nhập cổng debug bắt đầu (Enter để dùng {config.BASE_DEBUG_PORT}): ").strip()
                if not port_input:
                    logging.info(f"Sử dụng cổng mặc định: {config.BASE_DEBUG_PORT}")
                    break
                base_port = int(port_input)
                if 1024 <= base_port <= 65535:
                    config.BASE_DEBUG_PORT = base_port
                    logging.info(f"Sử dụng cổng bắt đầu: {base_port}")
                    break
                logging.error("Lỗi: Cổng phải trong khoảng 1024-65535.")
            except ValueError:
                logging.error("Lỗi: Vui lòng nhập số nguyên hợp lệ cho cổng.")

        user_agents = read_lines("user_agents.txt")
        proxies = read_lines("proxies.txt") or []
        accounts = load_accounts()
        if not user_agents or not accounts:
            logging.error("Thiếu user agents hoặc tài khoản hợp lệ.")
            return

        ports_list = get_chrome_ports(num_instances, config.BASE_DEBUG_PORT)
        debug_ports = [int(p.split(":")[-1]) for p in ports_list]
        logging.info(f"Cổng debug: {debug_ports}")

        successful_launches = 0
        for i in range(num_instances):
            profile_name = f"profile_{i}"
            port_num = debug_ports[i]
            logging.info(f"--- Khởi chạy instance {i} (Profile: {profile_name}, Cổng: {port_num}) ---")
            if open_chrome_with_profile(port_num, profile_name, config):
                successful_launches += 1
                time.sleep(random.uniform(2.0, 4.0))

        if successful_launches == 0:
            logging.critical("Không khởi chạy được instance Chrome nào.")
            return

        time.sleep(5.0 + successful_launches * 1.5)
        threads = []
        for i in range(successful_launches):
            thread = threading.Thread(
                target=process_chrome_instance,
                args=(
                    ports_list[i],
                    user_agents[i % len(user_agents)],
                    proxies[i % len(proxies)] if proxies else None,
                    accounts[i % len(accounts)],
                    i * config.THREAD_START_DELAY,
                    config,
                    i,
                ),
                daemon=True
            )
            threads.append(thread)
            thread.start()
            time.sleep(0.1)

        logging.info(f"🚀 Đã khởi động {successful_launches} luồng. Nhấn Ctrl+C để dừng.")
        while any(t.is_alive() for t in threads):
            time.sleep(5)

    except KeyboardInterrupt:
        logging.info("🛑 Nhận tín hiệu dừng (Ctrl+C).")
    except Exception as e:
        logging.critical(f"❌ Lỗi chính: {e}")
    finally:
        logging.info("--- Chương trình kết thúc ---")

if __name__ == "__main__":
    main()