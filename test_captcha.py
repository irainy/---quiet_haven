import json
import os
import logging
import time
from utils import reserve, get_user_credentials

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# ---------- 读取配置 ----------
USERNAME, PASSWORD = None, None
if os.environ.get("USERNAMES"):
    USERNAME = os.environ["USERNAMES"]
    PASSWORD = os.environ["PASSWORDS"]

config_path = os.path.join(os.path.dirname(__file__), "config.json")
with open(config_path, "r") as f:
    config = json.load(f)["reserve"][0]

ROOMID = config["roomid"]
SEATID = config["seatid"]
TIMES = config["time"]

if not USERNAME or not PASSWORD:
    logging.error("未读取到用户名密码！")
    exit(1)

# ---------- 创建 reserve 实例 ----------
s = reserve(
    sleep_time=3,
    max_attempt=3,
    enable_slider=True,
    reserve_next_day=False,
)

# ---------- 登录 ----------
logging.info("Step 1: 登录...")
s.get_login_status()
s.login(USERNAME, PASSWORD)
s.requests.headers.update({"Host": "office.chaoxing.com"})

# ---------- 测试预约（只试一次，不循环） ----------
seat = SEATID[0] if isinstance(SEATID, list) else SEATID

logging.info(f"Step 2: 开始预约测试 - room:{ROOMID}, seat:{seat}, time:{TIMES}")
suc = s.submit(TIMES, ROOMID, [seat], action=True)

logging.info(f"结果: {'成功' if suc else '失败'}")
