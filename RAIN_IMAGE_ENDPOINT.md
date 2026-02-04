# Rain Image Endpoint Documentation

## Overview

HTTP endpoint that returns the appropriate rain monitoring image from Azure Blob Storage with a SAS token, based on the time elapsed since the last rain event.

## Endpoint

**URL:** `/api/rain-image`  
**Method:** `GET`  
**Authentication:** None (public endpoint)

## Response Format

### Success Response (HTTP 200)

```json
{
  "imageUrl": "https://staticfilestrmnlsa.blob.core.windows.net/images/dias-sin-llover-03-full.png?sv=2021-08-06&se=2026-02-03T20%3A30%3A00Z&sr=b&sp=r&sig=...",
  "value_h": "84.0",
  "value_d": "3.50"
}
```

**Fields:**
- `imageUrl` (string): Full URL to the image with SAS token (valid for 1 hour)
- `value_h` (string): Hours without rain (formatted to 1 decimal place)
- `value_d` (string): Days without rain (formatted to 2 decimal places)

### Error Response (HTTP 500)

```json
{
  "error": "Error description",
  "imageUrl": null,
  "value_h": null,
  "value_d": null
}
```

**Fields:**
- `error` (string): Error message describing what went wrong
- `imageUrl` (null): No image URL available
- `value_h` (null): Time calculation failed
- `value_d` (null): Time calculation failed

## Image Selection Logic

The endpoint selects one of 11 images (00-10) based on the time elapsed since the last rain:

| Image Number | Time Range | Description |
|-------------|------------|-------------|
| `00` | < 24 hours | Less than 1 day |
| `01` | 24 - 48 hours | 1-2 days |
| `02` | 48 - 72 hours | 2-3 days |
| `03` | 72 - 96 hours | 3-4 days |
| `04` | 96 - 120 hours | 4-5 days |
| `05` | 120 - 144 hours | 5-6 days |
| `06` | 144 - 168 hours | 6-7 days |
| `07` | 168 - 192 hours | 7-8 days |
| `08` | 192 - 216 hours | 8-9 days |
| `09` | 216 - 240 hours | 9-10 days |
| `10` | >= 240 hours | 10+ days |

## Image URLs

All images are stored in Azure Blob Storage:

**Base URL:** `https://staticfilestrmnlsa.blob.core.windows.net/images/`

**Image names:** `dias-sin-llover-{00-10}-full.png`

Examples:
- `https://staticfilestrmnlsa.blob.core.windows.net/images/dias-sin-llover-00-full.png`
- `https://staticfilestrmnlsa.blob.core.windows.net/images/dias-sin-llover-05-full.png`
- `https://staticfilestrmnlsa.blob.core.windows.net/images/dias-sin-llover-10-full.png`

## SAS Token Details

**Token Type:** Blob SAS (Shared Access Signature)  
**Validity:** 1 hour from generation  
**Permissions:** Read-only (`sp=r`)  
**Service Version:** Latest Azure Storage API version

The SAS token is appended to the URL as query parameters:
```
?sv=2021-08-06&se=2026-02-03T20%3A30%3A00Z&sr=b&sp=r&sig=...
```

**Parameters:**
- `sv`: Service version
- `se`: Signature expiry time (UTC)
- `sr`: Signed resource (blob)
- `sp`: Signed permissions (read)
- `sig`: Cryptographic signature

## Configuration

### Required Environment Variables

**`AZURE_STORAGE_ACCOUNT_KEY`** (required)
- Storage account access key for SAS token generation
- Must have permissions to generate SAS tokens for the blob container
- Keep this secret and never commit to source control

**Example:**
```bash
AZURE_STORAGE_ACCOUNT_KEY="your_storage_account_key_here=="
```

### Azure Function Configuration

Add to `local.settings.json` (local development):
```json
{
  "Values": {
    "AZURE_STORAGE_ACCOUNT_KEY": "your_key_here",
    "AzureWebJobsStorage": "your_storage_connection_string"
  }
}
```

Add to Azure Function App Settings (production):
```bash
az functionapp config appsettings set \
  --name <function-app-name> \
  --resource-group <resource-group> \
  --settings "AZURE_STORAGE_ACCOUNT_KEY=your_key_here"
```

## Usage Examples

### cURL

```bash
curl https://your-function-app.azurewebsites.net/api/rain-image
```

### JavaScript (fetch)

```javascript
fetch('https://your-function-app.azurewebsites.net/api/rain-image')
  .then(response => response.json())
  .then(data => {
    console.log('Hours without rain:', data.value_h);
    console.log('Days without rain:', data.value_d);
    
    // Display image
    const img = document.createElement('img');
    img.src = data.imageUrl;
    document.body.appendChild(img);
  });
```

### Python

```python
import requests

response = requests.get('https://your-function-app.azurewebsites.net/api/rain-image')
data = response.json()

print(f"Hours: {data['value_h']}")
print(f"Days: {data['value_d']}")
print(f"Image: {data['imageUrl']}")
```

### TRMNL Integration

Call this endpoint from TRMNL to dynamically display rain status:

```liquid
{% assign rain_data = "https://your-function-app.azurewebsites.net/api/rain-image" | fetch_json %}

<div class="rain-status">
  <img src="{{ rain_data.imageUrl }}" alt="Days without rain" />
  <p>{{ rain_data.value_d }} días sin lluvia</p>
  <p>{{ rain_data.value_h }} horas</p>
</div>
```

## How It Works

1. **Request arrives** at `/api/rain-image`
2. **Calculate time** since last rain by:
   - Retrieving stored last rain date from Azure Table Storage
   - Calculating difference from current time (Europe/Madrid timezone)
