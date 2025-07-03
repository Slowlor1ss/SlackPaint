(function() {
    let isScanning = false;

    // Find the emoji container
    function findEmojiContainer() {
    const emojiPickerDialog = document.querySelector('div[role="dialog"], div[class*="emojiPicker"]');
    if (!emojiPickerDialog) return null;

    const scroller = emojiPickerDialog.querySelector('div[class*="scroller"]');
    return scroller && scroller.scrollHeight > scroller.clientHeight ? scroller : null;
    }

    // Open emoji picker if not already open
    function openEmojiPicker() {
    const emojiButton = Array.from(document.querySelectorAll('button[aria-label]'))
        .find(btn => btn.getAttribute('aria-label').toLowerCase().includes('emoji'));

    if (emojiButton && !findEmojiContainer()) {
        emojiButton.click();
        return true;
    }
    return false;
    }
  
    // Create loading indicator
    function createLoadingIndicator() {
    const indicator = document.createElement('div');
    indicator.id = 'emoji-loading-indicator';
    indicator.style.cssText = `
        position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%);
        background: rgba(0, 0, 0, 0.9); color: white; padding: 20px;
        border-radius: 10px; z-index: 10001; text-align: center;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        min-width: 300px; box-shadow: 0 4px 20px rgba(0,0,0,0.5);
    `;

    indicator.innerHTML = `
        <div style="font-size: 18px; margin-bottom: 10px;">Scanning Emojis...</div>
        <div id="loading-status" style="font-size: 14px; color: #ccc;">Initializing...</div>
        <div style="margin-top: 15px;">
        <button id="cancel-scan" style="
            background: #ed4245; color: white; border: none; padding: 8px 16px;
            border-radius: 4px; cursor: pointer; font-size: 12px;
        ">Cancel</button>
        </div>
    `;

    document.body.appendChild(indicator);

    document.getElementById('cancel-scan').addEventListener('click', () => {
        isScanning = false;
        document.body.removeChild(indicator);
    });

    return indicator;
    }

    // Update loading status
    function updateLoadingStatus(message) {
    const statusEl = document.getElementById('loading-status');
    if (statusEl) statusEl.textContent = message;
    }

    // Scan all sections to find available servers
    async function scanAllSections() {
    if (!findEmojiContainer()) {
        if (openEmojiPicker()) {
        await new Promise(r => setTimeout(r, 1000));
        } else {
        alert('Could not open emoji picker!');
        return [];
        }
    }

    const container = findEmojiContainer();
    if (!container) return [];

    isScanning = true;
    const loadingIndicator = createLoadingIndicator();

    try {
        updateLoadingStatus('Scanning all emoji sections...');
        
        container.scrollTop = 0;
        await new Promise(r => setTimeout(r, 1000));
        
        const sections = [];
        let scrollAttempts = 0;
        const maxScrollAttempts = 200;
        
        while (isScanning && scrollAttempts < maxScrollAttempts) {
        // Find headers
        const headers = Array.from(container.querySelectorAll('[class^="headerLabel"]'));
        
        headers.forEach(header => {
            const name = header.textContent.trim();
            if (name && !sections.find(s => s.name === name)) {
            sections.push({ 
                name, 
                scrollTop: getRelativeOffsetTop(header, container) 
            });
            }
        });
        
        updateLoadingStatus(`Found ${sections.length} sections... Scrolling (${scrollAttempts}/${maxScrollAttempts})`);
        
        container.scrollTop += Math.max(50, Math.floor(container.clientHeight * 0.1));
        await new Promise(r => setTimeout(r, 100));
        scrollAttempts++;
        }
        
        updateLoadingStatus(`Scan complete! Found ${sections.length} sections.`);
        await new Promise(r => setTimeout(r, 1500));
        
        return sections;
        
    } finally {
        if (document.body.contains(loadingIndicator)) {
        document.body.removeChild(loadingIndicator);
        }
        isScanning = false;
    }
    }

    // Load emojis from a specific section
    async function loadSectionEmojis(sectionName, sectionTop, sectionBottom = null) {
    if (!findEmojiContainer()) {
        if (openEmojiPicker()) {
        await new Promise(r => setTimeout(r, 1000));
        } else {
        return [];
        }
    }

    const container = findEmojiContainer();
    if (!container) return [];

    isScanning = true;
    const loadingIndicator = createLoadingIndicator();

    try {
        updateLoadingStatus(`Loading emojis from "${sectionName}"...`);
        
        container.scrollTop = sectionTop;
        await new Promise(r => setTimeout(r, 1000));
        
        const endScroll = sectionBottom || (container.scrollHeight - container.clientHeight);
        const collectedEmojis = [];
        let stableCount = 0;
        let lastCount = 0;
        
        while (isScanning && stableCount < 8) {
        // Collect emojis
        const emojiImages = Array.from(container.querySelectorAll('img[src*="emoji"], img[data-type="emoji"]'));
        const headers = Array.from(container.querySelectorAll('[class^="headerLabel"]'));
        
        emojiImages.forEach(img => {
            // Find which section this emoji belongs to
            let currentSection = 'unknown';
            for (let i = headers.length - 1; i >= 0; i--) {
            if (headers[i].compareDocumentPosition(img) & Node.DOCUMENT_POSITION_FOLLOWING) {
                currentSection = headers[i].textContent.trim();
                break;
            }
            }
            
            if (currentSection === sectionName && img.src) {
            const name = img.alt?.replace(/:/g, '') || 'unnamed';
            if (!collectedEmojis.some(e => e.name === name && e.src === img.src)) {
                collectedEmojis.push({ name, src: img.src, section: currentSection });
            }
            }
        });
        
        updateLoadingStatus(`Loading emojis... Found ${collectedEmojis.length} emojis`);
        
        // Check if we're making progress
        if (collectedEmojis.length === lastCount) {
            stableCount++;
        } else {
            stableCount = 0;
            lastCount = collectedEmojis.length;
        }
        
        // Scroll within section bounds
        container.scrollTop = Math.min(container.scrollTop + 30, endScroll);
        await new Promise(r => setTimeout(r, 150));
        
        // We add clientHeight as we need to keep in mind the size of the emji picker
        if (container.scrollTop + container.clientHeight >= endScroll) break;
        }
        
        updateLoadingStatus(`Loaded ${collectedEmojis.length} emojis from "${sectionName}"`);
        await new Promise(r => setTimeout(r, 1500));
        return collectedEmojis;
        
    } finally {
        if (document.body.contains(loadingIndicator)) {
        document.body.removeChild(loadingIndicator);
        }
        isScanning = false;
    }
    }

    // Load ALL emojis from all sections
    async function loadAllEmojis(sections) {
    const allEmojis = [];

    for (let i = 0; i < sections.length && isScanning; i++) {
        const nextSection = sections[i + 1];
        const emojis = await loadSectionEmojis(
        sections[i].name, 
        sections[i].scrollTop, 
        nextSection?.scrollTop
        );
        allEmojis.push(...emojis);
        await new Promise(r => setTimeout(r, 500));
    }

    return allEmojis;
    }

    // Create server selection dialog
    function createServerSelectionDialog(sections) {
    const overlay = document.createElement('div');
    overlay.style.cssText = `
        position: fixed; top: 0; left: 0; width: 100%; height: 100%;
        background: rgba(0, 0, 0, 0.5); z-index: 10000;
        display: flex; justify-content: center; align-items: center;
    `;

    const dialog = document.createElement('div');
    dialog.style.cssText = `
        background: white; padding: 24px; border-radius: 12px;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3); max-width: 450px;
        width: 90%; max-height: 80vh; overflow-y: auto;
    `;

    dialog.innerHTML = `
        <h2 style="margin: 0 0 16px 0; color: #333; font-size: 20px;">Select Server to Scrape Emojis</h2>
        <p style="margin: 0 0 16px 0; color: #666; font-size: 14px;">Found ${sections.length} servers with emojis:</p>
    `;

    // Download ALL button
    const allButton = document.createElement('button');
    allButton.textContent = `Download ALL Emojis (${sections.length} servers)`;
    allButton.style.cssText = `
        display: block; width: 100%; margin-bottom: 16px; padding: 16px;
        background: linear-gradient(45deg, #ff6b35, #f7931e); color: white;
        border: none; border-radius: 8px; cursor: pointer;
        font-size: 16px; font-weight: bold; transition: all 0.3s;
    `;

    allButton.addEventListener('click', async () => {
        document.body.removeChild(overlay);
        const allEmojis = await loadAllEmojis(sections);
        if (allEmojis.length > 0) {
        const emojiJSON = Object.fromEntries(allEmojis.map(e => [e.name, e.src]));
        createPreviewWindow('All Servers', emojiJSON);
        downloadJSON(emojiJSON, 'all_servers');
        }
    });

    dialog.appendChild(allButton);

    // Individual server buttons
    sections.forEach((section, index) => {
        const button = document.createElement('button');
        button.textContent = section.name;
        button.style.cssText = `
        display: block; width: 100%; margin-bottom: 8px; padding: 12px;
        background: #5865f2; color: white; border: none; border-radius: 6px;
        cursor: pointer; font-size: 14px; text-align: left;
        `;
        
        button.addEventListener('click', async () => {
        document.body.removeChild(overlay);
        const nextSection = sections[index + 1];
        const emojis = await loadSectionEmojis(section.name, section.scrollTop, nextSection?.scrollTop);
        
        if (emojis.length > 0) {
            const emojiJSON = Object.fromEntries(emojis.map(e => [e.name, e.src]));
            createPreviewWindow(section.name, emojiJSON);
            downloadJSON(emojiJSON, section.name);
        }
        });
        
        dialog.appendChild(button);
    });

    // Control buttons
    const controlsDiv = document.createElement('div');
    controlsDiv.style.cssText = 'display: flex; gap: 8px; margin-top: 16px;';

    const rescanButton = document.createElement('button');
    rescanButton.textContent = 'Rescan';
    rescanButton.style.cssText = `
        flex: 1; padding: 12px; background: #57f287; color: white;
        border: none; border-radius: 6px; cursor: pointer;
    `;
    rescanButton.addEventListener('click', async () => {
        document.body.removeChild(overlay);
        await startScraping();
    });

    const cancelButton = document.createElement('button');
    cancelButton.textContent = 'Cancel';
    cancelButton.style.cssText = `
        flex: 1; padding: 12px; background: #ed4245; color: white;
        border: none; border-radius: 6px; cursor: pointer;
    `;
    cancelButton.addEventListener('click', () => document.body.removeChild(overlay));

    controlsDiv.appendChild(rescanButton);
    controlsDiv.appendChild(cancelButton);
    dialog.appendChild(controlsDiv);

    overlay.appendChild(dialog);
    document.body.appendChild(overlay);
    }

    // Create preview window
    function createPreviewWindow(serverName, emojiJSON) {
    const container = document.createElement('div');
    container.style.cssText = `
        position: fixed; top: 20px; right: 20px; background: white;
        border: 1px solid #ccc; border-radius: 8px; z-index: 9999;
        max-height: 90vh; width: 350px; box-shadow: 0 4px 20px rgba(0,0,0,0.3);
    `;

    // Create header
    const header = document.createElement('div');
    header.style.cssText = 'display: flex; justify-content: space-between; align-items: center; padding: 16px; background: #f8f9fa; border-bottom: 1px solid #dee2e6;';

    const title = document.createElement('h3');
    title.style.cssText = 'margin: 0; font-size: 16px; color: #333;';
    title.textContent = `Emojis from ${serverName}`;

    const closeButton = document.createElement('button');
    closeButton.style.cssText = 'background: none; border: none; font-size: 24px; cursor: pointer; color: #6c757d;';
    closeButton.textContent = '×';
    closeButton.addEventListener('click', () => {
        document.body.removeChild(container);
    });

    header.appendChild(title);
    header.appendChild(closeButton);

    // Create count info
    const countInfo = document.createElement('div');
    countInfo.style.cssText = 'padding: 8px 16px; background: #e7f3ff; color: #0066cc; font-size: 12px;';
    countInfo.textContent = `${Object.keys(emojiJSON).length} emojis found`;

    // Create emoji list
    const emojiList = document.createElement('div');
    emojiList.style.cssText = 'max-height: 400px; overflow-y: auto; padding: 8px;';

    Object.entries(emojiJSON).forEach(([name, src]) => {
        const row = document.createElement('div');
        row.style.cssText = 'display: flex; align-items: center; padding: 6px 8px; margin-bottom: 2px;';
        
        const img = document.createElement('img');
        img.src = src;
        img.style.cssText = 'width: 24px; height: 24px; margin-right: 10px;';
        
        const span = document.createElement('span');
        span.style.cssText = 'font-size: 14px; color: #333;';
        span.textContent = name;
        
        row.appendChild(img);
        row.appendChild(span);
        emojiList.appendChild(row);
    });

    container.appendChild(header);
    container.appendChild(countInfo);
    container.appendChild(emojiList);
    document.body.appendChild(container);
    }

    // Download JSON file
    function downloadJSON(emojiJSON, serverName) {
    const blob = new Blob([JSON.stringify(emojiJSON, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${serverName.replace(/[^a-z0-9]/gi, '_').toLowerCase()}_emojis.json`;
    a.click();
    URL.revokeObjectURL(url);
    }

    // Helper function to get relative offset
    function getRelativeOffsetTop(element, container) {
    let offset = 0;
    let el = element;
    while (el && el !== container) {
        offset += el.offsetTop;
        el = el.offsetParent;
    }
    return offset;
    }

    // Main function to start scraping
    async function startScraping() {
    const sections = await scanAllSections();

    if (sections.length === 0) {
        alert('No emoji sections found! Make sure the emoji picker is open and contains custom emojis.');
        return;
    }

    createServerSelectionDialog(sections);
    }

    // Start the process
    startScraping();
})();