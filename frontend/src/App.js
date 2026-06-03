import React, { useState, useEffect, useRef } from 'react';
import {
  LayoutDashboard, Bell, Shield, Activity,
  FileText, Cpu, ChevronRight, RefreshCw,
  AlertTriangle, Zap, Eye, History, Database
} from 'lucide-react';
import {
  AreaChart, Area, BarChart, Bar,
  XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell
} from 'recharts';

const api = (path) =>
  fetch(`http://localhost:5000${path}`).then(r => r.json()).catch(() => null);

const postApi = (path, body) =>
  fetch(`http://localhost:5000${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  }).then(r => r.json()).catch(() => null);

// ── Fingerprint ───────────────────────────────────────────────────────────
function getFingerprint() {
  const raw = [
    navigator.userAgent,
    navigator.language,
    window.screen.width + 'x' + window.screen.height,
    window.screen.colorDepth,
    new Date().getTimezoneOffset(),
    navigator.hardwareConcurrency,
    navigator.platform,
  ].join('|');
  let hash = 0;
  for (let i = 0; i < raw.length; i++) {
    hash = ((hash << 5) - hash) + raw.charCodeAt(i);
    hash |= 0;
  }
  return Math.abs(hash).toString(16).padStart(8, '0');
}

// ── Shared components ─────────────────────────────────────────────────────
function Badge({ sev }) {
  const map = { CRITICAL:'#ff3d5a', HIGH:'#ff8c42', MEDIUM:'#ffe600', LOW:'#39ff6e' };
  const c = map[sev] || '#8899aa';
  return (
    <span style={{
      background:`${c}22`, color:c, border:`1px solid ${c}55`,
      padding:'2px 8px', borderRadius:3, fontSize:10, fontWeight:700,
      letterSpacing:1, fontFamily:'var(--font-mono)', whiteSpace:'nowrap',
    }}>{sev}</span>
  );
}

function StatCard({ label, value, icon:Icon, accent, sub }) {
  return (
    <div style={{
      background:'var(--card)', border:'1px solid var(--border)',
      borderTop:`2px solid ${accent}`, borderRadius:6, padding:'18px 20px',
      display:'flex', flexDirection:'column', gap:6,
    }}>
      <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center' }}>
        <span style={{ color:'var(--text2)', fontSize:11, letterSpacing:1, textTransform:'uppercase' }}>{label}</span>
        <Icon size={16} color={accent} />
      </div>
      <div style={{ fontSize:28, fontWeight:800, fontFamily:'var(--font-head)', color:accent }}>{value ?? 0}</div>
      {sub && <div style={{ color:'var(--text3)', fontSize:11 }}>{sub}</div>}
    </div>
  );
}

function KDot({ status }) {
  const c = status==='connected' ? '#39ff6e' : status==='connecting' ? '#ffe600' : '#ff3d5a';
  return (
    <span style={{
      display:'inline-block', width:8, height:8, borderRadius:'50%',
      background:c, boxShadow:status==='connected'?`0 0 6px ${c}`:'none',
      marginRight:6, flexShrink:0,
    }} />
  );
}

function Empty({ msg='No data yet' }) {
  return (
    <div style={{ padding:'40px', color:'var(--text3)', textAlign:'center', fontFamily:'var(--font-mono)' }}>
      {msg}
    </div>
  );
}

function SectionHeader({ children }) {
  return (
    <div style={{
      padding:'10px 20px', borderBottom:'1px solid var(--border)',
      fontSize:10, letterSpacing:1.5, color:'var(--text3)',
      textTransform:'uppercase', fontFamily:'var(--font-mono)',
    }}>{children}</div>
  );
}

const TT_STYLE = {
  background:'#131c26', border:'1px solid #1e2d3d',
  fontSize:11, fontFamily:'var(--font-mono)', color:'#e2eaf2',
};

// ══════════════════════════════════════════════════════════════════════════
// PAGE: Dashboard
// ══════════════════════════════════════════════════════════════════════════
function Dashboard({ stats, alerts }) {
  const [history, setHistory] = useState([{ t:'start', attacks:0, normal:0 }]);

  useEffect(() => {
    if (!stats) return;
    const now = new Date().toLocaleTimeString('en',{ hour12:false });
    setHistory(h => [...h.slice(-29), {
      t:now, attacks:stats.total_alerts??0, normal:stats.total_normal??0,
    }]);
  }, [stats]);

  const total  = (stats?.total_alerts??0) + (stats?.total_normal??0);
  const atkPct = total > 0 ? ((stats.total_alerts/total)*100).toFixed(1) : '0.0';
  const pieData = [
    { name:'Normal', value:Math.max(stats?.total_normal??0, 1), color:'#39ff6e' },
    { name:'Attack', value:Math.max(stats?.total_alerts??0, 0), color:'#ff3d5a' },
  ];

  return (
    <div style={{ display:'flex', flexDirection:'column', gap:20 }}>
      <div style={{ display:'grid', gridTemplateColumns:'repeat(4,1fr)', gap:14 }}>
        <StatCard label="Total Attacks"   value={stats?.total_alerts??0} icon={AlertTriangle} accent="#ff3d5a" sub="since startup" />
        <StatCard label="Normal Flows"    value={stats?.total_normal??0} icon={Activity}      accent="#39ff6e" sub="classified safe" />
        <StatCard label="Blacklisted IPs" value={stats?.blacklisted??0}  icon={Shield}        accent="#ff8c42" sub="auto-blocked" />
        <StatCard label="Attack Rate"     value={`${atkPct}%`}           icon={Zap}           accent="#00e5ff" sub={`of ${total.toLocaleString()} flows`} />
      </div>

      <div style={{ display:'grid', gridTemplateColumns:'2fr 1fr', gap:14 }}>
        <div style={{ background:'var(--card)', border:'1px solid var(--border)', borderRadius:6 }}>
          <SectionHeader>Traffic Timeline (live)</SectionHeader>
          <div style={{ padding:'16px 20px 8px' }}>
            <ResponsiveContainer width="100%" height={200}>
              <AreaChart data={history} margin={{ top:5, right:10, left:-20, bottom:0 }}>
                <defs>
                  <linearGradient id="gA" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%"  stopColor="#ff3d5a" stopOpacity={0.4} />
                    <stop offset="95%" stopColor="#ff3d5a" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="gN" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%"  stopColor="#39ff6e" stopOpacity={0.25} />
                    <stop offset="95%" stopColor="#39ff6e" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <XAxis dataKey="t" tick={{ fontSize:9, fill:'#4a5a6a' }} interval="preserveStartEnd" />
                <YAxis tick={{ fontSize:9, fill:'#4a5a6a' }} allowDecimals={false} />
                <Tooltip contentStyle={TT_STYLE} />
                <Area type="monotone" dataKey="attacks" name="Attacks" stroke="#ff3d5a" strokeWidth={2} fill="url(#gA)" dot={false} />
                <Area type="monotone" dataKey="normal"  name="Normal"  stroke="#39ff6e" strokeWidth={1} fill="url(#gN)" dot={false} />
              </AreaChart>
            </ResponsiveContainer>
            <div style={{ display:'flex', gap:16, justifyContent:'flex-end', marginTop:4 }}>
              <span style={{ fontSize:10, color:'#ff3d5a' }}>● Attacks</span>
              <span style={{ fontSize:10, color:'#39ff6e' }}>● Normal</span>
            </div>
          </div>
        </div>

        <div style={{ background:'var(--card)', border:'1px solid var(--border)', borderRadius:6 }}>
          <SectionHeader>Traffic Mix</SectionHeader>
          <div style={{ padding:'16px 20px 8px' }}>
            <ResponsiveContainer width="100%" height={200}>
              <PieChart>
                <Pie data={pieData} cx="50%" cy="50%" innerRadius={55} outerRadius={80}
                  dataKey="value" paddingAngle={3} strokeWidth={0}>
                  {pieData.map((d,i) => <Cell key={i} fill={d.color} />)}
                </Pie>
                <Tooltip contentStyle={TT_STYLE} formatter={(v,n) => [`${v.toLocaleString()} flows`, n]} />
              </PieChart>
            </ResponsiveContainer>
            <div style={{ display:'flex', justifyContent:'center', gap:20, marginTop:4 }}>
              {pieData.map(d => (
                <div key={d.name} style={{ textAlign:'center' }}>
                  <div style={{ fontSize:10, color:d.color }}>● {d.name}</div>
                  <div style={{ fontSize:16, fontWeight:800, color:d.color, fontFamily:'var(--font-head)' }}>
                    {d.value.toLocaleString()}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      <div style={{ background:'var(--card)', border:'1px solid var(--border)', borderRadius:6 }}>
        <SectionHeader>Recent Alerts</SectionHeader>
        {alerts.length === 0 ? <Empty msg="No attacks detected yet — system is monitoring" /> : (
          <div style={{ maxHeight:240, overflowY:'auto' }}>
            <div style={{
              display:'grid', gridTemplateColumns:'150px 130px 1fr 100px 80px',
              gap:12, padding:'8px 20px', borderBottom:'1px solid var(--border)',
              fontSize:10, letterSpacing:1, color:'var(--text3)', textTransform:'uppercase',
            }}>
              <span>Time</span><span>Source IP</span><span>Label</span><span>Severity</span>
              <span style={{ textAlign:'right' }}>Conf.</span>
            </div>
            {alerts.slice(0,20).map((a,i) => (
              <div key={i} style={{
                display:'grid', gridTemplateColumns:'150px 130px 1fr 100px 80px',
                gap:12, padding:'9px 20px', alignItems:'center',
                borderBottom:'1px solid var(--border)',
                background: i===0 ? '#ff3d5a08' : 'transparent',
              }}>
                <span style={{ color:'var(--text3)', fontSize:11 }}>{a.timestamp}</span>
                <span style={{ color:'#00e5ff', fontFamily:'var(--font-mono)', fontSize:12 }}>{a.src_ip}</span>
                <span style={{ color:'#ff3d5a' }}>{a.label}</span>
                <Badge sev={a.severity} />
                <span style={{ color:'var(--text2)', textAlign:'right' }}>{((a.confidence??0)*100).toFixed(1)}%</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ══════════════════════════════════════════════════════════════════════════
// PAGE: Alerts
// ══════════════════════════════════════════════════════════════════════════
function Alerts({ alerts }) {
  const [filter, setFilter] = useState('ALL');
  const sevs = ['ALL','CRITICAL','HIGH','MEDIUM','LOW'];
  const filtered = filter==='ALL' ? alerts : alerts.filter(a => a.severity===filter);
  return (
    <div style={{ display:'flex', flexDirection:'column', gap:16 }}>
      <div style={{ display:'flex', gap:8, flexWrap:'wrap', alignItems:'center' }}>
        {sevs.map(s => (
          <button key={s} onClick={() => setFilter(s)} style={{
            padding:'6px 14px', borderRadius:4, cursor:'pointer',
            fontSize:11, letterSpacing:1, fontFamily:'var(--font-mono)',
            border:`1px solid ${filter===s?'#00e5ff':'var(--border)'}`,
            background:filter===s?'#00e5ff22':'var(--card)',
            color:filter===s?'#00e5ff':'var(--text2)',
          }}>{s}</button>
        ))}
        <span style={{ marginLeft:'auto', color:'var(--text3)', fontSize:11 }}>{filtered.length} events</span>
      </div>
      <div style={{ background:'var(--card)', border:'1px solid var(--border)', borderRadius:6 }}>
        <div style={{
          display:'grid', gridTemplateColumns:'40px 150px 130px 1fr 100px 90px',
          gap:12, padding:'10px 20px', borderBottom:'1px solid var(--border)',
          fontSize:10, letterSpacing:1, color:'var(--text3)', textTransform:'uppercase',
        }}>
          <span>#</span><span>Time</span><span>Source IP</span>
          <span>Label</span><span>Severity</span><span style={{ textAlign:'right' }}>Confidence</span>
        </div>
        <div style={{ maxHeight:'calc(100vh - 280px)', overflowY:'auto' }}>
          {filtered.length===0 ? <Empty msg="No alerts match filter" /> :
            filtered.map((a,i) => (
              <div key={i} style={{
                display:'grid', gridTemplateColumns:'40px 150px 130px 1fr 100px 90px',
                gap:12, padding:'10px 20px', alignItems:'center',
                borderBottom:'1px solid var(--border)',
              }}>
                <span style={{ color:'var(--text3)' }}>{a.id}</span>
                <span style={{ color:'var(--text3)', fontSize:11 }}>{a.timestamp}</span>
                <span style={{ color:'#00e5ff', fontFamily:'var(--font-mono)' }}>{a.src_ip}</span>
                <span style={{ color:'#ff3d5a' }}>{a.label}</span>
                <Badge sev={a.severity} />
                <span style={{ color:'var(--text2)', textAlign:'right' }}>{((a.confidence??0)*100).toFixed(2)}%</span>
              </div>
            ))
          }
        </div>
      </div>
    </div>
  );
}

// ══════════════════════════════════════════════════════════════════════════
// PAGE: Blacklist
// ══════════════════════════════════════════════════════════════════════════
function Blacklist() {
  const [data, setData] = useState([]);
  useEffect(() => {
    const load = () => api('/api/blacklist').then(d => d && setData(d));
    load(); const id=setInterval(load,5000); return ()=>clearInterval(id);
  }, []);
  return (
    <div style={{ display:'flex', flexDirection:'column', gap:16 }}>
      <div style={{ display:'flex', alignItems:'center', gap:10 }}>
        <Shield size={18} color="#ff8c42" />
        <span style={{ fontFamily:'var(--font-head)', fontSize:16, fontWeight:700 }}>Blacklisted IPs</span>
        <span style={{ background:'#ff3d5a22', color:'#ff3d5a', border:'1px solid #ff3d5a55', padding:'2px 10px', borderRadius:3, fontSize:11 }}>
          {data.length} blocked
        </span>
      </div>
      <div style={{ background:'var(--card)', border:'1px solid var(--border)', borderRadius:6 }}>
        <div style={{
          display:'grid', gridTemplateColumns:'1fr 120px 180px 180px', gap:12,
          padding:'10px 20px', borderBottom:'1px solid var(--border)',
          fontSize:10, letterSpacing:1, color:'var(--text3)', textTransform:'uppercase',
        }}>
          <span>IP Address</span><span>Count</span><span>First Seen</span><span>Last Seen</span>
        </div>
        <div style={{ maxHeight:'calc(100vh - 260px)', overflowY:'auto' }}>
          {data.length===0 ? <Empty msg="No IPs blacklisted yet" /> :
            data.map((d,i) => (
              <div key={i} style={{
                display:'grid', gridTemplateColumns:'1fr 120px 180px 180px',
                gap:12, padding:'12px 20px', alignItems:'center',
                borderBottom:'1px solid var(--border)',
              }}>
                <span style={{ color:'#ff3d5a', fontFamily:'var(--font-mono)', display:'flex', alignItems:'center', gap:8 }}>
                  <span style={{ width:6, height:6, borderRadius:'50%', background:'#ff3d5a', display:'inline-block', flexShrink:0 }} />
                  {d.ip}
                </span>
                <span style={{ color:'#ffe600', fontWeight:700 }}>{d.count}</span>
                <span style={{ color:'var(--text3)', fontSize:11 }}>{d.first_seen}</span>
                <span style={{ color:'var(--text2)', fontSize:11 }}>{d.last_seen}</span>
              </div>
            ))
          }
        </div>
      </div>
    </div>
  );
}

// ══════════════════════════════════════════════════════════════════════════
// PAGE: Kafka Monitor
// ══════════════════════════════════════════════════════════════════════════
function KafkaMonitor() {
  const [data, setData] = useState({ raw_flows:[], predictions:[], status:{} });
  const [tab, setTab]   = useState('predictions');
  useEffect(() => {
    const load = () => api('/api/kafka').then(d => d && setData(d));
    load(); const id=setInterval(load,2000); return ()=>clearInterval(id);
  }, []);
  const msgs = tab==='predictions' ? data.predictions : data.raw_flows;
  return (
    <div style={{ display:'flex', flexDirection:'column', gap:16 }}>
      <div style={{ display:'flex', gap:12 }}>
        {['raw_flows','predictions'].map(t => (
          <div key={t} style={{
            background:'var(--card)', border:'1px solid var(--border)',
            borderRadius:6, padding:'10px 16px', display:'flex', alignItems:'center', gap:8,
          }}>
            <KDot status={data.status[t]||'connecting'} />
            <span style={{ fontFamily:'var(--font-mono)', fontSize:12 }}>{t}</span>
            <span style={{ color:'var(--text3)', fontSize:11 }}>{data.status[t]||'connecting'}</span>
          </div>
        ))}
      </div>
      <div style={{ display:'flex', gap:8 }}>
        {['predictions','raw_flows'].map(t => (
          <button key={t} onClick={() => setTab(t)} style={{
            padding:'6px 16px', borderRadius:4, cursor:'pointer',
            fontSize:11, letterSpacing:1, fontFamily:'var(--font-mono)',
            border:`1px solid ${tab===t?'#00e5ff':'var(--border)'}`,
            background:tab===t?'#00e5ff22':'var(--card)',
            color:tab===t?'#00e5ff':'var(--text2)',
          }}>{t}</button>
        ))}
        <span style={{ marginLeft:'auto', color:'var(--text3)', fontSize:11, lineHeight:'32px' }}>
          {msgs.length} messages buffered
        </span>
      </div>
      <div style={{
        background:'var(--bg2)', border:'1px solid var(--border)', borderRadius:6,
        padding:16, maxHeight:'calc(100vh - 320px)', overflowY:'auto',
        fontFamily:'var(--font-mono)', fontSize:11,
      }}>
        {msgs.length===0
          ? <span style={{ color:'var(--text3)' }}>Waiting for messages on topic: {tab}</span>
          : msgs.map((m,i) => (
            <div key={i} style={{
              marginBottom:6, padding:'8px 12px',
              background: m.label==='Attack' ? '#ff3d5a0d' : '#ffffff05',
              border:`1px solid ${m.label==='Attack'?'#ff3d5a33':'var(--border)'}`,
              borderRadius:4,
            }}>
              <span style={{ color:'var(--text3)' }}>{m.timestamp}  </span>
              <span style={{ color:'#00e5ff' }}>{m.src_ip||'—'}  </span>
              {m.label && <span style={{ color:m.label==='Attack'?'#ff3d5a':'#39ff6e' }}>→ {m.label}  </span>}
              {m.confidence!=null && <span style={{ color:'var(--text2)' }}>({(m.confidence*100).toFixed(1)}%)</span>}
              {m.features && <span style={{ color:'var(--text3)' }}> [{m.features.slice(0,4).map(v=>Number(v).toFixed(2)).join(', ')}...]</span>}
            </div>
          ))
        }
      </div>
    </div>
  );
}

// ══════════════════════════════════════════════════════════════════════════
// PAGE: Log Viewer
// ══════════════════════════════════════════════════════════════════════════
function LogViewer() {
  const [logs, setLogs]     = useState([]);
  const [search, setSearch] = useState('');
  useEffect(() => {
    const load = () => api('/api/logs').then(d => d && setLogs(d));
    load(); const id=setInterval(load,5000); return ()=>clearInterval(id);
  }, []);
  const filtered = search ? logs.filter(l => JSON.stringify(l).toLowerCase().includes(search.toLowerCase())) : logs;
  return (
    <div style={{ display:'flex', flexDirection:'column', gap:16 }}>
      <input placeholder="Search by IP, severity, attack type..."
        value={search} onChange={e => setSearch(e.target.value)}
        style={{
          background:'var(--card)', border:'1px solid var(--border)',
          borderRadius:4, padding:'9px 14px', color:'var(--text)',
          fontFamily:'var(--font-mono)', fontSize:12, outline:'none', width:'100%',
        }}
      />
      <div style={{ background:'var(--card)', border:'1px solid var(--border)', borderRadius:6 }}>
        <div style={{
          display:'grid', gridTemplateColumns:'160px 120px 1fr 90px 70px', gap:12,
          padding:'10px 20px', borderBottom:'1px solid var(--border)',
          fontSize:10, letterSpacing:1, color:'var(--text3)', textTransform:'uppercase',
        }}>
          <span>Timestamp</span><span>Source IP</span><span>Attack Type</span>
          <span>Severity</span><span style={{ textAlign:'right' }}>Score</span>
        </div>
        <div style={{ maxHeight:'calc(100vh - 280px)', overflowY:'auto' }}>
          {filtered.length===0
            ? <Empty msg={logs.length===0?'No log entries yet':'No entries match search'} />
            : filtered.map((l,i) => (
              <div key={i} style={{
                display:'grid', gridTemplateColumns:'160px 120px 1fr 90px 70px',
                gap:12, padding:'9px 20px', alignItems:'center',
                borderBottom:'1px solid var(--border)',
              }}>
                <span style={{ color:'var(--text3)', fontSize:11 }}>{l.timestamp}</span>
                <span style={{ color:'#00e5ff', fontFamily:'var(--font-mono)' }}>{l.src_ip}</span>
                <span style={{ color:'#ff3d5a' }}>{l.attack_type}</span>
                <Badge sev={l.severity} />
                <span style={{ color:'#ffe600', textAlign:'right', fontWeight:700 }}>{l.threat_score?.toFixed(1)??'—'}</span>
              </div>
            ))
          }
        </div>
      </div>
    </div>
  );
}

// ══════════════════════════════════════════════════════════════════════════
// PAGE: Models
// ══════════════════════════════════════════════════════════════════════════
function Models() {
  const [models,   setModels]   = useState([]);
  const [accuracy, setAccuracy] = useState(null);
  useEffect(() => {
    api('/api/models').then(d => d && setModels(d));
    api('/api/accuracy').then(d => d && setAccuracy(d));
  }, []);

  const mc = v => v>=0.95?'#39ff6e':v>=0.85?'#ffe600':'#ff3d5a';
  const metrics = accuracy ? [
    { label:'Accuracy',  value:accuracy.ensemble.accuracy  },
    { label:'F1 Score',  value:accuracy.ensemble.f1_score  },
    { label:'ROC-AUC',   value:accuracy.ensemble.roc_auc   },
    { label:'Precision', value:accuracy.ensemble.precision  },
    { label:'Recall',    value:accuracy.ensemble.recall     },
  ] : [];
  const cm = accuracy?.confusion_matrix;

  return (
    <div style={{ display:'flex', flexDirection:'column', gap:20 }}>
      {accuracy && (
        <>
          <div style={{ fontSize:11, fontWeight:700, color:'var(--text3)', letterSpacing:1.5, textTransform:'uppercase' }}>
            Ensemble Performance
          </div>
          <div style={{ display:'grid', gridTemplateColumns:'repeat(5,1fr)', gap:12 }}>
            {metrics.map(m => (
              <div key={m.label} style={{
                background:'var(--card)', border:'1px solid var(--border)',
                borderTop:`2px solid ${mc(m.value)}`, borderRadius:6, padding:'16px', textAlign:'center',
              }}>
                <div style={{ fontSize:24, fontWeight:800, fontFamily:'var(--font-head)', color:mc(m.value) }}>
                  {(m.value*100).toFixed(2)}%
                </div>
                <div style={{ fontSize:10, letterSpacing:1, color:'var(--text3)', textTransform:'uppercase', marginTop:6 }}>
                  {m.label}
                </div>
              </div>
            ))}
          </div>

          <div style={{ background:'var(--card)', border:'1px solid var(--border)', borderRadius:6 }}>
            <SectionHeader>Metric Comparison</SectionHeader>
            <div style={{ padding:'16px 20px 8px' }}>
              <ResponsiveContainer width="100%" height={180}>
                <BarChart data={metrics} margin={{ top:5, right:10, left:-10, bottom:0 }}>
                  <XAxis dataKey="label" tick={{ fontSize:10, fill:'#8899aa' }} />
                  <YAxis domain={[0.88,1]} tick={{ fontSize:10, fill:'#8899aa' }} tickFormatter={v=>`${(v*100).toFixed(0)}%`} />
                  <Tooltip contentStyle={TT_STYLE} formatter={v=>[`${(v*100).toFixed(2)}%`]} />
                  <Bar dataKey="value" radius={[4,4,0,0]}>
                    {metrics.map((m,i) => <Cell key={i} fill={mc(m.value)} />)}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {cm && (
            <div style={{ background:'var(--card)', border:'1px solid var(--border)', borderRadius:6 }}>
              <SectionHeader>Confusion Matrix — 386,046 test samples</SectionHeader>
              <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:10, maxWidth:420, margin:'16px 20px' }}>
                {[
                  { label:'True Negatives',  value:cm.tn, color:'#39ff6e', desc:'Normal → Normal' },
                  { label:'False Positives', value:cm.fp, color:'#ffe600', desc:'Normal → Attack' },
                  { label:'False Negatives', value:cm.fn, color:'#ff8c42', desc:'Attack → Normal' },
                  { label:'True Positives',  value:cm.tp, color:'#00e5ff', desc:'Attack → Attack' },
                ].map(c => (
                  <div key={c.label} style={{
                    background:`${c.color}11`, border:`1px solid ${c.color}44`,
                    borderRadius:6, padding:'14px 16px',
                  }}>
                    <div style={{ fontSize:22, fontWeight:800, fontFamily:'var(--font-head)', color:c.color }}>
                      {c.value.toLocaleString()}
                    </div>
                    <div style={{ fontSize:11, color:c.color, opacity:0.8, marginTop:3 }}>{c.label}</div>
                    <div style={{ fontSize:10, color:'var(--text3)', marginTop:3 }}>{c.desc}</div>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div style={{
            background:'var(--card)', border:'1px solid var(--border)',
            borderLeft:'3px solid #00e5ff', borderRadius:6,
            padding:'12px 16px', fontSize:12, color:'var(--text2)',
          }}>
            <span style={{ color:'#00e5ff', fontWeight:700 }}>Voting Strategy: </span>
            {accuracy.voting}
          </div>
        </>
      )}

      <div style={{ fontSize:11, fontWeight:700, color:'var(--text3)', letterSpacing:1.5, textTransform:'uppercase' }}>
        Individual Models
      </div>
      <div style={{ display:'grid', gridTemplateColumns:'repeat(3,1fr)', gap:14 }}>
        {(models.length===0
          ? [{name:'Random Forest',status:'loading',params:{}},{name:'SGD Classifier',status:'loading',params:{}},{name:'Extra Trees',status:'loading',params:{}}]
          : models
        ).map((m,i) => (
          <div key={i} style={{
            background:'var(--card)', border:'1px solid var(--border)',
            borderTop:'2px solid #00e5ff', borderRadius:6, padding:'16px 20px',
          }}>
            <div style={{ display:'flex', justifyContent:'space-between', marginBottom:14 }}>
              <span style={{ fontFamily:'var(--font-head)', fontWeight:700, fontSize:14 }}>{m.name}</span>
              <span style={{
                fontSize:10, padding:'2px 8px', borderRadius:3,
                background:m.status==='loaded'?'#39ff6e22':'#ffe60022',
                color:m.status==='loaded'?'#39ff6e':'#ffe600',
                border:`1px solid ${m.status==='loaded'?'#39ff6e':'#ffe600'}55`,
              }}>{m.status}</span>
            </div>
            {m.size_mb!=null && (
              <div style={{ fontSize:11, color:'var(--text3)', marginBottom:12 }}>
                File size: <span style={{ color:'#ffe600' }}>{m.size_mb} MB</span>
              </div>
            )}
            <div style={{ display:'flex', flexDirection:'column', gap:6 }}>
              {Object.entries(m.params||{}).map(([k,v]) => (
                <div key={k} style={{ display:'flex', justifyContent:'space-between', fontSize:11, gap:8 }}>
                  <span style={{ color:'var(--text3)' }}>{k}</span>
                  <span style={{ color:'var(--text)', fontFamily:'var(--font-mono)', textAlign:'right' }}>{v}</span>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ══════════════════════════════════════════════════════════════════════════
// PAGE: Session History (MongoDB)
// ══════════════════════════════════════════════════════════════════════════
function SessionHistory({ sessionId, sessionInfo }) {
  const [history, setHistory] = useState(null);
  const [tab, setTab]         = useState('attacks');
  const [dbStats, setDbStats] = useState(null);

  useEffect(() => {
    if (!sessionId) return;
    api(`/api/session/history?session_id=${sessionId}`).then(d => d && setHistory(d));
    api('/api/db/stats').then(d => d && setDbStats(d));
  }, [sessionId]);

  const records = tab==='attacks' ? (history?.alerts||[]) : (history?.normal||[]);

  return (
    <div style={{ display:'flex', flexDirection:'column', gap:20 }}>

      {/* Session info card */}
      <div style={{ display:'grid', gridTemplateColumns:'repeat(4,1fr)', gap:14 }}>
        <div style={{
          background:'var(--card)', border:'1px solid var(--border)',
          borderTop:'2px solid #00e5ff', borderRadius:6, padding:'16px 20px',
        }}>
          <div style={{ fontSize:10, color:'var(--text3)', letterSpacing:1, textTransform:'uppercase', marginBottom:8 }}>Session ID</div>
          <div style={{ fontSize:14, fontWeight:700, color:'#00e5ff', fontFamily:'var(--font-mono)' }}>
            {sessionId || '—'}
          </div>
          <div style={{ fontSize:10, color:'var(--text3)', marginTop:6 }}>browser fingerprint</div>
        </div>

        <div style={{
          background:'var(--card)', border:'1px solid var(--border)',
          borderTop:'2px solid #ffe600', borderRadius:6, padding:'16px 20px',
        }}>
          <div style={{ fontSize:10, color:'var(--text3)', letterSpacing:1, textTransform:'uppercase', marginBottom:8 }}>Visit Count</div>
          <div style={{ fontSize:28, fontWeight:800, fontFamily:'var(--font-head)', color:'#ffe600' }}>
            {sessionInfo?.visit_count ?? '—'}
          </div>
          <div style={{ fontSize:10, color:'var(--text3)', marginTop:6 }}>
            {sessionInfo?.new ? 'first visit' : 'returning user'}
          </div>
        </div>

        <div style={{
          background:'var(--card)', border:'1px solid var(--border)',
          borderTop:'2px solid #ff3d5a', borderRadius:6, padding:'16px 20px',
        }}>
          <div style={{ fontSize:10, color:'var(--text3)', letterSpacing:1, textTransform:'uppercase', marginBottom:8 }}>Attacks Stored</div>
          <div style={{ fontSize:28, fontWeight:800, fontFamily:'var(--font-head)', color:'#ff3d5a' }}>
            {history?.stats?.total_attacks ?? '—'}
          </div>
          <div style={{ fontSize:10, color:'var(--text3)', marginTop:6 }}>in MongoDB</div>
        </div>

        <div style={{
          background:'var(--card)', border:'1px solid var(--border)',
          borderTop:'2px solid #39ff6e', borderRadius:6, padding:'16px 20px',
        }}>
          <div style={{ fontSize:10, color:'var(--text3)', letterSpacing:1, textTransform:'uppercase', marginBottom:8 }}>Normal Stored</div>
          <div style={{ fontSize:28, fontWeight:800, fontFamily:'var(--font-head)', color:'#39ff6e' }}>
            {history?.stats?.total_normal ?? '—'}
          </div>
          <div style={{ fontSize:10, color:'var(--text3)', marginTop:6 }}>in MongoDB</div>
        </div>
      </div>

      {/* Session timestamps */}
      {sessionInfo && !sessionInfo.new && (
        <div style={{
          background:'var(--card)', border:'1px solid var(--border)',
          borderLeft:'3px solid #00e5ff', borderRadius:6, padding:'12px 16px',
          display:'flex', gap:32, fontSize:12,
        }}>
          <div>
            <span style={{ color:'var(--text3)' }}>First visit: </span>
            <span style={{ color:'#00e5ff' }}>{sessionInfo.created_at?.slice(0,19).replace('T',' ')}</span>
          </div>
          <div>
            <span style={{ color:'var(--text3)' }}>Last seen: </span>
            <span style={{ color:'#00e5ff' }}>{sessionInfo.last_seen?.slice(0,19).replace('T',' ')}</span>
          </div>
        </div>
      )}

      {/* Global DB stats */}
      {dbStats && (
        <div style={{
          background:'var(--card)', border:'1px solid var(--border)',
          borderRadius:6, padding:'14px 20px',
          display:'flex', gap:32, alignItems:'center',
        }}>
          <Database size={16} color="var(--text3)" />
          <div style={{ fontSize:11, color:'var(--text3)' }}>
            MongoDB totals:
            <span style={{ color:'#ff3d5a', marginLeft:12, fontWeight:700 }}>{dbStats.total_attacks_stored} attacks</span>
            <span style={{ color:'#39ff6e', marginLeft:12, fontWeight:700 }}>{dbStats.total_normal_stored} normal</span>
            <span style={{ color:'#00e5ff', marginLeft:12, fontWeight:700 }}>{dbStats.total_sessions} sessions</span>
          </div>
        </div>
      )}

      {/* Tab switch */}
      <div style={{ display:'flex', gap:8 }}>
        {['attacks','normal'].map(t => (
          <button key={t} onClick={() => setTab(t)} style={{
            padding:'6px 16px', borderRadius:4, cursor:'pointer',
            fontSize:11, letterSpacing:1, fontFamily:'var(--font-mono)',
            border:`1px solid ${tab===t?'#00e5ff':'var(--border)'}`,
            background:tab===t?'#00e5ff22':'var(--card)',
            color:tab===t?'#00e5ff':'var(--text2)',
          }}>{t === 'attacks' ? `Attacks (${history?.stats?.total_attacks??0})` : `Normal Flows (${history?.stats?.total_normal??0})`}</button>
        ))}
      </div>

      {/* History table */}
      <div style={{ background:'var(--card)', border:'1px solid var(--border)', borderRadius:6 }}>
        <SectionHeader>
          {tab === 'attacks' ? 'Attack History from MongoDB' : 'Normal Flow History from MongoDB'}
        </SectionHeader>
        {tab === 'attacks' ? (
          <div style={{ maxHeight:'calc(100vh - 480px)', overflowY:'auto' }}>
            {records.length===0 ? <Empty msg="No attack history stored yet" /> :
              records.map((r,i) => (
                <div key={i} style={{
                  display:'grid', gridTemplateColumns:'170px 130px 1fr 100px 90px',
                  gap:12, padding:'10px 20px', alignItems:'center',
                  borderBottom:'1px solid var(--border)',
                }}>
                  <span style={{ color:'var(--text3)', fontSize:11 }}>{r.timestamp}</span>
                  <span style={{ color:'#00e5ff', fontFamily:'var(--font-mono)' }}>{r.src_ip}</span>
                  <span style={{ color:'#ff3d5a' }}>{r.label}</span>
                  <Badge sev={r.severity} />
                  <span style={{ color:'var(--text2)', textAlign:'right' }}>{((r.confidence??0)*100).toFixed(1)}%</span>
                </div>
              ))
            }
          </div>
        ) : (
          <div style={{ maxHeight:'calc(100vh - 480px)', overflowY:'auto' }}>
            {records.length===0 ? <Empty msg="No normal flow history stored yet" /> :
              records.map((r,i) => (
                <div key={i} style={{
                  display:'grid', gridTemplateColumns:'170px 130px 1fr 90px',
                  gap:12, padding:'10px 20px', alignItems:'center',
                  borderBottom:'1px solid var(--border)',
                }}>
                  <span style={{ color:'var(--text3)', fontSize:11 }}>{r.timestamp}</span>
                  <span style={{ color:'#00e5ff', fontFamily:'var(--font-mono)' }}>{r.src_ip}</span>
                  <span style={{ color:'#39ff6e' }}>{r.label}</span>
                  <span style={{ color:'var(--text2)', textAlign:'right' }}>{((r.confidence??0)*100).toFixed(1)}%</span>
                </div>
              ))
            }
          </div>
        )}
      </div>
    </div>
  );
}

// ══════════════════════════════════════════════════════════════════════════
// SIDEBAR + APP SHELL
// ══════════════════════════════════════════════════════════════════════════
const NAV = [
  { id:'dashboard', label:'Dashboard',     icon:LayoutDashboard },
  { id:'alerts',    label:'Alerts',        icon:Bell },
  { id:'blacklist', label:'Blacklist',     icon:Shield },
  { id:'kafka',     label:'Kafka Monitor', icon:Activity },
  { id:'logs',      label:'Log Viewer',    icon:FileText },
  { id:'models',    label:'Models',        icon:Cpu },
  { id:'history',   label:'History',       icon:History },
];

export default function App() {
  const [page,        setPage]        = useState('dashboard');
  const [stats,       setStats]       = useState(null);
  const [alerts,      setAlerts]      = useState([]);
  const [sessionId,   setSessionId]   = useState(null);
  const [sessionInfo, setSessionInfo] = useState(null);

  // ── Fingerprint + session load ──────────────────────────────────────────
  useEffect(() => {
    const fp = getFingerprint();
    setSessionId(fp);

    postApi('/api/session/load', { session_id: fp })
      .then(d => {
        if (d) {
          setSessionInfo(d);
          console.log(
            d.new
              ? `[HIDS] New session created: ${fp}`
              : `[HIDS] Welcome back! Visit #${d.visit_count} — session: ${fp}`
          );
        }
      });
  }, []);

  // ── Polling ─────────────────────────────────────────────────────────────
  useEffect(() => {
    const load = () => {
      api('/api/stats').then(d  => d && setStats(d));
      api('/api/alerts').then(d => d && setAlerts(d));
    };
    load();
    const id = setInterval(load, 3000);
    return () => clearInterval(id);
  }, []);

  const PageMap = {
    dashboard: Dashboard,
    alerts:    Alerts,
    blacklist: Blacklist,
    kafka:     KafkaMonitor,
    logs:      LogViewer,
    models:    Models,
    history:   SessionHistory,
  };
  const Page    = PageMap[page] || Dashboard;
  const critCnt = alerts.filter(a => a.severity==='CRITICAL').length;
  const apiOk   = stats !== null;

  return (
    <div style={{ display:'flex', height:'100vh', overflow:'hidden', background:'var(--bg)' }}>

      {/* ── Sidebar ── */}
      <aside style={{
        width:224, flexShrink:0, background:'var(--bg2)',
        borderRight:'1px solid var(--border)', display:'flex', flexDirection:'column',
      }}>
        {/* Logo */}
        <div style={{ padding:'20px 20px 16px', borderBottom:'1px solid var(--border)' }}>
          <div style={{ fontFamily:'var(--font-head)', fontWeight:800, fontSize:20, color:'#00e5ff', letterSpacing:3, display:'flex', alignItems:'center', gap:10 }}>
            <Eye size={22} color="#00e5ff" /> HIDS
          </div>
          <div style={{ fontSize:9, color:'var(--text3)', letterSpacing:2, marginTop:3 }}>INTRUSION DETECTION SYSTEM</div>
        </div>

        {/* Session ID */}
        <div style={{ padding:'10px 20px', borderBottom:'1px solid var(--border)' }}>
          <div style={{ fontSize:9, letterSpacing:1.5, color:'var(--text3)', marginBottom:6, textTransform:'uppercase' }}>Session</div>
          <div style={{ fontFamily:'var(--font-mono)', fontSize:11, color:'#00e5ff', marginBottom:4 }}>
            {sessionId || 'loading...'}
          </div>
          <div style={{ fontSize:10, color:'var(--text3)' }}>
            {sessionInfo?.new ? '● new user' : `● visit #${sessionInfo?.visit_count ?? '—'}`}
          </div>
        </div>

        {/* Kafka status */}
        <div style={{ padding:'10px 20px 12px', borderBottom:'1px solid var(--border)' }}>
          <div style={{ fontSize:9, letterSpacing:1.5, color:'var(--text3)', marginBottom:8, textTransform:'uppercase' }}>Kafka Topics</div>
          {['raw_flows','predictions'].map(t => (
            <div key={t} style={{ display:'flex', alignItems:'center', marginBottom:5 }}>
              <KDot status={stats?.kafka_status?.[t]||'connecting'} />
              <span style={{ fontSize:11, color:'var(--text2)', fontFamily:'var(--font-mono)' }}>{t}</span>
            </div>
          ))}
        </div>

        {/* Nav */}
        <nav style={{ flex:1, padding:'8px 10px', overflowY:'auto' }}>
          {NAV.map(({ id, label, icon:Icon }) => {
            const active   = page===id;
            const hasBadge = id==='alerts' && critCnt>0;
            return (
              <button key={id} onClick={() => setPage(id)} style={{
                width:'100%', display:'flex', alignItems:'center', gap:10,
                padding:'9px 12px', borderRadius:5, marginBottom:2, cursor:'pointer',
                background: active?'#00e5ff18':'transparent',
                border:`1px solid ${active?'#00e5ff44':'transparent'}`,
                color: active?'#00e5ff':'var(--text2)',
                fontFamily:'var(--font-mono)', fontSize:12,
                transition:'all 0.12s', textAlign:'left',
              }}
                onMouseEnter={e => { if(!active){ e.currentTarget.style.background='#ffffff08'; e.currentTarget.style.color='var(--text)'; }}}
                onMouseLeave={e => { if(!active){ e.currentTarget.style.background='transparent'; e.currentTarget.style.color='var(--text2)'; }}}
              >
                <Icon size={15} />
                <span style={{ flex:1 }}>{label}</span>
                {hasBadge && (
                  <span style={{ background:'#ff3d5a', color:'#fff', borderRadius:10, padding:'1px 7px', fontSize:10, fontWeight:700 }}>
                    {critCnt}
                  </span>
                )}
                {active && <ChevronRight size={12} />}
              </button>
            );
          })}
        </nav>

        {/* Bottom summary */}
        <div style={{ padding:'12px 20px', borderTop:'1px solid var(--border)' }}>
          {[
            { label:'Total Alerts', value:stats?.total_alerts??'—', color:'#ff3d5a' },
            { label:'Blacklisted',  value:stats?.blacklisted??'—',  color:'#ff8c42' },
            { label:'Normal Flows', value:stats?.total_normal??'—', color:'#39ff6e' },
          ].map(r => (
            <div key={r.label} style={{ display:'flex', justifyContent:'space-between', marginBottom:5 }}>
              <span style={{ fontSize:10, color:'var(--text3)' }}>{r.label}</span>
              <span style={{ fontSize:11, color:r.color, fontWeight:700, fontFamily:'var(--font-mono)' }}>{r.value}</span>
            </div>
          ))}
        </div>
      </aside>

      {/* ── Main ── */}
      <main style={{ flex:1, display:'flex', flexDirection:'column', overflow:'hidden' }}>
        <header style={{
          padding:'0 24px', height:48, flexShrink:0,
          borderBottom:'1px solid var(--border)',
          display:'flex', alignItems:'center', justifyContent:'space-between',
          background:'var(--bg2)',
        }}>
          <div style={{ fontFamily:'var(--font-head)', fontWeight:700, fontSize:15 }}>
            {NAV.find(n => n.id===page)?.label}
          </div>
          <div style={{ display:'flex', alignItems:'center', gap:14 }}>
            <span style={{ fontSize:10, color:'var(--text3)', fontFamily:'var(--font-mono)', letterSpacing:1 }}>AUTO-REFRESH 3s</span>
            <RefreshCw size={13} color="var(--text3)" />
            <div style={{ display:'flex', alignItems:'center', gap:6 }}>
              <div style={{
                width:8, height:8, borderRadius:'50%',
                background: apiOk?'#39ff6e':'#ff3d5a',
                boxShadow: apiOk?'0 0 8px #39ff6e':'0 0 8px #ff3d5a',
              }} />
              <span style={{ fontSize:10, color:'var(--text3)', fontFamily:'var(--font-mono)' }}>
                {apiOk?'API CONNECTED':'API OFFLINE'}
              </span>
            </div>
          </div>
        </header>

        <div style={{ flex:1, overflowY:'auto', padding:'20px 24px' }}>
          <Page
            stats={stats}
            alerts={alerts}
            sessionId={sessionId}
            sessionInfo={sessionInfo}
          />
        </div>
      </main>
    </div>
  );
}
