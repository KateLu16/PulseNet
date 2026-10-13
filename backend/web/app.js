/* =====================================================
   PulseNet Teacher Dashboard — app.js
   Pages: Dashboard / Question Bank / Import / Sessions /
          Live Quiz / Devices / Results
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
        "nav.dashboard": "Dashboard",
        "nav.bank": "Question Bank",
        "nav.import": "Import Questions",
        "nav.sessions": "Quiz Sessions",
        "nav.live": "Live Quiz",
        "nav.devices": "Devices",
        "nav.results": "Quiz Results",
        "page.dashboard.t": "Dashboard",
        "page.dashboard.s": "Class overview at a glance",
        "page.bank.t": "Question bank",
        "page.bank.s": "Create and review questions for the selected session",
        "page.import.t": "Import questions",
        "page.import.s": "Add questions from CSV or generate them with AI",
        "page.sessions.t": "Quiz sessions",
        "page.sessions.s": "Create sessions, configure and control them",
        "page.live.t": "Live quiz",
        "page.live.s": "Lobby, quiz clock and live leaderboard",
        "page.devices.t": "Devices",
        "page.devices.s": "Student handhelds and the BLE gateway",
        "page.results.t": "Quiz results",
        "page.results.s": "Scores, students and question analysis",
        "quiz.label": "Session",
        "quiz.refresh": "Reload session list",
        "quiz.newPlaceholder": "New quiz name, e.g. IoT Midterm",
        "quiz.create": "Create",
        "quiz.none": "— No quizzes —",
        "quiz.noneSelected": "No session selected.",
        "quiz.pickHint": "Pick or create a session in “Quiz Sessions” first.",
        "status.draft": "Draft",
        "status.lobby": "Lobby",
        "status.running": "Live",
        "status.finished": "Finished",
        "dash.totalStudents": "Students",
        "dash.activeQuizzes": "Active sessions",
        "dash.finishedQuizzes": "Finished sessions",
        "dash.questions": "Questions",
        "dash.devicesOnline": "Devices online",
        "dash.accuracy": "Answer accuracy",
        "dash.recent": "Recent quiz sessions",
        "dash.new": "+ New session",
        "dash.colQuiz": "Quiz",
        "dash.colStatus": "Status",
        "dash.colStudents": "Students",
        "dash.colStarted": "Started",
        "dash.colFinished": "Finished",
        "dash.colAction": "Action",
        "dash.open": "Open",
        "bank.title": "Question bank",
        "bank.searchPh": "Search questions…",
        "bank.add": "+ Add question",
        "bank.belong": "Questions belong to the session selected in the top bar.",
        "bank.colNo": "No.",
        "bank.colQuestion": "Question",
        "bank.colAnswer": "Answer",
        "bank.noMatch": "No questions match the search.",
        "import.title": "Import from CSV",
        "import.hint": "CSV columns: <code>Question, A, B, C, D, Correct Answer</code>. Drop the file below — it is previewed locally, then the whole file is validated on the server before anything is saved.",
        "import.drop": "Drag & drop the CSV here",
        "import.or": "or",
        "import.preview": "Preview",
        "import.previewHint": "The first rows of the file will show up here once a file is picked.",
        "import.badHeader": "The first line must be exactly: Question, A, B, C, D, Correct Answer",
        "import.validRows": "{ok} valid · {bad} problem rows",
        "import.rowBad": "incomplete",
        "setup.pickFile": "Choose CSV",
        "setup.noFile": "No file selected",
        "setup.noQuestions": "No questions yet.",
        "setup.importBtn": "Import",
        "setup.template": "Download template",
        "setup.templateBtn": "CSV template",
        "setup.importOk": "Imported {imported} new questions, skipped {duplicates} duplicates.",
        "setup.importBad": "Import failed — nothing was saved.",
        "setup.aiTitle": "Generate from document (AI)",
        "setup.aiHint": "Upload a PDF / DOCX / TXT — AI reads the document and writes multiple-choice questions into this quiz. Review every question in the Question Bank before pushing to devices.",
        "setup.aiPickFile": "Choose document",
        "setup.aiNum": "Number of questions",
        "setup.aiLang": "Question language",
        "setup.aiLangAuto": "Same as document",
        "setup.aiLangVi": "Vietnamese",
        "setup.aiLangEn": "English",
        "setup.aiBtn": "Generate with AI",
        "setup.aiWorking": "Generating…",
        "setup.aiOk": "AI generated {n} question(s) from “{file}”. Review them in the Question Bank.",
        "setup.aiBad": "AI generation failed.",
        "setup.aiReady": "AI ready",
        "setup.aiNoKey": "No API key",
        "setup.aiStatusDown": "AI status unavailable",
        "setup.aiKeyHint": "AI is not configured yet — add GEMINI_API_KEY to backend/.env on the Pi, then restart the server.",
        "setup.aiDraftOnly": "Only a draft quiz can receive AI questions.",
        "setup.timeLimit": "Time limit (minutes)",
        "setup.expected": "Students in class",
        "setup.prefix": "Student ID prefix",
        "setup.length": "ID length",
        "setup.pushBtn": "Push to devices",
        "setup.pushHint": "Devices will show the quiz name and wait for students to enter their IDs.",
        "setup.minutes": "{m} min",
        "setup.needQuestions": "Import at least 1 question first.",
        "setup.needTime": "Set the time limit first.",
        "setup.saved": "Settings saved. Pushing to devices…",
        "setup.pushed": "Session pushed! Devices are accepting student IDs.",
        "sess.newTitle": "New session",
        "sess.listTitle": "All sessions",
        "sess.colTime": "Time limit",
        "sess.colExpected": "Expected",
        "sess.setupTitle": "Session setup",
        "sess.saveSettings": "Save settings",
        "sess.saved": "Settings saved.",
        "sess.finishedHint": "This session has finished — open “Quiz Results” for the breakdown.",
        "sess.selected": "Selected",
        "live.draftTitle": "Quiz not pushed yet",
        "live.draftHint": "Configure the session in “Quiz Sessions”, then push it to the devices.",
        "live.goSetup": "Open session setup",
        "live.lobbyTitle": "Lobby",
        "live.joinedHint": "students joined",
        "live.startBtn": "Start quiz",
        "live.cancelBtn": "Cancel",
        "live.lobbyHint": "Devices are accepting student IDs — start whenever everyone is in.",
        "live.timeLeft": "Time left",
        "live.finishBtn": "Finish",
        "live.currentQ": "Live answers",
        "live.progress": "Progress",
        "live.gatewayTitle": "Gateway",
        "live.followTable": "Live leaderboard",
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
        "live.finishedHint": "Open “Quiz Results” for the full breakdown.",
        "live.goResults": "Open results",
        "live.startOk": "Quiz started! Good luck to the class.",
        "live.finishConfirm": "Finish the quiz? Students cannot answer anymore.",
        "live.finishOk": "Quiz finished. See Results for scores.",
        "live.cancelOk": "Lobby cancelled — back to setup.",
        "live.created": "Quiz #{id} — {title} created",
        "live.enterTitle": "Enter a quiz name first.",
        "dev.online": "Devices online",
        "dev.known": "Known devices",
        "dev.gateway": "BLE gateway",
        "dev.title": "Devices",
        "dev.colMac": "Device (MAC)",
        "dev.colCode": "Code",
        "dev.colStatus": "Status",
        "dev.colBattery": "Battery",
        "dev.colSeen": "Last seen",
        "res.tabOverview": "Overview",
        "res.tabStudents": "Student results",
        "res.tabAnalysis": "Question analysis",
        "res.scoreDist": "Score distribution",
        "results.perStudent": "Student results",
        "results.colId": "Student ID",
        "results.colAnswered": "Answered",
        "results.colCorrect": "✓",
        "results.colWrong": "✗",
        "results.colBlank": "Blank",
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
        "stats.mcq": "Multiple choice",
        "stats.donutCorrect": "correct",
        "stats.legendCorrect": "correct",
        "stats.legendWrong": "incorrect",
        "stats.legendBlank": "no answer",
        "stats.correctAnswer": "Correct answer: {a}",
        "modal.title": "Add question",
        "modal.no": "Question number",
        "modal.text": "Question text",
        "modal.correct": "Correct answer",
        "modal.cancel": "Cancel",
        "modal.save": "Save question",
        "modal.needFields": "Fill in the question text and all four options.",
        "modal.created": "Question #{n} added.",
        "modal.preview": "Device preview",
        "modal.previewFit": "Fits on one screen — no scrolling needed.",
        "modal.previewScroll": "~{lines} lines on the device — students scroll with keys 2/8 (~{presses} presses).",
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
        "nav.dashboard": "Bảng điều khiển",
        "nav.bank": "Ngân hàng câu hỏi",
        "nav.import": "Nhập câu hỏi",
        "nav.sessions": "Buổi kiểm tra",
        "nav.live": "Quiz trực tiếp",
        "nav.devices": "Thiết bị",
        "nav.results": "Kết quả",
        "page.dashboard.t": "Bảng điều khiển",
        "page.dashboard.s": "Tổng quan lớp học trong một màn hình",
        "page.bank.t": "Ngân hàng câu hỏi",
        "page.bank.s": "Soạn và xem lại câu hỏi của buổi đang chọn",
        "page.import.t": "Nhập câu hỏi",
        "page.import.s": "Thêm câu hỏi từ CSV hoặc sinh bằng AI",
        "page.sessions.t": "Buổi kiểm tra",
        "page.sessions.s": "Tạo buổi, cấu hình và điều khiển",
        "page.live.t": "Quiz trực tiếp",
        "page.live.s": "Sảnh chờ, đồng hồ và bảng xếp hạng trực tiếp",
        "page.devices.t": "Thiết bị",
        "page.devices.s": "Máy cầm tay sinh viên và gateway BLE",
        "page.results.t": "Kết quả",
        "page.results.s": "Điểm số, sinh viên và phân tích câu hỏi",
        "quiz.label": "Buổi",
        "quiz.refresh": "Tải lại danh sách buổi",
        "quiz.newPlaceholder": "Tên quiz mới, ví dụ: Kiểm tra IoT",
        "quiz.create": "Tạo quiz",
        "quiz.none": "— Chưa có quiz nào —",
        "quiz.noneSelected": "Chưa chọn buổi nào.",
        "quiz.pickHint": "Chọn hoặc tạo một buổi trong “Buổi kiểm tra” trước.",
        "status.draft": "Nháp",
        "status.lobby": "Sảnh chờ",
        "status.running": "Đang chạy",
        "status.finished": "Đã kết thúc",
        "dash.totalStudents": "Sinh viên",
        "dash.activeQuizzes": "Buổi đang chạy",
        "dash.finishedQuizzes": "Buổi đã kết thúc",
        "dash.questions": "Câu hỏi",
        "dash.devicesOnline": "Thiết bị online",
        "dash.accuracy": "Độ chính xác",
        "dash.recent": "Buổi kiểm tra gần đây",
        "dash.new": "+ Tạo buổi mới",
        "dash.colQuiz": "Quiz",
        "dash.colStatus": "Trạng thái",
        "dash.colStudents": "SV",
        "dash.colStarted": "Bắt đầu",
        "dash.colFinished": "Kết thúc",
        "dash.colAction": "Hành động",
        "dash.open": "Mở",
        "bank.title": "Ngân hàng câu hỏi",
        "bank.searchPh": "Tìm câu hỏi…",
        "bank.add": "+ Thêm câu hỏi",
        "bank.belong": "Câu hỏi thuộc về buổi đang chọn ở thanh trên.",
        "bank.colNo": "STT",
        "bank.colQuestion": "Câu hỏi",
        "bank.colAnswer": "Đáp án",
        "bank.noMatch": "Không có câu hỏi nào khớp từ khóa.",
        "import.title": "Nhập từ CSV",
        "import.hint": "Cột CSV: <code>Question, A, B, C, D, Correct Answer</code>. Thả file vào khung bên dưới — xem trước ngay tại máy, cả file được kiểm tra trên server trước khi lưu.",
        "import.drop": "Kéo & thả file CSV vào đây",
        "import.or": "hoặc",
        "import.preview": "Xem trước",
        "import.previewHint": "Các dòng đầu tiên của file sẽ hiện ở đây sau khi chọn file.",
        "import.badHeader": "Dòng đầu tiên phải đúng định dạng: Question, A, B, C, D, Correct Answer",
        "import.validRows": "{ok} dòng hợp lệ · {bad} dòng lỗi",
        "import.rowBad": "thiếu dữ liệu",
        "setup.pickFile": "Chọn file CSV",
        "setup.noFile": "Chưa chọn file",
        "setup.noQuestions": "Chưa có câu hỏi nào.",
        "setup.importBtn": "Nhập câu hỏi",
        "setup.template": "Tải file mẫu",
        "setup.templateBtn": "File mẫu CSV",
        "setup.importOk": "Đã nhập {imported} câu mới, bỏ qua {duplicates} câu trùng.",
        "setup.importBad": "Nhập thất bại — không lưu gì.",
        "setup.aiTitle": "Tạo câu hỏi từ tài liệu (AI)",
        "setup.aiHint": "Tải lên file PDF / DOCX / TXT — AI đọc tài liệu và soạn câu hỏi trắc nghiệm vào quiz này. Hãy xem lại từng câu ở Ngân hàng câu hỏi trước khi gửi xuống thiết bị.",
        "setup.aiPickFile": "Chọn tài liệu",
        "setup.aiNum": "Số câu hỏi",
        "setup.aiLang": "Ngôn ngữ câu hỏi",
        "setup.aiLangAuto": "Theo tài liệu",
        "setup.aiLangVi": "Tiếng Việt",
        "setup.aiLangEn": "Tiếng Anh",
        "setup.aiBtn": "Sinh câu hỏi bằng AI",
        "setup.aiWorking": "Đang sinh câu hỏi…",
        "setup.aiOk": "AI đã sinh {n} câu hỏi từ “{file}”. Xem lại ở Ngân hàng câu hỏi.",
        "setup.aiBad": "Sinh câu hỏi bằng AI thất bại.",
        "setup.aiReady": "AI sẵn sàng",
        "setup.aiNoKey": "Chưa có API key",
        "setup.aiStatusDown": "Không xem được trạng thái AI",
        "setup.aiKeyHint": "AI chưa được cấu hình — thêm GEMINI_API_KEY vào backend/.env trên Pi rồi khởi động lại server.",
        "setup.aiDraftOnly": "Chỉ quiz ở trạng thái Nháp mới nhận được câu hỏi AI.",
        "setup.timeLimit": "Thời gian làm bài (phút)",
        "setup.expected": "Số sinh viên trong lớp",
        "setup.prefix": "Tiền tố MSSV",
        "setup.length": "Độ dài MSSV",
        "setup.pushBtn": "Gửi xuống thiết bị",
        "setup.pushHint": "Thiết bị sẽ hiện tên bài kiểm tra và chờ sinh viên nhập MSSV.",
        "setup.minutes": "{m} phút",
        "setup.needQuestions": "Hãy nhập ít nhất 1 câu hỏi trước.",
        "setup.needTime": "Hãy đặt thời gian làm bài trước.",
        "setup.saved": "Đã lưu cài đặt. Đang gửi xuống thiết bị…",
        "setup.pushed": "Đã gửi phiên! Thiết bị đang nhận MSSV của sinh viên.",
        "sess.newTitle": "Buổi mới",
        "sess.listTitle": "Tất cả các buổi",
        "sess.colTime": "Thời gian",
        "sess.colExpected": "Dự kiến",
        "sess.setupTitle": "Cài đặt buổi",
        "sess.saveSettings": "Lưu cài đặt",
        "sess.saved": "Đã lưu cài đặt.",
        "sess.finishedHint": "Buổi này đã kết thúc — xem “Kết quả” để biết chi tiết.",
        "sess.selected": "Đang chọn",
        "live.draftTitle": "Quiz chưa gửi xuống thiết bị",
        "live.draftHint": "Cấu hình buổi ở “Buổi kiểm tra”, sau đó gửi phiên xuống thiết bị.",
        "live.goSetup": "Mở cài đặt buổi",
        "live.lobbyTitle": "Sảnh chờ",
        "live.joinedHint": "sinh viên đã vào",
        "live.startBtn": "Bắt đầu quiz",
        "live.cancelBtn": "Hủy",
        "live.lobbyHint": "Thiết bị đang nhận MSSV — bắt đầu khi đủ người.",
        "live.timeLeft": "Thời gian còn lại",
        "live.finishBtn": "Kết thúc",
        "live.currentQ": "Phản hồi trực tiếp",
        "live.progress": "Tiến độ",
        "live.gatewayTitle": "Gateway",
        "live.followTable": "Bảng xếp hạng trực tiếp",
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
        "live.finishedHint": "Mở “Kết quả” để xem chi tiết.",
        "live.goResults": "Xem kết quả",
        "live.startOk": "Quiz đã bắt đầu! Chúc lớp làm bài tốt.",
        "live.finishConfirm": "Kết thúc quiz? Sinh viên sẽ không trả lời thêm được.",
        "live.finishOk": "Quiz đã kết thúc. Xem điểm ở tab Kết quả.",
        "live.cancelOk": "Đã hủy sảnh chờ — quay lại bước soạn.",
        "live.created": "Đã tạo quiz #{id} — {title}",
        "live.enterTitle": "Nhập tên quiz trước.",
        "dev.online": "Thiết bị online",
        "dev.known": "Thiết bị đã biết",
        "dev.gateway": "Gateway BLE",
        "dev.title": "Thiết bị",
        "dev.colMac": "Thiết bị (MAC)",
        "dev.colCode": "Mã",
        "dev.colStatus": "Trạng thái",
        "dev.colBattery": "Pin",
        "dev.colSeen": "Nhìn thấy lần cuối",
        "res.tabOverview": "Tổng quan",
        "res.tabStudents": "Kết quả sinh viên",
        "res.tabAnalysis": "Phân tích câu hỏi",
        "res.scoreDist": "Phân bố điểm",
        "results.perStudent": "Kết quả từng sinh viên",
        "results.colId": "MSSV",
        "results.colAnswered": "Đã trả lời",
        "results.colCorrect": "✓",
        "results.colWrong": "✗",
        "results.colBlank": "Bỏ trống",
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
        "stats.mcq": "Trắc nghiệm",
        "stats.donutCorrect": "đúng",
        "stats.legendCorrect": "đúng",
        "stats.legendWrong": "sai",
        "stats.legendBlank": "bỏ trống",
        "stats.correctAnswer": "Đáp án đúng: {a}",
        "modal.title": "Thêm câu hỏi",
        "modal.no": "Số thứ tự câu",
        "modal.text": "Nội dung câu hỏi",
        "modal.correct": "Đáp án đúng",
        "modal.cancel": "Hủy",
        "modal.save": "Lưu câu hỏi",
        "modal.needFields": "Nhập đủ nội dung câu hỏi và cả 4 phương án.",
        "modal.created": "Đã thêm câu #{n}.",
        "modal.preview": "Xem trước trên thiết bị",
        "modal.previewFit": "Vừa trong 1 màn hình — không cần cuộn.",
        "modal.previewScroll": "~{lines} dòng trên thiết bị — học sinh cuộn bằng phím 2/8 (~{presses} lần bấm).",
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

const badgeHtml = (status) =>
    `<span class="badge badge-${esc(status)}">${esc(t(STATUS_KEY[status] || status))}</span>`;

const fmtTime = (iso) => {
    if (!iso) return "—";
    const d = new Date(iso);
    return d.toLocaleTimeString(lang === "vi" ? "vi-VN" : "en-GB", {
        hour: "2-digit", minute: "2-digit", second: "2-digit",
    });
};

const fmtDateTime = (iso) => {
    if (!iso) return "—";
    const d = new Date(iso);
    return d.toLocaleString(lang === "vi" ? "vi-VN" : "en-GB", {
        day: "2-digit", month: "2-digit",
        hour: "2-digit", minute: "2-digit",
    });
};

/* ---------------- State ---------------- */

