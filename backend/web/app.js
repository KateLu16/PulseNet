/* =====================================================
   PulseNet Teacher Dashboard — app.js
   Kahoot-style flow: Setup -> Lobby -> Live -> Results
   i18n: EN (default) / VI toggle
   ===================================================== */

"use strict";

/* ---------------- i18n ---------------- */

const I18N = {
    en: {
        "app.subtitle": "Wireless classroom quiz system",
        "app.teacher": "Teacher",
        "app.teacherRole": "Room console",
        "conn.connecting": "Connecting…",
        "conn.ok": "Server connected",
        "conn.lost": "Server lost",
        "gw.title": "BLE gateway on the Raspberry Pi — bridge to student devices",
        "gw.connected": "Gateway: device linked",
        "gw.waiting": "Gateway: waiting for device",
        "gw.off": "Gateway: not running",
        "gw.deviceInfo": "BLE: ",
        "gw.pushed": "Last question pushed: Q",
        "gw.none": "No question pushed yet.",
        "quiz.label": "Quiz",
        "quiz.refresh": "Reload quiz list",
        "quiz.newPlaceholder": "New quiz name, e.g. IoT Midterm",
        "quiz.create": "Create",
        "quiz.none": "— No quizzes —",
        "empty.title": "No quiz selected.",
        "empty.hint": "Create a new quiz above, or pick one from the list.",
        "tabs.setup": "Setup",
        "tabs.live": "Live session",
        "tabs.results": "Results",
        "tabs.stats": "Statistics",
        "page.setup.t": "Session setup",
        "page.setup.s": "Import questions and configure the class session",
        "page.live.t": "Live session",
        "page.live.s": "Lobby, quiz clock and student tracker",
        "page.results.t": "Results",
        "page.results.s": "Scores and per-student breakdown",
        "page.stats.t": "Statistics",
        "page.stats.s": "Per-question answer analysis",
        "status.draft": "Draft",
        "status.lobby": "Lobby",
        "status.running": "Live",
        "status.finished": "Finished",
        "setup.importTitle": "Import questions",
        "setup.importHint": "CSV columns: <code>Question, A, B, C, D, Correct Answer</code>. The whole file is validated before anything is saved.",
        "setup.pickFile": "Choose CSV",
        "setup.noFile": "No file selected",
        "setup.importBtn": "Import",
        "setup.template": "Download template",
        "setup.templateBtn": "CSV template",
        "setup.settingsTitle": "Session settings",
        "setup.timeLimit": "Time limit (minutes)",
        "setup.expected": "Students in class",
        "setup.prefix": "Student ID prefix",
        "setup.length": "ID length",
        "setup.pushBtn": "Push to devices",
        "setup.pushHint": "Devices will show the quiz name and wait for students to enter their IDs.",
        "setup.questionsList": "Question list",
        "setup.colNo": "No.",
        "setup.colQuestion": "Question",
        "setup.colAnswer": "Answer",
        "setup.noQuestions": "No questions yet.",
        "setup.importOk": "Imported {imported} new questions, skipped {duplicates} duplicates.",
        "setup.importBad": "Import failed — nothing was saved.",
        "setup.aiTitle": "Generate from document (AI)",
        "setup.aiHint": "Upload a PDF / DOCX / TXT — AI reads the document and writes multiple-choice questions into this quiz. Review every question below before pushing to devices.",
        "setup.aiPickFile": "Choose document",
        "setup.aiNum": "Number of questions",
        "setup.aiLang": "Question language",
        "setup.aiLangAuto": "Same as document",
        "setup.aiLangVi": "Vietnamese",
        "setup.aiLangEn": "English",
        "setup.aiBtn": "Generate with AI",
        "setup.aiWorking": "Generating…",
        "setup.aiOk": "AI generated {n} question(s) from “{file}”. Review them in the list below.",
        "setup.aiBad": "AI generation failed.",
        "setup.aiReady": "AI ready",
        "setup.aiNoKey": "No API key",
        "setup.aiStatusDown": "AI status unavailable",
        "setup.aiKeyHint": "AI is not configured yet — add GEMINI_API_KEY to backend/.env on the Pi, then restart the server.",
        "setup.aiDraftOnly": "Only a draft quiz can receive AI questions.",
        "setup.needQuestions": "Import at least 1 question first.",
        "setup.needTime": "Set the time limit first.",
        "setup.saved": "Settings saved. Pushing to devices…",
        "setup.pushed": "Session pushed! Devices are accepting student IDs.",
        "setup.minutes": "{m} min",
        "live.draftTitle": "Quiz not pushed yet",
        "live.draftHint": "Set up questions, time limit and class info in the Setup tab, then push the session to the devices.",
        "live.lobbyTitle": "Lobby",
        "live.joinedHint": "students joined",
        "live.startBtn": "Start quiz",
        "live.cancelBtn": "Cancel",
        "live.lobbyHint": "Devices are accepting student IDs — start whenever everyone is in.",
        "live.timeLeft": "Time left",
        "live.finishBtn": "Finish",
        "live.progress": "Progress",
        "live.gatewayTitle": "Gateway",
        "live.followTable": "Live student tracker",
        "live.colId": "Student ID",
        "live.colDevice": "Device (MAC)",
        "live.colOn": "On question",
        "live.colAnswered": "Answered",
        "live.colCorrect": "✓",
        "live.colWrong": "✗",
        "live.colScore": "Score",
        "live.noStudents": "No students registered.",
        "live.followHint": "Questions advance on each device right after a student answers — every student moves at their own pace under the same quiz clock.",
        "live.done": "Done",
        "live.answeredTotal": "Questions answered so far",
        "live.runningHint": "The quiz clock runs for the whole class; each student advances after every answer.",
        "live.finishedTitle": "Quiz finished",
        "live.finishedHint": "Check the Results and Statistics tabs for the full breakdown.",
        "live.startOk": "Quiz started! Good luck to the class.",
        "live.finishConfirm": "Finish the quiz? Students cannot answer anymore.",
        "live.finishOk": "Quiz finished. See Results for scores.",
        "live.cancelOk": "Lobby cancelled — back to setup.",
        "live.notEnough": "No students have joined yet.",
        "live.created": "Quiz #{id} — {title} created",
        "live.enterTitle": "Enter a quiz name first.",
        "results.perStudent": "Student results",
        "results.colId": "Student ID",
        "results.colAnswered": "Answered",
        "results.colCorrect": "✓",
        "results.colWrong": "✗",
        "results.colScore": "Score",
        "results.colAcc": "Accuracy",
        "results.empty": "No data yet.",
        "results.students": "{n} students",
        "results.registered": "Registered students",
        "results.answered1": "Answered ≥ 1 question",
        "results.avgScore": "Class average",
        "results.accuracy": "Overall accuracy",
        "results.responses": "Total answers",
        "stats.empty": "No statistics yet.",
        "stats.questions": "Questions",
        "stats.correctRate": "{p}% correct",
        "stats.noAnswers": "No answers",
        "stats.answer": "Answer: {a}",
        "stats.answers": "{n} answers",
    },
    vi: {
        "app.subtitle": "Hệ thống trắc nghiệm không dây",
        "app.teacher": "Giảng viên",
        "app.teacherRole": "Bảng điều khiển lớp",
        "conn.connecting": "Đang kết nối…",
        "conn.ok": "Đã kết nối server",
        "conn.lost": "Mất kết nối server",
        "gw.title": "Gateway BLE trên Raspberry Pi — cầu nối tới thiết bị sinh viên",
        "gw.connected": "Gateway: đã nối thiết bị",
        "gw.waiting": "Gateway: chờ thiết bị",
        "gw.off": "Gateway: chưa chạy",
        "gw.deviceInfo": "BLE: ",
        "gw.pushed": "Câu cuối đã đẩy: Q",
        "gw.none": "Chưa đẩy câu hỏi nào.",
        "quiz.label": "Buổi quiz",
        "quiz.refresh": "Tải lại danh sách quiz",
        "quiz.newPlaceholder": "Tên quiz mới, ví dụ: Kiểm tra IoT",
        "quiz.create": "Tạo quiz",
        "quiz.none": "— Chưa có quiz nào —",
        "empty.title": "Chưa chọn buổi quiz nào.",
        "empty.hint": "Tạo quiz mới ở trên, hoặc chọn một quiz từ danh sách.",
        "tabs.setup": "Soạn & Cài đặt",
        "tabs.live": "Phiên trực tiếp",
        "tabs.results": "Kết quả",
        "tabs.stats": "Thống kê",
        "page.setup.t": "Soạn & Cài đặt",
        "page.setup.s": "Nhập câu hỏi và cấu hình buổi kiểm tra",
        "page.live.t": "Phiên trực tiếp",
        "page.live.s": "Sảnh chờ, đồng hồ và theo dõi sinh viên",
        "page.results.t": "Kết quả",
        "page.results.s": "Điểm số từng sinh viên",
        "page.stats.t": "Thống kê",
        "page.stats.s": "Phân tích đáp án từng câu hỏi",
        "status.draft": "Nháp",
        "status.lobby": "Sảnh chờ",
        "status.running": "Đang chạy",
        "status.finished": "Đã kết thúc",
        "setup.importTitle": "Nhập câu hỏi",
        "setup.importHint": "Cột CSV: <code>Question, A, B, C, D, Correct Answer</code>. Cả file được kiểm tra trước khi lưu.",
        "setup.pickFile": "Chọn file CSV",
        "setup.noFile": "Chưa chọn file",
        "setup.importBtn": "Nhập câu hỏi",
        "setup.template": "Tải file mẫu",
        "setup.templateBtn": "File mẫu CSV",
        "setup.settingsTitle": "Cài đặt buổi thi",
        "setup.timeLimit": "Thời gian làm bài (phút)",
        "setup.expected": "Số sinh viên trong lớp",
        "setup.prefix": "Tiền tố MSSV",
        "setup.length": "Độ dài MSSV",
        "setup.pushBtn": "Gửi xuống thiết bị",
        "setup.pushHint": "Thiết bị sẽ hiện tên bài kiểm tra và chờ sinh viên nhập MSSV.",
        "setup.questionsList": "Danh sách câu hỏi",
        "setup.colNo": "STT",
        "setup.colQuestion": "Câu hỏi",
        "setup.colAnswer": "Đáp án",
        "setup.noQuestions": "Chưa có câu hỏi nào.",
        "setup.importOk": "Đã nhập {imported} câu mới, bỏ qua {duplicates} câu trùng.",
        "setup.importBad": "Nhập thất bại — không lưu gì.",
        "setup.aiTitle": "Tạo câu hỏi từ tài liệu (AI)",
        "setup.aiHint": "Tải lên file PDF / DOCX / TXT — AI đọc tài liệu và soạn câu hỏi trắc nghiệm vào quiz này. Hãy xem lại từng câu bên dưới trước khi gửi xuống thiết bị.",
        "setup.aiPickFile": "Chọn tài liệu",
        "setup.aiNum": "Số câu hỏi",
        "setup.aiLang": "Ngôn ngữ câu hỏi",
        "setup.aiLangAuto": "Theo tài liệu",
        "setup.aiLangVi": "Tiếng Việt",
        "setup.aiLangEn": "Tiếng Anh",
        "setup.aiBtn": "Sinh câu hỏi bằng AI",
        "setup.aiWorking": "Đang sinh câu hỏi…",
        "setup.aiOk": "AI đã sinh {n} câu hỏi từ “{file}”. Xem lại ở danh sách bên dưới.",
        "setup.aiBad": "Sinh câu hỏi bằng AI thất bại.",
        "setup.aiReady": "AI sẵn sàng",
        "setup.aiNoKey": "Chưa có API key",
        "setup.aiStatusDown": "Không xem được trạng thái AI",
        "setup.aiKeyHint": "AI chưa được cấu hình — thêm GEMINI_API_KEY vào backend/.env trên Pi rồi khởi động lại server.",
        "setup.aiDraftOnly": "Chỉ quiz ở trạng thái Nháp mới nhận được câu hỏi AI.",
        "setup.needQuestions": "Hãy nhập ít nhất 1 câu hỏi trước.",
        "setup.needTime": "Hãy đặt thời gian làm bài trước.",
        "setup.saved": "Đã lưu cài đặt. Đang gửi xuống thiết bị…",
        "setup.pushed": "Đã gửi phiên! Thiết bị đang nhận MSSV của sinh viên.",
        "setup.minutes": "{m} phút",
        "live.draftTitle": "Quiz chưa gửi xuống thiết bị",
        "live.draftHint": "Soạn câu hỏi, đặt thời gian và thông tin lớp ở tab Soạn & Cài đặt, sau đó gửi phiên xuống thiết bị.",
        "live.lobbyTitle": "Sảnh chờ",
        "live.joinedHint": "sinh viên đã vào",
        "live.startBtn": "Bắt đầu quiz",
        "live.cancelBtn": "Hủy",
        "live.lobbyHint": "Thiết bị đang nhận MSSV — bắt đầu khi đủ người.",
        "live.timeLeft": "Thời gian còn lại",
        "live.finishBtn": "Kết thúc",
        "live.progress": "Tiến độ",
        "live.gatewayTitle": "Gateway",
        "live.followTable": "Theo dõi sinh viên trực tiếp",
        "live.colId": "MSSV",
        "live.colDevice": "Thiết bị (MAC)",
        "live.colOn": "Đang làm",
        "live.colAnswered": "Đã trả lời",
        "live.colCorrect": "✓",
        "live.colWrong": "✗",
        "live.colScore": "Điểm",
        "live.noStudents": "Chưa có sinh viên nào đăng ký.",
        "live.followHint": "Câu hỏi tự chuyển trên từng thiết bị ngay sau mỗi lượt trả lời — mỗi sinh viên một nhịp riêng, chung một đồng hồ.",
        "live.done": "Xong",
        "live.answeredTotal": "Số câu đã được trả lời",
        "live.runningHint": "Đồng hồ chạy chung cho cả lớp; mỗi sinh viên tự chuyển câu sau khi trả lời.",
        "live.finishedTitle": "Quiz đã kết thúc",
        "live.finishedHint": "Xem tab Kết quả và Thống kê để biết chi tiết.",
        "live.startOk": "Quiz đã bắt đầu! Chúc lớp làm bài tốt.",
        "live.finishConfirm": "Kết thúc quiz? Sinh viên sẽ không trả lời thêm được.",
        "live.finishOk": "Quiz đã kết thúc. Xem điểm ở tab Kết quả.",
        "live.cancelOk": "Đã hủy sảnh chờ — quay lại bước soạn.",
        "live.notEnough": "Chưa có sinh viên nào vào.",
        "live.created": "Đã tạo quiz #{id} — {title}",
        "live.enterTitle": "Nhập tên quiz trước.",
        "results.perStudent": "Kết quả từng sinh viên",
        "results.colId": "MSSV",
        "results.colAnswered": "Đã trả lời",
        "results.colCorrect": "✓",
        "results.colWrong": "✗",
        "results.colScore": "Điểm",
        "results.colAcc": "Độ chính xác",
        "results.empty": "Chưa có dữ liệu.",
        "results.students": "{n} sinh viên",
        "results.registered": "Sinh viên đăng ký",
        "results.answered1": "Trả lời ≥ 1 câu",
        "results.avgScore": "Điểm trung bình",
        "results.accuracy": "Độ chính xác tổng",
        "results.responses": "Tổng lượt trả lời",
        "stats.empty": "Chưa có dữ liệu thống kê.",
        "stats.questions": "Số câu hỏi",
        "stats.correctRate": "{p}% đúng",
        "stats.noAnswers": "Chưa có trả lời",
        "stats.answer": "Đáp án: {a}",
        "stats.answers": "{n} lượt trả lời",
    },
};

