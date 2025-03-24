import os
import time
from datetime import datetime
from openai import OpenAI
import tkinter as tk
from tkinter import ttk, Canvas, Scrollbar, Frame
import threading
import openai
import platform  # For detecting the operating system

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Removed test API call to avoid confusion for users
# print("Testing API...")
# try:
#     test_response = client.chat.completions.create(
#         model="gpt-3.5-turbo",
#         messages=[{"role": "user", "content": "Hello!"}]
#     )
#     print("Test response:", test_response.choices[0].message.content)
# except Exception as e:
#     print("Test failed:", str(e))

conversation = [{"role": "system", "content": "You are a witty, helpful assistant who loves to make users smile. Note: My knowledge is fresh up to October 2023, so for anything more recent, I might need a little help!"}]

class Tooltip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip_window = None
        self.widget.bind("<Enter>", self.show_tooltip)
        self.widget.bind("<Leave>", self.hide_tooltip)

    def show_tooltip(self, event=None):
        x, y, _, _ = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 25
        self.tooltip_window = tk.Toplevel(self.widget)
        self.tooltip_window.wm_overrideredirect(True)
        self.tooltip_window.wm_geometry(f"+{x}+{y}")
        label = tk.Label(
            self.tooltip_window,
            text=self.text,
            background="#ffffe0",
            foreground="black",
            relief="solid",
            borderwidth=1,
            font=("Helvetica", 10)
        )
        label.pack()

    def hide_tooltip(self, event=None):
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None

class ChatApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Zest Chatbot")
        self.root.geometry("400x600")
        self.root.configure(bg="#f0f0f0")
        self.root.minsize(250, 400)

        self.main_frame = Frame(self.root, bg="#f0f0f0")
        self.main_frame.pack(fill="both", expand=True)

        self.canvas = Canvas(self.main_frame, bg="#f0f0f0", highlightthickness=0)
        self.scrollbar = Scrollbar(self.main_frame, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = Frame(self.canvas, bg="#f0f0f0")

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")

        self.canvas.focus_set()

        self.root.bind_all("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind("<MouseWheel>", self._on_mousewheel)

        self.root.bind_all("<Button-4>", lambda event: self.canvas.yview_scroll(-1, "units"))
        self.root.bind_all("<Button-5>", lambda event: self.canvas.yview_scroll(1, "units"))
        self.canvas.bind("<Button-4>", lambda event: self.canvas.yview_scroll(-1, "units"))
        self.canvas.bind("<Button-5>", lambda event: self.canvas.yview_scroll(1, "units"))

        self.root.bind("<Configure>", self.schedule_update_layout)

        # Removed debug bindings
        # self.root.bind("<MouseWheel>", self._debug_scroll_event, add="+")
        # self.canvas.bind("<MouseWheel>", self._debug_scroll_event, add="+")
        # self.root.bind("<Button-4>", self._debug_scroll_event, add="+")
        # self.root.bind("<Button-5>", self._debug_scroll_event, add="+")
        # self.canvas.bind("<Button-4>", self._debug_scroll_event, add="+")
        # self.canvas.bind("<Button-5>", self._debug_scroll_event, add="+")

        self.input_frame = Frame(self.root, bg="#f0f0f0")
        self.input_frame.pack(side="bottom", fill="x", padx=5, pady=5)

        self.model_var = tk.StringVar(value="gpt-3.5-turbo")
        self.model_label = tk.Label(self.input_frame, text="Model:", bg="#f0f0f0", font=("Helvetica", 10))
        self.model_label.pack(side="left", padx=(5, 2))
        self.model_dropdown = tk.OptionMenu(self.input_frame, self.model_var, "gpt-3.5-turbo", "gpt-4.5-preview")
        self.model_dropdown.config(width=8)
        self.model_dropdown.pack(side="left", padx=(0, 3))

        self.input_text = tk.Text(self.input_frame, height=3, width=10, wrap="word", font=("Helvetica", 14), bd=0, relief="flat")
        self.input_text.pack(side="left", fill="x", expand=True, padx=(0, 3), pady=5)
        self.input_text.configure(
            bg="#ffffff",
            fg="black",
            insertbackground="black",
            borderwidth=1,
            relief="solid",
            highlightthickness=1,
            highlightbackground="#d3d3d3",
            highlightcolor="#40c057",
            selectbackground="#c3e8ff",
            selectforeground="black"
        )
        self.placeholder_text = "Input your text here and click Enter"
        self.input_text.insert("1.0", self.placeholder_text)
        self.input_text.tag_configure("placeholder", foreground="#a9a9a9")
        self.input_text.tag_add("placeholder", "1.0", tk.END)
        self.input_text.bind("<FocusIn>", self.clear_placeholder)
        self.input_text.bind("<FocusOut>", self.add_placeholder)
        self.input_text.bind("<Key>", self.on_key_press)
        self.input_text.bind("<Return>", self.send_message_event)

        self.send_button = ttk.Button(self.input_frame, text="➤", command=self.send_message, style="Send.TButton", width=2)
        self.send_button.pack(side="right", padx=(0, 5))
        Tooltip(self.send_button, "Send your message")

        self.clear_button = ttk.Button(self.input_frame, text="Clear", command=self.clear_chat, width=5)
        self.clear_button.pack(side="right", padx=(0, 3))
        Tooltip(self.clear_button, "This will clear the chat")

        self.copy_all_button = ttk.Button(self.input_frame, text="Copy All", command=self.copy_all_messages, width=8)
        self.copy_all_button.pack(side="right", padx=(0, 3))
        Tooltip(self.copy_all_button, "Copy the entire conversation to clipboard")

        style = ttk.Style()
        style.configure("Send.TButton", font=("Helvetica", 14), background="#40c057", foreground="black")
        style.map("Send.TButton", background=[("active", "#34a853")], foreground=[("active", "black")])

        self.message_frames = []
        self.message_bubbles = []
        self.copy_buttons = []
        self.update_id = None

        # Check for API key before adding the welcome message
        if not os.getenv("OPENAI_API_KEY"):
            self.add_message("System", "Error: OPENAI_API_KEY environment variable is not set. Please set it and restart the application.", show_copy_button=False)
        else:
            self.add_welcome_message()

    def add_welcome_message(self):
        current_hour = datetime.now().hour
        if 0 <= current_hour < 12:
            greeting = "Good Morning"
        elif 12 <= current_hour < 17:
            greeting = "Good Afternoon"
        else:
            greeting = "Good Evening"

        try:
            user_name = os.getlogin()
            welcome_text = f"{greeting}, {user_name}! I’m Zest, your cheerful assistant here to brighten your day. What’s on your mind?"
        except:
            welcome_text = f"{greeting}! I’m Zest, your cheerful assistant here to brighten your day. What’s on your mind?"

        self.add_message("GPT", welcome_text, is_thinking=False, show_copy_button=False)

    def _on_mousewheel(self, event):
        if platform.system() == "Darwin":
            scroll_amount = -1 * event.delta * 1
        else:
            scroll_amount = -1 * (event.delta / 120)
        
        if scroll_amount != 0:
            self.canvas.yview_scroll(int(scroll_amount), "units")

    def _debug_scroll_event(self, event):
        # Removed debug method
        pass

    def schedule_update_layout(self, event=None):
        if self.update_id is not None:
            self.root.after_cancel(self.update_id)
        self.update_id = self.root.after(100, self.update_layout)

    def update_layout(self):
        canvas_width = self.canvas.winfo_width()
        # Removed debug print
        # print(f"Updating layout: canvas_width={canvas_width}")
        new_wraplength = max(150, int(canvas_width * 0.8))
        new_padding = 5 if canvas_width < 300 else 10

        valid_bubbles = []
        valid_frames = []
        valid_copy_buttons = []
        for bubble, frame, copy_button in zip(self.message_bubbles, self.message_frames, self.copy_buttons + [None] * (len(self.message_bubbles) - len(self.copy_buttons))):
            try:
                bubble.configure(wraplength=new_wraplength)
                # Removed debug print
                # print(f"Updated wraplength for bubble: {bubble.cget('text')[:20]}... to {new_wraplength}, visible={bubble.winfo_viewable()}, width={bubble.winfo_width()}")
                frame.pack_configure(padx=new_padding)
                valid_bubbles.append(bubble)
                valid_frames.append(frame)
                if copy_button is not None:
                    valid_copy_buttons.append(copy_button)
            except tk.TclError:
                continue

        self.message_bubbles = valid_bubbles
        self.message_frames = valid_frames
        self.copy_buttons = valid_copy_buttons

        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        self.canvas.update_idletasks()
        self.root.update()

    def clear_placeholder(self, event):
        if self.input_text.get("1.0", tk.END).strip() == self.placeholder_text:
            self.input_text.delete("1.0", tk.END)
            self.input_text.tag_remove("placeholder", "1.0", tk.END)
            self.input_text.configure(fg="black")

    def add_placeholder(self, event):
        if not self.input_text.get("1.0", tk.END).strip():
            self.input_text.insert("1.0", self.placeholder_text)
            self.input_text.tag_add("placeholder", "1.0", tk.END)
        self.input_text.configure(fg="black")

    def on_key_press(self, event):
        if event.keysym not in ("Left", "Right", "Up", "Down", "Shift_L", "Shift_R", "Control_L", "Control_R"):
            if self.input_text.get("1.0", tk.END).strip() == self.placeholder_text:
                self.input_text.delete("1.0", tk.END)
                self.input_text.tag_remove("placeholder", "1.0", tk.END)
                self.input_text.configure(fg="black")

    def chat_with_gpt(self):
        try:
            start_time = time.time()
            response = client.chat.completions.create(
                model=self.model_var.get(),
                messages=conversation,
                timeout=40
            )
            end_time = time.time()
            response_time = end_time - start_time
            # Removed debug print
            # print(f"API response time: {response_time:.2f} seconds")
            return response.choices[0].message.content, response_time
        except openai.APITimeoutError:
            return "Error: API request timed out after 40 seconds. Please try again.", 0
        except Exception as e:
            return f"Error: {str(e)}", 0

    def copy_response(self, bubble, copy_button):
        text = bubble.cget("text")
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.root.update()
        # Removed debug print
        # print(f"Copied to clipboard: {text}")

        feedback_label = tk.Label(
            copy_button.master,
            text="Copied!",
            font=("Helvetica", 10),
            fg="#606060",
            bg="#f0f0f0"
        )
        feedback_label.pack(side="left", padx=(5, 0))
        self.root.after(2000, feedback_label.destroy)

    def copy_all_messages(self):
        conversation_text = []
        for frame, bubble in zip(self.message_frames, self.message_bubbles):
            timestamp_label = frame.winfo_children()[0]
            timestamp = timestamp_label.cget("text")
            sender = "You" if bubble.cget("bg") == "#40c057" else "GPT"
            message = bubble.cget("text")
            conversation_text.append(f"{timestamp} {sender}: {message}")
        
        full_text = "\n".join(conversation_text)
        self.root.clipboard_clear()
        self.root.clipboard_append(full_text)
        self.root.update()
        # Removed debug print
        # print("Copied entire conversation to clipboard")

    def add_message(self, sender, message, response_time=None, is_thinking=False, show_copy_button=True):
        bubble_frame = Frame(self.scrollable_frame, bg="#f0f0f0")
        bubble_frame.pack(fill="x", padx=10, pady=2)

        inner_frame = Frame(bubble_frame, bg="#f0f0f0")
        canvas_width = self.canvas.winfo_width()
        padding = 5 if canvas_width < 300 else 10
        anchor = "e" if sender == "You" else "w"
        inner_frame.pack(fill="x", padx=padding, anchor=anchor)

        wraplength = max(150, int(canvas_width * 0.8)) if canvas_width > 0 else 300

        timestamp = datetime.now().strftime("%H:%M")
        time_label = tk.Label(
            inner_frame,
            text=f"{timestamp}" + (f" ({response_time:.2f}s)" if response_time else ""),
            font=("Helvetica", 10),
            fg="#606060",
            bg="#f0f0f0"
        )
        time_label.pack(side="left" if sender == "You" else "right", padx=5)

        bubble_color = "#40c057" if sender == "You" else "#ffffff"
        bubble = tk.Label(
            inner_frame,
            text=message,
            wraplength=wraplength,
            justify="left",
            bg=bubble_color,
            fg="white" if sender == "You" else "black",
            font=("Helvetica", 14),
            padx=10,
            pady=5,
            relief="flat",
            borderwidth=0
        )
        bubble.pack(side="right" if sender == "You" else "left")

        copy_button = None
        if sender == "GPT" and not is_thinking and show_copy_button:
            copy_button = ttk.Button(
                inner_frame,
                text="Copy",
                command=lambda: self.copy_response(bubble, copy_button),
                width=5
            )
            copy_button.pack(side="left", padx=(5, 0))
            Tooltip(copy_button, "Copy this response to clipboard")

        self.message_bubbles.append(bubble)
        self.message_frames.append(inner_frame)
        if copy_button:
            self.copy_buttons.append(copy_button)

        # Removed debug print
        # print(f"Added message: sender={sender}, text={message[:20]}...")

        self.canvas.update_idletasks()
        self.canvas.yview_moveto(1)

    def send_message(self):
        user_input = self.input_text.get("1.0", tk.END).strip()
        if not user_input or user_input == self.placeholder_text:
            return
        # Removed debug prints
        # print("Send button clicked!")
        # print(f"Raw input: {user_input}")
        # print(f"User input: {user_input}")

        self.add_message("You", user_input)
        self.input_text.delete("1.0", tk.END)
        self.add_message("GPT", "Thinking...", is_thinking=True)

        conversation.append({"role": "user", "content": user_input})

        threading.Thread(target=self.process_message, daemon=True).start()

    def process_message(self):
        reply, response_time = self.chat_with_gpt()
        # Removed debug print
        # print(f"API response: {reply}")

        self.root.after(0, self.update_message, reply, response_time)

    def update_message(self, reply, response_time):
        thinking_widget = self.scrollable_frame.winfo_children()[-1]
        thinking_widget.destroy()

        if self.message_bubbles and self.message_frames:
            self.message_bubbles.pop()
            self.message_frames.pop()

        self.add_message("GPT", reply, response_time)
        conversation.append({"role": "assistant", "content": reply})

    def send_message_event(self, event):
        self.send_message()
        return "break"

    def clear_chat(self):
        # Removed debug print
        # print("Clear button clicked!")
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        self.message_bubbles.clear()
        self.message_frames.clear()
        self.copy_buttons.clear()
        conversation.clear()
        conversation.append({"role": "system", "content": "You are a witty, helpful assistant who loves to make users smile. Note: My knowledge is fresh up to October 2023, so for anything more recent, I might need a little help!"})

# Set up GUI
root = tk.Tk()
app = ChatApp(root)
root.mainloop()
