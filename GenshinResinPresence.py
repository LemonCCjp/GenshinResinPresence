from pypresence import AioPresence
from pypresence.types import ActivityType
import time
import asyncio
import json
import os
import sys
import ctypes

from PythinImpact import Details

from pystray import Icon, MenuItem, Menu
from PIL import Image
import threading


USER_DATA_PATH = "user_data.json"

with open(USER_DATA_PATH, 'r', encoding="utf-8") as f:
    USERS_DATA = json.load(f)

uid = USERS_DATA["uid"]
ltmid_v2 = USERS_DATA["ltmid_v2"]
ltuid_v2 = USERS_DATA["ltuid_v2"]
ltoken_v2 = USERS_DATA["ltoken_v2"]


CLIENT_ID = USERS_DATA["CLIENT_ID"]

current_resin = 0

refresh_event = threading.Event()

async def main():
    pi_user = Details.User(uid, ltmid_v2, ltuid_v2, ltoken_v2)

    RPC = AioPresence(CLIENT_ID)

    try:
        await RPC.connect()
    except Exception as e:
        msg = (
            "Discord RPC に接続できませんでした。\n\n"
            "考えられる原因:\n"
            "・Discord が起動していない\n"
            "・CLIENT_ID が間違っている\n"
            "・Discord にログインしていない\n"
            "・Discord 側のRPC接続に失敗した\n\n"
            f"エラー:\n{e}"
        )
        threading.Thread(
            target=show_error_popup,
            args=(msg, "RPC接続エラー", None),
            daemon=True
        ).start()
        return

    while True:
        DailyNote = await pi_user.getDailyNote()
        global current_resin

        if DailyNote["data"] is None:
            current_resin += 1
            missing = 200 - current_resin
            resin_recovery_time = missing *480

        else:
            current_resin = int(DailyNote["data"]["current_resin"])
            missing = 200 - current_resin
            resin_recovery_time = DailyNote["data"]["resin_recovery_time"]


        resin_time = int(time.time()) + int(resin_recovery_time)

        if missing <= 0:
            next_resin_in = 480
        else:
            next_resin_in = int(resin_recovery_time) - (missing - 1) * 480

        now = time.time()

        await RPC.update(
            state="樹脂",
            details="全回復まで",
            start=int(now),
            end=resin_time,
            large_image="https://media.discordapp.net/stickers/1496875430777454662.webp?size=160&quality=lossless",
            large_text="Genshin Impact",
            party_size=[current_resin, 200],
            activity_type=ActivityType.PLAYING,
            name="Genshin Impact",
            small_image="https://cdn.discordapp.com/emojis/1451244468568330293.webp?size=96",
            small_text="樹脂",
            instance=True
        )

        await interruptible_sleep(next_resin_in)


def show_error_popup(text, title="エラー", open=None):
    result = ctypes.windll.user32.MessageBoxW(0, text, title, 0x10)

    if not open is None:
        if result == 1:
            os.startfile(open)

async def wait_with_refresh(seconds):
    seconds = max(1, int(seconds))

    for _ in range(seconds):
        if refresh_event.is_set():
            refresh_event.clear()
            return False  # 手動更新
        await asyncio.sleep(1)

    return True  # 時間経過


def get_base_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


class taskTray:
    def __init__(self, image):
        image = Image.open(image)

        menu = Menu(
            MenuItem('GenshinImpactを起動', self.LaunchShortcut),
            MenuItem("更新", self.RefreshNow),
            MenuItem('終了', self.ExitProgram),
        )

        self.icon = Icon(name='GRP', title='GRP', icon=image, menu=menu)

    def LaunchShortcut(self, icon, item):
        base_dir = get_base_dir()
        shortcut_dir = os.path.join(base_dir, "Shortcut")

        if os.path.isdir(shortcut_dir):
            files = sorted(
                f for f in os.listdir(shortcut_dir)
                if f.lower().endswith(".lnk")
            )

            if files:
                first_path = os.path.join(shortcut_dir, files[0])
                os.startfile(first_path)
            else:
                threading.Thread(
                    target=show_error_popup,
                    args=("Shortcutフォルダ内にGenshinImpact.exeのショートカットを配置してください。", "エラー", "Shortcut"),
                    daemon=True
                ).start()
        else:
            threading.Thread(
                target=show_error_popup,
                args=("Shortcutフォルダが見つかりません。", "エラー", None),
                daemon=True
            ).start()

    def RefreshNow(self, icon, item):
        refresh_event.set()

    def ExitProgram(self, icon, item):
        self.icon.stop()


stop_event = threading.Event()

async def interruptible_sleep(seconds):
    for _ in range(max(1, int(seconds))):
        if stop_event.is_set():
            stop_event.clear()
            return False
        await asyncio.sleep(1)
    return True

def run_async_main():
    asyncio.run(main())


if __name__ == "__main__":
    threading.Thread(target=run_async_main, daemon=True).start()

    system_tray = taskTray(image="latest.ico")
    system_tray.icon.run()