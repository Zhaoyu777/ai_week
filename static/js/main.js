let tinymceEditor;
let reportTinymceEditor;
let calendar;
let allTags = [];
let tagModal;
let ocrModal;
let ocrFile = null;

tinymce.init({
    selector: '#recordContent',
    base_url: '/static/vendor/tinymce',
    suffix: '.min',
    height: 200,
    menubar: false,
    plugins: 'lists link image charmap preview',
    toolbar: 'undo redo | formatselect | bold italic backcolor | alignleft aligncenter | alignright alignjustify | bullist numlist outdent indent | removeformat',
    skin: 'oxide',
    content_css: 'default',
    setup(editor) {
        tinymceEditor = editor;
        editor.on('init', () => applyThemeToEditor(editor, localStorage.getItem('theme') || 'light'));
    }
});

tinymce.init({
    selector: '#reportContent',
    base_url: '/static/vendor/tinymce',
    suffix: '.min',
    height: 500,
    menubar: false,
    plugins: 'lists link image charmap preview',
    toolbar: 'undo redo | formatselect | bold italic backcolor | alignleft aligncenter | alignright alignjustify | bullist numlist outdent indent | removeformat',
    skin: 'oxide',
    content_css: 'default',
    setup(editor) {
        reportTinymceEditor = editor;
        editor.on('init', () => applyThemeToEditor(editor, localStorage.getItem('theme') || 'light'));
    }
});

document.addEventListener('DOMContentLoaded', () => {
    setTheme(localStorage.getItem('theme') || 'light');

    tagModal = new bootstrap.Modal(document.getElementById('tagModal'));
    ocrModal = new bootstrap.Modal(document.getElementById('ocrModal'));

    bindOcrEvents();
    bindPageEvents();

    loadTags();
    initCalendar();
    initDefaultDates();
    loadAiConfig();

    const today = formatDate(new Date());
    setSelectedDate(today);
    resetForm(today);
    loadRecords(today);
});

function bindPageEvents() {
    const keywordInput = document.getElementById('filterKeyword');
    keywordInput.addEventListener('keydown', (event) => {
        if (event.key === 'Enter') {
            event.preventDefault();
            loadRecords();
        }
    });
}

function bindOcrEvents() {
    const dropzone = document.getElementById('ocrDropzone');
    const fileInput = document.getElementById('ocrFileInput');

    dropzone.addEventListener('click', () => fileInput.click());
    dropzone.addEventListener('dragover', (event) => {
        event.preventDefault();
        dropzone.classList.add('dragover');
    });
    dropzone.addEventListener('dragleave', () => dropzone.classList.remove('dragover'));
    dropzone.addEventListener('drop', (event) => {
        event.preventDefault();
        dropzone.classList.remove('dragover');
        if (event.dataTransfer.files.length > 0) {
            handleOcrFile(event.dataTransfer.files[0]);
        }
    });

    document.addEventListener('paste', (event) => {
        if (!document.getElementById('ocrModal').classList.contains('show')) {
            return;
        }

        for (const item of event.clipboardData?.items || []) {
            if (item.type.startsWith('image/')) {
                const file = item.getAsFile();
                if (file) {
                    handleOcrFile(file);
                }
                break;
            }
        }
    });
}

function initDefaultDates() {
    const now = new Date();
    const lastWeek = new Date(now.getFullYear(), now.getMonth(), now.getDate() - 7);
    document.getElementById('reportEndDate').value = formatDate(now);
    document.getElementById('reportStartDate').value = formatDate(lastWeek);
}

function initCalendar() {
    const calendarEl = document.getElementById('calendar');
    calendar = new FullCalendar.Calendar(calendarEl, {
        initialView: 'dayGridMonth',
        locale: 'zh-cn',
        dayCellContent(arg) {
            return { html: arg.dayNumberText.replace('日', '') };
        },
        headerToolbar: {
            left: 'prev,next',
            center: 'title',
            right: 'today'
        },
        selectable: true,
        height: 'auto',
        contentHeight: 'auto',
        dayMaxEvents: false,
        dateClick(info) {
            handleDateClick(info.dateStr);
        },
        events: '/api/record-counts',
        eventContent(arg) {
            return {
                html: `<div class="text-center mt-1"><span class="badge bg-success rounded-pill calendar-count-badge">${escapeHtml(arg.event.title)}条</span></div>`
            };
        }
    });
    calendar.render();
}

