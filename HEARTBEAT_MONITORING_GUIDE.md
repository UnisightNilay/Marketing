# Heartbeat Monitoring System Guide

## Overview
This document explains the heartbeat monitoring system used in OneScan to maintain continuous connectivity with the backend, track message notifications, and detect device deletion. This guide is designed for developers implementing similar heartbeat systems in other applications.

---

## Table of Contents
1. [Purpose and Features](#purpose-and-features)
2. [Architecture Overview](#architecture-overview)
3. [Polling Mechanism](#polling-mechanism)
4. [API Endpoint Details](#api-endpoint-details)
5. [Request Format](#request-format)
6. [Response Handling](#response-handling)
7. [Message Count Tracking](#message-count-tracking)
8. [Device Deletion Detection](#device-deletion-detection)
9. [Error Handling](#error-handling)
10. [Implementation Example](#implementation-example)
11. [Service Interface](#service-interface)
12. [Integration Guide](#integration-guide)
13. [Best Practices](#best-practices)

---

## Purpose and Features

The heartbeat monitoring system serves multiple critical functions:

### Primary Functions
1. **Connectivity Verification**: Confirms device is still connected to backend
2. **Message Notifications**: Receives count of pending messages for the device
3. **Deletion Detection**: Detects when device has been removed from backend
4. **Status Monitoring**: Tracks device health and activity

### Key Features
- Runs continuously in background
- Polls every 60 seconds (1 minute intervals)
- Read-only operation (never modifies local registration data except on deletion)
- Event-driven architecture for UI updates
- Automatic file cleanup on deletion detection
- Robust error handling with detailed console logging

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                   HEARTBEAT ARCHITECTURE                    │
└─────────────────────────────────────────────────────────────┘

Application Startup
    ↓
Load Registration Config
    ├─ ApiKey (from registration.json)
    └─ BASE_URL (from baseUrl.json or env var)
    ↓
Initialize HeartbeatService
    ↓
Start Background Loop
    ↓
┌─────────────────────────────────┐
│   Every 60 Seconds (1 Minute)   │
└─────────────────────────────────┘
    ↓
Read ApiKey (from registration.json)
    ↓
Send GET Request
    ├─ Endpoint: {BASE_URL}/device-registration/heartbeat
    ├─ Header: X-Api-Key: {ApiKey}
    └─ Header: version: v1
    ↓
Receive Response
    ↓
Parse Response
    ├─ Check for Deletion Signal
    ├─ Check for Error Codes (401, 403, 404, 410)
    └─ Extract messageCount
    ↓
Update Local State
    ├─ MessageCount Property
    └─ Trigger MessageCountUpdated Event
    ↓
UI Updates Automatically
    ↓
Wait 60 Seconds → Repeat
```

---

## Polling Mechanism

### Timing Configuration

**Polling Interval**: 60 seconds (1 minute)

```csharp
private readonly TimeSpan _interval = TimeSpan.FromMinutes(1);
```

### Background Loop Implementation

The heartbeat runs continuously in a background task:

```csharp
private async Task LoopAsync(CancellationToken ct)
{
    try
    {
        // Check immediately on startup (no initial delay)
        Console.WriteLine("[Heartbeat] Background loop started");
        await CheckHeartbeatAsync(ct).ConfigureAwait(false);

        // Then check every 1 minute
        while (!ct.IsCancellationRequested)
        {
            await Task.Delay(_interval, ct).ConfigureAwait(false);
            Console.WriteLine("[Heartbeat] Checking heartbeat...");
            await CheckHeartbeatAsync(ct).ConfigureAwait(false);
        }
    }
    catch (OperationCanceledException) 
    { 
        // Normal cancellation during app shutdown
    }
    catch (Exception ex) 
    { 
        Console.WriteLine($"[Heartbeat] Loop error: {ex.Message}");
    }
}
```

**Key Points**:
- First check happens immediately when service starts (no delay)
- Subsequent checks happen every 60 seconds
- Continues indefinitely until app shutdown
- Gracefully handles cancellation via CancellationToken
- Logs all errors but doesn't crash the application

---

## API Endpoint Details

### Endpoint URL

**Full Path**: `{BASE_URL}/device-registration/heartbeat`

**Method**: `GET`

**Example**:
```
GET https://api.example.com/device-registration/heartbeat
```

### URL Construction

The endpoint URL is built by combining:

1. **BASE_URL** - Retrieved from:
   - Environment variable `BASE_URL` (first priority)
   - OR `/home/unisight/Config/baseUrl.json` file (fallback)

2. **Path** - Fixed constant: `device-registration/heartbeat`

**Code**:
```csharp
// Load BASE_URL
string? baseUrl = Environment.GetEnvironmentVariable("BASE_URL");

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

// Combine URL parts safely
private static string CombineUrl(string baseUrl, string path)
    => baseUrl.TrimEnd('/') + "/" + path.TrimStart('/');

var endpoint = CombineUrl(baseUrl, "device-registration/heartbeat");
// Result: https://api.example.com/device-registration/heartbeat
```

---

## Request Format

### HTTP Request Structure

**Method**: `GET`

**Headers**:
```
version: v1
Accept: application/json
X-Api-Key: {ApiKey from registration.json}
```

### Complete Request Example

```http
GET /device-registration/heartbeat HTTP/1.1
Host: api.example.com
version: v1
Accept: application/json
X-Api-Key: sk_live_1234567890abcdef
```

### Implementation Code

```csharp
// Read ApiKey from registration.json (read-only)
var local = await RegistrationLoader.LoadAsync(ct).ConfigureAwait(false);

// Create HTTP request
using var req = new HttpRequestMessage(HttpMethod.Get, endpoint);
req.Headers.TryAddWithoutValidation("version", "v1");
req.Headers.Accept.Add(new MediaTypeWithQualityHeaderValue("application/json"));

// Add API key for authentication
if (!string.IsNullOrWhiteSpace(local?.ApiKey))
    req.Headers.TryAddWithoutValidation("X-Api-Key", local.ApiKey);

// Send request
using var res = await _http.SendAsync(req, HttpCompletionOption.ResponseHeadersRead, ct);
```

### Authentication

**API Key Source**: `registration.json` file

The API key is the **only authentication mechanism** - no device ID or other credentials are sent. The backend identifies the device by the API key itself.

**Example registration.json**:
```json
{
  "AssignedGuid": "123e4567-e89b-12d3-a456-426614174000",
  "AccessToken": "Bearer eyJhbGciOiJIUzI1NiIs...",
  "DeviceStatus": "Activated",
  "ApiKey": "sk_live_1234567890abcdef",
  "BranchId": 2,
  "Branch": "Qualmart San Francisco"
}
```

**Important**: The heartbeat service **only reads** this file, never modifies it (except when device is deleted, then it deletes the entire file).

---

## Response Handling

### Response Structure

The backend can return different responses depending on device status:

### 1. Normal Heartbeat Response (HTTP 200)

**Status Code**: `200 OK`

**Response Body**:
```json
{
  "messageCount": 3,
  "status": "active",
  "lastSeen": "2026-01-05T12:34:56Z"
}
```

**Fields**:
- `messageCount` (int): Number of pending messages/notifications for device
- `status` (string): Device status (e.g., "active", "inactive")
- `lastSeen` (datetime): Last time device checked in (optional)

**Handling Code**:
```csharp
if (code == 200 && !string.IsNullOrWhiteSpace(text))
{
    using var doc = JsonDocument.Parse(text);
    
    // Extract messageCount
    if (doc.RootElement.TryGetProperty("messageCount", out var countElement) &&
        countElement.TryGetInt32(out var newCount))
    {
        Console.WriteLine($"[Heartbeat] MessageCount: {MessageCount} -> {newCount}");
        
        if (newCount != MessageCount)
        {
            MessageCount = newCount;
            MessageCountUpdated?.Invoke(MessageCount);
        }
    }
}
```

### 2. Device Deleted Response (HTTP 200 with Error Structure)

**Status Code**: `200 OK`

**Response Body** (specific error signature):
```json
{
  "message": null,
  "innerException": null,
  "errors": null,
  "stackTrace": null
}
```

**Critical**: This is the **primary deletion detection method**. All four fields must be explicitly `null` (not missing, but present with `null` values).

**Handling Code**:
```csharp
// Check for the specific deletion signature
if (!string.IsNullOrWhiteSpace(text) && 
    text.Contains("\"message\":null") && 
    text.Contains("\"innerException\":null") && 
    text.Contains("\"errors\":null") && 
    text.Contains("\"stackTrace\":null"))
{
    Console.WriteLine("[Heartbeat] Detected device deletion response");
    Console.WriteLine("[Heartbeat] Deleting local registration.json and branchInfo.json");
    
    // Delete configuration files
    RegistrationLoader.Delete();
    BranchInfoLoader.Delete();
    
    // Reset message count
    MessageCount = 0;
    MessageCountUpdated?.Invoke(MessageCount);
    return;
}
```

**Why This Pattern?**
- This specific JSON structure is the backend's standard error response for deleted devices
- It's distinct from normal responses and other error types
- Provides reliable deletion detection even when HTTP status is 200
- Prevents false positives from maintenance windows or network errors

### 3. Authentication Error (HTTP 401/403)

**Status Code**: `401 Unauthorized` or `403 Forbidden`

**Meaning**: 
- API key is invalid, revoked, or expired
- Device may have been deleted and re-created with new credentials
- Authorization failed

**Handling Code**:
```csharp
if (code == 401 || code == 403)
{
    Console.WriteLine("[Heartbeat] Authentication failed (401/403 response)");
    // Don't delete files - API key might be temporarily invalid
    // User may need to re-register device
    return;
}
```

**Action**: Log the error but don't delete files. User may need to manually re-register.

### 4. Device Not Found (HTTP 404/410)

**Status Code**: `404 Not Found` or `410 Gone`

**Meaning**:
- Device record doesn't exist in backend database
- Device was explicitly deleted (410 is preferred for deletions)

**Handling Code**:
```csharp
if (code == 404 || code == 410)
{
    Console.WriteLine("[Heartbeat] Device not found (404/410) - deleted from backend");
    
    // Delete configuration files
    RegistrationLoader.Delete();
    BranchInfoLoader.Delete();
    
    // Reset message count
    MessageCount = 0;
    MessageCountUpdated?.Invoke(MessageCount);
    return;
}
```

**Note**: This is the **secondary deletion detection method**. Some backends may return HTTP 200 with error structure (Method 1) instead of 404/410.

### 5. Other Error Codes (5xx, etc.)

**Status Codes**: `500`, `502`, `503`, etc.

**Meaning**: Backend server error or temporary issue

**Handling Code**:
```csharp
if (code != 200)
{
    Console.WriteLine($"[Heartbeat] Unexpected response code: {code}");
    // Don't modify state - just log and continue
    return;
}
```

**Action**: Log the error but don't take action. Wait for next heartbeat cycle.

---

## Message Count Tracking

### Purpose

The `MessageCount` property tracks the number of pending messages/notifications for the device. This can be used to:
- Display notification badges in UI
- Alert user to pending actions
- Trigger message fetch operations
- Track backend communication status

### Property and Event

```csharp
public int MessageCount { get; private set; }

public event Action<int>? MessageCountUpdated;
```

### Update Logic

```csharp
// Extract messageCount from response
if (doc.RootElement.TryGetProperty("messageCount", out var countElement) &&
    countElement.TryGetInt32(out var newCount))
{
    Console.WriteLine($"[Heartbeat] MessageCount changed: {MessageCount} -> {newCount}");
    
    // Only fire event if count actually changed
    if (newCount != MessageCount)
    {
        MessageCount = newCount;
        MessageCountUpdated?.Invoke(MessageCount);
    }
}
```

### Usage in UI

```csharp
// Subscribe to message count updates
_heartbeatService.MessageCountUpdated += OnMessageCountChanged;

private void OnMessageCountChanged(int newCount)
{
    Console.WriteLine($"Device has {newCount} pending messages");
    
    // Update UI badge
    NotificationBadge.Text = newCount.ToString();
    NotificationBadge.IsVisible = newCount > 0;
    
    // Optionally fetch messages
    if (newCount > 0)
    {
        await FetchPendingMessagesAsync();
    }
}
```

### Special Cases

**MessageCount = 0**:
- Can mean no pending messages
- OR device was deleted (when combined with file deletion)

```csharp
// Check if device was deleted
if (count == 0 && !File.Exists(RegistrationLoader.RegistrationPath))
{
    // Device deleted - return to registration screen
    Dispatcher.UIThread.InvokeAsync(() => ShowRegistrationView());
}
```

---

## Device Deletion Detection

### Detection Methods

The system uses **two independent methods** to detect device deletion:

#### Method 1: Error Response Pattern (Primary)

**Trigger**: Specific JSON structure in response body

**Pattern**:
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
if (!string.IsNullOrWhiteSpace(text) && 
    text.Contains("\"message\":null") && 
    text.Contains("\"innerException\":null") && 
    text.Contains("\"errors\":null") && 
    text.Contains("\"stackTrace\":null"))
{
    // Device deleted - cleanup and reset
    RegistrationLoader.Delete();
    BranchInfoLoader.Delete();
    MessageCount = 0;
    MessageCountUpdated?.Invoke(MessageCount);
}
```

**Advantages**:
- Most reliable method
- Works even when HTTP status is 200
- Unique signature prevents false positives
- Backend's standard deletion response

#### Method 2: HTTP Status Codes (Fallback)

**Trigger**: HTTP 404 or 410 status codes

**Detection Code**:
```csharp
if (code == 404 || code == 410)
{
    // Device not found - cleanup and reset
    RegistrationLoader.Delete();
    BranchInfoLoader.Delete();
    MessageCount = 0;
    MessageCountUpdated?.Invoke(MessageCount);
}
```

**Advantages**:
- Simple and standard HTTP semantics
- Works with backends that don't use error structure
- HTTP 410 (Gone) explicitly indicates deletion

### Deletion Response Flow

```
Heartbeat Response Received
    ↓
Check Response Body First
    ├─ Contains null pattern? → DELETION DETECTED
    └─ No null pattern → Continue
    ↓
Check HTTP Status Code
    ├─ 404 or 410? → DELETION DETECTED
    └─ Other codes → Process normally
    ↓
[DELETION DETECTED]
    ↓
Delete Local Files
    ├─ /home/unisight/Config/registration.json
    └─ /home/unisight/Config/branchInfo.json
    ↓
Reset MessageCount to 0
    ↓
Trigger MessageCountUpdated Event
    ↓
Application Returns to Registration Screen
```

### File Deletion Implementation

**RegistrationLoader.Delete()**:
```csharp
public static class RegistrationLoader
{
    public const string RegistrationPath = "/home/unisight/Config/registration.json";
    
    public static void Delete()
    {
        try 
        { 
            if (File.Exists(RegistrationPath)) 
            {
                File.Delete(RegistrationPath);
                Console.WriteLine($"[Registration] Deleted: {RegistrationPath}");
            }
        } 
        catch (Exception ex)
        {
            Console.WriteLine($"[Registration] Failed to delete: {ex.Message}");
        }
    }
}
```

**BranchInfoLoader.Delete()**:
```csharp
public static class BranchInfoLoader
{
    public const string BranchInfoPath = "/home/unisight/Config/branchInfo.json";
    
    public static void Delete()
    {
        try 
        { 
            if (File.Exists(BranchInfoPath)) 
            {
                File.Delete(BranchInfoPath);
                Console.WriteLine($"[BranchInfo] Deleted: {BranchInfoPath}");
            }
        } 
        catch (Exception ex)
        {
            Console.WriteLine($"[BranchInfo] Failed to delete: {ex.Message}");
        }
    }
}
```

### Application State Recovery

After deletion detection, the application automatically returns to registration screen:

```csharp
// In MainWindow or App initialization
_heartbeatService.MessageCountUpdated += (count) =>
{
    // Check if files were deleted (indicates device deletion)
    if (count == 0 && !File.Exists(RegistrationLoader.RegistrationPath))
    {
        // Device was deleted - return to registration screen
        Dispatcher.UIThread.InvokeAsync(() => 
        {
            Console.WriteLine("[MainWindow] Device deleted - showing registration view");
            ShowRegistrationView();
        });
    }
};
```

### False Positive Prevention

**Why backend maintenance won't trigger deletion**:

1. **Null pattern check is specific**: Maintenance errors typically return HTML error pages or JSON with actual error messages, not the specific null pattern
2. **Check order matters**: Response body check happens FIRST, before status code check
3. **All four fields required**: All four fields (`message`, `innerException`, `errors`, `stackTrace`) must be explicitly `null`
4. **Maintenance 404s**: Usually return HTML or generic JSON error, not the deletion signature

**Example maintenance response that WON'T trigger deletion**:
```json
{
  "error": "Service temporarily unavailable",
  "code": 503
}
```
OR
```html
<html><body><h1>503 Service Unavailable</h1></body></html>
```

**Only this specific pattern triggers deletion**:
```json
{
  "message": null,
  "innerException": null,
  "errors": null,
  "stackTrace": null
}
```

---

## Error Handling

### Network Errors

**Scenario**: Network timeout, connection refused, DNS failure

**Handling**:
```csharp
catch (HttpRequestException ex) 
{ 
    Console.WriteLine($"[Heartbeat] Network error: {ex.Message}");
    // Don't modify state - continue to next heartbeat cycle
}
```

**Action**: Log error and wait for next cycle. Transient network issues don't require action.

### Parsing Errors

**Scenario**: Invalid JSON response

**Handling**:
```csharp
catch (JsonException ex)
{ 
    Console.WriteLine($"[Heartbeat] Failed to parse JSON: {ex.Message}");
    Console.WriteLine($"[Heartbeat] Raw response was: {text}");
    // Don't modify state
}
```

**Action**: Log the raw response for debugging, continue to next cycle.

### Cancellation

**Scenario**: App shutdown or service stop

**Handling**:
```csharp
catch (OperationCanceledException) 
{ 
    // Normal cancellation - do nothing
    Console.WriteLine("[Heartbeat] Service stopped");
}
```

**Action**: Graceful shutdown, no error logging needed.

### Unexpected Errors

**Scenario**: Any other exception

**Handling**:
```csharp
catch (Exception ex) 
{ 
    Console.WriteLine($"[Heartbeat] Unexpected error: {ex.Message}");
    Console.WriteLine($"[Heartbeat] Stack trace: {ex.StackTrace}");
    // Don't crash - continue loop
}
```

**Action**: Log full exception details, continue running.

### HTTP Timeout Configuration

```csharp
private static readonly HttpClient _http = new() 
{ 
    Timeout = TimeSpan.FromSeconds(10) 
};
```

**Timeout**: 10 seconds per request

**Rationale**: 
- Prevents hanging on slow/dead connections
- Fast enough for good UX
- Allows recovery on next cycle

---

## Implementation Example

### Complete Service Implementation

```csharp
using System;
using System.Net.Http;
using System.Net.Http.Headers;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;

namespace YourApp.Services
{
    public sealed class DeviceHeartbeatService : IDeviceHeartbeatService, IDisposable
    {
        private const string DefaultHeartbeatPath = "device-registration/heartbeat";
        private readonly TimeSpan _interval = TimeSpan.FromMinutes(1);
        
        private CancellationTokenSource? _cts;
        private Task? _task;
        private static readonly HttpClient _http = new() { Timeout = TimeSpan.FromSeconds(10) };

        // Public properties
        public int MessageCount { get; private set; }
        public event Action<int>? MessageCountUpdated;

        /// <summary>
        /// Start the heartbeat monitoring service.
        /// Begins polling immediately, then every 1 minute.
        /// </summary>
        public Task StartAsync(CancellationToken ct = default)
        {
            if (_task != null && !_task.IsCompleted) 
                return Task.CompletedTask;
            
            _cts = CancellationTokenSource.CreateLinkedTokenSource(ct);
            _task = Task.Run(() => LoopAsync(_cts.Token));
            Console.WriteLine("[Heartbeat] Service started, polling every 1 minute");
            return Task.CompletedTask;
        }

        /// <summary>
        /// Background polling loop.
        /// Checks immediately, then every 60 seconds.
        /// </summary>
        private async Task LoopAsync(CancellationToken ct)
        {
            try
            {
                Console.WriteLine("[Heartbeat] Background loop started");
                
                // First check immediately
                await CheckHeartbeatAsync(ct).ConfigureAwait(false);

                // Then check every minute
                while (!ct.IsCancellationRequested)
                {
                    await Task.Delay(_interval, ct).ConfigureAwait(false);
                    Console.WriteLine("[Heartbeat] Checking heartbeat...");
                    await CheckHeartbeatAsync(ct).ConfigureAwait(false);
                }
            }
            catch (OperationCanceledException) 
            { 
                Console.WriteLine("[Heartbeat] Service stopped");
            }
            catch (Exception ex) 
            { 
                Console.WriteLine($"[Heartbeat] Loop error: {ex.Message}");
            }
        }

        /// <summary>
        /// Perform single heartbeat check.
        /// </summary>
        private async Task CheckHeartbeatAsync(CancellationToken ct)
        {
            try
            {
                // Load BASE_URL from environment or config
                string? baseUrl = Environment.GetEnvironmentVariable("BASE_URL");
                
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

                // Build endpoint URL
                var endpoint = CombineUrl(baseUrl!, DefaultHeartbeatPath);
                Console.WriteLine($"[Heartbeat] Endpoint: {endpoint}");
                
                // Load ApiKey from registration.json (read-only)
                var local = await RegistrationLoader.LoadAsync(ct).ConfigureAwait(false);
                if (string.IsNullOrWhiteSpace(local?.ApiKey))
                {
                    Console.WriteLine("[Heartbeat] No API key found, skipping check");
                    return;
                }

                // Create HTTP request
                using var req = new HttpRequestMessage(HttpMethod.Get, endpoint);
                req.Headers.TryAddWithoutValidation("version", "v1");
                req.Headers.Accept.Add(new MediaTypeWithQualityHeaderValue("application/json"));
                req.Headers.TryAddWithoutValidation("X-Api-Key", local.ApiKey);

                // Send request
                Console.WriteLine("[Heartbeat] Sending request...");
                using var res = await _http.SendAsync(req, HttpCompletionOption.ResponseHeadersRead, ct)
                    .ConfigureAwait(false);
                
                var code = (int)res.StatusCode;
                var text = await res.Content.ReadAsStringAsync(ct).ConfigureAwait(false);
                
                Console.WriteLine($"[Heartbeat] Response: HTTP {code}");
                Console.WriteLine($"[Heartbeat] Body: {(string.IsNullOrWhiteSpace(text) ? "(empty)" : text)}");

                // ========== DELETION DETECTION ==========
                
                // Method 1: Check for specific error response structure (primary)
                if (!string.IsNullOrWhiteSpace(text) && 
                    text.Contains("\"message\":null") && 
                    text.Contains("\"innerException\":null") && 
                    text.Contains("\"errors\":null") && 
                    text.Contains("\"stackTrace\":null"))
                {
                    Console.WriteLine("[Heartbeat] Device deleted - cleanup initiated");
                    RegistrationLoader.Delete();
                    BranchInfoLoader.Delete();
                    MessageCount = 0;
                    MessageCountUpdated?.Invoke(MessageCount);
                    return;
                }
                
                // Method 2: Check for HTTP 404/410 status codes (fallback)
                if (code == 404 || code == 410)
                {
                    Console.WriteLine("[Heartbeat] Device not found (404/410) - cleanup initiated");
                    RegistrationLoader.Delete();
                    BranchInfoLoader.Delete();
                    MessageCount = 0;
                    MessageCountUpdated?.Invoke(MessageCount);
                    return;
                }
                
                // Handle authentication errors
                if (code == 401 || code == 403)
                {
                    Console.WriteLine("[Heartbeat] Authentication failed");
                    return;
                }
                
                // Handle non-200 responses
                if (code != 200)
                {
                    Console.WriteLine($"[Heartbeat] Unexpected response code: {code}");
                    return;
                }
                
                // Parse successful response
                if (string.IsNullOrWhiteSpace(text))
                {
                    Console.WriteLine("[Heartbeat] Empty response body");
                    return;
                }

                try
                {
                    using var doc = JsonDocument.Parse(text);
                    
                    // Extract messageCount
                    if (doc.RootElement.TryGetProperty("messageCount", out var countElement) &&
                        countElement.TryGetInt32(out var newCount))
                    {
                        Console.WriteLine($"[Heartbeat] MessageCount: {MessageCount} -> {newCount}");
                        
                        if (newCount != MessageCount)
                        {
                            MessageCount = newCount;
                            MessageCountUpdated?.Invoke(MessageCount);
                        }
                    }
                    else
                    {
                        Console.WriteLine("[Heartbeat] No messageCount in response");
                    }
                }
                catch (JsonException ex)
                { 
                    Console.WriteLine($"[Heartbeat] JSON parse error: {ex.Message}");
                }
            }
            catch (OperationCanceledException) { }
            catch (HttpRequestException ex)
            {
                Console.WriteLine($"[Heartbeat] Network error: {ex.Message}");
            }
            catch (Exception ex) 
            { 
                Console.WriteLine($"[Heartbeat] Error: {ex.Message}");
            }
        }

        /// <summary>
        /// Safely combine base URL and path.
        /// </summary>
        private static string CombineUrl(string baseUrl, string path)
            => baseUrl.TrimEnd('/') + "/" + path.TrimStart('/');

        /// <summary>
        /// Stop the heartbeat service and cleanup resources.
        /// </summary>
        public void Dispose()
        {
            try { _cts?.Cancel(); } catch { }
            _cts?.Dispose();
        }
    }
}
```

---

## Service Interface

### IDeviceHeartbeatService Interface

```csharp
namespace YourApp.Services
{
    /// <summary>
    /// Heartbeat service: monitors backend connectivity and tracks message count.
    /// </summary>
    public interface IDeviceHeartbeatService
    {
        /// <summary>
        /// Latest message count from backend. Default 0 when unknown or device deleted.
        /// </summary>
        int MessageCount { get; }
        
        /// <summary>
        /// Raised when MessageCount changes (including when reset to 0 on deletion).
        /// </summary>
        event Action<int>? MessageCountUpdated;
        
        /// <summary>
        /// Start the heartbeat polling loop (checks every 1 minute).
        /// </summary>
        Task StartAsync(CancellationToken ct = default);
    }
}
```

### Dependency Injection Registration

```csharp
// In Program.cs or Startup.cs
services.AddSingleton<IDeviceHeartbeatService, DeviceHeartbeatService>();
```

### Service Initialization

```csharp
// In App.xaml.cs or Program.cs
public static async Task Main(string[] args)
{
    // ... build application and services ...
    
    // Start heartbeat monitoring after registration
    try
    {
        var heartbeatService = App.Services.GetService<IDeviceHeartbeatService>();
        await heartbeatService.StartAsync(cancellationToken);
        Console.WriteLine("✅ Heartbeat service started");
    }
    catch (Exception ex)
    {
        Console.WriteLine($"⚠️ Heartbeat service failed: {ex.Message}");
    }
    
    // ... run application ...
}
```

---

## Integration Guide

### Step 1: Create Configuration Loaders

You'll need loaders for reading configuration files:

**BaseUrlsLoader.cs**:
```csharp
public static class BaseUrlsLoader
{
    public static async Task<BaseUrlsConfig?> LoadAsync()
    {
        const string path = "/home/unisight/Config/baseUrl.json";
        
        try
        {
            if (!File.Exists(path)) return null;
            
            var json = await File.ReadAllTextAsync(path);
            return JsonSerializer.Deserialize<BaseUrlsConfig>(json, 
                new JsonSerializerOptions { PropertyNameCaseInsensitive = true });
        }
        catch (Exception ex)
        {
            Console.WriteLine($"[BaseUrls] Load error: {ex.Message}");
            return null;
        }
    }
}

public class BaseUrlsConfig
{
    [JsonPropertyName("BASE_URL")]
    public string? BaseUrl { get; set; }
}
```

**RegistrationLoader.cs**:
```csharp
public static class RegistrationLoader
{
    public const string RegistrationPath = "/home/unisight/Config/registration.json";
    
    public static async Task<RegistrationState?> LoadAsync(CancellationToken ct = default)
    {
        try
        {
            if (!File.Exists(RegistrationPath)) return null;
            
            var json = await File.ReadAllTextAsync(RegistrationPath, ct);
            return JsonSerializer.Deserialize<RegistrationState>(json, 
                new JsonSerializerOptions { PropertyNameCaseInsensitive = true });
        }
        catch (Exception ex)
        {
            Console.WriteLine($"[Registration] Load error: {ex.Message}");
            return null;
        }
    }
    
    public static void Delete()
    {
        try 
        { 
            if (File.Exists(RegistrationPath)) 
                File.Delete(RegistrationPath); 
        } 
        catch (Exception ex)
        {
            Console.WriteLine($"[Registration] Delete error: {ex.Message}");
        }
    }
}

public class RegistrationState
{
    [JsonPropertyName("ApiKey")]
    public string? ApiKey { get; set; }
    
    // ... other properties ...
}
```

**BranchInfoLoader.cs**:
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
            Console.WriteLine($"[BranchInfo] Delete error: {ex.Message}");
        }
    }
}
```

### Step 2: Implement Heartbeat Service

Copy the complete `DeviceHeartbeatService` implementation from the [Implementation Example](#implementation-example) section above.

### Step 3: Register Service with DI

```csharp
services.AddSingleton<IDeviceHeartbeatService, DeviceHeartbeatService>();
```

### Step 4: Start Service After Registration

```csharp
// After successful device registration
var heartbeatService = services.GetService<IDeviceHeartbeatService>();
await heartbeatService.StartAsync();
```

### Step 5: Subscribe to MessageCount Updates

```csharp
// In your ViewModel or MainWindow
_heartbeatService.MessageCountUpdated += OnMessageCountChanged;

private void OnMessageCountChanged(int newCount)
{
    // Update UI with new message count
    NotificationBadge.Text = newCount.ToString();
    NotificationBadge.IsVisible = newCount > 0;
    
    // Check for device deletion
    if (newCount == 0 && !File.Exists(RegistrationLoader.RegistrationPath))
    {
        // Device deleted - return to registration screen
        Dispatcher.UIThread.InvokeAsync(() => ShowRegistrationView());
    }
}
```

### Step 6: Handle App Shutdown

```csharp
// Clean shutdown
public override void OnExit(ExitEventArgs e)
{
    var heartbeatService = App.Services.GetService<IDeviceHeartbeatService>();
    if (heartbeatService is IDisposable disposable)
    {
        disposable.Dispose();
    }
    
    base.OnExit(e);
}
```

---

## Best Practices

### 1. Polling Frequency

**Recommendation**: 60 seconds (1 minute)

**Rationale**:
- Fast enough for timely notifications
- Low enough server load (1 request per device per minute)
- Good balance between responsiveness and resource usage
- Acceptable battery impact for mobile devices

**Customization**:
```csharp
// For different requirements:
private readonly TimeSpan _interval = TimeSpan.FromSeconds(30);  // More frequent
private readonly TimeSpan _interval = TimeSpan.FromMinutes(5);   // Less frequent
```

### 2. Error Handling Philosophy

**Don't Crash**: Always catch exceptions and continue running

**Log Everything**: Console logging helps debugging in production

**Retry Automatically**: Next cycle will retry failed requests

**Fail Gracefully**: Network errors shouldn't affect app functionality

### 3. Resource Management

**Single HttpClient**: Reuse one static HttpClient instance
```csharp
private static readonly HttpClient _http = new() { Timeout = TimeSpan.FromSeconds(10) };
```

**Dispose Properly**: Implement IDisposable for cleanup
```csharp
public void Dispose()
{
    try { _cts?.Cancel(); } catch { }
    _cts?.Dispose();
}
```

**ConfigureAwait**: Use `.ConfigureAwait(false)` for async calls
```csharp
await CheckHeartbeatAsync(ct).ConfigureAwait(false);
```

### 4. Read-Only Operations

**Never Modify Config**: Heartbeat only reads registration.json (except on deletion)

**Rationale**:
- Prevents race conditions with registration process
- Clear separation of concerns
- Simpler error handling

**Exception**: Only delete files when device is deleted

### 5. Event-Driven Architecture

**Use Events for UI Updates**:
```csharp
public event Action<int>? MessageCountUpdated;
```

**Benefits**:
- Loose coupling between service and UI
- Easy to add multiple listeners
- Testable without UI

### 6. Comprehensive Logging

**Log Everything Important**:
- Request/response details
- Status codes and body content
- MessageCount changes
- Errors and exceptions
- State transitions

**Format for Clarity**:
```csharp
Console.WriteLine("[Heartbeat] Message");  // Consistent prefix
Console.WriteLine($"[Heartbeat] Variable: {value}");  // Include values
```

### 7. Deletion Detection Best Practices

**Implement Both Methods**: Use both null pattern and status codes

**Check Order**:
1. Check response body for null pattern first (most specific)
2. Then check HTTP status codes (fallback)

**Cleanup Completely**:
```csharp
RegistrationLoader.Delete();      // Delete credentials
BranchInfoLoader.Delete();        // Delete branch info
MessageCount = 0;                 // Reset state
MessageCountUpdated?.Invoke(0);   // Notify listeners
```

**Automatic Recovery**: Return to registration screen automatically

### 8. Backend Recommendations

If you're implementing the backend:

**Use 410 Gone for Deletions**: More semantic than 404
```http
HTTP/1.1 410 Gone
```

**Return Consistent Error Structure**:
```json
{
  "message": null,
  "innerException": null,
  "errors": null,
  "stackTrace": null
}
```

**Include MessageCount in Normal Response**:
```json
{
  "messageCount": 3,
  "status": "active",
  "lastSeen": "2026-01-05T12:34:56Z"
}
```

**Authenticate by API Key**: Use `X-Api-Key` header
```http
X-Api-Key: sk_live_1234567890abcdef
```

### 9. Testing Considerations

**Test Deletion Detection**:
- Mock responses with null pattern
- Mock 404/410 responses
- Verify file deletion
- Verify event firing

**Test Network Failures**:
- Timeout scenarios
- Connection refused
- DNS failure
- Invalid JSON

**Test Message Count Updates**:
- Count increases
- Count decreases
- Count stays same (no event)
- Count resets to 0

### 10. Security Considerations

**Protect API Key**:
- Store in file with restricted permissions
- Never log full API key (use masking)
- Use HTTPS for all requests

**Validate Responses**:
- Check content type
- Validate JSON structure
- Handle unexpected formats

**Timeout Requests**:
```csharp
Timeout = TimeSpan.FromSeconds(10)  // Prevent hanging
```

---

## Summary

The heartbeat monitoring system provides:

### Key Features
- **Continuous monitoring** every 60 seconds
- **Message count tracking** for pending notifications
- **Device deletion detection** via two methods
- **Automatic recovery** to registration screen
- **Event-driven updates** for UI integration
- **Robust error handling** for network issues

### API Details
- **Endpoint**: `GET {BASE_URL}/device-registration/heartbeat`
- **Authentication**: `X-Api-Key` header (from registration.json)
- **Headers**: `version: v1`, `Accept: application/json`
- **Response**: JSON with `messageCount` property

### Deletion Detection
1. **Primary Method**: Specific JSON pattern with four null fields
2. **Fallback Method**: HTTP 404/410 status codes
3. **Action**: Delete local config files, reset state, return to registration

### Implementation Requirements
- Background service running continuously
- 60-second polling interval
- Read-only access to registration.json
- Event system for MessageCount updates
- File deletion capability
- Comprehensive logging

This system ensures devices maintain connectivity with the backend, receive timely notifications, and gracefully handle deletion scenarios with automatic recovery.
