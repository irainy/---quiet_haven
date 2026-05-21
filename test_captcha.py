import requests
import json
import os
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

USERNAME = os.environ.get("USERNAMES", "")
PASSWORD = os.environ.get("PASSWORDS", "")

if not USERNAME or not PASSWORD:
    logging.error("未读取到用户名密码！请检查 GitHub Secrets。")
    exit(1)

config_path = os.path.join(os.path.dirname(__file__), "config.json")
with open(config_path, "r") as f:
    config = json.load(f)["reserve"][0]

ROOMID = config["roomid"]
TIMES = config["time"]

s = requests.Session()
s.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
})

# Step 1: 获取 session
logging.info("Step 1: 获取 session...")
r = s.get("https://office.chaoxing.com/front/third/apps/seat/code?seatId=1&roomId=1")
logging.info(f"状态码: {r.status_code}")

# Step 2: 登录
logging.info("Step 2: 登录...")
login_url = "https://passport2.chaoxing.com/fanyalogin"
login_data = {
    "fid": "-1",
    "uname": USERNAME,
    "password": PASSWORD,
    "refer": "https://office.chaoxing.com/front/third/apps/seat/index",
    "t": "true",
    "forbidotherlogin": "0",
    "validate": "",
    "doubleFactorLogin": "0",
    "independentId": "0",
}
r = s.post(login_url, data=login_data)
logging.info(f"登录返回前300字符: {r.text[:300]}")

# Step 3: 触发预约
logging.info("Step 3: 触发预约请求...")
reserve_url = "https://office.chaoxing.com/front/third/apps/seat/submit"
params = {
    "roomId": ROOMID,
    "startTime": TIMES[0],
    "endTime": TIMES[1],
    "day": "",
    "captcha": "",
}
r = s.get(reserve_url, params=params)

# 打印完整返回
try:
    resp_json = r.json()
    logging.info("完整 JSON 返回:")
    logging.info(json.dumps(resp_json, ensure_ascii=False, indent=2))
except:
    logging.info(f"非 JSON 返回，前800字符: {r.text[:800]}")

logging.info("========== 测试完成 ==========")
