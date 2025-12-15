import { useRef, useEffect, useState, Suspense, lazy } from "react";
// import ForceGraph2D from "react-force-graph-2d";
import { invoke } from "@tauri-apps/api/core";
import { Loader2 } from "lucide-react";
// Type import might fail if the package is weird, so we use any for the ref for now to be safe
// import type { ForceGraphMethods } from "react-force-graph-2d";

// Lazy load the library which might be heavy or problematic with SSR/Vite
const ForceGraph2D = lazy(() => import("react-force-graph-2d"));
// const ForceGraph2D: any = null; // DISABLED FOR DEBUGGING

interface GraphNode {
    id: string;
    label: string;
    weight: number;
    x?: number;
    y?: number;
}

interface GraphLink {
    source: string | GraphNode;
    target: string | GraphNode;
}

interface GraphData {
    nodes: GraphNode[];
    links: GraphLink[];
}

export function GraphView() {
    const fgRef = useRef<any>(null); // Using any to avoid type import issues with lazy load
    const [data, setData] = useState<GraphData>({ nodes: [], links: [] });
    const [isLoading, setIsLoading] = useState(true);

    useEffect(() => {
        // Initial fetch of "The Lobotomy" data (Topology only)
        invoke<GraphData>("rebuild_graph")
            .then((graphData) => {
                setData(graphData);
                setIsLoading(false);
            })
            .catch((err) => {
                console.error("Failed to load graph:", err);
                setIsLoading(false);
            });
    }, []);

    useEffect(() => {
        // Warm-up physics then freeze
        if (fgRef.current && data.nodes.length > 0) {
            fgRef.current.d3Force("charge")?.strength(-100); // Standard repulsion

            // Let physics settle for 2s then freeze to save GPU/CPU
            setTimeout(() => {
                fgRef.current?.pauseAnimation();
            }, 2000);
        }
    }, [data]);

    if (isLoading) {
        return (
            <div className="flex items-center justify-center h-full bg-slate-950 text-orange-500">
                <Loader2 className="w-8 h-8 animate-spin mr-2" />
                <span className="font-mono uppercase tracking-widest">Indexing Neural Net...</span>
            </div>
        );
    }

    return (
        <div className="h-full w-full bg-slate-950 overflow-hidden relative border border-slate-800">
            <div className="absolute top-4 left-4 z-10 bg-slate-900/80 p-2 border border-slate-700 pointer-events-none">
                <span className="text-orange-500 font-mono text-xs"> NODES: {data.nodes.length} </span>
                <span className="text-slate-500 font-mono text-xs ml-2"> LINKS: {data.links.length} </span>
            </div>
            {/* Graph Canvas */}
            <Suspense fallback={
                <div className="flex items-center justify-center h-full text-orange-500 animate-pulse">
                    <Loader2 className="w-8 h-8 animate-spin mr-2" />
                    <span className="font-mono">INITIALIZING PHYSICS ENGINE...</span>
                </div>
            }>
                <ForceGraph2D
                    ref={fgRef}
                    graphData={data}
                    nodeLabel="label"
                    linkColor={() => "#334155"} // Slate-700
                    backgroundColor="#020617" // Slate-950
                    nodeRelSize={6}

                    // Render "Squares" instead of circles (Brutalist)
                    nodeCanvasObject={(node: any, ctx: any, globalScale: any) => {
                        const label = node.label;
                        const fontSize = 12 / globalScale;
                        ctx.font = `${fontSize}px monospace`;

                        ctx.fillStyle = node.weight > 5 ? '#f97316' : '#1e293b';

                        // Square Node
                        const size = 10;
                        ctx.fillRect(node.x - size / 2, node.y - size / 2, size, size);

                        ctx.textAlign = 'center';
                        ctx.textBaseline = 'middle';
                        ctx.fillStyle = node.weight > 5 ? '#000' : '#94a3b8';
                        ctx.fillText(label, node.x, node.y + size + 2);
                    }}

                    // Optimization
                    cooldownTicks={100}
                    onEngineStop={() => {
                        // usage of valid reference
                    }}
                />
            </Suspense>
        </div>
    );
}
