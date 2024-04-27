version = "1.0.3"
title = f"[v{version}] NameIt"

import win32gui, time, json, os, threading, psutil, win32process, win32api, win32con, random, requests, win32console, ctypes
import dearpygui.dearpygui as dpg
import pyMeow as pm

user32 = ctypes.WinDLL("user32")
configFilePath = f"{os.environ['LOCALAPPDATA']}\\temp\\nameIt"

class configListener(dict):
    def __init__(self, initialDict):
        for k, v in initialDict.items():
            if isinstance(v, dict):
                initialDict[k] = configListener(v)

        super().__init__(initialDict)

    def __setitem__(self, item, value):
        if isinstance(value, dict):
            value = configListener(value)

        super().__setitem__(item, value)

        if hasattr(nameItClass, "config"):
            json.dump(nameItClass.config, open(configFilePath, "w", encoding="utf-8"), indent=4)

class Colors:
    white = pm.get_color("white")
    whiteWatermark = pm.get_color("#f5f5ff")
    black = pm.get_color("black")
    blackFade = pm.fade_color(black, 0.6)
    red = pm.get_color("#e03636")
    green = pm.get_color("#43e06d")

class Offsets:
    m_pBoneArray = 480

class Entity:
    def __init__(self, ptr, pawnPtr, proc):
        self.ptr = ptr
        self.pawnPtr = pawnPtr
        self.proc = proc
        self.pos2d = None
        self.headPos2d = None

    @property
    def name(self):
        return pm.r_string(self.proc, self.ptr + Offsets.m_iszPlayerName)

    @property
    def health(self):
        return pm.r_int(self.proc, self.pawnPtr + Offsets.m_iHealth)

    @property
    def team(self):
        return pm.r_int(self.proc, self.pawnPtr + Offsets.m_iTeamNum)

    @property
    def pos(self):
        return pm.r_vec3(self.proc, self.pawnPtr + Offsets.m_vOldOrigin)
    
    @property
    def isDormant(self):
        return pm.r_bool(self.proc, self.pawnPtr + Offsets.m_bDormant)

    def bonePos(self, bone):
        gameScene = pm.r_int64(self.proc, self.pawnPtr + Offsets.m_pGameSceneNode)
        boneArrayPtr = pm.r_int64(self.proc, gameScene + Offsets.m_pBoneArray)

        return pm.r_vec3(self.proc, boneArrayPtr + bone * 32)
    
    def wts(self, viewMatrix):
        try:
            a, self.pos2d = pm.world_to_screen_noexc(viewMatrix, self.pos, 1)
            b, self.headPos2d = pm.world_to_screen_noexc(viewMatrix, self.bonePos(6), 1)
            
            if not a or not b:
                return False

            return True
        except:
            return False

