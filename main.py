import customtkinter as ctk
from tkinter import filedialog, messagebox
import tkinter as tk 
import tkintermapview
import math
import pandas as pd
import time
from tkinterdnd2 import TkinterDnD, DND_FILES

# Import modules
import config as cfg
from components import TransparentScaleBar
from utils import load_car_icons, process_gps_data, calculate_total_distance, haversine_distance, create_circle_icon_marker, create_transparent_icon

class GPSTrackingApp(ctk.CTk, TkinterDnD.DnDWrapper):
    def __init__(self):
        super().__init__()
        self.TkdndVersion = TkinterDnD._require(self)

        self.title(cfg.APP_TITLE)
        
        # Language Settings
        self.current_lang = "TH"
        self.TEXTS = {
            "TH": {
                "app_title": "GPS MONITOR",
                "load_btn": "📂 เลือกไฟล์ CSV",
                "date_label": "📅 เลือกวันที่:",
                "default_date": "-- กรุณาโหลดไฟล์ --",
                "total_count": "ทั้งหมด: {:,} จุด",
                "time_label": "⏰ เลือกช่วงเวลา:",
                "row_label": "🔢 เลือกช่วงแถว (Option):",
                "limit_label": "⚙️ จำกัดจุดแสดงผล:",
                "apply_btn": "นำไปใช้",
                "zoom_btn": "📍 ซูมไปที่รถ",
                "measure_btn_start": "📏 เริ่มวัดระยะทาง",
                "measure_btn_stop": "❌ หยุดวัดระยะทาง",
                "clear_btn": "🗑 ล้างหน้าจอ",
                "info_time": "เวลา",
                "info_speed": "ความเร็ว",
                "info_status": "🚦 สถานะ",
                "info_coord": "📍 พิกัด (Lat, Lon)",
                "file_ready": "พร้อมใช้งาน",
                "file_reading": "กำลังอ่านไฟล์...",
                "file_loaded": "โหลดสำเร็จ",
                "file_error": "Error",
                "timeline": "Timeline:",
                "hide_log": "▼ ซ่อน",
                "show_log": "▲ แสดง",
                "measure_title": "วัดระยะทาง",
                "measure_hint": "(คลิกซ้ายเพิ่มจุด / คลิกขวาเพื่อลบ)",
                "measure_total": "รวมระยะทาง: ",
                "no_car": "ยังไม่มีรถบนแผนที่",
                "copied": "คัดลอก:",
                "display_count": "แสดงผล: {:,} จุด",
                "status_Engine Off": "ดับเครื่อง",
                "status_Idling": "จอดติดเครื่อง",
                "status_Running": "กำลังวิ่ง"
            },
            "EN": {
                "app_title": "GPS MONITOR",
                "load_btn": "📂 Load CSV File",
                "date_label": "📅 Select Date:",
                "default_date": "-- Please load file --",
                "total_count": "Total: {:,} points",
                "time_label": "⏰ Time Range:",
                "row_label": "🔢 Row Range (Option):",
                "limit_label": "⚙️ Limit Points:",
                "apply_btn": "Apply Settings",
                "zoom_btn": "📍 Zoom to Car",
                "measure_btn_start": "📏 Start Measure",
                "measure_btn_stop": "❌ Stop Measure",
                "clear_btn": "🗑 Clear Screen",
                "info_time": "Time",
                "info_speed": "Speed",
                "info_status": "🚦 Status",
                "info_coord": "📍 Coords (Lat, Lon)",
                "file_ready": "Ready",
                "file_reading": "Reading file...",
                "file_loaded": "Loaded successfully",
                "file_error": "Error",
                "timeline": "Timeline:",
                "hide_log": "▼ Hide",
                "show_log": "▲ Show",
                "measure_title": "Distance Measurement",
                "measure_hint": "(Left Click: Add / Right Click: Del)",
                "measure_total": "Total Distance: ",
                "no_car": "No car on map",
                "copied": "Copied:",
                "display_count": "Display: {:,} points",
                "status_Engine Off": "Engine Off",
                "status_Idling": "Idling",
                "status_Running": "Running"
            }
        }
        
        # Auto Full Screen
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        self.geometry(f"{int(screen_width*0.9)}x{int(screen_height*0.9)}")
        self.after(0, lambda: self.state('zoomed'))
        
        # Variables
        self.raw_df = None       
        self.filtered_df = None  
        self.path_points = []
        self.animation_points = []
        
        self.car_marker = None
        self.path_line = None
        self.start_marker = None
        self.end_marker = None
        
        self.slider_job = None 
        self.last_update_time = 0 # [THROTTLE VAR]
        self.cached_logs = [] 
        self.log_widgets_pool = [] 
        
        # [KEY VAR] ตัวแปรแม่ข่าย
        self.current_frame = 0 
        
        # [SETTING] UI Configuration
        self.MAX_LOG_DISPLAY = 5 
        self.log_visible = True
        self.interp_steps = 10 
        
        self.last_draw_index = -1  
        
        # [KEY CONTROL VARS]
        self.key_loop_job = None
        self.current_key_direction = 0 
        
        # [MEASURE VARS]
        self.is_measuring = False
        self.measure_coords = []      
        self.measure_point_markers = [] 
        self.measure_segment_paths = [] 
        self.measure_segment_labels = [] 
        
        # Load Icons
        self.icons = load_car_icons()
        self.circle_icon = create_circle_icon_marker()
        self.trans_icon = create_transparent_icon()
        self.current_icon_key = None 

        # Bindings
        self.bind_all("<KeyPress-Left>", lambda e: self.on_key_press(e, -1))
        self.bind_all("<KeyRelease-Left>", lambda e: self.on_key_release(e, -1))
        self.bind_all("<KeyPress-Right>", lambda e: self.on_key_press(e, 1))
        self.bind_all("<KeyRelease-Right>", lambda e: self.on_key_release(e, 1))

        self.bind("<Delete>", lambda e: self.undo_measure_point())
        self.bind("<BackSpace>", lambda e: self.undo_measure_point())
        self.bind("<Escape>", lambda e: self.clear_measurements())
        
        # self.bind("<Button-1>", lambda e: self.focus_set())

        self.setup_ui()
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Register Drag and Drop
        self.drop_target_register(DND_FILES)
        self.dnd_bind('<<Drop>>', self.drop_file)

    def validate_number_input(self, P):
        if P == "": return True
        return P.isdigit()

    def on_closing(self):
        self.quit()
        self.destroy()

    def setup_ui(self):
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1) 
        self.grid_rowconfigure(1, weight=0) 
        self.grid_rowconfigure(2, weight=0)

        # --- SIDEBAR ---
        self.sidebar = ctk.CTkFrame(self, width=320, corner_radius=0)
        self.sidebar.grid(row=0, column=0, rowspan=3, sticky="nsew")
        self.sidebar.grid_propagate(False)
        

        # [LANG SWITCH] - Moved to bottom with switch style


        self.lbl_app_title = ctk.CTkLabel(self.sidebar, text=self.TEXTS[self.current_lang]["app_title"], font=ctk.CTkFont(size=26, weight="bold"))
        self.lbl_app_title.pack(pady=(20, 10))

        self.btn_load = ctk.CTkButton(self.sidebar, text=self.TEXTS[self.current_lang]["load_btn"], height=40, font=ctk.CTkFont(size=16, weight="bold"), command=self.load_csv_action)
        self.btn_load.pack(padx=20, pady=5, fill="x")

        self.lbl_date_title = ctk.CTkLabel(self.sidebar, text=self.TEXTS[self.current_lang]["date_label"], font=("Arial", 16, "bold"), text_color="white")
        self.lbl_date_title.pack(padx=20, pady=(5, 0), anchor="w")
        self.date_var = ctk.StringVar(value=self.TEXTS[self.current_lang]["default_date"])
        self.date_combo = ctk.CTkComboBox(self.sidebar, variable=self.date_var, height=30, font=("Arial", 16), state="disabled", command=self.on_date_selected)
        self.date_combo.pack(padx=20, pady=(5, 5), fill="x")

        self.lbl_total_count = ctk.CTkLabel(self.sidebar, text="", font=("Arial", 14, "bold"), text_color=cfg.COLORS["warning"])
        self.lbl_total_count.pack(padx=20, pady=0, anchor="w")

        # --- NEW TIME SELECTION (DROPDOWN) ---
        time_group = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        time_group.pack(fill="x", padx=10, pady=5)
        
        self.lbl_time_title = ctk.CTkLabel(time_group, text=self.TEXTS[self.current_lang]["time_label"], font=("Arial", 16, "bold"))
        self.lbl_time_title.pack(anchor="w", padx=5, pady=0)
        time_frame = ctk.CTkFrame(time_group, fg_color="transparent")
        time_frame.pack(fill="x", pady=2)
        
        # Generate Time List (00:00 - 23:00)
        self.time_values = [f"{h:02d}:00" for h in range(24)]
        self.time_values_end = self.time_values + ["23:59"]

        # Dropdown Start
        self.combo_time_start = ctk.CTkOptionMenu(time_frame, values=self.time_values, width=90, height=30)
        self.combo_time_start.set("00:00") # Default
        self.combo_time_start.pack(side="left", padx=(5, 5))

        ctk.CTkLabel(time_frame, text="-", font=("Arial", 18, "bold")).pack(side="left")

        # Dropdown End
        self.combo_time_end = ctk.CTkOptionMenu(time_frame, values=self.time_values_end, width=90, height=30)
        self.combo_time_end.set("23:59") # Default
        self.combo_time_end.pack(side="left", padx=(5, 5))

        # Control Group (Row & Limit)
        ctrl_group = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        ctrl_group.pack(fill="x", padx=10, pady=5)
        
        self.lbl_row_title = ctk.CTkLabel(ctrl_group, text=self.TEXTS[self.current_lang]["row_label"], font=("Arial", 14, "bold"))
        self.lbl_row_title.pack(anchor="w", padx=5, pady=0)
        row_frame = ctk.CTkFrame(ctrl_group, fg_color="transparent")
        row_frame.pack(fill="x", pady=2)
        self.entry_start = ctk.CTkEntry(row_frame, width=80, height=30, placeholder_text="Start")
        self.entry_start.pack(side="left", padx=(5, 5))
        ctk.CTkLabel(row_frame, text="-", font=("Arial", 18, "bold")).pack(side="left")
        self.entry_end = ctk.CTkEntry(row_frame, width=80, height=30, placeholder_text="End")
        self.entry_end.pack(side="left", padx=(5, 5))

        self.lbl_limit_title = ctk.CTkLabel(ctrl_group, text=self.TEXTS[self.current_lang]["limit_label"], font=("Arial", 14, "bold"))
        self.lbl_limit_title.pack(anchor="w", padx=5, pady=(5, 0))
        limit_frame = ctk.CTkFrame(ctrl_group, fg_color="transparent")
        limit_frame.pack(fill="x", pady=2)
        
        vcmd = (self.register(self.validate_number_input), '%P')
        self.entry_limit = ctk.CTkEntry(limit_frame, width=90, height=30, validate="key", validatecommand=vcmd)
        self.entry_limit.pack(side="left", padx=(5, 5))
        self.entry_limit.insert(0, "2000")
        self.last_limit_value = "2000"
        self.btn_load_all = ctk.CTkButton(limit_frame, text="All", width=50, height=30, fg_color=cfg.COLORS["warning"], text_color="black", command=self.toggle_limit_mode)
        self.btn_load_all.pack(side="left", padx=5)
        
        self.btn_apply = ctk.CTkButton(ctrl_group, text=self.TEXTS[self.current_lang]["apply_btn"], font=("Arial", 16, "bold"), fg_color=cfg.COLORS["success"], height=35, command=self.apply_settings)
        self.btn_apply.pack(fill="x", padx=5, pady=10)

        self.btn_zoom_car = ctk.CTkButton(self.sidebar, text=self.TEXTS[self.current_lang]["zoom_btn"], height=35, font=("Arial", 16, "bold"), fg_color=cfg.COLORS["primary"], command=self.zoom_to_car)
        self.btn_zoom_car.pack(padx=20, pady=(10, 5), fill="x")

        # Measure Button
        self.btn_measure = ctk.CTkButton(self.sidebar, text=self.TEXTS[self.current_lang]["measure_btn_start"], height=35, font=("Arial", 16, "bold"), 
                                         fg_color="gray40", hover_color="gray50", command=self.toggle_measure_mode)
        self.btn_measure.pack(padx=20, pady=(5, 5), fill="x")

        self.btn_clear = ctk.CTkButton(self.sidebar, text=self.TEXTS[self.current_lang]["clear_btn"], height=35, font=("Arial", 14, "bold"), fg_color="transparent", border_width=2, text_color=("gray10", "#DCE4EE"), command=self.clear_map)
        self.btn_clear.pack(padx=20, pady=5, fill="x")
        
        # Info Dashboard
        self.info_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.info_frame.pack(fill="both", expand=True, padx=20, pady=5)

        def create_stat_row(parent, title, icon="", key=""):
            f = ctk.CTkFrame(parent, fg_color="transparent")
            f.pack(fill="x", pady=2)
            lbl_title = ctk.CTkLabel(f, text=f"{icon} {title}", font=("Arial", 16), text_color="white")
            lbl_title.pack(anchor="w")
            lbl_val = ctk.CTkLabel(f, text="-", font=("Consolas", 22, "bold"), text_color=cfg.COLORS["primary"])
            lbl_val.pack(anchor="w")
            return lbl_val, lbl_title

        self.lbl_time, self.lbl_time_title_w = create_stat_row(self.info_frame, self.TEXTS[self.current_lang]["info_time"], "🕒")
        self.lbl_speed, self.lbl_speed_title_w = create_stat_row(self.info_frame, self.TEXTS[self.current_lang]["info_speed"], "🚀")
        
        self.lbl_status_title = ctk.CTkLabel(self.info_frame, text=self.TEXTS[self.current_lang]["info_status"], font=("Arial", 16), text_color="white")
        self.lbl_status_title.pack(anchor="w", pady=(10,2))
        self.lbl_status = ctk.CTkLabel(self.info_frame, text="-", font=("Arial", 18, "bold"), text_color="white", fg_color="gray30", corner_radius=8, padx=15, pady=5)
        self.lbl_status.pack(anchor="w", pady=2)

        self.lbl_coord_title = ctk.CTkLabel(self.info_frame, text=self.TEXTS[self.current_lang]["info_coord"], font=("Arial", 16), text_color="white")
        self.lbl_coord_title.pack(anchor="w", pady=(10, 2))
        coord_frame = ctk.CTkFrame(self.info_frame, fg_color="transparent")
        coord_frame.pack(fill="x", anchor="w", pady=2)
        self.lbl_coord = ctk.CTkLabel(coord_frame, text="- , -", font=("Consolas", 20, "bold"), text_color=cfg.COLORS["primary"])
        self.lbl_coord.pack(side="left")
        self.btn_copy_coord = ctk.CTkButton(coord_frame, text="📋", width=30, height=25, font=("Arial", 12), command=self.copy_coords_to_clipboard)
        self.btn_copy_coord.pack(side="left", padx=10)

        # Bottom Status & Language Switch
        self.bottom_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.bottom_frame.pack(side="bottom", pady=20, fill="x", padx=10)

        self.lbl_file_info = ctk.CTkLabel(self.bottom_frame, text=self.TEXTS[self.current_lang]["file_ready"], font=("Arial", 16, "bold"), text_color=cfg.COLORS["primary"]) 
        self.lbl_file_info.pack(side="left", padx=(5, 0))

        self.switch_lang = ctk.CTkSwitch(self.bottom_frame, text=self.current_lang, command=self.toggle_language,
                                         onvalue="TH", offvalue="EN", width=50)
        self.switch_lang.pack(side="right", padx=(0, 5))
        
        if self.current_lang == "TH":
            self.switch_lang.select()
        else:
            self.switch_lang.deselect()

        # --- RIGHT PANEL ---
        self.right_panel = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.right_panel.grid(row=0, column=1, rowspan=3, sticky="nsew")
        
        self.right_panel.grid_rowconfigure(0, weight=1) 
        self.right_panel.grid_rowconfigure(1, weight=0) 
        self.right_panel.grid_rowconfigure(2, weight=0) 
        self.right_panel.grid_columnconfigure(0, weight=1)

        # 1. Map
        self.map_widget = tkintermapview.TkinterMapView(self.right_panel, corner_radius=0, use_database_only=False, database_path="map_cache.db")
        self.map_widget.grid(row=0, column=0, sticky="nsew")
        self.map_widget.set_position(13.7563, 100.5018)
        self.map_widget.set_zoom(6)
        
        # Set Default Map Style
        self.map_widget.set_tile_server("https://mt0.google.com/vt/lyrs=m&hl=en&x={x}&y={y}&z={z}&s=Ga", max_zoom=22)
        
        self.map_widget.add_left_click_map_command(self.on_map_click)
        
        # Overlays
        self.map_option_menu = ctk.CTkOptionMenu(self.map_widget, 
                                                 values=["Google Normal", "OpenStreetMap", "Google Satellite"],
                                                 height=32, width=150,
                                                 font=("Arial", 12, "bold"),
                                                 fg_color="#333333", button_color="#444444",
                                                 button_hover_color="#555555", text_color="white",
                                                 corner_radius=15, anchor="center",
                                                 command=self.change_map_style)
        self.map_option_menu.place(relx=0.97, rely=0.88, anchor="se")
        self.map_option_menu.set("Google Normal")

        self.scale_canvas = TransparentScaleBar(self.map_widget, width=220, height=50)
        self.scale_canvas.place(relx=0.96, rely=0.97, anchor="se")

        # Measure Info Box
        self.measure_info_frame = ctk.CTkFrame(self.map_widget, fg_color="white", corner_radius=12, border_width=1, border_color="#cccccc")
        self.lbl_measure_title = ctk.CTkLabel(self.measure_info_frame, text=self.TEXTS[self.current_lang]["measure_title"], font=("Arial", 14, "bold"), text_color="#333333")
        self.lbl_measure_title.pack(anchor="w", padx=15, pady=(10,0))
        self.lbl_measure_hint = ctk.CTkLabel(self.measure_info_frame, text=self.TEXTS[self.current_lang]["measure_hint"], font=("Arial", 12), text_color="#666666")
        self.lbl_measure_hint.pack(anchor="w", padx=15, pady=(0, 5))
        self.measure_label = ctk.CTkLabel(self.measure_info_frame, text=self.TEXTS[self.current_lang]["measure_total"] + "0 m.", font=("Arial", 16, "bold"), text_color="black")
        self.measure_label.pack(anchor="w", padx=15, pady=(5, 15))

        # Map Bindings
        self.map_widget.canvas.bind("<MouseWheel>", self.update_map_scale, add="+")
        self.map_widget.canvas.bind("<ButtonRelease-1>", self.update_map_scale, add="+")
        self.map_widget.canvas.bind("<Configure>", self.update_map_scale, add="+")
        
        self.map_widget.canvas.bind("<B1-Motion>", self.update_offscreen_indicator, add="+")
        self.map_widget.canvas.bind("<ButtonRelease-1>", self.update_offscreen_indicator, add="+")
        
        # [KEY FIX] Focus
        self.map_widget.canvas.bind("<Button-1>", lambda e: self.focus_set(), add="+")

        # 2. Control Frame (Timeline)
        self.control_frame = ctk.CTkFrame(self.right_panel, corner_radius=0, height=60, fg_color=("white", "#212121"))
        self.control_frame.grid(row=1, column=0, sticky="ew")
        self.control_frame.grid_propagate(False) 
        
        self.lbl_timeline_title = ctk.CTkLabel(self.control_frame, text=self.TEXTS[self.current_lang]["timeline"], font=("Arial", 14, "bold"))
        self.lbl_timeline_title.pack(side="left", padx=15)
        self.slider = ctk.CTkSlider(self.control_frame, from_=0, to=100, command=self.on_slider_move, height=20)
        self.slider.pack(side="left", fill="x", expand=True, padx=(10, 5), pady=15)

        self.btn_toggle_log = ctk.CTkButton(self.control_frame, text=self.TEXTS[self.current_lang]["hide_log"], width=60, height=28, 
                                            font=("Arial", 12, "bold"), fg_color="gray30", hover_color="gray40",
                                            command=self.toggle_log_view)
        self.btn_toggle_log.pack(side="right", padx=15, pady=10)

        # 3. Log Frame
        self.log_container = ctk.CTkFrame(self.right_panel, corner_radius=0, height=110, fg_color="gray15")
        self.log_container.grid(row=2, column=0, sticky="nsew")
        self.log_container.grid_propagate(False)

        self.log_scroll = ctk.CTkScrollableFrame(self.log_container, fg_color="transparent")
        self.log_scroll.pack(fill="both", expand=True, padx=5, pady=0)

        self.init_log_pool()

    # --- UI UPDATES & HELPERS ---
    def toggle_language(self):
        self.current_lang = self.switch_lang.get()
        self.switch_lang.configure(text=self.current_lang)
        self.update_ui_text()

    def update_ui_text(self):
        t = self.TEXTS[self.current_lang]
        self.lbl_app_title.configure(text=t["app_title"])
        self.btn_load.configure(text=t["load_btn"])
        self.lbl_date_title.configure(text=t["date_label"])
        
        # Update Date Combo default if needed
        if self.date_var.get().startswith("--"):
            self.date_var.set(t["default_date"])
            
        self.lbl_time_title.configure(text=t["time_label"])
        self.lbl_row_title.configure(text=t["row_label"])
        self.lbl_limit_title.configure(text=t["limit_label"])
        self.btn_apply.configure(text=t["apply_btn"])
        self.btn_zoom_car.configure(text=t["zoom_btn"])
        
        if self.is_measuring:
            self.btn_measure.configure(text=t["measure_btn_stop"])
        else:
            self.btn_measure.configure(text=t["measure_btn_start"])
            
        self.btn_clear.configure(text=t["clear_btn"])
        self.lbl_time_title_w.configure(text=f"🕒 {t['info_time']}")
        self.lbl_speed_title_w.configure(text=f"🚀 {t['info_speed']}")
        self.lbl_status_title.configure(text=t["info_status"])
        self.lbl_coord_title.configure(text=t["info_coord"])
        
        if self.lbl_file_info.cget("text") in ["พร้อมใช้งาน", "Ready"]:
            self.lbl_file_info.configure(text=t["file_ready"])
        elif self.lbl_file_info.cget("text") in ["โหลดสำเร็จ", "Loaded successfully"]:
            self.lbl_file_info.configure(text=t["file_loaded"])
            
        self.lbl_timeline_title.configure(text=t["timeline"])
        
        if self.log_visible:
            self.btn_toggle_log.configure(text=t["hide_log"])
        else:
            self.btn_toggle_log.configure(text=t["show_log"])
            
        self.lbl_measure_title.configure(text=t["measure_title"])
        self.lbl_measure_hint.configure(text=t["measure_hint"])
        
        # Refresh dynamic labels
        if self.filtered_df is not None:
             self.lbl_total_count.configure(text=t["total_count"].format(len(self.filtered_df)))
             
        self.update_total_distance_label()
        self.update_map_scale() # Refresh scale bar text

    def update_map_scale(self, event=None):
        try:
            zoom = self.map_widget.zoom
            if zoom is None: return
            lat = self.map_widget.get_position()[0]
            meters_per_pixel = 156543.03392 * math.cos(math.radians(lat)) / (2 ** zoom)
            target_px = 100
            approx_dist = meters_per_pixel * target_px
            magnitude = 10 ** math.floor(math.log10(approx_dist))
            normalized = approx_dist / magnitude
            if normalized < 1.5: nice_val = 1
            elif normalized < 3.5: nice_val = 2
            elif normalized < 7.5: nice_val = 5
            else: nice_val = 10
            real_dist_m = nice_val * magnitude
            final_width_px = real_dist_m / meters_per_pixel
            
            # Localize units
            if self.current_lang == "TH":
                unit_km, unit_m = "กม.", "ม."
            else:
                unit_km, unit_m = "km", "m"

            label_text = f"{int(real_dist_m/1000)} {unit_km}" if real_dist_m >= 1000 else f"{int(real_dist_m)} {unit_m}"
            self.scale_canvas.update_scale(label_text, final_width_px)
            self.update_offscreen_indicator()
        except:
            self.scale_canvas.delete("all")

    def toggle_log_view(self):
        self.log_visible = not self.log_visible
        t = self.TEXTS[self.current_lang]
        if self.log_visible:
            self.log_container.grid(row=2, column=0, sticky="nsew")
            self.btn_toggle_log.configure(text=t["hide_log"])
        else:
            self.log_container.grid_forget()
            self.btn_toggle_log.configure(text=t["show_log"])

    # --- OFF-SCREEN INDICATOR WITH DISTANCE ---
    def update_offscreen_indicator(self, event=None):
        self.map_widget.canvas.delete("offscreen_arrow")
        if not self.car_marker: return

        try:
            zoom = self.map_widget.zoom
            if zoom is None: return
            
            c_lat, c_lon = self.map_widget.get_position()
            t_lat, t_lon = self.car_marker.position
            
            # คำนวณระยะทาง
            dist = haversine_distance(c_lat, c_lon, t_lat, t_lon)
            if dist >= 1000:
                dist_str = f"{dist/1000:.1f} กม."
            else:
                dist_str = f"{int(dist)} ม."

            def get_px(lat, lon):
                tile_size = 256
                num_tiles = 2 ** zoom
                x = (lon + 180) / 360 * num_tiles * tile_size
                y = (1 - math.log(math.tan(math.radians(lat)) + 1 / math.cos(math.radians(lat))) / math.pi) / 2 * num_tiles * tile_size
                return x, y

            cx, cy = get_px(c_lat, c_lon)
            tx, ty = get_px(t_lat, t_lon)
            
            w = self.map_widget.winfo_width()
            h = self.map_widget.winfo_height()
            
            screen_x = (w / 2) + (tx - cx)
            screen_y = (h / 2) + (ty - cy)
            
            if 0 <= screen_x <= w and 0 <= screen_y <= h:
                return

            center_x, center_y = w / 2, h / 2
            dx = screen_x - center_x
            dy = screen_y - center_y
            angle = math.atan2(dy, dx)
            
            pad = 20 
            if dx == 0: dx = 0.001
            slope = dy / dx
            
            if dx > 0:
                edge_x = w - pad
                edge_y = center_y + slope * (edge_x - center_x)
            else:
                edge_x = pad
                edge_y = center_y + slope * (edge_x - center_x)
                
            if edge_y < pad or edge_y > h - pad:
                if dy > 0:
                    edge_y = h - pad
                    edge_x = center_x + (edge_y - center_y) / slope
                else:
                    edge_y = pad
                    edge_x = center_x + (edge_y - center_y) / slope

            # [CONFIG] BIG ARROW
            arrow_len = 40 
            tip_x, tip_y = edge_x, edge_y
            
            angle1 = angle + math.radians(150)
            angle2 = angle - math.radians(150)
            
            p1_x = tip_x + arrow_len * math.cos(angle1)
            p1_y = tip_y + arrow_len * math.sin(angle1)
            p2_x = tip_x + arrow_len * math.cos(angle2)
            p2_y = tip_y + arrow_len * math.sin(angle2)
            
            self.map_widget.canvas.create_polygon(tip_x, tip_y, p1_x, p1_y, p2_x, p2_y, 
                                                  fill="#ff0000", outline="white", width=2, 
                                                  tags=("offscreen_arrow", "clickable_arrow"))
            
            # [CONFIG] TEXT OFFSET
            text_offset = 60 
            text_x = edge_x - text_offset * math.cos(angle)
            text_y = edge_y - text_offset * math.sin(angle)
            
            self.map_widget.canvas.create_text(text_x, text_y, text=dist_str, 
                                               fill="#ff0000", font=("Arial", 12, "bold"),
                                               tags=("offscreen_arrow", "clickable_arrow"))
            
            self.map_widget.canvas.tag_bind("clickable_arrow", "<Button-1>", lambda e: self.zoom_to_car())
            self.map_widget.canvas.tag_raise("offscreen_arrow")

        except Exception as e:
            pass

    # --- MEASURE LOGIC ---
    def toggle_measure_mode(self):
        self.is_measuring = not self.is_measuring
        self.map_widget.right_click_menu_commands = []
        t = self.TEXTS[self.current_lang]
        if self.is_measuring:
            self.btn_measure.configure(text=t["measure_btn_stop"], fg_color=cfg.COLORS["danger"])
            self.map_widget.canvas.config(cursor="crosshair")
            self.measure_info_frame.place(relx=0.5, rely=0.03, anchor="n")
            self.clear_measurements()
            self.map_widget.add_right_click_menu_command(label="❌ Undo", command=self.undo_measure_point, pass_coords=False)
            self.map_widget.add_right_click_menu_command(label="🗑️ Clear", command=self.clear_measurements, pass_coords=False)
        else:
            self.btn_measure.configure(text=t["measure_btn_start"], fg_color="gray40")
            self.map_widget.canvas.config(cursor="")
            self.measure_info_frame.place_forget()
            self.clear_measurements()
            self.map_widget.right_click_menu_commands = []

    def on_map_click(self, coords):
        if not self.is_measuring: return
        lat, lon = coords
        self.measure_coords.append((lat, lon))
        marker = self.map_widget.set_marker(lat, lon, text="", icon=self.circle_icon, icon_anchor="center")
        self.measure_point_markers.append(marker)
        if len(self.measure_coords) > 1:
            p1 = self.measure_coords[-2]
            p2 = self.measure_coords[-1]
            path_bg = self.map_widget.set_path([p1, p2], color="black", width=5)
            path_fg = self.map_widget.set_path([p1, p2], color="white", width=3)
            self.measure_segment_paths.append([path_bg, path_fg])
            dist = haversine_distance(p1[0], p1[1], p2[0], p2[1])
            dist_str = f"{dist/1000:.2f} กม." if dist >= 1000 else f"{dist:.2f} ม."
            mid_lat = (p1[0] + p2[0]) / 2
            mid_lon = (p1[1] + p2[1]) / 2
            label = self.map_widget.set_marker(mid_lat, mid_lon, text=dist_str, text_color="black", icon=self.trans_icon, font=("Arial", 12, "bold"))
            self.measure_segment_labels.append(label)
        self.update_total_distance_label()

    def undo_measure_point(self, event=None):
        if not self.is_measuring or not self.measure_coords: return
        self.measure_coords.pop()
        if self.measure_point_markers:
            m = self.measure_point_markers.pop()
            try: m.delete()
            except: pass
        if self.measure_segment_paths:
            paths = self.measure_segment_paths.pop()
            for p in paths:
                try: p.delete()
                except: pass
        if self.measure_segment_labels:
            l = self.measure_segment_labels.pop()
            try: l.delete()
            except: pass
        self.update_total_distance_label()

    def update_total_distance_label(self):
        total_dist = calculate_total_distance(self.measure_coords)
        if total_dist >= 1000:
            txt_m = f"{total_dist/1000:.2f} km."
        else:
            txt_m = f"{total_dist:.2f} m."
        feet = total_dist * 3.28084
        if feet >= 5280:
            miles = feet / 5280
            txt_imp = f"{miles:.2f} mi."
        else:
            txt_imp = f"{feet:,.2f} ft."
        t = self.TEXTS[self.current_lang]
        self.measure_label.configure(text=f"{t['measure_total']}{txt_m} ({txt_imp})", text_color="black")

    def clear_measurements(self):
        for m in self.measure_point_markers:
            try: m.delete()
            except: pass
        self.measure_point_markers = []
        for paths in self.measure_segment_paths:
            for p in paths:
                try: p.delete()
                except: pass
        self.measure_segment_paths = []
        for l in self.measure_segment_labels:
            try: l.delete()
            except: pass
        self.measure_segment_labels = []
        self.measure_coords = []
        self.update_total_distance_label()

    # --- ACTIONS ---
    def load_csv_action(self):
        file_path = filedialog.askopenfilename(filetypes=[("CSV Files", "*.csv")])
        if not file_path: return
        self.process_loaded_file(file_path)

    def process_loaded_file(self, file_path):
        t = self.TEXTS[self.current_lang]
        self.lbl_file_info.configure(text=t["file_reading"])
        self.update_idletasks()
        df, error = process_gps_data(file_path)
        if error:
            messagebox.showerror("Error", error)
            self.lbl_file_info.configure(text=t["file_error"])
            return
        self.raw_df = df
        unique_dates = sorted(self.raw_df['date_str'].unique())
        combo_values = [cfg.ALL_DAYS_OPTION] + unique_dates
        self.date_combo.configure(state="normal", values=combo_values)
        self.date_combo.set(cfg.ALL_DAYS_OPTION) 
        self.entry_start.delete(0, "end")
        self.entry_end.delete(0, "end")
        self.combo_time_start.set("00:00")
        self.combo_time_end.set("23:59")
        self.on_date_selected(cfg.ALL_DAYS_OPTION)
        self.lbl_file_info.configure(text=t["file_loaded"])

    def drop_file(self, event):
        file_path = event.data
        if file_path.startswith('{') and file_path.endswith('}'):
            file_path = file_path[1:-1]
        self.process_loaded_file(file_path)

    def on_date_selected(self, selected_date):
        if self.raw_df is None: return
        if selected_date == cfg.ALL_DAYS_OPTION:
            self.filtered_df = self.raw_df.copy()
        else:
            self.filtered_df = self.raw_df[self.raw_df['date_str'] == selected_date].copy()
        t = self.TEXTS[self.current_lang]
        self.lbl_total_count.configure(text=t["total_count"].format(len(self.filtered_df)))
        self.apply_settings()

    def toggle_limit_mode(self):
        current_val = self.entry_limit.get().strip()
        # Ensure state is normal before editing
        self.entry_limit.configure(state="normal")
        
        if current_val:
            self.last_limit_value = current_val
            self.entry_limit.delete(0, "end")
            self.entry_limit.focus_set() # Focus to entry so user can type immediately
            # self.btn_load_all.configure(text="Limit") # Keep text as All
        else:
            val = getattr(self, "last_limit_value", "2000")
            self.entry_limit.insert(0, val)
            # self.btn_load_all.configure(text="All")
            
        self.apply_settings()

    def apply_settings(self):
        if self.filtered_df is None or self.filtered_df.empty: return
        
        # 1. Filter by Time (Using OptionMenu)
        t_start_str = self.combo_time_start.get()
        t_end_str = self.combo_time_end.get()
        
        df_to_process = self.filtered_df.copy()
        
        # คอลัมน์เวลาชื่ออะไร? หาให้เจอ
        cols = {c.lower().strip(): c for c in df_to_process.columns}
        col_time = cols.get('r-time') or cols.get('time')
        
        if col_time and t_start_str and t_end_str:
            try:
                # แปลงเวลาใน DF เป็น string HH:MM เพื่อเทียบ
                time_series = df_to_process[col_time].dt.strftime('%H:%M')
                mask = (time_series >= t_start_str) & (time_series <= t_end_str)
                df_to_process = df_to_process[mask]
            except Exception as e:
                print(f"Time filter error: {e}")

        # 2. Filter by Row
        start_val = self.entry_start.get().strip()
        end_val = self.entry_end.get().strip()
        if start_val or end_val:
            try:
                s = int(start_val) if start_val else 0
                e = int(end_val) if end_val else len(df_to_process)
                if s < e: df_to_process = df_to_process.iloc[s:e]
            except ValueError: pass 
            
        limit_val = 0
        try:
            val = self.entry_limit.get().strip()
            if val: limit_val = int(val)
        except: pass
        
        t = self.TEXTS[self.current_lang]
        self.lbl_total_count.configure(text=t["display_count"].format(len(df_to_process)))
        self.process_display_data(df_to_process, limit_val)
        self.draw_map_elements()

    def process_display_data(self, df, max_points):
        total = len(df)
        if total == 0: return
        self.reset_logs()
        self.cached_logs = []
        step = 1
        if max_points > 0 and total > max_points:
            step = max(1, total // max_points)
        path_df = df.iloc[::step, :]
        cols = {c.lower().strip(): c for c in df.columns}
        col_lat = cols.get('lat')
        col_lon = cols.get('long') or cols.get('lon') or cols.get('lng')
        col_time = cols.get('r-time') or cols.get('time')
        col_speed = cols.get('gps_speed') or cols.get('speed')
        col_acc = cols.get('acc-on') or cols.get('acc')
        self.path_points = []
        for _, row in path_df.iterrows():
            lat, lon = float(row[col_lat]), float(row[col_lon])
            if lat != 0.0 and lon != 0.0:
                self.path_points.append((lat, lon))
        self.animation_points = []
        records = path_df.to_dict('records')
        prev_status = None
        
        # [SETTING] Smooth
        self.interp_steps = 1 

        for i in range(len(records)):
            p1 = records[i]
            if i < len(records) - 1:
                p2 = records[i+1]
                lat1, lon1 = float(p1[col_lat]), float(p1[col_lon])
                lat2, lon2 = float(p2[col_lat]), float(p2[col_lon])
            else:
                lat1, lon1 = float(p1[col_lat]), float(p1[col_lon])
                lat2, lon2 = lat1, lon1
            speed1 = float(p1.get(col_speed, 0)) if col_speed else 0
            acc_on = str(p1.get(col_acc, "0")) if col_acc else "0"
            is_run = ("1" in acc_on) or ("ON" in acc_on.upper())
            if not is_run: st, cl, ikey = "Engine Off", cfg.COLORS["danger"], "stop"
            elif speed1 == 0: st, cl, ikey = "Idling", cfg.COLORS["warning"], "idle"
            else: st, cl, ikey = "Running", cfg.COLORS["success"], "run"
            if st != prev_status:
                prev_status = st
                if "Idling" in st or "Engine Off" in st:
                    try: t_str = p1[col_time].strftime('%d/%m/%Y %H:%M:%S')
                    except: t_str = "-"
                    self.cached_logs.append({
                        "trigger_idx": len(self.animation_points),
                        "status": st, "time": t_str, "row": path_df.index[i], "color": cl
                    })
            if i < len(records) - 1:
                for j in range(self.interp_steps):
                    t = j / self.interp_steps
                    lat_next = lat1 + (lat2 - lat1) * t
                    lon_next = lon1 + (lon2 - lon1) * t
                    self.animation_points.append({
                        "lat": lat_next, "lon": lon_next,
                        "real_lat": lat1, "real_lon": lon1,
                        "time": p1[col_time].strftime('%d/%m/%Y %H:%M:%S'),
                        "speed": speed1, "status": st, "color_code": cl, "icon_key": ikey
                    })
            else:
                self.animation_points.append({
                    "lat": lat1, "lon": lon1,
                    "real_lat": lat1, "real_lon": lon1,
                    "time": p1[col_time].strftime('%d/%m/%Y %H:%M:%S'),
                    "speed": speed1, "status": st, "color_code": cl, "icon_key": ikey
                })

    def draw_map_elements(self):
        self.clear_map()
        if not self.path_points: return
        if len(self.path_points) > 1:
            try: self.path_line = self.map_widget.set_path(self.path_points, color="#004EFF", width=3)
            except: pass
        try:
            if len(self.path_points) > 0:
                s = self.path_points[0]
                e = self.path_points[-1]
                self.start_marker = self.map_widget.set_marker(s[0], s[1], text="Start", marker_color_circle="green", marker_color_outside="white")
                self.end_marker = self.map_widget.set_marker(e[0], e[1], text="End", marker_color_circle="red", marker_color_outside="white")
            if len(self.animation_points) > 0:
                first = self.animation_points[0]
                self.current_icon_key = first['icon_key']
                self.car_marker = self.map_widget.set_marker(
                    first['lat'], first['lon'], text="", icon=self.icons[self.current_icon_key], icon_anchor="center"
                )
        except: pass
        
        # [KEY FIX] ตั้งค่าตัวแปรแม่ข่าย
        self.current_frame = 0
        n_frames = len(self.animation_points)
        if n_frames > 1:
            self.slider.configure(from_=0, to=n_frames-1, number_of_steps=n_frames, state="normal")
            self.slider.set(0)
        else:
            self.slider.configure(state="disabled") 
        
        self.after(200, self.zoom_to_fit)
        self.perform_update(0) 
        self.update_map_scale()

    # --- CONTROLS [GAME STYLE] ---
    def on_key_press(self, event, direction):
        self.current_key_direction = direction
        if self.key_loop_job is None:
            self.move_loop()
        return "break" 

    def on_key_release(self, event, direction):
        if self.current_key_direction == direction:
            self.current_key_direction = 0
        return "break"

    def move_loop(self):
        if self.current_key_direction == 0:
            self.key_loop_job = None
            return

        new_val = self.current_frame + self.current_key_direction
        
        if 0 <= new_val < len(self.animation_points):
            self.slider.set(new_val) 
            self.perform_update(new_val)
            self.update_idletasks() 
            self.key_loop_job = self.after(250, self.move_loop)
        else:
            self.current_key_direction = 0
            self.key_loop_job = None

    def move_forward(self, event=None):
        if not self.animation_points: return
        new_val = self.current_frame + 1
        if new_val < len(self.animation_points):
            self.slider.set(new_val)
            self.perform_update(new_val)

    def move_backward(self, event=None):
        if not self.animation_points: return
        new_val = self.current_frame - 1
        if new_val >= 0:
            self.slider.set(new_val)
            self.perform_update(new_val)

    def on_slider_move(self, value):
        if self.slider_job:
            self.after_cancel(self.slider_job)
            self.slider_job = None
            
        current_time = time.time()
        # [THROTTLING] Update max 20 fps (0.05s) to be smooth but not heavy
        if current_time - self.last_update_time > 0.05:
            self.perform_update(int(value))
            self.last_update_time = current_time
        else:
            # Trailing update to ensure final value is set
            self.slider_job = self.after(50, lambda: self.perform_update(int(value)))

    def perform_update(self, value):
        if not self.animation_points: return
        
        idx = int(value)
        if idx >= len(self.animation_points): 
            idx = len(self.animation_points) - 1
        
        # [KEY] Update Master Variable
        self.current_frame = idx 
            
        try:
            data = self.animation_points[idx]
            if self.car_marker is None:
                 self.car_marker = self.map_widget.set_marker(data['lat'], data['lon'], text="", icon=self.icons[data['icon_key']], icon_anchor="center")
                 self.current_icon_key = data['icon_key']
            if data['icon_key'] != self.current_icon_key:
                self.car_marker.change_icon(self.icons[data['icon_key']])
                self.current_icon_key = data['icon_key']
            
            self.car_marker.set_position(data['lat'], data['lon'])
            self.lbl_time.configure(text=data['time'])
            self.lbl_speed.configure(text=f"{data['speed']:.1f}")
            
            status_key = f"status_{data['status']}"
            status_text = self.TEXTS[self.current_lang].get(status_key, data['status'])
            self.lbl_status.configure(text=status_text, fg_color=data['color_code'])
            
            self.lbl_coord.configure(text=f"{data['real_lat']:.5f}, {data['real_lon']:.5f}")
            
            logs_to_show = [log for log in self.cached_logs if log['trigger_idx'] <= idx]
            self.update_logs_display(logs_to_show)
            self.update_map_scale() 
        except: pass

    # ... (Rest of functions unchanged)
    def zoom_to_fit(self):
        if not self.path_points: return
        lats = [p[0] for p in self.path_points]
        lons = [p[1] for p in self.path_points]
        if lats and lons:
            try:
                min_lat, max_lat = min(lats), max(lats)
                min_lon, max_lon = min(lons), max(lons)
                if min_lat == max_lat and min_lon == max_lon:
                    self.map_widget.set_position(min_lat, min_lon)
                    self.map_widget.set_zoom(15)
                else:
                    self.map_widget.fit_bounding_box((max_lat, min_lon), (min_lat, max_lon))
            except: pass

    def zoom_to_car(self):
        if self.car_marker:
            pos = self.car_marker.position
            self.map_widget.set_position(pos[0], pos[1])
            self.update_map_scale()
        else:
            t = self.TEXTS[self.current_lang]
            messagebox.showinfo("Info", t["no_car"])

    def copy_coords_to_clipboard(self):
        text = self.lbl_coord.cget("text")
        if text and text != "- , -":
            self.clipboard_clear()
            self.clipboard_append(text)
            t = self.TEXTS[self.current_lang]
            messagebox.showinfo("Copied", f"{t['copied']} {text}")

    def change_map_style(self, new_map_style):
        if new_map_style == "OpenStreetMap":
            self.map_widget.set_tile_server("https://a.tile.openstreetmap.org/{z}/{x}/{y}.png")
        elif new_map_style == "Google Normal":
            self.map_widget.set_tile_server("https://mt0.google.com/vt/lyrs=m&hl=en&x={x}&y={y}&z={z}&s=Ga", max_zoom=22)
        elif new_map_style == "Google Satellite":
            self.map_widget.set_tile_server("https://mt0.google.com/vt/lyrs=s&hl=en&x={x}&y={y}&z={z}&s=Ga", max_zoom=22)
        self.update_map_scale()

    def clear_map(self):
        try:
            self.map_widget.delete_all_marker()
            self.map_widget.delete_all_path()
        except: pass
        self.path_line = None
        self.car_marker = None
        self.start_marker = None
        self.end_marker = None
        self.lbl_speed.configure(text="-")
        self.lbl_time.configure(text="-")
        self.lbl_status.configure(text="-", fg_color="gray30")
        self.lbl_coord.configure(text="- , -")
        # self.scale_canvas.delete("all")
        self.reset_logs()
        self.is_measuring = False
        self.measure_coords = []
        self.measure_point_markers = []
        self.measure_segment_paths = []
        self.measure_segment_labels = []
        t = self.TEXTS[self.current_lang]
        self.btn_measure.configure(text=t["measure_btn_start"], fg_color="gray40")
        self.measure_info_frame.place_forget()
        self.map_widget.canvas.config(cursor="")
        self.map_widget.right_click_menu_commands = [] 
        # Clear arrow
        self.map_widget.canvas.delete("offscreen_arrow")

    # --- LOG POOL ---
    def init_log_pool(self):
        self.log_widgets_pool = []
        for _ in range(self.MAX_LOG_DISPLAY):
            row_frame = ctk.CTkFrame(self.log_scroll, fg_color="transparent", height=20)
            status_box = ctk.CTkLabel(row_frame, text="", width=15, height=15, corner_radius=4)
            status_box.pack(side="left", padx=(5, 5))
            info_text = ctk.CTkLabel(row_frame, text="", font=("Consolas", 14), text_color="white")
            info_text.pack(side="left")
            self.log_widgets_pool.append({"frame": row_frame, "box": status_box, "label": info_text, "active": False})

    def update_logs_display(self, logs_to_show):
        raw_data = logs_to_show[-self.MAX_LOG_DISPLAY:] if logs_to_show else []
        display_data = raw_data[::-1] 
        for i in range(self.MAX_LOG_DISPLAY):
            widget_set = self.log_widgets_pool[i]
            if i < len(display_data):
                data = display_data[i]
                widget_set["box"].configure(fg_color=data['color'])
                status_key = f"status_{data['status']}"
                status_text = self.TEXTS[self.current_lang].get(status_key, data['status'])
                widget_set["label"].configure(text=f"[{data['time']}]  {status_text}  (Row: {data['row']})")
                if not widget_set["active"]:
                    widget_set["frame"].pack(fill="x", pady=0)
                    widget_set["active"] = True
            else:
                if widget_set["active"]:
                    widget_set["frame"].pack_forget()
                    widget_set["active"] = False
    
    def reset_logs(self):
        self.update_logs_display([])

if __name__ == "__main__":
    app = GPSTrackingApp()
    app.mainloop()