const state = {
    page: "dashboard",
    quizId: null,
    quiz: null,
    quizzes: [],
    liveQ: null,
    resultsTab: "overview",
    bankQuestions: [],
    pollTimer: null,
    liveTimer: null,
    devTimer: null,
    dashTimer: null,
};

/* ---------------- Session picker (top bar) ---------------- */

async function loadQuizzes(keepSelection = true) {
    let quizzes;
    try {
        quizzes = await api("/api/quizzes");
    } catch (err) {
        toast(errMsg(err), true);
        return;
    }

    state.quizzes = quizzes;

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
        renderCurrentPage();
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

    loadSettingsForm();
    renderCurrentPage();
}

/** Re-render the data of whatever page is open. */
async function renderCurrentPage() {
    switch (state.page) {
        case "bank": return loadBank();
        case "import": return renderImportGate();
        case "sessions": return loadSessions();
        case "live": return refreshLive();
        case "results": return loadResultsAll();
        // dashboard / devices show global data — no quiz needed.
    }
}

async function createQuiz() {
    const title = $("#newQuizTitle").value.trim();
    if (!title) { toast(t("live.enterTitle"), true); return; }

    try {
        const quiz = await api("/api/quizzes", { method: "POST", body: { title } });
        $("#newQuizTitle").value = "";
        toast(t("live.created", { id: quiz.id, title: quiz.title }));
        state.quizId = quiz.id;
        await loadQuizzes(false);
    } catch (err) {
        toast(errMsg(err), true);
    }
}

