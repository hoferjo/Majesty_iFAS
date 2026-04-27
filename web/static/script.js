    // Upload Existing Partlist (Settings Tab)
    var uploadExistingPartlistForm = document.getElementById("uploadExistingPartlistForm");
    if (uploadExistingPartlistForm) {
        uploadExistingPartlistForm.addEventListener("submit", function(e) {
            e.preventDefault();
            var fileInput = document.getElementById("existingPartlistFile");
            var envSelect = document.getElementById("existingPartlistEnv");
            var feedbackLog = document.getElementById("feedbackLog");
            var statusBox = document.getElementById("existingPartlistUploadStatus");
            if (!fileInput.files.length) {
                alert("Please select a CSV file to upload.");
                return;
            }
            var formData = new FormData();
            formData.append("existing_partlist_file", fileInput.files[0]);
            formData.append("partlist_env", envSelect.value);
            fetch("/upload-existing-partlist", {
                method: "POST",
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                let entry = `<div><b>Upload Existing Partlist:</b> <span style='color:${data.status === 'ok' ? '#27ae60' : '#c00'};'>${data.status === 'ok' ? 'Upload successful.' : 'Upload failed.'}</span></div>`;
                if (statusBox) {
                    statusBox.innerHTML = entry;
                }
                if (feedbackLog) feedbackLog.innerHTML = entry + feedbackLog.innerHTML;
                else alert(data.status === 'ok' ? 'Upload successful.' : 'Upload failed.');
            })
            .catch(err => {
                let entry = `<div><b>Upload Existing Partlist:</b> <span style='color:#c00;'>Error: ${err.message || err}</span></div>`;
                if (statusBox) {
                    statusBox.innerHTML = entry;
                }
                if (feedbackLog) feedbackLog.innerHTML = entry + feedbackLog.innerHTML;
                else alert('Upload failed.');
            });
        });
    }
// Helper: fetch and show partlist tree preview
    function showPartlistTreePreview(artnr, mode = "creation") {
        const container = document.getElementById("partlistTreePreview");
        if (!container) return;
        container.innerHTML = '<div style="color:#888;">Loading partlist tree...</div>';
        fetch(`/download-partlist-tree?artnr=${encodeURIComponent(artnr)}&mode=${encodeURIComponent(mode)}`)
            .then(response => {
                if (!response.ok) throw new Error("No partlist tree found for this article.");
                return response.text();
            })
            .then(text => {
                container.innerHTML = `<pre style='background:#f8f8f8;padding:1em;border-radius:6px;max-height:350px;overflow:auto;'>${text}</pre>`;
            })
            .catch(err => {
                container.innerHTML = `<div style='color:#c00;'>${err.message || err}</div>`;
            });
    }
