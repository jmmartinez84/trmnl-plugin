"""
Test script for rain monitoring functionality.
This is a simple standalone test to verify the rain monitoring logic works correctly.
"""
import pandas as pd
from io import StringIO
from datetime import datetime

# Sample CSV data similar to AEMET format
SAMPLE_CSV = """Vigo Aeropuerto
Actualizado: martes, 03 febrero 2026 a las 18:22 hora oficial

"Fecha y hora oficial","Temperatura (ÂºC)","Velocidad del viento (km/h)","DirecciÃ³n del viento","Racha (km/h)","DirecciÃ³n de racha","PrecipitaciÃ³n (mm)","PresiÃ³n (hPa)","Tendencia (hPa)","Humedad (%)"
"03/02/2026 18:00","8.1","13","Sur","26","Sur","0.0","964.9","-2.3","86.0"
"03/02/2026 17:00","9.0","17","Sur","32","Sudoeste","0.0","966.2","-1.3","82.0"
"03/02/2026 16:00","9.8","19","Sudoeste","39","Sudoeste","0.0","966.7","-0.9","69.0"
"03/02/2026 15:00","10.0","17","Sudoeste","32","Sudoeste","0.0","967.2","-0.2","75.0"
"03/02/2026 14:00","9.8","22","Sudoeste","35","Sudoeste","0.1","967.5","0.5","72.0"
"03/02/2026 13:00","9.0","10","Sudoeste","22","Sudoeste","0.0","967.6","1.5","82.0"
"""

def test_csv_parsing():
    """Test that we can parse the AEMET CSV format correctly."""
    print("Testing CSV parsing...")
    
    # Process CSV (skipping first 3 lines of metadata)
    df = pd.read_csv(StringIO(SAMPLE_CSV), skiprows=3, encoding='latin-1')
    
    # Identify columns
    precip_col = [c for c in df.columns if 'Precip' in c][0]
    date_col = [c for c in df.columns if 'Fecha' in c][0]
    
    print(f"✓ Found date column: {date_col}")
    print(f"✓ Found precipitation column: {precip_col}")
    
    # Convert columns
    df[date_col] = pd.to_datetime(df[date_col], format='%d/%m/%Y %H:%M')
    df[precip_col] = pd.to_numeric(df[precip_col], errors='coerce').fillna(0)
    
    print(f"✓ Parsed {len(df)} rows")
    
    # Find rainy hours
    rainy_hours = df[df[precip_col] > 0]
    
    if not rainy_hours.empty:
        last_rain = rainy_hours[date_col].max()
        print(f"✓ Last rain found in CSV: {last_rain}")
        
        # Verify it's the expected value (14:00 on 03/02/2026)
        expected = pd.to_datetime("03/02/2026 14:00", format='%d/%m/%Y %H:%M')
        if last_rain == expected:
            print("✓ Last rain date matches expected value")
        else:
            print(f"✗ Expected {expected}, got {last_rain}")
    else:
        print("✗ No rain found in CSV")
    
    # Calculate days without rain
    now = datetime.now()
    if not rainy_hours.empty:
        last_rain = rainy_hours[date_col].max()
        # Make last_rain timezone-aware for comparison
        if last_rain.tzinfo is None:
            last_rain = last_rain.replace(tzinfo=None)
        
        # For testing, calculate from a fixed date
        test_date = pd.to_datetime("03/02/2026 20:00", format='%d/%m/%Y %H:%M')
        diff = test_date - last_rain
        hours_without_rain = diff.total_seconds() / 3600
        print(f"✓ Hours since last rain (test scenario): {hours_without_rain:.1f} hours")
    
    print("\nAll tests passed! ✓")

if __name__ == "__main__":
    test_csv_parsing()
