export function Billing() {
  return (
    <button
      onClick={() => {
        window.location.href = '/admin/billing';
      }}
      className="bg-blue-500 text-white p-2"
    >
      Manage subscription
    </button>
  );
}
