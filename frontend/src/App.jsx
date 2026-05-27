import { useState, useEffect } from 'react'
import { login, getStats, getRecords, reviewRecord, ingestFile } from './api'

function LoginPage({ onLogin }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')

  const handleLogin = async () => {
    try {
      const res = await login(username, password)
      localStorage.setItem('token', res.data.token)
      onLogin()
    } catch {
      setError('Invalid username or password')
    }
  }

  return (
    <div style={{display:'flex',justifyContent:'center',alignItems:'center',height:'100vh',background:'#f0f4f8'}}>
      <div style={{background:'white',padding:'2rem',borderRadius:'8px',width:'320px',boxShadow:'0 2px 8px rgba(0,0,0,0.1)'}}>
        <h1 style={{color:'#2d6a4f',marginBottom:'0.5rem'}}>Breathe ESG</h1>
        <p style={{color:'#666',marginBottom:'1.5rem'}}>Emissions Data Review Platform</p>
        {error && <div style={{color:'red',marginBottom:'1rem'}}>{error}</div>}
        <input style={{width:'100%',padding:'0.5rem',marginBottom:'0.75rem',border:'1px solid #ddd',borderRadius:'4px',boxSizing:'border-box'}}
          placeholder="Username" value={username} onChange={e => setUsername(e.target.value)} />
        <input style={{width:'100%',padding:'0.5rem',marginBottom:'1rem',border:'1px solid #ddd',borderRadius:'4px',boxSizing:'border-box'}}
          type="password" placeholder="Password" value={password} onChange={e => setPassword(e.target.value)} />
        <button style={{width:'100%',padding:'0.75rem',background:'#2d6a4f',color:'white',border:'none',borderRadius:'4px',cursor:'pointer'}}
          onClick={handleLogin}>Sign In</button>
      </div>
    </div>
  )
}

function StatsBar({ stats }) {
  const items = [
    { label: 'Pending', value: stats.pending, color: '#f39c12' },
    { label: 'Flagged', value: stats.flagged, color: '#e74c3c' },
    { label: 'Approved', value: stats.approved, color: '#27ae60' },
    { label: 'Rejected', value: stats.rejected, color: '#95a5a6' },
    { label: 'Approved CO₂e', value: `${(stats.approved_co2e_kg||0).toLocaleString()} kg`, color: '#2d6a4f' },
    { label: 'Scope 1', value: `${(stats.scope1_co2e_kg||0).toLocaleString()} kg`, color: '#e74c3c' },
    { label: 'Scope 2', value: `${(stats.scope2_co2e_kg||0).toLocaleString()} kg`, color: '#f39c12' },
    { label: 'Scope 3', value: `${(stats.scope3_co2e_kg||0).toLocaleString()} kg`, color: '#3498db' },
  ]
  return (
    <div style={{display:'flex',gap:'1rem',padding:'1rem',background:'white',borderBottom:'1px solid #eee',flexWrap:'wrap'}}>
      {items.map(item => (
        <div key={item.label} style={{textAlign:'center',minWidth:'100px'}}>
          <div style={{fontSize:'1.4rem',fontWeight:'bold',color:item.color}}>{item.value ?? '—'}</div>
          <div style={{fontSize:'0.75rem',color:'#666'}}>{item.label}</div>
        </div>
      ))}
    </div>
  )
}

function UploadPanel({ onUploaded }) {
  const [sourceType, setSourceType] = useState('SAP')
  const [file, setFile] = useState(null)
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState('')

  const handleUpload = async () => {
    if (!file) return
    setLoading(true)
    setMessage('')
    try {
      const res = await ingestFile(sourceType, file)
      setMessage(`✓ ${res.data.message}`)
      onUploaded()
    } catch (e) {
      setMessage(`✗ Failed: ${e.response?.data?.error || e.message}`)
    }
    setLoading(false)
  }

  return (
    <div style={{padding:'1rem',background:'#f8f9fa',borderBottom:'1px solid #eee',display:'flex',alignItems:'center',gap:'1rem',flexWrap:'wrap'}}>
      <strong>Ingest Data:</strong>
      <select value={sourceType} onChange={e => setSourceType(e.target.value)}
        style={{padding:'0.4rem',borderRadius:'4px',border:'1px solid #ddd'}}>
        <option value="SAP">SAP — Fuel</option>
        <option value="UTILITY">Utility — Electricity</option>
        <option value="TRAVEL">Corporate Travel</option>
      </select>
      <input type="file" accept=".csv,.json,.txt" onChange={e => setFile(e.target.files[0])} />
      <button onClick={handleUpload} disabled={loading || !file}
        style={{padding:'0.4rem 1rem',background:'#2d6a4f',color:'white',border:'none',borderRadius:'4px',cursor:'pointer'}}>
        {loading ? 'Uploading...' : 'Upload & Ingest'}
      </button>
      {message && <span style={{color: message.startsWith('✓') ? 'green' : 'red'}}>{message}</span>}
    </div>
  )
}

