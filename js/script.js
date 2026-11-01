// ============================================================================
// NEUROADAPT AI - COMPLETE APPLICATION CONTROLLER (HACKATHON MVP)
// ============================================================================

const API_BASE = (window.location && window.location.origin && window.location.origin.startsWith("http"))
    ? window.location.origin
    : "http://127.0.0.1:8000";

let progressChartInstance = null;

// ----------------------------------------------------------------------------
// 1. ANONYMOUS LEARNER IDENTITY & SESSION RESTORATION
// ----------------------------------------------------------------------------

function generateAnonymousId() {
    const chars = "abcdef0123456789";
    let rand = "";
    for (let i = 0; i < 8; i++) {
        rand += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    return "lrn_" + rand;
}

function getLearnerProfile() {
    let learnerId = localStorage.getItem("neuroadapt_learner_id");
    let learnerName = localStorage.getItem("neuroadapt_learner_name");

    if (!learnerId) {
        learnerId = generateAnonymousId();
        learnerName = "Learner " + learnerId.replace("lrn_", "").toUpperCase();
        localStorage.setItem("neuroadapt_learner_id", learnerId);
        localStorage.setItem("neuroadapt_learner_name", learnerName);

        // Sync with backend to initialize learner record
        apiFetch("/api/learner/start", {
            method: "POST",
            body: JSON.stringify({ learner_id: learnerId, display_name: learnerName })
        }).catch(err => console.log("Initial session sync:", err));
    }

    return { id: learnerId, name: learnerName };
}

function updateNavLearnerBadge() {
    const profile = getLearnerProfile();

    const navName = document.getElementById("navLearnerName");
    if (navName) {
        navName.textContent = profile.name;
    }

    const activeDisplay = document.getElementById("activeLearnerDisplay");
    if (activeDisplay) {
        activeDisplay.textContent = `${profile.name} (${profile.id})`;
    }
}

async function promptChangeLearnerName() {
    const profile = getLearnerProfile();
    const newName = prompt("Enter your profile name:", profile.name);
    if (newName && newName.trim() && newName.trim() !== profile.name) {
        localStorage.setItem("neuroadapt_learner_name", newName.trim());
        updateNavLearnerBadge();

        try {
            await apiFetch("/api/learner/start", {
                method: "POST",
                body: JSON.stringify({ learner_id: profile.id, display_name: newName.trim() })
            });
        } catch (e) {
            console.warn("Could not sync name to backend:", e);
        }

        if (window.location.pathname.includes("dashboard.html")) {
            loadDashboard();
        }
    }
}

async function startNewLearningJourney() {
    const profile = getLearnerProfile();
    const confirmReset = confirm(
        `Are you sure you want to reset your learning journey?\n\nThis will clear attempts and mastery for ${profile.name} and start a fresh session.`
    );

    if (!confirmReset) return;

    try {
        await apiFetch("/api/learner/reset", {
            method: "POST",
            body: JSON.stringify({ learner_id: profile.id, confirm: true })
        });
        alert("Your learning journey has been reset! Starting fresh.");
        if (window.location.pathname.includes("dashboard.html")) {
            loadDashboard();
        } else if (window.location.pathname.includes("test.html")) {
            resetQuizRunner();
        }
    } catch (e) {
        // Fallback: create fresh anonymous profile
        createNewLearnerProfile();
    }
}

function createNewLearnerProfile() {
    const newId = generateAnonymousId();
    const newName = "Learner " + newId.replace("lrn_", "").toUpperCase();

    localStorage.setItem("neuroadapt_learner_id", newId);
    localStorage.setItem("neuroadapt_learner_name", newName);

    apiFetch("/api/learner/start", {
        method: "POST",
        body: JSON.stringify({ learner_id: newId, display_name: newName })
    }).catch(err => console.log("New profile creation:", err));

    alert(`Created new anonymous student session: ${newName} (${newId}).`);
    updateNavLearnerBadge();

    if (window.location.pathname.includes("dashboard.html")) {
        loadDashboard();
    } else if (window.location.pathname.includes("test.html")) {
        resetQuizRunner();
    }
}

// ----------------------------------------------------------------------------
// 2. BACKEND API CALLER WITH ANONYMOUS HEADERS
// ----------------------------------------------------------------------------

async function apiFetch(endpoint, options = {}) {
    const profile = getLearnerProfile();
    const headers = {
        "Content-Type": "application/json",
        "X-Learner-Id": profile.id,
        "X-Learner-Name": profile.name,
        ...(options.headers || {})
    };

    const url = endpoint.startsWith("http") ? endpoint : `${API_BASE}${endpoint}`;

    try {
        const response = await fetch(url, { ...options, headers });
        if (!response.ok) {
            const errData = await response.json().catch(() => ({}));
            throw new Error(errData.detail || `Request failed (${response.status})`);
        }
        return await response.json();
    } catch (err) {
        console.error("API Fetch Error:", endpoint, err);
        throw err;
    }
}

// ----------------------------------------------------------------------------
// 3. AI SOCRATIC TUTOR INTERFACE (chat.html)
// ----------------------------------------------------------------------------

async function sendMessage(event) {
    if (event) event.preventDefault();

    const input = document.getElementById("userInput");
    const messages = document.getElementById("messages");
    if (!input || !messages) return;

    const message = input.value.trim();
    if (message === "") return;

    // Render User Message
    const userMessageDiv = document.createElement("div");
    userMessageDiv.className = "message user-message";
    userMessageDiv.textContent = message;
    messages.appendChild(userMessageDiv);

    input.value = "";
    messages.scrollTop = messages.scrollHeight;

    // Render Typing Placeholder
    const typingDiv = document.createElement("div");
    typingDiv.className = "message ai-message";
    typingDiv.id = "typingIndicator";
    typingDiv.textContent = "🧠 NeuroAdapt AI is analyzing your concept context...";
    messages.appendChild(typingDiv);
    messages.scrollTop = messages.scrollHeight;

    const sendBtn = document.getElementById("chatSendBtn");
    if (sendBtn) sendBtn.disabled = true;

    try {
        const profile = getLearnerProfile();
        const response = await apiFetch("/api/tutor/chat", {
            method: "POST",
            body: JSON.stringify({
                learner_id: profile.id,
                message: message
            })
        });

        typingDiv.remove();

        const aiMessageDiv = document.createElement("div");
        aiMessageDiv.className = "message ai-message";
        aiMessageDiv.innerHTML = formatMarkdown(response.reply);
        messages.appendChild(aiMessageDiv);
    } catch (err) {
        typingDiv.remove();
        const errorDiv = document.createElement("div");
        errorDiv.className = "message ai-message";
        errorDiv.style.borderColor = "#B84A39";
        errorDiv.textContent = "Could not connect to the NeuroAdapt backend. Make sure the server is running on http://127.0.0.1:8000.";
        messages.appendChild(errorDiv);
    } finally {
        if (sendBtn) sendBtn.disabled = false;
        messages.scrollTop = messages.scrollHeight;
    }
}

function useSuggestion(text) {
    const input = document.getElementById("userInput");
    if (!input) return;
    input.value = text;
    sendMessage(null);
}

function formatMarkdown(text) {
    if (!text) return "";
    let html = text
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;");

    // Math bold notation
    html = html.replace(/\$\$(.*?)\$\$/g, '<div style="background:#FAF4EB; padding:8px 12px; border-radius:6px; margin:8px 0; font-family:serif; font-size:15px; text-align:center; color:#5A3E2A;">$1</div>');
    html = html.replace(/\$(.*?)\$/g, '<code style="background:#FAF4EB; padding:2px 5px; border-radius:4px; font-family:serif; color:#5A3E2A;">$1</code>');

    // Bold
    html = html.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
    // Italics
    html = html.replace(/\*(.*?)\*/g, "<em>$1</em>");
    // Line breaks
    html = html.replace(/\n/g, "<br>");
    return html;
}

// ----------------------------------------------------------------------------
// 4. TEST CENTRE & ADAPTIVE QUIZ RUNNER (test.html)
// ----------------------------------------------------------------------------

let currentTestMode = "adaptive";
let activeQuizQuestions = [];
let currentQuestionIndex = 0;
let currentSelectedAnswer = null;
let quizSessionResults = {
    total: 0,
    correct: 0,
    masteryGain: 0,
    misconceptions: []
};

function switchTestMode(mode) {
    currentTestMode = mode;

    document.querySelectorAll(".mode-pill").forEach(pill => pill.classList.remove("active"));
    const activeBtn = document.getElementById(`modeBtn${mode.charAt(0).toUpperCase() + mode.slice(1)}`);
    if (activeBtn) activeBtn.classList.add("active");

    const customControls = document.getElementById("customControls");
    const title = document.getElementById("configCardTitle");
    const desc = document.getElementById("configCardDesc");

    if (customControls) {
        customControls.style.display = (mode === "custom") ? "block" : "none";
    }

    if (mode === "diagnostic") {
        if (title) title.textContent = "🩺 Diagnostic Knowledge Assessment";
        if (desc) desc.textContent = "Assess your baseline competency across all 9 Class 10 Electricity concepts to calibrate your knowledge graph.";
    } else if (mode === "adaptive") {
        if (title) title.textContent = "🎯 Adaptive Practice Engine";
        if (desc) desc.textContent = "Questions dynamically target your weakest concept boundaries and adjust difficulty as you learn.";
    } else if (mode === "spaced") {
        if (title) title.textContent = "🔄 Spaced Repetition Review";
        if (desc) desc.textContent = "Reinforce concepts due for review to counter the forgetting curve and secure long-term retention.";
    } else if (mode === "custom") {
        if (title) title.textContent = "⚙️ Custom Topic Practice";
        if (desc) desc.textContent = "Select specific topics and difficulty levels to practice at your own pace.";
    }
}

async function generateTest() {
    const countSelect = document.getElementById("questionCount");
    const count = countSelect ? parseInt(countSelect.value) : 5;

    const resultDiv = document.getElementById("testResult");
    const startBtn = document.getElementById("startTestBtn");

    if (resultDiv) resultDiv.textContent = "Calibrating questions from NeuroAdapt Engine...";
    if (startBtn) startBtn.disabled = true;

    try {
        let endpoint = `/api/questions/adaptive?mode=${currentTestMode}&count=${count}`;

        if (currentTestMode === "diagnostic") {
            endpoint = `/api/diagnostic?count=${count}`;
        } else if (currentTestMode === "custom") {
            const topicInput = document.getElementById("testTopic");
            const diffSelect = document.getElementById("difficulty");
            const topic = topicInput ? topicInput.value.trim() : "";
            const diff = diffSelect ? diffSelect.value : 2;
            endpoint = `/api/questions/adaptive?mode=custom&topic=${encodeURIComponent(topic)}&difficulty=${diff}&count=${count}`;
        }

        const data = await apiFetch(endpoint);

        if (!data.questions || data.questions.length === 0) {
            if (resultDiv) resultDiv.textContent = "No questions found for this selection. Try Adaptive or Diagnostic mode!";
            if (startBtn) startBtn.disabled = false;
            return;
        }

        activeQuizQuestions = data.questions;
        currentQuestionIndex = 0;
        quizSessionResults = {
            total: activeQuizQuestions.length,
            correct: 0,
            masteryGain: 0,
            misconceptions: []
        };

        // Transition UI to Quiz Runner
        const configCard = document.getElementById("testConfigCard");
        const quizCard = document.getElementById("activeQuizCard");
        const summaryCard = document.getElementById("quizSummaryCard");

        if (configCard) configCard.style.display = "none";
        if (summaryCard) summaryCard.style.display = "none";
        if (quizCard) quizCard.style.display = "block";

        renderCurrentQuestion();
    } catch (err) {
        if (resultDiv) {
            resultDiv.textContent = "Could not load questions from the backend. Make sure FastAPI is running on http://127.0.0.1:8000.";
        }
    } finally {
        if (startBtn) startBtn.disabled = false;
    }
}

function renderCurrentQuestion() {
    const q = activeQuizQuestions[currentQuestionIndex];
    if (!q) {
        renderQuizSummary();
        return;
    }

    currentSelectedAnswer = null;

    // Badges & Progress
    const conceptBadge = document.getElementById("quizConceptBadge");
    const progressText = document.getElementById("quizProgressText");
    const promptText = document.getElementById("quizQuestionPrompt");
    const optionsContainer = document.getElementById("quizOptionsContainer");
    const reasoningInput = document.getElementById("userReasoning");
    const feedbackArea = document.getElementById("quizFeedbackArea");
    const submitBtn = document.getElementById("submitAnswerBtn");
    const nextBtn = document.getElementById("nextQuestionBtn");

    const diffLabels = {1: "Easy (Level 1)", 2: "Medium (Level 2)", 3: "Hard (Level 3)", 4: "Advanced (Level 4)"};
    const diffStr = diffLabels[q.difficulty] || `Level ${q.difficulty}`;

    if (conceptBadge) conceptBadge.textContent = `CONCEPT: ${q.concept_id.toUpperCase().replace(/-/g, " ")} | ${diffStr.toUpperCase()}`;
    if (progressText) progressText.textContent = `Question ${currentQuestionIndex + 1} of ${activeQuizQuestions.length}`;
    if (promptText) promptText.textContent = q.prompt;
    if (reasoningInput) reasoningInput.value = "";
    if (feedbackArea) {
        feedbackArea.style.display = "none";
        feedbackArea.innerHTML = "";
    }
    if (submitBtn) {
        submitBtn.style.display = "block";
        submitBtn.disabled = false;
        submitBtn.textContent = "Submit Answer";
    }
    if (nextBtn) nextBtn.style.display = "none";

    // Populate Option Buttons
    if (optionsContainer) {
        optionsContainer.innerHTML = "";
        const labels = ["A", "B", "C", "D"];
        q.options.forEach((opt, idx) => {
            const btn = document.createElement("button");
            btn.type = "button";
            btn.className = "quiz-option-btn";
            btn.innerHTML = `<strong style="color:var(--primary);">${labels[idx] || '•'})</strong> <span>${opt}</span>`;
            btn.onclick = () => selectOption(btn, opt);
            optionsContainer.appendChild(btn);
        });
    }
}

function selectOption(buttonElement, optionText) {
    document.querySelectorAll(".quiz-option-btn").forEach(b => b.classList.remove("selected"));
    buttonElement.classList.add("selected");
    currentSelectedAnswer = optionText;
}

async function submitCurrentAnswer() {
    if (!currentSelectedAnswer) {
        alert("Please select an answer choice before submitting.");
        return;
    }

    const q = activeQuizQuestions[currentQuestionIndex];
    const reasoningInput = document.getElementById("userReasoning");
    const reasoning = reasoningInput ? reasoningInput.value.trim() : "";

    const submitBtn = document.getElementById("submitAnswerBtn");
    const nextBtn = document.getElementById("nextQuestionBtn");
    const feedbackArea = document.getElementById("quizFeedbackArea");

    if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.textContent = "Evaluating...";
    }

    try {
        const profile = getLearnerProfile();
        const result = await apiFetch("/api/answer", {
            method: "POST",
            body: JSON.stringify({
                learner_id: profile.id,
                question_id: q.id,
                answer: currentSelectedAnswer,
                reasoning: reasoning
            })
        });

        // Update session results
        if (result.correct) {
            quizSessionResults.correct++;
        }
        quizSessionResults.masteryGain += (result.mastery_delta || 0);

        if (result.misconception_detected) {
            quizSessionResults.misconceptions.push({
                name: result.misconception_detected,
                explanation: result.misconception_explanation || ""
            });
        }

        // Color-code option buttons
        document.querySelectorAll(".quiz-option-btn").forEach(btn => {
            btn.disabled = true;
            const text = btn.querySelector("span") ? btn.querySelector("span").textContent : "";
            if (text.trim().toLowerCase() === result.correct_answer.trim().toLowerCase()) {
                btn.classList.add("correct-choice");
            } else if (text.trim().toLowerCase() === currentSelectedAnswer.trim().toLowerCase() && !result.correct) {
                btn.classList.add("wrong-choice");
            }
        });

        // Display Feedback
        if (feedbackArea) {
            feedbackArea.style.display = "block";
            let feedbackHtml = "";

            if (result.correct) {
                feedbackHtml += `
                    <div class="feedback-success-box">
                        <strong>✅ Correct!</strong> ${result.explanation}
                        <div style="margin-top: 8px; font-weight: 600; color: #23542A;">
                            Mastery: ${result.new_mastery}% (+${result.mastery_delta}%) | Calibrated Difficulty: Level ${result.difficulty_calibrated}
                        </div>
                    </div>
                `;
            } else {
                feedbackHtml += `
                    <div class="feedback-wrong-box">
                        <strong>❌ Incorrect.</strong> Correct answer: <strong>${result.correct_answer}</strong>
                        <p style="margin-top: 6px;">${result.explanation}</p>
                        <div style="margin-top: 6px; font-weight: 600; color: #792518;">
                            Mastery: ${result.new_mastery}% (${result.mastery_delta}%)
                        </div>
                    </div>
                `;
            }

            if (result.misconception_detected) {
                feedbackHtml += `
                    <div class="misconception-box">
                        <strong style="color: #983C1C;">💡 Misconception Detected:</strong> ${result.misconception_detected}
                        <p style="margin-top: 4px; color: var(--text);">${result.misconception_explanation || ''}</p>
                        ${result.remediation_hint ? `<p style="margin-top: 4px; font-size:12px; color:var(--muted);"><strong>Remediation:</strong> ${result.remediation_hint}</p>` : ''}
                    </div>
                `;
            }

            feedbackArea.innerHTML = feedbackHtml;
        }

        if (submitBtn) submitBtn.style.display = "none";
        if (nextBtn) {
            nextBtn.style.display = "block";
            nextBtn.textContent = (currentQuestionIndex + 1 < activeQuizQuestions.length)
                ? "Next Question →"
                : (currentTestMode === "diagnostic" ? "Finish Diagnostic & View Dashboard →" : "Finish Assessment & View Analysis →");
        }
    } catch (err) {
        alert("Could not submit answer to the backend. Please check connectivity.");
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.textContent = "Submit Answer";
        }
    }
}

