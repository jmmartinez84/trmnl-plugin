# Rain Monitoring Feature

## Overview

This Azure Function monitors rainfall data from AEMET (Agencia Estatal de Meteorología) for Vigo Airport (Station 1495) and tracks the time elapsed since the last rain event.

## How It Works

1. **Data Collection**: Every 15 minutes, downloads the latest 24-hour weather observations CSV from AEMET
2. **Rain Detection**: Parses precipitation data to find the most recent rain event
3. **Persistence**: Stores the last rain date in Azure Table Storage to maintain history beyond the 24-hour CSV window
4. **Calculation**: Computes days and hours without rain using proper Spanish timezone handling

## Implementation Details

### Timer Trigger

- **Schedule**: `0 */15 * * * *` (every 15 minutes)
- **Function Name**: `timer_trigger_rain_check`

### Data Source

- **URL**: AEMET Vigo Airport hourly observations
- **Format**: CSV with 3 metadata rows + header + data rows
- **Encoding**: latin-1
- **Update Frequency**: AEMET updates approximately every hour

### CSV Structure

```
Line 0: "Vigo Aeropuerto"
Line 1: Actualizado: [timestamp]
Line 2: (blank)
Line 3: Header row with column names
Line 4+: Data rows
```

### Key Columns

- **Fecha y hora oficial**: Timestamp in `DD/MM/YYYY HH:MM` format
- **Precipitación (mm)**: Precipitation in millimeters

### Persistence (Azure Table Storage)

- **Table**: `WeatherStatus`
- **Partition Key**: `RainStatus`
- **Row Key**: `LastRainDate`
- **Stored Value**: ISO 8601 timestamp of last detected rain

### Logic Flow

1. Download and parse CSV
2. Find all rows with precipitation > 0 mm
3. Get the most recent rain timestamp from CSV
4. Retrieve stored last rain date from Table Storage
5. If CSV has newer rain, update Table Storage
6. Calculate elapsed time using stored/CSV date (whichever is more recent)
7. Log results

## Configuration

### Required Environment Variables

- `AzureWebJobsStorage`: Azure Storage connection string (used by Function App)
  - Also used for Table Storage persistence

### Optional Configuration

You can modify the constants in `function_app.py`:

```python
CSV_URL = "https://www.aemet.es/es/eltiempo/observacion/ultimosdatos_1495_datos-horarios.csv?k=gal&l=1495&datos=det&w=0&f=precipitacion&x=h24"
TABLE_NAME = "WeatherStatus"
DEFAULT_LAST_RAIN_DATE = "2000-01-01 00:00:00"
```

To monitor a different station, change the `1495` parameter in the URL to the desired station code.

## Dependencies

Added to `requirements.txt`:

- `pandas`: CSV parsing and data manipulation
- `azure-data-tables`: Azure Table Storage client

## Testing

Two test files are included:

### `test_rain_monitoring.py`
Basic unit test for CSV parsing logic

```bash
python test_rain_monitoring.py
```

### `test_rain_integration.py`
Comprehensive integration tests covering:
- Rain detection in CSV with precipitation
- No rain detection (empty result)
- Days/hours calculation
- Persistence update logic
- Timezone handling

```bash
python test_rain_integration.py
```

## Logs

The function logs the following information:

```
Iniciando comprobación de lluvia...
🌧️ Lluvia detectada en CSV: 2026-02-03 14:00:00
Fecha de lluvia actualizada: 2026-02-03 14:00:00
Última lluvia registrada: 2026-02-03 14:00:00+01:00
Lleva sin llover: 0.25 días (6.0 horas)
```

In case of errors:
```
Error en comprobación de lluvia: [error details]
```

## Example Usage Scenario

1. **Initial run** (no previous data):
   - CSV shows rain at 14:00
   - No data in Table Storage
   - Function stores 14:00 in Table Storage
   - Calculates time since 14:00

2. **Subsequent runs** (no new rain):
   - CSV shows no rain (or only old rain from 24h window)
   - Table Storage has rain from 2 days ago
   - Function uses stored date (more recent than CSV)
   - Calculates 2 days without rain

3. **New rain detected**:
   - CSV shows rain at 10:00 today
   - Table Storage has rain from 2 days ago
   - Function updates Table Storage with new date
   - Calculates time since 10:00 today

## Timezone Handling

All timestamps are handled with proper timezone awareness:
- AEMET data is in Spanish local time (Europe/Madrid)
- Calculations account for daylight saving time
- Stored timestamps use ISO 8601 format with timezone info

## Error Handling

The function includes robust error handling for:
- Network failures when downloading CSV
- CSV parsing errors
- Azure Table Storage connection issues
- Missing or malformed data
- Timezone conversion issues

All errors are logged but don't crash the function.

## Cost Considerations

### Azure Functions
- Runs 96 times/day (every 15 minutes)
- Very lightweight processing
- Well within free tier limits

### Azure Table Storage
- Single entity (1 row)
- Minimal storage cost (< $0.01/month)
- Low transaction cost (96 upserts/day)

### Network
- CSV download: ~2 KB every 15 minutes
- ~276 KB/day in transfers
- Negligible bandwidth cost

## Security

- ✅ Uses Azure Managed Identity via connection string
- ✅ No hardcoded credentials
- ✅ HTTPS-only communication
- ✅ Dependencies scanned for vulnerabilities
- ✅ No sensitive data in logs

## Future Enhancements

Possible improvements:
- Send notifications when X days without rain threshold is reached
- Export data to TRMNL display
- Chart historical rain patterns
- Multi-station monitoring
- Integration with other weather services

## Troubleshooting

### "AzureWebJobsStorage no está configurada"
Ensure the Azure Function has the storage connection string configured.

### "No se encontró fecha de lluvia previa"
Normal on first run. The function will use default date and start tracking from the first rain detected.

### CSV parsing errors
AEMET occasionally changes CSV format. Check the CSV structure if parsing fails consistently.

### Table Storage connection errors
Verify Azure Storage account is accessible and connection string is valid.
