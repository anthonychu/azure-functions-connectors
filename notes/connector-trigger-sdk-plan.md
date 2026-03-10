# Plan: `@generic_connection_trigger` Python SDK

## User Experience

```python
import azure.functions as func
from azure_connector_triggers import generic_connection_trigger, register_connector_triggers

app = func.FunctionApp()

@generic_connection_trigger(
    connection_id="%OFFICE365_CONNECTION_ID%",
    trigger_path="/Mail/OnNewEmail",
    trigger_queries={"folderPath": "Inbox"},
)
async def on_new_email(item: dict):
    print(f"New email: {item['subject']}")

@generic_connection_trigger(
    connection_id="%SALESFORCE_CONNECTION_ID%",
    trigger_path="/datasets/default/tables/Lead/onnewitems",
)
def on_new_lead(item: dict):  # sync handlers also supported
    print(f"New lead: {item['Name']}")

# Required — wires up orchestrator, activities, and startup trigger.
# Raises error if decorators exist but this is never called.
register_connector_triggers(app)
```

## Key Problems to Solve

### 1. Deterministic Instance IDs
Each decorated function produces a unique orchestration instance ID based on its
trigger config. This prevents duplicates and enables lifecycle management.

```
instance_id = hash(connection_id + trigger_path + sorted(trigger_queries))
→ "ctp:office365:mail-onnew:a3f8b2c1"
```

### 2. Multi-Instance App Startup (Scale-Out)
When multiple Function App instances start simultaneously, each instance's decorator
will try to start the orchestration. We need idempotent startup.

**Approach: Start-if-not-running with Durable client**

```python
status = await client.get_status(instance_id)
if status is None or status.runtime_status in (OrchestrationStatus.COMPLETED, 
                                                 OrchestrationStatus.TERMINATED,
                                                 OrchestrationStatus.FAILED):
    await client.start_new("GenericPollingOrchestrator", instance_id, input)
elif status.runtime_status == OrchestrationStatus.RUNNING:
    # Already running — no-op
    pass
```

The Durable Task framework handles the race condition — if two instances call
start_new with the same instance_id simultaneously, one succeeds and the other
gets a "conflict" (409). Catch and ignore it.

### 3. Redeployment with Changed Triggers
When the user redeploys with different triggers, we need to:
- Stop orchestrations for triggers that no longer exist
- Start orchestrations for new triggers
- Leave unchanged triggers alone

**Approach: Desired-state reconciliation at app startup**

Each app instance, on startup:

1. **Collect desired state** — scan all `@generic_connection_trigger` decorators
   to build a set of desired instance IDs + configs

2. **Read current state** — query Durable Task for all running instances with
   our prefix ("ctp:*")

3. **Reconcile:**
   - Desired but not running → start
   - Running but not desired → terminate
   - Running and desired, same config → no-op
   - Running and desired, different config → terminate + restart

## Reconciliation Details

```python
async def reconcile(client, registered_triggers):
    desired = {t.instance_id: t for t in registered_triggers}
    running = {i.instance_id: i for i in await client.list_instances(prefix="ctp:")}

    # Start missing
    for iid, trigger in desired.items():
        if iid not in running:
            await safe_start(client, iid, trigger.to_input())
        else:
            instance = running[iid]
            restart, recover_cursor = needs_restart(instance, trigger)
            if restart:
                old_input = instance.input or {}
                cursor = old_input.get("cursor") if recover_cursor else None
                await client.terminate(iid, "Restart required")
                await client.purge_instance_history(iid)
                await safe_start(client, iid, trigger.to_input(cursor=cursor))

    # Terminate orphans
    for iid, instance in running.items():
        if iid not in desired:
            await client.terminate(iid, "Trigger removed in redeployment")
            asyncio.create_task(client.purge_instance_history(iid))

def needs_restart(instance, desired_trigger):
    """Returns (should_restart, should_recover_cursor)."""
    if instance.runtime_status in (FAILED, TERMINATED, COMPLETED):
        return True, True  # restart, recover cursor

    old_input = instance.input or {}
    old_structural = old_input.get("structural_hash")
    old_runtime = old_input.get("runtime_hash")

    if old_structural != desired_trigger.structural_hash:
        return True, False  # structural change — cursor invalid, start fresh

    if old_runtime != desired_trigger.runtime_hash:
        return True, True   # runtime change — cursor still valid, recover it

    return False, False  # no change

async def safe_start(client, iid, config):
    try:
        await client.start_new("GenericPollingOrchestrator", iid, config)
    except Conflict:
        pass  # already running — race condition, safe to ignore
```

### Rolling Deploy Protection

During a rolling deployment, old and new instances may have different package
versions. To prevent thrashing (old worker terminates new orchestration, new
worker terminates old orchestration):

