import re
import os
import tkinter as tk
from tkinter import messagebox, font as tkfont, Menu
# from tkinter.ttk import *
import random
from tkinter import filedialog
import webbrowser
import json
from tkinter import simpledialog  # Add import for simpledialog
from tkinter import colorchooser  # Add import for colorchooser

# Add DPI awareness
try:
    from ctypes import windll
    windll.shcore.SetProcessDpiAwareness(1)
except:
    pass

if os.name == 'nt':  # Windows
    CONFIG_DIR = os.path.join(os.getenv('USERPROFILE'), 'Documents', 'MemoHelper')
else:  # Unix-like (Linux, macOS, etc.)
    CONFIG_DIR = os.path.join(os.path.expanduser('~'), '.memo_helper')

os.makedirs(CONFIG_DIR, exist_ok=True)
CONFIG_FILE = os.path.join(CONFIG_DIR, '.memo_helper_config.json')

def load_config():
    try:
        with open(CONFIG_FILE, 'r') as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_config(config):
    with open(CONFIG_FILE, 'w') as file:
        json.dump(config, file)

def read_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.readlines()
    except FileNotFoundError:
        messagebox.showerror("Error", f"File not found: {file_path}")
        return []

class SectionTitle:
    def __init__(self, level, title):
        self.level = level
        self.title = title
        self.subsections = []

    def add_subsection(self, subsection):
        self.subsections.append(subsection)

class Entry:
    def __init__(self, indent_level, title, content, section_titles):
        self.indent_level = indent_level
        self.title = title
        self.content = content
        self.section_titles = section_titles

def parse_entries(lines):
    entries = []
    section_stack = []
    for line in lines:
        line = line.rstrip()
        if re.match(r'^#+\s*(.*)', line):
            level = len(re.match(r'^#+', line).group())
            title = re.match(r'^#+\s*(.*)', line).group(1).strip()
            while section_stack and section_stack[-1].level >= level:
                section_stack.pop()
            new_section = SectionTitle(level, title)
            if section_stack:
                section_stack[-1].add_subsection(new_section)
            section_stack.append(new_section)
        match = re.match(r'^\s*([-•\d]+)\s*(.*?)(：|:)(.*)', line)
        if match:
            indent_level = len(re.match(r'^\s*', line).group())
            title = match.group(2).strip()
            content = match.group(4).strip()
            content = content.replace('；', '；\n').replace('。', '。\n')
            section_titles = [section.title for section in section_stack]
            entries.append(Entry(indent_level, title, content, section_titles))
        elif re.match(r'^\s*[-•\d]+\s*(.*)', line):
            indent_level = len(re.match(r'^\s*', line).group())
            content = re.match(r'^\s*[-•\d]+\s*(.*)', line).group(1).strip()
            content = content.replace('；', '；\n').replace('。', '。\n')
            section_titles = [section.title for section in section_stack]
            entries.append(Entry(indent_level, None, content, section_titles))
    return entries

class Theme:
    def __init__(self, name, bg, fg, troughcolor, section_fg, section_bg, title_fg, title_bg, content_fg, content_bg, list_fg, list_bg):
        self.name = name
        self.bg = bg
        self.fg = fg
        self.troughcolor = troughcolor
        self.section_fg = section_fg
        self.section_bg = section_bg
        self.title_fg = title_fg
        self.title_bg = title_bg
        self.content_fg = content_fg
        self.content_bg = content_bg
        self.list_fg = list_fg
        self.list_bg = list_bg

    def apply(self, app):
        app.root.config(bg=self.bg)
        app.section_label.config(bg=self.section_bg, fg=self.section_fg)
        app.title_label.config(bg=self.title_bg, fg=self.title_fg)
        app.content_frame.config(bg=self.bg)
        app.list_frame.config(bg=self.bg)
        app.jump_listbox.config(bg=self.list_bg, fg=self.list_fg)
        app.content_text.config(bg=self.content_bg, fg=self.content_fg)
        app.button_frame.config(bg=self.bg)
        app.show_hide_button.config(bg=self.bg, fg=self.fg)
        app.prev_button.config(bg=self.bg, fg=self.fg)
        app.next_button.config(bg=self.bg, fg=self.fg)
        app.random_button.config(bg=self.bg, fg=self.fg)
        app.jump_scrollbar.config(bg=self.bg, troughcolor=self.troughcolor)

