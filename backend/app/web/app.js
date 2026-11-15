/* QueryMind workspace. Sample fixtures are illustrative and never sent to the API. */
'use strict';

const SAMPLES = {
  ecommerce: [
    {
      label: 'Top products', question: 'Which products bring in the most revenue?',
      sql: 'SELECT p.name AS product,\n       SUM(oi.quantity) AS units_sold,\n       SUM(oi.quantity * oi.unit_price) AS revenue\nFROM products AS p\nJOIN order_items AS oi ON oi.product_id = p.product_id\nGROUP BY p.product_id, p.name\nORDER BY revenue DESC\nLIMIT 5;',
      tables: ['products', 'order_items'], columns: ['product', 'units_sold', 'revenue'],
      rows: [['Studio Headphones', 148, 22185], ['Mechanical Keyboard', 126, 16367.40], ['4K Monitor', 42, 14658], ['Everyday Backpack', 193, 12525.70], ['Wireless Mouse', 214, 10678.60]],
    },
    {
      label: 'Top customers', question: 'Who are the top five customers by total spend?',
      sql: 'SELECT c.name AS customer, c.country,\n       COUNT(o.order_id) AS orders,\n       SUM(o.total_amount) AS total_spent\nFROM customers AS c\nJOIN orders AS o ON o.customer_id = c.customer_id\nGROUP BY c.customer_id, c.name, c.country\nORDER BY total_spent DESC\nLIMIT 5;',
      tables: ['customers', 'orders'], columns: ['customer', 'country', 'orders', 'total_spent'],
      rows: [['Alex Morgan', 'United States', 18, 3290.50], ['Sam Rivera', 'Canada', 14, 2864], ['Jordan Lee', 'Singapore', 11, 2140.25], ['Taylor Kim', 'South Korea', 9, 1830], ['Riley Patel', 'India', 8, 1595.80]],
    },
    {
      label: 'Low stock', question: 'Which products have fewer than 10 items in stock?',
      sql: 'SELECT name AS product, stock_quantity, price\nFROM products\nWHERE stock_quantity < 10\nORDER BY stock_quantity ASC\nLIMIT 100;',
      tables: ['products'], columns: ['product', 'stock_quantity', 'price'],
      rows: [['4K Monitor', 3, 349], ['Studio Headphones', 5, 149.90], ['Mechanical Keyboard', 8, 129.90]],
    },
  ],
  library: [
    {
      label: 'Popular books', question: 'Which books have been borrowed most often?',
      sql: 'SELECT b.title, b.author, COUNT(l.loan_id) AS times_borrowed\nFROM books AS b\nJOIN loans AS l ON l.book_id = b.book_id\nGROUP BY b.book_id, b.title, b.author\nORDER BY times_borrowed DESC\nLIMIT 5;',
      tables: ['books', 'loans'], columns: ['title', 'author', 'times_borrowed'],
      rows: [['1984', 'George Orwell', 42], ['The Hobbit', 'J. R. R. Tolkien', 37], ['Foundation', 'Isaac Asimov', 31], ['Animal Farm', 'George Orwell', 28], ['And Then There Were None', 'Agatha Christie', 24]],
    },
    {
      label: 'Overdue loans', question: 'Which members have overdue books?',
      sql: "SELECT m.name AS member, b.title, l.loan_date\nFROM loans AS l\nJOIN members AS m ON m.member_id = l.member_id\nJOIN books AS b ON b.book_id = l.book_id\nWHERE l.status = 'overdue'\nORDER BY l.loan_date\nLIMIT 100;",
      tables: ['loans', 'members', 'books'], columns: ['member', 'title', 'loan_date'],
      rows: [['Alex Morgan', 'Foundation', '2026-10-01'], ['Jordan Lee', 'The Hobbit', '2026-10-04'], ['Sam Rivera', '1984', '2026-10-06']],
    },
    {
      label: 'Unpaid fines', question: 'What are the unpaid fines for each member?',
      sql: 'SELECT m.name AS member, SUM(f.amount) AS unpaid_fines\nFROM fines AS f\nJOIN loans AS l ON l.loan_id = f.loan_id\nJOIN members AS m ON m.member_id = l.member_id\nWHERE f.paid = FALSE\nGROUP BY m.member_id, m.name\nORDER BY unpaid_fines DESC\nLIMIT 100;',
      tables: ['fines', 'loans', 'members'], columns: ['member', 'unpaid_fines'],
      rows: [['Jordan Lee', 12.50], ['Alex Morgan', 7], ['Sam Rivera', 3.50]],
    },
  ],
};

