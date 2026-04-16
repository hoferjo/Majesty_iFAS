// Lieferant search modal logic
function showLieferantSearchModal(onSelect) {
    // Create modal if not exists
    let modal = document.getElementById('lieferantSearchModal');
    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'lieferantSearchModal';
        modal.style.position = 'fixed';
        modal.style.left = 0;
        modal.style.top = 0;
        modal.style.width = '100vw';
        modal.style.height = '100vh';
        modal.style.background = 'rgba(0,0,0,0.3)';
        modal.style.display = 'flex';
        modal.style.alignItems = 'center';
        modal.style.justifyContent = 'center';
        modal.innerHTML = `<div style='background:#fff;padding:2em 2em 1.5em 2em;border-radius:10px;box-shadow:0 2px 16px #0002;min-width:420px;'>
            <div style='font-weight:600;margin-bottom:1em;'>Lieferant suchen</div>
            <input type='text' id='lieferantSearchInput' placeholder='Name, Nummer...' style='width:90%;padding:6px;font-size:1em;'>
            <div id='lieferantSearchResults' style='max-height:220px;overflow:auto;margin-top:1em;'></div>
            <div style='margin-top:1.2em;text-align:right;'>
                <button class='modern-btn' id='cancelLieferantSearchBtn' style='margin-right:1em;'>Abbrechen</button>
            </div>
        </div>`;
        document.body.appendChild(modal);
    }
    modal.style.display = 'flex';
    const input = document.getElementById('lieferantSearchInput');
    const resultsDiv = document.getElementById('lieferantSearchResults');
    input.value = '';
    resultsDiv.innerHTML = '';
    input.focus();
    document.getElementById('cancelLieferantSearchBtn').onclick = function() {
        modal.style.display = 'none';
        if (onSelect) onSelect(null);
    };
    input.oninput = function() {
        const q = input.value.trim();
        if (!q) {
            resultsDiv.innerHTML = '';
            return;
        }
        fetch(`/api/search-lieferant?q=${encodeURIComponent(q)}`)
            .then(res => res.json())
            .then(data => {
                resultsDiv.innerHTML = '';
                if (Array.isArray(data) && data.length > 0) {
                    data.forEach(lief => {
                        const div = document.createElement('div');
                        div.style.padding = '6px 0';
                        div.style.cursor = 'pointer';
                        div.textContent = `${lief.ifas_nummer} — ${lief.name || ''}`;
                        div.onclick = function() {
                            modal.style.display = 'none';
                            if (onSelect) onSelect(lief);
                        };
                        resultsDiv.appendChild(div);
                    });
                } else {
                    resultsDiv.innerHTML = '<div style="color:#888;">Keine Treffer</div>';
                }
            });
    };
}
