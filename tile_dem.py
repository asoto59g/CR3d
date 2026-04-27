import math
import os
import numpy as np
from PIL import Image

# CRTM05 (EPSG:5367) Parameters
A = 6378137.0
F = 1 / 298.257223563
B = A * (1 - F)
E2 = (A**2 - B**2) / A**2
K0 = 0.9999
L0 = math.radians(-84)
E0 = 500000.0
N0 = 0.0

def mercator_to_wgs84(x, y):
    lon = (x / 6378137.0) * 180 / math.pi
    lat = (2 * math.atan(math.exp(y / 6378137.0)) - math.pi / 2) * 180 / math.pi
    return lat, lon

def wgs84_to_crtm05_batch(lat_deg, lon_deg):
    lat = np.radians(lat_deg)
    lon = np.radians(lon_deg)
    n = (A - B) / (A + B)
    alpha = (A + B) / 2 * (1 + (n**2)/4 + (n**4)/64)
    beta = 3*n/2 - 27*(n**3)/32
    gamma = 21*(n**2)/16 - 55*(n**4)/32
    delta = 151*(n**3)/96
    epsilon = 1097*(n**4)/512
    m = alpha * (lat - beta*np.sin(2*lat) + gamma*np.sin(4*lat) - delta*np.sin(6*lat) + epsilon*np.sin(8*lat))
    nu = A / np.sqrt(1 - E2 * np.sin(lat)**2)
    p = lon - L0
    s1 = np.sin(lat)
    c1 = np.cos(lat)
    e = E0 + K0 * p * nu * c1 * (1 + (p**2/6)*c1**2*(1 - np.tan(lat)**2))
    n_coord = N0 + K0 * m + K0 * (p**2/2)*nu*s1*c1
    return e, n_coord

# TIF Metadata
TIF_W, TIF_H = 12324, 11452
TIF_XMIN, TIF_YMAX = 283609.5856, 1241130.5905
TIF_RES = 30.4516

print("Loading TIF into memory...")
tif_img = Image.open('rasters/CRdemrecort.tif')
tif_data = np.array(tif_img).astype(np.float32)

MERC_LIMIT = 20037508.342789244

def generate_tile(z, x, y):
    tile_size = (MERC_LIMIT * 2) / (2**z)
    xmin = -MERC_LIMIT + x * tile_size
    ymax = MERC_LIMIT - y * tile_size
    step = tile_size / 256
    
    # Create grid of mercator coords
    px = np.arange(256)
    py = np.arange(256)
    mx = xmin + px * step
    my = ymax - py * step
    MX, MY = np.meshgrid(mx, my)
    
    # Reproject grid
    LON = (MX / 6378137.0) * 180 / math.pi
    LAT = (2 * np.arctan(np.exp(MY / 6378137.0)) - math.pi / 2) * 180 / math.pi
    
    E, N = wgs84_to_crtm05_batch(LAT, LON)
    
    # Map to TIF pixels
    TX = ((E - TIF_XMIN) / TIF_RES).astype(np.int32)
    TY = ((TIF_YMAX - N) / TIF_RES).astype(np.int32)
    
    # Mask valid pixels
    mask = (TX >= 0) & (TX < TIF_W) & (TY >= 0) & (TY < TIF_H)
    elev = np.zeros((256, 256), dtype=np.float32)
    elev[mask] = tif_data[TY[mask], TX[mask]]
    
    if np.any(elev > 0):
        # Encode Terrain-RGB
        val = ((elev + 10000) * 10).astype(np.int32)
        r = (val >> 16) & 0xFF
        g = (val >> 8) & 0xFF
        b = val & 0xFF
        
        rgb = np.stack([r, g, b], axis=-1).astype(np.uint8)
        out_img = Image.fromarray(rgb)
        os.makedirs(f'tiles/{z}/{x}', exist_ok=True)
        out_img.save(f'tiles/{z}/{x}/{y}.png')
        return True
    return False

# Main loop
for z in range(10, 16): # Up to z15
    print(f"Zoom {z}...")
    # These bounds cover all Costa Rica
    sx, ex = int(((-86.5 + 180)/360)*2**z), int(((-82.4 + 180)/360)*2**z)
    sy, ey = int(((1 - np.log(np.tan(np.radians(11.8)) + 1/np.cos(np.radians(11.8)))/math.pi)/2)*2**z), \
             int(((1 - np.log(np.tan(np.radians(8.0)) + 1/np.cos(np.radians(8.0)))/math.pi)/2)*2**z)
    
    for tx in range(sx, ex + 1):
        for ty in range(sy, ey + 1):
            generate_tile(z, tx, ty)
