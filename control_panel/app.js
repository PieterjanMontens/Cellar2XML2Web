/* ===== Config ===== */
const proxy = 'http://localhost:8082';
const topic  = 'cmd.query_agent';
const logTopic = 'logs.app'; 
const groupId   = 'cp-panel-' + Math.random().toString(36).slice(2,8);

/* ===== Command publisher ===== */
async function publish(date) {
  const payload = {
      value_schema: '{"type":"record","name":"Cmd","fields":[{"name":"date","type":"string"},{"name":"collection","type":"string"}]}',
    records:[
        {
            value: { date: date, collection:"OJ" }
        }
    ]
  };
  const res = await fetch(`${proxy}/topics/${topic}`, {
    method:'POST',
    headers:{ 'Content-Type':'application/vnd.kafka.avro.v2+json' },
    body: JSON.stringify(payload)
  });
  if(!res.ok) throw new Error(await res.text());
}

document.getElementById('run').addEventListener('click', async () => {
  const date = document.getElementById('date').value;
  if(!date) return alert('Pick a date!');
  try {
    await publish(date);
    log(`Triggered build for ${date}`);
  } catch(e){ log(`Error: ${e.message}`); }
});

function log(msg){
  document.getElementById('logPane').textContent += 'Local: ' + msg + '\n';
}

/* ===== Log consumer (simple long-poll loop) ===== */
let consumerBase = null;

async function initConsumer() {
  if (consumerBase) return consumerBase;           // already created

  // 1  create new consumer instance
  const create = await fetch(`${proxy}/consumers/${groupId}`, {
    method:'POST',
    headers:{ 'Content-Type':'application/vnd.kafka.v2+json' },
    body: JSON.stringify({
      name: 'ui-' + Math.random().toString(36).slice(2,8),
      format: 'binary',                  
      'auto.offset.reset': 'latest' 
    })
  });
  const { base_uri } = await create.json();

  // 2  subscribe to the logs topic
  await fetch(`${base_uri}/subscription`, {
    method:'POST',
    headers:{ 'Content-Type':'application/vnd.kafka.v2+json' },
    body: JSON.stringify({ topics:[ logTopic ] })
  });

  consumerBase = base_uri;
    
  window.addEventListener('beforeunload', async () => {
      if (consumerBase) {
          try { await fetch(consumerBase, { method:'DELETE' }); } catch(_) {}
      }
  });

  return base_uri;
}

async function pollLogs() {
  const base = await initConsumer();

  try {
    const res   = await fetch(`${base}/records`, {
      headers:{ 'Accept':'application/vnd.kafka.binary.v2+json' }
    });
    if (res.ok) {
      const records = await res.json();
      if (Array.isArray(records) && records.length) {
        records.forEach(r => log_kafka(r));
      }
    }
  } catch (err) {
    console.error('log poll failed:', err.message);
  }

  setTimeout(pollLogs, 2000);   // long-poll every 2 s
}

/* ===== UI helpers ===== */
const logPane = document.getElementById('logPane');

function log_kafka(r) {
    data = JSON.parse(atob(r.value));
    appendLog(`${data.level} ${data.component} | ${data.msg}`);
}

function appendLog(msg) {
  const ts   = new Date().toISOString().slice(11,23);
  const line = `${ts}  ${JSON.stringify(msg)}\n`;
  logPane.textContent += line;

  // Auto-scroll to bottom
  logPane.scrollTop = logPane.scrollHeight;
}

/* ===== Kick off log tail ===== */
pollLogs();
