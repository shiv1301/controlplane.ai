import { useEffect, useState } from 'react';
import { Activity, Clock, Database, Layers } from 'lucide-react';
import { getMetrics, getCacheStats, getModels } from '../services/api';

const Dashboard = () => {
  const [metrics, setMetrics] = useState({ total_requests: 0, average_latency_ms: 0 });
  const [cache, setCache] = useState({ hit_rate: 0 });
  const [models, setModels] = useState({ models: [] });

  useEffect(() => {
    // In a real app we'd poll or use websockets, here we just fetch once
    Promise.all([
      getMetrics().catch(() => ({ total_requests: 0, average_latency_ms: 0 })),
      getCacheStats().catch(() => ({ hit_rate: 0 })),
      getModels().catch(() => ({ models: [] }))
    ]).then(([m, c, mods]) => {
      setMetrics(m);
      setCache(c);
      setModels(mods);
    });
  }, []);

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-semibold">Overview</h2>
      
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white p-4 rounded-lg shadow border flex items-center space-x-4">
          <div className="p-3 bg-blue-100 text-blue-600 rounded-full"><Activity /></div>
          <div>
            <p className="text-sm text-gray-500">Total Requests</p>
            <p className="text-xl font-bold">{metrics.total_requests}</p>
          </div>
        </div>
        
        <div className="bg-white p-4 rounded-lg shadow border flex items-center space-x-4">
          <div className="p-3 bg-green-100 text-green-600 rounded-full"><Clock /></div>
          <div>
            <p className="text-sm text-gray-500">Avg Latency</p>
            <p className="text-xl font-bold">{metrics.average_latency_ms} ms</p>
          </div>
        </div>
        
        <div className="bg-white p-4 rounded-lg shadow border flex items-center space-x-4">
          <div className="p-3 bg-purple-100 text-purple-600 rounded-full"><Database /></div>
          <div>
            <p className="text-sm text-gray-500">Cache Hit Rate</p>
            <p className="text-xl font-bold">{(cache.hit_rate * 100).toFixed(1)}%</p>
          </div>
        </div>
        
        <div className="bg-white p-4 rounded-lg shadow border flex items-center space-x-4">
          <div className="p-3 bg-orange-100 text-orange-600 rounded-full"><Layers /></div>
          <div>
            <p className="text-sm text-gray-500">Active Models</p>
            <p className="text-xl font-bold">{models.models.length}</p>
          </div>
        </div>
      </div>

      <div className="bg-white rounded-lg shadow border mt-6">
        <div className="px-6 py-4 border-b">
          <h3 className="font-semibold">Recent Requests</h3>
        </div>
        <div className="p-6 text-center text-gray-500">
          No recent requests found.
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
