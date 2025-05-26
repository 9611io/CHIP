/**
 * CHIP Application JavaScript (Updated)
 * ---------------------------
 * Fixes:
 * - Changed appContainer.getElementById to document.getElementById.
 * - Ensured all getElementById calls are on the document object.
 * - Added more robust checks for element existence.
 */

document.addEventListener('DOMContentLoaded', () => {
    // Main application container
    const appContainer = document.getElementById('chip-app-container');
    if (!appContainer) {
        console.error("CHIP Critical Error: Main application container #chip-app-container not found. App cannot initialize.");
        // Optionally, display a message to the user within a known, simple part of the page if possible
        // document.body.innerHTML = '<p style="color:red; text-align:center; font-size:18px;">CHIP Application Error: Main container not found.</p>' + document.body.innerHTML;
        return; // Stop execution if the main container isn't there
    }

    // DOM Element References - Always use document.getElementById for unique IDs
    const skillButtons = document.querySelectorAll('#chip-app-container .skill-button'); // Scoped querySelectorAll
    const aiResponseDisplay = document.getElementById('ai-response-display');
    const chatHistoryDisplay = document.getElementById('chatHistoryDisplay');
    const chatInput = document.getElementById('chat-input');
    const sendButton = document.getElementById('send-button');
    const chipCharacterImage = document.getElementById('chip-character-image');
    const instructionsContent = document.getElementById('instructionsContent');
    const skillActionButtonContainer = document.getElementById('skillActionButtonContainer');
    const clearHistoryButton = document.getElementById('clearHistoryButton');

    // Check if essential elements exist to prevent further errors
    const essentialElements = {
        aiResponseDisplay, chatHistoryDisplay, chatInput, sendButton,
        chipCharacterImage, instructionsContent, skillActionButtonContainer, clearHistoryButton
    };

    for (const key in essentialElements) {
        if (!essentialElements[key]) {
            console.error(`CHIP Error: Essential UI element with ID corresponding to '${key}' is missing. App functionality will be limited. Please check HTML structure for the element that should be linked to this variable.`);
        }
    }
    if (skillButtons.length === 0) {
         console.warn("CHIP Warning: No skill buttons found with class .skill-button inside #chip-app-container.");
    }


    // Application State
    let ALL_PROMPTS = [];
    let currentSkill = 'Clarifying'; // Default skill
    let currentPromptId = null;
    let currentPromptDetails = null;
    let conversationHistory = [];
    let currentExhibitIndex = 0;
    let doneAsking = false;
    let hypothesisCount = 0;

    // Configuration URLs
    const OPENAI_PROXY_URL = 'https://chip.zoran-a18.workers.dev/';
    const PROMPTS_JSON_URL = 'https://raw.githubusercontent.com/9611io/CHIP/main/prompts.json';

    // CHIP Character Images
    const chipImages = {
        default: "https://9611.io/wp-content/uploads/2025/05/CHIP-wait.png",
        waiting: "https://9611.io/wp-content/uploads/2025/05/CHIP-wait.png",
        talking: "https://9611.io/wp-content/uploads/2025/05/CHIP-talk.png",
        writing: "https://9611.io/wp-content/uploads/2025/05/CHIP-write.png",
        listening: "https://9611.io/wp-content/uploads/2025/05/CHIP-looking-forward-notepad.png",
        thinking: "https://9611.io/wp-content/uploads/2025/05/CHIP-think.png",
        feedback: "https://9611.io/wp-content/uploads/2025/05/CHIP-fb.png",
        clapping: "https://9611.io/wp-content/uploads/2025/05/CHIP-clapping.png",
        pointingUpward: "https://9611.io/wp-content/uploads/2025/05/CHIP-talk.png"
    };
    const chipAvatarSmall = "https://placehold.co/40x40/007ACC/FFFFFF?text=C&font=Inter&bold";

    const skillInstructions = {
        "Clarifying": "Read the prompt, then enter your clarifying questions one at a time. Press \"Send\" to submit. When satisfied, click the \"End Clarification Questions\" button in this panel.",
        "Hypothesis": "Formulate an initial hypothesis and what you'd like to investigate. CHIP will provide info. Refine up to 3 times. Click the \"End Hypothesis Formulation\" button in this panel when finished.",
        "Frameworks": "Outline your framework and proposed approach. When satisfied, press the \"Submit Framework for Feedback\" button that will appear in this panel.",
        "Analysis": "Analyze the exhibit(s) and explain its significance. Enter your analysis and click \"Submit Analysis\". For multiple exhibits, you'll proceed sequentially until the final one. The submit button will appear in this panel.",
        "Recommendation": "Review the case and findings, then structure your final recommendation (rationale, risks, next steps). Click the \"Submit Recommendation\" button that will appear in this panel."
    };

    // --- UI Update Functions ---
    function updateInstructions(skill) {
        if (instructionsContent) {
            instructionsContent.innerHTML = `<p>${skillInstructions[skill] || "Select a skill to see instructions."}</p>`;
        } else {
            console.warn("CHIP: instructionsContent element not found for updating instructions.");
        }
    }

    function setChipCharacterPose(pose) {
        if (chipCharacterImage) {
            chipCharacterImage.src = chipImages[pose] || chipImages.default;
        } else {
            console.warn("CHIP: chipCharacterImage element not found for setting pose.");
        }
    }

    function resetSkillState() {
        console.log("Resetting skill state for:", currentSkill);
        conversationHistory = [];
        currentPromptId = null;
        currentPromptDetails = null;
        currentExhibitIndex = 0;
        doneAsking = false;
        hypothesisCount = 0;
        if (aiResponseDisplay) aiResponseDisplay.innerHTML = '';
        if (skillActionButtonContainer) skillActionButtonContainer.innerHTML = '';
    }

    function createSkillActionButton(text, id, onClickHandler) {
        if (!skillActionButtonContainer) {
            console.warn("CHIP: skillActionButtonContainer element not found.");
            return;
        }
        skillActionButtonContainer.innerHTML = '';
        const button = document.createElement('button');
        button.id = id;
        button.textContent = text;
        button.classList.add('action-button');
        button.addEventListener('click', onClickHandler);
        skillActionButtonContainer.appendChild(button);
    }

    // --- Skill-Specific Action Handlers ---
    function handleEndClarifying() {
        console.log("Ending Clarifying Questions");
        doneAsking = true;
        if(skillActionButtonContainer) skillActionButtonContainer.innerHTML = '';
        setChipCharacterPose('feedback');
        displayAiResponseInMain(`<div class="bot-bubble-main-content-wrapper"><p class="p-4">Clarifying questions ended. Generating feedback...</p></div>`);
    }

    function handleEndHypothesis() {
        console.log("Ending Hypothesis Formulation");
        doneAsking = true;
        if(skillActionButtonContainer) skillActionButtonContainer.innerHTML = '';
        setChipCharacterPose('feedback');
        displayAiResponseInMain(`<div class="bot-bubble-main-content-wrapper"><p class="p-4">Hypothesis formulation ended. Generating feedback...</p></div>`);
    }

    function handleSubmitFramework() {
        console.log("Framework Submitted");
        doneAsking = true;
        if(skillActionButtonContainer) skillActionButtonContainer.innerHTML = '';
        setChipCharacterPose('feedback');
        displayAiResponseInMain(`<div class="bot-bubble-main-content-wrapper"><p class="p-4">Framework submitted. Generating feedback...</p></div>`);
    }
    function handleSubmitAnalysis() {
        console.log("Analysis Submitted");
        doneAsking = true;
        if(skillActionButtonContainer) skillActionButtonContainer.innerHTML = '';
        setChipCharacterPose('feedback');
        displayAiResponseInMain(`<div class="bot-bubble-main-content-wrapper"><p class="p-4">Analysis submitted. Generating feedback...</p></div>`);
    }
    function handleSubmitRecommendation() {
        console.log("Recommendation Submitted");
        doneAsking = true;
        if(skillActionButtonContainer) skillActionButtonContainer.innerHTML = '';
        setChipCharacterPose('feedback');
        displayAiResponseInMain(`<div class="bot-bubble-main-content-wrapper"><p class="p-4">Recommendation submitted. Generating feedback...</p></div>`);
    }
    
    function handleClearHistory() {
        if (chatHistoryDisplay) chatHistoryDisplay.innerHTML = '';
        conversationHistory = [];
        console.log("Chat history cleared.");
    }


    // --- Prompt Loading and Management ---
    function selectNewPromptJS() {
        if (!ALL_PROMPTS || ALL_PROMPTS.length === 0) {
            console.error("CHIP: ALL_PROMPTS is empty or not loaded.");
            return null;
        }
        const skillPrompts = ALL_PROMPTS.filter(p => p.skill_type === currentSkill);
        if (!skillPrompts.length) {
            console.error("CHIP: No prompts found for skill:", currentSkill);
            displayAiResponseInMain(`<div class="bot-bubble-main-content-wrapper"><p style="color:red; padding:1rem;">Error: No prompts found for ${currentSkill}.</p></div>`);
            return null;
        }
        const randomIndex = Math.floor(Math.random() * skillPrompts.length);
        currentPromptId = skillPrompts[randomIndex].id;
        console.log("Selected prompt ID:", currentPromptId, "for skill:", currentSkill);
        return currentPromptId;
    }

    function getPromptDetailsJS(promptId) {
        if (!ALL_PROMPTS) {
            console.error("CHIP: ALL_PROMPTS not loaded during getPromptDetailsJS.");
            return null;
        }
        currentPromptDetails = ALL_PROMPTS.find(p => p.id === promptId);
        return currentPromptDetails;
    }

    function initializeSkill(skillName) {
        currentSkill = skillName;
        resetSkillState();
        updateInstructions(currentSkill);
        selectNewPromptJS();

        if (currentPromptId) {
            getPromptDetailsJS(currentPromptId);
            if (currentPromptDetails) {
                displayCurrentPromptAndExhibit();
                if (currentSkill === "Clarifying" && !doneAsking) {
                    createSkillActionButton("End Clarification Questions", "end-clarifying-btn", handleEndClarifying);
                } else if (currentSkill === "Hypothesis" && !doneAsking) {
                    if (hypothesisCount < 3) {
                        createSkillActionButton("End Hypothesis Formulation", "end-hypothesis-btn", handleEndHypothesis);
                    }
                } else if (currentSkill === "Frameworks" && !doneAsking) {
                    createSkillActionButton("Submit Framework", "submit-framework-btn", handleSubmitFramework);
                } else if (currentSkill === "Analysis" && !doneAsking) {
                    createSkillActionButton("Submit Analysis", "submit-analysis-btn", handleSubmitAnalysis);
                } else if (currentSkill === "Recommendation" && !doneAsking) {
                    createSkillActionButton("Submit Recommendation", "submit-recommendation-btn", handleSubmitRecommendation);
                }
            } else {
                displayAiResponseInMain(`<div class="bot-bubble-main-content-wrapper"><p style="color:red; padding:1rem;">Error: Could not load details for the selected prompt.</p></div>`);
            }
        } else {
            // This case is usually handled by selectNewPromptJS if no prompts are found for the skill.
            // displayAiResponseInMain might have already shown an error.
        }
        setChipCharacterPose('waiting');
    }

    async function loadPrompts() {
        console.log("CHIP: Attempting to load prompts from:", PROMPTS_JSON_URL);
        try {
            const response = await fetch(PROMPTS_JSON_URL);
            if (!response.ok) {
                throw new Error(`HTTP error loading prompts! Status: ${response.status} from ${PROMPTS_JSON_URL}`);
            }
            ALL_PROMPTS = await response.json();
            if (!Array.isArray(ALL_PROMPTS) || ALL_PROMPTS.length === 0) {
                throw new Error("Prompts data is not a valid array or is empty.");
            }
            console.log("CHIP: Prompts loaded successfully:", ALL_PROMPTS.length, "prompts found.");

            const activeButton = document.querySelector('#chip-app-container .skill-button.active'); //Scoped
            if (activeButton) {
                currentSkill = activeButton.textContent.trim();
            }
            initializeSkill(currentSkill);
        } catch (error) {
            console.error("CHIP: Could not load or parse prompts:", error);
            displayAiResponseInMain(`<div class="bot-bubble-main-content-wrapper"><p style="color:red; padding:1rem;">Error: Could not load practice cases. Check console (F12) and ensure prompts.json URL is correct & accessible (CORS).</p></div>`);
        }
    }

    // --- Display Logic for Prompts, Exhibits, and Chat ---
    function displayCurrentPromptAndExhibit() {
        if (!currentPromptDetails || !aiResponseDisplay) {
            if (aiResponseDisplay) aiResponseDisplay.innerHTML = `<div class="bot-bubble-main-content-wrapper"><p style="color:red; padding:1rem;">No prompt selected or details available.</p></div>`;
            else console.error("CHIP: aiResponseDisplay element not found when trying to display prompt.");
            return;
        }

        let htmlContent = `<div class="bot-bubble-main-content-wrapper">`;
        htmlContent += `<p class="font-semibold mb-1 text-lg p-4" style="color: var(--color-accent-primary);">${currentPromptDetails.title || 'Case Prompt'}</p>`;

        if (currentPromptDetails.prompt_text) {
            const paragraphs = currentPromptDetails.prompt_text.split('\n\n');
            paragraphs.forEach((paraText, index) => {
                const pElement = document.createElement('p');
                pElement.classList.add('text-sm', 'px-4');
                pElement.classList.toggle('pt-0', index === 0 && !!(currentPromptDetails.title)); // More robust check
                pElement.classList.toggle('pb-2', index === 0 && !!(currentPromptDetails.title));
                pElement.classList.toggle('py-2', !(index === 0 && !!(currentPromptDetails.title)));
                pElement.style.color = 'var(--color-text-medium)';
                pElement.textContent = paraText;
                htmlContent += pElement.outerHTML;
            });
        }

        if (currentPromptDetails.exhibits && currentPromptDetails.exhibits.length > 0) {
            const exhibitsToShow = (currentSkill === 'Analysis') ?
                                 (currentPromptDetails.exhibits[currentExhibitIndex] ? [currentPromptDetails.exhibits[currentExhibitIndex]] : []) :
                                 currentPromptDetails.exhibits;

            exhibitsToShow.forEach((exhibit, idx) => {
                if (!exhibit) return;
                const exhibitNumber = (currentSkill === 'Analysis') ? currentExhibitIndex + 1 : idx + 1;
                let exhibitHtml = `<div class="exhibit-container mx-4 mb-4">`; // Tailwind classes for margin
                exhibitHtml += `<p class="font-semibold text-base mb-1" style="color: var(--color-accent-primary);">${exhibit.exhibit_title || `Exhibit ${exhibitNumber}`}</p>`;
                if (exhibit.description) {
                    exhibitHtml += `<p class="text-xs mb-1" style="color: var(--color-text-dark);">${exhibit.description}</p>`;
                }

                if (exhibit.chart_type === 'table' && exhibit.data) {
                    exhibitHtml += '<table class="w-full text-sm text-left" style="color: var(--color-text-secondary);">'; // Tailwind class
                    const headers = Object.keys(exhibit.data);
                    if (headers.length > 0 && Array.isArray(exhibit.data[headers[0]])) {
                        exhibitHtml += '<thead class="text-xs uppercase" style="color: var(--color-text-dark);"><tr>';
                        const numericHeaders = ['Previous Year', 'Last Year', 'Market Share %', 'Break-Even Volume (000s)', 'Projected Profit ($M)', 'Revenue Change (%)', 'Daily Active Users (000s)', 'Satisfaction Score', 'Utilization %', 'Idle Time (min)', 'Bookings (000s)', 'Cancellation %', 'Score', 'Units', 'Revenue', 'Share %', 'New Subs', 'Churn %', 'Return %', 'Avg Rides', 'Uplift %', 'Sales (000s)', 'Wait Time', 'Avg Wait', 'Demand (MW)', 'Alerts', 'FPR %', 'Accuracy %', 'Cost', 'Downtime', 'Improvement %', 'Completion %', 'Avg Time (min)', 'On-Time %', 'CTR %', 'Impressions (000s)', 'Emissions', 'Target %', 'AQI', 'Attendees', 'Conversion %', 'Abandoned', 'Rating', 'Cost ($k)', 'Days', 'Fulfilled (000s)', 'Avg Days', 'Count', 'Avg Time (hrs)', 'Subscriptions (000s)', 'Yield', 'Members (000s)', 'Logins (000s)'];
                        headers.forEach(header => {
                            const isNumeric = numericHeaders.includes(header) || header.endsWith('(000s)') || header.endsWith('%') || header.endsWith('($k)') || header.endsWith('(min)') || header.endsWith('(hrs)');
                            exhibitHtml += `<th scope="col" class="py-1 px-2 ${isNumeric ? 'text-right' : ''}">${header}</th>`; // Tailwind classes
                        });
                        exhibitHtml += '</tr></thead><tbody>';
                        const numRows = exhibit.data[headers[0]].length;
                        for (let i = 0; i < numRows; i++) {
                            exhibitHtml += `<tr class="border-b" style="border-color: var(--color-border);">`; // Tailwind class
                            headers.forEach(header => {
                                const isNumeric = numericHeaders.includes(header) || typeof exhibit.data[header][i] === 'number';
                                exhibitHtml += `<td class="py-1 px-2 ${isNumeric ? 'text-right' : ''}">${exhibit.data[header][i]}</td>`; // Tailwind classes
                            });
                            exhibitHtml += `</tr>`;
                        }
                        exhibitHtml += '</tbody>';
                    }
                    exhibitHtml += '</table>';
                } else if (exhibit.summary_text) {
                    if (Array.isArray(exhibit.summary_text)) {
                        exhibitHtml += '<ul class="list-disc list-inside pl-4 text-sm" style="color: var(--color-text-medium);">'; // Tailwind classes
                        exhibit.summary_text.forEach(itemText => exhibitHtml += `<li>${itemText}</li>`);
                        exhibitHtml += '</ul>';
                    } else {
                        exhibitHtml += `<p class="text-sm" style="color: var(--color-text-medium);">${exhibit.summary_text}</p>`; // Tailwind class
                    }
                } else if (exhibit.chart_type && exhibit.chart_type !== 'table' && exhibit.data) {
                    exhibitHtml += `<div id="plotly-chart-exhibit-${exhibitNumber}" class="mt-2" style="min-height: 300px;"></div>`; // Tailwind class
                }
                exhibitHtml += `</div>`;
                htmlContent += exhibitHtml;
            });
        }
        htmlContent += `</div>`;
        displayAiResponseInMain(htmlContent);

        if (currentPromptDetails.exhibits && currentPromptDetails.exhibits.length > 0) {
            const exhibitsToRender = (currentSkill === 'Analysis') ?
                                 (currentPromptDetails.exhibits[currentExhibitIndex] ? [currentPromptDetails.exhibits[currentExhibitIndex]] : []) :
                                 currentPromptDetails.exhibits;
            exhibitsToRender.forEach((exhibit, idx) => {
                 if (!exhibit) return;
                 const exhibitNumber = (currentSkill === 'Analysis') ? currentExhibitIndex + 1 : idx + 1;
                 if (exhibit.chart_type && exhibit.chart_type !== 'table' && exhibit.data && typeof Plotly !== 'undefined') {
                     renderPlotlyChart(exhibit, exhibitNumber);
                 }
            });
        }
    }

    function renderPlotlyChart(exhibit, exhibitNumber) {
        const chartDivId = `plotly-chart-exhibit-${exhibitNumber}`;
        const chartDiv = document.getElementById(chartDivId); // Use document.getElementById
        if (!chartDiv) {
            console.error("CHIP: Chart div not found:", chartDivId);
            return;
        }

        let plotData = [];
        let layout = {
            title: { text: exhibit.exhibit_title || '', font: { color: 'var(--color-text-lightest)'}},
            paper_bgcolor: 'var(--color-bg-content-panels)',
            plot_bgcolor: 'var(--color-bg-content-panels)',
            font: { color: 'var(--color-text-lightest)' },
            xaxis: {
                title: { text: exhibit.x_axis || '', font: {color: 'var(--color-text-medium)'}},
                gridcolor: 'var(--color-border)',
                tickfont: {color: 'var(--color-text-medium)'}
            },
            yaxis: {
                title: { text: Array.isArray(exhibit.y_axis) ? exhibit.y_axis.join(', ') : exhibit.y_axis || '', font: {color: 'var(--color-text-medium)'}},
                gridcolor: 'var(--color-border)',
                tickfont: {color: 'var(--color-text-medium)'}
            },
            legend: { font: { color: 'var(--color-text-lightest)'}},
            margin: { l: 50, r: 20, t: 50, b: 50 }
        };

        try {
            if (exhibit.chart_type === 'bar' && exhibit.data && exhibit.x_axis && exhibit.y_axis) {
                const xValues = exhibit.data[exhibit.x_axis];
                (Array.isArray(exhibit.y_axis) ? exhibit.y_axis : [exhibit.y_axis]).forEach(yKey => {
                    if(exhibit.data[yKey]) { // Ensure yKey data exists
                        plotData.push({
                            x: xValues, y: exhibit.data[yKey], type: 'bar', name: yKey,
                            marker: {color: plotData.length % 2 === 0 ? 'var(--color-accent-primary)' : 'var(--color-accent-secondary)'}
                        });
                    } else {
                        console.warn(`CHIP: Data for y-axis key "${yKey}" not found in exhibit data for bar chart.`);
                    }
                });
                layout.barmode = 'group';
            } else if (exhibit.chart_type === 'line' && exhibit.data && exhibit.x_axis && exhibit.y_axis) {
                const xValues = exhibit.data[exhibit.x_axis];
                (Array.isArray(exhibit.y_axis) ? exhibit.y_axis : [exhibit.y_axis]).forEach(yKey => {
                     if(exhibit.data[yKey]) { // Ensure yKey data exists
                        plotData.push({
                            x: xValues, y: exhibit.data[yKey], type: 'scatter', mode: 'lines+markers', name: yKey,
                            line: {color: plotData.length % 2 === 0 ? 'var(--color-accent-primary)' : 'var(--color-accent-secondary)'}
                        });
                    } else {
                        console.warn(`CHIP: Data for y-axis key "${yKey}" not found in exhibit data for line chart.`);
                    }
                });
            } else if (exhibit.chart_type === 'pie' && exhibit.data && exhibit.names && exhibit.values) {
                 if(exhibit.data[exhibit.names] && exhibit.data[exhibit.values]) { // Ensure data exists
                    plotData.push({
                        labels: exhibit.data[exhibit.names], values: exhibit.data[exhibit.values], type: 'pie', hole: 0.4,
                        marker: { colors: [ 'var(--color-accent-primary)', 'var(--color-accent-secondary)', '#FFBF00', '#4A3B31', '#6B7280']}
                    });
                    layout.showlegend = true;
                } else {
                     console.warn(`CHIP: Data for names key "${exhibit.names}" or values key "${exhibit.values}" not found for pie chart.`);
                }
            }

            if (plotData.length > 0) {
                Plotly.newPlot(chartDivId, plotData, layout, {responsive: true});
            } else {
                chartDiv.innerHTML = `<p class="text-sm p-2" style="color: var(--color-text-medium);">Chart data for '${exhibit.chart_type}' is misconfigured, not supported, or data is missing.</p>`;
            }
        } catch (e) {
            console.error("CHIP: Error rendering Plotly chart:", e);
            chartDiv.innerHTML = `<p class="text-sm p-2" style="color:red;">Error rendering chart. Check console.</p>`;
        }
    }

    function addMessageToHistory(text, sender) {
        if (!chatHistoryDisplay) {
            console.warn("CHIP: chatHistoryDisplay element not found.");
            return;
        }
        const messageWrapper = document.createElement('div');
        messageWrapper.classList.add('flex', 'items-start', 'space-x-2', 'mb-3'); // Tailwind classes

        const avatarContainer = document.createElement('div');
        avatarContainer.classList.add('w-7', 'h-7', 'rounded-full', 'flex', 'items-center', 'justify-center', 'text-white', 'font-bold', 'text-xs', 'shrink-0'); // Tailwind classes

        const bubbleDiv = document.createElement('div');
        bubbleDiv.classList.add('chat-bubble');
        bubbleDiv.textContent = text;

        if (sender === 'user') {
            messageWrapper.classList.add('justify-end'); // Tailwind class
            avatarContainer.style.backgroundColor = 'var(--color-accent-secondary)';
            avatarContainer.style.color = 'var(--color-text-on-secondary-accent)';
            avatarContainer.textContent = 'U';
            bubbleDiv.classList.add('user-bubble-history');
            messageWrapper.appendChild(bubbleDiv);
            messageWrapper.appendChild(avatarContainer);
        } else { // AI/Bot
            avatarContainer.style.backgroundColor = 'transparent';
            const chipAvatarImg = document.createElement('img');
            chipAvatarImg.src = chipAvatarSmall;
            chipAvatarImg.alt = "CHIP";
            chipAvatarImg.classList.add('w-full', 'h-full', 'rounded-full', 'object-cover'); // Tailwind classes
            avatarContainer.innerHTML = '';
            avatarContainer.appendChild(chipAvatarImg);
            bubbleDiv.classList.add('bot-bubble-history');
            messageWrapper.appendChild(avatarContainer);
            messageWrapper.appendChild(bubbleDiv);
        }
        chatHistoryDisplay.appendChild(messageWrapper);
        chatHistoryDisplay.scrollTop = chatHistoryDisplay.scrollHeight;
    }

    function displayAiResponseInMain(htmlContent) {
        if (!aiResponseDisplay) {
            console.warn("CHIP: aiResponseDisplay element not found for displaying main response.");
            return;
        }
        aiResponseDisplay.innerHTML = htmlContent;
        aiResponseDisplay.scrollTop = aiResponseDisplay.scrollHeight;
        if (htmlContent && !htmlContent.includes("CHIP is typing...")) {
            setChipCharacterPose('talking');
        }
    }

    function displayTypingIndicator() {
        setChipCharacterPose('thinking');
        displayAiResponseInMain(`<div class="bot-bubble-main-content-wrapper"><p class="text-[var(--color-text-medium)] italic p-4">CHIP is typing...</p></div>`);
    }

    // --- Event Listeners ---
    if (skillButtons.length > 0) {
        skillButtons.forEach(button => {
            button.addEventListener('click', () => {
                skillButtons.forEach(btn => btn.classList.remove('active'));
                button.classList.add('active');
                initializeSkill(button.textContent.trim());
            });
        });
    }


    if (sendButton) {
        sendButton.addEventListener('click', () => {
            if (!chatInput) {
                console.warn("CHIP: chatInput element not found for send button.");
                return;
            }
            const messageText = chatInput.value.trim();
            if (messageText) {
                addMessageToHistory(messageText, 'user');
                conversationHistory.push({ role: 'user', content: messageText });
                chatInput.value = '';
                displayTypingIndicator();

                setTimeout(() => {
                    const placeholderAiResponse = `This is a placeholder CHIP response to: "${messageText}". Actual interaction would involve calling the AI for skill "${currentSkill}".`;
                    displayAiResponseInMain(`<div class="bot-bubble-main-content-wrapper"><p class="p-4">${placeholderAiResponse}</p></div>`);
                    addMessageToHistory(placeholderAiResponse, 'bot');
                    conversationHistory.push({ role: 'assistant', content: placeholderAiResponse });
                    setChipCharacterPose('waiting');
                }, 1500);
            }
        });
    } else {
        console.warn("CHIP: Send button not found.");
    }

    if (chatInput) {
        chatInput.addEventListener('keypress', function (e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                if (sendButton) sendButton.click();
            }
        });
    } else {
        console.warn("CHIP: Chat input field not found.");
    }
    
    if (clearHistoryButton) {
        clearHistoryButton.addEventListener('click', handleClearHistory);
    } else {
        console.warn("CHIP: Clear history button not found.");
    }


    // --- Initial Setup ---
    loadPrompts(); 

    displayAiResponseInMain(`
        <div class="bot-bubble-main-content-wrapper">
            <p class="font-semibold mb-1 text-lg p-4" style="color: var(--color-accent-primary);">Welcome to CHIP!</p>
            <p class="p-4 pt-0" style="color: var(--color-text-lightest);">I'm CHIP, your personal case interview practice partner. Select a skill from the top to begin.</p>
            <p class="mt-2 text-sm p-4 pt-0" style="color: var(--color-text-secondary);">Loading practice cases...</p>
        </div>
    `);
    updateInstructions(currentSkill);

}); // End of DOMContentLoaded
