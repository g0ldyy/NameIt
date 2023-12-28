version = "1.0"

import win32gui, time, json, os, threading, psutil, win32process, win32api, win32con, random, requests
import dearpygui.dearpygui as dpg
import pyMeow as pm

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

        if hasattr(nameItClass, "config") and nameItClass.config["settings"]["saveSettings"]:
            json.dump(nameItClass.config, open(f"{os.environ['LOCALAPPDATA']}\\temp\\nameIt", "w", encoding="utf-8"), indent=4)

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

    def bonePos(self, bone):
        gameScene = pm.r_int64(self.proc, self.pawnPtr + Offsets.m_pGameSceneNode)
        boneArrayPtr = pm.r_int64(self.proc, gameScene + Offsets.m_pBoneArray)

        return pm.r_vec3(self.proc, boneArrayPtr + bone * 32)
    
    def wts(self, viewMatrix):
        try:
            self.pos2d = pm.world_to_screen(viewMatrix, self.pos, 1)
            self.headPos2d = pm.world_to_screen(viewMatrix, self.bonePos(6), 1)
        except:
            return False
        
        return True

class NameIt:
    def __init__(self):
        self.config = {
            "esp": {
                "enabled": False,
                "bind": 0,
                "box": True,
                "boxBackground": True,
                "skeleton": False,
                "snapline": False,
                "onlyEnnemies": True,
                "name": False,
                "health": False,
                "color": {"r": 1.0, "g": 0.11, "b": 0.11, "a": 0.8}
            },
            "triggerBot": {
                "enabled": False,
                "bind": 0,
                "onlyEnnemies": True
            },
            "misc": {
                "bhop": {
                    "enabled": False
                }
            },
            "settings": {
                "saveSettings": True
            }     
        }

        if os.path.isfile(f"{os.environ['LOCALAPPDATA']}\\temp\\nameIt"):
            try:
                config = json.loads(open(f"{os.environ['LOCALAPPDATA']}\\temp\\nameIt", encoding="utf-8").read())

                isConfigOk = True
                for key in self.config:
                    if not key in config or len(self.config[key]) != len(config[key]):
                        isConfigOk = False

                        break

                if isConfigOk:
                    if not config["settings"]["saveSettings"]:
                        self.config["settings"]["saveSettings"] = False
                    else:
                        self.config = config
            except:
                pass

        self.config = configListener(self.config)

        self.espColor = pm.new_color_float(self.config["esp"]["color"]["r"], self.config["esp"]["color"]["g"], self.config["esp"]["color"]["b"], self.config["esp"]["color"]["a"])
        self.espBackGroundColor = pm.fade_color(self.espColor, 0.1)

        self.run()

    def isCsOpened(self):
        while True:
            if not pm.process_running(self.proc):
                print("CS2 closed, bye :)")

                os._exit(0)

            time.sleep(5)

    def windowListener(self):
        while True:
            try:
                self.focusedProcess = psutil.Process(win32process.GetWindowThreadProcessId(win32gui.GetForegroundWindow())[-1]).name()
            except:
                self.focusedProcess = ""

            time.sleep(0.5)

    def run(self):
        print(f"Waiting for CS2...")

        while True:
            try:
                self.proc = pm.open_process("cs2.exe")
                self.mod = pm.get_module(self.proc, "client.dll")["base"]

                print(f"Starting NameIt!")

                break
            except:
                time.sleep(1)

                continue

        try:
            offsetsName = ["dwViewMatrix", "dwEntityList", "dwLocalPlayerController", "dwLocalPlayerPawn", "dwForceJump"]
            offsets = requests.get("https://raw.githubusercontent.com/a2x/cs2-dumper/main/generated/offsets.json").json()
            [setattr(Offsets, k, offsets["client_dll"]["data"][k]["value"]) for k in offsetsName]

            clientDllName = {
                "m_iIDEntIndex": "C_CSPlayerPawnBase",
                "m_hPlayerPawn": "CCSPlayerController",
                "m_fFlags": "C_BaseEntity",
                "m_iszPlayerName": "CBasePlayerController",
                "m_iHealth": "C_BaseEntity",
                "m_iTeamNum": "C_BaseEntity",
                "m_vOldOrigin": "C_BasePlayerPawn",
                "m_pGameSceneNode": "C_BaseEntity",
            }
            clientDll = requests.get("https://raw.githubusercontent.com/a2x/cs2-dumper/9a13b18e5bddb9bc59d5cd9a3693b39fd8d6849b/generated/client.dll.json").json()
            [setattr(Offsets, k, clientDll[clientDllName[k]]["data"][k]["value"]) for k in clientDllName]
        except:
            input("Can't retrieve offsets. Press any key to exit!")

            os._exit(0)

        threading.Thread(target=self.isCsOpened, daemon=True).start()
        threading.Thread(target=self.windowListener, daemon=True).start()
        threading.Thread(target=self.espBindListener, daemon=True).start()

        if self.config["esp"]["enabled"]:
            threading.Thread(target=self.esp, daemon=True).start()

        if self.config["triggerBot"]["enabled"]:
            threading.Thread(target=self.triggerBot, daemon=True).start()

        if self.config["misc"]["bhop"]["enabled"]:
            threading.Thread(target=self.bhop, daemon=True).start()

    def espBindListener(self):
        while True:
            time.sleep(0.001)

            bind = self.config["esp"]["bind"]

            if self.focusedProcess != "cs2.exe":
                time.sleep(1)

                continue

            if win32api.GetAsyncKeyState(bind) == 0:
                continue

            cursorInfo = win32gui.GetCursorInfo()[1] # prevents when typing in chat
            if cursorInfo == 65539:
                time.sleep(1)

                continue

            self.config["esp"]["enabled"] = not self.config["esp"]["enabled"]

            if self.config["esp"]["enabled"]:
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
        self.localTeam = None

        whiteColor = pm.get_color("white")
        blackColor = pm.get_color("black")

        while not hasattr(self, "focusedProcess"):
            time.sleep(0.1)

        pm.overlay_init("Counter-Strike 2", title="".join(random.choice("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789") for _ in range(8)), trackTarget=True)

        while pm.overlay_loop():
            if not self.config["esp"]["enabled"]:
                pm.overlay_close()

                break

            if self.focusedProcess != "cs2.exe":
                pm.end_drawing()

                time.sleep(1)

                continue

            viewMatrix = pm.r_floats(self.proc, self.mod + Offsets.dwViewMatrix, 16)

            pm.begin_drawing()
            for ent in self.getEntities():
                if ent.wts(viewMatrix):
                    if self.config["esp"]["onlyEnnemies"] and self.localTeam == ent.team:
                        continue

                    if ent.health == 0:
                        continue

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
                            0.1,
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
                            0.1,
                            1,
                            self.espBackGroundColor,
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

                            pm.draw_circle_lines(ent.headPos2d["x"], ent.headPos2d["y"], center / 3, whiteColor)
                            pm.draw_line(cou["x"], cou["y"], ent.headPos2d["x"], ent.headPos2d["y"], whiteColor, 1)
                            pm.draw_line(cou["x"], cou["y"], shoulderR["x"], shoulderR["y"], whiteColor, 1)
                            pm.draw_line(cou["x"], cou["y"], shoulderL["x"], shoulderL["y"], whiteColor, 1)
                            pm.draw_line(brasL["x"], brasL["y"], shoulderL["x"], shoulderL["y"], whiteColor, 1)
                            pm.draw_line(brasR["x"], brasR["y"], shoulderR["x"], shoulderR["y"], whiteColor, 1)
                            pm.draw_line(brasR["x"], brasR["y"], handR["x"], handR["y"], whiteColor, 1)
                            pm.draw_line(brasL["x"], brasL["y"], handL["x"], handL["y"], whiteColor, 1)
                            pm.draw_line(cou["x"], cou["y"], waist["x"], waist["y"], whiteColor, 1)
                            pm.draw_line(kneesR["x"], kneesR["y"], waist["x"], waist["y"], whiteColor, 1)
                            pm.draw_line(kneesL["x"], kneesL["y"], waist["x"], waist["y"], whiteColor, 1)
                            pm.draw_line(kneesL["x"], kneesL["y"], feetL["x"], feetL["y"], whiteColor, 1)
                            pm.draw_line(kneesR["x"], kneesR["y"], feetR["x"], feetR["y"], whiteColor, 1)
                        except:
                            pass

                    if self.config["esp"]["snapline"]:
                        width = pm.get_screen_width()
                        height = pm.get_screen_height()

                        pm.draw_line(
                            width / 2,
                            height,
                            ent.headPos2d["x"],
                            ent.headPos2d["y"],
                            self.espColor,
                        )

                    if self.config["esp"]["health"]:
                        pm.draw_circle_sector(
                            xStart,
                            ent.pos2d["y"] - center / 2,
                            center / 3 + 2,
                            0,
                            360,
                            0,
                            blackColor,
                        )

                        pm.draw_circle_sector(
                            xStart,
                            ent.pos2d["y"] - center / 2,
                            center / 3,
                            0,
                            360 / 100 * ent.health,
                            0,
                            self.espColor,
                        )

                    if self.config["esp"]["name"]:
                        pm.draw_text(
                            ent.name,
                            ent.headPos2d["x"] - pm.measure_text(ent.name, 7) // 2,
                            ent.headPos2d["y"] - center / 2,
                            7,
                            whiteColor,
                        )

            pm.end_drawing()

    def triggerBot(self):
        while not hasattr(self, "focusedProcess"):
            time.sleep(0.1)

        while True:
            time.sleep(0.001)

            if not self.config["triggerBot"]["enabled"]:
                break

            if win32api.GetAsyncKeyState(self.config["triggerBot"]["bind"]) == 0:
                continue

            if self.focusedProcess != "cs2.exe":
                time.sleep(1)

                continue

            player = pm.r_int64(self.proc, self.mod + Offsets.dwLocalPlayerPawn)
            entityId = pm.r_int(self.proc, player + Offsets.m_iIDEntIndex)

            if entityId > 0:
                entList = pm.r_int64(self.proc, self.mod + Offsets.dwEntityList)
                entEntry = pm.r_int64(self.proc, entList + 0x8 * (entityId >> 9) + 0x10)
                entity = pm.r_int64(self.proc, entEntry + 120 * (entityId & 0x1FF))

                entityTeam = pm.r_int(self.proc, entity + Offsets.m_iTeamNum)
                playerTeam = pm.r_int(self.proc, player + Offsets.m_iTeamNum)


                if self.config["triggerBot"]["onlyEnnemies"] and playerTeam == entityTeam:
                    continue

                entityHp = pm.r_int(self.proc, entity + Offsets.m_iHealth)

                if entityHp > 0:
                    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0)
                    time.sleep(0.02)
                    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0)

    def bhop(self):
        while not hasattr(self, "focusedProcess"):
            time.sleep(0.1)
        
        while True:
            if not self.config["misc"]["bhop"]["enabled"]:
                break

            if self.focusedProcess != "cs2.exe":
                time.sleep(1)

                continue

            if win32api.GetAsyncKeyState(0x20) == 0:
                continue

            player = pm.r_int64(self.proc, self.mod + Offsets.dwLocalPlayerPawn)
            flag = pm.r_int(self.proc, player + Offsets.m_fFlags)
            
            if flag & (1 << 0):
                time.sleep(0.015625)

                pm.w_int(self.proc, self.mod + Offsets.dwForceJump, 65537)
            else:
                pm.w_int(self.proc, self.mod + Offsets.dwForceJump, 256)

