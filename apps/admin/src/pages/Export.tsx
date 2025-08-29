import { useEffect, useState } from 'react';
import { requestExport, exportStatus, type ExportStatus } from '@neo/api';

interface Job {
  id: string;
  type: string;
  status: string;
  url?: string;
}

export function Export() {
  const [from, setFrom] = useState('');
  const [to, setTo] = useState('');
  const [jobs, setJobs] = useState<Job[]>([]);

  async function start(type: string) {
    try {
      const res = await requestExport({ type, from, to });
      setJobs((j) => [...j, { id: res.job, type, status: 'pending' }]);
    } catch (e) {
      // noop
    }
  }

  useEffect(() => {
    const timer = setInterval(() => {
      jobs.forEach(async (job) => {
        if (job.status === 'complete') return;
        try {
          const res: ExportStatus = await exportStatus(job.id);
          setJobs((prev) =>
            prev.map((j) => (j.id === job.id ? { ...j, ...res } : j))
          );
        } catch {
          // ignore
        }
      });
    }, 3000);
    return () => clearInterval(timer);
  }, [jobs]);

  return (
    <div className="space-y-6">
      <section>
        <h2 className="font-bold mb-2">Orders</h2>
        <input
          type="date"
          value={from}
          onChange={(e) => setFrom(e.target.value)}
          className="border px-2 py-1"
        />
        <input
          type="date"
          value={to}
          onChange={(e) => setTo(e.target.value)}
          className="border px-2 py-1 ml-2"
        />
        <button
          onClick={() => start('orders')}
          className="ml-2 border px-2 py-1"
        >
          Request export
        </button>
      </section>
      <section>
        <h2 className="font-bold mb-2">Items</h2>
        <button
          onClick={() => start('items')}
          className="border px-2 py-1"
        >
          Request export
        </button>
      </section>
      <section>
        <h2 className="font-bold mb-2">Customers</h2>
        <button
          onClick={() => start('customers')}
          className="border px-2 py-1"
        >
          Request export
        </button>
      </section>
      <section>
        <h2 className="font-bold mb-2">Download center</h2>
        <ul className="list-disc pl-5 space-y-1">
          {jobs.map((job) => (
            <li key={job.id}>
              {job.type} - {job.status}
              {job.url && (
                <a href={job.url} className="underline ml-2">
                  Download
                </a>
              )}
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
