export default function StatusBadge({status}) {
  const style = status === 'COMPLETED' || status === 'OK' ? 'success' : ['REJECTED', 'PROCESSING_FAILED', 'INVALID'].includes(status) ? 'danger' : 'pending';
  return <span className={`badge ${style}`}><i />{status?.replaceAll('_', ' ').toLowerCase()}</span>;
}
