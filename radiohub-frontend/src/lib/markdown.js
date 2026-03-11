/**
 * Einfacher Markdown-Parser (h1-h3, Listen, Absaetze, Bold, Links, Code, HR)
 * Wird von SetupAllgemein fuer Lizenz-/Rechtstexte verwendet.
 */

function esc(s) {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function inline(s) {
  s = esc(s);
  s = s.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
  s = s.replace(/\[(.+?)\]\((.+?)\)/g, '<a href="$2" target="_blank" rel="noopener" class="md-link">$1</a>');
  s = s.replace(/`(.+?)`/g, '<code class="md-code">$1</code>');
  return s;
}

export function parseMarkdown(md) {
  const lines = md.split('\n');
  let html = '';
  let inList = false;

  for (let line of lines) {
    line = line.trimEnd();

    if (!line.trim()) {
      if (inList) { html += '</ul>'; inList = false; }
      continue;
    }

    if (/^---+$/.test(line.trim())) {
      if (inList) { html += '</ul>'; inList = false; }
      html += '<hr class="md-hr"/>';
      continue;
    }

    if (line.startsWith('### ')) {
      if (inList) { html += '</ul>'; inList = false; }
      html += '<h4 class="md-h4">' + inline(line.slice(4)) + '</h4>';
      continue;
    }
    if (line.startsWith('## ')) {
      if (inList) { html += '</ul>'; inList = false; }
      html += '<h3 class="md-h3">' + inline(line.slice(3)) + '</h3>';
      continue;
    }
    if (line.startsWith('# ')) {
      if (inList) { html += '</ul>'; inList = false; }
      html += '<h2 class="md-h2">' + inline(line.slice(2)) + '</h2>';
      continue;
    }

    if (line.startsWith('- ') || line.startsWith('* ')) {
      if (!inList) { html += '<ul class="md-list">'; inList = true; }
      html += '<li>' + inline(line.slice(2)) + '</li>';
      continue;
    }

    if (inList) { html += '</ul>'; inList = false; }
    html += '<p class="md-text">' + inline(line) + '</p>';
  }

  if (inList) html += '</ul>';
  return html;
}