3. **Determine image number** (00-10) based on hours elapsed
4. **Generate SAS token** for the selected image blob
5. **Return JSON** with image URL (including SAS token) and time values

## Error Scenarios

### No Storage Key Configured

**Error:** `AZURE_STORAGE_ACCOUNT_KEY no está configurada`

**Solution:** Set the `AZURE_STORAGE_ACCOUNT_KEY` environment variable

### Cannot Calculate Rain Time

**Error:** `No se pudo calcular el tiempo sin lluvia`

**Causes:**
- Azure Table Storage unavailable
- No rain data in storage (first run)
- Connection issues

**Solution:** Ensure rain monitoring function (`timer_trigger_rain_check`) has run at least once

### Cannot Generate SAS Token

**Error:** `No se pudo generar la URL con SAS token`

**Causes:**
- Invalid storage account key
- Incorrect blob account/container configuration
- Network issues

**Solution:** Verify storage account credentials and blob storage access

## Performance & Costs

### Performance
- **Response time:** < 500ms (typical)
- **SAS generation:** < 50ms
- **Table Storage read:** < 100ms

### Costs

**Azure Blob Storage (SAS tokens):**
- SAS token generation is free
- Only charged when image is accessed via the URL
- Bandwidth: ~100-500 KB per image
- Cost: ~$0.01 per 10,000 image views

**Azure Table Storage:**
- 1 read operation per request
- Cost: ~$0.01 per 100,000 operations

**Azure Functions:**
- Called every 15 minutes = ~2,880 requests/month
- Well within free tier (1M requests/month)

**Total estimated cost:** < $1/month (assuming moderate usage)

## Caching Considerations

Since the endpoint is designed to be called every 15 minutes and the SAS token is valid for 1 hour, you can implement caching:

### Client-Side Caching

```javascript
// Cache for 15 minutes
const CACHE_DURATION = 15 * 60 * 1000; // 15 minutes in ms
let cachedData = null;
let cacheTimestamp = 0;

async function getRainImage() {
  const now = Date.now();
  
  if (cachedData && (now - cacheTimestamp) < CACHE_DURATION) {
    return cachedData;
  }
  
  const response = await fetch('/api/rain-image');
  cachedData = await response.json();
  cacheTimestamp = now;
  
  return cachedData;
}
```

### CDN Caching

If using Azure CDN or another CDN:
- Set `Cache-Control: max-age=900` (15 minutes)
- Reduces function invocations
- Improves response time

## Security Considerations

### SAS Token Security

✅ **Good practices:**
- SAS tokens are time-limited (1 hour)
- Read-only permissions
- Specific to one blob at a time
- Automatically expire

⚠️ **Important notes:**
- Anyone with the URL can access the image during the validity period
- Don't cache SAS URLs longer than their expiry
- Regenerate tokens on each request

### Storage Account Key

🔒 **Critical:**
- Never commit `AZURE_STORAGE_ACCOUNT_KEY` to source control
- Store in Azure Key Vault for production
- Rotate keys periodically
- Use Managed Identity if possible (future improvement)

### Endpoint Security

- Currently public (no authentication)
- Consider adding API key if abuse is a concern
- Rate limiting handled by Azure Functions automatically

## Monitoring & Logging

The endpoint logs the following information:

```
INFO: HTTP trigger: rain-image endpoint
INFO: Imagen seleccionada: dias-sin-llover-03-full.png (días: 3.50, horas: 84.0)
```

Error logs include:
```
ERROR: AZURE_STORAGE_ACCOUNT_KEY no está configurada
ERROR: Error al generar SAS token: [error details]
ERROR: Error en rain-image endpoint: [error details]
```

View logs in Azure:
```bash
func azure functionapp logstream <function-app-name>
```

Or in Azure Portal:
1. Navigate to Function App
2. Functions → rain-image → Monitor
3. View Invocations and Logs

## Testing

Run the test suite:

```bash
python test_rain_image_endpoint.py
```

Tests cover:
- Image number selection for all time ranges
- Boundary conditions (23.99h vs 24.0h)
- SAS URL generation (mocked)
- Endpoint success scenarios
- Error handling (calculation failures, SAS failures)

**Expected output:**
```
Ran 12 tests in 0.5s
OK
```

## Future Improvements

1. **Managed Identity:** Use Azure Managed Identity instead of storage key
2. **Image Caching:** Cache blob URLs server-side for better performance
3. **Custom expiry:** Allow SAS validity to be configured via query parameter
4. **Image variants:** Support different image sizes (thumbnail, full, etc.)
5. **Metadata:** Include additional weather data in response
6. **Compression:** Return compressed image URLs when supported

## Troubleshooting

### "imageUrl is null"

**Check:**
1. Storage account key is set correctly
2. Blob container name is correct (`images`)
3. Blob account name is correct (`staticfilestrmnlsa`)
4. Images exist in the blob storage

### "value_h and value_d are null"

**Check:**
1. Rain monitoring function has run at least once
2. Azure Table Storage is accessible
3. `AzureWebJobsStorage` connection string is configured

### SAS token expired

**Cause:** Token is only valid for 1 hour

**Solution:** Request a new URL from the endpoint

### Image not loading

**Check:**
1. SAS token hasn't expired
2. Image exists in blob storage
3. CORS settings if accessing from browser

## Support

For issues or questions:
1. Check logs in Azure Portal
2. Verify all environment variables are set
3. Test with the included test suite
4. Review error messages in the JSON response