function nextQuestion() {
    currentQuestionIndex++;
    if (currentQuestionIndex < activeQuizQuestions.length) {
        renderCurrentQuestion();
    } else {
        renderQuizSummary();
    }
}

function renderQuizSummary() {
    const quizCard = document.getElementById("activeQuizCard");
    const summaryCard = document.getElementById("quizSummaryCard");

    if (quizCard) quizCard.style.display = "none";
    if (summaryCard) summaryCard.style.display = "block";

    const scoreElem = document.getElementById("summaryScore");
    const deltaElem = document.getElementById("summaryMasteryDelta");
    const miscElem = document.getElementById("summaryMisconceptions");
    const nextElem = document.getElementById("summaryNextStep");
    const detailsElem = document.getElementById("summaryDetails");

    const pct = Math.round((quizSessionResults.correct / quizSessionResults.total) * 100) || 0;

    if (scoreElem) scoreElem.textContent = `${quizSessionResults.correct}/${quizSessionResults.total} (${pct}%)`;
    if (deltaElem) deltaElem.textContent = (quizSessionResults.masteryGain >= 0 ? "+" : "") + quizSessionResults.masteryGain.toFixed(1) + "%";
    if (miscElem) miscElem.textContent = quizSessionResults.misconceptions.length;

    let nextAction = "Adaptive Dashboard";
    if (pct < 50) nextAction = "Discuss with AI Tutor";
    else if (pct >= 80) nextAction = "Advance to Level 3/4";
    if (nextElem) nextElem.textContent = nextAction;

    if (detailsElem) {
        let detailsHtml = `<h4>Assessment Summary</h4>`;
        detailsHtml += `<p style="margin: 8px 0;">All responses evaluated and saved to your SQLite learner mastery profile.</p>`;

        if (quizSessionResults.misconceptions.length > 0) {
            detailsHtml += `<div style="margin-top: 12px;"><strong style="color: #983C1C;">Identified Misconceptions:</strong><ul style="margin: 6px 0 0 20px;">`;
            quizSessionResults.misconceptions.forEach(m => {
                detailsHtml += `<li><strong>${m.name}:</strong> ${m.explanation}</li>`;
            });
            detailsHtml += `</ul></div>`;
        } else {
            detailsHtml += `<p style="color: #4D7C54; font-weight: 600; margin-top: 8px;">✨ Strong conceptual reasoning! No major misconceptions flagged.</p>`;
        }

        detailsElem.innerHTML = detailsHtml;
    }
}

