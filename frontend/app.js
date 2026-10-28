// State Management
const state = {
    currentIntern: null,
    masterTask: null,
    reviewSchedule: [],
    emails: [],
    isSpeaking: false,
    synthVoice: null,
    theme: 'dark'
};

// Initialize app on load
window.addEventListener('DOMContentLoaded', async () => {
    initTheme();
    initSpeechSynthesis();
    await loadInitialSettingsAndTask();
    // Keep chatbot clean & plain in the starting: ask intern to enter their name first
    renderInitialPromptScreen();
    await loadEmailLogs();
    lucide.createIcons();
});

// View Switcher
function switchView(viewName) {
    const chatView = document.getElementById('view-chat');
    const inboxView = document.getElementById('view-inbox');
    const adminView = document.getElementById('view-admin');

    const btnChat = document.getElementById('tab-btn-chat');
    const btnInbox = document.getElementById('tab-btn-inbox');
    const btnAdmin = document.getElementById('tab-btn-admin');

    // Reset buttons
    [btnChat, btnInbox, btnAdmin].forEach(btn => {
        btn.className = "flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold text-slate-400 hover:text-slate-200 transition-all";
    });

    chatView.classList.add('hidden');
    inboxView.classList.add('hidden');
    adminView.classList.add('hidden');

    if (viewName === 'chat') {
        chatView.classList.remove('hidden');
        btnChat.className = "flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all bg-brand-600 text-white shadow-sm";
    } else if (viewName === 'inbox') {
        inboxView.classList.remove('hidden');
        btnInbox.className = "flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all bg-brand-600 text-white shadow-sm";
        loadEmailLogs();
    } else if (viewName === 'admin') {
        adminView.classList.remove('hidden');
        btnAdmin.className = "flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all bg-brand-600 text-white shadow-sm";
        loadAdminDashboard();
    }
    lucide.createIcons();
}

// -------------------------------------------------------------
// INITIAL PLAIN CHAT SCREEN (Ask intern name on startup)
// -------------------------------------------------------------
function renderInitialPromptScreen() {
    state.currentIntern = null;
    state.reviewSchedule = [];

    // Header pill
    const headerName = document.getElementById('header-user-name');
    const headerStage = document.getElementById('header-user-stage');
    if (headerName) headerName.innerText = 'Guest';
    if (headerStage) headerStage.innerText = 'Not Verified';

    // Intern card reset to clean awaiting state
    const avatar = document.getElementById('intern-avatar-initials');
    if (avatar) avatar.innerText = '?';

    const cardName = document.getElementById('intern-card-name');
    if (cardName) cardName.querySelector('span').innerText = 'Welcome, Intern';

    const role = document.getElementById('intern-card-role');
    if (role) role.innerText = 'Please enter your name in chat to begin';

    const doj = document.getElementById('intern-card-doj');
    if (doj) {
        doj.innerText = 'Pending Verification';
        doj.className = 'font-bold text-slate-400 font-mono text-xs';
    }

    const idEl = document.getElementById('intern-card-id');
    if (idEl) idEl.innerText = '----';

    const deptEl = document.getElementById('intern-card-dept');
    if (deptEl) deptEl.innerText = 'Engineering';

    const mentorEl = document.getElementById('intern-card-mentor');
    if (mentorEl) mentorEl.innerText = 'Assigned after verification';

    const badge = document.getElementById('intern-status-badge');
    if (badge) {
        badge.innerText = 'AWAITING IDENTIFICATION';
        badge.className = 'text-[10px] font-bold px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 border border-slate-700';
    }

    const certBox = document.getElementById('certificate-unlock-box');
    if (certBox) certBox.classList.add('hidden');

    // Clean placeholder in timeline roadmap
    const timelineContainer = document.getElementById('timeline-container');
    if (timelineContainer) {
        timelineContainer.innerHTML = `
            <div class="p-6 text-center text-xs text-slate-400 border border-dashed border-slate-800 rounded-xl bg-slate-900/30">
                <div class="w-10 h-10 rounded-full bg-slate-800 text-brand-400 flex items-center justify-center mx-auto mb-2.5">
                    <i data-lucide="user" class="w-5 h-5"></i>
                </div>
                <div class="font-bold text-white text-xs">Awaiting Intern Name</div>
                <p class="text-[11px] text-slate-500 mt-1 max-w-[220px] mx-auto leading-relaxed">
                    Type your full name in the chat to load your official review milestones &amp; schedule.
                </p>
            </div>
        `;
    }

    // Keep the chatbot clean & plain: single prompt asking the intern to enter their name
    const chatContainer = document.getElementById('chat-messages-container');
    if (chatContainer) {
        chatContainer.innerHTML = '';
        appendBotMessage(`
            <div class="space-y-3">
                <div class="flex items-center gap-2 text-brand-400 font-bold text-sm">
                    <i data-lucide="sparkles" class="w-4 h-4"></i>
                    <span>Welcome to the Autonomous Review System</span>
                </div>
                <p class="text-xs text-slate-300 leading-relaxed">
                    Hello! I am your AI Review &amp; Evaluation Mentor. To get started and view your assigned project details, official Date of Joining (DOJ), and dynamic review schedule:
                </p>
                <div class="bg-gradient-to-r from-brand-950/60 to-purple-950/40 p-3.5 rounded-xl border border-brand-500/30 flex items-center gap-3">
                    <div class="w-9 h-9 rounded-lg bg-brand-600/30 text-brand-300 flex items-center justify-center shrink-0">
                        <i data-lucide="user-check" class="w-5 h-5"></i>
                    </div>
                    <div>
                        <div class="text-xs font-bold text-white">Please enter your full name below:</div>
                        <div class="text-[11px] text-slate-400 mt-0.5">Type your name (or Intern ID / email) in the message box below to view your details.</div>
                    </div>
                </div>
            </div>
        `);
    }

    // Reset chat input field and placeholder
    const chatInput = document.getElementById('chat-input-field');
    if (chatInput) {
        chatInput.value = '';
        chatInput.placeholder = 'Type your name (e.g. Nithish Kumar M, Aarav Sharma)...';
        chatInput.focus();
    }

    if (window.lucide) lucide.createIcons();
}

// -------------------------------------------------------------
// 1. INITIALIZATION & DATE OF DOJ (Core Requirement 1)
// -------------------------------------------------------------
async function verifyInternByName(nameQuery) {
    try {
        const res = await fetch('/api/interns/verify', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query: nameQuery })
        });

        if (!res.ok) {
            const err = await res.json();
            appendBotMessage(`
                <div class="space-y-2">
                    <div class="text-amber-400 font-bold flex items-center gap-1.5 text-xs">
                        <i data-lucide="alert-circle" class="w-4 h-4"></i>
                        <span>Intern Record Not Found</span>
                    </div>
                    <p class="text-xs text-slate-300">
                        Could not find an intern record matching "<strong>${escapeHtml(nameQuery)}</strong>".
                    </p>
                    <p class="text-[11px] text-slate-400">
                        Please check spelling, select from registered interns below, or register as a new candidate:
                    </p>
                    <div class="pt-1 flex items-center gap-2">
                        <button onclick="openRegistrationModal('${escapeHtml(nameQuery)}')" class="bg-brand-600 hover:bg-brand-500 text-white font-bold px-3 py-1.5 rounded-lg text-xs flex items-center gap-1 shadow">
                            <i data-lucide="user-plus" class="w-3.5 h-3.5"></i>
                            <span>Register as New Intern</span>
                        </button>
                    </div>
                </div>
            `);
            if (window.lucide) lucide.createIcons();
            return false;
        }

        const data = await res.json();
        state.currentIntern = data.intern;
        state.masterTask = data.assigned_task;
        state.reviewSchedule = data.review_schedule;

        updateInternProfileUI();
        renderTimelineRoadmap();

        // 2. TASK ALLOCATION & BRIEFING (Core Requirement 2)
        displayWelcomeAndTaskBriefing(data.message);
        return true;
    } catch (e) {
        console.error("Verification error:", e);
        appendBotMessage(`⚠️ Connection error: Failed to reach backend API. Ensure server is active.`);
        return false;
    }
}

