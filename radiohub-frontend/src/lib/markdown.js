/**
 * Einfacher Markdown-Parser (h1-h3, Listen, Absätze, Bold, Links, Code, HR)
 * Wird von SetupAllgemein für Lizenz-/Rechtstexte verwendet.
 *
 * Template-Variablen: {{version}}, {{year}}, {{copyright}}
 */

const templateVars = {
  version: typeof __APP_VERSION__ !== 'undefined' ? __APP_VERSION__ : '0.0.0',
  year: new Date().getFullYear().toString(),
  copyright: `2025-${new Date().getFullYear()}`
};

function replaceVars(s) {
  return s.replace(/\{\{(\w+)\}\}/g, (_, key) => templateVars[key] || `{{${key}}}`);
}

function esc(s) {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function inline(s) {
  s = esc(s);
  s = s.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
  // Interne Links (#/...) ohne target="_blank", externe mit
  s = s.replace(/\[(.+?)\]\((.+?)\)/g, (_, text, href) => {
    if (href.startsWith('#/')) {
      return `<a href="${href}" class="md-link md-link-internal">${text}</a>`;
    }
    return `<a href="${href}" target="_blank" rel="noopener" class="md-link">${text}</a>`;
  });
  s = s.replace(/`(.+?)`/g, '<code class="md-code">$1</code>');
  return s;
}

export function parseMarkdown(md) {
  md = replaceVars(md);
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
