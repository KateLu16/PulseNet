/* =====================================================
   PulseNet Teacher Dashboard — app.js
   Vanilla JS, no build step. Talks to FastAPI on same
   origin at /api/...
   ===================================================== */

"use strict";

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

const STATUS_VI = {
    draft: "Nháp",
    running: "Đang chạy",
    finished: "Đã kết thúc",
};

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
        throw { status: 0, detail: "Không kết nối được server." };
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
    if (!err) return "Lỗi không xác định.";
    if (typeof err.detail === "string") return err.detail;
    if (err.message) return err.message;
    return "Đã có lỗi xảy ra.";
}

function setConn(ok) {
    const dot = $("#connStatus .dot");
    $("#connText").textContent = ok ? "Đã kết nối server" : "Mất kết nối server";
    dot.className = "dot " + (ok ? "dot-green" : "dot-red");
}

const fmtTime = (iso) => {
    if (!iso) return "—";
    const d = new Date(iso);
    return d.toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
};

/* ---------------- State ---------------- */

const state = {
    quizId: null,
    quiz: null,          // GET /api/quizzes/{id}
    tab: "questions",
    pollTimer: null,
    controlTimer: null,
};

/* =====================================================
   QUIZ BAR
   ===================================================== */

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
            ? "<option value=''>— Chưa có quiz nào —</option>"
            : quizzes
                .map((q) => {
                    const label = `#${q.id} — ${q.title} (${STATUS_VI[q.status] || q.status})`;
                    return `<option value="${q.id}">${esc(label)}</option>`;
                })
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
    renderControlButtons();
    await switchTab(state.tab);
    restartPolling();
}

function renderBadge() {
    const q = state.quiz;
    const badge = $("#quizBadge");
    badge.textContent = STATUS_VI[q.status] || q.status;
    badge.className = "badge badge-" + q.status;
}

async function createQuiz() {
    const title = $("#newQuizTitle").value.trim();
    if (!title) { toast("Nhập tên quiz trước khi tạo.", true); return; }

    try {
        const quiz = await api("/api/quizzes", { method: "POST", body: { title } });
        $("#newQuizTitle").value = "";
        toast(`Đã tạo quiz #${quiz.id} — ${quiz.title}`);
        await loadQuizzes(false);
        state.tab = "questions";
        await switchTab("questions");
    } catch (err) {
        toast(errMsg(err), true);
    }
}

/* =====================================================
   TABS
   ===================================================== */

async function switchTab(tab) {
    state.tab = tab;

    document.querySelectorAll(".tab").forEach((b) =>
        b.classList.toggle("active", b.dataset.tab === tab)
    );

    document.querySelectorAll(".tabpane").forEach((p) =>
        p.classList.add("hidden")
    );

    $(`#tab-${tab}`).classList.remove("hidden");

    if (tab === "questions") await loadQuestions();
    if (tab === "control") await refreshControl();
    if (tab === "results") await loadResults();
    if (tab === "stats") await loadStats();

    restartPolling();
}

/* =====================================================
   TAB: QUESTIONS
   ===================================================== */