function updateInternProfileUI() {
    const intern = state.currentIntern;
    if (!intern) return;

    // Header pill
    document.getElementById('header-user-name').innerText = intern.name;
    document.getElementById('header-user-stage').innerText = intern.status === 'COMPLETED' ? 'Completed 🎓' : `Stage ${intern.current_review_stage}`;

    // Intern card
    document.getElementById('intern-card-name').querySelector('span').innerText = intern.name;
    document.getElementById('intern-card-role').innerText = intern.role;
    document.getElementById('intern-card-doj').innerText = intern.doj;
    document.getElementById('intern-card-id').innerText = intern.intern_id;
    document.getElementById('intern-card-dept').innerText = intern.department;
    document.getElementById('intern-card-mentor').innerText = intern.mentor_name;

    const initials = intern.name.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase();
    document.getElementById('intern-avatar-initials').innerText = initials;

    // Status badge
    const badge = document.getElementById('intern-status-badge');
    if (intern.status === 'COMPLETED') {
        badge.innerText = 'GRADUATED 🏆';
        badge.className = 'text-[10px] font-bold px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-400 border border-amber-500/30';
        document.getElementById('certificate-unlock-box').classList.remove('hidden');
    } else {
        badge.innerText = 'ACTIVE';
        badge.className = 'text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/30';
        document.getElementById('certificate-unlock-box').classList.add('hidden');
    }
}

// -------------------------------------------------------------
// 2. TASK ALLOCATION & BRIEFING (Core Requirement 2)
// -------------------------------------------------------------
function displayWelcomeAndTaskBriefing(customWelcome) {
    const intern = state.currentIntern;
    const task = state.masterTask;
    const container = document.getElementById('chat-messages-container');
    container.innerHTML = ''; // Fresh chat flow for clean briefing

    // Message 1: DOJ Verification Confirmation
    appendBotMessage(`
        <div class="space-y-2">
            <div class="flex items-center gap-2 text-emerald-400 font-bold text-sm">
                <i data-lucide="shield-check" class="w-4 h-4"></i>
                <span>Official Identity &amp; Date of Joining Verified</span>
            </div>
            <p class="text-xs text-slate-300">
                Welcome, <strong>${intern.name}</strong> (Intern ID: <code class="text-indigo-300 font-mono">${intern.intern_id}</code>).
                Your official <strong>Date of Joining (DOJ)</strong> is recorded as <strong class="text-emerald-400 font-mono">${intern.doj}</strong>.
            </p>
        </div>
    `);

    // Message 2: Master Task Allocation & Objectives
    if (task) {
        const briefingText = `
        <div class="space-y-3">
            <div class="flex items-center justify-between border-b border-slate-700/60 pb-2">
                <span class="text-xs font-bold uppercase tracking-wider text-brand-400 flex items-center gap-1.5">
                    <i data-lucide="briefcase" class="w-4 h-4"></i> Assigned Master Task Details
                </span>
                <span class="text-[10px] font-mono px-2 py-0.5 rounded bg-brand-500/20 text-brand-300">Active Milestone</span>
            </div>
            <h4 class="font-extrabold text-sm text-white">${task.title}</h4>
            <div class="text-xs text-slate-300 leading-relaxed bg-slate-900/60 p-3 rounded-xl border border-slate-800">
                <strong class="text-slate-200">Project Scope:</strong><br/>
                ${task.project_scope}
            </div>
            <div class="text-xs text-slate-300 leading-relaxed">
                <strong class="text-slate-200">Core Objectives:</strong>
                <pre class="mt-1 font-sans text-xs text-slate-300 whitespace-pre-wrap bg-slate-950/40 p-2.5 rounded-lg border border-slate-800/80">${task.objectives}</pre>
            </div>
            <div class="text-xs text-slate-400">
                <strong class="text-slate-300">Technology Stack:</strong> ${task.tech_stack}
            </div>
            <div class="bg-indigo-950/30 border border-indigo-500/20 rounded-xl p-3 text-xs text-indigo-200 space-y-1">
                <div class="font-bold flex items-center gap-1.5 text-indigo-300">
                    <i data-lucide="alert-circle" class="w-3.5 h-3.5"></i> Strict Submission Rules:
                </div>
                <p class="text-[11px] text-slate-300">${task.submission_rules}</p>
            </div>
        </div>
        `;
        appendBotMessage(briefingText);

        // Message 3: Active Stage Prompt
        promptActiveStageSubmission();
    }

    const chatInput = document.getElementById('chat-input-field');
    if (chatInput) {
        const stageNum = intern.current_review_stage || 1;
        chatInput.placeholder = `Paste GitHub repository URL or attach .zip for Review Stage ${stageNum}...`;
        chatInput.focus();
    }

    lucide.createIcons();
}

function promptActiveStageSubmission() {
    const intern = state.currentIntern;
    if (intern.status === 'COMPLETED') {
        appendBotMessage(`
            <div class="bg-gradient-to-r from-emerald-950/60 to-slate-900 p-4 rounded-xl border border-emerald-500/30 space-y-2">
                <div class="text-emerald-400 font-bold text-sm flex items-center gap-2">
                    <i data-lucide="check-check" class="w-5 h-5"></i> Internship Program Completed!
                </div>
                <p class="text-xs text-slate-300">
                    You have cleared all ${intern.total_reviews} review stages. Your official certificate is unlocked in the left roadmap.
                </p>
                <button onclick="openCertificateModal()" class="text-xs font-bold px-3 py-1.5 rounded-lg bg-amber-500 hover:bg-amber-400 text-slate-950 flex items-center gap-1.5 shadow">
                    <i data-lucide="award" class="w-3.5 h-3.5"></i> View Certificate
                </button>
            </div>
        `);
        return;
    }

    const activeStage = state.reviewSchedule.find(s => s.stage_number === intern.current_review_stage);
    const stageTitle = activeStage ? activeStage.stage_name : `Review Stage ${intern.current_review_stage}`;
    const meetLink = activeStage ? activeStage.meeting_link : 'https://meet.google.com/review';
    const scheduledDate = activeStage ? activeStage.scheduled_date : 'Upcoming';

    const inviteButtonHtml = intern.current_review_stage === 1 ? `
        <div class="pt-1 flex items-center gap-2">
            <button onclick="dispatchStage1InvitationEmail()" class="text-[11px] font-semibold px-3 py-1.5 rounded-lg bg-indigo-900/60 hover:bg-indigo-800 text-indigo-200 border border-indigo-500/30 flex items-center gap-1.5 transition-colors">
                <i data-lucide="mail" class="w-3.5 h-3.5"></i>
                <span>Dispatch / View Stage 1 Meeting Invitation Email</span>
            </button>
        </div>
    ` : '';

    appendBotMessage(`
        <div class="space-y-2.5">
            <div class="flex items-center gap-2 text-indigo-400 font-bold text-xs uppercase tracking-wide">
                <i data-lucide="target" class="w-4 h-4"></i> Action Required: Stage ${intern.current_review_stage} Submission
            </div>
            <p class="text-xs text-slate-200">
                You are currently on <strong>${stageTitle}</strong>. 
                Scheduled Review Date: <strong class="text-emerald-400 font-mono">${scheduledDate}</strong>.
            </p>
            <div class="bg-slate-900/80 p-2.5 rounded-lg border border-slate-800 text-xs flex items-center justify-between">
                <span class="text-slate-400">Review Meeting Link:</span>
                <a href="${meetLink}" target="_blank" class="text-brand-400 hover:text-brand-300 font-mono flex items-center gap-1 font-bold">
                    ${meetLink} <i data-lucide="external-link" class="w-3 h-3"></i>
                </a>
            </div>
            <p class="text-xs text-slate-400 leading-relaxed">
                Please paste your <strong>GitHub Repository URL</strong> or click <i data-lucide="paperclip" class="w-3 h-3 inline text-brand-400"></i> below to upload your <strong>Task Document / Code Archive (.zip)</strong> to initiate automated AI Evaluation.
            </p>
            ${inviteButtonHtml}
        </div>
    `);
}

