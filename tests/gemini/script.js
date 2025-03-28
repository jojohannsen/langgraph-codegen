const canvas = document.getElementById('mainCanvas');
const ctx = canvas.getContext('2d');
const addRectBtn = document.getElementById('addRectBtn');
const statusText = document.getElementById('status');

// --- State ---
let rectangles = [];
let connections = [];
let nextRectId = 0;
let nextConnId = 0;

let isConnecting = false;
let startConnectionInfo = null; // { rectId, slotType }
let currentMousePos = { x: 0, y: 0 };

// --- NEW State for Dragging ---
let isDragging = false;
let draggedRectId = null;
let dragOffsetX = 0;
let dragOffsetY = 0;


// --- Constants ---
const RECT_WIDTH = 100;
const RECT_HEIGHT = 60;
const SLOT_RADIUS = 5;
const SLOT_HIT_RADIUS = 8; // Larger hitbox for easier clicking
const SLOT_COLOR = '#007bff';
const SLOT_HOVER_COLOR = '#0056b3';
const CONNECTION_COLOR = '#333';
const TEMP_CONNECTION_COLOR = '#aaa';
const RECT_COLOR = '#f8f9fa';
const RECT_BORDER_COLOR = '#adb5bd';
const RECT_DRAG_BORDER_COLOR = '#6c757d'; // Slightly darker when dragging

// --- Helper Functions ---

function getCanvasRelativePos(event) {
    const rect = canvas.getBoundingClientRect();
    return {
        x: event.clientX - rect.left,
        y: event.clientY - rect.top
    };
}

function getSlotPosition(rect, slotType) {
    switch (slotType) {
        case 'top':    return { x: rect.x + rect.width / 2, y: rect.y };
        case 'bottom': return { x: rect.x + rect.width / 2, y: rect.y + rect.height };
        case 'left':   return { x: rect.x, y: rect.y + rect.height / 2 };
        case 'right':  return { x: rect.x + rect.width, y: rect.y + rect.height / 2 };
        default:       return null;
    }
}

// --- NEW Helper Function ---
function isPointInRect(point, rect) {
    return point.x >= rect.x && point.x <= rect.x + rect.width &&
           point.y >= rect.y && point.y <= rect.y + rect.height;
}

function findSlotAtPos(pos) {
    // Check slots *before* checking rectangles for dragging
    for (const rect of rectangles) {
        const slotTypes = ['top', 'bottom', 'left', 'right'];
        for (const type of slotTypes) {
            const slotPos = getSlotPosition(rect, type);
            const dx = pos.x - slotPos.x;
            const dy = pos.y - slotPos.y;
            if (dx * dx + dy * dy < SLOT_HIT_RADIUS * SLOT_HIT_RADIUS) {
                return { rectId: rect.id, slotType: type };
            }
        }
    }
    return null;
}

// --- NEW Helper Function ---
function findRectAtPos(pos) {
    // Iterate backwards so topmost rectangle is found first
    for (let i = rectangles.length - 1; i >= 0; i--) {
        const rect = rectangles[i];
        if (isPointInRect(pos, rect)) {
            return rect;
        }
    }
    return null; // No rectangle found
}


// --- Drawing Functions ---

function drawRect(rect) {
    // Use different border color if dragging
    ctx.strokeStyle = (isDragging && rect.id === draggedRectId) ? RECT_DRAG_BORDER_COLOR : RECT_BORDER_COLOR;
    ctx.fillStyle = RECT_COLOR;
    ctx.lineWidth = (isDragging && rect.id === draggedRectId) ? 2 : 1; // Thicker border when dragging
    ctx.fillRect(rect.x, rect.y, rect.width, rect.height);
    ctx.strokeRect(rect.x, rect.y, rect.width, rect.height);
    ctx.lineWidth = 1; // Reset line width
}

function drawSlot(rect, slotType, isHovered = false) {
    const pos = getSlotPosition(rect, slotType);
    ctx.fillStyle = isHovered ? SLOT_HOVER_COLOR : SLOT_COLOR;
    ctx.beginPath();
    ctx.arc(pos.x, pos.y, SLOT_RADIUS, 0, Math.PI * 2);
    ctx.fill();
}

function drawConnection(conn) {
    const startRect = rectangles.find(r => r.id === conn.startRectId);
    const endRect = rectangles.find(r => r.id === conn.endRectId);

    if (!startRect || !endRect) return; // Skip if rectangles are missing (e.g., one was deleted)

    const startPos = getSlotPosition(startRect, conn.startSlotType);
    const endPos = getSlotPosition(endRect, conn.endSlotType);

    ctx.strokeStyle = CONNECTION_COLOR;
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(startPos.x, startPos.y);
    ctx.lineTo(endPos.x, endPos.y);
    ctx.stroke();
}