- Reconciliation only **starts** missing orchestrations and **restarts** its own
  failed/changed ones. It does NOT terminate a healthy running orchestration
  just because the runtime hash differs — it only restarts if the instance is
  also assigned to this worker's desired set.
- The blob lease ensures only one worker reconciles at a time.
- In practice, the new deployment replaces all instances quickly. The brief
  overlap window is handled by Durable Task's idempotent start semantics.

### Cursor Recovery on Restart

When an orchestration needs to restart, the reconciler reads the cursor from
the old instance's input before purging — but **only if the structural hash
is unchanged** (same data source). If the structural config changed, the cursor
is invalid and we start fresh.

### Package Versioning

Package version is included in the **runtime hash** (not structural hash). This means
a package upgrade triggers a restart with cursor recovery — no data loss.

```python
PACKAGE_VERSION = importlib.metadata.version("azure-connector-triggers")
# Included in runtime_hash, not structural_hash
```

| Change type | Hash affected | Cursor | Data impact |
|------------|--------------|--------|-------------|
| Package upgrade | Runtime | Recovered | No loss |
| trigger_path changed | Structural | Reset | Fresh start (correct) |
| trigger_queries changed | Structural | Reset | Fresh start (correct) |
| connection_id changed | Structural | Reset | Fresh start (correct) |
| min/max_interval changed | Runtime | Recovered | No loss |
| Handler code changed | Neither (no restart) | Preserved | No loss |

**No error handling needed in the orchestration itself.** Non-deterministic errors
are framework-level and uncatchable. The reconciler handles recovery externally.

### 4. Concurrency Control on Reconciliation
Multiple instances shouldn't all reconcile simultaneously on a deployment.
Only one should do the cleanup.

**Approach: Distributed lock via Durable Entity or blob lease**

Option A — Durable Entity lock:
```python
@entity_function("ReconciliationLock")
def reconciliation_lock(ctx):
    state = ctx.get_state(lambda: {"locked": False, "version": ""})
    op = ctx.operation_name
    if op == "acquire":
        if not state["locked"]:
            state["locked"] = True
            state["version"] = ctx.input
            ctx.set_state(state)
            ctx.set_result(True)
        else:
            ctx.set_result(False)
    elif op == "release":
        state["locked"] = False
        ctx.set_state(state)
        ctx.set_result(True)
```

Option B — Blob lease (simpler):
```python
lease = blob_client.acquire_lease(lease_duration=60)
try:
    await reconcile()
finally:
    lease.release()
```

### 5. Config Change Detection

Split config into **structural hash** (determines what data is polled) and
**runtime hash** (determines if orchestration code needs restart):

```python
# Structural hash — changes mean "different data source, start fresh"
structural_hash = sha256(json.dumps({
    "connection_id": config.connection_id,
    "trigger_path": config.trigger_path,
    "trigger_queries": config.trigger_queries,
}, sort_keys=True))

# Runtime hash — changes mean "same data source, but code/settings changed"
runtime_hash = sha256(json.dumps({
    "package_version": PACKAGE_VERSION,
    "min_interval": config.min_interval,
    "max_interval": config.max_interval,
}, sort_keys=True))
```

The instance ID is derived from the **structural hash** only.
Both hashes are stored in the orchestration input.

Reconciliation logic:

| Structural hash | Runtime hash | Action | Cursor |
|----------------|-------------|--------|--------|
| Same | Same | No-op | Preserved |
| Same | Changed | Terminate + restart | **Recovered** from old input |
| Changed | Any | Terminate + restart | **Reset** (old cursor invalid for new data source) |
| Missing (orphan) | — | Terminate | N/A |

## Package Structure

```
azure_connector_triggers/
├── __init__.py              # exports decorator, register_connector_triggers, types
├── decorator.py             # @generic_connection_trigger + env var resolution
├── registration.py          # register_connector_triggers(app) — wires up Durable functions
├── orchestrator.py          # GenericPollingOrchestrator (eternal, per-item fan-out)
├── activities/
│   ├── poll_trigger.py      # PollTrigger activity (calls dynamicInvoke)
│   └── process_item.py      # ProcessItem activity (calls user handler with single item)
├── reconciler.py            # Startup reconciliation logic + blob lease
├── instance_id.py           # Deterministic ID generation + config hashing
├── env.py                   # Env var resolution (%VAR% and $VAR syntax)
└── models.py                # TriggerConfig, PollResult, TriggerRegistration, etc.
```

## Decorator Implementation

