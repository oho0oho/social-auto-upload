# -*- coding: utf-8 -*-
import pathlib
from datetime import datetime, timedelta

from playwright.async_api import Playwright, async_playwright
import os
import asyncio



async def cookie_auth(account_file):
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        context = await browser.new_context(storage_state=account_file)
        # 创建一个新的页面
        page = await context.new_page()
        # 访问指定的 URL
        await page.goto("https://cp.kuaishou.com/article/publish/video?origin=www.kuaishou.com")
        try:
            await page.wait_for_selector("div.boards-more h3:text('立即登录')", timeout=200)  # 等待5秒
            print("[+] 等待5秒 cookie 失效")
            return False
        except:
            print("[+] cookie 有效")
            return True


async def kuaishou_setup(account_file, handle=False):
    if not os.path.exists(account_file) or not await cookie_auth(account_file):
        if not handle:
            # Todo alert message
            return False
        print('[+] cookie文件不存在或已失效，即将自动打开浏览器，请扫码登录，登陆后会自动生成cookie文件')
        await kuaishou_cookie_gen(account_file)
    return True


async def kuaishou_cookie_gen(account_file):
    async with async_playwright() as playwright:
        options = {
            'headless': False
        }
        # Make sure to run headed.
        browser = await playwright.chromium.launch(**options)
        # Setup context however you like.
        context = await browser.new_context()  # Pass any options
        # Pause the page, and start recording manually.
        page = await context.new_page()
        await page.goto("https://cp.kuaishou.com/article/publish/video?origin=www.kuaishou.com")
        await page.pause()
        # 点击调试器的继续，保存cookie
        await context.storage_state(path=account_file)