let lang = localStorage.getItem("pulsenet_lang") || "en";

function t(key, params) {
    let s = (I18N[lang] && I18N[lang][key]) || I18N.en[key] || key;

    if (params) {
        for (const [k, v] of Object.entries(params)) {
            s = s.split(`{${k}}`).join(v);
        }
    }

    return s;
}

function applyI18n() {
    document.querySelectorAll("[data-i18n]").forEach((el) => {
        const v = t(el.dataset.i18n);
        if (v.includes("<")) el.innerHTML = v; else el.textContent = v;
    });

    document.querySelectorAll("[data-i18n-ph]").forEach((el) => {
        el.placeholder = t(el.dataset.i18nPh);
    });

    document.querySelectorAll("[data-i18n-title]").forEach((el) => {
        el.title = t(el.dataset.i18nTitle);
    });

    const btn = $("#langBtn");
    btn.textContent = lang === "en" ? "VI" : "EN";
    btn.title = lang === "en" ? "Chuyển sang tiếng Việt" : "Switch to English";

    document.documentElement.lang = lang;
}

/* ---------------- Helpers ---------------- */

const $ = (sel) => document.querySelector(sel);

const esc = (s) =>
    String(s ?? "").replace(
        /[&<>"']/g,
        (c) => ({
            "&": "&amp;",
            "<": "&lt;",
            ">": "&gt;",
            '"': "&quot;",
            "'": "&#39;",
        })[c]
    );

function toast(msg, isErr = false) {
    const el = $("#toast");
    el.textContent = msg;
    el.classList.toggle("err", isErr);
    el.classList.remove("hidden");
    clearTimeout(toast._t);
    toast._t = setTimeout(() => el.classList.add("hidden"), 3500);
}

async function api(path, options = {}) {
    const opts = { headers: {}, ...options };

    if (opts.body && !(opts.body instanceof FormData)) {
        opts.headers["Content-Type"] = "application/json";
        opts.body = JSON.stringify(opts.body);
    }

    let res;
    try {
        res = await fetch(path, opts);
    } catch {
        setConn(false);
        throw { status: 0, detail: t("conn.lost") };
    }

    setConn(true);

    let data = null;
    try { data = await res.json(); } catch { /* no body */ }

    if (!res.ok) {
        throw {
            status: res.status,
            detail: data && data.detail !== undefined ? data.detail : data,
        };
    }

    return data;
}

function errMsg(err) {
    if (!err) return t("gw.none");
    if (typeof err.detail === "string") return err.detail;
    if (err.message) return err.message;
    return String(err);
}

function setConn(ok) {
    const dot = $("#connStatus .dot");
    $("#connText").textContent = ok ? t("conn.ok") : t("conn.lost");
    dot.className = "dot " + (ok ? "dot-green" : "dot-red");
}

const STATUS_KEY = {
    draft: "status.draft",
    lobby: "status.lobby",
    running: "status.running",
    finished: "status.finished",
};

const fmtTime = (iso) => {
    if (!iso) return "—";
    const d = new Date(iso);
    return d.toLocaleTimeString(lang === "vi" ? "vi-VN" : "en-GB", {
        hour: "2-digit", minute: "2-digit", second: "2-digit",
    });
};

/* ---------------- State ---------------- */

const state = {
    quizId: null,
    quiz: null,
    tab: "setup",
    pollTimer: null,
    liveTimer: null,
};

/* ---------------- Quiz bar ---------------- */

async function loadQuizzes(keepSelection = true) {
    let quizzes;
    try {
        quizzes = await api("/api/quizzes");
    } catch (err) {
        toast(errMsg(err), true);
        return;
    }

    const sel = $("#quizSelect");
    const prev = keepSelection ? state.quizId : null;

    sel.innerHTML =
        quizzes.length === 0
            ? `<option value=''>${esc(t("quiz.none"))}</option>`
            : quizzes
                .map((q) => `<option value="${q.id}">#${q.id} — ${esc(q.title)} (${t(STATUS_KEY[q.status] || q.status)})</option>`)
                .join("");

    const exists = quizzes.some((q) => q.id === prev);
    const target = exists ? prev : (quizzes[0] ? quizzes[0].id : null);

    if (target) {
        sel.value = String(target);
        await selectQuiz(target);
    } else {
        state.quizId = null;
        state.quiz = null;
        $("#quizPanel").classList.add("hidden");
        $("#emptyState").classList.remove("hidden");
    }
}

async function selectQuiz(id) {
    state.quizId = id;

    try {
        state.quiz = await api(`/api/quizzes/${id}`);
    } catch (err) {
        toast(errMsg(err), true);
        return;
    }

    $("#emptyState").classList.add("hidden");
    $("#quizPanel").classList.remove("hidden");
    $("#quizTitle").textContent = `#${state.quiz.id} — ${state.quiz.title}`;

    renderBadge();
    loadSettingsForm();
    await switchTab(preferredTab());
    restartPolling();
}

function preferredTab() {
    const st = state.quiz ? state.quiz.status : "draft";
    if (st === "lobby" || st === "running") return "live";
    if (state.tab === "live" && st === "draft") return "setup";
    return state.tab;
}

function renderBadge() {
    const q = state.quiz;
    const badge = $("#quizBadge");
    badge.textContent = t(STATUS_KEY[q.status] || q.status);
    badge.className = "badge badge-" + q.status;

    updateAiCard();
}

async function createQuiz() {
    const title = $("#newQuizTitle").value.trim();
    if (!title) { toast(t("live.enterTitle"), true); return; }

    try {
        const quiz = await api("/api/quizzes", { method: "POST", body: { title } });
        $("#newQuizTitle").value = "";
        toast(t("live.created", { id: quiz.id, title: quiz.title }));
        state.tab = "setup";
        await loadQuizzes(false);
    } catch (err) {
        toast(errMsg(err), true);
    }
}

/* ---------------- Tabs ---------------- */

const PAGE_META = {
    setup: ["page.setup.t", "page.setup.s"],
    live: ["page.live.t", "page.live.s"],
    results: ["page.results.t", "page.results.s"],
    stats: ["page.stats.t", "page.stats.s"],
};

async function switchTab(tab) {
    state.tab = tab;

    const meta = PAGE_META[tab] || PAGE_META.setup;
    $("#pageTitle").textContent = t(meta[0]);
    $("#pageSub").textContent = t(meta[1]);

    document.querySelectorAll(".tab").forEach((b) =>
        b.classList.toggle("active", b.dataset.tab === tab)
    );

    document.querySelectorAll(".tabpane").forEach((p) =>
        p.classList.add("hidden")
    );

    $(`#tab-${tab}`).classList.remove("hidden");

    if (tab === "setup") await loadQuestions();
    if (tab === "live") await refreshLive();
    if (tab === "results") await loadResults();
    if (tab === "stats") await loadStats();

    restartPolling();
}

/* ---------------- Tab: SETUP ---------------- */

async function loadQuestions() {
    let questions;
    try {
        questions = await api(`/api/quizzes/${state.quizId}/questions`);
    } catch (err) {
        toast(errMsg(err), true);
        return;
    }

    $("#questionCount").textContent = questions.length;

    $("#questionsBody").innerHTML =
        questions.length === 0
            ? `<tr><td colspan='7' class='muted ta-c pad'>${esc(t("setup.noQuestions"))}</td></tr>`
            : questions
                .map((q) => `
                    <tr>
                        <td class="ta-c"><b>${q.question_number}</b></td>
                        <td>${esc(q.question_text)}</td>
                        <td>${esc(q.option_a)}</td>
                        <td>${esc(q.option_b)}</td>
                        <td>${esc(q.option_c)}</td>
                        <td>${esc(q.option_d)}</td>
                        <td class="ta-c"><span class="chip chip-correct">${q.correct_answer}</span></td>
                    </tr>`)
                .join("");
}

function loadSettingsForm() {
    const q = state.quiz;
    if (!q) return;

    $("#timeLimitInput").value = q.time_limit_sec ? Math.round(q.time_limit_sec / 60) : "";
    $("#expectedInput").value = q.expected_students || "";
    $("#prefixInput").value = q.id_prefix || "";
    $("#idLengthInput").value = q.id_length || "";
}

function renderImportResult(result, ok) {
    const box = $("#importResult");
    box.classList.remove("hidden");

    const errors = result.errors_details || [];
    const dups = result.duplicate_details || [];

    let html = "";

    if (ok) {
        html += `<div class="import-box import-ok"><b>✔</b> ${esc(t("setup.importOk", { imported: result.imported, duplicates: result.duplicates }))}</div>`;
    } else {
        html += `<div class="import-box import-bad"><b>✖</b> ${esc(t("setup.importBad"))}</div>`;
    }

    if (errors.length) {
        html += `
            <div class="table-wrap"><table class="table">
                <thead><tr><th class="ta-c">Row</th><th>Field</th><th>Error</th></tr></thead>
                <tbody>
                ${errors.map((e) => `<tr><td class="ta-c">${e.row}</td><td>${esc(e.field)}</td><td>${esc(e.message)}</td></tr>`).join("")}
                </tbody>
            </table></div>`;
    }

    if (dups.length) {
        html += `
            <div class="table-wrap"><table class="table">
                <thead><tr><th class="ta-c">Row</th><th>Duplicate</th></tr></thead>
                <tbody>
                ${dups.map((d) => `<tr><td class="ta-c">${d.row}</td><td>${esc(d.message)}</td></tr>`).join("")}
                </tbody>
            </table></div>`;
    }

    box.innerHTML = html;
}

/* ---------------- Tab: SETUP — AI generation ---------------- */

async function refreshAiStatus() {
    const chip = $("#aiStatusChip");

    let st;
    try {
        st = await api("/api/ai/status");
    } catch {
        chip.textContent = t("setup.aiStatusDown");
        chip.className = "chip chip-warn";
        return;
    }

    if (st.configured) {
        chip.textContent = `${t("setup.aiReady")} · ${st.model}`;
        chip.className = "chip chip-ok";
        $("#aiKeyHint").classList.add("hidden");
    } else {
        chip.textContent = t("setup.aiNoKey");
        chip.className = "chip chip-warn";
        $("#aiKeyHint").classList.remove("hidden");
    }
}

function updateAiCard() {
    const isDraft = state.quiz ? state.quiz.status === "draft" : false;
    const hasFile = $("#aiFile").files.length > 0;

    const btn = $("#aiGenerateBtn");
    btn.disabled = !isDraft || !hasFile;
    btn.title = !isDraft ? t("setup.aiDraftOnly") : "";
}

async function generateAi() {
    const input = $("#aiFile");

    if (!input.files.length) { toast(t("setup.noFile"), true); return; }

    const fd = new FormData();
    fd.append("file", input.files[0]);
    fd.append("num_questions", $("#aiNum").value || "10");
    fd.append("language", $("#aiLang").value);

    const btn = $("#aiGenerateBtn");
    btn.disabled = true;
    btn.textContent = t("setup.aiWorking");

    const box = $("#aiResult");
    box.classList.add("hidden");

    try {
        let result;

        try {
            result = await api(`/api/quizzes/${state.quizId}/questions/generate-ai`, {
                method: "POST",
                body: fd,
            });
        } catch (err) {
            // Backend errors arrive as a string detail — surface it.
            throw typeof err.detail === "string" ? new Error(err.detail) : err;
        }

        box.classList.remove("hidden");
        box.innerHTML = `<div class="import-box import-ok"><b>✔</b> ${esc(t("setup.aiOk", { n: result.generated, file: result.filename }))}</div>`;

        toast(t("setup.aiOk", { n: result.generated, file: result.filename }));

        input.value = "";
        $("#aiFileName").textContent = t("setup.noFile");

        await loadQuestions();
    } catch (err) {
        box.classList.remove("hidden");
        box.innerHTML = `<div class="import-box import-bad"><b>✖</b> ${esc(t("setup.aiBad"))} ${esc(err.message || "")}</div>`;
        toast(errMsg(err), true);
    } finally {
        btn.textContent = t("setup.aiBtn");
        updateAiCard();
    }
}

async function importCsv() {
    const input = $("#csvFile");

    if (!input.files.length) { toast(t("setup.noFile"), true); return; }

    const fd = new FormData();
    fd.append("file", input.files[0]);

    $("#importBtn").disabled = true;

    try {
        let result;
        let ok = true;

        try {
            result = await api(`/api/quizzes/${state.quizId}/questions/import`, {
                method: "POST",
                body: fd,
            });
        } catch (err) {
            if (err.status === 400 && err.detail && typeof err.detail === "object") {
                result = err.detail;
                ok = false;
            } else {
                throw err;
            }
        }

        renderImportResult(result, ok);
        await loadQuestions();
    } catch (err) {
        toast(errMsg(err), true);
    } finally {
        $("#importBtn").disabled = false;
    }
}

function downloadTemplate() {
    const rows = [
        "Question,A,B,C,D,Correct Answer",
        "\"Which protocol is low power?\",WiFi,BLE,HTTP,FTP,B",
        "\"What does IoT stand for?, Internet of Things,Internet of Telephones,Internal Optical Tool,Input Output Table,A",
        "\"Which device acts as the BLE gateway?,ESP32,Raspberry Pi 4B,Arduino Uno,CR2032,B",
    ];

    const blob = new Blob(["\uFEFF" + rows.join("\r\n")], {
        type: "text/csv;charset=utf-8",
    });

    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "pulsenet_question_template.csv";
    a.click();
    URL.revokeObjectURL(a.href);
}

async function pushToDevices() {
    const minutes = Number($("#timeLimitInput").value);
    const expected = Number($("#expectedInput").value) || null;
    const prefix = $("#prefixInput").value.trim() || null;
    const idLength = Number($("#idLengthInput").value) || null;

    let questions;
    try {
        questions = await api(`/api/quizzes/${state.quizId}/questions`);
    } catch (err) {
        toast(errMsg(err), true);
        return;
    }

    if (!questions.length) {
        toast(t("setup.needQuestions"), true);
        return;
    }

    if (!minutes || minutes < 1) {
        toast(t("setup.needTime"), true);
        return;
    }

    try {
        await api(`/api/quizzes/${state.quizId}/setup`, {
            method: "POST",
            body: {
                time_limit_sec: Math.round(minutes * 60),
                expected_students: expected,
                id_prefix: prefix,
                id_length: idLength,
            },
        });

        toast(t("setup.saved"));

        await api(`/api/quizzes/${state.quizId}/lobby`, { method: "POST" });

        toast(t("setup.pushed"));

        state.quiz = await api(`/api/quizzes/${state.quizId}`);
        renderBadge();
        await loadQuizzes();
        state.tab = "live";
        await switchTab("live");
    } catch (err) {
        toast(errMsg(err), true);
    }
}

/* ---------------- Tab: LIVE ---------------- */

async function refreshLive() {
    if (state.quizId == null) return;

    try {
        state.quiz = await api(`/api/quizzes/${state.quizId}`);
        renderBadge();
    } catch { /* transient */ }

    const st = state.quiz ? state.quiz.status : "draft";

    $("#liveDraft").classList.toggle("hidden", st !== "draft");
    $("#liveLobby").classList.toggle("hidden", st !== "lobby");
    $("#liveRun").classList.toggle("hidden", st !== "running" && st !== "finished");
    $("#liveFinished").classList.toggle("hidden", st !== "finished");

    if (st === "draft") return;

    let students = null;
    try {
        students = await api(`/api/quizzes/${state.quizId}/students`);
    } catch { students = null; }

    if (st === "lobby") {
        const expected = state.quiz.expected_students || students.total_students || 0;
        const joined = students ? students.total_students : 0;

        $("#joinedCount").textContent = joined;
        $("#expectedCount").textContent = `/ ${expected}`;
        $("#lobbyPin").textContent = `#${state.quiz.id} — ${state.quiz.title}`;
        $("#lobbyBar").style.width =
            expected > 0 ? Math.min(100, Math.round((joined / expected) * 100)) + "%" : "0%";

        $("#startBtn").disabled = joined === 0;

        $("#joinedList").innerHTML =
            joined === 0
                ? `<span class='muted'>${esc(t("live.noStudents"))}</span>`
                : students.students
                    .map((s) => `<span class="joined-item">${esc(s.student_id)}</span>`)
                    .join("");
        return;
    }

    // running / finished

    $("#finishBtn").disabled = st !== "running";
    $("#liveHint").textContent =
        st === "running" ? t("live.runningHint") : t("live.finishedHint");

    // Quiz clock
    const q = state.quiz;
    const clockEl = $("#quizClock");

    if (q.status === "running" && q.started_at && q.time_limit_sec) {
        const iso = q.started_at.endsWith("Z") ? q.started_at : q.started_at + "Z";
        const deadline = new Date(iso).getTime() + q.time_limit_sec * 1000;
        const remaining = Math.max(0, Math.round((deadline - Date.now()) / 1000));

        const mm = String(Math.floor(remaining / 60)).padStart(2, "0");
        const ss = String(remaining % 60).padStart(2, "0");

        clockEl.textContent = `${mm}:${ss}`;
        clockEl.classList.toggle("low", remaining < 60);
    } else {
        clockEl.textContent = "00:00";
        clockEl.classList.remove("low");
    }

    // Gateway info
    const gw = gwState;
    if (gw && gw.online && gw.connected) {
        $("#gwChip").textContent = t("gw.connected");
        $("#gwChip").className = "chip chip-ok";

        $("#gwInfo").innerHTML =
            esc(t("gw.deviceInfo") + (gw.device_address || "?")) +
            "<br>" +
            (gw.last_pushed_question != null
                ? esc(t("gw.pushed") + gw.last_pushed_question)
                : esc(t("gw.none")));
    } else {
        $("#gwChip").textContent = gw && gw.online ? t("gw.waiting") : t("gw.off");
        $("#gwChip").className = "chip " + (gw && gw.online ? "chip-warn" : "chip-bad");
        $("#gwInfo").textContent = "—";
    }

    // Per-student live table
    let answeredTotal = 0;
    let slots = 0;

    if (students) {
        $("#studentCount").textContent = students.total_students;

        $("#studentsBody").innerHTML =
            students.total_students === 0
                ? `<tr><td colspan='7' class='muted ta-c pad'>${esc(t("live.noStudents"))}</td></tr>`
                : students.students
                    .map((s) => {
                        const tq = s.total_questions || 0;
                        const done = tq > 0 && s.answered_count >= tq;
                        const nowOn = done ? t("live.done") : `Q${(s.last_answered_question || 0) + 1}`;

                        answeredTotal += s.answered_count;
                        slots += tq;

                        return `
                            <tr>
                                <td><b>${esc(s.student_id)}</b></td>
                                <td class="muted">${esc(s.device_mac)}</td>
                                <td class="ta-c">${done ? `<span class="chip chip-ok">✓ ${esc(nowOn)}</span>` : nowOn}</td>
                                <td class="ta-c">${s.answered_count} / ${tq}</td>
                                <td class="ta-c"><span class="chip chip-ok">${s.correct_count}</span></td>
                                <td class="ta-c"><span class="chip chip-bad">${s.wrong_count}</span></td>
                                <td class="ta-c"><b>${s.score}</b>/10</td>
                            </tr>`;
                    })
                    .join("");
    }

    $("#progressCount").textContent = `${answeredTotal} / ${slots}`;
    $("#progressBar").style.width =
        slots > 0 ? Math.round((answeredTotal / slots) * 100) + "%" : "0%";

    $("#answeredList").innerHTML =
        answeredTotal === 0
            ? `<span class='muted'>${esc(t("live.noStudents"))}</span>`
            : `<div class="answered-item"><span>${esc(t("live.answeredTotal"))}</span><span class="muted">${answeredTotal}</span></div>`;
}

async function startQuiz() {
    try {
        await api(`/api/quizzes/${state.quizId}/start`, { method: "POST" });
        toast(t("live.startOk"));
        await loadQuizzes();
        state.tab = "live";
        await switchTab("live");
    } catch (err) {
        toast(errMsg(err), true);
        await loadQuizzes();
    }
}

async function finishQuiz() {
    if (!confirm(t("live.finishConfirm"))) return;

    try {
        await api(`/api/quizzes/${state.quizId}/finish`, { method: "POST" });
        toast(t("live.finishOk"));
        await loadQuizzes();
    } catch (err) {
        toast(errMsg(err), true);
        await loadQuizzes();
    }
}

async function cancelLobby() {
    try {
        await api(`/api/quizzes/${state.quizId}/cancel`, { method: "POST" });
        toast(t("live.cancelOk"));
        await loadQuizzes();
        state.tab = "setup";
        await switchTab("setup");
    } catch (err) {
        toast(errMsg(err), true);
        await loadQuizzes();
    }
}

/* ---------------- Tab: RESULTS ---------------- */

async function loadResults() {
    let results, stats;
    try {
        [results, stats] = await Promise.all([
            api(`/api/quizzes/${state.quizId}/results`),
            api(`/api/quizzes/${state.quizId}/statistics`),
        ]);
    } catch (err) {
        toast(errMsg(err), true);
        return;
    }

    $("#overallCards").innerHTML = `
        <div class="stat-card">
            <div class="stat-value">${results.total_students}</div>
            <div class="stat-label">${esc(t("results.registered"))}</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">${stats.answered_students}</div>
            <div class="stat-label">${esc(t("results.answered1"))}</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">${stats.average_score}<span class="stat-label">/10</span></div>
            <div class="stat-label">${esc(t("results.avgScore"))}</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">${stats.overall_accuracy}%</div>
            <div class="stat-label">${esc(t("results.accuracy"))}</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">${stats.total_responses}</div>
            <div class="stat-label">${esc(t("results.responses"))}</div>
        </div>`;

    $("#resultCount").textContent = t("results.students", { n: results.results.length });

    $("#resultsBody").innerHTML =
        results.results.length === 0
            ? `<tr><td colspan='7' class='muted ta-c pad'>${esc(t("results.empty"))}</td></tr>`
            : results.results
                .map((r, i) => `
                    <tr>
                        <td>${i + 1}</td>
                        <td><b>${esc(r.student_id)}</b></td>
                        <td class="ta-c">${r.answered_count} / ${r.total_questions}</td>
                        <td class="ta-c"><span class="chip chip-ok">${r.correct_count}</span></td>
                        <td class="ta-c"><span class="chip chip-bad">${r.wrong_count}</span></td>
                        <td class="ta-c"><b>${r.score}</b>/10</td>
                        <td class="ta-c">${r.accuracy}%</td>
                    </tr>`)
                .join("");
}

/* ---------------- Tab: STATISTICS ---------------- */

async function loadStats() {
    let data;
    try {
        data = await api(`/api/quizzes/${state.quizId}/questions/statistics`);
    } catch (err) {
        toast(errMsg(err), true);
        return;
    }

    $("#statsCards").innerHTML = `
        <div class="stat-card">
            <div class="stat-value">${data.total_questions}</div>
            <div class="stat-label">${esc(t("stats.questions"))}</div>
        </div>`;

    $("#questionStats").innerHTML =
        data.questions.length === 0
            ? `<div class='card'><p class='muted pad'>${esc(t("stats.empty"))}</p></div>`
            : data.questions
                .map((q) => {
                    const total = q.total_answers;
                    const max = Math.max(1, ...Object.values(q.answer_distribution));

                    const rows = ["A", "B", "C", "D"]
                        .map((k) => {
                            const count = q.answer_distribution[k] || 0;
                            const width = Math.round((count / max) * 100);
                            const correct = q.correct_answer === k;
                            return `
                                <div class="dist-row">
                                    <b>${k}</b>
                                    <div class="dist-track">
                                        <div class="dist-fill ${correct ? "correct" : ""}" style="width:${width}%"></div>
                                    </div>
                                    <span class="dist-count">${count}</span>
                                </div>`;
                        })
                        .join("");

                    const accChip =
                        total === 0
                            ? `<span class='chip'>${esc(t("stats.noAnswers"))}</span>`
                            : `<span class="chip ${q.accuracy >= 50 ? "chip-ok" : "chip-warn"}">${esc(t("stats.correctRate", { p: q.accuracy }))}</span>`;

                    return `
                        <div class="card">
                            <div class="qstat-head">
                                <span class="chip">Q${q.question_number}</span>
                                <span class="qstat-q">${esc(q.question_text)}</span>
                                <span class="chip chip-correct">${esc(t("stats.answer", { a: q.correct_answer }))}</span>
                                ${accChip}
                                <span class="chip">${esc(t("stats.answers", { n: total }))}</span>
                            </div>
                            <div style="margin-top:10px">${rows}</div>
                        </div>`;
                })
                .join("");
}

/* ---------------- Gateway status ---------------- */

let gwState = null;

async function refreshGateway() {
    let gw = null;
    try {
        gw = await api("/api/gateway/status");
    } catch { gw = null; }

    gwState = gw;
    renderGateway();
}

function renderGateway() {
    const dot = $("#gwStatus .dot");
    const text = $("#gwText");
    const el = $("#gwStatus");

    if (!gwState || !gwState.online) {
        dot.className = "dot dot-red";
        text.textContent = t("gw.off");
        el.title = t("gw.title");
    } else if (gwState.connected) {
        dot.className = "dot dot-green";
        text.textContent = t("gw.connected");
        el.title =
            t("gw.deviceInfo") + (gwState.device_address || "?") +
            (gwState.quiz_id ? ` — quiz #${gwState.quiz_id}` : "");
    } else {
        dot.className = "dot dot-amber";
        text.textContent = t("gw.waiting");
        el.title = t("gw.title");
    }
}

/* ---------------- Polling ---------------- */

function restartPolling() {
    clearInterval(state.pollTimer);
    clearInterval(state.liveTimer);

    if (state.tab === "live" && state.quizId != null) {
        state.liveTimer = setInterval(refreshLive, 2000);
        return;
    }

    state.pollTimer = setInterval(async () => {
        if (state.quizId == null) return;
        try {
            state.quiz = await api(`/api/quizzes/${state.quizId}`);
            renderBadge();
        } catch { /* transient */ }
    }, 5000);
}

/* ---------------- Init + events ---------------- */

function bindEvents() {
    $("#quizSelect").addEventListener("change", (e) => {
        const id = Number(e.target.value);
        if (id) selectQuiz(id);
    });

    $("#refreshQuizzesBtn").addEventListener("click", () => loadQuizzes());
    $("#createQuizBtn").addEventListener("click", createQuiz);
    $("#newQuizTitle").addEventListener("keydown", (e) => {
        if (e.key === "Enter") createQuiz();
    });

    document.querySelectorAll(".tab").forEach((btn) =>
        btn.addEventListener("click", () => switchTab(btn.dataset.tab))
    );

    const fileInput = $("#csvFile");
    fileInput.addEventListener("change", () => {
        const name = fileInput.files.length ? fileInput.files[0].name : t("setup.noFile");
        $("#csvFileName").textContent = name;
        $("#importBtn").disabled = !fileInput.files.length;
    });

    $("#importBtn").addEventListener("click", importCsv);
    $("#templateBtn").addEventListener("click", downloadTemplate);
    $("#pushBtn").addEventListener("click", pushToDevices);

    const aiFileInput = $("#aiFile");
    aiFileInput.addEventListener("change", () => {
        $("#aiFileName").textContent = aiFileInput.files.length
            ? aiFileInput.files[0].name
            : t("setup.noFile");
        updateAiCard();
    });

    $("#aiGenerateBtn").addEventListener("click", generateAi);
    $("#aiNum").addEventListener("change", updateAiCard);

    $("#startBtn").addEventListener("click", startQuiz);
    $("#finishBtn").addEventListener("click", finishQuiz);
    $("#cancelLobbyBtn").addEventListener("click", cancelLobby);

    $("#langBtn").addEventListener("click", () => {
        lang = lang === "en" ? "vi" : "en";
        localStorage.setItem("pulsenet_lang", lang);
        applyI18n();
        renderGateway();
        setConn($("#connStatus .dot").classList.contains("dot-green"));
        refreshAiStatus();
        if (state.quizId != null) {
            loadQuestions().then(() => {});
        }
    });
}

async function init() {
    applyI18n();
    bindEvents();

    try {
        await api("/health");
        setConn(true);
    } catch { setConn(false); }

    await refreshGateway();
    setInterval(refreshGateway, 2000);

    refreshAiStatus();

    await loadQuizzes();
}

init();
