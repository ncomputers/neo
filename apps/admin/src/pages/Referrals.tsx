import { useEffect, useState } from 'react';
import { Button } from '@neo/ui';
import { getReferral, createReferral, getCredits, type Referral, type Credits } from '@neo/api';

export function Referrals() {
  const [ref, setRef] = useState<Referral | null>(null);
  const [credits, setCredits] = useState<Credits | null>(null);

  useEffect(() => {
    getReferral().then(setRef).catch(() => {});
    getCredits().then(setCredits).catch(() => {});
  }, []);

  async function generate() {
    try {
      const r = await createReferral();
      setRef(r);
    } catch {
      /* ignore */
    }
  }

  function copy() {
    if (ref) navigator.clipboard.writeText(ref.landing_url);
  }

  if (!ref)
    return (
      <Button onClick={generate}>Generate Link</Button>
    );

  return (
    <div className="space-y-4">
      <div className="flex items-center space-x-2">
        <input
          data-testid="link-input"
          readOnly
          value={ref.landing_url}
          className="border p-1 flex-1"
        />
        <Button data-testid="copy-btn" onClick={copy}>
          Copy
        </Button>
      </div>
      <div className="flex flex-wrap gap-4 items-center">
        <span>Clicks {ref.clicks}</span>
        <span>Signups {ref.signups}</span>
        <span>Conversions {ref.converted}</span>
        <span className="px-2 py-0.5 bg-gray-100 rounded" data-testid="cap-chip">
          Max ₹{ref.max_credit_inr}
        </span>
        {credits && <span>Referral credits ₹{credits.referrals}</span>}
      </div>
      <table data-testid="credits-table" className="min-w-full border">
        <thead>
          <tr>
            <th className="text-left p-2">Date</th>
            <th className="text-left p-2">Amount</th>
            <th className="text-left p-2">Invoice</th>
          </tr>
        </thead>
        <tbody>
          {ref.credits.map((c) => (
            <tr key={c.id}>
              <td className="p-2">{c.created_at}</td>
              <td className="p-2">₹{c.amount_inr}</td>
              <td className="p-2">
                {c.applied_invoice_id ? (
                  <a href={`/admin/billing/invoice/${c.applied_invoice_id}`}>
                    {c.applied_invoice_id}
                  </a>
                ) : (
                  '-'
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