```python
# decorator.py

_registered_triggers: list[TriggerRegistration] = []
_handler_registry: dict[str, Callable] = {}  # instance_id → handler
_registration_done = False

def generic_connection_trigger(
    connection_id: str,
    trigger_path: str,
    trigger_queries: dict | None = None,
    min_interval: int = 2,
    max_interval: int = 300,
):
    def decorator(func):
        config = TriggerConfig(
            connection_id=connection_id,
            trigger_path=trigger_path,
            trigger_queries=trigger_queries or {},
            min_interval=min_interval,
            max_interval=max_interval,
        )
        registration = TriggerRegistration(
            config=config,
            handler=func,
            instance_id=compute_instance_id(config),
        )
        _registered_triggers.append(registration)
        _handler_registry[registration.instance_id] = func
        return func
    return decorator
```

## Registration Safety Check

```python
# registration.py
import atexit

def register_connector_triggers(app):
    global _registration_done
    _registration_done = True
    _register_durable_functions(app)

# At module exit (or app startup), warn if decorators were used without registration
atexit.register(lambda: (
    logging.error(
        "azure_connector_triggers: @generic_connection_trigger decorators found "
        "but register_connector_triggers(app) was never called. "
        "Triggers will NOT fire."
    ) if _registered_triggers and not _registration_done else None
))
```

## Dispatch Mechanism

Per-item dispatch via Durable activity fan-out:

```
poll → 200 (N items) → N x call_activity("ProcessItem", {instance_id, item})
```

The `ProcessItem` activity looks up the handler from a **dict keyed by instance_id**
(not list position). Supports both sync and async handlers.

```python
# Registry: stable mapping from instance_id → handler
_handler_registry: dict[str, Callable] = {}

@activity_function("ProcessItem")
async def process_item(input):
    instance_id = input["instance_id"]
    handler = _handler_registry.get(instance_id)
    if handler is None:
        logging.warning(f"No handler registered for {instance_id}, dropping item")
        return
    if asyncio.iscoroutinefunction(handler):
        await handler(input["item"])
    else:
        handler(input["item"])
```

**Bounded fan-out:** The orchestrator limits concurrent activities per poll cycle.
If a poll returns more items than `max_items_per_poll` (default: 100), the
orchestrator processes them in chunks to avoid overwhelming the task hub.

```python
MAX_ITEMS_PER_POLL = 100

items = poll_result["items"]
for chunk in batched(items, MAX_ITEMS_PER_POLL):
    tasks = [ctx.call_activity("ProcessItem", {"instance_id": iid, "item": item})
             for item in chunk]
    yield ctx.task_all(tasks)
```

## Startup Mechanism: Timer with `runOnStartup` ✅

Use a timer trigger with `run_on_startup=True` to kick off reconciliation.
The schedule itself is just a safety net — `runOnStartup` is what actually fires it.

```python
def register_connector_triggers(app):
    # 1. Register orchestrator + activities
    _register_durable_functions(app)

    # 2. Register startup trigger
    @app.function_name("ConnectorTriggerStartup")
    @app.timer_trigger(
        schedule="0 0 * * * *",    # hourly safety net
        arg_name="timer",
        run_on_startup=True         # fires on every instance startup
    )
    async def startup(timer: func.TimerRequest):
        client = df.DurableOrchestrationClient(...)
        await reconcile(client, _registered_triggers)
```

**Why this works on all plans:**

| Event | Fires? | Result |
|-------|--------|--------|
| First deployment | ✅ `runOnStartup` | Starts all orchestrations |
| Scale-out | ✅ `runOnStartup` | Everything running → no-op |
| Redeployment (same config) | ✅ `runOnStartup` | Everything running → no-op |
| Redeployment (changed) | ✅ `runOnStartup` | Terminate old, start new |
| Scale-to-zero → wake | ✅ `runOnStartup` | Durable resumes from state |
| Orchestration crashes | ✅ hourly safety net | Restarts failed orchestration |
| Works on Consumption? | ✅ | Yes |
| Works locally? | ✅ | Yes |

## Startup Flow

```
App instance starts
  → Module import triggers decorator registration
  → Timer fires (runOnStartup=True)
  → Reconciler runs:
      1. Acquire distributed lock (blob lease)
      2. List desired triggers from _registered_triggers
      3. List running "ctp:*" orchestrations
      4. Reconcile: start / terminate+purge / restart as needed
      5. Release lock
  → Orchestrations are running, polling begins
```

## Lifecycle Diagram

```
First deployment:
  decorators register → reconcile → start orchestrations → polling begins

Scale-out (new instance):
  decorators register → reconcile → all already running → no-op

Redeployment (same triggers):
  decorators register → reconcile → all already running → no-op
  (cursor continues from where it left off)

Redeployment (trigger changed):
  decorators register → reconcile → detect mismatch
  → terminate old → start new (cursor resets)

Redeployment (trigger removed):
  decorators register → reconcile → detect orphan
  → terminate orphan

Scale-to-zero → Scale-up:
  Durable Task persists orchestration state
  → orchestration resumes from last timer/cursor
  → no data loss
```

