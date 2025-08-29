import { useEffect, useState } from 'react';
import { Button, toast } from '@neo/ui';
import {
  listInvoices,
  downloadInvoice,
  getCredits,
  getSubscription,
  previewBillingPlan,
  changeBillingPlan,
  type PlanPreview,
  type Invoice,
  type Credits,
  type Subscription
} from '@neo/api';
import { useSearchParams } from 'react-router-dom';

export function Billing() {
  const [tab, setTab] = useState<'invoices' | 'plan'>('invoices');
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [credits, setCredits] = useState<Credits | null>(null);
  const [sub, setSub] = useState<Subscription | null>(null);
  const [invoiceId, setInvoiceId] = useState<string | null>(null);
  const [open, setOpen] = useState(false);
  const [selected, setSelected] = useState<string | null>(null);
  const [preview, setPreview] = useState<PlanPreview | null>(null);
  const [loading, setLoading] = useState(false);
  const [scheduledFor, setScheduledFor] = useState<string | null>(null);
  const [params, setParams] = useSearchParams();

  const from = params.get('from') || '';
  const to = params.get('to') || '';
  const status = params.get('status') || '';

  useEffect(() => {
    listInvoices({ from, to, status })
      .then(setInvoices)
      .catch(() => {});
  }, [from, to, status]);

  useEffect(() => {
    getCredits().then(setCredits).catch(() => {});
    getSubscription()
      .then((s) => {
        setSub(s);
        if (s.scheduled_change) setScheduledFor(s.scheduled_change.scheduled_for);
      })
      .catch(() => {});
  }, []);

  const plans = [
    { id: 'starter', name: 'Starter' },
    { id: 'standard', name: 'Standard' },
    { id: 'pro', name: 'Pro' }
  ];

  function updateParam(key: string, value: string) {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value);
    else next.delete(key);
    setParams(next);
  }

  async function select(id: string) {
    setSelected(id);
    setPreview(null);
    try {
      const p = await previewBillingPlan(id);
      setPreview(p);
    } catch (e: any) {
      toast.error(e.message);
    }
  }

  async function upgradeNow() {
    if (!selected) return;
    setLoading(true);
    try {
      const res = await changeBillingPlan({
        to_plan_id: selected,
        change_type: 'upgrade',
        when: 'now'
      });
      toast.success('Plan upgraded');
      if (res.invoice_id) setInvoiceId(res.invoice_id);
      const s = await getSubscription();
      setSub(s);
      setOpen(false);
    } catch (e: any) {
      toast.error(e.message);
    } finally {
      setLoading(false);
    }
  }

  async function scheduleDowngrade() {
    if (!selected) return;
    setLoading(true);
    try {
      const res = await changeBillingPlan({
        to_plan_id: selected,
        change_type: 'downgrade',
        when: 'period_end'
      });
      toast.success('Downgrade scheduled');
      if (res.scheduled_for) setScheduledFor(res.scheduled_for);
      const s = await getSubscription();
      setSub(s);
      setOpen(false);
    } catch (e: any) {
      toast.error(e.message);
    } finally {
      setLoading(false);
    }
  }

  const overCap = sub && sub.active_tables > sub.table_cap;
  const now = new Date();
  const daysLeft = sub
    ? Math.ceil(
        (new Date(sub.current_period_end).getTime() - now.getTime()) / 86400000
      )
    : 0;
  const expiringSoon = sub && sub.status === 'ACTIVE' && daysLeft <= 3;
  const graceDaysLeft =
    sub &&
    sub.status === 'GRACE' &&
    sub.grace_ends_at
      ? Math.ceil(
          (new Date(sub.grace_ends_at).getTime() - now.getTime()) / 86400000
        )
      : 0;

  return (
    <div className="p-4 space-y-4">
      <div className="space-x-4">
        <button
          onClick={() => setTab('invoices')}
          className={tab === 'invoices' ? 'font-bold' : ''}
        >
          Invoices
        </button>
        <button
          onClick={() => setTab('plan')}
          className={tab === 'plan' ? 'font-bold' : ''}
        >
          Plan & Usage
        </button>
      </div>

      {tab === 'invoices' && (
        <div>
          <div className="flex space-x-2 items-end">
            <input
              type="date"
              value={from}
              onChange={(e) => updateParam('from', e.target.value)}
              data-testid="from-filter"
            />
            <input
              type="date"
              value={to}
              onChange={(e) => updateParam('to', e.target.value)}
              data-testid="to-filter"
            />
            <select
              value={status}
              onChange={(e) => updateParam('status', e.target.value)}
              data-testid="status-filter"
            >
              <option value="">All</option>
              <option value="PAID">PAID</option>
              <option value="OPEN">OPEN</option>
              <option value="REFUNDED">REFUNDED</option>
            </select>
            <a
              href={`/admin/billing/invoices.csv?from=${from}&to=${to}`}
              data-testid="csv-export"
              className="underline text-blue-600"
            >
              Export CSV
            </a>
          </div>
          <table className="w-full mt-4" data-testid="invoice-table">
            <thead>
              <tr>
                <th>Date</th>
                <th>Number</th>
                <th>Period</th>
                <th>Amount</th>
                <th>GST</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {invoices.map((inv) => (
                <tr key={inv.id}>
                  <td>{new Date(inv.date).toLocaleDateString()}</td>
                  <td>{inv.number}</td>
                  <td>
                    {new Date(inv.period.from).toLocaleDateString()} –{' '}
                    {new Date(inv.period.to).toLocaleDateString()}
                  </td>
                  <td>₹{inv.amount}</td>
                  <td>₹{inv.gst}</td>
                  <td>{inv.status}</td>
                  <td>
                    <button
                      onClick={() => downloadInvoice(inv.id)}
                      data-testid={`download-${inv.id}`}
                    >
                      Download PDF
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {tab === 'plan' && sub && (
        <div className="space-y-2">
          {expiringSoon && (
            <div role="alert" className="bg-yellow-100 p-2">
              Subscription expiring soon
            </div>
          )}
          {sub.status === 'GRACE' && (
            <div role="alert" className="bg-yellow-100 p-2 space-x-2">
              <span>Subscription in grace period ({graceDaysLeft} days left)</span>
              <Button onClick={() => setOpen(true)}>Renew now</Button>
            </div>
          )}
          {sub.status === 'EXPIRED' && (
            <div role="alert" className="bg-red-100 p-2 space-x-2">
              <span>Subscription expired</span>
              <Button onClick={() => setOpen(true)}>Renew now</Button>
            </div>
          )}

          {scheduledFor && (
            <span
              className="inline-block bg-gray-200 px-2 py-1 rounded"
              data-testid="schedule-chip"
            >
              Scheduled downgrade →{' '}
              {new Date(scheduledFor).toLocaleDateString()}
            </span>
          )}
          {invoiceId && (
            <a
              href={`/admin/billing/invoice/${invoiceId}.pdf`}
              className="text-blue-600 underline"
              data-testid="invoice-link"
              target="_blank"
              rel="noreferrer"
            >
              View invoice
            </a>
          )}

          <div>
            <div>Plan: {sub.plan_id}</div>
            <div>
              Tables {sub.active_tables}/{sub.table_cap}
              {sub.trial_ends_at && new Date(sub.trial_ends_at) > now && (
                <span className="ml-2 bg-green-200 px-1 rounded">Trial</span>
              )}
              {sub.status === 'GRACE' && (
                <span className="ml-2 bg-yellow-200 px-1 rounded">Grace</span>
              )}
              {overCap && (
                <span
                  className="ml-2 bg-red-200 px-1 rounded"
                  data-testid="overcap-chip"
                >
                  Over cap by {sub.active_tables - sub.table_cap}
                </span>
              )}
            </div>
            {credits && (
              <div>
                Credits ₹{credits.balance}{' '}
                <span
                  title={`Referrals ₹${credits.referrals}; Adjustments ₹${credits.adjustments}`}
                >
                  ⓘ
                </span>
              </div>
            )}
          </div>
          <div data-testid="status-panel">
            Status: {sub.status}
            {sub.status === 'GRACE' && ` (${graceDaysLeft} days left)`}
            {sub.status === 'ACTIVE' && scheduledFor && (
              <span>
                {' '}- Scheduled downgrade →{' '}
                {new Date(scheduledFor).toLocaleDateString()}
              </span>
            )}
          </div>
          <div>
            <Button
              onClick={() => setOpen(true)}
              disabled={sub.status === 'EXPIRED'}
            >
              Change Plan
            </Button>
          </div>
        </div>
      )}

      {open && (
        <div
          role="dialog"
          className="fixed inset-0 bg-black/50 flex items-center justify-center"
        >
          <div className="bg-white p-4 rounded w-80 space-y-2">
            <h2 className="text-lg font-bold">Choose plan</h2>
            <div className="space-y-2">
              {plans.map((p) => (
                <button
                  key={p.id}
                  onClick={() => select(p.id)}
                  className={`border p-2 w-full text-left ${
                    selected === p.id ? 'border-blue-500' : ''
                  }`}
                >
                  {p.name}
                </button>
              ))}
            </div>
            {preview && (
              <div className="mt-2 space-y-1">
                <p>Δ₹{preview.delta}</p>
                <p>GST ₹{preview.gst}</p>
                <p>New table cap: {preview.table_cap}</p>
                <p>Effective: {new Date(preview.effective).toLocaleString()}</p>
                {sub && sub.active_tables > preview.table_cap && (
                  <p role="alert" className="text-red-600">
                    Active tables exceed new cap
                  </p>
                )}
              </div>
            )}
            <div className="flex justify-end space-x-2 pt-2">
              <Button onClick={upgradeNow} disabled={loading || !selected}>
                Upgrade now
              </Button>
              <Button onClick={scheduleDowngrade} disabled={loading || !selected}>
                Schedule downgrade
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

