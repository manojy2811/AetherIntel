import { useState, useEffect, useRef } from 'react';
import { 
  Play, Check, X, RefreshCw, Layers, 
  Terminal, FileText, BarChart3, Activity, Sparkles, Rewind
} from 'lucide-react';
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid, Legend } from 'recharts';

interface LogEntry {
  agent: string;
  status: string;
  timestamp: string;
}

interface HistoryItem {
  checkpoint_id: string;
  values: {
    research_query: string;
    current_status: string;
    report_markdown: string;
    feedback?: string;
  };
  next: string[];
}

export default function App() {
  // Input Query state
  const [query, setQuery] = useState('AAPL financial performance analysis');
  const [threadId] = useState(() => `session_${Math.random().toString(36).substring(7)}`);
  
  // Execution status
  const [isRunning, setIsRunning] = useState(false);
  const [currentNode, setCurrentNode] = useState<string | null>(null);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [tokens, setTokens] = useState('');
  const [reportMarkdown, setReportMarkdown] = useState('');
  
  // Human approval states
  const [isInterrupted, setIsInterrupted] = useState(false);
  const [criticFeedback, setCriticFeedback] = useState('');
  const [humanFeedback, setHumanFeedback] = useState('');
  
  // History & Time Travel States
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [historySliderIndex, setHistorySliderIndex] = useState(-1);
  const [selectedTab, setSelectedTab] = useState<'report' | 'charts' | 'history'>('report');

  const logsEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs, tokens]);

  // Fetch thread history
  const fetchHistory = async () => {
    try {
      const response = await fetch(`http://localhost:8000/api/v1/research/history/${threadId}`);
      if (response.ok) {
        const data = await response.json();
        const items = data.history || [];
        setHistory(items);
        if (items.length > 0 && historySliderIndex === -1) {
          setHistorySliderIndex(items.length - 1);
        }
      }
    } catch (err) {
      console.error('Failed to fetch history:', err);
    }
  };

  // Start / Resume Research Stream
  const handleStartResearch = async () => {
    if (!query.trim()) return;
    setIsRunning(true);
    setTokens('');
    setIsInterrupted(false);
    
    // Clear logs if starting a brand new run
    if (history.length === 0) {
      setLogs([]);
    }

    try {
      const response = await fetch('http://localhost:8000/api/v1/research/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          research_query: query,
          thread_id: threadId
        })
      });

      if (!response.body) return;
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value);
        const lines = buffer.split('\n');
        
        // Save the last partial line back to buffer
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;
          const dataStr = line.replace('data: ', '').trim();
          if (!dataStr) continue;

          try {
            const data = JSON.parse(dataStr);
            
            // Check SSE event type from the line before
            // We can detect which event fired based on fields
            if (data.token) {
              setTokens(prev => prev + data.token);
            } else if (data.agent && data.status) {
              // agent_start event
              setCurrentNode(data.agent);
              setLogs(prev => [...prev, {
                agent: data.agent,
                status: data.status,
                timestamp: new Date().toLocaleTimeString()
              }]);
            } else if (data.tool) {
              // tool_call event
              setLogs(prev => [...prev, {
                agent: 'tool',
                status: `Invoking tool [${data.tool}] with input: ${JSON.stringify(data.input)}`,
                timestamp: new Date().toLocaleTimeString()
              }]);
            } else if (data.next_nodes) {
              // graph_interrupt event
              setIsInterrupted(true);
              setCurrentNode(null);
              setIsRunning(false);
              setReportMarkdown(data.values?.report_markdown || '');
              setCriticFeedback(data.values?.feedback || 'Awaiting human approval...');
              setLogs(prev => [...prev, {
                agent: 'system',
                status: '⚠️ Workflow interrupted. Awaiting operator validation.',
                timestamp: new Date().toLocaleTimeString()
              }]);
              await fetchHistory();
            } else if (data.report_markdown) {
              // graph_end event
              setReportMarkdown(data.report_markdown);
              setCurrentNode(null);
              setIsRunning(false);
              setLogs(prev => [...prev, {
                agent: 'system',
                status: '✅ Workflow execution completed successfully.',
                timestamp: new Date().toLocaleTimeString()
              }]);
              await fetchHistory();
            }
          } catch (e) {
            console.error('Error parsing SSE chunk:', e);
          }
        }
      }
    } catch (err) {
      console.error('Streaming error:', err);
      setIsRunning(false);
    }
  };

  // Submit Human Approval Decision
  const handleApproval = async (approved: boolean) => {
    try {
      const response = await fetch('http://localhost:8000/api/v1/research/approve', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          thread_id: threadId,
          approved,
          feedback: approved ? undefined : humanFeedback
        })
      });

      if (response.ok) {
        setIsInterrupted(false);
        setHumanFeedback('');
        // Immediately resume stream execution
        handleStartResearch();
      }
    } catch (err) {
      console.error('Failed to submit approval:', err);
    }
  };

  // Setup mock chart data for visualization demonstration
  const chartData = [
    { name: 'AAPL', Revenue: 385.7, NetIncome: 97.0 },
    { name: 'MSFT', Revenue: 211.9, NetIncome: 72.4 },
    { name: 'GOOGL', Revenue: 307.4, NetIncome: 73.8 },
    { name: 'AMZN', Revenue: 574.8, NetIncome: 30.4 },
    { name: 'TSLA', Revenue: 96.8, NetIncome: 15.0 },
  ];

  // Load from history snapshot (time travel)
  const loadHistorySnapshot = (index: number) => {
    setHistorySliderIndex(index);
    const snapshot = history[index];
    if (snapshot) {
      setReportMarkdown(snapshot.values.report_markdown || '');
      setQuery(snapshot.values.research_query || '');
    }
  };

  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col font-sans">
      {/* Premium Header */}
      <header className="border-b border-zinc-800 bg-zinc-950 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 rounded-xl bg-gradient-to-tr from-blue-600 to-violet-600 flex items-center justify-center shadow-lg shadow-blue-500/20">
            <Sparkles className="h-5 w-5 text-white" />
          </div>
          <div>
            <h1 className="font-bold text-lg tracking-wide bg-gradient-to-r from-white via-zinc-200 to-zinc-400 bg-clip-text text-transparent">
              AetherIntel
            </h1>
            <p className="text-xs text-muted">Enterprise Cognitive Research Engine</p>
          </div>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-zinc-900 border border-zinc-800 text-xs text-zinc-300">
            <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse"></span>
            Agentic Swarm Live
          </div>
          <div className="text-xs text-muted">
            Session: <span className="font-mono text-zinc-300">{threadId}</span>
          </div>
        </div>
      </header>

      {/* Main Layout Grid */}
      <main className="flex-1 grid grid-cols-1 lg:grid-cols-12 overflow-hidden">
        
        {/* Left Control Panel: Graph, Query Inputs & Logs */}
        <section className="lg:col-span-5 border-r border-zinc-800 bg-zinc-950 flex flex-col p-6 overflow-y-auto gap-6">
          
          {/* Query Settings Input */}
          <div className="bg-zinc-900/40 border border-zinc-800/80 rounded-xl p-5 flex flex-col gap-4">
            <h2 className="text-sm font-semibold flex items-center gap-2 text-zinc-200">
              <Activity className="h-4 w-4 text-blue-500" />
              Intelligence Parameter
            </h2>
            <div className="flex flex-col gap-2">
              <label className="text-xs text-muted">Cognitive Search Query</label>
              <textarea 
                className="w-full bg-zinc-950 border border-zinc-850 rounded-lg p-3 text-sm focus:outline-none focus:border-blue-600 resize-none h-20 text-zinc-100"
                value={query}
                onChange={e => setQuery(e.target.value)}
                placeholder="Enter search topics..."
                disabled={isRunning}
              />
            </div>
            <button 
              onClick={handleStartResearch}
              disabled={isRunning || !query.trim()}
              className="w-full h-11 bg-gradient-to-r from-blue-600 to-violet-600 hover:from-blue-700 hover:to-violet-700 text-white rounded-lg font-medium text-sm flex items-center justify-center gap-2 disabled:opacity-40 transition-all shadow-md shadow-blue-600/10"
            >
              {isRunning ? (
                <>
                  <RefreshCw className="h-4 w-4 animate-spin" />
                  Running Cognitive Graph...
                </>
              ) : (
                <>
                  <Play className="h-4 w-4" />
                  Initiate Research Swarm
                </>
              )}
            </button>
          </div>

          {/* Real-time Dynamic Graph Pathway Visualization */}
          <div className="bg-zinc-900/40 border border-zinc-800/80 rounded-xl p-5 flex flex-col gap-4">
            <h2 className="text-sm font-semibold flex items-center gap-2 text-zinc-200">
              <Layers className="h-4 w-4 text-violet-500" />
              Dynamic Execution Path
            </h2>
            
            {/* SVG Interactive Topology */}
            <div className="relative border border-zinc-800 bg-zinc-950 rounded-lg h-44 flex items-center justify-center overflow-hidden">
              <svg className="w-full h-full p-4" viewBox="0 0 400 180">
                {/* Supervisor Node (Center) */}
                <g transform="translate(200, 90)">
                  <circle r="26" fill={currentNode === 'supervisor' ? '#3b82f6' : '#18181b'} stroke={currentNode === 'supervisor' ? '#60a5fa' : '#3f3f46'} strokeWidth="2" className={currentNode === 'supervisor' ? 'animate-pulse' : ''} />
                  <text fill="#fafafa" y="4" textAnchor="middle" fontSize="9" fontWeight="bold">Supervisor</text>
                </g>

                {/* Researcher Node (Left) */}
                <g transform="translate(60, 45)">
                  <circle r="24" fill={currentNode === 'researcher' ? '#8b5cf6' : '#18181b'} stroke={currentNode === 'researcher' ? '#a78bfa' : '#3f3f46'} strokeWidth="1.5" className={currentNode === 'researcher' ? 'animate-pulse' : ''} />
                  <text fill="#fafafa" y="4" textAnchor="middle" fontSize="8">Researcher</text>
                </g>

                {/* Data Analyst Node (Right) */}
                <g transform="translate(340, 45)">
                  <circle r="24" fill={currentNode === 'analyst' ? '#ec4899' : '#18181b'} stroke={currentNode === 'analyst' ? '#f472b6' : '#3f3f46'} strokeWidth="1.5" className={currentNode === 'analyst' ? 'animate-pulse' : ''} />
                  <text fill="#fafafa" y="4" textAnchor="middle" fontSize="8">Analyst</text>
                </g>

                {/* Critic Node (Bottom) */}
                <g transform="translate(200, 155)">
                  <circle r="24" fill={currentNode === 'critic' ? '#10b981' : '#18181b'} stroke={currentNode === 'critic' ? '#34d399' : '#3f3f46'} strokeWidth="1.5" className={currentNode === 'critic' ? 'animate-pulse' : ''} />
                  <text fill="#fafafa" y="4" textAnchor="middle" fontSize="8">Critic</text>
                </g>

                {/* Connecting Paths */}
                <line x1="84" y1="55" x2="176" y2="80" stroke="#3f3f46" strokeWidth="1" strokeDasharray="3,3" />
                <line x1="316" y1="55" x2="224" y2="80" stroke="#3f3f46" strokeWidth="1" strokeDasharray="3,3" />
                <line x1="200" y1="116" x2="200" y2="131" stroke="#3f3f46" strokeWidth="1" strokeDasharray="3,3" />
              </svg>

              <div className="absolute bottom-2 left-2 flex items-center gap-1.5 text-[10px] text-muted">
                <span className="inline-block w-2 h-2 rounded-full bg-blue-500"></span> Active Working Node
              </div>
            </div>
          </div>

          {/* Terminal Logs & Stream Console */}
          <div className="flex-1 flex flex-col bg-zinc-950 border border-zinc-800 rounded-xl overflow-hidden min-h-[220px]">
            <div className="bg-zinc-900 px-4 py-2 border-b border-zinc-800 flex items-center justify-between">
              <div className="flex items-center gap-2 text-xs font-semibold text-zinc-300">
                <Terminal className="h-3.5 w-3.5 text-blue-500" />
                Execution Timeline
              </div>
            </div>
            <div className="flex-1 p-4 font-mono text-[11px] overflow-y-auto bg-black flex flex-col gap-2.5 max-h-[300px]">
              {logs.length === 0 && !tokens && (
                <div className="text-zinc-600 italic">Initiate search to view logs.</div>
              )}
              {logs.map((log, index) => (
                <div key={index} className="flex gap-2">
                  <span className="text-zinc-500">[{log.timestamp}]</span>
                  <span className="text-blue-400 uppercase font-semibold">{log.agent}:</span>
                  <span className="text-zinc-300">{log.status}</span>
                </div>
              ))}
              {tokens && (
                <div className="flex gap-2">
                  <span className="text-zinc-500">[{new Date().toLocaleTimeString()}]</span>
                  <span className="text-purple-400 uppercase font-semibold">stream:</span>
                  <span className="text-zinc-200">{tokens}</span>
                </div>
              )}
              <div ref={logsEndRef} />
            </div>
          </div>
        </section>

        {/* Right Dashboard Workspace: Report Output, Charts & Human Gate */}
        <section className="lg:col-span-7 flex flex-col overflow-y-auto bg-zinc-950/60 p-6 gap-6">
          
          {/* Navigation Tabs */}
          <div className="flex border-b border-zinc-800 gap-6">
            <button 
              onClick={() => setSelectedTab('report')}
              className={`pb-3 font-semibold text-sm flex items-center gap-2 border-b-2 transition-all ${selectedTab === 'report' ? 'border-blue-600 text-white' : 'border-transparent text-muted'}`}
            >
              <FileText className="h-4 w-4" />
              Executive Summary
            </button>
            <button 
              onClick={() => setSelectedTab('charts')}
              className={`pb-3 font-semibold text-sm flex items-center gap-2 border-b-2 transition-all ${selectedTab === 'charts' ? 'border-blue-600 text-white' : 'border-transparent text-muted'}`}
            >
              <BarChart3 className="h-4 w-4" />
              Financial Dashboard
            </button>
            <button 
              onClick={() => setSelectedTab('history')}
              className={`pb-3 font-semibold text-sm flex items-center gap-2 border-b-2 transition-all ${selectedTab === 'history' ? 'border-blue-600 text-white' : 'border-transparent text-muted'}`}
            >
              <Rewind className="h-4 w-4" />
              Checkpoint History
            </button>
          </div>

          {/* Interactive Panels */}
          <div className="flex-1 flex flex-col gap-6">
            
            {/* 1. Report Reader Panel */}
            {selectedTab === 'report' && (
              <div className="flex-1 bg-zinc-900/30 border border-zinc-800 rounded-xl p-6 min-h-[300px] prose prose-invert max-w-none text-zinc-300">
                {reportMarkdown ? (
                  <div className="whitespace-pre-line">
                    {reportMarkdown}
                  </div>
                ) : (
                  <div className="flex flex-col items-center justify-center h-full text-zinc-500 py-12">
                    <FileText className="h-10 w-10 mb-2 opacity-40" />
                    <p className="text-sm">Initiate the workflow to synthesize the Markdown report.</p>
                  </div>
                )}
              </div>
            )}

            {/* 2. Charts Visualizations Panel */}
            {selectedTab === 'charts' && (
              <div className="flex-1 bg-zinc-900/30 border border-zinc-800 rounded-xl p-6 flex flex-col gap-6 min-h-[300px]">
                <h3 className="text-sm font-semibold text-zinc-200">Company Revenue & Net Income (Billions)</h3>
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={chartData}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
                      <XAxis dataKey="name" stroke="#71717a" />
                      <YAxis stroke="#71717a" />
                      <Tooltip contentStyle={{ backgroundColor: '#18181b', borderColor: '#27272a' }} />
                      <Legend />
                      <Bar dataKey="Revenue" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                      <Bar dataKey="NetIncome" fill="#a78bfa" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            )}

            {/* 3. History Time-Travel Checkpoint Slider */}
            {selectedTab === 'history' && (
              <div className="flex-1 bg-zinc-900/30 border border-zinc-800 rounded-xl p-6 flex flex-col gap-6 min-h-[300px]">
                <div className="flex flex-col gap-2">
                  <h3 className="text-sm font-semibold text-zinc-200">Time-Travel Checkpoints</h3>
                  <p className="text-xs text-muted">Slide or click through historical agent states to restore previous snapshots.</p>
                </div>
                {history.length > 0 ? (
                  <div className="flex flex-col gap-6">
                    <div className="flex items-center gap-4">
                      <input 
                        type="range" 
                        min="0" 
                        max={history.length - 1} 
                        value={historySliderIndex} 
                        onChange={e => loadHistorySnapshot(parseInt(e.target.value))}
                        className="flex-1 accent-blue-600 bg-zinc-800 rounded-lg h-2"
                      />
                      <span className="text-xs font-mono text-zinc-300">
                        {historySliderIndex + 1} / {history.length} Checkpoints
                      </span>
                    </div>
                    <div className="border border-zinc-800 rounded-lg p-4 bg-zinc-950/60 flex flex-col gap-3">
                      <div>
                        <div className="text-[10px] text-muted">CHECKPOINT ID</div>
                        <div className="text-xs font-mono text-zinc-300">{history[historySliderIndex]?.checkpoint_id || 'N/A'}</div>
                      </div>
                      <div>
                        <div className="text-[10px] text-muted">STATUS HISTORY SUMMARY</div>
                        <div className="text-xs text-zinc-300">
                          {history[historySliderIndex]?.values.current_status || 'No status message.'}
                        </div>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="text-center text-xs text-zinc-500 py-12">
                    No checkpoints captured yet. Perform a search to record snapshots.
                  </div>
                )}
              </div>
            )}

            {/* Human Gate Actions Dashboard (Appears on Interrupt) */}
            {isInterrupted && (
              <div className="border-2 border-amber-600/40 bg-amber-950/20 rounded-xl p-5 flex flex-col gap-4 animate-in fade-in duration-300">
                <div className="flex items-center gap-2">
                  <span className="h-2 w-2 rounded-full bg-amber-500 animate-pulse"></span>
                  <h3 className="font-semibold text-sm text-amber-500">Human Approval Decision Gate</h3>
                </div>
                
                <div className="border border-amber-800/40 bg-zinc-950/60 p-4 rounded-lg flex flex-col gap-2">
                  <div className="text-[10px] text-amber-400 font-semibold uppercase tracking-wider">Critic Evaluation Output:</div>
                  <p className="text-xs text-zinc-300">{criticFeedback}</p>
                </div>

                <div className="flex flex-col gap-2">
                  <label className="text-xs text-zinc-400">Directional Operator Feedback (if requesting revisions)</label>
                  <textarea 
                    className="w-full bg-zinc-950 border border-zinc-800 rounded-lg p-3 text-xs focus:outline-none focus:border-amber-600 resize-none h-16 text-zinc-100"
                    placeholder="Enter instructions for agent swarm (e.g. Focus on competitor BYD revenue)..."
                    value={humanFeedback}
                    onChange={e => setHumanFeedback(e.target.value)}
                  />
                </div>

                <div className="flex gap-4">
                  <button 
                    onClick={() => handleApproval(true)}
                    className="flex-1 h-10 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg font-medium text-xs flex items-center justify-center gap-2 transition-all shadow-md shadow-emerald-600/10"
                  >
                    <Check className="h-4 w-4" />
                    Approve and Publish
                  </button>
                  <button 
                    onClick={() => handleApproval(false)}
                    className="flex-1 h-10 bg-rose-600 hover:bg-rose-700 text-white rounded-lg font-medium text-xs flex items-center justify-center gap-2 transition-all shadow-md shadow-rose-600/10"
                  >
                    <X className="h-4 w-4" />
                    Reject & Request Revisions
                  </button>
                </div>
              </div>
            )}

          </div>
        </section>

      </main>
    </div>
  );
}
