import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';

const steps = [
  'Basics',
  'Branding',
  'Tables',
  'Billing',
  'Taxes',
  'Payments',
  'Alerts',
  'Review'
] as const;

interface BasicsData {
  name: string;
}

interface BrandingData {
  color: string;
  logo: string;
}

interface TablesData {
  count: number;
}

interface BillingData {
  plan: string;
}

interface TaxesData {
  mode: string;
}

interface PaymentsData {
  mode: 'central' | 'outlet';
  vpa: string;
}

interface AlertsData {
  email: boolean;
  whatsapp: boolean;
}

interface OnboardingData {
  basics: BasicsData;
  branding: BrandingData;
  tables: TablesData;
  billing: BillingData;
  taxes: TaxesData;
  payments: PaymentsData;
  alerts: AlertsData;
}

const defaultData: OnboardingData = {
  basics: { name: '' },
  branding: { color: '#2563eb', logo: '' },
  tables: { count: 0 },
  billing: { plan: 'starter' },
  taxes: { mode: 'none' },
  payments: { mode: 'central', vpa: '' },
  alerts: { email: false, whatsapp: false }
};

export function Onboarding() {
  const navigate = useNavigate();
  const [step, setStep] = useState(0);
  const [data, setData] = useState<OnboardingData>(defaultData);

  // redirect if already completed
  useEffect(() => {
    if (localStorage.getItem('onboarding_completed') === 'true') {
      navigate('/dashboard', { replace: true });
    }
  }, [navigate]);

  // load saved state
  useEffect(() => {
    const saved = localStorage.getItem('onboarding');
    if (saved) {
      try {
        setData({ ...defaultData, ...JSON.parse(saved) });
      } catch {
        /* ignore */
      }
    }
  }, []);

  // autosave
  useEffect(() => {
    localStorage.setItem('onboarding', JSON.stringify(data));
  }, [data]);

  const next = () => {
    if (step === steps.length - 1) {
      localStorage.setItem('onboarding_completed', 'true');
      navigate('/dashboard', { replace: true });
    } else {
      setStep((s) => s + 1);
    }
  };

  const prev = () => {
    if (step > 0) setStep((s) => s - 1);
  };

  const onBrandColor = (e: React.ChangeEvent<HTMLInputElement>) => {
    const color = e.target.value;
    setData((d) => ({ ...d, branding: { ...d.branding, color } }));
  };

  const onBrandLogo = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const url = URL.createObjectURL(file);
    setData((d) => ({ ...d, branding: { ...d.branding, logo: url } }));
  };

  const downloadQR = async () => {
    try {
      const res = await fetch('/api/admin/outlets/demo/qrposters.zip');
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'qrposters.zip';
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      /* ignore */
    }
  };

  const content = [
    (
      <div key="basics">
        <label htmlFor="name" className="block mb-1">
          Name
        </label>
        <input
          id="name"
          value={data.basics.name}
          onChange={(e) =>
            setData((d) => ({
              ...d,
              basics: { name: e.target.value }
            }))
          }
        />
      </div>
    ),
    (
      <div className="space-y-4" key="branding">
        <div>
          <label className="block mb-1" htmlFor="color">
            Primary Color
          </label>
          <input id="color" type="color" value={data.branding.color} onChange={onBrandColor} />
        </div>
        <div>
          <label className="block mb-1" htmlFor="logo">
            Logo
          </label>
          <input id="logo" type="file" accept="image/*" onChange={onBrandLogo} />
        </div>
        <div
          className="h-24 w-48 border bg-no-repeat bg-contain"
          style={{
            backgroundColor: data.branding.color,
            backgroundImage: data.branding.logo ? `url(${data.branding.logo})` : undefined
          }}
        />
      </div>
    ),
    (
      <div key="tables" className="space-y-4">
        <div>
          <label htmlFor="table-count" className="block mb-1">
            Table Count
          </label>
          <input
            id="table-count"
            type="number"
            value={data.tables.count}
            onChange={(e) =>
              setData((d) => ({
                ...d,
                tables: { count: Number(e.target.value) }
              }))
            }
          />
        </div>
        <button onClick={downloadQR} className="border px-2 py-1">
          Download QR ZIP
        </button>
      </div>
    ),
    (
      <div key="billing">
        <label htmlFor="plan" className="block mb-1">
          Plan
        </label>
        <select
          id="plan"
          value={data.billing.plan}
          onChange={(e) =>
            setData((d) => ({
              ...d,
              billing: { plan: e.target.value }
            }))
          }
        >
          <option value="starter">Starter</option>
          <option value="standard">Standard</option>
          <option value="pro">Pro</option>
        </select>
      </div>
    ),
    (
      <div key="taxes">
        <label htmlFor="tax-mode" className="block mb-1">
          Tax Mode
        </label>
        <select
          id="tax-mode"
          value={data.taxes.mode}
          onChange={(e) =>
            setData((d) => ({
              ...d,
              taxes: { mode: e.target.value }
            }))
          }
        >
          <option value="none">None</option>
          <option value="gst">GST</option>
        </select>
      </div>
    ),
    (
      <div className="space-y-4" key="payments">
        <div>
          <label className="mr-4">
            <input
              type="radio"
              checked={data.payments.mode === 'central'}
              onChange={() =>
                setData((d) => ({
                  ...d,
                  payments: { ...d.payments, mode: 'central' }
                }))
              }
            />{' '}
            Central VPA
          </label>
          <label>
            <input
              type="radio"
              checked={data.payments.mode === 'outlet'}
              onChange={() =>
                setData((d) => ({
                  ...d,
                  payments: { ...d.payments, mode: 'outlet' }
                }))
              }
            />{' '}
            Outlet VPA
          </label>
        </div>
        <div>
          <input
            placeholder="VPA"
            value={data.payments.vpa}
            onChange={(e) =>
              setData((d) => ({
                ...d,
                payments: { ...d.payments, vpa: e.target.value }
              }))
            }
          />
        </div>
      </div>
    ),
    (
      <div className="space-y-2" key="alerts">
        <label>
          <input
            type="checkbox"
            checked={data.alerts.email}
            onChange={(e) =>
              setData((d) => ({
                ...d,
                alerts: { ...d.alerts, email: e.target.checked }
              }))
            }
          />{' '}
          Email
        </label>
        <label>
          <input
            type="checkbox"
            checked={data.alerts.whatsapp}
            onChange={(e) =>
              setData((d) => ({
                ...d,
                alerts: { ...d.alerts, whatsapp: e.target.checked }
              }))
            }
          />{' '}
          WhatsApp
        </label>
      </div>
    ),
    (
      <div key="review" className="space-y-2">
        <div>Name: {data.basics.name || '-'}</div>
        <div>Tables: {data.tables.count}</div>
        <div>Plan: {data.billing.plan}</div>
        <div>Tax: {data.taxes.mode}</div>
      </div>
    )
  ];

  return (
    <div className="p-4">
      <ol className="flex space-x-2 mb-4">
        {steps.map((s, i) => (
          <li key={s} className={i === step ? 'font-bold' : ''}>
            {s}
          </li>
        ))}
      </ol>
      {content[step]}
      <div className="mt-4 flex justify-between">
        {step > 0 && (
          <button onClick={prev} className="border px-2 py-1">
            Back
          </button>
        )}
        <button onClick={next} className="ml-auto border px-2 py-1">
          {step === steps.length - 1 ? 'Finish' : 'Next'}
        </button>
      </div>
    </div>
  );
}