function handleDateClick(dateStr) {
    setSelectedDate(dateStr);
    resetForm(dateStr);
    loadRecords(dateStr);
}

function setSelectedDate(dateStr) {
    document.getElementById('recordDate').value = dateStr;
    document.getElementById('formTitle').innerText = dateStr;
    document.getElementById('listTitle').innerText = `${dateStr} 记录`;
}

function openOcrModal() {
    clearOcrImage();
    document.getElementById('ocrResultContainer').classList.add('d-none');
    document.getElementById('ocrResultText').value = '';
    updateOcrBtnState('disabled');
    ocrModal.show();
}

function handleFileSelect(input) {
    if (input.files.length > 0) {
        handleOcrFile(input.files[0]);
    }
}

function handleOcrFile(file) {
    if (!file || !file.type.startsWith('image/')) {
        alert('请上传图片文件');
        return;
    }

    ocrFile = file;
    const reader = new FileReader();
    reader.onload = (event) => {
        document.getElementById('ocrDropContent').classList.add('d-none');
        document.getElementById('ocrPreviewContainer').classList.remove('d-none');
        document.getElementById('ocrPreviewImage').src = event.target.result;
        startOcrProcess();
    };
    reader.readAsDataURL(file);
}

function clearOcrImage() {
    ocrFile = null;
    document.getElementById('ocrFileInput').value = '';
    document.getElementById('ocrDropContent').classList.remove('d-none');
    document.getElementById('ocrPreviewContainer').classList.add('d-none');
    document.getElementById('ocrPreviewImage').src = '';
    updateOcrBtnState('disabled');
}

function updateOcrBtnState(state) {
    const btn = document.getElementById('btnOcrConfirm');
    const spinner = document.getElementById('ocrModalSpinner');
    const text = document.getElementById('btnOcrText');

    if (state === 'disabled') {
        btn.disabled = true;
        btn.onclick = confirmOcrResult;
        text.innerText = '开始识别';
        spinner.classList.add('d-none');
        return;
    }

    if (state === 'ready') {
        btn.disabled = false;
        btn.onclick = startOcrProcess;
        text.innerText = '开始识别';
        spinner.classList.add('d-none');
        return;
    }

    if (state === 'processing') {
        btn.disabled = true;
        btn.onclick = null;
        text.innerText = '识别中...';
        spinner.classList.remove('d-none');
        return;
    }

    btn.disabled = false;
    btn.onclick = confirmOcrResult;
    text.innerText = '确认填入';
    spinner.classList.add('d-none');
}

function startOcrProcess() {
    if (!ocrFile) {
        return;
    }

    updateOcrBtnState('processing');
    const formData = new FormData();
    formData.append('image', ocrFile);

    fetch('/api/ocr', {
        method: 'POST',
        body: formData
    })
        .then(ensureJsonResponse)
        .then((data) => {
            if (data.error) {
                throw new Error(data.error);
            }

            document.getElementById('ocrResultContainer').classList.remove('d-none');
            document.getElementById('ocrResultText').value = data.text || '';
            updateOcrBtnState('confirm');
        })
        .catch((error) => {
            alert(`图片识别失败：${error.message}`);
            updateOcrBtnState('ready');
        });
}

function confirmOcrResult() {
    const text = document.getElementById('ocrResultText').value.trim();
    if (!text || !tinymceEditor) {
        return;
    }

    const currentContent = tinymceEditor.getContent();
    const nextContent = `${currentContent}${currentContent ? '<br><br>' : ''}${text.replace(/\n/g, '<br>')}`;
    tinymceEditor.setContent(nextContent);
    ocrModal.hide();
}

