import os
import time
import signal
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from datetime import datetime

# --- 配置项 ---
# 目标服务器页面
SERVER_URL = "https://panel.godlike.host/server/61b8ad3c"
# 登录页面
LOGIN_URL = "https://panel.godlike.host/auth/login"
# Cookie 名称
COOKIE_NAME = "remember_web_59ba36addc2b2f9401580f014c7f58ea4e30989d"
# 单次任务执行的超时时间（秒）
# 如果点击、等待广告等一系列操作超过这个时间，将强制中断本次任务并重试
TASK_TIMEOUT_SECONDS = 300  # 300秒 = 5分钟

# --- 超时处理机制 ---
class TaskTimeoutError(Exception):
    """自定义任务超时异常"""
    pass

def timeout_handler(signum, frame):
    """超时信号处理函数"""
    raise TaskTimeoutError("任务执行时间超过设定的阈值")

# 注册信号处理器 (仅在非Windows环境生效，这对于在Linux上运行的GitHub Actions是完美的)
if os.name != 'nt':
    signal.signal(signal.SIGALRM, timeout_handler)
# --------------------


def login_with_playwright(page):
    """
    处理登录逻辑，优先使用Cookie，失败则使用邮箱密码。
    返回 True 表示登录成功，False 表示失败。
    """
    # ... (此函数内容与之前版本完全相同，为保持完整性而保留)
    remember_web_cookie = os.environ.get('PTERODACTYL_COOKIE')
    pterodactyl_email = os.environ.get('PTERODACTYL_EMAIL')
    pterodactyl_password = os.environ.get('PTERODACTYL_PASSWORD')

    if remember_web_cookie:
        print("检测到 PTERODACTYL_COOKIE，尝试使用 Cookie 登录...")
        session_cookie = {
            'name': COOKIE_NAME, 'value': remember_web_cookie, 'domain': '.panel.godlike.host',
            'path': '/', 'expires': int(time.time()) + 3600 * 24 * 365, 'httpOnly': True,
            'secure': True, 'sameSite': 'Lax'
        }
        page.context.add_cookies([session_cookie])
        print(f"已设置 Cookie。正在访问目标服务器页面: {SERVER_URL}")
        page.goto(SERVER_URL, wait_until="domcontentloaded")
        
        if "auth/login" in page.url:
            print("Cookie 登录失败或会话已过期，将回退到邮箱密码登录。")
            page.context.clear_cookies()
        else:
            print("Cookie 登录成功！")
            return True

    if not (pterodactyl_email and pterodactyl_password):
        print("错误: Cookie 无效或未提供，且未提供 PTERODACTYL_EMAIL 和 PTERODACTYL_PASSWORD。无法登录。")
        return False

    print("正在尝试使用邮箱和密码登录...")
    page.goto(LOGIN_URL, wait_until="domcontentloaded")
    try:
        print("正在点击 'Through login/password'...")
        page.locator('a:has-text("Through login/password")').click()
        
        email_selector = 'input[name="username"]'
        password_selector = 'input[name="password"]'
        login_button_selector = 'button[type="submit"]:has-text("Login")'
        
        print("等待登录表单元素加载...")
        page.wait_for_selector(email_selector)
        page.wait_for_selector(password_selector)
        print("正在填写邮箱和密码...")
        page.fill(email_selector, pterodactyl_email)
        page.fill(password_selector, pterodactyl_password)
        print("正在点击登录按钮...")
        with page.expect_navigation(wait_until="domcontentloaded"):
            page.click(login_button_selector)
        
        if "auth/login" in page.url:
            print("邮箱密码登录失败，请检查凭据是否正确。")
            page.screenshot(path="login_fail_error.png")
            return False
        
        print("邮箱密码登录成功！")
        return True
    except Exception as e:
        print(f"邮箱密码登录过程中发生错误: {e}")
        page.screenshot(path="login_process_error.png")
        return False

def add_time_task(page):
    """
    执行一次增加90分钟时长的任务。
    此函数现在仅包含核心操作，超时逻辑移至主循环。
    """
    try:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 开始执行增加时长任务...")
        
        if page.url != SERVER_URL:
            print(f"当前不在目标页面，正在导航至: {SERVER_URL}")
            page.goto(SERVER_URL, wait_until="domcontentloaded")

        add_button_selector = 'button:has-text("Add 90 minutes")'
        print("步骤1: 查找并点击 'Add 90 minutes' 按钮...")
        page.locator(add_button_selector).wait_for(state='visible', timeout=30000)
        page.locator(add_button_selector).click()
        print("...已点击 'Add 90 minutes'。")

        watch_ad_selector = 'button:has-text("Watch advertisment")'
        print("步骤2: 查找并点击 'Watch advertisment' 按钮...")
        page.locator(watch_ad_selector).wait_for(state='visible', timeout=30000)
        page.locator(watch_ad_selector).click()
        print("...已点击 'Watch advertisment'，等待广告完成...")

        success_selector = 'p:has-text("Successfully added 90 minutes to server timer")'
        print("步骤3: 等待成功提示...")
        page.locator(success_selector).wait_for(state='visible', timeout=120000)
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ✅ 成功增加90分钟！")
        
        return True

    except PlaywrightTimeoutError as e:
        print(f"❌ 任务执行超时: 未在规定时间内找到元素。请检查选择器或页面是否已更改。")
        page.screenshot(path="task_element_timeout_error.png")
        return False
    except Exception as e:
        print(f"❌ 任务执行过程中发生未知错误: {e}")
        page.screenshot(path="task_general_error.png")
        return False


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_default_timeout(60000)

        try:
            if not login_with_playwright(page):
                print("登录失败，程序终止。")
                browser.close()
                return

            # 进入主循环
            while True:
                # --- 新增的超时监控逻辑 ---
                if os.name != 'nt':
                    signal.alarm(TASK_TIMEOUT_SECONDS) # 设置闹钟
                
                try:
                    print("\n----------------------------------------------------")
                    success = add_time_task(page)
                    if success:
                        print("本轮任务成功完成。")
                    else:
                        print("本轮任务失败，将按计划等待后重试。")
                    
                    if os.name != 'nt':
                        signal.alarm(0)  # 如果任务提前完成，取消闹钟

                except TaskTimeoutError as e:
                    print(f"🔥🔥🔥 任务强制超时（{TASK_TIMEOUT_SECONDS}秒）！脚本可能卡住了。🔥🔥🔥")
                    print(f"错误信息: {e}")
                    page.screenshot(path="task_force_timeout_error.png")
                    print("已截图，将按计划等待后重试。")
                except Exception as e:
                    print(f"主循环发生未知严重错误: {e}")
                    page.screenshot(path="main_loop_critical_error.png")
                # --- 超时逻辑结束 ---
                
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 等待6分钟后开始下一轮任务...")
                print("----------------------------------------------------")
                time.sleep(360)
        
        except Exception as e:
            print(f"主程序发生严重错误: {e}")
            page.screenshot(path="main_critical_error.png")
        finally:
            print("关闭浏览器，程序结束。")
            browser.close()


if __name__ == "__main__":
    print("启动自动化任务（带任务超时监控）...")
    main()
    exit(0)
