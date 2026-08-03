/**
 * AI 辅助判定 — 前端交互逻辑
 * 配置仅存于内存变量，页面刷新即清除
 */
(function () {
  'use strict';

  // ---- 内存中的 AI 配置 ----
  // 持久化到 sessionStorage：整页刷新（点击「开始判断」提交表单）后自动恢复，
  // 保证 API 连接不断链；关闭标签页 / 重启浏览器即清除。
  var SESSION_KEY = 'ai_session_config';
  var aiConfig = loadAIConfig(); // { platform, api_key, web_search } 或 null

  function loadAIConfig() {
    try {
      var raw = sessionStorage.getItem(SESSION_KEY);
      if (!raw) return null;
      var cfg = JSON.parse(raw);
      if (cfg && cfg.platform && cfg.api_key) return cfg;
    } catch (e) {}
    return null;
  }
  function saveAIConfig(cfg) {
    aiConfig = cfg;
    try {
      if (cfg) sessionStorage.setItem(SESSION_KEY, JSON.stringify(cfg));
      else sessionStorage.removeItem(SESSION_KEY);
    } catch (e) {}
  }

  // ---- DOM 引用 ----
  var configBtn = document.getElementById('ai-config-btn');
  var overlay = document.getElementById('ai-modal-overlay');
  var closeBtn = document.getElementById('ai-modal-close');
  var skipBtn = document.getElementById('ai-modal-skip');
  var confirmBtn = document.getElementById('ai-modal-confirm');
  var platformSel = document.getElementById('ai-platform');
  var apikeyInput = document.getElementById('ai-apikey');
  var webSearchCb = document.getElementById('ai-web-search');
  var statusDot = document.getElementById('ai-status-dot');
  var aiResultWrapper = document.getElementById('ai-result-wrapper');
  var aiResultContent = document.getElementById('ai-result-content');
  var aiResultPlatform = document.getElementById('ai-result-platform');
  // ---- 风险告知层 ----
  var disclaimerOverlay = document.getElementById('disclaimer-overlay');
  var disclaimerScroll = document.getElementById('disclaimer-scroll');
  var disclaimerYes = document.getElementById('disclaimer-yes');
  var disclaimerNo = document.getElementById('disclaimer-no');
  var disclaimerCount = document.getElementById('disclaimer-count');
  var DISCLAIMER_SECONDS = 10;
  var disclaimerTimer = null;
  var disclaimerRead = false;   // 是否已滚动到底（阅读完成）
  var disclaimerTimeUp = false; // 倒计时是否结束

  if (!configBtn || !overlay) return; // 不在首页时退出

  var PLATFORM_LABELS = {
    doubao: 'Doubao',
    deepseek: 'DeepSeek',
    glm: 'GLM',
    chatgpt: 'ChatGPT',
    gemini: 'Gemini',
    hunyuan: '腾讯混元',
    wenxin: '文心一言'
  };

  // ---- Modal 控制 ----
  var networkHint = document.getElementById('ai-network-hint');
  var NETWORK_WARN_PLATFORMS = { chatgpt: true, gemini: true };

  function syncNetworkHint() {
    if (!networkHint) return;
    if (NETWORK_WARN_PLATFORMS[platformSel.value]) {
      networkHint.hidden = false;
    } else {
      networkHint.hidden = true;
    }
  }

  function openModal() {
    // 回填已有配置
    if (aiConfig) {
      platformSel.value = aiConfig.platform;
      apikeyInput.value = aiConfig.api_key;
      webSearchCb.checked = aiConfig.web_search;
    }
    syncNetworkHint();
    overlay.classList.add('open');
  }

  function closeModal() {
    overlay.classList.remove('open');
  }

  // 切换平台时同步网络提示
  platformSel.addEventListener('change', syncNetworkHint);

  // ---- 风险告知：10 秒倒计时 + 需滚动读完全文，双条件满足才可确认 ----
  function syncDisclaimerState() {
    // 两个条件都满足才解锁「我已知晓上述风险」
    var ready = disclaimerTimeUp && disclaimerRead;
    if (disclaimerYes) disclaimerYes.disabled = !ready;
  }

  function openDisclaimer() {
    if (!disclaimerOverlay) { openModal(); return; }
    // 重置状态
    disclaimerRead = false;
    disclaimerTimeUp = false;
    if (disclaimerCount) disclaimerCount.textContent = String(DISCLAIMER_SECONDS);
    if (disclaimerScroll) disclaimerScroll.scrollTop = 0; // 从头开始阅读
    syncDisclaimerState();
    disclaimerOverlay.classList.add('open');
    if (disclaimerTimer) clearInterval(disclaimerTimer);
    var remain = DISCLAIMER_SECONDS;
    disclaimerTimer = setInterval(function () {
      remain--;
      if (disclaimerCount) disclaimerCount.textContent = String(Math.max(remain, 0));
      if (remain <= 0) {
        clearInterval(disclaimerTimer);
        disclaimerTimer = null;
        disclaimerTimeUp = true;
        syncDisclaimerState(); // 倒计时结束仅解锁条件之一，仍需滚动读完
      }
    }, 1000);
  }

  function closeDisclaimer() {
    if (disclaimerTimer) { clearInterval(disclaimerTimer); disclaimerTimer = null; }
    if (disclaimerOverlay) disclaimerOverlay.classList.remove('open');
  }

  // 滚动到底（阅读完成）判定
  if (disclaimerScroll) {
    disclaimerScroll.addEventListener('scroll', function () {
      var el = disclaimerScroll;
      // 距底部 4px 内视为已读完
      if (el.scrollTop + el.clientHeight >= el.scrollHeight - 4) {
        if (!disclaimerRead) {
          disclaimerRead = true;
          syncDisclaimerState();
        }
      }
    });
  }

  configBtn.addEventListener('click', openDisclaimer);

  // 「我已知晓上述风险」：双条件满足后点击 → 进入 API Key 配置
  if (disclaimerYes) {
    disclaimerYes.addEventListener('click', function () {
      if (!(disclaimerTimeUp && disclaimerRead)) return;
      clearInterval(disclaimerTimer);
      disclaimerTimer = null;
      closeDisclaimer();
      openModal();
    });
  }

  // 「我不认可」：直接退出整个配置窗口（不进入 API Key 界面）
  if (disclaimerNo) {
    disclaimerNo.addEventListener('click', function () {
      clearInterval(disclaimerTimer);
      disclaimerTimer = null;
      closeDisclaimer();
    });
  }

  // 点击遮罩 / ESC 均不跳过提示（必须读完并确认，或点「我不认可」退出）
  if (disclaimerOverlay) {
    disclaimerOverlay.addEventListener('click', function (e) {
      if (e.target === disclaimerOverlay) return; // 忽略遮罩点击
    });
  }
  closeBtn.addEventListener('click', closeModal);
  skipBtn.addEventListener('click', function () {
    saveAIConfig(null);
    updateStatusDot();
    closeModal();
  });
  confirmBtn.addEventListener('click', function () {
    var key = apikeyInput.value.trim();
    if (!key) {
      apikeyInput.focus();
      apikeyInput.style.borderColor = '#f87171';
      setTimeout(function () { apikeyInput.style.borderColor = ''; }, 1500);
      return;
    }
    saveAIConfig({
      platform: platformSel.value,
      api_key: key,
      web_search: webSearchCb.checked
    });
    updateStatusDot();
    closeModal();

    // 如果已有本地结果，立即触发 AI 判定
    if (window.__pageData && window.__pageData.hasResult) {
      triggerAICheck();
    }
  });

  // 点击遮罩关闭
  overlay.addEventListener('click', function (e) {
    if (e.target === overlay) closeModal();
  });

  // ESC 关闭
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && overlay.classList.contains('open')) {
      closeModal();
    }
  });

  function updateStatusDot() {
    if (aiConfig) {
      statusDot.classList.add('active');
    } else {
      statusDot.classList.remove('active');
    }
  }

  // ---- 构建 AI Prompt（需求2：联网判断是否符合12306学生票优惠区间） ----
  function buildPrompt(pageData) {
    var inp = pageData.input || {};
    var local = pageData.localResult || {};
    var parts = [];
    parts.push('你是一位中国铁路客运规则专家，请联网查询并核实 12306 学生票优惠区间规定（依据《铁路旅客运输规程》第十六条），判断以下购票方式是否符合规定。');
    parts.push('');
    parts.push('【用户输入】');
    parts.push('- 学校所在城市：' + (inp.school || '未填'));
    parts.push('- 家庭所在城市：' + (inp.home || '未填'));
    parts.push('- 出发站：' + (inp.dep || '未填'));
    parts.push('- 到达站：' + (inp.arr || '未填'));
    if (inp.waypoints && inp.waypoints.length) {
      parts.push('- 中转城市/车站：' + inp.waypoints.join('、') + '（存在中转）');
    } else {
      parts.push('- 中转城市/车站：无');
    }
    if (inp.seat) parts.push('- 席别：' + inp.seat);
    if (inp.fresh_grad) parts.push('- 身份：新生/毕业生');
    if (inp.new_home) parts.push('- 新家庭所在地：' + inp.new_home);
    parts.push('');
    parts.push('【本地引擎判定结果】');
    parts.push('- 是否合规：' + (local.ok ? '合规' : '不合规'));
    parts.push('- 原因：' + (local.reason || '无'));
    if (local.path && local.path.length) {
      parts.push('- 优惠路径：' + local.path.join(' → '));
    }
    if (local.is_reverse) parts.push('- 反向购票：是');
    if (local.seat_invalid) parts.push('- 席别不符：是');
    // 注入 12306 真实列车排图（直达/中转），辅助 AI 更精准判断
    var real = formatDirectRouteForPrompt();
    if (real) {
      parts.push('');
      parts.push(real);
    }
    parts.push('');
    parts.push('【请你分析】');
    parts.push('1. 该购票区间是否符合 12306 学生票优惠区间规定？请先给出结论。');
    parts.push('2. 第一行请严格输出「结论：合规」或「结论：不合规」或「结论：存疑」，不要包含其他内容。');
    parts.push('3. 随后给出简要理由与注意事项（如有直达/中转信息请结合）。');
    parts.push('');
    parts.push('请用简洁的中文回答。');
    return parts.join('\n');
  }

  // 格式化直达/中转数据供 AI prompt 使用（真实列车排图）
  function formatDirectRouteForPrompt() {
    if (!directRouteData) return '';
    var parts = [];
    if (directRouteData.has_direct && directRouteData.direct && directRouteData.direct.length) {
      parts.push('【12306 真实列车排图（学校↔家庭）】有直达列车，共 ' + directRouteData.direct.length + ' 趟，示例：');
      directRouteData.direct.slice(0, 5).forEach(function (t) {
        parts.push('- ' + t.trainCode + ' ' + t.departTime + '→' + t.arriveTime + '（' + t.fromStation + ' → ' + t.toStation + '，历时 ' + t.duration + '）');
      });
    } else if (directRouteData.transfers && directRouteData.transfers.length) {
      parts.push('【12306 真实列车排图（学校↔家庭）】无直达列车，推荐中转方案：');
      directRouteData.transfers.slice(0, 3).forEach(function (p) {
        parts.push('- 经「' + p.hub + '」中转：' + p.first.trainCode + ' ' + p.first.departTime + '→' + p.first.arriveTime + '，换乘等 ' + p.wait_min + ' 分钟后乘 ' + p.second.trainCode + ' ' + p.second.departTime + '→' + p.second.arriveTime + (p.same_day ? '（当日）' : '（次日）'));
      });
    } else {
      return '';
    }
    parts.push('（数据来源：12306 官方接口）');
    return parts.join('\n');
  }

  // ---- 触发 AI 判定（需求2：判定阶段强制联网；需求3/4：按合规分支处理） ----
  function triggerAICheck() {
    if (!aiConfig || !aiConfig.api_key) return;
    if (!window.__pageData || !window.__pageData.hasResult) return;

    // 显示 AI 结果区域
    aiResultWrapper.style.display = '';
    aiResultPlatform.textContent = PLATFORM_LABELS[aiConfig.platform] || aiConfig.platform;
    aiResultContent.innerHTML = '<div class="ai-loading"><span class="ai-loading-spinner"></span><span>AI 正在联网判断中...</span></div>';

    // 滚动到 AI 结果区域
    setTimeout(function () {
      aiResultWrapper.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }, 200);

    var prompt = buildPrompt(window.__pageData);

    callAI(prompt, true).then(function (data) {
      if (data.error) {
        aiResultContent.innerHTML = '<div class="ai-result-error">' +
          '<span>&#9888;</span> AI 辅助暂不可用：' + escapeHtml(data.error) + '</div>';
        return;
      }
      if (!data.content) {
        aiResultContent.innerHTML = '<div class="ai-result-error">' +
          '<span>&#9888;</span> AI 辅助暂不可用：未返回有效内容</div>';
        return;
      }
      // 全量展示 AI 判断结果
      aiResultContent.innerHTML = formatAIResponse(data.content);

      // 判断合规性：优先解析 AI 首行结论，回退本地判定
      var aiOk = parseAIConclusion(data.content);
      var local = window.__pageData.localResult || {};
      var isOk = aiOk === true || (aiOk === null && local.ok === true);
      var isNotOk = aiOk === false || (aiOk === null && local.ok === false);

      if (isNotOk) {
        // 需求4：不合规 → 自动追问如何修改家庭所在地，并截取相关内容
        autoAskModifyHome();
      } else if (isOk) {
        // 需求3：合规 → 展示三个多选选项，勾选后进一步查询
        renderAIOptions();
      }
      // 存疑且本地也无明确结论 → 仅展示 AI 结果，不追加
    })
    .catch(function (err) {
      aiResultContent.innerHTML = '<div class="ai-result-error">' +
        '<span>&#9888;</span> AI 辅助暂不可用：网络请求失败</div>';
    });
  }

  // 解析 AI 回复首行的「结论：合规/不合规/存疑」
  function parseAIConclusion(text) {
    var m = text.match(/结论\s*[:：]\s*(合规|不合规|存疑)/);
    if (!m) return null;
    if (m[1] === '合规') return true;
    if (m[1] === '不合规') return false;
    return null;
  }

  // 统一的 AI 请求封装（web_search 可强制开启）
  function callAI(prompt, forceSearch) {
    return fetch('/api/ai_check', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        platform: aiConfig.platform,
        api_key: aiConfig.api_key,
        prompt: prompt,
        web_search: forceSearch === true ? true : (aiConfig.web_search === true)
      })
    }).then(function (res) { return res.json(); });
  }

  // ---- 需求3：合规后的三个多选选项 ----
  var OPTION_DEFS = [
    { key: 'train_info', label: '是否让AI进一步查询该线路列车信息' },
    { key: 'ticket_price', label: '是否同步查询优惠后票价' },
    { key: 'advice', label: '是否让AI给出购票及出行建议' }
  ];

  function renderAIOptions() {
    // 若已存在选项区则跳过（避免重复）
    if (document.getElementById('ai-options-box')) return;

    var box = document.createElement('div');
    box.className = 'ai-options-box';
    box.id = 'ai-options-box';

    var title = document.createElement('p');
    title.className = 'ai-options-title';
    title.textContent = '需要 AI 进一步查询以下内容？（可多选）';
    box.appendChild(title);

    var row = document.createElement('div');
    row.className = 'ai-options-list';
    OPTION_DEFS.forEach(function (def) {
      var label = document.createElement('label');
      label.className = 'ai-option-item';
      var cb = document.createElement('input');
      cb.type = 'checkbox';
      cb.value = def.key;
      cb.className = 'ai-option-cb';
      label.appendChild(cb);
      var span = document.createElement('span');
      span.textContent = def.label;
      label.appendChild(span);
      row.appendChild(label);
    });
    box.appendChild(row);

    var btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'btn-ai-continue';
    btn.textContent = '继续查询';
    btn.addEventListener('click', function () {
      var picked = [];
      box.querySelectorAll('.ai-option-cb:checked').forEach(function (cb) {
        picked.push(cb.value);
      });
      if (!picked.length) {
        btn.textContent = '请至少勾选一项';
        setTimeout(function () { btn.textContent = '继续查询'; }, 1200);
        return;
      }
      btn.disabled = true;
      btn.textContent = 'AI 查询中...';
      // 追加结果区域
      var cont = document.createElement('div');
      cont.className = 'ai-option-result';
      cont.innerHTML = '<div class="ai-loading"><span class="ai-loading-spinner"></span><span>AI 正在查询真实列车数据...</span></div>';
      box.parentNode.insertBefore(cont, box.nextSibling);

      // 步骤1：查询 12306 真实列车信息（车次/时刻/余票/公布票价）
      fetchTrainInfo().then(function (trainData) {
        var prompt = buildDeepQueryPrompt(picked, trainData);
        return callAI(prompt, false);
      }).then(function (data) {
        btn.disabled = false;
        btn.textContent = '继续查询';
        if (data.error) {
          cont.innerHTML = '<div class="ai-result-error"><span>&#9888;</span> ' + escapeHtml(data.error) + '</div>';
          return;
        }
        if (data.content) {
          // 需求3：AI 完成判断后的内容全量展示
          cont.innerHTML = '<div class="ai-option-head">🔎 AI 深度查询结果</div>' + formatAIResponse(data.content);
        } else {
          cont.innerHTML = '<div class="ai-result-error"><span>&#9888;</span> 未返回有效内容</div>';
        }
        cont.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }).catch(function () {
        btn.disabled = false;
        btn.textContent = '继续查询';
        cont.innerHTML = '<div class="ai-result-error"><span>&#9888;</span> 网络请求失败</div>';
      });
    });
    box.appendChild(btn);

    aiResultContent.appendChild(box);
  }

  // 查询 12306 真实列车数据（通过后端 /api/train_info，走 skill 官方 API）
  function fetchTrainInfo() {
    var inp = window.__pageData ? (window.__pageData.input || {}) : {};
    var from = inp.dep || inp.school || '';
    var to = inp.arr || inp.home || '';
    if (!from || !to) return Promise.resolve(null);
    return fetch('/api/train_info', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ from: from, to: to })
    }).then(function (res) { return res.json(); })
      .then(function (data) {
        if (data.error || !data.trains || !data.trains.length) return null;
        return data;
      })
      .catch(function () { return null; });
  }

  // 格式化真实列车数据（注入 prompt 用）
  function formatTrainDataForPrompt(trainData) {
    if (!trainData || !trainData.trains || !trainData.trains.length) return '';
    var parts = [];
    parts.push('【12306 实时列车数据（官方接口，' + (trainData.date || '') + '）】');
    var seatLabel = { swz: '商务/特等', tz: '特等', zy: '一等座', ze: '二等座',
                      gr: '高级软卧', rw: '软卧', dw: '动卧', yw: '硬卧', rz: '软座', yz: '硬座', wz: '无座' };
    var priceLabel = { swz_price: '商务/特等', tz_price: '特等', zy_price: '一等座', ze_price: '二等座',
                       gr_price: '高级软卧', rw_price: '软卧', yw_price: '硬卧', rz_price: '软座', yz_price: '硬座', wz_price: '无座' };
    trainData.trains.slice(0, 10).forEach(function (t, i) {
      var line = (i + 1) + '. 车次 ' + t.trainCode + '：' + t.departTime + ' → ' + t.arriveTime +
        '（历时 ' + t.duration + '，' + t.fromStation + ' → ' + t.toStation + '）';
      var seatInfo = [];
      Object.keys(seatLabel).forEach(function (k) {
        if (t[k] && t[k] !== '--' && t[k] !== '') seatInfo.push(seatLabel[k] + ':' + t[k]);
      });
      if (seatInfo.length) line += '；余票【' + seatInfo.join('，') + '】';
      var priceInfo = [];
      Object.keys(priceLabel).forEach(function (k) {
        if (t.prices && t.prices[k] && t.prices[k] !== '--' && String(t.prices[k]) !== '-1') {
          // 12306 票价为「分」单位字符串（如 00820 = 82.0 元）
          var fen = parseInt(t.prices[k], 10);
          var yuan = (fen / 10).toFixed(1);
          priceInfo.push(priceLabel[k] + ':' + yuan + '元');
        }
      });
      if (priceInfo.length) line += '；公布票价【' + priceInfo.join('，') + '】';
      parts.push(line);
    });
    return parts.join('\n');
  }

  // 构建深度查询 Prompt（需求3：按勾选项追加；注入 12306 真实数据）
  function buildDeepQueryPrompt(picked, trainData) {
    var inp = window.__pageData.input || {};
    var parts = [];
    parts.push('基于前面已确认的结论（该购票区间符合 12306 学生票优惠区间规定），请基于下方提供的 12306 官方实时列车数据回答以下内容：');
    parts.push('');
    parts.push('【行程信息】');
    parts.push('- 学校所在城市：' + (inp.school || '未填'));
    parts.push('- 家庭所在城市：' + (inp.home || '未填'));
    parts.push('- 出发站：' + (inp.dep || '未填'));
    parts.push('- 到达站：' + (inp.arr || '未填'));
    if (inp.waypoints && inp.waypoints.length) {
      parts.push('- 中转：' + inp.waypoints.join('、'));
    }
    parts.push('');
    var real = formatTrainDataForPrompt(trainData);
    if (real) {
      parts.push(real);
    } else {
      parts.push('【注意】12306 实时数据获取失败，请基于铁路客运常识与公布票价规则给出参考信息，并注明「以下为参考信息」。');
    }
    parts.push('');
    if (picked.indexOf('train_info') !== -1) {
      parts.push('1. 请基于上述真实数据介绍该线路（' + (inp.dep || '') + ' → ' + (inp.arr || '') + '）的车次与列车信息（出发/到达时间、历时、余票）。');
    }
    if (picked.indexOf('ticket_price') !== -1) {
      parts.push('2. 请基于上述公布票价给出各席别票价，并计算学生票优惠后票价（硬座 5 折、二等座 7.5 折等）。');
    }
    if (picked.indexOf('advice') !== -1) {
      parts.push('3. 请给出购票及出行建议（购票时间、证件、取票、换乘等）。');
    }
    parts.push('');
    parts.push('请用简洁的中文回答，分点列出。');
    return parts.join('\n');
  }

  // ---- 需求4：不合规 → 自动追问如何修改家庭所在地，并截取相关内容 ----
  function autoAskModifyHome() {
    if (document.getElementById('ai-home-suggest')) return; // 已存在则跳过

    var cont = document.createElement('div');
    cont.className = 'ai-home-suggest';
    cont.id = 'ai-home-suggest';
    cont.innerHTML = '<div class="ai-loading"><span class="ai-loading-spinner"></span><span>AI 正在分析家庭所在地修改建议...</span></div>';
    aiResultContent.appendChild(cont);

    var inp = window.__pageData.input || {};
    var local = window.__pageData.localResult || {};
    var parts = [];
    parts.push('该购票区间不符合 12306 学生票优惠区间规定。请分析：如果不符合优惠区间，应当如何修改家庭所在地？');
    parts.push('');
    parts.push('【用户情况】');
    parts.push('- 学校所在城市：' + (inp.school || '未填'));
    parts.push('- 当前家庭所在城市：' + (inp.home || '未填'));
    parts.push('- 出发站：' + (inp.dep || '未填'));
    parts.push('- 到达站：' + (inp.arr || '未填'));
    if (local.suggested_new_home) {
      parts.push('- 本地建议的家庭所在地：' + local.suggested_new_home);
    }
    parts.push('');
    parts.push('请重点说明：1）应该将家庭所在地修改为哪个城市；2）修改的具体操作流程；3）修改后的注意事项（如 24 小时冷却期、次数限制等）。');
    parts.push('请用简洁的中文回答，重点围绕「家庭所在地」的修改。');

    callAI(parts.join('\n'), false).then(function (data) {
      if (data.error) {
        cont.innerHTML = '<div class="ai-result-error"><span>&#9888;</span> ' + escapeHtml(data.error) + '</div>';
        return;
      }
      if (data.content) {
        // 需求4：截取 AI 回复中关于建议修改「家庭所在地」的内容
        var excerpt = extractHomeSuggestion(data.content);
        cont.innerHTML = '<div class="ai-home-head">💡 修改家庭所在地建议</div>' + formatAIResponse(excerpt);
      } else {
        cont.innerHTML = '<div class="ai-result-error"><span>&#9888;</span> 未返回有效内容</div>';
      }
      cont.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }).catch(function () {
      cont.innerHTML = '<div class="ai-result-error"><span>&#9888;</span> 网络请求失败</div>';
    });
  }

  // 截取 AI 回复中涉及「家庭所在地」修改建议的段落
  function extractHomeSuggestion(text) {
    var paras = text.split(/\n{1,}/).map(function (s) { return s.trim(); }).filter(Boolean);
    var hit = paras.filter(function (p) {
      return /家庭所在地|修改家庭|改家/.test(p);
    });
    if (hit.length) {
      return hit.join('\n');
    }
    // 无直接命中 → 返回全文中包含「家庭」的句子
    var sentHit = text.split(/(?<=[。！？!?])/).filter(function (s) {
      return /家庭/.test(s);
    });
    return sentHit.length ? sentHit.join('\n') : text;
  }

  // ---- 格式化 AI 回复（简易 Markdown → HTML） ----
  function formatAIResponse(text) {
    var html = escapeHtml(text);
    // 粗体
    html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    // 列表
    html = html.replace(/^[•\-\*]\s+(.+)$/gm, '<li>$1</li>');
    html = html.replace(/(<li>.*<\/li>\n?)+/g, function (m) { return '<ul>' + m + '</ul>'; });
    // 数字列表
    html = html.replace(/^\d+\.\s+(.+)$/gm, '<li>$1</li>');
    // 段落
    html = html.replace(/\n{2,}/g, '</p><p>');
    html = html.replace(/\n/g, '<br>');
    html = '<p>' + html + '</p>';
    return html;
  }

  function escapeHtml(str) {
    var div = document.createElement('div');
    div.appendChild(document.createTextNode(str));
    return div.innerHTML;
  }

  // ---- 页面加载后自动触发（如果已配置且有结果） ----
  // 首次加载时 aiConfig 为 null，不会自动触发
  // 只有用户在 Modal 中确认配置后才会触发

  // ---- 家庭所在地修改建议 — AI 辅助 ----
  var homeSuggestAi = document.getElementById('homeSuggestAi');
  var btnAiHomeSuggest = document.getElementById('btnAiHomeSuggest');

  // 如果 AI 已配置且有家庭修改建议，显示 AI 辅助按钮
  function updateHomeSuggestAiVisibility() {
    if (homeSuggestAi && aiConfig && aiConfig.api_key) {
      homeSuggestAi.style.display = '';
    }
  }

  // 监听配置确认事件
  if (confirmBtn) {
    confirmBtn.addEventListener('click', updateHomeSuggestAiVisibility);
  }

  // AI 辅助分析家庭修改建议
  if (btnAiHomeSuggest) {
    btnAiHomeSuggest.addEventListener('click', function () {
      if (!aiConfig || !aiConfig.api_key) return;
      if (!window.__pageData) return;

      var inp = window.__pageData.input || {};
      var local = window.__pageData.localResult || {};
      var suggestedHome = local.suggested_new_home || '';

      var prompt = buildHomeSuggestPrompt(inp, local, suggestedHome);

      // 显示加载状态
      btnAiHomeSuggest.disabled = true;
      btnAiHomeSuggest.textContent = 'AI 分析中...';

      fetch('/api/ai_check', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          platform: aiConfig.platform,
          api_key: aiConfig.api_key,
          prompt: prompt,
          web_search: aiConfig.web_search
        })
      })
      .then(function (res) { return res.json(); })
      .then(function (data) {
        btnAiHomeSuggest.disabled = false;
        btnAiHomeSuggest.textContent = 'AI 辅助分析';

        if (data.error) {
          showHomeSuggestAiResult('AI 辅助暂不可用：' + data.error, true);
          return;
        }
        if (data.content) {
          showHomeSuggestAiResult(formatAIResponse(data.content), false);
        } else {
          showHomeSuggestAiResult('AI 辅助暂不可用：未返回有效内容', true);
        }
      })
      .catch(function (err) {
        btnAiHomeSuggest.disabled = false;
        btnAiHomeSuggest.textContent = 'AI 辅助分析';
        showHomeSuggestAiResult('AI 辅助暂不可用：网络请求失败', true);
      });
    });
  }

  function buildHomeSuggestPrompt(inp, local, suggestedHome) {
    var parts = [];
    parts.push('你是一位中国铁路客运规则专家，请根据以下信息分析如何修改家庭所在地以使学生票合规。');
    parts.push('');
    parts.push('【用户情况】');
    parts.push('- 学校所在城市：' + (inp.school || '未填'));
    parts.push('- 当前家庭所在城市：' + (inp.home || '未填'));
    parts.push('- 出发站：' + (inp.dep || '未填'));
    parts.push('- 到达站：' + (inp.arr || '未填'));
    parts.push('');
    parts.push('【本地引擎判定】');
    parts.push('- 是否合规：不合规');
    parts.push('- 原因：' + (local.reason || '购票区间超出优惠区间'));
    parts.push('- 建议修改家庭所在地为：' + suggestedHome);
    if (local.new_path && local.new_path.length) {
      parts.push('- 修改后合规路径：' + local.new_path.join(' → '));
    }
    parts.push('');
    parts.push('【请你分析】');
    parts.push('1. 将家庭所在地修改为「' + suggestedHome + '」是否合理？需要满足什么条件？');
    parts.push('2. 修改家庭所在地的具体流程是什么？（12306 App 操作步骤）');
    parts.push('3. 修改后有哪些注意事项？（冷却期、次数限制等）');
    parts.push('4. 如果不修改家庭所在地，还有其他合规购票方案吗？');
    parts.push('');
    parts.push('请用简洁的中文回答，控制在 400 字以内。');
    return parts.join('\n');
  }

  function showHomeSuggestAiResult(htmlContent, isError) {
    // 在建议卡片下方插入 AI 结果
    var card = document.querySelector('.home-suggest-card');
    if (!card) return;

    var existing = card.querySelector('.home-suggest-ai-result');
    if (existing) existing.remove();

    var div = document.createElement('div');
    div.className = 'home-suggest-ai-result' + (isError ? ' error' : '');
    div.innerHTML = htmlContent;
    card.appendChild(div);

    // 滚动到结果
    setTimeout(function () {
      div.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }, 100);
  }

  // ---- 直达/中转列车查询（12306 真实排图，融入本地判定展示） ----
  // 有判定结果时自动查询：学校↔家庭 是否有直达列车；无直达时给出真实中转方案。
  // 支持日期选择：当日 + 未来 14 天（共 15 天），晚间查询可看后续日期车次。
  var directWrapper = document.getElementById('direct-route-wrapper');
  var directDesc = document.getElementById('direct-route-desc');
  var directContent = document.getElementById('direct-route-content');
  var directDateSel = document.getElementById('direct-route-date');
  var directRouteData = null; // 供 AI prompt 注入
  var directSelectedDate = null; // 用户选择的日期（YYYY-MM-DD）

  // 生成当日 + 未来 14 天选项（共 15 天）
  function initDirectDateOptions() {
    if (!directDateSel) return;
    var WEEK = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'];
    var today = new Date();
    for (var i = 0; i < 15; i++) {
      var d = new Date(today.getFullYear(), today.getMonth(), today.getDate() + i);
      var ymd = d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0');
      var label = ymd + ' ' + WEEK[d.getDay()] + (i === 0 ? '（今天）' : '');
      var opt = document.createElement('option');
      opt.value = ymd;
      opt.textContent = label;
      directDateSel.appendChild(opt);
    }
    directDateSel.value = directDateSel.options[0].value;
    directSelectedDate = directDateSel.value;
    // 切换日期重新查询
    directDateSel.addEventListener('change', function () {
      directSelectedDate = this.value;
      fetchDirectRoute();
    });
  }

  function fetchDirectRoute() {
    if (!window.__pageData || !window.__pageData.hasResult) return;
    if (!directWrapper || !directContent) return;
    var inp = window.__pageData.input || {};
    var from = inp.school || '';
    var to = inp.home || '';
    if (!from || !to) return;

    directWrapper.style.display = '';
    directContent.innerHTML = '<div class="ai-loading"><span class="ai-loading-spinner"></span><span>正在查询 12306 真实列车排图（' + escapeHtml(from) + ' → ' + escapeHtml(to) + ' · ' + (directSelectedDate || '今日') + '）...</span></div>';

    var payload = { from: from, to: to };
    if (directSelectedDate) payload.date = directSelectedDate;
    // 传学校/家庭城市，供后端做学生票合规审核
    payload.school = inp.school || '';
    payload.home = inp.home || '';

    fetch('/api/direct_route', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    }).then(function (res) { return res.json(); })
      .then(function (data) {
        if (data.error) {
          directContent.innerHTML = '<div class="ai-result-error"><span>&#9888;</span> 列车查询暂不可用：' + escapeHtml(data.error) + '</div>';
          return;
        }
        directRouteData = data;
        renderDirectRoute(data);
      })
      .catch(function () {
        directContent.innerHTML = '<div class="ai-result-error"><span>&#9888;</span> 列车查询网络失败</div>';
      });
  }

  function renderDirectRoute(data) {
    if (!directDesc || !directContent) return;
    var d = data.date || '';
    if (data.has_direct && data.direct && data.direct.length) {
      directDesc.textContent = '直达车次 ' + data.direct.length + ' 趟 · ' + d;
      var rows = data.direct.slice(0, 8).map(function (t) {
        return '<tr><td class="dr-code">' + escapeHtml(t.trainCode) + '</td>' +
          '<td>' + escapeHtml(t.fromStation) + ' ' + escapeHtml(t.departTime) + ' → ' + escapeHtml(t.arriveTime) + ' ' + escapeHtml(t.toStation) + '</td>' +
          '<td>' + escapeHtml(t.duration) + '</td>' +
          '<td>' + (t.canBuy === 'Y' ? '<span class="dr-ok">可购</span>' : '<span class="dr-no">售罄</span>') + '</td></tr>';
      }).join('');
      directContent.innerHTML = '<table class="dr-table"><thead><tr><th>车次</th><th>出发 → 到达</th><th>历时</th><th>状态</th></tr></thead><tbody>' + rows + '</tbody></table>' +
        '<p class="dr-note">数据来源：12306 官方接口 · ' + d + '</p>';
    } else if (data.transfers && data.transfers.length) {
      var srcLabel = data.source === 'local_fallback' ? '（本地合规方案推荐）' : '';
      directDesc.textContent = '无直达列车 · 推荐 ' + data.transfers.length + ' 个中转方案 · ' + d + srcLabel;

      // 推荐依据标签区（时间最短/价格最优/路径最短）
      var recsHtml = '';
      if (data.recommendations && data.recommendations.length) {
        var recItems = data.recommendations.map(function (r) {
          var icon = r.label === '时间最短' ? '⏱️' : (r.label === '价格最优' ? '💰' : '🗺️');
          return '<div class="dr-rec-item"><span class="dr-rec-label">' + icon + ' ' + escapeHtml(r.label) + '</span>' +
            '<span class="dr-rec-desc">经<strong>' + escapeHtml(r.hub) + '</strong>中转 · ' + escapeHtml(r.reason) + '</span></div>';
        }).join('');
        recsHtml = '<div class="dr-recommendations"><div class="dr-rec-title">🎯 推荐方案（按不同标准）</div>' + recItems + '</div>';
      }

      var items = data.transfers.map(function (p) {
        var f = p.first, s = p.second;
        var audit = p.audit || null;
        // 该方案命中的推荐标签
        var recTags = '';
        if (data.recommendations) {
          var hits = data.recommendations.filter(function (r) {
            return r.hub === p.hub && Math.abs((r.total_min || 0) - (p.total_min || 0)) < 60 && (r.price === null || Math.abs((r.price || 0) - ((p.price_info || {}).total || 0)) < 1);
          });
          if (!hits.length) {
            hits = data.recommendations.filter(function (r) { return r.hub === p.hub; });
          }
          recTags = hits.map(function (r) {
            var icon = r.label === '时间最短' ? '⏱️' : (r.label === '价格最优' ? '💰' : '🗺️');
            return '<span class="dr-rec-tag">' + icon + ' ' + escapeHtml(r.label) + '</span>';
          }).join('');
          if (recTags) recTags = '<div class="dr-rec-tags">' + recTags + '</div>';
        }
        // 合规标注徽章
        var segBadges = '';
        if (audit && audit.segments && audit.segments.length) {
          segBadges = audit.segments.map(function (sg) {
            var cls = sg.ok ? 'dr-badge-student' : 'dr-badge-adult';
            return '<span class="' + cls + '">' + escapeHtml(sg.dep) + '→' + escapeHtml(sg.arr) + ' ' + escapeHtml(sg.ticket_type) + '</span>';
          }).join('');
        }
        var overallBadge = '';
        if (audit) {
          if (audit.overall_ok) {
            overallBadge = '<div class="dr-audit dr-audit-ok">✅ 全程符合学生票优惠条件</div>';
          } else if (audit.has_student && audit.has_adult) {
            overallBadge = '<div class="dr-audit dr-audit-part">⚠️ 部分区间符合：请按标注购买对应区间车票</div>';
          } else if (audit.has_student) {
            overallBadge = '<div class="dr-audit dr-audit-ok">✅ 全程符合学生票优惠条件</div>';
          }
        }
        var srcTag = p.source === 'local' ? '<span class="dr-src-tag">本地合规推荐</span>' : '';
        // 票价行
        var priceInfo = p.price_info || null;
        var priceHtml = '';
        if (priceInfo && priceInfo.has_price) {
          var legPrices = priceInfo.legs.map(function (l) {
            return '<span class="dr-leg-price">' + escapeHtml(l.dep) + '→' + escapeHtml(l.arr) + ' ¥' + l.price +
              '（' + escapeHtml(l.seat_label) + (l.is_student ? '·学生' : '') + '）</span>';
          }).join('');
          priceHtml = '<div class="dr-price-row"><span class="dr-price-total">总票价 ¥' + priceInfo.total + '</span>' + legPrices + '</div>';
        }
        return '<div class="dr-transfer">' +
          '<div class="dr-t-head">🔄 经 <strong>' + escapeHtml(p.hub) + '</strong> 中转（换乘等待 ' + p.wait_min + ' 分钟' + (p.same_day ? '，当日' : '，次日') + ' · 总行程约 ' + Math.round(p.total_min / 60) + ' 小时）' + srcTag + '</div>' +
          (recTags || '') +
          '<div class="dr-t-leg">① ' + escapeHtml(f.trainCode) + ' ' + escapeHtml(f.departTime) + ' → ' + escapeHtml(f.arriveTime) + '（' + escapeHtml(f.fromStation) + ' → ' + escapeHtml(f.toStation) + '）</div>' +
          '<div class="dr-t-leg">② ' + escapeHtml(s.trainCode) + ' ' + escapeHtml(s.departTime) + ' → ' + escapeHtml(s.arriveTime) + '（' + escapeHtml(s.fromStation) + ' → ' + escapeHtml(s.toStation) + '）</div>' +
          (segBadges ? '<div class="dr-seg-badges">' + segBadges + '</div>' : '') +
          (overallBadge || '') +
          (priceHtml || '') +
          '</div>';
      }).join('');
      directContent.innerHTML = (recsHtml || '') + items + '<p class="dr-note">数据来源：12306 官方接口 · 方案按总行程时间排序（路径最短优先） · ' + d + '</p>';
    } else {
      directDesc.textContent = '未找到直达列车与中转方案 · ' + d;
      directContent.innerHTML = '<p class="dr-note">当前日期无可用车次，建议更换出行日期重试。</p>';
    }
  }

  // 有本地判定结果时自动触发直达/中转查询
  (function autoDirectRoute() {
    if (!window.__pageData || !window.__pageData.hasResult) return;
    initDirectDateOptions();   // 生成 15 天日期选项
    setTimeout(fetchDirectRoute, 200);
  })();

  // ---- 页面加载：恢复持久化配置，自动补触发 AI 判定 ----
  // 场景：用户已配置 API Key → 点击「开始判断」→ 表单整页提交刷新 →
  // sessionStorage 恢复配置 → 页面有本地结果 → 自动重新执行 AI 判定（不断链）。
  (function autoResumeAI() {
    if (!aiConfig || !aiConfig.api_key) return;
    updateStatusDot();
    if (!window.__pageData || !window.__pageData.hasResult) return;
    // 若 AI 结果区尚未有有效内容（避免重复渲染），则自动触发
    if (aiResultWrapper && aiResultWrapper.style.display !== 'none') return;
    setTimeout(triggerAICheck, 300);
  })();
})();