function loadTags() {
    fetch('/api/tags')
        .then(ensureJsonResponse)
        .then((tags) => {
            allTags = Array.isArray(tags) ? tags : [];
            renderTagsInForm();
        })
        .catch((error) => alert(`加载标签失败：${error.message}`));
}

function renderTagsInForm() {
    const container = document.getElementById('tagContainer');
    container.innerHTML = '';

    allTags.forEach((tag) => {
        const id = `tag_${tag.id}`;
        container.insertAdjacentHTML('beforeend', `
            <input type="checkbox" class="btn-check" id="${id}" value="${escapeHtml(tag.name)}" autocomplete="off">
            <label class="btn btn-outline-${escapeHtml(tag.color)} btn-sm rounded-pill" for="${id}">${escapeHtml(tag.name)}</label>
        `);
    });
}

function loadTagsInModal() {
    fetch('/api/tags')
        .then(ensureJsonResponse)
        .then((tags) => {
            allTags = Array.isArray(tags) ? tags : [];
            const list = document.getElementById('tagList');
            list.innerHTML = '';

            allTags.forEach((tag) => {
                const nameText = escapeHtml(tag.name);
                const colorText = escapeHtml(tag.color);
                list.insertAdjacentHTML('beforeend', `
                    <div class="list-group-item d-flex justify-content-between align-items-center">
                        <div>
                            <span class="badge bg-${colorText} me-2">${nameText}</span>
                        </div>
                        <div>
                            <button class="btn btn-sm btn-link text-primary" onclick='editTag(${tag.id}, ${JSON.stringify(tag.name)}, ${JSON.stringify(tag.color)})'>编辑</button>
                            <button class="btn btn-sm btn-link text-danger" onclick="deleteTag(${tag.id})">删除</button>
                        </div>
                    </div>
                `);
            });

            renderTagsInForm();
        })
        .catch((error) => alert(`加载标签失败：${error.message}`));
}

function openTagModal() {
    loadTagsInModal();
    document.getElementById('tagId').value = '';
    document.getElementById('tagName').value = '';
    document.getElementById('tagColor').value = 'primary';
    tagModal.show();
}

function saveTag() {
    const id = document.getElementById('tagId').value;
    const name = document.getElementById('tagName').value.trim();
    const color = document.getElementById('tagColor').value;

    if (!name) {
        alert('请输入标签名称');
        return;
    }

    fetch(id ? `/api/tags/${id}` : '/api/tags', {
        method: id ? 'PUT' : 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, color })
    })
        .then(ensureJsonResponse)
        .then((data) => {
            if (data.error) {
                throw new Error(data.error);
            }

            document.getElementById('tagId').value = '';
            document.getElementById('tagName').value = '';
            document.getElementById('tagColor').value = 'primary';
            loadTagsInModal();
        })
        .catch((error) => alert(`保存标签失败：${error.message}`));
}

function editTag(id, name, color) {
    document.getElementById('tagId').value = id;
    document.getElementById('tagName').value = name;
    document.getElementById('tagColor').value = color;
}

function deleteTag(id) {
    if (!confirm('确定要删除这个标签吗？')) {
        return;
    }

    fetch(`/api/tags/${id}`, { method: 'DELETE' })
        .then(ensureJsonResponse)
        .then(() => loadTagsInModal())
        .catch((error) => alert(`删除标签失败：${error.message}`));
}

function loadRecords(date = null) {
    const selectedDate = date || document.getElementById('recordDate').value || formatDate(new Date());
    const keyword = document.getElementById('filterKeyword').value.trim();

    let url = `/api/records?start_date=${selectedDate}&end_date=${selectedDate}`;
    if (keyword) {
        url += `&keyword=${encodeURIComponent(keyword)}`;
    }

    fetch(url)
        .then(ensureJsonResponse)
        .then((records) => renderRecordList(Array.isArray(records) ? records : []))
        .catch((error) => alert(`加载记录失败：${error.message}`));
}

