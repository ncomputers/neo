import { useEffect, useState } from 'react';

export function Changelog() {
  const [text, setText] = useState('');
  useEffect(() => {
    fetch('/CHANGELOG.md')
      .then((r) => r.text())
      .then(setText)
      .catch(() => setText(''));
  }, []);
  return <pre className="whitespace-pre-wrap text-sm">{text}</pre>;
}