function drawTemporaryConnection() {
    if (!isConnecting || !startConnectionInfo) return;

    const startRect = rectangles.find(r => r.id === startConnectionInfo.rectId);
    if (!startRect) return;

    const startPos = getSlotPosition(startRect, startConnectionInfo.slotType);

    ctx.strokeStyle = TEMP_CONNECTION_COLOR;
    ctx.lineWidth = 2;
    ctx.setLineDash([5, 5]);
    ctx.beginPath();
    ctx.moveTo(startPos.x, startPos.y);
    ctx.lineTo(currentMousePos.x, currentMousePos.y);
    ctx.stroke();
    ctx.setLineDash([]);
}

function redrawCanvas() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Draw connections first (so they appear behind rectangles)
    connections.forEach(drawConnection);

    // Draw temporary connection line if connecting (also behind)
    drawTemporaryConnection();

    // Draw all rectangles
    rectangles.forEach(drawRect);

    // Draw all slots (check for hover) - draw on top of rectangles
    const hoveredSlot = !isDragging ? findSlotAtPos(currentMousePos) : null; // Don't check slots while dragging
    rectangles.forEach(rect => {
        ['top', 'bottom', 'left', 'right'].forEach(type => {
             const isHovered = hoveredSlot && hoveredSlot.rectId === rect.id && hoveredSlot.slotType === type;
             // Only show hover if not actively connecting OR dragging
             drawSlot(rect, type, isHovered && !isConnecting && !isDragging);
        });
    });

    // --- UPDATED Cursor Logic ---
    let cursorStyle = 'default';
    if (isDragging) {
        cursorStyle = 'grabbing'; // Use 'grabbing' class if added, otherwise fallback
        canvas.classList.add('grabbing'); // Add class for CSS styling
    } else if (isConnecting) {
        cursorStyle = 'crosshair'; // Indicate connecting state
        canvas.classList.remove('grabbing');
    } else if (hoveredSlot) {
        cursorStyle = 'crosshair'; // Indicate potential connection start
        canvas.classList.remove('grabbing');
    } else if (findRectAtPos(currentMousePos)) {
        cursorStyle = 'grab'; // Indicate rectangle can be moved
        canvas.classList.remove('grabbing');
    } else {
        canvas.classList.remove('grabbing'); // Ensure class is removed
    }
    canvas.style.cursor = cursorStyle;


    // --- UPDATED Status Text ---
    if (isDragging) {
        statusText.textContent = `Status: Dragging Rect ${draggedRectId}`;
    } else if (isConnecting) {
        statusText.textContent = `Status: Connecting from Slot ${startConnectionInfo.slotType.toUpperCase()} on Rect ${startConnectionInfo.rectId}... Click another slot.`;
    } else if (hoveredSlot) {
         statusText.textContent = `Status: Hovering Slot ${hoveredSlot.slotType.toUpperCase()} on Rect ${hoveredSlot.rectId}. Click to connect.`;
    } else if (findRectAtPos(currentMousePos)) {
         statusText.textContent = 'Status: Hovering Rectangle. Click and drag to move, double-click to delete.';
    }
     else {
        statusText.textContent = 'Status: Ready.';
    }
}

// --- Event Handlers ---

function handleAddRectangle() {
    const newRect = {
        id: nextRectId++,
        x: Math.random() * (canvas.width - RECT_WIDTH - 40) + 20,
        y: Math.random() * (canvas.height - RECT_HEIGHT - 40) + 20,
        width: RECT_WIDTH,
        height: RECT_HEIGHT
    };
    rectangles.push(newRect);
    redrawCanvas();
}

// --- UPDATED MouseDown Handler ---
function handleMouseDown(event) {
    if (event.button !== 0) return; // Only handle left clicks

    const pos = getCanvasRelativePos(event);
    const clickedSlot = findSlotAtPos(pos);

    if (clickedSlot) {
        // Start connection
        isConnecting = true;
        isDragging = false; // Ensure not dragging
        startConnectionInfo = clickedSlot;
        currentMousePos = pos;
        redrawCanvas();
    } else {
        // Check if clicking on a rectangle to start dragging
        const clickedRect = findRectAtPos(pos);
        if (clickedRect) {
            isDragging = true;
            isConnecting = false; // Ensure not connecting
            draggedRectId = clickedRect.id;
            // Calculate offset from top-left corner
            dragOffsetX = pos.x - clickedRect.x;
            dragOffsetY = pos.y - clickedRect.y;
            redrawCanvas(); // Redraw to potentially change border/cursor
        } else {
            // Clicked on empty space - reset states if needed (though mouseup usually handles this)
            isConnecting = false;
            isDragging = false;
        }
    }
}

