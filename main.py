import customtkinter as ctk
import requests
from tkhtmlview import HTMLLabel
import threading
import markdown2
import re
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
        self.geometry("1280x800")
        self.temp_dir = tempfile.mkdtemp(prefix="wiapin_cache_")

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Стандартные заголовки для обхода кэша
        self.nocache_headers = {
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Pragma': 'no-cache',
            'Expires': '0',
            'User-Agent': 'WiApIn-App'
        }

        # --- Панель управления ---
        self.sidebar = ctk.CTkFrame(self, width=220, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
            
        self.logo_label = ctk.CTkLabel(self.sidebar, text="WiApIn", font=ctk.CTkFont(size=24, weight="bold"))
        self.logo_label.pack(pady=30)

        self.btn_instr = ctk.CTkButton(self.sidebar, text="Инструкции", command=self.show_instructions_list, height=40)
        self.btn_instr.pack(pady=10, padx=20, fill="x")

        self.btn_scripts = ctk.CTkButton(self.sidebar, text="Скрипты", command=self.show_scripts_section, height=40)
        self.btn_scripts.pack(pady=10, padx=20, fill="x")

        self.btn_apps = ctk.CTkButton(self.sidebar, text="Приложения", state="disabled", height=40)
        self.btn_apps.pack(pady=10, padx=20, fill="x")

        # --- Контент ---
        self.main_container = ctk.CTkFrame(self, corner_radius=15)
        self.main_container.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")
            
        self.top_bar = ctk.CTkFrame(self.main_container, fg_color="transparent", height=50)
        self.top_bar.pack(fill="x", padx=10, pady=5)
        self.top_bar.pack_forget()

        self.back_btn = ctk.CTkButton(self.top_bar, text="← Назад к списку", command=self.show_instructions_list, width=140)
        self.back_btn.pack(side="left", padx=10)

        self.scroll_frame = ctk.CTkScrollableFrame(self.main_container, fg_color="transparent")
        self.scroll_frame.pack(expand=True, fill="both", padx=5, pady=5)

        # --- Создаем HTML виджет (ВАЖНО: До биндов и меню!) ---
        self.html_view = HTMLLabel(
            self.main_container, 
            html="", 
            background="#2b2b2b",
            selectbackground="#1f538d", # Цвет заливки выделения (синий)
            selectforeground="white"    # Цвет текста при выделении
        )
        
        # Настраиваем контекстное меню
        self.copy_menu = tk.Menu(self, tearoff=0, bg="#333333", fg="white", borderwidth=0)
        self.copy_menu.add_command(label="Копировать", command=self._copy_html_text)

        # Привязываем события (Клавиатура + Правая кнопка мыши)
        self.html_view.bind("<Control-c>", self._copy_html_text)
        self.html_view.bind("<Control-C>", self._copy_html_text)
        self.html_view.bind("<Button-3>", self._show_context_menu)

        self.show_welcome()
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def _show_context_menu(self, event):
        try:
            # Показываем меню только если есть выделенный текст
            if self.html_view.tag_ranges("sel"):
                self.copy_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.copy_menu.grab_release()

    def _copy_html_text(self, event=None):
        try:
            # Ищем выделенный текст напрямую через стандартный тег tkinter "sel"
            selected_text = self.html_view.get("sel.first", "sel.last")
            if selected_text:
                self.clipboard_clear()
                self.clipboard_append(selected_text)
                self.update() # Важно для синхронизации с системным буфером
        except tk.TclError:
            # Если выделения нет, просто ничего не делаем
            pass
        return "break" # Это останавливает дальнейшее распространение события

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

    # --- СКРИПТЫ ---

    def show_scripts_section(self):
        self.clear_main_area()
        # ШАГ 1: Полная очистка локального кэша перед запросом
        self.clear_temp_cache() 
        
        self.scroll_frame.pack(expand=True, fill="both")
        loading = ctk.CTkLabel(self.scroll_frame, text="⏳ Очистка кэша и загрузка скриптов...")
        loading.pack(pady=20)
        threading.Thread(target=self._load_scripts_worker, daemon=True).start()

    def clear_temp_cache(self):
        """Удаляет все файлы в кэше, чтобы исключить чтение старых данных с диска"""
        try:
            for filename in os.listdir(self.temp_dir):
                file_path = os.path.join(self.temp_dir, filename)
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
        except Exception as e:
            print(f"Ошибка очистки кэша: {e}")

    def _load_scripts_worker(self):
        try:
            # Используем новую сессию для каждого обновления
            with requests.Session() as s:
                ts = str(int(time.time()))
                r = s.get(f"{API_URL}/Scripts?t={ts}", headers=self.nocache_headers, timeout=10)
                if r.status_code == 200:
                    files = [f['name'] for f in r.json() if f['name'].endswith('.ps1')]
                    self.after(0, lambda: self.render_scripts_list(files))
                else:
                    self.after(0, lambda: self.show_error("Сервер GitHub временно недоступен"))
        except:
            self.after(0, lambda: self.show_error("Ошибка сети"))

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

            instr_btn = ctk.CTkButton(row, text="Инструкция", width=100, height=30, 
                                      fg_color="#444444", hover_color="#555555",
                                      command=lambda s=s_name: self.show_script_info(s))
            instr_btn.pack(side="left", expand=True)

            run_btn = ctk.CTkButton(row, text="▶ Запустить", width=100, height=30, 
                                    fg_color="#28a745", hover_color="#218838",
                                    command=lambda sf=script_file: self.run_ps_script(sf))
            run_btn.pack(side="right", padx=15)

    def show_script_info(self, name):
        """Загрузка инструкции через GitHub API (самый быстрый способ обновления)"""
        def load():
            import base64
            try:
                # Стучимся напрямую в API, а не в Raw
                api_file_url = f"{API_URL}/Scripts/{name}.txt"
                ts = str(int(time.time()))
                
                # Добавляем авторизацию, если есть токен (необязательно, но API любит заголовки)
                headers = {
                    'Authorization': f'token {self.github_token}' if hasattr(self, 'github_token') else '',
                    'Accept': 'application/vnd.github.v3+json',
                    'Cache-Control': 'no-cache',
                    'User-Agent': 'WiApIn-App'
                }

                r = requests.get(f"{api_file_url}?t={ts}", headers=headers, timeout=5)
                
                if r.status_code == 200:
                    data = r.json()
                    # GitHub API отдает контент в Base64, нужно декодировать
                    encoded_content = data.get('content', '')
                    decoded_bytes = base64.b64decode(encoded_content)
                    txt = decoded_bytes.decode('utf-8')
                    
                    self.after(0, lambda: ScriptInfoWindow(self, name, txt))
                elif r.status_code == 404:
                    self.after(0, lambda: messagebox.showinfo("Инфо", "Инструкция для этого скрипта еще не создана."))
                else:
                    # Если API тупит, пробуем старый метод как запасной
                    self._load_info_fallback(name)
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Ошибка", f"Критический сбой API: {e}"))
        
        threading.Thread(target=load, daemon=True).start()

    def _load_info_fallback(self, name):
        """Запасной метод через Raw, если API лимитирован"""
        url = f"{BASE_RAW_URL}/Scripts/{name}.txt?t={str(int(time.time()))}"
        try:
            r = requests.get(url, timeout=5)
            r.encoding = 'utf-8'
            if r.status_code == 200:
                self.after(0, lambda: ScriptInfoWindow(self, name, r.text))
        except: pass

    def run_ps_script(self, filename):
        def worker():
            path = os.path.join(self.temp_dir, filename)
            try:
                ts = str(int(time.time()))
                with requests.Session() as s:
                    r = s.get(f"{BASE_RAW_URL}/Scripts/{filename}?t={ts}", 
                              headers=self.nocache_headers, timeout=15)
                    
                    if r.status_code == 200:
                        content = r.text 
                        # Сохраняем с BOM, чтобы PowerShell не ругался на кодировку
                        with open(path, "w", encoding="utf-8-sig") as f: 
                            f.write(content)
                        
                        # --- ВОТ ЭТУ ЧАСТЬ МЫ МЕНЯЕМ ---
                        # Формируем команду, которая заставит Windows показать окно UAC (RunAs)
                        ps_command = f"Start-Process powershell.exe -ArgumentList '-ExecutionPolicy Bypass -File \"{path}\"' -Verb RunAs -Wait"
                        
                        res = subprocess.run(["powershell.exe", "-Command", ps_command], 
                                             capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
                        # ------------------------------

                        if res.returncode == 0:
                            self.after(0, lambda: messagebox.showinfo("Успех", "Скрипт выполнен!"))
                        else:
                            self.after(0, lambda: messagebox.showerror("Ошибка", f"Лог:\n{res.stderr}"))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Ошибка", f"Сбой: {e}"))
        threading.Thread(target=worker, daemon=True).start()

    # --- ИНСТРУКЦИИ (MD) ---
    def show_instructions_list(self):
        self.clear_main_area()
        self.scroll_frame.pack(expand=True, fill="both")
        loading = ctk.CTkLabel(self.scroll_frame, text="⏳ Синхронизация инструкций...")
        loading.pack(pady=20)
        threading.Thread(target=self._load_instr_worker, daemon=True).start()

    def _load_instr_worker(self):
        """Загрузка списка MD-файлов через API"""
        try:
            import time
            ts = str(int(time.time()))
            # Используем API для получения списка файлов в папке Instructions
            url = f"{API_URL}/Instructions?t={ts}"
            r = requests.get(url, headers=self.nocache_headers, timeout=10)
            
            if r.status_code == 200:
                files = [item['name'] for item in r.json() if item['name'].endswith('.md')]
                self.after(0, lambda: self.render_instr_buttons(files))
            else:
                self.after(0, lambda: self.show_error(f"GitHub API Error: {r.status_code}"))
        except:
            self.after(0, lambda: self.show_error("Ошибка сети при получении списка"))

    def render_instr_buttons(self, files):
        self.clear_main_area()
        self.scroll_frame.pack(expand=True, fill="both")
        ctk.CTkLabel(self.scroll_frame, text="📖 Инструкции", font=("Segoe UI", 22, "bold")).pack(pady=20)
        for f in files:
            btn = ctk.CTkButton(self.scroll_frame, text=f.replace(".md", ""), height=50, 
                               command=lambda fn=f: self.open_instruction(fn))
            btn.pack(pady=8, padx=60, fill="x")

    def open_instruction(self, file_name):
        self.clear_main_area()
        self.top_bar.pack(fill="x", padx=10, pady=5)
        self.scroll_frame.pack(expand=True, fill="both")
        loading = ctk.CTkLabel(self.scroll_frame, text="Загрузка...")
        loading.pack(pady=20)
        threading.Thread(target=self._read_md_worker, args=(file_name, loading), daemon=True).start()

    def _read_md_worker(self, file_name, loading_label):
        """Чтение конкретного MD-файла через API с декодированием Base64"""
        import base64
        import time
        try:
            ts = str(int(time.time()))
            # Стучимся в API за конкретным файлом
            url = f"{API_URL}/Instructions/{file_name}?t={ts}"
            r = requests.get(url, headers=self.nocache_headers, timeout=10)
            
            if r.status_code == 200:
                data = r.json()
                # Декодируем содержимое из Base64
                encoded_content = data.get('content', '')
                # Убираем лишние переносы строк, которые иногда добавляет API в Base64
                decoded_bytes = base64.b64decode(encoded_content.replace('\n', ''))
                md_text = decoded_bytes.decode('utf-8')
                
                # Рендерим MD в HTML
                html_body = markdown2.markdown(md_text, extras=["tables"])
                
                # Оформляем стили для темной темы
                styled = f"<body bgcolor='#2b2b2b' text='#ffffff' style='font-family: Segoe UI; padding: 20px;'>{html_body}</body>"
                styled = styled.replace("<p>", "<p style='color: #ffffff;'>")\
                               .replace("<li>", "<li style='color: #ffffff;'>")\
                               .replace("<h1>", "<h1 style='color: #ffffff; border-bottom: 1px solid #444;'>")\
                               .replace("<h2>", "<h2 style='color: #ffffff; border-bottom: 1px solid #444;'>")\
                               .replace("<code", "<code style='background: #3c3f41; color: #cc7832; padding: 2px 4px; border-radius: 4px;'")
                
                self.after(0, lambda: self.display_html(styled, loading_label))
            else:
                self.after(0, lambda: self.show_error("Не удалось получить текст через API"))
        except Exception as e:
            self.after(0, lambda: self.show_error(f"Ошибка декодирования: {e}"))

    def display_html(self, html, label):
        label.destroy()
        self.scroll_frame.pack_forget()
        self.html_view.pack(expand=True, fill="both", padx=10, pady=10)
        self.html_view.set_html(html)
        
        # Включаем возможность взаимодействия
        self.html_view.configure(state="normal")
        # Фокусируемся на виджете, чтобы он сразу принимал нажатия клавиш
        self.html_view.focus_set()

    def on_closing(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        self.destroy()

    def show_error(self, text):
        self.clear_main_area()
        self.scroll_frame.pack(expand=True, fill="both")
        ctk.CTkLabel(self.scroll_frame, text=text, text_color="#ff6b6b").pack(pady=20)

if __name__ == "__main__":
    ctk.set_appearance_mode("dark") 
    app = App()
    app.mainloop()