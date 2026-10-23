import os
import re
import threading
from tkinter import colorchooser, filedialog, messagebox
import customtkinter as ctk
from PIL import Image, ImageOps
from avif_converter import AvifConverterTab

# Stały ciemny motyw i wyłączenie skalowania DPI
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")
ctk.deactivate_automatic_dpi_awareness()


class ImageSquarePadderApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Dopełnianie Grafik do Kwadratu (Padding) & Konwerter AVIF")

        # Stały rozmiar okna
        WINDOW_WIDTH = 660
        WINDOW_HEIGHT = 620
        self.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.resizable(False, False)
        self.minsize(WINDOW_WIDTH, WINDOW_HEIGHT)
        self.maxsize(WINDOW_WIDTH, WINDOW_HEIGHT)

        self.selected_files = []
        self.output_dir = ""

        # Główny kontener zakładek o stałych ciemnych barwach
        self.tabview = ctk.CTkTabview(
            self,
            corner_radius=12,
            fg_color="#1e1e24"
        )
        self.tabview.pack(padx=20, pady=(10, 20), fill="both", expand=True)

        self.main_frame = self.tabview.add("Dopełnianie do Kwadratu")
        self.avif_tab_frame = self.tabview.add("Konwerter AVIF -> JPG")

        self._build_ui()
        self.avif_converter_ui = AvifConverterTab(self.avif_tab_frame)
        self.avif_converter_ui.pack(fill="both", expand=True)

    def _build_ui(self):
        title_lbl = ctk.CTkLabel(
            self.main_frame,
            text="Dopełnianie do Kwadratu (100% kadru)",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="#ffffff"
        )
        title_lbl.pack(pady=(10, 5))

        desc_lbl = ctk.CTkLabel(
            self.main_frame,
            text="Zachowuje cały obraz bez obcinania. Dopełnia brakujące marginesy.",
            font=ctk.CTkFont(size=12),
            text_color="#a0a0a0"
        )
        desc_lbl.pack(pady=(0, 15))

        # Sekcja 1: Wybór plików wejściowych
        files_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        files_frame.pack(fill="x", padx=25, pady=6)

        self.btn_select_files = ctk.CTkButton(
            files_frame,
            text="1. Wybierz obrazy",
            width=160,
            fg_color="#3b82f6",
            hover_color="#2563eb",
            command=self.select_files
        )
        self.btn_select_files.pack(side="left")

        self.lbl_files_status = ctk.CTkLabel(
            files_frame,
            text="Nie wybrano plików",
            text_color="#9ca3af",
            anchor="w"
        )
        self.lbl_files_status.pack(side="left", padx=15, fill="x", expand=True)

        # Sekcja 2: Folder docelowy
        out_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        out_frame.pack(fill="x", padx=25, pady=6)

        self.btn_select_output = ctk.CTkButton(
            out_frame,
            text="2. Folder zapisu (opcja)",
            width=160,
            fg_color="#3b82f6",
            hover_color="#2563eb",
            command=self.select_output_dir
        )
        self.btn_select_output.pack(side="left")

        self.lbl_output_status = ctk.CTkLabel(
            out_frame,
            text="Ten sam folder co oryginały (doda sufiks)",
            text_color="#9ca3af",
            anchor="w"
        )
        self.lbl_output_status.pack(side="left", padx=15, fill="x", expand=True)

        # Sekcja 3: Konfiguracja
        res_frame = ctk.CTkFrame(self.main_frame, corner_radius=8, fg_color="#2b2b36")
        res_frame.pack(fill="x", padx=25, pady=15)

        # Rozmiar kwadratu
        res_title = ctk.CTkLabel(res_frame, text="Wymiar kwadratu:", font=ctk.CTkFont(weight="bold"), text_color="#ffffff")
        res_title.grid(row=0, column=0, padx=15, pady=10, sticky="w")

        self.combo_presets = ctk.CTkComboBox(
            res_frame,
            values=["512 px", "1024 px", "1080 px (Instagram)", "1200 px", "2048 px", "Własny"],
            command=self._on_preset_changed,
            width=180
        )
        self.combo_presets.set("1080 px (Instagram)")
        self.combo_presets.grid(row=0, column=1, padx=10, pady=10)

        self.entry_custom_size = ctk.CTkEntry(res_frame, placeholder_text="Bok (px)", width=100)
        self.entry_custom_size.insert(0, "1080")
        self.entry_custom_size.grid(row=0, column=2, padx=10, pady=10)

        # Kolor dopełnienia (tła)
        bg_title = ctk.CTkLabel(res_frame, text="Kolor tła / marginesów:", font=ctk.CTkFont(weight="bold"), text_color="#ffffff")
        bg_title.grid(row=1, column=0, padx=15, pady=10, sticky="w")

        bg_controls = ctk.CTkFrame(res_frame, fg_color="transparent")
        bg_controls.grid(row=1, column=1, columnspan=2, padx=5, pady=10, sticky="w")
        self.combo_bg_color = ctk.CTkComboBox(
            bg_controls,
            values=["Biały", "Czarny", "Przezroczysty (wymusza PNG)", "Własny kolor"],
            width=170
        )
        self.combo_bg_color.set("Biały")
        self.combo_bg_color.grid(row=0, column=0, padx=(0, 5))

        self.entry_bg_hex = ctk.CTkEntry(bg_controls, width=95, placeholder_text="#RRGGBB")
        self.entry_bg_hex.insert(0, "#FFFFFF")
        self.entry_bg_hex.grid(row=0, column=1, padx=5)

        self.btn_choose_bg_color = ctk.CTkButton(
            bg_controls,
            text="Paleta",
            width=65,
            command=self._choose_bg_color
        )
        self.btn_choose_bg_color.grid(row=0, column=2, padx=(5, 0))

        # Format zapisu
        fmt_title = ctk.CTkLabel(res_frame, text="Format wyjściowy:", font=ctk.CTkFont(weight="bold"), text_color="#ffffff")
        fmt_title.grid(row=2, column=0, padx=15, pady=(0, 10), sticky="w")

        self.combo_format = ctk.CTkComboBox(
            res_frame,
            values=["Zachowaj oryginalny format każdego pliku", "Wszystko do JPG", "Wszystko do PNG", "Wszystko do WEBP"],
            width=280
        )
        self.combo_format.set("Zachowaj oryginalny format każdego pliku")
        self.combo_format.grid(row=2, column=1, columnspan=2, padx=10, pady=(0, 10), sticky="w")

        # Pasek postępu
        self.progress_bar = ctk.CTkProgressBar(self.main_frame, progress_color="#3b82f6")
        self.progress_bar.set(0)
        self.progress_bar.pack(fill="x", padx=25, pady=(10, 5))

        self.lbl_progress = ctk.CTkLabel(self.main_frame, text="Gotowy do pracy", text_color="#9ca3af")
        self.lbl_progress.pack(pady=(0, 10))

        # Przycisk start
        self.btn_process = ctk.CTkButton(
            self.main_frame,
            text="Dopełnij i zapisz obrazy",
            height=40,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#10b981",
            hover_color="#059669",
            command=self.start_processing
        )
        self.btn_process.pack(pady=5)

    def _on_preset_changed(self, choice):
        mapping = {
            "512 px": "512",
            "1024 px": "1024",
            "1080 px (Instagram)": "1080",
            "1200 px": "1200",
            "2048 px": "2048",
        }
        if choice in mapping:
            self.entry_custom_size.delete(0, "end")
            self.entry_custom_size.insert(0, mapping[choice])

    def _choose_bg_color(self):
        current_color = self.entry_bg_hex.get().strip()
        if not re.fullmatch(r"#?[0-9a-fA-F]{6}", current_color):
            current_color = "#FFFFFF"

        _, color_hex = colorchooser.askcolor(color=current_color, parent=self)
        if color_hex:
            self.entry_bg_hex.delete(0, "end")
            self.entry_bg_hex.insert(0, color_hex.upper())
            self.combo_bg_color.set("Własny kolor")

    def select_files(self):
        filetypes = [
            ("Obsługiwane obrazy", "*.jpg *.jpeg *.png *.webp *.avif *.bmp *.tiff"),
            ("Pliki AVIF", "*.avif"),
            ("Wszystkie pliki", "*.*")
        ]
        files = filedialog.askopenfilenames(title="Wybierz obrazy (miks formatów)", filetypes=filetypes)
        if files:
            self.selected_files = list(files)
            count = len(self.selected_files)
            self.lbl_files_status.configure(
                text=f"Wybrano: {count} {'plik' if count == 1 else 'pliki/ów'}",
                text_color="#ffffff"
            )

    def select_output_dir(self):
        directory = filedialog.askdirectory(title="Wybierz folder zapisu")
        if directory:
            self.output_dir = os.path.normpath(directory)
            display_path = self.output_dir if len(self.output_dir) < 40 else "..." + self.output_dir[-37:]
            self.lbl_output_status.configure(
                text=f"Katalog: {display_path} (bez zmiany nazw)",
                text_color="#ffffff"
            )

    def start_processing(self):
        if not self.selected_files:
            messagebox.showwarning("Brak plików", "Najpierw wybierz przynajmniej jeden plik graficzny.")
            return

        size_raw = self.entry_custom_size.get().strip()
        if not size_raw.isdigit() or int(size_raw) <= 0:
            messagebox.showerror("Błąd", "Wprowadź prawidłowy wymiar boku kwadratu (liczba całkowita > 0).")
            return

        bg_choice = self.combo_bg_color.get()
        custom_color = None
        if bg_choice == "Własny kolor":
            color_hex = self.entry_bg_hex.get().strip()
            if not re.fullmatch(r"#?[0-9a-fA-F]{6}", color_hex):
                messagebox.showerror("Błąd", "Wpisz kolor w formacie #RRGGBB, np. #3B82F6.")
                return
            color_hex = color_hex.lstrip("#")
            custom_color = tuple(int(color_hex[index:index + 2], 16) for index in (0, 2, 4))

        threading.Thread(
            target=self._process_worker,
            args=(int(size_raw), bg_choice, custom_color),
            daemon=True
        ).start()

    def _process_worker(self, target_size, bg_choice, custom_color):
        self.btn_process.configure(state="disabled")
        self.btn_select_files.configure(state="disabled")
        self.btn_select_output.configure(state="disabled")

        total = len(self.selected_files)
        success_count = 0
        fmt_choice = self.combo_format.get()

        for idx, file_path in enumerate(self.selected_files, start=1):
            try:
                src_dir = os.path.normpath(os.path.dirname(file_path))
                file_name = os.path.basename(file_path)
                name_wo_ext, orig_ext = os.path.splitext(file_name)

                # 1. Określenie formatu docelowego (rozszerzenia)
                if "Przezroczysty" in bg_choice:
                    target_ext = ".png"
                elif "JPG" in fmt_choice:
                    target_ext = ".jpg"
                elif "PNG" in fmt_choice:
                    target_ext = ".png"
                elif "WEBP" in fmt_choice:
                    target_ext = ".webp"
                else:
                    # Zachowaj oryginalny format
                    target_ext = orig_ext.lower()
                    if target_ext not in [".jpg", ".jpeg", ".png", ".webp", ".avif", ".bmp", ".tiff"]:
                        target_ext = ".png"

                # 2. Folder zapisu i logika nazewnictwa
                if self.output_dir and (self.output_dir.lower() != src_dir.lower()):
                    target_dir = self.output_dir
                    # INNY FOLDER -> ZACHOWUJEMY ORYGINALNĄ NAZWĘ
                    out_filename = f"{name_wo_ext}{target_ext}"
                else:
                    target_dir = src_dir
                    # TEN SAM FOLDER / BRAK WYBORU -> DODAJEMY SUFIKS PRZECIW NADPISANIU
                    out_filename = f"{name_wo_ext}_square_{target_size}x{target_size}{target_ext}"

                out_path = os.path.join(target_dir, out_filename)

                # 3. Przetwarzanie obrazu
                with Image.open(file_path) as img:
                    img = ImageOps.exif_transpose(img)

                    # Bezpieczna normalizacja przestrzeni barw (np. CMYK -> RGB)
                    if img.mode not in ("RGB", "RGBA"):
                        if "A" in img.mode or (img.mode == "P" and "transparency" in img.info):
                            img = img.convert("RGBA")
                        else:
                            img = img.convert("RGB")

                    # Skalowanie proporcjonalne z zachowaniem 100% kadru
                    img.thumbnail((target_size, target_size), Image.Resampling.LANCZOS)

                    # Tworzenie tła kwadratowego
                    if "Przezroczysty" in bg_choice:
                        canvas = Image.new("RGBA", (target_size, target_size), (0, 0, 0, 0))
                    elif "Czarny" in bg_choice:
                        canvas = Image.new("RGB", (target_size, target_size), (0, 0, 0))
                    elif bg_choice == "Własny kolor":
                        canvas = Image.new("RGB", (target_size, target_size), custom_color)
                    else:  # Biały
                        canvas = Image.new("RGB", (target_size, target_size), (255, 255, 255))

                    offset_x = (target_size - img.width) // 2
                    offset_y = (target_size - img.height) // 2

                    # Wklejanie z uwzględnieniem przezroczystości
                    if img.mode == "RGBA":
                        canvas.paste(img, (offset_x, offset_y), mask=img.split()[3])
                    else:
                        canvas.paste(img, (offset_x, offset_y))

                    # 4. Bezpieczny zapis do wybranego formatu
                    if target_ext in [".jpg", ".jpeg"]:
                        if canvas.mode != "RGB":
                            canvas = canvas.convert("RGB")
                        canvas.save(out_path, format="JPEG", quality=92, optimize=True)
                    elif target_ext == ".png":
                        canvas.save(out_path, format="PNG")
                    elif target_ext == ".webp":
                        canvas.save(out_path, format="WEBP", quality=90)
                    elif target_ext == ".avif":
                        canvas.save(out_path, format="AVIF", quality=90)
                    else:
                        canvas.save(out_path)

                success_count += 1
            except Exception as e:
                print(f"Błąd przetwarzania {file_path}: {e}")

            progress = idx / total
            self.progress_bar.set(progress)
            self.lbl_progress.configure(text=f"Przetwarzanie: {idx}/{total}...")

        self.lbl_progress.configure(text=f"Zakończono! Zapisano {success_count}/{total} obrazów.")
        self.btn_process.configure(state="normal")
        self.btn_select_files.configure(state="normal")
        self.btn_select_output.configure(state="normal")

        messagebox.showinfo("Koniec pracy", f"Pomyślnie przetworzono {success_count} z {total} plików.")


if __name__ == "__main__":
    app = ImageSquarePadderApp()
    app.mainloop()