async function loadQuestions() {
    let questions;
    try {
        questions = await api(`/api/quizzes/${state.quizId}/questions`);
    } catch (err) {
        toast(errMsg(err), true);
        return;
    }

    $("#questionCount").textContent = `${questions.length} câu`;

    $("#questionsBody").innerHTML =
        questions.length === 0
            ? "<tr><td colspan='7' class='muted ta-c pad'>Chưa có câu hỏi nào. Hãy nhập từ file CSV.</td></tr>"
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

function renderImportResult(result, ok) {
    const box = $("#importResult");
    box.classList.remove("hidden");

    const errors = result.errors_details || [];
    const dups = result.duplicate_details || [];

    let html = "";

    if (ok) {
        html += `<div class="import-box import-ok">
                    <b>✔ Nhập thành công</b> —
                    Đã thêm <b>${result.imported}</b> câu hỏi mới,
                    bỏ qua <b>${result.duplicates}</b> câu trùng lặp.
                 </div>`;
    } else {
        html += `<div class="import-box import-bad">
                    <b>✖ Nhập thất bại</b> —
                    ${result.imported || 0} câu hợp lệ,
                    ${result.duplicates || 0} câu trùng,
                    ${result.errors || errors.length} lỗi.
                    <b>Không có câu hỏi nào được lưu.</b>
                 </div>`;
    }

    if (errors.length) {
        html += `
            <div class="table-wrap"><table class="table">
                <thead><tr>
                    <th class="ta-c">Dòng</th><th>Cột</th><th>Lỗi</th>
                </tr></thead>
                <tbody>
                ${errors.map((e) => `
                    <tr>
                        <td class="ta-c">${e.row}</td>
                        <td>${esc(e.field)}</td>
                        <td>${esc(e.message)}</td>
                    </tr>`).join("")}
                </tbody>
            </table></div>`;
    }

    if (dups.length) {
        html += `
            <div class="table-wrap"><table class="table">
                <thead><tr>
                    <th class="ta-c">Dòng</th><th>Câu trùng lặp</th>
                </tr></thead>
                <tbody>
                ${dups.map((d) => `
                    <tr>
                        <td class="ta-c">${d.row}</td>
                        <td>${esc(d.message)}</td>
                    </tr>`).join("")}
                </tbody>
            </table></div>`;
    }

    box.innerHTML = html;
}

async function importCsv() {
    const input = $("#csvFile");

    if (!input.files.length) { toast("Chọn file CSV trước.", true); return; }

    const fd = new FormData();
    fd.append("file", input.files[0]);

    $("#importBtn").disabled = true;
    $("#importBtn").textContent = "Đang nhập...";

    try {
        // On validation failure FastAPI returns 400 with the
        // full result dict inside "detail" — still render it.
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
        renderControlButtons();
    } catch (err) {
        toast(errMsg(err), true);
    } finally {
        $("#importBtn").disabled = false;
        $("#importBtn").textContent = "⬆ Nhập câu hỏi";
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

/* =====================================================
   TAB: CONTROL
   ===================================================== */

function renderControlButtons() {
    const q = state.quiz;
    if (!q) return;

    $("#startBtn").disabled = q.status !== "draft";
    $("#nextBtn").disabled = q.status !== "running";
    $("#finishBtn").disabled = q.status !== "running";

    const hint = $("#controlHint");

    if (q.status === "draft") {
        hint.textContent =
            "Quiz chưa bắt đầu. Nhập câu hỏi, chờ sinh viên đăng ký trên thiết bị, sau đó nhấn \"Bắt đầu quiz\".";
    } else if (q.status === "running") {
        hint.textContent =
            "Quiz đang chạy. Nhấn \"Câu tiếp theo\" để chuyển câu — gateway sẽ đẩy câu hỏi xuống các thiết bị.";
    } else {
        hint.textContent = "Quiz đã kết thúc. Xem kết quả ở tab \"Kết quả\".";
    }
}

async function quizAction(action, confirmMsg) {
    if (confirmMsg && !confirm(confirmMsg)) return;

    try {
        const res = await api(`/api/quizzes/${state.quizId}/${action}`, { method: "POST" });

        if (action === "next" && !res.has_next) {
            toast("Đã đến câu cuối cùng. Hãy kết thúc quiz.");
        } else if (action === "start") {
            toast("Quiz đã bắt đầu!");
        } else if (action === "finish") {
            toast("Quiz đã kết thúc. Xem kết quả ở tab Kết quả.");
        }

        await loadQuizzes();       // refresh status everywhere
    } catch (err) {
        toast(errMsg(err), true);
        await loadQuizzes();
    }
}

async function refreshControl() {
    if (state.quizId == null) return;

    // Quiz status may have changed elsewhere
    try {
        state.quiz = await api(`/api/quizzes/${state.quizId}`);
        renderBadge();
        renderControlButtons();
    } catch { /* transient */ }

    // Current question + live progress
    let progress = null;
    try {
        progress = await api(`/api/quizzes/${state.quizId}/responses/current`);
    } catch { /* transient */ }

    if (progress && progress.question) {
        $("#currentQNum").textContent = `Câu ${progress.question.question_number}`;

        // Show options without the correct answer (same as API
        // used by the gateway); fetch them from /current.
        let html = `<div class="q-text">${esc(progress.question.question_text)}</div>`;

        try {
            const q = await api(`/api/quizzes/${state.quizId}/current`);
            html += ["a", "b", "c", "d"]
                .map((k) => `<div class="q-option"><b>${k.toUpperCase()}.</b> ${esc(q["option_" + k])}</div>`)
                .join("");
        } catch { /* quiz may have just finished */ }

        $("#currentQuestion").innerHTML = html;
    } else {
        $("#currentQNum").textContent = "—";
        $("#currentQuestion").innerHTML =
            "<p class='muted'>Chưa có câu hỏi nào đang hiển thị.</p>";
    }

    const total = progress ? progress.total_registered : 0;
    const done = progress ? progress.answered_count : 0;

    $("#progressCount").textContent = `${done} / ${total}`;
    $("#progressBar").style.width =
        total > 0 ? Math.round((done / total) * 100) + "%" : "0%";

    $("#answeredList").innerHTML =
        done === 0
            ? "<span class='muted'>Chưa có sinh viên nào trả lời.</span>"
            : progress.answered_students
                .map(
                    (s) => `
                    <div class="answered-item">
                        <span><b>${esc(s.student_id)}</b>${s.name ? " — " + esc(s.name) : ""}</span>
                        <span class="muted">${fmtTime(s.answered_at)}</span>
                    </div>`
                )
                .join("");

    // Registered students table
    let students;
    try {
        students = await api(`/api/quizzes/${state.quizId}/students`);
    } catch { students = null; }

    if (students) {
        $("#studentCount").textContent = `${students.total_students} đã đăng ký`;
        $("#studentsBody").innerHTML =
            students.total_students === 0
                ? "<tr><td colspan='4' class='muted ta-c pad'>Chưa có sinh viên nào đăng ký.</td></tr>"
                : students.students
                    .map((s) => `
                        <tr>
                            <td><b>${esc(s.student_id)}</b></td>
                            <td class="muted">${esc(s.device_mac)}</td>
                            <td class="ta-c">
                                <span class="chip ${s.device_status === "online" ? "chip-ok" : "chip-bad"}">
                                    ${s.device_status === "online" ? "Online" : "Offline"}
                                </span>
                            </td>
                            <td class="ta-c">${s.answered_count} / ${s.total_questions}</td>
                        </tr>`)
                    .join("");
    }
}

/* =====================================================
   TAB: RESULTS
   ===================================================== */

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
            <div class="stat-label">Sinh viên đăng ký</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">${stats.answered_students}</div>
            <div class="stat-label">Đã trả lời ít nhất 1 câu</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">${stats.average_score}<span class="stat-label">/10</span></div>
            <div class="stat-label">Điểm trung bình lớp</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">${stats.overall_accuracy}%</div>
            <div class="stat-label">Độ chính xác tổng</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">${stats.total_responses}</div>
            <div class="stat-label">Tổng lượt trả lời</div>
        </div>`;

    $("#resultCount").textContent = `${results.results.length} sinh viên`;

    $("#resultsBody").innerHTML =
        results.results.length === 0
            ? "<tr><td colspan='7' class='muted ta-c pad'>Chưa có sinh viên nào đăng ký.</td></tr>"
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

/* =====================================================
   TAB: QUESTION STATISTICS
   ===================================================== */

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
            <div class="stat-label">Số câu hỏi</div>
        </div>`;

    $("#questionStats").innerHTML =
        data.questions.length === 0
            ? "<div class='card'><p class='muted pad'>Chưa có câu hỏi nào.</p></div>"
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
                            ? "<span class='chip'>Chưa có trả lời</span>"
                            : `<span class="chip ${q.accuracy >= 50 ? "chip-ok" : "chip-warn"}">${q.accuracy}% đúng</span>`;

                    return `
                        <div class="card">
                            <div class="qstat-head">
                                <span class="chip">Câu ${q.question_number}</span>
                                <span class="qstat-q">${esc(q.question_text)}</span>
                                <span class="chip chip-correct">Đáp án: ${q.correct_answer}</span>
                                ${accChip}
                                <span class="chip">${total} lượt trả lời</span>
                            </div>
                            <div style="margin-top:10px">${rows}</div>
                        </div>`;
                })
                .join("");
}