/* ---------------- Page navigation ---------------- */

const PAGE_META = {
    dashboard: ["page.dashboard.t", "page.dashboard.s"],
    bank: ["page.bank.t", "page.bank.s"],
    import: ["page.import.t", "page.import.s"],
    sessions: ["page.sessions.t", "page.sessions.s"],
    live: ["page.live.t", "page.live.s"],
    devices: ["page.devices.t", "page.devices.s"],
    results: ["page.results.t", "page.results.s"],
};

async function switchPage(page) {
    state.page = page;

    const meta = PAGE_META[page] || PAGE_META.dashboard;
    $("#pageTitle").textContent = t(meta[0]);
    $("#pageSub").textContent = t(meta[1]);

    document.querySelectorAll(".side-nav .tab").forEach((b) =>
        b.classList.toggle("active", b.dataset.page === page)
    );

    document.querySelectorAll(".page").forEach((p) => p.classList.add("hidden"));
    $(`#page-${page}`).classList.remove("hidden");

    if (page === "dashboard") await loadDashboard();
    if (page === "bank") await loadBank();
    if (page === "import") await renderImportGate();
    if (page === "sessions") await loadSessions();
    if (page === "live") await refreshLive();
    if (page === "devices") await loadDevices();
    if (page === "results") await loadResultsAll();

    restartPolling();
}

/* ---------------- Page: DASHBOARD ---------------- */

