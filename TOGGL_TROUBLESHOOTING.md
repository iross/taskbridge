# Toggl Hook Troubleshooting Guide

## Common Issues and Solutions

### Issue: Tasks won't complete/stop when Toggl API is rate-limited

**Symptoms:**
- `task <id> done` fails or hangs
- Error messages about API limits
- Tasks stuck in started state

**Root Cause:**
The hook was failing during initialization when Toggl API returned HTTP 402 (hourly limit exceeded).

**Solution (FIXED in v2.0):**
The hook now detects rate limits during initialization and continues in "degraded mode":
- Taskwarrior operations work normally
- Toggl integration is temporarily disabled
- No blocking or failures

### Checking Hook Status

```bash
# View recent hook activity
tail -f ~/.task/hooks/toggl-hook.log

# Check for rate limit errors
grep -i "rate limit\|402\|429" ~/.task/hooks/toggl-hook.log

# Test hook manually (should return JSON even when rate-limited)
echo '{"uuid":"test"}' | echo '{"uuid":"test","status":"completed"}' | ~/.task/hooks/on-modify.toggl
```

### Expected Behavior

#### When API is Working:
```
⏱️  Started Toggl timer for ClientName in project 'ProjectName': Task description
⏹️  Stopped Toggl timer in project 'ProjectName': Task description (15m)
```

#### When API is Rate-Limited (Initialization):
```
⚠️  Toggl API rate limited - running without Toggl integration
```

#### When API is Rate-Limited (During Operation):
```
⚠️  Toggl rate limit reached - starting timer skipped (task will continue)
```

### Log Messages Explained

| Message | Meaning | Action Required |
|---------|---------|-----------------|
| `Successfully initialized Toggl API connection` | Hook working normally | None |
| `Toggl API rate limited - running without Toggl integration` | Rate limit during init, hook disabled temporarily | Wait for rate limit to reset |
| `Found client in cache: <name>` | Cache working, no API call made | None |
| `Client not in cache, fetching from API` | Cache miss, making API call | Normal operation |
| `You have hit your hourly limit` | Free plan limit reached | Wait or upgrade plan |

### Cache Management

```bash
# View cache location
ls -lh ~/.task/hooks/.toggl_cache.pkl

# Clear cache to force refresh (if cache seems stale)
rm ~/.task/hooks/.toggl_cache.pkl

# Cache expires automatically after 1 hour
```

### Rate Limit Information

**Toggl Free Plan Limits:**
- Hourly API call limit (varies by plan)
- HTTP 402 when limit exceeded
- Quota resets after the indicated time

**After Optimization:**
- First operation after cache expiry: 4-8 API calls
- Subsequent operations (within 1 hour): 2-3 API calls
- ~70-80% reduction vs. unoptimized version

### Debugging Steps

1. **Check if hook is executable:**
   ```bash
   ls -l ~/.task/hooks/on-modify.toggl
   # Should show: -rwxr-xr-x
   ```

2. **Verify TaskBridge is installed:**
   ```bash
   python3 -c "from taskbridge.toggl_api import TogglAPI; print('OK')"
   ```

3. **Check recent errors:**
   ```bash
   tail -20 ~/.task/hooks/toggl-hook.log | grep ERROR
   ```

4. **Test task operations:**
   ```bash
   # These should ALWAYS work, even when Toggl is rate-limited
   task add "Test task"
   task <id> start
   task <id> stop
   task <id> done
   ```

### Emergency: Disable Hook Temporarily

If you need to completely disable the Toggl hook:

```bash
# Make hook non-executable (taskwarrior will skip it)
chmod -x ~/.task/hooks/on-modify.toggl

# Or rename it
mv ~/.task/hooks/on-modify.toggl ~/.task/hooks/on-modify.toggl.disabled

# Re-enable later
chmod +x ~/.task/hooks/on-modify.toggl
# or
mv ~/.task/hooks/on-modify.toggl.disabled ~/.task/hooks/on-modify.toggl
```

### Verifying the Fix

After updating to v2.0, verify it's working:

1. **Trigger a rate limit** (or wait until you hit one naturally)
2. **Try completing a task:**
   ```bash
   task <id> done
   ```
3. **Expected result:** Task completes successfully, with warning message about Toggl
4. **Check logs:**
   ```bash
   tail -5 ~/.task/hooks/toggl-hook.log
   ```
   Should show: `Toggl API rate limited during initialization - hook will run in degraded mode`

### Support

If issues persist after v2.0 update:
1. Check logs: `~/.task/hooks/toggl-hook.log`
2. Verify hook version includes rate limit handling in `__init__`
3. Test with: `python3 -m py_compile ~/.task/hooks/on-modify.toggl`
4. Open issue with log excerpt