function renderRecordList(records) {
    const list = document.getElementById('recordsList');
    list.innerHTML = '';

    if (records.length === 0) {
        list.innerHTML = '<div class="list-group-item text-center text-muted py-4">暂无记录</div>';
        return;
    }

    records.forEach((record) => {
        const tags = (record.tag || '其他').split(',');
        const title = escapeHtml(record.title || extractTitleFromContent(record.content));
        const timeText = record.create_time?.split(' ')[1]?.substring(0, 5) || '';
        const tagsHtml = tags.map((tagName) => {
            const tag = allTags.find((item) => item.name === tagName);
            const badgeClass = resolveTagBadgeClass(tag);
            return `<span class="badge ${badgeClass} me-1 border">${escapeHtml(tagName)}</span>`;
        }).join('');

        list.insertAdjacentHTML('beforeend', `
            <div class="list-group-item">
                <div class="d-flex w-100 justify-content-between align-items-center mb-1">
                    <h6 class="mb-0 text-truncate" style="max-width: 70%;">${title}</h6>
                    <small class="text-muted">${escapeHtml(timeText)}</small>
                </div>
                <div class="d-flex justify-content-between align-items-center mt-2">
                    <div>${tagsHtml}</div>
                    <div class="btn-group btn-group-sm">
                        <button class="btn btn-outline-primary border-0" onclick='editRecordFromEncoded(${JSON.stringify(encodeURIComponent(JSON.stringify(record)))})'>
                            <i class="fas fa-edit"></i>
                        </button>
                        <button class="btn btn-outline-danger border-0" onclick="deleteRecord(${record.id})">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </div>
            </div>
        `);
    });
}

function resetForm(dateStr = null) {
    document.getElementById('recordId').value = '';
    document.querySelectorAll('.tag-checkbox-group input[type="checkbox"]').forEach((checkbox) => {
        checkbox.checked = false;
    });

    if (tinymceEditor) {
        tinymceEditor.setContent('');
    }

    if (dateStr) {
        setSelectedDate(dateStr);
    }

    const btn = document.querySelector('#recordForm button[onclick="saveRecord()"]');
    if (btn) {
        btn.innerHTML = '<i class="fas fa-save me-1"></i>保存';
    }
}

function editRecordFromEncoded(encodedRecord) {
    const record = JSON.parse(decodeURIComponent(encodedRecord));
    document.getElementById('recordId').value = record.id;

    const tags = (record.tag || '').split(',').filter(Boolean);
    document.querySelectorAll('.tag-checkbox-group input[type="checkbox"]').forEach((checkbox) => {
        checkbox.checked = tags.includes(checkbox.value);
    });

    const dateStr = record.create_time.split(' ')[0];
    setSelectedDate(dateStr);

    if (tinymceEditor) {
        tinymceEditor.setContent(record.content || '');
    }

    const btn = document.querySelector('#recordForm button[onclick="saveRecord()"]');
    if (btn) {
        btn.innerHTML = '<i class="fas fa-save me-1"></i>更新';
    }

    document.getElementById('recordForm').scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function saveRecord() {
    const id = document.getElementById('recordId').value;
    const dateStr = document.getElementById('recordDate').value;
    const content = tinymceEditor ? tinymceEditor.getContent() : '';

    if (!content.trim()) {
        alert('内容不能为空');
        return;
    }

    const selectedTags = Array.from(document.querySelectorAll('.tag-checkbox-group input[type="checkbox"]:checked'))
        .map((checkbox) => checkbox.value);

    const payload = {
        tag: selectedTags.join(',') || '其他',
        content
    };

    if (!id) {
        payload.create_time = `${dateStr} ${new Date().toTimeString().split(' ')[0]}`;
    }

    fetch(id ? `/api/records/${id}` : '/api/records', {
        method: id ? 'PUT' : 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    })
        .then(ensureJsonResponse)
        .then((result) => {
            if (result.error) {
                throw new Error(result.error);
            }

            resetForm(dateStr);
            loadRecords(dateStr);
            calendar.refetchEvents();
        })
        .catch((error) => alert(`保存失败：${error.message}`));
}

function deleteRecord(id) {
    if (!confirm('确定要删除这条记录吗？')) {
        return;
    }

    fetch(`/api/records/${id}`, { method: 'DELETE' })
        .then(ensureJsonResponse)
        .then(() => {
            loadRecords();
            calendar.refetchEvents();
        })
        .catch((error) => alert(`删除失败：${error.message}`));
}

function generateReport() {
    const start = document.getElementById('reportStartDate').value;
    const end = document.getElementById('reportEndDate').value;

    if (!start || !end) {
        alert('请选择开始日期和结束日期');
        return;
    }

    const btn = document.getElementById('btnGenerate');
    const spinner = btn.querySelector('.spinner-border');
    btn.disabled = true;
    spinner.classList.remove('d-none');

    fetch('/api/report', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ start_date: start, end_date: end })
    })
        .then(ensureJsonResponse)
        .then((data) => {
            if (!data.success) {
                throw new Error(data.report || '生成失败');
            }

            if (!data.content || !data.content.trim()) {
                throw new Error('当前时间范围内没有可生成周报的记录');
            }

            const htmlContent = marked.parse(data.content);
            const editor = tinymce.get('reportContent');
            if (editor) {
                editor.setContent(htmlContent);
            }
        })
        .catch((error) => alert(`生成周报失败：${error.message}`))
        .finally(() => {
            btn.disabled = false;
            spinner.classList.add('d-none');
        });
}

