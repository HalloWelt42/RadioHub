<script>
  /**
   * SanitizedHtml - Sichere HTML-Darstellung
   * Entfernt gefährliche Tags, behält sichere Formatierung.
   */
  let {
    html = '',
    maxHeight = null    // z.B. '200px' -- mit Fade-Out
  } = $props();

  const ALLOWED_TAGS = new Set(['p', 'br', 'a', 'b', 'i', 'em', 'strong', 'ul', 'ol', 'li', 'span']);

  function sanitize(raw) {
    if (!raw) return '';
    // Einfacher Tag-Filter: Entferne alles ausser erlaubte Tags
    return raw.replace(/<\/?([a-zA-Z][a-zA-Z0-9]*)\b[^>]*>/gi, (match, tag) => {
      const lower = tag.toLowerCase();
      if (ALLOWED_TAGS.has(lower)) {
        // Bei <a> Tags: nur href behalten, target="_blank" erzwingen
        if (lower === 'a' && match.startsWith('<a')) {
          const hrefMatch = match.match(/href="([^"]*)"/);
          const href = hrefMatch ? hrefMatch[1] : '#';
          return `<a href="${href}" target="_blank" rel="noopener noreferrer">`;
        }
        // Schliessende Tags und einfache Tags durchlassen
        if (match.startsWith('</')) return `</${lower}>`;
        if (lower === 'br') return '<br>';
        return `<${lower}>`;
      }
      return '';
    });
  }

  let sanitized = $derived(sanitize(html));
</script>

<div
  class="sanitized-html"
  class:has-max-height={!!maxHeight}
  style={maxHeight ? `--max-h: ${maxHeight}` : ''}
>
  {@html sanitized}
</div>

<style>
  .sanitized-html {
    font-family: var(--hifi-font-family, 'Barlow', sans-serif);
    font-size: 12px;
    line-height: 1.5;
    color: var(--hifi-text-secondary);
    word-break: break-word;
  }

  .sanitized-html :global(p) {
    margin: 0 0 8px 0;
  }

  .sanitized-html :global(a) {
    color: var(--hifi-accent);
    text-decoration: none;
  }

  .sanitized-html :global(a:hover) {
    text-decoration: underline;
  }

  .sanitized-html :global(ul),
  .sanitized-html :global(ol) {
    margin: 0 0 8px 0;
    padding-left: 20px;
  }

  .has-max-height {
    max-height: var(--max-h);
    overflow-y: auto;
  }
</style>