async function loadDashboard() {
    let data;
    try {
        data = await api("/api/stats/overview");
    } catch (err) {
        toast(errMsg(err), true);
        return;
    }

    $("#dashCards").innerHTML = `
        <div class="stat-card">
            <div class="stat-value">${data.total_students}</div>
            <div class="stat-label">${esc(t("dash.totalStudents"))}</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">${data.active_quizzes}</div>
            <div class="stat-label">${esc(t("dash.activeQuizzes"))}</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">${data.finished_quizzes}</div>
            <div class="stat-label">${esc(t("dash.finishedQuizzes"))}</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">${data.total_questions}</div>
            <div class="stat-label">${esc(t("dash.questions"))}</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">${data.devices_online}<span class="stat-label"> / ${data.devices_total}</span></div>
            <div class="stat-label">${esc(t("dash.devicesOnline"))}</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">${data.overall_accuracy}%</div>
            <div class="stat-label">${esc(t("dash.accuracy"))}</div>
        </div>`;

    $("#dashSessionsBody").innerHTML =
        data.recent_sessions.length === 0
            ? `<tr><td colspan='6' class='muted ta-c pad'>${esc(t("quiz.none"))}</td></tr>`
            : data.recent_sessions
                .map((s) => `
                    <tr>
                        <td><b>#${s.id} — ${esc(s.title)}</b></td>
                        <td class="ta-c">${badgeHtml(s.status)}</td>
                        <td class="ta-c">${s.student_count}</td>
                        <td>${esc(fmtDateTime(s.started_at))}</td>
                        <td>${esc(fmtDateTime(s.finished_at))}</td>
                        <td class="ta-c"><button class="btn btn-ghost btn-sm dash-open" data-id="${s.id}" data-status="${s.status}">${esc(t("dash.open"))}</button></td>
                    </tr>`)
                .join("");

    document.querySelectorAll(".dash-open").forEach((btn) =>
        btn.addEventListener("click", () => openQuiz(Number(btn.dataset.id), btn.dataset.status))
    );
}

/** Jump from a quiz row to the most useful page for its status. */
async function openQuiz(id, status) {
    state.quizId = id;
    try {
        state.quiz = await api(`/api/quizzes/${id}`);
    } catch (err) {
        toast(errMsg(err), true);
        return;
    }

    const sel = $("#quizSelect");
    if (sel) sel.value = String(id);

    loadSettingsForm();

    if (status === "lobby" || status === "running") await switchPage("live");
    else if (status === "finished") await switchPage("results");
    else await switchPage("sessions");
}

/* ---------------- Page: QUESTION BANK ---------------- */

async function loadBank() {
    const noQuiz = $("#bankNoQuiz");
    const panel = $("#bankPanel");

    if (state.quizId == null) {
        noQuiz.classList.remove("hidden");
        panel.classList.add("hidden");
        return;
    }

    noQuiz.classList.add("hidden");
    panel.classList.remove("hidden");

    let questions;
    try {
        questions = await api(`/api/quizzes/${state.quizId}/questions`);
    } catch (err) {
        toast(errMsg(err), true);
        return;
    }

    state.bankQuestions = questions;
    renderBankRows();
}

function renderBankRows() {
    const search = ($("#bankSearch").value || "").trim().toLowerCase();

    const questions = state.bankQuestions.filter((item) => {
        if (!search) return true;
        return [
            item.question_text,
            item.option_a,
            item.option_b,
            item.option_c,
            item.option_d,
            `q${item.question_number}`,
        ].some((v) => String(v || "").toLowerCase().includes(search));
    });

    $("#bankCount").textContent = questions.length;

    $("#bankBody").innerHTML =
        questions.length === 0
            ? `<tr><td colspan='7' class='muted ta-c pad'>${esc(search ? t("bank.noMatch") : t("setup.noQuestions"))}</td></tr>`
            : questions
                .map((item) => `
                    <tr>
                        <td class="ta-c"><b>${item.question_number}</b></td>
                        <td>${esc(item.question_text)}</td>
                        <td>${esc(item.option_a)}</td>
                        <td>${esc(item.option_b)}</td>
                        <td>${esc(item.option_c)}</td>
                        <td>${esc(item.option_d)}</td>
                        <td class="ta-c"><span class="chip chip-correct">${item.correct_answer}</span></td>
                    </tr>`)
                .join("");
}

function openQuestionModal() {
    if (state.quizId == null) return;

    const maxNo = state.bankQuestions.reduce(
        (m, q) => Math.max(m, q.question_number), 0
    );

    $("#modalNo").value = maxNo + 1;
    $("#modalText").value = "";
    $("#modalA").value = "";
    $("#modalB").value = "";
    $("#modalC").value = "";
    $("#modalD").value = "";
    $("#modalCorrect").value = "A";

    $("#questionModal").classList.remove("hidden");
    renderModalPreview();
    $("#modalText").focus();
}

function closeQuestionModal() {
    $("#questionModal").classList.add("hidden");
}

/* ---------------- Device preview (question modal) ---------------- */

// Mirrors the firmware's wrap metrics: the 160px TFT at font
// size 1 fits 25 chars per question line (150px / 6px) and
// 21 chars per option line (130px / 6px, right of the badge).
const DEV_Q_CHARS = 25;
const DEV_O_CHARS = 21;
const DEV_VIEW_ROWS = 9;    // viewport 93px / ~10px per row

/** Greedy word wrap like the firmware: spaces preferred, long
 *  words split at the line boundary, "\n" forces a break. */
function wrapDeviceLines(text, maxChars) {
    const out = [];

    String(text || "").split("\n").forEach((seg) => {
        let line = "";

        seg.trim().split(/\s+/).forEach((word) => {
            while (word.length > maxChars) {
                if (line) { out.push(line); line = ""; }
                out.push(word.slice(0, maxChars));
                word = word.slice(maxChars);
            }
            if (!word) return;
            if (!line) line = word;
            else if (line.length + 1 + word.length <= maxChars) line += ` ${word}`;
            else { out.push(line); line = word; }
        });

        if (line) out.push(line);
    });

    return out;
}

function renderModalPreview() {
    const box = $("#modalPreview");
    const note = $("#modalPreviewNote");
    if (!box || !note) return;

    const text = $("#modalText").value;
    const opts = [
        ["A", $("#modalA").value],
        ["B", $("#modalB").value],
        ["C", $("#modalC").value],
        ["D", $("#modalD").value],
    ];

    const qLines = wrapDeviceLines(text, DEV_Q_CHARS);
    const optLines = opts.map(([, v]) => wrapDeviceLines(v, DEV_O_CHARS));
    const totalRows = qLines.length + 1 +
        optLines.reduce((sum, l) => sum + Math.max(l.length, 1), 0);

    const no = $("#modalNo").value || "?";
    const total = state.quizId == null ? "?" : state.bankQuestions.length + 1;

    let html = `<div class="dv-hdr"><span>Q ${esc(no)}/${esc(total)}</span><span class="dv-clock">05:00</span></div>`;

    qLines.forEach((l) => {
        html += `<div class="dv-q">${esc(l) || "&nbsp;"}</div>`;
    });

    html += `<div class="dv-gap"></div>`;

    optLines.forEach((lines, i) => {
        (lines.length ? lines : [""]).forEach((l, j) => {
            html += `<div class="dv-opt">${
                j === 0
                    ? `<span class="dv-badge">${opts[i][0]}</span>`
                    : `<span class="dv-badge dv-badge-none"></span>`
            }<span>${esc(l) || "&nbsp;"}</span></div>`;
        });
    });

    const scrollable = totalRows > DEV_VIEW_ROWS;

    html += `<div class="dv-foot"><span>2:up 8:down</span><span>${scrollable ? "&#9650; &#9660;" : ""}</span></div>`;

    box.innerHTML = html;

    if (!text && opts.every(([, v]) => !v)) {
        note.textContent = "";
    } else if (!scrollable) {
        note.textContent = t("modal.previewFit");
    } else {
        note.textContent = t("modal.previewScroll", {
            lines: totalRows,
            presses: Math.ceil((totalRows - DEV_VIEW_ROWS) / 2),
        });
    }
}