function copyReport() {
    const editor = tinymce.get('reportContent');
    const reportText = editor ? editor.getContent({ format: 'text' }).trim() : '';

    if (!reportText) {
        alert('没有可复制的周报内容');
        return;
    }

    copyTextToClipboard(reportText)
        .then(() => alert('周报已复制到剪贴板'))
        .catch((error) => alert(`复制失败：${error.message}`));
}

function loadAiConfig(showSuccessMessage = false) {
    fetch('/api/settings/ai')
        .then(ensureJsonResponse)
        .then((config) => {
            applyAiConfig(config);
            if (showSuccessMessage) {
                showConfigAlert('配置已刷新', 'success');
            } else {
                hideConfigAlert();
            }
        })
        .catch((error) => showConfigAlert(`加载配置失败：${error.message}`, 'danger'));
}

function saveAiConfig() {
    const textModel = document.getElementById('textModel').value.trim();
    const visionModel = document.getElementById('visionModel').value.trim();
    const apiKey = document.getElementById('apiKey').value.trim();

    if (!textModel) {
        showConfigAlert('文本模型不能为空', 'warning');
        return;
    }

    if (!visionModel) {
        showConfigAlert('视觉模型不能为空', 'warning');
        return;
    }

    setConfigSaving(true);
    fetch('/api/settings/ai', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            text_model: textModel,
            vision_model: visionModel,
            api_key: apiKey
        })
    })
        .then(ensureJsonResponse)
        .then((result) => {
            if (result.error) {
                throw new Error(result.error);
            }

            applyAiConfig(result.data || {});
            document.getElementById('apiKey').value = '';
            showConfigAlert(result.message || '配置保存成功', 'success');
        })
        .catch((error) => showConfigAlert(`保存配置失败：${error.message}`, 'danger'))
        .finally(() => setConfigSaving(false));
}

function applyAiConfig(config) {
    document.getElementById('textModel').value = config.text_model || '';
    document.getElementById('visionModel').value = config.vision_model || '';
    document.getElementById('currentApiKeyHint').innerText = config.has_api_key
        ? `当前 Key：${config.api_key_masked}`
        : '当前 Key：未设置';

    const statusBadge = document.getElementById('configApiKeyStatus');
    if (config.has_api_key) {
        statusBadge.className = 'badge rounded-pill text-bg-success config-status-badge';
        statusBadge.innerText = '已配置 API Key';
    } else {
        statusBadge.className = 'badge rounded-pill text-bg-warning config-status-badge';
        statusBadge.innerText = '未配置 API Key';
    }
}

