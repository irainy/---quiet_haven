import os
os.environ["FLAGS_use_onednn"] = "0"

from utils import AES_Encrypt, enc, generate_captcha_key, verify_param
import json
import requests
import re
import time
import logging
import datetime
from hashlib import md5
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

    # ==================== 新的验证码处理 ====================

    def _get_captcha_data(self):
        """获取验证码数据（文字点选）"""
        timestamp = int(time.time() * 1000)

        # 第一步：调用 conf 接口获取 t 值
        conf_url = "https://captcha.chaoxing.com/captcha/get/conf"
        conf_params = {
            "callback": "cx_captcha_function",
            "captchaId": "42sxgHoTPTKbt0uZxPJ7ssOvtXr3ZgZ1",
            "_": timestamp,
        }
        conf_response = self.requests.get(url=conf_url, params=conf_params, headers=self.headers)
        conf_text = conf_response.text.replace("cx_captcha_function(", "").replace(")", "")
        conf_data = json.loads(conf_text)
        logging.info(f"conf 返回: {conf_data}")

        t_value = conf_data.get("t", timestamp)
        iv = md5(str(t_value).encode("utf-8")).hexdigest()
        logging.info(f"t={t_value}, 计算出的 iv={iv}")

        # 第二步：用 t 和 iv 调用 image 接口
        capture_key, token = generate_captcha_key(t_value, "textclick")

        referer = "https://office.chaoxing.com/front/third/apps/seat/index"

        image_url = "https://captcha.chaoxing.com/captcha/get/verification/image"
        image_params = {
            "callback": "cx_captcha_function",
            "captchaId": "42sxgHoTPTKbt0uZxPJ7ssOvtXr3ZgZ1",
            "type": "textclick",
            "version": "1.1.20",
            "captchaKey": capture_key,
            "token": token,
            "referer": referer,
            "iv": iv,
            "_": int(time.time() * 1000),
        }
        image_response = self.requests.get(url=image_url, params=image_params, headers=self.headers)
        content = image_response.text

        data = content.replace("cx_captcha_function(", "").replace(")", "")
        data = json.loads(data)

        logging.info(f"验证码接口完整返回: {json.dumps(data, ensure_ascii=False)}")

        captcha_token = data.get("token", "")
        if not captcha_token:
            logging.error(f"返回中没有 token 字段！keys: {list(data.keys())}")
            return "", "", ""

        origin_image = data["imageVerificationVo"]["originImage"]
        context = data["imageVerificationVo"]["context"]
        return captcha_token, origin_image, context

    def _ocr_text_click(self, image_url, target_words):
        """用 EasyOCR 识别图片中目标汉字的坐标"""
        import re as re_module
        from io import BytesIO
        import numpy as np
        import cv2
        import easyocr

        img_headers = {
            "Referer": "https://office.chaoxing.com/",
            "Host": "captcha-b.chaoxing.com",
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
        }
        r = self.requests.get(image_url, headers=img_headers)
        img_bytes = r.content
        img_array = np.frombuffer(img_bytes, dtype=np.uint8)
        img_cv = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

        words = re_module.findall(r'"(\w)"', target_words)
        logging.info(f"需要依次点击的文字: {words}")

        # 初始化 EasyOCR（首次会下载模型）
        reader = easyocr.Reader(['ch_sim'], gpu=False)
        result = reader.readtext(img_cv)

        # result 格式: [([[x1,y1],[x2,y2],[x3,y3],[x4,y4]], '文字', 置信度), ...]
        box_results = []
        for detection in result:
            box = detection[0]
            text = detection[1]
            x_coords = [p[0] for p in box]
            y_coords = [p[1] for p in box]
            x_center = int(sum(x_coords) / 4)
            y_center = int(sum(y_coords) / 4)
            box_results.append((x_center, y_center, text))
            logging.info(f"识别文字='{text}', 坐标: ({x_center}, {y_center})")

        # 按目标文字顺序匹配坐标
        text_click_arr = []
        used_indices = set()

        for target in words:
            found = False
            for i, (x, y, text) in enumerate(box_results):
                if i in used_indices:
                    continue
                if target == text or target in text or text in target:
                    text_click_arr.append({"x": x, "y": y})
                    used_indices.add(i)
                    logging.info(f"文字 '{target}' 匹配到 '{text}', 坐标: ({x}, {y})")
                    found = True
                    break
            if not found:
                logging.error(f"文字 '{target}' 未匹配到任何识别结果！")

        logging.info(f"最终坐标: {text_click_arr}")
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
        """统一的验证码处理入口"""
        logging.info("开始处理验证码...")

        try:
            captcha_token, origin_image, context = self._get_captcha_data()
            if not captcha_token:
                logging.error("获取验证码 token 失败")
                return ""

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

            logging.warning("文字点选验证失败")
            return ""

        except Exception as e:
            logging.error(f"验证码处理出错: {e}")
            return ""

    # ==================== 旧的滑块逻辑保留 ====================

    def get_slide_captcha_data(self):
        url = "https://captcha.chaoxing.com/captcha/get/verification/image"
        timestamp = int(time.time() * 1000)
        capture_key, token = generate_captcha_key(timestamp, "slide")
        referer = "https://office.chaoxing.com/front/third/apps/seat/code?id=3993&seatNum=0199"
        params = {
            "callback": "jQuery33107685004390294206_1716461324846",
            "captchaId": "42sxgHoTPTKbt0uZxPJ7ssOvtXr3ZgZ1",
            "type": "slide",
            "version": "1.1.18",
            "captchaKey": capture_key,
            "token": token,
            "referer": referer,
            "_": timestamp,
        }
        response = self.requests.get(url=url, params=params, headers=self.headers)
        content = response.text
        data = content.replace("jQuery33107685004390294206_1716461324846(", ")").replace(")", "")
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
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
        }
        bgc = self.requests.get(bg, headers=c_captcha_headers)
        tpc = self.requests.get(tp, headers=c_captcha_headers)
        bg, tp = bgc.content, tpc.content
        bg_img = cv2.imdecode(np.frombuffer(bg, np.uint8), cv2.IMREAD_COLOR)
        tp_img = cut_slide(tp)
        bg_edge = cv2.Canny(bg_img, 100, 200)
        tp_edge = cv2.Canny(tp_img, 100, 200)
        bg_pic = cv2.cvtColor(bg_edge, cv2.COLOR_GRAY2RGB)
        tp_pic = cv2.cvtColor(tp_edge, cv2.COLOR_GRAY2RGB)
        res = cv2.matchTemplate(bg_pic, tp_pic, cv2.TM_CCOEFF_NORMED)
        _, _, _, max_loc = cv2.minMaxLoc(res)
        return max_loc[0]

    # ==================== 提交逻辑 ====================

    def submit(self, times, roomid, seatid, action):
        for seat in seatid:
            suc = False
            while not suc and self.max_attempt > 0:
                token, value = self._get_page_token(
                    self.url.format(roomid, seat), require_value=True
                )
                logging.info(f"Get token: {token}")
                captcha = self.resolve_captcha()
                logging.info(f"Captcha token: {captcha}")
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
        day = datetime.date.today() + datetime.timedelta(days=0 + delta_day)
        if action:
            day = datetime.date.today() + datetime.timedelta(days=1 + delta_day)
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
        logging.info(f"submit parameter {parm}")
        parm["enc"] = verify_param(parm, value)
        html = self.requests.post(url=url, params=parm, verify=True).content.decode("utf-8")
        self.submit_msg.append(
            times[0] + "~" + times[1] + ":  " + str(json.loads(html))
        )
        logging.info(json.loads(html))
        return json.loads(html)["success"]
