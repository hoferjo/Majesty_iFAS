// Update Majesty Data button
    var updateMajestyForm = document.getElementById("updateMajestyForm");
    if (updateMajestyForm) {
        updateMajestyForm.addEventListener("submit", function(e) {
            e.preventDefault();
            fetch("/update-majesty-data", { method: "POST" })
                .then(response => response.json())
                .then(data => {
                    document.getElementById("updateMajestyStatus").innerText = data.message || (data.status === "success" ? "Update complete." : "Update failed.");
                })
                .catch(() => {
                    document.getElementById("updateMajestyStatus").innerText = "Update failed.";
                });
        });
    }

    // Hard Update Majesty Data button
    var hardUpdateMajestyForm = document.getElementById("hardUpdateMajestyForm");
    if (hardUpdateMajestyForm) {
        hardUpdateMajestyForm.addEventListener("submit", function(e) {
            e.preventDefault();
            fetch("/hard-update-majesty-data", { method: "POST" })
                .then(response => response.json())
                .then(data => {
                    document.getElementById("updateMajestyStatus").innerText = data.message || (data.status === "success" ? "Hard update complete." : "Update failed.");
                })
                .catch(() => {
                    document.getElementById("updateMajestyStatus").innerText = "Update failed.";
                });
        });
    }
    // Tab switching logic
function openTab(evt, tabName) {
    var i, tabcontent, tablinks;
    tabcontent = document.getElementsByClassName("tabcontent");
    for (i = 0; i < tabcontent.length; i++) {
        tabcontent[i].style.display = "none";
    }
    tablinks = document.getElementsByClassName("tablink");
    for (i = 0; i < tablinks.length; i++) {
        tablinks[i].className = tablinks[i].className.replace(" active", "");
    }
    document.getElementById(tabName).style.display = "block";
    evt.currentTarget.className += " active";
}

