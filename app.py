#  AI Chatbot
from google import genai
from google.genai import types
import pyttsx3
import speech_recognition as sr
import customtkinter as ctk
from PIL import Image, ImageTk, ImageSequence, ImageDraw
import pywhatkit as kit
import webbrowser
import os
import threading
import datetime
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Google AI Setup
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    raise ValueError("GOOGLE_API_KEY not found in .env file")

client       = genai.Client(api_key=api_key)
CURRENT_MODEL = "gemini-2.5-flash"
chat_session  = client.chats.create(model=CURRENT_MODEL)

#  Speech Engine 
engine = pyttsx3.init()
engine.setProperty("rate", 175)
recognizer = sr.Recognizer()

#   Paths     
BASE_DIR   = Path(__file__).parent
IMAGES_DIR = BASE_DIR / "images"

#  Theme Configs  
THEMES = {
    "Dark":   {"bg":"#0D0D14","bg2":"#12121C","bg3":"#1C1C2A","bg4":"#242434",
               "accent":"#7C6AF7","text":"#E0E0F0","text2":"#8888A8",
               "user_bubble":"#7C6AF7","bot_bubble":"#1C1C2A",
               "border":"#2A2A3A","entry_bg":"#1C1C2A"},
    "Light":  {"bg":"#F4F3FF","bg2":"#FFFFFF","bg3":"#EEEEFF","bg4":"#E0DFFA",
               "accent":"#5B50E8","text":"#1A1A2E","text2":"#666688",
               "user_bubble":"#5B50E8","bot_bubble":"#FFFFFF",
               "border":"#D0CEEE","entry_bg":"#FFFFFF"},
    "Ocean":  {"bg":"#00111E","bg2":"#001828","bg3":"#002236","bg4":"#003050",
               "accent":"#00B4D8","text":"#D0EAF5","text2":"#7AB8D4",
               "user_bubble":"#00B4D8","bot_bubble":"#001828",
               "border":"#003A55","entry_bg":"#001828"},
    "Rose":   {"bg":"#180510","bg2":"#220718","bg3":"#2E0A22","bg4":"#3A0D2C",
               "accent":"#F472B6","text":"#FCE7F3","text2":"#D18FA8",
               "user_bubble":"#EC4899","bot_bubble":"#220718",
               "border":"#5C1A38","entry_bg":"#220718"},
    "Forest": {"bg":"#081210","bg2":"#0E1C18","bg3":"#142820","bg4":"#1C3428",
               "accent":"#4ADE80","text":"#D4F5E0","text2":"#7AB898",
               "user_bubble":"#22C55E","bot_bubble":"#0E1C18",
               "border":"#1A3C28","entry_bg":"#0E1C18"},
}
THEME_COLORS = {"Dark":"#7C6AF7","Light":"#5B50E8","Ocean":"#00B4D8",
                "Rose":"#F472B6","Forest":"#4ADE80"}

T            = THEMES["Dark"]   # active theme dict (short alias)
message_count  = 0
chat_history_log = []

#  
#  WINDOW
#  
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")
root = ctk.CTk()
root.title("AI Chatbot Pro — Powered by Gemini")
root.geometry("1100x680+100+50")
root.minsize(820, 560)
root.configure(fg_color=T["bg"])

#   Circular avatars  
def make_circle(path, size=(38, 38)):
    img  = Image.open(path).convert("RGBA").resize(size, Image.LANCZOS)
    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).ellipse((0, 0)+size, fill=255)
    img.putalpha(mask)
    return ImageTk.PhotoImage(img)

user_avatar = make_circle(IMAGES_DIR / "user.jpg")
bot_avatar  = make_circle(IMAGES_DIR / "bot.jpg")

#  LAYOUT CONTAINERS  (created before any widgets that reference them)
 
sidebar   = ctk.CTkFrame(root, width=220, fg_color=T["bg2"], corner_radius=0)
sidebar.pack(side="left", fill="y")
sidebar.pack_propagate(False)

main_area = ctk.CTkFrame(root, fg_color=T["bg"], corner_radius=0)
main_area.pack(side="left", fill="both", expand=True)

top_bar   = ctk.CTkFrame(main_area, height=54, fg_color=T["bg2"], corner_radius=0)
top_bar.pack(fill="x")
top_bar.pack_propagate(False)

#   thinking bar (hidden until bot is processing)           
gif_path    = IMAGES_DIR / "robo.gif"
gif_obj     = Image.open(gif_path)
gif_frames  = [ImageTk.PhotoImage(f.convert("RGBA")) for f in ImageSequence.Iterator(gif_obj)]
gif_idx     = 0