// -------------------------------------------------------------
// 3. DYNAMIC N-REVIEW SCHEDULING (10–15 DAY GAPS) (Core Requirement 3)
// -------------------------------------------------------------
function renderTimelineRoadmap() {
    const container = document.getElementById('timeline-container');
    container.innerHTML = '';

    const currentStage = state.currentIntern ? state.currentIntern.current_review_stage : 1;
    const internCompleted = state.currentIntern && state.currentIntern.status === 'COMPLETED';

    if (!state.reviewSchedule || state.reviewSchedule.length === 0) return;

    state.reviewSchedule.forEach((stage, idx) => {
        const isDone = stage.status === 'COMPLETED';
        const isActive = !internCompleted && stage.stage_number === currentStage;
        const isScheduled = !isDone && !isActive;

        let statusBadge = '';
        let cardBg = '';
        let iconMarkup = '';

        if (isDone) {
            statusBadge = `<span class="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">PASSED (${stage.evaluation_score || 90}%)</span>`;
            cardBg = 'bg-slate-900/60 border-slate-800 text-slate-300';
            iconMarkup = `<div class="w-7 h-7 rounded-lg bg-emerald-500/20 text-emerald-400 flex items-center justify-center font-bold text-xs"><i data-lucide="check" class="w-4 h-4"></i></div>`;
        } else if (isActive) {
            statusBadge = `<span class="text-[10px] font-bold px-2 py-0.5 rounded-full bg-brand-500/20 text-brand-300 border border-brand-500/40 animate-pulse">ACTIVE REVIEW</span>`;
            cardBg = 'bg-gradient-to-r from-brand-950/40 to-slate-900 border-brand-500/40 shadow-lg shadow-brand-500/10 text-white';
            iconMarkup = `<div class="w-7 h-7 rounded-lg bg-brand-600 text-white flex items-center justify-center font-bold text-xs">${stage.stage_number}</div>`;
        } else {
            statusBadge = `<span class="text-[10px] font-medium px-2 py-0.5 rounded-full bg-slate-800 text-slate-400">SCHEDULED</span>`;
            cardBg = 'bg-slate-900/40 border-slate-800/80 text-slate-400';
            iconMarkup = `<div class="w-7 h-7 rounded-lg bg-slate-800 text-slate-400 flex items-center justify-center font-bold text-xs">${stage.stage_number}</div>`;
        }

        const stageCard = document.createElement('div');
        stageCard.className = `p-3.5 rounded-xl border transition-all ${cardBg}`;
        stageCard.innerHTML = `
            <div class="flex items-start justify-between gap-2 mb-2">
                <div class="flex items-center gap-2">
                    ${iconMarkup}
                    <div>
                        <div class="font-bold text-xs">${stage.stage_name}</div>
                        <div class="text-[11px] text-slate-400 flex items-center gap-1.5 mt-0.5">
                            <span>📅 ${stage.scheduled_date}</span>
                            <span>&bull;</span>
                            <span>⏰ ${stage.meeting_time}</span>
                        </div>
                    </div>
                </div>
                ${statusBadge}
            </div>

            <div class="flex items-center justify-between text-[11px] border-t border-slate-800/60 pt-2 mt-2">
                <span class="text-slate-400">
                    Gap: <strong class="text-indigo-400">${stage.gap_days} Days</strong>
                </span>
                <a href="${stage.meeting_link}" target="_blank" class="text-brand-400 hover:text-brand-300 flex items-center gap-1 font-mono text-[10px] hover:underline">
                    <span>Google Meet</span>
                    <i data-lucide="external-link" class="w-3 h-3"></i>
                </a>
            </div>
        `;
        container.appendChild(stageCard);
    });

    lucide.createIcons();
}

// -------------------------------------------------------------
// 4. GITHUB SUBMISSION & AI EVALUATION PIPELINE (Core Requirement 4)
// & 5. DUAL DISPATCH & ROLLING LOOP (Core Requirement 5)
// -------------------------------------------------------------
async function handleChatSubmit(e) {
    e.preventDefault();
    const input = document.getElementById('chat-input-field');
    const query = input.value.trim();
    if (!query) return;

    // Display user message in chat
    appendUserMessage(query);
    input.value = '';

    // Check if user is typing a name to switch / verify intern
    if (!query.includes('github.com') && !query.startsWith('http')) {
        // Attempt intern verification
        showTypingIndicator();
        setTimeout(async () => {
            hideTypingIndicator();
            const verified = await verifyInternByName(query);
            if (!verified) {
                appendBotMessage(`💡 If you want to evaluate your work, please paste your GitHub repository link (e.g. <code class="text-brand-300">https://github.com/intern/my-repo</code>).`);
            }
        }, 400);
        return;
    }

    // It's a GitHub URL submission!
    if (!state.currentIntern) {
        appendBotMessage(`⚠️ Please verify your intern name first before submitting code.`);
        return;
    }

    if (state.currentIntern.status === 'COMPLETED') {
        appendBotMessage(`🎉 You have already completed all review stages for this internship! Check your certificate.`);
        return;
    }

    // Trigger AI Evaluation Engine
    showTypingIndicator();

    try {
        const res = await fetch('/api/reviews/submit', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                intern_id: state.currentIntern.intern_id,
                github_url: query
            })
        });

        hideTypingIndicator();

        if (!res.ok) {
            const err = await res.json();
            appendBotMessage(`❌ Evaluation failed: ${err.detail || 'Could not process GitHub repository.'}`);
            return;
        }

        const data = await res.json();

        // Update local state
        state.currentIntern = data.intern;
        state.reviewSchedule = data.review_schedule;
        updateInternProfileUI();
        renderTimelineRoadmap();

        // Render high-fidelity AI Evaluation Report directly in chat
        renderEvaluationResultInChat(data.evaluation, data.email_dispatch, data.next_review, data.is_final_stage);

        // Load new email into inbox simulator
        await loadEmailLogs();

        // If completed all reviews, trigger celebration confetti!
        if (data.is_final_stage) {
            triggerConfetti();
        }

    } catch (err) {
        hideTypingIndicator();
        console.error(err);
        appendBotMessage(`⚠️ Network error occurred while evaluating GitHub submission.`);
    }
}