async function saveQuestionModal() {
    const number = Number($("#modalNo").value);
    const text = $("#modalText").value.trim();
    const a = $("#modalA").value.trim();
    const b = $("#modalB").value.trim();
    const c = $("#modalC").value.trim();
    const d = $("#modalD").value.trim();
    const correct = $("#modalCorrect").value;

    if (!number || number < 1 || !text || !a || !b || !c || !d) {
        toast(t("modal.needFields"), true);
        return;
    }

    try {
        await api(`/api/quizzes/${state.quizId}/questions`, {
            method: "POST",
            body: {
                question_number: number,
                question_text: text,
                option_a: a,
                option_b: b,
                option_c: c,
                option_d: d,
                correct_answer: correct,
            },
        });

        closeQuestionModal();
        toast(t("modal.created", { n: number }));
        await loadBank();
    } catch (err) {
        toast(errMsg(err), true);
    }
}

/* ---------------- Page: IMPORT (CSV + AI) ---------------- */

const EXPECTED_HEADERS = ["Question", "A", "B", "C", "D", "Correct Answer"];

function renderImportGate() {
    const noQuiz = $("#importNoQuiz");
    const panel = $("#importPanel");

    if (state.quizId == null) {
        noQuiz.classList.remove("hidden");
        panel.classList.add("hidden");
        return;
    }

    noQuiz.classList.add("hidden");
    panel.classList.remove("hidden");
    updateAiCard();
}

/** Minimal CSV parser (handles quotes + escaped quotes). */
function parseCsv(text) {
    const rows = [];
    let row = [];
    let field = "";
    let inQuotes = false;

    for (let i = 0; i < text.length; i++) {
        const ch = text[i];

        if (inQuotes) {
            if (ch === '"') {
                if (text[i + 1] === '"') { field += '"'; i++; }
                else inQuotes = false;
            } else {
                field += ch;
            }
        } else if (ch === '"') {
            inQuotes = true;
        } else if (ch === ",") {
            row.push(field);
            field = "";
        } else if (ch === "\n" || ch === "\r") {
            if (ch === "\r" && text[i + 1] === "\n") i++;
            row.push(field);
            field = "";
            if (row.some((x) => x !== "")) rows.push(row);
            row = [];
        } else {
            field += ch;
        }
    }

    row.push(field);
    if (row.some((x) => x !== "")) rows.push(row);

    return rows;
}

function rowIsValid(cells) {
    if (cells.length < 6) return false;
    const [q, a, b, c, d, ans] = cells.slice(0, 6);
    return [q, a, b, c, d].every((v) => v && v.trim() !== "")
        && /^[ABCD]$/.test(ans.trim().toUpperCase());
}

function renderCsvPreview(file) {
    const wrap = $("#previewWrap");
    const count = $("#previewCount");

    const reader = new FileReader();
    reader.onload = () => {
        const rows = parseCsv(String(reader.result || ""));

        if (rows.length === 0) {
            wrap.innerHTML = `<span class='muted'>${esc(t("import.previewHint"))}</span>`;
            count.textContent = "0";
            return;
        }

        const headerOk = rows[0].map((x) => x.trim()).join() === EXPECTED_HEADERS.join();
        const dataRows = rows.slice(1);

        const okCount = dataRows.filter(rowIsValid).length;
        const badCount = dataRows.length - okCount;

        const shown = dataRows.slice(0, 8).map((cells) => {
            const ok = rowIsValid(cells);
            return `
                <tr>
                    <td>${esc((cells[0] || "").slice(0, 60))}</td>
                    <td>${esc((cells[1] || "").slice(0, 24))}</td>
                    <td>${esc((cells[2] || "").slice(0, 24))}</td>
                    <td>${esc((cells[3] || "").slice(0, 24))}</td>
                    <td>${esc((cells[4] || "").slice(0, 24))}</td>
                    <td class="ta-c">${esc((cells[5] || "").slice(0, 4))}</td>
                    <td class="ta-c"><span class="chip ${ok ? "chip-ok" : "chip-bad"}">${ok ? "OK" : esc(t("import.rowBad"))}</span></td>
                </tr>`;
        }).join("");

        count.textContent = dataRows.length;

        wrap.innerHTML = `
            ${headerOk ? "" : `<div class="import-box import-bad">${esc(t("import.badHeader"))}</div>`}
            <div class="muted small" style="margin:8px 0">${esc(t("import.validRows", { ok: okCount, bad: badCount }))}${dataRows.length > 8 ? " · 8/" + dataRows.length : ""}</div>
            <div class="table-wrap"><table class="table">
                <thead><tr><th>Question</th><th>A</th><th>B</th><th>C</th><th>D</th><th class="ta-c">Ans</th><th class="ta-c">OK</th></tr></thead>
                <tbody>${shown}</tbody>
            </table></div>`;
    };

    reader.readAsText(file);
}

function onCsvChosen(file) {
    if (!file) return;

    $("#csvFileName").textContent = file.name;
    $("#importBtn").disabled = false;
    renderCsvPreview(file);
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
        "\"What does IoT stand for?\",Internet of Things,Internet of Telephones,Internal Optical Tool,Input Output Table,A",
        "\"Which device acts as the BLE gateway?\",ESP32,Raspberry Pi 4B,Arduino Uno,CR2032,B",
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

/* ---------------- AI generation ---------------- */

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
    } catch (err) {
        box.classList.remove("hidden");
        box.innerHTML = `<div class="import-box import-bad"><b>✖</b> ${esc(t("setup.aiBad"))} ${esc(err.message || "")}</div>`;
        toast(errMsg(err), true);
    } finally {
        btn.textContent = t("setup.aiBtn");
        updateAiCard();
    }
}

/* ---------------- Page: QUIZ SESSIONS ---------------- */

async function loadSessions() {
    let quizzes;
    try {
        quizzes = await api("/api/quizzes");
    } catch (err) {
        toast(errMsg(err), true);
        return;
    }

    state.quizzes = quizzes;
    $("#sessionCount").textContent = quizzes.length;

    $("#sessionsBody").innerHTML =
        quizzes.length === 0
            ? `<tr><td colspan='7' class='muted ta-c pad'>${esc(t("quiz.none"))}</td></tr>`
            : quizzes
                .map((q) => `
                    <tr>
                        <td><button class="row-link" data-id="${q.id}">#${q.id} — ${esc(q.title)}</button></td>
                        <td class="ta-c">${badgeHtml(q.status)}</td>
                        <td class="ta-c">${q.time_limit_sec ? esc(t("setup.minutes", { m: Math.round(q.time_limit_sec / 60) })) : "—"}</td>
                        <td class="ta-c">${q.expected_students || "—"}</td>
                        <td>${esc(fmtDateTime(q.started_at))}</td>
                        <td>${esc(fmtDateTime(q.finished_at))}</td>
                        <td class="ta-c">${q.id === state.quizId ? `<span class="chip chip-correct">${esc(t("sess.selected"))}</span>` : ""}</td>
                    </tr>`)
                .join("");

    document.querySelectorAll("#sessionsBody .row-link").forEach((btn) =>
        btn.addEventListener("click", () => selectQuiz(Number(btn.dataset.id)))
    );

    renderSetupCard();
}

function loadSettingsForm() {
    const q = state.quiz;
    if (!q) return;

    $("#timeLimitInput").value = q.time_limit_sec ? Math.round(q.time_limit_sec / 60) : "";
    $("#expectedInput").value = q.expected_students || "";
    $("#prefixInput").value = q.id_prefix || "";
    $("#idLengthInput").value = q.id_length || "";
}

