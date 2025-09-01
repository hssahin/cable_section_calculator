from flask import Flask, render_template, request, jsonify
import math
import time

app = Flask(__name__)

# IEC 60364 ve TSE akım taşıma kapasiteleri (bakır iletken, kablo tipi ve kesite göre)
CABLE_CAPACITY = {
    "NYY": {1.5:19,2.5:26,4:34,6:44,10:61,16:82,25:108,35:134,50:166,70:207,95:247,120:284,150:325,185:366,240:428},
    "NYY-J": {1.5:18,2.5:24,4:32,6:41,10:56,16:76,25:101,35:125,50:156,70:195,95:232,120:267,150:306,185:345,240:405},
    "N2XH": {1.5:20,2.5:27,4:36,6:46,10:64,16:85,25:111,35:138,50:170,70:212,95:255,120:296,150:340,185:385,240:450},
    "NHXMH": {1.5:16,2.5:21,4:28,6:36,10:50,16:68,25:90,35:110,50:135,70:170,95:205,120:235,150:270,185:305,240:360}
}

# Bakır iletken için özdirenç (Ω·mm²/m)
COPPER_RESISTIVITY = 0.0178

def calculate_current(power_kw, phases, voltage, pf=0.9):
    """Güce göre akımı hesapla"""
    power_w = power_kw * 1000
    if phases == 3:
        current = power_w / (math.sqrt(3) * voltage * pf)
    else:
        current = power_w / (voltage * pf)
    return round(current, 2)

def calculate_min_section(current, distance, voltage, voltage_drop_percent, phases=3):
    """Gerilim düşümüne göre minimum kesiti hesapla"""
    # İzin verilen maksimum gerilim düşümü (V)
    max_voltage_drop = voltage * voltage_drop_percent / 100
    
    # Formül: S = (√3 * I * L * ρ * cosφ) / ΔV (3 faz için)
    if phases == 3:
        min_section = (math.sqrt(3) * current * distance * COPPER_RESISTIVITY * 0.9) / max_voltage_drop
    else:
        # 1 faz için formül: S = (2 * I * L * ρ * cosφ) / ΔV
        min_section = (2 * current * distance * COPPER_RESISTIVITY * 0.9) / max_voltage_drop
    
    return round(min_section, 2)

def suggest_cable(current, min_section, cable_type):
    """Akım ve minimum kesite göre uygun kablo kesitini öner"""
    if cable_type not in CABLE_CAPACITY:
        return None
        
    # Önce akım taşıma kapasitesine göre uygun kesitleri bul
    suitable_sizes = []
    for size, capacity in sorted(CABLE_CAPACITY[cable_type].items()):
        if current <= capacity and size >= min_section:
            suitable_sizes.append(size)
    
    # Uygun kesitlerden en küçüğünü seç
    if suitable_sizes:
        return min(suitable_sizes)
    
    return None

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/calculate", methods=["POST"])
def calculate():
    try:
        # Yapay gecikme ekle (3 saniye)
        time.sleep(1)
        
        # JSON verilerini al
        data = request.get_json()
        
        # Gerekli alanları kontrol et
        if not data or not all(key in data for key in ['power_kw', 'phases', 'voltage', 'voltage_drop', 'distance', 'cable_type']):
            return jsonify({"error": "Eksik veri gönderildi!"}), 400
        
        # Değerleri al
        power_kw = float(data['power_kw'])
        phases = int(data['phases'])
        voltage = float(data['voltage'])
        voltage_drop = float(data['voltage_drop'])
        distance = float(data['distance'])
        cable_type = data['cable_type']
        
        # Validasyon
        if power_kw <= 0 or voltage <= 0 or voltage_drop <= 0 or distance <= 0:
            return jsonify({"error": "Pozitif değerler girmelisiniz!"}), 400
            
        if cable_type not in CABLE_CAPACITY:
            return jsonify({"error": "Geçersiz kablo tipi!"}), 400
        
        # Hesaplamalar
        current = calculate_current(power_kw, phases, voltage)
        min_section = calculate_min_section(current, distance, voltage, voltage_drop, phases)
        cable_size = suggest_cable(current, min_section, cable_type)
        
        # Sonuçları döndür
        result = {
            "current": current,
            "min_section": f"{min_section} mm²",
            "cable_size": f"{cable_size} mm²" if cable_size else "Tablo dışı (daha büyük kesit gerekli)"
        }
        
        return jsonify(result)
        
    except ValueError:
        return jsonify({"error": "Geçersiz sayı formatı!"}), 400
    except Exception as e:
        return jsonify({"error": f"Hesaplama hatası: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5080, debug=True)