const form = document.querySelector('#access-form');
const tokenInput = document.querySelector('#access-token');
const status = document.querySelector('#admin-status');
const list = document.querySelector('#lead-list');
const toolbar = document.querySelector('#admin-toolbar');
const leadCount = document.querySelector('#lead-count');
const downloadButton = document.querySelector('#download-csv');
const deleteTestsButton = document.querySelector('#delete-tests');

let accessToken = sessionStorage.getItem('pilotRequestsAccessToken') || '';

if (accessToken) {
  tokenInput.value = accessToken;
}

const formatDate = (value) => {
  if (!value) return 'Unknown time';
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value));
};

const escapeHtml = (value) =>
  String(value || '').replace(/[&<>"']/g, (char) => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;',
  })[char]);

function setStatus(message, isError = false) {
  status.textContent = message;
  status.classList.toggle('error', isError);
}

async function deleteRequest(payload) {
  const response = await fetch('/api/pilot-requests', {
    method: 'DELETE',
    headers: {
      authorization: `Bearer ${accessToken}`,
      'content-type': 'application/json',
    },
    body: JSON.stringify(payload),
  });
  const result = await response.json().catch(() => ({}));

  if (!response.ok || !result.ok) {
    throw new Error(result.message || 'Pilot request could not be deleted.');
  }

  return result;
}

function renderLeads(leads) {
  toolbar.hidden = false;
  leadCount.textContent = `${leads.length} ${leads.length === 1 ? 'request' : 'requests'}`;

  if (!leads.length) {
    list.innerHTML = '<div class="empty-state">No pilot requests yet.</div>';
    return;
  }

  list.innerHTML = leads.map((lead) => `
    <article class="lead-card" data-lead-id="${escapeHtml(lead.id)}">
      <div class="lead-card-head">
        <div>
          <span>${escapeHtml(formatDate(lead.submittedAt))}</span>
          <h2>${escapeHtml(lead.company)}</h2>
        </div>
        <div class="lead-card-actions">
          <a href="mailto:${encodeURIComponent(lead.email)}">${escapeHtml(lead.email)}</a>
          <button class="text-button delete-lead" type="button" data-lead-id="${escapeHtml(lead.id)}">Delete</button>
        </div>
      </div>
      <dl>
        <div><dt>Name</dt><dd>${escapeHtml(lead.name)}</dd></div>
        <div><dt>Role</dt><dd>${escapeHtml(lead.role || 'Not provided')}</dd></div>
        <div class="lead-workflow"><dt>Workflow</dt><dd>${escapeHtml(lead.workflow)}</dd></div>
      </dl>
    </article>
  `).join('');
}

async function loadLeads() {
  accessToken = tokenInput.value.trim();
  if (!accessToken) return;

  setStatus('Loading pilot requests...');
  list.innerHTML = '';
  toolbar.hidden = true;

  const response = await fetch('/api/pilot-requests', {
    headers: {
      authorization: `Bearer ${accessToken}`,
    },
  });
  const result = await response.json().catch(() => ({}));

  if (!response.ok || !result.ok) {
    sessionStorage.removeItem('pilotRequestsAccessToken');
    throw new Error(result.message || 'Pilot requests could not be loaded.');
  }

  sessionStorage.setItem('pilotRequestsAccessToken', accessToken);
  setStatus('');
  renderLeads(result.leads || []);
}

form.addEventListener('submit', (event) => {
  event.preventDefault();
  loadLeads().catch((error) => setStatus(error.message, true));
});

downloadButton.addEventListener('click', async () => {
  if (!accessToken) return;

  try {
    const response = await fetch('/api/pilot-requests?format=csv', {
      headers: {
        authorization: `Bearer ${accessToken}`,
      },
    });

    if (!response.ok) {
      throw new Error('CSV could not be downloaded.');
    }

    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'amo-helix-pilot-requests.csv';
    document.body.append(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  } catch (error) {
    setStatus(error.message, true);
  }
});

deleteTestsButton.addEventListener('click', async () => {
  if (!accessToken) return;

  try {
    setStatus('Removing test requests...');
    const result = await deleteRequest({ deleteTests: true });
    setStatus(`${result.deleted || 0} test requests removed.`);
    await loadLeads();
  } catch (error) {
    setStatus(error.message, true);
  }
});

list.addEventListener('click', async (event) => {
  const button = event.target.closest('.delete-lead');
  if (!button || !accessToken) return;

  try {
    setStatus('Deleting pilot request...');
    await deleteRequest({ id: button.dataset.leadId });
    await loadLeads();
  } catch (error) {
    setStatus(error.message, true);
  }
});
