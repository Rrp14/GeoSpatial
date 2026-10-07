import { AlertCircle } from 'lucide-react';
export default function ErrorAlert({message}) { return message ? <div className="error" role="alert"><AlertCircle size={18}/><span>{message}</span></div> : null; }