function renderSetupCard() {
    const card = $("#sessionSetup");

    if (state.quizId == null || !state.quiz) {
        card.classList.add("hidden");
        return;
    }

    card.classList.remove("hidden");

    $("#setupQuizTitle").textContent = `#${state.quiz.id} — ${state.quiz.title}`;

    const badge = $("#setupBadge");
    badge.textContent = t(STATUS_KEY[state.quiz.status] || state.quiz.status);
    badge.className = "badge badge-" + state.quiz.status;

    const st = state.quiz.status;
    $("#saveSettingsBtn").classList.toggle("hidden", !(st === "draft" || st === "lobby"));
    $("#pushBtn").classList.toggle("hidden", st !== "draft");
    $("#startHereBtn").classList.toggle("hidden", st !== "lobby");
    $("#cancelLobbyBtn").classList.toggle("hidden", st !== "lobby");
    $("#finishHereBtn").classList.toggle("hidden", st !== "running");
}

async function saveSettings() {
    const minutes = Number($("#timeLimitInput").value);

    try {
        state.quiz = await api(`/api/quizzes/${state.quizId}/setup`, {
            method: "POST",
            body: {
                time_limit_sec: minutes ? Math.round(minutes * 60) : null,
                expected_students: Number($("#expectedInput").value) || null,
                id_prefix: $("#prefixInput").value.trim() || null,
                id_length: Number($("#idLengthInput").value) || null,
            },
        });

        toast(t("sess.saved"));
        await loadQuizzes();
    } catch (err) {
        toast(errMsg(err), true);
    }
}

async function pushToDevices() {
    const minutes = Number($("#timeLimitInput").value);

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
                expected_students: Number($("#expectedInput").value) || null,
                id_prefix: $("#prefixInput").value.trim() || null,
                id_length: Number($("#idLengthInput").value) || null,
            },
        });

        toast(t("setup.saved"));

        await api(`/api/quizzes/${state.quizId}/lobby`, { method: "POST" });

        toast(t("setup.pushed"));

        state.quiz = await api(`/api/quizzes/${state.quizId}`);
        loadSettingsForm();
        await loadQuizzes();
        await switchPage("live");
    } catch (err) {
        toast(errMsg(err), true);
    }
}

async function startQuiz() {
    try {
        await api(`/api/quizzes/${state.quizId}/start`, { method: "POST" });
        toast(t("live.startOk"));
        state.liveQ = null;
        await loadQuizzes();
        await switchPage("live");
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
        renderCurrentPage();
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
        renderCurrentPage();
    } catch (err) {
        toast(errMsg(err), true);
        await loadQuizzes();
    }
}

/* ---------------- Page: LIVE QUIZ ---------------- */

// Polling guard: refreshLive fires every 2s; if a pass is
// still awaiting the API (slow Wi-Fi / busy Pi), the next
// tick must NOT stack on top of it — late responses would
// clobber newer state and chip clicks would feel dead.
let liveRefreshBusy = false;

async function refreshLive() {
    if (liveRefreshBusy) return;
    liveRefreshBusy = true;

    try {
        await refreshLiveInner();
    } finally {
        liveRefreshBusy = false;
    }
}

