# Sử dụng image Python có Chrome
FROM python:3.10

# Cài đặt Chrome & ChromeDriver
RUN apt-get update && apt-get install -y wget unzip \
    && wget -qO- https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb > /tmp/chrome.deb \
    && apt-get install -y /tmp/chrome.deb \
    && rm /tmp/chrome.deb \
    && wget -qO /tmp/chromedriver.zip https://chromedriver.storage.googleapis.com/$(curl -sS chromedriver.storage.googleapis.com/LATEST_RELEASE)/chromedriver_linux64.zip \
    && unzip /tmp/chromedriver.zip -d /usr/local/bin/ \
    && rm /tmp/chromedriver.zip

# Cài đặt thư viện Python cần thiết
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# Mở Chrome ở chế độ Debug
CMD ["google-chrome-stable", "--remote-debugging-port=9222", "--disable-gpu", "--no-sandbox", "--headless"]
