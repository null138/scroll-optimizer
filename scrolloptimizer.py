import ctypes
from ctypes import wintypes
import atexit
import threading
import time
import queue
import tkinter as tk

user32 = ctypes.windll.user32
winmm = ctypes.WinDLL('winmm')
scroll_queue = queue.Queue()
enabled = True
tick_interval_ms = 30
winmm.timeBeginPeriod(1)

class MSLLHOOKSTRUCT(ctypes.Structure):
	_fields_ = [("pt", wintypes.POINT), ("mouseData", wintypes.DWORD), ("flags", wintypes.DWORD), ("time", wintypes.DWORD), ("dwExtraInfo", ctypes.c_void_p)]

class MOUSEINPUT(ctypes.Structure):
	_fields_ = [("dx", wintypes.LONG), ("dy", wintypes.LONG), ("mouseData", wintypes.DWORD), ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD), ("dwExtraInfo", ctypes.c_void_p)]

class INPUT(ctypes.Structure):
	class _INPUT(ctypes.Union):
		_fields_ = [("mi", MOUSEINPUT)]
	_anonymous_ = ("_input",)
	_fields_ = [("type", wintypes.DWORD), ("_input", _INPUT)]

def send_scroll(delta, horizontal=False):
	flags = 0x01000 if horizontal else 0x0800
	mi = MOUSEINPUT(dx=0, dy=0, mouseData=delta & 0xFFFFFFFF, dwFlags=flags, time=0, dwExtraInfo=None)
	inp = INPUT(type=0, mi=mi)
	user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))

def scroll_worker():
	global tick_interval_ms
	next_tick = time.perf_counter()
	while True:
		interval_sec = tick_interval_ms / 1000.0
		next_tick += interval_sec
		while True:
			now = time.perf_counter()
			if now >= next_tick:
				break
			remaining = next_tick - now
			if remaining > 0.002:
				time.sleep(remaining - 0.001)
		if enabled and not scroll_queue.empty():
			delta, horizontal = scroll_queue.get()
			send_scroll(delta, horizontal)

threading.Thread(target=scroll_worker, daemon=True).start()

LowLevelMouseProc = ctypes.WINFUNCTYPE(ctypes.c_int, ctypes.c_int, wintypes.WPARAM, ctypes.POINTER(MSLLHOOKSTRUCT))

def hook_proc(nCode, wParam, lParam):
	if nCode == 0:
		event = lParam.contents
		if event.flags & (0x00000001 | 0x00000002):
			return user32.CallNextHookEx(None, nCode, wParam, ctypes.cast(lParam, ctypes.c_void_p))
		if wParam in (0x020A, 0x020E):
			delta = ctypes.c_short(event.mouseData >> 16).value
			horizontal = (wParam == 0x020E)
			if enabled:
				scroll_queue.put((delta, horizontal))
				return 1
	return user32.CallNextHookEx(None, nCode, wParam, ctypes.cast(lParam, ctypes.c_void_p))

hook_pointer = LowLevelMouseProc(hook_proc)
hook = user32.SetWindowsHookExW(14, hook_pointer, 0, 0)
if not hook:
	raise ctypes.WinError()

atexit.register(lambda: [user32.UnhookWindowsHookEx(hook), winmm.timeEndPeriod(1)])

def toggle_enabled():
	global enabled
	enabled = enable_var.get()

def update_interval(val):
	global tick_interval_ms
	tick_interval_ms = int(float(val))
	interval_label.config(text=f"{tick_interval_ms} ms")

root = tk.Tk()
root.title("Scroll Optimizer")
root.geometry("300x160")
root.resizable(False, False)
root.configure(bg="#414141")

frame = tk.Frame(root, bg="#414141")
frame.pack(expand=True, fill="both", padx=20, pady=30)

enable_var = tk.BooleanVar(value=True)
enable_check = tk.Checkbutton(
	frame, text="Enable", variable=enable_var,
	command=toggle_enabled,
	bg="#414141", fg="#888888",
	selectcolor="#414141",
	activebackground="#414141", activeforeground="#888888"
)
enable_check.pack(pady=(0, 5))

interval_label = tk.Label(frame, text=f"{tick_interval_ms} ms", fg="white", bg="#414141")
interval_label.pack()

slider_length = 220
slider = tk.Scale(
	frame, from_=1, to=80, orient="horizontal",
	command=lambda val: update_interval(val),
	bg="#414141", fg="white",
	troughcolor="#555555", highlightthickness=0,
	length=slider_length,
	showvalue=False
)
slider.set(tick_interval_ms)
slider.pack(pady=5)

marker_canvas = tk.Canvas(frame, width=slider_length, height=12, bg="#414141", highlightthickness=0)
marker_canvas.place(x=46, y=79)
marker_pos = int((30 - 15) / (80 - 15) * (slider_length - 30) + 16)
marker_canvas.create_line(marker_pos, 0, marker_pos, 12, fill="#E25822", width=2)

# respect the author...
author = tk.Label(root, text="~by Madness (null138)", fg="#00C6C6", bg="#414141", font=("Segoe UI", 8))
author.place(x=5, y=5)

def message_loop():
	msg = wintypes.MSG()
	while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
		user32.TranslateMessage(ctypes.byref(msg))
		user32.DispatchMessageW(ctypes.byref(msg))

threading.Thread(target=message_loop, daemon=True).start()

root.mainloop()