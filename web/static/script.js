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

    function fetchArticleFields(type, group) {
        const query = [`type=${encodeURIComponent(type)}`];
        if (group) query.push(`group=${encodeURIComponent(group)}`);
        return fetch(`/api/article-fields?${query.join("&")}`).then(r => r.json());
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
        fields.forEach(field => {
            const defVal = (field.value !== null && field.value !== undefined) ? String(field.value) : '';
            if (field.group === 'dropdown' && Array.isArray(field.options)) {
                const normalizedOptions = field.options.map(opt => {
                    if (opt === null || opt === undefined) {
                        return null;
                    }
                    if (typeof opt === 'string' || typeof opt === 'number' || typeof opt === 'boolean') {
                        const value = String(opt);
                        return value.trim() ? { value: value, label: value, customInput: false } : null;
                    }
                    if (typeof opt === 'object') {
                        const hasCustomInput = opt.custom_input === true || opt.customInput === true || opt.input === true;
                        const rawValue = opt.value !== undefined ? String(opt.value) : (hasCustomInput ? '__custom__' : (opt.label !== undefined ? String(opt.label) : (opt.name !== undefined ? String(opt.name) : '')));
                        const rawLabel = opt.label !== undefined ? String(opt.label) : rawValue;
                        const placeholder = opt.placeholder !== undefined ? String(opt.placeholder) : '';
                        return rawValue.trim() || rawLabel.trim() ? { value: rawValue || rawLabel, label: rawLabel || rawValue, customInput: hasCustomInput, placeholder: placeholder } : null;
                    }
                    return null;
                }).filter(Boolean);
                const customOption = normalizedOptions.find(opt => opt.customInput);
                const customInputId = customOption ? `dropdown-custom-${String(field.name || 'field').replace(/[^a-zA-Z0-9_-]+/g, '_')}` : '';
                const hasMatchingOption = normalizedOptions.some(opt => opt.value === defVal && !opt.customInput);
                const initialSelectValue = hasMatchingOption ? defVal : (defVal && customOption ? customOption.value : (normalizedOptions[0] ? normalizedOptions[0].value : (customOption ? customOption.value : '')));
                const initialCustomValue = customOption && !hasMatchingOption && defVal ? defVal : '';
                html += `<label style='display:block;margin:6px 0;'>${escHtml(field.name)}:`;
                html += `<div style='display:flex;flex-direction:column;gap:0.35em;'>`;
                html += `<select name='${escHtml(field.name)}' data-custom-input-id='${escHtml(customInputId)}' data-custom-option-value='${escHtml(customOption ? customOption.value : '')}' style='width:92%;padding:4px;' ${field.editable === false ? 'disabled' : ''}>`;
                normalizedOptions.forEach(opt => {
                    html += `<option value='${escHtml(opt.value)}'${initialSelectValue === opt.value ? ' selected' : ''}>${escHtml(opt.label)}</option>`;
                });
                html += `</select>`;
                if (customOption) {
                    html += `<input id='${escHtml(customInputId)}' type='text' value='${escHtml(initialCustomValue)}' placeholder='${escHtml(customOption.placeholder || customOption.label || 'Custom value')}' style='width:92%;padding:4px;display:${initialSelectValue === customOption.value ? 'block' : 'none'};' ${field.editable === false ? 'readonly' : ''}>`;
                }
                html += `</div></label>`;
            } else if (field.group === 'search' && field.search_query === 'lieferant') {
                html += `<label style='display:block;margin:6px 0;'>${escHtml(field.name)}: <input type='text' name='${escHtml(field.name)}' value='${escHtml(defVal)}' style='width:80%;padding:4px;display:inline-block;' ${field.editable === false ? 'readonly' : ''}><button type='button' class='lieferant-search-btn' data-field='${escHtml(field.name)}' style='margin-left:0.5em;'>🔍</button></label>`;
            } else if (field.group === 'default' && !field.editable) {
                html += `<label style='display:block;margin:6px 0;'>${escHtml(field.name)}: <input type='text' name='${escHtml(field.name)}' value='${escHtml(defVal)}' style='width:90%;padding:4px;' readonly></label>`;
            } else if (field.group === 'derivative' || field.group === 'derived') {
                html += `<label style='display:block;margin:6px 0;'>${escHtml(field.name)}: <input type='text' name='${escHtml(field.name)}' value='${escHtml(defVal)}' style='width:90%;padding:4px;' ${field.editable === false ? 'readonly' : ''}></label>`;
            } else {
                html += `<label style='display:block;margin:6px 0;'>${escHtml(field.name)}: <input type='text' name='${escHtml(field.name)}' value='${escHtml(defVal)}' style='width:90%;padding:4px;' ${field.editable === false ? 'readonly' : ''}></label>`;
            }
        });
        return html;
    }

    function serializeCreationForm(form) {
        const payload = {};
        form.querySelectorAll('input,select').forEach(el => {
            if (el.name) {
                payload[el.name] = el.value;
            }
        });
        form.querySelectorAll('select[data-custom-input-id]').forEach(select => {
            const customInputId = select.getAttribute('data-custom-input-id');
            const customOptionValue = select.getAttribute('data-custom-option-value') || '';
            if (!customInputId || select.value !== customOptionValue) {
                return;
            }
            const customInput = form.querySelector(`#${customInputId}`);
            if (customInput && select.name) {
                payload[select.name] = customInput.value;
            }
        });
        return payload;
    }

    function syncCustomDropdownInputs(container) {
        if (!container) return;
        container.querySelectorAll('select[data-custom-input-id]').forEach(select => {
            const customInputId = select.getAttribute('data-custom-input-id');
            if (!customInputId) return;
            const customInput = container.querySelector(`#${customInputId}`);
            if (!customInput) return;
            const update = function () {
                const isCustom = select.value === (select.getAttribute('data-custom-option-value') || '');
                customInput.style.display = isCustom ? 'block' : 'none';
            };
            select.addEventListener('change', update);
            update();
        });
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
        fetchCreationState().then(state => {
            const currentGroup = state.current_group || null;
            return fetchArticleFields(type, currentGroup).then(data => ({ data, currentGroup }));
        }).then(({ data, currentGroup }) => {
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
            syncCustomDropdownInputs(area);
            if (form) form.addEventListener("submit", function (e) {
                e.preventDefault();
                const payload = { type, is_module: isModule };
                if (currentGroup) payload.group = currentGroup;
                Object.assign(payload, serializeCreationForm(form));
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
        fetchArticleFields(type, groupName).then(data => {
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
            syncCustomDropdownInputs(area);
            if (form) form.addEventListener("submit", function (e) {
                e.preventDefault();
                const payload = { type, class: className, group: groupName };
                Object.assign(payload, serializeCreationForm(form));
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

    // Create from tree button (one-off): request server to parse drawing tree
    var createFromTreeBtn = document.getElementById("createFromTreeBtn");
    if (createFromTreeBtn) {
        createFromTreeBtn.addEventListener("click", function () {
            var folderInput = document.getElementById("treeFilterInput");
            var folderFilter = folderInput ? folderInput.value.trim() : "";
            
            var confirmMsg = folderFilter 
                ? `Run "Create from tree" to extract drawings from folder "${folderFilter}"?`
                : 'Run "Create from tree" to extract all drawings?';
            
            if (!confirm(confirmMsg)) return;
            
            var feedbackLog = document.getElementById("createTabFeedbackLog");
            var timestamp = new Date().toLocaleTimeString();
            var entry = `<div><b>[${timestamp}] Create From Tree:</b> <span style='color:#666;'>Processing${folderFilter ? " folder '" + escHtml(folderFilter) + "'" : ""}...</span></div>`;
            if (feedbackLog) feedbackLog.innerHTML = entry + feedbackLog.innerHTML;
            
            fetch('/api/create-from-tree', { 
                method: 'POST', 
                headers: { 'Content-Type': 'application/json' }, 
                body: JSON.stringify({ folder: folderFilter || null }) 
            })
                .then(r => r.json())
                .then(result => {
                    const timestamp = new Date().toLocaleTimeString();
                    const entry = `<div><b>[${timestamp}] Create From Tree:</b> <span style='color:${result && result.status === 'success' ? '#27ae60' : '#c00'};'>${result && result.message ? escHtml(result.message) : 'Completed'}</span></div>`;
                    if (feedbackLog) feedbackLog.innerHTML = entry + feedbackLog.innerHTML;
                    else alert(result && result.message ? result.message : 'Done');
                })
                .catch(err => {
                    const timestamp = new Date().toLocaleTimeString();
                    const entry = `<div><b>[${timestamp}] Create From Tree:</b> <span style='color:#c00;'>Error: ${escHtml(String(err))}</span></div>`;
                    const feedbackLog = document.getElementById("createTabFeedbackLog");
                    if (feedbackLog) feedbackLog.innerHTML = entry + feedbackLog.innerHTML;
                    else alert('Create from tree failed.');
                });
        });
    }

    // Update tree from disk button: write fresh tree file from server-side folder
    var updateTreeBtn = document.getElementById("updateTreeBtn");
    if (updateTreeBtn) {
        updateTreeBtn.addEventListener("click", function () {
            var rootInput = document.getElementById("treeRootInput");
            var rootFolder = rootInput ? rootInput.value.trim() : "";
            var confirmMsg = rootFolder
                ? `Write tree from folder ${escHtml(rootFolder)}?`
                : 'Write tree from default folder on server (T:...)?';
            if (!confirm(confirmMsg)) return;

            var feedbackLog = document.getElementById("createTabFeedbackLog") || document.getElementById("feedbackLog");
            var ts = new Date().toLocaleTimeString();
            var entry = `<div><b>[${ts}] Update Tree:</b> <span style='color:#666;'>Starting...</span></div>`;
            if (feedbackLog) feedbackLog.innerHTML = entry + feedbackLog.innerHTML;

            var payload = {};
            if (rootFolder) payload.root_folder = rootFolder;

            fetch('/api/save-tree', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) })
                .then(r => r.json())
                .then(result => {
                    const ts2 = new Date().toLocaleTimeString();
                    const entry = `<div><b>[${ts2}] Update Tree:</b> <span style='color:${result && result.status === 'success' ? '#27ae60' : '#c00'};'>${result && result.message ? escHtml(result.message) : 'Completed'}</span></div>`;
                    if (feedbackLog) feedbackLog.innerHTML = entry + feedbackLog.innerHTML;
                    else alert(result && result.message ? result.message : 'Done');
                })
                .catch(err => {
                    const ts2 = new Date().toLocaleTimeString();
                    const entry = `<div><b>[${ts2}] Update Tree:</b> <span style='color:#c00;'>Error: ${escHtml(String(err))}</span></div>`;
                    if (feedbackLog) feedbackLog.innerHTML = entry + feedbackLog.innerHTML;
                    else alert('Update tree failed.');
                });
        });
    }

    // Add unique artnr button: call server to create article_list_from_tree_unique.csv
    var addUniqueArtnrBtn = document.getElementById("addUniqueArtnrBtn");
    if (addUniqueArtnrBtn) {
        addUniqueArtnrBtn.addEventListener("click", function () {
            var modeSelect = document.getElementById("existingModeSelect");
            var outInput = document.getElementById("uniqueOutInput");
            var mode = modeSelect ? modeSelect.value : 'PROD';
            var outPath = outInput ? outInput.value.trim() : '';
            var confirmMsg = `Create unique artnr list for ${escHtml(mode)}?`;
            if (!confirm(confirmMsg)) return;

            var feedbackLog = document.getElementById("createTabFeedbackLog") || document.getElementById("feedbackLog");
            var ts = new Date().toLocaleTimeString();
            var entry = `<div><b>[${ts}] Add Unique artnr:</b> <span style='color:#666;'>Starting...</span></div>`;
            if (feedbackLog) feedbackLog.innerHTML = entry + feedbackLog.innerHTML;

            var payload = { existing_mode: mode };
            if (outPath) payload.out_csv = outPath;

            fetch('/api/add-unique-artnr', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) })
                .then(r => r.json())
                .then(result => {
                    const ts2 = new Date().toLocaleTimeString();
                    const entry = `<div><b>[${ts2}] Add Unique artnr:</b> <span style='color:${result && result.status === 'success' ? '#27ae60' : '#c00'};'>${result && result.message ? escHtml(result.message) : 'Completed'}</span></div>`;
                    if (feedbackLog) feedbackLog.innerHTML = entry + feedbackLog.innerHTML;
                    else alert(result && result.message ? result.message : 'Done');
                })
                .catch(err => {
                    const ts2 = new Date().toLocaleTimeString();
                    const entry = `<div><b>[${ts2}] Add Unique artnr:</b> <span style='color:#c00;'>Error: ${escHtml(String(err))}</span></div>`;
                    if (feedbackLog) feedbackLog.innerHTML = entry + feedbackLog.innerHTML;
                    else alert('Add unique artnr failed.');
                });
        });
    }

    // Build sheet cache button
    var buildSheetCacheBtn = document.getElementById("buildSheetCacheBtn");
    if (buildSheetCacheBtn) {
        buildSheetCacheBtn.addEventListener("click", function () {
            var confirmMsg = "Build sheet cache for created articles?";
            if (!confirm(confirmMsg)) return;

            buildSheetCacheBtn.disabled = true;
            buildSheetCacheBtn.textContent = "Building...";

            var feedbackLog = document.getElementById("createTabFeedbackLog") || document.getElementById("feedbackLog");
            var ts = new Date().toLocaleTimeString();
            var entry = `<div><b>[${ts}] Build Sheet Cache:</b> <span style='color:#666;'>Starting...</span></div>`;
            if (feedbackLog) feedbackLog.innerHTML = entry + feedbackLog.innerHTML;

            fetch('/api/build-sheet-cache-creation', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({}) })
                .then(r => r.json())
                .then(result => {
                    const ts2 = new Date().toLocaleTimeString();
                    let sheetInfo = "";
                    if (result && result.sheets && Array.isArray(result.sheets)) {
                        sheetInfo = result.sheets.map(s => `${s.sheet}: ${s.rows} rows`).join(", ");
                    }
                    const msg = result && result.message ? result.message + (sheetInfo ? " [" + sheetInfo + "]" : "") : "Completed";
                    const entry = `<div><b>[${ts2}] Build Sheet Cache:</b> <span style='color:${result && result.status === 'success' ? '#27ae60' : '#c00'};'>${escHtml(msg)}</span></div>`;
                    if (feedbackLog) feedbackLog.innerHTML = entry + feedbackLog.innerHTML;
                    else alert(result && result.message ? result.message : "Done");
                })
                .catch(err => {
                    const ts2 = new Date().toLocaleTimeString();
                    const entry = `<div><b>[${ts2}] Build Sheet Cache:</b> <span style='color:#c00;'>Error: ${escHtml(String(err))}</span></div>`;
                    if (feedbackLog) feedbackLog.innerHTML = entry + feedbackLog.innerHTML;
                    else alert("Build sheet cache failed.");
                })
                .finally(() => {
                    buildSheetCacheBtn.disabled = false;
                    buildSheetCacheBtn.textContent = "Build Sheet Cache";
                });
        });
    }

    // Download article data button
    var downloadArticleDataBtn = document.getElementById("downloadArticleDataBtn");
    if (downloadArticleDataBtn) {
        downloadArticleDataBtn.addEventListener("click", function () {
            if (!confirm("Download created article data as xlsx?")) return;

            var folderInput = document.getElementById("treeFilterInput");
            var folderFilter = folderInput ? folderInput.value.trim() : "";
            var url = '/download-article-data-xlsx';
            if (folderFilter) {
                url += `?folder_name=${encodeURIComponent(folderFilter)}`;
            }

            downloadArticleDataBtn.disabled = true;
            downloadArticleDataBtn.textContent = "Downloading...";

            var feedbackLog = document.getElementById("createTabFeedbackLog") || document.getElementById("feedbackLog");
            var ts = new Date().toLocaleTimeString();
            var entry = `<div><b>[${ts}] Download Article Data:</b> <span style='color:#666;'>Starting...</span></div>`;
            if (feedbackLog) feedbackLog.innerHTML = entry + feedbackLog.innerHTML;

            fetch(url)
                .then(r => {
                    if (!r.ok) throw new Error(`HTTP ${r.status}`);
                    return r.blob().then(blob => ({ blob, disposition: r.headers.get('content-disposition') }));
                })
                .then(({ blob, disposition }) => {
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = disposition ? disposition.replace(/attachment; filename="?([^"]*)"?/i, '$1') : 'article_data.xlsx';
                    document.body.appendChild(a);
                    a.click();
                    document.body.removeChild(a);
                    URL.revokeObjectURL(url);
                    
                    const ts2 = new Date().toLocaleTimeString();
                    const entry = `<div><b>[${ts2}] Download Article Data:</b> <span style='color:#27ae60;'>Complete.</span></div>`;
                    if (feedbackLog) feedbackLog.innerHTML = entry + feedbackLog.innerHTML;
                })
                .catch(err => {
                    const ts2 = new Date().toLocaleTimeString();
                    const entry = `<div><b>[${ts2}] Download Article Data:</b> <span style='color:#c00;'>Error: ${escHtml(String(err))}</span></div>`;
                    if (feedbackLog) feedbackLog.innerHTML = entry + feedbackLog.innerHTML;
                    else alert("Download failed: " + err.message);
                })
                .finally(() => {
                    downloadArticleDataBtn.disabled = false;
                    downloadArticleDataBtn.textContent = "Download Article Data (xlsx)";
                });
        });
    }

    // Download document data button
    var downloadDocumentDataBtn = document.getElementById("downloadDocumentDataBtn");
    if (downloadDocumentDataBtn) {
        downloadDocumentDataBtn.addEventListener("click", function () {
            if (!confirm("Download document data as xlsx?")) return;

            var folderInput = document.getElementById("treeFilterInput");
            var folderFilter = folderInput ? folderInput.value.trim() : "";
            var url = '/download-document-data-xlsx';
            if (folderFilter) {
                url += `?folder_name=${encodeURIComponent(folderFilter)}`;
            }

            downloadDocumentDataBtn.disabled = true;
            downloadDocumentDataBtn.textContent = "Downloading...";

            var feedbackLog = document.getElementById("createTabFeedbackLog") || document.getElementById("feedbackLog");
            var ts = new Date().toLocaleTimeString();
            var entry = `<div><b>[${ts}] Download Document Data:</b> <span style='color:#666;'>Starting...</span></div>`;
            if (feedbackLog) feedbackLog.innerHTML = entry + feedbackLog.innerHTML;

            fetch(url)
                .then(r => {
                    if (!r.ok) throw new Error(`HTTP ${r.status}`);
                    return r.blob().then(blob => ({ blob, disposition: r.headers.get('content-disposition') }));
                })
                .then(({ blob, disposition }) => {
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = disposition ? disposition.replace(/attachment; filename="?([^"]*)"?/i, '$1') : 'document_data.xlsx';
                    document.body.appendChild(a);
                    a.click();
                    document.body.removeChild(a);
                    URL.revokeObjectURL(url);
                    
                    const ts2 = new Date().toLocaleTimeString();
                    const entry = `<div><b>[${ts2}] Download Document Data:</b> <span style='color:#27ae60;'>Complete.</span></div>`;
                    if (feedbackLog) feedbackLog.innerHTML = entry + feedbackLog.innerHTML;
                })
                .catch(err => {
                    const ts2 = new Date().toLocaleTimeString();
                    const entry = `<div><b>[${ts2}] Download Document Data:</b> <span style='color:#c00;'>Error: ${escHtml(String(err))}</span></div>`;
                    if (feedbackLog) feedbackLog.innerHTML = entry + feedbackLog.innerHTML;
                    else alert("Download failed: " + err.message);
                })
                .finally(() => {
                    downloadDocumentDataBtn.disabled = false;
                    downloadDocumentDataBtn.textContent = "Download Document Data (xlsx)";
                });
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
            var existingArticlesTarget = getExistingArticlesTarget();
            fetch("/add-article", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    artnr: selectedResult.artnr,
                    existing_articles_target: existingArticlesTarget
                })
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
            var existingArticlesTarget = getExistingArticlesTarget();
            fetch("/generate-module-data", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    artnr: selectedResult.artnr,
                    selected_headers: selectedHeaders,
                    mode: "article",
                    existing_articles_target: existingArticlesTarget
                })
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
                overwriteBezeichnungen: "Overwrite Bezeichnungen Cache",
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
                validateArticleGroups: "Validate Groups",
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
                overwriteBezeichnungen: "Bezeichnungen im Cache ueberschreiben",
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
                validateArticleGroups: "Gruppen prüfen",
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
        var overwriteBezeichnungenBtn = document.getElementById("overwriteBezeichnungenBtn");
        var validateArticleGroupsBtn = document.getElementById("validateArticleGroupsBtn");
        var createValidateGroupsBtn = document.getElementById("createValidateGroupsBtn");
        var buildSheetCacheBtn = document.getElementById("buildSheetCacheBtn");
        var downloadCreationExcelUIBtn = document.getElementById("downloadCreationExcelUIBtn");
        var downloadCreationExcelBtn = document.getElementById("downloadCreationExcelBtn");
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
        var validationHauptgruppe = document.getElementById("validationHauptgruppe");
        var validationHauptgruppeCustom = document.getElementById("validationHauptgruppeCustom");
        var validationUntergruppe = document.getElementById("validationUntergruppe");
        var validationUntergruppeCustom = document.getElementById("validationUntergruppeCustom");
        var validationSpezifikation = document.getElementById("validationSpezifikation");
        var validationSpezifikationCustom = document.getElementById("validationSpezifikationCustom");
        var validationStatus = document.getElementById("validationStatus");
        var validationConfirmBtn = document.getElementById("validationConfirmBtn");
        var validationCloseBtn = document.getElementById("validationCloseBtn");
        var validationQueue = [];
        var validationIndex = 0;
        var validationCurrentItem = null;
        var validationSaving = false;
        var validationGroupsTree = {};

        var groupValidationModal = document.getElementById("groupValidationModal");
        var groupValidationModalMeta = document.getElementById("groupValidationModalMeta");
        var groupValidationArtbez1 = document.getElementById("groupValidationArtbez1");
        var groupValidationArtbez2 = document.getElementById("groupValidationArtbez2");
        var groupValidationArtbez3 = document.getElementById("groupValidationArtbez3");
        var groupValidationArtbezMem = document.getElementById("groupValidationArtbezMem");
        var groupValidationHauptgruppe = document.getElementById("groupValidationHauptgruppe");
        var groupValidationHauptgruppeCustom = document.getElementById("groupValidationHauptgruppeCustom");
        var groupValidationUntergruppe = document.getElementById("groupValidationUntergruppe");
        var groupValidationUntergruppeCustom = document.getElementById("groupValidationUntergruppeCustom");
        var groupValidationSpezifikation = document.getElementById("groupValidationSpezifikation");
        var groupValidationSpezifikationCustom = document.getElementById("groupValidationSpezifikationCustom");
        var groupValidationStatus = document.getElementById("groupValidationStatus");
        var groupValidationBezeichnungsContainer = document.getElementById("groupValidationBezeichnungsContainer");
        var groupValidationBezeichnung1 = document.getElementById("groupValidationBezeichnung1");
        var groupValidationBezeichnung2 = document.getElementById("groupValidationBezeichnung2");
        var groupValidationConfirmBtn = document.getElementById("groupValidationConfirmBtn");
        var groupValidationCloseBtn = document.getElementById("groupValidationCloseBtn");
        var groupValidationNewHauptgruppe = document.getElementById("groupValidationNewHauptgruppe");
        var groupValidationNewUntergruppe = document.getElementById("groupValidationNewUntergruppe");
        var groupValidationNewSpezifikation = document.getElementById("groupValidationNewSpezifikation");
        var groupValidationAddBtn = document.getElementById("groupValidationAddBtn");
        var groupValidationNewBezeichnungName = document.getElementById("groupValidationNewBezeichnungName");
        var groupValidationNewBezeichnungValue = document.getElementById("groupValidationNewBezeichnungValue");
        var groupValidationAddBezeichnungBtn = document.getElementById("groupValidationAddBezeichnungBtn");
        var groupValidationQueue = [];
        var groupValidationIndex = 0;
        var groupValidationCurrentItem = null;
        var groupValidationSaving = false;
        var groupValidationGroupsTree = {};
        var groupValidationUseFileQueue = false;
        var groupValidationCustomBezeichnungselemente = [];
        var groupValidationAutoRefreshHandler = null;

        function hasSelectOption(selectEl, value) {
            if (!selectEl || !value) return false;
            return Array.from(selectEl.options || []).some(function(opt) { return (opt && opt.value) === value; });
        }

        function getInputOrSelectValue(inputEl, selectEl) {
            var inputValue = inputEl ? String(inputEl.value || '').trim() : '';
            if (inputValue) return inputValue;
            return selectEl ? String(selectEl.value || '') : '';
        }

        function setCustomInputFromValue(inputEl, selectEl, value) {
            if (!inputEl || !selectEl) return;
            var normalized = String(value || '').trim();
            if (!normalized || hasSelectOption(selectEl, normalized)) {
                inputEl.value = '';
                return;
            }
            inputEl.value = normalized;
        }

        function ensureSelectHasValue(selectEl, value) {
            if (!selectEl) return;
            var normalized = String(value || '').trim();
            if (!normalized || hasSelectOption(selectEl, normalized)) return;
            var opt = document.createElement('option');
            opt.value = normalized;
            opt.textContent = normalized;
            selectEl.appendChild(opt);
        }
        function _refreshUntergruppenForSelectedHg() {
            if (!validationHauptgruppe || !validationUntergruppe) return;
            const hg = getInputOrSelectValue(validationHauptgruppeCustom, validationHauptgruppe);
            validationUntergruppe.innerHTML = '';
            let ugList = [];
            if (validationGroupsTree && validationGroupsTree[hg] && typeof validationGroupsTree[hg] === 'object') {
                ugList = Object.keys(validationGroupsTree[hg]);
            }
            ugList.forEach(function(o){ var opt = document.createElement('option'); opt.value = o; opt.textContent = o; validationUntergruppe.appendChild(opt); });
            if (validationCurrentItem && validationCurrentItem.untergruppe) {
                try { validationUntergruppe.value = validationCurrentItem.untergruppe; } catch(e){}
            }
            // if no value selected, pick first
            if (!validationUntergruppe.value && ugList.length) validationUntergruppe.value = ugList[0];
            if (validationUntergruppeCustom && validationUntergruppeCustom.value && hasSelectOption(validationUntergruppe, validationUntergruppeCustom.value)) {
                validationUntergruppeCustom.value = '';
            }
            _refreshSpezifikationForSelected();
        }

        function _refreshSpezifikationForSelected() {
            if (!validationHauptgruppe || !validationUntergruppe || !validationSpezifikation) return;
            const hg = getInputOrSelectValue(validationHauptgruppeCustom, validationHauptgruppe);
            const ug = getInputOrSelectValue(validationUntergruppeCustom, validationUntergruppe);
            validationSpezifikation.innerHTML = '';
            let specs = [];
            if (validationGroupsTree && validationGroupsTree[hg] && validationGroupsTree[hg][ug]) {
                const node = validationGroupsTree[hg][ug];
                if (Array.isArray(node)) specs = node;
                else if (typeof node === 'object') specs = Object.keys(node);
            }
            specs.forEach(function(o){ var opt = document.createElement('option'); opt.value = o; opt.textContent = o; validationSpezifikation.appendChild(opt); });
            if (validationCurrentItem && validationCurrentItem.spezifikation) {
                try { validationSpezifikation.value = validationCurrentItem.spezifikation; } catch(e){}
            }
            if (validationSpezifikationCustom && validationSpezifikationCustom.value && hasSelectOption(validationSpezifikation, validationSpezifikationCustom.value)) {
                validationSpezifikationCustom.value = '';
            }
        }

        if (validationHauptgruppe) {
            validationHauptgruppe.addEventListener('change', function() {
                _refreshUntergruppenForSelectedHg();
            });
        }
        if (validationUntergruppe) {
            validationUntergruppe.addEventListener('change', function() {
                _refreshSpezifikationForSelected();
            });
        }
        if (validationHauptgruppeCustom) {
            validationHauptgruppeCustom.addEventListener('input', function() {
                _refreshUntergruppenForSelectedHg();
            });
        }
        if (validationUntergruppeCustom) {
            validationUntergruppeCustom.addEventListener('input', function() {
                _refreshSpezifikationForSelected();
            });
        }
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
            // populate group selects
            if (validationHauptgruppe) {
                validationHauptgruppe.innerHTML = '';
                var hg_opts = item.hauptgruppen_options && item.hauptgruppen_options.length ? item.hauptgruppen_options : Object.keys(validationGroupsTree || {});
                hg_opts.forEach(function(o){ var opt = document.createElement('option'); opt.value = o; opt.textContent = o; validationHauptgruppe.appendChild(opt); });
                if (item.hauptgruppe) validationHauptgruppe.value = item.hauptgruppe;
            }
            if (validationHauptgruppeCustom) {
                setCustomInputFromValue(validationHauptgruppeCustom, validationHauptgruppe, item.hauptgruppe || '');
            }
            if (validationUntergruppe) {
                validationUntergruppe.innerHTML = '';
                var ug_opts = item.untergruppen_options || [];
                ug_opts.forEach(function(o){ var opt = document.createElement('option'); opt.value = o; opt.textContent = o; validationUntergruppe.appendChild(opt); });
                if (item.untergruppe) validationUntergruppe.value = item.untergruppe;
            }
            if (validationUntergruppeCustom) {
                setCustomInputFromValue(validationUntergruppeCustom, validationUntergruppe, item.untergruppe || '');
            }
            if (validationSpezifikation) {
                validationSpezifikation.innerHTML = '';
                var sp_opts = item.spezifikation_options || [];
                sp_opts.forEach(function(o){ var opt = document.createElement('option'); opt.value = o; opt.textContent = o; validationSpezifikation.appendChild(opt); });
                if (item.spezifikation) validationSpezifikation.value = item.spezifikation;
            }
            if (validationSpezifikationCustom) {
                setCustomInputFromValue(validationSpezifikationCustom, validationSpezifikation, item.spezifikation || '');
            }
            // If we have a groups tree from backend, prefer it to populate dependent selects
            if (validationGroupsTree && validationHauptgruppe && validationGroupsTree[validationHauptgruppe.value]) {
                _refreshUntergruppenForSelectedHg();
            }
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
                artbezmem: validationArtbezMem ? validationArtbezMem.value : "",
                hauptgruppe: getInputOrSelectValue(validationHauptgruppeCustom, validationHauptgruppe),
                untergruppe: getInputOrSelectValue(validationUntergruppeCustom, validationUntergruppe),
                spezifikation: getInputOrSelectValue(validationSpezifikationCustom, validationSpezifikation)
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
                    validationGroupsTree = data.groups_tree || {};
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

        function overwriteBezeichnungenCache() {
            if (!overwriteBezeichnungenBtn) {
                return;
            }
            overwriteBezeichnungenBtn.disabled = true;
            overwriteBezeichnungenBtn.textContent = "Overwriting...";
            fetch("/api/validate-artikelbezeichnungen/overwrite", {
                method: "POST",
                headers: { "Content-Type": "application/json" }
            })
                .then(function(response) { return response.json(); })
                .then(function(data) {
                    if (!data || data.status !== "ok") {
                        throw new Error((data && data.message) || "Failed to overwrite Bezeichnungen cache.");
                    }
                    var feedbackLog = document.getElementById("feedbackLog");
                    if (feedbackLog) {
                        feedbackLog.innerHTML = "<div><b>Overwrite Bezeichnungen:</b> <span style='color:#27ae60;'>Updated Artikelstamm rows: " +
                            (data.artikelstamm_rows_updated || 0) + ", Lieferant rows: " +
                            (data.lieferant_rows_updated || 0) + ".</span></div>" + feedbackLog.innerHTML;
                    }
                })
                .catch(function(err) {
                    alert(err.message || String(err));
                })
                .finally(function() {
                    overwriteBezeichnungenBtn.disabled = false;
                    overwriteBezeichnungenBtn.textContent = t("overwriteBezeichnungen") || "Overwrite Bezeichnungen Cache";
                });
        }

        if (overwriteBezeichnungenBtn) {
            overwriteBezeichnungenBtn.addEventListener("click", overwriteBezeichnungenCache);
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
                    body: JSON.stringify({ artnr: validationCurrentItem.artnr, updates: getValidationUpdates() })
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

        function setGroupValidationStatus(message, isError) {
            if (groupValidationStatus) {
                groupValidationStatus.textContent = message || "";
                groupValidationStatus.style.color = isError ? "#c00" : "#2c3e50";
            }
        }

        function hideGroupValidationModal() {
            if (groupValidationModal) {
                groupValidationModal.style.display = "none";
            }
            groupValidationCurrentItem = null;
            groupValidationQueue = [];
            groupValidationIndex = 0;
            groupValidationSaving = false;
            setGroupValidationStatus("");
        }

        function populateGroupValidationUntergruppen() {
            if (!groupValidationHauptgruppe || !groupValidationUntergruppe) return;
            var hg = getInputOrSelectValue(groupValidationHauptgruppeCustom, groupValidationHauptgruppe);
            var options = [];
            if (groupValidationGroupsTree && groupValidationGroupsTree[hg] && typeof groupValidationGroupsTree[hg] === "object") {
                options = Object.keys(groupValidationGroupsTree[hg]);
            }
            if (groupValidationCurrentItem && groupValidationCurrentItem.preset_untergruppe && options.indexOf(groupValidationCurrentItem.preset_untergruppe) === -1) {
                options = [groupValidationCurrentItem.preset_untergruppe].concat(options);
            }
            groupValidationUntergruppe.innerHTML = "";
            options.forEach(function(value) {
                var opt = document.createElement("option");
                opt.value = value;
                opt.textContent = value;
                groupValidationUntergruppe.appendChild(opt);
            });
            if (groupValidationCurrentItem && groupValidationCurrentItem.preset_untergruppe) {
                groupValidationUntergruppe.value = groupValidationCurrentItem.preset_untergruppe;
            }
            if (!groupValidationUntergruppe.value && options.length) {
                groupValidationUntergruppe.value = options[0];
            }
            if (groupValidationUntergruppeCustom && groupValidationUntergruppeCustom.value && hasSelectOption(groupValidationUntergruppe, groupValidationUntergruppeCustom.value)) {
                groupValidationUntergruppeCustom.value = '';
            }
            populateGroupValidationSpezifikationen();
        }

        function populateGroupValidationSpezifikationen() {
            if (!groupValidationHauptgruppe || !groupValidationUntergruppe || !groupValidationSpezifikation) return;
            var hg = getInputOrSelectValue(groupValidationHauptgruppeCustom, groupValidationHauptgruppe);
            var ug = getInputOrSelectValue(groupValidationUntergruppeCustom, groupValidationUntergruppe);
            var node = groupValidationGroupsTree && groupValidationGroupsTree[hg] ? groupValidationGroupsTree[hg][ug] : null;
            var options = [];
            if (Array.isArray(node)) {
                options = node;
            } else if (node && typeof node === "object") {
                options = Object.keys(node);
            }
            if (groupValidationCurrentItem && groupValidationCurrentItem.preset_spezifikation && options.indexOf(groupValidationCurrentItem.preset_spezifikation) === -1) {
                options = [groupValidationCurrentItem.preset_spezifikation].concat(options);
            }
            groupValidationSpezifikation.innerHTML = "";
            options.forEach(function(value) {
                var opt = document.createElement("option");
                opt.value = value;
                opt.textContent = value;
                groupValidationSpezifikation.appendChild(opt);
            });
            if (groupValidationCurrentItem && groupValidationCurrentItem.preset_spezifikation) {
                groupValidationSpezifikation.value = groupValidationCurrentItem.preset_spezifikation;
            }
            if (groupValidationSpezifikationCustom && groupValidationSpezifikationCustom.value && hasSelectOption(groupValidationSpezifikation, groupValidationSpezifikationCustom.value)) {
                groupValidationSpezifikationCustom.value = '';
            }
        }

        function renderCustomBezeichnungRow(elem, index) {
            var row = document.createElement('div');
            row.style.display = 'flex';
            row.style.gap = '0.6em';
            row.style.marginBottom = '0.4em';
            row.style.alignItems = 'flex-start';
            row.dataset.customIndex = index;
            row.dataset.customElement = 'true';
            
            var lbl = document.createElement('label');
            lbl.style.minWidth = '160px';
            lbl.style.fontWeight = '600';
            lbl.style.marginTop = '0.35em';
            lbl.textContent = elem.name || ('Custom ' + (index+1));
            
            var valInput = document.createElement('input');
            valInput.type = 'text';
            valInput.style.flex = '1';
            valInput.value = elem.value || '';
            valInput.dataset.customValue = 'true';
            valInput.dataset.customName = elem.name || '';
            
            var delBtn = document.createElement('button');
            delBtn.type = 'button';
            delBtn.className = 'modern-btn secondary';
            delBtn.style.padding = '0.4em 0.8em';
            delBtn.style.minWidth = 'auto';
            delBtn.textContent = '✕';
            delBtn.title = 'Remove this element';
            delBtn.addEventListener('click', function(e){
                e.preventDefault();
                row.remove();
                groupValidationCustomBezeichnungselemente = groupValidationCustomBezeichnungselemente.filter(function(_, i){ return i !== index; });
            });
            
            row.appendChild(lbl);
            row.appendChild(valInput);
            row.appendChild(delBtn);
            return row;
        }

        function refreshGroupValidationBezeichnungselemente() {
            if (!groupValidationCurrentItem) return;
            var hg = getInputOrSelectValue(groupValidationHauptgruppeCustom, groupValidationHauptgruppe);
            var ug = getInputOrSelectValue(groupValidationUntergruppeCustom, groupValidationUntergruppe);
            var spec = getInputOrSelectValue(groupValidationSpezifikationCustom, groupValidationSpezifikation);
            
            fetch('/api/validate/groups/resolve-bezeichnungselemente', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    artnr: groupValidationCurrentItem.artnr,
                    hauptgruppe: hg,
                    untergruppe: ug,
                    spezifikation: spec,
                })
            })
            .then(function(r){ return r.json(); })
            .then(function(data){
                if (data && data.status === 'ok') {
                    var elements = data.bezeichnungselemente || [];
                    if (groupValidationBezeichnungsContainer) {
                        Array.from(groupValidationBezeichnungsContainer.querySelectorAll('[data-predefined="true"]')).forEach(function(row){
                            row.remove();
                        });
                        var firstCustomRow = groupValidationBezeichnungsContainer.querySelector('[data-custom-element="true"]');
                        
                        elements.forEach(function(e, idx){
                            try {
                                var row = document.createElement('div');
                                row.style.display = 'flex';
                                row.style.gap = '0.6em';
                                row.style.marginBottom = '0.4em';
                                row.dataset.predefined = 'true';
                                var lbl = document.createElement('label');
                                lbl.style.minWidth = '160px';
                                lbl.style.fontWeight = '600';
                                lbl.textContent = e.name || ('Elem ' + (idx+1));
                                var rawOptions = Array.isArray(e.options) ? e.options : [];
                                var normalizedOptions = rawOptions.map(function(opt){
                                    if (opt && typeof opt === 'object') {
                                        return opt;
                                    }
                                    var s = String(opt || '').trim();
                                    return s ? s : null;
                                }).filter(function(x){ return x !== null; });
                                
                                var control;
                                if (normalizedOptions.length) {
                                    if ((e.name || '').toString().trim().toLowerCase() === 'checked') {
                                        var cbContainer = document.createElement('div');
                                        cbContainer.style.display = 'flex';
                                        cbContainer.style.flexDirection = 'column';
                                        cbContainer.style.flex = '1';
                                        cbContainer.dataset.key = e.name || '';
                                        normalizedOptions.forEach(function(opt){
                                            var optionLabel = (typeof opt === 'object') ? (opt.label !== undefined ? String(opt.label) : String(opt.value)) : String(opt);
                                            var optionVal = (typeof opt === 'object') ? (opt.value !== undefined ? String(opt.value) : optionLabel) : optionLabel;
                                            var cbRow = document.createElement('label');
                                            cbRow.style.display = 'flex';
                                            cbRow.style.alignItems = 'center';
                                            cbRow.style.gap = '0.6em';
                                            var cb = document.createElement('input');
                                            cb.type = 'checkbox';
                                            cb.dataset.key = e.name || '';
                                            cb.dataset.option = optionVal;
                                            cb.value = optionVal;
                                            var span = document.createElement('span');
                                            span.textContent = optionLabel;
                                            cbRow.appendChild(cb);
                                            cbRow.appendChild(span);
                                            cbContainer.appendChild(cbRow);
                                        });
                                        row.appendChild(lbl);
                                        row.appendChild(cbContainer);
                                        groupValidationBezeichnungsContainer.insertBefore(row, firstCustomRow || null);
                                        return;
                                    }
                                    var select = document.createElement('select');
                                    select.style.flex = '1';
                                    select.name = e.name || '';
                                    normalizedOptions.forEach(function(opt){
                                        var optionEl = document.createElement('option');
                                        if (typeof opt === 'object') {
                                            var val = opt.value !== undefined ? String(opt.value) : (opt.label !== undefined ? String(opt.label) : '');
                                            var lbl = opt.label !== undefined ? String(opt.label) : val;
                                            optionEl.value = val;
                                            optionEl.textContent = lbl;
                                        } else {
                                            optionEl.value = String(opt);
                                            optionEl.textContent = String(opt);
                                        }
                                        select.appendChild(optionEl);
                                    });
                                    try {
                                        if (e.value) select.value = e.value;
                                    } catch (ex) {}
                                    row.appendChild(lbl);
                                    row.appendChild(select);
                                } else {
                                    control = document.createElement('input');
                                    control.type = 'text';
                                    control.style.flex = '1';
                                    control.value = e.value || '';
                                    control.placeholder = '';
                                    control.title = '';
                                    row.appendChild(lbl);
                                    row.appendChild(control);
                                }
                                if (control) {
                                    control.dataset.key = e.name || '';
                                    control.dataset.options = JSON.stringify(normalizedOptions);
                                } else if (row) {
                                    var sel = row.querySelector('select');
                                    if (sel) sel.dataset.key = e.name || '';
                                }
                                groupValidationBezeichnungsContainer.insertBefore(row, firstCustomRow || null);
                            } catch (ex) {}
                        });
                            // Show manual add section only if no predefined elements found
                            var addElementSection = document.querySelector('[data-group-validation-add-element-section]');
                            if (addElementSection) {
                                addElementSection.style.display = (elements.length === 0) ? 'block' : 'none';
                            }
                            // After rendering elements, update rendered Bezeichnung texts
                            requestRenderBezeichnungen();
                            attachBezeichnungElementListeners();
                    }
                }
            })
            .catch(function(err){ if (DEBUG) console.log('Error refreshing elements:', err); });
        }

        function fillGroupValidationForm(item) {
            if (!item) return;
            var preserveCustomBezeichnungen = groupValidationCurrentItem && groupValidationCurrentItem.artnr === item.artnr;
            groupValidationCurrentItem = item;
            if (!preserveCustomBezeichnungen) {
                groupValidationCustomBezeichnungselemente = [];
            }
            if (groupValidationArtbez1) groupValidationArtbez1.value = item.artbez1 || "";
            if (groupValidationArtbez2) groupValidationArtbez2.value = item.artbez2 || "";
            if (groupValidationArtbez3) groupValidationArtbez3.value = item.artbez3 || "";
            if (groupValidationArtbezMem) groupValidationArtbezMem.value = item.artbezmem || "";

            if (groupValidationHauptgruppe) {
                groupValidationHauptgruppe.innerHTML = "";
                var hgOptions = item.hauptgruppen_options && item.hauptgruppen_options.length ? item.hauptgruppen_options : Object.keys(groupValidationGroupsTree || {});
                hgOptions.forEach(function(value) {
                    var opt = document.createElement("option");
                    opt.value = value;
                    opt.textContent = value;
                    groupValidationHauptgruppe.appendChild(opt);
                });
                if (item.preset_hauptgruppe) {
                    if (hgOptions.indexOf(item.preset_hauptgruppe) === -1) {
                        var presetOpt = document.createElement("option");
                        presetOpt.value = item.preset_hauptgruppe;
                        presetOpt.textContent = item.preset_hauptgruppe;
                        groupValidationHauptgruppe.appendChild(presetOpt);
                    }
                    groupValidationHauptgruppe.value = item.preset_hauptgruppe;
                }
            }
            if (groupValidationHauptgruppeCustom) {
                setCustomInputFromValue(groupValidationHauptgruppeCustom, groupValidationHauptgruppe, item.preset_hauptgruppe || item.hauptgruppe || '');
            }

            populateGroupValidationUntergruppen();
            if (groupValidationUntergruppeCustom) {
                setCustomInputFromValue(groupValidationUntergruppeCustom, groupValidationUntergruppe, item.preset_untergruppe || item.untergruppe || '');
            }
            if (groupValidationSpezifikationCustom) {
                setCustomInputFromValue(groupValidationSpezifikationCustom, groupValidationSpezifikation, item.preset_spezifikation || item.spezifikation || '');
            }
            // populate bezeichnungselemente (list of {name, value})
            if (groupValidationBezeichnungsContainer) {
                groupValidationBezeichnungsContainer.innerHTML = '';
                var elems = item.bezeichnungselemente || [];
                elems.forEach(function(e, idx) {
                    try {
                        var row = document.createElement('div');
                        row.style.display = 'flex';
                        row.style.gap = '0.6em';
                        row.style.marginBottom = '0.4em';
                        row.dataset.predefined = 'true';
                        var lbl = document.createElement('label');
                        lbl.style.minWidth = '160px';
                        lbl.style.fontWeight = '600';
                        lbl.textContent = e.name || ('Elem ' + (idx+1));
                                var rawOptions = Array.isArray(e.options) ? e.options : [];
                                var normalizedOptions = rawOptions.map(function(opt){
                                    if (opt && typeof opt === 'object') {
                                        // keep object as-is (expecting {value,label,custom_input,placeholder})
                                        return opt;
                                    }
                                    var s = String(opt || '').trim();
                                    return s ? s : null;
                                }).filter(function(x){ return x !== null; });

                                var control;
                                if (normalizedOptions.length) {
                                    // detect custom option
                                    var customOpt = normalizedOptions.find(function(o){ return (typeof o === 'object' && (o.custom_input === true || o.customInput === true)) || (typeof o === 'string' && o === '__custom__'); });
                                    // Special-case: render checkbox list when element name is 'checked'
                                    if ((e.name || '').toString().trim().toLowerCase() === 'checked') {
                                        var cbContainer = document.createElement('div');
                                        cbContainer.style.display = 'flex';
                                        cbContainer.style.flexDirection = 'column';
                                        cbContainer.style.flex = '1';
                                        cbContainer.dataset.key = e.name || '';
                                        normalizedOptions.forEach(function(opt, oidx){
                                            var optionLabel = (typeof opt === 'object') ? (opt.label !== undefined ? String(opt.label) : String(opt.value)) : String(opt);
                                            var optionVal = (typeof opt === 'object') ? (opt.value !== undefined ? String(opt.value) : optionLabel) : optionLabel;
                                            var cbRow = document.createElement('label');
                                            cbRow.style.display = 'flex';
                                            cbRow.style.alignItems = 'center';
                                            cbRow.style.gap = '0.6em';
                                            var cb = document.createElement('input');
                                            cb.type = 'checkbox';
                                            cb.dataset.key = e.name || '';
                                            cb.dataset.option = optionVal;
                                            cb.value = optionVal;
                                            var span = document.createElement('span');
                                            span.textContent = optionLabel;
                                            cbRow.appendChild(cb);
                                            cbRow.appendChild(span);
                                            cbContainer.appendChild(cbRow);
                                        });
                                        row.appendChild(lbl);
                                        row.appendChild(cbContainer);
                                        groupValidationBezeichnungsContainer.appendChild(row);
                                        return;
                                    }
                                    var select = document.createElement('select');
                                    select.style.flex = '1';
                                    select.name = e.name || '';
                                    normalizedOptions.forEach(function(opt){
                                        var optionEl = document.createElement('option');
                                        if (typeof opt === 'object') {
                                            var val = opt.value !== undefined ? String(opt.value) : (opt.label !== undefined ? String(opt.label) : '');
                                            var lbl = opt.label !== undefined ? String(opt.label) : val;
                                            optionEl.value = val;
                                            optionEl.textContent = lbl;
                                        } else {
                                            optionEl.value = String(opt);
                                            optionEl.textContent = String(opt);
                                        }
                                        select.appendChild(optionEl);
                                    });
                                    // determine initial selection
                                    try {
                                        if (e.value) select.value = e.value;
                                    } catch (ex) {}
                                    row.appendChild(lbl);
                                    row.appendChild(select);
                                    // if custom option exists, add a text input hidden/shown when selected
                                    if (customOpt) {
                                        var customId = 'gv_custom_' + (e.name || '').replace(/[^a-zA-Z0-9_\-]/g, '_');
                                        var customInput = document.createElement('input');
                                        customInput.type = 'text';
                                        customInput.id = customId;
                                        customInput.name = '__gv_custom_' + (e.name || '');
                                        customInput.dataset.customFor = e.name || '';
                                        customInput.style.flex = '1';
                                        customInput.style.marginTop = '0.35em';
                                        customInput.value = '';
                                        if (typeof customOpt === 'object') {
                                            customInput.placeholder = customOpt.placeholder || customOpt.label || 'Custom value';
                                        } else {
                                            customInput.placeholder = 'Custom value';
                                        }
                                        // show if selected value equals custom option value
                                        var customValue = typeof customOpt === 'object' ? (customOpt.value !== undefined ? String(customOpt.value) : '') : '__custom__';
                                        var updateVisibility = function(){
                                            customInput.style.display = (select.value === customValue) ? 'block' : 'none';
                                        };
                                        select.addEventListener('change', updateVisibility);
                                        updateVisibility();
                                        row.appendChild(customInput);
                                    }
                                } else {
                                    control = document.createElement('input');
                                    control.type = 'text';
                                    control.style.flex = '1';
                                    control.value = e.value || '';
                                    control.placeholder = '';
                                    control.title = '';
                                    row.appendChild(lbl);
                                    row.appendChild(control);
                                }
                                // attach dataset on the control(s)
                                if (control) {
                                    control.dataset.key = e.name || '';
                                    control.dataset.options = JSON.stringify(normalizedOptions);
                                } else if (row) {
                                    // set dataset for select and custom input handled above
                                    var sel = row.querySelector('select');
                                    if (sel) sel.dataset.key = e.name || '';
                                }
                                groupValidationBezeichnungsContainer.appendChild(row);
                    } catch (ex) {}
                });
                // Render custom Bezeichnungselemente that have been added
                if (groupValidationCustomBezeichnungselemente && groupValidationCustomBezeichnungselemente.length) {
                    groupValidationCustomBezeichnungselemente.forEach(function(elem, idx){
                        var row = renderCustomBezeichnungRow(elem, idx);
                        groupValidationBezeichnungsContainer.appendChild(row);
                    });
                }
            }
            if (groupValidationModalMeta) {
                groupValidationModalMeta.textContent = `${t("validationProgress") || "Progress"}: ${groupValidationIndex + 1} / ${groupValidationQueue.length}`;
            }
            // Clear input fields for adding new elements
            if (groupValidationNewBezeichnungName) groupValidationNewBezeichnungName.value = '';
            if (groupValidationNewBezeichnungValue) groupValidationNewBezeichnungValue.value = '';
            setGroupValidationStatus("");
            if (groupValidationModal) {
                groupValidationModal.style.display = "flex";
            }
            // Always align predefined fields with currently selected group path.
            refreshGroupValidationBezeichnungselemente();
            // initialize bezeichnung inputs
            if (groupValidationBezeichnung1) groupValidationBezeichnung1.value = item.bezeichnung1_de || '';
            if (groupValidationBezeichnung2) groupValidationBezeichnung2.value = item.bezeichnung2_de || '';
        }

        function getGroupValidationUpdates() {
            var updates = {
                hauptgruppe: getInputOrSelectValue(groupValidationHauptgruppeCustom, groupValidationHauptgruppe),
                untergruppe: getInputOrSelectValue(groupValidationUntergruppeCustom, groupValidationUntergruppe),
                spezifikation: getInputOrSelectValue(groupValidationSpezifikationCustom, groupValidationSpezifikation)
            };
            // collect bezeichnungselemente inputs
            if (groupValidationBezeichnungsContainer) {
                var elems = [];
                var customInputsByField = {};
                var selects = [];
                Array.from(groupValidationBezeichnungsContainer.querySelectorAll('input, select')).forEach(function(inp){
                    if (inp.tagName === 'SELECT') {
                        selects.push(inp);
                    } else if (inp.dataset.customFor) {
                        if (!customInputsByField[inp.dataset.customFor]) customInputsByField[inp.dataset.customFor] = inp;
                    }
                });
                // collect select values and substitute with custom input if custom is selected
                selects.forEach(function(sel){
                    var key = sel.dataset.key || sel.name || '';
                    var val = sel.value || '';
                    var customInput = customInputsByField[key];
                    if (customInput && customInput.value && customInput.style.display !== 'none') {
                        val = customInput.value;
                    }
                    if (key) elems.push({ name: key, value: val });
                });
                // also collect any plain text inputs (non-custom)
                Array.from(groupValidationBezeichnungsContainer.querySelectorAll('input[type="text"]:not([data-custom-for])')).forEach(function(inp){
                    if (inp.dataset.key) {
                        var val = inp.value || '';
                        elems.push({ name: inp.dataset.key, value: val });
                    }
                });
                // collect custom value inputs (editable custom elements added via "Add Element")
                Array.from(groupValidationBezeichnungsContainer.querySelectorAll('input[data-customValue="true"]')).forEach(function(inp){
                    var name = inp.dataset.customName || '';
                    var val = inp.value || '';
                    if (name && !elems.some(function(e){ return e.name === name; })) {
                        elems.push({ name: name, value: val });
                    }
                });
                // collect checkbox groups: group by data-key and join checked option labels
                var checkboxMap = {};
                Array.from(groupValidationBezeichnungsContainer.querySelectorAll('input[type="checkbox"][data-key]')).forEach(function(cb){
                    var key = cb.dataset.key || '';
                    var opt = cb.dataset.option || cb.value || '';
                    if (!checkboxMap[key]) checkboxMap[key] = [];
                    if (cb.checked) checkboxMap[key].push(opt);
                });
                Object.keys(checkboxMap).forEach(function(k){
                    var joined = (checkboxMap[k] || []).filter(function(x){ return String(x||'').trim(); }).join(', ');
                    elems.push({ name: k, value: joined });
                });
                updates.bezeichnungselemente = elems;
            }
            // include manually edited rendered bezeichnung texts
            if (groupValidationBezeichnung1) updates.bezeichnung1_de = groupValidationBezeichnung1.value || '';
            if (groupValidationBezeichnung2) updates.bezeichnung2_de = groupValidationBezeichnung2.value || '';
            return updates;
        }

        var _gv_render_timer = null;
        function requestRenderBezeichnungen() {
            if (_gv_render_timer) clearTimeout(_gv_render_timer);
            _gv_render_timer = setTimeout(function(){
                try { renderBezeichnungen(); } catch(e){}
            }, 250);
        }

        function attachBezeichnungElementListeners() {
            if (!groupValidationBezeichnungsContainer) return;
            Array.from(groupValidationBezeichnungsContainer.querySelectorAll('input, select')).forEach(function(el){
                // avoid adding duplicate listeners by using a marker
                if (el.dataset._gv_listened) return;
                el.addEventListener('change', requestRenderBezeichnungen);
                el.addEventListener('input', requestRenderBezeichnungen);
                el.dataset._gv_listened = '1';
            });
            // also listen to custom element inputs
            Array.from(groupValidationBezeichnungsContainer.querySelectorAll('input[data-customValue="true"]')).forEach(function(el){
                if (el.dataset._gv_listened) return;
                el.addEventListener('input', requestRenderBezeichnungen);
                el.dataset._gv_listened = '1';
            });
        }

        function renderBezeichnungen() {
            if (!groupValidationCurrentItem) return;
            // collect current bezeichnungselemente from DOM similar to getGroupValidationUpdates (but only elements)
            var elems = [];
            if (groupValidationBezeichnungsContainer) {
                var selects = [];
                Array.from(groupValidationBezeichnungsContainer.querySelectorAll('select')).forEach(function(sel){ selects.push(sel); });
                selects.forEach(function(sel){
                    var key = sel.dataset.key || sel.name || '';
                    var val = sel.value || '';
                    var custom = groupValidationBezeichnungsContainer.querySelector('input[data-custom-for="' + key + '"]');
                    if (custom && custom.style.display !== 'none' && custom.value) val = custom.value;
                    if (key) elems.push({ name: key, value: val });
                });
                Array.from(groupValidationBezeichnungsContainer.querySelectorAll('input[type="text"][data-key]')).forEach(function(inp){ if (inp.dataset.key) elems.push({ name: inp.dataset.key, value: inp.value || '' }); });
                Array.from(groupValidationBezeichnungsContainer.querySelectorAll('input[data-customValue="true"]')).forEach(function(inp){ var name = inp.dataset.customName || ''; if (name) elems.push({ name: name, value: inp.value || '' }); });
                var checkboxMap = {};
                Array.from(groupValidationBezeichnungsContainer.querySelectorAll('input[type="checkbox"][data-key]')).forEach(function(cb){ var key = cb.dataset.key || ''; var opt = cb.dataset.option || cb.value || ''; if (!checkboxMap[key]) checkboxMap[key]=[]; if (cb.checked) checkboxMap[key].push(opt); });
                Object.keys(checkboxMap).forEach(function(k){ elems.push({ name: k, value: (checkboxMap[k]||[]).join(', ') }); });
            }
            fetch('/api/validate/groups/render-bezeichnungen', {
                method: 'POST', headers: {'Content-Type':'application/json'},
                body: JSON.stringify({ artnr: groupValidationCurrentItem.artnr, bezeichnungselemente: elems })
            }).then(function(r){ return r.json(); }).then(function(data){
                if (data && data.status === 'ok') {
                    if (groupValidationBezeichnung1) groupValidationBezeichnung1.value = data.bezeichnung1_de || '';
                    if (groupValidationBezeichnung2) groupValidationBezeichnung2.value = data.bezeichnung2_de || '';
                }
            }).catch(function(e){ if (DEBUG) console.log('render bezeichnungen error', e); });
        }

        function showNextGroupValidationItem() {
            if (groupValidationIndex >= groupValidationQueue.length) {
                hideGroupValidationModal();
                var feedbackLogDone = document.getElementById("feedbackLog");
                if (feedbackLogDone) {
                    feedbackLogDone.innerHTML = `<div><b>Validate Groups:</b> <span style='color:#27ae60;'>Completed ${groupValidationQueue.length} entries.</span></div>` + feedbackLogDone.innerHTML;
                }
                return;
            }
            fillGroupValidationForm(groupValidationQueue[groupValidationIndex]);
        }

        function startGroupValidationFlow() {
            if (!validateArticleGroupsBtn) {
                return;
            }
            validateArticleGroupsBtn.disabled = true;
            validateArticleGroupsBtn.textContent = "Loading...";
            fetch("/api/validate/groups")
                .then(function(response) {
                    return response.json();
                })
                .then(function(data) {
                    if (!data || data.status !== "ok") {
                        throw new Error((data && data.message) || "Failed to load group validation queue.");
                    }
                    groupValidationQueue = Array.isArray(data.items) ? data.items : [];
                    groupValidationGroupsTree = data.groups_tree || {};
                    groupValidationIndex = 0;
                    if (!groupValidationQueue.length) {
                        alert(t("validationNoItems") || "No cache entries found.");
                        return;
                    }
                    groupValidationUseFileQueue = false;
                    showNextGroupValidationItem();
                })
                .catch(function(err) {
                    alert(err.message || String(err));
                })
                .finally(function() {
                    validateArticleGroupsBtn.disabled = false;
                    validateArticleGroupsBtn.textContent = t("validateArticleGroups") || "Validate Groups";
                });
        }

        if (validateArticleGroupsBtn) {
            validateArticleGroupsBtn.addEventListener("click", startGroupValidationFlow);
        }

        // Also allow starting group validation from the Create tab button
        if (createValidateGroupsBtn) {
            createValidateGroupsBtn.addEventListener("click", startGroupValidationFromFileFlow);
            // keep label in sync
            createValidateGroupsBtn.textContent = t("validateArticleGroups") || "Validate Groups";
        }

        function startGroupValidationFromFileFlow() {
            if (!createValidateGroupsBtn) return;
            createValidateGroupsBtn.disabled = true;
            createValidateGroupsBtn.textContent = "Loading...";
            fetch("/api/validate/groups/from-file", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({}) })
                .then(function(response) { return response.json(); })
                .then(function(data) {
                    if (!data || data.status !== "ok") {
                        throw new Error((data && data.message) || "Failed to load group validation queue from file.");
                    }
                    groupValidationQueue = Array.isArray(data.items) ? data.items : [];
                    groupValidationGroupsTree = data.groups_tree || {};
                    groupValidationIndex = 0;
                    groupValidationUseFileQueue = true;
                    if (!groupValidationQueue.length) {
                        alert(t("validationNoItems") || "No cache entries found.");
                        return;
                    }
                    showNextGroupValidationItem();
                })
                .catch(function(err) { alert(err.message || String(err)); })
                .finally(function() {
                    createValidateGroupsBtn.disabled = false;
                    createValidateGroupsBtn.textContent = t("validateArticleGroups") || "Validate Groups";
                });
        }

        if (groupValidationHauptgruppe) {
            groupValidationHauptgruppe.addEventListener("change", populateGroupValidationUntergruppen);
        }
        if (groupValidationUntergruppe) {
            groupValidationUntergruppe.addEventListener("change", populateGroupValidationSpezifikationen);
        }
        if (groupValidationHauptgruppeCustom) {
            groupValidationHauptgruppeCustom.addEventListener('input', function() {
                populateGroupValidationUntergruppen();
            });
        }
        if (groupValidationUntergruppeCustom) {
            groupValidationUntergruppeCustom.addEventListener('input', function() {
                populateGroupValidationSpezifikationen();
            });
        }

        if (!groupValidationAutoRefreshHandler) {
            groupValidationAutoRefreshHandler = function() {
                refreshGroupValidationBezeichnungselemente();
            };
        }
        if (groupValidationHauptgruppe) {
            groupValidationHauptgruppe.addEventListener('change', groupValidationAutoRefreshHandler);
        }
        if (groupValidationHauptgruppeCustom) {
            groupValidationHauptgruppeCustom.addEventListener('input', groupValidationAutoRefreshHandler);
            groupValidationHauptgruppeCustom.addEventListener('change', groupValidationAutoRefreshHandler);
        }
        if (groupValidationUntergruppe) {
            groupValidationUntergruppe.addEventListener('change', groupValidationAutoRefreshHandler);
        }
        if (groupValidationUntergruppeCustom) {
            groupValidationUntergruppeCustom.addEventListener('input', groupValidationAutoRefreshHandler);
            groupValidationUntergruppeCustom.addEventListener('change', groupValidationAutoRefreshHandler);
        }
        if (groupValidationSpezifikation) {
            groupValidationSpezifikation.addEventListener('change', groupValidationAutoRefreshHandler);
        }
        if (groupValidationSpezifikationCustom) {
            groupValidationSpezifikationCustom.addEventListener('input', groupValidationAutoRefreshHandler);
            groupValidationSpezifikationCustom.addEventListener('change', groupValidationAutoRefreshHandler);
        }

        function ensureGroupPathExists(hauptgruppe, untergruppe, spezifikation) {
            var hg = String(hauptgruppe || '').trim();
            var ug = String(untergruppe || '').trim();
            var spec = String(spezifikation || '').trim();
            if (!hg) {
                return Promise.resolve();
            }
            return fetch('/api/validate/groups/add', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    hauptgruppe: hg,
                    untergruppe: ug,
                    spezifikation: (ug ? spec : '')
                })
            })
            .then(function(r) { return r.json(); })
            .then(function(data) {
                if (!data || data.status !== 'ok') {
                    throw new Error((data && data.message) || 'Failed to add group entry');
                }
            });
        }

        if (groupValidationConfirmBtn) {
            groupValidationConfirmBtn.addEventListener("click", function() {
                if (groupValidationSaving || !groupValidationCurrentItem) {
                    return;
                }
                var updates = getGroupValidationUpdates();
                groupValidationSaving = true;
                setGroupValidationStatus("Saving...");
                ensureGroupPathExists(updates.hauptgruppe, updates.untergruppe, updates.spezifikation)
                .then(function() {
                    ensureSelectHasValue(groupValidationHauptgruppe, updates.hauptgruppe);
                    ensureSelectHasValue(groupValidationUntergruppe, updates.untergruppe);
                    ensureSelectHasValue(groupValidationSpezifikation, updates.spezifikation);
                    var saveUrl = groupValidationUseFileQueue ? "/api/validate/groups/from-file/save" : "/api/validate/groups/save";
                    return fetch(saveUrl, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(Object.assign({ artnr: groupValidationCurrentItem.artnr }, updates))
                });
                })
                .then(function(response) {
                    return response.json();
                })
                .then(function(data) {
                    if (!data || data.status !== "ok") {
                        throw new Error((data && data.message) || "Failed to save group validation item.");
                    }
                    var feedbackLog = document.getElementById("feedbackLog");
                    if (feedbackLog) {
                        feedbackLog.innerHTML = `<div><b>Validate Groups:</b> <span style='color:#27ae60;'>Saved ${groupValidationCurrentItem.artnr || ""}.</span></div>` + feedbackLog.innerHTML;
                    }
                    groupValidationIndex += 1;
                    showNextGroupValidationItem();
                })
                .catch(function(err) {
                    setGroupValidationStatus(err.message || String(err), true);
                })
                .finally(function() {
                    groupValidationSaving = false;
                });
            });
        }

        if (groupValidationAddBtn) {
            groupValidationAddBtn.addEventListener('click', function() {
                // collect values: explicit "new" fields have priority, then custom inputs, then selected options
                var newHg = groupValidationNewHauptgruppe ? groupValidationNewHauptgruppe.value.trim() : '';
                var newUg = groupValidationNewUntergruppe ? groupValidationNewUntergruppe.value.trim() : '';
                var newSpec = groupValidationNewSpezifikation ? groupValidationNewSpezifikation.value.trim() : '';
                var hgToSend = newHg || getInputOrSelectValue(groupValidationHauptgruppeCustom, groupValidationHauptgruppe);
                var ugToSend = newUg || getInputOrSelectValue(groupValidationUntergruppeCustom, groupValidationUntergruppe);
                var specToSend = newSpec || getInputOrSelectValue(groupValidationSpezifikationCustom, groupValidationSpezifikation);
                if (!hgToSend) {
                    alert('Please provide at least a Hauptgruppe name');
                    return;
                }
                groupValidationAddBtn.disabled = true;
                groupValidationAddBtn.textContent = 'Adding...';
                fetch('/api/validate/groups/add', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ hauptgruppe: hgToSend, untergruppe: ugToSend || '', spezifikation: (ugToSend ? specToSend : '') })
                })
                .then(function(r){ return r.json(); })
                .then(function(data){
                    if (!data || data.status !== 'ok') {
                        throw new Error((data && data.message) || 'Failed to add group entry');
                    }
                    // update local groups tree and UI
                    // reload groups tree from server by re-fetching queue
                    return fetch('/api/validate/groups').then(function(r){ return r.json(); });
                })
                .then(function(data){
                    if (data && data.status === 'ok') {
                        groupValidationGroupsTree = data.groups_tree || {};
                        // refill current form options
                        fillGroupValidationForm(groupValidationCurrentItem);
                        // clear add inputs
                        if (groupValidationNewHauptgruppe) groupValidationNewHauptgruppe.value = '';
                        if (groupValidationNewUntergruppe) groupValidationNewUntergruppe.value = '';
                        if (groupValidationNewSpezifikation) groupValidationNewSpezifikation.value = '';
                    }
                })
                .catch(function(err){ alert(err.message || String(err)); })
                .finally(function(){ groupValidationAddBtn.disabled = false; groupValidationAddBtn.textContent = 'Add'; });
            });
        }

        if (groupValidationAddBezeichnungBtn) {
            groupValidationAddBezeichnungBtn.addEventListener('click', function() {
                var name = groupValidationNewBezeichnungName ? groupValidationNewBezeichnungName.value.trim() : '';
                var value = groupValidationNewBezeichnungValue ? groupValidationNewBezeichnungValue.value.trim() : '';
                if (!name) {
                    alert('Please provide an element name');
                    return;
                }
                // Add to custom list
                groupValidationCustomBezeichnungselemente.push({ name: name, value: value });
                // Render it in the container
                if (groupValidationBezeichnungsContainer) {
                    var row = renderCustomBezeichnungRow({ name: name, value: value }, groupValidationCustomBezeichnungselemente.length - 1);
                    groupValidationBezeichnungsContainer.appendChild(row);
                }
                // Clear inputs
                if (groupValidationNewBezeichnungName) groupValidationNewBezeichnungName.value = '';
                if (groupValidationNewBezeichnungValue) groupValidationNewBezeichnungValue.value = '';
            });
        }

        if (groupValidationCloseBtn) {
            groupValidationCloseBtn.addEventListener("click", function() {
                hideGroupValidationModal();
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

    // ─── Article Number Generation Handler ────────────────────────────────────
    const generateNumberBtn = document.getElementById("generateNumberBtn");
    const numberPrefixInput = document.getElementById("numberPrefix");
    const generatedNumberInput = document.getElementById("generatedNumber");
    const numberStatusDiv = document.getElementById("numberGenerationStatus");

    if (generateNumberBtn) {
        generateNumberBtn.addEventListener("click", function() {
            const prefix = numberPrefixInput.value.trim();
            numberStatusDiv.innerHTML = '<span style="color:#888;">Generating...</span>';

            fetch("/api/generate-article-number", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ prefix })
            })
            .then(r => r.json())
            .then(result => {
                if (result.status === "ok") {
                    generatedNumberInput.value = result.number;
                    numberStatusDiv.innerHTML = '<span style="color:#27ae60;">✓ Number generated successfully</span>';
                } else {
                    numberStatusDiv.innerHTML = `<span style="color:#c00;">Error: ${escHtml(result.message)}</span>`;
                    generatedNumberInput.value = "";
                }
            })
            .catch(err => {
                numberStatusDiv.innerHTML = `<span style="color:#c00;">Error: ${escHtml(String(err))}</span>`;
                generatedNumberInput.value = "";
            });
        });

        // Allow Enter key to generate number
        numberPrefixInput.addEventListener("keypress", function(e) {
            if (e.key === "Enter") {
                generateNumberBtn.click();
            }
        });
    }
});