## Edge Cases

| Scenario | Handling |
|----------|----------|
| Two instances reconcile simultaneously | Blob lease ensures only one reconciles |
| start_new races (same instance ID) | Catch 409 Conflict, treat as success |
| App crashes mid-poll | Durable Task replays; activity is idempotent |
| Connection token expires | dynamicInvoke uses ARM token (managed identity), auto-refreshed |
| Connector API throttled (429) | Activity throws, orchestration retries with backoff (built-in) |
| Connector returns Retry-After header | Orchestrator honors it as minimum wait before next poll |
| Cursor becomes invalid after long outage | Connector returns 200 with full batch; cursor resets naturally |
| Large poll result (1000+ items) | Bounded fan-out: chunked into max_items_per_poll (default 100) |
| Orchestration crashes/fails | Reconciler detects FAILED, recovers cursor, restarts |
| Config changes on redeploy (structural) | Terminate + restart; cursor reset (different data source) |
| Package version changes on redeploy | Terminate + restart; cursor recovered (same data source) |
| Handler code changes, config unchanged | Orchestration keeps running; new code loaded; cursor preserved |
| Rolling deploy (old + new code) | Blob lease prevents thrashing; only one worker reconciles |
| Missing handler during rolling deploy | ProcessItem logs warning + drops item (no infinite retry) |
| Forgot register_connector_triggers(app) | atexit warning logged; loud error at module exit |
| Reconciliation fails (lease timeout, ARM error) | No-op — orchestrations stay as-is; next startup/timer retries |

### Known Limitations

1. **Cursor reset on structural config change** — When trigger path, queries, or
   connection changes, the cursor resets. Items between last poll and restart may
   be missed. This is by design — different config = different data source.

2. **Handlers must be idempotent** — Duplicate item delivery is possible around
   crash/replay/redeployment boundaries. The cursor minimizes this but cannot
   eliminate it entirely.

## Open Questions

> All resolved — decisions locked in below.

### 1. Registration: Explicit `register_connector_triggers(app)` ✅

No blueprint dependency. User must explicitly call registration:

```python
app = func.FunctionApp()
register_connector_triggers(app)
```

This wires up:
- The eternal orchestrator function
- `PollTrigger` activity
- `ProcessItem` activity (per-item dispatch)
- Timer trigger with `run_on_startup=True` that runs reconciliation

### 2. Error Handling: Log and Continue ✅

Start simple:
- If a per-item handler throws, log the error (WARNING level) and continue
  to the next item
- Cursor still advances — no re-processing of the whole batch
- Users add their own try/catch for custom error handling
- Future: opt-in retry policies and dead letter queue via decorator config

### 3. Per-Item Dispatch ✅

Handlers receive a single item, not a batch. Both sync and async handlers supported:

```python
@generic_connection_trigger(...)
async def on_new_email(item: dict):  # async supported
    print(f"New: {item['subject']}")

@generic_connection_trigger(...)
def on_new_lead(item: dict):  # sync also works
    print(f"New: {item['Name']}")
```

Behind the scenes, the orchestrator fans out with bounded concurrency:
```
poll → 200 (N items) → chunks of max_items_per_poll
    → call_activity("ProcessItem", {instance_id, item}) per item
```

Each activity is independent, retriable, and scales out across instances.
Missing handler (e.g., during rolling deploy) → log warning + drop item.

**Handlers must be idempotent.** Duplicates are possible around crash, replay,
and redeployment windows.

### 4. Observability: Python Logging ✅

Start with standard `logging` module:
- `INFO` — poll returned items (count + trigger path)
- `DEBUG` — empty polls, backoff changes
- `WARNING` — handler errors, API throttling
- Application Insights picks this up automatically on Azure Functions
- Future: custom metrics as opt-in

### 5. Config: Decorator Args with Env Var Resolution ✅

Support both Functions convention and shell-style env var syntax:

```python
@generic_connection_trigger(
    connection_id="%OFFICE365_CONNECTION_ID%",  # Functions convention
    trigger_path="/Mail/OnNewEmail",
    trigger_queries={"folderPath": "$INBOX_FOLDER"},  # Shell-style
)
def on_new_email(item: dict):
    ...
```

Resolution rules:
- `%VAR_NAME%` → `os.environ["VAR_NAME"]` (Azure Functions convention)
- `$VAR_NAME` → `os.environ["VAR_NAME"]` (shell-style)
- Anything else → literal value
- Resolved at startup (during reconciliation), not at import time
- Missing env var → raise clear error at startup
- **Applies to string values only** — query keys like `$filter`, `$select`,
  `$orderby` are NOT expanded (they start with `$` but contain non-alpha chars
  after the `$`). Resolution rule: `$` followed by `[A-Z_][A-Z0-9_]*` only.
