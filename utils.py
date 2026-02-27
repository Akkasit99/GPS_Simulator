import pandas as pd
from PIL import Image, ImageTk, ImageDraw
import os
import sys
import math
from config import COLORS

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

def load_car_icons():
    icons = {}
    # 1. Run Icon (Green)
    try:
        car_path = resource_path("car.png")
        if os.path.exists(car_path):
            img = Image.open(car_path).resize((45, 45), Image.Resampling.LANCZOS)
            icons['run'] = ImageTk.PhotoImage(img)
        elif os.path.exists("car.png"):
            img = Image.open("car.png").resize((45, 45), Image.Resampling.LANCZOS)
            icons['run'] = ImageTk.PhotoImage(img)
        else:
            raise FileNotFoundError
    except:
        w, h = 44, 44 
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.rounded_rectangle([8, 5, 36, 39], radius=6, fill=COLORS["success"], outline="white", width=2)
        icons['run'] = ImageTk.PhotoImage(img)

    # 2. Idle Icon (Yellow)
    img_idle = Image.new("RGBA", (30, 30), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img_idle)
    draw.ellipse([2, 2, 28, 28], fill=COLORS["warning"], outline="white", width=2)
    icons['idle'] = ImageTk.PhotoImage(img_idle)

    # 3. Stop Icon (Red)
    img_stop = Image.new("RGBA", (30, 30), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img_stop)
    draw.ellipse([2, 2, 28, 28], fill=COLORS["danger"], outline="white", width=2)
    icons['stop'] = ImageTk.PhotoImage(img_stop)
    
    return icons

def process_gps_data(file_path):
    try:
        try:
            df = pd.read_csv(file_path, encoding='utf-8')
        except UnicodeDecodeError:
            df = pd.read_csv(file_path, encoding='cp874')

        cols = {c.lower().strip(): c for c in df.columns}
        col_lat = cols.get('lat')
        col_lon = cols.get('long') or cols.get('lon') or cols.get('lng')
        col_time = cols.get('r-time') or cols.get('time')

        if not col_lat or not col_lon or not col_time:
            return None, "Missing Columns"

        # Try parsing dates with a more robust approach
        # Use dayfirst=True because data is DD/MM/YYYY
        # Use format='mixed' if available, otherwise fallback
        def parse_date(date_series):
              # Convert to string first to ensure consistency
              date_series = date_series.astype(str)
              
              # 1. Try DD/MM/YYYY format first (very common in TH)
              res = pd.to_datetime(date_series, dayfirst=True, errors='coerce')
              
              # If more than 50% failed, try without dayfirst (could be YYYY-MM-DD)
              if res.isna().sum() > len(res) * 0.5:
                  res = pd.to_datetime(date_series, dayfirst=False, errors='coerce')
              
              return res

        df[col_time] = parse_date(df[col_time])
        
        # Check if we have many NaT. Some systems/files might use different formats per row
        if df[col_time].isna().any():
            mask = df[col_time].isna()
            df.loc[mask, col_time] = pd.to_datetime(df.loc[mask, col_time], errors='coerce')

        # Drop rows where time couldn't be parsed
        df = df.dropna(subset=[col_time])
        df = df.sort_values(col_time)
        
        if df.empty: return None, "Empty Data"
        
        # [CRITICAL FIX] Ensure date_str is calculated for all years
        df['date_str'] = df[col_time].dt.strftime('%Y-%m-%d')
        return df, None

    except Exception as e:
        return None, str(e)

def create_circle_icon_marker():
    size = 12 # ขนาดวงกลม
    img = Image.new("RGBA", (size+4, size+4), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # วาดขอบดำ (ใหญ่กว่านิดนึง)
    draw.ellipse([0, 0, size+3, size+3], fill="black")
    # วาดวงกลมขาว (ทับตรงกลาง)
    draw.ellipse([2, 2, size+1, size+1], fill="white")
    return ImageTk.PhotoImage(img)

# [NEW] สร้างไอคอนใส (สำหรับเอาไว้วาง Text ระยะทางบนเส้น)
def create_transparent_icon():
    img = Image.new("RGBA", (1, 1), (0, 0, 0, 0))
    return ImageTk.PhotoImage(img)

# ฟังก์ชันคำนวณระยะทาง (Haversine)
def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371000  
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2.0) ** 2 + \
        math.cos(phi1) * math.cos(phi2) * \
        math.sin(delta_lambda / 2.0) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

# คำนวณระยะรวม (ใช้ใน main.py)
def calculate_total_distance(coords):
    total_dist = 0
    if len(coords) < 2: return 0
    for i in range(len(coords) - 1):
        total_dist += haversine_distance(coords[i][0], coords[i][1], coords[i+1][0], coords[i+1][1])
    return total_dist