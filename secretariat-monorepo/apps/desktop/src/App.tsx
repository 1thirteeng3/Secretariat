import { useState } from "react";
import "./App.css";
import { Mic, MessageSquare, Check, X, Edit, Calendar, Search, Brain, Archive } from "lucide-react";
import { GraphView } from "./components/GraphView";
import { invoke } from "@tauri-apps/api/core";

type View = "INBOX" | "NOTES" | "AGENDA" | "CHAT";

interface InboxItem {
  id: string;
  timestamp: string;
  source: "Mobile" | "Desktop";
  type: "AUDIO" | "TEXT";
  original: string;
  aiSuggestion: {
    title: string;
    tags: string[];
    body: string;
  };
}

const MOCK_INBOX: InboxItem[] = [
  {
    id: "1",
    timestamp: "10:42 AM",
    source: "Mobile",
    type: "AUDIO",
    original: "Ideia para o app, fazer o botão ser laranja",
    aiSuggestion: {
      title: "Sugestão de UI - Cor do Botão",
      tags: ["#ux", "#design"],
      body: "Sugere alterar a cor primária para laranja.",
    },
  },
  {
    id: "2",
    timestamp: "11:00 AM",
    source: "Mobile",
    type: "TEXT",
    original: "Reunião com o time de design hoje às 14h para revisar o fluxo de login",
    aiSuggestion: {
      title: "Reunião Design: Login Flow",
      tags: ["#meeting", "#work"],
      body: "Evento sugerido: Hoje 14:00 - 15:00"
    }
  }
];

import { ThemeProvider } from "./context/ThemeContext";
import { BreakerBox } from "./components/BreakerBox";