// Update Majesty Data button
    var updateMajestyForm = document.getElementById("updateMajestyForm");
    if (updateMajestyForm) {
        updateMajestyForm.addEventListener("submit", function(e) {
            e.preventDefault();
            fetch("/update-majesty-data", { method: "POST" })
                .then(response => response.json())
                .then(data => {
                    let feedbackLog = document.getElementById("feedbackLog");
                    let entry = `<div><b>Update Majesty Data:</b> <span style='color:${data.status === "success" ? "#27ae60" : "#c00"};'>${data.message || (data.status === "success" ? "Update complete." : "Update failed.")}</span></div>`;
                    if (feedbackLog) feedbackLog.innerHTML = entry + feedbackLog.innerHTML;
                })
                .catch(() => {
                    let feedbackLog = document.getElementById("feedbackLog");
                    let entry = `<div><b>Update Majesty Data:</b> <span style='color:#c00;'>Update failed.</span></div>`;
                    if (feedbackLog) feedbackLog.innerHTML = entry + feedbackLog.innerHTML;
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
                    let feedbackLog = document.getElementById("feedbackLog");
                    let entry = `<div><b>Hard Update Majesty Data:</b> <span style='color:${data.status === "success" ? "#27ae60" : "#c00"};'>${data.message || (data.status === "success" ? "Hard update complete." : "Update failed.")}</span></div>`;
                    if (feedbackLog) feedbackLog.innerHTML = entry + feedbackLog.innerHTML;
                })
                .catch(() => {
                    let feedbackLog = document.getElementById("feedbackLog");
                    let entry = `<div><b>Hard Update Majesty Data:</b> <span style='color:#c00;'>Update failed.</span></div>`;
                    if (feedbackLog) feedbackLog.innerHTML = entry + feedbackLog.innerHTML;
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
    // ─── Creation Workflow (stateful) ────────────────────────────────────────────
    var createRootArticleBtn = document.getElementById("createRootArticleBtn");
    var rootArticleFormContainer = document.getElementById("rootArticleFormContainer");

    function escHtml(text) {
        return String(text).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    }

    function fetchArticleTypes() {
        return fetch("/api/article-types")
            .then(res => res.json())
            .then(data => (Array.isArray(data.types) ? data.types : []));
    }

    function fetchArticleFields(type) {
        return fetch(`/api/article-fields?type=${encodeURIComponent(type)}`).then(r => r.json());
    }

    function fetchCreationState() {
        return fetch("/api/creation/state").then(r => r.json());
    }

    // ─── Hierarchical structure fetchers ──────────────────────────────────────
    function fetchClasses() {
        return fetch("/api/creation/structure")
            .then(res => res.json())
            .then(data => (Array.isArray(data.classes) ? data.classes : []));
    }

    function fetchGroupsForClass(className) {
        return fetch(`/api/creation/groups?class_name=${encodeURIComponent(className)}`)
            .then(res => res.json())
            .then(data => (Array.isArray(data.groups) ? data.groups : []));
    }

    function fetchTypesForGroup(groupName) {
        return fetch(`/api/creation/types?group_name=${encodeURIComponent(groupName)}`)
            .then(res => res.json())
            .then(data => ({
                types: Array.isArray(data.types) ? data.types : [],
                hasSubtypes: data.has_subtypes || false
            }));
    }

    function fetchAllowedChildren(parentType) {
        return fetch(`/api/creation/allowed-children?parent_type=${encodeURIComponent(parentType)}`)
            .then(res => res.json())
            .then(data => (Array.isArray(data.allowed_types) ? data.allowed_types : []));
    }

    // ─── Fields renderer (shared between root and child forms) ────────────────
    function renderFieldsHtml(fields) {
        let html = '';
        // Filter to show only input fields
        const inputFields = fields.filter(field => field.group === 'input');
        inputFields.forEach(field => {
            const defVal = (field.value !== null && field.value !== undefined) ? String(field.value) : '';
            if (field.group === 'dropdown' && Array.isArray(field.options)) {
                html += `<label style='display:block;margin:6px 0;'>${escHtml(field.name)}: <select name='${escHtml(field.name)}' style='width:92%;padding:4px;'>`;
                field.options.forEach(opt => {
                    html += `<option value='${escHtml(opt)}'${defVal === opt ? ' selected' : ''}>${escHtml(opt)}</option>`;
                });
                html += `</select></label>`;
            } else if (field.group === 'search' && field.search_query === 'lieferant') {
                html += `<label style='display:block;margin:6px 0;'>${escHtml(field.name)}: <input type='text' name='${escHtml(field.name)}' value='${escHtml(defVal)}' style='width:80%;padding:4px;display:inline-block;' readonly><button type='button' class='lieferant-search-btn' data-field='${escHtml(field.name)}' style='margin-left:0.5em;'>🔍</button></label>`;
            } else {
                html += `<label style='display:block;margin:6px 0;'>${escHtml(field.name)}: <input type='text' name='${escHtml(field.name)}' value='${escHtml(defVal)}' style='width:90%;padding:4px;' ${field.editable === false ? 'readonly' : ''}></label>`;
            }
        });
        return html;
    }

    function attachLieferantSearch(container) {
        container.querySelectorAll('.lieferant-search-btn').forEach(btn => {
            btn.addEventListener('click', function () {
                const fieldName = btn.getAttribute('data-field');
                showLieferantSearchModal(function (selected) {
                    if (selected && selected.ifas_nummer) {
                        const input = container.querySelector(`input[name='${fieldName}']`);
                        if (input) input.value = selected.ifas_nummer;
                    }
                });
            });
        });
    }

    function attachExistenceCheck(container, formSelector) {
        const form = container.querySelector(formSelector);
        if (!form) return;
        container.querySelectorAll("input[name='artnr'],input[name='modnr']").forEach(input => {
            input.addEventListener('blur', function () { checkExistenceInline(input.value, form); });
        });
    }

    function checkExistenceInline(artnr, form) {
        if (!artnr || !form) return;
        fetch(`/api/check-article-exists?artnr=${encodeURIComponent(artnr)}&mode=creation`)
            .then(r => r.json())
            .then(data => {
                let msgDiv = form.querySelector('.cs-exists-msg');
                if (!msgDiv) {
                    msgDiv = document.createElement('div');
                    msgDiv.className = 'cs-exists-msg';
                    msgDiv.style.margin = '0.5em 0';
                    form.insertBefore(msgDiv, form.firstChild);
                }
                if (data.status === "found_in_creation") {
                    msgDiv.innerHTML = `<span style='color:#c00;'>Already exists in this session. Choose a unique number.</span>`;
                } else if (data.status === "found") {
                    msgDiv.innerHTML = `<span style='color:#e67e22;'>Article exists in Majesty.</span>`;
                } else {
                    msgDiv.innerHTML = `<span style='color:#27ae60;'>New article (not in Majesty).</span>`;
                }
            })
            .catch(() => {});
    }

    // ─── Session panel ────────────────────────────────────────────────────────
    function renderSessionPanel(state) {
        if (!rootArticleFormContainer) return;
        rootArticleFormContainer.style.display = "block";

        const stack = state.stack || [];
        const current = stack.length > 0 ? stack[stack.length - 1] : null;
        const treeText = state.tree_text || "";
        const isComplete = state.is_complete || false;
        const isActive = state.is_active || false;

        const breadcrumb = stack.length
            ? stack.map((s, i) => {
                const isLast = i === stack.length - 1;
                return `<span style='${isLast ? "font-weight:600;color:#2980b9;" : "color:#888;"}'>${escHtml(s.artnr)} (${escHtml(s.artbez1)})</span>`;
            }).join(" <span style='color:#ccc;margin:0 0.3em;'>›</span> ")
            : '<span style="color:#888;">(root)</span>';

        if (isComplete) {
            rootArticleFormContainer.innerHTML = `
                <div style="color:#27ae60;font-weight:600;margin-bottom:0.8em;">Session complete — root module finished.</div>
                <div style="margin-bottom:1em;font-size:0.9em;">${breadcrumb}</div>
                <pre style="background:#f8f8f8;padding:1em;border-radius:6px;max-height:350px;overflow:auto;font-size:0.88em;">${escHtml(treeText)}</pre>
                <div style="margin-top:1em;display:flex;gap:0.7em;flex-wrap:wrap;">
                    <button id="cs-download-tree-btn" class="modern-btn">Download Partlist Tree</button>
                    <button id="cs-download-partlist-btn" class="modern-btn">Download Partlist</button>
                    <button id="cs-download-group-btn" class="modern-btn">Download Group (XLSX)</button>
                    <button id="cs-reset-btn" class="modern-btn secondary">Start New Session</button>
                </div>`;
                // Download Group (XLSX) button
                const dlGroupBtn = el("cs-download-group-btn");
                if (dlGroupBtn) dlGroupBtn.onclick = function () {
                    const rootArtnr = (state.stack || []).length > 0 ? state.stack[0].artnr : "";
                    if (!rootArtnr) { alert("No root article found."); return; }
                    const a = document.createElement('a');
                    a.href = `/download-group-excel?artnr=${encodeURIComponent(rootArtnr)}&mode=creation`;
                    a.download = `group_export_${rootArtnr}.xlsx`;
                    document.body.appendChild(a);
                    a.click();
                    document.body.removeChild(a);
                };
        } else if (!isActive || !current) {
            rootArticleFormContainer.innerHTML = `<div style="color:#888;">No active creation session.</div>`;
        } else {
            const finishLabel = stack.length <= 1
                ? 'Finish Root &amp; Complete'
                : `Finish Module: ${escHtml(current.artnr)}`;
            rootArticleFormContainer.innerHTML = `
                <div style="margin-bottom:0.8em;">
                    <div style="font-size:0.85em;color:#888;margin-bottom:0.3em;">Current path:</div>
                    <div>${breadcrumb}</div>
                </div>
                <div style="margin-bottom:1em;padding:0.6em 0.9em;background:#f0f8ff;border-radius:6px;border-left:3px solid #2980b9;">
                    <strong>Building: ${escHtml(current.artnr)}</strong> — ${escHtml(current.artbez1)}
                    <span style="color:#888;font-size:0.85em;margin-left:1em;">Depth ${stack.length - 1} · Next pos ${current.pos_counter}</span>
                </div>
                <div style="display:flex;gap:0.7em;flex-wrap:wrap;margin-bottom:1.2em;">
                    <button id="cs-add-article-btn" class="modern-btn">+ Add Article</button>
                    <button id="cs-add-module-btn" class="modern-btn">+ Add Module</button>
                    <button id="cs-finish-btn" class="modern-btn" style="background:#27ae60;color:#fff;">${finishLabel}</button>
                    <button id="cs-reset-btn" class="modern-btn secondary">Reset</button>
                </div>
                <div style="font-weight:600;margin-bottom:0.3em;font-size:0.88em;">Partlist tree:</div>
                <pre style="background:#f8f8f8;padding:1em;border-radius:6px;max-height:260px;overflow:auto;font-size:0.86em;">${escHtml(treeText)}</pre>`;
        }

        // Wire up buttons
        const el = id => document.getElementById(id);

        const addArticleBtn = el("cs-add-article-btn");
        const addModuleBtn  = el("cs-add-module-btn");
        const finishBtn     = el("cs-finish-btn");
        const resetBtn      = el("cs-reset-btn");
        const dlTreeBtn     = el("cs-download-tree-btn");

        if (addArticleBtn) addArticleBtn.onclick = () => showChildTypeSelection(false);
        if (addModuleBtn)  addModuleBtn.onclick  = () => showChildTypeSelection(true);

        if (finishBtn) finishBtn.onclick = function () {
            fetch("/api/creation/finish-module", { method: "POST", headers: { "Content-Type": "application/json" } })
                .then(r => r.json())
                .then(result => renderSessionPanel(result.state || result))
                .catch(err => alert("Error: " + err));
        };

        if (resetBtn) resetBtn.onclick = function () {
            if (!confirm("Reset creation session? All created articles in this session will be cleared.")) return;
            fetch("/api/creation/reset", { method: "POST", headers: { "Content-Type": "application/json" } })
                .then(r => r.json())
                .then(() => {
                    if (rootArticleFormContainer) {
                        rootArticleFormContainer.innerHTML = "";
                        rootArticleFormContainer.style.display = "none";
                    }
                    if (createRootArticleBtn) createRootArticleBtn.disabled = false;
                })
                .catch(err => alert("Error: " + err));
        };

        if (dlTreeBtn) dlTreeBtn.onclick = function () {
            const rootArtnr = (state.stack || []).length > 0 ? state.stack[0].artnr : "";
            if (!rootArtnr) { alert("No root article found."); return; }
            const a = document.createElement('a');
            a.href = `/download-partlist-tree?artnr=${encodeURIComponent(rootArtnr)}&mode=creation`;
            a.download = `partlist_tree_${rootArtnr}.txt`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
        };

            // Download Partlist CSV button
            const dlPartlistBtn = el("cs-download-partlist-btn");
            if (dlPartlistBtn) dlPartlistBtn.onclick = function () {
                const rootArtnr = (state.stack || []).length > 0 ? state.stack[0].artnr : "";
                if (!rootArtnr) { alert("No root article found."); return; }
                const a = document.createElement('a');
                a.href = `/download-partlist?artnr=${encodeURIComponent(rootArtnr)}&mode=creation`;
                a.download = `partlist_${rootArtnr}.csv`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
            };
    }

    // ─── Child type selection ─────────────────────────────────────────────────
    function showChildTypeSelection(isModule) {
        fetchCreationState().then(state => {
            if (!rootArticleFormContainer || !state.stack || state.stack.length === 0) return;
            // Get parent type from the last article in stack
            const parentType = state.articles && state.articles.length > 0
                ? state.articles[state.articles.length - 1].type
                : null;

            // Fetch allowed children for parent type
            if (parentType) {
                fetchAllowedChildren(parentType).then(allowedTypes => {
                    renderChildTypeSelectionUI(isModule, allowedTypes);
                });
            } else {
                // Fallback: show all types
                fetchArticleTypes().then(types => {
                    renderChildTypeSelectionUI(isModule, types);
                });
            }
        });
    }

    function renderChildTypeSelectionUI(isModule, types) {
        if (!rootArticleFormContainer || !types.length) return;
        const label = isModule ? "module" : "article";
        let html = `<div style='font-weight:600;margin-bottom:0.7em;'>Select type for new ${label}:</div>`;
        html += `<div style="margin-bottom:1em;">`;
        types.forEach(t => {
            html += `<button class="modern-btn cs-type-btn" data-type="${escHtml(t)}" style="margin:0.3em 0.7em 0.3em 0;">${escHtml(t)}</button>`;
        });
        html += `</div>`;
        html += `<button id="cs-cancel-type-btn" class="modern-btn secondary">Cancel</button>`;
        html += `<div id="cs-child-form-area" style="margin-top:1em;"></div>`;
        rootArticleFormContainer.innerHTML = html;

        rootArticleFormContainer.querySelectorAll(".cs-type-btn").forEach(btn => {
            btn.onclick = function () {
                const type = btn.getAttribute("data-type");
                showChildArticleForm(type, isModule);
            };
        });
        const cancelBtn = document.getElementById("cs-cancel-type-btn");
        if (cancelBtn) cancelBtn.onclick = () => fetchCreationState().then(renderSessionPanel);
    }

    // ─── Child article / module form ──────────────────────────────────────────
    function showChildArticleForm(type, isModule) {
        fetchArticleFields(type).then(data => {
            const area = document.getElementById("cs-child-form-area");
            if (!area) return;
            if (data.status !== "ok" || !Array.isArray(data.fields) || !data.fields.length) {
                area.innerHTML = '<div style="color:#c00;">No fields found for this type.</div>';
                return;
            }
            const label = isModule ? "Module" : "Article";
            let html = `<div style='font-weight:600;margin-bottom:0.7em;'>Create ${escHtml(type)} (${label}):</div>`;
            html += `<form id="cs-child-form">`;
            html += renderFieldsHtml(data.fields);
            html += `<div style="margin-top:1em;display:flex;gap:0.7em;">`;
            html += `<button type="submit" class="modern-btn">Create ${label}</button>`;
            html += `<button type="button" id="cs-cancel-child-form-btn" class="modern-btn secondary">Cancel</button>`;
            html += `</div></form>`;
            html += `<div id="cs-child-form-msg" style="margin-top:0.5em;"></div>`;
            area.innerHTML = html;
            attachLieferantSearch(area);
            attachExistenceCheck(area, "#cs-child-form");

            const cancelBtn = document.getElementById("cs-cancel-child-form-btn");
            if (cancelBtn) cancelBtn.onclick = () => fetchCreationState().then(renderSessionPanel);

            const form = document.getElementById("cs-child-form");
            if (form) form.addEventListener("submit", function (e) {
                e.preventDefault();
                const payload = { type, is_module: isModule };
                form.querySelectorAll("input,select").forEach(el => { if (el.name) payload[el.name] = el.value; });
                const msgDiv = document.getElementById("cs-child-form-msg");
                if (msgDiv) msgDiv.innerHTML = '<span style="color:#888;">Saving...</span>';
                fetch("/api/creation/add-child", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(payload)
                })
                    .then(r => r.json())
                    .then(result => {
                        if (result.status === "success") {
                            renderSessionPanel(result.state);
                        } else {
                            if (msgDiv) msgDiv.innerHTML = `<span style="color:#c00;">${escHtml(result.message || "Error")}</span>`;
                        }
                    })
                    .catch(err => { if (msgDiv) msgDiv.innerHTML = `<span style="color:#c00;">Error: ${escHtml(String(err))}</span>`; });
            });
        });
    }

    // ─── Root class selection ────────────────────────────────────────────────
    function showRootClassSelection() {
        fetchClasses().then(classes => {
            if (!rootArticleFormContainer) return;
            rootArticleFormContainer.style.display = "block";
            let html = `<div style='font-weight:600;margin-bottom:0.7em;'>Select product class:</div>`;
            html += `<div style="margin-bottom:1em;">`;
            classes.forEach(c => {
                html += `<button class="modern-btn cs-class-btn" data-class="${escHtml(c)}" style="margin:0.3em 0.7em 0.3em 0;min-width:120px;">${escHtml(c)}</button>`;
            });
            html += `</div>`;
            html += `<div id="cs-hierarchy-area" style="margin-top:1em;"></div>`;
            rootArticleFormContainer.innerHTML = html;

            rootArticleFormContainer.querySelectorAll(".cs-class-btn").forEach(btn => {
                btn.onclick = function () { showRootGroupSelection(btn.getAttribute("data-class")); };
            });
        });
    }

    // ─── Root group selection ──────────────────────────────────────────────
    function showRootGroupSelection(className) {
        fetchGroupsForClass(className).then(groups => {
            const area = document.getElementById("cs-hierarchy-area");
            if (!area) return;
            let html = `<div style='margin-top:0.5em;padding:0.8em;background:#f9f9f9;border-radius:6px;'>`;
            html += `<div style='font-weight:600;margin-bottom:0.5em;color:#2980b9;'>Class: ${escHtml(className)}</div>`;
            html += `<div style='font-weight:600;margin-bottom:0.7em;'>Select article group:</div>`;
            groups.forEach(g => {
                html += `<button class="modern-btn cs-group-btn" data-class="${escHtml(className)}" data-group="${escHtml(g)}" style="margin:0.3em 0.7em 0.3em 0;min-width:150px;">${escHtml(g)}</button>`;
            });
            html += `</div>`;
            area.innerHTML = html;

            area.querySelectorAll(".cs-group-btn").forEach(btn => {
                btn.onclick = function () {
                    showRootTypeSelection(btn.getAttribute("data-class"), btn.getAttribute("data-group"));
                };
            });
        });
    }

    // ─── Root type selection ──────────────────────────────────────────────
    function showRootTypeSelection(className, groupName) {
        // Check if this group has sub-types (Teileartikel and Norm Einkaufsteile)
        if (groupName === "Teileartikel" || groupName === "Norm Einkaufsteile") {
            fetchTypesForGroup(groupName).then(data => {
                const area = document.getElementById("cs-hierarchy-area");
                if (!area) return;
                const { types, hasSubtypes } = data;
                let html = `<div style='margin-top:0.5em;padding:0.8em;background:#f0f8ff;border-radius:6px;'>`;
                html += `<div style='font-weight:600;margin-bottom:0.3em;color:#2980b9;'>Class: ${escHtml(className)} › Group: ${escHtml(groupName)}</div>`;
                html += `<div style='font-weight:600;margin-bottom:0.7em;'>Select article sub-type:</div>`;
                types.forEach(t => {
                    html += `<button class="modern-btn cs-type-btn" data-class="${escHtml(className)}" data-group="${escHtml(groupName)}" data-type="${escHtml(t)}" style="margin:0.3em 0.7em 0.3em 0;min-width:150px;">${escHtml(t)}</button>`;
                });
                html += `</div>`;
                html += `<div id="cs-root-form-area"></div>`;
                area.innerHTML = html;

                area.querySelectorAll(".cs-type-btn").forEach(btn => {
                    btn.onclick = function () {
                        showRootArticleForm(
                            btn.getAttribute("data-class"),
                            btn.getAttribute("data-group"),
                            btn.getAttribute("data-type")
                        );
                    };
                });
            });
        } else {
            // For non-subtype groups, use group name as type and go to form directly
            showRootArticleForm(className, groupName, groupName);
        }
    }

    // ─── Root article form ────────────────────────────────────────────────────
    function showRootArticleForm(className, groupName, type) {
        fetchArticleFields(type).then(data => {
            const area = document.getElementById("cs-root-form-area");
            if (!area) return;
            if (data.status !== "ok" || !Array.isArray(data.fields) || !data.fields.length) {
                area.innerHTML = '<div style="color:#c00;">No fields found for this type.</div>';
                return;
            }
            let html = `<div style='margin-top:0.5em;padding:0.8em;background:#f0f8ff;border-radius:6px;'>`;
            html += `<div style='font-weight:600;margin-bottom:0.3em;color:#2980b9;'>Class: ${escHtml(className)} › Group: ${escHtml(groupName)} › Type: ${escHtml(type)}</div>`;
            html += `<div style='font-weight:600;margin-bottom:0.7em;'>Create root ${escHtml(type)}:</div>`;
            html += `<form id="cs-root-form">`;
            html += renderFieldsHtml(data.fields);
            html += `<button type="submit" class="modern-btn" style="margin-top:0.7em;">Create Root</button>`;
            html += `</form>`;
            html += `<div id="cs-root-form-msg" style="margin-top:0.5em;"></div>`;
            html += `</div>`;
            area.innerHTML = html;
            attachLieferantSearch(area);
            attachExistenceCheck(area, "#cs-root-form");

            const form = document.getElementById("cs-root-form");
            if (form) form.addEventListener("submit", function (e) {
                e.preventDefault();
                const payload = { type, class: className, group: groupName };
                form.querySelectorAll("input,select").forEach(el => { if (el.name) payload[el.name] = el.value; });
                const msgDiv = document.getElementById("cs-root-form-msg");
                if (msgDiv) msgDiv.innerHTML = '<span style="color:#888;">Creating...</span>';
                fetch("/api/creation/start", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(payload)
                })
                    .then(r => r.json())
                    .then(result => {
                        if (result.status === "success") {
                            renderSessionPanel(result.state);
                        } else {
                            if (msgDiv) msgDiv.innerHTML = `<span style="color:#c00;">${escHtml(result.message || "Error")}</span>`;
                        }
                    })
                    .catch(err => { if (msgDiv) msgDiv.innerHTML = `<span style="color:#c00;">Error: ${escHtml(String(err))}</span>`; });
            });
        });
    }

    // ─── Entry point ──────────────────────────────────────────────────────────
    if (createRootArticleBtn && rootArticleFormContainer) {
        createRootArticleBtn.addEventListener("click", function () {
            fetchCreationState()
                .then(state => {
                    if (state.is_active) {
                        renderSessionPanel(state);
                    } else {
                        showRootClassSelection();
                    }
                })
                .catch(() => showRootClassSelection());
        });
    }

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
            const url = `/download-partlist-excel?mode=article&artnr=${encodeURIComponent(selectedResult.artnr)}&_ts=${Date.now()}`;
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
                validateArtikelBezeichnungen: "Validate Artikelbezeichnungen",
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
                modalTextBtn: "Define as offerarticle",
                modalNoResults: "No results found.",
                modalNeedReplacement: "Please enter a replacement artnr or click Ignore.",
                showBlockedArticles: "Show Blocked Articles",
                validationModalTitle: "Validate Artikelbezeichnungen",
                validationProgress: "Progress",
                validationConfirm: "Confirm",
                validationClose: "Close",
                validationNoItems: "No cache entries found.",
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
                activeSheets: "Active Sheets",
                bezeichnungenAnpassen: "Bezeichnungen Anpassen"
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
                validateArtikelBezeichnungen: "Artikelbezeichnungen prüfen",
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
                modalTextBtn: "Als Angebotsartikel definieren",
                modalNoResults: "Keine Ergebnisse gefunden.",
                modalNeedReplacement: "Bitte Ersatz-Artikelnr eingeben oder Ignorieren klicken.",
                showBlockedArticles: "Gesperrte Artikel anzeigen",
                validationModalTitle: "Artikelbezeichnungen prüfen",
                validationProgress: "Fortschritt",
                validationConfirm: "Bestätigen",
                validationClose: "Schließen",
                validationNoItems: "Keine Cache-Einträge gefunden.",
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
                activeSheets: "Aktive Sheets",
                bezeichnungenAnpassen: "Bezeichnungen anpassen"
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

            // Download Documents XLSX button(s)
            var downloadDocsXlsxBtns = document.querySelectorAll("#downloadDocsXlsxBtn");
            if (downloadDocsXlsxBtns && downloadDocsXlsxBtns.length) {
                downloadDocsXlsxBtns.forEach(function(btn) {
                    btn.addEventListener("click", function() {
                        // Determine mode based on visible container
                        var mode = (window.searchMode === "module") ? "module" : "article";
                        fetch(`/download-docs-xlsx?mode=${encodeURIComponent(mode)}`)
                            .then(function(response) {
                                if (!response.ok) {
                                    return response.text().then(function(text) {
                                        let message = text || "Failed to create Docs XLSX file.";
                                        throw new Error(message);
                                    });
                                }
                                var disposition = response.headers.get("content-disposition") || "";
                                var fileName = "docs_export.xlsx";
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
                                let entry = `<div><b>Download Documents XLSX:</b> <span style='color:#27ae60;'>Excel created and downloaded.</span></div>`;
                                feedbackLog.innerHTML = entry + feedbackLog.innerHTML;
                            })
                            .catch(function(err) {
                                let entry = `<div><b>Download Documents XLSX:</b> <span style='color:#c00;'>Error: ${err.message || err}</span></div>`;
                                feedbackLog.innerHTML = entry + feedbackLog.innerHTML;
                            });
                    });
                });
            }

            // Download Partlist Excel button
            var downloadPartlistExcelBtn = document.getElementById("downloadPartlistExcelBtn");
            if (downloadPartlistExcelBtn) {
                downloadPartlistExcelBtn.addEventListener("click", function() {
                    fetch(`/download-partlist-excel?mode=module&_ts=${Date.now()}`)
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
        var validateArtikelBezeichnungenBtn = document.getElementById("validateArtikelBezeichnungenBtn");
        var validationModal = document.getElementById("validationModal");
        var validationModalMeta = document.getElementById("validationModalMeta");
        var validationArtnr = document.getElementById("validationArtnr");
        var validationBezeichnung1 = document.getElementById("validationBezeichnung1");
        var validationBezeichnung2 = document.getElementById("validationBezeichnung2");
        var validationLieferantBezeichnung = document.getElementById("validationLieferantBezeichnung");
        var validationLieferantZusatz = document.getElementById("validationLieferantZusatz");
        var validationArtbez1 = document.getElementById("validationArtbez1");
        var validationArtbez2 = document.getElementById("validationArtbez2");
        var validationArtbez3 = document.getElementById("validationArtbez3");
        var validationArtbezMem = document.getElementById("validationArtbezMem");
        var validationStatus = document.getElementById("validationStatus");
        var validationConfirmBtn = document.getElementById("validationConfirmBtn");
        var validationCloseBtn = document.getElementById("validationCloseBtn");
        var validationQueue = [];
        var validationIndex = 0;
        var validationCurrentItem = null;
        var validationSaving = false;
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
                            // Mark this blocked article as Angebotsartikel (Offer Article)
                            replacementMap[item.artnr] = { Angebotsartikel: true };
                            idx += 1;
                            showCurrentBlockedItem();
                        };
                    }
                }

                showCurrentBlockedItem();
            });
        }

        function setValidationStatus(message, isError) {
            if (validationStatus) {
                validationStatus.textContent = message || "";
                validationStatus.style.color = isError ? "#c00" : "#2c3e50";
            }
        }

        function hideValidationModal() {
            if (validationModal) {
                validationModal.style.display = "none";
            }
            validationCurrentItem = null;
            validationQueue = [];
            validationIndex = 0;
            validationSaving = false;
            setValidationStatus("");
        }

        function fillValidationForm(item) {
            if (!item) {
                return;
            }
            validationCurrentItem = item;
            if (validationArtnr) validationArtnr.value = item.artnr || "";
            if (validationBezeichnung1) validationBezeichnung1.value = item.bezeichnung1_de || "";
            if (validationBezeichnung2) validationBezeichnung2.value = item.bezeichnung2_de || "";
            if (validationLieferantBezeichnung) validationLieferantBezeichnung.value = item.lieferant_bezeichnung || "";
            if (validationLieferantZusatz) validationLieferantZusatz.value = item.lieferant_zusatz || "";
            if (validationArtbez1) validationArtbez1.value = item.artbez1 || "";
            if (validationArtbez2) validationArtbez2.value = item.artbez2 || "";
            if (validationArtbez3) validationArtbez3.value = item.artbez3 || "";
            if (validationArtbezMem) validationArtbezMem.value = item.artbezmem || "";
            if (validationModalMeta) {
                validationModalMeta.textContent = `${t("validationProgress") || "Progress"}: ${validationIndex + 1} / ${validationQueue.length}`;
            }
            setValidationStatus("");
            if (validationModal) {
                validationModal.style.display = "flex";
            }
            setTimeout(function() {
                if (validationBezeichnung1 && typeof validationBezeichnung1.focus === "function") {
                    validationBezeichnung1.focus();
                }
            }, 0);
        }

        function getValidationUpdates() {
            return {
                bezeichnung1_de: validationBezeichnung1 ? validationBezeichnung1.value : "",
                bezeichnung2_de: validationBezeichnung2 ? validationBezeichnung2.value : "",
                lieferant_bezeichnung: validationLieferantBezeichnung ? validationLieferantBezeichnung.value : "",
                lieferant_zusatz: validationLieferantZusatz ? validationLieferantZusatz.value : "",
                artbez1: validationArtbez1 ? validationArtbez1.value : "",
                artbez2: validationArtbez2 ? validationArtbez2.value : "",
                artbez3: validationArtbez3 ? validationArtbez3.value : "",
                artbezmem: validationArtbezMem ? validationArtbezMem.value : ""
            };
        }

        function showNextValidationItem() {
            if (validationIndex >= validationQueue.length) {
                hideValidationModal();
                var feedbackLogDone = document.getElementById("feedbackLog");
                if (feedbackLogDone) {
                    feedbackLogDone.innerHTML = `<div><b>Validate Artikelbezeichnungen:</b> <span style='color:#27ae60;'>Completed ${validationQueue.length} entries.</span></div>` + feedbackLogDone.innerHTML;
                }
                return;
            }
            fillValidationForm(validationQueue[validationIndex]);
        }

        function startValidationFlow() {
            if (!validateArtikelBezeichnungenBtn) {
                return;
            }
            validateArtikelBezeichnungenBtn.disabled = true;
            validateArtikelBezeichnungenBtn.textContent = "Loading...";
            fetch("/api/validate-artikelbezeichnungen")
                .then(function(response) {
                    return response.json();
                })
                .then(function(data) {
                    if (!data || data.status !== "ok") {
                        throw new Error((data && data.message) || "Failed to load validation queue.");
                    }
                    validationQueue = Array.isArray(data.items) ? data.items : [];
                    validationIndex = 0;
                    if (!validationQueue.length) {
                        alert(t("validationNoItems") || "No cache entries found.");
                        return;
                    }
                    showNextValidationItem();
                })
                .catch(function(err) {
                    alert(err.message || String(err));
                })
                .finally(function() {
                    validateArtikelBezeichnungenBtn.disabled = false;
                    validateArtikelBezeichnungenBtn.textContent = t("validateArtikelBezeichnungen") || "Validate Artikelbezeichnungen";
                });
        }

        if (validateArtikelBezeichnungenBtn) {
            validateArtikelBezeichnungenBtn.addEventListener("click", startValidationFlow);
        }

        if (validationConfirmBtn) {
            validationConfirmBtn.addEventListener("click", function() {
                if (validationSaving || !validationCurrentItem) {
                    return;
                }
                validationSaving = true;
                setValidationStatus("Saving...");
                fetch("/api/validate-artikelbezeichnungen/save", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        artnr: validationCurrentItem.artnr,
                        updates: getValidationUpdates()
                    })
                })
                .then(function(response) {
                    return response.json();
                })
                .then(function(data) {
                    if (!data || data.status !== "ok") {
                        throw new Error((data && data.message) || "Failed to save validation item.");
                    }
                    var feedbackLog = document.getElementById("feedbackLog");
                    if (feedbackLog) {
                        feedbackLog.innerHTML = `<div><b>Validate Artikelbezeichnungen:</b> <span style='color:#27ae60;'>Saved ${validationCurrentItem.artnr || ""}.</span></div>` + feedbackLog.innerHTML;
                    }
                    validationIndex += 1;
                    showNextValidationItem();
                })
                .catch(function(err) {
                    setValidationStatus(err.message || String(err), true);
                })
                .finally(function() {
                    validationSaving = false;
                });
            });
        }

        if (validationCloseBtn) {
            validationCloseBtn.addEventListener("click", function() {
                hideValidationModal();
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

    function loadBezeichnungenAnpassenToggle() {
        var toggle = document.getElementById("bezeichnungenAnpassenToggle");
        if (!toggle) return;

        fetch("/api/bezeichnungen-anpassen")
            .then(function(response) { return response.json(); })
            .then(function(data) {
                if (!data || data.status !== "success") {
                    return;
                }
                toggle.checked = !!data.enabled;
            })
            .catch(function() {});

        toggle.addEventListener("change", function() {
            fetch("/api/bezeichnungen-anpassen", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ enabled: !!toggle.checked })
            })
            .then(function(response) { return response.json(); })
            .then(function(data) {
                if (!data || data.status !== "success") {
                    throw new Error((data && data.message) || "Failed to save setting");
                }
            })
            .catch(function(err) {
                toggle.checked = !toggle.checked;
                alert(err.message || String(err));
            });
        });
    }

    loadBezeichnungenAnpassenToggle();

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
