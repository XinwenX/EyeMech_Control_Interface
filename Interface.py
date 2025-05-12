"""
Tkinter Control GUI of EyeMech
Author: Xinwen Xu
Date: 2025-04-23

This script provides a Tkinter GUI for controlling the EyeMech.
The GUI allows users to connect to a serial port, send commands to the Arduino,
and visualize the radar visualization.

The controls include:
- Connect button: Connect to a serial port
- Port selection: Select a serial port
- Update button: Update the list of available serial ports
- Mouse Left button: Click and drag to move the target point, sending XY coordinates(percentage of the range) to the Arduino
- Mouse Right button: Send a command to the Arduino to Blink
- Mouse Wheel: Send a command to the Arduino to Open/Close lid
"""

import tkinter as tk
from tkinter import ttk, messagebox
import serial
import serial.tools.list_ports
import time
import numpy as np

class Communication:
    """Manager for serial communication with Arduino"""
    def __init__(self, baudrate=9600):
        self.baudrate = baudrate
        self.ser = None
        self.port = None

    def list_ports(self):
        """Get list of available serial ports"""
        return [p.device for p in serial.tools.list_ports.comports()]

    def connect(self, port_name):
        """Attempt to connect to a serial port"""
        try:
            if self.ser and self.ser.is_open:
                self.ser.close()
            self.ser = serial.Serial(port_name, self.baudrate, timeout=1)
            time.sleep(2)  # Wait for port to open/reset
            self.port = port_name
            return True, f"{port_name}@{self.baudrate}"
        except Exception as e:
            self.ser = None
            return False, str(e)

    def send(self, cmd: str):
        """Send a command to the Arduino"""
        print(f"→ {cmd}")
        if self.ser and self.ser.is_open:
            self.ser.write((cmd + "\n").encode())


class EyeMech:
    """Wrapper for EyeMech control"""
    def __init__(self, comm: Communication, canvas_size=400):
        self.comm = comm
        self.canvas_size = canvas_size

    def move_eye(self, x: float, y: float):
        self.comm.send("EYE {:.2f} {:.2f}".format(x, y))

    def control_lid(self, delta: int):
        self.comm.send(f"LID {delta}")

    def blink(self):
        self.comm.send("BLINK")


class Interface:
    """ Tkinter Control GUI of EyeMech"""
    def __init__(self, root):
        self.root = root
        self.root.title("EyeMech Control Interface")

        self.comm = Communication()
        self.eye = EyeMech(self.comm)

        # Mouse drag
        self.dragging = False
        self.last_send_time = 0
        self.send_interval = 0.01  # seconds (update frequency is 10Hz) 


        self._build_ui()
        self._update_ports()

    def _build_ui(self):
        top = tk.Frame(self.root)
        top.pack(side=tk.TOP, fill=tk.X, pady=5)

        # Pull down menu: Port selection
        tk.Label(top, text="Port:").pack(side=tk.LEFT, padx=5)
        self.port_var = tk.StringVar()
        self.port_combo = ttk.Combobox(top, textvariable=self.port_var, state="readonly", width=15)
        self.port_combo.pack(side=tk.LEFT)

        # Update ports button: Update port list
        upd_btn = tk.Button(top, text="Update", command=self._update_ports)
        upd_btn.pack(side=tk.LEFT, padx=5)

        # Connect button: Connect to selected port
        conn_btn = tk.Button(top, text="Connected", command=self.on_connect)
        conn_btn.pack(side=tk.LEFT, padx=5)

        # Connection status
        self.status_var = tk.StringVar(value="Not Connected")
        tk.Label(top, textvariable=self.status_var).pack(side=tk.LEFT, padx=10)

        # Canvas: Radar visualization
        self.canvas_size = 400
        self.margin = 20
        self.radius = self.canvas_size // 2 - self.margin
        self.center_x = self.canvas_size // 2
        self.center_y = self.canvas_size // 2

        self.canvas = tk.Canvas(self.root, width=self.canvas_size,
                                height=self.canvas_size, bg="white")
        self.canvas.pack()
        self._draw_radar()
        self._bind_events()

    def _update_ports(self):
        """Update list of available serial ports"""
        ports = self.comm.list_ports()
        self.port_combo['values'] = ports
        if ports:
            self.port_var.set(ports[0])
        else:
            self.port_var.set("")

    def on_connect(self):
        """Connect to selected serial port"""
        port = self.port_var.get()
        if not port:
            messagebox.showwarning("Connection Failed", "Select a port first")
            return
        success, msg = self.comm.connect(port)
        if success:
            self.status_var.set(f"Connected: {msg}")
        else:
            self.status_var.set("Connection Failed")
            messagebox.showerror("Connection Failed", msg)

    def _draw_radar(self):
        c = self.canvas
        cx, cy, r = self.center_x, self.center_y, self.radius
        c.create_oval(cx - r, cy - r, cx + r, cy + r, outline="black", width=2)
        c.create_line(cx - r, cy, cx + r, cy, fill="black", dash=(4, 2))
        c.create_line(cx, cy - r, cx, cy + r, fill="black", dash=(4, 2))
        c.create_oval(cx - 3, cy - 3, cx + 3, cy + 3, fill="red")

    def _bind_events(self):
        self.canvas.bind("<Button-1>", self._on_left_press)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_left_release)
        self.canvas.bind("<Button-3>", self._on_right_click)
        self.canvas.bind("<MouseWheel>", self._on_wheel)
        self.canvas.bind("<Button-4>", self._on_wheel)
        self.canvas.bind("<Button-5>", self._on_wheel)

    def _on_left_press(self, event):
        """Left mouse button pressed, start dragging"""
        self.dragging = True
        self._update_dot_and_send(event.x, event.y)

    def _on_drag(self, event):
        """Dragging mouse, update target point and send to Arduino"""
        if not self.dragging:
            return
        now = time.time()
        if now - self.last_send_time >= self.send_interval:
            self._update_dot_and_send(event.x, event.y)
            self.last_send_time = now

    def _on_left_release(self, event):
        """Left mouse button released, stop dragging"""
        self.dragging = False

    def _update_dot_and_send(self, x, y):
        """Update target point and send to Arduino"""
        dx = x - self.center_x
        dy = y - self.center_y
        if dx*dx + dy*dy <= self.radius*self.radius:
            tx, ty = x, y
        else:
            tx, ty = self.center_x, self.center_y
        # Visualization update
        self.canvas.delete("click_dot")
        self.canvas.create_oval(tx-5, ty-5, tx+5, ty+5,
                                fill="blue", tags="click_dot")
        # map to [-50, 50]
        cx, cy, r = self.center_x, self.center_y, self.radius
        map_x = np.interp(tx, [cx - r, cx + r], [-50, 50])
        map_y = - np.interp(ty, [cy - r, cy + r], [-50, 50])

        # Send command to move eye
        self.eye.move_eye(map_x, map_y)

    def _on_wheel(self, event):
        # delta（Windows/macOS）
        if getattr(event, "delta", 0):
            # In Windows, delta is a multiple of ±120
            delta = event.delta // 120
        # num（Linux）
        elif getattr(event, "num", None) in (4, 5):
            delta = 1 if event.num == 4 else -1
        else:
            return  # No mouse wheel event detected
        self.eye.control_lid(delta)

    def _on_right_click(self, event):
        self.eye.blink()


if __name__ == "__main__":
    root = tk.Tk()
    app = Interface(root)
    root.mainloop()
