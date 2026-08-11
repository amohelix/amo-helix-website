const industryContent = {
  service: {
    kicker: 'FIELD SERVICE CONFIGURATION',
    title: 'Turn every repair into a better next visit.',
    description: 'Capture symptoms, diagnostics, corrective actions, parts, measurements, and verification—then return relevant history before the next job.',
    subject: 'Asset', activity: 'Service visit', outcome: 'Verified repair memory',
    workflow: ['Arrive', 'Inspect', 'Diagnose', 'Repair', 'Verify']
  },
  delivery: {
    kicker: 'DELIVERY CONFIGURATION',
    title: 'Make every exception clear, complete, and defensible.',
    description: 'Log arrivals, condition, refusals, signatures, photos, delays, and handoffs through a voice-guided delivery workflow.',
    subject: 'Shipment', activity: 'Delivery stop', outcome: 'Verified delivery record',
    workflow: ['Arrive', 'Inspect', 'Deliver', 'Document', 'Close']
  },
  healthcare: {
    kicker: 'HEALTHCARE OPERATIONS CONFIGURATION',
    title: 'Capture operational context without losing the human conversation.',
    description: 'Support organization-approved visit workflows, observations, actions, follow-up items, and human review with configurable governance.',
    subject: 'Patient or case', activity: 'Visit or round', outcome: 'Reviewed operational note',
    workflow: ['Check in', 'Observe', 'Document', 'Review', 'Complete']
  },
  manufacturing: {
    kicker: 'MANUFACTURING CONFIGURATION',
    title: 'Turn every defect and correction into plant memory.',
    description: 'Connect machine conditions, measurements, downtime, root causes, corrective actions, and verified restart outcomes.',
    subject: 'Machine or line', activity: 'Production event', outcome: 'Verified process knowledge',
    workflow: ['Detect', 'Isolate', 'Correct', 'Test', 'Release']
  }
};

const header = document.querySelector('.site-header');
const navToggle = document.querySelector('.nav-toggle');
const nav = document.querySelector('.site-nav');
const demoWindow = document.querySelector('.demo-window');
const demoButton = document.querySelector('.mic-button');
const demoLabel = document.querySelector('.mic-label');

window.addEventListener('scroll', () => header.classList.toggle('scrolled', window.scrollY > 16));

navToggle.addEventListener('click', () => {
  const open = nav.classList.toggle('open');
  navToggle.setAttribute('aria-expanded', String(open));
});

document.querySelectorAll('.site-nav a').forEach(link => link.addEventListener('click', () => {
  nav.classList.remove('open');
  navToggle.setAttribute('aria-expanded', 'false');
}));

demoButton.addEventListener('click', () => {
  demoWindow.classList.remove('playing');
  void demoWindow.offsetWidth;
  demoWindow.classList.add('playing');
  demoLabel.textContent = 'Nexus captured the record';
  setTimeout(() => demoLabel.textContent = 'Run voice demo', 2600);
});

document.querySelectorAll('[data-industry]').forEach(button => {
  button.addEventListener('click', () => {
    document.querySelectorAll('[data-industry]').forEach(item => item.setAttribute('aria-selected', 'false'));
    button.setAttribute('aria-selected', 'true');
    const data = industryContent[button.dataset.industry];
    document.querySelector('#industry-kicker').textContent = data.kicker;
    document.querySelector('#industry-title').textContent = data.title;
    document.querySelector('#industry-description').textContent = data.description;
    document.querySelector('#industry-subject').textContent = data.subject;
    document.querySelector('#industry-activity').textContent = data.activity;
    document.querySelector('#industry-outcome').textContent = data.outcome;
    data.workflow.forEach((value, index) => document.querySelector(`#wf-${index + 1}`).textContent = value);
  });
});

const observer = new IntersectionObserver(entries => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      entry.target.classList.add('visible');
      observer.unobserve(entry.target);
    }
  });
}, { threshold: 0.12 });

document.querySelectorAll('.reveal').forEach(element => observer.observe(element));

document.querySelector('#pilot-form').addEventListener('submit', event => {
  event.preventDefault();
  const form = event.currentTarget;
  const submitButton = form.querySelector('button[type="submit"]');
  const status = form.querySelector('.form-status');
  const originalLabel = submitButton.textContent;
  const formData = new FormData(form);
  const payload = Object.fromEntries(formData.entries());

  status.classList.remove('error', 'success');
  status.textContent = 'Sending your pilot request...';
  submitButton.disabled = true;
  submitButton.textContent = 'Sending request';

  fetch(form.action, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      ...payload,
      page: window.location.href
    })
  })
    .then(async response => {
      const result = await response.json().catch(() => ({}));
      if (!response.ok || !result.ok) {
        throw new Error(result.message || 'We could not send the request. Please try again.');
      }

      status.classList.add('success');
      status.textContent = 'Request received. We will review it and follow up.';
      form.reset();
    })
    .catch(error => {
      status.classList.add('error');
      status.textContent = error.message || 'We could not send the request. Please try again.';
    })
    .finally(() => {
      submitButton.disabled = false;
      submitButton.textContent = originalLabel;
    });
});

document.querySelector('#year').textContent = new Date().getFullYear();