const SCHEMAS = {
  ecommerce: [['customers', 6], ['orders', 5], ['order_items', 6], ['products', 6], ['categories', 3], ['reviews', 6], ['payments', 6]],
  library: [['books', 6], ['members', 5], ['loans', 6], ['fines', 4]],
};
const $ = id => document.getElementById(id);
const state = {mode: 'sample', schema: 'ecommerce', result: null, history: [], busy: false, healthId: 0};
let toastTimer;

function element(tag, text, className) {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  if (className) node.className = className;
  return node;
}

function notify(message) {
  clearTimeout(toastTimer);
  $('toast').textContent = message;
  $('toast').hidden = false;
  toastTimer = setTimeout(() => { $('toast').hidden = true; }, 3200);
}

function status(message = '', loading = false) {
  $('status-message').textContent = message;
  $('status-message').hidden = !message;
  $('status-message').classList.toggle('loading', loading);
}

function setBusy(busy) {
  state.busy = busy;
  ['run-query', 'schema', 'mobile-schema', 'sample-mode', 'live-mode', 'question'].forEach(id => { $(id).disabled = busy; });
  document.querySelectorAll('#suggestion-list button, #history-list button').forEach(button => { button.disabled = busy; });
  $('results').setAttribute('aria-busy', String(busy));
  $('run-label').textContent = busy ? 'Working…' : state.mode === 'sample' ? 'Run sample' : 'Run query';
}

function setConnection(message, offline = false) {
  $('connection').replaceChildren(element('i'), document.createTextNode(message));
  $('connection').classList.toggle('offline', offline);
}

function updateSchemas(names) {
  $('schema').replaceChildren(...names.map(name => {
    const option = element('option', name.charAt(0).toUpperCase() + name.slice(1));
    option.value = name;
    return option;
  }));
  if (!names.includes(state.schema)) state.schema = names[0];
  $('schema').value = state.schema;
  $('source-count').textContent = String(names.length).padStart(2, '0');
  renderSchema();
}

async function checkHealth() {
  const requestId = ++state.healthId;
  setConnection('Checking API…');
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 8000);
  try {
    const response = await fetch('/health', {signal: controller.signal, headers: {Accept: 'application/json'}});
    if (!response.ok) throw new Error('unavailable');
    const data = await response.json();
    if (requestId !== state.healthId || state.mode !== 'live') return;
    const names = data.schemas_available;
    if (!Array.isArray(names) || !names.length || names.some(name => typeof name !== 'string')) throw new Error('invalid health response');
    updateSchemas(names);
    setConnection('API reachable');
    if (data.live_configured === false) status('The API is running, but live queries need a database URL and an LLM API key. Follow the setup guide in Documentation.');
  } catch {
    if (requestId !== state.healthId || state.mode !== 'live') return;
    setConnection('API unavailable', true);
    status('Live queries need the QueryMind backend at this address. Start the backend using the setup guide, or switch to Sample to explore the interface.');
  } finally {
    clearTimeout(timeout);
  }
}

function setMode(mode) {
  if (state.busy || mode === state.mode) return;
  state.mode = mode;
  state.healthId++;
  status();
  $('sample-mode').setAttribute('aria-pressed', String(mode === 'sample'));
  $('live-mode').setAttribute('aria-pressed', String(mode === 'live'));
  const copy = $('mode-note').querySelector('p');
  copy.replaceChildren(
    element('strong', mode === 'sample' ? 'A little room to explore. ' : 'Connected to your curiosity. '),
    document.createTextNode(mode === 'sample' ? 'Try a curated example. Sample results need no database or API key.' : 'Questions run against your configured PostgreSQL database. Review the SQL alongside every answer.'),
  );
  $('mode-note').querySelector('.small-tag').textContent = mode === 'sample' ? 'SAMPLE DATA' : 'LIVE QUERIES';
  if (mode === 'sample') updateSchemas(Object.keys(SAMPLES));
  renderSchema();
  renderResult(null);
  setBusy(false);
  if (mode === 'sample') {
    setConnection('Sample workspace');
    loadSample(SAMPLES[state.schema][0], false);
  } else {
    checkHealth();
  }
}

