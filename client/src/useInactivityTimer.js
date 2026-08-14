/**
 * useInactivityTimer.js
 * ========================
 *
 * Requirement 2: 60 seconds of inactivity terminates the session and
 * redirects to the home screen. This hook implements the CLIENT-SIDE
 * half of that rule (the server independently enforces the same timeout
 * itself -- see server/app/session_store.py -- so the guarantee doesn't
 * depend on the client behaving well).
 *
 * The timer resets every time resetActivity() is called -- wire that to
 * every real user interaction (typing, sending a message, clicking
 * Hint/Give Up), not to things like the streaming reply arriving, since
 * "inactivity" means the CHILD stopped interacting, not that the
 * assistant stopped talking.
 */

import { useCallback, useEffect, useRef, useState } from "react";

const TIMEOUT_MS = 60_000;
const WARNING_MS = 45_000; // show a "still there?" warning 15s before timeout

export function useInactivityTimer(onTimeout) {
  const [showWarning, setShowWarning] = useState(false);
  const timeoutRef = useRef(null);
  const warningRef = useRef(null);

  const resetActivity = useCallback(() => {
    setShowWarning(false);
    if (timeoutRef.current) clearTimeout(timeoutRef.current);
    if (warningRef.current) clearTimeout(warningRef.current);

    warningRef.current = setTimeout(() => setShowWarning(true), WARNING_MS);
    timeoutRef.current = setTimeout(() => onTimeout(), TIMEOUT_MS);
  }, [onTimeout]);

  useEffect(() => {
    resetActivity();
    return () => {
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
      if (warningRef.current) clearTimeout(warningRef.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return { resetActivity, showWarning };
}