function AppContent() {
  const [activeView, setActiveView] = useState<View>("INBOX");

  const handleApprove = async (item: InboxItem) => {
    try {
      const fileName = await invoke("create_note", {
        title: item.aiSuggestion.title,
        content: `${item.aiSuggestion.body}\n\nRunning log:\n- Source: ${item.source}\n- Original: ${item.original}`,
        tags: item.aiSuggestion.tags
      });
      console.log(`Note created: ${fileName}`);
      // Remove from UI (Optimistic update) or refetch
      alert(`Note created successfully: ${fileName}`);
    } catch (error) {
      console.error("Failed to create note:", error);
      alert(`Failed to save note: ${error}`);
    }
  };


  return (
    <div className="flex h-screen w-full bg-slate-950 text-slate-200 relative">
      <BreakerBox />

      {/* Sidebar */}
      <aside className="w-16 md:w-64 border-r border-slate-800 flex flex-col p-4 space-y-4">
        <div className="flex items-center space-x-2 text-orange-500 font-bold text-xl mb-6">
          <Brain className="w-8 h-8" />
          <span className="hidden md:block">Secretariat</span>
        </div>

        <nav className="space-y-2">
          {[
            { id: "INBOX", icon: Archive, label: "Inbox" },
            { id: "NOTES", icon: Search, label: "Search & Graph" },
            { id: "CHAT", icon: MessageSquare, label: "Chat with Vault" },
            { id: "AGENDA", icon: Calendar, label: "Agenda" },
          ].map(item => (
            <button
              key={item.id}
              onClick={() => setActiveView(item.id as View)}
              className={`flex items-center space-x-3 w-full p-2 border border-transparent hover:border-slate-800 transition-colors ${activeView === item.id ? "bg-orange-500/10 text-orange-500 border-orange-500/50" : "hover:bg-slate-900"
                }`}
            >
              <item.icon className="w-5 h-5" />
              <span className="hidden md:block">{item.label}</span>
            </button>
          ))}
        </nav>
      </aside>

      {/* Main Content */}
      <main className="flex-1 overflow-auto p-8">
        <header className="mb-8 border-b border-slate-800 pb-4 flex justify-between items-center">
          <h1 className="text-3xl font-light tracking-tight text-white">
            {activeView === "INBOX" && "Incoming Thoughts (Inbox)"}
            {activeView === "NOTES" && "Knowledge Graph"}
            {activeView === "CHAT" && "Consultant Mode"}
            {activeView === "AGENDA" && "Timeline"}
          </h1>
          {activeView === "INBOX" && (
            <div />
          )}
          {activeView === "NOTES" && (
            <button
              onClick={async () => {
                try {
                  // @ts-ignore
                  const res = await invoke("sync_vault");
                  alert(res);
                } catch (e) {
                  alert("Sync Error: " + e);
                }
              }}
              className="bg-green-600 text-white px-3 py-1 rounded text-xs uppercase font-bold hover:bg-green-500"
            >
              Sync Now
            </button>
          )}
        </header>

        {activeView === "INBOX" && (
          <div className="space-y-6 max-w-3xl mx-auto">
            {MOCK_INBOX.map((item) => (
              <div key={item.id} className="bg-slate-950 border border-slate-800 shadow-sm hover:shadow-md transition-shadow">
                {/* Header */}
                <div className="bg-slate-900/50 p-3 border-b border-slate-800 flex items-center justify-between text-xs text-slate-500 uppercase tracking-widest font-mono">
                  <div className="flex items-center space-x-2">
                    {item.type === "AUDIO" ? <Mic className="w-4 h-4" /> : <MessageSquare className="w-4 h-4" />}
                    <span>{item.timestamp} • via {item.source}</span>
                  </div>
                  <span className="bg-slate-800 px-2 py-0.5 text-slate-400 border border-slate-700">Processing</span>
                </div>

                <div className="p-6 grid gap-6">
                  {/* Original */}
                  <div className="opacity-70 border-l-2 border-slate-700 pl-4 py-1 italic">
                    "{item.original}"
                  </div>

                  {/* Divider */}
                  <div className="h-px bg-slate-800" />

                  {/* AI Suggestion */}
                  <div className="space-y-2">
                    <div className="flex items-center space-x-2">
                      <span className="text-orange-500 font-bold text-xs uppercase px-1.5 py-0.5 border border-orange-500/50">AI Suggestion</span>
                      <h3 className="font-semibold text-white">{item.aiSuggestion.title}</h3>
                    </div>
                    <div className="flex items-center space-x-2">
                      {item.aiSuggestion.tags.map(tag => (
                        <span key={tag} className="text-xs text-blue-400 bg-blue-400/10 px-2 py-0.5 border border-blue-400/20">{tag}</span>
                      ))}
                    </div>
                    <p className="text-slate-300">{item.aiSuggestion.body}</p>
                  </div>
                </div>

                {/* Actions */}
                <div className="bg-slate-950 p-3 flex justify-end space-x-2 border-t border-slate-800">
                  <button className="flex items-center space-x-1 px-4 py-2 text-slate-400 hover:text-red-400 hover:bg-red-400/10 transition-colors border-r border-slate-800">
                    <X className="w-4 h-4" />
                    <span>Reject</span>
                  </button>
                  <button className="flex items-center space-x-1 px-4 py-2 text-slate-400 hover:text-white hover:bg-slate-800 transition-colors">
                    <Edit className="w-4 h-4" />
                    <span>Edit</span>
                  </button>
                  <button
                    onClick={() => handleApprove(item)}
                    className="flex items-center space-x-1 px-6 py-2 bg-orange-600 hover:bg-orange-500 text-white shadow-lg shadow-orange-900/20 transition-all transform active:scale-95 border border-orange-400">
                    <Check className="w-4 h-4" />
                    <span>Approve</span>
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}

        {activeView === "NOTES" && (
          <div className="h-[calc(100vh-120px)] border-2 border-slate-800 overflow-hidden">
            <GraphView />
          </div>
        )}

      </main>
    </div>
  );
}

export default function App() {
  return (
    <ThemeProvider>
      <AppContent />
    </ThemeProvider>
  );
}