function resetQuizRunner() {
    const configCard = document.getElementById("testConfigCard");
    const quizCard = document.getElementById("activeQuizCard");
    const summaryCard = document.getElementById("quizSummaryCard");

    if (configCard) configCard.style.display = "block";
    if (quizCard) quizCard.style.display = "none";
    if (summaryCard) summaryCard.style.display = "none";

    const resultDiv = document.getElementById("testResult");
    if (resultDiv) resultDiv.textContent = "";
}

// ----------------------------------------------------------------------------
// 5. STUDENT DASHBOARD LOADER & CHART.JS RENDERING (dashboard.html)
// ----------------------------------------------------------------------------

async function loadDashboard() {
    updateNavLearnerBadge();

    const overall = document.getElementById("overallScore");
    const topicCount = document.getElementById("topicsCount");
    const testCount = document.getElementById("testsCount");
    const status = document.getElementById("learningStatus");

    if (!overall) return; // Not on dashboard page

    try {
        const [dashData, graphData] = await Promise.all([
            apiFetch("/api/dashboard/student"),
            apiFetch("/api/concepts/graph")
        ]);

        // Empty state check
        const emptyBanner = document.getElementById("newLearnerBanner");
        if (emptyBanner) {
            emptyBanner.style.display = dashData.is_new_learner ? "block" : "none";
        }

        // Top KPI Cards
        overall.textContent = `${dashData.accuracy_percent}%`;
        topicCount.textContent = dashData.concept_mastery.filter(c => c.attempts > 0).length;
        testCount.textContent = dashData.total_attempts;

        const activeCount = dashData.concept_mastery.filter(c => c.attempts > 0).length;
        status.textContent = dashData.is_new_learner ? "New Learner" : (activeCount < 4 ? "Calibrating" : "Active");

        // Streak badge
        const streakBadge = document.getElementById("streakBadge");
        if (streakBadge) {
            streakBadge.textContent = `🔥 Streak: ${dashData.streak_days || 1} Day(s)`;
        }

        // 1. Topic-wise Mastery Breakdown with progress bars
        const topicAnalysis = document.getElementById("topicAnalysis");
        if (topicAnalysis && dashData.concept_mastery) {
            let topicHtml = "";
            dashData.concept_mastery.forEach(c => {
                const fillClass = c.score >= 75 ? "mastery-fill-high" : (c.score >= 40 ? "mastery-fill-mid" : "mastery-fill-low");
                topicHtml += `
                    <div style="margin-bottom: 14px;">
                        <div style="display:flex; justify-content:space-between; font-size:13px; font-weight:600;">
                            <span>${c.title}</span>
                            <span>${c.score}% (${c.correct}/${c.attempts})</span>
                        </div>
                        <div class="mastery-progress-track">
                            <div class="mastery-progress-fill ${fillClass}" style="width: ${c.score}%;"></div>
                        </div>
                    </div>
                `;
            });
            topicAnalysis.innerHTML = topicHtml;
        }

        // 2. AI Learning Recommendations (Module 10)
        const recContainer = document.getElementById("recommendations");
        if (recContainer && dashData.recommendations) {
            let recHtml = `<ul style="list-style-type:none; display:flex; flex-direction:column; gap:10px;">`;
            dashData.recommendations.forEach(rec => {
                recHtml += `<li style="padding:10px 14px; background:#FAF4EB; border-left:3px solid var(--primary); border-radius:4px; font-size:13px; line-height:1.6;">${formatMarkdown(rec)}</li>`;
            });
            recHtml += `</ul>`;
            recContainer.innerHTML = recHtml;
        }

        // 3. Reasoning & Misconception Analysis
        const reasoningElem = document.getElementById("reasoningAnalysis");
        const miscListElem = document.getElementById("misconceptionList");
        if (reasoningElem) {
            reasoningElem.innerHTML = dashData.is_new_learner
                ? "Your reasoning patterns will appear here as you answer questions in the Test Centre."
                : `Analysis based on ${dashData.total_attempts} assessment answers submitted.`;
        }
        if (miscListElem && dashData.misconceptions) {
            if (dashData.misconceptions.length === 0) {
                miscListElem.innerHTML = `<p style="font-size:13px; color:#4D7C54;">● No active misconceptions detected!</p>`;
            } else {
                let miscHtml = `<div style="font-size:13px; font-weight:600; margin-bottom:8px; color:var(--text);">Detected Error Patterns:</div>`;
                dashData.misconceptions.forEach(m => {
                    miscHtml += `
                        <div class="misconception-box" style="margin-bottom:8px;">
                            <strong>${m.title}</strong>
                            <div style="font-size:12px; margin-top:3px;">${m.feedback}</div>
                            ${m.remediation ? `<div style="font-size:11px; color:var(--muted); margin-top:2px;"><strong>Fix:</strong> ${m.remediation}</div>` : ''}
                        </div>
                    `;
                });
                miscListElem.innerHTML = miscHtml;
            }
        }

        // 4. Spaced Repetition Due Reviews
        const dueReviewsElem = document.getElementById("dueReviewsList");
        if (dueReviewsElem && dashData.due_revisions) {
            if (dashData.due_revisions.length === 0) {
                dueReviewsElem.innerHTML = `<p style="font-size:13px; color:var(--muted);">All concepts are currently up-to-date! No reviews due today.</p>`;
            } else {
                let dueHtml = `<div style="display:flex; flex-direction:column; gap:8px;">`;
                dashData.due_revisions.forEach(r => {
                    dueHtml += `
                        <div style="display:flex; justify-content:space-between; align-items:center; background:#FAF4EB; padding:10px 14px; border-radius:8px; border:1px solid var(--border);">
                            <div>
                                <strong style="font-size:13px; color:var(--text);">${r.title}</strong>
                                <div style="font-size:11px; color:var(--muted);">Interval: ${r.interval_days} day(s)</div>
                            </div>
                            <a href="test.html?mode=spaced" class="primary-btn" style="padding:6px 12px; font-size:11px;">Review Now</a>
                        </div>
                    `;
                });
                dueHtml += `</div>`;
                dueReviewsElem.innerHTML = dueHtml;
            }
        }

        // 5. Concept Knowledge Graph DAG Visualizer (NetworkX)
        renderConceptGraphVisual(graphData);

        // 6. Chart.js Learning Progress Timeline
        renderLearningProgressChart(dashData.progress_timeline);

    } catch (err) {
        console.error("Dashboard Load Error:", err);
    }
}

