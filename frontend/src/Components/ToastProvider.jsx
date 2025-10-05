import { createContext, useContext, useRef, useState, useCallback } from "react";

const ToastCtx = createContext({
  show: () => {},
  hide: () => {},
  showError: () => {},
  showSuccess: () => {},
});

export const useToast = () => useContext(ToastCtx);

export default function ToastProvider({ children }) {
  const [toast, setToast] = useState(null); // { text, type }
  const timerRef = useRef(null);

  const hide = useCallback(() => {
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = null;
    setToast(null);
  }, []);

  const show = useCallback((text, opts = {}) => {
    const options = typeof opts === "number" ? { duration: opts } : opts;
    const { type = "info", duration = 3000 } = options;

    hide();
    setToast({ text, type });
    timerRef.current = setTimeout(hide, duration);
  }, [hide]);

  const showError = useCallback((text, duration) => show(text, { type: "error", duration }), [show]);
  const showSuccess = useCallback((text, duration) => show(text, { type: "success", duration }), [show]);

  return (
    <ToastCtx.Provider value={{ show, hide, showError, showSuccess }}>
      {children}
      {toast && (
        <div className={`toast ${toast.type === "error" ? "toast-error" : ""}`} role="status" aria-live="polite">
          {toast.text}
        </div>
      )}
    </ToastCtx.Provider>
  );
}