function renderEvaluationResultInChat(evalData, emailDispatch, nextReview, isFinalStage) {
    const scoreColor = evalData.score >= 85 ? 'text-emerald-400 border-emerald-500/40 bg-emerald-500/10' : 'text-amber-400 border-amber-500/40 bg-amber-500/10';

    // Target label (repo or document)
    const targetLabel = evalData.submission_type === 'DOCUMENT_UPLOAD'
        ? `📄 Document: <span class="text-brand-300 font-mono">${escapeHtml(evalData.submission_target || evalData.item_label)}</span>`
        : `🔗 Repo: <span class="text-brand-300 font-mono">${escapeHtml(evalData.submission_target || evalData.github_url)}</span>`;

    // 1. Completed Modules HTML ("evlo mudichurukanga")
    let completedModulesHtml = (evalData.completed_modules || []).map(mod => `
        <div class="bg-slate-900/70 rounded-lg p-2.5 border border-slate-800 text-xs">
            <div class="flex items-center justify-between font-bold text-slate-200">
                <span>${mod.module}</span>
                <span class="text-emerald-400 font-mono text-[10px] bg-emerald-950/80 px-2 py-0.5 rounded border border-emerald-500/30">
                    ${mod.fulfillment_pct}% Verified
                </span>
            </div>
            <p class="text-[11px] text-slate-400 mt-1">${mod.evidence}</p>
        </div>
    `).join('');

    // 2. Code Corrections HTML ("enna enna corrections iruku")
    let codeCorrectionsHtml = (evalData.code_corrections || []).map(corr => `
        <div class="bg-red-950/30 rounded-lg p-2.5 border border-red-500/30 text-xs space-y-1">
            <div class="flex items-center justify-between">
                <span class="font-bold text-red-300 font-mono text-[10px] bg-red-900/60 px-1.5 py-0.5 rounded">
                    [${corr.severity}] ${corr.file}
                </span>
            </div>
            <p class="text-slate-300 text-[11px]">${corr.issue}</p>
            <div class="text-[11px] text-emerald-300 bg-slate-900/80 p-1.5 rounded border border-slate-800">
                <strong>Recommended Fix:</strong> ${corr.recommendation}
            </div>
        </div>
    `).join('');

    // 3. Missing Components HTML ("enna enna modules miss aayiruku")
    let missingComponentsHtml = (evalData.missing_components || []).map(miss => `
        <li class="text-[11px] text-slate-300">
            <strong>${miss.item}:</strong> ${miss.impact}
            <span class="block text-indigo-400 mt-0.5">&rarr; Resolution: ${miss.action_required}</span>
        </li>
    `).join('');

    // 4. Modules to Add for Next Stage ("enna enna modules add pannanum")
    let modulesToAddHtml = (evalData.modules_to_add || []).map(addMod => {
        const isDone = addMod.priority === 'COMPLETED';
        const badgeColor = isDone ? 'bg-emerald-950/80 text-emerald-400 border-emerald-500/30' : 'bg-blue-950/80 text-blue-300 border-blue-500/30';
        return `
        <div class="bg-slate-900/70 rounded-lg p-2.5 border border-slate-800 text-xs space-y-1">
            <div class="flex items-center justify-between font-bold text-slate-200">
                <span class="flex items-center gap-1.5">
                    <i data-lucide="sparkles" class="w-3.5 h-3.5 text-blue-400"></i>
                    ${addMod.module_name}
                </span>
                <span class="text-[10px] font-mono px-2 py-0.5 rounded border ${badgeColor}">
                    ${addMod.priority} Priority
                </span>
            </div>
            <p class="text-[11px] text-slate-400">${addMod.description}</p>
            <div class="text-[11px] text-brand-300 bg-slate-950/40 p-1.5 rounded border border-slate-800">
                <strong>Milestone Action:</strong> ${addMod.action}
            </div>
        </div>
        `;
    }).join('');

    // Next review block
    let nextStageNotice = '';
    if (!isFinalStage && nextReview) {
        nextStageNotice = `
        <div class="mt-4 p-4 rounded-xl bg-gradient-to-r from-brand-950/90 via-indigo-950/80 to-purple-950/90 border border-brand-500/40 space-y-2.5 shadow-lg">
            <div class="flex items-center justify-between">
                <span class="text-[10px] font-extrabold uppercase tracking-wider text-brand-300 px-2 py-0.5 rounded bg-brand-500/20 border border-brand-500/30">
                    NEXT REVIEW STAGE ASSIGNED
                </span>
                <span class="text-xs font-bold text-emerald-400">
                    ${nextReview.gap_days}-Day Interval Adhered
                </span>
            </div>
            <h4 class="font-bold text-sm text-white">${nextReview.stage_name}</h4>
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs text-slate-300 pt-1">
                <div>📅 Date: <strong class="text-white">${nextReview.scheduled_date}</strong></div>
                <div>⏰ Time: <strong class="text-white">${nextReview.meeting_time}</strong></div>
            </div>
            <div class="flex items-center justify-between bg-darkbg-950/80 p-2.5 rounded-lg border border-slate-800 text-xs">
                <span class="text-slate-400">Google Meet:</span>
                <a href="${nextReview.meeting_link}" target="_blank" class="text-cyan-400 hover:text-cyan-300 font-mono font-bold flex items-center gap-1">
                    ${nextReview.meeting_link} <i data-lucide="external-link" class="w-3 h-3"></i>
                </a>
            </div>
        </div>
        `;
    } else {
        nextStageNotice = `
        <div class="mt-4 p-4 rounded-xl bg-gradient-to-r from-emerald-950 via-teal-950 to-slate-900 border border-emerald-500/40 text-center space-y-2">
            <div class="text-2xl">🎓 🏆 📜</div>
            <h3 class="font-extrabold text-base text-white">ALL REVIEW STAGES COMPLETED</h3>
            <p class="text-xs text-emerald-200">
                You have fulfilled all corporate project specifications with high distinction. Your official certificate is available!
            </p>
            <button onclick="openCertificateModal()" class="mt-1 bg-amber-500 hover:bg-amber-400 text-slate-950 font-extrabold text-xs px-4 py-2 rounded-xl shadow-lg">
                View Official Internship Certificate
            </button>
        </div>
        `;
    }

    const evaluationHtml = `
    <div class="space-y-4">
        <!-- Top Score Banner & Verbal Voice Readout -->
        <div class="flex items-center justify-between p-3.5 rounded-xl bg-slate-900 border border-slate-800">
            <div>
                <span class="text-[10px] font-bold text-slate-400 uppercase tracking-wider">AI Evaluation Engine Dossier</span>
                <h4 class="font-bold text-sm text-white">${evalData.stage_name}</h4>
                <div class="text-[11px] text-slate-400 mt-0.5">${targetLabel}</div>
            </div>
            <div class="flex items-center gap-3">
                <button onclick="speakEvaluationFeedback('${escapeHtml(evalData.stage_name)}', ${evalData.score}, '${escapeHtml(evalData.verdict)}')" class="flex items-center gap-1 text-[11px] font-semibold px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-750 text-brand-300 hover:text-white border border-slate-700 transition-colors" title="Listen evaluation summary">
                    <i data-lucide="volume-2" class="w-3.5 h-3.5"></i>
                    <span>Listen</span>
                </button>
                <span class="text-lg font-black px-3 py-1 rounded-xl border ${scoreColor}">
                    ${evalData.score}/100 &bull; ${evalData.verdict}
                </span>
            </div>
        </div>

        <!-- Dual Dispatch Notification -->
        <div class="bg-indigo-950/40 border border-indigo-500/30 rounded-xl p-3 flex items-center justify-between text-xs">
            <div class="flex items-center gap-2 text-indigo-200">
                <i data-lucide="send" class="w-4 h-4 text-brand-400"></i>
                <span>Dual Dispatch: Feedback report automatically emailed to <strong>${emailDispatch.recipient_email}</strong></span>
            </div>
            <button onclick="switchView('inbox')" class="text-[11px] font-semibold text-brand-300 hover:text-white underline">
                View Email Log &rarr;
            </button>
        </div>

        <!-- Technical Critique -->
        <div class="text-xs text-slate-300 bg-slate-900/50 p-3 rounded-xl border border-slate-800 leading-relaxed">
            <strong class="text-slate-100 flex items-center gap-1 mb-1">
                <i data-lucide="cpu" class="w-3.5 h-3.5 text-brand-400"></i> Executive Technical Critique:
            </strong>
            ${evalData.detailed_summary}
        </div>

        <!-- 4 Pillars of Feedback Required by Mentor -->
        <div class="space-y-3.5">
            <!-- Pillar 1: Completed Modules -->
            <div>
                <span class="text-xs font-bold text-emerald-400 flex items-center gap-1 mb-2">
                    <i data-lucide="check-circle" class="w-3.5 h-3.5"></i> 1. Completed Modules &amp; Verification Evidence:
                </span>
                <div class="space-y-2">
                    ${completedModulesHtml}
                </div>
            </div>

            <!-- Pillar 2: Code Corrections -->
            <div>
                <span class="text-xs font-bold text-red-400 flex items-center gap-1 mb-2">
                    <i data-lucide="alert-triangle" class="w-3.5 h-3.5"></i> 2. Necessary Code Corrections &amp; Refactoring:
                </span>
                <div class="space-y-2">
                    ${codeCorrectionsHtml}
                </div>
            </div>

            <!-- Pillar 3: Missing Components -->
            <div>
                <span class="text-xs font-bold text-amber-400 flex items-center gap-1 mb-2">
                    <i data-lucide="help-circle" class="w-3.5 h-3.5"></i> 3. Missing Modules &amp; Components:
                </span>
                <ul class="space-y-1.5 bg-slate-900/60 p-3 rounded-xl border border-slate-800">
                    ${missingComponentsHtml}
                </ul>
            </div>

            <!-- Pillar 4: Modules to Add for Next Stage -->
            <div>
                <span class="text-xs font-bold text-blue-400 flex items-center gap-1 mb-2">
                    <i data-lucide="rocket" class="w-3.5 h-3.5"></i> 4. Modules to Add for Next Milestone:
                </span>
                <div class="space-y-2">
                    ${modulesToAddHtml}
                </div>
            </div>
        </div>

        <!-- Next Review Notice -->
        ${nextStageNotice}
    </div>
    `;

    appendBotMessage(evaluationHtml);
    lucide.createIcons();
}