function renderSchema() {
  $('mobile-schema').replaceChildren(...[...$('schema').options].map(option => option.cloneNode(true)));
  $('mobile-schema').value = state.schema;
  $('source-caption').textContent = state.mode === 'sample' ? 'Sample schema · PostgreSQL' : 'Configured profile · PostgreSQL';
  const tables = state.mode === 'sample' ? SCHEMAS[state.schema] || [] : [];
  $('schema-tables').replaceChildren(...tables.map(([name, count]) => {
    const item = element('li', name);
    item.append(element('span', `${count} cols`));
    return item;
  }));
  if (state.mode === 'live') $('schema-tables').append(element('li', 'Relevant tables appear with results'));
  $('suggestion-list').replaceChildren(...(SAMPLES[state.schema] || []).map(sample => {
    const button = element('button', sample.label);
    button.type = 'button';
    button.title = sample.question;
    button.addEventListener('click', () => {
      $('question').value = sample.question;
      $('question').focus();
      status();
    });
    return button;
  }));
}

function loadSample(sample, remember = true) {
  $('question').value = sample.question;
  const result = {success: true, sample: true, sql: sample.sql, columns: sample.columns, rows: sample.rows, row_count: sample.rows.length, schema_tables_used: sample.tables, attempts: null, latency_ms: null};
  renderResult(result);
  if (remember) rememberQuery(sample.question);
}

function rememberQuery(question) {
  state.history = [{question, schema: state.schema, mode: state.mode}, ...state.history.filter(item => !(item.question === question && item.schema === state.schema && item.mode === state.mode))].slice(0, 6);
  renderHistory();
}

function renderHistory() {
  $('history-empty').hidden = state.history.length > 0;
  $('clear-history').hidden = state.history.length === 0;
  $('history-list').replaceChildren(...state.history.map(item => {
    const li = element('li');
    const button = element('button', item.question);
    button.type = 'button';
    button.title = `${item.mode} · ${item.schema} · ${item.question}`;
    button.disabled = state.busy;
    button.addEventListener('click', () => {
      if (state.busy) return;
      setMode(item.mode);
      if (![...$('schema').options].some(option => option.value === item.schema)) {
        const option = element('option', item.schema); option.value = item.schema; $('schema').append(option);
      }
      state.schema = item.schema;
      $('schema').value = item.schema;
      renderSchema();
      renderResult(null);
      $('question').value = item.question;
      $('question').focus();
    });
    li.append(button);
    return li;
  }));
}

function tableData(result) {
  const rows = Array.isArray(result?.rows) ? result.rows : [];
  let columns = Array.isArray(result?.columns) ? result.columns : [];
  if (!columns.length && rows.length) columns = Array.isArray(rows[0]) ? rows[0].map((_, i) => `column_${i + 1}`) : Object.keys(rows[0]);
  return {columns, rows: rows.map(row => Array.isArray(row) ? row : columns.map(key => row[key]))};
}

function displayValue(value) {
  if (value === null || value === undefined) return 'NULL';
  if (typeof value === 'object') return JSON.stringify(value);
  return String(value);
}

function renderTable() {
  const {columns, rows} = tableData(state.result);
  const filter = $('filter-rows').value.trim().toLowerCase();
  const filtered = rows.map((row, index) => ({row, index})).filter(({row}) => row.some(value => displayValue(value).toLowerCase().includes(filter)));
  const heading = element('tr');
  ['#', ...columns].forEach(name => { const th = element('th', name); th.scope = 'col'; heading.append(th); });
  $('result-table').querySelector('thead').replaceChildren(heading);
  $('result-table').querySelector('tbody').replaceChildren(...filtered.map(({row, index}) => {
    const tr = element('tr');
    tr.append(element('td', String(index + 1).padStart(2, '0')));
    row.forEach(value => {
      const td = element('td', displayValue(value), value == null ? 'null-value' : '');
      td.title = displayValue(value);
      tr.append(td);
    });
    return tr;
  }));
  $('result-table').hidden = filtered.length === 0;
  $('empty-result').hidden = filtered.length > 0;
  $('empty-detail').textContent = filter ? 'No rows match this filter. Try a different search.' : !state.result ? 'Run a question to explore your data.' : !state.result.success ? 'This query did not return a successful result. Check the message above.' : 'The query completed successfully and returned no rows.';
  $('row-badge').textContent = rows.length;
  $('result-summary').textContent = !state.result ? 'Ready for your next question' : `${filter ? `${filtered.length} of ` : ''}${rows.length} row${rows.length === 1 ? '' : 's'} · ${state.result.sample ? 'Illustrative sample data' : 'Database result'}`;
}

