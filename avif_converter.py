import os
import re
import threading
from tkinter import colorchooser, filedialog, messagebox
import customtkinter as ctk
from PIL import Image, ImageOps

try:
    import pillow_avif  # noqa: F401 - opcjonalny plugin dla starszych wersji Pillow
except ImportError:
    pass


def convert_avif_file_to_jpg(
    file_path: str,
    output_dir: str = "",
    quality: int = 92,
    bg_rgb: tuple[int, int, int] = (255, 255, 255),
) -> str:
    """
    Konwertuje pojedynczy plik AVIF (lub inny obraz) do formatu JPG
    z zachowaniem oryginalnej rozdzielczości i obsługą kanału alfa.
    Zwraca ścieżkę do zapisanego pliku.
    """
    src_dir = os.path.normpath(os.path.dirname(file_path))
    file_name = os.path.basename(file_path)
    name_wo_ext, orig_ext = os.path.splitext(file_name)

    if output_dir and (os.path.normpath(output_dir).lower() != src_dir.lower()):
        target_dir = os.path.normpath(output_dir)
        out_filename = f"{name_wo_ext}.jpg"
    else:
        target_dir = src_dir
        if orig_ext.lower() in (".jpg", ".jpeg"):
            out_filename = f"{name_wo_ext}_converted.jpg"
        else:
            out_filename = f"{name_wo_ext}.jpg"

    out_path = os.path.join(target_dir, out_filename)

    with Image.open(file_path) as img:
        img = ImageOps.exif_transpose(img)

        if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
            rgba_img = img.convert("RGBA")
            canvas = Image.new("RGB", rgba_img.size, bg_rgb)
            canvas.paste(rgba_img, (0, 0), mask=rgba_img.split()[3])
            rgb_img = canvas
        elif img.mode != "RGB":
            rgb_img = img.convert("RGB")
        else:
            rgb_img = img

        rgb_img.save(out_path, format="JPEG", quality=quality, optimize=True)

    return out_path


