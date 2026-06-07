import pyautogui
import time
import random
import json
import base64
import requests
from io import BytesIO


OLLAMA_MODEL = "gemma3:4b"
OLLAMA_URL = "http://localhost:11434/api/generate"


SCREEN_W = 960
SCREEN_H = 540


CHAOS_LEVEL = 0.1
LOOP_DELAY = 0.4


pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.05


bot_mode = "build"
build_steps_done = 0




def screenshot_b64():
    img = pyautogui.screenshot()
    img = img.resize((SCREEN_W, SCREEN_H))


    buffer = BytesIO()
    img.save(buffer, format="PNG")


    return base64.b64encode(buffer.getvalue()).decode("utf-8")




def scale(x, y):
    real_w, real_h = pyautogui.size()
    return int(x / SCREEN_W * real_w), int(y / SCREEN_H * real_h)




def drag(x, y, x2, y2, duration=0.6):
    x, y = scale(x, y)
    x2, y2 = scale(x2, y2)


    pyautogui.moveTo(x, y, duration=0.1)
    pyautogui.mouseDown()
    time.sleep(0.15)
    pyautogui.moveTo(x2, y2, duration=duration)
    time.sleep(0.1)
    pyautogui.mouseUp()




def click(x, y):
    x, y = scale(x, y)
    pyautogui.click(x, y)




def basic_build_action():
    global build_steps_done, bot_mode


    # These are rough SFS part-bar positions.
    # Adjust Y values if your menu is different.
    build_plan = [
        # nose cone to top
        {"x": 45, "y": 110, "x2": 480, "y2": 170, "reason": "place nose cone"},


        # fuel tanks stacked
        {"x": 45, "y": 230, "x2": 480, "y2": 230, "reason": "place fuel tank"},
        {"x": 45, "y": 260, "x2": 480, "y2": 285, "reason": "place fuel tank"},
        {"x": 45, "y": 290, "x2": 480, "y2": 340, "reason": "place fuel tank"},


        # engine at bottom
        {"x": 45, "y": 420, "x2": 480, "y2": 405, "reason": "place engine"},
    ]


    if build_steps_done < len(build_plan):
        step = build_plan[build_steps_done]
        build_steps_done += 1


        return {
            "action": "drag",
            "x": step["x"],
            "y": step["y"],
            "x2": step["x2"],
            "y2": step["y2"],
            "duration": 0.7,
            "reason": step["reason"]
        }


    # After building, try clicking launch/new/save area depending SFS UI.
    bot_mode = "launch"


    return {
        "action": "click",
        "x": 890,
        "y": 45,
        "reason": "try launch or top-right button"
    }




def chaos_action():
    # Still chaotic, but smarter than old chaos.
    if bot_mode == "build":
        return {
            "action": "drag",
            "x": random.randint(30, 65),
            "y": random.choice([110, 180, 230, 280, 340, 410]),
            "x2": random.randint(430, 530),
            "y2": random.randint(150, 420),
            "duration": random.uniform(0.4, 0.9),
            "reason": "chaos build drag"
        }


    if bot_mode == "launch":
        return {
            "action": "click",
            "x": random.randint(800, 940),
            "y": random.randint(30, 90),
            "reason": "chaos launch click"
        }


    return {
        "action": "press",
        "key": random.choice(["space", "w", "up", "left", "right", "shift"]),
        "reason": "chaos flight control"
    }




def ask_gemma(image_b64):
    prompt = f"""
You are controlling Spaceflight Simulator.


Current bot mode: {bot_mode}


Your goal:
1. If on build screen, build a simple rocket.
2. A simple rocket is: nose cone on top, fuel tanks in middle, engine on bottom.
3. If rocket is built, launch it.
4. If flying, throttle up, stage, and try to keep rocket going upward.


Important SFS controls:
- Drag parts from the LEFT vertical parts bar to the CENTER grid.
- Do not only click parts.
- Use drag when building.
- Use click for launch/menu buttons.
- Use press for flight keys.
- Use space to stage.
- Use w or up for throttle/control if useful.


Return ONLY valid JSON.


Format:
{{
  "action": "click" | "drag" | "press" | "wait",
  "x": 100,
  "y": 200,
  "x2": 300,
  "y2": 400,
  "key": "space",
  "duration": 0.5,
  "reason": "short reason"
}}


Coordinates are based on 960x540 screenshot.
Only choose ONE action.
"""


    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "images": [image_b64],
        "stream": False
    }


    try:
        print("Asking Gemma...")
        response = requests.post(OLLAMA_URL, json=payload, timeout=10)
        response.raise_for_status()


        text = response.json()["response"].strip()


        start = text.find("{")
        end = text.rfind("}") + 1


        if start == -1 or end <= start:
            raise ValueError("No JSON found")


        return json.loads(text[start:end])


    except Exception as e:
        print("Gemma failed:", e)
        return chaos_action()




def sanitize(cmd):
    if not isinstance(cmd, dict):
        return chaos_action()


    action = cmd.get("action", "wait")


    if action not in ["click", "drag", "press", "wait"]:
        return chaos_action()


    for key in ["x", "y", "x2", "y2"]:
        if key in cmd:
            try:
                max_value = SCREEN_W if "x" in key else SCREEN_H
                cmd[key] = max(0, min(int(cmd[key]), max_value))
            except:
                cmd[key] = 480 if "x" in key else 270


    if "duration" in cmd:
        try:
            cmd["duration"] = max(0.05, min(float(cmd["duration"]), 2.0))
        except:
            cmd["duration"] = 0.5


    if action == "press":
        allowed = ["space", "w", "a", "s", "d", "up", "down", "left", "right", "shift", "ctrl"]
        if cmd.get("key") not in allowed:
            cmd["key"] = "space"


    return cmd




def do_action(cmd):
    cmd = sanitize(cmd)
    print("ACTION:", cmd)


    action = cmd["action"]


    if action == "click":
        click(cmd.get("x", 480), cmd.get("y", 270))


    elif action == "drag":
        drag(
            cmd.get("x", 45),
            cmd.get("y", 250),
            cmd.get("x2", 480),
            cmd.get("y2", 270),
            cmd.get("duration", 0.6)
        )


    elif action == "press":
        pyautogui.press(cmd.get("key", "space"))


    elif action == "wait":
        time.sleep(cmd.get("duration", 0.5))




def autopilot_action():
    global bot_mode


    # First few moves are rule-based so it actually tries to build a rocket.
    if bot_mode == "build" and build_steps_done < 5:
        return basic_build_action()


    # 10% chaos
    if random.random() < CHAOS_LEVEL:
        return chaos_action()


    image = screenshot_b64()
    return ask_gemma(image)




def main():
    print("===================================")
    print(" SFS BRAIN DAMAGE AUTOPILOT v0.2 ")
    print("===================================")
    print("Model:", OLLAMA_MODEL)
    print("Chaos level:", CHAOS_LEVEL)
    print("Mode:", bot_mode)
    print()
    print("Open SFS build screen now.")
    print("You have 5 seconds.")
    print("Emergency stop: mouse to TOP LEFT.")
    print()


    time.sleep(5)


    while True:
        cmd = autopilot_action()
        do_action(cmd)
        time.sleep(LOOP_DELAY)




if __name__ == "__main__":
    main()