function RecordRow({ record, onReview }) {
  const [note, setNote] = useState('')
  const [expanded, setExpanded] = useState(false)
  const scopeColor = { 1: '#e74c3c', 2: '#f39c12', 3: '#3498db' }
  const statusColor = { PENDING:'#f39c12', APPROVED:'#27ae60', FLAGGED:'#e74c3c', REJECTED:'#95a5a6' }

  return (
    <>
      <tr onClick={() => setExpanded(!expanded)} style={{cursor:'pointer',background:expanded?'#f8f9fa':'white',borderBottom:'1px solid #eee'}}>
        <td style={{padding:'0.5rem'}}>
          <span style={{background:scopeColor[record.scope],color:'white',padding:'2px 6px',borderRadius:'3px',fontSize:'0.75rem'}}>
            S{record.scope}
          </span>
        </td>
        <td style={{padding:'0.5rem',fontSize:'0.85rem'}}>{record.source_type}</td>
        <td style={{padding:'0.5rem',fontSize:'0.85rem'}}>{record.category}</td>
        <td style={{padding:'0.5rem',fontSize:'0.85rem'}}>{record.activity_date}</td>
        <td style={{padding:'0.5rem',fontSize:'0.85rem'}}>{parseFloat(record.quantity).toLocaleString()} {record.unit}</td>
        <td style={{padding:'0.5rem',fontSize:'0.85rem'}}>{record.co2e_kg ? `${parseFloat(record.co2e_kg).toFixed(2)} kg` : '—'}</td>
        <td style={{padding:'0.5rem',fontSize:'0.85rem'}}>{record.location || '—'}</td>
        <td style={{padding:'0.5rem'}}>
          <span style={{background:statusColor[record.status],color:'white',padding:'2px 6px',borderRadius:'3px',fontSize:'0.75rem'}}>
            {record.status}
          </span>
          {record.flag_reason && <span title={record.flag_reason} style={{marginLeft:'4px'}}>⚠️</span>}
        </td>
        <td style={{padding:'0.5rem'}} onClick={e => e.stopPropagation()}>
          <button onClick={() => onReview(record.id,'APPROVED',note)}
            style={{background:'#27ae60',color:'white',border:'none',borderRadius:'3px',padding:'2px 6px',marginRight:'3px',cursor:'pointer'}}>✓</button>
          <button onClick={() => onReview(record.id,'FLAGGED',note)}
            style={{background:'#e74c3c',color:'white',border:'none',borderRadius:'3px',padding:'2px 6px',marginRight:'3px',cursor:'pointer'}}>⚑</button>
          <button onClick={() => onReview(record.id,'REJECTED',note)}
            style={{background:'#95a5a6',color:'white',border:'none',borderRadius:'3px',padding:'2px 6px',cursor:'pointer'}}>✗</button>
        </td>
      </tr>
      {expanded && (
        <tr style={{background:'#f0f4f8'}}>
          <td colSpan="9" style={{padding:'0.75rem',fontSize:'0.85rem'}}>
            <strong>Vendor:</strong> {record.vendor||'—'} &nbsp;|&nbsp;
            <strong>Description:</strong> {record.description||'—'} &nbsp;|&nbsp;
            <strong>Flag:</strong> {record.flag_reason||'None'}<br/>
            <input placeholder="Add a note before reviewing..." value={note}
              onChange={e => setNote(e.target.value)} onClick={e => e.stopPropagation()}
              style={{marginTop:'0.5rem',padding:'0.4rem',width:'400px',border:'1px solid #ddd',borderRadius:'4px'}}/>
          </td>
        </tr>
      )}
    </>
  )
}