if __name__ == "__main__":
    if os.name != "nt":
        input("NameIt is only working on Windows.")

        os._exit(0)

    nameItClass = NameIt()

    uiWidth = 800
    uiHeight = 500

    dpg.create_context()

    def toggleEsp(id, value):
        nameItClass.config["esp"]["enabled"] = value

        if value:
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

    def toggleEspSnapline(id, value):
        nameItClass.config["esp"]["snapline"] = value

    def toggleEspOnlyEnnemies(id, value):
        nameItClass.config["esp"]["onlyEnnemies"] = value

    def toggleEspName(id, value):
        nameItClass.config["esp"]["name"] = value

    def toggleEspHealth(id, value):
        nameItClass.config["esp"]["health"] = value

    def setEspColor(id, value):
        nameItClass.config["esp"]["color"] = {"r": value[0], "g": value[1], "b": value[2], "a": value[3]}

        nameItClass.espColor = pm.new_color_float(value[0], value[1], value[2], value[3])
        nameItClass.espBackGroundColor = pm.fade_color(nameItClass.espColor, 0.3)

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

    def toggleTriggerBotOnlyEnnemies(id, value):
        nameItClass.config["triggerBot"]["onlyEnnemies"] = value

    def toggleBunnyHop(id, value):
        nameItClass.config["misc"]["bhop"]["enabled"] = value       

        if value:
            threading.Thread(target=nameItClass.bhop, daemon=True).start()    

    def toggleSaveSettings(id, value):
        nameItClass.config["settings"]["saveSettings"] = value

    def toggleAlwaysOnTop(id, value):
        guiWindows = win32gui.GetForegroundWindow()

        if value:
            win32gui.SetWindowPos(guiWindows, win32con.HWND_TOPMOST, 0, 0, 0, 0, win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
        else:
            win32gui.SetWindowPos(guiWindows, win32con.HWND_NOTOPMOST, 0, 0, 0, 0, win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)

    with dpg.window(label=f"[v{version}] NameIt", width=uiWidth, height=uiHeight, no_collapse=True, no_move=True, no_resize=True, on_close=dpg.destroy_context) as window:
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

                checkboxEspSkeleton= dpg.add_checkbox(label="Skeleton", default_value=nameItClass.config["esp"]["skeleton"], callback=toggleEspSkeleton)
                checkboxEspSnapline= dpg.add_checkbox(label="Snapline", default_value=nameItClass.config["esp"]["snapline"], callback=toggleEspSnapline)
                checkboxEspOnlyEnnemies = dpg.add_checkbox(label="Only Ennemies", default_value=nameItClass.config["esp"]["onlyEnnemies"], callback=toggleEspOnlyEnnemies)
                checkboxEspName = dpg.add_checkbox(label="Show Name", default_value=nameItClass.config["esp"]["name"], callback=toggleEspName)
                checkboxEspHealth = dpg.add_checkbox(label="Show Health", default_value=nameItClass.config["esp"]["health"], callback=toggleEspHealth)

                dpg.add_spacer(width=75)
                dpg.add_separator()
                dpg.add_spacer(width=75)

                colorPickerEsp = dpg.add_color_picker(label="Color", default_value=(nameItClass.config["esp"]["color"]["r"]*255, nameItClass.config["esp"]["color"]["g"]*255, nameItClass.config["esp"]["color"]["b"]*255, nameItClass.config["esp"]["color"]["a"]*255), width=150, no_inputs=True, callback=setEspColor)
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

                checkboxTriggerBotOnlyEnnemies = dpg.add_checkbox(label="Only Ennemies", default_value=nameItClass.config["triggerBot"]["onlyEnnemies"], callback=toggleTriggerBotOnlyEnnemies)
            with dpg.tab(label="Misc"):
                dpg.add_spacer(width=75)

                with dpg.group(horizontal=True):
                    checkboxBhop = dpg.add_checkbox(label="BunnyHop", default_value=nameItClass.config["misc"]["bhop"]["enabled"], callback=toggleBunnyHop)
                    dpg.add_text(default_value="| Hold space!")
            with dpg.tab(label="Settings"):
                dpg.add_spacer(width=75)

                checkboxSaveSettings = dpg.add_checkbox(label="Save Settings", default_value=nameItClass.config["settings"]["saveSettings"], callback=toggleSaveSettings)

                dpg.add_spacer(width=75)

                checkboxAlwaysOnTop = dpg.add_checkbox(label="Always On Top", callback=toggleAlwaysOnTop)

                dpg.add_spacer(width=75)
                dpg.add_separator()
                dpg.add_spacer(width=75)

                creditsText = dpg.add_text(default_value="Credits: Goldy and PyMeow Community")
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

    dpg.create_viewport(title=f"[v{version}] NameIt", width=uiWidth, height=uiHeight, decorated=False, resizable=False)
    dpg.show_viewport()
    dpg.setup_dearpygui()
    dpg.start_dearpygui()