thinking_bar    = ctk.CTkFrame(main_area, height=40, fg_color=T["bg3"], corner_radius=0)
thinking_canvas = ctk.CTkCanvas(thinking_bar, width=36, height=36,
                                 bg=T["bg3"], bd=0, highlightthickness=0)
thinking_canvas.pack(side="left", padx=8)
thinking_gif_id = thinking_canvas.create_image(0, 0, anchor="nw", image=gif_frames[0])
ctk.CTkLabel(thinking_bar, text="Gemini is thinking…",
             font=("Arial", 12, "italic"), text_color=T["text2"]).pack(side="left")

def _animate():
    global gif_idx
    gif_idx = (gif_idx + 1) % len(gif_frames)
    thinking_canvas.itemconfig(thinking_gif_id, image=gif_frames[gif_idx])
    root.after(80, _animate)
_animate()

chat_scroll = ctk.CTkScrollableFrame(main_area, fg_color=T["bg"],
                                      corner_radius=0,
                                      scrollbar_button_color=T["border"])
chat_scroll.pack(fill="both", expand=True)

bottom_bar  = ctk.CTkFrame(main_area, fg_color=T["bg2"], corner_radius=0, height=80)
bottom_bar.pack(fill="x", side="bottom")
bottom_bar.pack_propagate(False)

#  
#  TOAST  (must exist before sidebar buttons call show_toast)
#  
toast_lbl = ctk.CTkLabel(root, text="", font=("Arial", 12),
                          fg_color=T["bg4"], text_color=T["text"],
                          corner_radius=8, padx=14, pady=6)

def show_toast(msg, duration=2000):
    toast_lbl.configure(text=msg)
    toast_lbl.place(relx=0.5, rely=0.96, anchor="center")
    root.after(duration, toast_lbl.place_forget)

#  SIDEBAR
# Brand
bf = ctk.CTkFrame(sidebar, fg_color="transparent")
bf.pack(fill="x", padx=16, pady=(18, 8))
logo_box = ctk.CTkFrame(bf, width=44, height=44, fg_color=T["accent"], corner_radius=12)
logo_box.pack(side="left"); logo_box.pack_propagate(False)
ctk.CTkLabel(logo_box, text="AI", font=("Courier",16,"bold"),
             text_color="white").place(relx=.5, rely=.5, anchor="center")
brand_name = ctk.CTkLabel(bf, text="  Gemini Chat",
                           font=("Arial",16,"bold"), text_color=T["text"])
brand_name.pack(side="left")
ctk.CTkFrame(sidebar, height=1, fg_color=T["border"]).pack(fill="x", padx=12, pady=8)

#   Model selector   
ctk.CTkLabel(sidebar, text="MODEL", font=("Arial",10,"bold"),
             text_color=T["text2"]).pack(anchor="w", padx=16, pady=(4,4))

model_var  = ctk.StringVar(value="gemini-2.5-flash")
model_btns = {}

MODELS = [
    ("gemini-2.5-flash", "Gemini 2.5 Flash"),
    ("gemini-2.5-pro", "Gemini 2.5 Pro"),
    ("gemini-2.0-flash",   "Gemini 2.0 flash"),
]

def set_model(mid):
    global CURRENT_MODEL, chat_session
    CURRENT_MODEL = mid
    model_var.set(mid)
    chat_session  = client.chats.create(model=mid)
    for k, b in model_btns.items():
        b.configure(fg_color=T["accent"] if k == mid else T["bg3"],
                    text_color="white"   if k == mid else T["text2"])
    show_toast(f"Model: {mid}")

for mid, mlabel in MODELS:
    is_def = (mid == "gemini-2.5-flash")
    b = ctk.CTkButton(sidebar, text=mlabel, font=("Arial",12),
                      fg_color=T["accent"] if is_def else T["bg3"],
                      text_color="white"   if is_def else T["text2"],
                      hover_color=T["bg4"], corner_radius=8, height=32,
                      command=lambda m=mid: set_model(m))
    b.pack(fill="x", padx=12, pady=2)
    model_btns[mid] = b

ctk.CTkFrame(sidebar, height=1, fg_color=T["border"]).pack(fill="x", padx=12, pady=10)

#  Theme selector  
ctk.CTkLabel(sidebar, text="THEME", font=("Arial",10,"bold"),
             text_color=T["text2"]).pack(anchor="w", padx=16, pady=(0,4))

theme_grid = ctk.CTkFrame(sidebar, fg_color="transparent")
theme_grid.pack(fill="x", padx=12)