function renderLearningProgressChart(timelineData) {
    const canvas = document.getElementById("progressChart");
    if (!canvas || typeof Chart === "undefined") return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    if (progressChartInstance) {
        progressChartInstance.destroy();
    }

    if (!timelineData || timelineData.length === 0) {
        // Draw placeholder for empty state
        timelineData = [
            { attempt: 1, accuracy_so_far: 0 },
            { attempt: 2, accuracy_so_far: 0 }
        ];
    }

    const labels = timelineData.map(d => `Q${d.attempt}`);
    const dataPoints = timelineData.map(d => d.accuracy_so_far);

    progressChartInstance = new Chart(ctx, {
        type: "line",
        data: {
            labels: labels,
            datasets: [{
                label: "Cumulative Accuracy %",
                data: dataPoints,
                borderColor: "#8B5E3C",
                backgroundColor: "rgba(139, 94, 60, 0.12)",
                borderWidth: 2.5,
                fill: true,
                tension: 0.35,
                pointBackgroundColor: "#8B5E3C",
                pointRadius: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    min: 0,
                    max: 100,
                    ticks: {
                        callback: val => val + "%"
                    },
                    grid: { color: "rgba(232, 216, 197, 0.5)" }
                },
                x: {
                    grid: { display: false }
                }
            },
            plugins: {
                legend: { display: false }
            }
        }
    });
}

