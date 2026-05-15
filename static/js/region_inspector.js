(function () {
'use strict';

window.layoutEditorState = window.layoutEditorState || {
    currentProfile: null,
    layoutConfig: null,
    geometry: null,
    selectedRegionId: null,
    previewState: {},
    imagePool: []
};
window.layoutEditorState.previewState = window.layoutEditorState.previewState || {};
window.layoutEditorState.imagePool = Array.isArray(window.layoutEditorState.imagePool) ? window.layoutEditorState.imagePool : [];
const state = window.layoutEditorState;

function renderInspectorBlockEditor(block, blockIndex) {
    const type = String(block.type || "description_fields").trim() || "description_fields";
    const options = normalizeLayoutBlockOptions(type, block.options || {});
    const common = `
        <div class="inspector-field">
            <label>Block Type</label>
            <select onchange="updateInspectorBlockField(${blockIndex}, 'type', this.value, true)">
                <option value="description_fields" ${type === "description_fields" ? "selected" : ""}>description_fields</option>
                <option value="image" ${type === "image" ? "selected" : ""}>image</option>
                <option value="image_gallery" ${type === "image_gallery" ? "selected" : ""}>image_gallery</option>
                <option value="image_stack" ${type === "image_stack" ? "selected" : ""}>image_stack</option>
            </select>
        </div>
        <label class="checkbox-line inspector-field">
            <input type="checkbox" ${block.enabled !== false ? "checked" : ""} onchange="updateInspectorBlockField(${blockIndex}, 'enabled', this.checked)">
            <span>启用 Block</span>
        </label>
        <div class="inspector-field">
            <label>Source</label>
            <input value="${escapeHtml(block.source || "")}" oninput="updateInspectorBlockField(${blockIndex}, 'source', this.value)">
        </div>
    `;

    if (type === "image_stack") {
        return common + `
            <label class="checkbox-line inspector-field">
                <input type="checkbox" ${options.auto_source === true ? "checked" : ""} onchange="updateInspectorBlockField(${blockIndex}, 'options.auto_source', this.checked, true)">
                <span>自动使用当前订单上传的所有图片</span>
            </label>
            <label class="checkbox-line inspector-field">
                <input type="checkbox" ${options.use_image_pool === true ? "checked" : ""} onchange="updateInspectorBlockField(${blockIndex}, 'options.use_image_pool', this.checked, true)">
                <span>使用首页图片素材池</span>
            </label>
            <div class="inspector-field">
                <label>source_keys</label>
                <input value="${escapeHtml((options.source_keys || []).join(","))}" placeholder="${options.auto_source ? "auto_source 开启时不生效" : ""}" oninput="updateInspectorBlockField(${blockIndex}, 'options.source_keys', this.value)">
            </div>
            <div class="inspector-field">
                <label>exclude_keys</label>
                <input value="${escapeHtml((options.exclude_keys || []).join(","))}" placeholder="logo_image,qr_code" oninput="updateInspectorBlockField(${blockIndex}, 'options.exclude_keys', this.value)">
            </div>
            <div class="inspector-field">
                <label>max_images</label>
                <input type="number" min="0" value="${escapeHtml(options.max_images || 0)}" placeholder="0=不限制" oninput="updateInspectorBlockField(${blockIndex}, 'options.max_images', this.value)">
            </div>
            <div class="inspector-field">
                <label>width</label>
                <input type="number" min="1" value="${escapeHtml(options.image_width)}" oninput="updateInspectorBlockField(${blockIndex}, 'options.image_width', this.value)">
            </div>
            <div class="inspector-field">
                <label>height</label>
                <input type="number" min="1" value="${escapeHtml(options.image_height)}" oninput="updateInspectorBlockField(${blockIndex}, 'options.image_height', this.value)">
            </div>
            <label class="checkbox-line inspector-field">
                <input type="checkbox" ${options.keep_ratio !== false ? "checked" : ""} onchange="updateInspectorBlockField(${blockIndex}, 'options.keep_ratio', this.checked)">
                <span>keep_ratio</span>
            </label>
            <div class="inspector-field">
                <label>gap_px</label>
                <input type="number" min="0" value="${escapeHtml(options.gap_px)}" oninput="updateInspectorBlockField(${blockIndex}, 'options.gap_px', this.value)">
            </div>
            <div class="inspector-field">
                <label>layout_mode</label>
                <select onchange="updateInspectorBlockField(${blockIndex}, 'options.layout_mode', this.value)">
                    <option value="auto_stack" ${options.layout_mode === "auto_stack" ? "selected" : ""}>auto_stack</option>
                    <option value="row_step" ${options.layout_mode === "row_step" ? "selected" : ""}>row_step</option>
                </select>
            </div>
            <div class="inspector-field">
                <label>anchor_cell</label>
                <input value="${escapeHtml(options.anchor_cell || "")}" oninput="updateInspectorBlockField(${blockIndex}, 'options.anchor_cell', this.value)">
            </div>
        `;
    }

    if (type === "image_gallery") {
        return common + `
            <label class="checkbox-line inspector-field">
                <input type="checkbox" ${options.auto_source === true ? "checked" : ""} onchange="updateInspectorBlockField(${blockIndex}, 'options.auto_source', this.checked, true)">
                <span>自动使用当前订单上传的所有图片</span>
            </label>
            <label class="checkbox-line inspector-field">
                <input type="checkbox" ${options.use_image_pool === true ? "checked" : ""} onchange="updateInspectorBlockField(${blockIndex}, 'options.use_image_pool', this.checked, true)">
                <span>使用首页图片素材池</span>
            </label>
            <div class="inspector-field">
                <label>source_keys</label>
                <input value="${escapeHtml((options.source_keys || []).join(","))}" placeholder="${options.auto_source ? "auto_source 开启时不生效" : ""}" oninput="updateInspectorBlockField(${blockIndex}, 'options.source_keys', this.value)">
            </div>
            <div class="inspector-field">
                <label>exclude_keys</label>
                <input value="${escapeHtml((options.exclude_keys || []).join(","))}" placeholder="logo_image,qr_code" oninput="updateInspectorBlockField(${blockIndex}, 'options.exclude_keys', this.value)">
            </div>
            <div class="inspector-field">
                <label>max_images</label>
                <input type="number" min="0" value="${escapeHtml(options.max_images || 0)}" placeholder="0=不限制" oninput="updateInspectorBlockField(${blockIndex}, 'options.max_images', this.value)">
            </div>
            <div class="inspector-field">
                <label>columns</label>
                <input type="number" min="1" value="${escapeHtml(options.columns)}" oninput="updateInspectorBlockField(${blockIndex}, 'options.columns', this.value)">
            </div>
            <div class="inspector-field">
                <label>width</label>
                <input type="number" min="1" value="${escapeHtml(options.image_width)}" oninput="updateInspectorBlockField(${blockIndex}, 'options.image_width', this.value)">
            </div>
            <div class="inspector-field">
                <label>height</label>
                <input type="number" min="1" value="${escapeHtml(options.image_height)}" oninput="updateInspectorBlockField(${blockIndex}, 'options.image_height', this.value)">
            </div>
            <label class="checkbox-line inspector-field">
                <input type="checkbox" ${options.keep_ratio !== false ? "checked" : ""} onchange="updateInspectorBlockField(${blockIndex}, 'options.keep_ratio', this.checked)">
                <span>keep_ratio</span>
            </label>
            <div class="inspector-field">
                <label>row_step</label>
                <input type="number" min="1" value="${escapeHtml(options.row_step)}" oninput="updateInspectorBlockField(${blockIndex}, 'options.row_step', this.value)">
            </div>
            <div class="inspector-field">
                <label>col_step</label>
                <input type="number" min="1" value="${escapeHtml(options.col_step)}" oninput="updateInspectorBlockField(${blockIndex}, 'options.col_step', this.value)">
            </div>
        `;
    }

    if (type === "image") {
        return common + `
            <div class="inspector-field">
                <label>width</label>
                <input type="number" min="1" value="${escapeHtml(options.width)}" oninput="updateInspectorBlockField(${blockIndex}, 'options.width', this.value)">
            </div>
            <div class="inspector-field">
                <label>height</label>
                <input type="number" min="1" value="${escapeHtml(options.height)}" oninput="updateInspectorBlockField(${blockIndex}, 'options.height', this.value)">
            </div>
            <label class="checkbox-line inspector-field">
                <input type="checkbox" ${options.keep_ratio !== false ? "checked" : ""} onchange="updateInspectorBlockField(${blockIndex}, 'options.keep_ratio', this.checked)">
                <span>keep_ratio</span>
            </label>
        `;
    }

    return common;
}



function renderRegionInspector() {
    const inspector = document.getElementById("regionInspector");
    if (!inspector) {
        return;
    }
    if (!state.currentProfile || !state.currentProfile.layout_config || !state.currentProfile.layout_config.regions.length) {
        inspector.innerHTML = `<div class="inspector-muted">请选择或新增一个 Region。</div>`;
        return;
    }

    ensureSelectedLayoutRegion(state.currentProfile.layout_config.regions);
    const { index, region } = getSelectedLayoutRegion();
    if (!region) {
        inspector.innerHTML = `<div class="inspector-muted">请选择一个 Region。</div>`;
        return;
    }

    const blocks = Array.isArray(region.blocks) ? region.blocks : [];
    const blockCards = blocks.map((block, blockIndex) => {
        const isSelected = state.inspectorBlockIndex === blockIndex;
        return `
            <div class="inspector-block-card ${isSelected ? "selected" : ""}">
                <div class="inspector-block-title" onclick="selectInspectorBlock(${blockIndex})">
                    <span>[${escapeHtml(block.type || "description_fields")}]</span>
                    <span class="inspector-muted">${block.enabled !== false ? "on" : "off"}</span>
                </div>
                <div class="inspector-muted">${escapeHtml(summarizeBlockOptions(block))}</div>
                ${isSelected ? `
                    <div class="inspector-block-options">
                        ${renderInspectorBlockEditor(block, blockIndex)}
                        <button class="delete" type="button" onclick="deleteInspectorBlock(${blockIndex})">删除 Block</button>
                    </div>
                ` : ""}
            </div>
        `;
    }).join("");

    inspector.innerHTML = `
        <div class="inspector-summary">
            <h3>${escapeHtml(region.name || region.id || "Region")}</h3>
            <div class="inspector-muted">${escapeHtml(region.type || "region")}</div>
            <div class="inspector-muted">${escapeHtml(region.range || "-")}</div>
        </div>
        <div class="inspector-field">
            <label>Region Name</label>
            <input value="${escapeHtml(region.name || "")}" oninput="updateInspectorRegionField('name', this.value)">
        </div>
        <div class="inspector-field">
            <label>Excel Range</label>
            <input value="${escapeHtml(region.range || "")}" oninput="updateInspectorRegionField('range', this.value.toUpperCase())">
        </div>
        <div class="inspector-field">
            <label>Sheet</label>
            <div class="inspector-muted">${escapeHtml(region.sheet || "active")}</div>
        </div>
        <label class="checkbox-line inspector-field">
            <input type="checkbox" ${region.enabled !== false ? "checked" : ""} onchange="updateInspectorRegionField('enabled', this.checked)">
            <span>启用 Region</span>
        </label>
        <div class="button-row">
            <button type="button" onclick="addInspectorBlock()">新增 Block</button>
            <button class="delete" type="button" onclick="deleteInspectorRegion()">删除 Region</button>
        </div>
        <h4>Blocks</h4>
        ${blockCards || `<div class="inspector-muted">暂无 Block。</div>`}
    `;
}



function updateInspectorRegionField(field, value) {
    const { index, region } = getSelectedLayoutRegion();
    if (!region) {
        return;
    }
    const idPrefix = "layout_region_" + field + "_" + index;
    const input = document.getElementById(idPrefix);
    if (input) {
        if (input.type === "checkbox") {
            input.checked = Boolean(value);
        } else {
            input.value = value;
        }
    }
    if (field === "enabled") {
        const enabledInput = document.getElementById("layout_region_enabled_" + index);
        if (enabledInput) {
            enabledInput.checked = Boolean(value);
        }
    }
    region[field] = field === "enabled" ? Boolean(value) : String(value || "").trim();
    if (field === "range") {
        region.range = String(value || "").trim().toUpperCase();
    }
    state.currentProfile.layout_config.regions[index] = region;
    renderLayoutDesigner(state.currentProfile.layout_config.regions);
    highlightLayoutRegionForm();
}



function selectInspectorBlock(blockIndex) {
    state.inspectorBlockIndex = state.inspectorBlockIndex === blockIndex ? null : blockIndex;
    renderRegionInspector();
}



function updateInspectorBlockField(blockIndex, field, value, rerender = false) {
    const { index, region } = getSelectedLayoutRegion();
    if (!region || !region.blocks || !region.blocks[blockIndex]) {
        return;
    }
    const block = region.blocks[blockIndex];
    if (field === "type") {
        block.type = value;
        block.options = normalizeLayoutBlockOptions(value, {});
        rerender = true;
    } else if (field === "enabled") {
        block.enabled = Boolean(value);
    } else if (field === "source") {
        block.source = String(value || "").trim();
    } else if (field.startsWith("options.")) {
        const key = field.replace("options.", "");
        const type = String(block.type || "description_fields");
        const options = normalizeLayoutBlockOptions(type, block.options || {});
        if (key === "source_keys") {
            options.source_keys = parseLayoutSourceKeys(value);
        } else if (key === "exclude_keys") {
            options.exclude_keys = parseLayoutSourceKeys(value);
        } else if (key === "keep_ratio") {
            options.keep_ratio = Boolean(value);
        } else if (key === "auto_source") {
            options.auto_source = Boolean(value);
        } else if (key === "use_image_pool") {
            options.use_image_pool = Boolean(value);
        } else if (["image_width", "image_height", "width", "height", "columns", "row_step", "col_step", "gap_px"].includes(key)) {
            options[key] = parseLayoutNumber(value, options[key] || 1);
        } else if (key === "max_images") {
            options.max_images = parseLayoutNonNegativeNumber(value, 0);
        } else {
            options[key] = String(value || "").trim();
            if (key === "anchor_cell") {
                options[key] = options[key].toUpperCase();
            }
        }
        block.options = options;
    }
    region.blocks[blockIndex] = block;
    state.currentProfile.layout_config.regions[index] = region;
    renderLayoutRegions(state.currentProfile.layout_config.regions);
    renderLayoutDesigner(state.currentProfile.layout_config.regions);
    if (rerender) {
        renderRegionInspector();
    }
}



function addInspectorBlock() {
    const { index, region } = getSelectedLayoutRegion();
    if (!region) {
        return;
    }
    if (!Array.isArray(region.blocks)) {
        region.blocks = [];
    }
    region.blocks.push({
        id: `block_${Date.now()}`,
        type: "description_fields",
        enabled: true,
        source: "",
        options: {}
    });
    state.inspectorBlockIndex = region.blocks.length - 1;
    state.currentProfile.layout_config.regions[index] = region;
    renderLayoutConfig();
}



function deleteInspectorBlock(blockIndex) {
    const { index, region } = getSelectedLayoutRegion();
    if (!region || !Array.isArray(region.blocks)) {
        return;
    }
    region.blocks.splice(blockIndex, 1);
    state.inspectorBlockIndex = null;
    state.currentProfile.layout_config.regions[index] = region;
    renderLayoutConfig();
}



function deleteInspectorRegion() {
    const { index, region } = getSelectedLayoutRegion();
    if (!region) {
        return;
    }
    if (!confirm(`确定删除 Region：${region.name || region.id || region.range || index + 1} 吗？`)) {
        return;
    }
    deleteLayoutRegion(index, { skipConfirm: true });
}



Object.assign(window, {
    renderInspectorBlockEditor,
    renderRegionInspector,
    updateInspectorRegionField,
    selectInspectorBlock,
    updateInspectorBlockField,
    addInspectorBlock,
    deleteInspectorBlock,
    deleteInspectorRegion
});
})();