class MemoHelperApp:
    def __init__(self, root, entries):
        self.root = root
        self.entries = entries
        self.index = 0
        self.showing_content = False
        self.always_show = tk.BooleanVar()
        self.scrollbar_visible = tk.BooleanVar(value=True)
        self.content_folder = os.path.dirname(os.path.abspath(__file__))
        self.always_on_top = tk.BooleanVar()
        self.search_engine = tk.StringVar(value="Google")
        self.compact_mode = tk.BooleanVar()
        self.always_show_checkbutton = None  # Initialize the variable
        self.current_theme = tk.StringVar(value="default")  # Use StringVar for theme
        self.layout_mode = tk.StringVar(value="normal")  # Use StringVar for layout mode
        self.last_opened_entry = tk.IntVar(value=0)  # Track the last opened entry index
        self.min_content_length = tk.IntVar(value=0)  # Add a variable for minimum content length
        self.visibility_mode = tk.StringVar(value="show_list_and_scrollbar")  # Add a variable for visibility mode
        self.mouse_interaction_enabled = tk.BooleanVar(value=False)  # Add variable for mouse interaction
        self.title_font_family = tk.StringVar(value="SimSun")
        self.text_font_family = tk.StringVar(value="SimSun")
        self.title_bold = tk.BooleanVar(value=False)
        self.text_bold = tk.BooleanVar(value=False)

        self.config = load_config()
        self.recent_files = self.config.get("recent_files", [])
        self.custom_themes = self.load_custom_themes(self.config.get("custom_themes", {}))

        self.title_XL_font = tkfont.Font(family="SimSun", size=32, weight="normal")
        self.title_L_font = tkfont.Font(family="SimSun", size=18, weight="normal")
        self.title_M_font = tkfont.Font(family="SimSun", size=14, weight="normal")
        self.title_S_font = tkfont.Font(family="SimSun", size=10, weight="normal")
        self.context_XL_font = tkfont.Font(family="SimSun", size=32, weight="normal")
        self.context_L_font = tkfont.Font(family="SimSun", size=18, weight="normal")
        self.context_M_font = tkfont.Font(family="SimSun", size=14, weight="normal")
        self.context_S_font = tkfont.Font(family="SimSun", size=10, weight="normal")

        self.section_label = tk.Label(root, text="", font=self.title_S_font, wraplength=800, height=1)
        self.section_label.pack(pady=(15, 0))

        self.title_label = tk.Label(root, text="", font=self.title_L_font, wraplength=700, height=3)
        self.title_label.pack(pady=0)
        self.title_label.bind("<Button-1>", self.hide_content)

        self.content_frame = tk.Frame(root)
        self.content_frame.pack(pady=10, fill=tk.BOTH, expand=True)
        
        self.content_text = tk.Text(self.content_frame, wrap=tk.WORD, height=15, width=50, font=self.context_M_font)
        self.content_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(10, 10), pady=(10, 0))  # Adjust padding

        self.list_frame = tk.Frame(self.content_frame)
        self.list_frame.pack(side=tk.LEFT, padx=10, pady=(10, 0), fill=tk.Y)  # Adjust padding

        self.jump_listbox = tk.Listbox(self.list_frame, height=15, width=25)  # Adjust width
        self.jump_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.jump_scrollbar = tk.Scrollbar(self.list_frame, orient=tk.VERTICAL, command=self.jump_listbox.yview)
        self.jump_listbox.config(yscrollcommand=self.jump_scrollbar.set)
        self.jump_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.jump_listbox.bind("<Button-1>", self.jump_to_entry)

        self.button_frame = tk.Frame(root)
        self.button_frame.pack(pady=10)

        button_options = {'width': 10, 'height': 2}

        self.random_button = tk.Button(self.button_frame, text="Random", command=self.show_random_entry, **button_options)
        self.random_button.pack(side=tk.TOP, padx=5, pady=(0, 5))

        self.prev_button = tk.Button(self.button_frame, text="◀", command=self.show_previous, **button_options)
        self.prev_button.pack(side=tk.LEFT, padx=5)

        self.show_hide_button = tk.Button(self.button_frame, text="Show", command=self.toggle_content, **button_options)
        self.show_hide_button.pack(side=tk.LEFT, padx=5)

        self.next_button = tk.Button(self.button_frame, text="▶", command=self.show_next, **button_options)
        self.next_button.pack(side=tk.LEFT, padx=5)

        self.create_menu()
        
        self.themes = {
            "default": Theme("default", "SystemButtonFace", "black", "lightgray", "black", "SystemButtonFace", "black", "SystemButtonFace", "black", "SystemButtonFace", "black", "SystemButtonFace"),
            "light": Theme("light", "white", "black", "lightgray", "black", "white", "black", "white", "black", "white", "black", "white"),
            "dark": Theme("dark", "#1E1E1E", "#F3F3F3", "gray", "#F3F3F3", "#1E1E1E", "#F3F3F3", "#1E1E1E", "#F3F3F3", "#1E1E1E", "#F3F3F3", "#1E1E1E"),
            "green": Theme("green", "#8FBF8F", "#252D1E", "lightgray", "#252D1E", "#8FBF8F", "#252D1E", "#8FBF8F", "#252D1E", "#8FBF8F", "#252D1E", "#8FBF8F"),
            "dark_blue": Theme("dark_blue", "#2A3338", "#CFD1D2", "lightgray", "#CFD1D2", "#2A3338", "#CFD1D2", "#2A3338", "#CFD1D2", "#2A3338", "#CFD1D2", "#2A3338")
        }
        self.themes.update(self.custom_themes)
        
        self.set_default_mode()  # Set default mode on startup
        self.show_entry()

        self.bind_keys()
        self.create_context_menu()
        
        self.apply_config()  # Apply configuration after UI components are initialized
        self.load_files()  # Load files from the configured content folder
        self.apply_visibility_mode()  # Apply visibility mode after loading files

        # Automatically open the first file if available
        self.try_open_default_file()
        
        self.late_apply_config()  # Apply configuration after the first file is loaded

    def load_custom_themes(self, custom_themes_dict):
        custom_themes = {}
        for name, theme_dict in custom_themes_dict.items():
            custom_themes[name] = Theme(**theme_dict)
        return custom_themes

    def set_theme(self, theme_name):
        theme = self.themes.get(theme_name, self.themes["default"])
        theme.apply(self)
        self.current_theme.set(theme_name)

    def apply_config(self):
        # ...existing code...
        self.always_show.set(self.config.get("always_show", False))
        self.scrollbar_visible.set(self.config.get("scrollbar_visible", True))
        self.always_on_top.set(self.config.get("always_on_top", False))
        self.search_engine.set(self.config.get("search_engine", "Google"))
        self.content_folder = self.config.get("content_folder", os.path.dirname(os.path.abspath(__file__)))
        self.set_theme(self.config.get("theme", "default"))
        self.last_opened_file = self.config.get("last_opened_file", None)
        self.layout_mode.set(self.config.get("layout_mode", "normal"))
        self.min_content_length.set(self.config.get("min_content_length", 0))  # Load min content length from config
        self.visibility_mode.set(self.config.get("visibility_mode", "show_list_and_scrollbar"))  # Load visibility mode from config
        self.mouse_interaction_enabled.set(self.config.get("mouse_interaction_enabled", False))  # Load mouse interaction setting
        self.title_font_family.set(self.config.get("title_font_family", "Times New Roman"))
        self.text_font_family.set(self.config.get("text_font_family", "Times New Roman"))
        self.title_bold.set(self.config.get("title_bold", False))
        self.text_bold.set(self.config.get("text_bold", False))
        self.update_fonts()
        if self.layout_mode.get() == "compact":
            self.set_compact_mode()
        elif self.layout_mode.get() == "wide":
            self.set_wide_mode()
        else:
            self.set_normal_mode()
        self.apply_visibility_mode()  # Apply visibility mode
        self.toggle_scrollbar()
        self.toggle_always_on_top()
        self.apply_mouse_interaction()  # Apply mouse interaction setting
        
    def late_apply_config(self):
        self.index = (self.config.get("last_opened_entry", 0))
        if self.index > 0 and self.index < len(self.entries):
            self.show_entry()
        else:
            self.index = 0
            self.show_entry()

    def save_current_config(self):
        self.config["always_show"] = self.always_show.get()
        self.config["scrollbar_visible"] = self.scrollbar_visible.get()
        self.config["always_on_top"] = self.always_on_top.get()
        self.config["search_engine"] = self.search_engine.get()
        self.config["content_folder"] = self.content_folder
        self.config["theme"] = self.current_theme.get()  # Save the current theme
        self.config["layout_mode"] = self.layout_mode.get()  # Save the current layout mode
        self.config["last_opened_file"] = self.last_opened_file
        self.config["last_opened_entry"] = self.index
        self.config["recent_files"] = self.recent_files
        self.config["min_content_length"] = self.min_content_length.get()  # Save min content length to config
        self.config["visibility_mode"] = self.visibility_mode.get()  # Save visibility mode to config
        self.config["mouse_interaction_enabled"] = self.mouse_interaction_enabled.get()  # Save mouse interaction setting
        self.config["title_font_family"] = self.title_font_family.get()
        self.config["text_font_family"] = self.text_font_family.get()
        self.config["title_bold"] = self.title_bold.get()
        self.config["text_bold"] = self.text_bold.get()
        self.config["custom_themes"] = {name: theme.__dict__ for name, theme in self.custom_themes.items()}
        save_config(self.config)

    def try_open_default_file(self):
        if self.last_opened_file and os.path.exists(self.last_opened_file):
            self.load_selected_file_from_menu(os.path.basename(self.last_opened_file))
            self.show_entry()
        else:
            files = [f for f in os.listdir(self.content_folder) if f.startswith('N') and f.endswith('.md')]
            if files:
                self.load_selected_file_from_menu(files[0])
            else:
                self.show_guide()  # Show guide when no file is loaded

    def create_menu(self):
        menu_bar = Menu(self.root)
        self.root.config(menu=menu_bar)

        file_menu = Menu(menu_bar, tearoff=0)
        self.file_menu = file_menu
        menu_bar.add_cascade(label="File", menu=file_menu)

        file_submenu = Menu(file_menu, tearoff=0)
        self.file_submenu = file_submenu
        self.file_menu.add_command(label="Open File...", command=self.open_file)
        self.recent_files_menu = Menu(self.file_menu, tearoff=0)
        self.file_menu.add_cascade(label="Recent Files", menu=self.recent_files_menu)
        
        file_menu.add_separator()

        self.file_menu.add_command(label="File Folder...", command=self.set_file_folder)
        self.load_files()
        file_menu.add_cascade(label="Select File in Folder", menu=file_submenu)
        
        self.update_recent_files_menu()

        edit_menu = Menu(menu_bar, tearoff=0)
        menu_bar.add_cascade(label="Edit", menu=edit_menu, )
        
        self.always_show_checkbutton = edit_menu.add_checkbutton(label="Always Show Content", variable=self.always_show)
        edit_menu.add_checkbutton(label="Enable Mouse Interaction", variable=self.mouse_interaction_enabled, command=self.apply_mouse_interaction)
        
        edit_menu.add_separator()
        edit_menu.add_command(label=f"Set Min Content Length", command=self.set_min_content_length)  # Add menu item for setting min content length
        
        edit_menu.add_separator()

        search_engine_menu = Menu(edit_menu, tearoff=0)
        edit_menu.add_cascade(label="Search Engine", menu=search_engine_menu)
        search_engine_menu.add_radiobutton(label="Google", variable=self.search_engine, value="Google")
        search_engine_menu.add_radiobutton(label="Bing", variable=self.search_engine, value="Bing")
        search_engine_menu.add_radiobutton(label="DuckDuckGo", variable=self.search_engine, value="DuckDuckGo")
        
        edit_menu.add_separator()
        edit_menu.add_command(label="Save Config", command=self.save_current_config)

        view_menu = Menu(menu_bar, tearoff=0)
        menu_bar.add_cascade(label="View", menu=view_menu, )
        
        layout_menu = Menu(view_menu, tearoff=0)
        view_menu.add_cascade(label="Layout", menu=layout_menu)
        layout_menu.add_command(label="Normal", command=self.set_normal_mode)
        layout_menu.add_command(label="Compact", command=self.set_compact_mode)
        layout_menu.add_command(label="Wide", command=self.set_wide_mode)

        view_menu.add_separator()
        theme_menu = Menu(view_menu, tearoff=0)
        view_menu.add_cascade(label="Theme", menu=theme_menu, )
        theme_menu.add_command(label="Default", command=self.set_default_mode)
        theme_menu.add_command(label="Light", command=self.set_light_mode)
        theme_menu.add_command(label="Dark", command=self.set_dark_mode)
        theme_menu.add_command(label="Green", command=self.set_green_mode)
        theme_menu.add_command(label="Dark Blue", command=self.set_dark_blue_mode)
        if self.custom_themes:
            theme_menu.add_separator()
            for theme_name in self.custom_themes:
                theme_menu.add_command(label=theme_name, command=lambda name=theme_name: self.set_theme(name))
        theme_menu.add_separator()
        theme_menu.add_command(label="Create Theme", command=self.create_theme)
        theme_menu.add_command(label="Modify Theme", command=self.modify_theme)  # Add modify theme option
        theme_menu.add_command(label="Delete Theme", command=self.delete_theme)

        font_menu = Menu(edit_menu, tearoff=0)
        view_menu.add_cascade(label="Font", menu=font_menu)
        font_menu.add_command(label="Set Title Font", command=self.set_title_font)
        font_menu.add_command(label="Set Text Font", command=self.set_text_font)
        font_menu.add_separator()
        font_menu.add_checkbutton(label="Bold Title Font", variable=self.title_bold, command=self.update_fonts)
        font_menu.add_checkbutton(label="Bold Text Font", variable=self.text_bold, command=self.update_fonts)
        
        view_menu.add_separator()
        visibility_menu = Menu(view_menu, tearoff=0)
        view_menu.add_cascade(label="List Visibility", menu=visibility_menu)
        visibility_menu.add_radiobutton(label="Show List and Scrollbar", variable=self.visibility_mode, value="show_list_and_scrollbar", command=self.show_list_and_scrollbar)
        visibility_menu.add_radiobutton(label="Show List Only", variable=self.visibility_mode, value="show_list_only", command=self.show_list_only)
        visibility_menu.add_radiobutton(label="Hide List", variable=self.visibility_mode, value="hide_list", command=self.hide_list)
        
        view_menu.add_separator()
        view_menu.add_checkbutton(label="Sticky on Top", variable=self.always_on_top, command=self.toggle_always_on_top)

        help_menu = Menu(menu_bar, tearoff=0)
        menu_bar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="Show Guide", command=self.show_guide)

    def show_guide(self):
        guide_title = "User Guide"
        guide_content_en = (
            "Welcome to Memorax!\n\n"
            "Memorax is a simple tool for reviewing .md files.\n\n"
            "1. Use the 'File' menu to select and load .md files.\n"
            "2. Navigate through entries using the '◀' and '▶' buttons.\n"
            "3. Use the 'Random' button to display a random entry.\n"
            "4. Toggle content visibility with the 'Show'/'Hide' button.\n"
            "5. Customize the appearance using the 'View' menu.\n"
            "6. Search selected text on the web using the context menu.\n"
            "7. Save your settings using the 'Save Config' option in the 'File' menu.\n\n"
            "Your content in .md files should be like:\n"
            "# My Note\n"
            "### Chapter 1 - Overview\n"
            "- Note1: Content1\n"
            "- Note2: Content2\n"
            "......\n"
        )
        guide_content_cn = (
            "欢迎使用 Memorax！\n\n"
            "1. 使用“文件”菜单选择并加载 .md 文件。\n"
            "2. 使用“◀”和“▶”按钮浏览条目。\n"
            "3. 使用“随机”按钮显示随机条目�����\n"
            "4. 使用“显示”/“隐藏”按钮切换内容可见性。\n"
            "5. 使用“视图”菜单自定义外观。\n"
            "6. 使用右键菜单在 Web 上搜索选定的文本。\n"
            "7. 使用“文件”菜单中的“保存配置”选项保存您的设置。\n\n"
            "加载的 .md 文件内容应该为如下格式：\n"
            "# 我的笔记\n"
            "### 第一章：概述\n"
            "- 条目1: 内容1\n"
            "- 条目2: 内容2\n"
            "......\n"
        )
        guide_content = guide_content_en + "\n\n" + guide_content_cn

        guide_window = tk.Toplevel(self.root)
        guide_window.title(guide_title)
        guide_window.geometry("800x1200")

        guide_text = tk.Text(guide_window, wrap=tk.WORD, font=self.context_M_font)
        guide_text.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)
        guide_text.insert(tk.END, guide_content)
        guide_text.config(state=tk.DISABLED)

        close_button = tk.Button(guide_window, text="Close", command=guide_window.destroy)
        close_button.pack(pady=10)

    def set_light_mode(self):
        self.set_theme("light")

    def set_dark_mode(self):
        self.set_theme("dark")

    def set_default_mode(self):
        self.set_theme("default")

    def set_green_mode(self):
        self.set_theme("green")
        
    def set_dark_blue_mode(self):
        self.set_theme("dark_blue")

    def set_normal_mode(self):
        # Show list_frame and button_frame only if visibility mode is not "hide_list"
        if self.visibility_mode.get() != "hide_list":
            self.list_frame.pack(side=tk.LEFT, padx=10, pady=(10, 0), fill=tk.Y)
        self.button_frame.pack(pady=10)
        self.section_label.config(wraplength=950, height=1, font=self.title_S_font)
        self.title_label.config(wraplength=1000, height=3, font=self.title_L_font)
        self.jump_listbox.config(height=15, width=25)
        self.content_text.config(height=15, width=50, font=self.context_M_font)
        self.show_hide_button.config(width=10, height=2)
        self.prev_button.config(width=10, height=2)
        self.next_button.config(width=10, height=2)
        self.random_button.config(width=10, height=2)
        self.layout_mode.set("normal")
        self.apply_mouse_interaction()  # Apply mouse interaction setting

    def set_compact_mode(self):
        # Show list_frame and button_frame only if visibility mode is not "hide_list"
        if self.visibility_mode.get() != "hide_list":
            self.list_frame.pack(side=tk.LEFT, padx=10, pady=(10, 0), fill=tk.Y)
        self.button_frame.pack(pady=10)
        self.section_label.config(wraplength=500, height=1, font=self.title_S_font)
        self.title_label.config(wraplength=500, height=3, font=self.title_M_font)
        self.jump_listbox.config(height=10, width=20)
        self.content_text.config(height=10, width=30, font=self.context_S_font)
        self.show_hide_button.config(width=8, height=1)
        self.prev_button.config(width=8, height=1)
        self.next_button.config(width=8, height=1)
        self.random_button.config(width=8, height=1)
        self.layout_mode.set("compact")
        self.apply_mouse_interaction()  # Apply mouse interaction setting

    def set_wide_mode(self):
        # Show list_frame and button_frame only if visibility mode is not "hide_list"
        if self.visibility_mode.get() != "hide_list":
            self.list_frame.pack(side=tk.LEFT, padx=10, pady=(10, 0), fill=tk.Y)
        self.button_frame.pack(pady=10)
        # Adjust section_label and title_label
        self.section_label.config(wraplength=1500, height=2, font=self.title_L_font)
        self.title_label.config(wraplength=1500, height=3, font=self.title_XL_font)
        # Adjust content_text
        self.content_text.config(height=15, width=64, font=self.context_XL_font)
        self.layout_mode.set("wide")
        self.apply_mouse_interaction()  # Apply mouse interaction setting

    def toggle_list_visibility(self):
        if self.list_frame.winfo_ismapped():
            self.list_frame.pack_forget()
        else:
            self.list_frame.pack(side=tk.LEFT, padx=10, pady=(10, 0), fill=tk.Y)

    def toggle_compact_mode(self):
        if self.compact_mode.get():
            self.set_compact_mode()
        else:
            self.set_normal_mode()
        self.save_current_config()

    def toggle_scrollbar(self):
        if self.scrollbar_visible.get():
            self.jump_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        else:
            self.jump_scrollbar.pack_forget()

    def bind_keys(self):
        self.root.bind('<d>', lambda event: self.show_next())
        self.root.bind('<Right>', lambda event: self.show_next())
        self.root.bind('<a>', lambda event: self.show_previous())
        self.root.bind('<Left>', lambda event: self.show_previous())
        self.root.bind('<w>', lambda event: self.show_random_entry())
        self.root.bind('<Up>', lambda event: self.show_random_entry())
        self.root.bind('<space>', lambda event: self.toggle_content())
        self.root.bind('<Down>', lambda event: self.toggle_content())
        self.root.bind('<s>', lambda event: self.toggle_content())

    def load_files(self):
        self.file_submenu.delete(0, tk.END)
        files = [f for f in os.listdir(self.content_folder) if f.startswith('N') and f.endswith('.md')]
        for file in files:
            self.file_submenu.add_command(label=file, command=lambda f=file: self.load_selected_file_from_menu(f))

    def load_selected_file_from_menu(self, file_name):
        try:
            file_path = os.path.join(self.content_folder, file_name)
            lines = read_file(file_path)
            if lines:
                self.entries = parse_entries(lines)
                self.index = 0
                self.show_entry()
                self.jump_listbox.delete(0, tk.END)
                for i, entry in enumerate(self.entries):
                    title = entry.title if entry.title else entry.content
                    self.jump_listbox.insert(tk.END, f"{i+1}. {title}")
                self.last_opened_file = file_path
        except IndexError:
            messagebox.showerror("Error", "Please select a valid file.")

    def load_selected_file(self, file_path):
        try:
            lines = read_file(file_path)
            if lines:
                self.entries = parse_entries(lines)
                self.index = 0
                self.show_entry()
                self.jump_listbox.delete(0, tk.END)
                for i, entry in enumerate(self.entries):
                    title = entry.title if entry.title else entry.content
                    self.jump_listbox.insert(tk.END, f"{i+1}. {title}")
                self.last_opened_file = file_path
        except IndexError:
            messagebox.showerror("Error", "Please select a valid file.")

    def handle_click(self, event):
        if (event.widget == self.root):
            if event.x < self.root.winfo_width() // 2:
                self.show_previous()
            else:
                self.show_next()

    def show_entry(self):
        if self.index < 0 or self.index >= len(self.entries):
            return
        entry = self.entries[self.index]
        title = entry.title.replace('\n', ' ') if entry.title else entry.content.replace('\n', ' ')
        self.title_label.config(text=title if title else entry.content)
        self.content_text.delete(1.0, tk.END)
        self.showing_content = False
        self.jump_listbox.selection_clear(0, tk.END)
        self.jump_listbox.selection_set(self.index)
        self.jump_listbox.see(self.index)

        # Directly display content if title and content are the same or content is empty
        if entry.title == entry.content or not entry.content or self.always_show.get():
            if not entry.content:
                entry.content = "No Content"
            self.content_text.insert(tk.END, entry.content)
            self.showing_content = True
            self.show_hide_button.config(text="Hide")
        else:
            # Ensure proper alignment for entries without title
            self.title_label.config(height=3)
            self.show_hide_button.config(text="Show")

        # Update section label
        if entry.section_titles:
            self.root.title("Memorax - ".join(("", entry.section_titles[0])))
            section_title = " > ".join(entry.section_titles[1:])
        else:
            self.root.title("Memorax")
            section_title = ""
        self.section_label.config(text=section_title)

    def display_content(self):
        entry = self.entries[self.index]
        content = entry.content if entry.content else "No Content"
        self.content_text.insert(tk.END, content)
        self.showing_content = True
        self.show_hide_button.config(text="Hide")

    def toggle_content(self):
        if self.showing_content:
            self.hide_content()
            self.show_hide_button.config(text="Show")
        else:
            self.display_content()
            self.show_hide_button.config(text="Hide")

    def show_next(self):
        self.index = (self.index + 1) % len(self.entries)
        self.show_entry()

    def show_previous(self):
        self.index = (self.index - 1) % len(self.entries)
        self.show_entry()

    def hide_content(self, event=None):
        self.content_text.delete(1.0, tk.END)
        self.showing_content = False
        self.show_hide_button.config(text="Show")

    def jump_to_entry(self, event):
        try:
            index = self.jump_listbox.nearest(event.y)
            self.index = index
            self.show_entry()
        except IndexError:
            messagebox.showerror("Error", "Please select a valid entry.")

    def show_random_entry(self):
        valid_entries = [i for i, entry in enumerate(self.entries) if len(entry.content) >= self.min_content_length.get()]
        if valid_entries:
            self.index = random.choice(valid_entries)
            self.show_entry()
        else:
            messagebox.showinfo("Info", f"No entries with content longer than {self.min_content_length.get()} characters.")

    def toggle_always_on_top(self):
        self.root.attributes("-topmost", self.always_on_top.get())

    def create_context_menu(self):
        self.context_menu = Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="Search on Web", command=self.search_on_web)
        self.context_menu.add_separator()
        self.context_menu.add_checkbutton(label="Always Show Content", variable=self.always_show)
        self.context_menu.add_checkbutton(label="Enable Mouse Interaction", variable=self.mouse_interaction_enabled, command=self.apply_mouse_interaction)
        self.context_menu.add_separator()
        self.context_menu.add_checkbutton(label="Sticky on Top", variable=self.always_on_top, command=self.toggle_always_on_top)
        self.jump_listbox.bind("<Button-3>", self.show_context_menu)
        self.content_text.bind("<Button-3>", self.show_context_menu)

    def show_context_menu(self, event):
        try:
            self.context_menu.selection = event.widget.selection_get()
        except tk.TclError:
            self.context_menu.selection = None
        self.context_menu.post(event.x_root, event.y_root)

    def search_on_web(self):
        if self.context_menu.selection:
            query = self.context_menu.selection
        else:
            entry = self.entries[self.index]
            query = entry.title if entry.title else entry.content

        search_engine = self.search_engine.get()
        if search_engine == "Google":
            url = f"https://www.google.com/search?q={query}"
        elif search_engine == "Bing":
            url = f"https://www.bing.com/search?q={query}"
        elif search_engine == "DuckDuckGo":
            url = f"https://duckduckgo.com/?q={query}"
        
        webbrowser.open(url)

    def on_closing(self):
        self.save_current_config()
        self.root.destroy()

    def set_file_folder(self):
        folder_selected = filedialog.askdirectory()
        if folder_selected:
            self.content_folder = folder_selected
            self.load_files()
        self.save_current_config()

    def open_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("Markdown files", "*.md")])
        if file_path:
            self.load_selected_file(file_path)
            self.add_to_recent_files(file_path)

    def add_to_recent_files(self, file_path):
        if file_path in self.recent_files:
            self.recent_files.remove(file_path)
        self.recent_files.insert(0, file_path)
        self.recent_files = self.recent_files[:10]  # Keep only the last 10 entries
        self.update_recent_files_menu()
        self.save_current_config()

    def update_recent_files_menu(self):
        self.recent_files_menu.delete(0, tk.END)
        for file_path in self.recent_files:
            if os.path.exists(file_path):
                self.recent_files_menu.add_command(label=file_path, command=lambda fp=file_path: self.load_selected_file(fp))

    def set_min_content_length(self):
        def save_length():
            try:
                length = int(entry.get())
                self.min_content_length.set(length)
                self.save_current_config()
                
                dialog.destroy()
            except ValueError:
                messagebox.showerror("Error", "Please enter a valid number.")

        dialog = tk.Toplevel(self.root)
        dialog.title(f"Set Random Content Min Length")
        tk.Label(dialog, text="Min content length for random entries").pack(pady=10)
        entry = tk.Entry(dialog)
        entry.pack(pady=5)
        entry.insert(0, str(self.min_content_length.get()))
        tk.Button(dialog, text="Save", command=save_length).pack(pady=10)

    def show_list_and_scrollbar(self):
        self.list_frame.pack(side=tk.LEFT, padx=10, pady=(10, 0), fill=tk.Y)
        self.jump_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.visibility_mode.set("show_list_and_scrollbar")

    def show_list_only(self):
        self.list_frame.pack(side=tk.LEFT, padx=10, pady=(10, 0), fill=tk.Y)
        self.jump_scrollbar.pack_forget()
        self.visibility_mode.set("show_list_only")

    def hide_list(self):
        self.list_frame.pack_forget()
        self.visibility_mode.set("hide_list")

    def apply_visibility_mode(self):
        mode = self.visibility_mode.get()
        if (mode == "show_list_and_scrollbar"):
            self.show_list_and_scrollbar()
        elif (mode == "show_list_only"):
            self.show_list_only()
        elif (mode == "hide_list"):
            self.hide_list()

    def apply_mouse_interaction(self):
        if self.mouse_interaction_enabled.get():
            self.root.bind('<Button-1>', self.on_left_click)
            self.root.bind_all('<MouseWheel>', self.on_mouse_wheel)
            self.root.bind('<Button-4>', self.on_mouse_wheel_up)  # For Linux
            self.root.bind('<Button-5>', self.on_mouse_wheel_down)  # For Linux
            self.root.bind('<Button-2>', self.on_middle_click)  # Bind middle mouse button
        else:
            self.root.unbind('<Button-1>')
            self.root.unbind_all('<MouseWheel>')
            self.root.unbind('<Button-4>')
            self.root.unbind('<Button-5>')
            self.root.unbind('<Button-2>')  # Unbind middle mouse button

    def on_left_click(self, event):
        self.toggle_content()

    def on_mouse_wheel(self, event):
        if event.delta > 0:
            self.show_previous()
        else:
            self.show_next()

    def on_mouse_wheel_up(self, event):
        self.show_previous()

    def on_mouse_wheel_down(self, event):
        self.show_next()

    def on_middle_click(self, event):
        self.show_random_entry()

    def set_title_font(self):
        def save_font():
            selected_font = font_listbox.get(tk.ACTIVE)
            if selected_font:
                self.title_font_family.set(selected_font)
                self.update_fonts()
                self.save_current_config()
                self.apply_fonts()
            dialog.destroy()

        dialog = tk.Toplevel(self.root)
        dialog.title("Set Title Font")

        tk.Label(dialog, text="Select title font family:").pack(pady=10)
        font_var = tk.StringVar(dialog)
        font_var.set(self.title_font_family.get())

        font_frame = tk.Frame(dialog)
        font_frame.pack(pady=5, fill=tk.BOTH, expand=True)

        font_listbox = tk.Listbox(font_frame, height=10)
        font_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = tk.Scrollbar(font_frame, orient=tk.VERTICAL, command=font_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        font_listbox.config(yscrollcommand=scrollbar.set)

        for font in tkfont.families():
            font_listbox.insert(tk.END, font)

        tk.Button(dialog, text="Save", command=save_font).pack(pady=10)

    def set_text_font(self):
        def save_font():
            selected_font = font_listbox.get(tk.ACTIVE)
            if selected_font:
                self.text_font_family.set(selected_font)
                self.update_fonts()
                self.save_current_config()
                self.apply_fonts()
            dialog.destroy()

        dialog = tk.Toplevel(self.root)
        dialog.title("Set Text Font")

        tk.Label(dialog, text="Select text font family:").pack(pady=10)
        font_var = tk.StringVar(dialog)
        font_var.set(self.text_font_family.get())

        font_frame = tk.Frame(dialog)
        font_frame.pack(pady=5, fill=tk.BOTH, expand=True)

        font_listbox = tk.Listbox(font_frame, width=30, height=20)
        font_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = tk.Scrollbar(font_frame, orient=tk.VERTICAL, command=font_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        font_listbox.config(yscrollcommand=scrollbar.set)

        for font in tkfont.families():
            font_listbox.insert(tk.END, font)

        tk.Button(dialog, text="Save", command=save_font).pack(pady=10)

    def update_fonts(self):
        def is_font_installed(font_name):
            return font_name in tkfont.families()
        
        default_font_family = "SimHei"
        title_font_family = self.title_font_family.get()
        text_font_family = self.text_font_family.get()

        if not is_font_installed(title_font_family):
            title_font_family = default_font_family
        if not is_font_installed(text_font_family):
            text_font_family = default_font_family

        title_weight = "bold" if self.title_bold.get() else "normal"
        text_weight = "bold" if self.text_bold.get() else "normal"

        self.title_XL_font = tkfont.Font(family=title_font_family, size=32, weight=title_weight)
        self.title_L_font = tkfont.Font(family=title_font_family, size=18, weight=title_weight)
        self.title_M_font = tkfont.Font(family=title_font_family, size=14, weight=title_weight)
        self.title_S_font = tkfont.Font(family=title_font_family, size=10, weight=title_weight)
        self.context_XL_font = tkfont.Font(family=text_font_family, size=32, weight=text_weight)
        self.context_L_font = tkfont.Font(family=text_font_family, size=18, weight=text_weight)
        self.context_M_font = tkfont.Font(family=text_font_family, size=14, weight=text_weight)
        self.context_S_font = tkfont.Font(family=text_font_family, size=10, weight=text_weight)
        self.apply_fonts()  # Apply the new fonts immediately

    def apply_fonts(self):
        self.section_label.config(font=self.title_S_font)
        self.title_label.config(font=self.title_L_font)
        self.content_text.config(font=self.context_M_font)
        self.show_entry()

    def create_theme(self, modify=False, theme_name=None):
        def choose_color(entry, color_block):
            color_code = colorchooser.askcolor(title="Choose color", initialcolor=entry.get())[1]
            if color_code:
                entry.delete(0, tk.END)
                entry.insert(0, color_code)
                color_block.config(bg=color_code)

        def save_theme():
            name = name_entry.get()
            if not modify and name in self.themes:
                messagebox.showerror("Error", "Theme name already exists.")
                return
            # Ensure all color fields are filled
            if not all([bg_entry.get(), fg_entry.get(), troughcolor_entry.get(), section_fg_entry.get(), section_bg_entry.get(), title_fg_entry.get(), title_bg_entry.get(), content_fg_entry.get(), content_bg_entry.get(), list_fg_entry.get(), list_bg_entry.get()]):
                messagebox.showerror("Error", "All color fields must be filled.")
                return
            theme = Theme(
                name,
                bg_entry.get(),
                fg_entry.get(),
                troughcolor_entry.get(),
                section_fg_entry.get(),
                section_bg_entry.get(),
                title_fg_entry.get(),
                title_bg_entry.get(),
                content_fg_entry.get(),
                content_bg_entry.get(),
                list_fg_entry.get(),
                list_bg_entry.get()
            )
            if modify:
                del self.custom_themes[theme_name]
                del self.themes[theme_name]
            self.custom_themes[name] = theme
            self.themes[name] = theme
            self.save_current_config()
            self.create_menu()  # Update the menu to include the new theme
            self.set_theme(name)  # Apply the new or modified theme immediately
            dialog.destroy()

        dialog = tk.Toplevel(self.root)
        dialog.title("Modify Theme" if modify else "Create Theme")

        tk.Label(dialog, text="Name").grid(row=0, column=0)
        name_entry = tk.Entry(dialog)
        name_entry.grid(row=0, column=1)

        def create_color_picker_row(label_text, row, default_color):
            tk.Label(dialog, text=label_text).grid(row=row, column=0)
            entry = tk.Entry(dialog)
            entry.grid(row=row, column=1)
            entry.insert(0, default_color)
            color_block = tk.Label(dialog, width=2, height=1, bg=default_color, relief="solid")
            color_block.grid(row=row, column=2, padx=5)
            color_block.bind("<Button-1>", lambda e: choose_color(entry, color_block))
            return entry

        if modify and theme_name:
            current_theme = self.themes[theme_name]
            name_entry.insert(0, theme_name)
            name_entry.config(state='disabled')
        else:
            current_theme_name = self.current_theme.get()
            current_theme = self.themes.get(current_theme_name, self.themes["default"])

        bg_entry = create_color_picker_row("Background", 1, current_theme.bg)
        fg_entry = create_color_picker_row("Foreground", 2, current_theme.fg)
        troughcolor_entry = create_color_picker_row("Trough Color", 3, current_theme.troughcolor)
        section_fg_entry = create_color_picker_row("Section Foreground", 4, current_theme.section_fg)
        section_bg_entry = create_color_picker_row("Section Background", 5, current_theme.section_bg)
        title_fg_entry = create_color_picker_row("Title Foreground", 6, current_theme.title_fg)
        title_bg_entry = create_color_picker_row("Title Background", 7, current_theme.title_bg)
        content_fg_entry = create_color_picker_row("Content Foreground", 8, current_theme.content_fg)
        content_bg_entry = create_color_picker_row("Content Background", 9, current_theme.content_bg)
        list_fg_entry = create_color_picker_row("List Foreground", 10, current_theme.list_fg)
        list_bg_entry = create_color_picker_row("List Background", 11, current_theme.list_bg)

        tk.Button(dialog, text="Save", command=save_theme).grid(row=12, column=0, columnspan=3)

    def modify_theme(self):
        def select_theme():
            theme_name = theme_var.get()
            if theme_name in self.custom_themes:
                dialog.destroy()
                self.create_theme(modify=True, theme_name=theme_name)
            else:
                messagebox.showerror("Error", "Cannot modify predefined themes.")

        dialog = tk.Toplevel(self.root)
        dialog.title("Modify Theme")

        theme_var = tk.StringVar(dialog)
        theme_var.set("Select Theme")
        theme_options = [name for name in self.themes if name in self.custom_themes]

        tk.OptionMenu(dialog, theme_var, *theme_options).pack()
        tk.Button(dialog, text="Modify", command=select_theme).pack()

    def delete_theme(self):
        def delete_selected_theme():
            name = theme_var.get()
            if name in self.custom_themes:
                del self.custom_themes[name]
                del self.themes[name]
                self.save_current_config()
                self.create_menu()  # Update the menu to remove the deleted theme
                dialog.destroy()
            else:
                messagebox.showerror("Error", "Cannot delete predefined themes.")

        dialog = tk.Toplevel(self.root)
        dialog.title("Delete Theme")

        theme_var = tk.StringVar(dialog)
        theme_var.set("Select Theme")
        theme_options = [name for name in self.themes if name in self.custom_themes]

        tk.OptionMenu(dialog, theme_var, *theme_options).pack()
        tk.Button(dialog, text="Delete", command=delete_selected_theme).pack()

def main():
    root = tk.Tk()
    root.title("Memorax")
    app = MemoHelperApp(root, [])
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()

if __name__ == "__main__":
    main()