class AvifConverterTab(ctk.CTkFrame):
    """Moduł GUI (zakładka) do wgrywania plików AVIF i ich konwersji do JPG."""

    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.selected_files: list[str] = []
        self.output_dir: str = ""
        self._build_ui()

    def _build_ui(self):
        title_lbl = ctk.CTkLabel(
            self,
            text="Konwerter AVIF do JPG",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="#ffffff",
        )
        title_lbl.pack(pady=(10, 5))

        desc_lbl = ctk.CTkLabel(
            self,
            text="Szybka konwersja plików .avif do .jpg w oryginalnej rozdzielczości.",
            font=ctk.CTkFont(size=12),
            text_color="#a0a0a0",
        )
        desc_lbl.pack(pady=(0, 15))

        # Sekcja 1: Wybór plików AVIF
        files_frame = ctk.CTkFrame(self, fg_color="transparent")
        files_frame.pack(fill="x", padx=25, pady=6)

        self.btn_select_files = ctk.CTkButton(
            files_frame,
            text="1. Wgraj pliki AVIF",
            width=160,
            fg_color="#3b82f6",
            hover_color="#2563eb",
            command=self.select_files,
        )
        self.btn_select_files.pack(side="left")

        self.lbl_files_status = ctk.CTkLabel(
            files_frame,
            text="Nie wybrano plików",
            text_color="#9ca3af",
            anchor="w",
        )
        self.lbl_files_status.pack(side="left", padx=15, fill="x", expand=True)

        # Sekcja 2: Folder docelowy
        out_frame = ctk.CTkFrame(self, fg_color="transparent")
        out_frame.pack(fill="x", padx=25, pady=6)

        self.btn_select_output = ctk.CTkButton(
            out_frame,
            text="2. Folder zapisu (opcja)",
            width=160,
            fg_color="#3b82f6",
            hover_color="#2563eb",
            command=self.select_output_dir,
        )
        self.btn_select_output.pack(side="left")

        self.lbl_output_status = ctk.CTkLabel(
            out_frame,
            text="Ten sam folder co oryginały (.avif -> .jpg)",
            text_color="#9ca3af",
            anchor="w",
        )
        self.lbl_output_status.pack(side="left", padx=15, fill="x", expand=True)

        # Sekcja 3: Parametry konwersji
        cfg_frame = ctk.CTkFrame(self, corner_radius=8, fg_color="#2b2b36")
        cfg_frame.pack(fill="x", padx=25, pady=15)

        # Jakość JPG
        qual_title = ctk.CTkLabel(
            cfg_frame,
            text="Jakość JPG:",
            font=ctk.CTkFont(weight="bold"),
            text_color="#ffffff",
        )
        qual_title.grid(row=0, column=0, padx=15, pady=12, sticky="w")

        qual_controls = ctk.CTkFrame(cfg_frame, fg_color="transparent")
        qual_controls.grid(row=0, column=1, columnspan=2, padx=10, pady=12, sticky="w")

        self.slider_quality = ctk.CTkSlider(
            qual_controls,
            from_=50,
            to=100,
            number_of_steps=50,
            width=200,
            command=self._on_quality_changed,
        )
        self.slider_quality.set(92)
        self.slider_quality.pack(side="left", padx=(0, 10))

        self.lbl_quality_val = ctk.CTkLabel(
            qual_controls,
            text="92%",
            width=45,
            font=ctk.CTkFont(weight="bold"),
            text_color="#ffffff",
        )
        self.lbl_quality_val.pack(side="left")

        # Tło w przypadku przezroczystości w AVIF
        bg_title = ctk.CTkLabel(
            cfg_frame,
            text="Tło dla przezroczystości:",
            font=ctk.CTkFont(weight="bold"),
            text_color="#ffffff",
        )
        bg_title.grid(row=1, column=0, padx=15, pady=(0, 12), sticky="w")

        bg_controls = ctk.CTkFrame(cfg_frame, fg_color="transparent")
        bg_controls.grid(row=1, column=1, columnspan=2, padx=10, pady=(0, 12), sticky="w")

        self.combo_bg_color = ctk.CTkComboBox(
            bg_controls,
            values=["Biały", "Czarny", "Własny kolor"],
            width=140,
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
            command=self._choose_bg_color,
        )
        self.btn_choose_bg_color.grid(row=0, column=2, padx=(5, 0))

        # Pasek postępu
        self.progress_bar = ctk.CTkProgressBar(self, progress_color="#3b82f6")
        self.progress_bar.set(0)
        self.progress_bar.pack(fill="x", padx=25, pady=(15, 5))

        self.lbl_progress = ctk.CTkLabel(self, text="Gotowy do pracy", text_color="#9ca3af")
        self.lbl_progress.pack(pady=(0, 10))

        # Przycisk start
        self.btn_process = ctk.CTkButton(
            self,
            text="Konwertuj AVIF do JPG",
            height=40,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#10b981",
            hover_color="#059669",
            command=self.start_conversion,
        )
        self.btn_process.pack(pady=5)

    def _on_quality_changed(self, value):
        self.lbl_quality_val.configure(text=f"{int(round(value))}%")

    def _choose_bg_color(self):
        current_color = self.entry_bg_hex.get().strip()
        if not re.fullmatch(r"#?[0-9a-fA-F]{6}", current_color):
            current_color = "#FFFFFF"

        _, color_hex = colorchooser.askcolor(color=current_color, parent=self.winfo_toplevel())
        if color_hex:
            self.entry_bg_hex.delete(0, "end")
            self.entry_bg_hex.insert(0, color_hex.upper())
            self.combo_bg_color.set("Własny kolor")

    def select_files(self):
        filetypes = [
            ("Pliki AVIF", "*.avif"),
            ("Wszystkie pliki", "*.*"),
        ]
        files = filedialog.askopenfilenames(title="Wybierz pliki AVIF do konwersji", filetypes=filetypes)
        if files:
            self.selected_files = list(files)
            count = len(self.selected_files)
            self.lbl_files_status.configure(
                text=f"Wybrano: {count} {'plik' if count == 1 else 'pliki/ów'}",
                text_color="#ffffff",
            )

    def select_output_dir(self):
        directory = filedialog.askdirectory(title="Wybierz folder zapisu plików JPG")
        if directory:
            self.output_dir = os.path.normpath(directory)
            display_path = self.output_dir if len(self.output_dir) < 40 else "..." + self.output_dir[-37:]
            self.lbl_output_status.configure(
                text=f"Katalog: {display_path}",
                text_color="#ffffff",
            )

    def start_conversion(self):
        if not self.selected_files:
            messagebox.showwarning("Brak plików", "Najpierw wybierz przynajmniej jeden plik AVIF.")
            return

        bg_choice = self.combo_bg_color.get()
        if bg_choice == "Czarny":
            bg_rgb = (0, 0, 0)
        elif bg_choice == "Własny kolor":
            color_hex = self.entry_bg_hex.get().strip()
            if not re.fullmatch(r"#?[0-9a-fA-F]{6}", color_hex):
                messagebox.showerror("Błąd", "Wpisz kolor w formacie #RRGGBB, np. #FFFFFF.")
                return
            color_hex = color_hex.lstrip("#")
            bg_rgb = tuple(int(color_hex[i : i + 2], 16) for i in (0, 2, 4))
        else:
            bg_rgb = (255, 255, 255)

        quality = int(round(self.slider_quality.get()))

        threading.Thread(
            target=self._conversion_worker,
            args=(quality, bg_rgb),
            daemon=True,
        ).start()

    def _conversion_worker(self, quality: int, bg_rgb: tuple[int, int, int]):
        self.btn_process.configure(state="disabled")
        self.btn_select_files.configure(state="disabled")
        self.btn_select_output.configure(state="disabled")

        total = len(self.selected_files)
        success_count = 0

        for idx, file_path in enumerate(self.selected_files, start=1):
            try:
                convert_avif_file_to_jpg(
                    file_path=file_path,
                    output_dir=self.output_dir,
                    quality=quality,
                    bg_rgb=bg_rgb,
                )
                success_count += 1
            except Exception as e:
                print(f"Błąd konwersji AVIF {file_path}: {e}")

            progress = idx / total
            self.progress_bar.set(progress)
            self.lbl_progress.configure(text=f"Konwersja: {idx}/{total}...")

        self.lbl_progress.configure(text=f"Zakończono! Przekonwertowano {success_count}/{total} plików do JPG.")
        self.btn_process.configure(state="normal")
        self.btn_select_files.configure(state="normal")
        self.btn_select_output.configure(state="normal")

        messagebox.showinfo("Koniec konwersji", f"Pomyślnie przekonwertowano {success_count} z {total} plików do JPG.")

