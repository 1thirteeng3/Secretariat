console.log("Secretariat: Main entry point loaded");
import React, { Suspense, lazy } from "react";
import ReactDOM from "react-dom/client";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { Loader2 } from "lucide-react";

// Lazy load App to isolate import errors
const App = lazy(() => import("./App"));

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <ErrorBoundary>
      <Suspense fallback={
        <div className="flex h-screen w-full items-center justify-center bg-slate-950 text-orange-500 font-mono">
          <Loader2 className="w-10 h-10 animate-spin mr-3" />
          <span>BOOTING SYSTEM...</span>
        </div>
      }>
        <App />
      </Suspense>
    </ErrorBoundary>
  </React.StrictMode>,
);
