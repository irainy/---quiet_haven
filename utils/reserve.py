from utils import AES_Encrypt, enc, generate_captcha_key, verify_param
import json
import requests
import re
import time
import logging
import datetime
from urllib3.exceptions import InsecureRequestWarning


def get_date(day_offset: int = 0):
    today = datetime.datetime.now().date()
    offset_day = today + datetime.timedelta(days=day_offset)
    tomorrow = offset_day.strftime("%Y-%m-%d")
    return tomorrow


class reserve:
    def __init__(
        self,
        sleep_time=0.2,
        max_attempt=50,
        enable_slider=False,
        reserve_next_day=False,
    ):
        self.login_page = (
            "https://passport2.chaoxing.com/mlogin?loginType=1&newversion=true&fid="
        )
        self.url = (
            "https://office.chaoxing.com/front/third/apps/seat/code?id={}&seatNum={}"
        )
        self.submit_url = "https://office.chaoxing.com/data/apps/seat/submit"
        self.seat_url = "https://office.chaoxing.com/data/apps/seat/getusedtimes"
        self.login_url = "https://passport2.chaoxing.com/fanyalogin"
        self.token = ""
        self.success_times = 0
        self.fail_dict = []
        self.submit_msg = []
        self.requests = requests.session()
        self.token_pattern = re.compile("token = '(.*?)'")
        self.headers = {
            "Referer": "https://office.chaoxing.com/",
            "Host": "captcha.chaoxing.com",
            "Pragma": "no-cache",
            "Sec-Ch-Ua": '"Google Chrome";v="125", "Chromium";v="125", "Not.A/Brand";v="24"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Linux"',
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
        }
        self.login_headers = {
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "accept-encoding": "gzip, deflate, br, zstd",
            "cache-control": "no-cache",
            "Connection": "keep-alive",
            "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 10_3_1 like Mac OS X) AppleWebKit/603.1.3 (KHTML, like Gecko) Version/10.0 Mobile/14E304 Safari/602.1 wechatdevtools/1.05.2109131 MicroMessenger/8.0.5 Language/zh_CN webview/16364215743155638",
            "X-Requested-With": "XMLHttpRequest",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Host": "passport2.chaoxing.com",
        }

        self.sleep_time = sleep_time
        self.max_attempt = max_attempt
        self.enable_slider = enable_slider
        self.reserve_next_day = reserve_next_day
        requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

    def _get_page_token(self, url, require_value=False):
        response = self.requests.get(url=url, verify=False)
        html = response.content.decode("utf-8")
        matches = re.findall(r'id="submit_enc"\s+value="(.*?)"', html)
        value_matches = None
        if require_value:
            value_matches = re.findall(r'value="(.*?)"', html)
            if not matches:
                logging.error(f"Failed to get token from {url}")
                return "", ""
            if not value_matches:
                logging.error(f"Failed to get submit value from {url}")
                return matches[0], ""
        return matches[0] if matches else "", value_matches[0] if value_matches else ""

    def get_login_status(self):
        self.requests.headers = self.login_headers
        self.requests.get(url=self.login_page, verify=False)

    def login(self, username, password):
        username = AES_Encrypt(username)
        password = AES_Encrypt(password)
        parm = {
            "fid": -1,
            "uname": username,
            "password": password,
            "refer": "http%3A%2F%2Foffice.chaoxing.com%2Ffront%2Fthird%2Fapps%2Fseat%2Fcode%3Fid%3D4219%26seatNum%3D380",
            "t": True,
        }
        jsons = self.requests.post(url=self.login_url, params=parm, verify=False)
        obj = jsons.json()
        if obj["status"]:
            logging.info(f"User {username} login successfully")
            return (True, "")
        else:
            logging.info(
                f"User {username} login failed. Please check you password and username! "
            )
            return (False, obj["msg2"])

    def roomid(self, encode):
        url = f"https://office.chaoxing.com/data/apps/seat/room/list?cpage=1&pageSize=100&firstLevelName=&secondLevelName=&thirdLevelName=&deptIdEnc={encode}"
        json_data = self.requests.get(url=url).content.decode("utf-8")
        ori_data = json.loads(json_data)
        for i in ori_data["data"]["seatRoomList"]:
            info = f'{i["firstLevelName"]}-{i["secondLevelName"]}-{i["thirdLevelName"]} id为：{i["id"]}'
            print(info)

    # ========== 新的验证码处理 ==========

    def _get_captcha_data(self):
        """获取验证码数据（文字点选）"""
        url = "https://captcha.chaoxing.com/captcha/get/verification/image"
        timestamp = int(time.time() * 1000)
        capture_key, token = generate_captcha_key(timestamp)
        referer = f"https://office.chaoxing.com/front/third/apps/seat/code?id=3993&seatNum=0199"
        params = {
            "callback": f"jQuery33107685004390294206_1716461324846",
            "captchaId": "42sxgHoTPTKbt0uZxPJ7ssOvtXr3ZgZ1",
            "type": "textclick",
            "version": "1.1.20",
            "captchaKey": capture_key,
            "token": token,
            "referer": referer,
            "_": timestamp,
        }
        response = self.requests.get(url=url, params=params, headers=self.headers)
        content = response.text

        # 去掉 callback 包裹
        data = content.replace(
            "jQuery33107685004390294206_1716461324846(", ""
        ).replace(")", "")
        data = json.loads(data)

         # 调试：打印完整返回
        logging.info(f"验证码接口完整返回: {json.dumps(data, ensure_ascii=False)}")

        captcha_token = data.get("token", "")
        if not captcha_token:
           logging.error(f"返回中没有 token 字段！keys: {list(data.keys())}") 

        origin_image = data["imageVerificationVo"]["originImage"]
        context = data["imageVerificationVo"]["context"]
        return captcha_token, origin_image, context

    def _ocr_text_click(self, image_url, target_words):
        """用 ddddocr 识别图片中目标汉字的坐标"""
        import ddddocr
        import numpy as np
        from io import BytesIO
        from PIL import Image

        # 下载验证码图片
        img_headers = {
            "Referer": "https://office.chaoxing.com/",
            "Host": "captcha-b.chaoxing.com",
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
        }
        r = self.requests.get(image_url, headers=img_headers)
        img_bytes = r.content

        # 使用 ddddocr 的滑块/点选检测
        det = ddddocr.DdddOcr(det=True, show_ad=False)
        
        # 先尝试用目标检测模式
        poses = det.detection(img_bytes)
        
        # 如果上面不行，用传统的 OCR + 坐标方式
        ocr = ddddocr.DdddOcr(show_ad=False)
        result = ocr.classification(img_bytes)
        logging.info(f"OCR 识别结果: {result}")
        logging.info(f"目标文字: {target_words}")
        logging.info(f"检测到的位置: {poses}")

        # 解析目标文字
        # context 格式: ' "阵" "送" "流" '
        import re as re_module
        words = re_module.findall(r'"(\w)"', target_words)
        logging.info(f"需要依次点击的文字: {words}")

        # 如果 ddddocr 的 detection 返回了结果
        if poses:
            # poses 格式通常是 [[x1,y1,x2,y2], ...] 每个对应一个检测到的文字
            # 但我们需要把检测到的文字和坐标对应起来
            # 这里用简单方式：假设检测到的顺序就是图片中的顺序
            text_click_arr = []
            for i, word in enumerate(words):
                if i < len(poses):
                    pos = poses[i]
                    x = pos[0] + (pos[2] - pos[0]) // 2  # 中心点 x
                    y = pos[1] + (pos[3] - pos[1]) // 2  # 中心点 y
                    text_click_arr.append({"x": x, "y": y})
                    logging.info(f"文字 '{word}' 坐标: ({x}, {y})")
            return text_click_arr
        else:
            # 如果 detection 不行，尝试用 classification 配合图片识别
            # 这里用笨办法：假设四个字均匀分布
            logging.warning("ddddocr detection 未返回结果，使用备用方案")
            # 打开图片获取尺寸
            img = Image.open(BytesIO(img_bytes))
            w, h = img.size
            # 假设字在图片中均匀分布（这只是一个猜测，准确率低）
            n = len(words)
            text_click_arr = []
            for i, word in enumerate(words):
                x = int(w * (i + 0.5) / n)
                y = int(h * 0.5)
                text_click_arr.append({"x": x, "y": y})
            return text_click_arr

    def _verify_text_click(self, captcha_token, text_click_arr):
        """提交文字点选验证结果"""
        params = {
            "callback": "cx_captcha_function",
            "captchaId": "42sxgHoTPTKbt0uZxPJ7ssOvtXr3ZgZ1",
            "type": "textclick",
            "token": captcha_token,
            "textClickArr": json.dumps(text_click_arr),
            "coordinate": json.dumps([]),
            "runEnv": "10",
            "version": "1.1.20",
            "_": int(time.time() * 1000),
        }
        response = self.requests.get(
            "https://captcha.chaoxing.com/captcha/check/verification/result",
            params=params,
            headers=self.headers,
        )
        text = response.text.replace("cx_captcha_function(", "").replace(")", "")
        data = json.loads(text)
        logging.info(f"文字点选验证结果: {data}")
        
        if data.get("result") == True or data.get("error") == 0:
            try:
                validate_val = json.loads(data["extraData"])["validate"]
                return validate_val
            except:
                return data.get("token", "")
        return ""

    def resolve_captcha(self):
        """统一的验证码处理入口（优先文字点选，失败则尝试滑块）"""
        logging.info("开始处理验证码...")
        
        try:
            # 尝试文字点选验证码
            captcha_token, origin_image, context = self._get_captcha_data()
            logging.info(f"获取到验证码 token: {captcha_token}")
            logging.info(f"验证码图片: {origin_image}")
            logging.info(f"需要点击的文字: {context}")
            
            text_click_arr = self._ocr_text_click(origin_image, context)
            logging.info(f"识别出的坐标: {text_click_arr}")
            
            if text_click_arr:
                result = self._verify_text_click(captcha_token, text_click_arr)
                if result:
                    logging.info(f"文字点选验证成功！validate: {result}")
                    return result
            
            logging.warning("文字点选验证失败，返回空")
            return ""
            
        except Exception as e:
            logging.error(f"验证码处理出错: {e}")
            return ""

    # ========== 旧的滑块逻辑保留 ==========

    def get_slide_captcha_data(self):
        url = "https://captcha.chaoxing.com/captcha/get/verification/image"
        timestamp = int(time.time() * 1000)
        capture_key, token = generate_captcha_key(timestamp)
        referer = f"https://office.chaoxing.com/front/third/apps/seat/code?id=3993&seatNum=0199"
        params = {
            "callback": f"jQuery33107685004390294206_1716461324846",
            "captchaId": "42sxgHoTPTKbt0uZxPJ7ssOvtXr3ZgZ1",
            "type": "slide",
            "version": "1.1.18",
            "captchaKey": capture_key,
            "token": token,
            "referer": referer,
            "_": timestamp,
            "d": "a",
            "b": "a",
        }
        response = self.requests.get(url=url, params=params, headers=self.headers)
        content = response.text
        data = content.replace(
            "jQuery33107685004390294206_1716461324846(", ")"
        ).replace(")", "")
        data = json.loads(data)
        captcha_token = data["token"]
        bg = data["imageVerificationVo"]["shadeImage"]
        tp = data["imageVerificationVo"]["cutoutImage"]
        return captcha_token, bg, tp

    def x_distance(self, bg, tp):
        import numpy as np
        import cv2

        def cut_slide(slide):
            slider_array = np.frombuffer(slide, np.uint8)
            slider_image = cv2.imdecode(slider_array, cv2.IMREAD_UNCHANGED)
            slider_part = slider_image[:, :, :3]
            mask = slider_image[:, :, 3]
            mask[mask != 0] = 255
            x, y, w, h = cv2.boundingRect(mask)
            cropped_image = slider_part[y : y + h, x : x + w]
            return cropped_image

        c_captcha_headers = {
            "Referer": "https://office.chaoxing.com/",
            "Host": "captcha-b.chaoxing.com",
            "Pragma": "no-cache",
            "Sec-Ch-Ua": '"Google Chrome";v="125", "Chromium";v="125", "Not.A/Brand";v="24"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Linux"',
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        }
        bgc, tpc = self.requests.get(bg, headers=c_captcha_headers), self.requests.get(
            tp, headers=c_captcha_headers
        )
        bg, tp = bgc.content, tpc.content
        bg_img = cv2.imdecode(np.frombuffer(bg, np.uint8), cv2.IMREAD_COLOR)
        tp_img = cut_slide(tp)
        bg_edge = cv2.Canny(bg_img, 100, 200)
        tp_edge = cv2.Canny(tp_img, 100, 200)
        bg_pic = cv2.cvtColor(bg_edge, cv2.COLOR_GRAY2RGB)
        tp_pic = cv2.cvtColor(tp_edge, cv2.COLOR_GRAY2RGB)
        res = cv2.matchTemplate(bg_pic, tp_pic, cv2.TM_CCOEFF_NORMED)
        _, _, _, max_loc = cv2.minMaxLoc(res)
        tl = max_loc
        return tl[0]

    def submit(self, times, roomid, seatid, action):
        for seat in seatid:
            suc = False
            while ~suc and self.max_attempt > 0:
                token, value = self._get_page_token(
                    self.url.format(roomid, seat), require_value=True
                )
                logging.info(f"Get token: {token}")
                captcha = self.resolve_captcha()
                logging.info(f"Captcha token {captcha}")
                suc = self.get_submit(
                    self.submit_url,
                    times=times,
                    token=token,
                    roomid=roomid,
                    seatid=seat,
                    captcha=captcha,
                    action=action,
                    value=value,
                )
                if suc:
                    return suc
                time.sleep(self.sleep_time)
                self.max_attempt -= 1
        return suc

    def get_submit(
        self, url, times, token, roomid, seatid, captcha="", action=False, value=""
    ):
        delta_day = 1 if self.reserve_next_day else 0
        day = datetime.date.today() + datetime.timedelta(
            days=0 + delta_day
        )
        if action:
            day = datetime.date.today() + datetime.timedelta(
                days=1 + delta_day
            )
        parm = {
            "roomId": roomid,
            "startTime": times[0],
            "endTime": times[1],
            "day": str(day),
            "seatNum": seatid,
            "captcha": captcha,
            "token": token,
            "type": "1",
            "verifyData": "1",
        }
        logging.info(f"submit parameter {parm} ")
        parm["enc"] = verify_param(parm, value)
        html = self.requests.post(url=url, params=parm, verify=True).content.decode(
            "utf-8"
        )
        self.submit_msg.append(
            times[0] + "~" + times[1] + ":  " + str(json.loads(html))
        )
        logging.info(json.loads(html))
        return json.loads(html)["success"]
