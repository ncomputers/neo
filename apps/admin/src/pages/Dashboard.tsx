import { useState } from 'react';
import { useSSE } from '@neo/api';
import { SkeletonList } from '@neo/ui';

interface KPI {
  orders_today: number;
  sales: number;
  prep_p50: number;
  eta_sla_pct: number;
  webhook_breaker_pct: number;
}

export function Dashboard() {
  const [kpi, setKpi] = useState<KPI | null>(null);
  useSSE('/admin/kpis', {
    onMessage: (ev) => {
      setKpi(JSON.parse(ev.data));
    }
  });
  if (!kpi) return <SkeletonList count={5} />;
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      <div>Orders Today: {kpi.orders_today}</div>
      <div>Sales ₹: {kpi.sales}</div>
      <div>Avg Prep p50: {kpi.prep_p50}</div>
      <div>ETA SLA %: {kpi.eta_sla_pct}</div>
      <div>Webhook breaker %: {kpi.webhook_breaker_pct}</div>
    </div>
  );
}
