# Device Registration Process Guide

## Overview
This document explains the complete device registration flow for OneScan devices, including API endpoints, data models, configuration files, and the polling mechanism.

---

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Configuration Files](#configuration-files)
3. [Registration Flow Overview](#registration-flow-overview)
4. [Step-by-Step Process](#step-by-step-process)
5. [Heartbeat Monitoring](#heartbeat-monitoring)
6. [Device Deletion Handling](#device-deletion-handling)
7. [API Endpoints](#api-endpoints)
8. [Data Models](#data-models)
9. [File Structure](#file-structure)
10. [Error Handling](#error-handling)

---

## Prerequisites

### Required Configuration
Before starting registration, ensure the following file exists:

**File**: `/home/unisight/Config/baseUrl.json`

```json
{
  "BASE_URL": "https://your-api-base-url.com",
  "BASE_URL_POS": "https://your-pos-api-url.com",
  "BASE_URL_INVENTORY": "https://your-inventory-api-url.com",
  "ONESCAN_DEVICE_TYPE": "11"
}
```

### Device Types
- `11` = OneScan Document Scanner (default)
- `3` = Other device type (adjust as needed)

---

## Configuration Files

### 1. baseUrl.json
**Location**: `/home/unisight/Config/baseUrl.json`
**Purpose**: Stores API base URLs and device type configuration
**Created**: Manually before registration

**Structure**:
```json
{
  "BASE_URL": "https://api.example.com",
  "BASE_URL_POS": "https://pos-api.example.com",
  "BASE_URL_INVENTORY": "https://inventory-api.example.com",
  "ONESCAN_DEVICE_TYPE": "11"
}
```

### 2. registration.json
**Location**: `/home/unisight/Config/registration.json`
**Purpose**: Stores device registration state and credentials
**Created**: Automatically during registration process

**Structure**:
```json
{
  "AssignedGuid": "123e4567-e89b-12d3-a456-426614174000",
  "AccessToken": "Bearer eyJhbGciOiJIUzI1NiIs...",
  "DeviceStatus": "Activated",
  "ApiKey": "your-api-key-here",
  "BranchId": 2,
  "Branch": "Qualmart San Francisco"
}
```

### 3. branchInfo.json
**Location**: `/home/unisight/Config/branchInfo.json`
**Purpose**: Stores detailed branch information after activation
**Created**: Automatically after device activation

**Structure**:
```json
{
  "id": 2,
  "companyId": 1,
  "company": "Qualmart",
  "name": "Qualmart San Francisco",
  "address1": "123 Main St",
  "city": "San Francisco",
  "state": "CA",
  "zipCode": "94102",
  "phone": "(555) 123-4567",
  "timeZoneId": "America/Los_Angeles",
  "isActive": true
}
```

---

## Registration Flow Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    REGISTRATION FLOW                        │
└─────────────────────────────────────────────────────────────┘

1. Load baseUrl.json
   ↓
2. POST /device-registration/qr-registration
   ↓
3. Receive: QR Code, AssignedGuid, AccessToken
   ↓
4. Save initial registration.json (status: "QR issued")
   ↓
5. Display QR code to user
   ↓
6. Start polling loop (every 10 seconds)
   ↓
7. GET /device-registration/device-status/{guid}
   ↓
8. Update registration.json with latest status
   ↓
9. Check if ApiKey is present
   ├─ NO  → Continue polling (update status message)
   └─ YES → Device Activated!
       ↓
      10. Fetch branch info from inventory API
       ↓
      11. Save branchInfo.json
       ↓
      12. Stop polling
       ↓
      13. Show success message
```

---

## Step-by-Step Process

### Step 1: Initialize Registration

**Action**: Load base URLs and validate configuration

```csharp
// Load baseUrl.json
var baseCfg = await ConfigStorage.LoadBaseUrlsAsync("/home/unisight/Config/baseUrl.json");
var baseUrl = baseCfg?.BaseUrl?.Trim();

if (string.IsNullOrWhiteSpace(baseUrl))
    throw new InvalidOperationException("BASE_URL is missing in baseUrl.json");

// Get device type (default: 11)
var deviceType = 11;
if (!string.IsNullOrWhiteSpace(baseCfg?.OneScanDeviceType) &&
    int.TryParse(baseCfg.OneScanDeviceType, out var parsed))
    deviceType = parsed;
```

### Step 2: Request QR Code Registration

**Endpoint**: `POST {BASE_URL}/device-registration/qr-registration`

**Headers**:
```
version: v1
Content-Type: application/json
Accept: application/json
```

**Request Body**:
```json
{
  "DeviceType": 11
}
```

**Response** (HTTP 200/201):
```json
{
  "Url": "https://app.example.com/device-claim/123e4567-e89b-12d3-a456-426614174000",
  "QrCodeImage": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUg...",
  "AccessToken": "Bearer eyJhbGciOiJIUzI1NiIs...",
  "AssignedGuid": "123e4567-e89b-12d3-a456-426614174000"
}
```

**Implementation**:
```csharp
var registerEndpoint = $"{baseUrl}/device-registration/qr-registration";

using var req = new HttpRequestMessage(HttpMethod.Post, registerEndpoint);
req.Headers.TryAddWithoutValidation("version", "v1");
req.Headers.Accept.Add(new MediaTypeWithQualityHeaderValue("application/json"));

var body = new CreateQRCodeRegistrationDTO { DeviceType = deviceType };
var json = JsonSerializer.Serialize(body);
req.Content = new StringContent(json, Encoding.UTF8, "application/json");

using var res = await _http.SendAsync(req, HttpCompletionOption.ResponseHeadersRead, ct);
var text = await res.Content.ReadAsStringAsync(ct);
var resp = JsonSerializer.Deserialize<CreateQRCodeRegistrationResponse>(text, 
    new JsonSerializerOptions { PropertyNameCaseInsensitive = true });
```

### Step 3: Save Initial Registration State

**Action**: Persist registration data immediately after receiving QR code

```csharp
await ConfigStorage.SaveRegistrationAsync("/home/unisight/Config/registration.json", 
    new RegistrationState
    {
        AssignedGuid = resp.AssignedGuid,
        AccessToken  = resp.AccessToken,
        DeviceStatus = "QR issued"
    });
```

**File Created**: `/home/unisight/Config/registration.json`
```json
{
  "AssignedGuid": "123e4567-e89b-12d3-a456-426614174000",
  "AccessToken": "Bearer eyJhbGciOiJIUzI1NiIs...",
  "DeviceStatus": "QR issued"
}
```

### Step 4: Display QR Code

**Action**: Show QR code on device screen for user to scan with mobile app

```csharp
// Convert base64 QR image to bitmap
Qr = BitmapFromBase64(resp.QrCodeImage);

// Show instructions
Status = "Scan the QR code with your phone to claim this device.";
```

### Step 5: Start Polling for Activation

**Action**: Poll device status every 10 seconds until ApiKey is received

**Endpoint**: `GET {BASE_URL}/device-registration/device-status/{AssignedGuid}`

**Headers**:
```
version: v1
Accept: application/json
Authorization: Bearer {AccessToken}
```

**Polling Loop**:
```csharp
using var timer = new PeriodicTimer(TimeSpan.FromSeconds(10));

while (await timer.WaitForNextTickAsync(ct))
{
    var statusEndpoint = $"{baseUrl}/device-registration/device-status/{assignedGuid}";
    
    using var req = new HttpRequestMessage(HttpMethod.Get, statusEndpoint);
    req.Headers.TryAddWithoutValidation("version", "v1");
    req.Headers.Accept.Add(new MediaTypeWithQualityHeaderValue("application/json"));
    req.Headers.Authorization = new AuthenticationHeaderValue("Bearer", accessToken);
    
    using var res = await _http.SendAsync(req, ct);
    var text = await res.Content.ReadAsStringAsync(ct);
    var status = JsonSerializer.Deserialize<GetDeviceRegistrationStatusByIdResponse>(text);
    
    // Check for activation...
}
```

### Step 6: Check Status Responses

**Response Examples**:

**Initial State** (not yet claimed):
```json
{
  "deviceStatus": "Pending",
  "apiKey": null,
  "branchId": null,
  "branch": null
}
```

**After User Scans QR** (claimed but not activated):
```json
{
  "deviceStatus": "Claimed",
  "apiKey": null,
  "branchId": 2,
  "branch": "Qualmart San Francisco"
}
```

**Fully Activated**:
```json
{
  "deviceStatus": "Activated",
  "apiKey": "sk_live_1234567890abcdef",
  "branchId": 2,
  "branch": "Qualmart San Francisco"
}
```

### Step 7: Update Registration State on Each Poll

**Action**: Save updated status to registration.json after every poll

```csharp
await ConfigStorage.SaveRegistrationAsync("/home/unisight/Config/registration.json", 
    new RegistrationState
    {
        AssignedGuid = assignedGuid,
        AccessToken  = accessToken,
        DeviceStatus = status.DeviceStatus,
        ApiKey       = status.ApiKey,      // Will be null until activated
        BranchId     = status.BranchId,
        Branch       = status.Branch
    });
```

### Step 8: Detect Activation

**Condition**: Device is activated when `ApiKey` is present

```csharp
if (!string.IsNullOrWhiteSpace(status.ApiKey))
{
    // Device is activated! Stop polling and fetch branch info
    IsRegistered = true;
    Busy = false;
    
    // Continue to Step 9...
}
else
{
    // Still waiting for activation
    Status = $"Waiting for activation… ({status.DeviceStatus})";
    // Continue polling...
}
```

### Step 9: Fetch Branch Information

**Action**: After activation, retrieve detailed branch data

**Endpoint**: `GET {BASE_URL_INVENTORY}/api/v1/branches/current`

**Headers**:
```
version: v1
Accept: application/json
X-Api-Key: {ApiKey}
```

**Implementation**:
```csharp
var baseInventoryUrl = baseCfg?.BaseUrlInventory;
var endpoint = $"{baseInventoryUrl}/api/v1/branches/current";

using var req = new HttpRequestMessage(HttpMethod.Get, endpoint);
req.Headers.TryAddWithoutValidation("version", "v1");
req.Headers.Accept.Add(new MediaTypeWithQualityHeaderValue("application/json"));
req.Headers.TryAddWithoutValidation("X-Api-Key", status.ApiKey);

using var res = await _http.SendAsync(req, ct);
var text = await res.Content.ReadAsStringAsync(ct);
var branchResp = JsonSerializer.Deserialize<BranchResponse>(text, 
    new JsonSerializerOptions { PropertyNameCaseInsensitive = true });
```

**Response**:
```json
{
  "success": {
    "id": 2,
    "companyId": 1,
    "company": "Qualmart",
    "name": "Qualmart San Francisco",
    "address1": "123 Main St",
    "address2": "Suite 100",
    "city": "San Francisco",
    "zipCode": "94102",
    "stateId": 5,
    "state": "CA",
    "phone": "(555) 123-4567",
    "fax": "(555) 123-4568",
    "website": "https://qualmart.com",
    "imageUrl": "https://cdn.example.com/branch-logo.png",
    "timeZoneId": "America/Los_Angeles",
    "universalEditor": false,
    "isActive": true,
    "createdDate": "2024-01-15T10:30:00Z"
  }
}
```

### Step 10: Save Branch Information

**Action**: Extract the `success` object and save to branchInfo.json

```csharp
await SaveJsonAsync("/home/unisight/Config/branchInfo.json", branchResp.Success, ct);
```

**File Created**: `/home/unisight/Config/branchInfo.json`
```json
{
  "id": 2,
  "companyId": 1,
  "company": "Qualmart",
  "name": "Qualmart San Francisco",
  "address1": "123 Main St",
  "city": "San Francisco",
  "state": "CA",
  "zipCode": "94102",
  "phone": "(555) 123-4567",
  "timeZoneId": "America/Los_Angeles",
  "isActive": true
}
```

### Step 11: Show Success Message

**Action**: Display confirmation to user

```csharp
SuccessMessage = $"🎉 Congratulations! Your device is registered under: {status.Branch}";
Status = null;
Busy = false;
```

---

## Heartbeat Monitoring

After successful registration, the device continuously monitors its connection status with the backend through a heartbeat system.

### Heartbeat Overview

**Purpose**: 
- Verify device is still registered and active
- Receive message notifications from backend
- Detect if device has been deleted from the system
- Monitor connectivity status

**Polling Interval**: Every 60 seconds (1 minute)

**Endpoint**: `GET {BASE_URL}/device-registration/heartbeat`

### Heartbeat Implementation

#### Service Initialization

```csharp
// Start heartbeat monitoring after app startup
public async Task StartHeartbeatAsync()
{
    var heartbeatService = services.GetService<IDeviceHeartbeatService>();
    await heartbeatService.StartAsync(cancellationToken);
}
```

#### Background Loop

The heartbeat service runs continuously in the background:

```csharp
private async Task LoopAsync(CancellationToken ct)
{
    try
    {
        // Check immediately on startup
        await CheckHeartbeatAsync(ct);
        
        // Then check every minute
        while (!ct.IsCancellationRequested)
        {
            await Task.Delay(TimeSpan.FromMinutes(1), ct);
            await CheckHeartbeatAsync(ct);
        }
    }
    catch (OperationCanceledException) { }
    catch (Exception ex) 
    { 
        Console.WriteLine($"[Heartbeat] Loop error: {ex.Message}");
    }
}
```

#### Heartbeat Request

**Headers**:
```
version: v1
Accept: application/json
X-Api-Key: {ApiKey from registration.json}
```

**Implementation**:
```csharp
private async Task CheckHeartbeatAsync(CancellationToken ct)
{
    // Load ApiKey from registration.json (read-only)
    var registration = await RegistrationLoader.LoadAsync(ct);
    if (string.IsNullOrWhiteSpace(registration?.ApiKey))
    {
        Console.WriteLine("[Heartbeat] No API key found, skipping check");
        return;
    }
    
    // Load BASE_URL
    var baseUrl = Environment.GetEnvironmentVariable("BASE_URL");
    if (string.IsNullOrWhiteSpace(baseUrl))
    {
        var cfg = await BaseUrlsLoader.LoadAsync();
        baseUrl = cfg?.BaseUrl;
    }
    
    if (string.IsNullOrWhiteSpace(baseUrl))
    {
        Console.WriteLine("[Heartbeat] No BASE_URL found, skipping check");
        return;
    }
    
    // Send heartbeat request
    var endpoint = $"{baseUrl.TrimEnd('/')}/device-registration/heartbeat";
    using var req = new HttpRequestMessage(HttpMethod.Get, endpoint);
    req.Headers.TryAddWithoutValidation("version", "v1");
    req.Headers.Accept.Add(new MediaTypeWithQualityHeaderValue("application/json"));
    req.Headers.TryAddWithoutValidation("X-Api-Key", registration.ApiKey);
    
    using var res = await _http.SendAsync(req, ct);
    var code = (int)res.StatusCode;
    var text = await res.Content.ReadAsStringAsync(ct);
    
    Console.WriteLine($"[Heartbeat] Response: HTTP {code}");
    Console.WriteLine($"[Heartbeat] Body: {text}");
    
    // Handle response...
}
```

### Heartbeat Response Types

#### 1. Normal Heartbeat (HTTP 200)

**Response**:
```json
{
  "messageCount": 3,
  "status": "active",
  "lastSeen": "2026-01-02T12:34:56Z"
}
```

**Handling**:
```csharp
if (code == 200)
{
    using var doc = JsonDocument.Parse(text);
    if (doc.RootElement.TryGetProperty("messageCount", out var countElement) &&
        countElement.TryGetInt32(out var newCount))
    {
        if (newCount != MessageCount)
        {
            MessageCount = newCount;
            MessageCountUpdated?.Invoke(MessageCount);
            Console.WriteLine($"[Heartbeat] MessageCount updated: {newCount}");
        }
    }
}
```

#### 2. Device Deleted Response

The backend returns a specific error structure when a device has been deleted:

**Response** (HTTP 200 with error payload):
```json
{
  "message": null,
  "innerException": null,
  "errors": null,
  "stackTrace": null
}
```

**Detection Logic**:
```csharp
// Check for device deletion response signature
if (!string.IsNullOrWhiteSpace(text) && 
    text.Contains("\"message\":null") && 
    text.Contains("\"innerException\":null") && 
    text.Contains("\"errors\":null") && 
    text.Contains("\"stackTrace\":null"))
{
    Console.WriteLine("[Heartbeat] Device has been deleted from backend");
    // Handle deletion (see next section)
}
```

#### 3. Authentication Errors (HTTP 401/403)

**Response**: HTTP 401 or 403

**Handling**:
```csharp
if (code == 401 || code == 403)
{
    Console.WriteLine("[Heartbeat] Authentication failed - API key may be invalid");
    // Device may need re-registration
    return;
}
```

#### 4. Device Not Found (HTTP 404/410)

**Response**: HTTP 404 (Not Found) or 410 (Gone)

**Handling**:
```csharp
if (code == 404 || code == 410)
{
    Console.WriteLine("[Heartbeat] Device not found in backend");
    // Treat as deletion
    MessageCount = 0;
    MessageCountUpdated?.Invoke(MessageCount);
    return;
}
```

### Message Count Tracking

The heartbeat system tracks a `MessageCount` property that indicates pending notifications:

```csharp
public interface IDeviceHeartbeatService
{
    /// <summary>
    /// Latest message count from backend. 0 when unknown or device deleted.
    /// </summary>
    int MessageCount { get; }
    
    /// <summary>
    /// Raised when MessageCount changes.
    /// </summary>
    event Action<int>? MessageCountUpdated;
    
    Task StartAsync(CancellationToken ct = default);
}
```

**Usage in UI**:
```csharp
// Subscribe to message count updates
_heartbeatService.MessageCountUpdated += OnMessageCountChanged;

private void OnMessageCountChanged(int newCount)
{
    Console.WriteLine($"Device has {newCount} pending messages");
    // Update UI badge, notification indicator, etc.
}
```

---

## Device Deletion Handling

When a device is deleted from the backend (via admin panel or API), the device must detect this and reset to the registration screen.

### Detection Methods

The device detects deletion through the heartbeat system in two ways:

#### 1. Error Response Pattern

Backend returns a **specific error structure** when device is deleted:

**Exact JSON Response**:
```json
{
  "message": null,
  "innerException": null,
  "errors": null,
  "stackTrace": null
}
```

**Detection Code**:
```csharp
// Check if response body contains ALL these null fields
if (!string.IsNullOrWhiteSpace(text) && 
    text.Contains("\"message\":null") && 
    text.Contains("\"innerException\":null") && 
    text.Contains("\"errors\":null") && 
    text.Contains("\"stackTrace\":null"))
{
    // Device has been deleted from backend
    Console.WriteLine("[Heartbeat] Device deleted from backend");
    // Trigger deletion handling...
}
```

**Why This Works**:
- This is the backend's standard error response for deleted devices
- All four fields must be `null` (not missing, but explicitly `null`)
- This pattern is **unique** to deletion responses
- Normal responses have different structures

#### 2. HTTP Status Codes

Alternative detection method when backend returns specific HTTP codes:

- **404 Not Found**: Device record doesn't exist in database
- **410 Gone**: Device was explicitly deleted (preferred status for deletions)

**Detection Code**:
```csharp
if (code == 410)
{
    Console.WriteLine("[Heartbeat] Device not found (404/410) - deleted from backend");
    // Trigger deletion handling...
}
```

**Note**: Some backends may return HTTP 200 with the error structure (Method 1) instead of 404/410, so both methods should be implemented.

### Deletion Response Flow

```
Heartbeat Check
    ↓
Backend Response
    ↓
Deletion Detected
    ↓
Delete Local Files
    ├─ registration.json
    └─ branchInfo.json
    ↓
Reset MessageCount to 0
    ↓
Trigger MessageCountUpdated Event
    ↓
Application Returns to Registration Screen
```

### Implementation

#### Complete Deletion Detection and Handling

```csharp
// In DeviceHeartbeatService.cs - CheckHeartbeatAsync method
private async Task CheckHeartbeatAsync(CancellationToken ct)
{
    try
    {
        // ... (load config and send request)
        
        using var res = await _http.SendAsync(req, ct);
        var code = (int)res.StatusCode;
        var text = await res.Content.ReadAsStringAsync(ct);
        
        Console.WriteLine($"[Heartbeat] Response: HTTP {code}");
        Console.WriteLine($"[Heartbeat] Body: {text}");
        
        // ========== DELETION DETECTION ==========
        
        // METHOD 1: Check for specific error response structure (most reliable)
        // Backend returns this exact JSON when device is deleted:
        // {"message":null,"innerException":null,"errors":null,"stackTrace":null}
        if (!string.IsNullOrWhiteSpace(text) && 
            text.Contains("\"message\":null") && 
            text.Contains("\"innerException\":null") && 
            text.Contains("\"errors\":null") && 
            text.Contains("\"stackTrace\":null"))
        {
            Console.WriteLine("[Heartbeat] Detected device deletion response");
            Console.WriteLine("[Heartbeat] Deleting local registration.json and branchInfo.json");
            
            // Delete both configuration files
            RegistrationLoader.Delete();
            BranchInfoLoader.Delete();
            
            // Reset message count and notify listeners
            MessageCount = 0;
            MessageCountUpdated?.Invoke(MessageCount);
            return;
        }
        
        // METHOD 2: Check for HTTP 404/410 status codes
        if (code == 404 || code == 410)
        {
            Console.WriteLine("[Heartbeat] Device appears to be deleted (404/410 response)");
            
            // Delete both configuration files
            RegistrationLoader.Delete();
            BranchInfoLoader.Delete();
            
            // Reset message count and notify listeners
            MessageCount = 0;
            MessageCountUpdated?.Invoke(MessageCount);
            return;
        }
        
        // Handle other status codes...
        if (code == 401 || code == 403)
        {
            Console.WriteLine("[Heartbeat] Authentication failed");
            return;
        }
        
        if (code != 200)
        {
            Console.WriteLine($"[Heartbeat] Unexpected response code: {code}");
            return;
        }
        
        // Parse normal response (messageCount, status, etc.)
        // ...
    }
    catch (Exception ex)
    {
        Console.WriteLine($"[Heartbeat] Error: {ex.Message}");
    }
}
```

#### RegistrationLoader.Delete()

```csharp
public static class RegistrationLoader
{
    public const string RegistrationPath = "/home/unisight/Config/registration.json";
    
    public static void Delete()
    {
        try 
        { 
            if (File.Exists(RegistrationPath)) 
                File.Delete(RegistrationPath); 
        } 
        catch (Exception ex)
        {
            Console.WriteLine($"[Registration] Failed to delete: {ex.Message}");
        }
    }
}
```

#### BranchInfoLoader.Delete()

```csharp
public static class BranchInfoLoader
{
    public const string BranchInfoPath = "/home/unisight/Config/branchInfo.json";
    
    public static void Delete()
    {
        try 
        { 
            if (File.Exists(BranchInfoPath)) 
                File.Delete(BranchInfoPath); 
        } 
        catch (Exception ex)
        {
            Console.WriteLine($"[BranchInfo] Failed to delete: {ex.Message}");
        }
    }
}
```

### Application State Management

After detecting deletion, the application should automatically return to the registration screen:

```csharp
// In MainWindow or App initialization
public async Task CheckRegistrationStatusAsync()
{
    var registration = await RegistrationLoader.LoadAsync();
    
    if (registration == null || string.IsNullOrWhiteSpace(registration.ApiKey))
    {
        // No valid registration - show registration screen
        ShowRegistrationView();
        return;
    }
    
    // Valid registration - continue to main app
    ShowMainView();
    
    // Start heartbeat monitoring
    await _heartbeatService.StartAsync();
}

// Monitor heartbeat for deletion
_heartbeatService.MessageCountUpdated += (count) =>
{
    if (count == 0 && !File.Exists(RegistrationLoader.RegistrationPath))
    {
        // Device was deleted - return to registration
        Dispatcher.UIThread.InvokeAsync(() => ShowRegistrationView());
    }
};
```

### Console Output Example

When deletion is detected:

```
[Heartbeat] Checking heartbeat...
[Heartbeat] BASE_URL from config: https://api.example.com
[Heartbeat] Endpoint URL: https://api.example.com/device-registration/heartbeat
[Heartbeat] Using ApiKey: sk_l...4567
[Heartbeat] Sending request...
[Heartbeat] Response status: HTTP 200
[Heartbeat] Response body:
{
  "message": null,
  "innerException": null,
  "errors": null,
  "stackTrace": null
}
[Heartbeat] Detected device deletion response
[Heartbeat] Deleting local registration.json and branchInfo.json
[Heartbeat] MessageCount changed: 5 -> 0
[MainWindow] Registration files deleted - showing registration view
```

### Graceful Handling

**Key Principles**:

1. **Read-Only Heartbeat**: Heartbeat service only reads registration.json, never modifies it (except deletion)
2. **File Deletion Only**: When deletion detected, only delete local files - no API calls needed
3. **Event-Driven UI**: Use MessageCountUpdated event to trigger UI changes
4. **Automatic Recovery**: App automatically returns to registration screen without user intervention
5. **No Data Loss**: User data (scans, logs) is preserved; only registration credentials are deleted

---

## API Endpoints

### 1. Request QR Code Registration

**Endpoint**: `POST {BASE_URL}/device-registration/qr-registration`

**Headers**:
- `version: v1`
- `Content-Type: application/json`
- `Accept: application/json`

**Request**:
```json
{
  "DeviceType": 11
}
```

**Response** (200/201):
```json
{
  "Url": "https://app.example.com/device-claim/{guid}",
  "QrCodeImage": "data:image/png;base64,...",
  "AccessToken": "Bearer ...",
  "AssignedGuid": "guid-string"
}
```

### 2. Check Device Status

**Endpoint**: `GET {BASE_URL}/device-registration/device-status/{AssignedGuid}`

**Headers**:
- `version: v1`
- `Accept: application/json`
- `Authorization: Bearer {AccessToken}`

**Response** (200):
```json
{
  "deviceStatus": "Activated",
  "apiKey": "sk_live_...",
  "branchId": 2,
  "branch": "Branch Name"
}
```

### 3. Get Branch Information

**Endpoint**: `GET {BASE_URL_INVENTORY}/api/v1/branches/current`

**Headers**:
- `version: v1`
- `Accept: application/json`
- `X-Api-Key: {ApiKey}`

**Response** (200):
```json
{
  "success": {
    "id": 2,
    "name": "Branch Name",
    "address1": "123 Main St",
    "city": "City",
    "state": "State",
    ...
  }
}
```

### 4. Device Heartbeat

**Endpoint**: `GET {BASE_URL}/device-registration/heartbeat`

**Headers**:
- `version: v1`
- `Accept: application/json`
- `X-Api-Key: {ApiKey from registration.json}`

**Polling Interval**: Every 60 seconds

**Response - Normal** (200):
```json
{
  "messageCount": 3,
  "status": "active",
  "lastSeen": "2026-01-02T12:34:56Z"
}
```

**Response - Device Deleted** (200 with error structure):
```json
{
  "message": null,
  "innerException": null,
  "errors": null,
  "stackTrace": null
}
```

**Response - Device Not Found** (404 or 410):
```
HTTP 404 Not Found
or
HTTP 410 Gone
```

---

## Data Models

### CreateQRCodeRegistrationDTO

```csharp
public sealed class CreateQRCodeRegistrationDTO
{
    public int DeviceType { get; set; }  // 11 for OneScan
}
```

### CreateQRCodeRegistrationResponse

```csharp
public sealed class CreateQRCodeRegistrationResponse
{
    public string? Url { get; set; }
    public string? QrCodeImage { get; set; }
    public string? AccessToken { get; set; }
    public string? AssignedGuid { get; set; }
}
```

### GetDeviceRegistrationStatusByIdResponse

```csharp
public sealed class GetDeviceRegistrationStatusByIdResponse
{
    [JsonPropertyName("deviceStatus")]
    public string? DeviceStatus { get; set; }  // "Pending", "Claimed", "Activated"
    
    [JsonPropertyName("apiKey")]
    public string? ApiKey { get; set; }  // null until activated
    
    [JsonPropertyName("branchId")]
    public int? BranchId { get; set; }
    
    [JsonPropertyName("branch")]
    public string? Branch { get; set; }
}
```

### RegistrationState

```csharp
public sealed class RegistrationState
{
    [JsonPropertyName("AssignedGuid")]
    public string? AssignedGuid { get; set; }
    
    [JsonPropertyName("AccessToken")]
    public string? AccessToken { get; set; }
    
    [JsonPropertyName("DeviceStatus")]
    public string? DeviceStatus { get; set; }
    
    [JsonPropertyName("ApiKey")]
    public string? ApiKey { get; set; }
    
    [JsonPropertyName("BranchId")]
    public int? BranchId { get; set; }
    
    [JsonPropertyName("Branch")]
    public string? Branch { get; set; }
}
```

### BranchResponse

```csharp
public sealed class BranchResponse
{
    [JsonPropertyName("success")]
    public BranchSuccess? Success { get; set; }
}

public sealed class BranchSuccess
{
    [JsonPropertyName("id")] public int Id { get; set; }
    [JsonPropertyName("companyId")] public int CompanyId { get; set; }
    [JsonPropertyName("company")] public string? Company { get; set; }
    [JsonPropertyName("name")] public string? Name { get; set; }
    [JsonPropertyName("address1")] public string? Address1 { get; set; }
    [JsonPropertyName("city")] public string? City { get; set; }
    [JsonPropertyName("state")] public string? State { get; set; }
    [JsonPropertyName("zipCode")] public string? ZipCode { get; set; }
    [JsonPropertyName("phone")] public string? Phone { get; set; }
    [JsonPropertyName("timeZoneId")] public string? TimeZoneId { get; set; }
    [JsonPropertyName("isActive")] public bool IsActive { get; set; }
    // ... additional properties
}
```

### BaseUrlsConfig

```csharp
public sealed class BaseUrlsConfig
{
    [JsonPropertyName("BASE_URL")]
    public string? BaseUrl { get; set; }
    
    [JsonPropertyName("BASE_URL_POS")]
    public string? BaseUrlPos { get; set; }
    
    [JsonPropertyName("BASE_URL_INVENTORY")]
    public string? BaseUrlInventory { get; set; }
    
    [JsonPropertyName("ONESCAN_DEVICE_TYPE")]
    public string? OneScanDeviceType { get; set; }
}
```

### IDeviceHeartbeatService

```csharp
public interface IDeviceHeartbeatService
{
    /// <summary>
    /// Latest message count returned by the backend heartbeat. Default 0 when unknown.
    /// </summary>
    int MessageCount { get; }
    
    /// <summary>
    /// Raised when MessageCount changes (including when device is deleted and count resets to 0).
    /// </summary>
    event Action<int>? MessageCountUpdated;
    
    /// <summary>
    /// Start the heartbeat polling loop (checks every 1 minute).
    /// </summary>
    Task StartAsync(CancellationToken ct = default);
}
```

---

## File Structure

```
/home/unisight/
└── Config/
    ├── baseUrl.json          # Manual: API endpoints and device type
    ├── registration.json     # Auto: Device registration state
    └── branchInfo.json       # Auto: Branch details after activation
```

### File Creation Timeline

1. **Before Registration**: 
   - `baseUrl.json` (created manually)

2. **During QR Code Request**:
   - `registration.json` (created with AssignedGuid, AccessToken, status="QR issued")

3. **During Polling**:
   - `registration.json` (updated every 10 seconds with latest status)

4. **After Activation**:
   - `registration.json` (updated with ApiKey, BranchId, Branch)
   - `branchInfo.json` (created with full branch details)

---

## Error Handling

### Common Errors and Solutions

#### 1. Missing baseUrl.json
**Error**: `BASE_URL is missing in baseUrl.json`
**Solution**: Create `/home/unisight/Config/baseUrl.json` with required fields

#### 2. HTTP 400 (Bad Request)
**Possible Causes**:
- Invalid DeviceType
- Malformed request body
**Solution**: Verify DeviceType is numeric (e.g., 11)

#### 3. HTTP 401 (Unauthorized)
**Possible Causes**:
- Invalid or expired AccessToken
- Missing Authorization header
**Solution**: Ensure Bearer token is included in status check requests

#### 4. HTTP 404 (Not Found)
**Possible Causes**:
- Wrong AssignedGuid in status check
- Device registration expired
**Solution**: Start new registration process

#### 5. HTTP 500 (Server Error)
**Action**: Retry polling after delay
**Implementation**: Continue polling loop, log error

#### 6. Branch Info Fetch Failure
**Error**: `Branch info failed (HTTP {code})`
**Impact**: Non-fatal - device is still activated
**Solution**: Can be retried manually later

#### 7. Timeout During Polling
**Action**: Continue polling indefinitely until activation
**Note**: User can cancel registration if needed

#### 8. Heartbeat Authentication Failure
**Error**: HTTP 401/403 from heartbeat endpoint
**Possible Causes**:
- Invalid or revoked API key
- Device was deleted and re-created with different credentials
**Solution**: Device may need re-registration

#### 9. Device Deletion Detected
**Signal**: Error response structure or 404/410 status
**Action**: 
- Delete local registration.json and branchInfo.json
- Reset MessageCount to 0
- Return to registration screen automatically
**Impact**: Device will need to be re-registered

#### 10. Heartbeat Network Failure
**Error**: Connection timeout or network unreachable
**Action**: Continue heartbeat loop, retry on next interval (1 minute)
**Note**: Transient network issues don't require re-registration

---

## Best Practices

### 1. Polling Strategy
- **Interval**: 10 seconds (balances responsiveness vs. server load)
- **Timeout**: None (poll until activated or cancelled)
- **Error Handling**: Continue polling on transient errors (4xx/5xx)

### 2. File Persistence
- Save registration.json after **every** poll response
- Use atomic writes (write to .tmp, then rename)
- Create Config directory if it doesn't exist

### 3. Security
- Store AccessToken securely in registration.json
- Include Bearer token in all status check requests
- ApiKey is sensitive - protect registration.json file permissions

### 4. User Experience
- Display QR code immediately after receiving response
- Show status updates during polling ("Waiting for activation…")
- Clear success message when activated
- Allow user to cancel registration process

### 5. Cancellation
- Provide Cancel button/action
- Use CancellationToken to stop polling gracefully
- Clean up resources (HTTP clients, timers)

### 6. Heartbeat Monitoring
- Start heartbeat service immediately after successful registration
- Run continuously in background (every 60 seconds)
- Monitor for device deletion and handle gracefully
- Use event-driven pattern for MessageCount updates
- Never modify registration.json from heartbeat (read-only except deletion)

### 7. Device Deletion Recovery
- Detect deletion through heartbeat responses
- Delete local files automatically (registration.json, branchInfo.json)
- Return to registration screen without user intervention
- Preserve user data and application logs
- Allow immediate re-registration

---

## Usage Example

### Complete Registration Flow

```csharp
public async Task RegisterDeviceAsync(CancellationToken ct)
{
    // 1. Load configuration
    var baseCfg = await ConfigStorage.LoadBaseUrlsAsync("/home/unisight/Config/baseUrl.json");
    var baseUrl = baseCfg?.BaseUrl ?? throw new Exception("Missing BASE_URL");
    var deviceType = int.Parse(baseCfg.OneScanDeviceType ?? "11");
    
    // 2. Request QR code
    var response = await RequestQRCodeAsync(baseUrl, deviceType, ct);
    
    // 3. Save initial state
    await SaveRegistrationAsync(new RegistrationState 
    {
        AssignedGuid = response.AssignedGuid,
        AccessToken = response.AccessToken,
        DeviceStatus = "QR issued"
    });
    
    // 4. Display QR code
    DisplayQRCode(response.QrCodeImage);
    
    // 5. Poll for activation
    await PollUntilActivatedAsync(baseUrl, response.AssignedGuid, response.AccessToken, ct);
    
    // 6. Fetch branch info
    var registration = await LoadRegistrationAsync();
    await FetchBranchInfoAsync(baseCfg.BaseUrlInventory, registration.ApiKey, ct);
    
    // 7. Complete
    ShowSuccessMessage("Device activated!");
    
    // 8. Start heartbeat monitoring
    await _heartbeatService.StartAsync(ct);
    
    // 9. Monitor for deletion
    _heartbeatService.MessageCountUpdated += (count) =>
    {
        if (count == 0 && !File.Exists(RegistrationLoader.RegistrationPath))
        {
            // Device deleted - return to registration
            Dispatcher.UIThread.InvokeAsync(() => ShowRegistrationView());
        }
    };
}
```

---

## Summary

The registration process ensures secure device provisioning through:

1. **QR Code Generation**: Device requests unique registration QR code
2. **User Activation**: User scans QR with mobile app to claim device
3. **Polling**: Device polls backend every 10 seconds for activation status
4. **API Key Delivery**: Backend provides ApiKey when device is activated
5. **Branch Association**: Device fetches and stores branch information
6. **Configuration Persistence**: All data saved to JSON files in `/home/unisight/Config/`
7. **Heartbeat Monitoring**: Device checks backend every 60 seconds for status and messages
8. **Deletion Handling**: Automatic cleanup and re-registration when device is deleted

**Key Files**:
- `baseUrl.json` - API endpoints (manual)
- `registration.json` - Device credentials (automatic)
- `branchInfo.json` - Branch details (automatic)

**Key Endpoints**:
- `POST /device-registration/qr-registration` - Get QR code
- `GET /device-registration/device-status/{guid}` - Check activation status (10s interval)
- `GET /api/v1/branches/current` - Get branch details
- `GET /device-registration/heartbeat` - Monitor status and messages (60s interval)

**Key Features**:
- **Secure provisioning** through QR code and API keys
- **Automatic activation** detection via polling
- **Branch association** with full location details
- **Continuous monitoring** via heartbeat system
- **Message notifications** through MessageCount tracking
- **Deletion detection** with automatic cleanup
- **Graceful recovery** returns to registration screen automatically

This process ensures devices are securely registered, associated with the correct branch, continuously monitored, and can recover gracefully from deletion or de-provisioning.
