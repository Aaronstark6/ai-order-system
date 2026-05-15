(function () {
'use strict';

// 负责 Excel Geometry 与坐标换算。

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
if (typeof window.DEBUG_LAYOUT === "undefined") {
    window.DEBUG_LAYOUT = false;
}
window.layoutDebug = window.layoutDebug || function (...args) {
    if (window.DEBUG_LAYOUT) {
        console.log("[Layout]", ...args);
    }
};
window.layoutWarn = window.layoutWarn || function (...args) {
    console.warn("[Layout]", ...args);
};
window.layoutError = window.layoutError || function (...args) {
    console.error("[Layout]", ...args);
};

const LAYOUT_DESIGNER_COL_WIDTH = 70;
const LAYOUT_DESIGNER_ROW_HEIGHT = 24;
const LAYOUT_DESIGNER_ROW_LABEL_WIDTH = 40;
const LAYOUT_DESIGNER_COL_LABEL_HEIGHT = 24;
const LAYOUT_DESIGNER_COLUMNS = 12;
const LAYOUT_DESIGNER_ROWS = 40;
const GEOMETRY_FALLBACK_MESSAGE = "\u672a\u8bfb\u53d6\u5230\u771f\u5b9e Excel \u51e0\u4f55\uff0c\u5f53\u524d\u4f7f\u7528\u7b80\u5316\u7f51\u683c\u3002";

function syncLayoutEditorStateFromProfile(profile) {
    state.currentProfile = profile || null;
    state.layoutConfig = profile && profile.layout_config ? profile.layout_config : null;
    state.selectedRegionId = null;
    state.selectedBlockId = null;
    state.selectedRegionIndex = 0;
    state.dirty = false;
    state.lastSavedAt = null;
    if (!state.currentProfile) {
        state.geometry = null;
        state.geometryError = GEOMETRY_FALLBACK_MESSAGE;
    }
}

async function loadCurrentGeometry() {
    state.geometry = null;
    state.geometryError = GEOMETRY_FALLBACK_MESSAGE;
    if (!state.currentProfile || !state.currentProfile.template_file) {
        state.geometryError = GEOMETRY_FALLBACK_MESSAGE;
        return;
    }

    try {
        const response = await fetch(`/api/template-profiles/${state.currentProfile.id}/geometry`);
        const result = await response.json();
        if (result.success) {
            state.geometry = result;
            state.geometryError = "";
        } else {
            state.geometryError = result.error || "未读取到真实 Excel 几何，当前使用简化网格。";
        }
    } catch (error) {
        state.geometryError = GEOMETRY_FALLBACK_MESSAGE;
    }
}



function clampLayoutDesignerValue(value, min, max) {
    return Math.min(Math.max(value, min), max);
}



function excelColumnToNumber(label) {
    const text = String(label || "").trim().toUpperCase();
    let number = 0;
    for (const char of text) {
        const code = char.charCodeAt(0);
        if (code < 65 || code > 90) {
            return 0;
        }
        number = number * 26 + code - 64;
    }
    return number;
}



function numberToExcelColumn(number) {
    let value = Math.max(1, Math.round(Number(number) || 1));
    let label = "";
    while (value > 0) {
        const remainder = (value - 1) % 26;
        label = String.fromCharCode(65 + remainder) + label;
        value = Math.floor((value - 1) / 26);
    }
    return label;
}



function parseExcelCell(cell) {
    const match = String(cell || "").trim().toUpperCase().match(/^\$?([A-Z]{1,3})\$?(\d+)$/);
    if (!match) {
        return null;
    }
    const col = excelColumnToNumber(match[1]);
    const row = Number(match[2]);
    if (!col || !Number.isFinite(row) || row < 1) {
        return null;
    }
    return { col, row };
}



function hasCurrentGeometry() {
    return Boolean(
        state.geometry
        && Array.isArray(state.geometry.columns)
        && state.geometry.columns.length
        && Array.isArray(state.geometry.rows)
        && state.geometry.rows.length
    );
}



function getDesignerColumns() {
    if (hasCurrentGeometry()) {
        return state.geometry.columns.map(column => ({
            index: Number(column.index) || 1,
            letter: String(column.letter || numberToExcelColumn(column.index)).toUpperCase(),
            width: Math.max(1, Math.round(Number(column.width) || LAYOUT_DESIGNER_COL_WIDTH))
        }));
    }
    return Array.from({ length: LAYOUT_DESIGNER_COLUMNS }, (_, index) => ({
        index: index + 1,
        letter: numberToExcelColumn(index + 1),
        width: LAYOUT_DESIGNER_COL_WIDTH
    }));
}



function getDesignerRows() {
    if (hasCurrentGeometry()) {
        return state.geometry.rows.map(row => ({
            index: Number(row.index) || 1,
            height: Math.max(1, Math.round(Number(row.height) || LAYOUT_DESIGNER_ROW_HEIGHT))
        }));
    }
    return Array.from({ length: LAYOUT_DESIGNER_ROWS }, (_, index) => ({
        index: index + 1,
        height: LAYOUT_DESIGNER_ROW_HEIGHT
    }));
}



function getLayoutDesignerMetrics() {
    const columns = getDesignerColumns();
    const rows = getDesignerRows();
    const columnBoundaries = [0];
    const rowBoundaries = [0];
    columns.forEach(column => {
        columnBoundaries.push(columnBoundaries[columnBoundaries.length - 1] + column.width);
    });
    rows.forEach(row => {
        rowBoundaries.push(rowBoundaries[rowBoundaries.length - 1] + row.height);
    });
    return {
        columns,
        rows,
        columnBoundaries,
        rowBoundaries,
        width: columnBoundaries[columnBoundaries.length - 1],
        height: rowBoundaries[rowBoundaries.length - 1]
    };
}



function nearestBoundaryIndex(value, boundaries) {
    const number = Math.max(0, Number(value) || 0);
    let bestIndex = 0;
    let bestDistance = Infinity;
    boundaries.forEach((boundary, index) => {
        const distance = Math.abs(boundary - number);
        if (distance < bestDistance) {
            bestDistance = distance;
            bestIndex = index;
        }
    });
    return bestIndex;
}



function cellToCanvasPosition(cell) {
    const parsed = parseExcelCell(cell);
    if (!parsed) {
        return null;
    }
    const metrics = getLayoutDesignerMetrics();
    const col = clampLayoutDesignerValue(parsed.col, 1, metrics.columns.length);
    const row = clampLayoutDesignerValue(parsed.row, 1, metrics.rows.length);
    return {
        x: metrics.columnBoundaries[col - 1],
        y: metrics.rowBoundaries[row - 1]
    };
}



function rangeToRect(range) {
    const parts = String(range || "").trim().toUpperCase().split(":").filter(Boolean);
    if (!parts.length) {
        return null;
    }
    const start = parseExcelCell(parts[0]);
    const end = parseExcelCell(parts[1] || parts[0]);
    if (!start || !end) {
        return null;
    }
    const metrics = getLayoutDesignerMetrics();
    const startCol = clampLayoutDesignerValue(Math.min(start.col, end.col), 1, metrics.columns.length);
    const endCol = clampLayoutDesignerValue(Math.max(start.col, end.col), 1, metrics.columns.length);
    const startRow = clampLayoutDesignerValue(Math.min(start.row, end.row), 1, metrics.rows.length);
    const endRow = clampLayoutDesignerValue(Math.max(start.row, end.row), 1, metrics.rows.length);
    const left = metrics.columnBoundaries[startCol - 1];
    const top = metrics.rowBoundaries[startRow - 1];
    return {
        x: left,
        y: top,
        width: metrics.columnBoundaries[endCol] - left,
        height: metrics.rowBoundaries[endRow] - top
    };
}



function rectToRange(x, y, width, height) {
    const metrics = getLayoutDesignerMetrics();
    const maxWidth = metrics.width;
    const maxHeight = metrics.height;
    const left = clampLayoutDesignerValue(Number(x) || 0, 0, Math.max(0, maxWidth - 1));
    const top = clampLayoutDesignerValue(Number(y) || 0, 0, Math.max(0, maxHeight - 1));
    const right = clampLayoutDesignerValue(left + Math.max(1, Number(width) || 1), 1, maxWidth);
    const bottom = clampLayoutDesignerValue(top + Math.max(1, Number(height) || 1), 1, maxHeight);

    let startBoundary = nearestBoundaryIndex(left, metrics.columnBoundaries);
    let endBoundary = nearestBoundaryIndex(right, metrics.columnBoundaries);
    let startRowBoundary = nearestBoundaryIndex(top, metrics.rowBoundaries);
    let endRowBoundary = nearestBoundaryIndex(bottom, metrics.rowBoundaries);

    startBoundary = clampLayoutDesignerValue(startBoundary, 0, metrics.columns.length - 1);
    endBoundary = clampLayoutDesignerValue(endBoundary, 1, metrics.columns.length);
    startRowBoundary = clampLayoutDesignerValue(startRowBoundary, 0, metrics.rows.length - 1);
    endRowBoundary = clampLayoutDesignerValue(endRowBoundary, 1, metrics.rows.length);

    if (endBoundary <= startBoundary) {
        endBoundary = Math.min(metrics.columns.length, startBoundary + 1);
    }
    if (endRowBoundary <= startRowBoundary) {
        endRowBoundary = Math.min(metrics.rows.length, startRowBoundary + 1);
    }

    const startCol = startBoundary + 1;
    const startRow = startRowBoundary + 1;
    const endCol = endBoundary;
    const endRow = endRowBoundary;
    return `${numberToExcelColumn(startCol)}${startRow}:${numberToExcelColumn(endCol)}${endRow}`;
}



function defaultLayoutDesignerRect(index) {
    const metrics = getLayoutDesignerMetrics();
    const startCol = Math.min(metrics.columns.length, (index % 3) * 3 + 1);
    const startRow = Math.min(metrics.rows.length, Math.floor(index / 3) * 5 + 1);
    const endCol = Math.min(metrics.columns.length, startCol + 2);
    const endRow = Math.min(metrics.rows.length, startRow + 3);
    return rangeToRect(`${numberToExcelColumn(startCol)}${startRow}:${numberToExcelColumn(endCol)}${endRow}`) || {
        x: 0,
        y: 0,
        width: LAYOUT_DESIGNER_COL_WIDTH,
        height: LAYOUT_DESIGNER_ROW_HEIGHT
    };
}



Object.assign(window, {
    LAYOUT_DESIGNER_COL_WIDTH,
    LAYOUT_DESIGNER_ROW_HEIGHT,
    LAYOUT_DESIGNER_ROW_LABEL_WIDTH,
    LAYOUT_DESIGNER_COL_LABEL_HEIGHT,
    LAYOUT_DESIGNER_COLUMNS,
    LAYOUT_DESIGNER_ROWS,
    syncLayoutEditorStateFromProfile,
    loadCurrentGeometry,
    clampLayoutDesignerValue,
    excelColumnToNumber,
    numberToExcelColumn,
    parseExcelCell,
    hasCurrentGeometry,
    getDesignerColumns,
    getDesignerRows,
    getLayoutDesignerMetrics,
    nearestBoundaryIndex,
    cellToCanvasPosition,
    rangeToRect,
    rectToRange,
    defaultLayoutDesignerRect
});
})();
