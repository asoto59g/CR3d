import sqlite3
import math
import os
import json
import struct
from PIL import Image
import numpy as np

# Load DEM for sampling
print("Loading DEM for sampling...")
tif_img = Image.open('rasters/CRdemrecort.tif')
tif_data = np.array(tif_img).astype(np.float32)
TIF_W, TIF_H = 12324, 11452
TIF_XMIN, TIF_YMAX = 283609.5856, 1241130.5905
TIF_RES = 30.4516

# CRTM05 (EPSG:5367) Parameters
A = 6378137.0
B = 6356752.3142
E2 = (A**2 - B**2) / A**2
K0 = 0.9999
L0 = math.radians(-84)
E0 = 500000.0
N0 = 0.0

def deg2rad(d): return d * math.pi / 180
def rad2deg(r): return r * 180 / math.pi

def wgs84_to_crtm05(lat_deg, lon_deg):
    lat = deg2rad(lat_deg); lon = deg2rad(lon_deg)
    n = (A - B) / (A + B)
    alpha = (A + B) / 2 * (1 + (n**2)/4 + (n**4)/64)
    beta = 3*n/2 - 27*(n**3)/32
    gamma = 21*(n**2)/16 - 55*(n**4)/32
    delta = 151*(n**3)/96
    epsilon = 1097*(n**4)/512
    m = alpha * (lat - beta*math.sin(2*lat) + gamma*math.sin(4*lat) - delta*math.sin(6*lat) + epsilon*math.sin(8*lat))
    nu = A / math.sqrt(1 - E2 * math.sin(lat)**2)
    p = lon - L0
    s1 = math.sin(lat); c1 = math.cos(lat)
    e = E0 + K0 * p * nu * c1 * (1 + (p**2/6)*c1**2*(1 - math.tan(lat)**2))
    n_coord = N0 + K0 * m + K0 * (p**2/2)*nu*s1*c1
    return e, n_coord

def crtm05_to_wgs84_approx(e, n):
    lon = math.degrees(L0 + (e - E0) / (K0 * A))
    lat = math.degrees(n / (K0 * A))
    return lat, lon

def mercator_to_wgs84(x, y):
    lon = (x / 6378137.0) * 180 / math.pi
    lat = (2 * math.atan(math.exp(y / 6378137.0)) - math.pi / 2) * 180 / math.pi
    return lat, lon

def get_elevation(e, n):
    tx = int((e - TIF_XMIN) / TIF_RES)
    ty = int((TIF_YMAX - n) / TIF_RES)
    if 0 <= tx < TIF_W and 0 <= ty < TIF_H:
        return float(tif_data[ty, tx])
    return 0.0