// -------------------------------------------------------------
// DOCUMENT & FILE UPLOAD HANDLING (Core Requirement 4 & Mentor Audio)
// -------------------------------------------------------------
function handleFileSelected(event) {
    const file = event.target.files[0];
    if (!file) return;
    state.selectedFile = file;

    const sizeKb = (file.size / 1024).toFixed(1);
    document.getElementById('preview-file-name').innerText = file.name;
    document.getElementById('preview-file-size').innerText = `${sizeKb} KB`;
    document.getElementById('file-upload-preview-bar').classList.remove('hidden');
    lucide.createIcons();
}

function cancelSelectedFile() {
    state.selectedFile = null;
    const input = document.getElementById('doc-file-input');
    if (input) input.value = '';
    const bar = document.getElementById('file-upload-preview-bar');
    if (bar) bar.classList.add('hidden');
}

async function submitUploadedDocument() {
    if (!state.selectedFile) return;
    const file = state.selectedFile;

    if (!state.currentIntern) {
        appendBotMessage(`⚠️ Please verify your intern name first before submitting work.`);
        return;
    }

    if (state.currentIntern.status === 'COMPLETED') {
        appendBotMessage(`🎉 You have already completed all review stages for this internship! Check your certificate.`);
        cancelSelectedFile();
        return;
    }

    // Display user upload message
    const sizeKb = (file.size / 1024).toFixed(1);
    appendUserMessage(`📎 Uploaded Task Document: ${file.name} (${sizeKb} KB)`);

    cancelSelectedFile();
    showTypingIndicator();

    const formData = new FormData();
    formData.append('intern_id', state.currentIntern.intern_id);
    formData.append('file', file);

    try {
        const res = await fetch('/api/reviews/upload', {
            method: 'POST',
            body: formData
        });

        hideTypingIndicator();

        if (!res.ok) {
            const err = await res.json();
            appendBotMessage(`❌ Document evaluation failed: ${err.detail || 'Could not process document.'}`);
            return;
        }

        const data = await res.json();
        state.currentIntern = data.intern;
        state.reviewSchedule = data.review_schedule;
        updateInternProfileUI();
        renderTimelineRoadmap();

        renderEvaluationResultInChat(data.evaluation, data.email_dispatch, data.next_review, data.is_final_stage);
        await loadEmailLogs();

        if (data.is_final_stage) {
            triggerConfetti();
        }
    } catch (err) {
        hideTypingIndicator();
        console.error(err);
        appendBotMessage(`⚠️ Network error occurred while evaluating uploaded document.`);
    }
}

// Quick upload mock archive for instant demonstration
async function quickUploadSampleArchive() {
    const mockContent = "# Cloud Microservices AI - Milestone Project Archive\n\nAutomated Retail Shelf Monitoring System\n\nimport fastapi\nimport sqlalchemy\n# Code Scaffolding Verified";
    const blob = new Blob([mockContent], { type: 'text/markdown' });
    const file = new File([blob], "retail_monitoring_submission_v1.zip", { type: 'application/zip' });
    state.selectedFile = file;
    document.getElementById('preview-file-name').innerText = file.name;
    document.getElementById('preview-file-size').innerText = "142.5 KB";
    document.getElementById('file-upload-preview-bar').classList.remove('hidden');
    lucide.createIcons();
    await submitUploadedDocument();
}

// Send Review 1 Invite Email
async function dispatchStage1InvitationEmail() {
    if (!state.currentIntern) {
        appendBotMessage("⚠️ Please verify an intern first.");
        return;
    }

    try {
        const res = await fetch(`/api/interns/${state.currentIntern.intern_id}/send-invitation`, {
            method: 'POST'
        });

        if (!res.ok) {
            const err = await res.json();
            alert(`Failed: ${err.detail}`);
            return;
        }

        const data = await res.json();
        const d = data.dispatch;
        appendBotMessage(`
            <div class="space-y-2 bg-indigo-950/40 p-3.5 rounded-xl border border-indigo-500/30 text-xs">
                <div class="flex items-center gap-2 text-indigo-300 font-bold">
                    <i data-lucide="mail-check" class="w-4 h-4 text-brand-400"></i>
                    <span>Official Review 1 Invitation Email Dispatched!</span>
                </div>
                <p class="text-slate-300 leading-relaxed">
                    Following your project explanation call, the official <strong>Review Stage 1 Invitation Email</strong> has been sent to <strong class="text-white">${d.recipient_email}</strong>.
                </p>
                <div class="grid grid-cols-1 sm:grid-cols-2 gap-2 bg-slate-900/80 p-2.5 rounded-lg border border-slate-800 text-[11px]">
                    <div>📅 Date: <strong class="text-emerald-400 font-mono">${d.scheduled_date}</strong></div>
                    <div>🔗 Meet Link: <a href="${d.meeting_link}" target="_blank" class="text-brand-400 font-mono underline font-bold">${d.meeting_link}</a></div>
                </div>
            </div>
        `);
        await loadEmailLogs();
        lucide.createIcons();
    } catch (e) {
        alert("Failed to dispatch invitation email");
    }
}

// Verbal Readout for Evaluation Feedback
function speakEvaluationFeedback(stageName, score, verdict) {
    const intern = state.currentIntern;
    const name = intern ? intern.name : "Intern";
    const text = `Evaluation report for ${stageName}. Score: ${score} percent, verdict: ${verdict}. Hello ${name}, your completed modules have been verified against the master specification. Code corrections and next milestone additions have been emailed to your corporate address with your next Google Meet schedule.`;
    speakNeuralTTS(text);
}

// -------------------------------------------------------------
// NEURAL TEXT-TO-SPEECH (Microsoft Edge TTS via backend API)
// -------------------------------------------------------------
function initSpeechSynthesis() {
    // Legacy Web Speech API init kept for fallback detection only
    if ('speechSynthesis' in window) {
        window.speechSynthesis.onvoiceschanged = () => {
            const voices = window.speechSynthesis.getVoices();
            state.synthVoice = voices.find(v =>
                v.lang.includes('en') && (
                    v.name.includes('Natural') ||
                    v.name.includes('Google') ||
                    v.name.includes('Microsoft')
                )
            ) || voices[0];
        };
    }
}

async function speakNeuralTTS(text) {
    if (state.isSpeaking) {
        stopNeuralTTS();
        return;
    }

    const voiceSelect = document.getElementById('tts-voice-select');
    const voice = voiceSelect ? voiceSelect.value : 'en-US-AriaNeural';

    // Sanitize text — remove HTML tags, collapse whitespace
    const cleanText = text
        .replace(/<[^>]+>/g, ' ')
        .replace(/&amp;/g, 'and')
        .replace(/&bull;/g, '.')
        .replace(/&[a-z]+;/g, ' ')
        .replace(/\s+/g, ' ')
        .trim();

    setSpeakingState(true);

    try {
        const res = await fetch('/api/tts', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text: cleanText, voice })
        });

        if (!res.ok) {
            // Fallback to Web Speech API
            speakWithWebSpeech(cleanText);
            return;
        }

        const audioBlob = await res.blob();
        const audioUrl = URL.createObjectURL(audioBlob);
        const player = document.getElementById('tts-audio-player');

        player.src = audioUrl;
        player.onended = () => {
            URL.revokeObjectURL(audioUrl);
            setSpeakingState(false);
        };
        player.onerror = () => {
            URL.revokeObjectURL(audioUrl);
            setSpeakingState(false);
        };
        player.play();

    } catch (err) {
        console.warn('Neural TTS failed, falling back to Web Speech:', err);
        speakWithWebSpeech(cleanText);
    }
}

function stopNeuralTTS() {
    const player = document.getElementById('tts-audio-player');
    if (player) {
        player.pause();
        player.src = '';
    }
    if ('speechSynthesis' in window) {
        window.speechSynthesis.cancel();
    }
    setSpeakingState(false);
}

function speakWithWebSpeech(text) {
    if (!('speechSynthesis' in window)) {
        setSpeakingState(false);
        alert('Text-to-speech is not supported on this browser.');
        return;
    }
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    if (state.synthVoice) utterance.voice = state.synthVoice;
    utterance.rate = 0.95;
    utterance.pitch = 1.0;
    utterance.onend = () => setSpeakingState(false);
    utterance.onerror = () => setSpeakingState(false);
    window.speechSynthesis.speak(utterance);
}

