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

            // Download Partlist Excel button
            var downloadPartlistExcelBtn = document.getElementById("downloadPartlistExcelBtn");
            if (downloadPartlistExcelBtn) {
                downloadPartlistExcelBtn.addEventListener("click", function() {
                    fetch("/download-partlist-excel")
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
    var searchMode = "article";
    var toggleModeBtn = document.getElementById("toggleModeBtn");
    var searchModeLabel = document.getElementById("searchModeLabel");
    var modeSwitchIcon = document.getElementById("modeSwitchIcon");
    var modePillIcon = document.getElementById("modePillIcon");
    var modePillText = document.getElementById("modePillText");
    if (toggleModeBtn && searchModeLabel && modeSwitchIcon && modePillIcon && modePillText) {
        function updateModeUI() {
            if (searchMode === "article") {
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
        }
        updateModeUI();
        toggleModeBtn.addEventListener("click", function() {
            searchMode = (searchMode === "article") ? "module" : "article";
            updateModeUI();
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

            fetch(`/download-module-excel?artnr=${encodeURIComponent(artnr)}&existing_articles_target=${encodeURIComponent(existingArticlesTarget)}`)
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
                alert("Switch to Module mode to generate a module.");
                return;
            }
            if (!selectedResult || !selectedResult.artnr) {
                alert("No module selected.");
                return;
            }

            var existingArticlesTarget = getExistingArticlesTarget();
            if (existingArticlesTarget === "invalid") {
                alert("Only one existing-articles checkbox can be selected.");
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
                // Blocked articles UI
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
                        selected_headers: selectedHeaders
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
            const url = `/download-partlist-tree?artnr=${encodeURIComponent(artnr)}`;
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