function renderSql(sql) {
  // Build text nodes rather than injecting SQL or database values into HTML.
  const fragment = document.createDocumentFragment();
  const pattern = /('(?:''|[^'])*')|\b(SELECT|FROM|JOIN|LEFT|RIGHT|INNER|OUTER|ON|AS|WHERE|AND|OR|GROUP|BY|ORDER|DESC|ASC|LIMIT|COUNT|SUM|AVG|DISTINCT|HAVING|WITH|IS|NULL|FALSE|TRUE|NOT|IN)\b|\b(\d+(?:\.\d+)?)\b/gi;
  let offset = 0;
  for (const match of sql.matchAll(pattern)) {
    fragment.append(document.createTextNode(sql.slice(offset, match.index)));
    fragment.append(element('span', match[0], match[1] ? 'sql-string' : match[2] ? 'sql-keyword' : 'sql-number'));
    offset = match.index + match[0].length;
  }
  fragment.append(document.createTextNode(sql.slice(offset)));
  $('sql-code').replaceChildren(fragment);
}

function renderResult(result) {
  state.result = result;
  $('filter-rows').value = '';
  $('copy-sql').disabled = !result?.sql;
  $('export-csv').disabled = !result?.success || !result?.rows?.length;
  $('result-badge').textContent = !result ? 'Ready' : result.sample ? 'Sample result' : result.success ? 'Query complete' : 'Query unsuccessful';
  $('result-indicator').classList.toggle('error', result?.success === false);
  $('sql-caption').textContent = result?.sample ? 'Illustrative SQL · sample mode' : 'SQL from the query pipeline';
  renderSql(result?.sql || '-- Your SQL will appear here after you run a query.');
  $('result-metrics').replaceChildren();
  if (result) {
    const labels = result.sample ? [`${result.schema_tables_used.length} tables in this example`] : [`${result.attempts} attempt${result.attempts === 1 ? '' : 's'}`, `${(result.latency_ms / 1000).toFixed(2)}s`, result.correction_applied ? 'Correction applied' : 'No correction'];
    $('result-metrics').append(...labels.map(label => element('span', label)));
    if (state.mode === 'live' && result.schema_tables_used?.length) $('schema-tables').replaceChildren(...result.schema_tables_used.map(name => element('li', name)));
  }
  renderTable();
}

function selectTab(name, focus = false) {
  ['table', 'sql'].forEach(tab => {
    const selected = tab === name;
    $(`${tab}-tab`).setAttribute('aria-selected', String(selected));
    $(`${tab}-tab`).tabIndex = selected ? 0 : -1;
    $(`${tab}-panel`).hidden = !selected;
  });
  document.querySelector('.filter-label').hidden = name !== 'table';
  if (focus) $(`${name}-tab`).focus();
}