/* =====================================================
   POLLING
   ===================================================== */

function restartPolling() {
    clearInterval(state.pollTimer);
    clearInterval(state.controlTimer);

    // Control tab needs fast live updates
    if (state.tab === "control" && state.quizId != null) {
        state.controlTimer = setInterval(refreshControl, 2000);
        return;
    }

    // Other tabs: light refresh of quiz status
    state.pollTimer = setInterval(async () => {
        if (state.quizId == null) return;
        try {
            state.quiz = await api(`/api/quizzes/${state.quizId}`);
            renderBadge();
            renderControlButtons();
        } catch { /* transient network issue */ }
    }, 5000);
}

/* =====================================================
   INIT + EVENTS
   ===================================================== */

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
        const name = fileInput.files.length ? fileInput.files[0].name : "Chưa chọn file";
        $("#csvFileName").textContent = name;
        $("#importBtn").disabled = !fileInput.files.length;
    });

    $("#importBtn").addEventListener("click", importCsv);
    $("#templateBtn").addEventListener("click", downloadTemplate);

    $("#startBtn").addEventListener("click", () => quizAction("start"));
    $("#nextBtn").addEventListener("click", () => quizAction("next"));
    $("#finishBtn").addEventListener("click", () =>
        quizAction("finish", "Kết thúc quiz? Sinh viên sẽ không thể trả lời thêm.")
    );
}

async function init() {
    bindEvents();
    try {
        await api("/health");
        setConn(true);
    } catch { setConn(false); }
    await loadQuizzes();
}

init();
