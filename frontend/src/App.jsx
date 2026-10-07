import { useEffect, useState } from 'react';
import { ArrowUpRight, ArrowLeft, ArrowRight, Layers, FileArchive, FileText, Plus, RefreshCw, Ruler, Shapes, ShieldCheck, ChevronRight } from 'lucide-react';
import { listFiles, getFile, getMeasurements } from './api/files.js';
import FileUpload from './components/FileUpload.jsx';
import StatusBadge from './components/StatusBadge.jsx';
import ErrorAlert from './components/ErrorAlert.jsx';

const number = value => new Intl.NumberFormat(undefined, {maximumFractionDigits: 2}).format(value ?? 0);
const date = value => new Date(value).toLocaleString(undefined, {month:'short', day:'numeric', hour:'2-digit', minute:'2-digit'});
const icon = type => type === 'SHAPEFILE_ZIP' ? <FileArchive size={20}/> : <FileText size={20}/>;
const selectedId = () => location.hash.startsWith('#/files/') ? location.hash.slice(8) : null;

function Pagination({page, total, size, onPage}) {
  return <div className="pagination"><span>{total ? `${(page - 1) * size + 1}–${Math.min(page * size, total)} of ${total}` : '0 results'}</span><div><button aria-label="Previous page" disabled={page === 1} onClick={() => onPage(page - 1)}><ArrowLeft size={16}/></button><button aria-label="Next page" disabled={page * size >= total} onClick={() => onPage(page + 1)}><ArrowRight size={16}/></button></div></div>;
}

function FileList({revision}) {
  const [data, setData] = useState(null), [page, setPage] = useState(1), [error, setError] = useState(''), [refresh, setRefresh] = useState(0);
  useEffect(() => {
    const controller = new AbortController(); setError(''); setData(null);
    listFiles(page, controller.signal).then(setData).catch(e => {if (e.name !== 'AbortError') setError(e.message);});
    return () => controller.abort();
  }, [page, revision, refresh]);
  return <section className="recent"><div className="section-heading"><div className="inline"><h2>Recent files</h2>{data && <span className="count">{data.total}</span>}</div><button className="text-button" onClick={() => setRefresh(refresh + 1)}><RefreshCw size={14}/> Refresh</button></div>
    <ErrorAlert message={error}/>
    {!data && !error ? <div className="empty">Loading your files…</div> : data?.items.length ? <><div className="file-list">{data.items.map(file => <a href={`#/files/${file.id}`} className="file-row" key={file.id}><span className="file-icon">{icon(file.file_type)}</span><div className="file-title"><strong>{file.filename}</strong><small>{date(file.created_at)} <span>·</span> {number(file.file_size_bytes / 1024)} KB</small></div><span className="feature-count">{file.feature_count == null ? '—' : `${number(file.feature_count)} features`}</span><StatusBadge status={file.status}/><ChevronRight size={17}/></a>)}</div><Pagination page={page} total={data.total} size={10} onPage={setPage}/></> : !error && <div className="empty"><Layers size={28}/><h3>A clean slate for your next survey.</h3><p>Upload your first dataset. Its results will appear here.</p></div>}
  </section>;
}

