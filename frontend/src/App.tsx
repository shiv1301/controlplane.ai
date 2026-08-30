import { useEffect, useState } from 'react';
import axios from 'axios';
import { ShieldAlert, ShieldCheck, Activity, Brain, Server, Shield, CheckCircle, MessageSquare, Send } from 'lucide-react';
import { BarChart, Bar, XAxis, Tooltip, ResponsiveContainer } from 'recharts';

const API_BASE = 'http://localhost:8000/api';
const adminKey = import.meta.env.VITE_ADMIN_API_KEY || '<YOUR_ADMIN_API_KEY>';
const userKey = import.meta.env.VITE_API_KEY || '<YOUR_API_KEY>';
const AUTH_HEADER = { headers: { 'Authorization': `Bearer ${adminKey}` } };

export default function App() {
  const [metrics, setMetrics] = useState<any>(null);
  const [auditQueue, setAuditQueue] = useState<any[]>([]);
  const [prompt, setPrompt] = useState("");
  const [response, setResponse] = useState("");
  const [loading, setLoading] = useState(false);
  const [currentLatency, setCurrentLatency] = useState<any>(null);

  const sendPrompt = async () => {
    if (!prompt) return;
    setLoading(true);
    setResponse("");
    setCurrentLatency(null);
    try {
      const res = await fetch('http://localhost:8000/v1/chat/completions', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${userKey}`
        },
        body: JSON.stringify({
          model: "qwen3:1.7b",
          messages: [{ role: "user", content: prompt }],
          stream: true
        })
      });

      if (!res.ok) {
        const err = await res.text();
        throw new Error(err);
      }

      const reader = res.body?.getReader();
      const decoder = new TextDecoder();
      if (reader) {
        let currentResponse = "";
        let buffer = "";
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          
          let eolIndex;
          while ((eolIndex = buffer.indexOf('\n')) >= 0) {
            const line = buffer.slice(0, eolIndex).trim();
            buffer = buffer.slice(eolIndex + 1);
            
            if (line.startsWith('data:')) {
              const payload = line.slice(5).trim();
              if (payload === '[DONE]' || payload === '"[DONE]"') continue;
              try {
                const data = JSON.parse(payload);
                if (data.is_latency_stats) {
                  setCurrentLatency(data);
                  continue;
                }
                const content = data?.message?.content || data?.choices?.[0]?.delta?.content || data?.message?.thinking || "";
                if (content) {
                  currentResponse += content;
                  setResponse(currentResponse);
                }
              } catch (_) {}
            }
          }
        }
      }
    } catch (e: any) {
      setResponse("Error: " + e.message);
    }
    setLoading(false);
    fetchData();
  };

  const fetchData = async () => {
    try {
      const [metricsRes, auditRes] = await Promise.all([
        axios.get(`${API_BASE}/metrics`, AUTH_HEADER),
        axios.get(`${API_BASE}/audit`, AUTH_HEADER)
      ]);
      setMetrics(metricsRes.data);
      setAuditQueue(auditRes.data.queue || []);
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 3000);
    return () => clearInterval(interval);
  }, []);

  const resolveAudit = async (msgId: string, action: string) => {
    try {
      await axios.post(`${API_BASE}/audit/${msgId}/resolve?action=${action}`, {}, AUTH_HEADER);
      fetchData();
    } catch (e) {
      console.error(e);
    }
  };

  if (!metrics) return <div className="p-8 text-white">Loading Dashboard...</div>;

  const verifData = [
    { name: 'SUPPORTED', count: metrics.verification_stats?.SUPPORTED || 0, fill: '#22c55e' },
    { name: 'UNSUPPORTED', count: metrics.verification_stats?.UNSUPPORTED || 0, fill: '#f59e0b' },
    { name: 'CONTRADICTED', count: metrics.verification_stats?.CONTRADICTED || 0, fill: '#ef4444' }
  ];

  const currentRisk = currentLatency?.risk_level || null;

  const riskData = [
    { name: 'LOW', count: currentRisk === 'LOW' ? 1 : 0, fill: '#3b82f6' },
    { name: 'MED', count: currentRisk === 'MEDIUM' ? 1 : 0, fill: '#eab308' },
    { name: 'HIGH', count: currentRisk === 'HIGH' ? 1 : 0, fill: '#f97316' },
    { name: 'CRIT', count: currentRisk === 'CRITICAL' ? 1 : 0, fill: '#ef4444' }
  ];

  return (
    <div className="min-h-screen bg-gray-900 text-gray-100 p-8 font-sans">
      <header className="flex items-center gap-3 mb-8">
        <Shield className="text-blue-500 w-8 h-8" />
        <h1 className="text-3xl font-bold">AI Control Plane Dashboard</h1>
      </header>

      {/* Top Metrics Row */}
      <div className="grid grid-cols-1 md:grid-cols-5 gap-6 mb-8">
        <div className="bg-gray-800 p-6 rounded-xl border border-gray-700 flex flex-col">
          <span className="text-gray-400 text-sm font-medium mb-1 flex items-center gap-2"><Activity size={16}/> Total Requests</span>
          <span className="text-3xl font-bold">{metrics.total_requests}</span>
        </div>
        <div className="bg-gray-800 p-6 rounded-xl border border-gray-700 flex flex-col">
          <span className="text-gray-400 text-sm font-medium mb-1 flex items-center gap-2"><Server size={16}/> Avg Latency</span>
          <span className="text-3xl font-bold">{metrics.average_latency_ms?.toFixed(1) || 0} ms</span>
          <div className="flex flex-col gap-1 mt-2 text-xs text-gray-500">
            <div className="flex justify-between"><span>Preprocessing:</span><span>{metrics.prep_latency_ms?.toFixed(1) || 0} ms</span></div>
            <div className="flex justify-between"><span>Generation:</span><span>{metrics.gen_latency_ms?.toFixed(1) || 0} ms</span></div>
            <div className="flex justify-between"><span>Checks:</span><span>{metrics.verif_latency_ms?.toFixed(1) || 0} ms</span></div>
          </div>
        </div>
        <div className="bg-gray-800 p-6 rounded-xl border border-gray-700 flex flex-col">
          <span className="text-gray-400 text-sm font-medium mb-1 flex items-center gap-2"><Activity size={16}/> Current Latency</span>
          <span className="text-3xl font-bold">{currentLatency?.stats?.total?.toFixed(1) || 0} ms</span>
          <div className="flex flex-col gap-1 mt-2 text-xs text-gray-500">
            <div className="flex justify-between"><span>Preprocessing:</span><span>{currentLatency?.stats?.preprocessing?.toFixed(1) || 0} ms</span></div>
            <div className="flex justify-between"><span>Generation:</span><span>{currentLatency?.stats?.generation?.toFixed(1) || 0} ms</span></div>
            <div className="flex justify-between"><span>Checks:</span><span>{currentLatency?.stats?.verification?.toFixed(1) || 0} ms</span></div>
          </div>
        </div>
        <div className="bg-gray-800 p-6 rounded-xl border border-gray-700 flex flex-col">
          <span className="text-gray-400 text-sm font-medium mb-1 flex items-center gap-2"><Brain size={16}/> Cache Hits</span>
          <span className="text-3xl font-bold text-green-400">{metrics.cache_hits}</span>
        </div>
        <div className="bg-gray-800 p-6 rounded-xl border border-gray-700 flex flex-col">
          <span className="text-gray-400 text-sm font-medium mb-1 flex items-center gap-2"><ShieldAlert size={16}/> Pending Audit</span>
          <span className="text-3xl font-bold text-red-400">{auditQueue.length}</span>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Charts */}
        <div className="bg-gray-800 p-6 rounded-xl border border-gray-700 col-span-1 flex flex-col gap-6">
          <div>
            <h2 className="text-lg font-semibold mb-4 flex items-center gap-2"><ShieldCheck size={18}/> Verification Stats</h2>
            <div className="h-48">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={verifData}>
                  <XAxis dataKey="name" stroke="#9ca3af" fontSize={12} />
                  <Tooltip cursor={{fill: '#374151'}} contentStyle={{backgroundColor: '#1f2937', border: 'none'}} />
                  <Bar dataKey="count" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
          <div>
            <h2 className="text-lg font-semibold mb-4 flex items-center gap-2"><ShieldAlert size={18}/> Current Request Risk</h2>
            <div className="h-48">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={riskData}>
                  <XAxis dataKey="name" stroke="#9ca3af" fontSize={12} />
                  <Tooltip cursor={{fill: '#374151'}} contentStyle={{backgroundColor: '#1f2937', border: 'none'}} />
                  <Bar dataKey="count" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>

        {/* Audit Queue */}
        <div className="bg-gray-800 p-6 rounded-xl border border-gray-700 col-span-2 flex flex-col">
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2"><ShieldAlert size={18}/> HUMAN_REVIEW Audit Queue</h2>
          {auditQueue.length === 0 ? (
            <div className="flex-1 flex flex-col items-center justify-center text-gray-500">
              <CheckCircle size={48} className="mb-3 opacity-50" />
              <p>No items pending review.</p>
            </div>
          ) : (
            <div className="overflow-y-auto flex-1 space-y-4">
              {auditQueue.map(item => (
                <div key={item.message_id} className="bg-gray-700 p-4 rounded-lg flex flex-col">
                  <div className="flex justify-between items-start mb-2">
                    <span className="text-xs font-mono text-gray-400">Request: {item.request_id}</span>
                    <span className="text-xs bg-red-900 text-red-200 px-2 py-1 rounded">Action Required</span>
                  </div>
                  <p className="text-sm text-gray-200 mb-4">{item.payload.text || "Missing text..."}</p>
                  <div className="flex justify-end gap-3">
                    <button onClick={() => resolveAudit(item.message_id, 'REJECT')} className="px-4 py-2 bg-red-600 hover:bg-red-700 rounded text-sm font-semibold transition">Reject</button>
                    <button onClick={() => resolveAudit(item.message_id, 'APPROVE')} className="px-4 py-2 bg-green-600 hover:bg-green-700 rounded text-sm font-semibold transition">Approve</button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
      <div className="mt-8 bg-gray-800 p-6 rounded-xl border border-gray-700">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-lg font-semibold flex items-center gap-2"><MessageSquare size={18}/> API Gateway Playground</h2>
          {currentLatency && (
             <div className="flex gap-4">
                 <span className="text-sm px-3 py-1 bg-gray-700 rounded-full flex items-center gap-2">
                     <span className="text-gray-400">Complexity:</span>
                     <span className="font-mono text-blue-400">{currentLatency.complexity?.toFixed(2) || 'N/A'}</span>
                 </span>
                 <span className="text-sm px-3 py-1 bg-gray-700 rounded-full flex items-center gap-2">
                     <span className="text-gray-400">Risk:</span>
                     <span className={`font-bold ${currentLatency.risk_level === 'CRITICAL' ? 'text-red-500' : currentLatency.risk_level === 'HIGH' ? 'text-orange-400' : currentLatency.risk_level === 'MEDIUM' ? 'text-yellow-400' : 'text-green-400'}`}>{currentLatency.risk_level || 'N/A'}</span>
                 </span>
             </div>
          )}
        </div>
        <div className="flex gap-4">
          <div className="flex-1">
            <textarea 
              className="w-full bg-gray-900 border border-gray-700 rounded-lg p-3 text-gray-200 focus:outline-none focus:border-blue-500 transition h-24"
              placeholder="Enter a prompt to test the Control Plane..."
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
            />
            <button 
              onClick={sendPrompt}
              disabled={loading || !prompt}
              className="mt-3 px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 disabled:cursor-not-allowed rounded flex items-center gap-2 font-semibold transition"
            >
              {loading ? <Activity size={16} className="animate-spin" /> : <Send size={16} />}
              {loading ? 'Sending...' : 'Send Prompt'}
            </button>
          </div>
          <div className="flex-1 bg-gray-900 border border-gray-700 rounded-lg p-4 overflow-y-auto max-h-64 whitespace-pre-wrap font-mono text-sm">
            {response ? response : <span className="text-gray-500">Response will appear here...</span>}
          </div>
        </div>
      </div>
    </div>
  );
}
