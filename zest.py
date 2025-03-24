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
# Test API call
print("Testing API...")
try:
    test_response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": "Hello!"}]
    )
    print("Test response:", test_response.choices[0].message.content)
except Exception as e:
    print("Test failed:", str(e))

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
        self.root.title("Zest Chatbot")  # Updated window title
        self.root.geometry("400x600")
        self.root.configure(bg="#f0f0f0")
        # Set a minimum window size
        self.root.minsize(250, 400)

        # Main frame with scrollbar
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

        # Force focus on the canvas to ensure it receives scroll events
        self.canvas.focus_set()

        # Bind scrolling events globally and to the canvas
        self.root.bind_all("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind("<MouseWheel>", self._on_mousewheel)

        # Try Button-4 and Button-5 for macOS as a fallback
        self.root.bind_all("<Button-4>", lambda event: self.canvas.yview_scroll(-1, "units"))
        self.root.bind_all("<Button-5>", lambda event: self.canvas.yview_scroll(1, "units"))
        self.canvas.bind("<Button-4>", lambda event: self.canvas.yview_scroll(-1, "units"))
        self.canvas.bind("<Button-5>", lambda event: self.canvas.yview_scroll(1, "units"))

        # Bind window resize event to update message wraplength and padding
        self.root.bind("<Configure>", self.schedule_update_layout)

        # Debug bindings to check where scroll events are going
        self.root.bind("<MouseWheel>", self._debug_scroll_event, add="+")
        self.canvas.bind("<MouseWheel>", self._debug_scroll_event, add="+")
        self.root.bind("<Button-4>", self._debug_scroll_event, add="+")
        self.root.bind("<Button-5>", self._debug_scroll_event, add="+")
        self.canvas.bind("<Button-4>", self._debug_scroll_event, add="+")
        self.canvas.bind("<Button-5>", self._debug_scroll_event, add="+")

        # Input frame
        self.input_frame = Frame(self.root, bg="#f0f0f0")
        self.input_frame.pack(side="bottom", fill="x", padx=5, pady=5)

        # Model selection dropdown (using OptionMenu)
        self.model_var = tk.StringVar(value="gpt-3.5-turbo")
        self.model_label = tk.Label(self.input_frame, text="Model:", bg="#f0f0f0", font=("Helvetica", 10))
        self.model_label.pack(side="left", padx=(5, 2))
        self.model_dropdown = tk.OptionMenu(self.input_frame, self.model_var, "gpt-3.5-turbo", "gpt-4.5-preview")
        self.model_dropdown.config(width=8)
        self.model_dropdown.pack(side="left", padx=(0, 3))

        # Input text area (set a smaller minimum width and allow expansion)
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

        # Send, Clear, and Copy All buttons
        self.send_button = ttk.Button(self.input_frame, text="➤", command=self.send_message, style="Send.TButton", width=2)
        self.send_button.pack(side="right", padx=(0, 5))
        Tooltip(self.send_button, "Send your message")

        self.clear_button = ttk.Button(self.input_frame, text="Clear", command=self.clear_chat, width=5)
        self.clear_button.pack(side="right", padx=(0, 3))
        Tooltip(self.clear_button, "This will clear the chat")

        self.copy_all_button = ttk.Button(self.input_frame, text="Copy All", command=self.copy_all_messages, width=8)
        self.copy_all_button.pack(side="right", padx=(0, 3))
        Tooltip(self.copy_all_button, "Copy the entire conversation to clipboard")

        # Style for send button
        style = ttk.Style()
        style.configure("Send.TButton", font=("Helvetica", 14), background="#40c057", foreground="black")
        style.map("Send.TButton", background=[("active", "#34a853")], foreground=[("active", "black")])

        # Store all message frames, bubbles, and copy buttons to update their layout on resize
        self.message_frames = []
        self.message_bubbles = []
        self.copy_buttons = []  # List to store copy buttons for GPT responses
        self.update_id = None  # To manage scheduled updates

        # Add the welcome message
        self.add_welcome_message()

    def add_welcome_message(self):
        # Determine the time of day for the greeting
        current_hour = datetime.now().hour
        if 0 <= current_hour < 12:
            greeting = "Good Morning"
        elif 12 <= current_hour < 17:
            greeting = "Good Afternoon"
        else:
            greeting = "Good Evening"

        # Try to get the user's name, fall back to a generic greeting if it fails
        try:
            user_name = os.getlogin()
            welcome_text = f"{greeting}, {user_name}! I’m Zest, your cheerful assistant here to brighten your day. What’s on your mind?"  # Updated welcome message
        except:
            welcome_text = f"{greeting}! I’m Zest, your cheerful assistant here to brighten your day. What’s on your mind?"  # Updated welcome message

        # Add the welcome message as a GPT message without a Copy button
        self.add_message("GPT", welcome_text, is_thinking=False, show_copy_button=False)

    def _on_mousewheel(self, event):
        # Handle MouseWheel events for all platforms
        if platform.system() == "Darwin":  # macOS
            # macOS trackpad generates small delta values; reduce multiplier for slower scrolling
            scroll_amount = -1 * event.delta * 1
        else:
            # Windows/Linux: Use standard divisor
            scroll_amount = -1 * (event.delta / 120)
        
        # Ensure scroll_amount is an integer and non-zero to avoid unnecessary updates
        if scroll_amount != 0:
            self.canvas.yview_scroll(int(scroll_amount), "units")

    def _debug_scroll_event(self, event):
        # Debug method to print which scroll events are being triggered
        print(f"Scroll event triggered: {event.type}, delta={getattr(event, 'delta', 'N/A')}, widget={event.widget}")

    def schedule_update_layout(self, event=None):
        # Cancel any previously scheduled update
        if self.update_id is not None:
            self.root.after_cancel(self.update_id)
        # Schedule a new update with a slight delay to ensure window size is updated
        self.update_id = self.root.after(100, self.update_layout)

    def update_layout(self):
        # Update the wraplength and padding of all message bubbles based on the current canvas width
        canvas_width = self.canvas.winfo_width()
        print(f"Updating layout: canvas_width={canvas_width}")  # Debug print
        # Use 80% of the canvas width, with a minimum of 150
        new_wraplength = max(150, int(canvas_width * 0.8))
        # Dynamic padding: 5px for small windows, 10px for larger windows
        new_padding = 5 if canvas_width < 300 else 10

        # Create new lists of valid bubbles, frames, and copy buttons
        valid_bubbles = []
        valid_frames = []
        valid_copy_buttons = []
        for bubble, frame, copy_button in zip(self.message_bubbles, self.message_frames, self.copy_buttons + [None] * (len(self.message_bubbles) - len(self.copy_buttons))):
            try:
                # Check if the widget still exists by attempting to configure it
                bubble.configure(wraplength=new_wraplength)
                print(f"Updated wraplength for bubble: {bubble.cget('text')[:20]}... to {new_wraplength}, visible={bubble.winfo_viewable()}, width={bubble.winfo_width()}")  # Debug print
                frame.pack_configure(padx=new_padding)
                valid_bubbles.append(bubble)
                valid_frames.append(frame)
                if copy_button is not None:
                    valid_copy_buttons.append(copy_button)
            except tk.TclError:
                # Widget no longer exists, skip it
                continue

        # Update the lists with only valid widgets
        self.message_bubbles = valid_bubbles
        self.message_frames = valid_frames
        self.copy_buttons = valid_copy_buttons

        # Force the canvas to update its scroll region and redraw
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        self.canvas.update_idletasks()  # Force redraw
        self.root.update()  # Force full window update

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
        # Only clear placeholder if the user starts typing (not on arrow keys or selection)
        if event.keysym not in ("Left", "Right", "Up", "Down", "Shift_L", "Shift_R", "Control_L", "Control_R"):
            if self.input_text.get("1.0", tk.END).strip() == self.placeholder_text:
                self.input_text.delete("1.0", tk.END)
                self.input_text.tag_remove("placeholder", "1.0", tk.END)
                self.input_text.configure(fg="black")

    def chat_with_gpt(self):
        try:
            start_time = time.time()
            response = client.chat.completions.create(
                model=self.model_var.get(),  # Use selected model
                messages=conversation,
                timeout=40  # Set a 40-second timeout
            )
            end_time = time.time()
            response_time = end_time - start_time
            print(f"API response time: {response_time:.2f} seconds")
            return response.choices[0].message.content, response_time
        except openai.APITimeoutError:
            return "Error: API request timed out after 40 seconds. Please try again.", 0
        except Exception as e:
            return f"Error: {str(e)}", 0

    def copy_response(self, bubble, copy_button):
        """Copy the text of the given bubble to the clipboard and show feedback."""
        text = bubble.cget("text")
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.root.update()  # Ensure clipboard is updated
        print(f"Copied to clipboard: {text}")

        # Show "Copied!" feedback
        feedback_label = tk.Label(
            copy_button.master,
            text="Copied!",
            font=("Helvetica", 10),
            fg="#606060",
            bg="#f0f0f0"
        )
        feedback_label.pack(side="left", padx=(5, 0))
        # Remove the label after 2 seconds
        self.root.after(2000, feedback_label.destroy)

    def copy_all_messages(self):
        """Copy the entire conversation to the clipboard."""
        conversation_text = []
        for frame, bubble in zip(self.message_frames, self.message_bubbles):
            # Get the timestamp from the frame
            timestamp_label = frame.winfo_children()[0]  # First child is the timestamp
            timestamp = timestamp_label.cget("text")
            # Get the sender and message
            sender = "You" if bubble.cget("bg") == "#40c057" else "GPT"
            message = bubble.cget("text")
            conversation_text.append(f"{timestamp} {sender}: {message}")
        
        full_text = "\n".join(conversation_text)
        self.root.clipboard_clear()
        self.root.clipboard_append(full_text)
        self.root.update()  # Ensure clipboard is updated
        print("Copied entire conversation to clipboard")

    def add_message(self, sender, message, response_time=None, is_thinking=False, show_copy_button=True):
        # Create a frame for the message bubble and timestamp
        bubble_frame = Frame(self.scrollable_frame, bg="#f0f0f0")
        bubble_frame.pack(fill="x", padx=10, pady=2)

        # Create an inner frame to hold the bubble, timestamp, and copy button (if applicable)
        inner_frame = Frame(bubble_frame, bg="#f0f0f0")
        # Dynamic padding based on initial window size
        canvas_width = self.canvas.winfo_width()
        padding = 5 if canvas_width < 300 else 10
        anchor = "e" if sender == "You" else "w"
        inner_frame.pack(fill="x", padx=padding, anchor=anchor)

        # Calculate initial wraplength based on current canvas width, with a fallback
        wraplength = max(150, int(canvas_width * 0.8)) if canvas_width > 0 else 300  # Fallback to 300 if canvas width is 0

        # Timestamp
        timestamp = datetime.now().strftime("%H:%M")
        time_label = tk.Label(
            inner_frame,
            text=f"{timestamp}" + (f" ({response_time:.2f}s)" if response_time else ""),
            font=("Helvetica", 10),
            fg="#606060",
            bg="#f0f0f0"
        )
        time_label.pack(side="left" if sender == "You" else "right", padx=5)

        # Message bubble
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

        # Add a Copy button for GPT messages only, if show_copy_button is True and not a "Thinking..." message
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

        # Store the bubble, frame, and copy button (if applicable)
        self.message_bubbles.append(bubble)
        self.message_frames.append(inner_frame)
        if copy_button:
            self.copy_buttons.append(copy_button)

        # Debug print to confirm message is added
        print(f"Added message: sender={sender}, text={message[:20]}...")

        # Force scroll to bottom and update the canvas
        self.canvas.update_idletasks()
        self.canvas.yview_moveto(1)

    def send_message(self):
        user_input = self.input_text.get("1.0", tk.END).strip()
        if not user_input or user_input == self.placeholder_text:
            return
        print("Send button clicked!")
        print(f"Raw input: {user_input}")
        print(f"User input: {user_input}")

        self.add_message("You", user_input)
        self.input_text.delete("1.0", tk.END)
        self.add_message("GPT", "Thinking...", is_thinking=True)

        conversation.append({"role": "user", "content": user_input})

        # Run API call in a separate thread to prevent UI hanging
        threading.Thread(target=self.process_message, daemon=True).start()

    def process_message(self):
        reply, response_time = self.chat_with_gpt()
        print(f"API response: {reply}")

        # Update UI from the main thread
        self.root.after(0, self.update_message, reply, response_time)

    def update_message(self, reply, response_time):
        # Remove the "Thinking..." message
        thinking_widget = self.scrollable_frame.winfo_children()[-1]
        thinking_widget.destroy()

        # Remove the "Thinking..." message's bubble and frame from the lists
        if self.message_bubbles and self.message_frames:
            self.message_bubbles.pop()
            self.message_frames.pop()

        self.add_message("GPT", reply, response_time)
        conversation.append({"role": "assistant", "content": reply})

    def send_message_event(self, event):
        self.send_message()
        return "break"

    def clear_chat(self):
        print("Clear button clicked!")
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        self.message_bubbles.clear()  # Clear the list of message bubbles
        self.message_frames.clear()  # Clear the list of message frames
        self.copy_buttons.clear()  # Clear the list of copy buttons
        conversation.clear()
        conversation.append({"role": "system", "content": "You are a witty, helpful assistant who loves to make users smile. Note: My knowledge is fresh up to October 2023, so for anything more recent, I might need a little help!"})

# Set up GUI
root = tk.Tk()
app = ChatApp(root)
root.mainloop()
