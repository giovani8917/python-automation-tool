import logging
import queue
import random
import threading
import time
from datetime import datetime

import pyautogui
from pynput import keyboard, mouse

from .models import DemoItem, WildcardItem
from .utils import check_battery_level, check_internet_connection, parse_fecha

logger = logging.getLogger("main.engine")

# Configure pyautogui
# Configure pyautogui
pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0.01


class AutomationEngine:
    def __init__(self, callback_queue=None):
        self.recording = False
        self.replaying = False
        self.paused = False
        self.stop_flag = False

        self.current_recording = []
        self.start_time = None
        self.last_move_time = 0

        self.listener_mouse = None
        self.listener_keyboard = None
        self.global_listener = None

        self.callback_queue = callback_queue or queue.Queue()

        # Modifiers
        self.active_modifiers = set()
        self.MODS = {
            "ctrl_l",
            "ctrl_r",
            "ctrl",
            "alt_l",
            "alt_r",
            "alt",
            "shift",
            "shift_r",
            "shift_l",
            "win",
            "windows",
        }

    def emit_status(self, message):
        """Puts a status update in the queue for the UI."""
        if self.callback_queue:
            self.callback_queue.put(("status", message))

    def emit_log(self, message, level="info"):
        """Puts a log message in the queue."""
        if self.callback_queue:
            self.callback_queue.put(("log", level, message))

    # --- RECORDING ---
    def start_recording(self):
        self.current_recording = []
        self.recording = True
        self.start_time = time.time()
        self.active_modifiers.clear()

        self.listener_mouse = mouse.Listener(on_move=self._on_move, on_click=self._on_click)
        self.listener_keyboard = keyboard.Listener(
            on_press=self._on_press, on_release=self._on_release
        )
        self.listener_mouse.start()
        self.listener_keyboard.start()

        self.emit_log("Grabación iniciada (Motor V9)")

    def stop_recording(self, remove_last_seconds=0):
        self.recording = False
        if self.listener_mouse:
            self.listener_mouse.stop()
        if self.listener_keyboard:
            self.listener_keyboard.stop()
        self.emit_status("Grabación detenida")

        # Truncate logic (V9 feature ported to Modular)
        final_data = self.current_recording
        if remove_last_seconds > 0 and final_data:
            try:
                max_t = final_data[-1][0]
                cutoff = max_t - remove_last_seconds
                final_data = [e for e in final_data if e[0] <= cutoff]
                self.emit_log(f"Recortados últimos {remove_last_seconds}s")
            except:
                pass

        # Notify UI of finish
        if self.callback_queue:
            # Calculate stats
            moves = len([e for e in final_data if e[1] == "move"])
            clicks = len([e for e in final_data if e[1] == "click"])
            self.callback_queue.put(("recording_finished", final_data))
            self.emit_log(
                f"Fin Grabación: {len(final_data)} eventos ({moves} moves, {clicks} clicks)"
            )

    def _on_move(self, x, y):
        if self.recording:
            t = time.time()
            # Standard V9 logic: No throttle (or very minimal)
            # if t - self.last_move_time < 0.01: return

            self.last_move_time = t
            t_rel = t - self.start_time
            self.current_recording.append((t_rel, "move", x, y, None, None))

    def _on_click(self, x, y, button, pressed):
        if self.recording:
            t = time.time()
            t_rel = t - self.start_time
            btn_name = button.name if hasattr(button, "name") else str(button)
            self.current_recording.append((t_rel, "click", x, y, btn_name, pressed))

            if pressed:
                self.current_recording.append((t_rel + 0.001, "exact_pos", x, y, None, None))

    def _on_press(self, key):
        if self.recording:
            t = time.time() - self.start_time
            try:
                key_name = key.char if hasattr(key, "char") and key.char else str(key)
            except AttributeError:
                key_name = str(key)

            key_norm = key_name.lower().replace("key.", "")

            if key_norm in self.MODS:
                self.active_modifiers.add(key_norm)
                self.current_recording.append((t, "mod_press", None, None, key_norm, True))
                return

            if self.active_modifiers:
                combo = list(sorted(self.active_modifiers)) + [key_norm]
                self.current_recording.append((t, "hotkey", None, None, combo, True))
            else:
                self.current_recording.append((t, "key_press", None, None, key_norm, True))

    def _on_release(self, key):
        if self.recording:
            t = time.time() - self.start_time
            try:
                key_name = key.char if hasattr(key, "char") and key.char else str(key)
            except AttributeError:
                key_name = str(key)
            key_norm = key_name.lower().replace("key.", "")

            if key_norm in self.MODS:
                self.active_modifiers.discard(key_norm)
                self.current_recording.append((t, "mod_release", None, None, key_norm, False))
            else:
                self.current_recording.append((t, "key_release", None, None, key_norm, False))

    # --- PLAYBACK ---
    def start_replay(self, sequence, speed_factor=1.0, infinite=False, repeat_times=1):
        if self.replaying:
            return
        self.replaying = True
        self.stop_flag = False
        self.paused = False

        # Run in thread
        threading.Thread(
            target=self._replay_loop, args=(sequence, speed_factor, infinite, repeat_times)
        ).start()

    def stop_replay(self):
        self.stop_flag = True
        self.emit_status("Deteniendo reproducción...")

    def toggle_pause(self):
        self.paused = not self.paused
        state = "Pausado" if self.paused else "Reanudando"
        self.emit_status(state)

    def _replay_loop(self, sequence, speed_factor, infinite, repeat_times):
        try:
            iteration = 1
            while not self.stop_flag:
                if not infinite and iteration > repeat_times:
                    break

                if infinite or repeat_times > 1:
                    self.emit_status(f"Iteración {iteration}")

                for i, item in enumerate(sequence):
                    if self.stop_flag:
                        break
                    self._process_item(item, speed_factor)

                iteration += 1

            self.emit_status("Reproducción finalizada")
            if self.callback_queue:
                self.callback_queue.put(("finished",))

        except Exception as e:
            logger.error(f"Error in replay loop: {e}", exc_info=True)
            self.emit_status(f"Error: {str(e)}")
        finally:
            self.replaying = False

    def _process_item(self, item, speed_factor):
        if isinstance(item, DemoItem):
            self.emit_status(f"Reproduciendo: {item.name}")
            self._replay_demo_events(item.data, speed_factor)
        elif isinstance(item, WildcardItem):
            self._process_wildcard(item, speed_factor)

    def _process_wildcard(self, item, speed_factor):
        # ... logic mainly same as provided models ...
        if item.type == "wildcard":
            wait_time = random.uniform(item.min_time, item.max_time) / speed_factor
            self._wait_interruptible(wait_time, f"Esperando {wait_time:.1f}s ({item.name})")
        elif item.type == "internet_wait":
            self.emit_status("Esperando internet...")
            while not check_internet_connection():
                if self.stop_flag:
                    return
                time.sleep(1)
        elif item.type == "battery_wait":
            threshold = item.threshold or 20
            self.emit_status(f"Esperando batería > {threshold}%")
            while not check_battery_level(threshold):
                if self.stop_flag:
                    return
                time.sleep(5)

        elif item.type == "date_start":
            if item.datetime_target:
                try:
                    target = parse_fecha(item.datetime_target)
                    while datetime.now() < target:
                        if self.stop_flag:
                            return
                        self.emit_status(f"Esperando inicio: {item.datetime_target}")
                        time.sleep(1)
                except ValueError:
                    logger.error(f"Invalid date format: {item.datetime_target}")

        elif item.type == "date_end":
            if item.datetime_target:
                try:
                    target = parse_fecha(item.datetime_target)
                    if datetime.now() >= target:
                        self.emit_status(f"Fecha fin alcanzada: {item.datetime_target}")
                        self.stop_replay()
                except ValueError:
                    logger.error(f"Invalid date format: {item.datetime_target}")

    def _wait_interruptible(self, duration, status_msg):
        self.emit_status(status_msg)
        start = time.time()
        while time.time() - start < duration:
            if self.stop_flag:
                return
            while self.paused:
                time.sleep(0.1)
                if self.stop_flag:
                    return
            time.sleep(0.1)

    def _precise_click_and_drag(self, x, y, button, speed_factor=1.0):
        # V9 Logic exact
        pyautogui.moveTo(x, y, duration=0.1 / speed_factor)
        time.sleep(0.2 / speed_factor)
        pyautogui.mouseDown(x=x, y=y, button=button)
        time.sleep(0.05 / speed_factor)

    def _replay_demo_events(self, data, speed_factor):
        last_event_time = 0
        dragging = False
        current_button = None
        drag_start_position = None

        for i, event in enumerate(data):
            if self.stop_flag:
                break
            while self.paused:
                time.sleep(0.1)
                if self.stop_flag:
                    break

            t, event_type, x, y, button_or_key, pressed = event

            delay = t - last_event_time if i > 0 else 0
            adjusted_delay = delay / speed_factor

            if adjusted_delay > 0:
                # Interruptible sleep
                end_time = time.time() + adjusted_delay
                while time.time() < end_time:
                    if self.stop_flag:
                        break
                    time.sleep(min(0.05, end_time - time.time()))
                if self.stop_flag:
                    break

            last_event_time = t

            if event_type == "move":
                current_x, current_y = int(x), int(y)
                duration = 0.01 / speed_factor  # Default V9 movement

                if dragging:
                    if drag_start_position:
                        dist = (
                            (current_x - drag_start_position[0]) ** 2
                            + (current_y - drag_start_position[1]) ** 2
                        ) ** 0.5
                        if dist < 20:
                            duration = 0.01 / speed_factor
                        else:
                            duration = 0.005 / speed_factor
                    else:
                        duration = 0.005 / speed_factor
                else:
                    duration = 0.01 / speed_factor

                # Safe Move
                try:
                    pyautogui.moveTo(current_x, current_y, duration=duration)
                except Exception:
                    pyautogui.moveTo(current_x, current_y, duration=0)

            elif event_type == "click":
                button = self._convert_button(button_or_key)
                if pressed:
                    drag_start_position = (int(x), int(y))
                    self._precise_click_and_drag(int(x), int(y), button, speed_factor)
                    dragging = True
                    current_button = button
                else:
                    if dragging and current_button:
                        pyautogui.moveTo(int(x), int(y), duration=0.05 / speed_factor)
                        pyautogui.mouseUp(button=current_button)
                        dragging = False
                        current_button = None
                        drag_start_position = None

            elif event_type == "key_press":
                key = self._convert_key(button_or_key)
                if key:
                    pyautogui.keyDown(key)

            elif event_type == "key_release":
                key = self._convert_key(button_or_key)
                if key:
                    pyautogui.keyUp(key)

            elif event_type == "hotkey":
                # Handle hotkeys via keyboard module
                try:
                    import keyboard

                    keys = []
                    for k in button_or_key:
                        # V9 Logic: Handle control characters
                        if isinstance(k, str) and len(k) == 1 and ord(k) < 32:
                            # '\x03' -> 'c', etc.
                            letra = chr(ord(k) + 96)
                            keys.append(letra)
                        else:
                            keys.append(self._convert_key(k))

                    combo = "+".join(keys)
                    keyboard.send(combo)
                    time.sleep(0.08)
                except Exception:
                    pass

            elif event_type == "exact_pos":
                pass

        if dragging and current_button:
            pyautogui.mouseUp(button=current_button)

    def _convert_button(self, name):
        mapping = {"Button.left": "left", "Button.right": "right", "Button.middle": "middle"}
        return mapping.get(name, name)

    def _convert_key(self, key_name):
        # Full V9 Key Mapping
        special_keys = {
            "Key.shift": "shift",
            "Key.ctrl": "ctrl",
            "Key.alt": "alt",
            "Key.enter": "enter",
            "Key.esc": "esc",
            "Key.tab": "tab",
            "Key.space": "space",
            "Key.backspace": "backspace",
            "Key.up": "up",
            "Key.down": "down",
            "Key.left": "left",
            "Key.right": "right",
            "Key.page_up": "pageup",
            "Key.page_down": "pagedown",
            "Key.home": "home",
            "Key.end": "end",
            "Key.cmd": "command",
            "Key.cmd_r": "command",
            "Key.insert": "insert",
            "Key.delete": "delete",
            "Key.print_screen": "printscreen",
            "Key.f1": "f1",
            "Key.f2": "f2",
            "Key.f3": "f3",
            "Key.f4": "f4",
            "Key.f5": "f5",
            "Key.f6": "f6",
            "Key.f7": "f7",
            "Key.f8": "f8",
            "Key.f9": "f9",
            "Key.f10": "f10",
            "Key.f11": "f11",
            "Key.f12": "f12",
            # Mappings for common modifier strings from pynput
            "ctrl_l": "ctrl",
            "ctrl_r": "ctrl",  # V9 maps both to 'ctrl'
            "alt_l": "alt",
            "alt_r": "alt",
            "shift_l": "shift",
            "shift_r": "shift",
            "win": "windows",
        }

        s = str(key_name)
        if s in special_keys:
            return special_keys[s]

        if s.startswith("'") and s.endswith("'"):
            s = s[1:-1]

        return special_keys.get(s, s)

    # --- Global Keys ---
    def start_global_listener(self):
        """Starts global hotkeys (Ctrl+Shift+P, etc)"""
        if not self.global_listener:
            try:
                self.global_listener = keyboard.GlobalHotKeys(
                    {"<ctrl>+<shift>+p": self.toggle_pause, "<ctrl>+<shift>+d": self.stop_recording}
                )
                self.global_listener.start()
            except Exception as e:
                logger.error(f"Failed to start global listener: {e}")

    def stop_global_listener(self):
        if self.global_listener:
            self.global_listener.stop()
            self.global_listener = None
