import json
import time
import argparse
import os
import logging
import random
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


from utils import reserve, get_user_credentials

get_current_time = lambda action: (
    time.strftime("%H:%M:%S", time.localtime(time.time() + 8 * 3600))
    if action
    else time.strftime("%H:%M:%S", time.localtime(time.time()))
)
get_current_dayofweek = lambda action: (
    time.strftime("%A", time.localtime(time.time() + 8 * 3600))
    if action
    else time.strftime("%A", time.localtime(time.time()))
)


SLEEPTIME = 3  # 基础间隔（备用，新逻辑里用下面两个随机值）
ENDTIME = "20:01:00"  # 根据学校的预约座位时间+1min即可

ENABLE_SLIDER = True  # 是否有滑块验证
MAX_ATTEMPT = 60  # 最大尝试次数
RESERVE_NEXT_DAY = False  # 预约明天而不是今天的

MIN_SLEEP = 0.2  # 最小随机间隔（秒）
MAX_SLEEP = 0.5  # 最大随机间隔（秒）


def main(users, action=False):
    current_time = get_current_time(action)
    logging.info(f"start time {current_time}, action {'on' if action else 'off'}")
    attempt_times = 0
    username, password = None, None
    if action:
        username, password = get_user_credentials(action)
    else:
        username, password = users["username"], users["password"]
    current_dayofweek = get_current_dayofweek(action)
    if current_dayofweek not in users["daysofweek"]:
        logging.info("Today not set to reserve")
        return
    s = reserve(
        sleep_time=SLEEPTIME,
        max_attempt=MAX_ATTEMPT,
        enable_slider=ENABLE_SLIDER,
        reserve_next_day=RESERVE_NEXT_DAY,
    )
    s.get_login_status()
    s.login(username, password)
    s.requests.headers.update({"Host": "office.chaoxing.com"})
    _, _, _, times, roomid, seatid, _ = users.values()
    if type(seatid) == str:
        seatid = [seatid]
    suc = False
    while current_time < ENDTIME:
            suc = False
    seat_index = 0
    fast_switch = False
    while current_time < ENDTIME:
        attempt_times += 1
        
        # 如果是快速切换，等待 0.1~0.3 秒；否则正常随机等待
        if fast_switch:
            sleep_time = random.uniform(0.1, 0.3)
            fast_switch = False
        else:
            sleep_time = random.uniform(MIN_SLEEP, MAX_SLEEP)
        time.sleep(sleep_time)
        
        current_seat = seatid[seat_index]
        suc = s.submit(times, roomid, [current_seat], action)
        print(f"attempt {attempt_times}, time {current_time}, seat {current_seat}, success {suc}")
        
        if suc:
            break
        else:
            # 如果座位被占，切换到下一个
            if seat_index < len(seatid) - 1:
                seat_index += 1
                fast_switch = True  # 下次循环快速切换
            else:
                seat_index = 0  # 所有座位都试完，回到第一个继续
            current_time = get_current_time(action)


if __name__ == "__main__":
    config_path = os.path.join(os.path.dirname(__file__), "config.json")
    parser = argparse.ArgumentParser(prog="Chao Xing seat auto reserve")
    parser.add_argument("-u", "--user", default=config_path, help="user config file")
    parser.add_argument(
        "-m",
        "--method",
        default="reserve",
        choices=["reserve", "debug", "room"],
        help="for debug",
    )
    parser.add_argument(
        "-a",
        "--action",
        action="store_true",
        help="use --action to enable in github action",
    )
    args = parser.parse_args()
    func_dict = {"reserve": main}
    with open(args.user, "r+") as data:
        usersdata = json.load(data)["reserve"][0]
    func_dict[args.method](usersdata, args.action)
