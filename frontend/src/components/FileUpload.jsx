import { useRef, useState } from 'react';
import { UploadCloud, ArrowUpRight, LoaderCircle, ShieldCheck } from 'lucide-react';
import ErrorAlert from './ErrorAlert.jsx';
import { uploadFile } from '../api/files.js';

export default function FileUpload({onUploaded}) {
  const picker = useRef(null);
  const busy = useRef(false);
  const [loading, setLoading] = useState(false);
  const [dragging, setDragging] = useState(false);
  const [error, setError] = useState('');
  const [name, setName] = useState('');
  async function submit(file) {
    if (!file || busy.current) return;
    setError('');
    if (!/\.(kml|zip)$/i.test(file.name)) return setError('Choose a KML file or a ZIP containing one Shapefile dataset.');
    if (!file.size || file.size > 25 * 1024 * 1024) return setError('Choose a non-empty file up to 25 MB.');
    busy.current = true; setLoading(true); setName(file.name);
    try { onUploaded(await uploadFile(file)); } catch (e) { setError(e.message); }
    finally { busy.current = false; setLoading(false); if (picker.current) picker.current.value = ''; }
  }
  return <section className="upload-section">
    <div className="section-heading"><h2>Start a measurement</h2><span>01 / UPLOAD</span></div>
    <div className={`dropzone ${dragging ? 'dragging' : ''}`} onDragOver={e => {e.preventDefault(); setDragging(true);}} onDragLeave={() => setDragging(false)} onDrop={e => {e.preventDefault(); setDragging(false); submit(e.dataTransfer.files[0]);}}>
      <div className="upload-icon">{loading ? <LoaderCircle className="spin" size={28}/> : <UploadCloud size={28}/>}</div>
      <h3>{loading ? 'Your file is being processed' : 'Bring your spatial data into focus.'}</h3>
      <p>{loading ? name : 'Drop a KML or Shapefile ZIP here to calculate area and length.'}</p>
      <input ref={picker} type="file" accept=".kml,.zip" aria-label="Select geospatial file" onChange={e => submit(e.target.files[0])} hidden/>
      <button className="primary" disabled={loading} onClick={() => picker.current.click()}>{loading ? 'Scanning & measuring…' : 'Browse files'}{!loading && <ArrowUpRight size={17}/>}</button>
      <span className="file-hint">KML or ZIP · Up to 25 MB · One dataset per upload</span>
    </div>
    <div className="trust-note"><ShieldCheck size={16}/><span>Every upload is quarantined and scanned before processing.</span></div>
    <ErrorAlert message={error}/>
  </section>;
}
