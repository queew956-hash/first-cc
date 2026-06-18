#!/usr/bin/env python3
"""
🍅 番茄钟 - A beautiful desktop Pomodoro timer
Built with tkinter for native macOS experience
"""

import tkinter as tk
import math
import time
import subprocess
import threading
from enum import Enum


# ===== Configuration =====
WORK_TIME = 25 * 60        # 25 minutes
SHORT_BREAK = 5 * 60       # 5 minutes
LONG_BREAK = 15 * 60       # 15 minutes
LONG_BREAK_INTERVAL = 4    # Long break after 4 pomodoros


# ===== Color Theme =====
COLORS = {
    'bg': '#1a1a2e',
    'surface': '#16213e',
    'text': '#ffffff',
    'text_secondary': '#a0a0c0',
    'text_muted': '#7070a0',
    'work': '#ff6b6b',
    'work_glow': '#ee5a24',
    'short_break': '#4ecdc4',
    'long_break': '#45b7d1',
    'ring_bg': '#2d2d5e',
    'btn_bg': '#2d2d3e',
    'btn_border': '#2f2f42',
    'btn_hover': '#333348',
}


class TimerState(Enum):
    IDLE = 'idle'
    RUNNING = 'running'
    PAUSED = 'paused'


class PomodoroApp:
    def __init__(self):
        self.window = tk.Tk()
        self.window.title('番茄钟')
        self.window.geometry('420x560')
        self.window.configure(bg=COLORS['bg'])
        self.window.resizable(True, True)
        self.window.minsize(360, 500)

        # Center window
        self.window.update_idletasks()
        screen_w = self.window.winfo_screenwidth()
        screen_h = self.window.winfo_screenheight()
        x = (screen_w - 420) // 2
        y = (screen_h - 560) // 2
        self.window.geometry(f'420x560+{x}+{y}')

        # Always on top
        self.always_on_top = True
        self.window.attributes('-topmost', True)

        # Title bar style (macOS)
        try:
            self.window.tk.call(
                'tk::unsupported::MacWindowStyle', 'appearance', 'dark'
            )
        except Exception:
            pass

        # ===== State =====
        self.mode = 'work'
        self.timer_state = TimerState.IDLE
        self.remaining = WORK_TIME
        self.total_duration = WORK_TIME
        self.completed_pomodoros = 0
        self.after_id = None

        # ===== Build UI =====
        self._build_ui()
        self._update_display()

        # ===== Keyboard bindings =====
        self.window.bind('<space>', lambda e: self._toggle_timer())
        self.window.bind('<Key-r>', lambda e: self.reset_timer())
        self.window.bind('<Key-s>', lambda e: self.skip_to_next())
        self.window.bind('<Command-w>', lambda e: self.window.withdraw())

        # ===== Window close behavior =====
        self.window.protocol('WM_DELETE_WINDOW', self.window.withdraw)

    # ===== UI Construction =====

    def _build_ui(self):
        # Drag region (acts as spacer)
        tk.Frame(self.window, bg=COLORS['bg'], height=30).pack()

        # Title
        self.title_label = tk.Label(
            self.window,
            text='🍅 番茄钟',
            font=('SF Pro Display', 22, 'bold'),
            fg=COLORS['text'],
            bg=COLORS['bg'],
        )
        self.title_label.pack(pady=(0, 20))

        # Canvas for circular progress
        self.canvas_size = 240
        self.canvas = tk.Canvas(
            self.window,
            width=self.canvas_size,
            height=self.canvas_size,
            bg=COLORS['bg'],
            highlightthickness=0,
        )
        self.canvas.pack()

        # Draw ring elements
        self._draw_ring()

        # Mode label
        self.mode_label = tk.Label(
            self.window,
            text='准备开始',
            font=('SF Pro Display', 12, 'bold'),
            fg=COLORS['text_secondary'],
            bg=COLORS['bg'],
        )
        self.mode_label.pack(pady=(16, 10))

        # Buttons frame
        btn_frame = tk.Frame(self.window, bg=COLORS['bg'])
        btn_frame.pack(pady=(10, 16))

        self.btn_start = self._make_button(btn_frame, '▶', COLORS['work'], self.start_timer)
        self.btn_start.pack(side=tk.LEFT, padx=6)

        self.btn_pause = self._make_button(
            btn_frame, '⏸', COLORS['text_secondary'], self.pause_timer, disabled=True
        )
        self.btn_pause.pack(side=tk.LEFT, padx=6)

        self.btn_reset = self._make_button(
            btn_frame, '↺', COLORS['text_secondary'], self.reset_timer, disabled=True
        )
        self.btn_reset.pack(side=tk.LEFT, padx=6)

        self.btn_skip = self._make_button(
            btn_frame, '⏭', COLORS['text_secondary'], self.skip_to_next
        )
        self.btn_skip.pack(side=tk.LEFT, padx=6)

        # Pomodoro counter
        counter_frame = tk.Frame(self.window, bg=COLORS['bg'])
        counter_frame.pack(pady=(8, 10))

        self.counter_label = tk.Label(
            counter_frame,
            text='已完成：',
            font=('SF Pro Display', 13),
            fg=COLORS['text_muted'],
            bg=COLORS['bg'],
        )
        self.counter_label.pack(side=tk.LEFT)

        self.tomato_icons_label = tk.Label(
            counter_frame,
            text='',
            font=('SF Pro Display', 12),
            fg=COLORS['text'],
            bg=COLORS['bg'],
        )
        self.tomato_icons_label.pack(side=tk.LEFT, padx=(4, 2))

        self.count_label = tk.Label(
            counter_frame,
            text='0 个番茄',
            font=('SF Pro Display', 13),
            fg=COLORS['text_muted'],
            bg=COLORS['bg'],
        )
        self.count_label.pack(side=tk.LEFT)

        # Bottom toggle
        bottom = tk.Frame(self.window, bg=COLORS['bg'])
        bottom.pack(side=tk.BOTTOM, pady=(0, 20))

        self.always_on_top_var = tk.BooleanVar(value=True)
        self.on_top_check = tk.Checkbutton(
            bottom,
            text='置顶',
            variable=self.always_on_top_var,
            command=self._toggle_always_on_top,
            font=('SF Pro Display', 11),
            fg=COLORS['text_muted'],
            bg=COLORS['bg'],
            selectcolor=COLORS['bg'],
            activebackground=COLORS['bg'],
            activeforeground=COLORS['text_muted'],
            highlightthickness=0,
        )
        self.on_top_check.pack(side=tk.LEFT)

    def _make_button(self, parent, text, color, command, disabled=False):
        btn = tk.Button(
            parent,
            text=text,
            font=('SF Pro Display', 20),
            fg=color if not disabled else COLORS['text_muted'],
            bg=COLORS['btn_bg'],
            activebackground=COLORS['btn_hover'],
            activeforeground=color,
            relief=tk.FLAT,
            borderwidth=0,
            padx=14,
            pady=8,
            cursor='pointinghand',
            command=command,
            state=tk.DISABLED if disabled else tk.NORMAL,
            highlightthickness=0,
        )
        return btn

    def _draw_ring(self):
        cx, cy = self.canvas_size // 2, self.canvas_size // 2
        r = 94
        ring_width = 8

        # Background ring
        self.canvas.create_oval(
            cx - r, cy - r, cx + r, cy + r,
            outline=COLORS['ring_bg'],
            width=ring_width,
            tags='bg_ring',
        )

        # Progress arc (drawn as an arc, going counter-clockwise from top)
        self.arc_id = None
        self._update_arc(cx, cy, r, ring_width, 0)

        # Time text
        self.time_text_id = self.canvas.create_text(
            cx, cy - 6,
            text='25:00',
            font=('SF Mono', 48, 'bold'),
            fill=COLORS['text'],
            tags='time_text',
        )

    def _update_arc(self, cx, cy, r, width, fraction):
        """Update the progress arc. fraction goes from 0 (full) to 1 (empty)."""
        if self.arc_id:
            self.canvas.delete(self.arc_id)

        # Draw arc from top (90°) going clockwise based on remaining fraction
        # Full circle = 360°, we draw from 90° going clockwise
        extent = -fraction * 359.9  # negative = clockwise on macOS

        color = COLORS['work']
        if self.mode == 'short_break':
            color = COLORS['short_break']
        elif self.mode == 'long_break':
            color = COLORS['long_break']

        self.arc_id = self.canvas.create_arc(
            cx - r, cy - r, cx + r, cy + r,
            start=90,
            extent=extent,
            outline=color,
            width=width,
            style='arc',
            tags='progress_arc',
        )

    def _update_display(self):
        """Update all display elements."""
        mins, secs = divmod(self.remaining, 60)
        time_str = f'{mins:02d}:{secs:02d}'
        self.canvas.itemconfig(self.time_text_id, text=time_str)

        # Mode label
        mode_labels = {
            'work': '🔴 专注时间',
            'short_break': '🟢 短休息',
            'long_break': '🔵 长休息',
        }
        if self.timer_state == TimerState.IDLE and self.remaining == self.total_duration:
            mode_labels['work'] = '🔴 准备开始'

        self.mode_label.config(text=mode_labels.get(self.mode, ''))

        # Progress arc
        cx = cy = self.canvas_size // 2
        r = 94
        fraction = self.remaining / self.total_duration if self.total_duration > 0 else 0
        self._update_arc(cx, cy, r, 8, fraction)

        # Tomato counter
        count = self.completed_pomodoros
        display_count = min(count, 10)
        self.tomato_icons_label.config(text='🍅' * display_count if count > 0 else '')
        self.count_label.config(text=f'{count} 个番茄')

        # Button states
        if self.timer_state == TimerState.IDLE:
            self._set_button_state(self.btn_start, tk.NORMAL)
            self._set_button_state(self.btn_pause, tk.DISABLED)
            self._set_button_state(self.btn_reset, tk.DISABLED)
            self._set_button_state(self.btn_skip, tk.NORMAL)
        elif self.timer_state == TimerState.RUNNING:
            self._set_button_state(self.btn_start, tk.DISABLED)
            self._set_button_state(self.btn_pause, tk.NORMAL)
            self._set_button_state(self.btn_reset, tk.NORMAL)
            self._set_button_state(self.btn_skip, tk.NORMAL)
        elif self.timer_state == TimerState.PAUSED:
            self._set_button_state(self.btn_start, tk.NORMAL)
            self._set_button_state(self.btn_pause, tk.DISABLED)
            self._set_button_state(self.btn_reset, tk.NORMAL)
            self._set_button_state(self.btn_skip, tk.NORMAL)

    def _set_button_state(self, btn, state):
        btn.config(state=state)
        if state == tk.DISABLED:
            btn.config(fg=COLORS['text_muted'])
        elif btn == self.btn_start:
            btn.config(fg=COLORS['work'])
        else:
            btn.config(fg=COLORS['text_secondary'])

    # ===== Timer Logic =====

    def _toggle_timer(self):
        if self.timer_state == TimerState.RUNNING:
            self.pause_timer()
        else:
            self.start_timer()

    def start_timer(self):
        if self.timer_state == TimerState.RUNNING:
            return
        self.timer_state = TimerState.RUNNING
        self._update_display()
        self._tick()

    def pause_timer(self):
        if self.timer_state != TimerState.RUNNING:
            return
        self.timer_state = TimerState.PAUSED
        if self.after_id:
            self.window.after_cancel(self.after_id)
            self.after_id = None
        self._update_display()

    def reset_timer(self):
        self.timer_state = TimerState.IDLE
        if self.after_id:
            self.window.after_cancel(self.after_id)
            self.after_id = None
        self.remaining = self.total_duration
        self._update_display()

    def skip_to_next(self):
        self.timer_state = TimerState.IDLE
        if self.after_id:
            self.window.after_cancel(self.after_id)
            self.after_id = None
        self._timer_complete(skipped=True)

    def _tick(self):
        if self.timer_state != TimerState.RUNNING:
            return

        if self.remaining <= 0:
            self._timer_complete()
            return

        self.remaining -= 1
        self._update_display()
        self.after_id = self.window.after(1000, self._tick)

    def _timer_complete(self, skipped=False):
        """Handle timer completion - play sound, notify, switch mode."""
        if self.mode == 'work' and not skipped:
            self.completed_pomodoros += 1

        # Play sound in background
        threading.Thread(target=self._play_chime, daemon=True).start()

        # Send notification
        self._send_notification()

        # Flash the window to get attention
        try:
            self.window.attributes('-topmost', True)
            self.window.deiconify()
            self.window.lift()
        except Exception:
            pass

        # Switch mode
        if self.mode == 'work':
            if self.completed_pomodoros % LONG_BREAK_INTERVAL == 0:
                self.mode = 'long_break'
                self.total_duration = LONG_BREAK
            else:
                self.mode = 'short_break'
                self.total_duration = SHORT_BREAK
        else:
            self.mode = 'work'
            self.total_duration = WORK_TIME

        self.timer_state = TimerState.IDLE
        self.remaining = self.total_duration
        self._update_display()

    def _play_chime(self):
        """Play a pleasant three-tone chime using afplay."""
        try:
            # Use macOS built-in sound
            subprocess.run(
                ['afplay', '/System/Library/Sounds/Glass.aiff'],
                capture_output=True,
            )
        except Exception:
            pass

    def _send_notification(self):
        """Send macOS desktop notification."""
        if self.mode == 'work':
            title = '🍅 番茄钟完成！'
            body = f'已完成 {self.completed_pomodoros} 个番茄，休息一下吧~'
        else:
            title = '⏰ 休息结束'
            body = '准备开始新的番茄钟吧！'

        script = f'''
        display notification "{body}" with title "{title}" sound name "Glass"
        '''
        try:
            subprocess.run(['osascript', '-e', script], capture_output=True)
        except Exception:
            pass

    def _toggle_always_on_top(self):
        self.always_on_top = self.always_on_top_var.get()
        self.window.attributes('-topmost', self.always_on_top)

    def run(self):
        self.window.mainloop()


if __name__ == '__main__':
    app = PomodoroApp()
    app.run()
