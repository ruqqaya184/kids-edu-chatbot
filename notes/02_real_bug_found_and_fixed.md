# A Real Bug Found During Live Testing: Orphaned Sessions

## What Was Observed

During live end-to-end testing (a headless browser opening the Quick
Fire activity, then clicking Back), the backend's health check showed
2 active sessions while inside the activity (expected: 1), and 1
remaining session after clicking Back (expected: 0) - a real, live-
observed session leak.

## Root Cause

React's StrictMode (enabled by default in development, see main.jsx)
intentionally double-invokes effects on mount specifically to help
surface exactly this kind of bug. ActivityChat.jsx's session-creation
effect called startSession(activity) with no guard against a second
invocation. Because startSession() is asynchronous, the first effect
run's cleanup function captured whatever sessionIdRef.current held AT
CLEANUP TIME - but by the time cleanup ran, the SECOND effect's
startSession() call had already overwritten sessionIdRef.current with a
different session's id. The result: the first session's id was never
correctly targeted for termination, leaving it orphaned server-side even
after the user clicked Back and the (wrong) session id was terminated.

## The Fix

The same pattern used to fix an equivalent bug in Week 2's Day 13
project: a useRef guard (hasStarted) that ensures the session-creation
logic only actually runs once, regardless of how many times StrictMode
invokes the effect:

```jsx
const hasStarted = useRef(false);
useEffect(() => {
  if (hasStarted.current) return;
  hasStarted.current = true;
  // ...the actual session-start logic...
}, [activity]);
```

## Verified After the Fix

The exact same live test was re-run:
- Sessions while inside the activity: 1 (previously 2)
- Sessions after clicking Back: 0 (previously 1)

## The General Lesson

Any "run once per mount" side effect in a React component - creating a
resource, opening a connection, starting a timer with side effects -
needs an explicit guard against StrictMode's intentional double-
invocation in development. Relying on a plain empty dependency array
alone is not sufficient once the effect has an asynchronous body whose
completion order isn't guaranteed relative to its own cleanup function.