function setConfigSaving(isSaving) {
    const button = document.getElementById('saveConfigBtn');
    const spinner = document.getElementById('saveConfigSpinner');

    button.disabled = isSaving;
    spinner.classList.toggle('d-none', !isSaving);
}

function showConfigAlert(message, type) {
    const alertEl = document.getElementById('configAlert');
    alertEl.className = `alert alert-${type}`;
    alertEl.innerText = message;
}

function hideConfigAlert() {
    const alertEl = document.getElementById('configAlert');
    alertEl.className = 'alert d-none';
    alertEl.innerText = '';
}

function setTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);

    if (typeof tinymce !== 'undefined' && tinymce.editors) {
        tinymce.editors.forEach((editor) => applyThemeToEditor(editor, theme));
    }
}

function applyThemeToEditor(editor, theme) {
    try {
        if (editor.getBody()) {
            if (theme === 'dark') {
                editor.getBody().style.backgroundColor = '#2d2d2d';
                editor.getBody().style.color = '#e0e0e0';
            } else if (theme === 'eye-care') {
                editor.getBody().style.backgroundColor = '#fafff0';
                editor.getBody().style.color = '#2e3b2a';
            } else {
                editor.getBody().style.backgroundColor = '#ffffff';
                editor.getBody().style.color = '#323232';
            }
        }

        if (editor.getDoc()) {
            const doc = editor.getDoc();
            let styleEl = doc.getElementById('dynamic-theme-style');
            if (!styleEl) {
                styleEl = doc.createElement('style');
                styleEl.id = 'dynamic-theme-style';
                doc.head.appendChild(styleEl);
            }

            const commonRules = 'p, span, li, td, th { color: inherit; }';
            const bodySelector = 'body, body.mce-content-body';

            if (theme === 'dark') {
                styleEl.textContent = `
                    ${bodySelector} { background-color: #2d2d2d !important; color: #e0e0e0 !important; color-scheme: dark; }
                    ${commonRules}
                    a { color: #8ab6d6 !important; }
                `;
            } else if (theme === 'eye-care') {
                styleEl.textContent = `
                    ${bodySelector} { background-color: #fafff0 !important; color: #2e3b2a !important; color-scheme: light; }
                    ${commonRules}
                    a { color: #5c7a45 !important; }
                `;
            } else {
                styleEl.textContent = `
                    ${bodySelector} { background-color: #ffffff !important; color: #323232 !important; color-scheme: light; }
                    ${commonRules}
                    a { color: #0d6efd !important; }
                `;
            }

            editor.getBody().style.display = 'none';
            editor.getBody().offsetHeight;
            editor.getBody().style.display = '';
        }
    } catch (error) {
        console.error('Error applying theme to editor:', error);
    }
}

function resolveTagBadgeClass(tag) {
    if (!tag) {
        return 'bg-secondary';
    }

    const needsDarkText = ['warning', 'info', 'light'].includes(tag.color);
    return `bg-${tag.color}${needsDarkText ? ' text-dark' : ''}`;
}

function extractTitleFromContent(content) {
    const plainText = (content || '').replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim();
    return plainText ? plainText.slice(0, 24) : '未命名记录';
}

function ensureJsonResponse(response) {
    return response.json().then((data) => {
        if (!response.ok) {
            throw new Error(data.error || '请求失败');
        }
        return data;
    });
}

function copyTextToClipboard(text) {
    if (navigator.clipboard?.writeText) {
        return navigator.clipboard.writeText(text);
    }

    return new Promise((resolve, reject) => {
        const textarea = document.createElement('textarea');
        textarea.value = text;
        textarea.style.position = 'fixed';
        textarea.style.opacity = '0';
        document.body.appendChild(textarea);
        textarea.focus();
        textarea.select();

        const copied = document.execCommand('copy');
        document.body.removeChild(textarea);

        if (copied) {
            resolve();
        } else {
            reject(new Error('浏览器不支持复制'));
        }
    });
}

function escapeHtml(value) {
    return String(value ?? '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

function formatDate(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
}