function Details({id}) {
  const [file, setFile] = useState(null), [data, setData] = useState(null), [page, setPage] = useState(1), [type, setType] = useState(''), [error, setError] = useState('');
  useEffect(() => {
    const controller = new AbortController(); setError(''); setData(null);
    Promise.all([getFile(id, controller.signal), getMeasurements(id, page, type, controller.signal)]).then(([f, m]) => {setFile(f); setData(m);}).catch(e => {if(e.name !== 'AbortError') setError(e.message);});
    return () => controller.abort();
  }, [id, page, type]);
  return <><a className="back" href="#"><ArrowLeft size={16}/> All files</a><ErrorAlert message={error}/>{!file ? !error && <div className="empty">Loading measurements…</div> : <>
    <div className="detail-heading"><div><p className="eyebrow">DATASET / RESULTS</p><h1>{file.filename}</h1><p className="muted">Uploaded {date(file.created_at)} · {number(file.file_size_bytes / 1024)} KB</p></div><StatusBadge status={file.status}/></div>
    <ErrorAlert message={file.error_message}/>
    {file.warnings.map((warning, i) => <p className="warning" key={i}>{warning}</p>)}
    <div className="stats"><div><span>Features</span><strong>{number(file.feature_count)}</strong><small>{file.summary.polygons || 0} polygons · {file.summary.lines || 0} lines · {file.summary.points || 0} points</small></div><div><span>Total area</span><strong>{number(file.summary.total_area_m2)} <em>m²</em></strong><small>Valid polygon measurements</small></div><div><span>Total length</span><strong>{number(file.summary.total_length_m)} <em>m</em></strong><small>Valid line measurements</small></div></div>
    <div className="method"><Ruler size={20}/><div><strong>{file.measurement_method || 'Awaiting'} measurement</strong><p>{file.source_crs || 'CRS unavailable'} <ArrowRight size={13}/> {file.measurement_crs || (file.measurement_method === 'GEODESIC' ? 'WGS84 ellipsoid' : '—')}</p></div><span>Canonical SI units</span></div>
    <section className="results"><div className="section-heading"><h2>Feature measurements</h2><select aria-label="Filter by geometry" value={type} onChange={e => {setType(e.target.value); setPage(1);}}><option value="">All geometries</option>{['Polygon', 'MultiPolygon', 'LineString', 'MultiLineString', 'Point', 'MultiPoint', 'GeometryCollection'].map(t => <option key={t}>{t}</option>)}</select></div>
    <div className="table-scroll"><table><thead><tr><th>Feature</th><th>Geometry</th><th>Measurement</th><th>Method</th><th>Status</th></tr></thead><tbody>{data?.items.map(row => <tr key={row.feature_index}><td><strong>#{row.feature_index + 1}</strong><details><summary>Properties</summary><pre>{JSON.stringify(row.properties, null, 2)}</pre><small>Source: {row.source_feature_id}</small></details></td><td>{row.geometry_type}</td><td className="numeric">{row.measurement ? <>{number(row.measurement.value)} <span>{row.measurement.unit === 'm2' ? 'm²' : 'm'}</span></> : '—'}</td><td>{row.measurement?.method?.toLowerCase() || '—'}</td><td><StatusBadge status={row.status}/>{row.warning && <p className="row-warning">{row.warning}</p>}</td></tr>)}</tbody></table></div>
    {!data && !error && <p className="empty">Loading features…</p>}{data?.items.length === 0 && <p className="empty">No matching features.</p>}{data && <Pagination page={page} total={data.total} size={25} onPage={setPage}/>}
    </section></> }</>;
}

export default function App() {
  const [id, setId] = useState(selectedId), [revision, setRevision] = useState(0);
  useEffect(() => {const update = () => {setId(selectedId()); window.scrollTo(0, 0);}; window.addEventListener('hashchange', update); return () => window.removeEventListener('hashchange', update);}, []);
  function uploaded(file) {setRevision(v => v + 1); location.hash = `/files/${file.id}`;}
  return <div className="app"><header><a href="#" className="brand"><span className="brand-symbol"><Layers size={23}/></span>GeoMeasure<span className="version">/ V1</span></a><nav><a href="#" className={!id ? 'active' : ''}>Workspace</a><a href="/docs" target="_blank" rel="noreferrer">API docs <ArrowUpRight size={14}/></a></nav><span className="header-label"><span/> Spatial intelligence, measured.</span></header>
    <main>{id ? <Details key={id} id={id}/> : <><div className="hero"><div><p className="eyebrow"><span/> THE GEOSPATIAL WORKSPACE</p><h1>From spatial data.<br/><span>To precise measurements.</span></h1><p className="hero-description">A clear picture of every polygon, line, and point.<br/>Upload your files. We’ll take care of the measurements.</p><div className="hero-tags"><span><ShieldCheck size={15}/> Secure by design</span><span><Ruler size={15}/> CRS-aware results</span></div></div><div className="contour-art" aria-hidden="true"><svg viewBox="0 0 360 260"><defs><pattern id="grid" width="24" height="24" patternUnits="userSpaceOnUse"><path d="M 24 0 L 0 0 0 24" fill="none" stroke="#dce5dc" strokeWidth=".6"/></pattern></defs><rect width="360" height="260" fill="url(#grid)"/>{Array.from({length: 9}, (_, i) => <ellipse key={i} cx="185" cy="130" rx={25 + i * 15} ry={17 + i * 10} fill="none" stroke={i === 5 ? '#466a50' : '#9fb498'} strokeWidth={i === 5 ? 1.8 : .8} transform={`rotate(-28 185 130)`}/>)}<path d="M80 180 L135 61 L284 100 L247 201 Z" stroke="#274f43" strokeWidth="1.4" strokeDasharray="4 4" fill="#a9c29a" fillOpacity=".15"/>{[[80,180],[135,61],[284,100],[247,201]].map(([x,y])=><circle key={x} cx={x} cy={y} r="3.5" fill="#254b3f"/>)}<path d="M185 116v28M171 130h28" stroke="#254b3f"/><text x="18" y="240" fontSize="9" fill="#6c7e6c" letterSpacing="2">GEOMETRY → CLARITY</text><text x="323" y="28" fontSize="10" fill="#466a50">N ↑</text></svg><span className="art-label">AREA / LENGTH / INSIGHT</span></div></div>
    <div className="workspace-grid"><div><FileUpload onUploaded={uploaded}/><FileList revision={revision}/></div><aside><p className="eyebrow">BUILT FOR YOUR DATA</p><h2>Every coordinate<br/>counts.</h2><p>Measurements grounded in the right coordinate reference system, with a method you can inspect.</p><div className="aside-feature"><Shapes size={20}/><div><h3>Area & length</h3><p>Polygons in square metres.<br/>Lines in metres. No guesswork.</p></div></div><div className="aside-feature"><Layers size={20}/><div><h3>Your properties, preserved</h3><p>Keep feature attributes alongside each measurement.</p></div></div><div className="aside-feature"><ShieldCheck size={20}/><div><h3>Checked at every step</h3><p>Malware scanning, archive validation, and geometry checks.</p></div></div><div className="format-note"><span>SUPPORTED FORMATS</span><div><b>.KML</b><Plus size={12}/><b>.ZIP</b></div><p>Shapefile ZIPs need matching .shp, .shx, .dbf and .prj files.</p></div></aside></div></> }</main><footer><span><Layers size={14}/> GeoMeasure</span><p>Built for clarity. Measured with care.</p><span className="footer-note">WGS84 / PROJECTED / GEODESIC</span></footer></div>;
}
