import { useState } from 'react';

export function QRPack() {
  const [label, setLabel] = useState('Table 1');
  const [link, setLink] = useState('https://example.com');
  const [color, setColor] = useState('#2563eb');
  const [logo, setLogo] = useState<string | null>(null);

  const qrUrl = `https://api.qrserver.com/v1/create-qr-code/?size=150x150&data=${encodeURIComponent(link)}`;

  const onLogo = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setLogo(URL.createObjectURL(file));
    }
  };

  const downloadPDF = async () => {
    try {
      const res = await fetch('/api/outlet/demo/qrpack.pdf');
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'qr_pack.pdf';
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      /* ignore */
    }
  };

  const downloadPNG = () => {
    const a = document.createElement('a');
    a.href = qrUrl;
    a.download = 'qr.png';
    a.click();
  };

  return (
    <div className="space-y-4">
      <div className="space-y-2">
        <div>
          <label className="block mb-1" htmlFor="label">Table Label</label>
          <input id="label" value={label} onChange={(e) => setLabel(e.target.value)} />
        </div>
        <div>
          <label className="block mb-1" htmlFor="link">Deep Link</label>
          <input id="link" value={link} onChange={(e) => setLink(e.target.value)} />
        </div>
        <div>
          <label className="block mb-1" htmlFor="logo">Logo</label>
          <input id="logo" type="file" accept="image/*" onChange={onLogo} />
        </div>
        <div>
          <label className="block mb-1" htmlFor="color">Primary Color</label>
          <input id="color" type="color" value={color} onChange={(e) => setColor(e.target.value)} />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="border p-4 text-center" style={{ borderColor: color }}>
            {logo && <img src={logo} alt="logo" className="h-8 mx-auto mb-2" />}
            <img src={qrUrl} alt="qr" className="mx-auto" />
            <div className="mt-2" style={{ color }}>{label}</div>
          </div>
        ))}
      </div>

      <div className="space-x-2">
        <button onClick={downloadPDF} className="border px-2 py-1">Download PDF pack</button>
        <button onClick={downloadPNG} className="border px-2 py-1">Download PNG (single)</button>
      </div>
    </div>
  );
}
