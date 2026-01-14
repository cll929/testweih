import os
import time
from datetime import datetime
from playwright.sync_api import sync_playwright, TimeoutError

# ========== 配置区 ==========
SERVER_URLS = [
    "https://hub.weirdhost.xyz/server/xxxxxxxx"
]

REMEMBER_COOKIE = os.getenv("REMEMBER_WEB_COOKIE")
SCREENSHOT_DIR = "screenshots"
HEADLESS = True
# ===========================


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def ensure_dir():
    if not os.path.exists(SCREENSHOT_DIR):
        os.makedirs(SCREENSHOT_DIR)


def screenshot(page, name):
    path = f"{SCREENSHOT_DIR}/{name}"
    page.screenshot(path=path, full_page=True)
    print(f"📸 截图保存: {path}")


def wait_cf(page):
    print("⏳ 等待 Cloudflare...")
    for _ in range(30):
        if "Checking your browser" not in page.content():
            return
        time.sleep(1)


def inject_cookie(context):
    if not REMEMBER_COOKIE:
        raise RuntimeError("❌ 未设置 REMEMBER_WEB_COOKIE")

    context.add_cookies([{
        "name": "remember_web",
        "value": REMEMBER_COOKIE,
        "domain": "hub.weirdhost.xyz",
        "path": "/",
        "httpOnly": True,
        "secure": True
    }])


def get_expire_text(page):
    try:
        el = page.locator("text=/\\d{4}-\\d{2}-\\d{2}/").first
        return el.text_content()
    except:
        return None


def renew_server(page, url, idx):
    print(f"\n🚀 处理服务器 {idx + 1}")
    page.goto(url, wait_until="domcontentloaded", timeout=60000)
    wait_cf(page)
    screenshot(page, f"server_{idx}_loaded.png")

    before = get_expire_text(page)
    print(f"📅 续期前到期时间: {before}")

    # 多 selector 兜底
    renew_selectors = [
        'button:has-text("시간추가")',
        'button:has-text("연장")',
        'text=시간추가'
    ]

    btn = None
    for sel in renew_selectors:
        try:
            btn = page.locator(sel).first
            if btn.is_visible():
                break
        except:
            pass

    if not btn or not btn.is_visible():
        screenshot(page, f"server_{idx}_no_button.png")
        print("❌ 未找到续期按钮")
        return "no_button"

    print("🖱️ 点击续期按钮")
    btn.click()
    page.wait_for_timeout(3000)

    # 判断弹窗成功提示
    success = False
    popup_texts = ["성공", "완료", "추가되었습니다"]

    for _ in range(10):
        content = page.content()
        if any(t in content for t in popup_texts):
            success = True
            break
        time.sleep(1)

    screenshot(page, f"server_{idx}_after_click.png")

    page.reload(wait_until="domcontentloaded")
    wait_cf(page)

    after = get_expire_text(page)
    print(f"📅 续期后到期时间: {after}")

    if success or (before and after and before != after):
        print("🎉 续期成功")
        return "success"

    print("⚠️ 点击完成，但未确认成功")
    return "uncertain"


def main():
    ensure_dir()
    print(f"🕒 开始执行 WeirdHost Cookie-only 自动续期 | {now()}")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=HEADLESS,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage"
            ]
        )
        context = browser.new_context()
        inject_cookie(context)

        page = context.new_page()

        # ⚠️ 只访问首页，不碰 /login
        page.goto("https://hub.weirdhost.xyz", wait_until="domcontentloaded", timeout=60000)
        wait_cf(page)
        screenshot(page, "homepage.png")

        results = {}
        for i, url in enumerate(SERVER_URLS):
            results[url] = renew_server(page, url, i)

        browser.close()

    print("\n📊 执行结果汇总:")
    for k, v in results.items():
        print(f" - {k}: {v}")

    print("\n🎉 脚本执行完毕")


if __name__ == "__main__":
    main()
