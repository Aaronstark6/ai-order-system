(function () {
'use strict';

window.layoutEditorState = window.layoutEditorState || {};
Object.entries({
    currentProfile: null,
    layoutConfig: null,
    geometry: null,
    selectedRegionId: null,
    selectedBlockId: null,
    dirty: false,
    lastSavedAt: null,
    previewState: {},
    imagePool: [],
    geometryError: "",
    selectedRegionIndex: 0,
    activeDrag: null,
    advancedVisible: false
}).forEach(([key, value]) => {
    if (!Object.prototype.hasOwnProperty.call(window.layoutEditorState, key)) {
        window.layoutEditorState[key] = value;
    }
});
window.layoutEditorState.previewState = window.layoutEditorState.previewState || {};
window.layoutEditorState.imagePool = Array.isArray(window.layoutEditorState.imagePool) ? window.layoutEditorState.imagePool : [];
const state = window.layoutEditorState;

function defaultLayoutConfig() {
    return {
        enabled: false,
        regions: []
    };
}



function defaultLayoutPreview() {
    return {
        enabled: false,
        image_path: "",
        image_width: 0,
        image_height: 0
    };
}



function normalizeLayoutPreview(raw) {
    const preview = raw && typeof raw === "object" && !Array.isArray(raw) ? raw : {};
    const imagePath = String(preview.image_path || "").trim().replace(/\\/g, "/");
    const imageWidth = Math.max(0, Math.round(Number(preview.image_width || 0)));
    const imageHeight = Math.max(0, Math.round(Number(preview.image_height || 0)));
    return {
        enabled: Boolean(preview.enabled) && Boolean(imagePath),
        image_path: imagePath,
        image_width: Number.isFinite(imageWidth) ? imageWidth : 0,
        image_height: Number.isFinite(imageHeight) ? imageHeight : 0
    };
}



function normalizeLayoutConfig(raw) {
    const config = raw && typeof raw === "object" ? raw : {};
    const regions = Array.isArray(config.regions) ? config.regions : [];
    return {
        enabled: config.enabled === true,
        regions: regions.map((region, index) => ({
            id: String(region && region.id || "").trim() || `region_${Date.now()}_${index}`,
            name: String(region && region.name || "").trim(),
            type: String(region && region.type || "").trim(),
            enabled: !region || region.enabled !== false,
            sheet: String(region && region.sheet || "active").trim() || "active",
            range: String(region && region.range || "").trim().toUpperCase(),
            blocks: Array.isArray(region && region.blocks)
                ? region.blocks.map(block => {
                    const type = String(block && block.type || "").trim() || "description_fields";
                    const rawOptions = block && typeof block.options === "object" && !Array.isArray(block.options) ? block.options : {};
                    return {
                        id: String(block && block.id || "").trim(),
                        type: type,
                        source: String(block && block.source || "").trim(),
                        enabled: !block || block.enabled !== false,
                        options: normalizeLayoutBlockOptions(type, rawOptions)
                    };
                })
                : [],
            options: region && typeof region.options === "object" && !Array.isArray(region.options) ? region.options : {}
        }))
    };
}


function getLayoutEditorState() {
    return state;
}



function renderLayoutSaveStatus(message) {
    const status = document.getElementById("layoutDirtyStatus");
    if (!status) {
        return;
    }
    status.className = "layout-save-status " + (state.dirty ? "dirty" : "saved");
    status.textContent = message || (state.dirty ? "Layout 有未保存修改" : "Layout 已保存");
}


function renderLayoutAdvancedPanelState() {
    const panel = document.getElementById("layoutAdvancedPanel");
    const button = document.getElementById("layoutAdvancedToggle");
    if (panel) {
        panel.classList.toggle("open", Boolean(state.advancedVisible));
    }
    if (button) {
        button.textContent = state.advancedVisible ? "隐藏高级配置" : "显示高级配置";
    }
}



function toggleLayoutAdvancedPanel() {
    state.advancedVisible = !state.advancedVisible;
    renderLayoutAdvancedPanelState();
    if (state.advancedVisible) {
        renderLayoutRegions(getLayoutConfig().regions || []);
    }
}



function syncCurrentProfileLayoutConfig() {
    const config = getLayoutConfig();
    if (state.currentProfile) {
        state.currentProfile.layout_config = config;
    }
    try {
        if (currentProfile) {
            currentProfile.layout_config = config;
        }
    } catch (error) {
        // config.html owns the legacy currentProfile binding.
    }
    return config;
}



function markLayoutDirty() {
    state.dirty = true;
    renderLayoutSaveStatus();
}



function markLayoutSaved() {
    state.dirty = false;
    state.lastSavedAt = new Date().toISOString();
    renderLayoutSaveStatus();
}



function getLayoutConfig() {
    if (!state.layoutConfig) {
        state.layoutConfig = normalizeLayoutConfig(state.currentProfile?.layout_config || defaultLayoutConfig());
    }
    return state.layoutConfig;
}



function setLayoutConfig(layoutConfig, options = {}) {
    const config = normalizeLayoutConfig(layoutConfig || defaultLayoutConfig());
    state.layoutConfig = config;
    syncCurrentProfileLayoutConfig();
    ensureSelectedLayoutRegion(config.regions);
    if (options.dirty !== false) {
        markLayoutDirty();
    } else {
        renderLayoutSaveStatus();
    }
    if (options.render !== false) {
        renderLayoutDesigner(config.regions);
        renderRegionInspector();
    }
    return config;
}



function getSelectedRegion() {
    return getSelectedLayoutRegion().region;
}



function setSelectedRegion(regionId, options = {}) {
    const previousRegionId = state.selectedRegionId;
    state.selectedRegionId = regionId || null;
    if (previousRegionId !== state.selectedRegionId) {
        state.selectedBlockId = null;
    }
    const regions = getLayoutConfig().regions || [];
    const index = regions.findIndex((region, regionIndex) => getLayoutRegionId(region, regionIndex) === state.selectedRegionId);
    state.selectedRegionIndex = index >= 0 ? index : 0;
    highlightLayoutDesignerRegion();
    highlightLayoutRegionForm();
    if (options.renderInspector !== false) {
        renderRegionInspector();
    }
}



function setSelectedBlock(blockId) {
    state.selectedBlockId = state.selectedBlockId === blockId ? null : blockId;
    renderRegionInspector();
}



function getLayoutRegionId(region, index) {
    return String(region && region.id || `region_${index}`).trim();
}



function getLayoutBlockId(block, index) {
    return String(block && block.id || `block_${index}`).trim();
}



function findLayoutRegionIndexById(regionId) {
    const regions = getLayoutConfig().regions || [];
    return regions.findIndex((region, index) => getLayoutRegionId(region, index) === regionId);
}



function ensureSelectedLayoutRegion(regions) {
    const list = Array.isArray(regions) ? regions : [];
    if (!list.length) {
        state.selectedRegionId = null;
        state.selectedBlockId = null;
        state.selectedRegionIndex = 0;
        return;
    }
    const existingIndex = list.findIndex((region, index) => getLayoutRegionId(region, index) === state.selectedRegionId);
    state.selectedRegionIndex = existingIndex >= 0 ? existingIndex : 0;
    state.selectedRegionId = getLayoutRegionId(list[state.selectedRegionIndex], state.selectedRegionIndex);
    const blocks = list[state.selectedRegionIndex].blocks || [];
    if (state.selectedBlockId && !blocks.some((block, blockIndex) => getLayoutBlockId(block, blockIndex) === state.selectedBlockId)) {
        state.selectedBlockId = null;
    }
}



function syncLayoutDesignerRangeInput(index, range) {
    const input = document.getElementById("layout_region_range_" + index);
    if (input) {
        input.value = range;
    }
    const config = getLayoutConfig();
    if (config.regions[index]) {
        config.regions[index].range = range;
    }
    syncCurrentProfileLayoutConfig();
    markLayoutDirty();
    renderRegionInspector();
}



function syncLayoutDesignerFromRegionInput(index, shouldRender = true) {
    if (!state.currentProfile) {
        return;
    }
    const config = setLayoutConfig(collectLayoutConfig(), { render: false });
    state.selectedRegionIndex = clampLayoutDesignerValue(index, 0, Math.max(0, config.regions.length - 1));
    state.selectedRegionId = getLayoutRegionId(config.regions[state.selectedRegionIndex], state.selectedRegionIndex);
    if (shouldRender) {
        renderLayoutDesigner(config.regions);
        highlightLayoutRegionForm();
        renderRegionInspector();
    }
}



function highlightLayoutRegionForm() {
    document.querySelectorAll(".layout-region-card").forEach(card => {
        card.classList.toggle("selected", card.dataset.regionId === state.selectedRegionId);
    });
}



function highlightLayoutDesignerRegion() {
    document.querySelectorAll(".layout-designer-region").forEach(region => {
        region.classList.toggle("selected", region.dataset.regionId === state.selectedRegionId);
    });
}



function selectLayoutDesignerRegion(index, shouldScroll = true, shouldRenderInspector = true) {
    state.selectedRegionIndex = Number(index) || 0;
    const region = getLayoutConfig().regions?.[state.selectedRegionIndex];
    setSelectedRegion(getLayoutRegionId(region, state.selectedRegionIndex), {
        renderInspector: shouldRenderInspector
    });
    if (shouldScroll) {
        const card = document.querySelector(`.layout-region-card[data-region-index="${state.selectedRegionIndex}"]`);
        if (card) {
            card.scrollIntoView({ behavior: "smooth", block: "nearest" });
        }
    }
}



function renderLayoutDesigner(regions) {
    const container = document.getElementById("layoutDesignerCanvas");
    if (!container) {
        return;
    }
    const layoutConfig = getLayoutConfig();
    regions = Array.isArray(regions) ? regions : layoutConfig.regions;
    const preview = normalizeLayoutPreview(state.currentProfile?.layout_preview || defaultLayoutPreview());
    const metrics = getLayoutDesignerMetrics();

    const stage = document.createElement("div");
    stage.className = "layout-designer-stage";
    stage.style.width = `${LAYOUT_DESIGNER_ROW_LABEL_WIDTH + metrics.width}px`;
    stage.style.height = `${LAYOUT_DESIGNER_COL_LABEL_HEIGHT + metrics.height}px`;

    const corner = document.createElement("div");
    corner.className = "layout-designer-corner";
    stage.appendChild(corner);

    metrics.columns.forEach((column, index) => {
        const label = document.createElement("div");
        label.className = "layout-designer-col";
        label.textContent = column.letter;
        label.title = `${column.letter}: ${column.width}px`;
        label.style.left = `${LAYOUT_DESIGNER_ROW_LABEL_WIDTH + metrics.columnBoundaries[index]}px`;
        label.style.top = "0";
        label.style.width = `${column.width}px`;
        label.style.height = `${LAYOUT_DESIGNER_COL_LABEL_HEIGHT}px`;
        stage.appendChild(label);
    });

    metrics.rows.forEach((row, index) => {
        const label = document.createElement("div");
        label.className = "layout-designer-row";
        label.textContent = String(row.index);
        label.title = `${row.index}: ${row.height}px`;
        label.style.left = "0";
        label.style.top = `${LAYOUT_DESIGNER_COL_LABEL_HEIGHT + metrics.rowBoundaries[index]}px`;
        label.style.width = `${LAYOUT_DESIGNER_ROW_LABEL_WIDTH}px`;
        label.style.height = `${row.height}px`;
        stage.appendChild(label);
    });

    const grid = document.createElement("div");
    grid.className = "layout-designer-grid";
    grid.style.width = `${metrics.width}px`;
    grid.style.height = `${metrics.height}px`;
    if (preview.enabled && preview.image_path) {
        const imageUrl = preview.image_path.startsWith("/")
            ? preview.image_path
            : `/${preview.image_path}`;
        grid.style.backgroundImage = `url("${imageUrl}")`;
        grid.style.backgroundSize = "contain";
        grid.style.backgroundRepeat = "no-repeat";
        grid.style.backgroundPosition = "top left";
    }

    metrics.columnBoundaries.forEach(boundary => {
        const line = document.createElement("div");
        line.className = "layout-designer-grid-line vertical";
        line.style.left = `${boundary}px`;
        grid.appendChild(line);
    });
    metrics.rowBoundaries.forEach(boundary => {
        const line = document.createElement("div");
        line.className = "layout-designer-grid-line horizontal";
        line.style.top = `${boundary}px`;
        grid.appendChild(line);
    });
    if (hasCurrentGeometry() && Array.isArray(state.geometry.merged_cells)) {
        state.geometry.merged_cells.forEach(item => {
            const mergedRect = rangeToRect(item.range);
            if (!mergedRect) {
                return;
            }
            const merged = document.createElement("div");
            merged.className = "layout-designer-merged-cell";
            merged.title = item.range;
            merged.style.left = `${mergedRect.x}px`;
            merged.style.top = `${mergedRect.y}px`;
            merged.style.width = `${mergedRect.width}px`;
            merged.style.height = `${mergedRect.height}px`;
            grid.appendChild(merged);
        });
    }
    stage.appendChild(grid);

    (regions || []).forEach((region, index) => {
        const rect = rangeToRect(region.range) || defaultLayoutDesignerRect(index);
        const regionId = getLayoutRegionId(region, index);
        const box = document.createElement("div");
        box.className = "layout-designer-region" + (regionId === state.selectedRegionId ? " selected" : "");
        box.dataset.regionIndex = String(index);
        box.dataset.regionId = regionId;
        box.style.left = `${LAYOUT_DESIGNER_ROW_LABEL_WIDTH + rect.x}px`;
        box.style.top = `${LAYOUT_DESIGNER_COL_LABEL_HEIGHT + rect.y}px`;
        box.style.width = `${rect.width}px`;
        box.style.height = `${rect.height}px`;
        const blocks = Array.isArray(region.blocks) ? region.blocks : [];
        box.innerHTML = `
            <div class="layout-designer-region-title">${escapeHtml(region.name || region.id || "Region")}</div>
            <div class="layout-designer-region-meta">${escapeHtml(region.range || rectToRange(rect.x, rect.y, rect.width, rect.height))}</div>
            <div class="region-preview">${renderRegionBlockPreview(region)}</div>
            <div class="layout-designer-region-meta">Blocks: ${blocks.length}</div>
            <div class="layout-designer-resize"></div>
        `;
        box.addEventListener("mousedown", event => startLayoutDesignerDrag(event, index, "move"));
        box.addEventListener("click", event => {
            event.stopPropagation();
            selectLayoutDesignerRegion(index);
        });
        const handle = box.querySelector(".layout-designer-resize");
        if (handle) {
            handle.addEventListener("mousedown", event => startLayoutDesignerDrag(event, index, "resize"));
        }
        stage.appendChild(box);
    });

    container.innerHTML = "";
    container.appendChild(stage);
    if ((regions || []).length > 0) {
        ensureSelectedLayoutRegion(regions);
        highlightLayoutDesignerRegion();
        highlightLayoutRegionForm();
    }
}



function startLayoutDesignerDrag(event, index, mode) {
    event.preventDefault();
    event.stopPropagation();
    selectLayoutDesignerRegion(index, false);
    const box = event.currentTarget.classList.contains("layout-designer-region")
        ? event.currentTarget
        : event.currentTarget.closest(".layout-designer-region");
    const rect = rangeToRect(getLayoutConfig().regions?.[index]?.range)
        || defaultLayoutDesignerRect(index);
    state.activeDrag = {
        index,
        mode,
        startX: event.clientX,
        startY: event.clientY,
        rect,
        box
    };
    document.addEventListener("mousemove", onLayoutDesignerDragMove);
    document.addEventListener("mouseup", endLayoutDesignerDrag);
}



function onLayoutDesignerDragMove(event) {
    if (!state.activeDrag) {
        return;
    }
    const drag = state.activeDrag;
    const deltaX = event.clientX - drag.startX;
    const deltaY = event.clientY - drag.startY;
    let nextX = drag.rect.x;
    let nextY = drag.rect.y;
    let nextWidth = drag.rect.width;
    let nextHeight = drag.rect.height;

    if (drag.mode === "resize") {
        nextWidth = drag.rect.width + deltaX;
        nextHeight = drag.rect.height + deltaY;
    } else {
        nextX = drag.rect.x + deltaX;
        nextY = drag.rect.y + deltaY;
    }

    const range = rectToRange(nextX, nextY, nextWidth, nextHeight);
    const rect = rangeToRect(range);
    if (!rect || !drag.box) {
        return;
    }
    drag.box.style.left = `${LAYOUT_DESIGNER_ROW_LABEL_WIDTH + rect.x}px`;
    drag.box.style.top = `${LAYOUT_DESIGNER_COL_LABEL_HEIGHT + rect.y}px`;
    drag.box.style.width = `${rect.width}px`;
    drag.box.style.height = `${rect.height}px`;
    const meta = drag.box.querySelector(".layout-designer-region-meta");
    if (meta) {
        meta.textContent = range;
    }
    syncLayoutDesignerRangeInput(drag.index, range);
}



function endLayoutDesignerDrag() {
    if (!state.activeDrag) {
        return;
    }
    const index = state.activeDrag.index;
    state.activeDrag = null;
    document.removeEventListener("mousemove", onLayoutDesignerDragMove);
    document.removeEventListener("mouseup", endLayoutDesignerDrag);
    syncLayoutDesignerFromRegionInput(index, false);
    renderLayoutConfig();
}



function renderLayoutConfig() {
    const area = document.getElementById("layoutConfigArea");
    const resultDiv = document.getElementById("layoutConfigResult");
    if (!area) {
        return;
    }
    if (resultDiv) {
        resultDiv.innerHTML = "";
    }

    if (!state.currentProfile) {
        area.innerHTML = `<div class="empty-form">请先选择模板映射</div>`;
        return;
    }

    if (!state.layoutConfig) {
        setLayoutConfig(state.currentProfile.layout_config || defaultLayoutConfig(), { dirty: false, render: false });
    }
    const config = getLayoutConfig();
    syncCurrentProfileLayoutConfig();
    ensureSelectedLayoutRegion(config.regions);
    state.currentProfile.layout_preview = normalizeLayoutPreview(state.currentProfile.layout_preview || defaultLayoutPreview());
    const preview = state.currentProfile.layout_preview;
    const previewSrc = preview.image_path
        ? (preview.image_path.startsWith("/") ? preview.image_path : `/${preview.image_path}`)
        : "";
    const geometryNotice = hasCurrentGeometry()
        ? `已读取真实 Excel 几何：${escapeHtml(state.geometry.sheet_name || "Active Sheet")}，${state.geometry.max_column || state.geometry.columns.length} 列 × ${state.geometry.max_row || state.geometry.rows.length} 行`
        : escapeHtml(state.geometryError || "未读取到真实 Excel 几何，当前使用简化网格。");

    area.innerHTML = `
        <div id="layoutDirtyStatus" class="layout-save-status ${state.dirty ? "dirty" : "saved"}">${state.dirty ? "Layout 有未保存修改" : "Layout 已保存"}</div>
        <label class="checkbox-line">
            <input type="checkbox" id="layout_enabled" ${config.enabled ? "checked" : ""} onchange="refreshLayoutConfigDraft()">
            <span>启用 Layout Engine</span>
        </label>
        <div class="button-row">
            <button type="button" onclick="addLayoutRegion()">新增区域</button>
            <button type="button" class="save" onclick="saveLayoutConfig()">保存 Layout 配置</button>
        </div>
        <div class="layout-background-panel">
            <h3>Template Background（实验）</h3>
            <p class="tips">上传模板截图后，可作为 Layout Designer 背景参考；Region 仍按简化 Excel 网格换算区域。</p>
            <label class="checkbox-line">
                <input type="checkbox" id="layout_preview_enabled" ${preview.enabled ? "checked" : ""} onchange="toggleLayoutPreviewEnabled()">
                <span>启用背景图</span>
            </label>
            <div class="layout-background-row">
                <input id="layoutPreviewInput" type="file" accept=".png,.jpg,.jpeg,image/png,image/jpeg">
                <button type="button" onclick="uploadLayoutPreview()">上传背景图</button>
                <button class="delete" type="button" onclick="clearLayoutPreview()">清除背景图</button>
                <span class="tips">${preview.image_path ? `${preview.image_width || 0} × ${preview.image_height || 0}` : "当前未上传背景图"}</span>
            </div>
            ${previewSrc ? `<img class="layout-background-preview" src="${escapeHtml(previewSrc)}" alt="Layout preview">` : ""}
        </div>
        <div class="layout-designer-workspace">
            <div class="layout-designer-main">
                <div class="layout-designer-section">
                    <h3>Layout Designer（实验）</h3>
                    <p class="tips">当前为简化版 Excel 区域设计器，用于快速调整 Region 的大致位置和大小。保存后会同步到 Excel区域。</p>
                    <p class="tips">${geometryNotice}</p>
                    <div id="layoutDesignerCanvas" class="layout-designer"></div>
                </div>
            </div>
            <div id="regionInspector" class="region-inspector"></div>
        </div>
        <div class="layout-advanced-toggle-row">
            <button id="layoutAdvancedToggle" type="button" class="gray" onclick="toggleLayoutAdvancedPanel()">${state.advancedVisible ? "隐藏高级配置" : "显示高级配置"}</button>
        </div>
        <div class="layout-advanced-panel ${state.advancedVisible ? "open" : ""}" id="layoutAdvancedPanel">
            <p class="layout-advanced-tip">高级配置用于直接编辑 Layout 原始结构。一般情况下请优先使用上方 Designer 和右侧 Inspector。</p>
            <div id="layoutRegionList"></div>
        </div>
    `;

    renderLayoutRegions(config.regions);
    renderLayoutDesigner(config.regions);
    renderRegionInspector();
    renderLayoutAdvancedPanelState();
}



function renderLayoutRegions(regions) {
    const list = document.getElementById("layoutRegionList");
    if (!list) {
        return;
    }

    if (!regions || regions.length === 0) {
        list.innerHTML = `<div class="empty-form">暂无 Layout Region，请点击“新增区域”。</div>`;
        return;
    }

    list.oninput = event => {
        if (event.target.closest(".layout-block-row")) {
            syncLayoutFormDraftFromLower();
        }
    };
    list.onchange = event => {
        if (event.target.closest(".layout-block-row")) {
            syncLayoutFormDraftFromLower();
        }
    };
    list.innerHTML = "";
    regions.forEach((region, index) => {
        const regionId = getLayoutRegionId(region, index);
        const card = document.createElement("div");
        card.className = "layout-region-card" + (regionId === state.selectedRegionId ? " selected" : "");
        card.dataset.regionIndex = String(index);
        card.dataset.regionId = regionId;
        card.addEventListener("click", () => selectLayoutDesignerRegion(index, false));
        const blocks = Array.isArray(region.blocks) ? region.blocks : [];
        card.innerHTML = `
            <div class="layout-region-header">
                <div>
                    <label>区域ID</label>
                    <input id="layout_region_id_${index}" value="${escapeHtml(region.id || "")}" placeholder="main_description" oninput="syncLayoutDesignerFromRegionInput(${index})">
                </div>
                <div>
                    <label>区域名称</label>
                    <input id="layout_region_name_${index}" value="${escapeHtml(region.name || "")}" placeholder="主产品描述区域" oninput="syncLayoutDesignerFromRegionInput(${index})">
                </div>
                <div>
                    <label>区域类型</label>
                    <input id="layout_region_type_${index}" value="${escapeHtml(region.type || "")}" placeholder="rich_text" oninput="syncLayoutDesignerFromRegionInput(${index})">
                </div>
                <div>
                    <label>工作表</label>
                    <input id="layout_region_sheet_${index}" value="${escapeHtml(region.sheet || "active")}" placeholder="active">
                </div>
                <div>
                    <label>Excel区域</label>
                    <input id="layout_region_range_${index}" value="${escapeHtml(region.range || "")}" placeholder="A10:H20" oninput="syncLayoutDesignerFromRegionInput(${index})">
                </div>
                <div class="layout-count">Block数量：${blocks.length}</div>
                <label class="checkbox-line">
                    <input type="checkbox" id="layout_region_enabled_${index}" ${region.enabled !== false ? "checked" : ""} onchange="syncLayoutDesignerFromRegionInput(${index})">
                    <span>启用</span>
                </label>
                <button class="delete" type="button" onclick="deleteLayoutRegion(${index})">删除区域</button>
            </div>
            <div class="layout-blocks-title">Blocks</div>
            <div id="layout_blocks_${index}"></div>
            <div class="button-row">
                <button type="button" onclick="addLayoutBlock(${index}, 'description_fields')">新增描述 Block</button>
                <button type="button" onclick="addLayoutBlock(${index}, 'image')">新增 Image Block</button>
                <button type="button" onclick="addLayoutBlock(${index}, 'image_gallery')">新增 Gallery Block</button>
                <button type="button" onclick="addLayoutBlock(${index}, 'image_stack')">新增 Stack Block</button>
            </div>
        `;
        list.appendChild(card);
        renderLayoutBlocks(index, blocks);
    });
}



function renderLayoutBlocks(regionIndex, blocks) {
    const container = document.getElementById("layout_blocks_" + regionIndex);
    if (!container) {
        return;
    }

    if (!blocks || blocks.length === 0) {
        container.innerHTML = `<div class="tips">暂无 Block。</div>`;
        return;
    }

    container.innerHTML = "";
    blocks.forEach((block, blockIndex) => {
        const row = document.createElement("div");
        row.className = "layout-block-row";
        row.dataset.blockIndex = String(blockIndex);
        const type = String(block.type || "description_fields").trim() || "description_fields";
        const options = normalizeLayoutBlockOptions(type, block.options || {});
        const isImage = type === "image";
        const isGallery = type === "image_gallery";
        const isStack = type === "image_stack";
        const hasSourceKeys = isGallery || isStack;
        const autoSourceValue = hasSourceKeys ? options.auto_source === true : false;
        const useImagePoolValue = hasSourceKeys ? options.use_image_pool === true : false;
        const excludeKeysValue = hasSourceKeys ? (options.exclude_keys || []).join(",") : "";
        const maxImagesValue = hasSourceKeys ? options.max_images : "";
        const sourcePlaceholder = isImage ? "front_label" : (hasSourceKeys ? "image_data" : "description_fields");
        const sizeOptionsDisabled = isImage || isGallery || isStack ? "" : "disabled";
        const widthValue = isImage ? options.width : (hasSourceKeys ? options.image_width : "");
        const heightValue = isImage ? options.height : (hasSourceKeys ? options.image_height : "");
        const stepLabel = isStack ? "Gap Rows" : "Row Step";
        const stepValue = isGallery ? options.row_step : (isStack ? options.gap_rows : "");
        const stepEnabled = isGallery || isStack;
        const layoutModeValue = isStack ? (options.layout_mode || "auto_stack") : "";
        const anchorCellValue = isStack ? (options.anchor_cell || "") : "";
        const gapPxValue = isStack ? options.gap_px : "";
        row.innerHTML = `
            <div>
                <label>Block ID</label>
                <input id="layout_block_id_${regionIndex}_${blockIndex}" value="${escapeHtml(block.id || "")}" placeholder="description">
            </div>
            <div>
                <label>Block Type</label>
                <select id="layout_block_type_${regionIndex}_${blockIndex}" onchange="refreshLayoutConfigDraft()">
                    <option value="description_fields" ${type === "description_fields" ? "selected" : ""}>description_fields</option>
                    <option value="image" ${type === "image" ? "selected" : ""}>image</option>
                    <option value="image_gallery" ${type === "image_gallery" ? "selected" : ""}>image_gallery</option>
                    <option value="image_stack" ${type === "image_stack" ? "selected" : ""}>image_stack</option>
                </select>
            </div>
            <div>
                <label>Source</label>
                <input id="layout_block_source_${regionIndex}_${blockIndex}" value="${escapeHtml(block.source || "")}" placeholder="${escapeHtml(sourcePlaceholder)}">
            </div>
            <div>
                <label>Source Keys</label>
                <input id="layout_block_source_keys_${regionIndex}_${blockIndex}" value="${hasSourceKeys ? escapeHtml((options.source_keys || []).join(",")) : ""}" placeholder="${autoSourceValue ? "auto_source 开启时，source_keys 不生效" : "front_label,back_label,product_image"}" ${hasSourceKeys ? "" : "disabled"}>
            </div>
            <label class="checkbox-line">
                <input type="checkbox" id="layout_block_auto_source_${regionIndex}_${blockIndex}" ${autoSourceValue ? "checked" : ""} ${hasSourceKeys ? "" : "disabled"}>
                <span>自动使用当前订单上传的所有图片</span>
            </label>
            <label class="checkbox-line">
                <input type="checkbox" id="layout_block_use_image_pool_${regionIndex}_${blockIndex}" ${useImagePoolValue ? "checked" : ""} ${hasSourceKeys ? "" : "disabled"}>
                <span>使用首页图片素材池</span>
            </label>
            <div>
                <label>Exclude Keys</label>
                <input id="layout_block_exclude_keys_${regionIndex}_${blockIndex}" value="${escapeHtml(excludeKeysValue)}" placeholder="logo_image,qr_code" ${hasSourceKeys ? "" : "disabled"}>
            </div>
            <div>
                <label>Max Images</label>
                <input id="layout_block_max_images_${regionIndex}_${blockIndex}" type="number" min="0" value="${escapeHtml(maxImagesValue)}" placeholder="0=不限制" ${hasSourceKeys ? "" : "disabled"}>
            </div>
            <div>
                <label>Layout Mode</label>
                <select id="layout_block_layout_mode_${regionIndex}_${blockIndex}" ${isStack ? "" : "disabled"}>
                    <option value="row_step" ${layoutModeValue === "row_step" ? "selected" : ""}>row_step</option>
                    <option value="auto_stack" ${layoutModeValue === "auto_stack" ? "selected" : ""}>auto_stack</option>
                </select>
            </div>
            <div>
                <label>Anchor Cell</label>
                <input id="layout_block_anchor_cell_${regionIndex}_${blockIndex}" value="${escapeHtml(anchorCellValue)}" placeholder="G7" ${isStack ? "" : "disabled"}>
            </div>
            <div>
                <label>Width</label>
                <input id="layout_block_width_${regionIndex}_${blockIndex}" type="number" min="1" value="${escapeHtml(widthValue)}" placeholder="${isGallery ? "180" : "220"}" ${sizeOptionsDisabled}>
            </div>
            <div>
                <label>Height</label>
                <input id="layout_block_height_${regionIndex}_${blockIndex}" type="number" min="1" value="${escapeHtml(heightValue)}" placeholder="${isStack ? "120" : (isGallery ? "140" : "160")}" ${sizeOptionsDisabled}>
            </div>
            <div>
                <label>Columns</label>
                <input id="layout_block_columns_${regionIndex}_${blockIndex}" type="number" min="1" value="${isGallery ? escapeHtml(options.columns) : ""}" placeholder="3" ${isGallery ? "" : "disabled"}>
            </div>
            <div>
                <label>${stepLabel}</label>
                <input id="layout_block_row_step_${regionIndex}_${blockIndex}" type="number" min="1" value="${stepEnabled ? escapeHtml(stepValue) : ""}" placeholder="8" ${stepEnabled ? "" : "disabled"}>
            </div>
            <div>
                <label>Col Step</label>
                <input id="layout_block_col_step_${regionIndex}_${blockIndex}" type="number" min="1" value="${isGallery ? escapeHtml(options.col_step) : ""}" placeholder="4" ${isGallery ? "" : "disabled"}>
            </div>
            <div>
                <label>Gap PX</label>
                <input id="layout_block_gap_px_${regionIndex}_${blockIndex}" type="number" min="0" value="${isStack ? escapeHtml(gapPxValue) : ""}" placeholder="12" ${isStack ? "" : "disabled"}>
            </div>
            <label class="checkbox-line">
                <input type="checkbox" id="layout_block_keep_ratio_${regionIndex}_${blockIndex}" ${options.keep_ratio !== false ? "checked" : ""} ${sizeOptionsDisabled}>
                <span>等比</span>
            </label>
            <label class="checkbox-line">
                <input type="checkbox" id="layout_block_enabled_${regionIndex}_${blockIndex}" ${block.enabled !== false ? "checked" : ""}>
                <span>启用</span>
            </label>
            <button class="delete" type="button" onclick="deleteLayoutBlock(${regionIndex}, ${blockIndex})">删除</button>
        `;
        container.appendChild(row);
    });
}



function collectLayoutConfig() {
    const enabled = document.getElementById("layout_enabled");
    const regionCards = Array.from(document.querySelectorAll(".layout-region-card"));
    if (!regionCards.length) {
        const current = getLayoutConfig();
        return normalizeLayoutConfig({
            ...current,
            enabled: enabled ? enabled.checked : current.enabled
        });
    }
    const regions = regionCards.map(card => {
        const regionIndex = card.dataset.regionIndex;
        const blocks = Array.from(card.querySelectorAll(".layout-block-row")).map(row => {
            const blockIndex = row.dataset.blockIndex;
            const type = (document.getElementById(`layout_block_type_${regionIndex}_${blockIndex}`)?.value || "description_fields").trim();
            let options = {};
            if (type === "image") {
                options = {
                    width: parseLayoutNumber(document.getElementById(`layout_block_width_${regionIndex}_${blockIndex}`)?.value, 220),
                    height: parseLayoutNumber(document.getElementById(`layout_block_height_${regionIndex}_${blockIndex}`)?.value, 160),
                    keep_ratio: Boolean(document.getElementById(`layout_block_keep_ratio_${regionIndex}_${blockIndex}`)?.checked)
                };
            } else if (type === "image_gallery") {
                options = {
                    source_keys: parseLayoutSourceKeys(document.getElementById(`layout_block_source_keys_${regionIndex}_${blockIndex}`)?.value),
                    auto_source: Boolean(document.getElementById(`layout_block_auto_source_${regionIndex}_${blockIndex}`)?.checked),
                    use_image_pool: Boolean(document.getElementById(`layout_block_use_image_pool_${regionIndex}_${blockIndex}`)?.checked),
                    exclude_keys: parseLayoutSourceKeys(document.getElementById(`layout_block_exclude_keys_${regionIndex}_${blockIndex}`)?.value),
                    max_images: parseLayoutNonNegativeNumber(document.getElementById(`layout_block_max_images_${regionIndex}_${blockIndex}`)?.value, 0),
                    columns: parseLayoutNumber(document.getElementById(`layout_block_columns_${regionIndex}_${blockIndex}`)?.value, 3),
                    image_width: parseLayoutNumber(document.getElementById(`layout_block_width_${regionIndex}_${blockIndex}`)?.value, 180),
                    image_height: parseLayoutNumber(document.getElementById(`layout_block_height_${regionIndex}_${blockIndex}`)?.value, 140),
                    keep_ratio: Boolean(document.getElementById(`layout_block_keep_ratio_${regionIndex}_${blockIndex}`)?.checked),
                    row_step: parseLayoutNumber(document.getElementById(`layout_block_row_step_${regionIndex}_${blockIndex}`)?.value, 8),
                    col_step: parseLayoutNumber(document.getElementById(`layout_block_col_step_${regionIndex}_${blockIndex}`)?.value, 4)
                };
            } else if (type === "image_stack") {
                options = {
                    source_keys: parseLayoutSourceKeys(document.getElementById(`layout_block_source_keys_${regionIndex}_${blockIndex}`)?.value),
                    auto_source: Boolean(document.getElementById(`layout_block_auto_source_${regionIndex}_${blockIndex}`)?.checked),
                    use_image_pool: Boolean(document.getElementById(`layout_block_use_image_pool_${regionIndex}_${blockIndex}`)?.checked),
                    exclude_keys: parseLayoutSourceKeys(document.getElementById(`layout_block_exclude_keys_${regionIndex}_${blockIndex}`)?.value),
                    max_images: parseLayoutNonNegativeNumber(document.getElementById(`layout_block_max_images_${regionIndex}_${blockIndex}`)?.value, 0),
                    layout_mode: (document.getElementById(`layout_block_layout_mode_${regionIndex}_${blockIndex}`)?.value || "auto_stack").trim() || "auto_stack",
                    anchor_cell: (document.getElementById(`layout_block_anchor_cell_${regionIndex}_${blockIndex}`)?.value || "").trim().toUpperCase(),
                    image_width: parseLayoutNumber(document.getElementById(`layout_block_width_${regionIndex}_${blockIndex}`)?.value, 220),
                    image_height: parseLayoutNumber(document.getElementById(`layout_block_height_${regionIndex}_${blockIndex}`)?.value, 120),
                    keep_ratio: Boolean(document.getElementById(`layout_block_keep_ratio_${regionIndex}_${blockIndex}`)?.checked),
                    gap_rows: parseLayoutNumber(document.getElementById(`layout_block_row_step_${regionIndex}_${blockIndex}`)?.value, 8),
                    gap_px: parseLayoutNumber(document.getElementById(`layout_block_gap_px_${regionIndex}_${blockIndex}`)?.value, 12)
                };
            }
            return {
                id: (document.getElementById(`layout_block_id_${regionIndex}_${blockIndex}`)?.value || "").trim(),
                type: type,
                source: (document.getElementById(`layout_block_source_${regionIndex}_${blockIndex}`)?.value || "").trim(),
                enabled: Boolean(document.getElementById(`layout_block_enabled_${regionIndex}_${blockIndex}`)?.checked),
                options: options
            };
        });

        return {
            id: (document.getElementById("layout_region_id_" + regionIndex)?.value || "").trim(),
            name: (document.getElementById("layout_region_name_" + regionIndex)?.value || "").trim(),
            type: (document.getElementById("layout_region_type_" + regionIndex)?.value || "").trim(),
            enabled: Boolean(document.getElementById("layout_region_enabled_" + regionIndex)?.checked ?? true),
            sheet: (document.getElementById("layout_region_sheet_" + regionIndex)?.value || "active").trim() || "active",
            range: (document.getElementById("layout_region_range_" + regionIndex)?.value || "").trim().toUpperCase(),
            blocks: blocks,
            options: {}
        };
    });

    return {
        enabled: enabled ? enabled.checked : false,
        regions: regions
    };
}



function collectLayoutPreview() {
    const current = normalizeLayoutPreview(state.currentProfile?.layout_preview || defaultLayoutPreview());
    const enabledInput = document.getElementById("layout_preview_enabled");
    return normalizeLayoutPreview({
        ...current,
        enabled: enabledInput ? enabledInput.checked : current.enabled
    });
}



function getSelectedLayoutRegion() {
    const index = findLayoutRegionIndexById(state.selectedRegionId);
    if (index < 0) {
        return { index: -1, region: null };
    }
    return {
        index,
        region: getLayoutConfig().regions[index]
    };
}



function syncLayoutFormDraftFromLower() {
    if (!state.currentProfile) {
        return;
    }
    const config = setLayoutConfig(collectLayoutConfig(), { render: false });
    ensureSelectedLayoutRegion(config.regions);
    renderLayoutDesigner(config.regions);
    renderRegionInspector();
}



function syncCurrentProfileFromResult(profile) {
    if (!profile || !profile.id) {
        return;
    }
    state.currentProfile = profile;
    state.layoutConfig = normalizeLayoutConfig(profile.layout_config || defaultLayoutConfig());
    state.selectedBlockId = null;
    try {
        currentProfile = profile;
    } catch (error) {
        // config.html owns the legacy currentProfile binding.
    }
    try {
        profiles = profiles.map(item => item.id === profile.id ? profile : item);
    } catch (error) {
        // Profile list is only present after config.html initialization.
    }
}



function refreshLayoutConfigDraft() {
    if (!state.currentProfile) {
        return;
    }
    setLayoutConfig(collectLayoutConfig(), { render: false });
    renderLayoutConfig();
}



function toggleLayoutPreviewEnabled() {
    if (!state.currentProfile) {
        return;
    }
    state.currentProfile.layout_preview = collectLayoutPreview();
    markLayoutDirty();
    renderLayoutDesigner(getLayoutConfig().regions || []);
}



async function uploadLayoutPreview() {
    const resultDiv = document.getElementById("layoutConfigResult");
    const input = document.getElementById("layoutPreviewInput");
    if (!state.currentProfile) {
        return;
    }
    if (!input || !input.files || !input.files.length) {
        if (resultDiv) {
            resultDiv.innerHTML = `<p class="error">请先选择背景图</p>`;
        }
        return;
    }

    const formData = new FormData();
    formData.append("file", input.files[0]);
    const response = await fetch(`/api/template-profiles/${state.currentProfile.id}/layout-preview`, {
        method: "POST",
        body: formData
    });
    const result = await response.json();
    if (!result.success) {
        if (resultDiv) {
            resultDiv.innerHTML = `<p class="error">${escapeHtml(result.error || "背景图上传失败")}</p>`;
        }
        return;
    }

    syncCurrentProfileFromResult(result.profile);
    markLayoutSaved();
    renderLayoutConfig();
    if (resultDiv) {
        resultDiv.innerHTML = `<p class="success">背景图已上传</p>`;
    }
}



function clearLayoutPreview() {
    if (!state.currentProfile) {
        return;
    }
    state.currentProfile.layout_preview = defaultLayoutPreview();
    markLayoutDirty();
    renderLayoutConfig();
}



function addLayoutRegion() {
    if (!state.currentProfile) {
        return;
    }
    const config = getLayoutConfig();
    const ts = Date.now();
    config.regions.push({
        id: `region_${ts}`,
        name: "新区域",
        type: "rich_text",
        enabled: true,
        sheet: "active",
        range: "",
        blocks: [],
        options: {}
    });
    setLayoutConfig(config, { render: false });
    renderLayoutConfig();
}



function deleteLayoutRegion(index, options = {}) {
    if (!state.currentProfile) {
        return;
    }
    const config = getLayoutConfig();
    const region = config.regions[index];
    if (!options.skipConfirm && region && !confirm(`确定删除 Region：${region.name || region.id || region.range || index + 1} 吗？`)) {
        return;
    }
    config.regions.splice(index, 1);
    state.selectedRegionId = null;
    state.selectedBlockId = null;
    setLayoutConfig(config, { render: false });
    renderLayoutConfig();
}

function addLayoutBlock(regionIndex, blockType) {
    if (!state.currentProfile) {
        return;
    }
    const config = getLayoutConfig();
    if (!config.regions[regionIndex]) {
        return;
    }
    const ts = Date.now();
    const type = ["image", "image_gallery", "image_stack"].includes(blockType)
        ? blockType
        : "description_fields";
    config.regions[regionIndex].blocks.push({
        id: `block_${ts}`,
        type: type,
        source: type === "image" ? "" : (["image_gallery", "image_stack"].includes(type) ? "image_data" : "description_fields"),
        enabled: true,
        options: type === "image"
            ? {
                width: 220,
                height: 160,
                keep_ratio: true
            }
            : type === "image_gallery"
                ? {
                    source_keys: [],
                    auto_source: false,
                    use_image_pool: false,
                    exclude_keys: [],
                    max_images: 0,
                    columns: 3,
                    image_width: 180,
                    image_height: 140,
                    keep_ratio: true,
                    row_step: 8,
                    col_step: 4
                }
                : type === "image_stack"
                    ? {
                        source_keys: [],
                        auto_source: false,
                        use_image_pool: false,
                        exclude_keys: [],
                        max_images: 0,
                        layout_mode: "auto_stack",
                        anchor_cell: "",
                        image_width: 220,
                        image_height: 120,
                        keep_ratio: true,
                        gap_rows: 8,
                        gap_px: 12
                    }
            : {}
    });
    setLayoutConfig(config, { render: false });
    renderLayoutConfig();
}



function deleteLayoutBlock(regionIndex, blockIndex) {
    if (!state.currentProfile) {
        return;
    }
    const config = getLayoutConfig();
    if (!config.regions[regionIndex]) {
        return;
    }
    const block = config.regions[regionIndex].blocks[blockIndex];
    if (block && getLayoutBlockId(block, blockIndex) === state.selectedBlockId) {
        state.selectedBlockId = null;
    }
    config.regions[regionIndex].blocks.splice(blockIndex, 1);
    setLayoutConfig(config, { render: false });
    renderLayoutConfig();
}



async function saveLayoutConfig() {
    const resultDiv = document.getElementById("layoutConfigResult");
    if (!state.currentProfile) {
        if (resultDiv) {
            resultDiv.innerHTML = `<p class="error">请先选择模板映射</p>`;
        }
        return;
    }

    setLayoutConfig(collectLayoutConfig(), { render: false });
    const layoutConfig = getLayoutConfig();
    const layoutPreview = collectLayoutPreview();
    const response = await fetch(`/api/template-profiles/${state.currentProfile.id}/layout-config`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            layout_config: layoutConfig,
            layout_preview: layoutPreview
        })
    });
    const result = await response.json();

    if (!result.success) {
        if (resultDiv) {
            resultDiv.innerHTML = `<p class="error">${escapeHtml(result.error || "Layout配置保存失败")}</p>`;
        }
        return;
    }

    syncCurrentProfileFromResult(result.profile);
    setLayoutConfig(result.profile.layout_config || defaultLayoutConfig(), { dirty: false, render: false });
    markLayoutSaved();
    renderLayoutConfig();
    if (resultDiv) {
        resultDiv.innerHTML = `<p class="success">Layout配置已保存</p>`;
    }
}