class KuaiShouVideo(object):
    def __init__(self, title, video_file,pic_file, tags, publish_date: datetime, account_file):
        self.title = title  # 视频标题
        self.video_file = video_file
        self.pic_file = pic_file
        self.tags = tags
        self.publish_date = publish_date
        self.account_file = account_file
        self.date_format = '%Y年%m月%d日 %H:%M'
        self.local_executable_path = ""  # change me

    async def set_schedule_time_kuaishou(self, page, publish_date):
        await page.get_by_label("定时发布").check()
        await asyncio.sleep(1)
        publish_date_hour = publish_date.strftime("%Y-%m-%d %H:%M:%S")
        await page.locator('input[readonly][placeholder="选择日期时间"]').click()
        await page.keyboard.press("Control+KeyA")
        await page.keyboard.type(str(publish_date_hour))
        await page.keyboard.press("Enter")

    async def set_video_cover(self, page):
        await page.click('button:has-text("编辑封面")')
        await page.wait_for_selector('div:has-text("上传封面")')
        await page.click('div:has-text("上传封面")')
        await page.wait_for_selector('input[type="file"]')
        await page.locator('input[type="file"]').set_input_files(self.pic_file)
        await page.click('button:has-text("确认")')


    async def handle_upload_error(self, page):
        print("视频出错了，重新上传中")
        await page.locator('div.progress-div [class^="upload-btn-input"]').set_input_files(self.video_file)

    async def upload(self, playwright: Playwright) -> None:
        # 使用 Chromium 浏览器启动一个浏览器实例
        if self.local_executable_path:
            browser = await playwright.chromium.launch(headless=False, executable_path=self.local_executable_path)
        else:
            browser = await playwright.chromium.launch(headless=False)
        # 创建一个浏览器上下文，使用指定的 cookie 文件
        context = await browser.new_context(storage_state=f"{self.account_file}")

        # 创建一个新的页面
        page = await context.new_page()
        # 访问指定的 URL
        await page.goto("https://cp.kuaishou.com/article/publish/video")
        print('[+]正在上传-------{} '.format(self.video_file))
        # 等待页面跳转到指定的 URL，没进入，则自动等待到超时
        print('[-] 正在打开主页...')
        await page.wait_for_url("https://cp.kuaishou.com/article/publish/video")
        # 等待 input[type="file"] 元素出现
        await page.wait_for_selector('input[type="file"]', state="attached", timeout=5000)  # 等待5秒
        inputfile_element1 = await page.query_selector('input[type=file]')
        if inputfile_element1 is not None:
            await inputfile_element1.set_input_files(self.video_file)
        else:
            print("未找到匹配的 input 元素")
        

        # 等待上传成功
        while True:
            try:
                await page.wait_for_selector("div:has-text('上传成功')", timeout=5000)
                break
            except:
                print("  [-] 正在等待上传成功...")
                await asyncio.sleep(0.1)

        # 上传封面
        await self.set_video_cover(page)

        # 填写描述，@好友，#话题
        # 检查是否存在包含输入框的元素
        # 这里为了避免页面变化，故使用相对位置定位：作品标题父级右侧第一个元素的input子元素
        await asyncio.sleep(1)
        print("  [-] 正在填写描述，@好友，#话题...")
        title_container = await page.query_selector('div[placeholder="添加合适的话题和描述，作品能获得更多推荐～"]')
        await title_container.fill(self.title[:30])
       
        # 选择配置项
        await page.get_by_label("不关联").check()
        await page.get_by_label("允许别人跟我拍同框 （时长15分钟以内的作品支持拍同框）").uncheck()
        await page.get_by_label("不允许下载此作品").check()
        await page.get_by_label("作品在同城不显示").uncheck()
        await page.get_by_label("不展示").check()
        await page.get_by_label("公开 （所有人可见）").check()


        # 选择"健康"和"保健养生"标签
        input_element = await page.query_selector('input.ant-select-selection-search-input')
        if (input_element is None):
            print("未找到匹配的 input 元素")
        await asyncio.sleep(1)
        await input_element.click() 

        # 获取滚动条元素的位置
        scrollbar = await page.query_selector('div.rc-virtual-list-scrollbar-thumb')
        scrollbar_bounding_box = await scrollbar.bounding_box()
        
        # 移动鼠标到滚动条元素的位置
        await page.mouse.move(scrollbar_bounding_box['x']-2, scrollbar_bounding_box['y']-2)
        print("scrollbar_bounding_box = ",scrollbar_bounding_box)
        # 持续滚动直至无法继续滚动
        while True:
            try:
                print("[")
                await page.wait_for_selector('div.ant-select-item-option[title="健康"]', timeout=100)
                print("-")
                break
            except Exception:
                print(".")
                await page.mouse.wheel(0, 500)
                # 等待一段时间，让页面有时间加载新的选项
                await asyncio.sleep(0.05)
        
        # 然后点击该元素
        await page.click('div.ant-select-item-option[title="健康"]')
        

        
        # 获取所有匹配的元素
        input_elements = await page.query_selector_all('input.ant-select-selection-search-input')

        # 检查是否找到了足够的元素
        if len(input_elements) < 2:
            print("未找到足够的匹配元素")
        else:
            # 定位到第二个 input 元素
            input_element_2 = input_elements[1]
            await asyncio.sleep(1)
            await input_element_2.click()
        
        scrollbars = await page.query_selector_all('div.rc-virtual-list-scrollbar-thumb')
        if len(scrollbars) < 2:
            print("未找到足够的匹配元素")
        else:
            # 定位到第二个滚动条元素的位置
            print("count = ",len(scrollbars))
            scrollbar2 = scrollbars[1]
            print("scrollbar2 = ",scrollbar2)
            scrollbar_bounding_box2 = await scrollbar2.bounding_box()
            if scrollbar_bounding_box2 is None:
                print("滚动条元素不可见或不存在")
            else:
                await page.mouse.move(scrollbar_bounding_box2['x'], scrollbar_bounding_box2['y'])
        
        # 持续滚动直至无法继续滚动
        while True:
            try:
                print("[")
                await page.wait_for_selector('div.ant-select-item-option[title="保健养生"]', timeout=500)
                print("-")
                break
            except Exception:
                print(".")
                await page.mouse.wheel(0, 150)
                # 等待一段时间，让页面有时间加载新的选项
                await asyncio.sleep(0.05)
        
        # 然后点击该元素
        await page.click('div.ant-select-item-option[title="保健养生"]')
      
        

        
        if self.publish_date != 0:
            await self.set_schedule_time_kuaishou(page, self.publish_date)

        

        # 判断视频是否发布成功
        while True:
            # 判断视频是否发布成功
            try:
                publish_button = page.get_by_role('button', name="发布", exact=True)
                
                if await publish_button.count():
                    await publish_button.click()
                    await page.wait_for_selector('button:has-text("确认发布")')
                    await page.click('button:has-text("确认发布")')
                    
                await page.wait_for_url("https://cp.kuaishou.com/article/manage/video?status=2&from=publish",
                                        timeout=5000)  # 如果自动跳转到作品页面，则代表发布成功
                print("  [-]视频发布成功")
                break
            except Exception as e:
                print("  [-] 视频正在发布中...")
                print(f"  [-] 异常信息：{e}")
                await page.screenshot(full_page=True)
                await asyncio.sleep(0.5)

        await context.storage_state(path=self.account_file)  # 保存cookie
        print('  [-]cookie更新完毕！')
        await asyncio.sleep(2)  # 这里延迟是为了方便眼睛直观的观看
        # 关闭浏览器上下文和浏览器实例
        await context.close()
        await browser.close()


    async def main(self):
        async with async_playwright() as playwright:
            await kuaishou_setup(self.account_file, handle=True)
            await self.upload(playwright)


if __name__ == '__main__':
    account_file = "kuaishou_cookie.json"
    video = KuaiShouVideo("test", "demo.mp4","demo.jpeg", ["test"], datetime.now() + timedelta(hours=4), account_file)
    asyncio.run(video.main())