class NameIt:
    def __init__(self):
        self.config = {
            "version": version,
            "esp": {
                "enabled": False,
                "bind": 0,
                "box": True,
                "boxBackground": False,
                "boxRounding": 0,
                "skeleton": True,
                "redHead": False,
                "snapline": False,
                "onlyEnemies": True,
                "name": False,
                "health": True,
                "color": {"r": 1.0, "g": 0.11, "b": 0.11, "a": 0.8}
            },
            "triggerBot": {
                "enabled": False,
                "bind": 0,
                "onlyEnemies": True,
                "delay": 0,
            },
            "misc": {
                "bhop": False,
                "noFlash": False,
                "watermark": True
            },
            "settings": {
                "saveSettings": True,
                "streamProof": False
            }     
        }

        if os.path.isfile(configFilePath):
            try:
                config = json.loads(open(configFilePath, encoding="utf-8").read())

                isConfigOk = True
                for key in self.config:
                    if not key in config or len(self.config[key]) != len(config[key]):
                        isConfigOk = False

                        break

                if isConfigOk:
                    if not config["settings"]["saveSettings"]:
                        self.config["settings"]["saveSettings"] = False
                    else:
                        if config["version"] == version:
                            self.config = config
            except:
                pass

        self.config = configListener(self.config)

        self.guiWindowHandle = None
        self.overlayWindowHandle = None

        self.overlayThreadExists = False
        self.localTeam = None

        self.espColor = pm.new_color_float(self.config["esp"]["color"]["r"], self.config["esp"]["color"]["g"], self.config["esp"]["color"]["b"], self.config["esp"]["color"]["a"])
        self.espBackGroundColor = pm.fade_color(self.espColor, 0.1)

        self.run()

    def isCsOpened(self):
        while True:
            if not pm.process_running(self.proc):
                os._exit(0)

            time.sleep(3)

    def windowListener(self):
        while True:
            try:
                self.focusedProcess = psutil.Process(win32process.GetWindowThreadProcessId(win32gui.GetForegroundWindow())[-1]).name()
            except:
                self.focusedProcess = ""

            time.sleep(0.5)

    def run(self):
        print("Waiting for CS2...")

        while True:
            time.sleep(1)

            try:
                self.proc = pm.open_process("cs2.exe")
                self.mod = pm.get_module(self.proc, "client.dll")["base"]

                break
            except:
                pass

        print("Starting NameIt!")

        os.system("cls") 

        try:
            offsetsName = ["dwViewMatrix", "dwEntityList", "dwLocalPlayerController", "dwLocalPlayerPawn"] # dwForceJump
            offsets = requests.get("https://raw.githubusercontent.com/a2x/cs2-dumper/main/output/offsets.json").json()
            [setattr(Offsets, k, offsets["client.dll"][k]) for k in offsetsName]

            clientDllName = {
                "m_iIDEntIndex": "C_CSPlayerPawnBase",
                "m_hPlayerPawn": "CCSPlayerController",
                "m_fFlags": "C_BaseEntity",
                "m_iszPlayerName": "CBasePlayerController",
                "m_iHealth": "C_BaseEntity",
                "m_iTeamNum": "C_BaseEntity",
                "m_vOldOrigin": "C_BasePlayerPawn",
                "m_pGameSceneNode": "C_BaseEntity",
                "m_bDormant": "CGameSceneNode",
            }
            clientDll = requests.get("https://raw.githubusercontent.com/a2x/cs2-dumper/main/output/client.dll.json").json()
            [setattr(Offsets, k, clientDll["client.dll"]["classes"][clientDllName[k]]["fields"][k]) for k in clientDllName]
        except Exception as e:
            print(e)
            input("Can't retrieve offsets. Press any key to exit!")

            os._exit(0)

        threading.Thread(target=self.isCsOpened, daemon=True).start()
        threading.Thread(target=self.windowListener, daemon=True).start()
        threading.Thread(target=self.espBindListener, daemon=True).start()

        if self.config["esp"]["enabled"] or self.config["misc"]["watermark"]:
            threading.Thread(target=self.esp, daemon=True).start()

        if self.config["triggerBot"]["enabled"]:
            threading.Thread(target=self.triggerBot, daemon=True).start()

        if self.config["misc"]["bhop"]:
            threading.Thread(target=self.bhop, daemon=True).start()
            
        if self.config["misc"]["noFlash"]:
            self.noFlash()

    def espBindListener(self):
        while not hasattr(self, "focusedProcess"):
            time.sleep(0.1)
        
        while True:
            if self.focusedProcess != "cs2.exe":
                time.sleep(1)

                continue

            time.sleep(0.001)

            bind = self.config["esp"]["bind"]

            if win32api.GetAsyncKeyState(bind) == 0: continue

            self.config["esp"]["enabled"] = not self.config["esp"]["enabled"]

            if self.config["esp"]["enabled"] and not self.overlayThreadExists:
                threading.Thread(target=self.esp, daemon=True).start()
            
            while True:
                try:
                    dpg.set_value(checkboxToggleEsp, not dpg.get_value(checkboxToggleEsp))

                    break
                except:
                    time.sleep(1)

                    pass

            while win32api.GetAsyncKeyState(bind) != 0:
                time.sleep(0.001)

    def getEntities(self):
        entList = pm.r_int64(self.proc, self.mod + Offsets.dwEntityList)
        local = pm.r_int64(self.proc, self.mod + Offsets.dwLocalPlayerController)
        
        for i in range(1, 65):
            try:
                entryPtr = pm.r_int64(self.proc, entList + (8 * (i & 0x7FFF) >> 9) + 16)
                controllerPtr = pm.r_int64(self.proc, entryPtr + 120 * (i & 0x1FF))
                
                if controllerPtr == local:
                    self.localTeam = pm.r_int(self.proc, local + Offsets.m_iTeamNum)

                    continue

                controllerPawnPtr = pm.r_int64(self.proc, controllerPtr + Offsets.m_hPlayerPawn)
                listEntryPtr = pm.r_int64(self.proc, entList + 0x8 * ((controllerPawnPtr & 0x7FFF) >> 9) + 16)
                pawnPtr = pm.r_int64(self.proc, listEntryPtr + 120 * (controllerPawnPtr & 0x1FF))
            except:
                continue

            yield Entity(controllerPtr, pawnPtr, self.proc)

    def esp(self):
        self.overlayThreadExists = True

        while not hasattr(self, "focusedProcess"):
            time.sleep(0.1)

        pm.overlay_init("Counter-Strike 2", fps=144, title="".join(random.choice("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789") for _ in range(8)), trackTarget=True)
        
        self.overlayWindowHandle = pm.get_window_handle()
        if self.config["settings"]["streamProof"]:
            user32.SetWindowDisplayAffinity(self.overlayWindowHandle, 0x00000011)
        else:
            user32.SetWindowDisplayAffinity(self.overlayWindowHandle, 0x00000000)

        while pm.overlay_loop():
            pm.begin_drawing()

            if self.focusedProcess != "cs2.exe":
                pm.end_drawing()

                time.sleep(1)

                continue

            if self.config["misc"]["watermark"]:
                watermark = f"NameIt | {pm.get_fps()} fps"

                xPos = -(-(185 - pm.measure_text(watermark, 20)) // 2)+1

                pm.draw_rectangle_rounded(5, 5, 180, 30, 0.2, 4, Colors.blackFade)
                pm.draw_rectangle_rounded_lines(5, 5, 180, 30, 0.2, 4, self.espBackGroundColor, 2)
                pm.draw_text(watermark, xPos, 11, 20, Colors.whiteWatermark)

            if not self.config["esp"]["enabled"] and not self.config["misc"]["watermark"]:
                pm.end_drawing()
                pm.overlay_close()

                break
            elif not self.config["esp"]["enabled"]:
                pm.end_drawing()

                time.sleep(0.001) # prevent crashing overlay with nuitka??? yes wtf

                continue

            viewMatrix = pm.r_floats(self.proc, self.mod + Offsets.dwViewMatrix, 16)

            for ent in self.getEntities():
                try:
                    if (ent.isDormant or (self.config["esp"]["onlyEnemies"] and self.localTeam == ent.team) or ent.health == 0):
                        continue
                except:
                    pass
                    
                if self.config["esp"]["snapline"]:
                    try:
                        bounds, pos = pm.world_to_screen_noexc(viewMatrix, ent.bonePos(6), 1)

                        posx = pos["x"]
                        posy = pos["y"]

                        if not bounds:
                            posx = pm.get_screen_width() - posx
                            posy = pm.get_screen_height()

                        width = pm.get_screen_width() / 2
                        height = pm.get_screen_height() - 50

                        pm.draw_line(
                            width,
                            height,
                            posx,
                            posy,
                            self.espColor,
                        )
                    except:
                        pass

                if ent.wts(viewMatrix):
                    head = ent.pos2d["y"] - ent.headPos2d["y"]
                    width = head / 2
                    center = width / 2
                    xStart = ent.headPos2d["x"] - center
                    yStart = ent.headPos2d["y"] - center / 2

                    if self.config["esp"]["box"]:
                        pm.draw_rectangle_rounded_lines(
                            xStart,
                            yStart,
                            width,
                            head + center / 2,
                            self.config["esp"]["boxRounding"],
                            1,
                            self.espColor,
                            1.2,
                        )

                    if self.config["esp"]["boxBackground"]:
                        pm.draw_rectangle_rounded(
                            xStart,
                            yStart,
                            width,
                            head + center / 2,
                            self.config["esp"]["boxRounding"],
                            1,
                            self.espBackGroundColor,
                        )

                    if self.config["esp"]["redHead"]:
                        pm.draw_circle_sector(
                            ent.headPos2d["x"],
                            ent.headPos2d["y"],
                            center / 3,
                            0,
                            360,
                            0,
                            Colors.red,
                        )

                    if self.config["esp"]["skeleton"]:
                        try:
                            cou = pm.world_to_screen(viewMatrix, ent.bonePos(5), 1)
                            shoulderR = pm.world_to_screen(viewMatrix, ent.bonePos(8), 1)
                            shoulderL = pm.world_to_screen(viewMatrix, ent.bonePos(13), 1)
                            brasR = pm.world_to_screen(viewMatrix, ent.bonePos(9), 1)
                            brasL = pm.world_to_screen(viewMatrix, ent.bonePos(14), 1)
                            handR = pm.world_to_screen(viewMatrix, ent.bonePos(11), 1)
                            handL = pm.world_to_screen(viewMatrix, ent.bonePos(16), 1)
                            waist = pm.world_to_screen(viewMatrix, ent.bonePos(0), 1)
                            kneesR = pm.world_to_screen(viewMatrix, ent.bonePos(23), 1)
                            kneesL = pm.world_to_screen(viewMatrix, ent.bonePos(26), 1)
                            feetR = pm.world_to_screen(viewMatrix, ent.bonePos(24), 1)
                            feetL = pm.world_to_screen(viewMatrix, ent.bonePos(27), 1)

                            # pm.draw_circle_lines(ent.headPos2d["x"], ent.headPos2d["y"], center / 3, Colors.white) # looks bad?
                            pm.draw_line(cou["x"], cou["y"], shoulderR["x"], shoulderR["y"], Colors.white, 1)
                            pm.draw_line(cou["x"], cou["y"], shoulderL["x"], shoulderL["y"], Colors.white, 1)
                            pm.draw_line(brasL["x"], brasL["y"], shoulderL["x"], shoulderL["y"], Colors.white, 1)
                            pm.draw_line(brasR["x"], brasR["y"], shoulderR["x"], shoulderR["y"], Colors.white, 1)
                            pm.draw_line(brasR["x"], brasR["y"], handR["x"], handR["y"], Colors.white, 1)
                            pm.draw_line(brasL["x"], brasL["y"], handL["x"], handL["y"], Colors.white, 1)
                            pm.draw_line(cou["x"], cou["y"], waist["x"], waist["y"], Colors.white, 1)
                            pm.draw_line(kneesR["x"], kneesR["y"], waist["x"], waist["y"], Colors.white, 1)
                            pm.draw_line(kneesL["x"], kneesL["y"], waist["x"], waist["y"], Colors.white, 1)
                            pm.draw_line(kneesL["x"], kneesL["y"], feetL["x"], feetL["y"], Colors.white, 1)
                            pm.draw_line(kneesR["x"], kneesR["y"], feetR["x"], feetR["y"], Colors.white, 1)
                        except:
                            pass

                    if self.config["esp"]["health"]:
                        pm.draw_rectangle_rounded(
                            ent.headPos2d["x"] - center - 10,
                            ent.headPos2d["y"] - center / 2 + (head * 0 / 100),
                            3,
                            head + center / 2 - (head * 0 / 100),
                            self.config["esp"]["boxRounding"],
                            1,
                            self.espBackGroundColor,
                        )

                        pm.draw_rectangle_rounded(
                            ent.headPos2d["x"] - center - 10,
                            ent.headPos2d["y"] - center / 2 + (head * (100 - ent.health) / 100),
                            3,
                            head + center / 2 - (head * (100 - ent.health) / 100),
                            self.config["esp"]["boxRounding"],
                            1,
                            Colors.green,
                        )

                    if self.config["esp"]["name"]:
                        pm.draw_text(
                            ent.name,
                            ent.headPos2d["x"] - pm.measure_text(ent.name, 15) // 2,
                            ent.headPos2d["y"] - center / 2 - 15,
                            15,
                            Colors.white,
                        )

            pm.end_drawing()

        self.overlayThreadExists = False

    def triggerBot(self):
        while not hasattr(self, "focusedProcess"):
            time.sleep(0.1)

        while True:
            time.sleep(0.001)

            if not self.config["triggerBot"]["enabled"]: break

            if self.focusedProcess != "cs2.exe":
                time.sleep(1)
                
                continue

            if win32api.GetAsyncKeyState(self.config["triggerBot"]["bind"]) == 0: continue

            try:
                player = pm.r_int64(self.proc, self.mod + Offsets.dwLocalPlayerPawn)
                entityId = pm.r_int(self.proc, player + Offsets.m_iIDEntIndex)

                if entityId > 0:
                    entList = pm.r_int64(self.proc, self.mod + Offsets.dwEntityList)
                    entEntry = pm.r_int64(self.proc, entList + 0x8 * (entityId >> 9) + 0x10)
                    entity = pm.r_int64(self.proc, entEntry + 120 * (entityId & 0x1FF))

                    entityTeam = pm.r_int(self.proc, entity + Offsets.m_iTeamNum)
                    playerTeam = pm.r_int(self.proc, player + Offsets.m_iTeamNum)


                    if self.config["triggerBot"]["onlyEnemies"] and playerTeam == entityTeam: continue

                    entityHp = pm.r_int(self.proc, entity + Offsets.m_iHealth)

                    if entityHp > 0:
                        time.sleep(self.config["triggerBot"]["delay"])
                        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0)
                        time.sleep(0.01)
                        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0)
            except:
                pass

    def bhop(self):
        return
        
        # while not hasattr(self, "focusedProcess"):
        #     time.sleep(0.1)
        
        # while True:
        #     if not self.config["misc"]["bhop"]: break

        #     if self.focusedProcess != "cs2.exe":
        #         time.sleep(1)

        #         continue

        #     if win32api.GetAsyncKeyState(0x20) == 0: continue

        #     player = pm.r_int64(self.proc, self.mod + Offsets.dwLocalPlayerPawn)
        #     flag = pm.r_int(self.proc, player + Offsets.m_fFlags)
            
        #     if flag & (1 << 0):
        #         time.sleep(0.0017)
                
        #         pm.w_int(self.proc, self.mod + Offsets.dwForceJump, 65537)
        #     else:
        #         pm.w_int(self.proc, self.mod + Offsets.dwForceJump, 256)
                
    def noFlash(self):
        return
        
        # try:
        #     (flashAddress,) = pm.aob_scan_module(self.proc, pm.get_module(self.proc, "client.dll")["name"], "0f 83 ?? ?? ?? ?? 48 8b 1d ?? ?? ?? ?? 40 38 73")
        # except:
        #     (flashAddress,) = pm.aob_scan_module(self.proc, pm.get_module(self.proc, "client.dll")["name"], "0f 82 ?? ?? ?? ?? 48 8b 1d ?? ?? ?? ?? 40 38 73")
        
        # if self.config["misc"]["noFlash"]:
        #     pm.w_bytes(self.proc, flashAddress, b"\x0f\x82")
        # else:
        #     pm.w_bytes(self.proc, flashAddress, b"\x0f\x83")