def densify_and_elevate(pts_crtm, max_dist=50.0):
    new_pts = []
    for i in range(len(pts_crtm) - 1):
        p1 = pts_crtm[i]
        p2 = pts_crtm[i+1]
        dist = math.sqrt((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2)
        
        # Add start point with precise native CRTM05 (E,N)
        new_pts.append([p1[0], p1[1], get_elevation(p1[0], p1[1])])
        
        if dist > max_dist:
            num_steps = int(math.ceil(dist / max_dist))
            for step in range(1, num_steps):
                f = step / num_steps
                ex = p1[0] + (p2[0] - p1[0]) * f
                ey = p1[1] + (p2[1] - p1[1]) * f
                new_pts.append([ex, ey, get_elevation(ex, ey)])
    
    # Add final point
    pf = pts_crtm[-1]
    new_pts.append([pf[0], pf[1], get_elevation(pf[0], pf[1])])
    return new_pts

def parse_gpkg_geom_3d(blob):
    if not blob: return None
    flags = blob[3]
    envelope_type = (flags >> 1) & 0x07
    header_size = 8 + [0, 32, 48, 48, 64][envelope_type]
    wkb = blob[header_size:]
    
    byte_order = '<' if wkb[0] == 1 else '>'
    geom_type = struct.unpack(byte_order + 'I', wkb[1:5])[0]
    
    if geom_type == 1: # POINT
        e, n = struct.unpack(byte_order + 'dd', wkb[5:21])
        return {"type": "Point", "coordinates": [e, n, get_elevation(e, n)]}
    
    elif geom_type == 2: # LINESTRING
        num_pts = struct.unpack(byte_order + 'I', wkb[5:9])[0]
        pts_crtm = [struct.unpack(byte_order + 'dd', wkb[9 + i*16 : 9 + (i+1)*16]) for i in range(num_pts)]
        return {"type": "LineString", "coordinates": densify_and_elevate(pts_crtm)}
    
    elif geom_type == 5: # MULTILINESTRING
        num_lines = struct.unpack(byte_order + 'I', wkb[5:9])[0]
        multi_pts = []
        offset = 9
        for _ in range(num_lines):
            sub_byte_order = '<' if wkb[offset] == 1 else '>'
            sub_num_pts = struct.unpack(sub_byte_order + 'I', wkb[offset+5 : offset+9])[0]
            pts_crtm = [struct.unpack(sub_byte_order + 'dd', wkb[offset+9 + i*16 : offset+9 + (i+1)*16]) for i in range(sub_num_pts)]
            multi_pts.append(densify_and_elevate(pts_crtm))
            offset += 9 + sub_num_pts * 16
        return {"type": "MultiLineString", "coordinates": multi_pts}
    return None

def generate_tiles(layer_name, folder_name):
    print(f"Tiling {layer_name} (3D Draping)...")
    conn = sqlite3.connect('packaged_data.gpkg')
    c = conn.cursor()
    c.execute(f"SELECT column_name FROM gpkg_geometry_columns WHERE table_name='{layer_name}'")
    geom_col = c.fetchone()[0]
    
    MERC_LIMIT = 20037508.342789244
    for z in range(10, 16):
        print(f"  Zoom {z}...")
        sx, ex = int(((-86.5 + 180)/360)*2**z), int(((-82.4 + 180)/360)*2**z)
        sy, ey = int(((1 - math.log(math.tan(math.radians(11.8)) + 1/math.cos(math.radians(11.8)))/math.pi)/2)*2**z), \
                 int(((1 - math.log(math.tan(math.radians(8.0)) + 1/math.cos(math.radians(8.0)))/math.pi)/2)*2**z)
        
        for tx in range(sx, ex + 1):
            for ty in range(sy, ey + 1):
                tile_size = (MERC_LIMIT * 2) / (2**z)
                xmin_m = -MERC_LIMIT + tx * tile_size
                xmax_m = xmin_m + tile_size
                ymax_m = MERC_LIMIT - ty * tile_size
                ymin_m = ymax_m - tile_size
                
                pts = [mercator_to_wgs84(xmin_m, ymin_m), mercator_to_wgs84(xmax_m, ymax_m)]
                c_pts = [wgs84_to_crtm05(p[0], p[1]) for p in pts]
                min_e, max_e = min(p[0] for p in c_pts), max(p[0] for p in c_pts)
                min_n, max_n = min(p[1] for p in c_pts), max(p[1] for p in c_pts)
                
                query_with_name = f"SELECT {geom_col}, NOMBRE FROM {layer_name} WHERE fid IN (SELECT id FROM rtree_{layer_name}_{geom_col} WHERE minx < ? AND maxx > ? AND miny < ? AND maxy > ?)"
                try:
                    c.execute(query_with_name, (max_e, min_e, max_n, min_n))
                    rows = c.fetchall()
                except sqlite3.OperationalError:
                    query_without_name = f"SELECT {geom_col} FROM {layer_name} WHERE fid IN (SELECT id FROM rtree_{layer_name}_{geom_col} WHERE minx < ? AND maxx > ? AND miny < ? AND maxy > ?)"
                    c.execute(query_without_name, (max_e, min_e, max_n, min_n))
                    rows = c.fetchall()
                    
                if rows:
                    features = []
                    for r in rows:
                        g = parse_gpkg_geom_3d(r[0])
                        if g:
                            props = {"nombre": r[1] if len(r) > 1 else "Desconocido"}
                            if g['type'] == 'Point': props["altitud"] = g['coordinates'][2]
                            features.append({"type": "Feature", "geometry": g, "properties": props})
                    
                    if features:
                        fc = {"type": "FeatureCollection", "features": features}
                        os.makedirs(f'tiles_vector/{folder_name}/{z}/{tx}', exist_ok=True)
                        with open(f'tiles_vector/{folder_name}/{z}/{tx}/{ty}.json', 'w') as f:
                            json.dump(fc, f)

if __name__ == "__main__":
    generate_tiles('Poblados2014crtm05_poblados2014crtm05_shp', 'poblados')
    generate_tiles('Redcamino2014crtm05_redcaminos2014crtm05_shp', 'carreteras')
    generate_tiles('Rios150000crtm05_rios150000crtm05_shp', 'rios')
