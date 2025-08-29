import { useEffect, useState } from 'react';
import { API_BASE, WS_BASE } from '../env';

interface Incident {
  service: string;
  ts: string;
}
interface Feed {
  uptime_7d?: number;
  uptime_30d?: number;
  incidents_7d?: Incident[];
  incidents_30d?: Incident[];
}

function Tile({ label, state }: { label: string; state: string }) {
  const color =
    state === 'ok' ? 'bg-green-500' : state === 'degraded' ? 'bg-amber-500' : 'bg-red-500';
  return (
    <div className={`p-2 rounded text-white text-center ${color}`}>{label}</div>
  );
}

export function Status() {
  const [status, setStatus] = useState<any>();
  const [deps, setDeps] = useState<any>();
  const [wsOk, setWsOk] = useState<string>('degraded');
  const [feed, setFeed] = useState<Feed>();

  useEffect(() => {
    fetch(`${API_BASE}/status.json`).then(r => r.json()).then(setStatus).catch(() => {});
    fetch(`${API_BASE}/status/deps`).then(r => r.json()).then(setDeps).catch(() => {});
    fetch('/incidents.json').then(r => r.json()).then(setFeed).catch(() => {});
    try {
      const ws = new WebSocket(WS_BASE);
      ws.onopen = () => {
        setWsOk('ok');
        ws.close();
      };
      ws.onerror = () => setWsOk('error');
    } catch {
      setWsOk('error');
    }
  }, []);

  const webhooks = deps?.webhooks && Object.values(deps.webhooks).every((v: any) => v === 'ok') ? 'ok' : 'error';

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">Status</h1>
      <div className="grid grid-cols-2 gap-2 w-48">
        <Tile label="API" state={status?.state ?? 'error'} />
        <Tile label="DB" state={status?.db ?? 'error'} />
        <Tile label="WS" state={wsOk} />
        <Tile label="Webhooks" state={webhooks} />
      </div>
      <div>
        <h2 className="font-semibold">Uptime</h2>
        <p>7d: {feed?.uptime_7d ?? 'N/A'}%</p>
        <p>30d: {feed?.uptime_30d ?? 'N/A'}%</p>
      </div>
      <div>
        <h2 className="font-semibold">Incidents (7d)</h2>
        <ul className="list-disc ml-4">
          {feed?.incidents_7d && feed.incidents_7d.length > 0 ? (
            feed.incidents_7d.map((i, idx) => (
              <li key={idx}>{i.service} - {new Date(i.ts).toLocaleString()}</li>
            ))
          ) : (
            <li>None</li>
          )}
        </ul>
      </div>
      <div>
        <h2 className="font-semibold">Incidents (30d)</h2>
        <ul className="list-disc ml-4">
          {feed?.incidents_30d && feed.incidents_30d.length > 0 ? (
            feed.incidents_30d.map((i, idx) => (
              <li key={idx}>{i.service} - {new Date(i.ts).toLocaleString()}</li>
            ))
          ) : (
            <li>None</li>
          )}
        </ul>
      </div>
    </div>
  );
}

export default Status;