async function refreshLiveInner() {
    const noQuiz = $("#liveNoQuiz");
    const panel = $("#livePanel");

    if (state.quizId == null) {
        noQuiz.classList.remove("hidden");
        panel.classList.add("hidden");
        return;
    }

    noQuiz.classList.add("hidden");
    panel.classList.remove("hidden");

    try {
        state.quiz = await api(`/api/quizzes/${state.quizId}`);
    } catch { /* transient */ }

    const st = state.quiz ? state.quiz.status : "draft";

    $("#liveDraft").classList.toggle("hidden", st !== "draft");
    $("#liveLobby").classList.toggle("hidden", st !== "lobby");
    $("#liveRun").classList.toggle("hidden", st !== "running" && st !== "finished");
    $("#liveFinished").classList.toggle("hidden", st !== "finished");
    $("#liveQuestionCard").classList.toggle("hidden", st === "finished");

    if (st === "draft") return;

    let students = null;
    try {
        students = await api(`/api/quizzes/${state.quizId}/students`);
    } catch { students = null; }

    if (st === "lobby") {
        const expected = state.quiz.expected_students || (students ? students.total_students : 0);
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
    renderLiveGateway();

    // Live question card (answer distribution)
    let qStats = null;
    try {
        qStats = await api(`/api/quizzes/${state.quizId}/questions/statistics`);
    } catch { qStats = null; }

    if (qStats && qStats.questions.length > 0 && st !== "finished") {
        const totalStudents = students ? students.total_students : 0;

        // Default to the most recently answered question.
        const maxAnswered = students
            ? students.students.reduce(
                (m, s) => Math.max(m, s.last_answered_question || 0), 0)
            : 0;

        const valid = qStats.questions.some((x) => x.question_number === state.liveQ);
        if (!valid) {
            // SELF-PACED: follow the class frontier (the most
            // recently answered question), else Q1.
            state.liveQ = maxAnswered
                || qStats.questions[0].question_number;
        }

        renderLiveQuestion(qStats, totalStudents);
    } else {
        $("#qChips").innerHTML = "";
        $("#liveQText").textContent = "—";
        $("#liveQOptions").innerHTML = "";
        $("#liveAnsweredChip").textContent = "0 / 0";
    }

    // Leaderboard
    let answeredTotal = 0;
    let slots = 0;

    if (students) {
        $("#studentCount").textContent = students.total_students;

        const ranked = [...students.students].sort(
            (a, b) => b.score - a.score || b.correct_count - a.correct_count
        );

        $("#studentsBody").innerHTML =
            students.total_students === 0
                ? `<tr><td colspan='8' class='muted ta-c pad'>${esc(t("live.noStudents"))}</td></tr>`
                : ranked
                    .map((s, i) => {
                        const tq = s.total_questions || 0;
                        const done = tq > 0 && s.answered_count >= tq;
                        const nowOn = done ? t("live.done") : `Q${(s.last_answered_question || 0) + 1}`;

                        answeredTotal += s.answered_count;
                        slots += tq;

                        return `
                            <tr>
                                <td class="ta-c"><b>${i + 1}</b></td>
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

function renderLiveQuestion(qStats, totalStudents) {
    const chips = $("#qChips");

    chips.innerHTML = qStats.questions
        .map((x) =>
            `<button class="qchip ${x.question_number === state.liveQ ? "active" : ""}" data-q="${x.question_number}">Q${x.question_number}</button>`
        )
        .join("");

    chips.querySelectorAll(".qchip").forEach((btn) =>
        btn.addEventListener("click", () => {
            state.liveQ = Number(btn.dataset.q);
            refreshLive();
        })
    );

    const q = qStats.questions.find(
        (x) => x.question_number === state.liveQ
    );

    if (!q) return;

    $("#liveAnsweredChip").textContent = `${q.total_answers} / ${totalStudents}`;
    $("#liveQText").textContent = `Q${q.question_number}. ${q.question_text}`;

    const max = Math.max(1, ...Object.values(q.answer_distribution));

    const options = [
        ["A", q.correct_answer === "A"],
        ["B", q.correct_answer === "B"],
        ["C", q.correct_answer === "C"],
        ["D", q.correct_answer === "D"],
    ];

    $("#liveQOptions").innerHTML = options
        .map(([letter, correct]) => {
            const count = q.answer_distribution[letter] || 0;
            const width = Math.round((count / max) * 100);

            return `
                <div class="live-option ${correct ? "correct" : ""}">
                    <span class="live-opt-letter">${letter}</span>
                    <div class="live-opt-track">
                        <div class="live-opt-fill" style="width:${width}%"></div>
                    </div>
                    <span class="live-opt-count">${count}</span>
                </div>`;
        })
        .join("");
}

/** Connected BLE device addresses reported by the gateway. */
function gwConnectedAddresses(gw) {
    const devices = (gw && gw.devices) || [];
    return devices.filter((d) => d.connected).map((d) => d.address);
}

function renderLiveGateway() {
    const gw = gwState;

    if (gw && gw.online && gw.connected) {
        $("#gwChip").textContent = t("gw.connected");
        $("#gwChip").className = "chip chip-ok";

        const addrs = gwConnectedAddresses(gw);
        const addrText = addrs.length ? addrs.join(", ") : (gw.device_address || "?");

        $("#gwInfo").innerHTML =
            esc(t("gw.deviceInfo") + addrText) +
            "<br>" +
            (gw.last_pushed_question != null
                ? esc(t("gw.pushed") + gw.last_pushed_question)
                : esc(t("gw.none")));
    } else {
        $("#gwChip").textContent = gw && gw.online ? t("gw.waiting") : t("gw.off");
        $("#gwChip").className = "chip " + (gw && gw.online ? "chip-warn" : "chip-bad");
        $("#gwInfo").textContent = "—";
    }
}

/* ---------------- Page: DEVICES ---------------- */

let devicesBusy = false;

async function loadDevices() {
    if (devicesBusy) return;
    devicesBusy = true;

    try {
        await loadDevicesInner();
    } finally {
        devicesBusy = false;
    }
}

async function loadDevicesInner() {
    let data;
    try {
        data = await api("/api/devices");
    } catch (err) {
        toast(errMsg(err), true);
        return;
    }

    const devices = data.devices || [];
    const online = devices.filter((d) => d.status === "online").length;

    $("#devOnline").innerHTML = `${online}<span class="stat-label"> / ${devices.length}</span>`;
    $("#devTotal").textContent = devices.length;
    $("#deviceCount").textContent = devices.length;

    renderDevicesGateway();

    $("#devicesBody").innerHTML =
        devices.length === 0
            ? `<tr><td colspan='5' class='muted ta-c pad'>${esc(t("quiz.none"))}</td></tr>`
            : devices
                .map((d) => `
                    <tr>
                        <td><b>${esc(d.device_mac)}</b></td>
                        <td class="muted">${esc(d.device_code || "—")}</td>
                        <td class="ta-c"><span class="chip ${d.status === "online" ? "chip-ok" : ""}">${esc(d.status || "—")}</span></td>
                        <td class="ta-c">${d.battery != null ? `${d.battery}%` : "—"}</td>
                        <td>${esc(fmtDateTime(d.last_seen))}</td>
                    </tr>`)
                .join("");
}

function renderDevicesGateway() {
    const el = $("#devGw");
    const gw = gwState;

    if (gw && gw.online && gw.connected) {
        el.innerHTML = `<span style="color:var(--green)">●</span>`;

        const addrs = gwConnectedAddresses(gw);
        el.title =
            t("gw.deviceInfo") +
            (addrs.length ? addrs.join(", ") : (gw.device_address || "?"));
    } else if (gw && gw.online) {
        el.innerHTML = `<span style="color:var(--amber)">●</span>`;
        el.title = t("gw.waiting");
    } else {
        el.innerHTML = `<span style="color:var(--red)">●</span>`;
        el.title = t("gw.off");
    }
}

/* ---------------- Page: RESULTS ---------------- */

function switchResultsTab(tab) {
    state.resultsTab = tab;

    document.querySelectorAll(".subtab").forEach((b) =>
        b.classList.toggle("active", b.dataset.rtab === tab)
    );

    $("#rtab-overview").classList.toggle("hidden", tab !== "overview");
    $("#rtab-students").classList.toggle("hidden", tab !== "students");
    $("#rtab-analysis").classList.toggle("hidden", tab !== "analysis");
}

async function loadResultsAll() {
    const noQuiz = $("#resultsNoQuiz");
    const panel = $("#resultsPanel");

    if (state.quizId == null) {
        noQuiz.classList.remove("hidden");
        panel.classList.add("hidden");
        return;
    }

    noQuiz.classList.add("hidden");
    panel.classList.remove("hidden");

    await Promise.all([loadResults(), loadStats()]);
}

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

    // Score distribution buckets 0–2, 2–4 … 8–10
    const buckets = [
        ["0–2", 0, 2],
        ["2–4", 2, 4],
        ["4–6", 4, 6],
        ["6–8", 6, 8],
        ["8–10", 8, 10.01],
    ];

    const scores = results.results.map((r) => r.score);
    const counts = buckets.map(([, lo, hi]) =>
        scores.filter((s) => s >= lo && s < hi).length
    );
    const maxCount = Math.max(1, ...counts);

    $("#distCount").textContent = scores.length;

    $("#scoreDist").innerHTML = buckets
        .map(([label], i) => `
            <div class="score-row">
                <b>${label}</b>
                <div class="score-track">
                    <div class="score-fill" style="width:${Math.round((counts[i] / maxCount) * 100)}%"></div>
                </div>
                <span class="score-count">${counts[i]}</span>
            </div>`)
        .join("");

    $("#resultCount").textContent = t("results.students", { n: results.results.length });

    $("#resultsBody").innerHTML =
        results.results.length === 0
            ? `<tr><td colspan='8' class='muted ta-c pad'>${esc(t("results.empty"))}</td></tr>`
            : results.results
                .map((r, i) => `
                    <tr>
                        <td>${i + 1}</td>
                        <td><b>${esc(r.student_id)}</b></td>
                        <td class="ta-c">${r.answered_count} / ${r.total_questions}</td>
                        <td class="ta-c"><span class="chip chip-ok">${r.correct_count}</span></td>
                        <td class="ta-c"><span class="chip chip-bad">${r.wrong_count}</span></td>
                        <td class="ta-c"><span class="chip">${r.blank_count ?? Math.max(r.total_questions - r.answered_count, 0)}</span></td>
                        <td class="ta-c"><b>${r.score}</b>/10</td>
                        <td class="ta-c">${r.accuracy}%</td>
                    </tr>`)
                .join("");
}

async function loadStats() {
    const [data, resultsData] = await Promise.all([
        api(`/api/quizzes/${state.quizId}/questions/statistics`),
        api(`/api/quizzes/${state.quizId}/results`).catch(() => null),
    ]).catch((err) => {
        toast(errMsg(err), true);
        return [null, null];
    });

    if (!data) return;

    const studentCount = resultsData ? resultsData.results.length : 0;

    $("#questionStats").innerHTML =
        data.questions.length === 0
            ? `<div class='card'><p class='muted pad'>${esc(t("stats.empty"))}</p></div>`
            : data.questions
                .map((q) => {
                    const total = q.total_answers;
                    const noAnswer = Math.max(studentCount - total, 0);
                    const acc = total > 0 ? Math.round(q.accuracy) : 0;

                    // Donut: green = correct, red = wrong (among answers)
                    const R = 40, CIRC = 2 * Math.PI * R;
                    const okLen = total > 0 ? (q.correct_count / total) * CIRC : 0;
                    const noLen = total > 0 ? (q.wrong_count / total) * CIRC : 0;

                    const donut = `
                        <div class="qstat-donut">
                            <svg width="96" height="96" viewBox="0 0 96 96">
                                <circle cx="48" cy="48" r="${R}" fill="none" stroke="#E5E7EB" stroke-width="10"/>
                                <circle cx="48" cy="48" r="${R}" fill="none" stroke="#22C55E" stroke-width="10"
                                        stroke-dasharray="${okLen} ${CIRC}" stroke-dashoffset="0"/>
                                <circle cx="48" cy="48" r="${R}" fill="none" stroke="#EF4444" stroke-width="10"
                                        stroke-dasharray="${noLen} ${CIRC}" stroke-dashoffset="${-okLen}"/>
                            </svg>
                            <div class="qstat-donut-center">
                                <span class="qstat-donut-pct">${acc}%</span>
                                <span class="qstat-donut-sub">${esc(total > 0 ? t("stats.donutCorrect") : t("stats.noAnswers"))}</span>
                            </div>
                        </div>`;

                    const legend = `
                        <div class="qstat-legend">
                            <div class="qstat-legend-row"><span class="qstat-dot ok"></span><b>${q.correct_count}</b> ${esc(t("stats.legendCorrect"))}</div>
                            <div class="qstat-legend-row"><span class="qstat-dot no"></span><b>${q.wrong_count}</b> ${esc(t("stats.legendWrong"))}</div>
                            <div class="qstat-legend-row"><span class="qstat-dot skip"></span><b>${noAnswer}</b> ${esc(t("stats.legendBlank"))}</div>
                        </div>`;

                    const rows = Object.keys(q.answer_distribution)
                        .map((k) => {
                            const count = q.answer_distribution[k] || 0;
                            const pct = total > 0 ? Math.round((count / total) * 100) : 0;
                            const isCorrect = q.correct_answer === k;
                            const picked = count > 0;
                            const letterCls = isCorrect ? " correct" : picked ? " wrong" : "";
                            const fillCls = isCorrect ? " correct" : "";
                            return `
                                <div class="qopt">
                                    <span class="qopt-letter${letterCls}">${k}</span>
                                    <div class="qopt-track">
                                        <div class="qopt-fill${fillCls}" style="width:${pct}%"></div>
                                    </div>
                                    <span class="qopt-pct">${pct}% (${count})</span>
                                </div>`;
                        })
                        .join("");

                    return `
                        <div class="card qstat-card">
                            <div class="qstat-left">
                                <span class="qstat-badge${total > 0 && acc < 50 ? " bad" : ""}">Q${q.question_number}</span>
                                <div class="qstat-left-main">
                                    <div class="qstat-q">${esc(q.question_text)}</div>
                                    <span class="qstat-type">${esc(t("stats.mcq"))}</span>
                                </div>
                            </div>
                            <div class="qstat-mid">${donut}${legend}</div>
                            <div class="qstat-right">
                                ${rows}
                                <div class="qstat-foot">
                                    <span class="check">✓</span>
                                    ${esc(t("stats.correctAnswer", { a: q.correct_answer }))} · ${esc(t("stats.answers", { n: total }))}
                                </div>
                            </div>
                        </div>`;
                })
                .join("");
}

/* ---------------- Gateway status (sidebar + pages) ---------------- */

let gwState = null;

async function refreshGateway() {
    let gw = null;
    try {
        gw = await api("/api/gateway/status");
    } catch { gw = null; }

    gwState = gw;
    renderGateway();

    if (state.page === "live") renderLiveGateway();
    if (state.page === "devices") renderDevicesGateway();
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

        const addrs = gwConnectedAddresses(gwState);
        el.title =
            t("gw.deviceInfo") +
            (addrs.length ? addrs.join(", ") : (gwState.device_address || "?")) +
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
    clearInterval(state.devTimer);
    clearInterval(state.dashTimer);

    if (state.page === "live") {
        state.liveTimer = setInterval(refreshLive, 2000);
    } else if (state.page === "devices") {
        state.devTimer = setInterval(loadDevices, 3000);
    } else if (state.page === "dashboard") {
        state.dashTimer = setInterval(loadDashboard, 10000);
    } else {
        state.pollTimer = setInterval(async () => {
            if (state.quizId == null) return;
            try {
                state.quiz = await api(`/api/quizzes/${state.quizId}`);
                if (state.page === "sessions") renderSetupCard();
            } catch { /* transient */ }
        }, 5000);
    }
}

/* ---------------- Init + events ---------------- */

function bindEvents() {
    $("#quizSelect").addEventListener("change", (e) => {
        const id = Number(e.target.value);
        if (id) selectQuiz(id);
    });

    $("#refreshQuizzesBtn").addEventListener("click", () => loadQuizzes());
    $("#langBtn").addEventListener("click", () => {
        lang = lang === "en" ? "vi" : "en";
        localStorage.setItem("pulsenet_lang", lang);
        applyI18n();
        renderGateway();
        setConn($("#connStatus .dot").classList.contains("dot-green"));
        refreshAiStatus();
        switchPage(state.page);
    });

    document.querySelectorAll(".side-nav .tab").forEach((btn) =>
        btn.addEventListener("click", () => switchPage(btn.dataset.page))
    );

    // Dashboard
    $("#dashNewBtn").addEventListener("click", async () => {
        await switchPage("sessions");
        $("#newQuizTitle").focus();
    });

    // Question bank
    $("#bankSearch").addEventListener("input", renderBankRows);
    $("#addQuestionBtn").addEventListener("click", openQuestionModal);
    $("#modalClose").addEventListener("click", closeQuestionModal);
    $("#modalCancel").addEventListener("click", closeQuestionModal);
    $("#modalSave").addEventListener("click", saveQuestionModal);

    // Live device preview while typing the question
    ["modalNo", "modalText", "modalA", "modalB", "modalC", "modalD"].forEach((id) => {
        const el = document.getElementById(id);
        if (el) el.addEventListener("input", renderModalPreview);
    });

    // Import — dropzone + file input
    const dropzone = $("#dropzone");
    const csvInput = $("#csvFile");

    dropzone.addEventListener("click", (e) => {
        if (e.target.tagName !== "INPUT") csvInput.click();
    });

    ["dragover", "dragenter"].forEach((ev) =>
        dropzone.addEventListener(ev, (e) => {
            e.preventDefault();
            dropzone.classList.add("drag");
        })
    );

    ["dragleave", "drop"].forEach((ev) =>
        dropzone.addEventListener(ev, (e) => {
            e.preventDefault();
            dropzone.classList.remove("drag");
        })
    );

    dropzone.addEventListener("drop", (e) => {
        const file = e.dataTransfer.files && e.dataTransfer.files[0];
        if (!file) return;

        if (!file.name.toLowerCase().endsWith(".csv")) {
            toast(t("import.badHeader"), true);
            return;
        }

        csvInput.files = e.dataTransfer.files;
        onCsvChosen(file);
    });

    csvInput.addEventListener("change", () => {
        if (csvInput.files.length) onCsvChosen(csvInput.files[0]);
    });

    $("#importBtn").addEventListener("click", importCsv);
    $("#templateBtn").addEventListener("click", downloadTemplate);

    // Import — AI
    const aiFileInput = $("#aiFile");
    aiFileInput.addEventListener("change", () => {
        $("#aiFileName").textContent = aiFileInput.files.length
            ? aiFileInput.files[0].name
            : t("setup.noFile");
        updateAiCard();
    });

    $("#aiGenerateBtn").addEventListener("click", generateAi);
    $("#aiNum").addEventListener("change", updateAiCard);

    // Sessions
    $("#createQuizBtn").addEventListener("click", createQuiz);
    $("#newQuizTitle").addEventListener("keydown", (e) => {
        if (e.key === "Enter") createQuiz();
    });
    $("#saveSettingsBtn").addEventListener("click", saveSettings);
    $("#pushBtn").addEventListener("click", pushToDevices);
    $("#startHereBtn").addEventListener("click", startQuiz);
    $("#cancelLobbyBtn").addEventListener("click", cancelLobby);
    $("#finishHereBtn").addEventListener("click", finishQuiz);

    // Live
    $("#startBtn").addEventListener("click", startQuiz);
    $("#finishBtn").addEventListener("click", finishQuiz);
    $("#cancelLobbySideBtn").addEventListener("click", cancelLobby);
    $("#goSetupBtn").addEventListener("click", () => switchPage("sessions"));
    $("#goResultsBtn").addEventListener("click", () => switchPage("results"));

    // Results sub-tabs
    document.querySelectorAll(".subtab").forEach((btn) =>
        btn.addEventListener("click", () => switchResultsTab(btn.dataset.rtab))
    );
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

    await switchPage("dashboard");
    await loadQuizzes();
}

init();