document.addEventListener("DOMContentLoaded", function() {
        // --- Article List Preview logic ---
        function fetchAndRenderArticleListPreview() {
            fetch('/article-list-preview')
                .then(response => response.json())
                .then(data => {
                    const table = document.getElementById('articleListPreviewTable');
                    if (!table) return;
                    const tbody = table.querySelector('tbody');
                    if (!tbody) return;
                    tbody.innerHTML = '';
                    const rows = Array.isArray(data.rows) ? data.rows : [];
                    if (rows.length > 0) {
                        rows.forEach(row => {
                            const tr = document.createElement('tr');
                            const artnr = row.artnr || '';
                            const artbez1 = row.artbez1 || '';
                            const zeichnr = row.zeichnr || '';
                            tr.innerHTML = `<td>${artnr}</td><td>${artbez1}</td><td>${zeichnr}</td><td><button class="remove-article-btn" data-artnr="${artnr}" style="color:#c00; background:none; border:none; cursor:pointer; font-size:1em;">✖</button></td>`;
                            tbody.appendChild(tr);
                        });
                        // Add event listeners for remove buttons
                        tbody.querySelectorAll('.remove-article-btn').forEach(btn => {
                            btn.addEventListener('click', function(e) {
                                const artnr = this.getAttribute('data-artnr');
                                if (confirm(`Remove article ${artnr} from list?`)) {
                                    fetch('/remove-article-from-list', {
                                        method: 'POST',
                                        headers: { 'Content-Type': 'application/json' },
                                        body: JSON.stringify({ artnr })
                                    })
                                    .then(res => res.json())
                                    .then(result => {
                                        let feedbackLog = document.getElementById('feedbackLog');
                                        if (feedbackLog && result && result.message) {
                                            let entry = `<div><b>Remove Article:</b> ${artnr} — <span style='color:${result.status === 'success' ? '#27ae60' : '#c00'};'>${result.message}</span></div>`;
                                            feedbackLog.innerHTML = entry + feedbackLog.innerHTML;
                                        }
                                        fetchAndRenderArticleListPreview();
                                    });
                                }
                                e.stopPropagation();
                            });
                        });
                    } else {
                        const tr = document.createElement('tr');
                        tr.innerHTML = `<td colspan="4" style="text-align:center;color:#888;">No articles in list.</td>`;
                        tbody.appendChild(tr);
                    }
                })
                .catch(() => {
                    const table = document.getElementById('articleListPreviewTable');
                    if (!table) return;
                    const tbody = table.querySelector('tbody');
                    if (!tbody) return;
                    tbody.innerHTML = '';
                    const tr = document.createElement('tr');
                    tr.innerHTML = `<td colspan="4" style="text-align:center;color:#c00;">Failed to load preview.</td>`;
                    tbody.appendChild(tr);
                });
        }

        // Wire up refresh button
        var refreshArticleListPreviewBtn = document.getElementById('refreshArticleListPreviewBtn');
                // Wire up reset button
                var resetArticleListBtn = document.getElementById('resetArticleListBtn');
                if (resetArticleListBtn) {
                    resetArticleListBtn.addEventListener('click', function() {
                        if (confirm('Are you sure you want to reset the article list?')) {
                            fetch('/reset-article-list', { method: 'POST' })
                                .then(res => res.json())
                                .then(() => fetchAndRenderArticleListPreview());
                        }
                    });
                }
        if (refreshArticleListPreviewBtn) {
            refreshArticleListPreviewBtn.addEventListener('click', fetchAndRenderArticleListPreview);
        }
        // Initial load
        fetchAndRenderArticleListPreview();
    // --- Article mode buttons logic ---
    var addArticleBtn = document.getElementById("addArticleBtn");
    var generateArticleDataBtn = document.getElementById("generateArticleDataBtn");
    var downloadArticleExcelBtn = document.getElementById("downloadArticleExcelBtn");
    var downloadArticlePartlistBtn = document.getElementById("downloadArticlePartlistBtn");
    var downloadArticlePartlistTreeBtn = document.getElementById("downloadArticlePartlistTreeBtn");

    if (addArticleBtn) {
        addArticleBtn.addEventListener("click", function() {
            console.log("Add Article button clicked");
            if (searchMode !== "article") {
                alert("Switch to Article mode to add article.");
                return;
            }
            if (!selectedResult || !selectedResult.artnr) {
                alert("No article selected.");
                return;
            }
            fetch("/add-article", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ artnr: selectedResult.artnr })
            })
            .then(response => response.json())
            .then(data => {
                let entry = `<div><b>Add Article:</b> ${selectedResult.artnr} — <span style='color:${data.status === 'success' ? '#27ae60' : '#c00'};'>${data.message}</span></div>`;
                feedbackLog.innerHTML = entry + feedbackLog.innerHTML;
            })
            .catch(err => {
                let entry = `<div><b>Add Article:</b> ${selectedResult.artnr} — <span style='color:#c00;'>Error: ${err}</span></div>`;
                feedbackLog.innerHTML = entry + feedbackLog.innerHTML;
            });
        });
    }

    if (generateArticleDataBtn) {
        generateArticleDataBtn.addEventListener("click", function() {
            console.log("Generate Data button clicked");
            if (searchMode !== "article") {
                alert("Switch to Article mode to generate data.");
                return;
            }
            if (!selectedResult || !selectedResult.artnr) {
                alert("No article selected.");
                return;
            }
            var selectedHeaders = getSelectedSheetHeaders ? getSelectedSheetHeaders() : [];
            if (!selectedHeaders.length) {
                alert("No sheets selected in Settings.");
                return;
            }
            fetch("/generate-module-data", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ artnr: selectedResult.artnr, selected_headers: selectedHeaders, mode: "article" })
            })
            .then(response => response.json())
            .then(data => {
                let entry = `<div><b>Generate Data:</b> ${selectedResult.artnr} — <span style='color:${data.status === 'success' ? '#27ae60' : '#c00'};'>${data.message}</span></div>`;
                feedbackLog.innerHTML = entry + feedbackLog.innerHTML;
            })
            .catch(err => {
                let entry = `<div><b>Generate Data:</b> ${selectedResult.artnr} — <span style='color:#c00;'>Error: ${err}</span></div>`;
                feedbackLog.innerHTML = entry + feedbackLog.innerHTML;
            });
        });
    }

    if (downloadArticleExcelBtn) {
        downloadArticleExcelBtn.addEventListener("click", function() {
            console.log("Download Article Import button clicked");
            if (searchMode !== "article") {
                alert("Switch to Article mode to download XLSX.");
                return;
            }
            if (!selectedResult || !selectedResult.artnr) {
                alert("No article selected.");
                return;
            }
            fetch(`/download-module-excel?artnr=${encodeURIComponent(selectedResult.artnr)}&mode=article`)
                .then(function(response) {
                    if (!response.ok) {
                        return response.text().then(function(text) {
                            let message = text || "Failed to create Excel file.";
                            throw new Error(message);
                        });
                    }
                    var disposition = response.headers.get("content-disposition") || "";
                    var fileName = `module_export_${selectedResult.artnr}.xlsx`;
                    var match = disposition.match(/filename="?([^";]+)"?/i);
                    if (match && match[1]) {
                        fileName = match[1];
                    }
                    return response.blob().then(function(blob) {
                        return { blob: blob, fileName: fileName };
                    });
                })
                .then(function(result) {
                    var url = window.URL.createObjectURL(result.blob);
                    var link = document.createElement("a");
                    link.href = url;
                    link.download = result.fileName;
                    document.body.appendChild(link);
                    link.click();
                    document.body.removeChild(link);
                    window.URL.revokeObjectURL(url);
                    let entry = `<div><b>Download XLSX:</b> ${selectedResult.artnr} — <span style='color:#27ae60;'>Excel created and downloaded.</span></div>`;
                    feedbackLog.innerHTML = entry + feedbackLog.innerHTML;
                })
                .catch(function(err) {
                    let entry = `<div><b>Download XLSX:</b> ${selectedResult.artnr} — <span style='color:#c00;'>Error: ${err.message || err}</span></div>`;
                    feedbackLog.innerHTML = entry + feedbackLog.innerHTML;
                });
        });
    }

    if (downloadArticlePartlistBtn) {
        downloadArticlePartlistBtn.addEventListener("click", function() {
            console.log("Download Partlist Import button clicked");
            if (searchMode !== "article") {
                alert("Switch to Article mode to download partlist.");
                return;
            }
            if (!selectedResult || !selectedResult.artnr) {
                alert("No article selected.");
                return;
            }
            const url = `/download-partlist-excel?mode=article&artnr=${encodeURIComponent(selectedResult.artnr)}`;
            const link = document.createElement('a');
            link.href = url;
            link.download = `partlist_export_${selectedResult.artnr}.xlsx`;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        });
    }

    if (downloadArticlePartlistTreeBtn) {
        downloadArticlePartlistTreeBtn.addEventListener("click", function() {
            console.log("Download Partlist Tree button clicked");
            if (searchMode !== "article") {
                alert("Switch to Article mode to download partlist tree.");
                return;
            }
            if (!selectedResult || !selectedResult.artnr) {
                alert("No article selected.");
                return;
            }
            const url = `/download-partlist-tree?mode=article&artnr=${encodeURIComponent(selectedResult.artnr)}`;
            const link = document.createElement('a');
            link.href = url;
            link.download = `partlist_tree_${selectedResult.artnr}.txt`;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        });
    }

    // --- Mode visibility logic ---
    var articleModeContainer = document.getElementById("articleModeContainer");
    var moduleModeContainer = document.getElementById("moduleModeContainer");
    window.searchMode = "article";
    function updateArticleModeUI() {
        if (articleModeContainer) {
            articleModeContainer.style.display = (window.searchMode === "article") ? "flex" : "none";
        }
        if (moduleModeContainer) {
            moduleModeContainer.style.display = (window.searchMode === "module") ? "flex" : "none";
        }
    }
    updateArticleModeUI();

        var i18n = {
            en: {
                tabSearch: "Search & Transform",
                tabSettings: "Settings",
                searchPlaceholder: "Search by Artikelnummer, Zeichnungsnummer or description",
                searchButton: "Search",
                addArticle: "Add Article",
                generateData: "Generate Data",
                downloadArticleImport: "Download Article Import",
                downloadPartlistImport: "Download Partlist Import",
                downloadPartlistTree: "Download Partlist Tree",
                modeArticle: "Article",
                changeMode: "Change Mode",
                currentSelection: "Current Selection",
                generateModule: "Generate Module Structure",
                generateModuleData: "Generate Module Data",
                downloadModuleExcel: "Download Module (XLSX)",
                downloadPartlistExcel: "Download Partlist Excel",
                settingsHeading: "Settings",
                alertNoModule: "No module selected.",
                alertSwitchModule: "Switch to Module mode to generate a module.",
                alertOneTarget: "Only one existing-articles checkbox can be selected.",
                modalTitle: "Blocked Article Replacement",
                modalSearchLabel: "Search replacement",
                modalReplacementLabel: "Replacement artnr",
                modalSearchPlaceholder: "Search by artnr / zeichnr / text",
                modalReplacementPlaceholder: "Enter replacement artnr",
                modalConfirm: "Confirm",
                modalIgnore: "Ignore",
                modalSearch: "Search",
                modalTextBtn: "Use as text article",
                modalNoResults: "No results found.",
                modalNeedReplacement: "Please enter a replacement artnr or click Ignore.",
                showBlockedArticles: "Show Blocked Articles",
                langEnglish: "English",
                langGerman: "German",
                uploadIfas: "Upload iFAS artikelstamm.txt:",
                updateTarget: "Update target:",
                uploadButton: "Upload",
                existingArticleTarget: "Existing Article Target",
                none: "None",
                addToProd: "Add to existing articles PROD",
                addToTest: "Add to existing articles TEST",
                updateMajesty: "Update Majesty Data",
                hardUpdateMajesty: "Hard Update Majesty Data",
                activeSheets: "Active Sheets"
            },
            de: {
                tabSearch: "Suche & Transformation",
                tabSettings: "Einstellungen",
                searchPlaceholder: "Suche nach Artikelnr, Zeichnungsnr oder Beschreibung",
                searchButton: "Suchen",
                addArticle: "Artikel hinzufügen",
                generateData: "Daten generieren",
                downloadArticleImport: "Artikel-Import herunterladen",
                downloadPartlistImport: "Stücklisten-Import herunterladen",
                downloadPartlistTree: "Stücklistenbaum herunterladen",
                modeArticle: "Artikel",
                changeMode: "Modus wechseln",
                currentSelection: "Aktuelle Auswahl",
                generateModule: "Modulstruktur generieren",
                generateModuleData: "Moduldaten generieren",
                downloadModuleExcel: "Modul herunterladen (XLSX)",
                downloadPartlistExcel: "Stückliste Excel herunterladen",
                settingsHeading: "Einstellungen",
                alertNoModule: "Kein Modul ausgewählt.",
                alertSwitchModule: "Für die Modulgenerierung bitte in den Modulmodus wechseln.",
                alertOneTarget: "Es darf nur ein Existing-Articles Ziel ausgewählt sein.",
                modalTitle: "Ersatz für gesperrten Artikel",
                modalSearchLabel: "Ersatz suchen",
                modalReplacementLabel: "Ersatz-Artikelnr",
                modalSearchPlaceholder: "Suche nach Artnr / Zeichnr / Text",
                modalReplacementPlaceholder: "Ersatz-Artikelnr eingeben",
                modalConfirm: "Bestätigen",
                modalIgnore: "Ignorieren",
                modalSearch: "Suchen",
                modalTextBtn: "Als Textartikel verwenden",
                modalNoResults: "Keine Ergebnisse gefunden.",
                modalNeedReplacement: "Bitte Ersatz-Artikelnr eingeben oder Ignorieren klicken.",
                showBlockedArticles: "Gesperrte Artikel anzeigen",
                langEnglish: "Englisch",
                langGerman: "Deutsch",
                uploadIfas: "iFAS artikelstamm.txt hochladen:",
                updateTarget: "Ziel aktualisieren:",
                uploadButton: "Hochladen",
                existingArticleTarget: "Ziel für bestehende Artikel",
                none: "Keine",
                addToProd: "Zu bestehenden Artikeln PROD hinzufügen",
                addToTest: "Zu bestehenden Artikeln TEST hinzufügen",
                updateMajesty: "Majesty-Daten aktualisieren",
                hardUpdateMajesty: "Majesty-Daten hart aktualisieren",
                activeSheets: "Aktive Sheets"
            }
        };
        var currentLanguage = "en";

        function t(key) {
            return (i18n[currentLanguage] && i18n[currentLanguage][key]) || (i18n.en[key] || key);
        }

        function applyLanguage() {
            // Update all elements with data-i18n
            document.querySelectorAll('[data-i18n]').forEach(function(el) {
                var key = el.getAttribute('data-i18n');
                if (key && i18n[currentLanguage][key]) {
                    el.textContent = i18n[currentLanguage][key];
                }
                // Show/hide based on language
                var showFor = el.getAttribute('data-lang');
                if (showFor) {
                    el.style.display = (showFor === currentLanguage) ? '' : 'none';
                }
            });
            // Update placeholders with data-i18n-placeholder
            document.querySelectorAll('[data-i18n-placeholder]').forEach(function(el) {
                var key = el.getAttribute('data-i18n-placeholder');
                if (key && i18n[currentLanguage][key]) {
                    el.setAttribute('placeholder', i18n[currentLanguage][key]);
                }
            });
        }

        var languageSwitch = document.getElementById("languageSwitch");
        if (languageSwitch) {
            languageSwitch.addEventListener("change", function() {
                currentLanguage = languageSwitch.value || "en";
                applyLanguage();
            });
        }
        applyLanguage();

            // Download Partlist Excel button
            var downloadPartlistExcelBtn = document.getElementById("downloadPartlistExcelBtn");
            if (downloadPartlistExcelBtn) {
                downloadPartlistExcelBtn.addEventListener("click", function() {
                    fetch("/download-partlist-excel?mode=module")
                        .then(function(response) {
                            if (!response.ok) {
                                return response.text().then(function(text) {
                                    let message = text || "Failed to create Excel file.";
                                    throw new Error(message);
                                });
                            }
                            var disposition = response.headers.get("content-disposition") || "";
                            var fileName = "partlist_export.xlsx";
                            var match = disposition.match(/filename="?([^";]+)"?/i);
                            if (match && match[1]) {
                                fileName = match[1];
                            }
                            return response.blob().then(function(blob) {
                                return { blob: blob, fileName: fileName };
                            });
                        })
                        .then(function(result) {
                            var url = window.URL.createObjectURL(result.blob);
                            var link = document.createElement("a");
                            link.href = url;
                            link.download = result.fileName;
                            document.body.appendChild(link);
                            link.click();
                            document.body.removeChild(link);
                            window.URL.revokeObjectURL(url);
                            let entry = `<div><b>Download Partlist Excel:</b> <span style='color:#27ae60;'>Excel created and downloaded.</span></div>`;
                            feedbackLog.innerHTML = entry + feedbackLog.innerHTML;
                        })
                        .catch(function(err) {
                            let entry = `<div><b>Download Partlist Excel:</b> <span style='color:#c00;'>Error: ${err.message || err}</span></div>`;
                            feedbackLog.innerHTML = entry + feedbackLog.innerHTML;
                        });
                });
            }
        // Blocked articles UI logic
        var blockedArticlesContainer = document.getElementById("blockedArticlesContainer");
        var showBlockedArticlesBtn = document.getElementById("showBlockedArticlesBtn");
        var blockedArticlesArea = document.getElementById("blockedArticlesArea");
        var blockedReplacementModal = document.getElementById("blockedReplacementModal");
        var blockedModalDetails = document.getElementById("blockedModalDetails");
        var blockedSearchInput = document.getElementById("blockedSearchInput");
        var blockedSearchBtn = document.getElementById("blockedSearchBtn");
        var blockedSearchResults = document.getElementById("blockedSearchResults");
        var blockedReplacementArtnr = document.getElementById("blockedReplacementArtnr");
        var blockedConfirmBtn = document.getElementById("blockedConfirmBtn");
        var blockedIgnoreBtn = document.getElementById("blockedIgnoreBtn");
        var blockedTextBtn = document.getElementById("blockedTextBtn");
        if (blockedArticlesContainer && showBlockedArticlesBtn && blockedArticlesArea) {
            showBlockedArticlesBtn.addEventListener("click", function() {
                if (blockedArticlesArea.style.display === "none") {
                    blockedArticlesArea.style.display = "block";
                    showBlockedArticlesBtn.textContent = "Hide Blocked Articles";
                } else {
                    blockedArticlesArea.style.display = "none";
                    showBlockedArticlesBtn.textContent = "Show Blocked Articles";
                }
            });
            blockedArticlesContainer.style.display = "none";
            blockedArticlesArea.style.display = "none";
        }

        function updateBlockedArticlesPanel(data) {
            if (blockedArticlesContainer && showBlockedArticlesBtn && blockedArticlesArea) {
                if (data.blocked_articles && data.blocked_articles.trim().length > 0) {
                    blockedArticlesArea.value = data.blocked_articles;
                    blockedArticlesContainer.style.display = "block";
                    blockedArticlesArea.style.display = "none";
                    showBlockedArticlesBtn.style.display = "inline-block";
                    showBlockedArticlesBtn.textContent = "Show Blocked Articles";
                } else {
                    blockedArticlesContainer.style.display = "none";
                    blockedArticlesArea.value = "";
                }
            }
        }

        function renderBlockedDetails(item) {
            var lines = [
                `artnr: ${item.artnr || ""}`,
                `artbez1: ${item.artbez1 || ""}`,
                `artbez2: ${item.artbez2 || ""}`,
                `artbez3: ${item.artbez3 || ""}`,
                `artbezmem: ${item.artbezmem || ""}`,
                `zeichnr: ${item.zeichnr || ""}`
            ];
            return lines.join("\n");
        }

        function searchReplacementArticles(query) {
            return fetch(`/search?query=${encodeURIComponent(query)}&mode=article`)
                .then(function(response) { return response.json(); })
                .then(function(data) {
                    if (!data || !Array.isArray(data.results)) {
                        return [];
                    }
                    return data.results;
                })
                .catch(function() { return []; });
        }

        function showBlockedReplacementFlow(moduleArtnr, existingArticlesTarget, blockedItems) {
            if (!blockedReplacementModal || !blockedModalDetails || !blockedSearchBtn || !blockedConfirmBtn || !blockedIgnoreBtn) {
                return Promise.resolve(null);
            }
            if (!Array.isArray(blockedItems) || blockedItems.length === 0) {
                return Promise.resolve(null);
            }

            var replacementMap = {};
            var idx = 0;

            return new Promise(function(resolve) {
                function finishFlow() {
                    blockedReplacementModal.style.display = "none";
                    if (!Object.keys(replacementMap).length) {
                        resolve(null);
                        return;
                    }

                    fetch("/generate-module-apply-replacements", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({
                            artnr: moduleArtnr,
                            existing_articles_target: existingArticlesTarget,
                            replacement_map: replacementMap
                        })
                    })
                    .then(function(response) {
                        return response.text().then(function(text) {
                            try {
                                return text ? JSON.parse(text) : { status: "error", message: "Empty response" };
                            } catch (e) {
                                return { status: "error", message: text || "Invalid response format" };
                            }
                        });
                    })
                    .then(function(data) { resolve(data); })
                    .catch(function(err) {
                        resolve({ status: "error", message: err.message || String(err) });
                    });
                }

                function showCurrentBlockedItem() {
                    if (idx >= blockedItems.length) {
                        finishFlow();
                        return;
                    }

                    var item = blockedItems[idx] || {};
                    blockedModalDetails.textContent = renderBlockedDetails(item);
                    blockedSearchResults.innerHTML = "";
                    // Do NOT pre-fill search or replacement fields with the blocked article's artnr.
                    blockedSearchInput.value = "";
                    blockedReplacementArtnr.value = "";
                    blockedReplacementModal.style.display = "flex";

                    // Add style for selected search result if not present
                    if (!document.getElementById('blocked-search-result-style')) {
                        var style = document.createElement('style');
                        style.id = 'blocked-search-result-style';
                        style.innerHTML = `.selected-blocked-search-result { background: #d0eaff; font-weight: bold; }`;
                        document.head.appendChild(style);
                    }

                    let selectedRow = null;
                    blockedSearchBtn.onclick = function() {
                        var q = (blockedSearchInput.value || "").trim();
                        if (!q) {
                            blockedSearchResults.innerHTML = "";
                            selectedRow = null;
                            return;
                        }
                        searchReplacementArticles(q).then(function(results) {
                            if (!results.length) {
                                blockedSearchResults.innerHTML = `<div class='blocked-search-results-item'>${t("modalNoResults")}</div>`;
                                selectedRow = null;
                                return;
                            }
                            blockedSearchResults.innerHTML = "";
                            selectedRow = null;
                            results.slice(0, 20).forEach(function(r) {
                                var row = document.createElement("div");
                                row.className = "blocked-search-results-item";
                                row.textContent = `${r.artnr || ""} | ${r.artbez1 || ""} | ${r.zeichnr || ""}`;
                                row.addEventListener("click", function() {
                                    // Remove highlight from previous
                                    if (selectedRow) selectedRow.classList.remove("selected-blocked-search-result");
                                    row.classList.add("selected-blocked-search-result");
                                    selectedRow = row;
                                    blockedReplacementArtnr.value = r.artnr || "";
                                });
                                blockedSearchResults.appendChild(row);
                            });
                        });
                    };

                    blockedConfirmBtn.onclick = function() {
                        var repl = (blockedReplacementArtnr.value || "").trim();
                        if (!repl) {
                            alert(t("modalNeedReplacement"));
                            return;
                        }
                        replacementMap[item.artnr] = repl;
                        idx += 1;
                        showCurrentBlockedItem();
                    };

                    blockedIgnoreBtn.onclick = function() {
                        idx += 1;
                        showCurrentBlockedItem();
                    };

                    if (blockedTextBtn) {
                        blockedTextBtn.onclick = function() {
                            // Mark this blocked article as Textartikel
                            replacementMap[item.artnr] = { textartikel: true };
                            idx += 1;
                            showCurrentBlockedItem();
                        };
                    }
                }

                showCurrentBlockedItem();
            });
        }
    // Set Search & Transform as default tab
    var tablinks = document.getElementsByClassName("tablink");
    if (tablinks && tablinks.length > 0) {
        tablinks[0].click();
    }

    function getExistingArticlesTarget() {
        var radios = document.getElementsByName("existingArticlesTarget");
        for (var i = 0; i < radios.length; i++) {
            if (radios[i].checked) {
                return radios[i].value;
            }
        }
        return "none";
    }

    // No need for wireExclusiveTargetCheckboxes with radios

    function getSelectedSheetHeaders() {
        var checked = document.querySelectorAll('#sheetsCheckboxes input[name="sheetHeader"]:checked');
        return Array.from(checked).map(function(input) { return input.value; });
    }

    function loadSheetCheckboxes() {
        var container = document.getElementById("sheetsCheckboxes");
        if (!container) return;

        fetch("/sheets-config")
            .then(function(response) { return response.json(); })
            .then(function(data) {
                if (data.status !== "success") {
                    container.innerHTML = "<p style='color:#c00;'>Failed to load sheet configuration.</p>";
                    return;
                }

                var headers = Array.isArray(data.headers) ? data.headers : [];
                var activeHeaders = new Set(Array.isArray(data.active_headers) ? data.active_headers : []);

                if (!headers.length) {
                    container.innerHTML = "<p>No sheet headers found.</p>";
                    return;
                }

                container.innerHTML = headers.map(function(header, idx) {
                    var checked = activeHeaders.has(header) ? "checked" : "";
                    return "<label style='display:block; margin:6px 0;'>" +
                        "<input type='checkbox' name='sheetHeader' value='" + header + "' " + checked + "> " +
                        header +
                        "</label>";
                }).join("");
            })
            .catch(function() {
                container.innerHTML = "<p style='color:#c00;'>Failed to load sheet configuration.</p>";
            });
    }

    loadSheetCheckboxes();

    // Search mode toggle
    var toggleModeBtn = document.getElementById("toggleModeBtn");
    var searchModeLabel = document.getElementById("searchModeLabel");
    var modeSwitchIcon = document.getElementById("modeSwitchIcon");
    var modePillIcon = document.getElementById("modePillIcon");
    var modePillText = document.getElementById("modePillText");
    if (toggleModeBtn && searchModeLabel && modeSwitchIcon && modePillIcon && modePillText) {
        function updateModeUI() {
            if (window.searchMode === "article") {
                modeSwitchIcon.textContent = "↔️";
                toggleModeBtn.style.background = "linear-gradient(90deg, #3498db 0%, #6dd5ed 100%)";
                searchModeLabel.classList.remove("mode-module");
                searchModeLabel.classList.add("mode-article");
                modePillIcon.textContent = "🔎";
                modePillText.textContent = "Article";
            } else {
                modeSwitchIcon.textContent = "↔️";
                toggleModeBtn.style.background = "linear-gradient(90deg, #43c6ac 0%, #217dbb 100%)";
                searchModeLabel.classList.remove("mode-article");
                searchModeLabel.classList.add("mode-module");
                modePillIcon.textContent = "📦";
                modePillText.textContent = "Module";
            }
            updateArticleModeUI();
        }
        updateModeUI();
        toggleModeBtn.addEventListener("click", function() {
            window.searchMode = (window.searchMode === "article") ? "module" : "article";
            updateModeUI();
            updateArticleModeUI();
        });
    }

    // File upload
    var uploadForm = document.getElementById("uploadForm");
    if (uploadForm) {
        uploadForm.addEventListener("submit", function(e) {
            e.preventDefault();
            var formData = new FormData(uploadForm);
            var uploadTargetEnv = document.getElementById("uploadTargetEnv");
            var targetEnv = uploadTargetEnv ? uploadTargetEnv.value : "test";
            formData.set("target_env", targetEnv);

            fetch("/upload-ifas-artikelstamm", {
                method: "POST",
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === "success") {
                    document.getElementById("uploadStatus").innerText = data.message || "Upload successful!";
                } else {
                    document.getElementById("uploadStatus").innerText = data.message || "Upload failed.";
                }
            })
            .catch(() => {
                document.getElementById("uploadStatus").innerText = "Upload failed.";
            });
        });
    }

    // Search form with API call and feedback log
    var searchForm = document.getElementById("searchForm");
    var feedbackLog = document.getElementById("feedbackLog");
    var currentSelection = document.getElementById("currentSelection");
    var selectedResult = null;

    // Download Module Excel (direct xlsx)
    var downloadModuleExcelBtn = document.getElementById("downloadModuleExcelBtn");
    if (downloadModuleExcelBtn && currentSelection) {
        downloadModuleExcelBtn.addEventListener("click", function() {
            if (searchMode !== "module") {
                alert("Switch to Module mode to download module Excel.");
                return;
            }
            if (!selectedResult || !selectedResult.artnr) {
                alert("No module selected.");
                return;
            }

            var artnr = selectedResult.artnr;
            var existingArticlesTarget = getExistingArticlesTarget();
            if (existingArticlesTarget === "invalid") {
                alert("Only one existing-articles checkbox can be selected.");
                return;
            }

            fetch(`/download-module-excel?artnr=${encodeURIComponent(artnr)}&existing_articles_target=${encodeURIComponent(existingArticlesTarget)}&mode=module`)
                .then(function(response) {
                    if (!response.ok) {
                        return response.text().then(function(text) {
                            let message;
                            try {
                                const data = JSON.parse(text);
                                message = data.message || "Failed to create Excel file.";
                            } catch {
                                message = text || "Failed to create Excel file.";
                            }
                            throw new Error(message);
                        });
                    }

                    var disposition = response.headers.get("content-disposition") || "";
                    var fileName = `module_export_${artnr}.xlsx`;
                    var match = disposition.match(/filename="?([^";]+)"?/i);
                    if (match && match[1]) {
                        fileName = match[1];
                    }

                    return response.blob().then(function(blob) {
                        return { blob: blob, fileName: fileName };
                    });
                })
                .then(function(result) {
                    var url = window.URL.createObjectURL(result.blob);
                    var link = document.createElement("a");
                    link.href = url;
                    link.download = result.fileName;
                    document.body.appendChild(link);
                    link.click();
                    document.body.removeChild(link);
                    window.URL.revokeObjectURL(url);

                    let entry = `<div><b>Download Module Excel:</b> ${artnr} — <span style='color:#27ae60;'>Excel created and downloaded.</span></div>`;
                    feedbackLog.innerHTML = entry + feedbackLog.innerHTML;
                })
                .catch(function(err) {
                    let entry = `<div><b>Download Module Excel:</b> ${artnr} — <span style='color:#c00;'>Error: ${err.message || err}</span></div>`;
                    feedbackLog.innerHTML = entry + feedbackLog.innerHTML;
                });
        });
    }

    if (searchForm && feedbackLog && currentSelection) {
        searchForm.addEventListener("submit", function(e) {
            e.preventDefault();
            var query = document.getElementById("searchInput").value;
            if (!query) return;
            fetch(`/search?query=${encodeURIComponent(query)}&mode=${encodeURIComponent(searchMode)}`)
                .then(response => response.json())
                .then(data => {
                    let entry = `<div><b>Search (${searchMode}):</b> "${query}"<br>`;
                    if (data.results && data.results.length > 0) {
                        entry += `<b>Results:</b><ul style='margin:0;' id='searchResultsList'>`;
                        data.results.slice(0, 5).forEach((row, idx) => {
                            let display = `${row.artnr} | ${row.artbez1} | ${row.zeichnr}`;
                            entry += `<li style='cursor:pointer;' data-idx='${idx}'>${display}</li>`;
                        });
                        if (data.results.length > 5) entry += `<li>...and ${data.results.length - 5} more</li>`;
                        entry += `</ul>`;
                        // Select the first result by default
                        selectedResult = data.results[0];
                        currentSelection.value = `${selectedResult.artnr} | ${selectedResult.artbez1} | ${selectedResult.zeichnr}`;
                    } else {
                        entry += `<span style='color:#c00;'>No results found.</span>`;
                        selectedResult = null;
                        currentSelection.value = '';
                    }
                    entry += `</div>`;
                    feedbackLog.innerHTML = entry + feedbackLog.innerHTML;
                    // Removed: document.getElementById("transformBtn").style.display = "block";

                    // Add click listeners to results for selection
                    setTimeout(function() {
                        var list = document.getElementById('searchResultsList');
                        if (list) {
                            Array.from(list.children).forEach(function(li, idx) {
                                li.addEventListener('click', function() {
                                    selectedResult = data.results[idx];
                                    currentSelection.value = `${selectedResult.artnr} | ${selectedResult.artbez1} | ${selectedResult.zeichnr}`;
                                    // Highlight selected
                                    Array.from(list.children).forEach(el => el.style.background = '');
                                    li.style.background = '#d0eaff';
                                });
                                // Highlight first by default
                                if (idx === 0) li.style.background = '#d0eaff';
                            });
                        }
                    }, 0);
                })
                .catch(err => {
                    let entry = `<div><b>Search (${searchMode}):</b> "${query}"<br><span style='color:#c00;'>Error: ${err}</span></div>`;
                    feedbackLog.innerHTML = entry + feedbackLog.innerHTML;
                    selectedResult = null;
                    currentSelection.value = '';
                });
        });
    }
    // Generate Module button logic (now inside DOMContentLoaded)
    var generateModuleBtn = document.getElementById("generateModuleBtn");
    if (generateModuleBtn && currentSelection) {
        generateModuleBtn.addEventListener("click", function() {
            if (searchMode !== "module") {
                alert(t("alertSwitchModule"));
                return;
            }
            if (!selectedResult || !selectedResult.artnr) {
                alert(t("alertNoModule"));
                return;
            }

            var existingArticlesTarget = getExistingArticlesTarget();
            if (existingArticlesTarget === "invalid") {
                alert(t("alertOneTarget"));
                return;
            }

            fetch("/generate-module", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    artnr: selectedResult.artnr,
                    existing_articles_target: existingArticlesTarget
                })
            })
            .then(function(response) {
                // Try to parse JSON, with fallback to text if not JSON
                return response.text().then(function(text) {
                    try {
                        var data = text ? JSON.parse(text) : { status: "error", message: "Empty response" };
                        return { ok: response.ok, data: data };
                    } catch (e) {
                        return { ok: response.ok, data: { status: "error", message: text || "Invalid response format" } };
                    }
                });
            })
            .then(function(result) {
                var data = result.data;
                let entry = `<div><b>Generate Module:</b> ${selectedResult.artnr} — <span style='color:${data.status === 'success' ? '#27ae60' : '#c00'};'>${data.message}</span></div>`;
                feedbackLog.innerHTML = entry + feedbackLog.innerHTML;

                updateBlockedArticlesPanel(data);

                return showBlockedReplacementFlow(selectedResult.artnr, existingArticlesTarget, data.blocked_items || [])
                    .then(function(replacementResult) {
                        if (!replacementResult) {
                            return;
                        }

                        let replacementEntry = `<div><b>Apply Replacements:</b> ${selectedResult.artnr} — <span style='color:${replacementResult.status === 'success' ? '#27ae60' : '#c00'};'>${replacementResult.message}</span></div>`;
                        feedbackLog.innerHTML = replacementEntry + feedbackLog.innerHTML;
                        updateBlockedArticlesPanel(replacementResult);
                    });
            })
            .catch(function(err) {
                let entry = `<div><b>Generate Module:</b> ${selectedResult.artnr} — <span style='color:#c00;'>Error: ${err}</span></div>`;
                feedbackLog.innerHTML = entry + feedbackLog.innerHTML;
            });
        });
    }

        // Generate Module Data button logic
        var generateModuleDataBtn = document.getElementById("generateModuleDataBtn");
        if (generateModuleDataBtn && currentSelection) {
            generateModuleDataBtn.addEventListener("click", function() {
                if (searchMode !== "module") {
                    alert("Switch to Module mode to generate module data.");
                    return;
                }
                if (!selectedResult || !selectedResult.artnr) {
                    alert("No module selected.");
                    return;
                }

                var selectedHeaders = getSelectedSheetHeaders();
                if (!selectedHeaders.length) {
                    alert("No sheets selected in Settings.");
                    return;
                }

                fetch("/generate-module-data", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        artnr: selectedResult.artnr,
                        selected_headers: selectedHeaders,
                        mode: "module"
                    })
                })
                .then(response => response.json())
                .then(data => {
                    let entry = `<div><b>Generate Module Data:</b> ${selectedResult.artnr} — <span style='color:${data.status === 'success' ? '#27ae60' : '#c00'};'>${data.message}</span></div>`;
                    feedbackLog.innerHTML = entry + feedbackLog.innerHTML;
                })
                .catch(err => {
                    let entry = `<div><b>Generate Module Data:</b> ${selectedResult.artnr} — <span style='color:#c00;'>Error: ${err}</span></div>`;
                    feedbackLog.innerHTML = entry + feedbackLog.innerHTML;
                });
            });
        }

    // Download Module Export (zip with excel + partlist + tree)
    var downloadModuleExportBtn = document.getElementById("downloadModuleExportBtn");
    if (downloadModuleExportBtn && currentSelection) {
        downloadModuleExportBtn.addEventListener("click", function() {
            if (searchMode !== "module") {
                alert("Switch to Module mode to download module export.");
                return;
            }
            if (!selectedResult || !selectedResult.artnr) {
                alert("No module selected.");
                return;
            }

            var artnr = selectedResult.artnr;
            var existingArticlesTarget = getExistingArticlesTarget();
            if (existingArticlesTarget === "invalid") {
                alert("Only one existing-articles checkbox can be selected.");
                return;
            }

            fetch(`/download-module-export?artnr=${encodeURIComponent(artnr)}&existing_articles_target=${encodeURIComponent(existingArticlesTarget)}`)
                .then(function(response) {
                    if (!response.ok) {
                        return response.json().then(function(err) {
                            throw new Error(err.message || "Failed to create export zip.");
                        });
                    }

                    var disposition = response.headers.get("content-disposition") || "";
                    var fileName = `module_export_${artnr}.zip`;
                    var match = disposition.match(/filename="?([^";]+)"?/i);
                    if (match && match[1]) {
                        fileName = match[1];
                    }

                    return response.blob().then(function(blob) {
                        return { blob: blob, fileName: fileName };
                    });
                })
                .then(function(result) {
                    var url = window.URL.createObjectURL(result.blob);
                    var link = document.createElement("a");
                    link.href = url;
                    link.download = result.fileName;
                    document.body.appendChild(link);
                    link.click();
                    document.body.removeChild(link);
                    window.URL.revokeObjectURL(url);

                    let entry = `<div><b>Download Module Export:</b> ${artnr} — <span style='color:#27ae60;'>ZIP created, archived, and downloaded.</span></div>`;
                    feedbackLog.innerHTML = entry + feedbackLog.innerHTML;
                })
                .catch(function(err) {
                    let entry = `<div><b>Download Module Export:</b> ${artnr} — <span style='color:#c00;'>Error: ${err.message || err}</span></div>`;
                    feedbackLog.innerHTML = entry + feedbackLog.innerHTML;
                });
        });
    }

    // Download Partlist Tree button
    var downloadPartlistTreeBtn = document.getElementById("downloadPartlistTreeBtn");
    if (downloadPartlistTreeBtn && currentSelection) {
        downloadPartlistTreeBtn.addEventListener("click", function() {
            if (!selectedResult || !selectedResult.artnr) {
                alert("No article selected for tree download.");
                return;
            }
            const artnr = selectedResult.artnr;
            const url = `/download-partlist-tree?mode=module&artnr=${encodeURIComponent(artnr)}`;
            // Create a hidden link and trigger download
            const link = document.createElement('a');
            link.href = url;
            link.download = `partlist_tree_${artnr}.txt`;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        });
    }
});
