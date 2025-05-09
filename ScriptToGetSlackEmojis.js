// EXPLANATION OF THE REASON FOR THIS FILE:
//
// To use Slack emojis in the slack drawer tool you need to export them as a JSON file.
//    1. Visit your Slack workspace in a browser
//    https://YourworkspaceName.slack.com/customize/emoji
//    2. Open DevTools (F12 or Ctrl+Shift+I)
//    3. In the Console tab, paste the code from this file
//    4. Save the output file
//    5. Use this file when clicking 'Add Slack Emoji' in slack paint

// Function to extract and download Slack emojis
async function extractAndDownloadSlackEmojis(emojiImages) {
    console.log("Processing emoji image elements...");
    
    if (!emojiImages || emojiImages.length === 0) {
      console.error("No emoji image elements provided!");
      return;
    }
    
    // Create a collection of emojis with better naming
    const emojis = {};
    emojiImages.forEach((img, index) => {
      // Try to extract a sensible name from the image
      let name = '';

      // Try to get name from alt, title, or nearby text
      if (img.alt && img.alt.trim()) {
        name = img.alt.trim();
      } else if (img.title && img.title.trim()) {
        name = img.title.trim();
      } else {
        // Try to find a parent element with relevant text
        const parent = img.closest('[data-qa="custom_emoji_item"]') || 
                       img.closest('.c-custom_emoji_list__item') ||
                       img.closest('.emoji_row');
        
        if (parent) {
          const nameElement = parent.querySelector('[data-qa="custom_emoji_name"]') ||
                             parent.querySelector('.c-custom_emoji_list__name') ||
                             parent.querySelector('.emoji_name');
  
          if (nameElement && nameElement.textContent.trim()) {
            name = nameElement.textContent.trim();
          }
        }
      }
      // If we still don't have a name, use the URL to extract one
      if (!name) {
        const urlParts = img.src.split('/');
        const lastPart = urlParts[urlParts.length - 1];
        name = lastPart.split('.')[0] || `emoji_${index}`;
      }
      // Clean the name
      name = name.replace(/:/g, '');
      // Add to collection
      emojis[name] = img.src;
    });
  
  const emojiCount = Object.keys(emojis).length;
  console.log(`Processed ${emojiCount} emojis`);
  
  // Display the first 5 emojis in console for preview
  const previewEmojis = Object.entries(emojis).slice(0, 5);
  console.log("Preview of first 5 emojis:");
  previewEmojis.forEach(([name, url]) => {
    console.log(`${name}: ${url}`);
  });
  
  // Create JSON for download
  const jsonData = JSON.stringify(emojis, null, 2);
  const jsonBlob = new Blob([jsonData], {type: 'application/json'});
  const jsonUrl = URL.createObjectURL(jsonBlob);
  
  // Create HTML preview and download buttons
  const container = document.createElement('div');
  container.style.position = 'fixed';
  container.style.top = '20px';
  container.style.right = '20px';
  container.style.backgroundColor = 'white';
  container.style.padding = '15px';
  container.style.border = '1px solid #ddd';
  container.style.borderRadius = '5px';
  container.style.zIndex = '9999';
  container.style.maxHeight = '80vh';
  container.style.overflow = 'auto';
  container.style.boxShadow = '0 0 10px rgba(0,0,0,0.2)';
  
  // Add header
  const header = document.createElement('h3');
  header.textContent = `Found ${emojiCount} Slack Emojis`;
  header.style.marginTop = '0';
  container.appendChild(header);
  
  // Add close button
  const closeBtn = document.createElement('button');
  closeBtn.textContent = 'X';
  closeBtn.style.position = 'absolute';
  closeBtn.style.top = '10px';
  closeBtn.style.right = '10px';
  closeBtn.style.backgroundColor = '#f44336';
  closeBtn.style.color = 'white';
  closeBtn.style.border = 'none';
  closeBtn.style.borderRadius = '50%';
  closeBtn.style.width = '25px';
  closeBtn.style.height = '25px';
  closeBtn.style.cursor = 'pointer';
  closeBtn.onclick = () => container.remove();
  container.appendChild(closeBtn);
  
  // Add download JSON button
  const downloadJsonBtn = document.createElement('button');
  downloadJsonBtn.textContent = 'Download JSON';
  downloadJsonBtn.style.display = 'block';
  downloadJsonBtn.style.marginBottom = '10px';
  downloadJsonBtn.style.padding = '8px 12px';
  downloadJsonBtn.style.backgroundColor = '#4CAF50';
  downloadJsonBtn.style.color = 'white';
  downloadJsonBtn.style.border = 'none';
  downloadJsonBtn.style.borderRadius = '4px';
  downloadJsonBtn.style.cursor = 'pointer';
  downloadJsonBtn.onclick = () => {
    const a = document.createElement('a');
    a.href = jsonUrl;
    a.download = 'slack_emojis.json';
    a.click();
  };
  container.appendChild(downloadJsonBtn);
  
// ---------------------------------------------------------------------------------------
// Commented out for now as theres no point in zipping 3000 images when we dont need them,
// leaving in the code because I cant get myself to delete it
// ---------------------------------------------------------------------------------------
//   // Add download all images button
//   const downloadAllBtn = document.createElement('button');
//   downloadAllBtn.textContent = 'Download All Images (ZIP)';
//   downloadAllBtn.style.display = 'block';
//   downloadAllBtn.style.marginBottom = '15px';
//   downloadAllBtn.style.padding = '8px 12px';
//   downloadAllBtn.style.backgroundColor = '#2196F3';
//   downloadAllBtn.style.color = 'white';
//   downloadAllBtn.style.border = 'none';
//   downloadAllBtn.style.borderRadius = '4px';
//   downloadAllBtn.style.cursor = 'pointer';
//   downloadAllBtn.onclick = async () => {
//     // Load JSZip library dynamically
//     if (!window.JSZip) {
//       const script = document.createElement('script');
//       script.src = 'https://cdnjs.cloudflare.com/ajax/libs/jszip/3.10.1/jszip.min.js';
//       document.head.appendChild(script);
      
//       // Wait for script to load
//       await new Promise(resolve => script.onload = resolve);
//     }
    
//     // Create new zip
//     const zip = new JSZip();
    
//     // Status message
//     const status = document.createElement('div');
//     status.textContent = 'Preparing download...';
//     container.appendChild(status);
    
//     // Add files to zip
//     let completed = 0;
//     const total = Object.keys(emojis).length;
    
//     try {
//       const promises = Object.entries(emojis).map(async ([name, url]) => {
//         try {
//           // Fetch the image
//           const response = await fetch(url);
//           const blob = await response.blob();
          
//           // Get file extension
//           let extension = 'png'; // Default
//           if (url.includes('.')) {
//             extension = url.split('.').pop().split('?')[0];
//           }
          
//           // Add to zip
//           zip.file(`${name}.${extension}`, blob);
          
//           // Update status
//           completed++;
//           status.textContent = `Downloaded ${completed}/${total} emojis...`;
//         } catch (err) {
//           console.error(`Failed to download ${name}: ${err}`);
//         }
//       });
      
//       // Wait for all downloads to complete
//       await Promise.all(promises);
      
//       // Generate the zip file
//       status.textContent = 'Creating ZIP file...';
//       const content = await zip.generateAsync({type: 'blob'});
      
//       // Create download link
//       const zipUrl = URL.createObjectURL(content);
//       const a = document.createElement('a');
//       a.href = zipUrl;
//       a.download = 'slack_emojis.zip';
//       a.click();
      
//       // Update status
//       status.textContent = 'Download complete!';
//       setTimeout(() => status.remove(), 3000);
//     } catch (error) {
//       status.textContent = `Error: ${error.message}`;
//     }
//   };
//   container.appendChild(downloadAllBtn);
  
  // Add preview grid
  const previewGrid = document.createElement('div');
  previewGrid.style.display = 'grid';
  previewGrid.style.gridTemplateColumns = 'repeat(4, 1fr)';
  previewGrid.style.gap = '10px';
  
  // Add up to 20 emojis to the preview
  Object.entries(emojis).slice(0, 20).forEach(([name, url]) => {
    const emojiCard = document.createElement('div');
    emojiCard.style.textAlign = 'center';
    emojiCard.style.border = '1px solid #eee';
    emojiCard.style.borderRadius = '4px';
    emojiCard.style.padding = '5px';
    
    const img = document.createElement('img');
    img.src = url;
    img.style.width = '30px';
    img.style.height = '30px';
    img.style.objectFit = 'contain';
    
    const nameSpan = document.createElement('div');
    nameSpan.textContent = name;
    nameSpan.style.fontSize = '10px';
    nameSpan.style.overflow = 'hidden';
    nameSpan.style.textOverflow = 'ellipsis';
    nameSpan.style.whiteSpace = 'nowrap';
    
    emojiCard.appendChild(img);
    emojiCard.appendChild(nameSpan);
    previewGrid.appendChild(emojiCard);
  });
  
  container.appendChild(previewGrid);
  
  // Show more info
  if (emojiCount > 20) {
    const moreInfo = document.createElement('p');
    moreInfo.textContent = `...and ${emojiCount - 20} more`;
    moreInfo.style.textAlign = 'center';
    moreInfo.style.marginTop = '10px';
    container.appendChild(moreInfo);
  }
  
  // Add to page
  document.body.appendChild(container);
  
  return emojis;
}

