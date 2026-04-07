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
    var defaultTab = document.getElementById("defaultTab");
    if (defaultTab) defaultTab.click();

    // Search mode toggle
    var searchMode = "article";
    var toggleModeBtn = document.getElementById("toggleModeBtn");
    var searchModeLabel = document.getElementById("searchModeLabel");
    if (toggleModeBtn && searchModeLabel) {
        toggleModeBtn.addEventListener("click", function() {
            if (searchMode === "article") {
                searchMode = "module";
                toggleModeBtn.innerText = "Switch to Article Search";
                searchModeLabel.innerText = "Mode: Module";
            } else {
                searchMode = "article";
                toggleModeBtn.innerText = "Switch to Module Search";
                searchModeLabel.innerText = "Mode: Article";
            }
        });
    }

    // File upload
    var uploadForm = document.getElementById("uploadForm");
    if (uploadForm) {
        uploadForm.addEventListener("submit", function(e) {
            e.preventDefault();
            var formData = new FormData(uploadForm);
            fetch("/upload-file", {
                method: "POST",
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                document.getElementById("uploadStatus").innerText = data.status ? "Upload successful!" : "Upload failed.";
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
                    document.getElementById("transformBtn").style.display = "block";

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
            fetch("/generate-module", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ artnr: selectedResult.artnr })
            })
            .then(response => response.json())
            .then(data => {
                let entry = `<div><b>Generate Module:</b> ${selectedResult.artnr} — <span style='color:${data.status === 'success' ? '#27ae60' : '#c00'};'>${data.message}</span></div>`;
                feedbackLog.innerHTML = entry + feedbackLog.innerHTML;
            })
            .catch(err => {
                let entry = `<div><b>Generate Module:</b> ${selectedResult.artnr} — <span style='color:#c00;'>Error: ${err}</span></div>`;
                feedbackLog.innerHTML = entry + feedbackLog.innerHTML;
            });
        });
    }

        // Generate Module Data button logic (placeholder)
        var generateModuleDataBtn = document.getElementById("generateModuleDataBtn");
        if (generateModuleDataBtn && currentSelection) {
            generateModuleDataBtn.addEventListener("click", function() {
                if (!selectedResult) {
                    feedbackLog.innerHTML = `<div style='color:#c00;'>No article/module selected.</div>` + feedbackLog.innerHTML;
                    return;
                }
                feedbackLog.innerHTML = `<div>Generate Module Data clicked for: ${selectedResult.artnr}</div>` + feedbackLog.innerHTML;
                // TODO: Implement actual API call for module data generation
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
            link.download = `partlist_tree_${artnr}.json`;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        });
    }
});