def apply_theme(name):
    global T
    T = THEMES[name]
    root.configure(fg_color=T["bg"])
    sidebar.configure(fg_color=T["bg2"])
    main_area.configure(fg_color=T["bg"])
    top_bar.configure(fg_color=T["bg2"])
    bottom_bar.configure(fg_color=T["bg2"])
    chat_scroll.configure(fg_color=T["bg"])
    entry_frame.configure(fg_color=T["entry_bg"])
    message_entry.configure(text_color=T["text"],
                             placeholder_text_color=T["text2"])
    brand_name.configure(text_color=T["text"])
    logo_box.configure(fg_color=T["accent"])
    toast_lbl.configure(fg_color=T["bg4"], text_color=T["text"])
    for k, b in model_btns.items():
        b.configure(fg_color=T["accent"] if k == model_var.get() else T["bg3"],
                    text_color="white"   if k == model_var.get() else T["text2"])
    show_toast(f"Theme: {name}")

for i, tname in enumerate(THEMES):
    ctk.CTkButton(
        theme_grid, text=tname[:4], width=58, height=30,
        fg_color=THEME_COLORS[tname], text_color="white",
        hover_color=THEME_COLORS[tname], corner_radius=8, font=("Arial",11),
        command=lambda n=tname: apply_theme(n)
    ).grid(row=i//3, column=i%3, padx=3, pady=3)

ctk.CTkFrame(sidebar, height=1, fg_color=T["border"]).pack(fill="x", padx=12, pady=10)

#   Settings toggles  
ctk.CTkLabel(sidebar, text="SETTINGS", font=("Arial",10,"bold"),
             text_color=T["text2"]).pack(anchor="w", padx=16, pady=(0,6))
sound_var      = ctk.BooleanVar(value=True)
autoscroll_var = ctk.BooleanVar(value=True)
ctk.CTkSwitch(sidebar, text="Sound Effects", font=("Arial",12),
              variable=sound_var, text_color=T["text"],
              progress_color=T["accent"]).pack(anchor="w", padx=16, pady=2)
ctk.CTkSwitch(sidebar, text="Auto Scroll", font=("Arial",12),
              variable=autoscroll_var, text_color=T["text"],
              progress_color=T["accent"]).pack(anchor="w", padx=16, pady=2)
ctk.CTkFrame(sidebar, height=1, fg_color=T["border"]).pack(fill="x", padx=12, pady=10)

#   Quick actions  
ctk.CTkLabel(sidebar, text="QUICK ACTIONS", font=("Arial",10,"bold"),
             text_color=T["text2"]).pack(anchor="w", padx=16, pady=(0,6))

def quick_action(prefix):
    message_entry.delete(0, "end")
    message_entry.insert(0, prefix)
    message_entry.focus()

for label, prefix in [
    ("💻  Write Code",  "Write clean Python code for: "),
    ("📝  Summarize",   "Summarize this in 3 points: "),
    ("🌐  Translate",   "Translate to English: "),
    ("💡  Explain",     "Explain simply: "),
    ("🔍  Research",    "Give a detailed overview of: "),
]:
    ctk.CTkButton(sidebar, text=label, font=("Arial",12), anchor="w",
                  fg_color="transparent", text_color=T["text2"],
                  hover_color=T["bg3"], height=30, corner_radius=6,
                  command=lambda p=prefix: quick_action(p)
    ).pack(fill="x", padx=10, pady=1)

#   Stats (bottom of sidebar)                 ─
ctk.CTkFrame(sidebar, height=1, fg_color=T["border"]).pack(side="bottom", fill="x", padx=12)
stats_frame = ctk.CTkFrame(sidebar, fg_color="transparent")
stats_frame.pack(side="bottom", fill="x", padx=16, pady=10)
msg_stat_lbl = ctk.CTkLabel(stats_frame, text="💬  0 messages",
                              font=("Arial",11), text_color=T["text2"])
msg_stat_lbl.pack(anchor="w")

#  
#  TOP BAR
#  
tl = ctk.CTkFrame(top_bar, fg_color="transparent")
tl.pack(side="left", padx=16)
status_dot = ctk.CTkLabel(tl, text="●", font=("Arial",14), text_color="#4ADE80")
status_dot.pack(side="left")
status_lbl = ctk.CTkLabel(tl, text=" Ready", font=("Arial",13), text_color=T["text"])
status_lbl.pack(side="left")

tr = ctk.CTkFrame(top_bar, fg_color="transparent")
tr.pack(side="right", padx=12)

def export_chat():
    if not chat_history_log:
        show_toast("Nothing to export"); return
    ts    = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    fname = BASE_DIR / f"chat_export_{ts}.txt"
    with open(fname, "w", encoding="utf-8") as f:
        f.write(f"AI Chatbot Export — {ts}\n{'='*50}\n\n")
        for e in chat_history_log:
            f.write(f"[{e['time']}] {e['role'].upper()}:\n{e['text']}\n\n")
    show_toast(f"Saved: chat_export_{ts}.txt")

def clear_chat():
    global message_count, chat_history_log, chat_session
    message_count = 0; chat_history_log = []
    for w in chat_scroll.winfo_children(): w.destroy()
    chat_session = client.chats.create(model=CURRENT_MODEL)
    msg_stat_lbl.configure(text="💬  0 messages")
    show_toast("Chat cleared!")

ctk.CTkButton(tr, text="🗑 Clear", width=80, height=32, font=("Arial",12),
              fg_color=T["bg3"], text_color=T["text"],
              hover_color="#3A1520", corner_radius=8,
              command=clear_chat).pack(side="left", padx=4)
ctk.CTkButton(tr, text="💾 Export", width=90, height=32, font=("Arial",12),
              fg_color=T["bg3"], text_color=T["text"],
              hover_color=T["bg4"], corner_radius=8,
              command=export_chat).pack(side="left", padx=4)

#  
#  BOTTOM BAR  (entry + buttons)
#  
entry_frame = ctk.CTkFrame(bottom_bar, fg_color=T["entry_bg"],
                            corner_radius=14, border_width=1,
                            border_color=T["border"])
entry_frame.pack(fill="x", padx=14, pady=12, side="left", expand=True)

message_entry = ctk.CTkEntry(
    entry_frame,
    placeholder_text="Message Gemini…  (Enter = send)",
    font=("Arial",13), fg_color="transparent", border_width=0,
    text_color=T["text"], placeholder_text_color=T["text2"], height=40
)
message_entry.pack(fill="x", padx=12, pady=4, side="left", expand=True)

btn_frame = ctk.CTkFrame(bottom_bar, fg_color="transparent")
btn_frame.pack(side="right", padx=10, pady=12)

# Mic button — defined before send_btn so we can reference it in listen()
mic_btn = ctk.CTkButton(btn_frame, text="🎤", width=44, height=44,
                         font=("Arial",18), corner_radius=12,
                         fg_color=T["bg3"], text_color=T["text"],
                         hover_color=T["bg4"],
                         command=lambda: threading.Thread(target=listen, daemon=True).start())
mic_btn.pack(side="left", padx=4)

#   send_btn uses a lambda so send_message() can be defined AFTER this line  
send_btn = ctk.CTkButton(btn_frame, text="➤", width=44, height=44,
                          font=("Arial",18), corner_radius=12,
                          fg_color=T["accent"], text_color="white",
                          hover_color=T["bg4"],
                          command=lambda: send_message())   # <  lambda fix
send_btn.pack(side="left", padx=4)

#  
#  HELPERS
#  
def add_message(text, role="user"):
    global message_count
    ts = datetime.datetime.now().strftime("%H:%M")
    chat_history_log.append({"role": role, "text": text, "time": ts})
    message_count += 1
    msg_stat_lbl.configure(text=f"💬  {message_count} messages")

    outer = ctk.CTkFrame(chat_scroll, fg_color="transparent")
    outer.pack(fill="x", pady=4, padx=12, anchor="e" if role=="user" else "w")

    av  = ctk.CTkLabel(outer, image=user_avatar if role=="user" else bot_avatar, text="")
    bub = ctk.CTkTextbox(
        outer, font=("Arial",13),
        fg_color=T["user_bubble"] if role=="user" else T["bot_bubble"],
        text_color="white" if role=="user" else T["text"],
        corner_radius=16,
        border_width=0 if role=="user" else 1,
        border_color=T["border"],
        wrap="word", activate_scrollbars=False, width=520
    )
    bub.insert("end", text)
    bub.configure(state="disabled",
                  height=max(36, (text.count("\n")+1+len(text)//65)*22+16))
    tl = ctk.CTkLabel(outer, text=ts, font=("Arial",9), text_color=T["text2"])

    if role == "user":
        tl.pack(side="bottom", anchor="e")
        bub.pack(side="right", anchor="e")
        av.pack(side="right", padx=(6,0), anchor="s")
    else:
        tl.pack(side="bottom", anchor="w")
        av.pack(side="left",  padx=(0,6), anchor="s")
        bub.pack(side="left", anchor="w")

    if autoscroll_var.get():
        root.after(60, lambda: chat_scroll._parent_canvas.yview_moveto(1.0))

def show_thinking(show: bool):
    if show:
        thinking_bar.pack(fill="x", after=top_bar)
        status_lbl.configure(text=" Thinking…")
        status_dot.configure(text_color=T["accent"])
        send_btn.configure(state="disabled")
    else:
        thinking_bar.pack_forget()
        status_lbl.configure(text=" Ready")
        status_dot.configure(text_color="#4ADE80")
        send_btn.configure(state="normal")

def speak(text):
    if sound_var.get():
        def _say():
            try: engine.say(text[:300]); engine.runAndWait()
            except Exception: pass
        threading.Thread(target=_say, daemon=True).start()

def listen():
    with sr.Microphone() as src:
        root.after(0, lambda: show_toast("🎤 Listening…"))
        root.after(0, lambda: mic_btn.configure(fg_color="#EF4444"))
        recognizer.adjust_for_ambient_noise(src, duration=0.5)
        try:
            audio = recognizer.listen(src, timeout=6)
            text  = recognizer.recognize_google(audio)
            root.after(0, lambda: (message_entry.delete(0,"end"),
                                   message_entry.insert(0, text)))
            root.after(0, lambda: show_toast(f"Heard: {text[:40]}"))
        except sr.UnknownValueError:
            root.after(0, lambda: show_toast("❌ Could not understand"))
        except sr.WaitTimeoutError:
            root.after(0, lambda: show_toast("⏱ No speech detected"))
        except Exception as e:
            root.after(0, lambda: show_toast(f"Mic error: {e}"))
        finally:
            root.after(0, lambda: mic_btn.configure(fg_color=T["bg3"]))

#  
#  AI RESPONSE (runs in background thread)
#  
def get_ai_response(message):
    root.after(0, lambda: show_thinking(True))
    try:
        ml = message.lower()

        if "open google and search for" in ml:
            q = ml.replace("open google and search for","").strip()
            webbrowser.open(f"https://www.google.com/search?q={q}")
            root.after(0, lambda: add_message(f"🔍 Searching Google for '{q}'","bot"))
            root.after(0, lambda: speak(f"Searching Google for {q}"))
            return

        if "open youtube for" in ml:
            q = ml.replace("open youtube for","").strip()
            webbrowser.open(f"https://www.youtube.com/results?search_query={q}")
            root.after(0, lambda: add_message(f"▶ YouTube search: '{q}'","bot"))
            return

        if "open video" in ml:
            q = ml.replace("open video","").strip()
            kit.playonyt(q)
            root.after(0, lambda: add_message(f"▶ Playing '{q}' on YouTube","bot"))
            return

        if "open website" in ml or "open url" in ml:
            url = ml.replace("open website","").replace("open url","").strip()
            if not url.startswith("http"): url = "https://"+url
            webbrowser.open(url)
            root.after(0, lambda: add_message(f"🌐 Opening {url}","bot"))
            return

        #   Gemini call (new SDK)                
        response = chat_session.send_message(message)
        reply    = response.text
        root.after(0, lambda r=reply: add_message(r, "bot"))
        root.after(0, lambda r=reply: speak(r))

    except Exception as e:
        err = str(e)
        root.after(0, lambda: add_message(f"⚠️ Error: {err}", "bot"))
    finally:
        root.after(0, lambda: show_thinking(False))

#  
#  SEND  (defined AFTER send_btn — the lambda above handles the forward ref)
#  
def send_message():
    text = message_entry.get().strip()
    if not text: return
    if text.lower() in ("bye","goodbye","exit","quit"):
        add_message("Goodbye! 👋", "bot")
        speak("Goodbye!")
        root.after(1500, root.quit)
        return
    message_entry.delete(0, "end")
    add_message(text, "user")
    threading.Thread(target=get_ai_response, args=(text,), daemon=True).start()

message_entry.bind("<Return>", lambda e: send_message() if not (e.state & 0x1) else None)

#  
#  WELCOME MESSAGE
#  
root.after(400, lambda: add_message(
    "👋 Hello! I'm your Gemini-powered AI assistant.\n\n"
    "Things I can do:\n"
    "• Answer any question / write & debug code\n"
    "• Search Google  →  'open google and search for Python tutorials'\n"
    "• Play YouTube   →  'open video lofi hip hop'\n"
    "• Open websites  →  'open website github.com'\n\n"
    "Pick a theme or model from the sidebar. Let's go! 🚀", "bot"
))

root.mainloop()