function renderConceptGraphVisual(graphData) {
    const visual = document.getElementById("conceptGraphVisual");
    if (!visual || !graphData || !graphData.nodes) return;

    let html = `<div style="display:flex; flex-direction:column; gap:20px;">`;

    // Group concepts by prerequisite stages
    const levels = [
        { name: "Stage 1: Foundational Quantities", ids: ["electric-current", "potential-difference", "factors-affecting-resistance"] },
        { name: "Stage 2: Core Oppositions & Linear Law", ids: ["resistance", "ohms-law"] },
        { name: "Stage 3: Circuit Topologies", ids: ["series-circuits", "parallel-circuits"] },
        { name: "Stage 4: Power Dissipation & Joule Heating", ids: ["electrical-power", "heating-effect"] }
    ];

    levels.forEach(lvl => {
        html += `
            <div>
                <div style="font-size:11px; font-weight:700; color:var(--muted); text-transform:uppercase; letter-spacing:1px; margin-bottom:8px;">${lvl.name}</div>
                <div style="display:flex; gap:14px; flex-wrap:wrap;">
        `;

        lvl.ids.forEach(cid => {
            const node = graphData.nodes.find(c => c.id === cid);
            if (!node) return;

            let borderColor = "var(--border)";
            let badgeBg = "#E8D8C5";
            let badgeText = "Unattempted";

            if (node.status === "mastered") {
                borderColor = "#4D7C54";
                badgeBg = "#E8F4E8";
                badgeText = `Mastered (${node.mastery_score}%)`;
            } else if (node.status === "developing") {
                borderColor = "#C07D38";
                badgeBg = "#FCF3EA";
                badgeText = `Developing (${node.mastery_score}%)`;
            } else if (node.status === "gap") {
                borderColor = "#B84A39";
                badgeBg = "#FCEAEA";
                badgeText = `Gap (${node.mastery_score}%)`;
            }

            const prereqs = node.prerequisites && node.prerequisites.length > 0
                ? `<div style="font-size:10px; color:var(--muted); margin-top:4px;">Requires: ${node.prerequisites.join(", ")}</div>`
                : "";

            html += `
                <div class="concept-node" style="border: 2px solid ${borderColor}; min-width: 175px;">
                    <div style="font-weight:700; font-size:13px; color:var(--text);">${node.title}</div>
                    <div style="margin-top:6px;">
                        <span style="background:${badgeBg}; font-size:11px; padding:3px 8px; border-radius:12px; font-weight:600;">${badgeText}</span>
                    </div>
                    ${prereqs}
                </div>
            `;
        });

        html += `</div></div>`;
    });

    html += `</div>`;
    visual.innerHTML = html;
}

