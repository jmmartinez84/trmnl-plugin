"""
Integration test for the rain monitoring functionality.
Tests the complete flow including CSV parsing, persistence simulation, and calculation.
"""
import pandas as pd
from io import StringIO
from datetime import datetime
from dateutil import tz

# Sample CSV data with rain
SAMPLE_CSV_WITH_RAIN = """Vigo Aeropuerto
Actualizado: martes, 03 febrero 2026 a las 18:22 hora oficial

"Fecha y hora oficial","Temperatura (ÂºC)","Velocidad del viento (km/h)","DirecciÃ³n del viento","Racha (km/h)","DirecciÃ³n de racha","PrecipitaciÃ³n (mm)","PresiÃ³n (hPa)","Tendencia (hPa)","Humedad (%)"
"03/02/2026 18:00","8.1","13","Sur","26","Sur","0.0","964.9","-2.3","86.0"
"03/02/2026 17:00","9.0","17","Sur","32","Sudoeste","0.0","966.2","-1.3","82.0"
"03/02/2026 16:00","9.8","19","Sudoeste","39","Sudoeste","0.0","966.7","-0.9","69.0"
"03/02/2026 15:00","10.0","17","Sudoeste","32","Sudoeste","0.0","967.2","-0.2","75.0"
"03/02/2026 14:00","9.8","22","Sudoeste","35","Sudoeste","0.1","967.5","0.5","72.0"
"03/02/2026 13:00","9.0","10","Sudoeste","22","Sudoeste","0.2","967.6","1.5","82.0"
"03/02/2026 12:00","8.5","15","Sudoeste","28","Sudoeste","0.5","968.0","2.0","85.0"
"""

# Sample CSV data without rain
SAMPLE_CSV_NO_RAIN = """Vigo Aeropuerto
Actualizado: martes, 03 febrero 2026 a las 18:22 hora oficial

"Fecha y hora oficial","Temperatura (ÂºC)","Velocidad del viento (km/h)","DirecciÃ³n del viento","Racha (km/h)","DirecciÃ³n de racha","PrecipitaciÃ³n (mm)","PresiÃ³n (hPa)","Tendencia (hPa)","Humedad (%)"
"03/02/2026 18:00","8.1","13","Sur","26","Sur","0.0","964.9","-2.3","86.0"
"03/02/2026 17:00","9.0","17","Sur","32","Sudoeste","0.0","966.2","-1.3","82.0"
"03/02/2026 16:00","9.8","19","Sudoeste","39","Sudoeste","0.0","966.7","-0.9","69.0"
"03/02/2026 15:00","10.0","17","Sudoeste","32","Sudoeste","0.0","967.2","-0.2","75.0"
"""

def process_csv_data(csv_data):
    """Process CSV data and return rain information."""
    df = pd.read_csv(StringIO(csv_data), skiprows=3, encoding='latin-1')
    
    # Identify columns
    precip_col = [c for c in df.columns if 'Precip' in c][0]
    date_col = [c for c in df.columns if 'Fecha' in c][0]
    
    # Convert columns
    df[date_col] = pd.to_datetime(df[date_col], format='%d/%m/%Y %H:%M')
    df[precip_col] = pd.to_numeric(df[precip_col], errors='coerce').fillna(0)
    
    # Find rainy hours
    rainy_hours = df[df[precip_col] > 0]
    
    last_rain_csv = None
    if not rainy_hours.empty:
        last_rain_csv = rainy_hours[date_col].max()
    
    return last_rain_csv, df

def test_rain_detection():
    """Test that rain is detected correctly in CSV data."""
    print("Test 1: Rain detection in CSV with precipitation")
    last_rain, df = process_csv_data(SAMPLE_CSV_WITH_RAIN)
    
    if last_rain is not None:
        print(f"  ✓ Rain detected: {last_rain}")
        # Should be the latest rainy hour (14:00 has 0.1mm, 13:00 has 0.2mm, 12:00 has 0.5mm)
        expected = pd.to_datetime("03/02/2026 14:00", format='%d/%m/%Y %H:%M')
        assert last_rain == expected, f"Expected {expected}, got {last_rain}"
        print(f"  ✓ Latest rain is correct: {last_rain}")
    else:
        raise AssertionError("Expected to find rain but found none")

def test_no_rain_detection():
    """Test behavior when no rain is present."""
    print("\nTest 2: No rain in CSV")
    last_rain, df = process_csv_data(SAMPLE_CSV_NO_RAIN)
    
    if last_rain is None:
        print("  ✓ Correctly detected no rain in CSV")
    else:
        raise AssertionError(f"Expected no rain but found: {last_rain}")

