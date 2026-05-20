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


SLEEPTIME = 3
ENDTIME = "20:01:00"

ENABLE_SLIDER = True
MAX_ATTEMPT = 60
RESERVE_NEXT_DAY = False

MIN_SLEEP = 2.0
MAX_SLEEP = 3.0

SPRINT_TIME = "19:59:58"
MIN_SPRINT = 0.3
MAX_SPRINT = 0.7

FAST_SWITCH_MIN = 0.1
FAST_SWITCH_MAX = 0.3

LOGIN_TIME = "19:59:30"


def main(users, action=False):
    current_time = get_current_time(action)
    logging.info(f"start time {current_time}, action {'on' if action else 'off'}")

    username, password = None, None
    if action:
        username, password = get_user_credentials(action)
    else:
        username, password = users["username"], users["password"]

    current_dayofweek = get_current_dayofweek(action)
    if current_dayofweek not in users["daysofweek"]:
        logging.info("Today not set to reserve")
        return

    # 等到 19:59:30 再登录
    target_hour = 19
    target_minute = 59
    target_second = 30
    logging.info(f"等待到 {target_hour:02d}:{target_minute:02d}:{target_second:02d} 再登录...")

    while True:
        now_ts = time.time() + (8 * 3600 if action else 0)
        now = time.localtime(now_ts)
        if (now.tm_hour == target_hour and
            now.tm_min == target_minute and
            now.tm_sec >= target_second):
            break
        time.sleep(0.5)

    logging.info("时间到！开始登录！")

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
    seat_index = 0
    fast_switch = False
    attempt_times = 0
    current_time = get_current_time(action)

    while current_time < ENDTIME:
        attempt_times += 1

        # 决定等待时间
        if fast_switch:
            sleep_time = random.uniform(FAST_SWITCH_MIN, FAST_SWITCH_MAX)
            fast_switch = False
        elif current_time >= SPRINT_TIME:
            sleep_time = random.uniform(MIN_SPRINT, MAX_SPRINT)
        else:
            sleep_time = random.uniform(MIN_SLEEP, MAX_SLEEP)

        # 打断机制：每 0.5 秒检查时间，确保冲刺准时
        sleep_left = sleep_time
        while sleep_left > 0:
            time.sleep(0.5)
            sleep_left -= 0.5
            current_time = get_current_time(action)
            if current_time >= SPRINT_TIME:
                break

        current_seat = seatid[seat_index]
        suc = s.submit(times, roomid, [current_seat], action)
        print(f"attempt {attempt_times}, time {current_time}, seat {current_seat}, success {suc}")

        if suc:
            break
        else:
            if seat_index < len(seatid) - 1:
                seat_index += 1
                fast_switch = True
            else:
                seat_index = 0
            current_time = get_current_time(action)

    if suc:
        print("reserved successfully!")
    else:
        print("out of reserve time.")


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
