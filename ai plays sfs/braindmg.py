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


CHAOS_LEVEL = 0.5
LOOP_DELAY = 0.25


pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.05




def screenshot_b64():
    img = pyautogui.screenshot()
    img = img.resize((SCREEN_W, SCREEN_H))
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("utf-8")




def scale(x, y):
    real_w, real_h = pyautogui.size()
    return int(x / SCREEN_W * real_w), int(y / SCREEN_H * real_h)




def random_action():
    action = random.choices(
        ["click", "drag", "press", "wait"],
        weights=[1, 8, 1, 1],
        k=1
    )[0]


    if action == "drag":
        return {
            "action": "drag",
            "x": random.randint(25, 70),
            "y": random.randint(90, 480),
            "x2": random.randint(300, 700),
            "y2": random.randint(150, 420),
            "duration": random.uniform(0.4, 1.0),
            "reason": "drag part from menu to build grid"
        }


    if action == "click":
        return {
            "action": "click",
            "x": random.randint(20, 940),
            "y": random.randint(40, 500),
            "reason": "random click"
        }


    if action == "press":
        return {
            "action": "press",
            "key": random.choice(["space", "w", "a", "s", "d", "up", "down", "left", "right"]),
            "reason": "keyboard panic"
        }


    return {
        "action": "wait",
        "duration": random.uniform(0.1, 0.5),
        "reason": "thinking poorly"
    }




def ask_gemma(image_b64):
    print("Asking Gemma...")


    prompt = """
You are controlling Spaceflight Simulator.


Important:
To build a rocket, drag parts from the LEFT vertical parts bar into the CENTER grid.
Do not just click the parts.
Use drag actions often.


Goal:
Build a messy rocket and launch it.


Return ONLY JSON:


{
  "action": "drag",
  "x": 45,
  "y": 250,
  "x2": 480,
  "y2": 270,
  "key": "space",
  "duration": 0.7,
  "reason": "drag fuel tank to grid"
}


Valid actions: click, drag, press, wait.
Coordinates are based on 960x540 screenshot.
"""


    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "images": [image_b64],
        "stream": False
    }


    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=8)
        response.raise_for_status()
        text = response.json()["response"].strip()


        start = text.find("{")
        end = text.rfind("}") + 1


        if start == -1 or end <= start:
            raise ValueError("No JSON found")


        return json.loads(text[start:end])


    except Exception as e:
        print("Gemma failed, chaos mode:", e)
        return random_action()




def sanitize(cmd):
    if not isinstance(cmd, dict):
        return random_action()


    action = cmd.get("action", "wait")


    if action not in ["click", "drag", "press", "wait"]:
        return random_action()


    for key in ["x", "y", "x2", "y2"]:
        if key in cmd:
            cmd[key] = int(cmd[key])


    if "duration" in cmd:
        cmd["duration"] = max(0.05, min(float(cmd["duration"]), 2.0))


    return cmd




def do_action(cmd):
    cmd = sanitize(cmd)
    print("ACTION:", cmd)


    action = cmd["action"]


    if action == "click":
        x, y = scale(cmd.get("x", 480), cmd.get("y", 270))
        pyautogui.click(x, y)


    elif action == "drag":
        x, y = scale(cmd.get("x", 45), cmd.get("y", 250))
        x2, y2 = scale(cmd.get("x2", 480), cmd.get("y2", 270))


        pyautogui.moveTo(x, y, duration=0.1)
        pyautogui.mouseDown()
        time.sleep(0.15)
        pyautogui.moveTo(x2, y2, duration=cmd.get("duration", 0.7))
        time.sleep(0.1)
        pyautogui.mouseUp()


    elif action == "press":
        pyautogui.press(cmd.get("key", "space"))


    elif action == "wait":
        time.sleep(cmd.get("duration", 0.3))




def autopilot_action():
    if random.random() < CHAOS_LEVEL:
        return random_action()


    image = screenshot_b64()
    return ask_gemma(image)




def main():
    print("SFS BRAIN DAMAGE AUTOPILOT ONLINE")
    print("Chaos level:", CHAOS_LEVEL)
    print("Open SFS build screen now.")
    print("Emergency stop: mouse to TOP LEFT.")
    time.sleep(5)


    while True:
        cmd = autopilot_action()
        do_action(cmd)
        time.sleep(LOOP_DELAY)




if __name__ == "__main__":
    main()