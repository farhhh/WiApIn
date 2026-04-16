import customtkinter as ctk
import requests
from tkhtmlview import HTMLLabel
import threading
import markdown2
import re
import sys
import os
import tempfile
import shutil
import hashlib
import subprocess
import time
from io import BytesIO
from PIL import Image
from tkinter import messagebox
import tkinter as tk

# Настройки репозитория
GITHUB_USER = "farhhh"
GITHUB_REPO = "WiApIn"
BASE_RAW_URL = f"https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}/main"
API_URL = f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/contents"

def resource_path(relative_path):
    """ Получает абсолютный путь к ресурсу, работает для dev и для PyInstaller """
    try:
        # PyInstaller создает временную папку и хранит путь в _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

class ScriptInfoWindow(ctk.CTkToplevel):
    def __init__(self, master, title, text):
        super().__init__(master)
        self.title(f"Инструкция: {title}")
        self.geometry("600x400")
        self.after(10, self.lift)

        self.textbox = ctk.CTkTextbox(self, font=("Segoe UI", 14), activate_scrollbars=True)
        self.textbox.pack(expand=True, fill="both", padx=20, pady=20)
        self.textbox.insert("0.0", text)
        self.textbox.configure(state="disabled")

        self.btn_close = ctk.CTkButton(self, text="Закрыть", command=self.destroy)
        self.btn_close.pack(pady=(0, 20))

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("WiApIn - Помощник по установке")
        icon_path = resource_path("icon.ico")
        if os.path.exists(icon_path):
            self.iconbitmap(icon_path)
        self.geometry("1280x800")
        self.temp_dir = tempfile.mkdtemp(prefix="wiapin_cache_")

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.nocache_headers = {
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Pragma': 'no-cache',
            'Expires': '0',
            'User-Agent': 'WiApIn-App'
        }

        self.all_apps = [] # Хранилище для полного списка (для поиска)


        # --- Панель управления ---
        self.sidebar = ctk.CTkFrame(self, width=220, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
            
        self.logo_label = ctk.CTkLabel(self.sidebar, text="WiApIn", font=ctk.CTkFont(size=24, weight="bold"))
        self.logo_label.pack(pady=30)

        self.btn_instr = ctk.CTkButton(self.sidebar, text="Инструкции", command=self.show_instructions_list, height=40)
        self.btn_instr.pack(pady=10, padx=20, fill="x")

        self.btn_scripts = ctk.CTkButton(self.sidebar, text="Скрипты", command=self.show_scripts_section, height=40)
        self.btn_scripts.pack(pady=10, padx=20, fill="x")

        # КНОПКА ПРИЛОЖЕНИЯ ТЕПЕРЬ РАБОТАЕТ
        self.btn_apps = ctk.CTkButton(self.sidebar, text="Приложения", command=self.show_apps_section, height=40)
        self.btn_apps.pack(pady=10, padx=20, fill="x")

        # --- Контент ---
        self.main_container = ctk.CTkFrame(self, corner_radius=15)
        self.main_container.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")

        self.search_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.search_entry = ctk.CTkEntry(self.search_frame, placeholder_text="Поиск приложений...", width=300)
        self.search_entry.pack(side="left", padx=10)
        self.search_entry.bind("<KeyRelease>", self._on_search_change)

        self.search_frame.pack_forget()

        self.search_timer = None
            
        self.top_bar = ctk.CTkFrame(self.main_container, fg_color="transparent", height=50)
        self.top_bar.pack(fill="x", padx=10, pady=5)
        self.top_bar.pack_forget()

        self.back_btn = ctk.CTkButton(self.top_bar, text="← Назад", command=self.show_welcome, width=140)
        self.back_btn.pack(side="left", padx=10)

        self.scroll_frame = ctk.CTkScrollableFrame(self.main_container, fg_color="transparent")
        self.scroll_frame.pack(expand=True, fill="both", padx=5, pady=5)

        self.html_view = HTMLLabel(self.main_container, html="", background="#2b2b2b")
        self.copy_menu = tk.Menu(self, tearoff=0, bg="#333333", fg="white", borderwidth=0)
        self.copy_menu.add_command(label="Копировать", command=self._copy_html_text)

        self.html_view.bind("<Control-c>", self._copy_html_text)
        self.html_view.bind("<Control-C>", self._copy_html_text)
        self.html_view.bind("<<Copy>>", self._copy_html_text)
        self.html_view.bind("<Button-3>", self._show_context_menu)
        self.html_view.bind("<Control-KeyPress>", self._fallback_copy)
        self.html_view.bind("<Key>", self._prevent_typing)

        self.show_welcome()
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    # --- ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ (Копирование, Очистка и т.д.) ---
    def _show_context_menu(self, event):
        try:
            if self.html_view.tag_ranges("sel"):
                self.copy_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.copy_menu.grab_release()

    def _copy_html_text(self, event=None):
        try:
            selected_text = self.html_view.get("sel.first", "sel.last")
            if selected_text:
                self.clipboard_clear()
                self.clipboard_append(selected_text)
                self.update()
        except tk.TclError: pass
        return "break"

    def _fallback_copy(self, event):
        keysym = getattr(event, 'keysym', '').lower()
        keycode = getattr(event, 'keycode', 0)
        if keysym == 'cyrillic_es' or keycode in (67, 54):
            return self._copy_html_text(event)

    def _prevent_typing(self, event):
        if event.state & 4 or event.keysym in ('Up', 'Down', 'Left', 'Right', 'Home', 'End', 'Prior', 'Next'):
            return None
        return "break"

    def clear_main_area(self):
        self.top_bar.pack_forget()
        self.scroll_frame.pack_forget()
        self.html_view.pack_forget()
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()

    def show_welcome(self):
        self.clear_main_area()
        self.scroll_frame.pack(expand=True, fill="both")
        label = ctk.CTkLabel(self.scroll_frame, text="Добро пожаловать в WiApIn\nВыберите раздел слева", font=("Segoe UI", 20))
        label.pack(pady=200)

    # --- РАЗДЕЛ ПРИЛОЖЕНИЙ (НОВОЕ) ---

    def show_apps_section(self):
        self.clear_main_area()
        self.search_frame.pack(fill="x", padx=20, pady=(10, 0)) # Показываем поиск
        self.scroll_frame.pack(expand=True, fill="both")
        loading = ctk.CTkLabel(self.scroll_frame, text="⏳ Синхронизация репозитория...")
        loading.pack(pady=20)
        threading.Thread(target=self._load_apps_worker, daemon=True).start()

    def _load_apps_worker(self):
        try:
            ts = str(int(time.time()))
            r = requests.get(f"{API_URL}/Apps?t={ts}", headers=self.nocache_headers, timeout=10)
            if r.status_code == 200:
                self.all_apps = [f['name'].replace(".txt", "") for f in r.json() if f['name'].endswith('.txt')]
                self.after(0, lambda: self.render_apps_list(self.all_apps))
        except: pass

    def render_apps_list(self, app_names, is_searching=False):
        # Очищаем только список, не трогая поиск
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()
        
        if not is_searching:
            ctk.CTkLabel(self.scroll_frame, text="🚀 Магазин приложений", font=("Segoe UI", 24, "bold")).pack(pady=10)

        for name in app_names:
            self._create_app_row(name)

    def _create_app_row(self, name):
        row = ctk.CTkFrame(self.scroll_frame, fg_color="#333333", height=100)
        row.pack(fill="x", padx=20, pady=10)
        
        # 1. Иконка (загружается в отдельном потоке)
        icon_label = ctk.CTkLabel(row, text="⌛", width=60, height=60)
        icon_label.pack(side="left", padx=15, pady=10)
        threading.Thread(target=self._load_icon, args=(name, icon_label), daemon=True).start()

        # 2. Название приложения
        name_lbl = ctk.CTkLabel(row, text=name, font=("Segoe UI", 16, "bold"), width=200, anchor="w")
        name_lbl.pack(side="left", padx=10)

        # 3. Кнопка "Инструкция"
        info_btn = ctk.CTkButton(row, text="Инструкция", width=110, fg_color="#444444", 
                                command=lambda n=name: self._show_app_details(n))
        info_btn.pack(side="left", padx=10)

        # 4. Кнопка "Скачать" (или "Открыть")
        down_btn = ctk.CTkButton(row, text="Скачать", width=110, fg_color="#1f538d")
        down_btn.pack(side="right", padx=15)

        # 5. Прогресс-бар (изначально скрыт, пакуется при нажатии "Скачать")
        p_bar = ctk.CTkProgressBar(row, height=4)
        p_bar.set(0)

        # --- УНИВЕРСАЛЬНАЯ ПРОВЕРКА НАЛИЧИЯ ФАЙЛА ---
        desktop_path = os.path.join(os.path.expanduser("~"), "Desktop", "Приложения WiApIn")
        
        # Список расширений, которые могут быть у твоих файлов
        extensions = ['.exe', '.zip', '.rar', '.7z', '.msi', '.tar.gz']
        file_exists = False
        
        if os.path.exists(desktop_path):
            for ext in extensions:
                if os.path.exists(os.path.join(desktop_path, f"{name}{ext}")):
                    file_exists = True
                    break
        
        # Если файл найден — меняем вид кнопки на "Открыть"
        if file_exists:
            down_btn.configure(text="Открыть", fg_color="#28a745")
        
        # Привязываем команду скачивания (логика внутри сама решит, открывать папку или качать)
        down_btn.configure(command=lambda: self._start_app_download(name, down_btn, p_bar))

    def _load_icon(self, name, label):
        try:
            url = f"{BASE_RAW_URL}/Apps/{name}.png?t={int(time.time())}"
            res = requests.get(url, timeout=5)
            if res.status_code == 200:
                img_data = BytesIO(res.content)
                img = Image.open(img_data)
                ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(60, 60))
                
                # Используем безопасную функцию для отрисовки
                def safe_set():
                    try:
                        if label.winfo_exists():
                            label.configure(image=ctk_img, text="")
                    except: 
                        pass # Виджет уже мертв, и бог с ним
                
                self.after(0, safe_set)
            else:
                self.after(0, lambda: label.configure(text="❌") if label.winfo_exists() else None)
        except:
            pass

    def _show_app_details(self, name):
        """Парсим TXT и показываем описание"""
        try:
            url = f"{BASE_RAW_URL}/Apps/{name}.txt?t={int(time.time())}"
            r = requests.get(url, timeout=5)
            r.encoding = 'utf-8'
            if r.status_code == 200:
                lines = r.text.split('\n')
                # 0 - ссылка, 1 - размер, 2+ - описание
                description = "\n".join(lines[2:]) if len(lines) > 2 else "Нет описания."
                size_info = lines[1] if len(lines) > 1 else "Неизвестно"
                full_text = f"Размер: {size_info}\n\n{description}"
                ScriptInfoWindow(self, name, full_text)
        except:
            messagebox.showerror("Ошибка", "Не удалось загрузить инфо")

    def _start_app_download(self, name, button, progress_bar):
        if button.cget("text") == "Открыть":
            path = os.path.join(os.path.expanduser("~"), "Desktop", "Приложения WiApIn")
            os.startfile(path)
            return

        def downloader():
            try:
                # 1. Получаем инфо из TXT
                url_res = requests.get(f"{BASE_RAW_URL}/Apps/{name}.txt?t={int(time.time())}", timeout=5)
                if url_res.status_code != 200: return
                
                # Чистим ссылку от лишних пробелов и переносов
                download_url = url_res.text.split('\n')[0].strip()
                
                # --- ИСПРАВЛЕНИЕ ТУТ: Определяем расширение из ссылки ---
                # Извлекаем путь из URL (без параметров ?t=...) и берем расширение
                pure_url = download_url.split('?')[0]
                extension = os.path.splitext(pure_url)[1] 
                
                # Если вдруг в ссылке нет расширения, по умолчанию ставим .exe
                if not extension:
                    extension = ".exe"
                
                filename = f"{name}{extension}" 

                dest_dir = os.path.join(os.path.expanduser("~"), "Desktop", "Приложения WiApIn")
                if not os.path.exists(dest_dir): os.makedirs(dest_dir)
                target_path = os.path.join(dest_dir, filename)

                # --- ДАЛЕЕ ЛОГИКА ОСТАЕТСЯ ПРЕЖНЕЙ ---
                existing_size = os.path.getsize(target_path) if os.path.exists(target_path) else 0
                headers = self.nocache_headers.copy()
                if existing_size > 0:
                    headers['Range'] = f'bytes={existing_size}-'
                
                def start_ui():
                    if button.winfo_exists() and progress_bar.winfo_exists():
                        progress_bar.pack(side="bottom", fill="x", padx=10, pady=(0, 5))
                        button.configure(state="disabled", text="Синхронизация...")

                self.after(0, start_ui)

                mode = 'ab' if existing_size > 0 else 'wb'
                
                with requests.get(download_url, stream=True, headers=headers, timeout=15) as r:
                    if r.status_code == 416: 
                        self.after(0, lambda: self._finish_download(button, progress_bar, name))
                        return

                    total_size = int(r.headers.get('content-length', 0)) + existing_size
                    downloaded = existing_size
                    
                    def set_loading_text():
                        if button.winfo_exists():
                            button.configure(text="Загрузка...")
                    self.after(0, set_loading_text)

                    with open(target_path, mode) as f:
                        for chunk in r.iter_content(chunk_size=1024*1024):
                            if chunk:
                                f.write(chunk)
                                downloaded += len(chunk)
                                if total_size > 0:
                                    percent = downloaded / total_size
                                    def update_p(p=percent):
                                        if progress_bar.winfo_exists():
                                            progress_bar.set(p)
                                    self.after(0, update_p)

                self.after(0, lambda: self._finish_download(button, progress_bar, name))

            except Exception as e:
                def on_error():
                    if button.winfo_exists():
                        button.configure(state="normal", text="Скачать")
                    print(f"Error: {e}")
                self.after(0, on_error)

        threading.Thread(target=downloader, daemon=True).start()

    def _on_search_change(self, event):
        # Если таймер уже запущен — отменяем его (сброс при новом нажатии)
        if self.search_timer:
            self.after_cancel(self.search_timer)
        
        # Запускаем новый таймер на 300мс
        self.search_timer = self.after(300, self._execute_search)

    def _execute_search(self):
        query = self.search_entry.get().lower()
        if not query:
            self.render_apps_list(self.all_apps)
            return
            
        filtered = [name for name in self.all_apps if query in name.lower()]
        self.render_apps_list(filtered, is_searching=True)

    def _finish_download(self, button, progress_bar, name):
        if progress_bar.winfo_exists() and button.winfo_exists():
            progress_bar.set(1)
            progress_bar.configure(progress_color="#28a745")
            button.configure(state="normal", text="Открыть", fg_color="#28a745")
            messagebox.showinfo("WiApIn", f"Загрузка {name} завершена!")

    # --- ОСТАЛЬНЫЕ МЕТОДЫ (Скрипты, Инструкции) ---
    # (Здесь остаются твои методы load_scripts_worker, render_scripts_list и т.д. из прошлого кода)
    
    def show_scripts_section(self):
        self.clear_main_area()
        self.clear_temp_cache() 
        self.scroll_frame.pack(expand=True, fill="both")
        loading = ctk.CTkLabel(self.scroll_frame, text="⏳ Загрузка скриптов...")
        loading.pack(pady=20)
        threading.Thread(target=self._load_scripts_worker, daemon=True).start()

    def clear_temp_cache(self):
        try:
            for filename in os.listdir(self.temp_dir):
                file_path = os.path.join(self.temp_dir, filename)
                if os.path.isfile(file_path): os.unlink(file_path)
                elif os.path.isdir(file_path): shutil.rmtree(file_path)
        except: pass

    def _load_scripts_worker(self):
        try:
            ts = str(int(time.time()))
            r = requests.get(f"{API_URL}/Scripts?t={ts}", headers=self.nocache_headers, timeout=10)
            if r.status_code == 200:
                files = [f['name'] for f in r.json() if f['name'].endswith('.ps1')]
                self.after(0, lambda: self.render_scripts_list(files))
        except: pass

    def render_scripts_list(self, scripts):
        self.clear_main_area()
        self.scroll_frame.pack(expand=True, fill="both")
        ctk.CTkLabel(self.scroll_frame, text="🛠️ Доступные скрипты", font=("Segoe UI", 22, "bold")).pack(pady=20)
        for script_file in scripts:
            s_name = script_file.replace(".ps1", "")
            row = ctk.CTkFrame(self.scroll_frame, fg_color="#333333")
            row.pack(fill="x", padx=20, pady=5)
            name_lbl = ctk.CTkLabel(row, text=s_name, font=("Segoe UI", 14, "bold"), width=200, anchor="w")
            name_lbl.pack(side="left", padx=15, pady=10)
            ctk.CTkButton(row, text="Инструкция", width=100, fg_color="#444444", command=lambda s=s_name: self.show_script_info(s)).pack(side="left", expand=True)
            ctk.CTkButton(row, text="▶ Запустить", width=100, fg_color="#28a745", command=lambda sf=script_file: self.run_ps_script(sf)).pack(side="right", padx=15)

    def show_script_info(self, name):
        def load():
            import base64
            try:
                api_file_url = f"{API_URL}/Scripts/{name}.txt"
                r = requests.get(f"{api_file_url}?t={int(time.time())}", timeout=5)
                if r.status_code == 200:
                    data = r.json()
                    txt = base64.b64decode(data.get('content', '')).decode('utf-8')
                    self.after(0, lambda: ScriptInfoWindow(self, name, txt))
                else:
                    self.after(0, lambda: messagebox.showinfo("Инфо", "Инструкция не найдена."))
            except: pass
        threading.Thread(target=load, daemon=True).start()

    def run_ps_script(self, filename):
        def worker():
            path = os.path.join(self.temp_dir, filename)
            try:
                r = requests.get(f"{BASE_RAW_URL}/Scripts/{filename}?t={int(time.time())}", timeout=15)
                if r.status_code == 200:
                    with open(path, "w", encoding="utf-8-sig") as f: f.write(r.text)
                    ps_command = f"Start-Process powershell.exe -ArgumentList '-ExecutionPolicy Bypass -File \"{path}\"' -Verb RunAs -Wait"
                    subprocess.run(["powershell.exe", "-Command", ps_command], creationflags=subprocess.CREATE_NO_WINDOW)
                    self.after(0, lambda: messagebox.showinfo("Успех", "Скрипт выполнен!"))
            except: pass
        threading.Thread(target=worker, daemon=True).start()

    def show_instructions_list(self):
        self.clear_main_area()
        self.scroll_frame.pack(expand=True, fill="both")
        loading = ctk.CTkLabel(self.scroll_frame, text="⏳ Загрузка инструкций...")
        loading.pack(pady=20)
        threading.Thread(target=self._load_instr_worker, daemon=True).start()

    def _load_instr_worker(self):
        try:
            r = requests.get(f"{API_URL}/Instructions?t={int(time.time())}", headers=self.nocache_headers, timeout=10)
            if r.status_code == 200:
                files = [item['name'] for item in r.json() if item['name'].endswith('.md')]
                self.after(0, lambda: self.render_instr_buttons(files))
        except: pass

    def render_instr_buttons(self, files):
        self.clear_main_area()
        self.scroll_frame.pack(expand=True, fill="both")
        ctk.CTkLabel(self.scroll_frame, text="📖 Инструкции", font=("Segoe UI", 22, "bold")).pack(pady=20)
        for f in files:
            btn = ctk.CTkButton(self.scroll_frame, text=f.replace(".md", ""), height=50, command=lambda fn=f: self.open_instruction(fn))
            btn.pack(pady=8, padx=60, fill="x")

    def open_instruction(self, file_name):
        self.clear_main_area()
        self.top_bar.pack(fill="x", padx=10, pady=5)
        self.scroll_frame.pack(expand=True, fill="both")
        loading = ctk.CTkLabel(self.scroll_frame, text="Загрузка...")
        loading.pack(pady=20)
        threading.Thread(target=self._read_md_worker, args=(file_name, loading), daemon=True).start()

    def _read_md_worker(self, file_name, loading_label):
        import base64
        try:
            r = requests.get(f"{API_URL}/Instructions/{file_name}?t={int(time.time())}", timeout=10)
            if r.status_code == 200:
                data = r.json()
                md_text = base64.b64decode(data.get('content', '').replace('\n', '')).decode('utf-8')
                html_body = markdown2.markdown(md_text, extras=["tables"])
                styled = f"<body bgcolor='#2b2b2b' text='#ffffff' style='font-family: Segoe UI; padding: 20px;'>{html_body}</body>"
                styled = styled.replace("<p>", "<p style='color: #ffffff;'>").replace("<li>", "<li style='color: #ffffff;'>")
                self.after(0, lambda: self.display_html(styled, loading_label))
        except: pass

    def display_html(self, html, label):
        label.destroy()
        self.scroll_frame.pack_forget()
        self.html_view.pack(expand=True, fill="both", padx=10, pady=10)
        self.html_view.set_html(html)
        self.html_view.configure(state="normal", selectbackground="#005fb8", selectforeground="white", inactiveselectbackground="#005fb8", insertofftime=0)
        self.html_view.tag_configure("sel", background="#005fb8", foreground="white")
        self.html_view.tag_raise("sel")
        self.html_view.focus_set()

    def on_closing(self):
        try: shutil.rmtree(self.temp_dir, ignore_errors=True)
        except: pass
        self.destroy()

if __name__ == "__main__":
    ctk.set_appearance_mode("dark") 
    app = App()
    app.mainloop()