async function submitQuery(event) {
  event.preventDefault();
  if (state.busy) return;
  const question = $('question').value.trim();
  if (!question) { status('Write a question first.'); $('question').focus(); return; }
  if (question.length > 2000) { status('Please keep your question under 2,000 characters.'); return; }
  status();
  if (state.mode === 'sample') {
    const normalize = value => value.toLowerCase().replace(/[?.!]+$/, '').trim();
    const sample = (SAMPLES[state.schema] || []).find(item => normalize(item.question) === normalize(question));
    if (!sample) { renderResult(null); status('Sample mode supports the suggested questions below the editor. Choose one, or switch to Live database to ask your own question.'); return; }
    loadSample(sample);
    selectTab('table');
    return;
  }
  setBusy(true);
  renderResult(null);
  status('Finding the relevant schema, generating SQL, and running your query. The first request can take longer while models load.', true);
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 120000);
  try {
    const response = await fetch('/query', {method: 'POST', headers: {'Content-Type': 'application/json', Accept: 'application/json'}, body: JSON.stringify({question, schema_name: state.schema, max_attempts: 3}), signal: controller.signal});
    let data;
    try { data = await response.json(); } catch { throw new Error('The backend returned an unexpected response. Check that the QueryMind API is running.'); }
    if (!response.ok) {
      const message = Array.isArray(data.detail) ? data.detail.map(item => item.msg).join('; ') : data.detail;
      throw new Error(typeof message === 'string' ? message : `The request failed (HTTP ${response.status}). Please try again.`);
    }
    if (typeof data.success !== 'boolean') throw new Error('The backend returned an invalid query result.');
    renderResult({...data, sample: false});
    selectTab('table');
    rememberQuery(question);
    status(data.success ? '' : data.error_message || 'The query could not be completed. Try a more specific question.');
  } catch (error) {
    status(error.name === 'AbortError' ? 'The browser stopped waiting after two minutes. The server may still be processing the query; check it before submitting again.' : error.message || 'Unable to reach the backend. Check your connection and try again.');
  } finally {
    clearTimeout(timeout);
    setBusy(false);
  }
}

function csvCell(value) {
  if (value == null) return '""';
  let text = displayValue(value);
  // Quoting alone does not stop spreadsheet formula execution.
  if (typeof value === 'string' && /^[\s]*[=+\-@]|^[\t\r\n]/.test(text)) text = "'" + text;
  return '"' + text.replace(/"/g, '""') + '"';
}

function exportCsv() {
  const {columns, rows} = tableData(state.result);
  if (!rows.length) return;
  const csv = [columns, ...rows].map(row => row.map(csvCell).join(',')).join('\r\n');
  const url = URL.createObjectURL(new Blob(['\uFEFF' + csv], {type: 'text/csv;charset=utf-8;'}));
  const link = element('a');
  link.href = url;
  link.download = `querymind-${state.schema.replace(/[^a-z0-9_-]/gi, '_')}-${state.result.sample ? 'sample' : 'results'}.csv`;
  document.body.append(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
  notify('CSV exported. Includes all result rows.');
}

$('query-form').addEventListener('submit', submitQuery);
$('question').addEventListener('keydown', event => {
  if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') { event.preventDefault(); $('query-form').requestSubmit(); }
});
$('sample-mode').addEventListener('click', () => setMode('sample'));
$('live-mode').addEventListener('click', () => setMode('live'));
function chooseSchema(value) {
  state.schema = value;
  $('schema').value = value;
  status(); renderSchema(); renderResult(null);
  $('question').value = SAMPLES[state.schema]?.[0]?.question || '';
  if (state.mode === 'sample') loadSample(SAMPLES[state.schema][0], false);
}
$('schema').addEventListener('change', () => chooseSchema($('schema').value));
$('mobile-schema').addEventListener('change', () => chooseSchema($('mobile-schema').value));
$('filter-rows').addEventListener('input', renderTable);
$('export-csv').addEventListener('click', exportCsv);
$('copy-sql').addEventListener('click', async () => {
  if (!state.result?.sql) return;
  try { await navigator.clipboard.writeText(state.result.sql); notify('SQL copied to clipboard.'); }
  catch { selectTab('sql'); notify('Clipboard access is unavailable. Select the SQL to copy it.'); }
});
['table', 'sql'].forEach(tab => {
  $(`${tab}-tab`).addEventListener('click', () => selectTab(tab));
  $(`${tab}-tab`).addEventListener('keydown', event => {
    if (['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) {
      event.preventDefault(); selectTab(event.key === 'Home' ? 'table' : event.key === 'End' ? 'sql' : tab === 'table' ? 'sql' : 'table', true);
    }
  });
});
$('clear-history').addEventListener('click', () => { state.history = []; renderHistory(); notify('Session history cleared.'); });
renderSchema();
loadSample(SAMPLES.ecommerce[0], false);
