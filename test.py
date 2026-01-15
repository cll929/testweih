import os
import sys
import time
from datetime import datetime
from playwright.sync_api import sync_playwright, TimeoutError

# ================== 配置区 ==================
SERVER_URL = "https://hub.weirdhost.xyz/server/e66c2244"
COOKIE_ENV = "REMEMBER_WEB_COOKIE"
SCREENSHOT_DIR = "screenshots"
HEADLESS = True   # GitHub Actions / VPS 必须 True
# ===========================================


def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)


def log(msg):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{now}] {msg}", flush=True)


def main():
    log("🚀 WeirdHost 自动续期启动（Cookie-only 终极版）")

    cookie_raw = os.getenv(COOKIE_ENV)
    if not cookie_raw:
        log("❌ 未检测到 REMEMBER_WEB_COOKIE")
        sys.exit(1)

    ensure_dir(SCREENSHOT_DIR)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=HEADLESS)
        context = browser.new_context()

        # ===== 设置 Cookie（不访问 /login）=====
        context.add_cookies([
            {
                "name": "REMEMBER_WEB",
                "value": cookie_raw,
                "domain": "hub.weirdhost.xyz",
                "path": "/",
                "httpOnly": True,
                "secure": True,
                "sameSite": "Lax",
            }
        ])

        page = context.new_page()

        # Cookie 设置截图
        page.goto("https://hub.weirdhost.xyz", wait_until="domcontentloaded")
        page.screenshot(path=f"{SCREENSHOT_DIR}/01_cookie_set.png")
        log("🍪 Cookie 已注入")

        # ===== 直进服务器页面 =====
        log(f"🌐 访问服务器页面: {SERVER_URL}")
        page.goto(SERVER_URL, wait_until="networkidle", timeout=60000)
        page.screenshot(path=f"{SCREENSHOT_DIR}/02_server_page_loaded.png")

        # ===== 等待「时间追加」按钮 =====
        log("🔍 等待「시간추가 / 时间追加」按钮出现")

        renew_btn = None
        try:
            renew_btn = page.wait_for_selector(
                "button:has-text('시간추가'), button:has-text('시간 추가')",
                timeout=30000
            )
        except TimeoutError:
            log("❌ 未找到 时间追加 按钮")
            page.screenshot(path=f"{SCREENSHOT_DIR}/ERROR_no_renew_button.png")
            browser.close()
            sys.exit(1)

        page.screenshot(path=f"{SCREENSHOT_DIR}/03_renew_button_found.png")
        log("✅ 已找到 时间追加 按钮")

        # ===== 点击续期 =====
        renew_btn.click()
        log("🖱 已点击 时间追加")

        time.sleep(3)
        page.screenshot(path=f"{SCREENSHOT_DIR}/04_after_click.png")

        # ===== 最终留证 =====
        time.sleep(5)
        page.screenshot(path=f"{SCREENSHOT_DIR}/05_done.png")

        log("🎉 自动续期流程执行完毕")
        browser.close()


if __name__ == "__main__":
    main()
