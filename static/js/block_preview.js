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

function parseLayoutNumber(value, fallback) {
    const text = String(value ?? "").trim();
    if (!text) {
        return fallback;
    }
    const number = Number(text);
    return Number.isFinite(number) && number > 0 ? number : fallback;
}



function parseLayoutNonNegativeNumber(value, fallback = 0) {
    const text = String(value ?? "").trim();
    if (!text) {
        return fallback;
    }
    const number = Number(text);
    return Number.isFinite(number) && number >= 0 ? number : fallback;
}



function parseLayoutSourceKeys(value) {
    if (Array.isArray(value)) {
        return value.map(item => String(item || "").trim()).filter(Boolean);
    }
    return String(value || "")
        .split(",")
        .map(item => item.trim())
        .filter(Boolean);
}



function parseSourceKeys(value) {
    return parseLayoutSourceKeys(value);
}



function normalizeLayoutBlockOptions(type, options) {
    const source = options && typeof options === "object" && !Array.isArray(options) ? options : {};
    if (type === "image") {
        return {
            width: parseLayoutNumber(source.width, 220),
            height: parseLayoutNumber(source.height, 160),
            keep_ratio: source.keep_ratio !== false
        };
    }
    if (type === "image_gallery") {
        return {
            source_keys: parseLayoutSourceKeys(source.source_keys),
            auto_source: source.auto_source === true,
            use_image_pool: source.use_image_pool === true,
            exclude_keys: parseLayoutSourceKeys(source.exclude_keys),
            max_images: parseLayoutNonNegativeNumber(source.max_images, 0),
            columns: parseLayoutNumber(source.columns, 3),
            image_width: parseLayoutNumber(source.image_width, 180),
            image_height: parseLayoutNumber(source.image_height, 140),
            keep_ratio: source.keep_ratio !== false,
            row_step: parseLayoutNumber(source.row_step, 8),
            col_step: parseLayoutNumber(source.col_step, 4)
        };
    }
    if (type === "image_stack") {
        return {
            source_keys: parseLayoutSourceKeys(source.source_keys),
            auto_source: source.auto_source === true,
            use_image_pool: source.use_image_pool === true,
            exclude_keys: parseLayoutSourceKeys(source.exclude_keys),
            max_images: parseLayoutNonNegativeNumber(source.max_images, 0),
            layout_mode: String(source.layout_mode || "auto_stack").trim() || "auto_stack",
            anchor_cell: String(source.anchor_cell || "").trim().toUpperCase(),
            image_width: parseLayoutNumber(source.image_width, 220),
            image_height: parseLayoutNumber(source.image_height, 120),
            keep_ratio: source.keep_ratio !== false,
            gap_rows: parseLayoutNumber(source.gap_rows, 8),
            gap_px: parseLayoutNumber(source.gap_px, 12)
        };
    }
    return source;
}



function renderBlockPreview(block) {
    const type = String(block && block.type || "description_fields").trim() || "description_fields";
    const options = normalizeLayoutBlockOptions(type, block?.options || {});

    if (type === "description_fields") {
        return `
            <div class="block-preview">
                <div class="preview-label">文本描述预览</div>
                <div class="preview-text-block">产品描述
配方要求
包装方式
颜色/口味</div>
            </div>
        `;
    }

    if (type === "image_stack") {
        const keys = parseSourceKeys(options.source_keys);
        const count = (options.use_image_pool || options.auto_source) ? 4 : Math.min(3, Math.max(1, keys.length || 3));
        const boxes = Array.from({ length: count }, (_, index) => `
            <div class="preview-image-box">图片 ${index + 1}</div>
        `).join("");
        return `
            <div class="block-preview">
                <div class="preview-label">${options.use_image_pool ? "图片素材池" : (options.auto_source ? "自动图片区域" : "纵向图片堆叠")}</div>
                <div class="preview-image-stack">${boxes}</div>
            </div>
        `;
    }

    if (type === "image_gallery") {
        const keys = parseSourceKeys(options.source_keys);
        const count = (options.use_image_pool || options.auto_source) ? 4 : Math.min(9, Math.max(1, keys.length || 6));
        const columns = Math.min(6, Math.max(1, Math.round(Number(options.columns) || 3)));
        const boxes = Array.from({ length: count }, () => `<div class="preview-image-box">图</div>`).join("");
        return `
            <div class="block-preview">
                <div class="preview-label">${options.use_image_pool ? "图片素材池" : (options.auto_source ? "自动图片区域" : "图片画廊")}</div>
                <div class="preview-gallery-grid" style="grid-template-columns: repeat(${columns}, minmax(0, 1fr));">${boxes}</div>
            </div>
        `;
    }

    if (type === "image") {
        return `
            <div class="block-preview">
                <div class="preview-label">单图</div>
                <div class="preview-image-box">单图</div>
            </div>
        `;
    }

    return `
        <div class="block-preview">
            <div class="preview-label">未知Block：${escapeHtml(type)}</div>
        </div>
    `;
}



function renderRegionBlockPreview(region) {
    const blocks = Array.isArray(region && region.blocks) ? region.blocks.filter(block => block && block.enabled !== false) : [];
    const visibleBlocks = blocks.length ? blocks : [];
    if (!visibleBlocks.length) {
        return `<div class="block-preview"><div class="preview-label">Blocks: 0</div></div>`;
    }
    return visibleBlocks.map(block => renderBlockPreview(block)).join("");
}



function summarizeBlockOptions(block) {
    const type = String(block.type || "description_fields");
    const options = normalizeLayoutBlockOptions(type, block.options || {});
    if (type === "image_stack") {
        if (options.use_image_pool) {
            return `image_pool · max: ${options.max_images || "不限"} · ${options.image_width}×${options.image_height} · ${options.layout_mode}`;
        }
        if (options.auto_source) {
            return `auto_source · exclude: ${(options.exclude_keys || []).join(",") || "-"} · max: ${options.max_images || "不限"}`;
        }
        return `source_keys: ${(options.source_keys || []).join(",") || "-"} · ${options.image_width}×${options.image_height} · ${options.layout_mode}`;
    }
    if (type === "image_gallery") {
        if (options.use_image_pool) {
            return `image_pool · ${options.columns}列 · max: ${options.max_images || "不限"} · ${options.image_width}×${options.image_height}`;
        }
        if (options.auto_source) {
            return `auto_source · ${options.columns}列 · exclude: ${(options.exclude_keys || []).join(",") || "-"} · max: ${options.max_images || "不限"}`;
        }
        return `source_keys: ${(options.source_keys || []).join(",") || "-"} · ${options.columns}列 · ${options.image_width}×${options.image_height}`;
    }
    if (type === "image") {
        return `source: ${block.source || "-"} · ${options.width}×${options.height}`;
    }
    return block.source ? `source: ${block.source}` : "description_fields";
}



Object.assign(window, {
    parseLayoutNumber,
    parseLayoutNonNegativeNumber,
    parseLayoutSourceKeys,
    parseSourceKeys,
    normalizeLayoutBlockOptions,
    renderBlockPreview,
    renderRegionBlockPreview,
    summarizeBlockOptions
});
})();