// --- UPDATED MouseMove Handler ---
function handleMouseMove(event) {
    currentMousePos = getCanvasRelativePos(event);

    if (isDragging && draggedRectId !== null) {
        const rect = rectangles.find(r => r.id === draggedRectId);
        if (rect) {
            // Update position based on mouse and original offset
            rect.x = currentMousePos.x - dragOffsetX;
            rect.y = currentMousePos.y - dragOffsetY;
        }
    }

    // Redraw is needed to update hover effects, temp line, or dragged position
    redrawCanvas();
}

// --- UPDATED MouseUp Handler ---
function handleMouseUp(event) {
     if (event.button !== 0) return; // Only handle left clicks

    if (isConnecting) {
        const pos = getCanvasRelativePos(event);
        const endSlot = findSlotAtPos(pos);

        if (endSlot && startConnectionInfo && (endSlot.rectId !== startConnectionInfo.rectId || endSlot.slotType !== startConnectionInfo.slotType)) {
            const newConnection = {
                id: nextConnId++,
                startRectId: startConnectionInfo.rectId,
                startSlotType: startConnectionInfo.slotType,
                endRectId: endSlot.rectId,
                endSlotType: endSlot.slotType
            };
            // Prevent duplicate connections (optional but good practice)
            const exists = connections.some(c =>
                 (c.startRectId === newConnection.startRectId && c.startSlotType === newConnection.startSlotType && c.endRectId === newConnection.endRectId && c.endSlotType === newConnection.endSlotType) ||
                 (c.startRectId === newConnection.endRectId && c.startSlotType === newConnection.endSlotType && c.endRectId === newConnection.startRectId && c.endSlotType === newConnection.startSlotType)
            );
            if (!exists) {
                connections.push(newConnection);
            } else {
                 console.log("Connection already exists.");
            }
        } else {
            console.log("Connection cancelled.");
        }
        isConnecting = false;
        startConnectionInfo = null;
    }

    if (isDragging) {
        // Stop dragging
        isDragging = false;
        draggedRectId = null;
        dragOffsetX = 0;
        dragOffsetY = 0;
    }

    redrawCanvas(); // Redraw to finalize state (remove temp line, reset styles)
}

// --- NEW Double Click Handler for Deletion ---
function handleDoubleClick(event) {
    if (event.button !== 0) return; // Only handle left double clicks

    const pos = getCanvasRelativePos(event);
    const clickedRect = findRectAtPos(pos); // Find rect at double-click position

    if (clickedRect) {
        const idToDelete = clickedRect.id;

        // Confirm before deleting (optional but recommended)
        // if (!confirm(`Delete Rectangle ${idToDelete}?`)) {
        //     return;
        // }

        // Remove the rectangle
        rectangles = rectangles.filter(rect => rect.id !== idToDelete);

        // Remove connections attached to the deleted rectangle
        connections = connections.filter(conn => conn.startRectId !== idToDelete && conn.endRectId !== idToDelete);

        // Reset potentially active states if the deleted rect was involved
        if (isConnecting && startConnectionInfo?.rectId === idToDelete) {
             isConnecting = false;
             startConnectionInfo = null;
        }
        if (isDragging && draggedRectId === idToDelete) {
            isDragging = false;
            draggedRectId = null;
        }


        console.log(`Deleted Rectangle ${idToDelete} and associated connections.`);
        redrawCanvas(); // Update the view
    }
}


// --- Initialization ---
addRectBtn.addEventListener('click', handleAddRectangle);
canvas.addEventListener('mousedown', handleMouseDown);
canvas.addEventListener('mousemove', handleMouseMove);
canvas.addEventListener('mouseup', handleMouseUp);
canvas.addEventListener('dblclick', handleDoubleClick); // ADDED Double click listener
// Optional: Prevent context menu on right-click if you plan actions for it later
// canvas.addEventListener('contextmenu', (e) => e.preventDefault());
canvas.addEventListener('dragstart', (e) => e.preventDefault()); // Prevent default image dragging

// Initial draw
redrawCanvas();