import { Component, ErrorInfo, ReactNode } from "react";

interface Props {
    children?: ReactNode;
}

interface State {
    hasError: boolean;
    error: Error | null;
    errorInfo: ErrorInfo | null;
}

export class ErrorBoundary extends Component<Props, State> {
    public state: State = {
        hasError: false,
        error: null,
        errorInfo: null,
    };

    public static getDerivedStateFromError(error: Error): State {
        return { hasError: true, error, errorInfo: null };
    }

    public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
        console.error("Uncaught error:", error, errorInfo);
        this.setState({ error, errorInfo });
    }

    public render() {
        if (this.state.hasError) {
            return (
                <div className="h-screen w-full bg-red-950 text-white p-8 overflow-auto font-mono">
                    <h1 className="text-3xl font-bold mb-4">System Critical Failure</h1>
                    <div className="bg-black/50 p-4 rounded border border-red-500 mb-4">
                        <h2 className="text-xl text-red-500 mb-2">Error:</h2>
                        <pre className="whitespace-pre-wrap text-sm text-red-200">
                            {this.state.error?.toString()}
                        </pre>
                    </div>
                    <div className="bg-black/50 p-4 rounded border border-red-500">
                        <h2 className="text-xl text-red-500 mb-2">Stack Trace:</h2>
                        <pre className="whitespace-pre-wrap text-xs text-slate-400">
                            {this.state.errorInfo?.componentStack || "No stack trace available"}
                        </pre>
                    </div>
                </div>
            );
        }

        return this.props.children;
    }
}