Object.assign(window, {
    getLayoutEditorState,
    setLayoutConfig,
    getLayoutConfig,
    setSelectedRegion,
    getSelectedRegion,
    setSelectedBlock,
    markLayoutDirty,
    markLayoutSaved,
    syncCurrentProfileLayoutConfig,
    defaultLayoutConfig,
    defaultLayoutPreview,
    normalizeLayoutPreview,
    normalizeLayoutConfig,
    getLayoutRegionId,
    getLayoutBlockId,
    findLayoutRegionIndexById,
    ensureSelectedLayoutRegion,
    highlightLayoutDesignerRegion,
    renderLayoutAdvancedPanelState,
    toggleLayoutAdvancedPanel,
    syncLayoutDesignerRangeInput,
    syncLayoutDesignerFromRegionInput,
    highlightLayoutRegionForm,
    selectLayoutDesignerRegion,
    renderLayoutDesigner,
    startLayoutDesignerDrag,
    onLayoutDesignerDragMove,
    endLayoutDesignerDrag,
    renderLayoutConfig,
    renderLayoutRegions,
    renderLayoutBlocks,
    collectLayoutConfig,
    collectLayoutPreview,
    getSelectedLayoutRegion,
    syncLayoutFormDraftFromLower,
    syncCurrentProfileFromResult,
    refreshLayoutConfigDraft,
    toggleLayoutPreviewEnabled,
    uploadLayoutPreview,
    clearLayoutPreview,
    addLayoutRegion,
    deleteLayoutRegion,
    addLayoutBlock,
    deleteLayoutBlock,
    saveLayoutConfig
});
})();