if __name__ == "__main__":
    if os.name != "nt":
        input("NameIt is only working on Windows.")

        os._exit(0)

    nameItClass = NameIt()

    win32gui.ShowWindow(win32console.GetConsoleWindow(), win32con.SW_HIDE)

    uiWidth = 800
    uiHeight = 500

    dpg.create_context()

    def toggleEsp(id, value):
        nameItClass.config["esp"]["enabled"] = value

        if value and not nameItClass.overlayThreadExists:
            threading.Thread(target=nameItClass.esp, daemon=True).start()
    
    waitingForKeyEsp = False
    def statusBindEsp(id):
        global waitingForKeyEsp

        if not waitingForKeyEsp:
            with dpg.handler_registry(tag="Esp Bind Handler"):
                dpg.add_key_press_handler(callback=setBindEsp)

            dpg.set_item_label(buttonBindEsp, "...")

            waitingForKeyEsp = True

    def setBindEsp(id, value):
        global waitingForKeyEsp

        if waitingForKeyEsp:
            nameItClass.config["esp"]["bind"] = value

            dpg.set_item_label(buttonBindEsp, f"Bind: {chr(value)}")
            dpg.delete_item("Esp Bind Handler")

            waitingForKeyEsp = False

    def toggleEspBox(id, value):
        nameItClass.config["esp"]["box"] = value

    def toggleEspBoxBackground(id, value):
        nameItClass.config["esp"]["boxBackground"] = value

    def toggleEspSkeleton(id, value):
        nameItClass.config["esp"]["skeleton"] = value

    def toggleEspRedHead(id, value):
        nameItClass.config["esp"]["redHead"] = value

    def toggleEspSnapline(id, value):
        nameItClass.config["esp"]["snapline"] = value

    def toggleEspOnlyEnemies(id, value):
        nameItClass.config["esp"]["onlyEnemies"] = value

    def toggleEspName(id, value):
        nameItClass.config["esp"]["name"] = value

    def toggleEspHealth(id, value):
        nameItClass.config["esp"]["health"] = value

    def setEspColor(id, value):
        nameItClass.config["esp"]["color"] = {"r": value[0], "g": value[1], "b": value[2], "a": value[3]}

        nameItClass.espColor = pm.new_color_float(value[0], value[1], value[2], value[3])
        nameItClass.espBackGroundColor = pm.fade_color(nameItClass.espColor, 0.3)

    def setEspBoxRounding(id, value):
        nameItClass.config["esp"]["boxRounding"] = value

    def toggleTriggerBot(id, value):
        nameItClass.config["triggerBot"]["enabled"] = value

        if value:
            threading.Thread(target=nameItClass.triggerBot, daemon=True).start()
    
    waitingForKeyTriggerBot = False
    def statusBindTriggerBot(id):
        global waitingForKeyTriggerBot

        if not waitingForKeyTriggerBot:
            with dpg.handler_registry(tag="TriggerBot Bind Handler"):
                dpg.add_key_press_handler(callback=setBindTriggerBot)

            dpg.set_item_label(buttonBindTriggerBot, "...")

            waitingForKeyTriggerBot = True

    def setBindTriggerBot(id, value):
        global waitingForKeyTriggerBot

        if waitingForKeyTriggerBot:
            nameItClass.config["triggerBot"]["bind"] = value

            dpg.set_item_label(buttonBindTriggerBot, f"Bind: {chr(value)}")
            dpg.delete_item("TriggerBot Bind Handler")

            waitingForKeyTriggerBot = False

    def toggleTriggerBotOnlyEnemies(id, value):
        nameItClass.config["triggerBot"]["onlyEnemies"] = value

    def sliderTriggerBotDelay(id, value):
        nameItClass.config["triggerBot"]["delay"] = value

    def toggleBunnyHop(id, value):
        nameItClass.config["misc"]["bhop"] = value       

        if value:
            threading.Thread(target=nameItClass.bhop, daemon=True).start()    
            
    def toggleNoFlash(id, value):
        nameItClass.config["misc"]["noFlash"] = value       

        nameItClass.noFlash()

    def toggleWatermark(id, value):
        nameItClass.config["misc"]["watermark"] = value    

        if value and not nameItClass.overlayThreadExists:
            threading.Thread(target=nameItClass.esp, daemon=True).start()

    def toggleSaveSettings(id, value):
        nameItClass.config["settings"]["saveSettings"] = value

    def toggleStreamProof(id, value):
        nameItClass.config["settings"]["streamProof"] = value   

        if value:
            user32.SetWindowDisplayAffinity(nameItClass.guiWindowHandle, 0x00000011)
            user32.SetWindowDisplayAffinity(nameItClass.overlayWindowHandle, 0x00000011)
        else:
            user32.SetWindowDisplayAffinity(nameItClass.guiWindowHandle, 0x00000000)
            user32.SetWindowDisplayAffinity(nameItClass.overlayWindowHandle, 0x00000000)

    def toggleAlwaysOnTop(id, value):
        if value:
            win32gui.SetWindowPos(nameItClass.guiWindowHandle, win32con.HWND_TOPMOST, 0, 0, 0, 0, win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
        else:
            win32gui.SetWindowPos(nameItClass.guiWindowHandle, win32con.HWND_NOTOPMOST, 0, 0, 0, 0, win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)

    with dpg.window(label=title, width=uiWidth, height=uiHeight, no_collapse=True, no_move=True, no_resize=True, on_close=lambda: os._exit(0)) as window:
        with dpg.tab_bar():
            with dpg.tab(label="ESP"):
                dpg.add_spacer(width=75)

                with dpg.group(horizontal=True):
                    checkboxToggleEsp = dpg.add_checkbox(label="Toggle", default_value=nameItClass.config["esp"]["enabled"], callback=toggleEsp)
                    buttonBindEsp = dpg.add_button(label="Click to Bind", callback=statusBindEsp)

                    bind = nameItClass.config["esp"]["bind"]
                    if bind != 0:
                        dpg.set_item_label(buttonBindEsp, f"Bind: {chr(bind)}")

                dpg.add_spacer(width=75)
                dpg.add_separator()
                dpg.add_spacer(width=75)

                with dpg.group(horizontal=True):
                    checkboxEspBox= dpg.add_checkbox(label="Box", default_value=nameItClass.config["esp"]["box"], callback=toggleEspBox)
                    checkboxEspBackground = dpg.add_checkbox(label="Background", default_value=nameItClass.config["esp"]["boxBackground"], callback=toggleEspBoxBackground)

                with dpg.group(horizontal=True):
                    checkboxEspSkeleton= dpg.add_checkbox(label="Skeleton", default_value=nameItClass.config["esp"]["skeleton"], callback=toggleEspSkeleton)
                    checkboxEspSkeleton= dpg.add_checkbox(label="Red Head", default_value=nameItClass.config["esp"]["redHead"], callback=toggleEspRedHead)

                checkboxEspSnapline= dpg.add_checkbox(label="Snapline", default_value=nameItClass.config["esp"]["snapline"], callback=toggleEspSnapline)
                checkboxEspOnlyEnemies = dpg.add_checkbox(label="Only Enemies", default_value=nameItClass.config["esp"]["onlyEnemies"], callback=toggleEspOnlyEnemies)
                checkboxEspName = dpg.add_checkbox(label="Show Name", default_value=nameItClass.config["esp"]["name"], callback=toggleEspName)
                checkboxEspHealth = dpg.add_checkbox(label="Show Health", default_value=nameItClass.config["esp"]["health"], callback=toggleEspHealth)

                dpg.add_spacer(width=75)
                dpg.add_separator()
                dpg.add_spacer(width=75)

                colorPickerEsp = dpg.add_color_picker(label="Global Color", default_value=(nameItClass.config["esp"]["color"]["r"]*255, nameItClass.config["esp"]["color"]["g"]*255, nameItClass.config["esp"]["color"]["b"]*255, nameItClass.config["esp"]["color"]["a"]*255), width=150, no_inputs=True, callback=setEspColor)
                sliderEspBoxRounding = dpg.add_slider_float(label="Box Rounding", default_value=nameItClass.config["esp"]["boxRounding"], min_value=0, max_value=1, clamped=True, format="%.1f", callback=setEspBoxRounding, width=250)
            with dpg.tab(label="TriggerBot"):
                dpg.add_spacer(width=75)

                with dpg.group(horizontal=True):
                    checkboxToggleTriggerBot = dpg.add_checkbox(label="Toggle", default_value=nameItClass.config["triggerBot"]["enabled"], callback=toggleTriggerBot)
                    buttonBindTriggerBot = dpg.add_button(label="Click to Bind", callback=statusBindTriggerBot)
                    bind = nameItClass.config["triggerBot"]["bind"]
                    if bind != 0:
                        dpg.set_item_label(buttonBindTriggerBot, f"Bind: {chr(bind)}")   

                dpg.add_spacer(width=75)
                dpg.add_separator()
                dpg.add_spacer(width=75)

                checkboxTriggerBotOnlyEnemies = dpg.add_checkbox(label="Only Enemies", default_value=nameItClass.config["triggerBot"]["onlyEnemies"], callback=toggleTriggerBotOnlyEnemies)
                
                dpg.add_spacer(width=75)
                dpg.add_separator()
                dpg.add_spacer(width=75)

                sliderDelayTriggerBot = dpg.add_slider_float(label="Shot Delay", default_value=nameItClass.config["triggerBot"]["delay"], max_value=1, callback=sliderTriggerBotDelay, width=250, clamped=True, format="%.1f")
            with dpg.tab(label="Misc"):
                dpg.add_spacer(width=75)

                with dpg.group(horizontal=True):
                    checkboxBhop = dpg.add_checkbox(label="BunnyHop", default_value=nameItClass.config["misc"]["bhop"], callback=toggleBunnyHop)
                    dpg.add_text(default_value="| Hold space!")
                    
                checkboxNoFlash = dpg.add_checkbox(label="NoFlash", default_value=nameItClass.config["misc"]["noFlash"], callback=toggleNoFlash)
                checkboxWatermark = dpg.add_checkbox(label="Watermark", default_value=nameItClass.config["misc"]["watermark"], callback=toggleWatermark)
            with dpg.tab(label="Settings"):
                dpg.add_spacer(width=75)

                checkboxSaveSettings = dpg.add_checkbox(label="Save Settings", default_value=nameItClass.config["settings"]["saveSettings"], callback=toggleSaveSettings)

                dpg.add_spacer(width=75)

                checkboxStreamProof = dpg.add_checkbox(label="Stream Proof", default_value=nameItClass.config["settings"]["streamProof"], callback=toggleStreamProof)
                checkboxAlwaysOnTop = dpg.add_checkbox(label="Always On Top", callback=toggleAlwaysOnTop)

                dpg.add_spacer(width=75)
                dpg.add_separator()
                dpg.add_spacer(width=75)

                creditsText = dpg.add_text(default_value="Credits: Goldy, Pingu and PyMeow Community")
                githubText = dpg.add_text(default_value="https://github.com/g0ldyy/NameIt")

    def dragViewport(sender, appData, userData):
        if dpg.get_mouse_pos(local=False)[1] <= 40:
            dragDeltas = appData
            viewportPos = dpg.get_viewport_pos()
            newX = viewportPos[0] + dragDeltas[1]
            newY = max(viewportPos[1] + dragDeltas[2], 0)

            dpg.set_viewport_pos([newX, newY])

    with dpg.handler_registry():
        dpg.add_mouse_drag_handler(button=0, threshold=0.0, callback=dragViewport)

    with dpg.theme() as globalTheme:
        with dpg.theme_component(dpg.mvAll):
            dpg.add_theme_color(dpg.mvThemeCol_WindowBg, (21, 19, 21, 255))
            dpg.add_theme_color(dpg.mvThemeCol_TitleBg, (21, 19, 21, 255))
            dpg.add_theme_color(dpg.mvThemeCol_CheckMark, (255, 255, 255, 255))
            dpg.add_theme_color(dpg.mvThemeCol_Text, (225, 225, 225, 255))

            dpg.add_theme_style(dpg.mvStyleVar_WindowBorderSize, 0)
            dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 3)

    dpg.bind_theme(globalTheme)

    dpg.create_viewport(title=title, width=uiWidth, height=uiHeight, decorated=False, resizable=False)
    dpg.show_viewport()
    
    nameItClass.guiWindowHandle = win32gui.FindWindow(title, None)
    if nameItClass.config["settings"]["streamProof"]:
        user32.SetWindowDisplayAffinity(nameItClass.guiWindowHandle, 0x00000011)

    dpg.setup_dearpygui()
    dpg.start_dearpygui()