import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException

# Kết nối với Chrome đang chạy ở chế độ debug
chrome_options = webdriver.ChromeOptions()
chrome_options.debugger_address = "127.0.0.1:9222"  # Cổng debug của Chrome

# Khởi tạo trình duyệt Selenium kết nối với Chrome đang mở
driver = webdriver.Chrome(options=chrome_options)

# Danh sách trang web cần xử lý
urls = [
    "https://fmcpay.com/p2p",
    "https://fmcpay.com/dashboard",
    "https://fmcpay.com/markets",
    "https://fmcpay.com/stakings",
    "https://fmcpay.com/exchange",
    "https://fmcpay.com/wallet/spot"
]

# Lặp lại chương trình mỗi 7 phút
while True:
    print("\n⏳ Bắt đầu chu trình mới...")

    for url in urls:
        try:
            print(f"\n🚀 Đang mở trang: {url}")
            driver.get(url)
            time.sleep(5)  # Chờ trang tải xong

            # Bước 1: Xử lý Cloudflare CAPTCHA nếu có
            try:
                captcha_iframe = driver.find_element(By.XPATH,
                                                     '//iframe[contains(@title, "Cloudflare security challenge")]')
                driver.switch_to.frame(captcha_iframe)  # Chuyển vào iframe CAPTCHA

                checkbox_element = driver.find_element(By.XPATH, '//input[@type="checkbox"]')
                checkbox_element.click()
                print("✅ Click vào checkbox Cloudflare thành công!")

                time.sleep(10)  # Chờ xác minh hoàn tất
                driver.switch_to.default_content()  # Quay lại trang chính

            except NoSuchElementException:
                print("⚠️ Không tìm thấy Cloudflare CAPTCHA, tiếp tục...")

            # Bước 2: Kiểm tra và đóng modal box nếu xuất hiện
            try:
                close_modal_button = driver.find_element(By.XPATH, '//div[contains(@class, "cursor-pointer absolute top-4 right-4 z-10")]')
                close_modal_button.click()
                print("❌ Đã đóng modal box!")
                time.sleep(2)  # Chờ modal đóng
            except NoSuchElementException:
                print("⚠️ Không tìm thấy modal box, tiếp tục...")

            # Bước 3: Tìm thẻ `<img>` có src="/assets/gift.svg`
            try:
                img_element = driver.find_element(By.XPATH, '//img[@src="/assets/gift.svg"]')
                div_element = img_element.find_element(By.XPATH, './parent::div')  # Lấy thẻ cha <div>
                div_element.click()
                print("🎉 Click vào ảnh thành công!")

            except NoSuchElementException:
                print("⏩ Không tìm thấy ảnh, bỏ qua trang này.")
                continue  # Bỏ qua vòng lặp hiện tại và chuyển sang trang tiếp theo

            time.sleep(3)  # Chờ hiệu ứng click

        except Exception as e:
            print(f"❌ Lỗi khi xử lý trang {url}: {str(e)}")

    print("\n🔄 Đợi 7 phút trước khi chạy lại...")
    time.sleep(320)  # Đợi 7 phút (420 giây) trước khi chạy lại
