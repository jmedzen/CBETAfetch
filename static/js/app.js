/**
 * CBETAfetch 2.0 - Vue 3 Fluent Pipeline & Reading Workbench
 * 4-Step Guided Pipeline, Buddhist Presets, Real-time SSE Logs, and Markdown Reader
 */

const { createApp, ref, reactive, computed, onMounted, onUnmounted, watch, nextTick } = Vue;

const app = createApp({
  setup() {
    // --- Navigation & Theme State ---
    // tabs: 'step1_corpus', 'step2_download', 'step3_combine', 'step4_workbench', 'full_canon', 'settings', 'diagnostics'
    const currentTab = ref('step1_corpus');
    const currentTheme = ref(localStorage.getItem('cbeta_theme') || 'dark');
    const currentLang = ref(localStorage.getItem('cbeta_lang') || 'zh-TW');
    const translations = ref({});

    // --- System & Job Engine State ---
    const systemStatus = ref('ready'); // 'ready' | 'busy'
    const activeJob = ref(null);
    const isSubmitting = ref(false);
    const toastMessage = ref('');
    const showToast = ref(false);

    // --- Live Logs State ---
    const logs = ref([]);
    const logFilter = ref('all'); // 'all' | 'error' | 'success' | 'info'
    const autoScroll = ref(true);
    const isLogDrawerOpen = ref(true);
    const terminalRef = ref(null);
    let sseSource = null;
    let pollTimer = null;

    // --- Presets & Corpus Library ---
    const presets = ref([]);
    const selectedPresetId = ref('weishi');

    // --- Step 1 & Pipeline Config Form ---
    const pipelineForm = reactive({
      idList: 'T1585\nT1586\nT1590\nT1592\nT1599',
      destDir: './downloads',
      outputDir: './complete',
      formats: ['txt'],
      removeZip: true,
      autoHeading: true,
      exampleUrl: '',
      htmlUrl: '',
      pdfUrl: '',
      epubUrl: '',
      mobiUrl: '',
      docxUrl: '',
      odtUrl: '',
      docuskyUrl: '',
      textNotesUrl: ''
    });

    // --- Full Pack Form (TXT and XML editions) ---
    const fullPackForm = reactive({
      edition: 'txt', // 'txt' | 'xml'
      destDir: './downloads',
      outputDir: './complete',
      packUrl: 'https://cbdata.dila.edu.tw/stable/download/cbeta-text.zip',
      xmlRepoUrl: 'https://github.com/cbeta-org/xml-p5',
      xmlDestDir: './downloads-xml',
      shallow: true,
      convertMd: true,
      autoHeading: true
    });
    const xmlRepoStatus = ref(null);
    const isCheckingXmlStatus = ref(false);
    const remoteUpdates = ref(null);
    const isCheckingUpdates = ref(false);

    // --- Step 4: Workbench & Completed Files ---
    const completeFiles = ref([]);
    const selectedFileName = ref('');
    const fileContentData = ref(null);
    const isLoadingFile = ref(false);
    const fileSearchQuery = ref('');
    const fileCategoryFilter = ref('all'); // 'all' | 'sutra_md' | 'ebook' | 'document' | 'data'
    const readerViewMode = ref('rendered'); // 'rendered' | 'raw'
    const textSearchQuery = ref('');

    // --- Smart Adaptive Pipeline Mode Detection ---
    const pipelineStreamMode = computed(() => {
      const fmts = pipelineForm.formats.map(f => f.toLowerCase());
      const textFmts = ['txt', 'text-with-notes'];
      const hasText = fmts.some(f => textFmts.includes(f));
      const hasNonText = fmts.some(f => !textFmts.includes(f));
      if (hasText && hasNonText) return 'dual_stream';
      if (hasText) return 'text_stream';
      return 'ebook_stream';
    });

    // --- Diagnostics State ---
    const diagnosticsReport = ref(null);
    const isDiagnosing = ref(false);

    // --- i18n Helpers ---
    const t = (key, fallback = '') => translations.value[key] || fallback || key;

    const loadLanguage = async (lang) => {
      try {
        const res = await fetch(`/static/lang/${lang}.json`);
        translations.value = await res.json();
        localStorage.setItem('cbeta_lang', lang);
        currentLang.value = lang;
      } catch (err) {
        console.error('Failed to load language:', err);
      }
    };

    const toggleTheme = (themeName) => {
      currentTheme.value = themeName;
      localStorage.setItem('cbeta_theme', themeName);
      document.body.className = themeName === 'dark' ? '' : `theme-${themeName}`;
    };

    const triggerToast = (msg, duration = 3000) => {
      toastMessage.value = msg;
      showToast.value = true;
      setTimeout(() => {
        showToast.value = false;
      }, duration);
    };

    // --- Presets Management (CRUD) ---
    const presetModalOpen = ref(false);
    const isSavingPreset = ref(false);
    const editingPreset = reactive({
      id: '',
      title: '',
      category: '自訂部類',
      badge: '常用',
      description: '',
      default_ids: '',
      is_custom: true
    });

    const loadPresets = async () => {
      try {
        const res = await fetch('/api/presets');
        presets.value = await res.json();
      } catch (e) {
        console.error('Failed to load presets:', e);
      }
    };

    const applyPreset = (preset) => {
      selectedPresetId.value = preset.id;
      pipelineForm.idList = preset.default_ids;
      triggerToast(`已套用《${preset.title}》經典預設`);
    };

    const openCreatePresetModal = () => {
      editingPreset.id = '';
      editingPreset.title = '';
      editingPreset.category = '自訂部類';
      editingPreset.badge = '常用';
      editingPreset.description = '';
      editingPreset.default_ids = '';
      editingPreset.is_custom = true;
      presetModalOpen.value = true;
    };

    const openEditPresetModal = (preset, event) => {
      if (event) event.stopPropagation();
      editingPreset.id = preset.id;
      editingPreset.title = preset.title;
      editingPreset.category = preset.category || '自訂部類';
      editingPreset.badge = preset.badge || '常用';
      editingPreset.description = preset.description || '';
      editingPreset.default_ids = preset.default_ids || '';
      editingPreset.is_custom = preset.is_custom !== false;
      presetModalOpen.value = true;
    };

    const savePreset = async () => {
      if (!editingPreset.title.trim()) {
        alert('請填寫預設典籍標題');
        return;
      }
      if (!editingPreset.default_ids.trim()) {
        alert('請填寫常用經號列表');
        return;
      }

      isSavingPreset.value = true;
      try {
        const res = await fetch('/api/presets', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            id: editingPreset.id || undefined,
            title: editingPreset.title,
            category: editingPreset.category,
            badge: editingPreset.badge,
            description: editingPreset.description,
            default_ids: editingPreset.default_ids,
            is_custom: true
          })
        });

        if (res.ok) {
          const data = await res.json();
          await loadPresets();
          presetModalOpen.value = false;
          if (data.preset) {
            applyPreset(data.preset);
          }
          triggerToast(`預設典籍《${editingPreset.title}》已成功儲存`);
        } else {
          alert('儲存預設失敗');
        }
      } catch (e) {
        alert('儲存預設時發生異常: ' + e);
      } finally {
        isSavingPreset.value = false;
      }
    };

    const deletePreset = async (preset, event) => {
      if (event) event.stopPropagation();
      if (!confirm(`確定要刪除預設《${preset.title}》嗎？`)) {
        return;
      }

      try {
        const res = await fetch(`/api/presets/${encodeURIComponent(preset.id)}`, {
          method: 'DELETE'
        });
        if (res.ok) {
          await loadPresets();
          if (selectedPresetId.value === preset.id) {
            selectedPresetId.value = '';
          }
          triggerToast(`已刪除預設《${preset.title}》`);
        } else {
          alert('刪除預設失敗');
        }
      } catch (e) {
        alert('刪除預設時發生異常: ' + e);
      }
    };

    const resetPresets = async () => {
      if (!confirm('確定要重置為 CBETA 內建 6 大經典預設嗎？（自訂預設將被覆蓋）')) {
        return;
      }
      try {
        const res = await fetch('/api/presets/reset', { method: 'POST' });
        if (res.ok) {
          await loadPresets();
          triggerToast('已重置為內建經典預設');
        }
      } catch (e) {
        alert('重置失敗: ' + e);
      }
    };

    const clearIdList = () => {
      pipelineForm.idList = '';
      selectedPresetId.value = '';
      triggerToast('經文編號列表已清空');
    };

    // --- SSE & Logs ---
    const parseLogLevel = (text) => {
      const lower = text.toLowerCase();
      if (text.includes('[PROGRESS]') || text.includes('█') || text.includes('░')) return 'progress';
      if (lower.includes('error') || lower.includes('failed') || lower.includes('失敗') || lower.includes('異常')) return 'error';
      if (lower.includes('finished') || lower.includes('success') || lower.includes('完成') || lower.includes('成功') || lower.includes('圓滿')) return 'success';
      if (lower.includes('starting') || lower.includes('progress') || lower.includes('開始') || lower.includes('步驟')) return 'info';
      if (lower.includes('warning') || lower.includes('警示')) return 'warning';
      return 'normal';
    };

    const appendLogEntry = (rawText) => {
      if (rawText === '.') {
        if (logs.value.length > 0) {
          logs.value[logs.value.length - 1].text += '.';
        }
        return;
      }

      const isProgress = rawText.includes('[PROGRESS]') || rawText.includes('█') || rawText.includes('░');

      // Update active job percentage in real time from log
      const pctMatch = rawText.match(/(\d+\.?\d*)\s*%/);
      if (pctMatch && activeJob.value) {
        activeJob.value.progress_percent = parseFloat(pctMatch[1]);
      }

      // Smooth in-place progress bar animation (replaces previous progress bar line in console)
      if (isProgress && logs.value.length > 0) {
        const lastEntry = logs.value[logs.value.length - 1];
        if (lastEntry.level === 'progress' || lastEntry.text.includes('[PROGRESS]') || lastEntry.text.includes('█') || lastEntry.text.includes('░')) {
          lastEntry.text = rawText;
          lastEntry.level = 'progress';
          if (autoScroll.value) {
            nextTick(() => {
              if (terminalRef.value) {
                terminalRef.value.scrollTop = terminalRef.value.scrollHeight;
              }
            });
          }
          return;
        }
      }

      logs.value.push({
        id: Date.now() + Math.random(),
        text: rawText,
        level: isProgress ? 'progress' : parseLogLevel(rawText)
      });

      if (logs.value.length > 600) {
        logs.value.shift();
      }

      if (autoScroll.value) {
        nextTick(() => {
          if (terminalRef.value) {
            terminalRef.value.scrollTop = terminalRef.value.scrollHeight;
          }
        });
      }
    };

    const initSSE = () => {
      if (sseSource) sseSource.close();
      sseSource = new EventSource('/logs');
      sseSource.onmessage = (event) => {
        try {
          const incoming = JSON.parse(event.data);
          if (Array.isArray(incoming)) {
            incoming.forEach(appendLogEntry);
          } else {
            appendLogEntry(incoming);
          }
        } catch (e) {
          appendLogEntry(event.data);
        }
      };
    };

    const clearLogs = () => {
      logs.value = [];
      triggerToast('日誌已清空');
    };

    const copyLogs = async () => {
      const allText = logs.value.map(l => l.text).join('\n');
      try {
        await navigator.clipboard.writeText(allText);
        triggerToast('日誌已複製到剪貼簿');
      } catch (err) {
        triggerToast('複製失敗: ' + err);
      }
    };

    const filteredLogs = computed(() => {
      if (logFilter.value === 'all') return logs.value;
      return logs.value.filter(l => l.level === logFilter.value);
    });

    // --- Status Polling & Completed Files ---
    const pollStatus = async () => {
      try {
        const res = await fetch('/api/status');
        const data = await res.json();
        const prevStatus = systemStatus.value;
        systemStatus.value = data.status;
        activeJob.value = data.active_job;

        // If job just completed, refresh files list
        if (prevStatus === 'busy' && data.status === 'ready') {
          await loadCompleteFiles();
        }
      } catch (e) {}
    };

    const cancelActiveJob = async () => {
      if (!activeJob.value) return;
      try {
        await fetch(`/api/jobs/${activeJob.value.job_id}/cancel`, { method: 'POST' });
        triggerToast('已送出中斷任務請求');
        await pollStatus();
      } catch (e) {
        triggerToast('中斷失敗: ' + e);
      }
    };

    const loadCompleteFiles = async () => {
      try {
        const res = await fetch('/api/complete/files');
        completeFiles.value = await res.json();
        if (completeFiles.value.length > 0 && !selectedFileName.value) {
          await openFilePreview(completeFiles.value[0].filename);
        }
      } catch (e) {
        console.error('Failed to load complete files:', e);
      }
    };

    const openFilePreview = async (filename) => {
      selectedFileName.value = filename;
      isLoadingFile.value = true;
      try {
        const res = await fetch(`/api/complete/file?filename=${encodeURIComponent(filename)}`);
        if (res.ok) {
          fileContentData.value = await res.json();
        } else {
          fileContentData.value = null;
          triggerToast('讀取檔案失敗');
        }
      } catch (e) {
        triggerToast('連線失敗: ' + e);
      } finally {
        isLoadingFile.value = false;
      }
    };

    const downloadCurrentFile = () => {
      if (!fileContentData.value) return;
      const fn = fileContentData.value.filename;

      if (fileContentData.value.is_binary) {
        // Direct browser stream download for PDF, EPUB, DOCX, ODT
        const url = `/api/complete/download?filename=${encodeURIComponent(fn)}`;
        const a = document.createElement('a');
        a.href = url;
        a.download = fn;
        a.click();
        triggerToast(`已開始下載 ${fn}`);
        return;
      }

      // Markdown / Text download
      const blob = new Blob([fileContentData.value.content], { type: 'text/markdown;charset=utf-8' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = fn;
      a.click();
      URL.revokeObjectURL(url);
      triggerToast(`已下載 ${fn}`);
    };

    const copyCurrentFileContent = async () => {
      if (!fileContentData.value || fileContentData.value.is_binary) return;
      try {
        await navigator.clipboard.writeText(fileContentData.value.content);
        triggerToast(`已複製《${fileContentData.value.filename}》全文到剪貼簿`);
      } catch (e) {
        triggerToast('複製失敗: ' + e);
      }
    };

    const filteredCompleteFiles = computed(() => {
      let list = completeFiles.value;
      if (fileCategoryFilter.value !== 'all') {
        list = list.filter(f => f.category === fileCategoryFilter.value);
      }
      if (!fileSearchQuery.value.trim()) return list;
      const q = fileSearchQuery.value.toLowerCase();
      return list.filter(f => f.filename.toLowerCase().includes(q));
    });

    const renderedFileHtml = computed(() => {
      if (!fileContentData.value || !fileContentData.value.content) return '';
      let text = fileContentData.value.content;

      // Escape HTML
      text = text
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');

      // Format H2 headings (## ...)
      text = text.replace(/^##\s+(.+)$/gm, '<h2 class="text-lg font-bold text-amber-400 mt-6 mb-3 pb-1 border-b border-amber-500/20 flex items-center space-x-2"><span class="px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 font-mono text-xs">卷品</span><span>$1</span></h2>');

      // Format Comments (// ...)
      text = text.replace(/^\/\/\s*(.+)$/gm, '<div class="text-xs text-slate-500 code-font py-0.5 italic">// $1</div>');

      // Format paragraphs
      const lines = text.split('\n');
      const formatted = lines.map(line => {
        if (line.startsWith('<h2') || line.startsWith('<div class="text-xs')) return line;
        if (!line.trim()) return '<div class="h-3"></div>';
        return `<p class="buddhist-font my-2 leading-relaxed zen-text-main text-sm sm:text-base">${line}</p>`;
      });

      return formatted.join('');
    });

    // --- Pipeline Actions ---
    const runFullPipeline = async () => {
      if (!pipelineForm.idList.trim()) {
        alert('請先輸入經文編號');
        return;
      }
      isSubmitting.value = true;
      try {
        const res = await fetch('/api/pipeline/run', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            id_list: pipelineForm.idList,
            dest_dir: pipelineForm.destDir || './downloads',
            output_dir: pipelineForm.outputDir || './complete',
            formats: pipelineForm.formats,
            remove_zip: pipelineForm.removeZip,
            auto_heading: pipelineForm.autoHeading
          })
        });
        const data = await res.json();
        if (data.status === 'started') {
          triggerToast('一鍵端到端研讀流水線已在背景啟動！');
          await pollStatus();
        }
      } catch (e) {
        alert('流水線啟動失敗: ' + e);
      } finally {
        isSubmitting.value = false;
      }
    };

    // Sub-stage trigger actions
    const startDownloadOnly = async () => {
      if (!pipelineForm.idList.trim()) return;
      isSubmitting.value = true;
      try {
        const res = await fetch('/api/download', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            id_list: pipelineForm.idList,
            dest_dir: pipelineForm.destDir,
            example_url: pipelineForm.exampleUrl || undefined,
            formats: pipelineForm.formats,
            html_url: pipelineForm.htmlUrl || undefined,
            pdf_url: pipelineForm.pdfUrl || undefined,
            epub_url: pipelineForm.epubUrl || undefined,
            mobi_url: pipelineForm.mobiUrl || undefined,
            docx_url: pipelineForm.docxUrl || undefined,
            odt_url: pipelineForm.odtUrl || undefined,
            docusky_url: pipelineForm.docuskyUrl || undefined,
            text_notes_url: pipelineForm.textNotesUrl || undefined
          })
        });
        const data = await res.json();
        if (data.status === 'started') {
          triggerToast('批次下載已啟動');
          await pollStatus();
        }
      } catch (e) {
        alert('下載啟動失敗: ' + e);
      } finally {
        isSubmitting.value = false;
      }
    };

    const startProcessOnly = async () => {
      isSubmitting.value = true;
      try {
        const res = await fetch('/api/process', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            project_dir: pipelineForm.destDir,
            output_dir: pipelineForm.outputDir || undefined,
            remove_zip: pipelineForm.removeZip
          })
        });
        const data = await res.json();
        if (data.status === 'started') {
          triggerToast('解壓與卷次合併已啟動');
          await pollStatus();
        }
      } catch (e) {
        alert('合併啟動失敗: ' + e);
      } finally {
        isSubmitting.value = false;
      }
    };

    const startConvertOnly = async () => {
      isSubmitting.value = true;
      try {
        const res = await fetch('/api/convert_md', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            project_dir: pipelineForm.outputDir || './complete',
            auto_heading: pipelineForm.autoHeading,
            remove_source: true
          })
        });
        const data = await res.json();
        if (data.status === 'started') {
          triggerToast('Markdown 轉換與排版已啟動');
          await pollStatus();
        }
      } catch (e) {
        alert('排版啟動失敗: ' + e);
      } finally {
        isSubmitting.value = false;
      }
    };

    const checkRemoteUpdates = async () => {
      isCheckingUpdates.value = true;
      try {
        const zipUrl = fullPackForm.packUrl || 'https://cbdata.dila.edu.tw/stable/download/cbeta-text.zip';
        const gitUrl = fullPackForm.xmlRepoUrl || 'https://github.com/cbeta-org/xml-p5';
        const localXml = fullPackForm.xmlDestDir || './downloads-xml';
        const res = await fetch(`/api/remote/updates?zip_url=${encodeURIComponent(zipUrl)}&git_url=${encodeURIComponent(gitUrl)}&local_xml_dir=${encodeURIComponent(localXml)}`);
        if (res.ok) {
          remoteUpdates.value = await res.json();
        }
      } catch (e) {
        console.error('Failed to fetch remote updates:', e);
      } finally {
        isCheckingUpdates.value = false;
      }
    };

    const checkXmlRepoStatus = async () => {
      isCheckingXmlStatus.value = true;
      try {
        const dest = fullPackForm.xmlDestDir || './downloads-xml';
        const res = await fetch(`/api/xml_repo/status?dest_dir=${encodeURIComponent(dest)}`);
        xmlRepoStatus.value = await res.json();
      } catch (e) {
        console.error('Failed to check XML repo status:', e);
      } finally {
        isCheckingXmlStatus.value = false;
      }
    };

    const startFullPack = async () => {
      isSubmitting.value = true;
      try {
        let payload = {};
        if (fullPackForm.edition === 'xml') {
          payload = {
            edition: 'xml',
            dest_dir: fullPackForm.xmlDestDir || './downloads-xml',
            xml_repo_url: fullPackForm.xmlRepoUrl || 'https://github.com/cbeta-org/xml-p5',
            shallow: fullPackForm.shallow
          };
        } else {
          payload = {
            edition: 'txt',
            dest_dir: fullPackForm.destDir || './downloads',
            output_dir: fullPackForm.outputDir || undefined,
            pack_url: fullPackForm.packUrl,
            convert_md: fullPackForm.convertMd,
            auto_heading: fullPackForm.autoHeading
          };
        }

        const res = await fetch('/api/complete_process', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (data.status === 'started') {
          const modeName = fullPackForm.edition === 'xml' ? 'TEI P5 XML Git 同步' : '純文字 ZIP 全藏下載';
          triggerToast(`全藏下載 [${modeName}] 任務已在背景啟動`);
          await pollStatus();
        }
      } catch (e) {
        alert('全藏任務啟動失敗: ' + e);
      } finally {
        isSubmitting.value = false;
      }
    };

    const startXmlToObsidian = async () => {
      isSubmitting.value = true;
      try {
        const res = await fetch('/api/xml_repo/convert_obsidian', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            xml_dir: fullPackForm.xmlDestDir || './downloads-xml',
            output_dir: fullPackForm.outputDir || './complete',
            include_page_marks: false,
            include_line_anchors: false
          })
        });
        const data = await res.json();
        if (data.status === 'started') {
          triggerToast('XML 轉 Obsidian Markdown 作業已在背景啟動');
          await pollStatus();
        }
      } catch (e) {
        alert('啟動轉換失敗: ' + e);
      } finally {
        isSubmitting.value = false;
      }
    };

    const runDiagnostics = async () => {
      isDiagnosing.value = true;
      try {
        const res = await fetch('/api/system/self-test');
        diagnosticsReport.value = await res.json();
        triggerToast('全系統自檢完成');
      } catch (e) {
        alert('自檢呼叫失敗: ' + e);
      } finally {
        isDiagnosing.value = false;
      }
    };

    // --- Lifecycle ---
    onMounted(async () => {
      await loadLanguage(currentLang.value);
      toggleTheme(currentTheme.value);
      await loadPresets();
      await loadCompleteFiles();
      checkXmlRepoStatus();
      checkRemoteUpdates();
      initSSE();
      await pollStatus();
      pollTimer = setInterval(pollStatus, 2000);
    });

    onUnmounted(() => {
      if (sseSource) sseSource.close();
      if (pollTimer) clearInterval(pollTimer);
    });

    return {
      currentTab,
      currentTheme,
      currentLang,
      systemStatus,
      activeJob,
      isSubmitting,
      showToast,
      toastMessage,
      logs,
      logFilter,
      autoScroll,
      isLogDrawerOpen,
      terminalRef,
      filteredLogs,
      presets,
      selectedPresetId,
      presetModalOpen,
      isSavingPreset,
      editingPreset,
      openCreatePresetModal,
      openEditPresetModal,
      savePreset,
      deletePreset,
      resetPresets,
      pipelineForm,
      fullPackForm,
      completeFiles,
      selectedFileName,
      fileContentData,
      isLoadingFile,
      fileSearchQuery,
      fileCategoryFilter,
      pipelineStreamMode,
      readerViewMode,
      textSearchQuery,
      filteredCompleteFiles,
      renderedFileHtml,
      diagnosticsReport,
      isDiagnosing,
      t,
      loadLanguage,
      toggleTheme,
      clearLogs,
      copyLogs,
      cancelActiveJob,
      applyPreset,
      clearIdList,
      runFullPipeline,
      startDownloadOnly,
      startProcessOnly,
      startConvertOnly,
      startFullPack,
      runDiagnostics,
      openFilePreview,
      downloadCurrentFile,
      copyCurrentFileContent,
      loadCompleteFiles,
      xmlRepoStatus,
      isCheckingXmlStatus,
      checkXmlRepoStatus,
      remoteUpdates,
      isCheckingUpdates,
      checkRemoteUpdates,
      startXmlToObsidian
    };
  }
});

app.mount('#app');