function toggleTaskAudioBriefing() {
    if (state.isSpeaking) {
        stopNeuralTTS();
        return;
    }

    const task = state.masterTask;
    const intern = state.currentIntern;
    if (!task || !intern) return;

    const speechText = `Welcome, ${intern.name}. Your Date of Joining has been confirmed as ${intern.doj}. Here is your assigned master task briefing. ${task.title}. ${task.project_scope}. You have ${intern.total_reviews} scheduled review milestones, spaced with strict 10 to 15 day intervals. Please submit your GitHub repository for stage ${intern.current_review_stage} to begin automated AI evaluation.`;

    speakNeuralTTS(speechText);
}

function setSpeakingState(isSpeaking) {
    state.isSpeaking = isSpeaking;
    const label = document.getElementById('tts-label');
    const wave = document.getElementById('tts-wave');
    const icon = document.getElementById('tts-icon');

    if (isSpeaking) {
        label.innerText = 'Pause Briefing';
        wave.classList.remove('hidden');
        icon.className = 'w-3.5 h-3.5 text-red-400';
    } else {
        label.innerText = 'Listen Briefing';
        wave.classList.add('hidden');
        icon.className = 'w-3.5 h-3.5 text-brand-400';
    }
}

// -------------------------------------------------------------
// LIGHT / DARK MODE THEME TOGGLE
// -------------------------------------------------------------
function initTheme() {
    const saved = localStorage.getItem('nexus-theme') || 'dark';
    applyTheme(saved);
}

function toggleTheme() {
    const next = state.theme === 'dark' ? 'light' : 'dark';
    applyTheme(next);
    localStorage.setItem('nexus-theme', next);
}

function applyTheme(theme) {
    state.theme = theme;
    const html = document.documentElement;
    const sun = document.getElementById('theme-icon-sun');
    const moon = document.getElementById('theme-icon-moon');

    if (theme === 'light') {
        html.classList.add('light');
        html.classList.remove('dark');
        if (sun) sun.classList.remove('hidden');
        if (moon) moon.classList.add('hidden');
    } else {
        html.classList.remove('light');
        html.classList.add('dark');
        if (sun) sun.classList.add('hidden');
        if (moon) moon.classList.remove('hidden');
    }
    if (window.lucide) {
        lucide.createIcons();
    }
}

// -------------------------------------------------------------
// EMAIL DISPATCH LOGS & SIMULATOR (Core Requirement 5 & 6)
// -------------------------------------------------------------
async function loadEmailLogs() {
    try {
        const res = await fetch('/api/emails');
        if (!res.ok) return;
        const data = await res.json();
        state.emails = data.emails;

        document.getElementById('badge-email-count').innerText = data.count;
        document.getElementById('admin-kpi-emails').innerText = data.count;

        const container = document.getElementById('email-items-container');
        container.innerHTML = '';

        if (data.emails.length === 0) {
            container.innerHTML = `<div class="p-4 text-center text-xs text-slate-500">No emails dispatched yet. Submit a review stage or click Send Invite to trigger dispatch.</div>`;
            return;
        }

        data.emails.forEach((email, idx) => {
            const isInvite = email.email_type === 'INVITATION';
            const badgeClass = isInvite ? 'bg-indigo-500/20 text-indigo-300 border border-indigo-500/30' : 'bg-brand-500/20 text-brand-300 border border-brand-500/30';
            const badgeLabel = isInvite ? 'Stage 1 Invite' : `Stage ${email.stage_number} Feedback`;

            let deliveryBadge = '';
            if (email.status === 'SENT_LIVE_EMAIL') {
                deliveryBadge = `<span class="font-bold text-[9px] px-1.5 py-0.2 rounded bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">Live SMTP</span>`;
            } else if (email.status === 'SMTP_ERROR') {
                deliveryBadge = `<span class="font-bold text-[9px] px-1.5 py-0.2 rounded bg-red-500/20 text-red-400 border border-red-500/30">SMTP Error</span>`;
            } else {
                deliveryBadge = `<span class="font-bold text-[9px] px-1.5 py-0.2 rounded bg-slate-800 text-slate-400 border border-slate-700">Simulated</span>`;
            }

            const item = document.createElement('div');
            item.className = "p-3 rounded-xl border border-slate-800 bg-slate-900/60 hover:bg-slate-800/80 cursor-pointer transition-all";
            item.onclick = () => previewEmail(email);
            item.innerHTML = `
                <div class="flex items-center justify-between text-[11px] mb-1">
                    <div class="flex items-center gap-1.5">
                        <span class="font-bold text-[10px] px-2 py-0.5 rounded-full ${badgeClass}">${badgeLabel}</span>
                        ${deliveryBadge}
                    </div>
                    <span class="text-slate-500 text-[10px]">${email.dispatched_at}</span>
                </div>
                <div class="text-xs font-semibold text-slate-200 truncate mt-1">${email.subject}</div>
                <div class="text-[11px] text-slate-400 truncate mt-0.5">To: ${email.recipient_email}</div>
            `;
            container.appendChild(item);
        });

        // Preview the latest email
        if (data.emails.length > 0) {
            previewEmail(data.emails[0]);
        }
    } catch (e) {
        console.error("Failed to load emails:", e);
    }
}

function previewEmail(email) {
    document.getElementById('email-preview-subject').innerText = email.subject;
    document.getElementById('email-preview-meta').innerText = `Recipient: ${email.recipient_email} • Dispatched: ${email.dispatched_at}`;
    
    const statusPill = document.getElementById('email-preview-status');
    if (statusPill) {
        if (email.status === 'SENT_LIVE_EMAIL') {
            statusPill.innerText = 'LIVE DELIVERED (SMTP)';
            statusPill.className = 'text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/30';
        } else if (email.status === 'SMTP_ERROR') {
            statusPill.innerText = 'SMTP DELIVERY FAILED';
            statusPill.className = 'text-[10px] font-bold px-2 py-0.5 rounded-full bg-red-500/20 text-red-400 border border-red-500/30';
        } else {
            statusPill.innerText = 'LOCAL SIMULATOR';
            statusPill.className = 'text-[10px] font-bold px-2 py-0.5 rounded-full bg-indigo-500/20 text-indigo-300 border border-indigo-500/30';
        }
    }

    const iframe = document.getElementById('email-iframe');
    iframe.srcdoc = email.email_body_html;
}

// -------------------------------------------------------------
// ADMIN DASHBOARD & CONTROLS (Core Requirement 6)
// -------------------------------------------------------------
async function loadInitialSettingsAndTask() {
    try {
        const [taskRes, settingsRes] = await Promise.all([
            fetch('/api/master-task'),
            fetch('/api/settings')
        ]);

        if (taskRes.ok) {
            const data = await taskRes.json();
            state.masterTask = data.master_task;
            populateMasterTaskForm(data.master_task);
        }

        if (settingsRes.ok) {
            const sData = await settingsRes.json();
            const s = sData.settings;
            if (s.default_total_reviews) document.getElementById('setting-total-reviews').value = s.default_total_reviews;
            if (s.default_gap_days) document.getElementById('setting-gap-days').value = s.default_gap_days;
            if (s.company_name) document.getElementById('setting-company-name').value = s.company_name;
        }
    } catch (e) {
        console.error(e);
    }
}

function populateMasterTaskForm(task) {
    if (!task) return;
    document.getElementById('admin-task-title').value = task.title;
    document.getElementById('admin-task-scope').value = task.project_scope;
    document.getElementById('admin-task-objectives').value = task.objectives;
    document.getElementById('admin-task-techstack').value = task.tech_stack;
    document.getElementById('admin-task-rules').value = task.submission_rules;
    document.getElementById('admin-task-rubric').value = task.review_requirements;
}