def test_days_calculation():
    """Test calculation of days without rain."""
    print("\nTest 3: Days without rain calculation")
    last_rain = pd.to_datetime("03/02/2026 14:00", format='%d/%m/%Y %H:%M')
    
    # Test scenario: it's now 03/02/2026 20:00 (6 hours later)
    test_now = pd.to_datetime("03/02/2026 20:00", format='%d/%m/%Y %H:%M')
    
    diff = test_now - last_rain
    hours_without_rain = diff.total_seconds() / 3600
    days_without_rain = diff.total_seconds() / (24 * 3600)
    
    print(f"  ✓ Hours since last rain: {hours_without_rain:.1f} hours")
    print(f"  ✓ Days since last rain: {days_without_rain:.2f} days")
    
    assert hours_without_rain == 6.0, f"Expected 6.0 hours, got {hours_without_rain}"
    assert abs(days_without_rain - 0.25) < 0.01, f"Expected 0.25 days, got {days_without_rain}"

def test_persistence_logic():
    """Test the persistence update logic."""
    print("\nTest 4: Persistence update logic")
    
    # Simulate stored date
    last_rain_stored = pd.to_datetime("02/02/2026 10:00", format='%d/%m/%Y %H:%M')
    
    # CSV has newer rain
    last_rain_csv = pd.to_datetime("03/02/2026 14:00", format='%d/%m/%Y %H:%M')
    
    # Logic: if CSV has newer rain, update
    if last_rain_csv is not None and last_rain_csv > last_rain_stored:
        current_last_rain = last_rain_csv
        should_update = True
    else:
        current_last_rain = last_rain_stored
        should_update = False
    
    print(f"  ✓ Stored date: {last_rain_stored}")
    print(f"  ✓ CSV date: {last_rain_csv}")
    print(f"  ✓ Should update: {should_update}")
    print(f"  ✓ Current last rain: {current_last_rain}")
    
    assert should_update, "Should update with newer rain from CSV"
    assert current_last_rain == last_rain_csv, "Should use CSV date"
    
    # Test opposite: stored is newer
    last_rain_stored = pd.to_datetime("04/02/2026 10:00", format='%d/%m/%Y %H:%M')
    last_rain_csv = pd.to_datetime("03/02/2026 14:00", format='%d/%m/%Y %H:%M')
    
    if last_rain_csv is not None and last_rain_csv > last_rain_stored:
        current_last_rain = last_rain_csv
        should_update = True
    else:
        current_last_rain = last_rain_stored
        should_update = False
    
    print(f"\n  Test with older CSV:")
    print(f"  ✓ Stored date: {last_rain_stored}")
    print(f"  ✓ CSV date: {last_rain_csv}")
    print(f"  ✓ Should update: {should_update}")
    print(f"  ✓ Current last rain: {current_last_rain}")
    
    assert not should_update, "Should NOT update with older rain from CSV"
    assert current_last_rain == last_rain_stored, "Should keep stored date"

def test_timezone_handling():
    """Test timezone handling for Spanish time."""
    print("\nTest 5: Timezone handling")
    
    spanish_tz = tz.gettz('Europe/Madrid')
    now = datetime.now(spanish_tz)
    
    print(f"  ✓ Spanish timezone: {spanish_tz}")
    print(f"  ✓ Current time (Spain): {now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    
    # Test adding timezone to naive datetime
    last_rain_naive = pd.to_datetime("03/02/2026 14:00", format='%d/%m/%Y %H:%M')
    if last_rain_naive.tzinfo is None:
        last_rain_aware = last_rain_naive.replace(tzinfo=spanish_tz)
        print(f"  ✓ Converted naive to aware: {last_rain_aware}")
    
    assert last_rain_aware.tzinfo is not None, "Should have timezone info"

def run_all_tests():
    """Run all integration tests."""
    print("="*60)
    print("Running Rain Monitoring Integration Tests")
    print("="*60)
    
    try:
        test_rain_detection()
        test_no_rain_detection()
        test_days_calculation()
        test_persistence_logic()
        test_timezone_handling()
        
        print("\n" + "="*60)
        print("✓ All integration tests passed!")
        print("="*60)
    except Exception as e:
        print("\n" + "="*60)
        print(f"✗ Test failed: {str(e)}")
        print("="*60)
        raise

if __name__ == "__main__":
    run_all_tests()