function Dashboard() {
  const [stats, setStats] = useState({})
  const [records, setRecords] = useState([])
  const [filters, setFilters] = useState({ scope:'', status:'', source_type:'' })
  const [loading, setLoading] = useState(true)

  const fetchData = async () => {
    setLoading(true)
    try {
      const active = Object.fromEntries(Object.entries(filters).filter(([,v]) => v))
      const [s, r] = await Promise.all([getStats(), getRecords(active)])
      setStats(s.data)
      setRecords(r.data)
    } catch(e) { console.error(e) }
    setLoading(false)
  }

  useEffect(() => { fetchData() }, [filters])

  const handleReview = async (id, status, note) => {
    await reviewRecord(id, status, note)
    fetchData()
  }

  return (
    <div style={{fontFamily:'sans-serif',minHeight:'100vh',background:'#f0f4f8'}}>
      <header style={{background:'#2d6a4f',color:'white',padding:'1rem 1.5rem',display:'flex',justifyContent:'space-between',alignItems:'center'}}>
        <h1 style={{margin:0,fontSize:'1.25rem'}}>Breathe ESG — Analyst Dashboard</h1>
        <button onClick={() => { localStorage.removeItem('token'); window.location.reload() }}
          style={{background:'rgba(255,255,255,0.2)',color:'white',border:'none',padding:'0.4rem 1rem',borderRadius:'4px',cursor:'pointer'}}>
          Logout
        </button>
      </header>
      <StatsBar stats={stats} />
      <UploadPanel onUploaded={fetchData} />
      <div style={{padding:'1rem'}}>
        <div style={{display:'flex',gap:'0.75rem',marginBottom:'1rem',flexWrap:'wrap'}}>
          {[
            ['scope',['','1','2','3'],['All Scopes','Scope 1','Scope 2','Scope 3']],
            ['status',['','PENDING','FLAGGED','APPROVED','REJECTED'],['All Statuses','Pending','Flagged','Approved','Rejected']],
            ['source_type',['','SAP','UTILITY','TRAVEL'],['All Sources','SAP','Utility','Travel']],
          ].map(([key, vals, labels]) => (
            <select key={key} value={filters[key]} onChange={e => setFilters({...filters,[key]:e.target.value})}
              style={{padding:'0.4rem',borderRadius:'4px',border:'1px solid #ddd'}}>
              {vals.map((v,i) => <option key={v} value={v}>{labels[i]}</option>)}
            </select>
          ))}
          <button onClick={fetchData} style={{padding:'0.4rem 1rem',border:'1px solid #ddd',borderRadius:'4px',cursor:'pointer'}}>Refresh</button>
        </div>
        {loading ? <div style={{textAlign:'center',padding:'2rem',color:'#666'}}>Loading...</div> : (
          <div style={{background:'white',borderRadius:'8px',overflow:'auto',boxShadow:'0 1px 4px rgba(0,0,0,0.1)'}}>
            <table style={{width:'100%',borderCollapse:'collapse'}}>
              <thead>
                <tr style={{background:'#f8f9fa',borderBottom:'2px solid #eee'}}>
                  {['Scope','Source','Category','Date','Quantity','CO₂e','Location','Status','Actions'].map(h => (
                    <th key={h} style={{padding:'0.75rem 0.5rem',textAlign:'left',fontSize:'0.85rem',color:'#666'}}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {records.length === 0
                  ? <tr><td colSpan="9" style={{textAlign:'center',padding:'2rem',color:'#999'}}>No records. Upload a file above to get started.</td></tr>
                  : records.map(r => <RecordRow key={r.id} record={r} onReview={handleReview} />)
                }
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}

export default function App() {
  const [loggedIn, setLoggedIn] = useState(!!localStorage.getItem('token'))
  return loggedIn ? <Dashboard /> : <LoginPage onLogin={() => setLoggedIn(true)} />
}