async function handleMasterTaskSave(e) {
    e.preventDefault();
    const payload = {
        title: document.getElementById('admin-task-title').value,
        project_scope: document.getElementById('admin-task-scope').value,
        objectives: document.getElementById('admin-task-objectives').value,
        tech_stack: document.getElementById('admin-task-techstack').value,
        submission_rules: document.getElementById('admin-task-rules').value,
        review_requirements: document.getElementById('admin-task-rubric').value
    };

    try {
        const res = await fetch('/api/master-task', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (res.ok) {
            const msg = document.getElementById('master-task-saved-msg');
            msg.classList.remove('hidden');
            setTimeout(() => msg.classList.add('hidden'), 3000);
            await loadInitialSettingsAndTask();
        }
    } catch (err) {
        alert("Failed to update master task");
    }
}

async function handleSettingsSave(e) {
    e.preventDefault();
    const payload = {
        default_total_reviews: parseInt(document.getElementById('setting-total-reviews').value),
        default_gap_days: parseInt(document.getElementById('setting-gap-days').value),
        company_name: document.getElementById('setting-company-name').value
    };

    try {
        const res = await fetch('/api/settings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        if (res.ok) {
            alert("Scheduling parameters updated successfully!");
        }
    } catch (err) {
        alert("Error saving settings.");
    }
}

async function loadAdminDashboard() {
    try {
        const res = await fetch('/api/interns');
        if (!res.ok) return;
        const data = await res.json();
        const interns = data.interns;

        document.getElementById('admin-kpi-interns').innerText = interns.length;
        const activeCount = interns.filter(i => i.status === 'ACTIVE').length;
        const completedCount = interns.filter(i => i.status === 'COMPLETED').length;

        document.getElementById('admin-kpi-active-reviews').innerText = activeCount;
        document.getElementById('admin-kpi-completed-reviews').innerText = completedCount;

        const tableBody = document.getElementById('admin-interns-table-body');
        tableBody.innerHTML = '';

        interns.forEach(intern => {
            const tr = document.createElement('tr');
            tr.className = "hover:bg-slate-800/40 transition-colors";
            tr.innerHTML = `
                <td class="p-3 font-mono font-bold text-slate-400">${intern.intern_id}</td>
                <td class="p-3 font-bold text-white">${intern.name}</td>
                <td class="p-3 text-slate-400">${intern.email}</td>
                <td class="p-3 font-mono text-emerald-400">${intern.doj}</td>
                <td class="p-3">
                    <span class="px-2 py-0.5 rounded bg-brand-500/20 text-brand-300 font-semibold text-[10px]">
                        Stage ${intern.current_review_stage}/${intern.total_reviews}
                    </span>
                </td>
                <td class="p-3">
                    <span class="px-2 py-0.5 rounded text-[10px] font-bold ${intern.status === 'COMPLETED' ? 'bg-amber-500/20 text-amber-400' : 'bg-emerald-500/20 text-emerald-400'}">
                        ${intern.status}
                    </span>
                </td>
                <td class="p-3 text-right space-x-1.5">
                    <button onclick="selectAndSwitchToIntern('${intern.name}')" class="px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 text-[11px]">
                        Review
                    </button>
                    <button onclick="resetInternViaId('${intern.intern_id}')" class="px-2 py-1 rounded bg-slate-800 hover:bg-red-950/60 text-slate-400 hover:text-red-400 text-[11px]" title="Reset to Stage 1">
                        Reset
                    </button>
                </td>
            `;
            tableBody.appendChild(tr);
        });

        await loadSmtpConfig();
        if (window.lucide) lucide.createIcons();

    } catch (e) {
        console.error(e);
    }
}

function selectAndSwitchToIntern(name) {
    verifyInternByName(name);
    switchView('chat');
}

async function resetInternViaId(internId) {
    if (!confirm(`Reset intern ${internId} progress back to Stage 1 for testing?`)) return;
    try {
        const res = await fetch(`/api/interns/${internId}/reset`, { method: 'POST' });
        if (res.ok) {
            await loadAdminDashboard();
            if (state.currentIntern && state.currentIntern.intern_id === internId) {
                await verifyInternByName(state.currentIntern.name);
            }
        }
    } catch (e) {
        alert("Failed to reset intern");
    }
}

// -------------------------------------------------------------
// LIVE EMAIL DISPATCH & SMTP CONFIGURATION
// -------------------------------------------------------------
async function loadSmtpConfig() {
    try {
        const res = await fetch('/api/smtp/config');
        if (!res.ok) return;
        const cfg = await res.json();

        const hostEl = document.getElementById('smtp-host');
        const portEl = document.getElementById('smtp-port');
        const userEl = document.getElementById('smtp-user');
        const passEl = document.getElementById('smtp-password');
        const nameEl = document.getElementById('smtp-from-name');
        const badgeEl = document.getElementById('smtp-status-badge');

        if (hostEl && cfg.host) { hostEl.value = cfg.host; onSmtpHostChange(cfg.host); }
        if (portEl && cfg.port) portEl.value = cfg.port;
        if (userEl && cfg.user) userEl.value = cfg.user;
        if (nameEl && cfg.from_name) nameEl.value = cfg.from_name;
        if (passEl && cfg.has_password) passEl.placeholder = '•••••••••••••••• (16-char App Password saved)';

        if (badgeEl) {
            if (cfg.is_configured && cfg.enabled) {
                badgeEl.innerText = '🟢 Live SMTP Active';
                badgeEl.className = 'text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/30';
            } else {
                badgeEl.innerText = '🟡 Local Inbox Simulator';
                badgeEl.className = 'text-[10px] font-bold px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-400 border border-amber-500/30';
            }
        }
    } catch (e) {
        console.error("Failed to load SMTP config:", e);
    }
}

function applySmtpPreset(preset) {
    const hostEl = document.getElementById('smtp-host');
    const portEl = document.getElementById('smtp-port');
    if (preset === 'gmail') {
        if (hostEl) hostEl.value = 'smtp.gmail.com';
        if (portEl) portEl.value = 587;
    } else if (preset === 'outlook') {
        if (hostEl) hostEl.value = 'smtp.office365.com';
        if (portEl) portEl.value = 587;
    }
    if (hostEl) onSmtpHostChange(hostEl.value);
}

// Show/hide Gmail App Password guide banner depending on host
function onSmtpHostChange(host) {
    const guide = document.getElementById('gmail-apppassword-guide');
    if (!guide) return;
    if (host && host.toLowerCase().includes('gmail')) {
        guide.classList.remove('hidden');
    } else {
        guide.classList.add('hidden');
    }
}

// Live password length indicator — warn if not 16 chars for Gmail
function validateAppPasswordLength(input) {
    const lenEl = document.getElementById('smtp-pw-len-indicator');
    const warnEl = document.getElementById('smtp-pw-warning');
    const hostEl = document.getElementById('smtp-host');
    const isGmail = hostEl && hostEl.value.toLowerCase().includes('gmail');
    const clean = (input.value || '').replace(/\s/g, '');
    const len = clean.length;

    if (lenEl) {
        lenEl.innerText = len ? `${len} chars` : '';
        lenEl.className = `absolute right-2 top-1/2 -translate-y-1/2 text-[10px] font-bold ${
            isGmail ? (len === 16 ? 'text-emerald-400' : 'text-amber-400') : 'text-slate-500'
        }`;
    }
    if (warnEl && isGmail) {
        if (len > 0 && len !== 16) {
            warnEl.innerText = `⚠️ Gmail App Passwords are exactly 16 characters (no spaces). You have ${len}.`;
            warnEl.className = 'text-[10px] font-semibold mt-0.5 block text-amber-400';
        } else if (len === 16) {
            warnEl.innerText = '✅ Correct App Password length (16 characters).';
            warnEl.className = 'text-[10px] font-semibold mt-0.5 block text-emerald-400';
        } else {
            warnEl.innerText = '';
            warnEl.classList.add('hidden');
        }
    }
}

async function handleSmtpConfigSave(e) {
    e.preventDefault();
    const errorEl = document.getElementById('smtp-error-msg');
    const savedEl = document.getElementById('smtp-saved-msg');

    // Hide previous messages
    if (errorEl) { errorEl.classList.add('hidden'); errorEl.innerText = ''; }
    if (savedEl) savedEl.classList.add('hidden');

    const payload = {
        enabled: true,
        host: document.getElementById('smtp-host').value.trim(),
        port: parseInt(document.getElementById('smtp-port').value),
        user: document.getElementById('smtp-user').value.trim(),
        from_name: document.getElementById('smtp-from-name').value.trim()
    };

    const passVal = (document.getElementById('smtp-password').value || '').replace(/\s/g, '');
    if (passVal) {
        payload.password = passVal;
    }

    try {
        const res = await fetch('/api/smtp/config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (res.ok) {
            if (savedEl) {
                savedEl.classList.remove('hidden');
                setTimeout(() => savedEl.classList.add('hidden'), 5000);
            }
            await loadSmtpConfig();
        } else {
            const err = await res.json();
            const msg = err.detail || 'Failed to save SMTP configuration.';
            if (errorEl) {
                errorEl.innerText = `❌ ${msg}`;
                errorEl.classList.remove('hidden');
            } else {
                alert(msg);
            }
        }
    } catch (ex) {
        const msg = 'Network error — could not reach the backend. Is the server running?';
        if (errorEl) {
            errorEl.innerText = `❌ ${msg}`;
            errorEl.classList.remove('hidden');
        }
    }
}

async function sendTestSmtpEmail() {
    const input = document.getElementById('smtp-test-recipient');
    const recipient = input ? input.value.trim() : '';
    const resultMsg = document.getElementById('smtp-test-result-msg');
    const btn = document.getElementById('btn-smtp-test');

    if (!recipient || !recipient.includes('@')) {
        alert("Please enter a valid student email address to send the test email to.");
        if (input) input.focus();
        return;
    }

    if (btn) {
        btn.disabled = true;
        btn.innerHTML = `<span class="animate-spin mr-1">⏳</span> Sending...`;
    }

    try {
        const res = await fetch('/api/smtp/test', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ recipient_email: recipient })
        });

        const data = await res.json();

        if (res.ok) {
            if (resultMsg) {
                resultMsg.innerText = `✅ Test email successfully delivered to ${recipient}! Check your inbox.`;
                resultMsg.className = 'text-[11px] mt-1.5 block text-emerald-400 font-semibold';
                resultMsg.classList.remove('hidden');
            }
            await loadEmailLogs();
        } else {
            if (resultMsg) {
                const detail = data.detail || 'Could not connect to SMTP server.';
                resultMsg.innerText = `❌ ${detail}`;
                resultMsg.className = 'text-[11px] mt-1.5 block text-red-400 font-medium leading-relaxed';
                resultMsg.classList.remove('hidden');
            }
        }
    } catch (e) {
        if (resultMsg) {
            resultMsg.innerText = `❌ Error: ${e.message}`;
            resultMsg.className = 'text-[11px] mt-1.5 block text-red-400 font-semibold';
        }
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = `<i data-lucide="send" class="w-3 h-3"></i><span>Send Test</span>`;
            if (window.lucide) lucide.createIcons();
        }
    }
}