// ----------------------------------------------------------------------------
// 6. TEACHER DASHBOARD LOADER (teacher.html)
// ----------------------------------------------------------------------------

async function loadTeacherDashboard() {
    updateNavLearnerBadge();

    const totalStudentsElem = document.getElementById("teacherTotalStudents");
    if (!totalStudentsElem) return; // Not on teacher page

    try {
        const data = await apiFetch("/api/dashboard/teacher");

        // KPI Stats
        totalStudentsElem.textContent = data.total_learners;
        document.getElementById("teacherClassMastery").textContent = `${data.class_mastery}%`;
        document.getElementById("teacherTotalAttempts").textContent = data.total_attempts;
        document.getElementById("teacherTopGap").textContent = data.hardest_concept;

        // Concept Mastery Breakdown
        const conceptList = document.getElementById("teacherConceptList");
        if (conceptList && data.concept_breakdown) {
            let html = "";
            data.concept_breakdown.forEach(c => {
                const fillClass = c.average_mastery >= 70 ? "mastery-fill-high" : (c.average_mastery >= 40 ? "mastery-fill-mid" : "mastery-fill-low");
                html += `
                    <div style="margin-bottom: 14px;">
                        <div style="display:flex; justify-content:space-between; font-size:13px; font-weight:600;">
                            <span>${c.title}</span>
                            <span>${c.average_mastery}% (${c.students_tested} tested)</span>
                        </div>
                        <div class="mastery-progress-track">
                            <div class="mastery-progress-fill ${fillClass}" style="width: ${c.average_mastery}%;"></div>
                        </div>
                    </div>
                `;
            });
            conceptList.innerHTML = html;
        }

        // Cohort Misconceptions
        const miscList = document.getElementById("teacherMisconceptionList");
        if (miscList && data.common_misconceptions) {
            if (data.common_misconceptions.length === 0) {
                miscList.innerHTML = `<p style="font-size:13px; color:var(--muted);">No student errors recorded yet.</p>`;
            } else {
                let html = "";
                data.common_misconceptions.forEach(m => {
                    html += `
                        <div class="misconception-box" style="margin-bottom:10px;">
                            <strong>${m.title}</strong>
                            <div style="font-size:11px; color:var(--muted); margin-top:2px;">
                                Detected across ${m.count} student attempt(s)
                            </div>
                        </div>
                    `;
                });
                miscList.innerHTML = html;
            }
        }

        // Actionable Interventions
        const interventionsElem = document.getElementById("teacherInterventions");
        if (interventionsElem && data.interventions) {
            let html = `<ul style="list-style-type:none; display:flex; flex-direction:column; gap:10px;">`;
            data.interventions.forEach(item => {
                html += `
                    <li style="padding:12px 16px; background:#FAF4EB; border-left:4px solid var(--primary); border-radius:6px; font-size:13px; line-height:1.6;">
                        ${formatMarkdown(item)}
                    </li>
                `;
            });
            html += `</ul>`;
            interventionsElem.innerHTML = html;
        }

        // Student Roster Table
        const rosterBody = document.getElementById("teacherRosterBody");
        if (rosterBody && data.student_roster) {
            if (data.student_roster.length === 0) {
                rosterBody.innerHTML = `<tr><td colspan="6" style="padding:20px; text-align:center; color:var(--muted);">No student profiles recorded yet.</td></tr>`;
            } else {
                let html = "";
                data.student_roster.forEach(s => {
                    const statusColor = s.status === "Active" ? "#4D7C54" : "#C07D38";
                    html += `
                        <tr style="border-bottom: 1px solid var(--border);">
                            <td style="padding: 12px 10px; font-weight:600;">${s.display_name} <span style="font-size:11px; color:var(--muted);">(${s.learner_id})</span></td>
                            <td style="padding: 12px 10px;">${s.attempts}</td>
                            <td style="padding: 12px 10px;">${s.accuracy}%</td>
                            <td style="padding: 12px 10px; font-weight:600;">${s.average_mastery}%</td>
                            <td style="padding: 12px 10px; color:var(--muted);">${s.weakest_concept}</td>
                            <td style="padding: 12px 10px;"><span style="color:${statusColor}; font-weight:600;">● ${s.status}</span></td>
                        </tr>
                    `;
                });
                rosterBody.innerHTML = html;
            }
        }

    } catch (err) {
        console.error("Teacher Dashboard Load Error:", err);
    }
}

// ----------------------------------------------------------------------------
// 7. INITIALIZATION ON DOM READY
// ----------------------------------------------------------------------------

document.addEventListener("DOMContentLoaded", function() {
    updateNavLearnerBadge();

    const path = window.location.pathname;

    if (path.includes("dashboard.html")) {
        loadDashboard();
    } else if (path.includes("teacher.html")) {
        loadTeacherDashboard();
    } else if (path.includes("test.html")) {
        // Auto-check URL parameters for diagnostic test flow
        const urlParams = new URLSearchParams(window.location.search);
        const mode = urlParams.get("mode");
        if (mode) {
            switchTestMode(mode);
            // Automatically launch diagnostic assessment if requested
            if (mode === "diagnostic") {
                generateTest();
            }
        }
    }
});