// Function to scroll through the emoji list and ensure all images are loaded
async function scrollUntilAllEmojisLoad(container, cacheImagesCallback, maxAttempts = 300) {
    let lastEmojiCount = 0;
    //let noChangeCount = 0;
    //const maxNoChange = 10;

    for (let i = 0; i < maxAttempts; i++) {
      container.scrollTop = container.scrollHeight;
  
      // Give DOM time to load and render new elements
      await new Promise(resolve => setTimeout(resolve, 100)); // If this doesnt work for you can can try making this wait time bigger
  
      // Optionally collect visible images during scrolling
      if (typeof cacheImagesCallback === 'function') {
        let imageCount = cacheImagesCallback();
        //console.log(`Image count ${imageCount}`);

        // Early out
        if (imageCount === lastEmojiCount) {
            noNewEmojiCount++;
            // Extra wait
            await new Promise(resolve => setTimeout(resolve, 1000));
            if (noNewEmojiCount >= 5) {
              console.log("No new emojis loaded for several iterations, assuming done.");
              break;
            }
          } else {
            noNewEmojiCount = 0;
            lastEmojiCount = imageCount;
          }
      }
  
      const newHeight = container.scrollHeight;
      lastHeight = newHeight;
    }

    // Extra quick runover bottom to top
    // This is most definitly jank in every single way imaginable but
    // if we scroll too slow first time slack will only loa din a max of 100 emojis
    // scroll fast enough to load in more and we might not be able to save all emojis in time
    // [Solution] we scroll down fast loading everything in on the webpage and then scroll up slower to save everything
    for (let i = 0; i < maxAttempts; i++) {
        container.scrollTop -= 900 // = container.scrollHeight;
    
        // Give DOM time to load and render new elements
        await new Promise(resolve => setTimeout(resolve, 400)); // If this doesnt work for you can can try making this wait time bigger
    
        // Optionally collect visible images during scrolling
        if (typeof cacheImagesCallback === 'function') {
          cacheImagesCallback();
        }
        if(container.scrollTop <= 0){
            break;
        }
      }
  }
  async function loadAllEmojiImages() {
    console.log("Starting to load all emoji images...");
  
    const virtualListContainer = document.querySelector('.c-virtual_list--scrollbar');
    const scrollContainer = document.querySelector('.c-scrollbar__hider');
    const alternativeContainer = 
      document.querySelector('.c-table_view_all_rows_container') || 
      document.querySelector('[role="presentation"][style*="height: 1000px"]') ||
      document.querySelector('.c-virtual_list.c-virtual_list--scrollbar');
  
    const container = scrollContainer || virtualListContainer || alternativeContainer;
  
    if (!container) {
      console.error("Couldn't find the emoji container. Are you on the emoji customization page?");
      return;
    }

    // Reset scroll
    container.scrollTop = 0;
  
    console.log("Found emoji container, beginning to scroll...");
  
    const seenImages = new Set();
    const collectedImages = [];
  
    function cacheVisibleImages() {
      const images = document.querySelectorAll('img[src*="emoji"]');
      images.forEach(img => {
        if (!seenImages.has(img.src)) {
          seenImages.add(img.src);
          collectedImages.push(img);
        }
      });
      console.log(`Cached ${collectedImages.length} unique emoji images so far`);
      return collectedImages.length
    }
  
    await scrollUntilAllEmojisLoad(container, cacheVisibleImages);
  
    cacheVisibleImages(); // Final cache after scroll
    container.scrollTop = 0;
    console.log(`Finished loading. Total collected: ${collectedImages.length} images`);
  
    return collectedImages;
  }  


loadAllEmojiImages().then((emojiImageElements) => {
    extractAndDownloadSlackEmojis(emojiImageElements);
  });
  