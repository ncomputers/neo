import { useEffect, useState } from 'react';
import { Button, toast } from '@neo/ui';
import {
  getBillingPlan,
  previewBillingPlan,
  changeBillingPlan,
  type PlanPreview
} from '@neo/api';

export function Billing() {
  const [open, setOpen] = useState(false);
  const [selected, setSelected] = useState<string | null>(null);
  const [preview, setPreview] = useState<PlanPreview | null>(null);
  const [loading, setLoading] = useState(false);
  const [invoiceId, setInvoiceId] = useState<string | null>(null);
  const [scheduledFor, setScheduledFor] = useState<string | null>(null);
  const [activeTables, setActiveTables] = useState(0);

  useEffect(() => {
    getBillingPlan()
      .then((p) => {
        setActiveTables(p.active_tables);
        if (p.scheduled_change) setScheduledFor(p.scheduled_change.scheduled_for);
      })
      .catch(() => {});
  }, []);

  const plans = [
    { id: 'starter', name: 'Starter' },
    { id: 'standard', name: 'Standard' },
    { id: 'pro', name: 'Pro' }
  ];

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
      setOpen(false);
    } catch (e: any) {
      toast.error(e.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="p-4 space-y-2">
      {scheduledFor && (
        <span
          className="inline-block bg-gray-200 px-2 py-1 rounded"
          data-testid="schedule-chip"
        >
          Scheduled for {new Date(scheduledFor).toLocaleDateString()}
        </span>
      )}
      {invoiceId && (
        <a
          href={`/invoice/${invoiceId}/pdf`}
          className="text-blue-600 underline"
          data-testid="invoice-link"
          target="_blank"
          rel="noreferrer"
        >
          View invoice
        </a>
      )}
      <div>
        <Button onClick={() => setOpen(true)}>Change Plan</Button>
      </div>
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
                {activeTables > preview.table_cap && (
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