async function resetCurrentInternProgress() {
    if (!state.currentIntern) {
        renderInitialPromptScreen();
        return;
    }
    await resetInternViaId(state.currentIntern.intern_id);
}

// -------------------------------------------------------------
// REGISTRATION MODAL
// -------------------------------------------------------------
function openRegistrationModal(prefillName) {
    document.getElementById('modal-register').classList.remove('hidden');
    // Set default DOJ to today
    document.getElementById('reg-doj').value = new Date().toISOString().split('T')[0];
    if (prefillName && typeof prefillName === 'string') {
        const nameField = document.getElementById('reg-name');
        if (nameField) nameField.value = prefillName;
        const emailField = document.getElementById('reg-email');
        if (emailField) emailField.focus();
    }
    lucide.createIcons();
}

function closeRegistrationModal() {
    document.getElementById('modal-register').classList.add('hidden');
}

async function handleInternRegistration(e) {
    e.preventDefault();
    const payload = {
        name: document.getElementById('reg-name').value.trim(),
        email: document.getElementById('reg-email').value.trim(),
        role: document.getElementById('reg-role').value.trim(),
        department: document.getElementById('reg-dept').value.trim(),
        doj: document.getElementById('reg-doj').value,
        total_reviews: parseInt(document.getElementById('reg-total-reviews').value),
        gap_days: parseInt(document.getElementById('reg-gap-days').value)
    };

    try {
        const res = await fetch('/api/interns/register', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (!res.ok) {
            const err = await res.json();
            alert(`Registration failed: ${err.detail}`);
            return;
        }

        const data = await res.json();
        closeRegistrationModal();
        state.currentIntern = data.intern;
        state.masterTask = data.assigned_task;
        state.reviewSchedule = data.review_schedule;

        updateInternProfileUI();
        renderTimelineRoadmap();
        switchView('chat');
        displayWelcomeAndTaskBriefing(data.message);

    } catch (err) {
        alert("Registration network error.");
    }
}

// -------------------------------------------------------------
// CERTIFICATE MODAL
// -------------------------------------------------------------
function openCertificateModal() {
    const intern = state.currentIntern;
    if (!intern) return;

    document.getElementById('cert-intern-name').innerText = intern.name;
    document.getElementById('cert-reviews-count').innerText = intern.total_reviews;
    document.getElementById('cert-doj').innerText = intern.doj;
    document.getElementById('cert-id').innerText = `CERT-AIRS-${intern.intern_id}`;
    if (state.masterTask) {
        document.getElementById('cert-project-title').innerText = state.masterTask.title;
    }

    document.getElementById('modal-certificate').classList.remove('hidden');
    lucide.createIcons();
}

function closeCertificateModal() {
    document.getElementById('modal-certificate').classList.add('hidden');
}

function triggerConfetti() {
    if (typeof confetti === 'function') {
        confetti({
            particleCount: 120,
            spread: 80,
            origin: { y: 0.6 }
        });
    }
}

// -------------------------------------------------------------
// CHAT UTILITIES
// -------------------------------------------------------------
function appendUserMessage(text) {
    const container = document.getElementById('chat-messages-container');
    const msg = document.createElement('div');
    msg.className = "flex items-start justify-end gap-2.5 chat-bubble-enter";
    msg.innerHTML = `
        <div class="max-w-[85%] bg-gradient-to-r from-brand-600 to-indigo-600 text-white rounded-2xl rounded-tr-sm px-4 py-2.5 text-xs shadow-md">
            <p class="whitespace-pre-wrap leading-relaxed">${escapeHtml(text)}</p>
        </div>
        <div class="w-8 h-8 rounded-xl bg-slate-800 text-slate-300 flex items-center justify-center text-xs font-bold shrink-0">
            YOU
        </div>
    `;
    container.appendChild(msg);
    container.scrollTop = container.scrollHeight;
}

function appendBotMessage(htmlContent) {
    const container = document.getElementById('chat-messages-container');
    const msg = document.createElement('div');
    msg.className = "flex items-start gap-2.5 chat-bubble-enter";
    msg.innerHTML = `
        <div class="w-8 h-8 rounded-xl bg-gradient-to-tr from-brand-600 to-purple-500 text-white flex items-center justify-center shrink-0 shadow-md">
            <i data-lucide="bot" class="w-4 h-4"></i>
        </div>
        <div class="max-w-[90%] bg-darkbg-850 text-slate-200 rounded-2xl rounded-tl-sm p-4 text-xs border border-slate-800 shadow-md leading-relaxed">
            ${htmlContent}
        </div>
    `;
    container.appendChild(msg);
    container.scrollTop = container.scrollHeight;
    lucide.createIcons();
}

function showTypingIndicator() {
    const container = document.getElementById('chat-messages-container');
    const indicator = document.createElement('div');
    indicator.id = 'typing-indicator-bubble';
    indicator.className = "flex items-center gap-2 text-slate-400 text-xs p-2 chat-bubble-enter";
    indicator.innerHTML = `
        <div class="w-2 h-2 rounded-full bg-brand-500 animate-ping"></div>
        <span>AI Evaluation Engine inspecting repository &amp; verifying code AST...</span>
    `;
    container.appendChild(indicator);
    container.scrollTop = container.scrollHeight;
}

function hideTypingIndicator() {
    const indicator = document.getElementById('typing-indicator-bubble');
    if (indicator) indicator.remove();
}

function quickSelectIntern(name) {
    verifyInternByName(name);
}

function quickFillGithub(url) {
    document.getElementById('chat-input-field').value = url;
    document.getElementById('chat-input-field').focus();
}

function escapeHtml(str) {
    return str.replace(/[&<>'"]/g,
        tag => ({
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            "'": '&#39;',
            '"': '&quot;'
        }[tag] || tag)
    );
}
