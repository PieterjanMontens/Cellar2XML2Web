/* ============================================================================
   Config
============================================================================ */
const proxy          = 'http://localhost:8082';          // REST-Proxy
const buildTopic     = 'cmd.query_agent';                // kick off a build
const deployTopic    = 'cmd.web_agent.deploy';           // promote run to prod
const logTopic       = 'logs.app';                       // unified logs
const groupId        = 'cp-panel-' + Math.random().toString(36).slice(2,8);
const log_pol        = 500
const web_agent_host = 'http://localhost:8080'

/* ============================================================================
   DOM
============================================================================ */
const logPane         = document.getElementById('logPane');
const latestPanel     = document.getElementById('latestRunPanel');
const latestRunLinkEl = document.getElementById('latestRunLink');
const promotedLinkEl  = document.getElementById('promotedLink');
const deployBtn       = document.getElementById('deploy');

/* ============================================================================
   State
============================================================================ */
let latestRunId = null;

/* ============================================================================
   Utility: JSON Avro publisher
============================================================================ */
async function publishAvro(topic, schemaObj, value) {
  const payload = {
    value_schema: JSON.stringify(schemaObj),
    records:      [{ value }]
  };
  const res = await fetch(`${proxy}/topics/${topic}`, {
    method:'POST',
    headers:{ 'Content-Type':'application/vnd.kafka.avro.v2+json' },
    body: JSON.stringify(payload)
  });
  if (!res.ok) throw new Error(await res.text());
}

/* ============================================================================
   Build trigger
============================================================================ */
document.getElementById('run').onclick = async () => {
  const date = document.getElementById('date').value;
  if (!date) { alert('Pick a date first 🙂'); return; }

  await publishAvro(buildTopic,
    { type:'record',
      name:'Cmd',
      fields:[
        {name:'date',      type:'string'},
        {name:'collection',type:'string'}
      ]},
    { date, collection:'OJ' }
  );
  appendLog(`<span class="log_action">Triggered build for ${date}</span>`);
};

/* ============================================================================
   Deploy latest run
============================================================================ */
deployBtn.onclick = async () => {
  if (!latestRunId) { alert('No run available yet'); return; }

  await publishAvro(deployTopic,
    { type:'record',
      name:'DeployCmd',
      fields:[
        {name:'run_id', type:'string'},
        {name:'target', type:'string'}
      ]},
    { run_id: latestRunId, target:'prod' }
  );
  appendLog(`<span class="log_prod">Deploy request sent for ${latestRunId}</span>`);
};

/* ============================================================================
   Log consumer
============================================================================ */
let consumerBase = null;

async function initConsumer() {
  if (consumerBase) return consumerBase;

  /* 1. create consumer instance */
  const create = await fetch(`${proxy}/consumers/${groupId}`, {
    method:'POST',
    headers:{ 'Content-Type':'application/vnd.kafka.v2+json' },
    body: JSON.stringify({
      name:'ui-'+Math.random().toString(36).slice(2,8),
      format:'binary',
      'auto.offset.reset':'latest'
    })
  });
  const { base_uri } = await create.json();

  /* 2. subscribe */
  await fetch(`${base_uri}/subscription`, {
    method:'POST',
    headers:{ 'Content-Type':'application/vnd.kafka.v2+json' },
    body: JSON.stringify({ topics:[logTopic] })
  });

  /* 3. auto-delete on tab close */
  window.addEventListener('beforeunload', () => {
    fetch(base_uri, { method:'DELETE' });
  });

  consumerBase = base_uri;
  return base_uri;
}

async function pollLogs() {
  const base = await initConsumer();

  try {
    const res = await fetch(`${base}/records`, {
      headers:{ 'Accept':'application/vnd.kafka.binary.v2+json' }
    });
    if (res.ok) {
      const recs = await res.json();
      recs.forEach(r => handleRecord(r));
    }
  } catch (e) {
    console.error('log poll failed:', e.message);
  }

  setTimeout(pollLogs, log_pol);        // refresh every 0.5 s
}

function handleRecord(r) {
  const data = JSON.parse(atob(r.value));      // binary → JSON

  appendLog(`<span class='log_${data.level}'>${data.level}</span> ${data.component} | ${data.msg}`);

  /* Detect Web-Builder completion line:
     "Site built → /app/output/<run_id>/..." */
  if (data.msg && data.msg.startsWith('Site built')) {
    const match = data.msg.match(/output\/([^/ ]+)/);
    if (match) setLatestRun(match[1]);
  }

  if (data.msg && data.msg.startsWith('Promoted')) {
    const match = data.msg.match(/Promoted ([^\/ ]+)/);
    if (match) setPromotedRun(match[1]);
  }
}

function setLatestRun(runId) {
  latestRunId = runId;
  latestRunLinkEl.textContent = runId;
  latestRunLinkEl.href        = `${web_agent_host}/staging/${runId}/`;
  latestPanel.hidden          = false;
  promotedLinkEl.hidden = true;
  deployBtn.hidden      = false;
}

function setPromotedRun(runId) {
    if (runId == latestRunId) {
        deployBtn.hidden      = true;
        promotedLinkEl.href   = `${web_agent_host}/`;
        promotedLinkEl.hidden = false;

    }
}

/* ============================================================================
   Log display helpers
============================================================================ */
function appendLog(msg) {
  const ts   = new Date().toISOString().slice(11,23);
  logPane.innerHTML += `<span class="log_line"><span class="log_time">${ts}</span> ${msg}</span>\n`;
  logPane.scrollTop = logPane.scrollHeight;
}

/* ============================================================================
   Start polling
============================================================================ */
pollLogs();
